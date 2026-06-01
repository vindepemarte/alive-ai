"""
Brain: Episodic Memory
Event and conversation memory - per-user storage
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Optional

class EpisodicMemory:
    """Episodic memory for events - per-user conversation storage"""

    def __init__(self, data_path: Path, user_id: str = "default"):
        """
        Initialize episodic memory for a specific user.

        Args:
            data_path: User's base path (already includes users/{user_id})
            user_id: User's Telegram ID (for reference)
        """
        self.user_id = user_id
        # data_path is already the user's base path (data/users/{user_id})
        self.path = data_path / "conversations"
        self.path.mkdir(parents=True, exist_ok=True)

    def save(self, user_msg: str, ai_response: str, emotion: dict):
        """Save conversation turn"""
        date = datetime.now().strftime("%Y-%m-%d")
        file = self.path / f"{date}.jsonl"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": user_msg,
            "ai": ai_response,
            "emotion": emotion
        }

        with open(file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def save_proactive(self, ai_msg: str, emotion: dict):
        """Save a proactive message (Alive-AI initiated, no user message)"""
        date = datetime.now().strftime("%Y-%m-%d")
        file = self.path / f"{date}.jsonl"

        entry = {
            "timestamp": datetime.now().isoformat(),
            "user": "",  # Empty - Alive-AI initiated
            "ai": ai_msg,
            "emotion": {**emotion, "proactive": True}
        }

        with open(file, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def load_recent(self, limit: int = 5) -> list:
        """Load recent conversations (most recent first, then reversed to chronological)"""
        all_entries = []

        for file in sorted(self.path.glob("*.jsonl"), reverse=True):
            file_entries = []
            with open(file) as f:
                for line in f:
                    try:
                        file_entries.append(json.loads(line))
                    except Exception:
                        pass
            # Reverse so newest entries from this file come first
            all_entries.extend(reversed(file_entries))
            if len(all_entries) >= limit:
                break

        # Take the most recent 'limit' entries, then reverse to chronological order
        result = list(reversed(all_entries[:limit]))
        print(f"[Episodic] Loading {len(result)} recent entries from {len(all_entries)} total")
        return result

    def get_by_date(self, date_str: str) -> list:
        """Get conversations by date"""
        file = self.path / f"{date_str}.jsonl"
        if not file.exists():
            return []

        entries = []
        with open(file) as f:
            for line in f:
                try:
                    entries.append(json.loads(line))
                except:
                    pass
        return entries
