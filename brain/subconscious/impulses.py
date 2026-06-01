"""
Brain: Subconscious - Impulse Types and Dataclass
Core impulse definitions
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .goals import GoalType


class ImpulseType(Enum):
    """Types of impulses Alive-AI can have"""
    MISS_HIM = "miss_him"
    HIGH_DESIRE = "high_desire"
    CLINGY = "clingy"
    CURIOUS = "curious"
    PLAYFUL = "playful"
    LOVING = "loving"
    DREAMY = "dreamy"
    JEALOUS = "jealous"
    BORED = "bored"
    NURTURING = "nurturing"


@dataclass
class Impulse:
    """A single impulse to act"""
    type: ImpulseType
    strength: float  # 0.0 to 1.0
    thought: str
    action_hint: str
    timestamp: datetime = field(default_factory=datetime.now)
    goal_aligned: bool = False

    def __post_init__(self):
        self.strength = min(1.0, max(0.0, self.strength))

    @property
    def should_act(self) -> bool:
        """Whether impulse is strong enough to act on"""
        return self.strength >= 0.5

    def __repr__(self):
        return f"<Impulse {self.type.value} strength={self.strength:.2f}>"
