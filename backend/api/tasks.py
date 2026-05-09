"""
评估任务管理API (T024 / T025)
提供任务的CRUD操作：列表、创建、查看、删除、执行、结果查询。
路由前缀: /api/v1/tasks
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from db import get_db
from models.task import Task
from models.dataset import Dataset
from schemas.dataset import SuccessResponse
from schemas.task import (
    TaskCreate,
    TaskSummary,
    TaskListResponse,
    TaskDetail,
    EvaluationResult,
    ResultSummary,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])


# ── 辅助函数：将Task ORM对象转为TaskSummary ──
def _to_summary(task: Task) -> TaskSummary:
    """将ORM Task对象转换为TaskSummary（含dataset_name解析）"""
    return TaskSummary(
        id=task.id,
        name=task.name,
        agent_version=task.agent_version,
        dataset_name="",  # 由调用方填充
        dataset_id=task.dataset_id,
        metrics=task.metrics or [],
        agent_endpoint=task.agent_endpoint,
        adapter_type=getattr(task, "adapter_type", None) or "native",
        status=task.status,
        progress_current=task.progress_current,
        progress_total=task.progress_total,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


def _to_detail(task: Task, dataset_name: str = "") -> TaskDetail:
    """将ORM Task对象转换为TaskDetail"""
    return TaskDetail(
        id=task.id,
        name=task.name,
        agent_version=task.agent_version,
        dataset_name=dataset_name,
        dataset_id=task.dataset_id,
        metrics=task.metrics or [],
        agent_endpoint=task.agent_endpoint,
        adapter_type=getattr(task, "adapter_type", None) or "native",
        status=task.status,
        progress_current=task.progress_current,
        progress_total=task.progress_total,
        created_at=task.created_at,
        updated_at=task.updated_at,
        weight_config=task.weight_config,
        adapter_config=getattr(task, "adapter_config", None),
        result=task.result,
        error_message=task.error_message,
    )


# ── GET /tasks — 分页获取任务列表 ──
@router.get("", response_model=TaskListResponse)
def list_tasks(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(10, ge=1, le=100, description="每页条数"),
    status: Optional[str] = Query(None, description="按状态筛选"),
    db: Session = Depends(get_db),
):
    """返回分页的任务列表，支持按状态筛选"""
    # 构建查询
    query = select(Task)
    count_query = select(func.count(Task.id))

    if status:
        query = query.where(Task.status == status)
        count_query = count_query.where(Task.status == status)

    # 查询总数
    total = db.execute(count_query).scalar() or 0

    # 分页查询
    offset = (page - 1) * size
    tasks = (
        db.execute(query.order_by(Task.created_at.desc()).offset(offset).limit(size))
        .scalars()
        .all()
    )

    # 构建响应（需要解析dataset_name）
    items = []
    for task in tasks:
        summary = _to_summary(task)
        # 关联查询dataset_name
        dataset = db.execute(
            select(Dataset.name).where(Dataset.id == task.dataset_id)
        ).scalar_one_or_none()
        summary.dataset_name = dataset or "未知数据集"
        items.append(summary)

    return TaskListResponse(items=items, total=total, page=page, size=size)


# ── POST /tasks — 创建新任务 ──
@router.post("", response_model=TaskSummary, status_code=201)
def create_task(body: TaskCreate, db: Session = Depends(get_db)):
    """创建新的评估任务，校验数据集存在且指标合法"""
    # 校验数据集存在
    dataset = db.execute(
        select(Dataset).where(Dataset.id == body.dataset_id)
    ).scalar_one_or_none()
    if not dataset:
        raise HTTPException(status_code=400, detail="指定的数据集不存在")

    # 校验数据集非空
    if not dataset.cases or len(dataset.cases) == 0:
        raise HTTPException(status_code=400, detail="数据集为空，无法创建评估任务")

    # 校验适配器类型(避免持久化非法值)
    from core.adapters.base import AdapterRegistry
    import core.adapters  # noqa: F401  触发适配器注册

    if not AdapterRegistry.is_registered(body.adapter_type):
        raise HTTPException(
            status_code=400,
            detail=f"未知的适配器类型: '{body.adapter_type}',可选: {list(AdapterRegistry.list_all().keys())}",
        )

    # 创建任务
    task = Task(
        name=body.name,
        agent_version=body.agent_version,
        dataset_id=body.dataset_id,
        metrics=body.metrics,
        agent_endpoint=body.agent_endpoint,
        adapter_type=body.adapter_type,
        adapter_config=body.adapter_config,
        weight_config=body.weight_config,
        # status='draft' 表示"已创建但未提交执行",
        # executor 后台轮询只取 'pending' 不取 'draft',因此用户必须手动点"执行"
        status="draft",
        progress_total=dataset.case_count,
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    summary = _to_summary(task)
    summary.dataset_name = dataset.name
    return summary


# ── GET /tasks/{task_id} — 获取任务详情 ──
@router.get("/{task_id}", response_model=TaskDetail)
def get_task(task_id: str, db: Session = Depends(get_db)):
    """获取任务详情（含结果数据）"""
    task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")

    # 获取数据集名称
    dataset = db.execute(
        select(Dataset.name).where(Dataset.id == task.dataset_id)
    ).scalar_one_or_none()

    return _to_detail(task, dataset_name=dataset or "未知数据集")


# ── DELETE /tasks/{task_id} — 删除任务 ──
@router.delete("/{task_id}", response_model=SuccessResponse)
def delete_task(task_id: str, db: Session = Depends(get_db)):
    """删除任务（仅非运行状态可删除）"""
    task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")

    if task.status == "running":
        raise HTTPException(status_code=409, detail="无法删除正在运行的任务")

    db.delete(task)
    db.commit()

    return SuccessResponse(success=True)


# ── POST /tasks/{task_id}/execute — 启动任务执行 ──
@router.post("/{task_id}/execute", response_model=TaskSummary)
def execute_task(task_id: str, db: Session = Depends(get_db)):
    """手动触发任务执行（状态从pending变为running）"""
    task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")

    if task.status == "running":
        raise HTTPException(status_code=409, detail="任务已在运行中")

    # 允许的可执行起始状态:
    # - draft   : 刚创建,从未跑过(默认)
    # - pending : 已排队等待 executor 拾取
    # - failed  : 上一次跑失败,允许重试
    # done 状态不允许覆盖,要重跑请用"重跑"按钮(创建一个新任务)
    if task.status not in ("draft", "pending", "failed"):
        raise HTTPException(
            status_code=409,
            detail=f"当前状态 '{task.status}' 不允许执行;如需重跑请使用'重跑'按钮",
        )

    # 转入 pending 队列,由 executor 后台线程接管;同时清空上次结果
    task.status = "pending"
    task.progress_current = 0
    task.error_message = None
    task.result = None
    db.commit()
    db.refresh(task)

    dataset = db.execute(
        select(Dataset.name).where(Dataset.id == task.dataset_id)
    ).scalar_one_or_none()

    summary = _to_summary(task)
    summary.dataset_name = dataset or "未知数据集"
    return summary


# ── GET /tasks/{task_id}/result — 获取完整评估结果 ──
@router.get("/{task_id}/result", response_model=EvaluationResult)
def get_task_result(task_id: str, db: Session = Depends(get_db)):
    """获取任务的完整评估结果（含每用例详情）"""
    task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")

    if task.status not in ("done", "failed"):
        raise HTTPException(
            status_code=404,
            detail="任务尚未完成，结果不可用",
        )

    if task.result is None:
        raise HTTPException(status_code=404, detail="任务结果数据为空")

    return EvaluationResult(**task.result)


# ── GET /tasks/{task_id}/result/summary — 获取结果摘要 ──
@router.get("/{task_id}/result/summary", response_model=ResultSummary)
def get_task_result_summary(task_id: str, db: Session = Depends(get_db)):
    """获取任务结果摘要（仅总分和各指标均分）"""
    task = db.execute(select(Task).where(Task.id == task_id)).scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="任务未找到")

    if task.status not in ("done", "failed"):
        raise HTTPException(
            status_code=404,
            detail="任务尚未完成",
        )

    result = task.result or {}
    return ResultSummary(
        overall_score=result.get("overall_score", 0.0),
        metric_scores=result.get("metric_scores", {}),
    )
