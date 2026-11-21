"""Append-only JSONL trace: one event per line, flushed immediately."""
from __future__ import annotations

import json
import time
from pathlib import Path


class Trace:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._fh = self.path.open("a", encoding="utf-8")

    def log(self, type: str, **fields) -> None:
        event = {"ts": round(time.time(), 3), "type": type, **fields}
        self._fh.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


def read_trace(path: str | Path) -> list[dict]:
    with Path(path).open(encoding="utf-8") as fh:
        return [json.loads(line) for line in fh if line.strip()]
