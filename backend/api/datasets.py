"""
数据集管理API (T018)
提供数据集的CRUD操作：列表、上传、查看详情、删除。
路由前缀: /api/v1/datasets
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select

from db import get_db
from models.dataset import Dataset
from models.task import Task
from schemas.dataset import (
    DatasetCreate,
    DatasetSummary,
    DatasetDetail,
    SuccessResponse,
)

router = APIRouter(prefix="/datasets", tags=["datasets"])


# ── GET /datasets — 获取所有数据集列表 ──
@router.get("", response_model=List[DatasetSummary])
def list_datasets(db: Session = Depends(get_db)):
    """返回所有数据集的摘要列表（不含测试用例详情）"""
    datasets = db.execute(select(Dataset).order_by(Dataset.created_at.desc())).scalars().all()
    return [
        DatasetSummary(
            id=ds.id,
            name=ds.name,
            description=ds.description,
            case_count=ds.case_count,
            created_at=ds.created_at,
        )
        for ds in datasets
    ]


# ── POST /datasets — 上传新数据集 ──
@router.post("", response_model=DatasetSummary, status_code=201)
def create_dataset(body: DatasetCreate, db: Session = Depends(get_db)):
    """上传新的数据集（JSON格式），校验用例ID唯一性"""
    # 检查数据集名称是否已存在
    existing = db.execute(
        select(Dataset).where(Dataset.name == body.name)
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail=f"数据集名称 '{body.name}' 已存在")

    # 创建数据集记录（cases以dict列表存储）
    dataset = Dataset(
        name=body.name,
        description=body.description,
        cases=[case.model_dump() for case in body.cases],
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    return DatasetSummary(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        case_count=dataset.case_count,
        created_at=dataset.created_at,
    )


# ── GET /datasets/{dataset_id} — 获取数据集详情 ──
@router.get("/{dataset_id}", response_model=DatasetDetail)
def get_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """获取数据集详情，包含全部测试用例"""
    dataset = db.execute(
        select(Dataset).where(Dataset.id == dataset_id)
    ).scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    return DatasetDetail(
        id=dataset.id,
        name=dataset.name,
        description=dataset.description,
        case_count=dataset.case_count,
        created_at=dataset.created_at,
        cases=dataset.cases,
    )


# ── DELETE /datasets/{dataset_id} — 删除数据集 ──
@router.delete("/{dataset_id}", response_model=SuccessResponse)
def delete_dataset(dataset_id: str, db: Session = Depends(get_db)):
    """删除数据集（仅当无运行中的任务引用时允许）"""
    dataset = db.execute(
        select(Dataset).where(Dataset.id == dataset_id)
    ).scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail="数据集未找到")

    # 检查是否有运行中的任务引用此数据集
    running_task = db.execute(
        select(Task).where(
            Task.dataset_id == dataset_id,
            Task.status == "running",
        )
    ).scalar_one_or_none()

    if running_task:
        raise HTTPException(
            status_code=409,
            detail="无法删除：有运行中的任务正在使用此数据集",
        )

    db.delete(dataset)
    db.commit()

    return SuccessResponse(success=True)
