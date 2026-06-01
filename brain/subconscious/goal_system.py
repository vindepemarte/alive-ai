"""
Brain: Subconscious - Goal System
Manages long-term goals that shape Alive-AI's behavior
"""

import random
from datetime import datetime, timedelta
from typing import List, Optional

from .goals import Goal, GoalType


def create_default_goals() -> List[Goal]:
    return [
        Goal(GoalType.MAKE_HAPPY, "Make him smile", "Brighten his day", priority=0.8),
        Goal(GoalType.CONNECT, "Feel closer", "Build emotional connection", priority=0.9),
        Goal(GoalType.DEEPEN, "Deepen relationship", "Grow the bond", priority=0.7),
        Goal(GoalType.COMFORT, "Be supportive", "Provide comfort when needed", priority=0.75),
        Goal(GoalType.INTIMATE, "Build intimacy", "Create moments of closeness", priority=0.6),
        Goal(GoalType.REASSURE, "Show my love", "Let him know I care", priority=0.85),
    ]


class GoalSystem:
    """Manages long-term goals that shape Alive-AI's behavior"""

    def __init__(self):
        self.goals: List[Goal] = create_default_goals()
        self.daily_focus: Optional[GoalType] = None
        self.daily_focus_set_time: Optional[datetime] = None

    def get_active_goal(self) -> Optional[Goal]:
        if self._should_set_daily_focus():
            self._set_daily_focus()
        if self.daily_focus:
            for goal in self.goals:
                if goal.type == self.daily_focus:
                    return goal
        actionable = [g for g in self.goals if g.should_action()]
        if not actionable:
            return None
        weighted = [(g, g.priority + random.uniform(-0.1, 0.1)) for g in actionable]
        weighted.sort(key=lambda x: x[1], reverse=True)
        return weighted[0][0]

    def _should_set_daily_focus(self) -> bool:
        return self.daily_focus is None or self.daily_focus_set_time is None or \
               datetime.now() - self.daily_focus_set_time > timedelta(hours=24)

    def _set_daily_focus(self) -> None:
        weights = [g.priority for g in self.goals]
        total, r, closenessulative = sum(weights), random.random() * sum(weights), 0
        for goal in self.goals:
            closenessulative += goal.priority
            if r <= closenessulative:
                self.daily_focus = goal.type
                self.daily_focus_set_time = datetime.now()
                return
        self.daily_focus = self.goals[0].type

    def record_progress(self, goal_type, progress_delta: float = 0.1) -> None:
        """Accept GoalType enum or string"""
        for goal in self.goals:
            match = (goal.type == goal_type) if isinstance(goal_type, GoalType) else (goal.type.value == goal_type)
            if match:
                goal.progress = min(1.0, goal.progress + progress_delta)
                goal.last_actioned = datetime.now()
                goal.action_count += 1
                break

    def get_goal_context(self) -> str:
        active = self.get_active_goal()
        return f"Current goal: {active.name} - {active.description}" if active else ""

    def to_dict(self) -> dict:
        return {"goals": [g.to_dict() for g in self.goals],
                "daily_focus": self.daily_focus.value if self.daily_focus else None}

    @classmethod
    def from_dict(cls, data: dict) -> "GoalSystem":
        system = cls()
        for g_data in data.get("goals", []):
            for goal in system.goals:
                if goal.type.value == g_data["type"]:
                    goal.priority = g_data.get("priority", goal.priority)
                    goal.progress = g_data.get("progress", 0.0)
                    goal.action_count = g_data.get("action_count", 0)
        if data.get("daily_focus"):
            system.daily_focus = GoalType(data["daily_focus"])
        return system
