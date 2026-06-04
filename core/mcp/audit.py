"""Append-only local MCP audit helper."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


REDACT_KEYS = {"text", "content", "secret", "token", "password", "api_key", "arguments"}


def _redact(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(k): ("[redacted]" if str(k).lower() in REDACT_KEYS else _redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [_redact(item) for item in value]
    return value


class McpAuditLog:
    def __init__(self, path: Path):
        self.path = Path(path)

    def record(self, event_type: str, payload: Any) -> None:
        if is_dataclass(payload):
            payload = asdict(payload)
        row = {
            "timestamp": datetime.now().isoformat(),
            "event_type": str(event_type),
            "payload": _redact(payload),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
