"""
Dataset ORM模型 (T009)
对应数据模型中的Dataset实体，存储测试用例集合。
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, JSON
from db import Base


class Dataset(Base):
    """数据集——包含多个测试用例的命名集合"""

    __tablename__ = "datasets"

    # 主键：UUID字符串，应用层生成
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 数据集名称，不可为空，唯一
    name = Column(String(255), nullable=False, unique=True)

    # 可选的详细描述
    description = Column(Text, nullable=True)

    # JSON数组，存储TestCase对象列表
    cases = Column(JSON, nullable=False)

    # 创建时间，自动填充
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    @property
    def case_count(self) -> int:
        """返回数据集中的测试用例数量"""
        return len(self.cases) if self.cases else 0

    def __repr__(self):
        return f"<Dataset(id={self.id}, name={self.name}, cases={self.case_count})>"
