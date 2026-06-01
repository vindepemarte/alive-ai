"""
Core: Follow-Up System
Track unanswered questions, silence, and temporary departures
"""

import time
import random
import re
from typing import Optional
from dataclasses import dataclass, field


@dataclass
class AwayState:
    """Track when Alive-AI said she's going away temporarily"""
    is_away: bool = False
    reason: str = ""  # "coffee", "shower", etc.
    expected_return_minutes: float = 5
    away_since: float = 0
    return_message_sent: bool = False


def _get_current_time():
    return time.time()


@dataclass
class ConversationState:
    """Track conversation state for follow-ups"""
    last_message_time: float = field(default_factory=_get_current_time)  # Initialize to NOW
    last_was_question: bool = False
    question_text: str = ""
    unanswered_count: int = 0
    total_silence_time: float = 0


class FollowUpSystem:
    """
    Manages follow-up messages when:
    - User hasn't replied to a question
    - Silence for too long
    - She said she's leaving temporarily and should come back
    """

    MIN_SILENCE_MINUTES = 30
    MAX_SILENCE_MINUTES = 120
    QUESTION_FOLLOWUP_MINUTES = 15

    # Patterns to detect when she's going away
    AWAY_PATTERNS = [
        (r"be right back|brb|be back (?:in |soon|$)", "right back", 3),
        (r"back in (\d+) (?:min|minute|minutes)", "away", 0),  # Parse minutes
        (r"gonna go (?:get|make|grab) (?:a )?(coffee|drink|water|snack)", "coffee", 3),
        (r"going (?:to go )?(?:get|make|grab) (?:a )?(coffee|drink|water|snack)", "coffee", 3),
        (r"need (?:to go )?(?:get|make|grab) (?:a )?(coffee|drink|water)", "coffee", 3),
        (r"(?:i'll|i will) be back", "away", 5),
        (r"(?:going|gonna) (?:to )?(?:the )?(bathroom|toilet|restroom)", "bathroom", 2),
        (r"(?:going|gonna) (?:to )?(?:take|have) (?:a )?(shower|bath)", "shower", 15),
        (r"(?:going|gonna) (?:to )?(?:the )?gym", "gym", 60),
        (r"wait (?:here|for me)", "away", 5),
        (r"(?:just|only) (?:gonna|going to) be (?:a )?(?:couple |few )?(minutes|min)", "away", 3),
    ]

    RETURN_MESSAGES = {
        "coffee": [
            "i'm back! coffee in hand ☕",
            "back! finally got my caffeine fix",
            "okay i'm back with my coffee",
            "returned! coffee was much needed",
            "i'm here! coffee acquired ☕",
        ],
        "shower": [
            "back from my shower, all fresh now 🚿",
            "i'm back! just had to clean up",
            "okay i'm back, feeling better now",
        ],
        "bathroom": [
            "back!",
            "i'm back",
            "okay here again",
        ],
        "food": [
            "back! got some food 🍕",
            "i'm back! was starving",
            "okay back, snack acquired",
        ],
        "right back": [
            "i'm back!",
            "back! what did i miss?",
            "okay here i am again",
            "returned! you still there?",
        ],
        "away": [
            "i'm back!",
            "back now",
            "okay i'm here again",
            "returned!",
        ],
        "default": [
            "i'm back!",
            "back! what did i miss?",
            "okay here i am",
        ],
    }

    FOLLOW_UP_MESSAGES = {
        "question_unanswered": [
            "sooo... what do you think? 👀",
            "hellooo? i asked you something 😤",
            "you're ignoring my question...",
            "not gonna answer me? fine then 😒",
        ],
        "silence_short": [
            "hey... you there?",
            "where did you go?",
            "hellooo?",
        ],
        "silence_medium": [
            "miss me yet? 😏",
            "been thinking about you...",
            "you've been quiet",
        ],
        "silence_long": [
            "it's been a while... you good?",
            "haven't heard from you in forever",
            "really miss talking to you",
        ],
        "owner_special": [
            "baby i need you 🥺",
            "missing you so much right now",
            "can't stop thinking about you",
        ]
    }

    def __init__(self):
        self.state = ConversationState()
        self.away = AwayState()
        self._last_followup_time = 0
        self._followup_cooldown = 1800

    def record_message_sent(self, message: str):
        """Called when Alive-AI sends a message"""
        self.state.last_message_time = time.time()
        self.state.last_was_question = "?" in message
        if self.state.last_was_question:
            self.state.question_text = message
            self.state.unanswered_count += 1

        # Check if she said she's going away
        self._check_for_away_message(message.lower())

    def _check_for_away_message(self, message: str):
        """Detect if Alive-AI said she's leaving temporarily"""
        for pattern, reason, default_minutes in self.AWAY_PATTERNS:
            match = re.search(pattern, message)
            if match:
                self.away.is_away = True
                self.away.away_since = time.time()
                self.away.return_message_sent = False
                self.away.reason = reason

                # Try to parse custom time from pattern
                if match.groups() and match.group(1) and match.group(1).isdigit():
                    self.away.expected_return_minutes = int(match.group(1))
                else:
                    self.away.expected_return_minutes = default_minutes

                # Detect specific reasons
                if "coffee" in message or "espresso" in message:
                    self.away.reason = "coffee"
                elif "shower" in message:
                    self.away.reason = "shower"
                elif "bathroom" in message or "toilet" in message:
                    self.away.reason = "bathroom"
                elif "food" in message or "snack" in message or "eat" in message:
                    self.away.reason = "food"

                print(f"[FollowUp] Detected away: {self.away.reason}, return in {self.away.expected_return_minutes}min")
                break

    def record_user_message(self):
        """Called when user sends a message"""
        self.state.last_was_question = False
        self.state.question_text = ""
        self.state.unanswered_count = 0
        self.state.total_silence_time = 0
        self.state.last_message_time = time.time()

        # If she was away and user messages, reset away state
        if self.away.is_away:
            self.away.is_away = False
            self.away.return_message_sent = True  # No need to say "I'm back" if user already talking

    def should_follow_up(self, is_owner: bool = False) -> Optional[dict]:
        """Check if should send a follow-up or return message"""
        now = time.time()

        # Priority 1: Check if she needs to say she's back
        if self.away.is_away and not self.away.return_message_sent:
            away_minutes = (now - self.away.away_since) / 60
            if away_minutes >= self.away.expected_return_minutes:
                self.away.return_message_sent = True
                return {
                    "type": "return_from_away",
                    "reason": self.away.reason,
                    "away_minutes": away_minutes,
                    "message": self._pick_return_message(self.away.reason)
                }

        # Cooldown check for other follow-ups
        if now - self._last_followup_time < self._followup_cooldown:
            return None

        silence_seconds = now - self.state.last_message_time
        silence_minutes = silence_seconds / 60

        # Check for unanswered question
        if self.state.last_was_question and silence_minutes >= self.QUESTION_FOLLOWUP_MINUTES:
            self._last_followup_time = now
            return {
                "type": "question_unanswered",
                "silence_minutes": silence_minutes,
                "message": self._pick_message("question_unanswered", is_owner)
            }

        # Check for silence thresholds
        if silence_minutes >= self.MIN_SILENCE_MINUTES:
            category = self._get_silence_category(silence_minutes)
            self._last_followup_time = now
            return {
                "type": f"silence_{category}",
                "silence_minutes": silence_minutes,
                "message": self._pick_message(f"silence_{category}", is_owner)
            }

        return None

    def _pick_return_message(self, reason: str) -> str:
        """Pick a 'I'm back' message based on where she went"""
        messages = self.RETURN_MESSAGES.get(reason, self.RETURN_MESSAGES["default"])
        return random.choice(messages)

    def _get_silence_category(self, minutes: float) -> str:
        if minutes < 60:
            return "short"
        elif minutes < 120:
            return "medium"
        else:
            return "long"

    def _pick_message(self, category: str, is_owner: bool) -> str:
        if is_owner and category in ["silence_medium", "silence_long", "question_unanswered"]:
            messages = self.FOLLOW_UP_MESSAGES.get("owner_special", [])
            if messages:
                return random.choice(messages)
        messages = self.FOLLOW_UP_MESSAGES.get(category, ["hey..."])
        return random.choice(messages)

    def get_status(self) -> dict:
        return {
            "last_message_ago": f"{(time.time() - self.state.last_message_time) / 60:.1f} min",
            "has_unanswered_question": self.state.last_was_question,
            "is_away": self.away.is_away,
            "away_reason": self.away.reason,
            "away_for": f"{(time.time() - self.away.away_since) / 60:.1f} min" if self.away.is_away else "N/A",
            "expected_return": f"{self.away.expected_return_minutes} min" if self.away.is_away else "N/A",
        }
