"""
Brain: Subconscious - Learning Data Models
InteractionRecord dataclass
"""

from datetime import datetime
from typing import Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class InteractionRecord:
    """Record of a single interaction and its outcome"""
    message: str
    message_type: str
    timestamp: datetime = field(default_factory=datetime.now)
    response_sentiment: float = 0.0
    response_type: Optional[str] = None
    context: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {"message": self.message, "message_type": self.message_type,
                "timestamp": self.timestamp.isoformat(),
                "response_sentiment": self.response_sentiment, "response_type": self.response_type}
