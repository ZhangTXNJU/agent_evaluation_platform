from __future__ import annotations

import json

from agent_core import AutonomousTravelAgent, _clean_surrogates
from config import load_settings


def _print_event(event: dict) -> None:
    et = event.get("event_type")
    data = event.get("data", {})
    if et == "thought":
        print(f"[思考] {data.get('content', '')}")
    elif et == "tool_call":
        tool_name = data.get("tool_name", "")
        params = json.dumps(data.get("params", {}), ensure_ascii=False)
        print(f"[工具调用] {tool_name} {params}")
    elif et == "observation":
        print(f"[观察] {data.get('result_summary', '')}")
    elif et == "correction":
        print(f"[修正] {json.dumps(data, ensure_ascii=False)}")
    elif et == "final":
        print(f"[最终输出] {data.get('final_response', '')}")
    elif et == "error":
        print(f"[错误] {json.dumps(data, ensure_ascii=False)}")


def main() -> None:
    settings = load_settings()
    agent = AutonomousTravelAgent(settings=settings, event_callback=_print_event)

    print("欢迎使用旅行规划自治Agent（主干版）")
    print("输入旅行需求开始规划；输入 /status 查看状态；输入 /quit 退出。")

    while True:
        user_text = _clean_surrogates(input("\n你> ").strip())
        if not user_text:
            continue
        if user_text == "/quit":
            print("已退出。")
            break
        if user_text == "/status":
            print(json.dumps(agent.get_status(), ensure_ascii=False, indent=2))
            continue

        result = agent.run(user_text)
        print(f"\n会话完成：session_id={result.session_id}, trace_events={len(result.trace)}")


if __name__ == "__main__":
    main()
    