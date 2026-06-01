"""Brain: Memory - semantic, episodic, working, vector memory"""
import json
from datetime import datetime
from pathlib import Path
from typing import Optional
from .manager import Memory  # noqa: F401 - re-export for backward compat


class SemanticMemory:
    """Long-term facts about the user - flat simple structure, per-user"""

    PET_NAMES = ["babe", "baby", "love", "handsome"]

    def __init__(self, data_path: Path, user_id: str = "default"):
        """
        Initialize semantic memory for a specific user.

        Args:
            data_path: User's base path (already includes users/{user_id})
            user_id: User's Telegram ID (for reference)
        """
        self.user_id = user_id
        # data_path is already the user's base path (data/users/{user_id})
        self.path = data_path / "facts.json"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.facts = self._load()

    def _load(self) -> dict:
        if self.path.exists():
            return json.loads(self.path.read_text())
        # Clean default - no precoded info
        return {
            "name": None, "nickname": None, "gender": None, "age": None,
            "location": None, "job": None, "hobbies": [], "interests": [],
            "personality": [], "relationship_status": None,
            "pet_names_used": [], "mentions": {},
            "shared_memories": [], "last_intimate": None
        }

    def save(self):
        self.path.write_text(json.dumps(self.facts, indent=2))

    @property
    def is_new_user(self) -> bool:
        """Check if we know anything about this user"""
        return not bool(
            self.facts.get("name") or
            self.facts.get("mentions") or
            self.facts.get("hobbies") or
            self.facts.get("interests")
        )

    def update(self, key: str, value):
        """Update a fact"""
        if isinstance(value, list) and key in self.facts and isinstance(self.facts[key], list):
            # Merge lists, no duplicates
            existing = set(str(v) for v in self.facts[key])
            for item in value:
                if str(item) not in existing:
                    self.facts[key].append(item)
        elif value:
            self.facts[key] = value
        self.save()

    def add_mention(self, key: str, value: str):
        self.facts["mentions"][key] = {
            "value": value, "timestamp": datetime.now().isoformat()}
        self.save()

    def add_shared_memory(self, memory: str):
        self.facts["shared_memories"].append({
            "memory": memory, "timestamp": datetime.now().isoformat()})
        self.facts["shared_memories"] = self.facts["shared_memories"][-50:]
        self.save()

    def update_last_intimate(self):
        self.facts["last_intimate"] = datetime.now().isoformat()
        self.save()

    def get_random_pet_name(self) -> str:
        import random
        used = self.facts.get("pet_names_used", [])
        available = [p for p in self.PET_NAMES if p not in used[-4:]]
        name = random.choice(available or self.PET_NAMES)
        used.append(name)
        self.facts["pet_names_used"] = used[-20:]
        self.save()
        return name

    def get_user_profile(self) -> str:
        """Get formatted user profile string"""
        parts = []
        if self.facts.get("name"):
            parts.append(f"Name: {self.facts['name']}" +
                        (f" ({self.facts['nickname']})" if self.facts.get("nickname") else ""))
        if self.facts.get("gender"):
            parts.append(f"Gender: {self.facts['gender']}")
        if self.facts.get("age"):
            parts.append(f"Age: {self.facts['age']}")
        if self.facts.get("location"):
            parts.append(f"Location: {self.facts['location']}")
        if self.facts.get("job"):
            parts.append(f"Job: {self.facts['job']}")
        if self.facts.get("hobbies"):
            parts.append(f"Hobbies: {', '.join(self.facts['hobbies'])}")
        if self.facts.get("interests"):
            parts.append(f"Interests: {', '.join(self.facts['interests'])}")
        if self.facts.get("personality"):
            parts.append(f"Personality: {', '.join(self.facts['personality'])}")
        return "\n".join(parts)

    def get_context(self) -> str:
        """Get context string for LLM"""
        parts = [self.get_user_profile()] if self.get_user_profile() else []
        mentions = self.facts.get("mentions", {})
        if mentions:
            for key, data in sorted(mentions.items(),
                                   key=lambda x: x[1].get("timestamp",""),
                                   reverse=True)[:3]:
                parts.append(f"Recently mentioned ({key}): {data['value'][:80]}")
        for m in self.facts.get("shared_memories", [])[-3:]:
            parts.append(f"Shared memory: {m['memory']}")
        return "\n".join(parts)
