"""
Core: State
Global shared state across all modules
"""

import json
from datetime import datetime
from .paths import state_file


STATE_PATH = state_file("runtime_state.json")

class State:
    """Global AI state"""

    def __init__(self):
        self.user_id = None
        self.chat_id = None
        self.last_interaction = None
        self.interaction_count = 0
        self.session_start = datetime.now().isoformat()
        self._load()

    def update_interaction(self, user_id=None, chat_id=None):
        if user_id is not None:
            self.user_id = user_id
        if chat_id is not None:
            self.chat_id = chat_id
        self.interaction_count += 1
        self.last_interaction = datetime.now().isoformat()
        self.save()

    @property
    def time_together_minutes(self) -> int:
        if not self.session_start:
            return 0
        start = datetime.fromisoformat(self.session_start)
        return int((datetime.now() - start).total_seconds() / 60)

    def to_dict(self) -> dict:
        return {
            "user_id": self.user_id,
            "chat_id": self.chat_id,
            "last_interaction": self.last_interaction,
            "interaction_count": self.interaction_count,
            "session_start": self.session_start,
            "saved_at": datetime.now().isoformat(),
        }

    def save(self):
        try:
            STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            STATE_PATH.write_text(json.dumps(self.to_dict(), indent=2))
        except Exception as e:
            print(f"[State] Error saving runtime state: {e}")

    def _load(self) -> bool:
        try:
            if STATE_PATH.exists():
                data = json.loads(STATE_PATH.read_text())
                self.user_id = data.get("user_id")
                self.chat_id = data.get("chat_id")
                self.last_interaction = data.get("last_interaction")
                self.interaction_count = int(data.get("interaction_count", 0))
                return True
        except Exception as e:
            print(f"[State] Error loading runtime state: {e}")
        return False
