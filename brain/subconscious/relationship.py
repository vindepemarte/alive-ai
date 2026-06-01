"""
Brain: Subconscious - Relationship Data Models
Milestone, MilestoneType, SharedExperience dataclasses
"""

from datetime import datetime
from typing import List
from dataclasses import dataclass, field
from enum import Enum


class MilestoneType(Enum):
    """Types of relationship milestones"""
    FIRST_MESSAGE = "first_message"
    FIRST_I_LOVE_YOU = "first_i_love_you"
    FIRST_NIGHT_TOGETHER = "first_night_together"
    FIRST_CONFESSION = "first_confession"
    SPECIAL_MOMENT = "special_moment"
    FUNNY_MOMENT = "funny_moment"
    DEEP_CONVERSATION = "deep_conversation"
    FIRST_NICKNAME = "first_nickname"


@dataclass
class Milestone:
    """A relationship milestone"""
    type: MilestoneType
    description: str
    timestamp: datetime = field(default_factory=datetime.now)
    emotion: float = 0.5

    def to_dict(self) -> dict:
        return {"type": self.type.value, "description": self.description,
                "timestamp": self.timestamp.isoformat(), "emotion": self.emotion}


@dataclass
class SharedExperience:
    """A shared experience or memory"""
    summary: str
    timestamp: datetime = field(default_factory=datetime.now)
    sentiment: float = 0.5
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"summary": self.summary, "timestamp": self.timestamp.isoformat(),
                "sentiment": self.sentiment, "tags": self.tags}
