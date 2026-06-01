"""
Brain: Linguistic Absorption System
Alive-AI gradually absorbs the user's speech patterns - slang, emoji habits,
abbreviations, punctuation style, capitalization, message length.

MODULAR - can be connected/disconnected without breaking anything.
"""

import json
import re
import threading
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional

DATA_PATH = Path(__file__).parent.parent / "data"

# Common words to exclude from frequency tracking
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "i", "you", "he", "she", "it",
    "we", "they", "my", "your", "his", "her", "its", "our", "their", "me", "him",
    "us", "them", "to", "of", "in", "for", "on", "at", "with", "and", "or", "but",
    "not", "do", "have", "be", "this", "that", "what", "how", "who", "which",
    "when", "where", "why", "so", "if", "then", "than", "just", "like", "can",
    "will", "would", "could", "should", "did", "does", "had", "has", "been",
    "being", "get", "got", "go", "going", "went", "come", "came", "know", "think",
    "want", "need", "see", "look", "make", "take", "give", "say", "said", "tell",
    "told", "about", "up", "out", "no", "yes", "ok", "okay", "yeah", "yep",
    "from", "by", "as", "all", "some", "any", "more", "very", "really", "too",
    "also", "well", "now", "here", "there", "im", "dont", "its", "thats", "ill",
    "ive", "youre", "hes", "shes", "were", "theyre", "cant", "wont", "didnt",
    "doesnt", "isnt", "arent", "wasnt", "havent", "hadnt", "wouldnt", "couldnt",
    "shouldnt", "one", "thing", "way", "even", "still", "back", "only", "much",
}

# Known abbreviations to track
KNOWN_ABBREVS = {
    "u", "ur", "yk", "ngl", "fr", "rn", "tbh", "imo", "smh", "lol", "lmao",
    "omg", "brb", "idk", "nvm", "btw", "irl", "af", "lowkey", "highkey", "pls",
    "plz", "thx", "ty", "np", "ofc", "icl", "istg", "wbu", "hbu", "fyi", "tho",
    "cuz", "cus", "bc", "w", "rly", "srsly", "jk", "haha", "hehe", "nah",
}

ABSORPTION_THRESHOLD = 10  # occurrences before a pattern is "absorbed"
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols
    "\U0001F680-\U0001F6FF"  # transport
    "\U0001F1E0-\U0001F1FF"  # flags
    "\U00002702-\U000027B0"
    "\U000024C2-\U0001F251"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FA6F"
    "\U0001FA70-\U0001FAFF"
    "]+", flags=re.UNICODE
)


class LinguisticProfile:
    def __init__(self, user_id: str):
        self.user_id = user_id
        self._lock = threading.RLock()
        self.file_path = DATA_PATH / f"linguistic_{user_id}.json"
        self.frequent_words: Counter = Counter()
        self.emoji_counts: Counter = Counter()
        self.abbreviation_counts: Counter = Counter()
        self.punctuation_counts: Counter = Counter()  # tracks "...", "!!", "??" etc
        self.total_messages: int = 0
        self.total_chars: int = 0
        self.lowercase_count: int = 0  # messages that are all lowercase
        self.uppercase_count: int = 0  # messages with normal capitalization
        self._load()

    def _load(self):
        try:
            if self.file_path.exists():
                with open(self.file_path, 'r') as f:
                    d = json.load(f)
                self.frequent_words = Counter(d.get("frequent_words", {}))
                self.emoji_counts = Counter(d.get("emoji_counts", {}))
                self.abbreviation_counts = Counter(d.get("abbreviation_counts", {}))
                self.punctuation_counts = Counter(d.get("punctuation_counts", {}))
                self.total_messages = d.get("total_messages", 0)
                self.total_chars = d.get("total_chars", 0)
                self.lowercase_count = d.get("lowercase_count", 0)
                self.uppercase_count = d.get("uppercase_count", 0)
        except Exception as e:
            print(f"[Linguistic] Load error for {self.user_id}: {e}")

    def _save(self):
        try:
            DATA_PATH.mkdir(parents=True, exist_ok=True)
            data = {
                "user_id": self.user_id,
                "updated": datetime.now().isoformat(),
                "frequent_words": dict(self.frequent_words.most_common(50)),
                "emoji_counts": dict(self.emoji_counts.most_common(20)),
                "abbreviation_counts": dict(self.abbreviation_counts.most_common(20)),
                "punctuation_counts": dict(self.punctuation_counts.most_common(10)),
                "total_messages": self.total_messages,
                "total_chars": self.total_chars,
                "lowercase_count": self.lowercase_count,
                "uppercase_count": self.uppercase_count,
            }
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"[Linguistic] Save error for {self.user_id}: {e}")

    def absorb(self, message: str):
        """Analyze a user message and update linguistic patterns."""
        with self._lock:
            if not message or not message.strip():
                return

            self.total_messages += 1
            self.total_chars += len(message)

            # Capitalization: check if alphabetic chars are mostly lowercase
            alpha = [c for c in message if c.isalpha()]
            if alpha:
                lower_ratio = sum(1 for c in alpha if c.islower()) / len(alpha)
                if lower_ratio > 0.9:
                    self.lowercase_count += 1
                else:
                    self.uppercase_count += 1

            # Emojis
            for match in EMOJI_PATTERN.finditer(message):
                for ch in match.group():
                    self.emoji_counts[ch] += 1

            # Punctuation patterns
            for pat in re.findall(r'[.]{2,}|[!]{2,}|[?]{2,}|[?!]{2,}', message):
                normalized = pat[0] + pat[0]  # normalize "..." and ".." both to ".."
                self.punctuation_counts[normalized] += 1

            # Words
            words = re.findall(r'[a-zA-Z]+', message.lower())
            for word in words:
                if word in KNOWN_ABBREVS:
                    self.abbreviation_counts[word] += 1
                elif word not in STOP_WORDS and len(word) > 2:
                    self.frequent_words[word] += 1

            # Save every 5 messages
            if self.total_messages % 5 == 0:
                self._save()

    def force_save(self):
        with self._lock:
            self._save()

    def get_absorbed_patterns(self) -> Dict:
        """Get patterns that have crossed the absorption threshold."""
        with self._lock:
            return {
                "words": [w for w, c in self.frequent_words.most_common(20) if c >= ABSORPTION_THRESHOLD],
                "emojis": [e for e, c in self.emoji_counts.most_common(10) if c >= ABSORPTION_THRESHOLD],
                "abbreviations": [a for a, c in self.abbreviation_counts.most_common(10) if c >= ABSORPTION_THRESHOLD],
                "punctuation": [p for p, c in self.punctuation_counts.most_common(5) if c >= ABSORPTION_THRESHOLD],
                "avg_length": round(self.total_chars / max(1, self.total_messages)),
                "uses_lowercase": self.lowercase_count > self.uppercase_count * 2 if self.total_messages > 20 else None,
            }

    def get_prompt_section(self) -> str:
        """Return 1-2 line prompt section describing user's style to mirror."""
        with self._lock:
            if self.total_messages < 20:
                return ""

            patterns = self.get_absorbed_patterns()
            parts = []

            # Capitalization
            if patterns["uses_lowercase"] is True:
                parts.append("lowercase")
            elif patterns["uses_lowercase"] is False:
                parts.append("normal caps")

            # Message length
            avg = patterns["avg_length"]
            if avg < 40:
                parts.append("short msgs")
            elif avg > 150:
                parts.append("long msgs")

            # Abbreviations
            if patterns["abbreviations"]:
                abbrs = " ".join(f"'{a}'" for a in patterns["abbreviations"][:5])
                parts.append(f"uses {abbrs}")

            # Punctuation
            if patterns["punctuation"]:
                puncts = " ".join(f"'{p}'" for p in patterns["punctuation"][:3])
                parts.append(f"lots of {puncts}")

            # Emojis
            if patterns["emojis"]:
                parts.append(f"loves {''.join(patterns['emojis'][:5])}")

            if not parts:
                return ""

            return f"Match his vibe: {', '.join(parts)}"


# Per-user singleton management
_profiles: Dict[str, LinguisticProfile] = {}
_profiles_lock = threading.Lock()


def get_linguistic_profile(user_id: str) -> LinguisticProfile:
    with _profiles_lock:
        if user_id not in _profiles:
            _profiles[user_id] = LinguisticProfile(user_id)
        return _profiles[user_id]


def absorb(user_id: str, message: str):
    """Top-level convenience: absorb a message for a user."""
    try:
        get_linguistic_profile(user_id).absorb(message)
    except Exception:
        pass


def get_linguistic_prompt_section(user_id: str) -> str:
    """Safe top-level access for prompt building."""
    try:
        return get_linguistic_profile(user_id).get_prompt_section()
    except Exception:
        return ""
