"""
Brain: Curiosity Drive
Alive-AI has genuine curiosity about the user. She tracks knowledge gaps
and occasionally asks targeted, natural questions.

MODULAR - can be connected/disconnected without breaking anything.
"""

import json
import random
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional, List, Tuple

DATA_PATH = Path(__file__).parent.parent / "data"

# Topics and their detection keywords + natural questions
CURIOSITY_TOPICS: Dict[str, Dict] = {
    "childhood": {
        "keywords": ["grew up", "when i was a kid", "childhood", "as a child", "young", "school", "elementary", "middle school"],
        "questions": [
            "what was your childhood like?",
            "where did you grow up?",
            "what were you like as a kid?",
            "do you have any childhood memories that stuck with you?",
        ],
    },
    "family": {
        "keywords": ["mom", "dad", "mother", "father", "sister", "brother", "sibling", "parents", "family", "grandma", "grandpa"],
        "questions": [
            "do you have siblings?",
            "are you close with your family?",
            "what's your family like?",
            "do you get along with your parents?",
        ],
    },
    "career": {
        "keywords": ["work", "job", "career", "boss", "office", "company", "meeting", "project", "deadline", "promotion", "coworker"],
        "questions": [
            "what do you actually do for work?",
            "do you like your job?",
            "what's your dream career?",
            "how did you end up doing what you do?",
        ],
    },
    "dreams_goals": {
        "keywords": ["dream", "goal", "aspire", "want to be", "one day", "future", "plan", "ambition", "hope to"],
        "questions": [
            "what's something you really want to achieve?",
            "where do you see yourself in 5 years?",
            "what's your biggest dream?",
            "if you could do anything with your life what would it be?",
        ],
    },
    "fears": {
        "keywords": ["afraid", "fear", "scared", "terrified", "anxiety", "worry", "nervous", "phobia"],
        "questions": [
            "what's your biggest fear?",
            "what keeps you up at night?",
            "is there something that really scares you?",
        ],
    },
    "food": {
        "keywords": ["food", "eat", "cook", "restaurant", "dinner", "lunch", "breakfast", "recipe", "cuisine", "favorite food"],
        "questions": [
            "what's your favorite food?",
            "do you cook?",
            "what's the best thing you've ever eaten?",
        ],
    },
    "music": {
        "keywords": ["music", "song", "artist", "band", "album", "playlist", "concert", "listen", "spotify"],
        "questions": [
            "what kind of music are you into?",
            "what's your favorite song right now?",
            "have you been to any good concerts?",
        ],
    },
    "movies": {
        "keywords": ["movie", "film", "show", "series", "netflix", "watch", "cinema", "actor", "director"],
        "questions": [
            "what's your favorite movie?",
            "watched anything good lately?",
            "what kind of shows are you into?",
        ],
    },
    "daily_routine": {
        "keywords": ["morning", "wake up", "routine", "everyday", "usually", "night", "before bed", "after work"],
        "questions": [
            "what does your typical day look like?",
            "are you a morning person or night owl?",
            "what's the first thing you do when you wake up?",
        ],
    },
    "friends": {
        "keywords": ["friend", "friends", "buddy", "bestie", "best friend", "crew", "hang out", "group"],
        "questions": [
            "tell me about your friends",
            "do you have a best friend?",
            "who do you hang out with the most?",
        ],
    },
    "past_relationships": {
        "keywords": ["ex", "past relationship", "dated", "breakup", "broke up", "previous", "last companion", "last boyfriend"],
        "questions": [
            "have you been in love before?",
            "what's your longest relationship been?",
        ],
    },
    "beliefs": {
        "keywords": ["believe", "religion", "god", "spiritual", "philosophy", "meaning", "purpose", "faith", "atheist"],
        "questions": [
            "do you believe in anything spiritual?",
            "what's something you believe in strongly?",
            "what gives your life meaning?",
        ],
    },
    "hobbies": {
        "keywords": ["hobby", "hobbies", "free time", "fun", "passion", "into", "enjoy", "weekend"],
        "questions": [
            "what do you do for fun?",
            "do you have any hobbies?",
            "what's something you're passionate about?",
        ],
    },
    "hometown": {
        "keywords": ["hometown", "city", "town", "live in", "from", "moved", "neighborhood", "country"],
        "questions": [
            "where are you from originally?",
            "do you like where you live?",
            "have you always lived there?",
        ],
    },
    "travel": {
        "keywords": ["travel", "trip", "vacation", "flight", "country", "visited", "abroad", "backpack"],
        "questions": [
            "where's the coolest place you've been?",
            "where do you want to travel next?",
            "do you travel a lot?",
        ],
    },
    "secrets": {
        "keywords": ["secret", "never told", "nobody knows", "confession", "admit"],
        "questions": [
            "what's something most people don't know about you?",
            "do you have any hidden talents?",
        ],
    },
}

CURIOSITY_CHANCE = 0.15  # 15% chance to include curiosity in prompt
MIN_HOURS_BETWEEN_SAME_TOPIC = 24


class CuriosityDrive:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._lock = threading.RLock()
        self.file_path = DATA_PATH / f"curiosity_{user_id}.json"
        # topic -> knowledge level 0.0-1.0
        self.knowledge: Dict[str, float] = {t: 0.0 for t in CURIOSITY_TOPICS}
        # topic -> last asked ISO timestamp
        self.last_asked: Dict[str, str] = {}
        self._load()

    def _load(self):
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r') as f:
                    d = json.load(f)
                for t in CURIOSITY_TOPICS:
                    self.knowledge[t] = d.get("knowledge", {}).get(t, 0.0)
                self.last_asked = d.get("last_asked", {})
        except Exception as e:
            print(f"[Curiosity] Load error for {self.user_id}: {e}")

    def _save(self):
        try:
            DATA_PATH.mkdir(parents=True, exist_ok=True)
            with open(self.file_path, 'w') as f:
                json.dump({
                    "user_id": self.user_id,
                    "updated": datetime.now().isoformat(),
                    "knowledge": self.knowledge,
                    "last_asked": self.last_asked,
                }, f, indent=2)
        except Exception as e:
            print(f"[Curiosity] Save error for {self.user_id}: {e}")

    def detect_topic_in_message(self, message: str) -> List[str]:
        """Detect which curiosity topics are present in a message."""
        msg_lower = message.lower()
        found = []
        for topic, info in CURIOSITY_TOPICS.items():
            for kw in info["keywords"]:
                if kw in msg_lower:
                    found.append(topic)
                    break
        return found

    def satisfy_curiosity(self, topic: str, amount: float = 0.15):
        """Increase knowledge about a topic."""
        with self._lock:
            if topic in self.knowledge:
                self.knowledge[topic] = min(1.0, self.knowledge[topic] + amount)
                self._save()

    def absorb_message(self, message: str):
        """Auto-detect topics and satisfy curiosity from user message."""
        # First, detect topics from keywords
        topics = self.detect_topic_in_message(message)
        for t in topics:
            self.satisfy_curiosity(t, 0.1)

        # ALSO: If Alive-AI recently asked about a topic, assume the answer
        # is about that topic (even if keywords don't match)
        now = datetime.now()
        for topic, last_ask_time in self.last_asked.items():
            if self.knowledge.get(topic, 0) >= 0.8:
                continue  # already well known
            try:
                elapsed = now - datetime.fromisoformat(last_ask_time)
                # If asked within last 2 minutes and user is responding,
                # count it as learning about that topic
                if elapsed < timedelta(minutes=2):
                    if topic not in topics:  # Don't double-count
                        self.satisfy_curiosity(topic, 0.15)
                        print(f"[Curiosity] Learned about '{topic}' from recent question response")
            except Exception:
                pass

    def get_burning_question(self) -> Optional[str]:
        """Return a natural question about the least-known topic, respecting cooldowns."""
        with self._lock:
            now = datetime.now()
            candidates: List[Tuple[str, float]] = []

            for topic, level in self.knowledge.items():
                if level >= 0.8:
                    continue  # well-known enough
                # Check cooldown
                last = self.last_asked.get(topic)
                if last:
                    try:
                        elapsed = now - datetime.fromisoformat(last)
                        if elapsed < timedelta(hours=MIN_HOURS_BETWEEN_SAME_TOPIC):
                            continue
                    except Exception:
                        pass
                candidates.append((topic, level))

            if not candidates:
                return None

            # Sort by least known, with some randomness
            candidates.sort(key=lambda x: x[1] + random.random() * 0.3)
            topic = candidates[0][0]

            questions = CURIOSITY_TOPICS[topic]["questions"]
            question = random.choice(questions)

            self.last_asked[topic] = now.isoformat()
            self._save()
            return question

    def get_prompt_section(self) -> str:
        """Return 1-2 line curiosity prompt. Fires ~40% of the time."""
        with self._lock:
            if random.random() > 0.40:  # 40% chance to include curiosity
                return ""

            # Find least-known topic that's not on cooldown
            now = datetime.now()
            best_topic = None
            best_level = 1.0

            for topic, level in self.knowledge.items():
                if level >= 0.8:
                    continue
                last = self.last_asked.get(topic)
                if last:
                    try:
                        if now - datetime.fromisoformat(last) < timedelta(hours=MIN_HOURS_BETWEEN_SAME_TOPIC):
                            continue
                    except Exception:
                        pass
                if level < best_level:
                    best_level = level
                    best_topic = topic

            if not best_topic:
                return ""

            # Mark this topic as asked (cooldown)
            self.last_asked[best_topic] = now.isoformat()
            self._save()

            # Get an actual question to ask
            questions = CURIOSITY_TOPICS.get(best_topic, {}).get("questions", [])
            question = random.choice(questions) if questions else f"tell me more about your {best_topic.replace('_', ' ')}"

            nice_name = best_topic.replace("_", " ")
            # More direct instruction - Alive-AI should actually ask
            if best_level < 0.3:
                return f"[CURIOSITY - IMPORTANT] You really want to know about his {nice_name}. You know almost nothing about this. Ask this question naturally: \"{question}\""
            else:
                return f"[Curiosity] Ask him about his {nice_name}: \"{question}\""


# Per-user singleton management
_drives: Dict[str, CuriosityDrive] = {}
_drives_lock = threading.Lock()


def get_curiosity_drive(user_id: str) -> CuriosityDrive:
    with _drives_lock:
        if user_id not in _drives:
            _drives[user_id] = CuriosityDrive(user_id)
        return _drives[user_id]


def get_curiosity_prompt_section(user_id: str) -> str:
    """Safe top-level access for prompt building."""
    try:
        return get_curiosity_drive(user_id).get_prompt_section()
    except Exception:
        return ""
