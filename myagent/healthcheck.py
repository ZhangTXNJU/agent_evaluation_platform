from __future__ import annotations

import httpx

from config import load_settings


def main() -> None:
    settings = load_settings()
    url = settings.base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": settings.model_name,
        "messages": [
            {"role": "system", "content": "You are a connectivity checker."},
            {"role": "user", "content": "reply with exactly: ok"},
        ],
        "temperature": 0,
    }
    headers = {
        "Authorization": f"Bearer {settings.api_key}",
        "Content-Type": "application/json",
    }
    response = httpx.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()
    try:
        data = response.json()
    except ValueError as exc:
        preview = response.text[:300].replace("\n", " ")
        raise RuntimeError(f"非 JSON 响应: {preview}") from exc
    content = data["choices"][0]["message"]["content"]
    print("healthcheck: success")
    print(f"model={settings.model_name}")
    print(f"response={content}")


if __name__ == "__main__":
    main()
