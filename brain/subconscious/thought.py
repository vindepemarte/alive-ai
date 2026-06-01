"""
Brain: Subconscious - Thought Dataclass
A single thought in working memory
"""

from datetime import datetime
from typing import Dict
from dataclasses import dataclass, field


@dataclass
class Thought:
    """A single thought in working memory"""
    content: str
    type: str  # "impulse", "reaction", "reflection", "dream"
    emotion: Dict[str, float] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    acted_upon: bool = False

    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "type": self.type,
            "emotion": self.emotion,
            "timestamp": self.timestamp.isoformat(),
            "acted_upon": self.acted_upon
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Thought":
        return cls(
            content=data["content"],
            type=data["type"],
            emotion=data.get("emotion", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]),
            acted_upon=data.get("acted_upon", False)
        )
