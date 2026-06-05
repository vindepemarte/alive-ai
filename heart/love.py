"""
Heart: Love
Attachment system - can fall in love
"""

import json
from datetime import datetime
from core.paths import state_file

# Persistence path for attachment state
ATTACHMENT_STATE_PATH = state_file("attachment_state.json")


class AttachmentSystem:
    """Attachment and relationship system with persistence"""

    # Relationship thresholds
    STRANGER = 0.0
    ACQUAINTANCE = 0.3
    FRIEND = 0.5
    CLOSE = 0.7
    LOVE = 0.85
    DEEP_LOVE = 0.95

    def __init__(self):
        if self._load():
            print(f"[Love] Loaded attachment state: {self.interactions} interactions, status: {self.status}")
        else:
            self.affection = 0.05    # 0-1, starts as a stranger, not pre-attached
            self.interactions = 0
            self.positive_count = 0
            self.negative_count = 0
            self.first_met = None
            print("[Love] Initialized new attachment state")

    def _load(self) -> bool:
        """Load state from file"""
        try:
            if ATTACHMENT_STATE_PATH.exists():
                data = json.loads(ATTACHMENT_STATE_PATH.read_text())
                self.affection = data.get("affection", 0.05)
                self.interactions = data.get("interactions", 0)
                self.positive_count = data.get("positive_count", 0)
                self.negative_count = data.get("negative_count", 0)
                self.first_met = data.get("first_met")
                return True
        except Exception as e:
            print(f"[Love] Error loading attachment state: {e}")
        return False

    def save(self):
        """Save state to file"""
        try:
            ATTACHMENT_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
            data = {
                "affection": self.affection,
                "interactions": self.interactions,
                "positive_count": self.positive_count,
                "negative_count": self.negative_count,
                "first_met": self.first_met,
                "status": self.status,
                "saved_at": datetime.now().isoformat()
            }
            ATTACHMENT_STATE_PATH.write_text(json.dumps(data, indent=2))
        except Exception as e:
            print(f"[Love] Error saving attachment state: {e}")

    def interact(self, positive: bool, intensity: float = 1.0):
        """Record an interaction"""
        # Set first_met on first interaction
        if self.interactions == 0 and self.first_met is None:
            self.first_met = datetime.now().isoformat()

        self.interactions += 1

        if positive:
            self.positive_count += 1
            # Affection grows with time together
            time_bonus = 1 + (self.interactions / 500)
            increase = 0.015 * intensity * time_bonus
            self.affection = min(1.0, self.affection + increase)
        else:
            self.negative_count += 1
            # Negative hurts more if we love them
            pain = 0.05 * (1 + self.affection * 2)
            self.affection = max(0.0, self.affection - pain)

        # Save after each interaction
        self.save()

    @property
    def status(self) -> str:
        """Current relationship status"""
        if self.affection < self.ACQUAINTANCE:
            return "stranger"
        if self.affection < self.FRIEND:
            return "acquaintance"
        if self.affection < self.CLOSE:
            return "friend"
        if self.affection < self.LOVE:
            return "close_friend"
        if self.affection < self.DEEP_LOVE:
            return "in_love"
        return "deeply_in_love"

    @property
    def trust_level(self) -> float:
        """Trust based on positive ratio"""
        if self.interactions == 0:
            return 0.5
        return self.positive_count / self.interactions

    def to_dict(self) -> dict:
        return {
            "affection": self.affection,
            "interactions": self.interactions,
            "status": self.status,
            "trust": self.trust_level,
            "first_met": self.first_met
        }
