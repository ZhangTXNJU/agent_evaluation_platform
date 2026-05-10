"""
Task Pydantic Schemas (T012)
定义评估任务相关的请求/响应数据结构，与OpenAPI合约保持一致。
"""

from datetime import datetime
from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, model_validator


# ── 请求Schema ──
class TaskCreate(BaseModel):
    """创建评估任务的请求体"""

    name: str = Field(..., min_length=1, max_length=255, description="任务名称")
    agent_version: str = Field(..., max_length=100, description="Agent版本标识")
    dataset_id: str = Field(..., description="关联的数据集ID")
    metrics: List[str] = Field(
        ..., min_length=1, description="选用的指标名称列表，至少1个"
    )
    agent_endpoint: str = Field(
        "http://localhost:8000/api/eval/run",
        description="Agent Platform的评估端点URL",
    )
    adapter_type: str = Field(
        "native",
        description="Agent 协议适配器类型,如 'native' 或 'openai_chat'",
    )
    adapter_config: Optional[Dict[str, Any]] = Field(
        None,
        description="适配器配置(model、api_key、temperature 等),随适配器类型不同而不同",
    )
    eval_mode: str = Field(
        "single_turn",
        description="评估模式: 'single_turn'(单轮,默认) 或 'multi_turn'(多轮对话)",
    )
    simulator_config: Optional[Dict[str, Any]] = Field(
        None,
        description="User Simulator配置(多轮模式专用): api_base, api_key, model, temperature",
    )
    weight_config: Optional[Dict[str, float]] = Field(
        None, description="自定义指标权重，不设置则等权重"
    )

    @model_validator(mode="after")
    def check_valid_metrics(self):
        """校验指标名称是否合法"""
        valid_metrics = {
            "success_rate", "tool_accuracy", "llm_judge", "response_time",
            "dialogue_quality", "task_completion", "conversation_efficiency",
        }
        for m in self.metrics:
            if m not in valid_metrics:
                raise ValueError(f"无效的指标名称: '{m}'，可选值: {valid_metrics}")
        return self


# ── 响应Schema ──
class TaskSummary(BaseModel):
    """任务列表项的摘要信息"""

    id: str
    name: str
    agent_version: str
    dataset_name: str = ""
    dataset_id: str = ""
    metrics: List[str] = []
    agent_endpoint: str = ""
    adapter_type: str = "native"
    status: str  # pending / running / done / failed
    progress_current: int = 0
    progress_total: int = 0
    created_at: datetime
    updated_at: Optional[datetime] = None


class TaskListResponse(BaseModel):
    """分页任务列表响应"""

    items: List[TaskSummary]
    total: int
    page: int
    size: int


# ── 结果相关Schema ──
class TraceEvent(BaseModel):
    """Agent执行追踪中的单个事件"""

    timestamp: Optional[str] = None
    event_type: str  # thought / tool_call / observation
    data: Optional[Dict[str, Any]] = None


class CaseResult(BaseModel):
    """单个测试用例的评估结果"""

    case_id: str
    status: str  # passed / failed / error
    metric_scores: Dict[str, float] = {}
    metric_details: Dict[str, Any] = {}
    agent_output: Optional[Dict[str, Any]] = None
    agent_trace: List[TraceEvent] = []
    error_message: Optional[str] = None


class EvaluationResult(BaseModel):
    """完整的评估结果"""

    overall_score: float = 0.0
    metric_scores: Dict[str, float] = {}
    case_results: List[CaseResult] = []
    execution_time_seconds: float = 0.0
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class ResultSummary(BaseModel):
    """评估结果摘要（仅总分和各指标均分）"""

    overall_score: float
    metric_scores: Dict[str, float]


class TaskDetail(TaskSummary):
    """任务详情，包含完整配置和结果"""

    eval_mode: str = "single_turn"
    simulator_config: Optional[Dict[str, Any]] = None
    weight_config: Optional[Dict[str, float]] = None
    adapter_config: Optional[Dict[str, Any]] = None
    result: Optional[EvaluationResult] = None
    error_message: Optional[str] = None


# ── 对比相关Schema ──
class CompareRequest(BaseModel):
    """多任务对比请求"""

    task_ids: List[str] = Field(
        ..., min_length=2, description="要对比的任务ID列表，至少2个"
    )


class TaskCompareItem(BaseModel):
    """对比中的单个任务数据"""

    task_id: str
    task_name: str
    metric_scores: Dict[str, float]
    overall_score: float


class CompareResponse(BaseModel):
    """多任务对比响应"""

    tasks: List[TaskSummary] = []
    metrics_comparison: Dict[str, Any] = {}
