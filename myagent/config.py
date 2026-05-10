from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv


@dataclass
class Settings:
    base_url: str
    api_key: str
    model_name: str
    max_steps: int
    long_term_memory_file: Path


def _load_from_call_doc() -> dict[str, str]:
    candidates = [
        Path("./调用文档.txt"),
        Path("../调用文档.txt"),
    ]
    parsed: dict[str, str] = {}
    for path in candidates:
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        for line in text.splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            key = key.strip().lower()
            value = value.strip()
            if key in {"base_url", "api_key", "model"} and value:
                parsed[key] = value
        if parsed:
            return parsed
    return parsed


def load_settings() -> Settings:
    load_dotenv()
    doc_cfg = _load_from_call_doc()

    base_url = doc_cfg.get("base_url", "") or os.getenv("BASE_URL", "").strip()
    api_key = doc_cfg.get("api_key", "") or os.getenv("API_KEY", "").strip()
    model_name = (
        doc_cfg.get("model", "")
        or os.getenv("MODEL_NAME", "").strip()
        or os.getenv("MODEL", "").strip()
    )
    max_steps = int(os.getenv("MAX_STEPS", "12"))
    long_term_memory_file = Path(
        os.getenv("LONG_TERM_MEMORY_FILE", "./data/long_term_memory.jsonl").strip()
    )

    if not base_url:
        raise ValueError("缺少 BASE_URL，请在 .env 中配置。")
    if not api_key:
        raise ValueError("缺少 API_KEY，请在 .env 中配置。")
    if not model_name:
        raise ValueError("缺少 MODEL_NAME，请在 .env 中配置。")

    long_term_memory_file.parent.mkdir(parents=True, exist_ok=True)

    return Settings(
        base_url=base_url,
        api_key=api_key,
        model_name=model_name,
        max_steps=max_steps,
        long_term_memory_file=long_term_memory_file,
    )
