"""
多任务对比API (T044)
提供两种方式获取对比数据：POST /compare 和 GET /compare/data。
路由前缀: /api/v1/compare
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from db import get_db
from models.task import Task
from models.dataset import Dataset
from schemas.task import CompareRequest, CompareResponse, TaskSummary

router = APIRouter(prefix="/compare", tags=["compare"])


def _task_to_summary(task: Task, dataset_name: str) -> TaskSummary:
    """Task ORM → TaskSummary"""
    return TaskSummary(
        id=task.id,
        name=task.name,
        agent_version=task.agent_version,
        dataset_name=dataset_name,
        dataset_id=task.dataset_id,
        metrics=task.metrics or [],
        agent_endpoint=task.agent_endpoint,
        status=task.status,
        progress_current=task.progress_current,
        progress_total=task.progress_total,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


# ── POST /compare — 提交对比请求 ──
@router.post("", response_model=CompareResponse)
def compare_tasks(body: CompareRequest, db: Session = Depends(get_db)):
    """对指定任务列表进行指标对比分析（至少2个任务，且必须已完成）"""
    return _build_comparison(body.task_ids, db)


# ── GET /compare/data — 便捷GET方式 ──
@router.get("/data", response_model=CompareResponse)
def compare_tasks_get(
    ids: str = Query(..., description="逗号分隔的任务ID列表，如 'id1,id2'"),
    db: Session = Depends(get_db),
):
    """GET便捷方式获取对比数据"""
    task_ids = [tid.strip() for tid in ids.split(",") if tid.strip()]
    if len(task_ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个任务ID进行对比")
    return _build_comparison(task_ids, db)


def _build_comparison(task_ids: list, db: Session) -> CompareResponse:
    """构建对比数据的核心逻辑"""
    if len(task_ids) < 2:
        raise HTTPException(status_code=400, detail="至少需要2个任务ID进行对比")

    # 查询并校验任务
    tasks = []
    tasks_summary = []
    for tid in task_ids:
        task = db.execute(
            select(Task).where(Task.id == tid)
        ).scalar_one_or_none()
        if not task:
            raise HTTPException(status_code=404, detail=f"任务未找到: {tid}")
        if task.status not in ("done", "failed"):
            raise HTTPException(
                status_code=400,
                detail=f"任务 '{task.name}' 尚未完成（状态: {task.status}）",
            )

        # 获取数据集名称
        dataset = db.execute(
            select(Dataset.name).where(Dataset.id == task.dataset_id)
        ).scalar_one_or_none()

        tasks.append(task)
        tasks_summary.append(_task_to_summary(task, dataset or "未知数据集"))

    # 收集所有出现过的指标名称
    all_metrics = set()
    for t in tasks:
        if t.result and t.result.get("metric_scores"):
            all_metrics.update(t.result["metric_scores"].keys())

    metric_names = sorted(all_metrics)

    # 构建每个任务的分数对比
    scores = []
    for t in tasks:
        result = t.result or {}
        scores.append({
            "task_id": t.id,
            "task_name": t.name,
            "metric_scores": result.get("metric_scores", {}),
            "overall_score": result.get("overall_score", 0.0),
        })

    return CompareResponse(
        tasks=tasks_summary,
        metrics_comparison={
            "metric_names": metric_names,
            "scores": scores,
        },
    )
