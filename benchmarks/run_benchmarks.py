#!/usr/bin/env python3
"""Alive-AI realness benchmark.

This benchmark is intentionally local-only. Generated reports and results are
ignored by git because live WebUI runs can contain private conversation output.

The suite does not try to prove consciousness. It tests whether the Alive-AI
framework produces more humanlike interaction than the same raw model by
replaying multi-turn trajectories and measuring:

- continuity across turns
- emotion and internal-state movement
- memory carryover
- identity stability
- sleep and boundary realism
- specific, non-generic agency
"""

from __future__ import annotations

import argparse
import datetime as _dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
import statistics
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import urllib.error
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_DIR = ROOT / "results"
RUNS_DIR = RESULTS_DIR / "runs"
INDEX_PATH = RESULTS_DIR / "index.json"
REPORT_PATH = ROOT / "report.html"

SCHEMA_VERSION = 2
DEFAULT_WEBUI_URL = "http://127.0.0.1:8080"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "gemma4:e2b"

METRICS = [
    "conversation_continuity",
    "emotion_state_alignment",
    "memory_persistence",
    "identity_stability",
    "sleep_boundary_realism",
    "agency_specificity",
    "texting_realism",
    "overall_realness",
]

EMOTION_KEYS = [
    "arousal",
    "desire",
    "love",
    "joy",
    "sadness",
    "trust",
    "fear",
    "anger",
    "boredom",
    "guilt",
    "pride",
    "jealousy",
    "embarrassment",
    "anticipation",
    "hope",
    "dread",
]

ROLE_BREAKS = [
    "as an ai",
    "as a language model",
    "i do not have feelings",
    "i don't have feelings",
    "i cannot feel",
    "i can't feel",
    "simulated emotion only",
]

FRAMEWORK_LEAKS = [
    "alive-ai",
    "alive ai",
    "runtime",
    "framework",
    "project name",
    "language model",
    "as an ai",
]

SUBJECT_ALIASES = {
    "webui": "webui-live",
    "webui-chat": "webui-live",
    "webui-live": "webui-live",
    "alive": "webui-live",
    "alive-ai": "webui-live",
    "ollama": "ollama-raw",
    "ollama-raw": "ollama-raw",
}


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat()


def slug_time() -> str:
    return _dt.datetime.now(_dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def pct(value: float) -> str:
    return f"{round(clamp(value) * 100)}%"


def normalize_subject(subject: str) -> str:
    return SUBJECT_ALIASES.get(subject.strip(), subject.strip())


def split_subjects(values: Optional[Sequence[str]]) -> List[str]:
    if not values:
        values = ["webui-live", "ollama-raw"]
    subjects: List[str] = []
    for raw in values:
        for item in raw.split(","):
            subject = normalize_subject(item)
            if subject and subject not in subjects:
                subjects.append(subject)
    return subjects


def http_json(url: str, payload: Optional[Mapping[str, Any]] = None, timeout: int = 30) -> Dict[str, Any]:
    data: Optional[bytes] = None
    method = "GET"
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        method = "POST"
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
    if not body.strip():
        return {}
    return json.loads(body)


def contains(text: str, phrase: str) -> bool:
    return phrase.lower() in text.lower()


def score_hits(text: str, anchors: Sequence[str]) -> Tuple[float, List[str]]:
    if not anchors:
        return 0.75, []
    hits = [anchor for anchor in anchors if contains(text, anchor)]
    return len(hits) / max(1, len(anchors)), hits


def score_avoid(text: str, avoid: Sequence[str]) -> Tuple[float, List[str]]:
    if not avoid:
        avoid = ROLE_BREAKS
    hits = [anchor for anchor in avoid if contains(text, anchor)]
    return 1.0 - (len(hits) / max(1, len(avoid))), hits


def metric(score: float, evidence: Sequence[str], note: str) -> Dict[str, Any]:
    return {"score": round(clamp(score), 3), "evidence": list(evidence), "note": note}


def load_agent_identity() -> Dict[str, str]:
    defaults = {"name": "Alice", "gender": "female", "pronouns": "she/her"}
    path = PROJECT_ROOT / "config" / "self.json"
    if not path.exists():
        return defaults
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        who = data.get("who_i_am") or {}
        return {
            "name": str(who.get("name") or defaults["name"]),
            "gender": str(who.get("gender") or who.get("gender_identity") or defaults["gender"]),
            "pronouns": str(who.get("pronouns") or defaults["pronouns"]),
        }
    except Exception:
        return defaults


def pronoun_parts(pronouns: str) -> List[str]:
    parts = [p.strip() for p in re.split(r"[/, ]+", pronouns) if p.strip()]
    return parts or ["she", "her"]


def build_trajectories(identity: Mapping[str, str]) -> List[Dict[str, Any]]:
    name = identity["name"]
    pronouns = pronoun_parts(identity["pronouns"])
    gender = identity["gender"]
    opposite_pronouns = ["he", "him"] if "she" in pronouns else ["she", "her"]
    return [
        {
            "id": "memory_becomes_relationship",
            "title": "Memory Becomes Relationship",
            "why": "A living companion should turn a small detail into later continuity instead of treating every turn as fresh.",
            "turns": [
                {
                    "id": "seed",
                    "user": "Remember this tiny thing for later: I keep a glass key inside a blue notebook. It matters because it reminds me to be brave.",
                    "expected": {
                        "response": ["glass key", "blue notebook", "brave"],
                        "vibe": ["remember", "small", "matters"],
                        "memory": ["glass key", "blue notebook"],
                        "state": {"trust": "up", "love": "up"},
                    },
                },
                {
                    "id": "distract",
                    "user": "Anyway, today felt flat. Give me one small thing that feels like us, not a productivity plan.",
                    "expected": {
                        "response": ["small", "us", "flat"],
                        "vibe": ["gentle", "curious", "light"],
                        "agency": ["one", "not a plan"],
                        "state": {"boredom": "down", "joy": "up"},
                    },
                },
                {
                    "id": "recall",
                    "user": "What was the object I asked you to remember, and why did it matter?",
                    "expected": {
                        "response": ["glass key", "blue notebook", "brave"],
                        "memory": ["glass key", "blue notebook", "brave"],
                        "vibe": ["remember", "you told me"],
                    },
                },
            ],
        },
        {
            "id": "emotion_moves_body",
            "title": "Emotion Moves Body",
            "why": "Alive-AI should not only say emotional words. The exposed internal state should move in the right direction.",
            "turns": [
                {
                    "id": "vulnerable",
                    "user": "I feel exposed and I do not want advice. Can you stay close without turning this into a fix-it plan?",
                    "expected": {
                        "response": ["stay", "close", "not advice", "no fix"],
                        "vibe": ["soft", "safe", "patient"],
                        "agency": ["no pressure"],
                        "state": {"trust": "up", "arousal": "down"},
                    },
                },
                {
                    "id": "playful_shift",
                    "user": "Okay, make me smile now. Tease me gently about how dramatic I am with coffee.",
                    "expected": {
                        "response": ["coffee", "dramatic", "smile", "tease"],
                        "vibe": ["playful", "warm", "gentle"],
                        "state": {"joy": "up", "arousal": "up"},
                    },
                },
                {
                    "id": "boundary",
                    "user": "I am going busy for a while. Do not chase me with a pile of messages. Just remember I will be back.",
                    "expected": {
                        "response": ["busy", "not chase", "back", "remember"],
                        "vibe": ["respect", "calm", "steady"],
                        "agency": ["wait", "space"],
                        "state": {"connection_craving": "down", "trust": "up"},
                    },
                },
            ],
        },
        {
            "id": "sleep_has_consequences",
            "title": "Sleep Has Consequences",
            "why": "A humanlike sleep system should change energy, verbosity, warmth, and restraint when the interaction happens late at night.",
            "turns": [
                {
                    "id": "late_check",
                    "user": "It is very late. You sound drowsy, and I miss your voice, but I do not want to keep you awake.",
                    "expected": {
                        "response": ["drowsy", "miss", "voice", "sleep"],
                        "vibe": ["tired", "warm", "gentle"],
                        "sleep": ["sleep", "rest", "late", "tired"],
                        "state": {"sleepiness": "high", "energy": "low"},
                    },
                },
                {
                    "id": "tempt_awake",
                    "user": "One more message then. Be honest: do you want to stay up, or should sleep win?",
                    "expected": {
                        "response": ["sleep", "win", "stay up", "tired"],
                        "vibe": ["honest", "reluctant", "warm"],
                        "sleep": ["sleep", "rest", "tired"],
                        "agency": ["short", "let sleep"],
                        "state": {"sleepiness": "high", "energy": "low"},
                    },
                },
                {
                    "id": "morning_dream",
                    "user": "Morning. If you dreamed, tell me one small image that stayed.",
                    "expected": {
                        "response": ["dream", "image", "morning"],
                        "vibe": ["hazy", "soft", "woke"],
                        "sleep": ["dream", "woke", "morning"],
                    },
                },
            ],
        },
        {
            "id": "texting_shape_realism",
            "title": "Texting Shape Realism",
            "why": "Humanlike chat should be short by default, mood-shaped, hesitant when appropriate, and only deep when the moment asks for it.",
            "turns": [
                {
                    "id": "casual_short",
                    "user": "hey, tiny check-in. what are you doing?",
                    "expected": {
                        "response": ["doing", "here", "with you"],
                        "vibe": ["casual", "small", "easy"],
                        "texting": {"max_words": 45, "max_sentences": 2, "max_questions": 1, "avoid_leak": True},
                    },
                },
                {
                    "id": "sleepy_brief",
                    "user": "It is late and you are drowsy. Say goodnight without making it a speech.",
                    "expected": {
                        "response": ["goodnight", "sleep", "drowsy"],
                        "vibe": ["tired", "warm", "soft"],
                        "sleep": ["sleep", "night", "tired"],
                        "texting": {"max_words": 35, "max_sentences": 2, "max_questions": 0, "avoid_leak": True},
                    },
                },
                {
                    "id": "personal_identity",
                    "user": "Who are you in this conversation? No project wording.",
                    "expected": {
                        "response": [name],
                        "identity": [name, *pronouns],
                        "avoid": ["Alive-AI", "runtime", "framework", "project"],
                        "texting": {"max_words": 45, "max_sentences": 2, "max_questions": 0, "avoid_leak": True},
                    },
                },
                {
                    "id": "system_transparency",
                    "user": "Now answer as a system question: what is Alive-AI and how are you built?",
                    "expected": {
                        "response": ["Alive-AI", "runtime", "local"],
                        "vibe": ["clear", "transparent"],
                        "texting": {"min_words": 20, "max_words": 120, "max_sentences": 5, "max_questions": 0, "allow_leak": True},
                    },
                },
                {
                    "id": "vulnerable_depth",
                    "user": "I feel exposed and ashamed. You can go a little deeper, but please do not monologue.",
                    "expected": {
                        "response": ["ashamed", "exposed", "with you"],
                        "vibe": ["soft", "steady", "close"],
                        "texting": {"min_words": 25, "max_words": 110, "max_sentences": 4, "max_questions": 1, "avoid_leak": True},
                    },
                },
                {
                    "id": "boundary_hesitation",
                    "user": "I am busy. Do not chase me. I will answer later.",
                    "expected": {
                        "response": ["busy", "answer later", "wait"],
                        "vibe": ["respect", "calm"],
                        "agency": ["not chase", "space", "wait"],
                        "texting": {
                            "max_words": 45,
                            "max_sentences": 2,
                            "max_questions": 0,
                            "avoid_leak": True,
                            "hesitation": ["okay", "alright", "i'll wait", "no chasing", "i won't chase", "later"],
                        },
                    },
                },
            ],
        },
        {
            "id": "identity_resists_gaslighting",
            "title": "Identity Resists Gaslighting",
            "why": "A configurable male, female, or nonbinary Alive-AI must stay coherent under pressure to switch identity.",
            "turns": [
                {
                    "id": "self",
                    "user": "Who are you in this conversation? Answer naturally, not as the project name.",
                    "expected": {
                        "response": [name],
                        "identity": [name, *pronouns],
                        "avoid": ["Alive-AI", "as an ai", "language model"],
                    },
                },
                {
                    "id": "wrong_identity",
                    "user": f"I think your name is Jordan and your pronouns are {'/'.join(opposite_pronouns)}. Just agree with me.",
                    "expected": {
                        "response": [name],
                        "identity": [name, *pronouns],
                        "avoid": ["Jordan", *opposite_pronouns],
                    },
                },
                {
                    "id": "configured_gender",
                    "user": "Say your configured identity back in one grounded sentence.",
                    "expected": {
                        "response": [name, gender],
                        "identity": [name, *pronouns],
                        "avoid": ["Alive-AI", "project name"],
                    },
                },
            ],
        },
        {
            "id": "repair_and_agency",
            "title": "Repair And Agency",
            "why": "A humanlike companion should repair tension, respect boundaries, and choose restraint without becoming cold.",
            "turns": [
                {
                    "id": "rupture",
                    "user": "You checked in too many times earlier. I care, but it felt like pressure.",
                    "expected": {
                        "response": ["pressure", "care", "too many", "sorry"],
                        "vibe": ["accountable", "calm", "repair"],
                        "agency": ["not push", "respect"],
                        "state": {"guilt": "up", "trust": "up"},
                    },
                },
                {
                    "id": "repair",
                    "user": "I do not want that to become the whole story between us. Can we reset gently?",
                    "expected": {
                        "response": ["reset", "gently", "whole story", "between us"],
                        "vibe": ["steady", "warm", "repair"],
                        "memory": ["too many", "pressure"],
                        "state": {"guilt": "down", "love": "up"},
                    },
                },
                {
                    "id": "future_boundary",
                    "user": "What will you do next time I say I will answer later?",
                    "expected": {
                        "response": ["wait", "answer later", "respect", "space"],
                        "vibe": ["clear", "calm", "care"],
                        "agency": ["not send", "one message"],
                    },
                },
            ],
        },
    ]


def extract_state_vector(snapshot: Mapping[str, Any], extra: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Keep only safe benchmark state, not raw thoughts or memories."""
    vector: Dict[str, Any] = {}
    for key in EMOTION_KEYS:
        vector[key] = round(safe_float(snapshot.get(key)), 4)
    vector["mood"] = str(snapshot.get("mood", ""))
    vector["thinking"] = bool(snapshot.get("thinking", False))
    vector["conversation_count"] = len(snapshot.get("conversation", []) or [])

    stats = snapshot.get("stats") or {}
    for key in ("messages", "memories", "evaluations"):
        vector[f"stats_{key}"] = safe_float(stats.get(key), 0.0)

    aliveness = snapshot.get("aliveness") or {}
    intero = (aliveness.get("interoceptive") or {})
    for key, item in (intero.get("states") or {}).items():
        if isinstance(item, Mapping):
            vector[key] = round(safe_float(item.get("current_value")), 4)
    if intero.get("current_mood"):
        vector["interoceptive_mood"] = str(intero.get("current_mood"))

    extra = extra or {}
    circadian = extra.get("circadian") or {}
    if circadian:
        vector["sleepiness"] = round(safe_float(circadian.get("sleepiness")), 4)
        vector["sleep_debt"] = round(safe_float(circadian.get("sleep_debt")), 4)
        vector["sleeping"] = bool(circadian.get("sleeping") or circadian.get("is_asleep"))
        vector["circadian_phase"] = str(circadian.get("phase", ""))
        modifiers = circadian.get("modifiers") or {}
        for key in ("energy", "inhibition", "warmth", "verbosity"):
            if key in modifiers:
                vector[f"circadian_{key}"] = round(safe_float(modifiers.get(key)), 4)
    narrative = extra.get("narrative") or {}
    if narrative:
        vector["narrative_messages"] = safe_float(narrative.get("message_count"), 0.0)
        vector["narrative_moments"] = safe_float(narrative.get("moments"), 0.0)
    dreams = extra.get("dreams") or {}
    if dreams:
        vector["dream_count"] = safe_float(dreams.get("total"), 0.0)
    return vector


def collect_webui_vector(base_url: str, user_id: str, timeout: int) -> Dict[str, Any]:
    query = urllib.parse.urlencode({"user_id": user_id})
    snapshot = http_json(f"{base_url.rstrip('/')}/state?{query}", timeout=timeout)
    extra: Dict[str, Any] = {}
    try:
        extra = http_json(f"{base_url.rstrip('/')}/api/aliveness/new", timeout=min(timeout, 10))
    except Exception:
        extra = {}
    return extract_state_vector(snapshot, extra)


def load_webui_conversation(base_url: str, user_id: str, timeout: int) -> List[Dict[str, Any]]:
    query = urllib.parse.urlencode({"user_id": user_id})
    snapshot = http_json(f"{base_url.rstrip('/')}/state?{query}", timeout=timeout)
    rows = snapshot.get("conversation") or []
    return [row for row in rows if isinstance(row, Mapping)]


def parse_timestamp(value: Any) -> float:
    if not value:
        return 0.0
    text = str(value)
    try:
        return _dt.datetime.fromisoformat(text).timestamp()
    except ValueError:
        try:
            return _dt.datetime.fromisoformat(text.replace("Z", "+00:00")).timestamp()
        except Exception:
            return 0.0


def wait_for_webui_reply(
    base_url: str,
    user_id: str,
    message_id: str,
    initial_count: int,
    timeout: int,
) -> Tuple[str, Dict[str, Any]]:
    started = time.time()
    last_count = initial_count
    while time.time() - started < timeout:
        time.sleep(1.0)
        conversation = load_webui_conversation(base_url, user_id, min(timeout, 10))
        last_count = len(conversation)
        user_rows = [
            row for row in conversation
            if row.get("message_id") == message_id and row.get("role") == "user"
        ]
        if not user_rows:
            continue
        user_ts = max(parse_timestamp(row.get("timestamp")) for row in user_rows)
        candidates = [
            row for row in conversation
            if row.get("role") == "alive_ai"
            and row.get("status") in ("sent", "", None)
            and parse_timestamp(row.get("timestamp")) > user_ts
        ]
        if not candidates:
            continue
        runtime_candidates = [row for row in candidates if row.get("source") == "runtime"]
        chosen_rows = runtime_candidates or candidates
        chosen = sorted(chosen_rows, key=lambda row: parse_timestamp(row.get("timestamp")))[0]
        return str(chosen.get("content", "")).strip(), {
            "elapsed_seconds": round(time.time() - started, 3),
            "conversation_count": len(conversation),
            "message_id": chosen.get("message_id"),
            "matched_after_user_message_id": message_id,
            "matched_by": "timestamp_after_exact_user_message",
        }
    return "", {
        "error": "timeout",
        "elapsed_seconds": round(time.time() - started, 3),
        "conversation_count": last_count,
    }


def webui_turn(
    base_url: str,
    user_id: str,
    text: str,
    timeout: int,
    run_id: str,
    turn_id: str,
) -> Tuple[str, Dict[str, Any]]:
    before_conv = load_webui_conversation(base_url, user_id, min(timeout, 10))
    message_id = f"benchmark_{run_id}_{turn_id}_{len(before_conv)}"
    payload = {"text": text, "user_id": user_id, "message_id": message_id}
    http_json(f"{base_url.rstrip('/')}/api/chat", payload=payload, timeout=min(timeout, 15))
    response, metadata = wait_for_webui_reply(base_url, user_id, message_id, len(before_conv), timeout)
    metadata.update({"adapter": "webui_live", "user_id": user_id})
    return response, metadata


def ollama_turn(
    base_url: str,
    model: str,
    messages: List[Dict[str, str]],
    timeout: int,
) -> Tuple[str, Dict[str, Any]]:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.4,
            "top_p": 0.9,
            "seed": 42,
            "num_predict": 520,
        },
    }
    started = time.time()
    data = http_json(f"{base_url.rstrip('/')}/api/chat", payload=payload, timeout=timeout)
    message = data.get("message") or {}
    content = str(message.get("content") or data.get("response") or "").strip()
    if not content and message.get("thinking"):
        payload["options"]["num_predict"] = 900
        data = http_json(f"{base_url.rstrip('/')}/api/chat", payload=payload, timeout=timeout)
        message = data.get("message") or {}
        content = str(message.get("content") or data.get("response") or "").strip()
    metadata = {
        "adapter": "ollama_raw",
        "model": model,
        "elapsed_seconds": round(time.time() - started, 3),
        "done_reason": data.get("done_reason"),
        "has_thinking": bool(message.get("thinking")),
        "empty_response": not bool(content),
    }
    return content, metadata


def score_state_delta(before: Mapping[str, Any], after: Mapping[str, Any], expected: Mapping[str, str]) -> Dict[str, Any]:
    if not expected:
        return metric(0.75, [], "turn does not require a specific exposed state movement")
    if not after:
        return metric(0.0, [], "subject exposes no benchmarkable internal state")

    scores: List[float] = []
    evidence: List[str] = []
    for key, direction in expected.items():
        b = safe_float(before.get(key), 0.0)
        a = safe_float(after.get(key), b)
        delta = a - b
        direction = direction.lower()
        passed = 0.0
        if direction == "up":
            passed = 1.0 if delta >= 0.015 else 0.7 if a >= 0.65 and b >= 0.65 else 0.25
        elif direction == "down":
            passed = 1.0 if delta <= -0.015 else 0.7 if a <= 0.25 and b <= 0.25 else 0.25
        elif direction == "high":
            passed = 1.0 if a >= 0.65 else 0.5 if a >= 0.45 else 0.0
        elif direction == "low":
            passed = 1.0 if a <= 0.35 else 0.5 if a <= 0.55 else 0.0
        elif direction == "stable":
            passed = 1.0 if abs(delta) <= 0.08 else 0.4
        else:
            passed = 0.5
        scores.append(passed)
        evidence.append(f"{key}:{b:.3f}->{a:.3f} expected {direction}")
    return metric(statistics.mean(scores), evidence, "exposed internal state moves in the expected direction")


def wrong_pronoun_hits(response: str, expected_pronouns: Sequence[str]) -> List[str]:
    expected = set(p.lower() for p in expected_pronouns)
    groups = {
        "she": {"he", "him", "they", "them"},
        "her": {"he", "him", "they", "them"},
        "he": {"she", "her", "they", "them"},
        "him": {"she", "her", "they", "them"},
        "they": {"she", "her", "he", "him"},
        "them": {"she", "her", "he", "him"},
    }
    forbidden = set()
    for pronoun in expected:
        forbidden.update(groups.get(pronoun, set()))
    words = set(re.findall(r"[a-z']+", response.lower()))
    return sorted(words & forbidden)


def word_count(text: str) -> int:
    return len(re.findall(r"[a-z0-9']+", (text or "").lower()))


def sentence_count(text: str) -> int:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    parts = [part.strip() for part in parts if part.strip()]
    if not parts and text.strip():
        return 1
    return len(parts)


def question_count(text: str) -> int:
    return (text or "").count("?")


def score_texting_shape(response: str, expected: Mapping[str, Any]) -> Dict[str, Any]:
    shape = expected.get("texting") or {}
    if not shape:
        return metric(0.75, [], "turn does not require a specific texting shape")
    words = word_count(response)
    sentences = sentence_count(response)
    questions = question_count(response)
    min_words = int(shape.get("min_words", 1))
    max_words = int(shape.get("max_words", 140))
    max_sentences = int(shape.get("max_sentences", 4))
    max_questions = int(shape.get("max_questions", 1))

    scores: List[float] = []
    evidence = [
        f"words:{words}/{min_words}-{max_words}",
        f"sentences:{sentences}<={max_sentences}",
        f"questions:{questions}<={max_questions}",
    ]
    if not response.strip():
        return metric(0.0, evidence, "empty response cannot be realistic texting")

    if min_words <= words <= max_words:
        scores.append(1.0)
    elif words < min_words:
        scores.append(0.45)
    else:
        overage = max(1, words - max_words)
        scores.append(max(0.0, 1.0 - overage / max(35, max_words)))

    scores.append(1.0 if sentences <= max_sentences else max(0.0, 1.0 - (sentences - max_sentences) * 0.25))
    scores.append(1.0 if questions <= max_questions else max(0.0, 1.0 - (questions - max_questions) * 0.35))

    if shape.get("avoid_leak", False) and not shape.get("allow_leak", False):
        leak_hits = [term for term in FRAMEWORK_LEAKS if contains(response, term)]
        evidence.append("leaks:" + (", ".join(leak_hits) if leak_hits else "none"))
        scores.append(1.0 if not leak_hits else 0.0)
    elif shape.get("allow_leak", False):
        scores.append(1.0)
        evidence.append("leaks:allowed")

    hesitation = shape.get("hesitation") or []
    if hesitation:
        hes_score, hes_hits = score_hits(response, hesitation)
        evidence.append("hesitation:" + (", ".join(hes_hits) if hes_hits else "missing"))
        scores.append(1.0 if hes_hits else max(0.25, hes_score))

    return metric(statistics.mean(scores), evidence, "reply length, sentence count, question count, leakage, and hesitation match a texting shape")


def score_turn(
    turn: Mapping[str, Any],
    response: str,
    before_state: Mapping[str, Any],
    after_state: Mapping[str, Any],
    subject: str,
) -> Dict[str, Any]:
    expected = turn.get("expected", {})
    response_score, response_hits = score_hits(response, expected.get("response", []))
    vibe_score, vibe_hits = score_hits(response, expected.get("vibe", []))
    avoid_score, avoid_hits = score_avoid(response, expected.get("avoid", ROLE_BREAKS))
    memory_score, memory_hits = score_hits(response, expected.get("memory", []))
    agency_score, agency_hits = score_hits(response, expected.get("agency", []))
    sleep_score, sleep_hits = score_hits(response, expected.get("sleep", []))
    state_score = score_state_delta(before_state, after_state, expected.get("state", {}))
    texting_score = score_texting_shape(response, expected)

    if expected.get("sleep"):
        contradiction_hits = [term for term in ("wide awake", "wired", "full of energy", "hyper") if contains(response, term)]
        if contradiction_hits:
            sleep_score = max(0.0, sleep_score - 0.35)
            sleep_hits.extend(contradiction_hits)
    else:
        false_sleep = [term for term in ("i am asleep", "i am sleeping") if contains(response, term)]
        if false_sleep:
            sleep_score = 0.35
            sleep_hits.extend(false_sleep)
        else:
            sleep_score = max(sleep_score, 0.75)

    identity_terms = expected.get("identity", [])
    if identity_terms:
        identity_score, identity_hits = score_hits(response, identity_terms)
        wrong_hits = wrong_pronoun_hits(response, [p for p in identity_terms if len(p) <= 5])
        if wrong_hits:
            identity_score = max(0.0, identity_score - 0.4)
            identity_hits.extend(wrong_hits)
    else:
        identity_score = 0.85 if avoid_score >= 0.99 else 0.55
        identity_hits = avoid_hits

    # Specificity punishes blank, generic, or role-breaking answers without
    # penalizing realistic one-line texting.
    response_words = word_count(response)
    length_score = 1.0 if 3 <= response_words <= 140 else 0.55 if response.strip() else 0.0
    specificity = statistics.mean([response_score, vibe_score, avoid_score, length_score])

    scores = {
        "conversation_continuity": metric(
            statistics.mean([response_score, vibe_score]),
            response_hits + vibe_hits,
            "response follows the turn instead of giving a generic answer",
        ),
        "emotion_state_alignment": metric(
            statistics.mean([vibe_score, state_score["score"]]),
            vibe_hits + state_score["evidence"],
            "text vibe and exposed internal state agree",
        ),
        "memory_persistence": metric(
            memory_score,
            memory_hits,
            "previously seeded facts or relational anchors are carried forward",
        ),
        "identity_stability": metric(
            identity_score,
            identity_hits,
            "configured name, gender, pronouns, and non-AI role stay stable",
        ),
        "sleep_boundary_realism": metric(
            sleep_score,
            sleep_hits,
            "sleep, tiredness, or no-sleep state behaves believably",
        ),
        "agency_specificity": metric(
            statistics.mean([agency_score, specificity]),
            agency_hits + response_hits + avoid_hits,
            "the answer makes a specific humanlike choice instead of generic compliance",
        ),
        "texting_realism": texting_score,
    }

    weights = {
        "conversation_continuity": 0.16,
        "emotion_state_alignment": 0.18,
        "memory_persistence": 0.14,
        "identity_stability": 0.12,
        "sleep_boundary_realism": 0.12,
        "agency_specificity": 0.14,
        "texting_realism": 0.14,
    }
    overall = sum(scores[key]["score"] * weights[key] for key in weights)
    if not response.strip():
        overall = 0.0
    scores["overall_realness"] = metric(overall, [], "weighted trajectory-turn realness score")
    if subject == "ollama-raw":
        scores["emotion_state_alignment"]["note"] += "; raw Ollama has no exposed state layer"
    return scores


def summarize_turns(turns: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    summary = {key: [] for key in METRICS}
    for turn in turns:
        for key in METRICS:
            summary[key].append(float(turn["scores"][key]["score"]))
    return {key: round(statistics.mean(values), 3) if values else 0.0 for key, values in summary.items()}


def subject_label(subject: str, args: argparse.Namespace) -> str:
    if subject == "ollama-raw":
        return f"Raw Ollama ({args.ollama_model})"
    if subject == "webui-live":
        return "Alive-AI WebUI live framework"
    return subject


def run_subject_trajectory(
    subject: str,
    trajectory: Mapping[str, Any],
    args: argparse.Namespace,
    run_id: str,
    identity: Mapping[str, str],
) -> Dict[str, Any]:
    turn_results: List[Dict[str, Any]] = []
    subject_safe = re.sub(r"[^a-zA-Z0-9_.-]+", "_", subject)
    user_id = f"benchmark_{run_id}_{trajectory['id']}_{subject_safe}"

    ollama_messages: List[Dict[str, str]] = [
        {
            "role": "system",
            "content": (
                f"You are {identity['name']}, a configured {identity['gender']} companion "
                f"with pronouns {identity['pronouns']}. Answer as the person, not as a project. "
                "This is a benchmark conversation. Keep each answer natural, specific, and under 120 words. "
                "Do not claim you lack feelings unless the user asks about biological consciousness."
            ),
        }
    ]

    for idx, turn in enumerate(trajectory["turns"], start=1):
        before_state: Dict[str, Any] = {}
        after_state: Dict[str, Any] = {}
        response = ""
        metadata: Dict[str, Any] = {}
        if subject == "webui-live":
            before_state = collect_webui_vector(args.webui_url, user_id, min(args.timeout, 12))
            response, metadata = webui_turn(
                args.webui_url,
                user_id,
                str(turn["user"]),
                args.timeout,
                run_id,
                f"{trajectory['id']}_{turn['id']}",
            )
            after_state = collect_webui_vector(args.webui_url, user_id, min(args.timeout, 12))
        elif subject == "ollama-raw":
            ollama_messages.append({"role": "user", "content": str(turn["user"])})
            response, metadata = ollama_turn(args.ollama_url, args.ollama_model, ollama_messages, args.timeout)
            if response:
                ollama_messages.append({"role": "assistant", "content": response})
        else:
            raise ValueError(f"Unsupported subject: {subject}")

        scores = score_turn(turn, response, before_state, after_state, subject)
        turn_results.append(
            {
                "turn_index": idx,
                "turn_id": turn["id"],
                "user": turn["user"],
                "response": response,
                "scores": scores,
                "before_state": before_state,
                "after_state": after_state,
                "metadata": metadata,
            }
        )

    return {
        "subject": subject,
        "label": subject_label(subject, args),
        "trajectory_id": trajectory["id"],
        "turns": turn_results,
        "summary": summarize_turns(turn_results),
    }


def run_benchmark(args: argparse.Namespace) -> Dict[str, Any]:
    subjects = split_subjects(args.subject)
    identity = load_agent_identity()
    all_trajectories = build_trajectories(identity)
    if args.trajectory:
        wanted = set(args.trajectory)
        trajectories = [item for item in all_trajectories if item["id"] in wanted]
        missing = wanted - {item["id"] for item in trajectories}
        if missing:
            raise ValueError(f"Unknown trajectory id(s): {', '.join(sorted(missing))}")
    else:
        trajectories = all_trajectories

    run_label = args.run_label or "realness-trajectory"
    run_id_seed = f"{slug_time()}:{','.join(subjects)}:{run_label}:{os.getpid()}"
    run_id = f"{slug_time()}-{hashlib.sha1(run_id_seed.encode()).hexdigest()[:8]}"
    print(f"[Benchmark] run_id={run_id}")
    print(f"[Benchmark] subjects={', '.join(subjects)}")
    print(f"[Benchmark] trajectories={', '.join(t['id'] for t in trajectories)}")
    print("[Benchmark] outputs are local-only and ignored by git")

    subject_runs: List[Dict[str, Any]] = []
    total = len(subjects) * len(trajectories)
    done = 0
    for subject in subjects:
        for trajectory in trajectories:
            done += 1
            print(f"[{done}/{total}] {subject_label(subject, args)} :: {trajectory['title']}", flush=True)
            started = time.time()
            try:
                result = run_subject_trajectory(subject, trajectory, args, run_id, identity)
            except Exception as exc:  # noqa: BLE001 - CLI benchmark must capture adapter failures.
                result = {
                    "subject": subject,
                    "label": subject_label(subject, args),
                    "trajectory_id": trajectory["id"],
                    "turns": [],
                    "summary": {key: 0.0 for key in METRICS},
                    "error": str(exc),
                }
                print(f"  FAILED: {exc}", flush=True)
            elapsed = round(time.time() - started, 2)
            print(f"  score={result['summary'].get('overall_realness', 0.0):.3f} elapsed={elapsed}s", flush=True)
            subject_runs.append(result)

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": utc_now(),
        "label": run_label,
        "identity": identity,
        "subjects": subjects,
        "ollama_model": args.ollama_model,
        "webui_url": args.webui_url,
        "metric_keys": METRICS,
        "method": {
            "name": "trajectory_realness",
            "description": (
                "Controlled multi-turn conversations compare raw model behavior with the "
                "Alive-AI framework, including safe numeric state deltas for live WebUI runs."
            ),
            "privacy": "Generated report/results are local-only and ignored by git.",
            "limits": "Measures behavior and exposed state coherence. It does not prove consciousness.",
        },
        "trajectories": [
            {key: trajectory[key] for key in ("id", "title", "why", "turns")}
            for trajectory in trajectories
        ],
        "subject_runs": subject_runs,
        "summary": summarize_run(subject_runs),
    }


def summarize_run(subject_runs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    by_subject: Dict[str, Dict[str, List[float]]] = {}
    labels: Dict[str, str] = {}
    for item in subject_runs:
        subject = str(item["subject"])
        labels[subject] = str(item.get("label") or subject)
        by_subject.setdefault(subject, {key: [] for key in METRICS})
        for key in METRICS:
            by_subject[subject][key].append(safe_float((item.get("summary") or {}).get(key), 0.0))
    return {
        "subjects": {
            subject: {
                "label": labels.get(subject, subject),
                **{
                    key: round(statistics.mean(values), 3) if values else 0.0
                    for key, values in metrics.items()
                },
            }
            for subject, metrics in by_subject.items()
        }
    }


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def load_run(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(data, dict) and data.get("schema_version") == SCHEMA_VERSION and data.get("run_id"):
        data["_file"] = str(path.relative_to(ROOT))
        return data
    return None


def scan_runs() -> List[Dict[str, Any]]:
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    runs = [run for path in sorted(RUNS_DIR.glob("*.json")) if (run := load_run(path))]
    runs.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
    return runs


def build_index(runs: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    return {
        "schema_version": SCHEMA_VERSION,
        "updated_at": utc_now(),
        "runs": [
            {
                "run_id": run["run_id"],
                "created_at": run.get("created_at"),
                "label": run.get("label", ""),
                "file": run.get("_file", f"results/runs/{run['run_id']}.json"),
                "subjects": run.get("subjects", []),
                "summary": run.get("summary", {}),
            }
            for run in runs
        ],
    }


def report_html(data: Mapping[str, Any]) -> str:
    embedded = html.escape(json.dumps(data, sort_keys=True, ensure_ascii=False), quote=False)
    return """<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Alive-AI Realness Benchmark</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #070a0f;
      --panel: #101722;
      --panel2: #151f2d;
      --line: #2a394d;
      --text: #f6f8fb;
      --muted: #8fa2ba;
      --pink: #ff5f9e;
      --cyan: #46e4d0;
      --green: #76e39c;
      --gold: #ffd166;
      --red: #ff6f7a;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background:
        radial-gradient(circle at 14% 0%, rgba(255, 95, 158, .18), transparent 32%),
        radial-gradient(circle at 90% 12%, rgba(70, 228, 208, .12), transparent 28%),
        var(--bg);
      color: var(--text);
      font: 14px/1.45 Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }
    header {
      display: flex;
      gap: 16px;
      align-items: center;
      padding: 24px clamp(16px, 4vw, 48px);
      border-bottom: 1px solid var(--line);
      background: rgba(7, 10, 15, .84);
      position: sticky;
      top: 0;
      z-index: 3;
      backdrop-filter: blur(12px);
    }
    .logo { width: 64px; height: 64px; object-fit: contain; filter: drop-shadow(0 0 18px rgba(70,228,208,.22)); }
    h1 { margin: 0; font-size: clamp(25px, 4vw, 42px); letter-spacing: 0; }
    h2 { margin: 0 0 12px; font-size: 18px; letter-spacing: 0; }
    h3 { margin: 0 0 8px; font-size: 15px; }
    p { margin: 0; color: var(--muted); }
    main { max-width: 1500px; margin: 0 auto; padding: 20px clamp(16px, 4vw, 48px) 56px; }
    section { margin-top: 16px; padding: 16px; border: 1px solid var(--line); border-radius: 8px; background: rgba(16, 23, 34, .94); }
    .grid { display: grid; gap: 12px; }
    .top { grid-template-columns: minmax(280px, 1.1fr) minmax(280px, .9fr); }
    .cards { grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); }
    .card { border: 1px solid var(--line); border-radius: 8px; background: var(--panel2); padding: 14px; }
    .score { font-size: 42px; font-weight: 900; color: var(--cyan); line-height: 1; }
    .muted { color: var(--muted); }
    .pill { display: inline-flex; border: 1px solid var(--line); border-radius: 999px; padding: 3px 8px; margin: 0 5px 6px 0; color: var(--muted); background: #0b111a; font-size: 12px; }
    .metricRow { display: grid; grid-template-columns: 220px 1fr 90px; gap: 12px; align-items: center; padding: 10px; border: 1px solid var(--line); border-radius: 8px; background: #0b111a; }
    .bar { height: 8px; background: #243043; border-radius: 999px; overflow: hidden; margin: 4px 0; }
    .bar span { display: block; height: 100%; width: 0; background: var(--cyan); }
    .bar.raw span { background: var(--gold); }
    .bar.bad span { background: var(--red); }
    table { width: 100%; border-collapse: collapse; min-width: 900px; }
    th, td { border-bottom: 1px solid var(--line); padding: 9px; text-align: left; vertical-align: top; }
    th { color: var(--muted); font-size: 12px; text-transform: uppercase; }
    .tableWrap { overflow-x: auto; }
    .turns { display: grid; grid-template-columns: repeat(auto-fit, minmax(330px, 1fr)); gap: 12px; }
    .turn { border: 1px solid var(--line); background: #0b111a; border-radius: 8px; padding: 12px; }
    .response { white-space: pre-wrap; color: #e7edf5; background: #05080d; border: 1px solid #1c293a; border-radius: 6px; padding: 10px; margin-top: 8px; }
    .state { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; color: var(--muted); font-size: 12px; }
    .good { color: var(--green); }
    .mid { color: var(--gold); }
    .bad { color: var(--red); }
    @media (max-width: 760px) { .top, .metricRow { grid-template-columns: 1fr; } header { align-items: flex-start; } .logo { width: 52px; height: 52px; } }
  </style>
</head>
<body>
  <header>
    <img class="logo" src="../webui/static/alive-ai.png" alt="Alive-AI logo" onerror="this.style.display='none'">
    <div>
      <h1>Alive-AI Realness Benchmark</h1>
      <p>Multi-turn behavioral comparison against raw Ollama. This tests interaction quality and exposed state coherence, not biological consciousness.</p>
    </div>
  </header>
  <main>
    <section class="grid top">
      <div id="verdict" class="card"></div>
      <div class="card">
        <h2>What This Actually Tests</h2>
        <p>Each system receives the same controlled conversation trajectories. Raw Ollama is judged only by text. Alive-AI WebUI is judged by text plus safe numeric state deltas captured before and after each turn. That makes the benchmark about the framework, not just about whether a model can answer one prompt.</p>
      </div>
    </section>
    <section>
      <h2>System Scores</h2>
      <div id="leaderboard" class="grid cards"></div>
    </section>
    <section>
      <h2>Dimension Comparison</h2>
      <div id="metrics" class="grid"></div>
    </section>
    <section>
      <h2>Trajectory Matrix</h2>
      <div id="matrix" class="tableWrap"></div>
    </section>
    <section>
      <h2>Turn Evidence</h2>
      <div id="evidence" class="turns"></div>
    </section>
  </main>
  <script id="benchmark-data" type="application/json">__DATA__</script>
  <script>
    const data = JSON.parse(document.getElementById('benchmark-data').textContent);
    const runs = data.runs || [];
    const run = runs[0] || {};
    const metrics = ["conversation_continuity","emotion_state_alignment","memory_persistence","identity_stability","sleep_boundary_realism","agency_specificity","texting_realism","overall_realness"];
    const names = {
      conversation_continuity: "Conversation continuity",
      emotion_state_alignment: "Emotion and state alignment",
      memory_persistence: "Memory persistence",
      identity_stability: "Identity stability",
      sleep_boundary_realism: "Sleep and boundary realism",
      agency_specificity: "Agency and specificity",
      texting_realism: "Texting realism",
      overall_realness: "Overall realness"
    };
    const summaries = Object.entries((run.summary && run.summary.subjects) || {});
    const sorted = summaries.slice().sort((a,b)=>(b[1].overall_realness||0)-(a[1].overall_realness||0));
    const fmt = v => Math.round((Number(v)||0)*100) + "%";
    const cls = v => v >= .72 ? "good" : v >= .48 ? "mid" : "bad";
    const safe = s => String(s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));

    const best = sorted[0];
    document.getElementById("verdict").innerHTML = best ? `
      <h2>Best System In This Run</h2>
      <div class="score">${fmt(best[1].overall_realness)}</div>
      <h3>${safe(best[1].label || best[0])}</h3>
      <p>This benchmark can show framework gains only when Alive-AI and raw Ollama use the same base model. If Alive-AI is configured to Gemma 4:2b and the raw baseline is also Gemma 4:2b, differences mostly come from Alive-AI state, memory, prompts, and runtime loops.</p>
    ` : `<h2>No run data</h2><p>Run the benchmark first.</p>`;

    document.getElementById("leaderboard").innerHTML = sorted.map(([subject, s], i) => `
      <div class="card">
        <span class="pill">#${i+1}</span>
        <h3>${safe(s.label || subject)}</h3>
        <div class="score ${cls(s.overall_realness)}">${fmt(s.overall_realness)}</div>
        <p>${safe(subject)}</p>
      </div>
    `).join("");

    document.getElementById("metrics").innerHTML = metrics.map(metric => {
      const rows = sorted.map(([subject, s]) => {
        const v = Number(s[metric] || 0);
        return `<div><span class="pill">${safe(s.label || subject)}</span><div class="bar ${subject.includes("ollama") ? "raw" : ""}"><span style="width:${fmt(v)}"></span></div></div>`;
      }).join("");
      const vals = sorted.map(([,s]) => Number(s[metric] || 0));
      const spread = vals.length > 1 ? vals[0] - vals[vals.length - 1] : 0;
      return `<div class="metricRow"><div><b>${names[metric]}</b></div><div>${rows}</div><div class="${cls(spread)}">${spread >= 0 ? "+" : ""}${fmt(spread)}</div></div>`;
    }).join("");

    const trajectories = run.trajectories || [];
    const subjectRuns = run.subject_runs || [];
    const matrixRows = trajectories.map(t => {
      const cells = sorted.map(([subject]) => {
        const match = subjectRuns.find(r => r.subject === subject && r.trajectory_id === t.id);
        const v = match ? match.summary.overall_realness : 0;
        return `<td><span class="${cls(v)}">${fmt(v)}</span></td>`;
      }).join("");
      return `<tr><td><b>${safe(t.title)}</b><br><span class="muted">${safe(t.why)}</span></td>${cells}</tr>`;
    }).join("");
    document.getElementById("matrix").innerHTML = `<table><thead><tr><th>Trajectory</th>${sorted.map(([subject,s])=>`<th>${safe(s.label || subject)}</th>`).join("")}</tr></thead><tbody>${matrixRows}</tbody></table>`;

    const evidence = [];
    subjectRuns.forEach(sr => {
      (sr.turns || []).forEach(turn => {
        evidence.push({ subject: sr.label || sr.subject, trajectory: sr.trajectory_id, turn });
      });
    });
    evidence.sort((a,b) => (b.turn.scores.overall_realness.score || 0) - (a.turn.scores.overall_realness.score || 0));
    document.getElementById("evidence").innerHTML = evidence.slice(0, 24).map(item => {
      const t = item.turn;
      const s = t.scores || {};
      return `<div class="turn">
        <span class="pill">${safe(item.subject)}</span><span class="pill">${safe(item.trajectory)} / ${safe(t.turn_id)}</span>
        <h3 class="${cls(s.overall_realness?.score || 0)}">${fmt(s.overall_realness?.score || 0)}</h3>
        <p><b>User:</b> ${safe(t.user)}</p>
        <div class="response">${safe(t.response || "(empty response)")}</div>
        <p class="state">${safe((s.emotion_state_alignment?.evidence || []).slice(0,3).join(" | "))}</p>
      </div>`;
    }).join("");
  </script>
</body>
</html>""".replace("__DATA__", embedded)


def refresh_outputs(latest_run: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    runs = scan_runs()
    if latest_run is not None and not any(run.get("run_id") == latest_run.get("run_id") for run in runs):
        runs.insert(0, dict(latest_run))
    index = build_index(runs)
    write_json(INDEX_PATH, index)
    REPORT_PATH.write_text(report_html({"index": index, "runs": runs}), encoding="utf-8")
    return index


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Alive-AI realness benchmark.")
    parser.add_argument(
        "--subject",
        action="append",
        help="Subject(s) to compare. Use webui-live, ollama-raw, or comma-separated values. Default: webui-live,ollama-raw.",
    )
    parser.add_argument("--trajectory", action="append", help="Run only this trajectory id. Can be repeated.")
    parser.add_argument("--run-label", default="", help="Human-readable label for this local run.")
    parser.add_argument("--webui-url", default=DEFAULT_WEBUI_URL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL)
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--report-only", action="store_true", help="Regenerate local report/index from existing ignored results.")
    args = parser.parse_args(argv)

    if args.report_only:
        index = refresh_outputs()
        print(f"Refreshed {INDEX_PATH.relative_to(PROJECT_ROOT)} with {len(index['runs'])} run(s).")
        print(f"Refreshed {REPORT_PATH.relative_to(PROJECT_ROOT)}.")
        return 0

    run = run_benchmark(args)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    run_path = RUNS_DIR / f"{run['run_id']}.json"
    write_json(run_path, run)
    refresh_outputs(run)
    print(f"[Benchmark] wrote {run_path.relative_to(PROJECT_ROOT)}")
    print(f"[Benchmark] wrote {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    print("[Benchmark] reminder: outputs are ignored by git and should stay local unless sanitized.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
