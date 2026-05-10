from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path


def _tokenize(text: str) -> set[str]:
    clean = "".join(ch.lower() if ch.isalnum() else " " for ch in text)
    return {tok for tok in clean.split() if len(tok) > 1}


def _similarity(a: str, b: str) -> float:
    ta = _tokenize(a)
    tb = _tokenize(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    union = len(ta | tb)
    return inter / union if union else 0.0


@dataclass
class ShortTermMemory:
    events: list[dict] = field(default_factory=list)

    def add(self, event_type: str, content: str) -> None:
        self.events.append({"type": event_type, "content": content, "ts": int(time.time())})

    def recent(self, limit: int = 8) -> list[dict]:
        return self.events[-limit:]


@dataclass
class LongTermMemory:
    file_path: Path

    def add(self, content: str, tags: list[str] | None = None) -> None:
        item = {
            "content": content,
            "tags": tags or [],
            "ts": int(time.time()),
        }
        with self.file_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    def _load_all(self) -> list[dict]:
        if not self.file_path.exists():
            return []
        lines = self.file_path.read_text(encoding="utf-8").splitlines()
        items: list[dict] = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                items.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return items

    def search(self, query: str, top_k: int = 5) -> list[dict]:
        items = self._load_all()
        scored = []
        for item in items:
            content = str(item.get("content", ""))
            score = _similarity(query, content)
            if score > 0:
                scored.append((score, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        return [item for _, item in scored[:top_k]]
