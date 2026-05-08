"""
数据库初始化 & 种子数据脚本 (T054)
创建数据表并导入预置的旅行规划测试用例数据集。
首次启动时自动调用，重复运行安全（幂等）。

运行方式:
    cd backend
    python init_db.py
"""

import json
import os
from db import SessionLocal, engine, Base, init_db as setup_db


def seed_default_dataset():
    """导入预置旅行规划数据集（如果不存在）"""
    # 查找 datasets/travel_cases.json
    dataset_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "datasets",
        "travel_cases.json",
    )

    if not os.path.exists(dataset_path):
        print(f"种子数据文件未找到: {dataset_path}")
        return

    with open(dataset_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    from models.dataset import Dataset
    from sqlalchemy import select

    db = SessionLocal()
    try:
        # 检查是否已存在同名数据集（幂等导入）
        existing = db.execute(
            select(Dataset).where(Dataset.name == data["name"])
        ).scalar_one_or_none()

        if existing:
            print(f"种子数据集已存在: '{data['name']}' ({existing.case_count}个用例)，跳过导入")
            return

        dataset = Dataset(
            name=data["name"],
            description=data.get("description", ""),
            cases=data["cases"],
        )
        db.add(dataset)
        db.commit()
        print(f"种子数据集已导入: '{dataset.name}' ({dataset.case_count}个用例)")
    except Exception as e:
        db.rollback()
        print(f"导入种子数据失败: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("初始化数据库表...")
    setup_db()
    print("数据库表创建完成")

    print("导入种子数据...")
    seed_default_dataset()
    print("数据库初始化完成")
