"""
Brain: Subconscious - Learning System
Tracks successful actions and learns from user responses
"""

from datetime import datetime
from typing import Dict, Any, List
from collections import defaultdict

from .learning import InteractionRecord


class LearningSystem:
    """Tracks what works and adapts behavior over time"""

    def __init__(self, max_records: int = 200):
        self.interactions: List[InteractionRecord] = []
        self.max_records = max_records
        self.successful_messages: Dict[str, float] = defaultdict(float)
        self.successful_times: Dict[int, float] = defaultdict(float)

    def record_interaction(self, message: str, message_type: str,
                           response_sentiment: float = 0.0, response_type: str = "neutral",
                           context: Dict[str, Any] = None) -> None:
        record = InteractionRecord(message=message, message_type=message_type,
                                    response_sentiment=response_sentiment,
                                    response_type=response_type, context=context or {})
        self.interactions.append(record)
        success = response_sentiment > 0.3
        self._update_success_rate(self.successful_messages, message_type, success)
        self._update_success_rate(self.successful_times, record.timestamp.hour, success)
        if len(self.interactions) > self.max_records:
            self.interactions.pop(0)

    def _update_success_rate(self, tracking_dict: Dict, key: Any, success: bool) -> None:
        current = tracking_dict[key]
        alpha = 0.1
        tracking_dict[key] = current * (1 - alpha) + (1.0 if success else 0.0) * alpha

    def get_best_message_types(self, limit: int = 3) -> List[str]:
        if not self.successful_messages:
            return ["loving", "curious", "playful"]
        sorted_types = sorted(self.successful_messages.items(), key=lambda x: x[1], reverse=True)
        return [t[0] for t in sorted_types[:limit]]

    def get_success_rate(self, message_type: str) -> float:
        return self.successful_messages.get(message_type, 0.5)

    def get_recent_success_rate(self, n: int = 10) -> float:
        if not self.interactions:
            return 0.5
        recent = self.interactions[-n:]
        successes = sum(1 for i in recent if i.response_sentiment > 0.3)
        return successes / len(recent)

    def suggest_message_type(self) -> str:
        best_types = self.get_best_message_types()
        return best_types[0] if best_types else "loving"

    def to_dict(self) -> dict:
        return {"interactions": [i.to_dict() for i in self.interactions[-50:]],
                "successful_messages": dict(self.successful_messages),
                "successful_times": {str(k): v for k, v in self.successful_times.items()}}

    @classmethod
    def from_dict(cls, data: dict) -> "LearningSystem":
        learning = cls()
        for i_data in data.get("interactions", []):
            record = InteractionRecord(
                message=i_data["message"], message_type=i_data["message_type"],
                timestamp=datetime.fromisoformat(i_data["timestamp"]),
                response_sentiment=i_data.get("response_sentiment", 0.0),
                response_type=i_data.get("response_type", "neutral")
            )
            learning.interactions.append(record)
        learning.successful_messages = defaultdict(float, data.get("successful_messages", {}))
        learning.successful_times = defaultdict(float,
            {int(k): v for k, v in data.get("successful_times", {}).items()})
        return learning
