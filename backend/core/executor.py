"""
评估执行引擎 (T032)
在后台线程中异步执行评估任务的核心引擎。

核心流程：
1. 轮询pending状态的任务
2. 并发控制（最多3个同时执行）
3. 逐个测试用例调用Agent Platform API
4. 每个用例计算所选指标得分
5. 更新进度，推送WebSocket通知
6. 汇总结果并写入数据库
"""

import time
import threading
import logging
from datetime import datetime, timezone
from typing import Optional

import httpx

from db import SessionLocal
from models.task import Task
from models.dataset import Dataset
from core.metric_factory import MetricRegistry

# 导入指标模块以触发注册
import core.metrics.success_rate  # noqa: F401
import core.metrics.tool_accuracy  # noqa: F401
import core.metrics.llm_judge  # noqa: F401
import core.metrics.response_time  # noqa: F401

logger = logging.getLogger(__name__)

# 并发限制
MAX_CONCURRENT = 3
# 单个用例超时（秒）
CASE_TIMEOUT = 120
# 轮询间隔（秒）
POLL_INTERVAL = 2


class EvaluationExecutor:
    """
    评估执行器——后台线程持续轮询pending任务并执行评估。

    使用方式:
        executor = EvaluationExecutor()
        executor.start()  # 启动后台线程
        executor.stop()   # 优雅关闭
    """

    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._running = False
        # 跟踪当前运行中的任务数
        self._active_count = 0
        self._lock = threading.Lock()

    def start(self):
        """启动后台执行线程"""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        logger.info("评估执行器已启动（最大并发: %d）", MAX_CONCURRENT)

    def stop(self):
        """停止后台执行线程"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=30)
        logger.info("评估执行器已停止")

    def _run_loop(self):
        """主轮询循环"""
        while self._running:
            try:
                # 检查是否有空闲槽位
                with self._lock:
                    available = MAX_CONCURRENT - self._active_count

                if available > 0:
                    # 获取pending任务
                    db = SessionLocal()
                    try:
                        pending_task = (
                            db.query(Task)
                            .filter(Task.status == "pending")
                            .order_by(Task.created_at.asc())
                            .first()
                        )

                        if pending_task:
                            with self._lock:
                                self._active_count += 1
                            # 在新线程中异步执行
                            t = threading.Thread(
                                target=self._execute_task,
                                args=(pending_task.id,),
                                daemon=True,
                            )
                            t.start()
                    finally:
                        db.close()

            except Exception:
                logger.exception("执行器轮询异常")

            # 轮询间隔
            time.sleep(POLL_INTERVAL)

    def _execute_task(self, task_id: str):
        """
        执行单个评估任务的核心逻辑。

        Args:
            task_id: 任务ID
        """
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if not task or task.status != "pending":
                return

            # 加载关联的数据集
            dataset = (
                db.query(Dataset).filter(Dataset.id == task.dataset_id).first()
            )
            if not dataset or not dataset.cases:
                self._fail_task(db, task, "关联的数据集为空或不存在")
                return

            # 标记任务为运行中
            task.status = "running"
            db.commit()

            logger.info("开始执行任务: %s (%d个用例)", task.name, len(dataset.cases))

            # ── 逐个执行测试用例 ──
            case_results = []
            started_at = datetime.now(timezone.utc)
            metric_names = task.metrics or []

            for idx, case_meta in enumerate(dataset.cases):
                case_id = case_meta.get("id", f"case_{idx}")
                logger.debug("  执行用例: %s [%d/%d]", case_id, idx + 1, len(dataset.cases))

                # 调用Agent Platform
                try:
                    agent_response = self._call_agent(
                        task.agent_endpoint, case_meta, CASE_TIMEOUT
                    )
                    case_result = self._evaluate_case(
                        case_meta, agent_response, metric_names
                    )
                except httpx.TimeoutException:
                    case_result = self._error_case(
                        case_meta, "timeout", f"用例超时（>{CASE_TIMEOUT}秒）"
                    )
                except httpx.ConnectError:
                    case_result = self._error_case(
                        case_meta, "connection_error", "无法连接到Agent Platform"
                    )
                except Exception as e:
                    logger.exception("用例执行异常: %s", case_id)
                    case_result = self._error_case(
                        case_meta, "error", str(e)[:500]
                    )

                case_results.append(case_result)

                # 更新进度
                task.progress_current = idx + 1
                db.commit()

                # 通过WebSocket推送进度更新
                self._broadcast_progress(task.id, task.progress_current, task.progress_total, "running")

            # ── 汇总计算总分 ──
            completed_at = datetime.now(timezone.utc)
            execution_time = (completed_at - started_at).total_seconds()

            # 计算权重
            weight_config = task.weight_config or {}
            if not weight_config:
                # 等权重
                w = 1.0 / len(metric_names) if metric_names else 1.0
                weight_config = {name: w for name in metric_names}

            # 计算各指标均分
            metric_sums: dict = {name: 0.0 for name in metric_names}
            valid_counts: dict = {name: 0 for name in metric_names}
            for cr in case_results:
                for name in metric_names:
                    s = cr.get("metric_scores", {}).get(name)
                    if s is not None:
                        metric_sums[name] += s
                        valid_counts[name] += 1

            metric_scores = {}
            for name in metric_names:
                if valid_counts[name] > 0:
                    metric_scores[name] = round(
                        metric_sums[name] / valid_counts[name], 4
                    )
                else:
                    metric_scores[name] = 0.0

            # 加权总分
            overall_score = round(
                sum(
                    metric_scores.get(name, 0.0) * weight_config.get(name, 0.0)
                    for name in metric_names
                ),
                4,
            )

            # ── 存储结果 ──
            result_data = {
                "overall_score": overall_score,
                "metric_scores": metric_scores,
                "case_results": case_results,
                "execution_time_seconds": round(execution_time, 2),
                "started_at": started_at.isoformat(),
                "completed_at": completed_at.isoformat(),
            }

            task.result = result_data
            task.status = "done"
            db.commit()

            # 广播完成状态
            self._broadcast_progress(
                task.id,
                len(dataset.cases),
                len(dataset.cases),
                "done",
            )

            logger.info(
                "任务完成: %s, 总分=%.3f, 耗时=%.1fs",
                task.name,
                overall_score,
                execution_time,
            )

        except Exception:
            logger.exception("任务执行异常: %s", task_id)
            try:
                self._fail_task(db, task, "执行引擎内部异常")
            except Exception:
                pass
        finally:
            db.close()
            with self._lock:
                self._active_count -= 1

    def _call_agent(
        self,
        endpoint: str,
        case_meta: dict,
        timeout: int,
    ) -> dict:
        """
        调用外部Agent Platform API。

        Args:
            endpoint: Agent Platform的评估端点URL
            case_meta: 测试用例数据
            timeout: 超时秒数

        Returns:
            Agent Platform的响应JSON

        Raises:
            httpx.TimeoutException: 请求超时
            httpx.ConnectError: 连接失败
        """
        request_body = {
            "input": case_meta.get("input", ""),
            "session_config": {
                "case_id": case_meta.get("id"),
                "difficulty": case_meta.get("difficulty"),
            },
        }

        with httpx.Client(timeout=timeout) as client:
            response = client.post(endpoint, json=request_body)
            response.raise_for_status()
            return response.json()

    def _evaluate_case(
        self,
        case_meta: dict,
        agent_response: dict,
        metric_names: list,
    ) -> dict:
        """
        对单个用例执行所有选定指标的计算。

        Args:
            case_meta: 测试用例元数据
            agent_response: Agent Platform的原始响应
            metric_names: 要计算的指标名称列表

        Returns:
            CaseResult结构
        """
        # 构造指标计算所需的输入
        compute_input = {
            "case_meta": case_meta,
            "agent_output": agent_response.get("output", {}),
            "agent_trace": agent_response.get("trace", []),
            "agent_metrics": agent_response.get("metrics", {}),
        }

        metric_scores = {}
        metric_details = {}

        for name in metric_names:
            metric = MetricRegistry.get(name)
            if metric is None:
                metric_scores[name] = 0.0
                metric_details[name] = {"error": f"未知指标: {name}"}
                continue

            try:
                result = metric.compute(compute_input)
                metric_scores[name] = result.get("score", 0.0)
                metric_details[name] = result.get("details", {})
            except Exception as e:
                logger.exception("指标计算失败: %s", name)
                metric_scores[name] = 0.0
                metric_details[name] = {"error": str(e)[:200]}

        return {
            "case_id": case_meta.get("id", "unknown"),
            "status": "passed",  # 单用例总是"passed"，除非抛出异常
            "metric_scores": metric_scores,
            "metric_details": metric_details,
            "agent_output": agent_response.get("output"),
            "agent_trace": agent_response.get("trace", []),
            "error_message": None,
        }

    def _error_case(self, case_meta: dict, error_type: str, message: str) -> dict:
        """构造错误用例结果"""
        return {
            "case_id": case_meta.get("id", "unknown"),
            "status": "error",
            "metric_scores": {},
            "metric_details": {"error_type": error_type, "message": message},
            "agent_output": None,
            "agent_trace": [],
            "error_message": f"[{error_type}] {message}",
        }

    def _fail_task(self, db, task: Task, message: str):
        """将任务标记为失败状态"""
        if task:
            task.status = "failed"
            task.error_message = message
            db.commit()
            self._broadcast_progress(task.id, task.progress_current, task.progress_total, "failed")

    def _broadcast_progress(self, task_id: str, current: int, total: int, status: str):
        """通过WebSocket广播进度更新"""
        try:
            import asyncio
            from ws.manager import ws_manager

            loop = asyncio.new_event_loop()
            loop.run_until_complete(
                ws_manager.broadcast(
                    task_id,
                    {
                        "task_id": task_id,
                        "progress_current": current,
                        "progress_total": total,
                        "status": status,
                    },
                )
            )
            loop.close()
        except Exception:
            # WebSocket推送失败不影响主流程
            pass
