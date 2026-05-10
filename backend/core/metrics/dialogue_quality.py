"""
对话质量评估指标 (dialogue_quality)
使用LLM-as-Judge对完整的多轮对话进行质量评估。

评估维度:
- 目标达成度 (goal_achievement): Agent是否满足了用户的核心需求
- 回复相关性 (response_relevance): 每轮回复是否紧扣用户问题
- 信息充分性 (information_sufficiency): 提供的信息是否足够详细
- 用户体验 (user_experience): 对话流畅性、态度、交互自然度
"""

import os
import json
import logging
from typing import Any, Dict, List
from core.metrics.base import BaseMetric
from core.metric_factory import MetricRegistry

logger = logging.getLogger(__name__)

JUDGE_PROMPT = """你是一个对话质量评估专家。请对以下用户与AI Agent之间的对话进行评分。

## 用户场景
{scenario}

## 完整对话记录
{transcript}

## 评分标准(每项0-100分)

1. **目标达成度** (goal_achievement): 用户的核心目标是否被满足?Agent是否真正解决了用户的问题?
2. **回复相关性** (response_relevance): Agent的回复是否始终紧扣用户的问题?有无答非所问?
3. **信息充分性** (information_sufficiency): Agent提供的信息是否具体、准确、充分?
4. **用户体验** (user_experience): 对话是否流畅自然?Agent的态度和交互方式是否令人满意?

请以JSON格式返回评分结果:
{{"goal_achievement": 85, "response_relevance": 90, "information_sufficiency": 80, "user_experience": 88, "comment": "总体评价..."}}

只返回JSON,不要包含其他文字。"""


@MetricRegistry.register("dialogue_quality")
class DialogueQualityMetric(BaseMetric):
    """对话质量——使用LLM评估多轮对话的整体质量"""

    description = "使用LLM评估多轮对话的目标达成度、回复相关性、信息充分性和用户体验"

    def __init__(self):
        super().__init__()
        self.api_key = os.getenv("LLM_JUDGE_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        self.api_base = os.getenv("LLM_JUDGE_API_BASE", os.getenv("OPENAI_API_BASE", "https://api.openai.com/v1"))
        self.model = os.getenv("LLM_JUDGE_MODEL", "deepseek-chat")

    def compute(self, case_result: Dict[str, Any]) -> Dict[str, Any]:
        case_meta = case_result.get("case_meta", {})
        agent_output = case_result.get("agent_output", {}) or {}
        agent_trace = case_result.get("agent_trace", []) or []

        # 获取对话转录本
        transcript_text = self._build_transcript(case_meta, agent_output, agent_trace)
        if not transcript_text:
            return {
                "score": 0.0,
                "details": {
                    "goal_achievement": 0, "response_relevance": 0,
                    "information_sufficiency": 0, "user_experience": 0,
                    "comment": "对话转录本为空,无法评分",
                },
            }

        scenario = case_meta.get("scenario", {})
        scenario_text = self._format_scenario(scenario)

        try:
            scores = self._call_llm(scenario_text, transcript_text)
        except Exception as e:
            return {
                "score": 0.5,
                "details": {
                    "goal_achievement": 50, "response_relevance": 50,
                    "information_sufficiency": 50, "user_experience": 50,
                    "comment": f"LLM评分不可用({str(e)[:100]}),返回默认分",
                },
            }

        raw_score = (
            scores.get("goal_achievement", 50)
            + scores.get("response_relevance", 50)
            + scores.get("information_sufficiency", 50)
            + scores.get("user_experience", 50)
        ) / 4
        score = raw_score / 100.0

        return {
            "score": self.validate_score(score),
            "details": {
                "goal_achievement": scores.get("goal_achievement", 0),
                "response_relevance": scores.get("response_relevance", 0),
                "information_sufficiency": scores.get("information_sufficiency", 0),
                "user_experience": scores.get("user_experience", 0),
                "comment": scores.get("comment", ""),
            },
        }

    def _build_transcript(
        self,
        case_meta: dict,
        agent_output: dict,
        agent_trace: list,
    ) -> str:
        """从多种数据源构建对话转录本"""
        # 优先从 agent_output.transcript 获取
        transcript = agent_output.get("transcript") or case_meta.get("transcript")
        if transcript and isinstance(transcript, list):
            lines = []
            for turn in transcript:
                role = turn.get("role", "unknown")
                content = turn.get("content", "")
                lines.append(f"[{role}]: {content}")
            return "\n\n".join(lines)

        # 回退: 从 agent_trace 构建
        if agent_trace:
            lines = []
            for event in agent_trace:
                role = event.get("event_type", "unknown")
                data = event.get("data", {})
                if isinstance(data, dict):
                    content = data.get("content") or data.get("text") or str(data)
                else:
                    content = str(data)
                lines.append(f"[{role}]: {content}")
            return "\n\n".join(lines)

        # 最后回退: 检查 agent_output 中的 conversation 字段
        conv = agent_output.get("conversation")
        if conv and isinstance(conv, list):
            return json.dumps(conv, ensure_ascii=False, indent=2)

        return ""

    def _format_scenario(self, scenario: dict) -> str:
        if not scenario:
            return "无场景信息"
        parts = []
        for key in ("goal", "persona", "context", "success_criteria"):
            val = scenario.get(key)
            if val:
                parts.append(f"- {key}: {val}")
        return "\n".join(parts) if parts else str(scenario)

    def _call_llm(self, scenario_text: str, transcript_text: str) -> Dict[str, Any]:
        if not self.api_key:
            raise RuntimeError("未配置LLM API Key")

        try:
            from openai import OpenAI
        except ImportError:
            raise RuntimeError("openai库未安装,请执行 pip install openai")

        import httpx
        client = OpenAI(
            api_key=self.api_key,
            base_url=self.api_base,
            timeout=httpx.Timeout(60.0, connect=10.0),
        )
        prompt = JUDGE_PROMPT.format(scenario=scenario_text, transcript=transcript_text)

        kwargs = dict(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.1,
            max_tokens=1024,
        )
        # response_format 仅限 OpenAI 官方支持
        if "openai.com" in self.api_base:
            kwargs["response_format"] = {"type": "json_object"}

        logger.debug("dialogue_quality LLM调用: model=%s, prompt_len=%d", self.model, len(prompt))
        response = client.chat.completions.create(**kwargs)

        content = response.choices[0].message.content
        logger.debug("dialogue_quality LLM返回: %s", (content or "")[:300])
        if content:
            content = content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                if lines[-1].strip() == "```":
                    lines = lines[1:-1]
                else:
                    lines = lines[1:]
                content = "\n".join(lines).strip()
            return json.loads(content)

        raise RuntimeError("LLM返回了空响应")
