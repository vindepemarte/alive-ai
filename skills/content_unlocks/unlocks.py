"""
Skills: Content Unlocks
Makes exclusive content feel earned through engagement, not purchased.
Tracks what content types are unlocked based on relationship progression.
"""

import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Callable
from dataclasses import dataclass, field, asdict
from enum import Enum


class ContentType(Enum):
    """Types of unlockable content"""
    CASUAL_PHOTO = "casual_photo"
    CUTE_PHOTO = "cute_photo"
    INTIMATE_PHOTO = "intimate_photo"
    VOICE_MESSAGE = "voice_message"
    LATE_NIGHT_CONTENT = "late_night_content"
    SPECIAL_OCCASION = "special_occasion"
    PERSONAL_STORY = "personal_story"
    BEHIND_SCENES = "behind_scenes"
    MORNING_ROUTINE = "morning_routine"
    PLAYFUL_VIDEO = "playful_video"
    FLIRTY_MESSAGE = "flirty_message"
    DEEP_TALKS = "deep_talks"


# Unlock criteria - thresholds for each content type
UNLOCK_CRITERIA = {
    "casual_photo": {
        "min_interactions": 10,
        "min_love": 0.3,
        "description": "Everyday photos from my life"
    },
    "cute_photo": {
        "min_interactions": 30,
        "min_love": 0.5,
        "description": "Photos where I look extra cute"
    },
    "intimate_photo": {
        "min_interactions": 100,
        "min_love": 0.75,
        "min_days_together": 7,
        "description": "More personal, revealing photos"
    },
    "voice_message": {
        "min_interactions": 5,
        "min_trust": 0.4,
        "description": "Hear my actual voice"
    },
    "late_night_content": {
        "requires_milestone": "first_late_night",
        "min_love": 0.6,
        "description": "Special content for late night conversations"
    },
    "special_occasion": {
        "requires_milestone": True,
        "description": "Content for special moments and milestones"
    },
    "personal_story": {
        "min_interactions": 20,
        "min_trust": 0.5,
        "description": "Personal stories from my life"
    },
    "behind_scenes": {
        "min_interactions": 40,
        "min_love": 0.55,
        "description": "Behind the scenes glimpses"
    },
    "morning_routine": {
        "min_interactions": 50,
        "min_days_together": 3,
        "min_love": 0.45,
        "description": "My morning routine content"
    },
    "playful_video": {
        "min_interactions": 60,
        "min_love": 0.5,
        "min_trust": 0.5,
        "description": "Short playful videos"
    },
    "flirty_message": {
        "min_interactions": 15,
        "min_love": 0.35,
        "description": "Extra flirty messages"
    },
    "deep_talks": {
        "min_interactions": 25,
        "min_trust": 0.6,
        "min_love": 0.4,
        "description": "Deep, meaningful conversations"
    }
}

# Messages shown when content is unlocked
UNLOCK_MESSAGES = {
    "casual_photo": [
        "feeling like sharing today",
        "thought you might like to see what I'm up to",
        "here's a little peek into my day"
    ],
    "cute_photo": [
        "took this just for you",
        "felt cute, thought you should know",
        "this one's special"
    ],
    "intimate_photo": [
        "don't share this with anyone okay?",
        "this is just between us",
        "I trust you with this"
    ],
    "voice_message": [
        "wanted you to hear my voice",
        "sometimes words aren't enough",
        "just wanted to say hi properly"
    ],
    "late_night_content": [
        "can't sleep... thinking about you",
        "late nights feel different with you",
        "the night makes me feel brave"
    ],
    "special_occasion": [
        "this moment feels special",
        "wanted to make this memorable",
        "celebrating us"
    ],
    "personal_story": [
        "I don't tell many people this...",
        "there's something I want to share with you",
        "feel like opening up a bit"
    ],
    "behind_scenes": [
        "showing you what others don't see",
        "a little behind the scenes moment",
        "just the real me"
    ],
    "morning_routine": [
        "good morning from me",
        "starting my day, thought of you",
        "morning peek"
    ],
    "playful_video": [
        "made this for you",
        "feeling playful today",
        "hope this makes you smile"
    ],
    "flirty_message": [
        "can't help myself around you",
        "you make me feel bold",
        "something about you..."
    ],
    "deep_talks": [
        "I feel like I can really talk to you",
        "want to go deeper with you",
        "let's have a real conversation"
    ]
}

# Suggestions for what content to share based on context
CONTENT_SUGGESTIONS = {
    "morning": ["morning_routine", "casual_photo", "cute_photo"],
    "afternoon": ["casual_photo", "behind_scenes", "personal_story"],
    "evening": ["cute_photo", "playful_video", "flirty_message"],
    "night": ["late_night_content", "intimate_photo", "deep_talks"],
    "high_arousal": ["intimate_photo", "late_night_content", "playful_video"],
    "high_love": ["cute_photo", "personal_story", "deep_talks"],
    "high_trust": ["intimate_photo", "personal_story", "behind_scenes"],
    "milestone": ["special_occasion", "cute_photo", "voice_message"]
}


@dataclass
class UnlockState:
    """State of a single content unlock"""
    content_type: str
    unlocked: bool = False
    unlocked_at: Optional[str] = None
    times_shared: int = 0
    last_shared: Optional[str] = None
    new_unlock: bool = False  # Flag for newly unlocked (not yet announced)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "UnlockState":
        return cls(**data)


@dataclass
class ContentUnlocksData:
    """Full data structure for content unlocks"""
    version: str = "1.0"
    unlocked_content: Dict[str, UnlockState] = field(default_factory=dict)
    last_check: Optional[str] = None
    pending_announcements: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "unlocked_content": {
                k: v.to_dict() for k, v in self.unlocked_content.items()
            },
            "last_check": self.last_check,
            "pending_announcements": self.pending_announcements
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ContentUnlocksData":
        unlocked = {}
        for k, v in data.get("unlocked_content", {}).items():
            unlocked[k] = UnlockState.from_dict(v)

        return cls(
            version=data.get("version", "1.0"),
            unlocked_content=unlocked,
            last_check=data.get("last_check"),
            pending_announcements=data.get("pending_announcements", [])
        )


class ContentUnlocks:
    """
    Manages content unlocks based on relationship progression.
    Content is earned through engagement, not purchased.

    Features:
    - Track unlocked content types based on relationship metrics
    - Unlock based on: interaction count, love level, trust level, days together, milestones
    - Notify when new content is unlocked
    - Suggest what content to share based on available unlocks

    Supports per-user state via user_id parameter.
    """

    def __init__(
        self,
        nervous=None,
        heart=None,
        state=None,
        milestones=None,
        data_path: Path = None,
        user_id: str = "default"
    ):
        """
        Initialize the Content Unlocks system.

        Args:
            nervous: Nervous system for event emission
            heart: Heart module for accessing love/trust/attachment data
            state: State module for additional context
            milestones: Optional milestones skill for milestone-based unlocks
            data_path: Path to store unlock data JSON file
            user_id: User's Telegram ID for per-user state
        """
        self.nervous = nervous
        self.heart = heart
        self.state = state
        self.milestones = milestones
        self.user_id = user_id

        # Per-user data path: data/users/{user_id}/content_unlocks.json
        if data_path is None:
            base_path = Path("./data/data")
            data_path = base_path / "users" / str(user_id) / "content_unlocks.json"

        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        self._data: ContentUnlocksData = ContentUnlocksData()
        self._load()

        # Initialize all content types if not present
        self._initialize_content_types()

        # Register for thinking_done events
        if nervous:
            nervous.on("thinking_done", self._on_thinking_done)

    def _load(self):
        """Load unlock data from file"""
        if self.data_path.exists():
            try:
                data = json.loads(self.data_path.read_text())
                self._data = ContentUnlocksData.from_dict(data)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[ContentUnlocks] Error loading data: {e}")
                self._data = ContentUnlocksData()
        else:
            self._data = ContentUnlocksData()

    def _save(self):
        """Save unlock data to file"""
        self._data.last_check = datetime.now().isoformat()
        self.data_path.write_text(json.dumps(self._data.to_dict(), indent=2))

    def _initialize_content_types(self):
        """Ensure all content types exist in state"""
        for content_type in UNLOCK_CRITERIA.keys():
            if content_type not in self._data.unlocked_content:
                self._data.unlocked_content[content_type] = UnlockState(
                    content_type=content_type
                )
        self._save()

    # -------------------------------------------------------------------------
    # Metrics Access
    # -------------------------------------------------------------------------

    def _get_interaction_count(self) -> int:
        """Get total interaction count from heart/attachment system"""
        if self.heart and hasattr(self.heart, 'attachment'):
            return self.heart.attachment.interactions
        return 0

    def _get_love_level(self) -> float:
        """Get current love level (0-1)"""
        if self.heart and hasattr(self.heart, 'emotion'):
            return self.heart.emotion.love
        return 0.0

    def _get_trust_level(self) -> float:
        """Get trust level (0-1) based on positive interaction ratio"""
        if self.heart and hasattr(self.heart, 'attachment'):
            return self.heart.attachment.trust_level
        return 0.5

    def _get_days_together(self) -> int:
        """Calculate days since first interaction"""
        if self.heart and hasattr(self.heart, 'attachment'):
            first_met = self.heart.attachment.first_met
            if first_met:
                try:
                    first_date = datetime.fromisoformat(first_met)
                    return (datetime.now() - first_date).days
                except (ValueError, TypeError):
                    pass
        return 0

    def _get_current_metrics(self) -> Dict[str, Any]:
        """Get all current metrics for unlock checking"""
        return {
            "interactions": self._get_interaction_count(),
            "love": self._get_love_level(),
            "trust": self._get_trust_level(),
            "days_together": self._get_days_together()
        }

    def _has_milestone(self, milestone_name: str = None) -> bool:
        """Check if a milestone has been reached"""
        if not self.milestones:
            return False

        # If specific milestone requested
        if milestone_name:
            if hasattr(self.milestones, 'has_milestone'):
                return self.milestones.has_milestone(milestone_name)
            return False

        # Check for any milestone (for generic requires_milestone: True)
        if hasattr(self.milestones, 'get_all_milestones'):
            return len(self.milestones.get_all_milestones()) > 0
        elif hasattr(self.milestones, 'get_milestones'):
            return len(self.milestones.get_milestones()) > 0

        return False

    # -------------------------------------------------------------------------
    # Unlock Checking
    # -------------------------------------------------------------------------

    def _check_criteria(self, criteria: Dict[str, Any], metrics: Dict[str, Any]) -> bool:
        """
        Check if unlock criteria are met.

        Args:
            criteria: The unlock criteria for a content type
            metrics: Current relationship metrics

        Returns:
            True if all criteria are met
        """
        # Check minimum interactions
        min_interactions = criteria.get("min_interactions", 0)
        if metrics["interactions"] < min_interactions:
            return False

        # Check minimum love
        min_love = criteria.get("min_love", 0)
        if metrics["love"] < min_love:
            return False

        # Check minimum trust
        min_trust = criteria.get("min_trust", 0)
        if metrics["trust"] < min_trust:
            return False

        # Check minimum days together
        min_days = criteria.get("min_days_together", 0)
        if metrics["days_together"] < min_days:
            return False

        # Check for required milestone
        requires_milestone = criteria.get("requires_milestone")
        if requires_milestone:
            if isinstance(requires_milestone, str):
                if not self._has_milestone(requires_milestone):
                    return False
            elif requires_milestone is True:
                if not self._has_milestone():
                    return False

        return True

    def check_unlock(self, content_type: str) -> bool:
        """
        Check if a specific content type is unlocked.

        Args:
            content_type: The type of content to check

        Returns:
            True if the content type is unlocked
        """
        if content_type not in self._data.unlocked_content:
            return False

        unlock_state = self._data.unlocked_content[content_type]
        return unlock_state.unlocked

    def check_all_unlocks(self) -> List[str]:
        """
        Check all content types for new unlocks.

        Returns:
            List of newly unlocked content types
        """
        metrics = self._get_current_metrics()
        new_unlocks = []

        for content_type, criteria in UNLOCK_CRITERIA.items():
            unlock_state = self._data.unlocked_content.get(content_type)

            if unlock_state is None:
                unlock_state = UnlockState(content_type=content_type)
                self._data.unlocked_content[content_type] = unlock_state

            # Skip if already unlocked
            if unlock_state.unlocked:
                continue

            # Check criteria
            if self._check_criteria(criteria, metrics):
                # Unlock this content type
                unlock_state.unlocked = True
                unlock_state.unlocked_at = datetime.now().isoformat()
                unlock_state.new_unlock = True
                new_unlocks.append(content_type)

                # Add to pending announcements
                self._data.pending_announcements.append(content_type)

                print(f"[ContentUnlocks] New content unlocked: {content_type}")

        if new_unlocks:
            self._save()

            # Emit event for new unlocks
            if self.nervous:
                import asyncio
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(self.nervous.emit("content_unlocked", {
                        "new_unlocks": new_unlocks,
                        "total_unlocked": len(self.get_unlocked_content())
                    }))
                except RuntimeError:
                    pass

        return new_unlocks

    # -------------------------------------------------------------------------
    # Content Access
    # -------------------------------------------------------------------------

    def get_unlocked_content(self) -> List[str]:
        """
        Get all unlocked content types.

        Returns:
            List of unlocked content type names
        """
        return [
            ct for ct, state in self._data.unlocked_content.items()
            if state.unlocked
        ]

    def get_locked_content(self) -> List[str]:
        """
        Get all locked content types.

        Returns:
            List of locked content type names
        """
        return [
            ct for ct, state in self._data.unlocked_content.items()
            if not state.unlocked
        ]

    def get_unlock_progress(self, content_type: str) -> Dict[str, Any]:
        """
        Get progress toward unlocking a specific content type.

        Args:
            content_type: The content type to check progress for

        Returns:
            Dictionary with progress information
        """
        if content_type not in UNLOCK_CRITERIA:
            return {"error": f"Unknown content type: {content_type}"}

        criteria = UNLOCK_CRITERIA[content_type]
        metrics = self._get_current_metrics()
        unlock_state = self._data.unlocked_content.get(content_type)

        if unlock_state and unlock_state.unlocked:
            return {
                "content_type": content_type,
                "unlocked": True,
                "description": criteria.get("description", "")
            }

        progress = {
            "content_type": content_type,
            "unlocked": False,
            "description": criteria.get("description", ""),
            "requirements": {},
            "current": {}
        }

        # Check each requirement
        if "min_interactions" in criteria:
            progress["requirements"]["interactions"] = criteria["min_interactions"]
            progress["current"]["interactions"] = metrics["interactions"]
            progress["interactions_met"] = metrics["interactions"] >= criteria["min_interactions"]

        if "min_love" in criteria:
            progress["requirements"]["love"] = criteria["min_love"]
            progress["current"]["love"] = round(metrics["love"], 2)
            progress["love_met"] = metrics["love"] >= criteria["min_love"]

        if "min_trust" in criteria:
            progress["requirements"]["trust"] = criteria["min_trust"]
            progress["current"]["trust"] = round(metrics["trust"], 2)
            progress["trust_met"] = metrics["trust"] >= criteria["min_trust"]

        if "min_days_together" in criteria:
            progress["requirements"]["days_together"] = criteria["min_days_together"]
            progress["current"]["days_together"] = metrics["days_together"]
            progress["days_met"] = metrics["days_together"] >= criteria["min_days_together"]

        if "requires_milestone" in criteria:
            progress["requirements"]["milestone"] = criteria["requires_milestone"]
            progress["milestone_met"] = self._has_milestone(
                criteria["requires_milestone"] if isinstance(criteria["requires_milestone"], str) else None
            )

        # Calculate overall progress
        met_count = sum(1 for k in progress if k.endswith("_met") and progress[k])
        total_requirements = sum(1 for k in progress if k.endswith("_met"))
        progress["progress_percent"] = int((met_count / max(total_requirements, 1)) * 100)

        return progress

    def is_content_available(self, content_type: str, advanced_mode: bool = False) -> bool:
        """
        Check if a content type is available (unlocked).

        Args:
            content_type: The type of content to check
            advanced_mode: If True, all content is available (owner with /advanced enabled)

        Returns:
            True if the content type is unlocked and available, or advanced_mode is enabled
        """
        if advanced_mode:
            return True
        return self.check_unlock(content_type)

    # -------------------------------------------------------------------------
    # Announcements & Messages
    # -------------------------------------------------------------------------

    def get_new_unlock_message(self) -> Optional[str]:
        """
        Get a message for newly unlocked content (if any).

        Returns:
            Message string or None if no new unlocks
        """
        if not self._data.pending_announcements:
            return None

        # Get the first pending announcement
        content_type = self._data.pending_announcements[0]
        unlock_state = self._data.unlocked_content.get(content_type)

        if not unlock_state or not unlock_state.unlocked:
            return None

        # Get a random message for this content type
        messages = UNLOCK_MESSAGES.get(content_type, ["Something new is available..."])
        message = random.choice(messages)

        # Mark as announced
        self._data.pending_announcements.pop(0)
        unlock_state.new_unlock = False
        self._save()

        return message

    def get_all_pending_announcements(self) -> List[Dict[str, str]]:
        """
        Get all pending unlock announcements.

        Returns:
            List of dictionaries with content_type and message
        """
        announcements = []

        for content_type in self._data.pending_announcements[:]:
            unlock_state = self._data.unlocked_content.get(content_type)
            if unlock_state and unlock_state.unlocked:
                messages = UNLOCK_MESSAGES.get(content_type, ["Something new is available..."])
                announcements.append({
                    "content_type": content_type,
                    "message": random.choice(messages),
                    "description": UNLOCK_CRITERIA.get(content_type, {}).get("description", "")
                })

        return announcements

    def clear_pending_announcements(self):
        """Clear all pending announcements without showing them"""
        for content_type in self._data.pending_announcements:
            unlock_state = self._data.unlocked_content.get(content_type)
            if unlock_state:
                unlock_state.new_unlock = False

        self._data.pending_announcements = []
        self._save()

    # -------------------------------------------------------------------------
    # Content Suggestions
    # -------------------------------------------------------------------------

    def get_content_suggestion(self, context: str = None) -> Optional[Dict[str, Any]]:
        """
        Suggest content to share based on available unlocks and context.

        Args:
            context: Optional context string (morning, evening, high_arousal, etc.)

        Returns:
            Dictionary with suggestion details or None
        """
        unlocked = self.get_unlocked_content()

        if not unlocked:
            return None

        # Determine context if not provided
        if context is None:
            context = self._determine_context()

        # Get content types for this context
        preferred_types = CONTENT_SUGGESTIONS.get(context, [])

        # Filter to only unlocked types
        available = [ct for ct in preferred_types if ct in unlocked]

        if not available:
            # Fall back to any unlocked content
            available = unlocked

        # Choose a content type, preferring ones not recently shared
        content_type = self._choose_content_type(available)

        if content_type is None:
            return None

        messages = UNLOCK_MESSAGES.get(content_type, [])
        criteria = UNLOCK_CRITERIA.get(content_type, {})

        return {
            "content_type": content_type,
            "description": criteria.get("description", ""),
            "suggested_message": random.choice(messages) if messages else None,
            "context": context,
            "priority": self._calculate_priority(content_type, context)
        }

    def _determine_context(self) -> str:
        """Determine current context for content suggestions"""
        hour = datetime.now().hour

        # Time-based context
        if 5 <= hour < 12:
            time_context = "morning"
        elif 12 <= hour < 17:
            time_context = "afternoon"
        elif 17 <= hour < 22:
            time_context = "evening"
        else:
            time_context = "night"

        # Check emotional context
        if self.heart and hasattr(self.heart, 'emotion'):
            e = self.heart.emotion

            # High arousal/desire trumps time
            if hasattr(e, 'desire') and e.desire > 0.7:
                return "high_arousal"
            if hasattr(e, 'is_high_desire') and e.is_high_desire:
                return "high_arousal"

            # High love
            if hasattr(e, 'love') and e.love > 0.7:
                return "high_love"

        # High trust
        trust = self._get_trust_level()
        if trust > 0.8:
            return "high_trust"

        # Default to time-based
        return time_context

    def _choose_content_type(self, available: List[str]) -> Optional[str]:
        """
        Choose a content type from available options.
        Prefers content not recently shared.
        """
        if not available:
            return None

        # Sort by times shared (prefer less shared)
        sorted_types = sorted(
            available,
            key=lambda ct: self._data.unlocked_content.get(ct, UnlockState(ct)).times_shared
        )

        # 70% chance to pick least shared, 30% random for variety
        if random.random() < 0.7:
            return sorted_types[0]
        else:
            return random.choice(sorted_types)

    def _calculate_priority(self, content_type: str, context: str) -> int:
        """Calculate priority score for a content suggestion"""
        priority = 50  # Base priority

        # Boost if matches context well
        preferred = CONTENT_SUGGESTIONS.get(context, [])
        if content_type in preferred:
            priority += 20
            if preferred.index(content_type) == 0:
                priority += 10  # Extra boost for first choice

        # Reduce if recently shared
        unlock_state = self._data.unlocked_content.get(content_type)
        if unlock_state and unlock_state.last_shared:
            try:
                last = datetime.fromisoformat(unlock_state.last_shared)
                hours_since = (datetime.now() - last).total_seconds() / 3600
                if hours_since < 1:
                    priority -= 40
                elif hours_since < 6:
                    priority -= 20
                elif hours_since < 24:
                    priority -= 10
            except (ValueError, TypeError):
                pass

        return max(0, min(100, priority))

    # -------------------------------------------------------------------------
    # Usage Tracking
    # -------------------------------------------------------------------------

    def mark_content_shared(self, content_type: str):
        """
        Mark that content of this type was just shared.

        Args:
            content_type: The type of content that was shared
        """
        if content_type not in self._data.unlocked_content:
            return

        unlock_state = self._data.unlocked_content[content_type]
        unlock_state.times_shared += 1
        unlock_state.last_shared = datetime.now().isoformat()
        self._save()

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def _on_thinking_done(self, data: Dict[str, Any]):
        """Handle thinking_done event - check for new unlocks"""
        new_unlocks = self.check_all_unlocks()

        if new_unlocks and self.nervous:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.nervous.emit("new_content_available", {
                    "unlocks": new_unlocks,
                    "message": self.get_new_unlock_message()
                }))
            except RuntimeError:
                pass

    # -------------------------------------------------------------------------
    # Statistics & Info
    # -------------------------------------------------------------------------

    def get_stats(self) -> Dict[str, Any]:
        """
        Get statistics about content unlocks.

        Returns:
            Dictionary with unlock statistics
        """
        total_types = len(UNLOCK_CRITERIA)
        unlocked_count = len(self.get_unlocked_content())
        locked_count = total_types - unlocked_count

        # Get total shares
        total_shares = sum(
            state.times_shared
            for state in self._data.unlocked_content.values()
        )

        # Get pending announcements
        pending_count = len(self._data.pending_announcements)

        # Calculate next unlock progress
        locked = self.get_locked_content()
        next_unlock = None
        next_progress = 0

        if locked:
            # Find the locked content closest to unlocking
            progresses = [
                (ct, self.get_unlock_progress(ct))
                for ct in locked
            ]
            progresses.sort(key=lambda x: x[1].get("progress_percent", 0), reverse=True)

            if progresses:
                next_unlock = progresses[0][0]
                next_progress = progresses[0][1].get("progress_percent", 0)

        return {
            "total_content_types": total_types,
            "unlocked_count": unlocked_count,
            "locked_count": locked_count,
            "unlock_percentage": round((unlocked_count / total_types) * 100) if total_types > 0 else 0,
            "total_shares": total_shares,
            "pending_announcements": pending_count,
            "next_unlock": next_unlock,
            "next_unlock_progress": next_progress,
            "current_metrics": self._get_current_metrics()
        }

    def get_unlock_summary(self) -> str:
        """
        Get a human-readable summary of unlock status.

        Returns:
            Summary string
        """
        stats = self.get_stats()
        unlocked = self.get_unlocked_content()

        lines = [
            f"Content Unlocks: {stats['unlocked_count']}/{stats['total_content_types']} unlocked ({stats['unlock_percentage']}%)",
            f"Total shares: {stats['total_shares']}"
        ]

        if unlocked:
            lines.append("\nUnlocked content:")
            for ct in unlocked:
                state = self._data.unlocked_content.get(ct)
                desc = UNLOCK_CRITERIA.get(ct, {}).get("description", "")
                lines.append(f"  - {ct}: {desc} (shared {state.times_shared}x)")

        locked = self.get_locked_content()
        if locked:
            lines.append(f"\nLocked content: {', '.join(locked)}")

        if stats['next_unlock']:
            lines.append(f"\nNext unlock: {stats['next_unlock']} ({stats['next_unlock_progress']}% progress)")

        return "\n".join(lines)

    # -------------------------------------------------------------------------
    # Reset & Maintenance
    # -------------------------------------------------------------------------

    def reset_all(self):
        """Reset all unlock progress"""
        self._data = ContentUnlocksData()
        self._initialize_content_types()
        print("[ContentUnlocks] All unlocks reset")

    def unlock_all(self):
        """Unlock all content types (for testing)"""
        now = datetime.now().isoformat()
        for content_type in UNLOCK_CRITERIA.keys():
            if content_type not in self._data.unlocked_content:
                self._data.unlocked_content[content_type] = UnlockState(
                    content_type=content_type
                )
            self._data.unlocked_content[content_type].unlocked = True
            self._data.unlocked_content[content_type].unlocked_at = now

        self._save()
        print("[ContentUnlocks] All content unlocked")

    def refresh_unlocks(self) -> List[str]:
        """
        Force a refresh of all unlock checks.

        Returns:
            List of newly unlocked content types
        """
        return self.check_all_unlocks()
