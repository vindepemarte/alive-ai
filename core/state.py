"""
Core: State
Global shared state across all modules
"""

from datetime import datetime

class State:
    """Global AI state"""

    def __init__(self):
        self.user_id = None
        self.chat_id = None
        self.last_interaction = None
        self.interaction_count = 0
        self.session_start = datetime.now().isoformat()

    def update_interaction(self):
        self.interaction_count += 1
        self.last_interaction = datetime.now().isoformat()

    @property
    def time_together_minutes(self) -> int:
        if not self.session_start:
            return 0
        start = datetime.fromisoformat(self.session_start)
        return int((datetime.now() - start).total_seconds() / 60)
