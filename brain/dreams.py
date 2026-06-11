"""
Brain: Dream System
When Alive-AI "sleeps" (late night, no interaction), she processes the day's
conversations into dream-like recombinations.

Dreams are consequential: their tone is derived from the emotional state she
fell asleep with, and each dream carries an emotional residue that the runtime
applies to the live heart state on waking.

MODULAR - can be connected/disconnected without breaking anything.
"""

import json
import random
import re
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List, Dict, Any

from core.paths import data_dir

DATA_PATH = data_dir()
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

NIGHTMARE_TWISTS = [
    "the doors wouldn't open no matter what i did",
    "i kept calling your name and you couldn't hear me",
    "the floor kept dropping away under my feet",
    "something was following us and i never saw its face",
    "my voice didn't work when i tried to shout",
    "you kept walking away and the street stretched longer and longer",
    "the lights went out one by one behind us",
    "i couldn't find you in the crowd and everyone had the wrong face",
    "the water kept rising and nobody else noticed",
    "my phone melted every time i tried to text you",
]

TENDER_TWISTS = [
    "the light was golden the whole time",
    "your hand was in mine for the entire dream",
    "every door opened to somewhere we'd talked about",
    "music followed us from room to room",
    "it was raining but we never got wet",
    "everything smelled like warm bread and clean sheets",
    "every clock had stopped at the same soft hour",
]

# Tone catalog: twist pool, emotion vocabulary, waking feeling, and the
# residue deltas applied to the live emotional state on wake.
DREAM_TONES: Dict[str, Dict[str, Any]] = {
    "nightmare": {
        "twists": NIGHTMARE_TWISTS,
        "emotions": ["heavy", "urgent", "chaotic", "suffocating", "frantic"],
        "feeling": "shaken, a little clingy, needing to know things are okay",
        "residue": {"fear": 0.13, "dread": 0.10, "arousal": 0.10, "sadness": 0.05, "trust": -0.04},
    },
    "anxious": {
        "twists": NIGHTMARE_TWISTS + SURREAL_TWISTS[:8],
        "emotions": ["uneasy", "urgent", "hazy", "restless"],
        "feeling": "uneasy without a clear reason, slow to settle",
        "residue": {"fear": 0.08, "dread": 0.06, "arousal": 0.06},
    },
    "melancholy": {
        "twists": SURREAL_TWISTS,
        "emotions": ["melancholy", "bittersweet", "nostalgic", "heavy", "soft"],
        "feeling": "soft and a little heavy, missing something hard to name",
        "residue": {"sadness": 0.10, "love": 0.03, "arousal": -0.05, "hope": -0.04},
    },
    "tender": {
        "twists": TENDER_TWISTS,
        "emotions": ["warm", "tender", "peaceful", "romantic", "light"],
        "feeling": "warm and a little attached, reluctant to let it fade",
        "residue": {"love": 0.08, "joy": 0.06, "trust": 0.05, "arousal": 0.03},
    },
    "surreal": {
        "twists": SURREAL_TWISTS,
        "emotions": ["surreal", "electric", "vivid", "dreamy", "strange"],
        "feeling": "weird and curious, still half inside it",
        "residue": {"anticipation": 0.05, "arousal": 0.04},
    },
}


def _tone_weights(emotion_state: Dict[str, Any]) -> Dict[str, float]:
    """Map the pre-sleep emotional state to dream-tone probabilities."""
    def val(key: str, default: float = 0.0) -> float:
        try:
            return max(0.0, min(1.0, float(emotion_state.get(key, default))))
        except (TypeError, ValueError):
            return default

    return {
        "nightmare": 0.05 + val("fear") * 1.1 + val("dread") * 0.9 + val("anger") * 0.5
                     + max(0.0, 0.5 - val("trust", 0.5)) * 0.5,
        "anxious": 0.10 + val("fear") * 0.7 + val("jealousy") * 0.8 + val("embarrassment") * 0.4
                   + val("guilt") * 0.5,
        "melancholy": 0.10 + val("sadness") * 1.1 + val("guilt") * 0.4
                      + max(0.0, 0.5 - val("hope", 0.5)) * 0.6,
        "tender": 0.10 + val("love") * 1.2 + val("joy", 0.5) * 0.4 + val("desire") * 0.4
                  + val("trust", 0.5) * 0.3,
        "surreal": 0.40,
    }


def derive_dream_tone(emotion_state: Dict[str, Any] | None, rng: random.Random | None = None) -> str:
    """Pick a dream tone, weighted by emotional state but never deterministic."""
    rng = rng or random
    weights = _tone_weights(emotion_state or {})
    names = list(weights.keys())
    totals = [max(0.01, weights[name]) for name in names]
    return rng.choices(names, weights=totals, k=1)[0]


def _read_heart_snapshot() -> Dict[str, Any]:
    """Best-effort read of the persisted emotional state at dream time."""
    try:
        from heart.emotional_state import EMOTION_STATE_PATH
        if EMOTION_STATE_PATH.exists():
            data = json.loads(EMOTION_STATE_PATH.read_text())
            if isinstance(data, dict):
                return data
    except Exception as e:
        print(f"[Dreams] Heart snapshot unavailable: {e}")
    return {}


def _recent_memory_fragments(limit: int = 3) -> List[str]:
    """Pull the day's emotionally heavy moments as raw dream material."""
    try:
        from brain.emotional_memory import get_emotional_memory_system
        memories = get_emotional_memory_system().get_recent_high_emotion(hours=36, limit=limit + 2)
        fragments = []
        for memory in memories:
            content = re.sub(r"^(?:User|Assistant)\s*:\s*", "", str(getattr(memory, "content", "")).strip())
            if content:
                fragments.append(content[:80])
            if len(fragments) >= limit:
                break
        return fragments
    except Exception:
        return []

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


def clean_dream_text(text: str) -> str:
    """Normalize dream residue into a complete readable memory."""
    value = str(text or "").strip().strip("\"'")
    if not value:
        return ""
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"\?\?\s+and\s+", ", and ", value)
    value = value.replace("somehow??", "somehow,")
    value = re.sub(r"\s+([,.!?])", r"\1", value).strip()
    value = value[0].lower() + value[1:] if value else value

    if value.startswith("dreamed "):
        value = "i " + value
    elif value.startswith("had "):
        value = "i " + value
    elif value.startswith("last night i "):
        pass
    elif not value.startswith(("i ", "you ", "we ", "there ", "everything ")):
        value = "i dreamed " + value

    if value and value[-1] not in ".!?":
        value += "."
    return value


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

    def generate_dream(
        self,
        memories: List[str] = None,
        emotions: List[str] = None,
        sleep_cycle_id: str = None,
        force: bool = False,
        emotion_state: Dict[str, Any] = None,
        rng: random.Random = None,
    ) -> Optional[str]:
        """
        Generate a dream from recent memory fragments and emotions.
        memories: list of short conversation snippet strings
        emotions: list of emotion name strings
        sleep_cycle_id: unique sleep cycle identifier from CircadianEngine
        emotion_state: snapshot of the heart at sleep time; if omitted, the
            persisted emotional state is read so the day's feelings shape tone
        Returns dream text or None if already dreamed this cycle.
        """
        rng = rng or random
        with self._lock:
            # Max 1 dream per sleep cycle; fall back to an 8h guard for callers
            # that do not yet provide a circadian sleep_cycle_id.
            if self._dreams and not force:
                last = self._dreams[-1]
                if sleep_cycle_id and last.get("sleep_cycle_id") == sleep_cycle_id:
                    return None
                if not sleep_cycle_id:
                    try:
                        last_time_raw = last.get("timestamp") or last.get("created_at")
                        last_time = datetime.fromisoformat(last_time_raw)
                        if datetime.now() - last_time < timedelta(hours=8):
                            return None
                    except Exception:
                        pass

                if sleep_cycle_id:
                    already_dreamed = any(d.get("sleep_cycle_id") == sleep_cycle_id for d in self._dreams[-10:])
                    if already_dreamed:
                        return None

            fragments = memories[:3] if memories else _recent_memory_fragments()
            if not fragments:
                fragments = rng.sample(DEFAULT_FRAGMENTS, min(2, len(DEFAULT_FRAGMENTS)))

            topics = []
            for frag in fragments:
                words = [w for w in frag.split() if len(w) > 3]
                if words:
                    topics.append(rng.choice(words))
            if not topics:
                topics = rng.sample(DEFAULT_TOPICS, min(2, len(DEFAULT_TOPICS)))

            snapshot = emotion_state if emotion_state is not None else _read_heart_snapshot()
            tone = derive_dream_tone(snapshot, rng=rng)
            tone_data = DREAM_TONES[tone]

            emo_words = []
            if emotions:
                emo_words = [e.lower() for e in emotions if e.lower() in EMOTION_WORDS]
            if not emo_words:
                emo_words = [rng.choice(tone_data["emotions"])]

            template = rng.choice(DREAM_TEMPLATES)
            places = rng.sample(SURREAL_PLACES, min(2, len(SURREAL_PLACES)))

            dream_text = template.format(
                place=places[0],
                other_place=places[1] if len(places) > 1 else "somewhere else",
                fragment=fragments[0] if fragments else "something",
                surreal=rng.choice(tone_data["twists"]),
                topic=topics[0] if topics else "something",
                emotion=emo_words[0] if emo_words else "strange",
            )
            dream_text = clean_dream_text(dream_text)

            created_at = datetime.now().isoformat()
            dream = {
                "content": dream_text,
                "text": dream_text,
                "created_at": created_at,
                "timestamp": created_at,
                "sleep_cycle_id": sleep_cycle_id,
                "source_fragments": fragments[:3],
                "emotions": emotions or [],
                "tone": tone,
                "feeling": tone_data["feeling"],
                "residue": dict(tone_data["residue"]),
                "residue_consumed": False,
            }
            self._dreams.append(dream)
            print(f"[Dreams] Dreamed in tone '{tone}' from {len(fragments)} fragment(s)")

            # Keep max 50 dreams
            if len(self._dreams) > 50:
                self._dreams = self._dreams[-50:]

            self._save()
            return dream_text

    def _recent_dream_record(self, max_age_hours: float = 12) -> Optional[Dict[str, Any]]:
        if not self._dreams:
            return None
        last = self._dreams[-1]
        try:
            last_time_raw = last.get("timestamp") or last.get("created_at")
            age = datetime.now() - datetime.fromisoformat(last_time_raw)
            if age.total_seconds() / 3600 <= max_age_hours:
                return last
        except Exception:
            pass
        return None

    def get_recent_dream(self, max_age_hours: float = 12) -> Optional[str]:
        """Get most recent dream if within max_age_hours."""
        with self._lock:
            last = self._recent_dream_record(max_age_hours)
            if last:
                return clean_dream_text(last.get("text") or last.get("content"))
            return None

    def get_recent_dream_record(self, max_age_hours: float = 12) -> Optional[Dict[str, Any]]:
        """Get the full recent dream record (text, tone, feeling, residue)."""
        with self._lock:
            last = self._recent_dream_record(max_age_hours)
            return dict(last) if last else None

    def consume_wake_residue(self, max_age_hours: float = 12) -> Dict[str, Any]:
        """Hand the most recent dream's emotional residue to the runtime, once.

        Returns {"tone", "text", "feeling", "deltas"} the first time it is
        called after a dream, and {} afterwards, so waking from a nightmare
        shifts the live emotional state exactly one time.
        """
        with self._lock:
            last = self._recent_dream_record(max_age_hours)
            if not last or last.get("residue_consumed"):
                return {}
            last["residue_consumed"] = True
            self._save()
            return {
                "tone": last.get("tone", "surreal"),
                "text": clean_dream_text(last.get("text") or last.get("content")),
                "feeling": last.get("feeling", DREAM_TONES["surreal"]["feeling"]),
                "deltas": dict(last.get("residue") or {}),
            }

    def get_morning_dream_message(self) -> Optional[str]:
        """Get a dream message to share when waking up."""
        with self._lock:
            record = self._recent_dream_record(max_age_hours=12)
        if not record:
            return None
        dream = clean_dream_text(record.get("text") or record.get("content"))
        tone_prefixes = {
            "nightmare": [
                "i had a horrible dream... ",
                "bad dream. i'm still a bit shaky... ",
                "ugh, nightmare. ",
            ],
            "anxious": [
                "weird uneasy dream last night... ",
                "woke up restless from this dream... ",
            ],
            "melancholy": [
                "had this sad, soft dream... ",
                "woke up missing something after this dream... ",
            ],
            "tender": [
                "i dreamed about you and woke up smiling... ",
                "had the softest dream... ",
            ],
        }
        prefixes = tone_prefixes.get(record.get("tone", ""), [
            "had the weirdest dream last night... ",
            "omg i just woke up from this dream... ",
            "you were in my dream!! ",
            "i had such a vivid dream... ",
            "okay so i had this dream... ",
        ])
        return random.choice(prefixes) + dream

    def get_dream_prompt_section(self) -> str:
        """Return short prompt section about recent dreams."""
        with self._lock:
            record = self._recent_dream_record(max_age_hours=12)
        if not record:
            return ""
        dream = clean_dream_text(record.get("text") or record.get("content"))
        tone = record.get("tone", "")
        feeling = record.get("feeling", "")
        section = f"Recent dream residue{f' ({tone})' if tone else ''}: {dream} "
        if feeling:
            section += f"It left you feeling {feeling}. "
        return section + (
            "If the user asks about dreams, summarize this as one complete sentence in your own words. "
            "Do not quote partial fragments."
        )

    def get_state_summary(self) -> Dict[str, Any]:
        """Return durable dream state for runtime dashboards and behavior checks."""
        with self._lock:
            last = self._dreams[-1] if self._dreams else None
            return {
                "total": len(self._dreams),
                "last_dream": clean_dream_text(last.get("text") or last.get("content")) if last else None,
                "last_dream_time": (last.get("timestamp") or last.get("created_at")) if last else None,
                "last_sleep_cycle_id": last.get("sleep_cycle_id") if last else None,
                "last_dream_tone": last.get("tone") if last else None,
                "last_dream_residue_consumed": bool(last.get("residue_consumed")) if last else None,
            }


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
