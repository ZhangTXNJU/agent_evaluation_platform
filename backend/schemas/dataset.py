"""
Dataset Pydantic Schemas (T011)
定义数据集相关的请求/响应数据结构，与OpenAPI合约保持一致。
"""

from datetime import datetime
from typing import Optional, Dict, List
from pydantic import BaseModel, Field, model_validator


# ── 内嵌Schema：测试用例 ──
class TestCaseSchema(BaseModel):
    """单个测试用例的结构定义"""

    id: str = Field(..., description="用例唯一标识，如 case_01")
    input: Optional[str] = Field(None, description="自然语言描述的用户旅行需求（单轮模式）")
    scenario: Optional[Dict] = Field(
        None,
        description="多轮对话场景：goal, persona, context, success_criteria（多轮模式）",
    )
    max_turns: Optional[int] = Field(None, description="最大对话轮次（多轮模式）")
    expected_turns: Optional[int] = Field(None, description="预期对话轮次（多轮模式）")
    expected_constraints: Optional[Dict] = Field(
        None,
        description="预期约束：destination, days, budget_limit, must_include_keywords",
    )
    expected_tool_sequence: Optional[List[str]] = Field(
        None,
        description="预期的工具调用顺序列表",
    )
    expected_tools: Optional[List[str]] = Field(
        None,
        description="预期使用的工具列表（多轮模式）",
    )
    difficulty: Optional[str] = Field(
        "medium",
        description="难度级别：easy / medium / hard",
    )

    @model_validator(mode="after")
    def check_id_not_empty(self):
        """校验用例ID不能为空"""
        if not self.id or not self.id.strip():
            raise ValueError("测试用例ID不能为空")
        return self


# ── 请求Schema ──
class DatasetCreate(BaseModel):
    """创建数据集的请求体"""

    name: str = Field(..., min_length=1, max_length=255, description="数据集名称")
    description: Optional[str] = Field(None, description="数据集描述")
    cases: List[TestCaseSchema] = Field(
        ..., min_length=1, description="测试用例列表，至少1个"
    )

    @model_validator(mode="after")
    def check_unique_case_ids(self):
        """校验测试用例ID在数据集中唯一"""
        ids = [case.id for case in self.cases]
        if len(ids) != len(set(ids)):
            raise ValueError("数据集中存在重复的测试用例ID")
        return self


# ── 响应Schema ──
class DatasetSummary(BaseModel):
    """数据集列表项的摘要信息"""

    id: str
    name: str
    description: Optional[str] = None
    case_count: int
    created_at: datetime


class DatasetDetail(DatasetSummary):
    """数据集详情，包含全部测试用例"""

    cases: List[TestCaseSchema]


class SuccessResponse(BaseModel):
    """通用成功响应"""

    success: bool = True
