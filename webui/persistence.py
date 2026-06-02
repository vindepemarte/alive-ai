"""Durable WebUI projection helpers.

The runtime has several durable stores. This module gives the dashboard one
small journal for visible chat rows and a safe fallback into episodic memory.
"""

import json
import os
import re
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.paths import data_dir


_SAFE_ID = re.compile(r"[^A-Za-z0-9_.@-]+")


def normalize_user_id(user_id: Any) -> str:
    raw = str(user_id or "").strip()
    if not raw:
        raw = "webui"
    safe = _SAFE_ID.sub("_", raw).strip("._-")
    return safe or "webui"


def _configured_owner_id() -> str:
    owner = os.environ.get("TELEGRAM_OWNER_ID", "")
    if owner:
        return owner
    try:
        from core.settings import get as settings_get
        return str(settings_get("TELEGRAM_OWNER_ID", "") or "")
    except Exception:
        return ""


def _tracked_active_user_id() -> str:
    try:
        from core.user_tracker import get_user_tracker
        active = get_user_tracker().get_active_users(within_minutes=24 * 60)
        if active:
            active = sorted(active, key=lambda u: u.last_interaction, reverse=True)
            return active[0].user_id
    except Exception:
        pass
    return ""


def _path_activity_score(path: Path) -> Tuple[float, int]:
    latest = path.stat().st_mtime if path.exists() else 0.0
    count = 0
    for pattern in ("conversations/*.jsonl", "webui_chat.jsonl", "narrative.json",
                    "facts.json", "emotional_memories.json"):
        for item in path.glob(pattern):
            try:
                latest = max(latest, item.stat().st_mtime)
                if item.is_file():
                    count += 1
            except Exception:
                continue
    return latest, count


def _most_active_disk_user_id() -> str:
    users = data_dir() / "users"
    if not users.exists():
        return ""
    candidates = []
    for child in users.iterdir():
        if not child.is_dir() or child.name in {"default", "webui"}:
            continue
        latest, count = _path_activity_score(child)
        if count:
            candidates.append((latest, child.name))
    if not candidates:
        return ""
    return max(candidates)[1]


def resolve_active_user_id(explicit: Any = None, self_ref: Any = None,
                           dashboard_state: Optional[Dict[str, Any]] = None) -> str:
    if explicit:
        return normalize_user_id(explicit)

    dashboard_state = dashboard_state or {}
    active = dashboard_state.get("active_user")
    if active and normalize_user_id(active) not in {"default", "webui"}:
        return normalize_user_id(dashboard_state["active_user"])

    tracked = _tracked_active_user_id()
    if tracked:
        return normalize_user_id(tracked)

    owner = _configured_owner_id()
    if owner:
        return normalize_user_id(owner)

    runtime_state = getattr(self_ref, "state", None)
    runtime_user = getattr(runtime_state, "user_id", None) if runtime_state else None
    if runtime_user and normalize_user_id(runtime_user) not in {"default", "webui"}:
        return normalize_user_id(runtime_state.user_id)

    disk_user = _most_active_disk_user_id()
    if disk_user:
        return normalize_user_id(disk_user)

    if active:
        return normalize_user_id(active)

    if runtime_user:
        return normalize_user_id(runtime_user)

    return "webui"


def user_base(user_id: str) -> Path:
    path = data_dir() / "users" / normalize_user_id(user_id)
    path.mkdir(parents=True, exist_ok=True)
    return path


def chat_journal_path(user_id: str) -> Path:
    return user_base(user_id) / "webui_chat.jsonl"


def new_message_id(prefix: str = "msg") -> str:
    return f"{prefix}_{uuid.uuid4().hex[:16]}"


def _read_jsonl(path: Path) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    if not path.exists():
        return rows
    with path.open() as fh:
        for line in fh:
            try:
                row = json.loads(line)
                if isinstance(row, dict):
                    rows.append(row)
            except Exception:
                continue
    return rows


def append_chat_message(user_id: str, role: str, content: str,
                        message_id: Optional[str] = None,
                        status: str = "sent", source: str = "runtime",
                        metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    message_id = message_id or new_message_id(role)
    entry = {
        "message_id": message_id,
        "role": role,
        "content": str(content or ""),
        "status": status,
        "source": source,
        "timestamp": datetime.now().isoformat(),
    }
    if metadata:
        entry["metadata"] = metadata

    path = chat_journal_path(user_id)
    existing = _read_jsonl(path)
    for idx, row in enumerate(existing):
        if row.get("message_id") == message_id:
            merged = {**row, **{k: v for k, v in entry.items() if v not in (None, "")}}
            existing[idx] = merged
            tmp = path.with_suffix(path.suffix + ".tmp")
            with tmp.open("w") as fh:
                for item in existing:
                    fh.write(json.dumps(item, ensure_ascii=False) + "\n")
            tmp.replace(path)
            return entry
    with path.open("a") as fh:
        fh.write(json.dumps(entry, ensure_ascii=False) + "\n")
    return entry


def _format_entry(row: Dict[str, Any]) -> Dict[str, Any]:
    timestamp = row.get("timestamp") or row.get("created_at") or ""
    time_label = ""
    if timestamp:
        try:
            time_label = datetime.fromisoformat(timestamp).strftime("%H:%M:%S")
        except Exception:
            time_label = str(timestamp)[11:19] if len(str(timestamp)) >= 19 else ""
    return {
        "message_id": row.get("message_id") or new_message_id("legacy"),
        "role": row.get("role", "assistant"),
        "content": row.get("content", ""),
        "time": time_label,
        "timestamp": timestamp,
        "status": row.get("status", "sent"),
        "source": row.get("source", "runtime"),
        "metadata": row.get("metadata") or {},
        "reply_to_message_id": (row.get("metadata") or {}).get("reply_to_message_id"),
    }


def _load_journal(user_id: str) -> List[Dict[str, Any]]:
    return [_format_entry(row) for row in _read_jsonl(chat_journal_path(user_id))]


def _load_episodic_fallback(user_id: str, limit_turns: int) -> List[Dict[str, Any]]:
    base = user_base(user_id) / "conversations"
    legacy = data_dir() / "conversations"
    conv_dirs = [base]
    if legacy != base and not str(user_id).startswith("benchmark_"):
        conv_dirs.append(legacy)
    if not str(user_id).startswith("benchmark_"):
        bot_prefixed = [p for p in (data_dir() / "users").glob(f"*_{normalize_user_id(user_id)}")
                       if (p / "conversations").exists()]
        conv_dirs.extend(p / "conversations" for p in bot_prefixed)

    existing_dirs = [p for p in conv_dirs if p.exists() and list(p.glob("*.jsonl"))]
    if not existing_dirs:
        return []

    turns: List[Dict[str, Any]] = []
    for conv_dir in existing_dirs:
        for file in sorted(conv_dir.glob("*.jsonl"), reverse=True):
            file_rows = _read_jsonl(file)
            turns.extend(reversed(file_rows))
    turns = sorted(turns, key=lambda row: row.get("timestamp", ""), reverse=True)[:limit_turns]

    messages: List[Dict[str, Any]] = []
    for row in reversed(turns):
        ts = row.get("timestamp", "")
        if row.get("user"):
            messages.append(_format_entry({
                "message_id": f"legacy_user_{len(messages)}_{ts}",
                "role": "user",
                "content": row.get("user", ""),
                "timestamp": ts,
                "source": "episodic",
            }))
        if row.get("ai"):
            messages.append(_format_entry({
                "message_id": f"legacy_ai_{len(messages)}_{ts}",
                "role": "alive_ai",
                "content": row.get("ai", ""),
                "timestamp": ts,
                "source": "episodic",
            }))
    return messages


def load_chat_messages(user_id: str, limit: int = 60) -> List[Dict[str, Any]]:
    if limit and limit > 0:
        episodic_limit = max(1, limit // 2)
    else:
        episodic_limit = 1_000_000
    messages = _load_episodic_fallback(user_id, episodic_limit)
    messages.extend(_load_journal(user_id))

    deduped: Dict[str, Dict[str, Any]] = {}
    for msg in messages:
        key = msg.get("message_id") or f"{msg.get('role')}:{msg.get('timestamp')}:{msg.get('content')}"
        deduped[key] = msg

    ordered = sorted(
        deduped.values(),
        key=lambda m: m.get("timestamp") or ""
    )
    return ordered[-limit:] if limit and limit > 0 else ordered


def count_visible_messages(user_id: str) -> int:
    return len(load_chat_messages(user_id, limit=0))
