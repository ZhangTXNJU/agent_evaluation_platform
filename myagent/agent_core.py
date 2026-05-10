from __future__ import annotations

import json
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import httpx

from config import Settings
from memory import LongTermMemory, ShortTermMemory
from tools import get_all_tools


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_json_loads(content: str) -> dict[str, Any]:
    content = content.strip()
    if content.startswith("```"):
        lines = content.splitlines()
        if len(lines) >= 3:
            content = "\n".join(lines[1:-1]).strip()
    try:
        return _deep_clean(json.loads(content))
    except json.JSONDecodeError:
        start = content.find("{")
        end = content.rfind("}")
        if start != -1 and end != -1 and end > start:
            return _deep_clean(json.loads(content[start : end + 1]))
        raise


def _clean_surrogates(s: str) -> str:
    return s.encode("utf-8", errors="replace").decode("utf-8")


def _deep_clean(obj: Any) -> Any:
    """递归清理 JSON 结构中所有字符串的非法代理字符"""
    if isinstance(obj, str):
        return _clean_surrogates(obj)
    if isinstance(obj, dict):
        return {k: _deep_clean(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deep_clean(item) for item in obj]
    return obj


def _extract_model_content(completion: Any) -> str:
    # 兼容不同 SDK / 网关返回格式：
    # 1) 标准对象：completion.choices[0].message.content
    # 2) 字典：{"choices":[{"message":{"content":"..."}}]}
    # 3) 字符串：直接返回（有些兼容层会直接给 content）
    result = ""
    if isinstance(completion, str):
        result = completion

    elif isinstance(completion, dict):
        choices = completion.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            content = message.get("content", "")
            if isinstance(content, str):
                result = content
            elif isinstance(content, list):
                texts = [
                    str(item.get("text", ""))
                    for item in content
                    if isinstance(item, dict) and item.get("type") == "text"
                ]
                result = "".join(texts)

    else:
        choices = getattr(completion, "choices", None)
        if choices:
            first = choices[0]
            message = getattr(first, "message", None)
            content = getattr(message, "content", "")
            if isinstance(content, str):
                result = content
            elif isinstance(content, list):
                texts = []
                for item in content:
                    text = getattr(item, "text", None)
                    if text:
                        texts.append(str(text))
                result = "".join(texts)

    if not result:
        return "{}"
    return _clean_surrogates(result)


def _looks_like_html(text: str) -> bool:
    sample = text.lstrip().lower()
    return sample.startswith("<!doctype html") or sample.startswith("<html")


@dataclass
class AgentResult:
    session_id: str
    final_response: str
    trace: list[dict[str, Any]]
    status: str


class AutonomousTravelAgent:
    def __init__(
        self,
        settings: Settings,
        event_callback: Callable[[dict[str, Any]], None] | None = None,
    ) -> None:
        self.settings = settings
        self.tools = get_all_tools()
        self.short_memory = ShortTermMemory()
        self.long_memory = LongTermMemory(settings.long_term_memory_file)
        self.event_callback = event_callback
        self.trace: list[dict[str, Any]] = []
        self.status = "idle"
        self.last_session_id: str | None = None

    def get_status(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "last_session_id": self.last_session_id,
            "trace_events": len(self.trace),
        }

    def run(self, user_input: str) -> AgentResult:
        user_input = _clean_surrogates(user_input)
        session_id = str(uuid.uuid4())
        self.last_session_id = session_id
        self.trace = []
        self.short_memory = ShortTermMemory()
        self.status = "planning"

        long_memories = self.long_memory.search(user_input, top_k=5)
        
        self._emit(session_id, "thought", {"content": f"收到目标：{user_input}"})
        if long_memories:
            self._emit(
                session_id,
                "thought",
                {"content": f"检索到 {len(long_memories)} 条相关长期记忆，纳入决策上下文。"},
            )

        # ====== Phase 1: Plan (Plan-and-Execute 框架的 Plan 阶段) ======
        self._emit(session_id, "thought", {"content": "[Plan阶段] 正在生成初始宏观计划..."})
        high_level_plan = self._generate_initial_plan(user_input, long_memories)
        self._emit(session_id, "thought", {"content": f"[Plan阶段] 初始计划已生成:\n{high_level_plan}"})
        self.short_memory.add("plan", high_level_plan)

        final_response = ""

        # ====== Phase 2: Execute (ReAct 循环阶段) ======
        for step in range(1, self.settings.max_steps + 1):
            self.status = "executing"
            steps_remaining = self.settings.max_steps - step
            convergence_hint = ""
            if steps_remaining <= 2:
                convergence_hint = (
                    f"剩余步数仅 {steps_remaining}，请优先输出阶段性收敛结果。"
                )
                self._emit(
                    session_id,
                    "thought",
                    {"content": f"[系统提醒] {convergence_hint}"},
                )
            try:
                decision = self._decide_next_action(
                    user_input=user_input,
                    step=step,
                    high_level_plan=high_level_plan,
                    long_memories=long_memories,
                    steps_remaining=steps_remaining,
                    convergence_hint=convergence_hint,
                )
            except Exception as exc:
                self.status = "finished"
                err_msg = (
                    "模型调用失败："
                    f"{exc}\n"
                    "请检查 .env 中 BASE_URL 是否是 OpenAI 兼容 API 地址（不是网页地址），"
                    "并确认 API_KEY 与 MODEL_NAME 可用。"
                )
                self._emit(session_id, "error", {"message": err_msg})
                final_response = "因模型接口配置异常，当前会话已停止。请修正 .env 后重试。"
                self._emit(
                    session_id,
                    "final",
                    {"final_response": final_response, "plan": high_level_plan},
                )
                break

            thought = str(decision.get("thought", "")).strip()
            if thought:
                self.short_memory.add("thought", thought)
                self._emit(session_id, "thought", {"content": thought})

            plan_update = str(decision.get("plan_update", "")).strip()
            if plan_update:
                high_level_plan = plan_update
                self.short_memory.add("plan", plan_update)

            action = decision.get("action")
            if not isinstance(action, dict):
                action = {}
            action_type = str(action.get("type", "reflect")).strip()

            if action_type == "tool_call":
                tool_name = str(action.get("tool_name", "")).strip()
                arguments = action.get("arguments", {}) or {}

                tool_event = {
                    "tool_name": tool_name,
                    "params": arguments,
                    "source_spec": "e:/se3/iteration2/agent工具调用需求文档.md",
                }
                self._emit(session_id, "tool_call", tool_event)
                self.short_memory.add("tool_call", json.dumps(tool_event, ensure_ascii=False))

                # 实际执行工具
                target_tool = next((t for t in self.tools if t.name == tool_name), None)
                if target_tool:
                    try:
                        tool_result = target_tool.execute(**arguments)
                        result_summary = json.dumps(tool_result, ensure_ascii=False)
                    except Exception as e:
                        result_summary = f"工具执行异常: {e}"
                else:
                    result_summary = f"未找到名为 {tool_name} 的工具"

                observation = {
                    "tool_name": tool_name,
                    "result_summary": result_summary,
                }
                self._emit(session_id, "observation", observation)
                self.short_memory.add("observation", observation["result_summary"])
                continue

            if action_type == "final_answer":
                final_response = str(action.get("final_answer", "")).strip()
                if not final_response:
                    final_response = "已完成当前轮规划。"
                self.status = "finished"
                self._emit(
                    session_id,
                    "final",
                    {
                        "final_response": final_response,
                        "plan": high_level_plan,
                    },
                )
                self.long_memory.add(
                    content=f"用户需求: {user_input}\n最终答复: {final_response}",
                    tags=["travel", "final"],
                )
                break

            if action_type == "converge":
                summary = str(action.get("summary", "")).strip()
                if not summary:
                    summary = "已进行阶段性收敛，可继续补充约束进入下一轮规划。"
                final_response = summary
                self.status = "finished"
                self._emit(
                    session_id,
                    "final",
                    {
                        "final_response": final_response,
                        "plan": high_level_plan,
                        "stage": "intermediate",
                    },
                )
                self.long_memory.add(
                    content=f"用户需求: {user_input}\n阶段性收敛: {final_response}",
                    tags=["travel", "intermediate"],
                )
                break

            self.short_memory.add("reflect", "继续下一步决策")

        if self.status != "finished":
            self.status = "finished"
            final_response = (
                "达到最大步数，已停止。你可以继续补充偏好，我会基于当前记忆继续规划。"
            )
            self._emit(
                session_id,
                "final",
                {"final_response": final_response, "plan": high_level_plan},
            )

        # ====== 运行结束后保存 trace 到 eval_records.jsonl ======
        self._save_eval_record(session_id, user_input, final_response, self.trace)

        return AgentResult(
            session_id=session_id,
            final_response=final_response,
            trace=self.trace,
            status=self.status,
        )

    def _generate_initial_plan(self, user_input: str, long_memories: list[dict[str, Any]]) -> str:
        system_prompt = (
            "你是一个旅行规划 Planner。你的任务是根据用户的需求和相关记忆，"
            "制定解决该问题的【工作步骤大纲】（即你将如何一步步完成这个规划），而不是直接生成最终的旅游行程。\n"
            "例如，你的步骤应该类似：\n"
            "1. 澄清用户的具体出行天数和预算需求\n"
            "2. 查询目标城市的必去景点和最新天气\n"
            "3. 估算交通和住宿成本\n"
            "4. 拟定每日的具体行程安排并汇总输出\n\n"
            "请以清晰的编号列表形式输出这个解决过程的计划，不需要调用工具。"
        )
        user_prompt = {
            "goal": user_input,
            "long_memories": [
                f"【历史参考信息（请注意：这仅是过去的记录，目的地和约束可能与本次完全无关）】：{mem}" 
                for mem in long_memories
            ] if long_memories else []
        }
        try:
            completion = self._request_chat_completion(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
                ],
                temperature=0.3,
            )
            content = _extract_model_content(completion)
            return content.strip() if content else "（无初始计划）"
        except Exception as e:
            return f"（生成初始计划失败: {e}）"

    def _save_eval_record(self, session_id: str, user_input: str, final_response: str, trace: list[dict[str, Any]]) -> None:
        import os
        from pathlib import Path
        record_file = Path("data/eval_records.jsonl")
        record_file.parent.mkdir(parents=True, exist_ok=True)

        record = {
            "session_id": session_id,
            "timestamp": _utc_now(),
            "user_input": user_input,
            "final_response": final_response,
            "trace": trace
        }
        # 清理代理字符防止写入崩溃
        raw = json.dumps(record, ensure_ascii=False)
        raw = _clean_surrogates(raw)
        with open(record_file, "a", encoding="utf-8") as f:
            f.write(raw + "\n")

    def _decide_next_action(
        self,
        user_input: str,
        step: int,
        high_level_plan: str,
        long_memories: list[dict[str, Any]],
        steps_remaining: int,
        convergence_hint: str,
    ) -> dict[str, Any]:
        recent_short = self.short_memory.recent(limit=8)
        tool_docs = [
            {"name": t.name, "description": t.description, "parameters": t.parameters}
            for t in self.tools
        ]

        system_prompt = (
            "你是一个自治旅行规划 Agent，不是固定 workflow。\n"
            "你必须每一轮自主选择下一步行动：反思、调用工具、或输出最终答案。\n"
            "你有短期记忆（recent_short）和长期记忆（long_memories），请在决策中利用它们。\n"
            "【注意】：high_level_plan 是你解决问题的工作步骤计划。你可以通过输出 plan_update 字段来更新这个计划的状态（例如：给已完成的步骤打上[已完成]标签，或者追加新的工作步骤）。\n"
            "当信息暂不完整但已可交付阶段结果时，请使用 converge 动作主动收敛。\n"
            "当剩余步数很少时，优先收敛而不是继续发散探索。\n"
            "请仅输出 JSON，不要 markdown，不要多余文字。"
        )
        user_prompt = {
            "step": step,
            "steps_remaining": steps_remaining,
            "convergence_hint": convergence_hint,
            "goal": user_input,
            "high_level_plan": high_level_plan,
            "recent_short": recent_short,
            "long_memories": [
                f"【历史参考信息（请注意：这仅是过去的记录，目的地和约束可能与本次完全无关）】：{mem}" 
                for mem in long_memories
            ] if long_memories else [],
            "available_tools": tool_docs,
            "output_schema": {
                "thought": "string",
                "plan_update": "string",
                "action": {
                    "type": "tool_call | final_answer | converge | reflect",
                    "tool_name": "string, when type=tool_call",
                    "arguments": "object, when type=tool_call",
                    "final_answer": "string, when type=final_answer",
                    "summary": "string, when type=converge",
                },
            },
        }

        completion = self._request_chat_completion(
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
            ],
            temperature=0.2,
        )

        content = _extract_model_content(completion) or "{}"
        if _looks_like_html(content):
            preview = content[:120].replace("\n", " ")
            raise ValueError(
                "收到 HTML 页面而非模型 JSON 响应。"
                f"响应片段: {preview}"
            )
        try:
            return _safe_json_loads(content)
        except json.JSONDecodeError:
            # 兜底策略：保守地进入反思，避免中断会话。
            return {
                "thought": f"模型输出不是合法 JSON，原始输出: {content[:200]}",
                "plan_update": high_level_plan,
                "action": {"type": "reflect"},
            }

    def _emit(self, session_id: str, event_type: str, data: dict[str, Any]) -> None:
        event = {
            "timestamp": _utc_now(),
            "event_type": event_type,
            "session_id": session_id,
            "data": data,
        }
        self.trace.append(event)
        if self.event_callback:
            self.event_callback(event)

    def _request_chat_completion(
        self,
        messages: list[dict[str, str]],
        temperature: float,
    ) -> dict[str, Any]:
        url = self.settings.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.model_name,
            "messages": messages,
            "temperature": temperature,
        }

        with httpx.Client(timeout=60.0) as client:
            response = client.post(url, headers=headers, json=payload)

        if response.status_code >= 400:
            preview = response.text[:300].replace("\n", " ")
            raise ValueError(
                f"HTTP {response.status_code} 调用失败，响应片段: {preview}"
            )

        content_type = (response.headers.get("content-type") or "").lower()
        if "json" not in content_type:
            preview = response.text[:300].replace("\n", " ")
            raise ValueError(
                "模型接口返回非 JSON 响应。"
                f"content-type={content_type}, 响应片段: {preview}"
            )

        try:
            data = _deep_clean(response.json())
        except json.JSONDecodeError as exc:
            preview = response.text[:300].replace("\n", " ")
            raise ValueError(f"JSON 解析失败: {preview}") from exc

        if not isinstance(data, dict):
            raise ValueError(f"模型接口返回结构异常: {type(data)}")
        return data
