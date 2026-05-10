"""
User Simulator — LLM驱动的用户模拟器 (多轮对话评估核心组件)

在多轮对话评估模式下,UserSimulator扮演"用户"角色,与被测试的Agent进行多轮对话:
1. 根据测试场景(scenario)生成首条自然语言消息
2. 每轮收到Agent回复后,判断目标是否达成,生成下一条用户消息
3. 对话结束后返回完整判定结果

配置优先级: 任务级 simulator_config > 环境变量 > 默认值
"""

import json
import os
import logging
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)

# ── User Simulator 的 Prompt 模板 ──

SYSTEM_PROMPT = """你是一个用户模拟器(User Simulator),负责在Agent评估平台中模拟真实用户行为。

## 你的任务
根据给定的"对话场景",扮演一个真实用户,与被测试的AI Agent进行多轮对话。

## 场景信息包含
- **goal**(用户目标): 用户最终想达成的目标
- **persona**(用户人设): 用户的身份、知识背景、偏好
- **context**(上下文): 额外的场景约束
- **success_criteria**(成功标准): 判断Agent是否完成任务的明确标准

## 行为规则
1. 模仿真实用户的说话风格——自然、随意、可以带口语
2. **首条消息必须直接、明确地表达用户目标(goal)**。例如目标是"规划3天北京游"，首条消息必须说"我想去北京玩3天，帮我规划"之类的，不能说"推荐好玩的地方"这种模糊的话
3. 逐步提供细节: 首条说出核心目标后，在后续对话中逐步补充偏好、预算、限制条件等
4. 如果Agent的回复不够好,可以追问、质疑或要求改进
5. 当Agent的回复满足了 success_criteria 时,设置 is_done=true 并表示满意
6. 如果Agent明显偏离主题或无法完成任务,也设置 is_done=true 但标记为失败
7. 你应该先思考判断再给出消息,不要让对话无限循环

## 输出格式
你必须只返回一个JSON对象(不要包含markdown代码块标记):
{"is_done": false, "reason": "用户还想...", "message": "那你能帮我..."}
或
{"is_done": true, "reason": "目标已达成,Agent提供了...", "message": "太好了,谢谢你的帮助!"}

注意: message 必须始终是自然的用户消息,不要在其中包含分析或判断。"""


class UserSimulator:
    """LLM驱动的用户模拟器"""

    def __init__(
        self,
        api_base: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
    ):
        # 配置优先级: 参数 > 环境变量 > 默认值
        self.api_base = (
            api_base
            or os.getenv("SIMULATOR_API_BASE")
            or os.getenv("OPENAI_API_BASE")
            or "https://api.openai.com/v1"
        )
        self.api_key = (
            api_key
            or os.getenv("SIMULATOR_API_KEY")
            or os.getenv("OPENAI_API_KEY")
            or ""
        )
        self.model = (
            model
            or os.getenv("SIMULATOR_MODEL")
            or os.getenv("LLM_JUDGE_MODEL")
            or "deepseek-chat"
        )
        self.temperature = temperature
        self._client = None

    @property
    def is_configured(self) -> bool:
        """检查是否已配置API Key"""
        return bool(self.api_key)

    def _get_client(self):
        """延迟初始化OpenAI客户端"""
        if self._client is None:
            try:
                from openai import OpenAI
            except ImportError:
                raise RuntimeError(
                    "openai 库未安装,请执行: pip install openai"
                )
            import httpx
            self._client = OpenAI(
                api_key=self.api_key,
                base_url=self.api_base,
                timeout=httpx.Timeout(60.0, connect=10.0),
            )
        return self._client

    def _call_llm(
        self, messages: list, temperature: Optional[float] = None
    ) -> str:
        """调用LLM并返回文本内容"""
        client = self._get_client()
        kwargs = dict(
            model=self.model,
            messages=messages,
            temperature=temperature if temperature is not None else self.temperature,
            max_tokens=1024,
        )
        # response_format 仅限 OpenAI 官方支持, DeepSeek 等兼容接口可能报错
        if "openai.com" in self.api_base:
            kwargs["response_format"] = {"type": "json_object"}
        logger.debug("UserSimulator LLM调用: model=%s, msg_count=%d", self.model, len(messages))
        response = client.chat.completions.create(**kwargs)
        content = response.choices[0].message.content
        logger.debug("UserSimulator LLM返回: %s", (content or "")[:200])
        return content.strip() if content else ""

    def _parse_json_response(self, raw: str) -> Dict[str, Any]:
        """从LLM返回中解析JSON,兼容markdown代码块包裹的情况"""
        raw = raw.strip()
        if raw.startswith("```"):
            lines = raw.split("\n")
            # 去掉首行 ```json 和末行 ```
            if lines[-1].strip() == "```":
                lines = lines[1:-1]
            else:
                lines = lines[1:]
            raw = "\n".join(lines).strip()
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("UserSimulator JSON解析失败,原始返回: %s", raw[:300])
            return {"is_done": True, "reason": "JSON解析失败", "message": raw[:200]}

    def _build_scenario_text(self, scenario: Dict[str, Any]) -> str:
        """将场景字典格式化为LLM可读文本"""
        goal = scenario.get("goal", "")
        persona = scenario.get("persona", "普通用户")
        context = scenario.get("context", "")
        success = scenario.get("success_criteria", "")

        parts = [f"用户目标: {goal}"]
        if persona:
            parts.append(f"用户人设: {persona}")
        if context:
            parts.append(f"上下文: {context}")
        if success:
            parts.append(f"成功标准: {success}")
        return "\n".join(parts)

    def _extract_scenario(self, case_meta: Dict[str, Any]) -> Dict[str, Any]:
        """
        从测试用例中提取场景信息。
        优先使用 scenario 字段, 如果不存在则将 input 字段作为 goal 使用。
        """
        scenario = case_meta.get("scenario", {})
        if scenario and scenario.get("goal"):
            return scenario
        # fallback: 用 input 作为 goal
        input_text = case_meta.get("input", "")
        if input_text:
            return {"goal": input_text}
        return scenario or {}

    def start_conversation(self, scenario: Dict[str, Any]) -> str:
        """
        根据场景生成首条用户消息。

        Args:
            scenario: 测试用例中的 scenario 字段

        Returns:
            首条用户消息文本
        """
        scenario_text = self._build_scenario_text(scenario)
        goal = scenario.get("goal", "")

        # 直接提取 goal 中的关键词，构建一个简单粗暴的首条消息模板
        # 避免 LLM 不遵守指令导致首条消息偏离目标
        prompt = f"""你正在扮演一个用户，你需要发起一段对话。

## 严格规则
你必须把"用户目标"翻译成一句自然的用户开场白，直接表达目标本身。
**禁止**说任何与目标无关的话，**禁止**用模糊的"推荐好玩的地方"之类代替目标。

## 场景
{scenario_text}

## 正确示例
- 如果目标是"规划3天北京游"，你该说 → "你好，我想去北京玩3天，能帮我规划一下行程吗？"
- 如果目标是"预订机票去三亚"，你该说 → "你好，我想订去三亚的机票"
- 如果目标是"找上海周边适合自驾的地方"，你该说 → "你好，帮我找找上海周边适合自驾游的地方"

## 错误示例（不要这样说）
- 目标"规划3天北京游"但你说"推荐周末放松的地方" → 错误！偏离目标
- 目标"预订机票"但你说"最近有什么好玩的地方" → 错误！完全偏离

请以JSON格式返回:
{{"is_done": false, "reason": "对话刚开始", "message": "你的开场白"}}"""

        raw = self._call_llm(
            [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.3,  # 降低温度, 确保首条消息遵循场景
        )
        parsed = self._parse_json_response(raw)
        message = parsed.get("message", f"你好,{goal or '我需要帮助'}")
        logger.info("UserSimulator 首条消息: %s", message[:120])
        return message

    def next_message(
        self,
        scenario: Dict[str, Any],
        history: list,
        agent_response: str,
    ) -> Tuple[bool, str, str]:
        """
        判断对话下一步: 是否结束? 下一条用户消息是什么?

        Args:
            scenario: 测试用例中的 scenario 字段
            history: 对话历史列表 [{"role": "user", "content": "..."}, ...]
            agent_response: Agent 最新一条回复文本

        Returns:
            (is_done: bool, reason: str, message: str)
        """
        scenario_text = self._build_scenario_text(scenario)

        # 格式化对话历史
        history_lines = []
        for h in history:
            role_label = "用户" if h["role"] == "user" else "Agent"
            content = h.get("content", "")
            # 截断过长的内容
            if len(content) > 800:
                content = content[:800] + "..."
            history_lines.append(f"[{role_label}]: {content}")
        # 加上Agent最新回复
        if len(agent_response) > 800:
            agent_response = agent_response[:800] + "..."
        history_lines.append(f"[Agent(最新)]: {agent_response}")
        history_text = "\n\n".join(history_lines)

        prompt = f"""请根据以下场景和对话历史,判断对话是否应该结束,并生成用户的下一步回复。

## 场景
{scenario_text}

## 对话历史
{history_text}

## 判断指南
- 如果Agent的回复**已经满足** success_criteria 中的标准 → is_done=true, 用户表示满意/结束
- 如果Agent**明显做不到**这个任务(回复完全无关/反复出错) → is_done=true, 用户表示失望/放弃
- 如果Agent**犯了严重错误**(捏造信息/逻辑矛盾) → is_done=true, 用户指出问题并结束
- 否则 → is_done=false, 用户继续推进对话(追问细节/要求改进/提出新需求)
- 如果对话已经很长(>8轮)但目标尚未达成 → 也应该考虑 is_done=true 结束

请返回JSON:
{{"is_done": true|false, "reason": "你的判断理由", "message": "用户的消息"}}"""

        raw = self._call_llm([
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ])
        parsed = self._parse_json_response(raw)
        is_done = parsed.get("is_done", True)
        reason = parsed.get("reason", "")
        message = parsed.get("message", "")

        logger.info(
            "UserSimulator 判定: is_done=%s, reason=%s, message=%s",
            is_done, reason, message[:100],
        )
        return is_done, reason, message

    def final_evaluation(
        self,
        scenario: Dict[str, Any],
        history: list,
    ) -> Dict[str, Any]:
        """
        对话结束后,对整体对话质量进行最终评估。

        Returns:
            {
                "task_completed": bool,
                "completion_reason": str,
                "user_satisfaction": float,  # 0-1
                "key_issues": list[str],
            }
        """
        scenario_text = self._build_scenario_text(scenario)

        history_lines = []
        for h in history:
            role_label = "用户" if h["role"] == "user" else "Agent"
            content = h.get("content", "")
            if len(content) > 500:
                content = content[:500] + "..."
            history_lines.append(f"[{role_label}]: {content}")
        history_text = "\n\n".join(history_lines)

        prompt = f"""请评估以下对话的整体完成情况。

## 场景
{scenario_text}

## 完整对话
{history_text}

请返回JSON:
{{
    "task_completed": true|false,
    "completion_reason": "任务完成/未完成的理由",
    "user_satisfaction": 0.0-1.0,
    "key_issues": ["问题1", "问题2"]
}}

评价标准:
- task_completed: Agent是否满足了success_criteria
- user_satisfaction: 综合考虑回复质量、效率、态度,0-1分
- key_issues: Agent在对话中暴露的主要问题(如有)"""

        try:
            raw = self._call_llm([
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ], temperature=0.3)
            parsed = self._parse_json_response(raw)
            return parsed
        except Exception as e:
            logger.warning("UserSimulator最终评估失败: %s", e)
            return {
                "task_completed": False,
                "completion_reason": f"评估失败: {str(e)[:100]}",
                "user_satisfaction": 0.5,
                "key_issues": [],
            }
