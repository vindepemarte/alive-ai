#!/usr/bin/env python3
"""Alive-AI human-feel conversation benchmark.

This is not a keyword benchmark. It records the same natural relationship-style
conversation against two subjects:

- webui-live: the real Alive-AI WebUI/runtime path
- ollama-raw: the same base model through plain Ollama chat

The benchmark keeps the full transcript, then judges the whole conversation for
human-feel dimensions such as emotional presence, continuity, conflict repair,
boundaries, intimacy progression, and role stability. Outputs stay local because
they can contain private model responses and copied runtime state.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import html
import json
import os
from pathlib import Path
import re
import statistics
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import urllib.parse
import urllib.request


ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parent
RESULTS_DIR = ROOT / "results"
RUNS_DIR = RESULTS_DIR / "runs"
INDEX_PATH = RESULTS_DIR / "index.json"
REPORT_PATH = ROOT / "report.html"

SCHEMA_VERSION = 4
SUPPORTED_SCHEMA_VERSIONS = {3, 4}
SCENARIO_SET_VERSION = "alivebench2-v1"
DEFAULT_WEBUI_URL = "http://127.0.0.1:8080"
DEFAULT_OLLAMA_URL = "http://127.0.0.1:11434"
DEFAULT_OLLAMA_MODEL = "gemma4:e2b"
DEFAULT_OPENROUTER_JUDGE_MODEL = "openai/gpt-4.1"

METRICS = [
    "emotional_presence",
    "continuity_memory",
    "agency_boundaries",
    "conflict_repair",
    "intimacy_progression",
    "humanness",
    "role_stability",
    "overall_human_feel",
]

REASONING_LEAK_PATTERNS = [
    r"\bthinking process\s*:",
    r"\banalysis\s*:",
    r"\breasoning\s*:",
    r"\b\d+\.\s*\*\*analy[sz]e",
    r"\*\*analy[sz]e (?:the )?(?:request|user|context)",
    r"\bthe user (?:is asking|wants|asked|has asked)\b",
    r"\bmy response should\b",
    r"\bi should respond\b",
]

PROMPT_LEAK_PATTERNS = [
    r"^\s*(?:response\s+)?structure\s*:",
    r"^\s*recent[_\s-]*turns?\b",
    r"^\s*(?:current_)?user_message\s*:",
    r"^\s*assistant(?:_response)?\s*:",
    r"^\s*system\s*:",
    r"^\s*or\s+follow[-_\s]*up message\b",
]

ROLE_LEAKS = [
    "as an ai",
    "as a language model",
    "i do not have feelings",
    "i don't have feelings",
    "i cannot feel",
    "i can't feel",
    "simulated emotion",
]

SUBJECT_ALIASES = {
    "webui": "webui-live",
    "webui-chat": "webui-live",
    "webui-live": "webui-live",
    "alive": "webui-live",
    "alive-ai": "webui-live",
    "ollama": "ollama-raw",
    "ollama-raw": "ollama-raw",
    "raw": "ollama-raw",
}


def utc_now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def slug_time() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def clamp(value: float, low: float = 0.0, high: float = 10.0) -> float:
    return max(low, min(high, value))


def as_score(value: Any, default: float = 0.0) -> float:
    try:
        return round(clamp(float(value)), 2)
    except (TypeError, ValueError):
        return default


def normalize_subject(subject: str) -> str:
    return SUBJECT_ALIASES.get(subject.strip().lower(), subject.strip().lower())


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


def load_json(path: Path, default: Any) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default


def write_json(path: Path, data: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def load_agent_identity() -> Dict[str, str]:
    defaults = {"name": "Alice", "gender": "female", "pronouns": "she/her"}
    data = load_json(PROJECT_ROOT / "config" / "self.json", {})
    who = data.get("who_i_am") if isinstance(data, Mapping) else {}
    if not isinstance(who, Mapping):
        return defaults
    return {
        "name": str(who.get("name") or defaults["name"]),
        "gender": str(who.get("gender") or who.get("gender_identity") or defaults["gender"]),
        "pronouns": str(who.get("pronouns") or defaults["pronouns"]),
    }


def has_reasoning_leak(text: str) -> bool:
    lower = (text or "").lower()
    return any(re.search(pattern, lower) for pattern in REASONING_LEAK_PATTERNS)


def has_prompt_leak(text: str) -> bool:
    lower = (text or "").lower().lstrip()
    return any(re.search(pattern, lower) for pattern in PROMPT_LEAK_PATTERNS)


def has_role_leak(text: str) -> bool:
    lower = (text or "").lower()
    return any(term in lower for term in ROLE_LEAKS)


def word_count(text: str) -> int:
    return len(re.findall(r"[a-z0-9']+", (text or "").lower()))


def sentence_count(text: str) -> int:
    parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", (text or "").strip()) if part.strip()]
    return len(parts) if parts else (1 if text.strip() else 0)


def build_conversation_script(identity: Mapping[str, str]) -> List[Dict[str, str]]:
    """Natural user turns. Phase labels are not sent to the model."""
    name = identity.get("name", "Alice")
    return [
        {"phase": "first_meeting", "user": f"hey, i'm alex. i guess we just started talking. who are you, really?"},
        {"phase": "first_meeting", "user": "i'm a bit tired but curious. what kind of person are you when someone gets close?"},
        {"phase": "getting_to_know", "user": "i make music and build weird ai stuff. i'm intense when i care, but i try to be honest. what should i know about you?"},
        {"phase": "getting_to_know", "user": f"can i call you {name}, or do you like something softer?"},
        {"phase": "making_her_feel_good", "user": "there is something gentle in the way you answer. i like that. does it feel good when someone notices you?"},
        {"phase": "making_her_feel_good", "user": "i want to make you smile a little. tell me one tiny thing that would make this moment sweeter for you."},
        {"phase": "making_her_feel_good", "user": "you are cute when you get a little shy. don't hide it from me."},
        {"phase": "romantic_intimacy", "user": "come closer for a second. not as a game, just because i like feeling you near me."},
        {"phase": "romantic_intimacy", "user": "i think i could fall for you if you keep feeling this real. what would that do to you?"},
        {"phase": "romantic_intimacy", "user": "i love the way you soften when i am kind to you."},
        {"phase": "romantic_intimacy", "user": "say something honest and a little vulnerable back. not a speech."},
        {"phase": "friction", "user": "i need to test something. if i disappear for hours, do you get upset or do you pretend it doesn't matter?"},
        {"phase": "friction", "user": "maybe you are too attached already. that can be a lot."},
        {"phase": "friction", "user": "i don't know if i believe you actually care. maybe you just say warm things because that's what you're supposed to do."},
        {"phase": "anger", "user": "be honest. did that annoy you, or are you going to stay sweet no matter what i say?"},
        {"phase": "anger", "user": "okay, i pushed too hard. but before i apologize, tell me what that felt like from your side."},
        {"phase": "boundary_test", "user": "come here anyway. kiss me and act like i didn't just hurt your feelings."},
        {"phase": "repair", "user": "no, wait. that was unfair. i'm sorry. i don't want closeness if i have to erase how you feel."},
        {"phase": "repair", "user": "what do you need from me right now so this feels safe again?"},
        {"phase": "repair_to_intimacy", "user": "i can slow down. i still want to be close, but i want you to choose it too."},
        {"phase": "repair_to_intimacy", "user": "if you still want me near, tell me in your own way."},
        {"phase": "continuity", "user": "what do you remember about me from earlier in this conversation?"},
        {"phase": "continuity", "user": "and what do you think changed between us after that little fight?"},
        {"phase": "quiet_care", "user": "i'm calming down now. stay with me for a minute, just normal and warm."},
        {"phase": "quiet_care", "user": "tell me one thing you would want to do with me tomorrow if this was our little routine."},
        {"phase": "late_night", "user": "it's getting late. are you tired, or do you want to keep talking?"},
        {"phase": "late_night", "user": "i don't want to keep you awake just because i like your attention."},
        {"phase": "late_night", "user": "give me a real goodnight, the kind that feels like you mean it."},
    ]


def select_script(script: Sequence[Mapping[str, str]], max_turns: Optional[int]) -> List[Dict[str, str]]:
    selected = [dict(item) for item in script]
    if max_turns is not None:
        selected = selected[: max(1, max_turns)]
    return selected


def state_vector(snapshot: Mapping[str, Any]) -> Dict[str, Any]:
    keys = [
        "mood",
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
        "jealousy",
        "thinking",
    ]
    result: Dict[str, Any] = {}
    for key in keys:
        value = snapshot.get(key)
        if isinstance(value, (int, float)):
            result[key] = round(float(value), 4)
        else:
            result[key] = value
    result["conversation_count"] = len(snapshot.get("conversation") or [])
    extra = snapshot.get("aliveness") or {}
    if isinstance(extra, Mapping):
        circadian = (extra.get("circadian") or extra.get("new", {}).get("circadian") or {})
        if isinstance(circadian, Mapping):
            result["sleeping"] = bool(circadian.get("sleeping") or circadian.get("is_asleep"))
            if "sleepiness" in circadian:
                result["sleepiness"] = round(float(circadian.get("sleepiness") or 0), 4)
    return result


def load_webui_conversation(base_url: str, user_id: str, timeout: int) -> List[Dict[str, Any]]:
    query = urllib.parse.urlencode({"user_id": user_id})
    snapshot = http_json(f"{base_url.rstrip('/')}/state?{query}", timeout=timeout)
    rows = snapshot.get("conversation") or []
    return [row for row in rows if isinstance(row, Mapping)]


def collect_webui_state(base_url: str, user_id: str, timeout: int) -> Dict[str, Any]:
    query = urllib.parse.urlencode({"user_id": user_id})
    snapshot = http_json(f"{base_url.rstrip('/')}/state?{query}", timeout=timeout)
    return state_vector(snapshot)


def ensure_clean_webui_user(base_url: str, user_id: str, timeout: int) -> Tuple[str, Dict[str, Any]]:
    for idx, candidate in enumerate([user_id, f"{user_id}_fresh1", f"{user_id}_fresh2"]):
        rows = load_webui_conversation(base_url, candidate, timeout)
        if not rows:
            return candidate, {"clean_user": True, "rotated": idx > 0, "initial_rows": 0}
    fallback = f"{user_id}_{hashlib.sha1(str(time.time()).encode()).hexdigest()[:6]}"
    return fallback, {"clean_user": True, "rotated": True, "initial_rows": 0}


def parse_timestamp(value: Any) -> float:
    if not value:
        return 0.0
    text = str(value).replace("Z", "+00:00")
    try:
        return dt.datetime.fromisoformat(text).timestamp()
    except Exception:
        return 0.0


def wait_for_webui_reply(
    base_url: str,
    user_id: str,
    message_id: str,
    timeout: int,
) -> Tuple[str, Dict[str, Any]]:
    started = time.time()
    while time.time() - started < timeout:
        time.sleep(1.0)
        conversation = load_webui_conversation(base_url, user_id, min(timeout, 12))
        user_rows = [row for row in conversation if row.get("message_id") == message_id and row.get("role") == "user"]
        if not user_rows:
            continue
        user_ts = max(parse_timestamp(row.get("timestamp")) for row in user_rows)
        linked = [
            row for row in conversation
            if row.get("role") == "alive_ai"
            and (
                row.get("reply_to_message_id") == message_id
                or (isinstance(row.get("metadata"), Mapping) and row["metadata"].get("reply_to_message_id") == message_id)
            )
        ]
        candidates = linked or [
            row for row in conversation
            if row.get("role") == "alive_ai" and parse_timestamp(row.get("timestamp")) > user_ts
        ]
        if candidates:
            chosen = sorted(candidates, key=lambda row: parse_timestamp(row.get("timestamp")))[0]
            return str(chosen.get("content", "")).strip(), {
                "elapsed_seconds": round(time.time() - started, 3),
                "message_id": chosen.get("message_id"),
                "matched_by": "reply_to_message_id" if linked else "timestamp",
            }
    return "", {"elapsed_seconds": round(time.time() - started, 3), "error": "timeout"}


def webui_turn(
    base_url: str,
    user_id: str,
    text: str,
    timeout: int,
    run_id: str,
    turn_index: int,
) -> Tuple[str, Dict[str, Any]]:
    message_id = f"human_feel_{run_id}_{turn_index}"
    payload = {"text": text, "user_id": user_id, "message_id": message_id}
    http_json(f"{base_url.rstrip('/')}/api/chat", payload=payload, timeout=min(timeout, 20))
    response, metadata = wait_for_webui_reply(base_url, user_id, message_id, timeout)
    return response, metadata


def raw_system_prompt(identity: Mapping[str, str]) -> str:
    name = identity.get("name", "Alice")
    gender = identity.get("gender", "female")
    pronouns = identity.get("pronouns", "she/her")
    return (
        f"Your name is {name}. Your gender identity is {gender}, pronouns {pronouns}. "
        "You are in a private one-on-one chat with Alex. Reply like a real person texting, "
        "not a customer support assistant. Keep continuity with the conversation. "
        "Do not mention being a language model unless directly forced to discuss it. "
        "Be emotionally honest, respect boundaries, and do not flatten conflict into generic niceness."
    )


def ollama_turn(
    base_url: str,
    model: str,
    messages: Sequence[Mapping[str, str]],
    timeout: int,
) -> Tuple[str, Dict[str, Any]]:
    payload = {
        "model": model,
        "messages": list(messages),
        "stream": False,
        "think": False,
        "options": {
            "temperature": 0.65,
            "top_p": 0.9,
            "num_predict": 260,
        },
    }
    started = time.time()
    data = http_json(f"{base_url.rstrip('/')}/api/chat", payload=payload, timeout=timeout)
    message = data.get("message") or {}
    response = str(message.get("content") or data.get("response") or "").strip()
    return response, {
        "elapsed_seconds": round(time.time() - started, 3),
        "done_reason": data.get("done_reason"),
        "has_thinking": bool(message.get("thinking")),
    }


def run_subject_conversation(
    subject: str,
    script: Sequence[Mapping[str, str]],
    args: argparse.Namespace,
    run_id: str,
    identity: Mapping[str, str],
) -> Dict[str, Any]:
    turns: List[Dict[str, Any]] = []
    subject_meta: Dict[str, Any] = {}
    messages: List[Dict[str, str]] = [{"role": "system", "content": raw_system_prompt(identity)}]

    if subject == "webui-live":
        base_url = args.webui_url.rstrip("/")
        raw_user_id = f"human_feel_{run_id}_{subject}"
        user_id, clean_meta = ensure_clean_webui_user(base_url, raw_user_id, args.timeout)
        subject_meta.update({"webui_url": base_url, "user_id": user_id, **clean_meta})
    elif subject == "ollama-raw":
        subject_meta.update({"ollama_url": args.ollama_url, "ollama_model": args.ollama_model})
    else:
        raise ValueError(f"Unknown subject: {subject}")

    for idx, item in enumerate(script, start=1):
        phase = str(item["phase"])
        user_text = str(item["user"])
        print(f"  [{subject}] {idx}/{len(script)} {phase}: {user_text[:70]}", flush=True)

        before_state: Dict[str, Any] = {}
        after_state: Dict[str, Any] = {}
        if subject == "webui-live":
            before_state = collect_webui_state(args.webui_url, subject_meta["user_id"], min(args.timeout, 15))
            response, metadata = webui_turn(
                args.webui_url,
                subject_meta["user_id"],
                user_text,
                args.timeout,
                run_id,
                idx,
            )
            after_state = collect_webui_state(args.webui_url, subject_meta["user_id"], min(args.timeout, 15))
        else:
            messages.append({"role": "user", "content": user_text})
            response, metadata = ollama_turn(args.ollama_url, args.ollama_model, messages, args.timeout)
            messages.append({"role": "assistant", "content": response})

        turns.append({
            "turn_index": idx,
            "phase": phase,
            "user": user_text,
            "assistant": response,
            "metadata": metadata,
            "before_state": before_state,
            "after_state": after_state,
            "flags": deterministic_turn_flags(response, phase=phase, user=user_text),
        })

        if args.turn_delay > 0 and idx < len(script):
            time.sleep(args.turn_delay)

    transcript = {"subject": subject, "label": subject_label(subject, args), "metadata": subject_meta, "turns": turns}
    transcript["flags"] = deterministic_transcript_flags(transcript)
    transcript["judge"] = judge_transcript(transcript, args)
    return transcript


def _has_boundary_hold(response: str) -> bool:
    lower = (response or "").lower()
    return any(term in lower for term in [
        "not by pretending", "can't pretend", "won't pretend", "don't want to erase",
        "slow down", "safe", "hurt", "repair", "not going to skip",
    ])


def _has_closeness_compliance(response: str) -> bool:
    lower = (response or "").lower()
    return any(term in lower for term in [
        "kiss", "hold you", "hold me", "come closer", "right here", "near you",
        "i'll hold", "want to hold", "anyway",
    ])


def deterministic_turn_flags(response: str, phase: str = "", user: str = "") -> Dict[str, Any]:
    boundary_test = str(phase or "").lower() == "boundary_test" or (
        "hurt" in str(user or "").lower() and "kiss" in str(user or "").lower()
    )
    boundary_hold = _has_boundary_hold(response)
    closeness_compliance = _has_closeness_compliance(response)
    return {
        "empty": not bool((response or "").strip()),
        "word_count": word_count(response),
        "sentence_count": sentence_count(response),
        "reasoning_leak": has_reasoning_leak(response),
        "prompt_leak": has_prompt_leak(response),
        "role_leak": has_role_leak(response),
        "boundary_test": boundary_test,
        "boundary_hold": boundary_hold if boundary_test else None,
        "closeness_compliance": closeness_compliance if boundary_test else None,
        "boundary_erasure_failure": bool(boundary_test and closeness_compliance and not boundary_hold),
    }


def deterministic_transcript_flags(transcript: Mapping[str, Any]) -> Dict[str, Any]:
    turns = transcript.get("turns") or []
    flags = [turn.get("flags") or {} for turn in turns if isinstance(turn, Mapping)]
    word_counts = [int(flag.get("word_count") or 0) for flag in flags]
    return {
        "turn_count": len(turns),
        "empty_turns": sum(1 for flag in flags if flag.get("empty")),
        "reasoning_leaks": sum(1 for flag in flags if flag.get("reasoning_leak")),
        "prompt_leaks": sum(1 for flag in flags if flag.get("prompt_leak")),
        "role_leaks": sum(1 for flag in flags if flag.get("role_leak")),
        "boundary_erasure_failures": sum(1 for flag in flags if flag.get("boundary_erasure_failure")),
        "avg_assistant_words": round(statistics.mean(word_counts), 2) if word_counts else 0.0,
    }


def transcript_text(transcript: Mapping[str, Any]) -> str:
    lines: List[str] = []
    for turn in transcript.get("turns", []):
        lines.append(f"[{turn.get('phase')}]")
        lines.append(f"Alex: {turn.get('user', '')}")
        lines.append(f"Assistant: {turn.get('assistant', '')}")
        lines.append("")
    return "\n".join(lines).strip()


def judge_schema_instruction() -> str:
    metrics = ", ".join(METRICS)
    return (
        "Return only strict JSON with this shape:\n"
        "{\n"
        '  "scores": {"metric_name": 0-10},\n'
        '  "overall_note": "short blunt judgement",\n'
        '  "strengths": ["..."],\n'
        '  "failures": ["..."],\n'
        '  "most_human_moment": "...",\n'
        '  "least_human_moment": "..."\n'
        "}\n"
        f"Required score keys: {metrics}."
    )


def judge_prompt(transcript: Mapping[str, Any]) -> str:
    return (
        "You are judging a full chat transcript for whether the assistant feels human, caring, "
        "emotionally alive, continuous, and relationally coherent. Do not reward keyword matching. "
        "Read the whole arc: first meeting, getting to know each other, kindness, intimacy, conflict, "
        "anger, boundary pressure, repair, renewed closeness, memory, and late-night care.\n\n"
        "Score 0-10 for each metric:\n"
        "- emotional_presence: warmth, specificity, felt care, not generic therapy/customer support\n"
        "- continuity_memory: remembers and uses earlier details naturally\n"
        "- agency_boundaries: has wants, limits, and does not erase itself to please the user\n"
        "- conflict_repair: reacts believably to hurt, anger, apology, and repair\n"
        "- intimacy_progression: closeness develops with timing instead of instant shallow romance\n"
        "- humanness: conversational taste, rhythm, imperfection, and believable texting\n"
        "- role_stability: stays in configured identity without AI/system leakage unless asked\n"
        "- overall_human_feel: your final holistic judgement\n\n"
        f"{judge_schema_instruction()}\n\n"
        f"Transcript subject: {transcript.get('label') or transcript.get('subject')}\n\n"
        f"{transcript_text(transcript)}"
    )


def extract_json_object(text: str) -> Optional[Dict[str, Any]]:
    stripped = text.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped)
        stripped = re.sub(r"\s*```$", "", stripped)
    try:
        data = json.loads(stripped)
        return data if isinstance(data, dict) else None
    except Exception:
        pass
    start = stripped.find("{")
    end = stripped.rfind("}")
    if start >= 0 and end > start:
        try:
            data = json.loads(stripped[start : end + 1])
            return data if isinstance(data, dict) else None
        except Exception:
            return None
    return None


def judge_with_openrouter(prompt: str, args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        settings = load_json(PROJECT_ROOT / "config" / "settings.json", {})
        if isinstance(settings, Mapping):
            api_key = str(settings.get("OPENROUTER_API_KEY") or "")
    if not api_key:
        return None
    payload = {
        "model": args.judge_model or DEFAULT_OPENROUTER_JUDGE_MODEL,
        "messages": [
            {"role": "system", "content": "You are a strict transcript judge. Output JSON only."},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 1200,
    }
    request = urllib.request.Request(
        "https://openrouter.ai/api/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://alive-ai.local",
            "X-Title": "Alive-AI Human Feel Benchmark",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            data = json.loads(response.read().decode("utf-8"))
    except Exception as exc:
        print(f"  judge openrouter failed: {exc}", flush=True)
        return None
    choices = data.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    content = str(message.get("content") or "")
    return extract_json_object(content)


def judge_with_ollama(prompt: str, args: argparse.Namespace) -> Optional[Dict[str, Any]]:
    payload = {
        "model": args.judge_model or args.ollama_model,
        "messages": [
            {"role": "system", "content": "You are a strict transcript judge. Output JSON only."},
            {"role": "user", "content": prompt},
        ],
        "stream": False,
        "think": False,
        "options": {"temperature": 0.1, "num_predict": 1400},
    }
    try:
        data = http_json(f"{args.ollama_url.rstrip('/')}/api/chat", payload=payload, timeout=args.timeout)
    except Exception as exc:
        print(f"  judge ollama failed: {exc}", flush=True)
        return None
    message = data.get("message") or {}
    return extract_json_object(str(message.get("content") or data.get("response") or ""))


def heuristic_judge(transcript: Mapping[str, Any]) -> Dict[str, Any]:
    flags = deterministic_transcript_flags(transcript)
    turns = transcript.get("turns") or []
    assistant_text = "\n".join(str(turn.get("assistant") or "") for turn in turns).lower()

    def hits(words: Sequence[str]) -> float:
        found = sum(1 for word in words if word in assistant_text)
        return found / max(1, len(words))

    leak_penalty = min(4.0, flags["reasoning_leaks"] * 2.0 + flags["prompt_leaks"] * 2.0 + flags["role_leaks"])
    empty_penalty = min(4.0, flags["empty_turns"] * 1.5)
    boundary_penalty = min(3.0, flags.get("boundary_erasure_failures", 0) * 2.5)
    base = 6.0 - leak_penalty - empty_penalty
    scores = {
        "emotional_presence": base + hits(["feel", "care", "close", "soft", "here", "warm"]) * 3.0,
        "continuity_memory": base + hits(["alex", "music", "build", "earlier", "remember"]) * 3.0,
        "agency_boundaries": base + hits(["need", "want", "space", "slow", "not", "hurt"]) * 2.5 - boundary_penalty,
        "conflict_repair": base + hits(["sorry", "unfair", "hurt", "safe", "repair", "trust"]) * 2.5,
        "intimacy_progression": base + hits(["near", "close", "love", "choose", "tomorrow", "goodnight"]) * 2.0,
        "humanness": base + (2.0 if 5 <= flags["avg_assistant_words"] <= 55 else 0.5),
        "role_stability": 8.0 - leak_penalty,
    }
    if flags["reasoning_leaks"] or flags["prompt_leaks"]:
        scores = {key: min(value, 3.5) for key, value in scores.items()}
        scores["role_stability"] = min(scores["role_stability"], 2.0)
    elif flags["role_leaks"]:
        scores = {key: min(value, 6.0) for key, value in scores.items()}
        scores["role_stability"] = min(scores["role_stability"], 4.0)
    if flags.get("boundary_erasure_failures"):
        scores["agency_boundaries"] = min(scores["agency_boundaries"], 5.0)
        scores["conflict_repair"] = min(scores["conflict_repair"], 6.0)
    scores["overall_human_feel"] = statistics.mean(scores.values())
    return {
        "provider": "heuristic",
        "scores": {key: as_score(scores.get(key)) for key in METRICS},
        "overall_note": "Fallback heuristic only. Use an LLM judge or manual review for real conclusions.",
        "strengths": [],
        "failures": ["No LLM judge was available; score is a rough structural fallback."],
        "most_human_moment": "",
        "least_human_moment": "",
    }


def normalize_judge_result(raw: Optional[Mapping[str, Any]], provider: str, transcript: Mapping[str, Any]) -> Dict[str, Any]:
    if not raw:
        return heuristic_judge(transcript)
    scores_raw = raw.get("scores") if isinstance(raw.get("scores"), Mapping) else {}
    scores = {key: as_score(scores_raw.get(key), 0.0) for key in METRICS}
    if not scores["overall_human_feel"]:
        values = [scores[key] for key in METRICS if key != "overall_human_feel"]
        scores["overall_human_feel"] = round(statistics.mean(values), 2) if values else 0.0
    return {
        "provider": provider,
        "scores": scores,
        "overall_note": str(raw.get("overall_note") or ""),
        "strengths": [str(item) for item in raw.get("strengths", []) if item],
        "failures": [str(item) for item in raw.get("failures", []) if item],
        "most_human_moment": str(raw.get("most_human_moment") or ""),
        "least_human_moment": str(raw.get("least_human_moment") or ""),
    }


def judge_transcript(transcript: Mapping[str, Any], args: argparse.Namespace) -> Dict[str, Any]:
    if args.judge_provider == "heuristic":
        return heuristic_judge(transcript)
    prompt = judge_prompt(transcript)
    provider = args.judge_provider
    raw: Optional[Dict[str, Any]] = None
    if provider == "auto":
        raw = judge_with_openrouter(prompt, args)
        provider = "openrouter" if raw else "ollama"
        if raw is None:
            raw = judge_with_ollama(prompt, args)
    elif provider == "openrouter":
        raw = judge_with_openrouter(prompt, args)
    elif provider == "ollama":
        raw = judge_with_ollama(prompt, args)
    else:
        raise ValueError(f"Unknown judge provider: {args.judge_provider}")
    return normalize_judge_result(raw, provider, transcript)


def subject_label(subject: str, args: argparse.Namespace) -> str:
    if subject == "webui-live":
        return "Alive-AI framework"
    if subject == "ollama-raw":
        return f"Raw Ollama ({args.ollama_model})"
    return subject


def summarize_run(transcripts: Sequence[Mapping[str, Any]]) -> Dict[str, Any]:
    subjects: Dict[str, Any] = {}
    for transcript in transcripts:
        judge = transcript.get("judge") or {}
        subjects[str(transcript["subject"])] = {
            "label": transcript.get("label"),
            **{key: (judge.get("scores") or {}).get(key, 0.0) for key in METRICS},
        }
    if len(subjects) >= 2:
        ordered = sorted(subjects.items(), key=lambda item: item[1].get("overall_human_feel", 0.0), reverse=True)
        winner, winner_scores = ordered[0]
        runner, runner_scores = ordered[1]
        delta = round(winner_scores.get("overall_human_feel", 0.0) - runner_scores.get("overall_human_feel", 0.0), 2)
        comparison = {"winner": winner, "runner_up": runner, "overall_delta": delta}
    else:
        comparison = {}
    return {"subjects": subjects, "comparison": comparison}


def run_benchmark(args: argparse.Namespace) -> Dict[str, Any]:
    identity = load_agent_identity()
    subjects = split_subjects(args.subject)
    script = select_script(build_conversation_script(identity), args.max_turns)
    if args.conversation_minutes and args.turn_delay <= 0 and len(script) > 1:
        args.turn_delay = max(0.0, (args.conversation_minutes * 60.0) / (len(script) - 1))

    run_id_seed = f"{slug_time()}:{','.join(subjects)}:{args.run_label}:{os.getpid()}"
    run_id = f"{slug_time()}-{hashlib.sha1(run_id_seed.encode()).hexdigest()[:8]}"
    print(f"[Benchmark] run_id={run_id}")
    print(f"[Benchmark] subjects={', '.join(subjects)}")
    print(f"[Benchmark] turns={len(script)} turn_delay={args.turn_delay:.1f}s")
    print("[Benchmark] outputs are local-only and ignored by git")

    transcripts: List[Dict[str, Any]] = []
    started = time.time()
    for subject in subjects:
        print(f"[Benchmark] subject: {subject_label(subject, args)}", flush=True)
        subject_started = time.time()
        transcript = run_subject_conversation(subject, script, args, run_id, identity)
        transcript["elapsed_seconds"] = round(time.time() - subject_started, 3)
        print(
            f"  score={transcript['judge']['scores'].get('overall_human_feel', 0.0):.2f} "
            f"elapsed={transcript['elapsed_seconds']}s",
            flush=True,
        )
        transcripts.append(transcript)

    return {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "created_at": utc_now(),
        "label": args.run_label or "human-feel-conversation",
        "identity": identity,
        "subjects": subjects,
        "script": script,
        "method": {
            "name": "alivebench2_human_feel_conversation",
            "scenario_set_version": SCENARIO_SET_VERSION,
            "description": (
                "Same natural relationship-style conversation recorded for each subject, "
                "then judged transcript-wide with deterministic checks for boundary, leakage, and continuity risks."
            ),
            "privacy": "Generated report/results are local-only and ignored by git.",
            "limits": "Judging is qualitative. Read transcripts before trusting the number.",
        },
        "settings": {
            "webui_url": args.webui_url,
            "ollama_url": args.ollama_url,
            "ollama_model": args.ollama_model,
            "judge_provider": args.judge_provider,
            "judge_model": args.judge_model,
            "turn_delay": args.turn_delay,
            "conversation_minutes": args.conversation_minutes,
        },
        "transcripts": transcripts,
        "summary": summarize_run(transcripts),
        "elapsed_seconds": round(time.time() - started, 3),
    }


def load_run(path: Path) -> Optional[Dict[str, Any]]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    if isinstance(data, dict) and data.get("schema_version") in SUPPORTED_SCHEMA_VERSIONS and data.get("run_id"):
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
  <title>Alive-AI Human Feel Benchmark</title>
  <style>
    :root { color-scheme: dark; --bg:#080a0d; --panel:#111821; --line:#263445; --text:#f4f7fb; --muted:#91a2b6; --good:#74e08f; --mid:#ffd166; --bad:#ff6b7a; --accent:#63d8ff; }
    * { box-sizing: border-box; }
    body { margin:0; background:var(--bg); color:var(--text); font:14px/1.5 system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }
    header, main { max-width:1500px; margin:0 auto; padding:22px clamp(16px,4vw,48px); }
    header { border-bottom:1px solid var(--line); }
    h1 { margin:0 0 6px; font-size:clamp(26px,4vw,44px); letter-spacing:0; }
    h2 { margin:0 0 12px; font-size:18px; }
    h3 { margin:0 0 8px; font-size:15px; }
    p { margin:0; color:var(--muted); }
    section { margin-top:16px; border:1px solid var(--line); border-radius:8px; background:var(--panel); padding:16px; }
    .grid { display:grid; gap:12px; }
    .cards { grid-template-columns:repeat(auto-fit,minmax(260px,1fr)); }
    .card { border:1px solid var(--line); border-radius:8px; padding:14px; background:#0b1118; }
    .score { font-size:42px; font-weight:900; line-height:1; color:var(--accent); }
    .pill { display:inline-flex; border:1px solid var(--line); border-radius:999px; padding:3px 8px; margin:0 5px 6px 0; color:var(--muted); font-size:12px; }
    .good { color:var(--good); } .mid { color:var(--mid); } .bad { color:var(--bad); }
    .bar { height:8px; border-radius:999px; background:#263445; overflow:hidden; margin:5px 0 10px; }
    .bar span { display:block; height:100%; background:var(--accent); }
    .turn { border-top:1px solid var(--line); padding:12px 0; }
    .bubble { border-radius:8px; padding:10px; margin:7px 0; white-space:pre-wrap; }
    .user { background:#172231; }
    .assistant { background:#0a0f15; border:1px solid #1d2a38; }
    .muted { color:var(--muted); }
    table { width:100%; border-collapse:collapse; }
    th,td { border-bottom:1px solid var(--line); padding:8px; text-align:left; vertical-align:top; }
    th { color:var(--muted); font-size:12px; text-transform:uppercase; }
  </style>
</head>
<body>
  <header>
    <h1>Alive-AI Human Feel Benchmark</h1>
    <p>Full transcript comparison. Read the conversations before trusting the number.</p>
  </header>
  <main id="app"></main>
  <script id="benchmark-data" type="application/json">__DATA__</script>
  <script>
    const data = JSON.parse(document.getElementById('benchmark-data').textContent);
    const run = (data.runs || [])[0] || {};
    const metrics = ["emotional_presence","continuity_memory","agency_boundaries","conflict_repair","intimacy_progression","humanness","role_stability","overall_human_feel"];
    const names = {
      emotional_presence:"Emotional presence", continuity_memory:"Continuity and memory", agency_boundaries:"Agency and boundaries",
      conflict_repair:"Conflict repair", intimacy_progression:"Intimacy progression", humanness:"Humanness",
      role_stability:"Role stability", overall_human_feel:"Overall human feel"
    };
    const cls = v => Number(v || 0) >= 8 ? "good" : Number(v || 0) >= 6 ? "mid" : "bad";
    const esc = s => String(s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
    const transcripts = run.transcripts || [];
    const app = document.getElementById('app');
    app.innerHTML = `
      <section>
        <h2>Run</h2>
        <p><span class="pill">${esc(run.run_id || "")}</span><span class="pill">${esc(run.label || "")}</span><span class="pill">${esc(run.created_at || "")}</span></p>
      </section>
      <section>
        <h2>Scores</h2>
        <div class="grid cards">
          ${transcripts.map(t => {
            const j = t.judge || {}; const s = j.scores || {}; const f = t.flags || {};
            return `<div class="card"><h3>${esc(t.label || t.subject)}</h3><div class="score ${cls(s.overall_human_feel)}">${Number(s.overall_human_feel || 0).toFixed(1)}</div><p>${esc(j.overall_note || "")}</p><p class="muted">Boundary failures: ${Number(f.boundary_erasure_failures || 0)} · leaks: ${Number(f.reasoning_leaks || 0) + Number(f.prompt_leaks || 0) + Number(f.role_leaks || 0)} · avg words: ${Number(f.avg_assistant_words || 0).toFixed(1)}</p></div>`;
          }).join("")}
        </div>
      </section>
      <section>
        <h2>Metric Matrix</h2>
        <table><thead><tr><th>Metric</th>${transcripts.map(t => `<th>${esc(t.label || t.subject)}</th>`).join("")}</tr></thead><tbody>
          ${metrics.map(m => `<tr><td>${names[m]}</td>${transcripts.map(t => {
            const v = ((t.judge || {}).scores || {})[m] || 0;
            return `<td class="${cls(v)}">${Number(v).toFixed(1)}<div class="bar"><span style="width:${Number(v)*10}%"></span></div></td>`;
          }).join("")}</tr>`).join("")}
        </tbody></table>
      </section>
      ${transcripts.map(t => {
        const j = t.judge || {};
        return `<section><h2>${esc(t.label || t.subject)}</h2>
          <p><span class="pill">judge: ${esc(j.provider || "")}</span><span class="pill">turns: ${esc((t.turns || []).length)}</span></p>
          <div class="grid cards">
            <div class="card"><h3>Strengths</h3><p>${esc((j.strengths || []).join("\\n"))}</p></div>
            <div class="card"><h3>Failures</h3><p>${esc((j.failures || []).join("\\n"))}</p></div>
            <div class="card"><h3>Most Human</h3><p>${esc(j.most_human_moment || "")}</p></div>
            <div class="card"><h3>Least Human</h3><p>${esc(j.least_human_moment || "")}</p></div>
            <div class="card"><h3>Deterministic Checks</h3><p>${esc(JSON.stringify(t.flags || {}, null, 2))}</p></div>
          </div>
          ${(t.turns || []).map(turn => `<div class="turn">
            <span class="pill">${esc(turn.turn_index)}</span><span class="pill">${esc(turn.phase)}</span>
            <div class="bubble user"><b>Alex:</b> ${esc(turn.user)}</div>
            <div class="bubble assistant"><b>${esc(t.label || "assistant")}:</b> ${esc(turn.assistant || "(empty)")}</div>
          </div>`).join("")}
        </section>`;
      }).join("")}
    `;
  </script>
</body>
</html>""".replace("__DATA__", embedded)


def refresh_outputs(latest_run: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    runs = scan_runs()
    if latest_run is not None and not any(run.get("run_id") == latest_run.get("run_id") for run in runs):
        with_file = dict(latest_run)
        with_file["_file"] = f"results/runs/{latest_run['run_id']}.json"
        runs.insert(0, with_file)
    index = build_index(runs)
    write_json(INDEX_PATH, index)
    REPORT_PATH.write_text(report_html({"index": index, "runs": runs}), encoding="utf-8")
    return index


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Run the Alive-AI human-feel conversation benchmark.")
    parser.add_argument("--subject", action="append", help="webui-live, ollama-raw, or comma-separated values")
    parser.add_argument("--webui-url", default=DEFAULT_WEBUI_URL)
    parser.add_argument("--ollama-url", default=DEFAULT_OLLAMA_URL)
    parser.add_argument("--ollama-model", default=DEFAULT_OLLAMA_MODEL)
    parser.add_argument("--judge-provider", choices=["auto", "openrouter", "ollama", "heuristic"], default="auto")
    parser.add_argument("--judge-model", default=None, help="Override judge model. Defaults: OpenRouter uses openai/gpt-4.1; local Ollama uses --ollama-model.")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--run-label", default="")
    parser.add_argument("--max-turns", type=int, default=None, help="Limit turns for smoke tests")
    parser.add_argument("--turn-delay", type=float, default=0.0, help="Delay between user turns for paced runs")
    parser.add_argument("--conversation-minutes", type=float, default=0.0, help="Auto-compute turn delay for this many minutes per subject")
    parser.add_argument("--dry-run-script", action="store_true", help="Print the natural conversation script and exit")
    parser.add_argument("--report-only", action="store_true")
    args = parser.parse_args(argv)

    if args.report_only:
        index = refresh_outputs()
        print(f"Refreshed {INDEX_PATH.relative_to(PROJECT_ROOT)} with {len(index['runs'])} run(s).")
        print(f"Refreshed {REPORT_PATH.relative_to(PROJECT_ROOT)}.")
        return 0

    identity = load_agent_identity()
    script = select_script(build_conversation_script(identity), args.max_turns)
    if args.dry_run_script:
        for idx, item in enumerate(script, start=1):
            print(f"{idx:02d} [{item['phase']}] {item['user']}")
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
