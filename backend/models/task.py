"""
Task ORM模型 (T010)
对应数据模型中的Task实体，存储评估任务的配置和执行结果。
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Text, DateTime, Integer, JSON, ForeignKey
from db import Base


class Task(Base):
    """评估任务——一次完整的Agent评估运行"""

    __tablename__ = "tasks"

    # 主键：UUID字符串，应用层生成
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 任务名称
    name = Column(String(255), nullable=False)

    # Agent版本标识（如 "v1.0.0"）
    agent_version = Column(String(100), nullable=False)

    # 关联的数据集ID（外键引用datasets表）
    dataset_id = Column(String(36), ForeignKey("datasets.id"), nullable=False)

    # 选用的指标名称列表（如 ["success_rate", "tool_accuracy"]）
    metrics = Column(JSON, nullable=False)

    # Agent Platform的API端点URL
    agent_endpoint = Column(
        String(500), nullable=False, default="http://localhost:8000/api/eval/run"
    )

    # 适配器类型(决定如何与目标 Agent 通信),默认 "native" 向后兼容
    adapter_type = Column(String(50), nullable=False, default="native")

    # 适配器额外配置(model、api_key、temperature 等);随适配器类型不同而不同
    adapter_config = Column(JSON, nullable=True)

    # 评估模式: "single_turn"(默认,向后兼容) / "multi_turn"(多轮对话评估)
    eval_mode = Column(String(20), nullable=False, default="single_turn")

    # User Simulator配置(多轮模式专用): {api_base, api_key, model, temperature}
    simulator_config = Column(JSON, nullable=True)

    # 可选的自定义权重配置，不设置则等权重
    weight_config = Column(JSON, nullable=True)

    # 任务状态：pending / running / done / failed
    status = Column(String(20), nullable=False, default="pending")

    # 已完成测试用例数
    progress_current = Column(Integer, nullable=False, default=0)

    # 测试用例总数
    progress_total = Column(Integer, nullable=False, default=0)

    # 评估结果（JSON），任务完成后填充
    result = Column(JSON, nullable=True)

    # 任务级别错误信息
    error_message = Column(Text, nullable=True)

    # 创建时间
    created_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # 最后更新时间
    updated_at = Column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    @property
    def progress_display(self) -> str:
        """返回进度显示字符串，如 '3/10'"""
        return f"{self.progress_current}/{self.progress_total}"

    @property
    def is_running(self) -> bool:
        """判断任务是否正在运行"""
        return self.status == "running"

    def can_delete(self) -> bool:
        """只有非运行状态的任务才能删除"""
        return self.status != "running"

    def __repr__(self):
        return (
            f"<Task(id={self.id}, name={self.name}, "
            f"status={self.status}, progress={self.progress_display})>"
        )
