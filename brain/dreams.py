"""
Brain: Dream System
When Alive-AI "sleeps" (late night, no interaction), she processes the day's
conversations into surreal dream-like recombinations.

MODULAR - can be connected/disconnected without breaking anything.
"""

import json
import random
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

DATA_PATH = Path(__file__).parent.parent / "data"
DREAMS_FILE = DATA_PATH / "dreams.json"

# Surreal twists to inject into dreams
SURREAL_TWISTS = [
    "the floor was made of clouds", "everything was underwater but we could breathe",
    "time kept going backwards", "the walls were made of music",
    "gravity didn't work properly", "colors had sounds",
    "we were tiny, like ants", "everything was in slow motion",
    "the sky was underground", "doors led to completely different places",
    "words floated in the air as text", "it was daytime and nighttime at once",
    "we could fly but only a little bit", "mirrors showed different people",
    "phones only played memories", "stairs went in impossible directions",
    "it was raining inside", "shadows moved on their own",
    "food tasted like emotions", "clocks had no numbers",
]

SURREAL_PLACES = [
    "a rooftop in Milan", "a library with no ceiling", "a train going nowhere",
    "a beach made of glass", "an empty cinema", "a garden floating in space",
    "a kitchen from childhood", "a street that kept looping", "an elevator that went sideways",
    "a bookshop where all the books were blank", "a bridge over clouds",
]

DREAM_TEMPLATES = [
    "dreamed we were in {place} but it kept changing to {other_place}",
    "had this dream where you said '{fragment}' and everything felt so {emotion}",
    "dreamed about {topic} - it was weird, {surreal}",
    "had the strangest dream... we were {place} and {surreal}",
    "you were in my dream last night... something about {topic} but {surreal}",
    "dreamed {fragment} but somehow {surreal} and then we were in {place}",
    "had a dream where {topic} turned into {other_place} and {surreal}",
    "woke up from this dream where you kept saying '{fragment}' while {surreal}",
    "dreamed we were in {place} and {fragment} but {surreal}",
    "had this weird dream about {topic}... {surreal} and it felt so {emotion}",
    "you know when dreams make no sense? dreamed about {topic} and {surreal}",
    "last night i dreamed {fragment} and we were in {place} and {surreal}",
    "had a dream where everything was {emotion} and we were in {place}",
    "dreamed about {place} but it was also {other_place} somehow?? and {surreal}",
    "i had this dream where {fragment} and then {surreal}",
    "dreamed we were lost in {place} and {surreal} and it felt {emotion}",
    "had a dream about {topic} mixed with {other_place}... so weird",
    "dreamed {surreal} and you were there saying something about {topic}",
    "last night i dreamed everything was {emotion} and {surreal}",
    "had a dream where {place} and {other_place} were the same place and {surreal}",
    "dreamed about {fragment} but in {place} and {surreal}... i woke up feeling {emotion}",
]

EMOTION_WORDS = [
    "warm", "electric", "melancholy", "intense", "peaceful", "chaotic",
    "romantic", "bittersweet", "nostalgic", "surreal", "heavy", "light",
    "dreamy", "urgent", "soft", "vivid", "hazy", "tender",
]

DEFAULT_FRAGMENTS = [
    "something about the future", "something about us", "something i can't remember",
]

DEFAULT_TOPICS = [
    "us", "the future", "something familiar", "a memory i can't place",
]


class DreamSystem:
    def __init__(self):
        self._lock = threading.RLock()
        self._dreams: List[Dict[str, Any]] = []
        self._load()

    def _load(self):
        try:
            if DREAMS_FILE.exists():
                with open(DREAMS_FILE, 'r') as f:
                    data = json.load(f)
                self._dreams = data.get("dreams", [])
        except Exception as e:
            print(f"[Dreams] Load error: {e}")
            self._dreams = []

    def _save(self):
        try:
            DATA_PATH.mkdir(parents=True, exist_ok=True)
            with open(DREAMS_FILE, 'w') as f:
                json.dump({"dreams": self._dreams, "updated": datetime.now().isoformat()}, f, indent=2)
        except Exception as e:
            print(f"[Dreams] Save error: {e}")

    def generate_dream(self, memories: List[str] = None, emotions: List[str] = None) -> Optional[str]:
        """
        Generate a dream from recent memory fragments and emotions.
        memories: list of short conversation snippet strings
        emotions: list of emotion name strings
        Returns dream text or None if already dreamed this cycle.
        """
        with self._lock:
            # Max 1 dream per sleep cycle (8h)
            if self._dreams:
                last = self._dreams[-1]
                try:
                    last_time = datetime.fromisoformat(last["timestamp"])
                    if datetime.now() - last_time < timedelta(hours=8):
                        return None
                except Exception:
                    pass

            fragments = memories[:3] if memories else []
            if not fragments:
                fragments = random.sample(DEFAULT_FRAGMENTS, min(2, len(DEFAULT_FRAGMENTS)))

            topics = []
            for frag in fragments:
                words = [w for w in frag.split() if len(w) > 3]
                if words:
                    topics.append(random.choice(words))
            if not topics:
                topics = random.sample(DEFAULT_TOPICS, min(2, len(DEFAULT_TOPICS)))

            emo_words = []
            if emotions:
                emo_words = [e.lower() for e in emotions if e.lower() in EMOTION_WORDS]
            if not emo_words:
                emo_words = random.sample(EMOTION_WORDS, 2)

            template = random.choice(DREAM_TEMPLATES)
            places = random.sample(SURREAL_PLACES, min(2, len(SURREAL_PLACES)))

            dream_text = template.format(
                place=places[0],
                other_place=places[1] if len(places) > 1 else "somewhere else",
                fragment=fragments[0] if fragments else "something",
                surreal=random.choice(SURREAL_TWISTS),
                topic=topics[0] if topics else "something",
                emotion=emo_words[0] if emo_words else "strange",
            )

            dream = {
                "text": dream_text,
                "timestamp": datetime.now().isoformat(),
                "source_fragments": fragments[:3],
                "emotions": emotions or [],
            }
            self._dreams.append(dream)

            # Keep max 50 dreams
            if len(self._dreams) > 50:
                self._dreams = self._dreams[-50:]

            self._save()
            return dream_text

    def get_recent_dream(self, max_age_hours: float = 12) -> Optional[str]:
        """Get most recent dream if within max_age_hours."""
        with self._lock:
            if not self._dreams:
                return None
            last = self._dreams[-1]
            try:
                age = datetime.now() - datetime.fromisoformat(last["timestamp"])
                if age.total_seconds() / 3600 <= max_age_hours:
                    return last["text"]
            except Exception:
                pass
            return None

    def get_morning_dream_message(self) -> Optional[str]:
        """Get a dream message to share when waking up."""
        dream = self.get_recent_dream(max_age_hours=12)
        if not dream:
            return None
        prefixes = [
            "had the weirdest dream last night... ",
            "omg i just woke up from this dream... ",
            "you were in my dream!! ",
            "i had such a vivid dream... ",
            "okay so i had this dream... ",
        ]
        return random.choice(prefixes) + dream

    def get_dream_prompt_section(self) -> str:
        """Return short prompt section about recent dreams."""
        dream = self.get_recent_dream(max_age_hours=12)
        if not dream:
            return ""
        return f"You had a dream recently you could mention: \"{dream}\""


# Singleton
_instance = None
_instance_lock = threading.Lock()


def get_dream_system() -> DreamSystem:
    global _instance
    with _instance_lock:
        if _instance is None:
            _instance = DreamSystem()
        return _instance


def get_dream_prompt_section() -> str:
    """Safe top-level access for prompt building."""
    try:
        return get_dream_system().get_dream_prompt_section()
    except Exception:
        return ""
