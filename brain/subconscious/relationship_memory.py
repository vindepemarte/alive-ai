"""Brain: Subconscious - Relationship Memory — milestones and experiences"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from .relationship import Milestone, MilestoneType, SharedExperience


class RelationshipMemory:
    def __init__(self, max_experiences: int = 100):
        self.milestones: List[Milestone] = []
        self.shared_experiences: List[SharedExperience] = []
        self.max_experiences = max_experiences
        self.favorite_topics: Dict[str, int] = {}
        self.conversation_count: int = 0
        self.relationship_start: Optional[datetime] = None
        self.total_messages_sent: int = 0
        self.total_messages_received: int = 0

    def record_milestone(self, mtype: MilestoneType, desc: str, emotion: float = 0.5):
        if any(m.type == mtype for m in self.milestones): return
        m = Milestone(type=mtype, description=desc, emotion=emotion)
        self.milestones.append(m)
        if not self.relationship_start: self.relationship_start = m.timestamp

    def record_experience(self, summary: str, sentiment: float = 0.5, tags: List[str] = None):
        self.shared_experiences.append(SharedExperience(summary=summary, sentiment=sentiment, tags=tags or []))
        for t in (tags or []): self.favorite_topics[t] = self.favorite_topics.get(t, 0) + 1
        if len(self.shared_experiences) > self.max_experiences: self.shared_experiences.pop(0)

    def record_conversation(self, topics: List[str] = None):
        self.conversation_count += 1
        for t in (topics or []): self.favorite_topics[t] = self.favorite_topics.get(t, 0) + 1

    def record_message_sent(self): self.total_messages_sent += 1
    def record_message_received(self): self.total_messages_received += 1

    def get_relationship_duration(self) -> timedelta:
        return datetime.now() - self.relationship_start if self.relationship_start else timedelta(0)

    def get_relationship_stage(self) -> str:
        d = self.get_relationship_duration().days
        if d < 1: return "just_met"
        if d < 7: return "getting_to_know"
        if d < 30: return "developing"
        if d < 90: return "growing"
        return "established"

    def get_special_memories(self, limit: int = 5) -> List[str]:
        return [m.description for m in self.milestones if m.emotion > 0.7][-limit:]

    def get_recent_experiences(self, limit: int = 5) -> List[str]:
        return [e.summary for e in self.shared_experiences[-limit:]]

    def get_relationship_context(self) -> str:
        stage, days = self.get_relationship_stage(), self.get_relationship_duration().days
        special = self.get_special_memories(2)
        ctx = f"Relationship: {stage} ({days} days)"
        return ctx + f"\nSpecial: {', '.join(special)}" if special else ctx

    def to_dict(self) -> dict:
        return {"milestones": [m.to_dict() for m in self.milestones],
                "shared_experiences": [e.to_dict() for e in self.shared_experiences[-50:]],
                "favorite_topics": self.favorite_topics, "conversation_count": self.conversation_count,
                "total_messages_sent": self.total_messages_sent,
                "total_messages_received": self.total_messages_received,
                "relationship_start": self.relationship_start.isoformat() if self.relationship_start else None}

    @classmethod
    def from_dict(cls, data: dict) -> "RelationshipMemory":
        rm = cls()
        for md in data.get("milestones", []):
            rm.milestones.append(Milestone(type=MilestoneType(md["type"]), description=md["description"],
                timestamp=datetime.fromisoformat(md["timestamp"]), emotion=md.get("emotion", 0.5)))
        for ed in data.get("shared_experiences", []):
            rm.shared_experiences.append(SharedExperience(summary=ed["summary"],
                timestamp=datetime.fromisoformat(ed["timestamp"]), sentiment=ed.get("sentiment", 0.5),
                tags=ed.get("tags", [])))
        rm.favorite_topics = data.get("favorite_topics", {})
        rm.conversation_count = data.get("conversation_count", 0)
        rm.total_messages_sent = data.get("total_messages_sent", 0)
        rm.total_messages_received = data.get("total_messages_received", 0)
        if data.get("relationship_start"):
            rm.relationship_start = datetime.fromisoformat(data["relationship_start"])
        return rm
