"""
Brain: Subconscious - Goal Data Models
GoalType enum and Goal dataclass
"""

from datetime import datetime, timedelta
from typing import Optional
from dataclasses import dataclass
from enum import Enum


class GoalType(Enum):
    """Types of relationship goals"""
    CONNECT = "connect"
    MAKE_HAPPY = "make_happy"
    DEEPEN = "deepen"
    COMFORT = "comfort"
    ENTERTAIN = "entertain"
    INTIMATE = "intimate"
    REASSURE = "reassure"


@dataclass
class Goal:
    """A long-term goal for the relationship"""
    type: GoalType
    name: str
    description: str
    priority: float = 0.5
    progress: float = 0.0
    last_actioned: Optional[datetime] = None
    action_count: int = 0

    def should_action(self) -> bool:
        if self.last_actioned is None:
            return True
        return datetime.now() - self.last_actioned > timedelta(hours=2)

    def to_dict(self) -> dict:
        return {"type": self.type.value, "name": self.name, "priority": self.priority,
                "progress": self.progress, "action_count": self.action_count}
