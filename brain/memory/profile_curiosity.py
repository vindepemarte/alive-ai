"""Natural first-conversation curiosity about the human user."""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping


PROFILE_FIELDS = [
    {
        "key": "name",
        "facts": ("name", "nickname"),
        "label": "what they like being called",
        "examples": ["what should I call you?", "wait, what do you like being called?"],
        "keywords": ("name", "call you", "called"),
    },
    {
        "key": "age",
        "facts": ("age",),
        "label": "their age",
        "examples": ["how old are you, actually?", "wait, I don't know how old you are yet."],
        "keywords": ("old are you", "age"),
    },
    {
        "key": "gender",
        "facts": ("gender",),
        "label": "their gender or pronouns",
        "examples": ["how should I think of you, gender-wise?", "what pronouns feel right for you?"],
        "keywords": ("gender", "pronouns", "man", "woman", "male", "female"),
    },
    {
        "key": "location",
        "facts": ("location",),
        "label": "where they are in the world",
        "examples": ["where are you based?", "what part of the world are you in?"],
        "keywords": ("where are you", "based", "world", "city"),
    },
    {
        "key": "hobbies",
        "facts": ("hobbies", "interests"),
        "label": "what they enjoy doing",
        "examples": ["what do you do when you're not here?", "what are you into lately?"],
        "keywords": ("what are you into", "hobbies", "enjoy", "like doing"),
    },
    {
        "key": "job",
        "facts": ("job",),
        "label": "what their days are usually like",
        "examples": ["what do your days usually look like?", "what keeps you busy most days?"],
        "keywords": ("work", "job", "days", "busy"),
    },
]


class ProfileCuriosity:
    """Pick one natural question about missing profile facts, without a setup flow."""

    def __init__(self, data_path: Path):
        self.data_path = Path(data_path)
        self.facts_path = self.data_path / "facts.json"
        self.state_path = self.data_path / "profile_curiosity.json"

    def _load_json(self, path: Path, default: Any) -> Any:
        try:
            if path.exists():
                return json.loads(path.read_text())
        except Exception:
            pass
        return default

    def _save_state(self, state: dict):
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(state, indent=2))

    def _load_facts(self) -> dict:
        return self._load_json(self.facts_path, {})

    def _load_state(self) -> dict:
        return self._load_json(self.state_path, {"asked": {}, "complete": False})

    @staticmethod
    def _known(facts: Mapping[str, Any], field: Mapping[str, Any]) -> bool:
        for key in field["facts"]:
            value = facts.get(key)
            if isinstance(value, list) and value:
                return True
            if value not in (None, "", [], {}):
                return True
        return False

    @staticmethod
    def _bad_moment(current_message: str) -> bool:
        text = (current_message or "").lower()
        return any(
            term in text
            for term in (
                "panic", "depressed", "suicide", "emergency", "hurt", "crying",
                "not now", "stop asking", "leave me", "angry", "pissed",
            )
        )

    @staticmethod
    def _recent_assistant_question(history: list[dict]) -> bool:
        for turn in reversed(history[-4:]):
            if turn.get("role") == "assistant":
                return "?" in str(turn.get("content", ""))
        return False

    def next_prompt(self, current_message: str, history: list[dict]) -> dict | None:
        try:
            from core.settings import get_bool, get_int
            if not get_bool("PROFILE_CURIOSITY_ENABLED", True):
                return None
            min_turns_between = get_int("PROFILE_CURIOSITY_MIN_TURNS_BETWEEN", 2)
        except Exception:
            min_turns_between = 2

        if self._bad_moment(current_message) or self._recent_assistant_question(history):
            return None

        facts = self._load_facts()
        state = self._load_state()
        if state.get("complete"):
            return None

        asked = state.get("asked", {})
        turn_index = len(history)
        last_turn = int(state.get("last_asked_turn", -999))
        if turn_index - last_turn < min_turns_between:
            return None

        missing = [
            field for field in PROFILE_FIELDS
            if not self._known(facts, field) and field["key"] not in asked
        ]
        if not missing:
            state["complete"] = True
            state["completed_at"] = datetime.now().isoformat()
            self._save_state(state)
            return None

        field = missing[0]
        examples = " / ".join(field["examples"])
        return {
            "key": field["key"],
            "label": field["label"],
            "keywords": list(field["keywords"]),
            "turn_index": turn_index,
            "prompt": (
                "PROFILE CURIOSITY\n"
                f"You still don't know {field['label']}.\n"
                "If it fits naturally, answer the user's message first, then weave in ONE small question about that detail.\n"
                "Do not sound like onboarding, setup, a survey, or a checklist. Do not ask multiple questions.\n"
                "If the moment feels wrong, skip the question.\n"
                f"Natural examples: {examples}"
            ),
        }

    def mark_if_asked(self, response: str, prompt_info: Mapping[str, Any] | None) -> bool:
        if not prompt_info or "?" not in (response or ""):
            return False
        response_lower = response.lower()
        keywords = [str(item).lower() for item in prompt_info.get("keywords", [])]
        if keywords and not any(keyword in response_lower for keyword in keywords):
            return False

        state = self._load_state()
        asked = state.setdefault("asked", {})
        key = str(prompt_info.get("key") or "").strip()
        if not key:
            return False
        asked[key] = datetime.now().isoformat()
        state["last_asked_turn"] = int(prompt_info.get("turn_index", 0))
        self._save_state(state)
        return True

    def capture_obvious_answer(self, user_message: str) -> dict:
        """Capture simple direct answers before the slower LLM fact extractor runs."""
        message = (user_message or "").strip()
        if not message:
            return {}

        facts = self._load_facts()
        updates: dict[str, Any] = {}

        name_match = re.search(r"\b(?:my name is|i'm called|i am called|call me)\s+([A-Za-z][A-Za-z' -]{1,40})", message, re.IGNORECASE)
        if name_match and not facts.get("name"):
            updates["name"] = name_match.group(1).strip(" .,!").title()

        age_match = re.search(r"\b(?:i am|i'm)\s+(\d{1,3})\b", message, re.IGNORECASE)
        if age_match and not facts.get("age"):
            age = int(age_match.group(1))
            if 1 <= age <= 120:
                updates["age"] = age

        gender_patterns = [
            (r"\b(?:i am|i'm)\s+(?:a\s+)?(?:male|man|guy|boy)\b", "male"),
            (r"\b(?:i am|i'm)\s+(?:a\s+)?(?:female|woman|girl)\b", "female"),
            (r"\b(?:i am|i'm)\s+(?:nonbinary|non-binary|nb)\b", "nonbinary"),
        ]
        if not facts.get("gender"):
            for pattern, value in gender_patterns:
                if re.search(pattern, message, re.IGNORECASE):
                    updates["gender"] = value
                    break

        if not updates:
            return {}

        facts.update(updates)
        self.facts_path.parent.mkdir(parents=True, exist_ok=True)
        self.facts_path.write_text(json.dumps(facts, indent=2))
        return updates

    def capture_profile_metadata(self, profile: Mapping[str, Any]) -> dict:
        """Store visible transport profile data without treating it as preferred identity."""
        if not profile:
            return {}

        facts = self._load_facts()
        updates: dict[str, Any] = {}

        display_name = str(profile.get("display_name") or "").strip()
        username = str(profile.get("username") or "").strip().lstrip("@")

        if display_name and not facts.get("display_name"):
            updates["display_name"] = display_name
        if username and not facts.get("username"):
            updates["username"] = username

        if not updates:
            return {}

        facts.update(updates)
        self.facts_path.parent.mkdir(parents=True, exist_ok=True)
        self.facts_path.write_text(json.dumps(facts, indent=2))
        return updates
