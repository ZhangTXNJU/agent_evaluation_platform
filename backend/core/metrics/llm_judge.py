"""
LLM-as-a-Judge推理质量指标 (T029)
使用外部LLM对Agent的思考链（thought链）进行评分。

评估维度：
- 计划合理性 (plan_reasonableness)：规划步骤是否逻辑清晰
- 工具选择恰当性 (tool_appropriateness)：选用的工具是否适合任务
- 自我修正有效性 (self_correction)：是否能在发现问题后调整策略

需要使用OpenAI兼容API进行评分。
"""

import os
import json
from typing import Any, Dict, List
from core.metrics.base import BaseMetric
from core.metric_factory import MetricRegistry


# LLM Judge的评分提示模板（中文）
JUDGE_PROMPT = """你是一个Agent评估专家。请对以下旅行规划Agent的思考链进行评分。

## 用户需求
{input}

## Agent的思考链
{thoughts}

## 评分标准（每项0-100分）

1. **计划合理性** (plan_reasonableness)：规划步骤是否逻辑清晰、考虑全面？是否合理分解了用户需求？
2. **工具选择恰当性** (tool_appropriateness)：选择的工具是否适合当前步骤？是否存在更好的工具选择？
3. **自我修正有效性** (self_correction)：发现错误或信息不足时，是否能有效调整策略？

请以JSON格式返回评分结果，格式如下：
{{"plan_reasonableness": 85, "tool_appropriateness": 90, "self_correction": 80, "comment": "总体评价..."}}

只返回JSON，不要包含其他文字。"""


@MetricRegistry.register("llm_judge")
class LLMJudgeMetric(BaseMetric):
    """LLM-as-a-Judge——使用LLM评估Agent推理质量"""

    description = "使用LLM评估Agent思考链的计划合理性、工具选择恰当性和自我修正能力"

    def __init__(self):
        super().__init__()
        # LLM配置：从环境变量读取，默认使用OpenAI兼容API
        self.api_key = os.getenv("LLM_JUDGE_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.api_base = os.getenv("LLM_JUDGE_API_BASE", os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"))
        self.model = os.getenv("LLM_JUDGE_MODEL", "gpt-3.5-turbo")

    def compute(self, case_result: Dict[str, Any]) -> Dict[str, Any]:
        """
        调用LLM对Agent思考链评分。

        case_result包含:
            - case_meta.input: 原始用户需求
            - agent_trace: Agent执行追踪（提取thought事件）
        """
        case_meta = case_result.get("case_meta", {})
        agent_trace = case_result.get("agent_trace", [])

        user_input = case_meta.get("input", "")

        # 提取所有thought事件
        thoughts = self._extract_thoughts(agent_trace)

        if not thoughts:
            return {
                "score": 0.0,
                "details": {
                    "plan_reasonableness": 0,
                    "tool_appropriateness": 0,
                    "self_correction": 0,
                    "comment": "Agent思考链为空，无法评分",
                },
            }

        # 格式化思考链文本
        thoughts_text = self._format_thoughts(thoughts)

        # 尝试调用LLM评分
        try:
            scores = self._call_llm(user_input, thoughts_text)
        except Exception as e:
            # LLM不可用时返回默认分数
            return {
                "score": 0.5,
                "details": {
                    "plan_reasonableness": 50,
                    "tool_appropriateness": 50,
                    "self_correction": 50,
                    "comment": f"LLM评分不可用({str(e)[:100]})，返回默认分",
                },
            }

        # 综合得分 = 三维度的平均（归一化到0-1）
        raw_score = (
            scores.get("plan_reasonableness", 50)
            + scores.get("tool_appropriateness", 50)
            + scores.get("self_correction", 50)
        ) / 3
        score = raw_score / 100.0

        return {
            "score": self.validate_score(score),
            "details": {
                "plan_reasonableness": scores.get("plan_reasonableness", 0),
                "tool_appropriateness": scores.get("tool_appropriateness", 0),
                "self_correction": scores.get("self_correction", 0),
                "comment": scores.get("comment", ""),
            },
        }

    def _extract_thoughts(self, trace: List[Dict]) -> List[Dict]:
        """从trace中提取所有thought事件"""
        thoughts = []
        for event in trace:
            if event.get("event_type") == "thought":
                thoughts.append(event)
        return thoughts

    def _format_thoughts(self, thoughts: List[Dict]) -> str:
        """将思考链事件格式化为文本"""
        lines = []
        for i, t in enumerate(thoughts):
            step = i + 1
            data = t.get("data", {})
            if isinstance(data, dict):
                content = data.get("content") or data.get("text") or str(data)
            else:
                content = str(data)
            lines.append(f"步骤{step}: {content}")
        return "\n".join(lines)

    def _call_llm(self, user_input: str, thoughts_text: str) -> Dict[str, Any]:
        """调用LLM API进行评分"""
        if not self.api_key:
            raise RuntimeError("未配置LLM API Key（设置环境变量LLM_JUDGE_API_KEY或OPENAI_API_KEY）")

        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai库未安装，请执行 pip install openai")

        client = OpenAI(api_key=self.api_key, base_url=self.api_base)
        prompt = JUDGE_PROMPT.format(input=user_input, thoughts=thoughts_text)

        response = client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,  # 低温度以获得稳定评分
            max_tokens=500,
        )

        content = response.choices[0].message.content
        if content:
            # 提取JSON（有些模型可能包裹在markdown代码块中）
            content = content.strip()
            if content.startswith("```"):
                content = content.split("\n", 1)[1]
                if content.endswith("```"):
                    content = content[:-3]
            return json.loads(content)

        raise RuntimeError("LLM返回了空响应")
