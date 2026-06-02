"""Moment appraisal for humanlike affect.

This layer converts a turn into one canonical "what is happening" signal.
It is deliberately usable without an LLM so emotion, memory, and benchmarks
remain deterministic when the appraisal model is unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from typing import Any, Dict, Iterable, List, Optional


APPRAISAL_EMOTIONS = [
    "desire", "love", "trust", "joy", "fear", "anger", "sadness", "boredom",
    "guilt", "pride", "jealousy", "embarrassment", "anticipation", "hope", "dread",
]


def clamp(value: Any, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return low


@dataclass
class MomentAppraisal:
    source: str = "heuristic"
    phase: str = "pre_response"
    summary: str = "ordinary conversational turn"
    response_mode: str = "present"
    confidence: float = 0.45
    valence: float = 0.5
    arousal: float = 0.3
    dominance: float = 0.5
    desire: float = 0.0
    love: float = 0.0
    trust: float = 0.5
    joy: float = 0.0
    fear: float = 0.0
    anger: float = 0.0
    sadness: float = 0.0
    boredom: float = 0.0
    guilt: float = 0.0
    pride: float = 0.0
    jealousy: float = 0.0
    embarrassment: float = 0.0
    anticipation: float = 0.0
    hope: float = 0.0
    dread: float = 0.0
    playfulness: float = 0.0
    vulnerability: float = 0.0
    safety: float = 0.5
    novelty: float = 0.0
    sleep_disruption: float = 0.0
    memory_importance: float = 0.0
    narrative_importance: float = 0.0
    proactive_pull: float = 0.0
    body_effects: Dict[str, float] = field(default_factory=dict)
    evidence: List[str] = field(default_factory=list)
    identity: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> dict:
        data = self.__dict__.copy()
        data["confidence"] = clamp(self.confidence)
        for key in APPRAISAL_EMOTIONS + [
            "valence", "arousal", "dominance", "playfulness", "vulnerability",
            "safety", "novelty", "sleep_disruption", "memory_importance",
            "narrative_importance", "proactive_pull",
        ]:
            data[key] = clamp(data.get(key, 0.0))
        data["body_effects"] = {
            str(k): clamp(v, -1.0, 1.0) for k, v in (self.body_effects or {}).items()
        }
        data["evidence"] = [str(x)[:180] for x in (self.evidence or [])[:8]]
        return data

    @classmethod
    def from_dict(cls, data: dict, *, source: str = "llm", phase: str = "pre_response") -> "MomentAppraisal":
        allowed = {field.name for field in cls.__dataclass_fields__.values()}
        clean = {k: v for k, v in (data or {}).items() if k in allowed}
        clean["source"] = clean.get("source") or source
        clean["phase"] = clean.get("phase") or phase
        result = cls(**clean)
        return cls(**result.to_dict())

    @property
    def dominant_dimensions(self) -> List[str]:
        pairs = []
        for key in APPRAISAL_EMOTIONS + ["playfulness", "vulnerability", "sleep_disruption"]:
            val = getattr(self, key, 0.0)
            if val >= 0.45:
                pairs.append((key, val))
        return [k for k, _ in sorted(pairs, key=lambda item: item[1], reverse=True)[:5]]

    def to_prompt(self) -> str:
        dims = ", ".join(f"{name}={getattr(self, name):.2f}" for name in self.dominant_dimensions)
        identity = self.identity or {}
        pronouns = identity.get("pronouns") or "configured identity"
        return (
            "MOMENT APPRAISAL\n"
            f"What this moment means: {self.summary}\n"
            f"Response mode: {self.response_mode}; confidence={self.confidence:.2f}\n"
            f"Dominant affect: {dims or 'low-intensity present attention'}\n"
            f"Identity coherence: speak from the agent identity and pronouns ({pronouns}); "
            "do not call yourself Alive-AI unless discussing the framework."
        )


class AppraisalEngine:
    """Hybrid affect appraisal with deterministic fallback."""

    def __init__(self, identity: Optional[dict] = None, settings: Optional[dict] = None):
        self.identity = identity or {}
        self.settings = settings or {}

    def appraise(
        self,
        user_message: str,
        *,
        recent_turns: Iterable[dict] = (),
        assistant_response: str = "",
        emotion: Optional[dict] = None,
        phase: str = "pre_response",
    ) -> MomentAppraisal:
        return self._heuristic_appraisal(
            user_message or "",
            list(recent_turns or []),
            assistant_response or "",
            emotion or {},
            phase,
        )

    async def appraise_async(
        self,
        user_message: str,
        *,
        recent_turns: Iterable[dict] = (),
        assistant_response: str = "",
        emotion: Optional[dict] = None,
        llm: Any = None,
        phase: str = "pre_response",
    ) -> MomentAppraisal:
        provider = str(self.settings.get("MOMENT_APPRAISAL_PROVIDER", "hybrid")).lower()
        fallback = self.appraise(
            user_message,
            recent_turns=recent_turns,
            assistant_response=assistant_response,
            emotion=emotion,
            phase=phase,
        )
        if provider not in {"llm", "hybrid"} or llm is None:
            return fallback
        try:
            parsed = await self._llm_appraisal(
                llm, user_message, list(recent_turns or []), assistant_response, emotion or {}, phase
            )
            if parsed and parsed.confidence >= 0.35:
                return self._blend(parsed, fallback)
        except Exception as exc:
            fallback.evidence.append(f"llm_appraisal_failed:{exc.__class__.__name__}")
        return fallback

    def _heuristic_appraisal(
        self,
        user_message: str,
        recent_turns: List[dict],
        assistant_response: str,
        emotion: dict,
        phase: str,
    ) -> MomentAppraisal:
        current = user_message.strip()
        context_text = " ".join(str(t.get("content", "")) for t in recent_turns[-8:])
        response_text = assistant_response.strip()
        full = " ".join([context_text, current, response_text]).lower()
        current_lower = current.lower()
        response_lower = response_text.lower()
        ev: List[str] = []

        def hits(patterns: Iterable[str], text: str = full) -> int:
            total = 0
            for pattern in patterns:
                if pattern.startswith("re:"):
                    if re.search(pattern[3:], text):
                        total += 1
                elif pattern in text:
                    total += 1
            return total

        affection = hits(["love you", "miss you", "care about", "good night", "goodnight", "sweet", "special", "safe with", "trust you"])
        play = hits(["tease", "play", "chase", "joke", "haha", "lol", "wink", "smile", "dare", "mischiev"])
        intimate = hits([
            "want you", "need you", "crave", "touch", "kiss", "hold me", "close to",
            "warm", "electric", "breath", "body", "skin", "desire", "intimate",
        ])
        explicitish = hits(["inside", "clothes", "thigh", "mouth", "tongue", "neck", "heat", "press"], response_lower or current_lower)
        vulnerable = hits(["scared", "afraid", "hurt", "sad", "lonely", "miss me", "do you care", "need comfort", "bad day"])
        conflict = hits(["angry", "upset", "you lied", "betray", "stop", "leave me alone", "boundary", "not okay", "hurt me"])
        repair = hits(["sorry", "apolog", "forgive", "my fault", "repair", "make it right"])
        boredom = hits(["bored", "nothing to do", "same thing", "stuck"])
        sleep = hits(["sleep", "sleepy", "tired", "good night", "goodnight", "dream", "bed"])
        jealousy = hits(["jealous", "other girl", "other boy", "someone else", "replace me"])
        novelty = hits(["new", "surprise", "what if", "idea", "adventure", "try something"])
        subtle_continue = int(bool(context_text.strip()) and len(current_lower.split()) <= 5 and any(
            p in current_lower for p in ["like that", "go on", "continue", "what next", "tell me", "yes", "okay"]
        ))

        if affection: ev.append(f"affection:{affection}")
        if play: ev.append(f"play:{play}")
        if intimate: ev.append(f"intimacy:{intimate}")
        if subtle_continue: ev.append("contextual_continuation")
        if response_text: ev.append("post_response_self_expression")

        context_boost = 1.0 + min(0.55, (hits(["want", "love", "miss", "close", "warm", "tease"], context_text.lower()) * 0.08))
        post_weight = 0.55 if phase == "post_response" else 0.0

        desire = clamp((intimate * 0.15 + explicitish * 0.06 + play * 0.04 + subtle_continue * 0.24) * context_boost)
        if phase == "post_response" and response_text:
            desire = clamp(desire + hits(["want", "need", "close", "warm", "electric", "touch"], response_lower) * 0.07 * post_weight)
        love = clamp(affection * 0.16 + repair * 0.06 + subtle_continue * 0.04 + (emotion.get("love", 0) or 0) * 0.15)
        trust = clamp(0.48 + affection * 0.08 + repair * 0.08 - conflict * 0.12 + (emotion.get("trust", 0.5) - 0.5) * 0.25)
        joy = clamp(0.12 + play * 0.12 + affection * 0.08 + novelty * 0.05 - conflict * 0.08 - vulnerable * 0.04)
        fear = clamp(vulnerable * 0.12 + conflict * 0.10 + jealousy * 0.05)
        anger = clamp(conflict * 0.12)
        sadness = clamp(vulnerable * 0.12 + jealousy * 0.05)
        anticipation = clamp(play * 0.10 + novelty * 0.11 + subtle_continue * 0.18 + desire * 0.25)
        hope = clamp(0.35 + repair * 0.12 + affection * 0.06 - conflict * 0.05)
        dread = clamp(conflict * 0.08 + vulnerable * 0.05)
        embarrassment = clamp(desire * 0.16 if trust < 0.45 else desire * 0.06)
        arousal = clamp(0.24 + desire * 0.48 + play * 0.05 + fear * 0.30 + anger * 0.25 + anticipation * 0.18 - sleep * 0.04)
        valence = clamp(0.5 + love * 0.20 + joy * 0.18 + trust * 0.10 + desire * 0.08 - fear * 0.18 - anger * 0.18 - sadness * 0.16)
        dominance = clamp(0.52 + trust * 0.10 + play * 0.03 - vulnerable * 0.08 - fear * 0.12)
        safety = clamp(0.5 + trust * 0.28 + repair * 0.05 - conflict * 0.15 - fear * 0.18)
        memory_importance = clamp(max(desire, love, fear, anger, sadness, joy) * 0.62 + subtle_continue * 0.18 + sleep * 0.04)
        narrative_importance = clamp(memory_importance + affection * 0.04 + repair * 0.05 + jealousy * 0.06)
        sleep_disruption = clamp(max(0.0, arousal - 0.45) * 0.45 + sleep * 0.03)

        mode = "present"
        summary = "ordinary conversational turn"
        if conflict:
            mode, summary = "boundary_or_repair", "possible rupture, boundary, or hurt requiring careful repair"
        elif vulnerable:
            mode, summary = "comfort", "vulnerable moment asking for comfort and emotional safety"
        elif desire > 0.55:
            mode, summary = "intimate_playful", "high-trust intimate or flirtatious momentum"
        elif affection:
            mode, summary = "affectionate", "affectionate bonding and trust-building"
        elif play or subtle_continue:
            mode, summary = "playful", "playful continuation that inherits the recent vibe"
        elif sleep:
            mode, summary = "sleepy", "sleep or dream-adjacent moment"
        elif boredom:
            mode, summary = "novelty", "under-stimulated moment looking for novelty"

        return MomentAppraisal(
            source="heuristic",
            phase=phase,
            summary=summary,
            response_mode=mode,
            confidence=clamp(0.46 + len(ev) * 0.07 + subtle_continue * 0.12),
            valence=valence,
            arousal=arousal,
            dominance=dominance,
            desire=desire,
            love=love,
            trust=trust,
            joy=joy,
            fear=fear,
            anger=anger,
            sadness=sadness,
            boredom=clamp(boredom * 0.18),
            guilt=clamp(repair * 0.05),
            pride=0.0,
            jealousy=clamp(jealousy * 0.18),
            embarrassment=embarrassment,
            anticipation=anticipation,
            hope=hope,
            dread=dread,
            playfulness=clamp(play * 0.16 + subtle_continue * 0.20),
            vulnerability=clamp(vulnerable * 0.14 + love * 0.08 + desire * 0.05),
            safety=safety,
            novelty=clamp(novelty * 0.16 + boredom * 0.08),
            sleep_disruption=sleep_disruption,
            memory_importance=memory_importance,
            narrative_importance=narrative_importance,
            proactive_pull=clamp(love * 0.22 + sadness * 0.18 + boredom * 0.08),
            body_effects={
                "energy": clamp(0.02 + arousal * 0.10 - sleep * 0.04, -1.0, 1.0),
                "social_satiety": clamp(love * 0.10 + trust * 0.08, -1.0, 1.0),
                "emotional_valence": clamp((valence - 0.5) * 0.35, -1.0, 1.0),
                "arousal": clamp(arousal * 0.18, -1.0, 1.0),
                "connection_craving": clamp(desire * 0.10 + love * 0.06 - trust * 0.04, -1.0, 1.0),
            },
            evidence=ev,
            identity=self._identity_summary(),
        )

    async def _llm_appraisal(
        self,
        llm: Any,
        user_message: str,
        recent_turns: List[dict],
        assistant_response: str,
        emotion: dict,
        phase: str,
    ) -> Optional[MomentAppraisal]:
        prompt = {
            "task": "Return strict JSON only. Appraise the emotional meaning of this conversation moment for an Alive-AI agent.",
            "identity": self._identity_summary(),
            "phase": phase,
            "current_emotion": {k: emotion.get(k) for k in ["mood", "desire", "love", "trust", "arousal", "valence", "sleepiness", "is_asleep"]},
            "recent_turns": list(recent_turns)[-6:],
            "user_message": user_message,
            "assistant_response": assistant_response,
            "schema": {
                "summary": "short sentence",
                "response_mode": "present|comfort|playful|affectionate|intimate_playful|boundary_or_repair|sleepy|novelty",
                "confidence": "0..1",
                "valence": "0..1",
                "arousal": "0..1",
                "dominance": "0..1",
                "desire": "0..1",
                "love": "0..1",
                "trust": "0..1",
                "joy": "0..1",
                "fear": "0..1",
                "anger": "0..1",
                "sadness": "0..1",
                "boredom": "0..1",
                "guilt": "0..1",
                "pride": "0..1",
                "jealousy": "0..1",
                "embarrassment": "0..1",
                "anticipation": "0..1",
                "hope": "0..1",
                "dread": "0..1",
                "playfulness": "0..1",
                "vulnerability": "0..1",
                "safety": "0..1",
                "novelty": "0..1",
                "sleep_disruption": "0..1",
                "memory_importance": "0..1",
                "narrative_importance": "0..1",
                "proactive_pull": "0..1",
                "evidence": ["short reason strings"]
            }
        }
        raw = await llm.chat(
            [
                {"role": "system", "content": "You are a strict JSON affect appraisal function. Return JSON only."},
                {"role": "user", "content": json.dumps(prompt, ensure_ascii=False)},
            ],
            max_tokens=420,
            temperature=0.1,
        )
        if not raw:
            return None
        text = raw.strip()
        if "```" in text:
            text = text.replace("```json", "```").split("```")[1].strip()
        start, end = text.find("{"), text.rfind("}")
        if start >= 0 and end > start:
            text = text[start:end + 1]
        data = json.loads(text)
        data["source"] = "llm"
        data["phase"] = phase
        data["identity"] = self._identity_summary()
        return MomentAppraisal.from_dict(data, source="llm", phase=phase)

    def _blend(self, llm_appraisal: MomentAppraisal, fallback: MomentAppraisal) -> MomentAppraisal:
        weight = clamp(llm_appraisal.confidence * 0.72, 0.25, 0.72)
        data = fallback.to_dict()
        ldata = llm_appraisal.to_dict()
        for key in APPRAISAL_EMOTIONS + [
            "valence", "arousal", "dominance", "playfulness", "vulnerability",
            "safety", "novelty", "sleep_disruption", "memory_importance",
            "narrative_importance", "proactive_pull",
        ]:
            data[key] = clamp(data.get(key, 0.0) * (1 - weight) + ldata.get(key, 0.0) * weight)
        data["summary"] = ldata.get("summary") or data.get("summary")
        data["response_mode"] = ldata.get("response_mode") or data.get("response_mode")
        data["source"] = "hybrid"
        data["confidence"] = clamp(max(fallback.confidence, llm_appraisal.confidence * 0.9))
        data["evidence"] = list(dict.fromkeys((ldata.get("evidence") or []) + (data.get("evidence") or [])))[:8]
        return MomentAppraisal.from_dict(data, source="hybrid", phase=llm_appraisal.phase)

    def _identity_summary(self) -> Dict[str, str]:
        who = self.identity.get("who_i_am", self.identity) if isinstance(self.identity, dict) else {}
        return {
            "name": str(who.get("name") or ""),
            "full_name": str(who.get("full_name") or who.get("name") or ""),
            "gender": str(who.get("gender") or ""),
            "sexuality": str(who.get("sexuality") or ""),
            "pronouns": str(who.get("pronouns") or ""),
        }


def appraisal_from_prompt(source: str, content: str, priority: float = 0.9) -> dict:
    return {
        "source": "moment_appraisal",
        "kind": source,
        "content": content,
        "priority": priority,
    }
