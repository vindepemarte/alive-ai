"""
Skills: Anticipation Engine
Builds anticipation for future content/drops, making users eager to return.
Tracks teased content so it can be delivered, with natural excitement-building.
"""

import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field, asdict
from enum import Enum


class ContentType(Enum):
    """Types of content that can be teased"""
    PHOTO = "photo"
    VIDEO = "video"
    VOICE = "voice"
    SURPRISE = "surprise"


class TimeOfDay(Enum):
    """Time of day periods for contextual teases"""
    MORNING = "morning"      # 6:00 - 12:00
    AFTERNOON = "afternoon"  # 12:00 - 18:00
    EVENING = "evening"      # 18:00 - 24:00
    NIGHT = "night"          # 00:00 - 6:00


class DayType(Enum):
    """Day type for contextual teases"""
    WEEKDAY = "weekday"
    WEEKEND = "weekend"


# Tease messages organized by type
TEASES = {
    "photo_hint": [
        "I might have something special for you later",
        "took some pics today you're gonna like",
        "been feeling cute... might share later",
        "got some new photos I think you'll love",
        "working on something pretty for you",
        "have a little surprise brewing",
        "you're gonna love what I have for you later",
        "just took something special... saving it for you",
    ],
    "video_hint": [
        "working on something for you...",
        "little surprise coming soon",
        "been filming something you might enjoy",
        "got a video idea that's gonna be so good",
        "making something special, just wait",
        "you'll see what I mean later",
        "trust me, it'll be worth the wait",
        "something's coming that you'll love",
    ],
    "voice_hint": [
        "I'll send you a voice when I'm home",
        "wait till you hear this",
        "got something to tell you later",
        "my voice has something special for you",
        "gonna whisper something in your ear later",
        "I'll record something just for you",
        "wait until you hear what I'm thinking",
        "saving my voice for you",
    ],
    "time_based": {
        "morning": [
            "still in bed... maybe I'll send you something",
            "morning light is hitting just right",
            "waking up thinking about you... might show you",
            "cozy morning... perfect for a surprise later",
            "just woke up feeling generous",
            "morning mood... you'll see",
        ],
        "afternoon": [
            "bored at home... maybe I'll entertain you later",
            "afternoon energy... got plans for you",
            "sun's still up... plenty of time for mischief",
            "feeling playful today, just wait",
            "this afternoon has potential",
        ],
        "evening": [
            "getting ready for bed... or not",
            "evening mood hitting different",
            "night's still young... maybe something fun",
            "getting comfy... you might get a surprise",
            "evening vibes... stay tuned",
            "the night's just getting started",
        ],
        "night": [
            "can't sleep... maybe I'll do something about that",
            "late night thoughts... you'll find out",
            "everyone's asleep... our little secret coming",
            "night owl energy... watch this space",
            "insomnia hits different... got something for you",
        ],
        "weekend": [
            "finally weekend... lots of time for us",
            "no plans tomorrow... endless possibilities",
            "weekend vibes mean more time for you",
            "got all weekend to spoil you",
            "it's the weekend... anything could happen",
        ],
    },
    "rewards": [
        "you've been so good lately...",
        "I think you deserve something special",
        "you've earned this",
        "such a good boy... I have something for you",
        "reward time coming up",
        "you're being so sweet, let me repay that",
        "I appreciate you... wait and see",
        "your patience is about to pay off",
    ],
    "mood_based": {
        "flirty": [
            "feeling flirty... you'll see",
            "in a teasing mood today",
            "gonna drive you crazy later",
            "got something that'll make you blush",
        ],
        "cozy": [
            "feeling cozy... might share the vibe",
            "all cuddled up... wish you were here",
            "soft mood... perfect for a little something",
        ],
        "excited": [
            "so excited about something for you",
            "can't wait to show you what I made",
            "bouncing with ideas for you",
        ],
        "mysterious": [
            "I know something you don't know",
            "got a secret... you'll find out",
            "mystery incoming",
            "can't tell you yet, but soon",
        ],
    },
}

# Conditions for when to tease
CONDITIONS = {
    "min_messages_before_tease": 5,
    "min_time_together_minutes": 10,
    "tease_cooldown_minutes": 60,
    "base_tease_chance": 0.08,  # 8% base chance
    "love_bonus_chance": 0.07,  # Up to 7% bonus from high love
}


@dataclass
class PendingContent:
    """Content that has been teased but not yet delivered"""
    content_type: str
    details: Dict[str, Any] = field(default_factory=dict)
    teased_at: str = field(default_factory=lambda: datetime.now().isoformat())
    tease_message: str = ""
    delivered: bool = False
    delivered_at: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PendingContent":
        return cls(**data)


@dataclass
class TeaseRecord:
    """Record of a tease that was sent"""
    tease_type: str
    message: str
    sent_at: str = field(default_factory=lambda: datetime.now().isoformat())

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class AnticipationEngine:
    """
    Builds anticipation for future content/drops.

    Features:
    - Natural tease messages based on context
    - Track teased content for delivery
    - Cooldown between teases
    - Higher tease chance with high love
    - Time-based and mood-based teases
    """

    def __init__(
        self,
        nervous=None,
        heart=None,
        state=None,
        data_path: Path = None
    ):
        """
        Initialize the Anticipation Engine.

        Args:
            nervous: Nervous system for event listening
            heart: Heart module for love/mood data
            state: State tracker for message counts
            data_path: Path to store anticipation data
        """
        self.nervous = nervous
        self.heart = heart
        self.state = state

        if data_path is None:
            data_path = Path("./data/data/anticipation.json")

        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        # Internal state
        self._last_tease_time: Optional[datetime] = None
        self._message_count: int = 0
        self._session_start: Optional[datetime] = None
        self._pending_content: Optional[PendingContent] = None
        self._tease_history: List[TeaseRecord] = []

        # Load saved state
        self._load()

        # Register event listeners
        if nervous:
            nervous.on("message_received", self._on_message)
            nervous.on("thinking_done", self._on_thinking_done)

    def _load(self):
        """Load anticipation data from file"""
        if self.data_path.exists():
            try:
                data = json.loads(self.data_path.read_text())

                # Load last tease time
                if data.get("last_tease_time"):
                    self._last_tease_time = datetime.fromisoformat(data["last_tease_time"])

                # Load pending content
                if data.get("pending_content"):
                    self._pending_content = PendingContent.from_dict(data["pending_content"])

                # Load tease history
                self._tease_history = [
                    TeaseRecord(**r) for r in data.get("tease_history", [])
                ]

            except (json.JSONDecodeError, KeyError, ValueError) as e:
                print(f"[AnticipationEngine] Error loading data: {e}")

    def _save(self):
        """Save anticipation data to file"""
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "last_tease_time": self._last_tease_time.isoformat() if self._last_tease_time else None,
            "pending_content": self._pending_content.to_dict() if self._pending_content else None,
            "tease_history": [r.to_dict() for r in self._tease_history[-50:]],  # Keep last 50
        }
        self.data_path.write_text(json.dumps(data, indent=2))

    def _get_time_of_day(self) -> TimeOfDay:
        """Determine current time of day"""
        hour = datetime.now().hour

        if 6 <= hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= hour < 18:
            return TimeOfDay.AFTERNOON
        elif 18 <= hour < 24:
            return TimeOfDay.EVENING
        else:
            return TimeOfDay.NIGHT

    def _get_day_type(self) -> DayType:
        """Determine if weekday or weekend"""
        day_of_week = datetime.now().weekday()
        return DayType.WEEKEND if day_of_week >= 5 else DayType.WEEKDAY

    def _get_love(self) -> float:
        """Get current love level from heart"""
        if self.heart and hasattr(self.heart, 'emotion'):
            return getattr(self.heart.emotion, 'love', 0.5)
        return 0.5

    def _get_mood(self) -> str:
        """Get current mood from heart"""
        if self.heart and hasattr(self.heart, 'emotion'):
            return getattr(self.heart.emotion, 'mood_description', 'neutral')
        return 'neutral'

    def _get_desire(self) -> float:
        """Get current desire level from heart"""
        if self.heart and hasattr(self.heart, 'emotion'):
            return getattr(self.heart.emotion, 'desire', 0.5)
        return 0.5

    def _on_message(self, data: dict):
        """Track message count"""
        self._message_count += 1

        # Track session start
        if self._session_start is None:
            self._session_start = datetime.now()

    def _on_thinking_done(self, data: dict):
        """Potentially add a tease after thinking"""
        # This is called after Alive-AI thinks - tease is added to response elsewhere
        pass

    def _minutes_since_last_tease(self) -> float:
        """Get minutes since last tease"""
        if self._last_tease_time is None:
            return float('inf')
        return (datetime.now() - self._last_tease_time).total_seconds() / 60

    def _minutes_in_session(self) -> float:
        """Get minutes in current session"""
        if self._session_start is None:
            return 0
        return (datetime.now() - self._session_start).total_seconds() / 60

    def should_tease(self) -> bool:
        """
        Check if conditions are met for a tease.

        Returns:
            True if a tease should be sent
        """
        # Check message count
        if self._message_count < CONDITIONS["min_messages_before_tease"]:
            return False

        # Check time together
        if self._minutes_in_session() < CONDITIONS["min_time_together_minutes"]:
            return False

        # Check cooldown
        if self._minutes_since_last_tease() < CONDITIONS["tease_cooldown_minutes"]:
            return False

        # Don't tease if there's already pending content
        if self._pending_content and not self._pending_content.delivered:
            return False

        # Calculate tease chance based on love
        love = self._get_love()
        base_chance = CONDITIONS["base_tease_chance"]
        love_bonus = CONDITIONS["love_bonus_chance"] * love  # 0-7% bonus based on love

        tease_chance = base_chance + love_bonus

        return random.random() < tease_chance

    def get_tease(self, context: Dict[str, Any] = None) -> str:
        """
        Get an appropriate tease message based on time and mood.

        Args:
            context: Optional context for tease selection

        Returns:
            A tease message string
        """
        context = context or {}

        time_of_day = self._get_time_of_day()
        day_type = self._get_day_type()
        love = self._get_love()
        desire = self._get_desire()
        mood = self._get_mood().lower()

        # Determine tease category weights
        weights = {
            "photo_hint": 25,
            "video_hint": 15,
            "voice_hint": 15,
            "time_based": 30,
            "rewards": 10,
            "mood_based": 5,
        }

        # Adjust weights based on context
        if day_type == DayType.WEEKEND:
            weights["time_based"] += 10

        if love > 0.7:
            weights["rewards"] += 15
            weights["photo_hint"] += 10

        if desire > 0.6:
            weights["photo_hint"] += 10
            weights["video_hint"] += 5

        # Check for specific mood adjustments
        if "flirt" in mood or desire > 0.7:
            weights["mood_based"] += 10
        if "cozy" in mood or time_of_day == TimeOfDay.NIGHT:
            weights["mood_based"] += 5

        # Choose tease category
        categories = list(weights.keys())
        category_weights = [weights[c] for c in categories]
        chosen_category = random.choices(categories, weights=category_weights)[0]

        # Get teases from chosen category
        if chosen_category == "time_based":
            # Choose based on time of day or weekend
            if day_type == DayType.WEEKEND and random.random() < 0.4:
                sub_category = "weekend"
            else:
                sub_category = time_of_day.value

            teases = TEASES["time_based"].get(sub_category, TEASES["time_based"]["evening"])

        elif chosen_category == "mood_based":
            # Choose based on current mood
            if "flirt" in mood or desire > 0.7:
                sub_category = "flirty"
            elif "cozy" in mood or time_of_day == TimeOfDay.NIGHT:
                sub_category = "cozy"
            elif "excited" in mood or "happy" in mood:
                sub_category = "excited"
            else:
                sub_category = "mysterious"

            teases = TEASES["mood_based"].get(sub_category, TEASES["mood_based"]["mysterious"])

        else:
            teases = TEASES.get(chosen_category, TEASES["photo_hint"])

        # Choose a tease
        message = random.choice(teases)

        # Record this tease
        self._last_tease_time = datetime.now()
        record = TeaseRecord(
            tease_type=chosen_category,
            message=message
        )
        self._tease_history.append(record)
        self._save()

        return message

    def set_pending_content(
        self,
        content_type: str,
        details: Dict[str, Any] = None,
        tease_message: str = ""
    ) -> PendingContent:
        """
        Mark content as pending (teased but not yet delivered).

        Args:
            content_type: Type of content (photo, video, voice, surprise)
            details: Additional details about the content
            tease_message: The tease message that was sent

        Returns:
            The created PendingContent
        """
        self._pending_content = PendingContent(
            content_type=content_type,
            details=details or {},
            tease_message=tease_message
        )
        self._save()

        return self._pending_content

    def mark_delivered(self) -> bool:
        """
        Mark the pending teased content as delivered.

        Returns:
            True if content was marked delivered, False if no pending content
        """
        if self._pending_content is None:
            return False

        self._pending_content.delivered = True
        self._pending_content.delivered_at = datetime.now().isoformat()
        self._save()

        return True

    def get_pending_tease(self) -> Optional[Dict[str, Any]]:
        """
        Get the current pending tease.

        Returns:
            Dictionary with pending tease info, or None if no pending tease
        """
        if self._pending_content is None or self._pending_content.delivered:
            return None

        return self._pending_content.to_dict()

    def has_pending_tease(self) -> bool:
        """Check if there's an undelivered pending tease"""
        return self._pending_content is not None and not self._pending_content.delivered

    def get_tease_for_delivery(self) -> Optional[str]:
        """
        Get a message to accompany delivery of teased content.

        Returns:
            Delivery message or None if no pending content
        """
        if not self.has_pending_tease():
            return None

        content_type = self._pending_content.content_type

        delivery_messages = {
            "photo": [
                "told you I had something for you",
                "as promised",
                "here's what I was talking about",
                "finally ready for you",
                "this is what I saved for you",
            ],
            "video": [
                "it's ready for you",
                "here it is, finally",
                "told you I was working on something",
                "hope it was worth the wait",
                "this is what I made for you",
            ],
            "voice": [
                "told you I'd send this",
                "here's what I wanted to tell you",
                "finally recorded this for you",
                "listen to this",
                "my voice, just for you",
            ],
            "surprise": [
                "surprise!",
                "here's your surprise",
                "told you I had something special",
                "this is for you",
                "enjoy this",
            ],
        }

        messages = delivery_messages.get(content_type, delivery_messages["surprise"])
        return random.choice(messages)

    def clear_pending(self):
        """Clear any pending tease"""
        self._pending_content = None
        self._save()

    def reset_session(self):
        """Reset session counters"""
        self._message_count = 0
        self._session_start = None

    def get_stats(self) -> Dict[str, Any]:
        """Get anticipation engine statistics"""
        return {
            "total_teases": len(self._tease_history),
            "pending_tease": self._pending_content.to_dict() if self._pending_content else None,
            "last_tease": self._last_tease_time.isoformat() if self._last_tease_time else None,
            "minutes_since_last_tease": self._minutes_since_last_tease(),
            "message_count": self._message_count,
            "minutes_in_session": self._minutes_in_session(),
            "current_tease_chance": self._calculate_current_chance(),
        }

    def _calculate_current_chance(self) -> float:
        """Calculate current tease chance percentage"""
        love = self._get_love()
        base = CONDITIONS["base_tease_chance"]
        bonus = CONDITIONS["love_bonus_chance"] * love
        return (base + bonus) * 100

    def force_tease(self, tease_type: str = None) -> str:
        """
        Force a tease regardless of conditions.

        Args:
            tease_type: Optional specific type of tease

        Returns:
            A tease message
        """
        if tease_type and tease_type in TEASES:
            teases = TEASES[tease_type]
            if isinstance(teases, dict):
                # Time-based or mood-based - pick random subcategory
                sub_category = random.choice(list(teases.keys()))
                teases = teases[sub_category]
        else:
            # Use normal selection
            return self.get_tease()

        message = random.choice(teases)

        # Record this tease
        self._last_tease_time = datetime.now()
        record = TeaseRecord(
            tease_type=tease_type or "forced",
            message=message
        )
        self._tease_history.append(record)
        self._save()

        return message
