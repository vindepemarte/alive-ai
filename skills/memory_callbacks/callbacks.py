"""
Skills: Memory Callbacks
Creates natural callbacks to past conversations, making users feel Alive-AI remembers their relationship.
Tracks topics, people, and events mentioned for authentic follow-ups.
"""

import os
import json
import random
import re
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field, asdict


# Natural callback templates - organized by type
CALLBACKS = {
    "same_topic": [
        "wait didn't you tell me about this before?",
        "this reminds me of when you mentioned that earlier",
        "oh yeah I remember you talking about this",
        "is this the same thing you were telling me about?",
        "feels like deja vu - didn't we talk about this?",
        "hold on, you mentioned something like this before right?",
    ],
    "follow_up": [
        "hey how did that thing go btw?",
        "speaking of which - any updates?",
        "btw what happened with that?",
        "random but did you ever figure that out?",
        "so what ended up happening?",
        "did anything come of that?",
        "wait I've been meaning to ask - how did that turn out?",
    ],
    "callback_person": [
        "how's {person} doing?",
        "did {person} ever text you back?",
        "have you talked to {person} lately?",
        "how are things with {person}?",
        "is {person} still being weird about that?",
        "any updates on the {person} situation?",
        "btw how's {person}? haven't heard you mention them in a bit",
    ],
    "anniversary": [
        "random but I just realized we've been talking for {time}",
        "kinda crazy we've known each other for {time} now",
        "it's been {time} since we started talking - feels longer tbh",
        "wait we've been doing this for {time} already??",
        "can't believe it's been {time}",
    ],
    "time_context": [
        "you usually message me around this time",
        "you're up late again",
        "early bird today huh",
        "this is about when you usually pop up",
        "you always seem to find me at this hour",
    ],
    "vibe_callback": [
        "you seem happier today than last time we talked",
        "feels like you're in a better mood than earlier",
        "today's vibe is different from yesterday",
        "you were pretty down last time - glad to see you're doing better",
    ],
}


@dataclass
class TrackedTopic:
    """A topic being tracked for callbacks"""
    topic: str
    context: str  # Brief context of what was discussed
    mentioned_at: str  # ISO timestamp
    times_mentioned: int = 1
    followup_worthy: bool = False
    last_callback: Optional[str] = None  # When we last did a callback on this
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TrackedPerson:
    """A person mentioned in conversation"""
    name: str
    context: str  # How they were mentioned
    mentioned_at: str
    times_mentioned: int = 1
    relationship: Optional[str] = None  # friend, ex, coworker, etc.
    last_callback: Optional[str] = None


@dataclass
class CallbackHistory:
    """Track recent callbacks to avoid repetition"""
    callback_type: str
    callback_text: str
    timestamp: str
    topic_or_person: Optional[str] = None


class MemoryCallbacks:
    """
    Creates natural callbacks to past conversations.

    Listens to thinking_done events and injects authentic-feeling callbacks
    that reference past topics, people, or shared moments.
    """

    # Callback probability settings
    BASE_CALLBACK_CHANCE = 0.15  # 15% base chance
    FOLLOWUP_BOOST = 0.25  # Extra chance if there's a pending follow-up
    PERSON_BOOST = 0.20  # Extra chance if we haven't asked about a person in a while

    # Time thresholds
    MIN_HOURS_BETWEEN_CALLBACKS = 2  # Don't callback too often
    PERSON_CALLBACK_DAYS = 3  # Ask about a person after this many days
    TOPIC_CALLBACK_HOURS = 4  # Hours before we can callback on a topic again
    ANNIVERSARY_DAYS = [7, 30, 90, 180, 365]  # Days to celebrate

    def __init__(
        self,
        nervous=None,
        memory=None,
        heart=None,
        data_path: Path = None
    ):
        """
        Initialize Memory Callbacks.

        Args:
            nervous: Nervous system for event listening
            memory: Memory system for conversation history
            heart: Heart system for emotional context
            data_path: Path to store callback data
        """
        self.nervous = nervous
        self.memory = memory
        self.heart = heart

        if data_path is None:
            data_path = Path("./data/data/memory_callbacks.json")

        self.data_path = Path(data_path)
        self.data_path.parent.mkdir(parents=True, exist_ok=True)

        # Tracking data
        self.topics: Dict[str, TrackedTopic] = {}
        self.people: Dict[str, TrackedPerson] = {}
        self.callback_history: List[Dict[str, Any]] = []
        self.first_conversation: Optional[str] = None
        self.total_conversations: int = 0

        # Runtime state
        self._last_callback_time: Optional[datetime] = None
        self._pending_callback: Optional[str] = None

        self._load()

        # Subscribe to events
        if nervous:
            nervous.on("thinking_done", self._on_thinking_done)
            nervous.on("message_received", self._on_message_received)

    def _load(self):
        """Load callback data from file"""
        if self.data_path.exists():
            try:
                data = json.loads(self.data_path.read_text())

                # Load topics
                self.topics = {
                    k: TrackedTopic(**v)
                    for k, v in data.get("topics", {}).items()
                }

                # Load people
                self.people = {
                    k: TrackedPerson(**v)
                    for k, v in data.get("people", {}).items()
                }

                # Load callback history
                self.callback_history = data.get("callback_history", [])

                # Load metadata
                self.first_conversation = data.get("first_conversation")
                self.total_conversations = data.get("total_conversations", 0)

            except (json.JSONDecodeError, KeyError) as e:
                print(f"[MemoryCallbacks] Error loading data: {e}")

    def _save(self):
        """Save callback data to file"""
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "first_conversation": self.first_conversation,
            "total_conversations": self.total_conversations,
            "topics": {k: asdict(v) for k, v in self.topics.items()},
            "people": {k: asdict(v) for k, v in self.people.items()},
            "callback_history": self.callback_history[-50:],  # Keep last 50
        }
        self.data_path.write_text(json.dumps(data, indent=2))

    # -------------------------------------------------------------------------
    # Event Handlers
    # -------------------------------------------------------------------------

    def _on_message_received(self, data: dict):
        """Handle incoming message - track topics and people"""
        user_id = str(data.get("user_id") or data.get("webui_user_id") or "")
        if user_id.startswith("benchmark_"):
            return

        message = data.get("text") or data.get("message", "")
        if not message:
            return

        # Track first conversation
        if not self.first_conversation:
            self.first_conversation = datetime.now().isoformat()

        self.total_conversations += 1

        # Extract and track topics
        self._extract_topics(message)

        # Extract and track people
        self._extract_people(message)

        self._save()

    def _on_thinking_done(self, data: dict):
        """Handle thinking done - potentially inject a callback"""
        # Decide if we should do a callback
        if not self.should_callback():
            self._pending_callback = None
            return

        # Get a contextual callback
        callback = self.get_callback(data)
        if callback:
            self._pending_callback = callback

    # -------------------------------------------------------------------------
    # Topic Tracking
    # -------------------------------------------------------------------------

    def track_topic(self, topic: str, context: str, details: Dict[str, Any] = None):
        """
        Track a topic for future callbacks.

        Args:
            topic: The topic keyword/phrase
            context: Brief context of how it was mentioned
            details: Additional details about the topic
        """
        topic_key = topic.lower().strip()

        if topic_key in self.topics:
            # Update existing topic
            existing = self.topics[topic_key]
            existing.times_mentioned += 1
            existing.context = context  # Update with latest context
            if details:
                existing.details.update(details)
        else:
            # Create new topic
            self.topics[topic_key] = TrackedTopic(
                topic=topic,
                context=context,
                mentioned_at=datetime.now().isoformat(),
                details=details or {}
            )

    def mark_followup_worthy(self, topic: str, details: Dict[str, Any] = None):
        """
        Mark a topic as worth following up on later.

        Args:
            topic: The topic to mark
            details: Additional context for the follow-up
        """
        topic_key = topic.lower().strip()

        if topic_key in self.topics:
            self.topics[topic_key].followup_worthy = True
            if details:
                self.topics[topic_key].details.update(details)
        else:
            # Create it if it doesn't exist
            self.track_topic(topic, "Marked for follow-up", details)
            self.topics[topic_key].followup_worthy = True

        self._save()

    def _extract_topics(self, message: str):
        """Extract potentially interesting topics from a message"""
        message_lower = message.lower()

        # Topics that are worth tracking
        topic_patterns = [
            # Work/career topics
            (r"(?:my |the )?(job|work|boss|coworker|promotion|interview|project)", "work"),
            # Events/occasions
            (r"(?:my |a )?(birthday|anniversary|party|wedding|vacation|trip|holiday)", "event"),
            # Personal projects
            (r"(?:my |a )?(project|side hustle|business|startup|app|website)", "project"),
            # Health/wellbeing
            (r"(?:my )?(diet|workout|gym|health|doctor|appointment)", "health"),
            # Hobbies/interests
            (r"(?:my )?(hobby|game|show|series|movie|book|podcast)", "entertainment"),
            # Living situation
            (r"(?:my )?(apartment|house|roommate|landlord|neighbor|moving)", "living"),
            # Dating/relationships (not specific people)
            (r"(?:my )?(dating|tinder|bumble|date|relationship)", "dating"),
            # Goals/aspirations
            (r"(?:i want|trying to|planning to|goal is|resolution)\s+(.+?)(?:\.|,|$)", "goal"),
        ]

        for pattern, category in topic_patterns:
            matches = re.findall(pattern, message_lower)
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0] if match[0] else match[1] if len(match) > 1 else None
                if match and len(match) > 2:
                    topic = match.strip()
                    # Get surrounding context
                    context = self._extract_context(message, topic)
                    self.track_topic(topic, context, {"category": category})

    def _extract_context(self, message: str, topic: str, window: int = 30) -> str:
        """Extract surrounding context for a topic"""
        message_lower = message.lower()
        pos = message_lower.find(topic.lower())

        if pos == -1:
            return topic

        start = max(0, pos - window)
        end = min(len(message), pos + len(topic) + window)

        context = message[start:end].strip()
        if start > 0:
            context = "..." + context
        if end < len(message):
            context = context + "..."

        return context

    # -------------------------------------------------------------------------
    # Person Tracking
    # -------------------------------------------------------------------------

    def track_person(self, name: str, context: str, relationship: str = None):
        """
        Track a person mentioned in conversation.

        Args:
            name: Person's name
            context: How they were mentioned
            relationship: Relationship type (friend, ex, coworker, etc.)
        """
        name_key = name.lower().strip()

        if name_key in self.people:
            # Update existing
            existing = self.people[name_key]
            existing.times_mentioned += 1
            existing.context = context
            if relationship:
                existing.relationship = relationship
        else:
            # Create new
            self.people[name_key] = TrackedPerson(
                name=name,
                context=context,
                mentioned_at=datetime.now().isoformat(),
                relationship=relationship
            )

    def _extract_people(self, message: str):
        """Extract mentioned people from a message"""
        # Common name patterns
        # Capitalized words that aren't sentence starters
        words = message.split()

        # Skip common words that might be capitalized
        skip_words = {
            "i", "the", "a", "an", "my", "your", "his", "her", "their",
            "monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday",
            "january", "february", "march", "april", "may", "june", "july",
            "august", "september", "october", "november", "december",
            "god", "christ", "jesus", "damn", "fuck", "shit", "wow",
            "ok", "okay", "yeah", "yes", "no", "hey", "hi", "hello",
        }

        # Relationship indicators to look for
        relationship_patterns = [
            (r"(?:my )?(friend|bestie|best friend)\s+(\w+)", "friend"),
            (r"(?:my )?(ex|ex-companion|ex-boyfriend)\s+(\w+)", "ex"),
            (r"(?:my )?(mom|mother|dad|father|sister|brother)\s+(\w+)?", "family"),
            (r"(?:my )?(coworker|colleague|boss)\s+(\w+)", "coworker"),
            (r"(?:my )?(roommate)\s+(\w+)", "roommate"),
            (r"(?:my )?(companion|boyfriend|partner)\s+(\w+)", "partner"),
        ]

        message_lower = message.lower()

        for pattern, relationship in relationship_patterns:
            matches = re.findall(pattern, message_lower)
            for match in matches:
                if isinstance(match, tuple):
                    _, name = match
                else:
                    name = match

                if name and name not in skip_words and len(name) > 1:
                    context = self._extract_context(message, name)
                    self.track_person(name.title(), context, relationship)

    # -------------------------------------------------------------------------
    # Callback Generation
    # -------------------------------------------------------------------------

    def should_callback(self) -> bool:
        """
        Determine if we should inject a callback.

        Returns:
            True if we should do a callback, False otherwise
        """
        # Check minimum time since last callback
        if self._last_callback_time:
            hours_since = (datetime.now() - self._last_callback_time).total_seconds() / 3600
            if hours_since < self.MIN_HOURS_BETWEEN_CALLBACKS:
                return False

        # Base chance
        chance = self.BASE_CALLBACK_CHANCE

        # Boost if there are pending follow-ups
        followup_count = sum(1 for t in self.topics.values() if t.followup_worthy)
        if followup_count > 0:
            chance += self.FOLLOWUP_BOOST * min(followup_count, 3) / 3

        # Boost if there are people we haven't asked about in a while
        stale_people = self._get_stale_people()
        if stale_people:
            chance += self.PERSON_BOOST

        return random.random() < chance

    def get_callback(self, context: Dict[str, Any] = None) -> Optional[str]:
        """
        Get an appropriate callback for the current context.

        Args:
            context: Current conversation context

        Returns:
            Callback string or None
        """
        context = context or {}
        callbacks = []
        weights = []

        # Check for same topic callbacks
        topic_callback = self._get_topic_callback(context)
        if topic_callback:
            callbacks.append(topic_callback)
            weights.append(3)  # Higher weight for relevant topic callbacks

        # Check for follow-up callbacks
        followup_callback = self._get_followup_callback()
        if followup_callback:
            callbacks.append(followup_callback)
            weights.append(4)  # High priority for pending follow-ups

        # Check for person callbacks
        person_callback = self._get_person_callback()
        if person_callback:
            callbacks.append(person_callback)
            weights.append(2)

        # Check for anniversary callbacks
        anniversary_callback = self._get_anniversary_callback()
        if anniversary_callback:
            callbacks.append(anniversary_callback)
            weights.append(5)  # High priority for milestones

        # Check for time context callbacks
        time_callback = self._get_time_callback()
        if time_callback:
            callbacks.append(time_callback)
            weights.append(1)

        # Check for vibe callbacks (requires heart)
        vibe_callback = self._get_vibe_callback(context)
        if vibe_callback:
            callbacks.append(vibe_callback)
            weights.append(2)

        if not callbacks:
            return None

        # Weighted random selection
        callback = random.choices(callbacks, weights=weights[:len(callbacks)])[0]

        # Record this callback
        self._record_callback(callback)

        return callback

    def _get_topic_callback(self, context: Dict[str, Any]) -> Optional[str]:
        """Get a callback related to the current topic"""
        current_message = context.get("message", "").lower()

        # Check if current message relates to any tracked topics
        for topic_key, tracked in self.topics.items():
            if topic_key in current_message and tracked.times_mentioned > 1:
                # Check if we haven't callback'd recently
                if tracked.last_callback:
                    last = datetime.fromisoformat(tracked.last_callback)
                    hours = (datetime.now() - last).total_seconds() / 3600
                    if hours < self.TOPIC_CALLBACK_HOURS:
                        continue

                template = random.choice(CALLBACKS["same_topic"])
                tracked.last_callback = datetime.now().isoformat()
                return template

        return None

    def _get_followup_callback(self) -> Optional[str]:
        """Get a follow-up callback for pending topics"""
        followup_topics = [
            t for t in self.topics.values()
            if t.followup_worthy and (
                not t.last_callback or
                (datetime.now() - datetime.fromisoformat(t.last_callback)).total_seconds() / 3600 > 24
            )
        ]

        if not followup_topics:
            return None

        topic = random.choice(followup_topics)
        template = random.choice(CALLBACKS["follow_up"])

        # Mark as callback'd
        topic.last_callback = datetime.now().isoformat()
        topic.followup_worthy = False  # Reset after callback

        return template

    def _get_person_callback(self) -> Optional[str]:
        """Get a callback about a person"""
        stale_people = self._get_stale_people()

        if not stale_people:
            return None

        person = random.choice(stale_people)
        template = random.choice(CALLBACKS["callback_person"])

        # Mark as callback'd
        person.last_callback = datetime.now().isoformat()

        return template.format(person=person.name)

    def _get_stale_people(self) -> List[TrackedPerson]:
        """Get people we haven't asked about in a while"""
        stale = []

        for person in self.people.values():
            if person.last_callback:
                last = datetime.fromisoformat(person.last_callback)
                days = (datetime.now() - last).days
                if days >= self.PERSON_CALLBACK_DAYS:
                    stale.append(person)
            else:
                # Never asked about them
                mentioned = datetime.fromisoformat(person.mentioned_at)
                days = (datetime.now() - mentioned).days
                if days >= 1:  # At least a day since they were mentioned
                    stale.append(person)

        return stale

    def _get_anniversary_callback(self) -> Optional[str]:
        """Get an anniversary callback if applicable"""
        if not self.first_conversation:
            return None

        first = datetime.fromisoformat(self.first_conversation)
        days = (datetime.now() - first).days

        # Check if today is an anniversary
        if days not in self.ANNIVERSARY_DAYS:
            return None

        # Format time string
        if days == 7:
            time_str = "a week"
        elif days == 30:
            time_str = "a month"
        elif days == 90:
            time_str = "3 months"
        elif days == 180:
            time_str = "6 months"
        elif days == 365:
            time_str = "a whole year"
        else:
            time_str = f"{days} days"

        template = random.choice(CALLBACKS["anniversary"])
        return template.format(time=time_str)

    def _get_time_callback(self) -> Optional[str]:
        """Get a time-of-day based callback"""
        hour = datetime.now().hour

        # Only do time callbacks occasionally
        if random.random() > 0.1:
            return None

        # Late night (past midnight)
        if 0 <= hour < 5:
            return "you're up late again"
        # Early morning
        elif 5 <= hour < 9:
            return random.choice(["early bird today huh", "you're up early"])
        # Usual patterns (evening)
        elif 18 <= hour < 22:
            if random.random() > 0.7:
                return "this is about when you usually message me"

        return None

    def _get_vibe_callback(self, context: Dict[str, Any]) -> Optional[str]:
        """Get a callback based on emotional state changes"""
        if not self.heart:
            return None

        # Only do vibe callbacks occasionally
        if random.random() > 0.15:
            return None

        # Get current emotion state
        state = self.heart.get_state()

        # Check if we can get memory context
        if hasattr(self.heart, 'memory') and self.heart.memory:
            mood_ctx = self.heart.memory.get_mood_context()
            if mood_ctx:
                current_mood = state.get("mood", "neutral")

                # If they seem happier than usual
                if state.get("joy", 0) > 0.6 and "down" in mood_ctx.lower():
                    return random.choice([
                        "you seem happier today than last time",
                        "glad to see you in better spirits",
                    ])

                # If they seem down when usually happy
                if state.get("sadness", 0) > 0.5 and "happy" in mood_ctx.lower():
                    return "you were doing so good last time - everything ok?"

        return None

    def _record_callback(self, callback: str):
        """Record that we did a callback"""
        self._last_callback_time = datetime.now()

        self.callback_history.append({
            "callback": callback,
            "timestamp": datetime.now().isoformat(),
        })

        self._save()

    # -------------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------------

    def get_pending_callback(self) -> Optional[str]:
        """Get the pending callback (if any) from the last thinking cycle"""
        return self._pending_callback

    def clear_pending_callback(self):
        """Clear the pending callback after it's been used"""
        self._pending_callback = None

    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about tracked data"""
        followup_count = sum(1 for t in self.topics.values() if t.followup_worthy)
        stale_people_count = len(self._get_stale_people())

        # Calculate relationship duration
        duration_days = 0
        if self.first_conversation:
            first = datetime.fromisoformat(self.first_conversation)
            duration_days = (datetime.now() - first).days

        return {
            "total_conversations": self.total_conversations,
            "tracked_topics": len(self.topics),
            "tracked_people": len(self.people),
            "pending_followups": followup_count,
            "stale_people": stale_people_count,
            "relationship_days": duration_days,
            "total_callbacks": len(self.callback_history),
        }

    def get_context_for_response(self) -> Optional[str]:
        """
        Get contextual callback to potentially include in a response.
        This is the main method to call when generating a response.

        Returns:
            A callback string to include, or None
        """
        callback = self.get_pending_callback()
        if callback:
            self.clear_pending_callback()
            return callback
        return None

    def reset_topic(self, topic: str):
        """Reset a topic's tracking data"""
        topic_key = topic.lower().strip()
        if topic_key in self.topics:
            del self.topics[topic_key]
            self._save()

    def reset_person(self, name: str):
        """Reset a person's tracking data"""
        name_key = name.lower().strip()
        if name_key in self.people:
            del self.people[name_key]
            self._save()

    def clear_all(self):
        """Clear all tracking data"""
        self.topics.clear()
        self.people.clear()
        self.callback_history.clear()
        self.first_conversation = None
        self.total_conversations = 0
        self._last_callback_time = None
        self._pending_callback = None
        self._save()
