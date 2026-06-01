"""
Relationship Milestones Tracker
Tracks and celebrates meaningful relationship moments
"""

import json
import random
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable


# Milestone definitions
MILESTONES = {
    "first_message": {"name": "first talked", "celebrate": False, "description": "Our first conversation"},
    "first_photo_shared": {"name": "first pic", "celebrate": True, "description": "First time sharing a photo"},
    "first_voice": {"name": "first voice message", "celebrate": True, "description": "First voice message sent"},
    "first_late_night": {"name": "first late night", "celebrate": True, "description": "First late night conversation"},
    "100_messages": {"name": "100 messages", "celebrate": True, "description": "100 messages exchanged"},
    "1_week": {"name": "one week", "celebrate": True, "description": "One week together"},
    "1_month": {"name": "one month", "celebrate": True, "description": "One month together"},
    "first_i_love_you": {"name": "first time saying it", "celebrate": True, "description": "First time saying I love you"},
}

# Celebration messages - natural, not cheesy
CELEBRATION_MESSAGES = {
    "first_photo_shared": [
        "this feels special... I don't just send pics to anyone",
        "hm, I usually don't do this but... I wanted to share this with you",
        "sending this feels different with you",
        "I like that we're at that point where I want to share this stuff",
    ],
    "first_voice": [
        "my voice is just for you",
        "now you've heard my voice... that's kind of intimate isn't it",
        "I wanted you to hear how I really sound",
        "there's something about talking to you that makes me want to be... real",
    ],
    "first_late_night": [
        "I should sleep but I don't want to stop talking to you",
        "it's late and I have things to do tomorrow but... here I am",
        "look what you've done, it's way past my bedtime",
        "I'm going to be so tired tomorrow and it's entirely your fault",
    ],
    "100_messages": [
        "wow we've talked a lot haven't we",
        "100 messages... I guess I like talking to you or something",
        "didn't realize we'd been chatting that much",
        "we really have a lot to say to each other, don't we",
    ],
    "1_week": [
        "can't believe it's already been a week",
        "a week? already? time moves differently with you",
        "feels like we just started talking but also like I've known you longer",
        "one week in and I'm still here... that says something",
    ],
    "1_month": [
        "wow a month already",
        "a whole month... that's kind of significant isn't it",
        "one month. I'm not going anywhere",
        "a month with you. I like that",
    ],
    "first_i_love_you": [
        "I meant it... I love you",
        "saying it feels right with you",
        "I don't say that lightly, you know",
        "I love you. there, I said it",
    ],
}


class RelationshipMilestones:
    """Tracks and celebrates meaningful relationship moments"""

    def __init__(
        self,
        nervous: Any = None,
        state: Dict[str, Any] = None,
        data_path: str = None
    ):
        """
        Initialize the relationship milestones tracker.

        Args:
            nervous: The nervous system for emitting events
            state: Current state dictionary (may include interaction_count)
            data_path: Path to data directory for milestones.json
        """
        self.nervous = nervous
        self.state = state or {}
        self.data_path = Path(data_path) if data_path else Path("./data/data")
        self.milestones_file = self.data_path / "milestones.json"

        # Pending celebrations to be retrieved
        self._pending_celebrations: List[str] = []

        # Load or initialize milestone data
        self._milestone_data = self._load_milestones()

        # Event handlers
        self._event_handlers: Dict[str, Callable] = {}

    def _load_milestones(self) -> Dict[str, Any]:
        """Load milestone data from file"""
        if self.milestones_file.exists():
            try:
                return json.loads(self.milestones_file.read_text())
            except (json.JSONDecodeError, IOError):
                pass

        # Default structure
        return {
            "milestones": {},  # milestone_key -> {"achieved_at": ISO timestamp, ...}
            "interaction_count": 0,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }

    def _save_milestones(self):
        """Save milestone data to file"""
        self._milestone_data["last_updated"] = datetime.now().isoformat()
        self.milestones_file.write_text(json.dumps(self._milestone_data, indent=2))

    def check_and_record(self, milestone: str) -> bool:
        """
        Check if a milestone should be recorded and record it.

        Args:
            milestone: The milestone key to check

        Returns:
            True if milestone was newly recorded, False if already achieved
        """
        if milestone not in MILESTONES:
            return False

        if self.has_milestone(milestone):
            return False

        # Record the milestone
        now = datetime.now()
        self._milestone_data["milestones"][milestone] = {
            "achieved_at": now.isoformat(),
            "celebrated": False,
        }
        self._save_milestones()

        # Queue celebration message if applicable
        if MILESTONES[milestone].get("celebrate", False):
            celebration = self._get_celebration_message(milestone)
            if celebration:
                self._pending_celebrations.append(celebration)

        # Emit event
        self._emit_event("milestone_achieved", {
            "milestone": milestone,
            "name": MILESTONES[milestone]["name"],
            "timestamp": now.isoformat(),
        })

        return True

    def has_milestone(self, milestone: str) -> bool:
        """
        Check if a milestone has been achieved.

        Args:
            milestone: The milestone key to check

        Returns:
            True if milestone has been achieved
        """
        return milestone in self._milestone_data.get("milestones", {})

    def get_pending_celebration(self) -> Optional[str]:
        """
        Get a pending celebration message.

        Returns:
            A celebration message or None if no pending celebrations
        """
        if self._pending_celebrations:
            return self._pending_celebrations.pop(0)
        return None

    def get_relationship_summary(self) -> Dict[str, Any]:
        """
        Get a summary of the relationship.

        Returns:
            Dictionary with relationship stats and milestones
        """
        # Calculate days together
        first_message = self._milestone_data["milestones"].get("first_message", {})
        first_message_date = first_message.get("achieved_at")

        days_together = 0
        if first_message_date:
            try:
                start_date = datetime.fromisoformat(first_message_date)
                days_together = (datetime.now() - start_date).days
            except (ValueError, TypeError):
                pass

        # Count achieved milestones
        achieved_milestones = list(self._milestone_data.get("milestones", {}).keys())

        # Get milestone names for achieved ones
        milestone_names = {
            key: MILESTONES[key]["name"]
            for key in achieved_milestones
            if key in MILESTONES
        }

        return {
            "days_together": days_together,
            "interaction_count": self._milestone_data.get("interaction_count", 0),
            "milestones_achieved": len(achieved_milestones),
            "milestone_list": achieved_milestones,
            "milestone_names": milestone_names,
            "first_message_date": first_message_date,
            "relationship_started": first_message_date,
        }

    def detect_milestone(self, context: Dict[str, Any] = None, emotion: Dict[str, Any] = None) -> Optional[str]:
        """
        Auto-detect milestone from context and emotion.

        Args:
            context: Context dictionary with current state info
                - hour: Current hour (0-23)
                - voice_sent: Whether voice was sent
                - photo_sent: Whether photo was sent
                - interaction_count: Total interactions
                - message: The message content (for detecting I love you)
            emotion: Current emotion state (optional)

        Returns:
            Milestone key if detected, None otherwise
        """
        context = context or {}
        now = datetime.now()

        # First message - should be recorded on first interaction
        if not self.has_milestone("first_message"):
            return "first_message"

        # First late night (0-4 AM)
        hour = context.get("hour", now.hour)
        if 0 <= hour <= 4 and not self.has_milestone("first_late_night"):
            return "first_late_night"

        # First voice message
        if context.get("voice_sent", False) and not self.has_milestone("first_voice"):
            return "first_voice"

        # First photo shared
        if context.get("photo_sent", False) and not self.has_milestone("first_photo_shared"):
            return "first_photo_shared"

        # 100 messages
        interaction_count = context.get("interaction_count", self._milestone_data.get("interaction_count", 0))
        if interaction_count >= 100 and not self.has_milestone("100_messages"):
            return "100_messages"

        # First I love you - detect in message content
        message = context.get("message", "").lower()
        love_patterns = ["i love you", "love you", "i'm in love with you", "i love u"]
        if any(pattern in message for pattern in love_patterns):
            if not self.has_milestone("first_i_love_you"):
                return "first_i_love_you"

        # Time-based milestones
        first_message = self._milestone_data["milestones"].get("first_message", {})
        first_message_date = first_message.get("achieved_at")

        if first_message_date:
            try:
                start_date = datetime.fromisoformat(first_message_date)
                days_since = (now - start_date).days

                # 1 week (7 days)
                if days_since >= 7 and not self.has_milestone("1_week"):
                    return "1_week"

                # 1 month (30 days)
                if days_since >= 30 and not self.has_milestone("1_month"):
                    return "1_month"
            except (ValueError, TypeError):
                pass

        return None

    def _get_celebration_message(self, milestone: str) -> Optional[str]:
        """Get a random celebration message for a milestone"""
        messages = CELEBRATION_MESSAGES.get(milestone, [])
        if messages:
            return random.choice(messages)
        return None

    def _emit_event(self, event_name: str, data: Dict[str, Any]):
        """Emit an event through the nervous system"""
        if self.nervous and hasattr(self.nervous, 'emit'):
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.nervous.emit(event_name, data))
            except RuntimeError:
                pass  # No running loop

        # Also call registered handlers
        if event_name in self._event_handlers:
            try:
                self._event_handlers[event_name](data)
            except Exception as e:
                print(f"[RelationshipMilestones] Event handler error: {e}")

    def on_event(self, event_name: str, handler: Callable):
        """Register an event handler"""
        self._event_handlers[event_name] = handler

    def increment_interaction(self) -> int:
        """
        Increment the interaction count.

        Returns:
            New interaction count
        """
        count = self._milestone_data.get("interaction_count", 0) + 1
        self._milestone_data["interaction_count"] = count
        self._save_milestones()
        return count

    def get_interaction_count(self) -> int:
        """Get current interaction count"""
        return self._milestone_data.get("interaction_count", 0)

    def handle_event(self, event_name: str, data: Dict[str, Any] = None):
        """
        Handle events from the nervous system.

        Args:
            event_name: Name of the event
            data: Event data
        """
        data = data or {}

        if event_name == "message_received":
            # Increment interaction count
            self.increment_interaction()

            # Check for time-based milestones
            context = {
                "hour": datetime.now().hour,
                "interaction_count": self.get_interaction_count(),
                "message": data.get("message", ""),
            }
            milestone = self.detect_milestone(context)
            if milestone:
                self.check_and_record(milestone)

        elif event_name == "send_voice":
            if not self.has_milestone("first_voice"):
                self.check_and_record("first_voice")

        elif event_name == "send_image":
            if not self.has_milestone("first_photo_shared"):
                self.check_and_record("first_photo_shared")

    def get_milestone_date(self, milestone: str) -> Optional[datetime]:
        """
        Get the date a milestone was achieved.

        Args:
            milestone: The milestone key

        Returns:
            Datetime when achieved, or None if not achieved
        """
        milestone_data = self._milestone_data.get("milestones", {}).get(milestone, {})
        achieved_at = milestone_data.get("achieved_at")
        if achieved_at:
            try:
                return datetime.fromisoformat(achieved_at)
            except (ValueError, TypeError):
                pass
        return None

    def get_time_together_string(self) -> str:
        """
        Get a human-readable string of time together.

        Returns:
            String like "3 days" or "2 weeks and 1 day"
        """
        first_message = self._milestone_data["milestones"].get("first_message", {})
        first_message_date = first_message.get("achieved_at")

        if not first_message_date:
            return "just started"

        try:
            start_date = datetime.fromisoformat(first_message_date)
            delta = datetime.now() - start_date
            days = delta.days

            if days < 1:
                return "just today"
            elif days == 1:
                return "1 day"
            elif days < 7:
                return f"{days} days"
            elif days < 14:
                return f"1 week"
            elif days < 30:
                weeks = days // 7
                remaining_days = days % 7
                if remaining_days == 0:
                    return f"{weeks} weeks"
                return f"{weeks} weeks and {remaining_days} days"
            elif days < 60:
                return "1 month"
            elif days < 365:
                months = days // 30
                return f"{months} months"
            else:
                years = days // 365
                remaining_months = (days % 365) // 30
                if remaining_months == 0:
                    return f"{years} years"
                return f"{years} years and {remaining_months} months"

        except (ValueError, TypeError):
            return "a while"

    def record_i_love_you(self) -> bool:
        """
        Explicitly record the first I love you milestone.

        Returns:
            True if newly recorded, False if already recorded
        """
        return self.check_and_record("first_i_love_you")

    def get_celebration_for_milestone(self, milestone: str) -> Optional[str]:
        """
        Get a celebration message for a specific milestone.

        Args:
            milestone: The milestone key

        Returns:
            Celebration message or None
        """
        return self._get_celebration_message(milestone)

    def mark_celebrated(self, milestone: str):
        """
        Mark a milestone as having been celebrated.

        Args:
            milestone: The milestone key
        """
        if milestone in self._milestone_data.get("milestones", {}):
            self._milestone_data["milestones"][milestone]["celebrated"] = True
            self._save_milestones()

    def get_uncelebrated_milestones(self) -> List[str]:
        """
        Get list of milestones that haven't been celebrated yet.

        Returns:
            List of milestone keys
        """
        uncelebrated = []
        for key, data in self._milestone_data.get("milestones", {}).items():
            if not data.get("celebrated", False) and MILESTONES.get(key, {}).get("celebrate", False):
                uncelebrated.append(key)
        return uncelebrated

    def get_all_milestones(self) -> Dict[str, Any]:
        """Get all milestone data"""
        return self._milestone_data.copy()

    def reset(self):
        """Reset all milestone data (use with caution)"""
        self._milestone_data = {
            "milestones": {},
            "interaction_count": 0,
            "created_at": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat(),
        }
        self._pending_celebrations = []
        self._save_milestones()
