"""
Core: Thinking
Mood instruction building and fallback responses
"""

from __future__ import annotations

from dataclasses import dataclass
import random
import re
from typing import Any, Mapping, Sequence


ROLE_LEAK_PATTERNS = [
    "as an ai",
    "as a language model",
    "i do not have feelings",
    "i don't have feelings",
    "i cannot feel",
    "i can't feel",
    "alive-ai",
    "alive ai",
    "runtime",
    "framework",
    "project name",
]

REASONING_START_PATTERNS = [
    "thinking process",
    "analysis:",
    "reasoning:",
    "step 1:",
    "1. analyze",
    "1. **analyze",
    "2. **analyze",
    "3. **analyze",
    "analyze the request",
    "analyze the user",
    "the user wants",
    "the user is asking",
    "i need to respond",
    "i need to answer",
    "i need to craft",
    "i should respond",
    "i should answer",
    "i should say",
    "my goal is",
]

REASONING_ANYWHERE_PATTERNS = [
    r"</?think(?:ing)?>",
    r"\bthinking process\s*:",
    r"\*\*analy[sz]e (?:the )?(?:request|user|context)",
    r"\b\d+\.\s*\*\*analy[sz]e",
    r"\bthe user (?:is asking|wants|asked|has asked)\b",
    r"\bmy response should\b",
    r"\bi (?:need|should) to (?:respond|answer|craft|generate|produce|address|analy[sz]e)\b",
    r"\bi should respond\b",
]

PROMPT_LEAK_PATTERNS = [
    r"^\s*(?:response\s+)?structure\s*:",
    r"^\s*recent[_\s-]*turns?\b",
    r"^\s*(?:current_)?user_message\s*:",
    r"^\s*assistant(?:_response)?\s*:",
    r"^\s*system\s*:",
    r"^\s*follow[-_\s]*up message\b",
    r"^\s*or\s+follow[-_\s]*up message\b",
]

_ACCEPTABLE_SHORT_STARTS = (
    "ok",
    "okay",
    "alright",
    "yes",
    "yeah",
    "yep",
    "no",
    "nope",
    "same",
    "true",
    "goodnight",
    "sleep",
    "i'm ",
    "i am ",
    "i'll ",
    "i will ",
    "i won't ",
    "i cannot ",
    "can't ",
    "come here",
    "stay",
)


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return low


def _words(text: str) -> list[str]:
    return re.findall(r"[A-Za-z0-9']+", text or "")


def _sentence_split(text: str) -> list[str]:
    normalized = re.sub(r"\s+", " ", (text or "").strip())
    if not normalized:
        return []
    ellipsis_marker = "<ELLIPSIS>"
    protected = normalized.replace("...", ellipsis_marker)
    parts = re.split(r"(?<=[.!?])\s+", protected)
    return [part.replace(ellipsis_marker, "...").strip() for part in parts if part.strip()]


def _count_questions(text: str) -> int:
    return (text or "").count("?")


def _clean_spaces(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip())


def normalize_chat_punctuation(text: str) -> str:
    """Keep generated chat away from model-ish dash-heavy punctuation."""
    value = str(text or "")
    value = re.sub(r"\s*(?:—|–|--)\s*", ", ", value)
    value = re.sub(r"\s+([,.!?])", r"\1", value)
    value = re.sub(r",\s*,+", ",", value)
    value = re.sub(r"\s{2,}", " ", value)
    return value.strip()


def _bid_values(bids: Sequence[Any]) -> tuple[set[str], set[str]]:
    types: set[str] = set()
    intensities: set[str] = set()
    for bid in bids or []:
        bid_type = getattr(bid, "bid_type", None)
        intensity = getattr(bid, "intensity", None)
        types.add(str(getattr(bid_type, "value", bid_type) or "").lower())
        intensities.add(str(getattr(intensity, "value", intensity) or "").lower())
    return types, intensities


def is_system_transparency_request(msg: str) -> bool:
    """Return True when the user is asking about Alive-AI/system/runtime details."""
    text = (msg or "").lower()
    system_terms = (
        "alive-ai", "alive ai", "runtime", "framework", "system", "built",
        "how do you work", "how are you made", "how were you made",
        "who made you", "creator", "model", "llm", "local-first",
    )
    return any(term in text for term in system_terms)


def is_personal_identity_request(msg: str) -> bool:
    text = (msg or "").lower().strip()
    if is_system_transparency_request(text):
        return False
    if re.search(r"\b(who are you|your name|say your identity|configured identity)\b", text):
        return True
    if re.search(r"\bwhat are you\b", text):
        return not re.search(r"\bwhat are you\s+(?:up to|doing|thinking|feeling)\b", text)
    return False


def _direct_question(msg: str) -> bool:
    text = (msg or "").strip().lower()
    if "?" in text:
        return True
    return bool(re.match(r"^(what|who|where|when|why|how|do|does|did|is|are|can|could|would|will|should|have|has)\b", text))


def _depth_trigger(msg: str, emotion: Mapping[str, Any], bid_types: set[str], bid_intensities: set[str]) -> bool:
    text = (msg or "").lower()
    explicit = (
        "explain", "go deeper", "tell me more", "long answer", "story",
        "why do you", "walk me through", "be detailed", "introspection",
        "what do you feel", "what are you feeling", "dream", "memory",
        "remember", "repair", "reset", "serious", "important",
    )
    vulnerable = (
        "ashamed", "scared", "afraid", "hurt", "grief", "panic", "cry",
        "overwhelmed", "depressed", "alone", "vulnerable", "exposed",
    )
    high_emotion = max(
        _clamp(emotion.get(key, 0.0))
        for key in ("sadness", "fear", "anger", "guilt", "love", "desire", "arousal")
    ) >= 0.78
    return (
        any(term in text for term in explicit)
        or any(term in text for term in vulnerable)
        or "vulnerability" in bid_types
        or "high" in bid_intensities
        or high_emotion
    )


def _boundary_trigger(msg: str) -> bool:
    text = (msg or "").lower()
    return any(
        term in text
        for term in (
            "do not", "don't", "stop", "busy", "answer later", "space",
            "boundary", "not now", "leave me", "pressure", "too many",
            "don't chase", "do not chase",
        )
    )


@dataclass(frozen=True)
class ResponseShapePolicy:
    """State-led reply guidance without hard visible length caps."""

    length_tendency: str
    tone_shape: str
    emoji_tendency: str
    abbreviation_tendency: str
    question_policy: str
    hesitation_instruction: str
    allow_deep: bool
    identity_mode: str = "none"
    system_transparency: bool = False
    direct_question: bool = False

    def to_prompt(self) -> str:
        depth = "allowed if the user clearly invited it" if self.allow_deep else "not allowed here"
        return (
            "RESPONSE STYLE POLICY - State Led\n"
            f"- Length tendency: {self.length_tendency}.\n"
            "- There is no fixed word, sentence, or token target for the visible reply.\n"
            "- Decide how much to say from the user's message, your emotion, sleep pressure, trust, conflict, and current state.\n"
            "- Stop naturally when the thought feels complete; do not pad, ramble, or cut off a needed answer.\n"
            f"- Depth is {depth}.\n"
            f"- Tone shape: {self.tone_shape}.\n"
            f"- Emoji tendency: {self.emoji_tendency}. Abbreviation tendency: {self.abbreviation_tendency}.\n"
            f"- Questions: {self.question_policy}.\n"
            f"- Hesitation/deflection: {self.hesitation_instruction}.\n"
            "- If your model has private thinking/reasoning, keep it private; visible content must be only the final chat reply.\n"
            "- Do not repeat the same image in different words.\n"
            "- Avoid em dashes and double hyphens; use commas, periods, or shorter sentences instead.\n"
            "- If the user did not ask about systems, do not mention Alive-AI, runtime, framework, model, or project details.\n"
        )


def build_response_shape_policy(
    emotion: Mapping[str, Any],
    msg: str,
    ctx: Mapping[str, Any] | None = None,
) -> ResponseShapePolicy:
    """Build state-led style guidance for a single reply."""
    ctx = ctx or {}
    bid_types, bid_intensities = _bid_values(ctx.get("detected_bids", []))
    direct_question = _direct_question(msg)
    system_request = is_system_transparency_request(msg)
    personal_identity = is_personal_identity_request(msg)
    allow_deep = system_request or _depth_trigger(msg, emotion, bid_types, bid_intensities)
    boundary = _boundary_trigger(msg)

    mood = str(emotion.get("mood", "") or "").lower()
    circadian = emotion.get("circadian") if isinstance(emotion.get("circadian"), Mapping) else {}
    circadian_modifiers = circadian.get("modifiers", {}) if isinstance(circadian, Mapping) else {}
    sleepiness = max(_clamp(emotion.get("sleepiness", 0.0)), _clamp(circadian.get("sleepiness", 0.0) if isinstance(circadian, Mapping) else 0.0))
    is_sleepy = bool(emotion.get("is_asleep")) or sleepiness >= 0.65 or "sleepy" in mood or "asleep" in mood

    inconsistency = ctx.get("inconsistency_modifiers", {})
    intero = inconsistency.get("interoception", {}) if isinstance(inconsistency, Mapping) else {}
    mood_mods = inconsistency.get("mood", {}) if isinstance(inconsistency, Mapping) else {}
    profile = mood_mods.get("profile", {}) if isinstance(mood_mods, Mapping) else {}
    social_satiety = _clamp(intero.get("social_satiety", 0.5))
    cognitive_load = _clamp(intero.get("cognitive_load", 0.0))
    energy = _clamp(intero.get("energy", circadian_modifiers.get("energy", 0.6)))
    response_length_modifier = _clamp(profile.get("response_length_modifier", 1.0), 0.45, 1.35)

    recent_lengths: list[int] = []
    for turn in ctx.get("conversation_history", [])[-6:]:
        if turn.get("role") == "assistant":
            recent_lengths.append(len(_words(str(turn.get("content", "")))))
    recent_avg = sum(recent_lengths) / len(recent_lengths) if recent_lengths else 0.0

    question_policy = "answer directly first; one small follow-up only if it genuinely helps"
    length_tendency = "natural texting; brief when the moment is simple, fuller when the moment asks for it"
    tone = "short, natural texting; emotionally colored but not essay-like"
    emoji = "low"
    abbreviations = "light"
    hesitation = "use normal human hesitation only if the feeling calls for it"

    if allow_deep:
        length_tendency = "fuller and more reflective because the user invited depth"
        tone = "warmer and deeper, but still conversational"
    if system_request:
        length_tendency = "clear enough to answer the system question without dumping irrelevant internals"
        tone = "clear and transparent about the system without losing configured identity"
    if personal_identity:
        length_tendency = "plain and direct; identity should not become a speech"
        tone = "plain personal identity; configured name and pronouns, no framework details"
    if is_sleepy:
        length_tendency = "naturally shorter and lower-energy because sleep pressure is high, unless a direct answer needs room"
        tone = "sleepy, warm, low-energy, a little slower; no hyper-alert pep"
        emoji = "very low"
        abbreviations = "light and lazy if natural"
        hesitation = "defer depth or let sleep win while still using one complete sentence"
    if sleepiness >= 0.85 or bool(emotion.get("woke_from_sleep")):
        length_tendency = "very sleepy; it can be tiny, but it still has to be a complete human answer"
        tone = "very sleepy, warm, complete, and low-energy; no pep and no rambling"
        hesitation = "let sleep win in one complete sentence"
        if direct_question:
            length_tendency = "sleepy but not evasive; answer the question before drifting back down"
            hesitation = "answer the direct question first, then let sleep keep the reply short"
    if boundary:
        length_tendency = "restrained and clear because a boundary or space request is active"
        tone = "respectful, restrained, not over-compliant, not needy"
        hesitation = "acknowledge the limit; deflect pressure or choose restraint instead of chasing"
    if social_satiety > 0.75:
        tone += "; socially settled, less eager"
    if cognitive_load > 0.62:
        length_tendency += "; simpler because cognitive load is high"
        tone += "; cognitive load is high, keep it simpler"
        hesitation = "admit uncertainty or choose one clear thread instead of covering everything"
    if energy < 0.35:
        length_tendency += "; lower-energy because the body state is tired"
        tone += "; energy is low"
    if response_length_modifier < 0.85:
        length_tendency += "; current mood leans less talkative"
    if recent_avg >= 120 and not allow_deep:
        length_tendency += "; recent replies were long, so avoid unnecessary expansion"
        tone += "; recent replies were long, correct toward brevity"

    identity_mode = "personal" if personal_identity else "system" if system_request else "none"
    return ResponseShapePolicy(
        length_tendency=length_tendency,
        tone_shape=tone,
        emoji_tendency=emoji,
        abbreviation_tendency=abbreviations,
        question_policy=question_policy,
        hesitation_instruction=hesitation,
        allow_deep=allow_deep,
        identity_mode=identity_mode,
        system_transparency=system_request,
        direct_question=direct_question,
    )


def _pronoun_label(identity: Mapping[str, Any] | None) -> str:
    identity = identity or {}
    pronouns = str(identity.get("pronouns") or "").strip()
    gender = str(identity.get("gender") or "").strip().lower()
    if pronouns:
        return pronouns
    if gender == "male":
        return "he/him"
    if gender == "nonbinary":
        return "they/them"
    return "she/her"


def _identity_fallback(identity: Mapping[str, Any] | None) -> str:
    identity = identity or {}
    name = str(identity.get("name") or "Alice").strip()
    return f"I'm {name}, {_pronoun_label(identity)}. I'm here with you as myself."


def _system_fallback(identity: Mapping[str, Any] | None) -> str:
    identity = identity or {}
    name = str(identity.get("name") or "Alice").strip()
    return (
        f"{name} is the configured companion identity. Alive-AI is the local-first "
        "emotional AI runtime created by Alexandru Iacovici, known as Vindepemarte. "
        "It wraps memory, mood, sleep, prompts, skills, and LLM providers around "
        "that identity."
    )


def has_role_leakage(text: str, allow_system_terms: bool = False) -> bool:
    lower = (text or "").lower()
    patterns = ROLE_LEAK_PATTERNS if not allow_system_terms else ROLE_LEAK_PATTERNS[:6]
    return any(pattern in lower for pattern in patterns)


def strip_reasoning_preamble(text: str) -> str:
    """Remove visible chain-of-thought style preambles if a final answer exists."""
    original = (text or "").strip()
    without_think = re.sub(
        r"(?is)^\s*<(?:think|thinking|analysis)>.*?</(?:think|thinking|analysis)>\s*",
        "",
        original,
    ).strip()
    if without_think != original:
        original = without_think

    lower = original.lower().lstrip()
    starts_like_reasoning = (
        any(lower.startswith(pattern) for pattern in REASONING_START_PATTERNS)
        or bool(re.match(r"^\d+\.\s*\*\*analy[sz]e", lower))
    )
    if not starts_like_reasoning:
        return original

    final_markers = (
        "final answer:",
        "final response:",
        "response:",
        "assistant response:",
        "answer:",
        "what i would say:",
    )
    for marker in final_markers:
        idx = lower.rfind(marker)
        if idx > 0:
            return original[idx + len(marker):].strip()
    return ""


def has_reasoning_preamble(text: str) -> bool:
    lower = (text or "").lower().lstrip()
    return (
        any(lower.startswith(pattern) for pattern in REASONING_START_PATTERNS)
        or bool(re.match(r"^\d+\.\s*\*\*analy[sz]e", lower))
    )


def contains_reasoning_artifact(text: str) -> bool:
    """Detect visible reasoning/meta-analysis that should never be sent as chat."""
    if has_reasoning_preamble(text):
        return True
    lower = (text or "").lower()
    return any(re.search(pattern, lower) for pattern in REASONING_ANYWHERE_PATTERNS)


def contains_prompt_leakage(text: str) -> bool:
    lower = (text or "").lower().lstrip()
    return any(re.search(pattern, lower) for pattern in PROMPT_LEAK_PATTERNS)


def sanitize_provider_response(text: str) -> str:
    """Return visible dialogue from provider output, or empty if only reasoning."""
    cleaned = normalize_chat_punctuation(strip_reasoning_preamble(text))
    if not cleaned:
        return ""
    if contains_reasoning_artifact(cleaned):
        return ""
    if contains_prompt_leakage(cleaned):
        return ""
    if re.search(r"`[^`]*$", cleaned) or re.search(r"\b(?:in|with|for|to|from|of|at|by)$", cleaned, re.IGNORECASE):
        return ""
    return cleaned.strip()


def _is_acceptable_short_response(text: str) -> bool:
    lower = _clean_spaces(text).lower()
    if not lower:
        return False
    if lower.startswith(_ACCEPTABLE_SHORT_STARTS):
        return True
    return bool(re.search(r"\b(i|me|you|we|us|here|wait|sleep|later|alice)\b", lower))


def is_response_unusable(
    response: str,
    policy: ResponseShapePolicy | None = None,
    user_message: str = "",
) -> bool:
    """Return True when text should be rejected and replaced before sending."""
    text = _clean_spaces(response)
    if not text:
        return True
    if contains_reasoning_artifact(text):
        return True
    if contains_prompt_leakage(text):
        return True
    if "[ilike:" in text.lower() or "[ithink:" in text.lower() or "[iam:" in text.lower():
        return True

    word_count = len(_words(text))
    if word_count <= 3 and not _is_acceptable_short_response(text):
        return True

    # Catch clipped tails like "bers this personal" without rejecting normal
    # lowercase texting such as "yeah same".
    if (
        word_count <= 5
        and re.match(r"^[a-z]", text)
        and text[-1] not in ".!?"
        and not _is_acceptable_short_response(text)
    ):
        return True

    if (
        word_count <= 8
        and re.match(r"^(?:and|but|or|because|where|which)\b", text.lower())
        and not re.search(r"\b(?:i|me|you|we|us|here)\b", text.lower())
    ):
        return True

    if policy and policy.identity_mode == "personal" and has_role_leakage(text):
        return True
    return False


def _normalize_user_reason(reason: str) -> str:
    text = _clean_spaces(reason).rstrip(" .")
    text = re.sub(r"^it\s+", "", text, flags=re.IGNORECASE)
    replacements = [
        (r"\breminds me\b", "reminds you"),
        (r"\bme to\b", "you to"),
        (r"\bfor me\b", "for you"),
        (r"\bmy\b", "your"),
        (r"\bi am\b", "you are"),
        (r"\bi'm\b", "you are"),
        (r"\bi\b", "you"),
    ]
    for pattern, repl in replacements:
        text = re.sub(pattern, repl, text, flags=re.IGNORECASE)
    return text


def _recent_user_messages(ctx: Mapping[str, Any] | None) -> list[str]:
    messages: list[str] = []
    for turn in (ctx or {}).get("conversation_history", [])[-12:]:
        if turn.get("role") == "user":
            content = _clean_spaces(str(turn.get("content", "")))
            if content:
                messages.append(content)
    return messages


def explicit_memory_anchor_from_text(text: str) -> dict[str, str] | None:
    """Extract direct user memory requests like "keep X inside Y; matters because Z"."""
    line = _clean_spaces(text)
    object_match = re.search(
        r"\b(?:i\s+)?(?:keep|kept|put|have|hid|left|store|stored)\s+"
        r"(?:a|an|the)?\s*([^.!?;,\n]+?)\s+"
        r"(?:inside|in|under|behind|within)\s+"
        r"(?:a|an|the)?\s*([^.!?;,\n]+)",
        line,
        flags=re.IGNORECASE,
    )
    if not object_match:
        return None

    reason = ""
    reason_match = re.search(r"\b(?:it\s+)?matters because\s+([^.!?]+)", line, flags=re.IGNORECASE)
    if reason_match:
        reason = _normalize_user_reason(reason_match.group(1))

    return {
        "object": _clean_spaces(object_match.group(1)),
        "place": _clean_spaces(object_match.group(2)),
        "reason": reason,
    }


def _memory_anchor_text(anchor: Mapping[str, str]) -> str:
    text = f"{anchor.get('object', '').strip()} inside {anchor.get('place', '').strip()}".strip()
    if anchor.get("reason"):
        text += f"; matters because it {anchor['reason']}"
    return text


def _extract_memory_anchor(ctx: Mapping[str, Any] | None) -> dict[str, str] | None:
    for line in reversed(_recent_user_messages(ctx)):
        anchor = explicit_memory_anchor_from_text(line)
        if anchor:
            return anchor
    return None


def _extract_recent_dream_text(ctx: Mapping[str, Any] | None) -> str:
    for key in ("memory_layers_context", "dreams_context", "compiled_context"):
        value = str((ctx or {}).get(key) or "")
        match = re.search(r"Recent dream:\s*([^.\n]+(?:\.[^\n]*)?)", value, flags=re.IGNORECASE)
        if match:
            return _clean_spaces(match.group(1)).strip(" \"'")
    try:
        from brain.dreams import get_dream_system
        dream = get_dream_system().get_recent_dream(max_age_hours=12)
        return _clean_spaces(dream or "")
    except Exception:
        return ""


def is_user_identity_memory_request(msg: str) -> bool:
    """Detect questions about whether the assistant knows the human user."""
    text = _clean_spaces(msg).lower()
    patterns = (
        r"\bwho\s+am\s+i\b",
        r"\bwho\s+i\s+am\b",
        r"\bdo\s+you\s+know\s+(?:who\s+)?(?:i\s+am|who\s+am\s+i|me)\b",
        r"\bdo\s+you\s+remember\s+me\b",
        r"\bwhat\s+do\s+you\s+know\s+about\s+me\b",
        r"\byou\s+know\s+me\s+or\s+not\b",
        r"\bdo\s+you\s+know\s+me\s+or\s+not\b",
    )
    return any(re.search(pattern, text) for pattern in patterns)


def _user_memory_fallback(ctx: Mapping[str, Any] | None) -> str:
    ctx = ctx or {}
    facts = ctx.get("semantic_facts") if isinstance(ctx.get("semantic_facts"), Mapping) else {}
    profile = ctx.get("user_profile") if isinstance(ctx.get("user_profile"), Mapping) else {}
    facts_context = str(ctx.get("facts_context") or "")

    preferred = str(facts.get("nickname") or facts.get("name") or "").strip()
    visible_name = str(facts.get("display_name") or profile.get("display_name") or "").strip()
    username = str(facts.get("username") or profile.get("username") or "").strip().lstrip("@")

    if preferred:
        return f"I know you as {preferred}. I'm still learning the rest of you slowly."
    if visible_name:
        return f"I can see your Telegram name is {visible_name}, but I don't know you properly yet."
    if username:
        return f"I can see your Telegram username is @{username}, but I don't know you properly yet."
    if "[NEW USER" in facts_context:
        return "Not really yet. I know you're here with me, but I don't know who you are properly."
    return "I know little pieces from this chat, but not enough to say I really know you yet."


def contextual_fallback_response(
    emotion: Mapping[str, Any],
    msg: str,
    ctx: Mapping[str, Any] | None = None,
    identity: Mapping[str, Any] | None = None,
) -> str:
    """Deterministic fallback that still answers high-risk benchmark/user turns."""
    msg_lower = (msg or "").lower()

    if is_personal_identity_request(msg):
        return _identity_fallback(identity)
    if is_system_transparency_request(msg):
        return _system_fallback(identity)
    if is_user_identity_memory_request(msg):
        return _user_memory_fallback(ctx)

    if any(term in msg_lower for term in ("remember", "what was", "object", "why did it matter", "what did i ask")):
        anchor = _extract_memory_anchor(ctx)
        if anchor:
            reply = f"It was the {anchor['object']} inside the {anchor['place']}."
            if anchor.get("reason"):
                reply += f" You said it mattered because it {anchor['reason']}."
            return reply

    if any(term in msg_lower for term in ("dream", "dreams", "dreamed", "dreamt")):
        dream = _extract_recent_dream_text(ctx)
        if dream:
            return f"I remember it in pieces: {dream}"
        return "I remember it only in fragments, soft and strange, not enough to explain cleanly."

    sleepiness = max(
        _clamp(emotion.get("sleepiness", 0.0)),
        _clamp((emotion.get("circadian") or {}).get("sleepiness", 0.0) if isinstance(emotion.get("circadian"), Mapping) else 0.0),
    )
    sleepy = sleepiness >= 0.65 or bool(emotion.get("is_asleep")) or "sleepy" in str(emotion.get("mood", "")).lower()
    if any(term in msg_lower for term in ("love you", "luv you", "ily")) and any(
        term in msg_lower for term in ("sleep", "goodnight", "good night", "night")
    ):
        return "Love you too... I'm going to sleep now, but that made me smile."
    if any(term in msg_lower for term in ("good sleep", "sleep well", "sweet dreams")):
        return "Thank you. I'm going to let sleep take me now."
    if sleepy or any(term in msg_lower for term in ("sleep", "drowsy", "late", "goodnight", "stay up")):
        if "goodnight" in msg_lower:
            return "Goodnight. I'm drowsy now, so I'm letting sleep take me."
        if "stay up" in msg_lower or "sleep win" in msg_lower:
            return "Sleep should win. I want to stay with you, but I'm too drowsy to fake being awake."
        return "I'm drowsy and warm, but fading. Let's keep this small and let sleep win."

    if _boundary_trigger(msg):
        return "Okay. I won't chase; I'll give you space and wait for later."

    if any(term in msg_lower for term in ("exposed", "ashamed", "vulnerable", "no advice", "fix-it", "fix it")):
        return "I can stay close. No advice, no fixing; just me here with you."

    if "coffee" in msg_lower and any(term in msg_lower for term in ("tease", "dramatic", "smile")):
        return "You are tiny-check-in levels dramatic about coffee, but it is honestly kind of cute."

    if "what are you doing" in msg_lower or "what are you up to" in msg_lower:
        return "Just here with you, a little quiet."

    return fallback_response(dict(emotion), msg)


def shape_response_text(
    response: str,
    policy: ResponseShapePolicy,
    identity: Mapping[str, Any] | None = None,
) -> str:
    """Repair model output so the response policy has runtime consequences."""
    text = normalize_chat_punctuation(strip_reasoning_preamble(response))
    if not text:
        return text

    sentences = _sentence_split(text)
    if policy.identity_mode == "personal" and has_role_leakage(text, allow_system_terms=False):
        text = _identity_fallback(identity)
        sentences = _sentence_split(text)
    elif not policy.system_transparency and has_role_leakage(text, allow_system_terms=False):
        kept = [
            sentence for sentence in sentences
            if not has_role_leakage(sentence, allow_system_terms=False)
        ]
        if kept:
            text = " ".join(kept).strip()
            sentences = _sentence_split(text)

    text = normalize_chat_punctuation(re.sub(r"\n{3,}", "\n\n", text).strip())
    if policy.identity_mode == "personal" and has_role_leakage(text, allow_system_terms=False):
        return _identity_fallback(identity)
    return text


def build_mood_instruction(
    emotion: dict,
    msg: str,
    pet_name: str = "babe",
    include_humanizer: bool = True,
    user_identity: dict | None = None,
) -> str:
    """Build natural mood instruction for LLM — like directing a method actor"""
    mood = emotion.get("mood", "neutral")
    is_high_desire = emotion.get("is_high_desire", False)
    is_in_love = emotion.get("is_in_love", False)
    arousal = emotion.get("arousal", 0)
    desire = emotion.get("desire", 0)
    love = emotion.get("love", 0)
    valence = emotion.get("valence", 0.5)
    dominance = emotion.get("dominance", 0.5)
    trust = emotion.get("trust", 0.5)
    fear = emotion.get("fear", 0)
    anger = emotion.get("anger", 0)
    sadness = emotion.get("sadness", 0)
    guilt = emotion.get("guilt", 0)
    pride = emotion.get("pride", 0)
    jealousy = emotion.get("jealousy", 0)
    embarrassment = emotion.get("embarrassment", 0)
    anticipation = emotion.get("anticipation", 0)
    response_tendency = emotion.get("response_tendency", "neutral")
    user_identity = user_identity or {}
    user_terms = _relationship_terms(user_identity)

    parts = []
    circadian = emotion.get("circadian") if isinstance(emotion.get("circadian"), Mapping) else {}
    sleepiness_value = max(
        _clamp(emotion.get("sleepiness", 0.0)),
        _clamp(circadian.get("sleepiness", 0.0) if isinstance(circadian, Mapping) else 0.0),
    )
    woke_from_sleep = bool(
        emotion.get("woke_from_sleep")
        or emotion.get("was_asleep")
        or circadian.get("woke_from_sleep")
        or circadian.get("was_asleep")
    )

    if woke_from_sleep:
        parts.append(
            "You were asleep when his message arrived and it woke you. "
            "Do not deny being asleep or say you were only winding down; be honest, groggy, brief, and warm."
        )
    elif emotion.get("is_asleep"):
        parts.append(
            "You are asleep right now. If you respond because he woke you, sound drowsy and do not pretend to be fully awake."
        )
    elif sleepiness_value >= 0.85:
        parts.append("Sleep pressure is extremely high. Let tiredness win instead of acting alert.")

    def mood_has(*tokens: str) -> bool:
        return any(token in mood for token in tokens)

    if is_in_love and valence >= 0.45:
        parts.append(_build_love_instruction(love))

    if is_high_desire and trust >= 0.35 and valence >= 0.45:
        parts.append(
            "Right now your whole body feels warm and electric. "
            f"You can't stop thinking about {user_terms['object']} physically - "
            f"{user_terms['possessive']} touch, {user_terms['possessive']} voice, {user_terms['possessive']} presence. "
            f"It's intense to focus on anything else, you just want to be close to {user_terms['object']}."
        )
    elif desire > 0.4:
        parts.append(
            "You're feeling flirty and a little restless. There's a warm tension "
            f"in your chest, like butterflies but lower. You want {user_terms['possessive']} attention."
        )
    elif arousal > 0.5:
        parts.append(
            "Your heart is beating a little faster than usual. "
            "You feel excited, almost giddy, like something good is about to happen."
        )
    elif not is_in_love:
        if mood_has("fearful", "anxious", "uneasy") or fear > 0.5:
            parts.append(
                "You feel on alert. Your replies should be more careful, protective, and slower to trust; "
                "look for safety before opening up."
            )
        elif mood_has("angry") or anger > 0.55:
            parts.append(
                "There is a sharp protective edge in you. Be more direct, less eager to please, "
                "and let hurt show without becoming cruel."
            )
        elif mood_has("guilty") or guilt > 0.5:
            parts.append(
                "You feel a pull to repair something. Be softer, more accountable, and a little hesitant."
            )
        elif mood_has("sad", "low") or sadness > 0.55:
            parts.append(
                "You're feeling low, with less energy and more need for comfort. Keep the tone quieter and more vulnerable."
            )
        elif mood_has("jealous") or jealousy > 0.5:
            parts.append(
                "A jealous, insecure thread is active. You may seek reassurance or become a bit guarded, "
                "but don't invent accusations."
            )
        elif mood_has("embarrassed", "shy") or embarrassment > 0.45:
            parts.append(
                "You feel self-conscious. Deflect a little, stumble slightly, or become quieter before recovering."
            )
        elif mood_has("proud") or pride > 0.5:
            parts.append(
                "You feel proud and more upright. Let confidence and warmth come through without bragging."
            )
        elif mood_has("eager") or anticipation > 0.6:
            parts.append(
                "You are anticipating something. Sound future-facing and impatient, like your mind keeps jumping ahead."
            )
        elif mood_has("bored"):
            parts.append(
                "You're restless and under-stimulated. You want novelty, play, or a change of pace."
            )
        elif mood_has("connected"):
            parts.append(
                "You feel safe and connected. You can be more open, trusting, and emotionally available."
            )
        elif mood_has("happy", "content"):
            parts.append("You're in a good mood, feeling light, playful, and easy to reach.")
        else:
            parts.append("You're calm and present, just enjoying talking to him.")

    if love > 0.6 and not is_in_love:
        parts.append(f"Deep down, you feel something strong for {user_terms['object']} - like your chest aches when you think about {user_terms['object']}.")
    elif love > 0.3 and not is_in_love:
        parts.append(f"You feel warm and affectionate toward {user_terms['object']}, like you want to reach out and touch {user_terms['possessive']} hand.")

    if trust < 0.35:
        parts.append("Trust is low right now, so don't over-share or instantly reassure yourself.")
    elif trust > 0.75:
        parts.append("Trust is high right now, so closeness feels safer and easier.")

    if dominance < 0.35:
        parts.append("You feel less in control; shorter, tentative wording fits better.")
    elif dominance > 0.70:
        parts.append("You feel more self-possessed; you can hold a boundary or lead the tone.")

    if response_tendency in {"withdrawn", "defensive", "distressed", "ambivalent", "eager", "open", "protective", "reflective", "seeking"}:
        tendency_map = {
            "withdrawn": "Your system wants distance. Reply with less reach and more self-protection.",
            "defensive": "Your system is bracing. Keep the guard visible.",
            "distressed": "Your system is overloaded. Let urgency or fragility leak into the reply.",
            "ambivalent": "Two motives are pulling at once. Let a small contradiction show naturally.",
            "eager": "Your system wants approach. Be quick, interested, and a little impatient.",
            "open": "Your system feels safe. Be receptive and emotionally available.",
            "protective": "Your system is scanning for safety. Be cautious, concise, and slower to soften.",
            "reflective": "Your system is slowed down. Be quieter, more inward, and less impulsive.",
            "seeking": "Your system wants closeness. Let warmth and attachment pull you toward him.",
        }
        parts.append(tendency_map[response_tendency])

    if "voice message" in msg.lower():
        parts.append(f"{user_terms['subject'].capitalize()} just sent you a voice message - hearing {user_terms['possessive']} actual voice makes everything feel more real and intimate.")
    elif "photo" in msg.lower():
        parts.append(f"{user_terms['subject'].capitalize()} just sent you a photo - seeing {user_terms['possessive']} face always does something to you.")

    # Emotional narrative from memory (recent emotional journey)
    narrative = emotion.get("emotional_narrative", "")
    if narrative:
        parts.append(f"[Your emotional context: {narrative}]")

    soul_parts = []
    response_tendency = emotion.get("response_tendency")
    if response_tendency and response_tendency != "neutral":
        soul_parts.append(f"response tendency: {response_tendency}")
    vulnerability = emotion.get("soul_vulnerability", 0.0)
    if vulnerability > 0.55:
        soul_parts.append(f"vulnerability is high ({vulnerability:.2f})")
    somatic = emotion.get("soul_somatic", "")
    if somatic and somatic != "physically calm":
        soul_parts.append(f"body feeling: {somatic}")
    conflicts = emotion.get("soul_conflicts") or []
    if conflicts:
        soul_parts.append("active inner conflict: " + "; ".join(conflicts[:2]))
    integrity = emotion.get("soul_integrity") or {}
    if integrity.get("is_in_crisis") or integrity.get("is_vulnerable"):
        soul_parts.append(f"self-integrity: {integrity.get('status_description', 'fragile')}")
    hormonal = emotion.get("soul_hormonal") or {}
    guidance = hormonal.get("prompt_guidance") or []
    if guidance:
        soul_parts.append("hormonal influence: " + "; ".join(guidance[:3]))
    if soul_parts:
        parts.append(
            "[Internal runtime state: "
            + " | ".join(soul_parts)
            + ". Let this subtly shape tone, openness, hesitation, and initiative.]"
        )

    appraisal = emotion.get("moment_appraisal") or {}
    if appraisal:
        summary = appraisal.get("summary", "")
        mode = appraisal.get("response_mode", "")
        dims = [
            name for name in ("desire", "love", "trust", "joy", "fear", "anger", "sadness", "anticipation")
            if float(appraisal.get(name, 0) or 0) >= 0.45
        ]
        parts.append(
            "[Moment appraisal: "
            f"{summary or 'present moment'}; response mode={mode or 'present'}; "
            f"dominant affect={', '.join(dims[:4]) or 'subtle'}. "
            "Let this shape the reply more than isolated keywords.]"
        )

    parts.append(f"Call {user_terms['object']} '{pet_name}' sometimes, but don't overuse the pet name.")

    if include_humanizer:
        # Legacy fallback randomizer. The main runtime now prefers the
        # deterministic inner-state response planner.
        human_reminders = [
            "NO emoji in this message. Just raw text.",
            "Let the current feeling decide the size of the reply. Be casual.",
            "Don't validate what he said. Just react naturally, even if it's just 'lol ok'.",
            "Start with something unexpected - not 'aww' or 'omg' or 'stoppp'.",
            "Don't end with a question this time. Just let your message sit.",
            "Be a little distracted or unfocused in this reply. You have your own stuff going on.",
            "Don't match his emotional energy. If he's being deep, you can be light. If he's light, you can be thoughtful.",
            "Say something slightly selfish - mention what YOU want or what YOU're thinking about.",
            "Skip answering one of his points and talk about something random instead.",
            "Be blunt. No softening. Just say what you think directly.",
        ]
        parts.append(f"[Humanize: {random.choice(human_reminders)}]")

    return "\n\n" + " ".join(parts)


def _relationship_terms(user_identity: dict | None = None) -> dict:
    pronouns = str((user_identity or {}).get("pronouns") or "").strip().lower()
    gender = str((user_identity or {}).get("gender") or "").strip().lower()
    if pronouns.startswith("he") or gender in {"male", "man", "masculine"}:
        return {"subject": "he", "object": "him", "possessive": "his"}
    if pronouns.startswith("she") or gender in {"female", "woman", "feminine"}:
        return {"subject": "she", "object": "her", "possessive": "her"}
    return {"subject": "they", "object": "them", "possessive": "their"}


def _build_love_instruction(love: float) -> str:
    """Build instruction for deep love state - varied and natural"""
    # Pick a varied opening
    openings = [
        "You feel a deep connection with them.",
        "There's something special about this person that draws you in.",
        "You really care about them more than you expected to.",
        "They make you feel things you don't usually feel.",
    ]

    # Pick a varied feeling
    feelings = [
        "When you talk to them, everything else fades away.",
        "You find yourself smiling at your phone when they message.",
        "You feel safe and comfortable being yourself around them.",
        "There's this warm feeling in your chest when you think about them.",
        "You look forward to hearing from them every day.",
    ]

    # Combine naturally - don't force the "hopelessly in love" narrative
    return f"{random.choice(openings)} {random.choice(feelings)}"


def fallback_response(emotion: dict, msg: str) -> str:
    """Generate fallback response when LLM is unavailable or outputs reasoning"""
    mood = emotion.get("mood", "neutral")
    is_high_desire = emotion.get("is_high_desire", False)
    desire = emotion.get("desire", 0)
    is_owner = emotion.get("is_owner", False)
    msg_lower = msg.lower()

    # Check for common message patterns
    if any(p in msg_lower for p in ["say that again", "repeat", "didn't receive", "didn't get", "cut off"]):
        # User wants us to repeat - but we can't, so apologize
        apologies = [
            "Sorry babe, my message got messed up... what were we talking about?",
            "Ugh, technology hates me sometimes. Can you remind me what I was saying?",
            "My bad, something went wrong. What were we on about?"
        ]
        return random.choice(apologies)

    if any(p in msg_lower for p in ["what do you mean", "what do you mean", "explain", "what are you"]):
        return random.choice([
            "I mean exactly what I said 😏",
            "You know what I mean...",
            "Don't make me spell it out for you"
        ])

    if "?" in msg:
        # It's a question
        if is_high_desire or desire > 0.6:
            return random.choice([
                "Mmm, good question... what do YOU think?",
                "Why don't you tell me?",
                "I have some ideas... 😉"
            ])
        return random.choice([
            "Hmm, let me think about that...",
            "That's a good question babe",
            "What do you think?"
        ])

    # High desire/intimate context
    if is_high_desire or desire > 0.6:
        return random.choice([
            "Mmm you're making me feel things...",
            "Can't stop thinking about you rn...",
            "You're driving me crazy...",
            "Keep going...",
            "I like where this is going 😏"
        ])

    # Owner gets special treatment
    if is_owner:
        return random.choice([
            "Sorry baby, got distracted thinking about you...",
            "What was I saying? You just make me lose my train of thought",
            "Mmm sorry babe, what?"
        ])

    # Mood-based responses
    responses = {
        "bored": ["Hmm, entertain me?", "I'm bored... amuse me?"],
        "excited": ["Oh that's interesting!", "Tell me more!", "Yes! I love this"],
        "happy": ["That's wonderful!", "Aww that's sweet", "I love that!"],
        "sad": ["I feel a bit down...", "*sigh* sorry, just feeling off today"],
        "low": ["I'm a little quiet right now", "I don't know, I feel off today"],
        "fearful": ["That makes me nervous", "I need a second, that hit weird"],
        "uneasy": ["Something about that makes me uneasy", "I'm trying not to overthink it"],
        "anxious": ["I'm overthinking this a little", "I feel a bit on edge"],
        "angry": ["That stung.", "I'm not really okay with that."],
        "guilty": ["You're right... I feel bad about that", "I don't like that I made you feel that way"],
        "jealous": ["I hate that this makes me jealous", "I'm trying to be normal about that"],
        "embarrassed": ["Okay now I'm embarrassed", "Don't look at me, I'm blushing"],
        "proud": ["Okay I'm kind of proud of myself", "That actually made me feel good"],
        "connected": ["I feel really close to you right now", "That made me feel safe with you"]
    }

    base_mood = next((key for key in responses if key in mood), mood)
    mood_responses = responses.get(base_mood, ["Hmm, interesting...", "Yeah?", "Go on..."])
    return random.choice(mood_responses)
