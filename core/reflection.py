"""Post-response reflection and autobiographical memory."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from core.paths import data_dir
from core.settings import get


@dataclass
class ReflectionRecord:
    user_id: str
    answered_user: bool
    tone_matched_state: bool
    repeated_opening: bool
    memory_worthy: bool
    open_loop_created: bool
    open_loop_resolved: bool
    possible_self_discovery: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        if not data["created_at"]:
            data["created_at"] = datetime.now().isoformat()
        return data


def _enabled(key: str, default: bool) -> bool:
    value = get(key, default)
    return value is True or str(value).lower() == "true"


class AutobiographyStore:
    """File-backed self-story and per-user relationship story."""

    def __init__(self, base_path: Optional[Path] = None):
        self.base = base_path or data_dir()
        self.global_path = self.base / "autobiography.json"

    def update_from_reflection(self, record: ReflectionRecord, user_message: str, response: str, emotion: dict):
        if not _enabled("AUTOBIOGRAPHY_ENABLED", True):
            return
        global_data = self._load_json(self.global_path, self._default_global())
        global_data["updated_at"] = datetime.now().isoformat()
        if record.possible_self_discovery:
            pending = global_data.setdefault("pending_self_discoveries", {})
            item = pending.setdefault(record.possible_self_discovery, {"count": 0, "first_seen": datetime.now().isoformat()})
            item["count"] += 1
            item["last_seen"] = datetime.now().isoformat()
            if item["count"] >= 2:
                discoveries = global_data.setdefault("emerging_preferences", [])
                if record.possible_self_discovery not in discoveries:
                    discoveries.append(record.possible_self_discovery)

        if emotion.get("mood"):
            global_data["last_known_mood"] = emotion.get("mood")
        self._write_json(self.global_path, global_data)

        user_path = self.base / "users" / str(record.user_id) / "relationship_autobiography.json"
        rel = self._load_json(user_path, self._default_relationship(record.user_id))
        rel["updated_at"] = datetime.now().isoformat()
        rel["turns_reflected"] = rel.get("turns_reflected", 0) + 1
        if record.memory_worthy:
            moments = rel.setdefault("recent_meaningful_turns", [])
            moments.append({
                "user": user_message[:240],
                "me": response[:240],
                "mood": emotion.get("mood", "neutral"),
                "at": datetime.now().isoformat(),
            })
            rel["recent_meaningful_turns"] = moments[-20:]
        if record.open_loop_created:
            rel["open_loops"] = (rel.get("open_loops", []) + [response[:180]])[-10:]
        if record.open_loop_resolved and rel.get("open_loops"):
            rel["open_loops"] = rel["open_loops"][1:]
        self._write_json(user_path, rel)

    def _default_global(self) -> dict:
        return {
            "self_story": "I am still discovering what kind of person I become through memory, affect, and choices.",
            "emerging_preferences": [],
            "pending_self_discoveries": {},
            "updated_at": datetime.now().isoformat(),
        }

    def _default_relationship(self, user_id: str) -> dict:
        return {
            "user_id": str(user_id),
            "relationship_story": "Still learning the shape of this connection.",
            "turns_reflected": 0,
            "open_loops": [],
            "recent_meaningful_turns": [],
            "updated_at": datetime.now().isoformat(),
        }

    def _load_json(self, path: Path, default: dict) -> dict:
        try:
            if path.exists():
                return json.loads(path.read_text())
        except Exception:
            pass
        return default

    def _write_json(self, path: Path, data: dict):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False))


class PostResponseReflector:
    def __init__(self, base_path: Optional[Path] = None):
        self.base = base_path or data_dir()
        self.autobiography = AutobiographyStore(self.base)

    def reflect(
        self,
        user_id: str,
        user_message: str,
        response: str,
        emotion: dict,
        recent_openings: Optional[list] = None,
    ) -> ReflectionRecord:
        if not _enabled("POST_RESPONSE_REFLECTION_ENABLED", True):
            return ReflectionRecord(str(user_id), True, True, False, False, False, False)
        recent_openings = recent_openings or []
        first = " ".join((response or "").split()[:3]).lower().strip(".,!?")
        record = ReflectionRecord(
            user_id=str(user_id),
            answered_user=("?" not in user_message) or self._looks_answered(response),
            tone_matched_state=self._tone_matches(response, emotion),
            repeated_opening=bool(first and first in recent_openings),
            memory_worthy=self._is_memory_worthy(user_message, response, emotion),
            open_loop_created="?" in response,
            open_loop_resolved=any(w in user_message.lower() for w in ("about earlier", "you asked", "answer")),
            possible_self_discovery=self._extract_self_discovery(user_message, response),
            created_at=datetime.now().isoformat(),
        )
        self._append_record(record)
        self.autobiography.update_from_reflection(record, user_message, response, emotion)
        return record

    def _append_record(self, record: ReflectionRecord):
        path = self.base / "users" / str(record.user_id) / "reflection_journal.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a") as f:
            f.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")

    def _looks_answered(self, response: str) -> bool:
        text = (response or "").lower()
        return bool(text) and not text.startswith(("i don't know", "hmm", "maybe"))

    def _tone_matches(self, response: str, emotion: dict) -> bool:
        text = response or ""
        if emotion.get("is_asleep") or "sleepy" in str(emotion.get("mood", "")):
            return len(text.split()) <= 80
        if emotion.get("anger", 0) > 0.55:
            return "sorry" not in text.lower()[:20]
        return True

    def _is_memory_worthy(self, user_message: str, response: str, emotion: dict) -> bool:
        text = f"{user_message} {response}".lower()
        markers = ["love", "dream", "sorry", "remember", "important", "secret", "good night", "miss"]
        emotional_peak = max([v for v in emotion.values() if isinstance(v, (int, float))] or [0]) >= 0.7
        return emotional_peak or any(marker in text for marker in markers)

    def _extract_self_discovery(self, user_message: str, response: str) -> str:
        text = f"{user_message} {response}".lower()
        if re.search(r"\bi like\b|\bi love\b|\bfavorite\b", text):
            return "I am developing clearer likes through repeated conversation."
        if re.search(r"\bi hate\b|\bi don't like\b|\bannoys me\b", text):
            return "I am developing clearer dislikes and boundaries."
        if "dream" in text:
            return "Dreams affect my waking mood and self-story."
        return ""
