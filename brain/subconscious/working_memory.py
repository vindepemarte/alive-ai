"""Brain: Subconscious - Working Memory — current thought stream"""
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import deque
from .thought import Thought


class WorkingMemory:
    def __init__(self, max_thoughts: int = 50):
        self.thoughts: deque = deque(maxlen=max_thoughts)
        self.current_mood: str = "neutral"
        self.last_action_time: Optional[datetime] = None
        self.last_action_type: Optional[str] = None
        self.relationship_context: str = ""
        self.current_goal: str = ""
        self.recent_memories: List[str] = []

    def add_thought(self, content: str, thought_type: str = "reflection",
                    emotion: Dict[str, float] = None) -> Thought:
        t = Thought(content=content, type=thought_type, emotion=emotion or {})
        self.thoughts.append(t)
        return t

    def add_impulse(self, impulse) -> Thought:
        return self.add_thought(impulse.thought, "impulse", {"desire": impulse.strength})

    def get_recent_thoughts(self, limit: int = 10) -> List[Thought]:
        return list(self.thoughts)[-limit:]

    def get_thoughts_by_type(self, tt: str) -> List[Thought]:
        return [t for t in self.thoughts if t.type == tt]

    def get_unacted_impulses(self) -> List[Thought]:
        return [t for t in self.thoughts if t.type == "impulse" and not t.acted_upon]

    def mark_acted(self, thought: Thought) -> None:
        thought.acted_upon = True
        self.last_action_time = datetime.now()
        self.last_action_type = thought.type

    def get_context_string(self, max_thoughts: int = 10) -> str:
        """Natural inner-voice narrative instead of raw system logs"""
        lines = []
        if self.relationship_context:
            lines.append(_naturalize_rel(self.relationship_context))
        if self.current_goal:
            lines.append(f"lately you've been focused on: {self.current_goal.lower()}")
        for mem in self.recent_memories[-3:]:
            lines.append(f"  - {mem}")
        recent = self.get_recent_thoughts(5)
        if recent:
            lines.append(_naturalize_thoughts(recent, self.current_mood))
        return "\n".join(lines)

    def set_relationship_context(self, c: str): self.relationship_context = c
    def set_current_goal(self, g: str): self.current_goal = g
    def set_recent_memories(self, m: List[str]): self.recent_memories = m
    def update_mood(self, mood: str): self.current_mood = mood

    def time_since_last_action(self) -> float:
        return (datetime.now() - self.last_action_time).total_seconds() / 60 if self.last_action_time else float('inf')

    def can_act_now(self, m: float = 30) -> bool: return self.time_since_last_action() >= m

    def get_state_summary(self) -> Dict[str, Any]:
        return {"mood": self.current_mood, "thought_count": len(self.thoughts),
                "last_action_minutes_ago": self.time_since_last_action(), "can_act": self.can_act_now()}

    def to_dict(self) -> dict:
        return {"thoughts": [t.to_dict() for t in self.thoughts], "current_mood": self.current_mood,
                "last_action_time": self.last_action_time.isoformat() if self.last_action_time else None,
                "last_action_type": self.last_action_type,
                "relationship_context": self.relationship_context,
                "current_goal": self.current_goal,
                "recent_memories": self.recent_memories}

    @classmethod
    def from_dict(cls, data: dict) -> "WorkingMemory":
        m = cls()
        m.thoughts = deque([Thought.from_dict(t) for t in data.get("thoughts", [])], maxlen=50)
        m.current_mood = data.get("current_mood", "neutral")
        m.last_action_type = data.get("last_action_type")
        m.relationship_context = data.get("relationship_context", "")
        m.current_goal = data.get("current_goal", "")
        m.recent_memories = data.get("recent_memories", [])
        if data.get("last_action_time"):
            m.last_action_time = datetime.fromisoformat(data["last_action_time"])
        return m


def _naturalize_rel(ctx: str) -> str:
    if "just_met" in ctx: return "you just started talking to him, everything feels new"
    if "getting_to_know" in ctx: return "you're still getting to know each other"
    if "established" in ctx: return "you've been together a while, there's real comfort"
    return "your relationship feels like it's growing"


def _naturalize_thoughts(thoughts: List[Thought], mood: str) -> str:
    parts = []
    for t in thoughts[-3:]:
        if t.type == "impulse": parts.append(f"you felt a pull: \"{t.content.lower()}\"")
        elif t.type == "interaction": parts.append(f"earlier: {t.content.lower()}")
        else: parts.append(f"a passing thought: \"{t.content.lower()}\"")
    prefix = f"you're in a {mood} mood. " if mood != "neutral" else ""
    return prefix + "; ".join(parts) if parts else ""
