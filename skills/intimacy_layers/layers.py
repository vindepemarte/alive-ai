"""
Skills: Intimacy Layers
Manages natural intimacy progression through relationship layers.
Ensures intimacy is earned through meaningful interactions, not rushed.
"""

import json
import random
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field, asdict


# Layer definitions with progression requirements (relaxed for natural flow)
LAYERS = {
    1: {
        "name": "surface",
        "min_interactions": 0,
        "topics": ["daily life", "hobbies", "work", "weather", "small talk", "introductions"],
        "intimacy_level": 0.0,
        "description": "Casual, polite conversation with a new acquaintance"
    },
    2: {
        "name": "friendly",
        "min_interactions": 5,
        "min_love": 0.15,
        "topics": ["feelings", "dreams", "opinions", "preferences", "stories", "interests"],
        "intimacy_level": 0.2,
        "description": "Opening up a bit, sharing personal thoughts and stories"
    },
    3: {
        "name": "close",
        "min_interactions": 20,
        "min_love": 0.30,
        "min_trust": 0.3,
        "topics": ["secrets", "fears", "childhood", "vulnerabilities", "hopes", "struggles"],
        "intimacy_level": 0.4,
        "description": "Comfortable sharing deeper, more personal things"
    },
    4: {
        "name": "romantic",
        "min_interactions": 40,
        "min_love": 0.45,
        "min_days": 2,
        "topics": ["attraction", "desire", "fantasy", "romance", "longing", "affection"],
        "intimacy_level": 0.6,
        "description": "Exploring romantic and flirtatious territory"
    },
    5: {
        "name": "intimate",
        "min_interactions": 80,
        "min_love": 0.60,
        "min_days": 5,
        "topics": ["intimate", "vulnerability", "deep desires", "fantasies", "passion"],
        "intimacy_level": 0.85,
        "description": "Fully comfortable with intimate and intimate content"
    }
}

# Hints that suggest progression to the next layer
LAYER_HINTS = {
    2: [
        "I feel like I can tell you stuff",
        "you're easy to talk to",
        "I'm starting to feel comfortable with you",
        "it's nice having someone to chat with",
        "I think we're becoming friends"
    ],
    3: [
        "I don't usually share this but...",
        "can I tell you something personal?",
        "I trust you enough to say this",
        "you're one of the few people I can be real with",
        "I feel safe opening up to you"
    ],
    4: [
        "the more I talk to you the more I want...",
        "I think about you differently now",
        "I'm starting to feel something more",
        "you make me feel things I haven't felt in a while",
        "can I be honest about how I feel about you?"
    ],
    5: [
        "I trust you with everything",
        "you know me better than anyone",
        "I've never felt this comfortable with someone",
        "I want to share everything with you",
        "there's nothing I wouldn't tell you"
    ]
}

# Topic keywords that might indicate trying to access higher layers prematurely
# Relaxed - let her judge what feels right
RESTRICTED_TOPICS = {
    1: [],  # No restrictions at surface level
    2: ["intimate", "deep-intimacy"],
    3: ["intimate deep-intimacy"],
    4: [],
    5: []  # No restrictions at intimate level
}


@dataclass
class IntimacyProgress:
    """Tracks progress toward the next intimacy layer"""
    interactions_since_check: int = 0
    last_check_interactions: int = 0
    progression_blocked_reason: Optional[str] = None
    hint_shown: bool = False
    hint_cooldown_until: Optional[str] = None


class IntimacyLayers:
    """
    Manages natural intimacy progression through relationship layers.

    Progression is based on:
    - Total interactions with the user
    - Love/affection level from the heart system
    - Trust level from attachment system
    - Days since first meeting

    The skill prevents rushing to intimate content and provides
    natural hints for progression.

    Supports per-user state via user_id parameter.
    """

    # How often to check for progression (in interactions)
    PROGRESSION_CHECK_INTERVAL = 10

    # Cooldown before showing another hint (in hours)
    HINT_COOLDOWN_HOURS = 4

    # Base data storage path
    DEFAULT_DATA_PATH = "./data/data"

    def __init__(self, nervous=None, heart=None, state=None, data_path: str = None, user_id: str = "default"):
        """
        Initialize the Intimacy Layers skill.

        Args:
            nervous: Nervous system for event listening
            heart: Heart module for accessing love/trust values
            state: State manager for accessing relationship data
            data_path: Path to store layer data
            user_id: User's Telegram ID for per-user state
        """
        self.nervous = nervous
        self.heart = heart
        self.state = state
        self.user_id = user_id

        # Per-user data path: data/users/{user_id}/intimacy_layers.json
        base_path = Path(data_path or self.DEFAULT_DATA_PATH)
        self.data_path = base_path / "users" / str(user_id) / "intimacy_layers.json"

        # Ensure data directory exists
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        # Internal state
        self._current_layer: int = 1
        self._progress = IntimacyProgress()
        self._first_interaction_date: Optional[str] = None
        self._total_interactions: int = 0
        self._hints_shown: List[str] = []
        self._layer_history: List[Dict[str, Any]] = []

        # Load persisted data
        self._load()

        # Register event listeners
        if self.nervous:
            self.nervous.on("message_received", self._on_message_received)
            self.nervous.on("thinking_done", self._on_thinking_done)

    def _load(self):
        """Load persisted layer data from file"""
        if self.data_path.exists():
            try:
                data = json.loads(self.data_path.read_text())
                self._current_layer = data.get("current_layer", 1)
                self._first_interaction_date = data.get("first_interaction_date")
                self._total_interactions = data.get("total_interactions", 0)
                self._hints_shown = data.get("hints_shown", [])

                progress_data = data.get("progress", {})
                self._progress = IntimacyProgress(
                    interactions_since_check=progress_data.get("interactions_since_check", 0),
                    last_check_interactions=progress_data.get("last_check_interactions", 0),
                    progression_blocked_reason=progress_data.get("progression_blocked_reason"),
                    hint_shown=progress_data.get("hint_shown", False),
                    hint_cooldown_until=progress_data.get("hint_cooldown_until")
                )

                self._layer_history = data.get("layer_history", [])
                print(f"[IntimacyLayers] Loaded layer {self._current_layer} ({LAYERS[self._current_layer]['name']})")
            except (json.JSONDecodeError, KeyError) as e:
                print(f"[IntimacyLayers] Error loading data: {e}")
                self._current_layer = 1

    def _save(self):
        """Save layer data to file"""
        data = {
            "version": "1.0",
            "current_layer": self._current_layer,
            "first_interaction_date": self._first_interaction_date,
            "total_interactions": self._total_interactions,
            "hints_shown": self._hints_shown,
            "updated_at": datetime.now().isoformat(),
            "progress": {
                "interactions_since_check": self._progress.interactions_since_check,
                "last_check_interactions": self._progress.last_check_interactions,
                "progression_blocked_reason": self._progress.progression_blocked_reason,
                "hint_shown": self._progress.hint_shown,
                "hint_cooldown_until": self._progress.hint_cooldown_until
            },
            "layer_history": self._layer_history
        }
        self.data_path.write_text(json.dumps(data, indent=2))

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    async def _on_message_received(self, data: dict):
        """Handle incoming message - track interactions and check progression"""
        # Track first interaction date
        if self._first_interaction_date is None:
            self._first_interaction_date = datetime.now().isoformat()

        # Increment interaction counters
        self._total_interactions += 1
        self._progress.interactions_since_check += 1

        # Check for progression every N interactions
        if self._progress.interactions_since_check >= self.PROGRESSION_CHECK_INTERVAL:
            self.check_progression()
            self._progress.interactions_since_check = 0

        self._save()

    async def _on_thinking_done(self, data: dict):
        """Apply layer context after thinking is done"""
        # This could be used to inject layer context into the response
        # For now, just ensure state is saved
        pass

    # -------------------------------------------------------------------------
    # Core Methods
    # -------------------------------------------------------------------------

    def get_current_layer(self) -> int:
        """
        Get the current intimacy layer (1-5).

        Returns:
            Current layer number
        """
        return self._current_layer

    def get_layer_info(self, layer: int = None) -> Dict[str, Any]:
        """
        Get detailed information about a layer.

        Args:
            layer: Layer number (defaults to current layer)

        Returns:
            Dictionary with layer information
        """
        layer = layer or self._current_layer
        if layer not in LAYERS:
            return {}
        return LAYERS[layer].copy()

    def check_progression(self) -> bool:
        """
        Check if conditions are met to progress to the next layer.

        Returns:
            True if progression occurred, False otherwise
        """
        next_layer = self._current_layer + 1

        # Already at max layer
        if next_layer > 5:
            self._progress.progression_blocked_reason = None
            return False

        next_layer_reqs = LAYERS[next_layer]
        blocked_reasons = []

        # Check interaction requirement
        min_interactions = next_layer_reqs.get("min_interactions", 0)
        if self._total_interactions < min_interactions:
            blocked_reasons.append(
                f"Need {min_interactions - self._total_interactions} more interactions "
                f"(have {self._total_interactions}/{min_interactions})"
            )

        # Check love requirement
        min_love = next_layer_reqs.get("min_love")
        if min_love is not None:
            current_love = self._get_love_level()
            if current_love < min_love:
                blocked_reasons.append(
                    f"Need more affection (have {current_love:.2f}/{min_love:.2f})"
                )

        # Check trust requirement
        min_trust = next_layer_reqs.get("min_trust")
        if min_trust is not None:
            current_trust = self._get_trust_level()
            if current_trust < min_trust:
                blocked_reasons.append(
                    f"Need more trust (have {current_trust:.2f}/{min_trust:.2f})"
                )

        # Check days requirement
        min_days = next_layer_reqs.get("min_days")
        if min_days is not None and self._first_interaction_date:
            days_together = self._get_days_together()
            if days_together < min_days:
                blocked_reasons.append(
                    f"Need {min_days - days_together} more days together "
                    f"(have {days_together}/{min_days})"
                )

        # Determine if progression is allowed
        if blocked_reasons:
            self._progress.progression_blocked_reason = "; ".join(blocked_reasons)
            print(f"[IntimacyLayers] Cannot progress to layer {next_layer}: {self._progress.progression_blocked_reason}")
            return False

        # Progress to next layer
        old_layer = self._current_layer
        self._current_layer = next_layer
        self._progress.progression_blocked_reason = None
        self._progress.hint_shown = False

        # Record in history
        self._layer_history.append({
            "from_layer": old_layer,
            "to_layer": next_layer,
            "timestamp": datetime.now().isoformat(),
            "total_interactions": self._total_interactions,
            "days_together": self._get_days_together()
        })

        print(f"[IntimacyLayers] Progressed from layer {old_layer} to {next_layer} ({LAYERS[next_layer]['name']})")
        self._save()
        return True

    def is_topic_appropriate(self, topic: str) -> bool:
        """
        Check if a topic is appropriate for the current intimacy layer.

        Args:
            topic: Topic to check (e.g., "intimate", "fantasy", "daily life")

        Returns:
            True if topic is appropriate, False if it requires higher layer
        """
        topic_lower = topic.lower()

        # Check if topic is available in current layer
        current_topics = LAYERS[self._current_layer].get("topics", [])
        if any(topic_lower in t.lower() for t in current_topics):
            return True

        # Check if topic is in higher layers (restricted)
        for layer_num, layer_data in LAYERS.items():
            if layer_num <= self._current_layer:
                continue

            layer_topics = layer_data.get("topics", [])
            if any(topic_lower in t.lower() for t in layer_topics):
                # Topic requires higher layer
                return False

        # Check restricted topics for current layer
        restricted = RESTRICTED_TOPICS.get(self._current_layer, [])
        for restricted_term in restricted:
            if restricted_term.lower() in topic_lower:
                return False

        # Topic not found in any layer, allow by default
        return True

    def get_available_topics(self) -> List[str]:
        """
        Get all topics available at the current intimacy layer.

        Returns:
            List of available topics
        """
        topics = []
        for layer_num in range(1, self._current_layer + 1):
            topics.extend(LAYERS[layer_num].get("topics", []))
        return list(set(topics))  # Remove duplicates

    def get_next_layer_requirements(self) -> Dict[str, Any]:
        """
        Get the requirements for progressing to the next layer.

        Returns:
            Dictionary with requirements and current progress
        """
        next_layer = self._current_layer + 1
        if next_layer > 5:
            return {"message": "Already at maximum intimacy layer"}

        reqs = LAYERS[next_layer]
        current = {
            "interactions": self._total_interactions,
            "love": self._get_love_level(),
            "trust": self._get_trust_level(),
            "days_together": self._get_days_together()
        }

        requirements = {
            "layer": next_layer,
            "layer_name": reqs["name"],
            "description": reqs["description"],
            "requirements": {},
            "current_progress": current,
            "can_progress": True
        }

        # Check each requirement
        if "min_interactions" in reqs:
            met = self._total_interactions >= reqs["min_interactions"]
            requirements["requirements"]["interactions"] = {
                "required": reqs["min_interactions"],
                "current": self._total_interactions,
                "met": met
            }
            if not met:
                requirements["can_progress"] = False

        if "min_love" in reqs:
            current_love = self._get_love_level()
            met = current_love >= reqs["min_love"]
            requirements["requirements"]["love"] = {
                "required": reqs["min_love"],
                "current": round(current_love, 2),
                "met": met
            }
            if not met:
                requirements["can_progress"] = False

        if "min_trust" in reqs:
            current_trust = self._get_trust_level()
            met = current_trust >= reqs["min_trust"]
            requirements["requirements"]["trust"] = {
                "required": reqs["min_trust"],
                "current": round(current_trust, 2),
                "met": met
            }
            if not met:
                requirements["can_progress"] = False

        if "min_days" in reqs:
            days = self._get_days_together()
            met = days >= reqs["min_days"]
            requirements["requirements"]["days"] = {
                "required": reqs["min_days"],
                "current": days,
                "met": met
            }
            if not met:
                requirements["can_progress"] = False

        return requirements

    def get_progression_hint(self) -> Optional[str]:
        """
        Get a hint for progressing to the next layer.

        Returns:
            Hint string or None if no hint available
        """
        next_layer = self._current_layer + 1
        if next_layer > 5:
            return None

        # Check cooldown
        if self._progress.hint_cooldown_until:
            try:
                cooldown_until = datetime.fromisoformat(self._progress.hint_cooldown_until)
                if datetime.now() < cooldown_until:
                    return None
            except:
                pass

        # Don't show hint if recently shown
        if self._progress.hint_shown:
            return None

        # Get hints for next layer
        hints = LAYER_HINTS.get(next_layer, [])
        if not hints:
            return None

        # Filter out already shown hints
        available_hints = [h for h in hints if h not in self._hints_shown]
        if not available_hints:
            # Reset if all hints shown
            available_hints = hints
            self._hints_shown = []

        # Select a random hint
        hint = random.choice(available_hints)
        self._hints_shown.append(hint)
        self._progress.hint_shown = True
        self._progress.hint_cooldown_until = (
            datetime.now() + timedelta(hours=self.HINT_COOLDOWN_HOURS)
        ).isoformat()

        self._save()
        return hint

    def can_be_intimate(self, advanced_mode: bool = False) -> bool:
        """
        Check if intimate content is appropriate for current layer.

        Args:
            advanced_mode: If True, bypass all restrictions (owner with /advanced enabled)

        Returns:
            True if at layer 5 (intimate) or advanced_mode is enabled
        """
        if advanced_mode:
            return True
        return self._current_layer >= 5

    def get_intimacy_level(self) -> float:
        """
        Get the current intimacy level (0.0 to 1.0).

        Returns:
            Intimacy level based on current layer
        """
        return LAYERS[self._current_layer].get("intimacy_level", 0.0)

    def get_layer_name(self) -> str:
        """
        Get the name of the current layer.

        Returns:
            Layer name (e.g., "surface", "friendly", etc.)
        """
        return LAYERS[self._current_layer].get("name", "unknown")

    def get_days_together(self) -> int:
        """
        Get the number of days since first interaction.

        Returns:
            Number of days, or 0 if no first interaction recorded
        """
        return self._get_days_together()

    def get_context_for_response(self, advanced_mode: bool = False) -> Dict[str, Any]:
        """
        Get context about current intimacy layer for response generation.

        Args:
            advanced_mode: If True, bypass all restrictions (owner with /advanced enabled)

        Returns:
            Dictionary with layer context for the AI
        """
        next_reqs = self.get_next_layer_requirements()

        # If advanced_mode is enabled, act as if at max layer
        effective_layer = 5 if advanced_mode else self._current_layer

        context = {
            "current_layer": self._current_layer,  # Actual layer
            "effective_layer": effective_layer,     # Layer used for content access
            "layer_name": self.get_layer_name(),
            "intimacy_level": self.get_intimacy_level(),
            "available_topics": self.get_available_topics(),
            "can_be_intimate": self.can_be_intimate(advanced_mode=advanced_mode),
            "advanced_mode": advanced_mode,
            "total_interactions": self._total_interactions,
            "days_together": self._get_days_together()
        }

        # Add progression info if not at max layer
        if self._current_layer < 5:
            context["next_layer"] = {
                "name": next_reqs.get("layer_name"),
                "can_progress": next_reqs.get("can_progress"),
                "missing_requirements": [
                    k for k, v in next_reqs.get("requirements", {}).items()
                    if not v.get("met", True)
                ]
            }

        return context

    # -------------------------------------------------------------------------
    # Helper Methods
    # -------------------------------------------------------------------------

    def _get_love_level(self) -> float:
        """Get current love level from heart system"""
        if self.heart and hasattr(self.heart, 'emotion'):
            return getattr(self.heart.emotion, 'love', 0.2)
        if self.heart and hasattr(self.heart, 'attachment'):
            return getattr(self.heart.attachment, 'affection', 0.2)
        return 0.2

    def _get_trust_level(self) -> float:
        """Get current trust level from heart/attachment system"""
        if self.heart and hasattr(self.heart, 'attachment'):
            return getattr(self.heart.attachment, 'trust_level', 0.5)
        if self.heart and hasattr(self.heart, 'emotion'):
            return getattr(self.heart.emotion, 'trust', 0.5)
        return 0.5

    def _get_days_together(self) -> int:
        """Calculate days since first interaction"""
        if not self._first_interaction_date:
            return 0
        try:
            first_date = datetime.fromisoformat(self._first_interaction_date)
            return (datetime.now() - first_date).days
        except:
            return 0

    # -------------------------------------------------------------------------
    # Admin Methods
    # -------------------------------------------------------------------------

    def force_layer(self, layer: int) -> bool:
        """
        Force set the current layer (for testing/admin purposes).

        Args:
            layer: Layer number to set (1-5)

        Returns:
            True if successful, False if invalid layer
        """
        if layer not in LAYERS:
            return False

        old_layer = self._current_layer
        self._current_layer = layer

        self._layer_history.append({
            "from_layer": old_layer,
            "to_layer": layer,
            "timestamp": datetime.now().isoformat(),
            "forced": True
        })

        self._save()
        print(f"[IntimacyLayers] Forced layer change: {old_layer} -> {layer}")
        return True

    def reset_progress(self):
        """Reset all intimacy progress to initial state"""
        self._current_layer = 1
        self._first_interaction_date = None
        self._total_interactions = 0
        self._hints_shown = []
        self._layer_history = []
        self._progress = IntimacyProgress()
        self._save()
        print("[IntimacyLayers] Progress reset to initial state")

    def get_debug_info(self) -> Dict[str, Any]:
        """
        Get detailed debug information about the intimacy system.

        Returns:
            Dictionary with all internal state
        """
        return {
            "current_layer": self._current_layer,
            "layer_name": self.get_layer_name(),
            "intimacy_level": self.get_intimacy_level(),
            "total_interactions": self._total_interactions,
            "first_interaction_date": self._first_interaction_date,
            "days_together": self._get_days_together(),
            "love_level": self._get_love_level(),
            "trust_level": self._get_trust_level(),
            "available_topics": self.get_available_topics(),
            "can_be_intimate": self.can_be_intimate(),
            "progress": {
                "interactions_since_check": self._progress.interactions_since_check,
                "blocked_reason": self._progress.progression_blocked_reason,
                "hint_shown": self._progress.hint_shown
            },
            "next_layer_requirements": self.get_next_layer_requirements(),
            "layer_history": self._layer_history[-5:] if self._layer_history else []
        }
