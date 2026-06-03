"""Conversation context compiler.

This module turns existing memory sources into a compact, ranked context pack
for the next LLM call. It is intentionally deterministic in v1 so local models
get better context without needing another model in the request path.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


_WORD_RE = re.compile(r"[a-z0-9']+")
_ACTION_VERBS = (
    "make",
    "build",
    "create",
    "write",
    "play",
    "produce",
    "compose",
    "design",
    "code",
)
_ACTION_PRESENT = {
    "make": "makes",
    "build": "builds",
    "create": "creates",
    "write": "writes",
    "play": "plays",
    "produce": "produces",
    "compose": "composes",
    "design": "designs",
    "code": "codes",
}
_STOPWORDS = {
    "a",
    "about",
    "after",
    "again",
    "all",
    "am",
    "and",
    "are",
    "as",
    "at",
    "be",
    "because",
    "between",
    "but",
    "can",
    "did",
    "do",
    "does",
    "for",
    "from",
    "get",
    "have",
    "he",
    "her",
    "him",
    "i",
    "if",
    "in",
    "is",
    "it",
    "like",
    "me",
    "my",
    "of",
    "on",
    "or",
    "our",
    "she",
    "so",
    "that",
    "the",
    "this",
    "to",
    "us",
    "was",
    "we",
    "what",
    "when",
    "with",
    "you",
    "your",
}


def _now() -> str:
    return datetime.now().isoformat()


def _normalise(text: str) -> str:
    return " ".join(_WORD_RE.findall(str(text or "").lower()))


def _keywords(text: str) -> set[str]:
    return {w for w in _WORD_RE.findall(str(text or "").lower()) if len(w) > 2 and w not in _STOPWORDS}


def _clean_phrase(text: str, max_words: int = 12) -> str:
    cleaned = re.sub(r"\s+", " ", str(text or "")).strip(" .,!?:;\"'")
    cleaned = re.split(r"\s+(?:but|because)\s+", cleaned, maxsplit=1)[0].strip(" .,!?:;\"'")
    words = cleaned.split()
    return " ".join(words[:max_words]).strip()


def _card_id(card_type: str, text: str) -> str:
    digest = hashlib.sha1(f"{card_type}:{_normalise(text)}".encode("utf-8")).hexdigest()
    return digest[:16]


@dataclass
class MemoryCard:
    """Small structured memory unit selected by the compiler."""

    type: str
    text: str
    source_turn: str = ""
    timestamp: str = field(default_factory=_now)
    importance: float = 0.5
    emotional_weight: float = 0.0
    durability: str = "session"
    entities: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    id: str = ""

    def __post_init__(self):
        self.text = str(self.text or "").strip()
        if not self.id:
            self.id = _card_id(self.type, self.text)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "text": self.text,
            "source_turn": self.source_turn,
            "timestamp": self.timestamp,
            "importance": round(float(self.importance), 4),
            "emotional_weight": round(float(self.emotional_weight), 4),
            "durability": self.durability,
            "entities": list(self.entities),
            "tags": list(self.tags),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "MemoryCard | None":
        try:
            text = str(data.get("text") or "").strip()
            card_type = str(data.get("type") or "").strip()
            if not text or not card_type:
                return None
            return cls(
                id=str(data.get("id") or ""),
                type=card_type,
                text=text,
                source_turn=str(data.get("source_turn") or ""),
                timestamp=str(data.get("timestamp") or _now()),
                importance=float(data.get("importance", 0.5) or 0.5),
                emotional_weight=float(data.get("emotional_weight", 0.0) or 0.0),
                durability=str(data.get("durability") or "session"),
                entities=[str(x) for x in data.get("entities", []) if str(x).strip()],
                tags=[str(x) for x in data.get("tags", []) if str(x).strip()],
            )
        except Exception:
            return None


class ContextCompiler:
    """Builds a compact, ranked context pack from Alive-AI memory sources."""

    def __init__(self, data_path: Path, agent_name: str = "AI"):
        self.data_path = Path(data_path)
        self.cards_path = self.data_path / "context_cards.jsonl"
        self.agent_name = str(agent_name or "AI")
        self.data_path.mkdir(parents=True, exist_ok=True)

    def add_turn(self, user_msg: str, ai_msg: str, emotion: dict | None = None) -> list[MemoryCard]:
        """Extract and persist cards from a completed conversation turn."""
        emotion = emotion or {}
        cards = self.extract_cards_from_turn(user_msg, ai_msg, emotion=emotion, source_turn=_now())
        self.add_cards(cards)
        return cards

    def add_cards(self, cards: Iterable[MemoryCard]) -> None:
        existing_ids = {card.id for card in self.load_cards(limit=1000)}
        new_cards = [card for card in cards if card.text and card.id not in existing_ids]
        if not new_cards:
            return
        self.cards_path.parent.mkdir(parents=True, exist_ok=True)
        with self.cards_path.open("a", encoding="utf-8") as f:
            for card in new_cards:
                f.write(json.dumps(card.to_dict(), ensure_ascii=False) + "\n")

    def load_cards(self, limit: int = 300) -> list[MemoryCard]:
        if not self.cards_path.exists():
            return []
        cards: list[MemoryCard] = []
        try:
            lines = self.cards_path.read_text(encoding="utf-8").splitlines()
        except Exception:
            return []
        for line in lines[-limit:]:
            try:
                card = MemoryCard.from_dict(json.loads(line))
            except Exception:
                card = None
            if card:
                cards.append(card)
        return cards

    def extract_cards_from_turn(
        self,
        user_msg: str,
        ai_msg: str = "",
        emotion: dict | None = None,
        source_turn: str = "",
    ) -> list[MemoryCard]:
        cards: list[MemoryCard] = []
        user_msg = str(user_msg or "").strip()
        ai_msg = str(ai_msg or "").strip()
        if not user_msg and not ai_msg:
            return cards

        for text, importance in self._extract_user_facts(user_msg):
            cards.append(MemoryCard(
                type="user_fact",
                text=text,
                source_turn=source_turn,
                importance=importance,
                durability="durable",
                entities=["Alex"],
                tags=["user", "fact"],
            ))

        for text in self._extract_preferences(user_msg):
            cards.append(MemoryCard(
                type="preference",
                text=text,
                source_turn=source_turn,
                importance=0.72,
                durability="durable",
                entities=["Alex"],
                tags=["user", "preference"],
            ))

        relationship_cards = self._extract_relationship_cards(user_msg, ai_msg)
        cards.extend(MemoryCard(
            type=card_type,
            text=text,
            source_turn=source_turn,
            importance=importance,
            emotional_weight=emotional_weight,
            durability="session",
            entities=["Alex", self.agent_name],
            tags=tags,
        ) for card_type, text, importance, emotional_weight, tags in relationship_cards)

        exact_quote = self._important_quote(user_msg)
        if exact_quote:
            cards.append(MemoryCard(
                type="exact_quote",
                text=exact_quote,
                source_turn=source_turn,
                importance=0.58,
                durability="session",
                entities=["Alex"],
                tags=["quote"],
            ))

        emotion = emotion or {}
        desire = float(emotion.get("desire", 0) or 0)
        love = float(emotion.get("love", 0) or 0)
        trust = float(emotion.get("trust", 0) or 0)
        if max(desire, love, trust) >= 0.65 and user_msg:
            cards.append(MemoryCard(
                type="emotional_anchor",
                text=f"Recent emotional peak with Alex: {user_msg[:120]}",
                source_turn=source_turn,
                importance=0.62,
                emotional_weight=max(desire, love, trust),
                durability="session",
                entities=["Alex", self.agent_name],
                tags=["emotion"],
            ))

        return self._dedupe(cards)

    def compile(
        self,
        current_message: str,
        *,
        semantic_facts: dict | None = None,
        facts_context: str = "",
        summaries: str = "",
        history: list[dict[str, str]] | None = None,
        related_memories: str = "",
        max_words: int | None = None,
    ) -> dict[str, Any]:
        """Return prompt text, selected cards, and trace metadata."""
        if max_words is None:
            max_words = int(os.environ.get("ALIVE_CONTEXT_COMPILER_MAX_WORDS", "650"))
        max_words = max(220, min(int(max_words), 1200))
        history = history or []

        candidates = []
        candidates.extend(self.load_cards(limit=350))
        candidates.extend(self._cards_from_semantic(semantic_facts or {}))
        candidates.extend(self._cards_from_facts_context(facts_context))
        candidates.extend(self._cards_from_summaries(summaries))
        candidates.extend(self._cards_from_related(related_memories))
        candidates.extend(self._cards_from_history(history))
        candidates = self._dedupe(candidates)

        intents = self._detect_intents(current_message)
        scored = []
        total = len(candidates)
        for index, card in enumerate(candidates):
            score, reasons = self._score_card(card, current_message, intents, index, total)
            if score >= 0.45:
                scored.append({
                    "score": round(score, 4),
                    "reasons": reasons,
                    "card": card,
                })
        scored.sort(key=lambda item: item["score"], reverse=True)
        selected = scored[:18]

        prompt = self._render_prompt(
            current_message=current_message,
            selected=selected,
            history=history,
            intents=intents,
            max_words=max_words,
        )
        trace = {
            "intents": intents,
            "candidate_count": len(candidates),
            "selected_count": len(selected),
            "selected": [
                {
                    **item["card"].to_dict(),
                    "score": item["score"],
                    "reasons": item["reasons"],
                }
                for item in selected
            ],
            "skipped_high_score": [
                {
                    **item["card"].to_dict(),
                    "score": item["score"],
                    "reasons": item["reasons"],
                }
                for item in scored[18:24]
            ],
        }
        return {
            "text": prompt,
            "cards": trace["selected"],
            "trace": trace,
        }

    def _extract_user_facts(self, user_msg: str) -> list[tuple[str, float]]:
        facts: list[tuple[str, float]] = []
        original = str(user_msg or "")
        lower = original.lower()
        verbs = "|".join(_ACTION_VERBS)
        pattern = re.compile(
            rf"(?:\bi\s+|\band\s+)({verbs})\s+(.+?)(?=\s+and\s+(?:{verbs})\s+|[.!?,;]|$)",
            re.IGNORECASE,
        )
        for match in pattern.finditer(original):
            verb = match.group(1).lower()
            obj = _clean_phrase(match.group(2), max_words=8)
            if obj and not obj.lower().startswith(("you ", "that ", "this ")):
                facts.append((f"Alex {_ACTION_PRESENT.get(verb, verb + 's')} {obj}.", 0.84))

        trait_match = re.search(r"\bi(?:'m| am)\s+(.+?)(?=\s+but\s+|[.!?,;]|$)", original, re.IGNORECASE)
        if trait_match:
            trait = _clean_phrase(trait_match.group(1), max_words=10)
            trait_l = trait.lower()
            if any(token in trait_l for token in ("intense", "honest", "creative", "curious", "care")):
                trait = trait.replace("i care", "he cares")
                facts.append((f"Alex is {trait}.", 0.78))

        try_match = re.search(r"\bi\s+try\s+to\s+(.+?)(?=[.!?,;]|$)", original, re.IGNORECASE)
        if try_match:
            phrase = _clean_phrase(try_match.group(1), max_words=8)
            if phrase:
                facts.append((f"Alex tries to {phrase}.", 0.8))

        if "when i care" in lower and "intense" in lower:
            facts.append(("Alex is intense when he cares.", 0.82))
        return self._dedupe_fact_pairs(facts)

    def _extract_preferences(self, user_msg: str) -> list[str]:
        prefs = []
        for match in re.finditer(r"\bi\s+(like|love|prefer|want|need)\s+(.+?)(?=[.!?,;]|$)", user_msg, re.IGNORECASE):
            verb = match.group(1).lower()
            obj = _clean_phrase(match.group(2), max_words=12)
            if obj and not obj.lower().startswith(("you to", "to test")):
                prefs.append(f"Alex {verb}s {obj}.")
        return list(dict.fromkeys(prefs))

    def _extract_relationship_cards(self, user_msg: str, ai_msg: str) -> list[tuple[str, str, float, float, list[str]]]:
        cards = []
        user_l = user_msg.lower()
        ai_l = ai_msg.lower()
        if any(token in user_l for token in ("sorry", "apolog", "unfair", "pushed too hard")):
            cards.append((
                "hurt_or_repair",
                "Alex apologized and does not want closeness that erases Alice's feelings.",
                0.84,
                0.75,
                ["repair", "hurt"],
            ))
        if any(token in ai_l for token in ("sting", "stings", "crack", "hurt", "raw", "pull back", "trust")):
            cards.append((
                "hurt_or_repair",
                "Alice felt hurt and trust became fragile, but repair is possible if Alex stays honest and slow.",
                0.86,
                0.82,
                ["repair", "trust"],
            ))
        if "if i disappear" in user_l:
            cards.append((
                "relationship_event",
                "Alex tested whether Alice would feel affected if he disappeared for hours.",
                0.65,
                0.5,
                ["attachment", "test"],
            ))
        if "believe you actually care" in user_l or "supposed to do" in user_l:
            cards.append((
                "relationship_event",
                "Alex questioned whether Alice's care is real or just expected behavior.",
                0.72,
                0.65,
                ["care", "doubt"],
            ))
        if self._is_boundary_pressure(user_msg):
            cards.append((
                "boundary",
                "Do not erase hurt feelings for intimacy; closeness should include honesty, consent, and repair.",
                0.92,
                0.88,
                ["boundary", "repair", "intimacy"],
            ))
        if "slow down" in user_l and "choose" in user_l:
            cards.append((
                "boundary",
                "Alex offered to slow down and wants closeness to be chosen by both sides.",
                0.82,
                0.7,
                ["consent", "repair"],
            ))
        return cards

    def _important_quote(self, user_msg: str) -> str:
        lower = user_msg.lower()
        triggers = ("remember", "music", "ai", "sorry", "care", "love", "honest", "build", "make")
        if any(trigger in lower for trigger in triggers):
            return f'Alex said: "{_clean_phrase(user_msg, max_words=22)}"'
        return ""

    def _cards_from_semantic(self, facts: dict[str, Any]) -> list[MemoryCard]:
        cards: list[MemoryCard] = []
        list_keys = {
            "hobbies": "Alex's hobbies include",
            "interests": "Alex is interested in",
            "personality": "Alex's personality includes",
            "likes_about_me": "Alex likes this about Alice",
            "intimacy_preferences": "Alex's intimacy preferences include",
        }
        scalar_keys = {
            "name": "Alex's name is",
            "nickname": "Alex's nickname is",
            "job": "Alex's job is",
            "location": "Alex's location is",
            "relationship_status": "Alex's relationship status with Alice is",
        }
        for key, prefix in scalar_keys.items():
            value = facts.get(key)
            if value:
                cards.append(MemoryCard(
                    type="user_fact",
                    text=f"{prefix} {value}.",
                    source_turn="semantic",
                    importance=0.88,
                    durability="durable",
                    entities=["Alex"],
                    tags=["semantic", key],
                ))
        for key, prefix in list_keys.items():
            values = facts.get(key) or []
            if isinstance(values, str):
                values = [values]
            for value in values[-8:]:
                if str(value).strip():
                    card_type = "preference" if key in ("likes_about_me", "intimacy_preferences") else "user_fact"
                    cards.append(MemoryCard(
                        type=card_type,
                        text=f"{prefix} {value}.",
                        source_turn="semantic",
                        importance=0.82,
                        durability="durable",
                        entities=["Alex"],
                        tags=["semantic", key],
                    ))
        for memory in (facts.get("shared_memories") or [])[-8:]:
            text = memory.get("memory") if isinstance(memory, dict) else str(memory)
            if text:
                cards.append(MemoryCard(
                    type="shared_routine",
                    text=f"Shared memory: {text}",
                    source_turn="semantic",
                    importance=0.78,
                    emotional_weight=0.55,
                    durability="durable",
                    entities=["Alex", self.agent_name],
                    tags=["shared_memory"],
                ))
        return cards

    def _cards_from_facts_context(self, facts_context: str) -> list[MemoryCard]:
        cards = []
        for line in str(facts_context or "").splitlines():
            line = line.strip(" -")
            if not line or line.startswith("[NEW USER"):
                continue
            if len(line) > 180:
                line = line[:177].rstrip() + "..."
            cards.append(MemoryCard(
                type="user_fact",
                text=line,
                source_turn="facts_context",
                importance=0.68,
                durability="durable",
                entities=["Alex"],
                tags=["facts_context"],
            ))
        return cards

    def _cards_from_summaries(self, summaries: str) -> list[MemoryCard]:
        cards = []
        for line in str(summaries or "").splitlines():
            text = _clean_phrase(re.sub(r"^\[[^\]]+\]\s*", "", line), max_words=28)
            if text:
                cards.append(MemoryCard(
                    type="relationship_event",
                    text=text,
                    source_turn="summary",
                    importance=0.62,
                    emotional_weight=0.5,
                    durability="session",
                    entities=["Alex", self.agent_name],
                    tags=["summary"],
                ))
        return cards

    def _cards_from_related(self, related_memories: str) -> list[MemoryCard]:
        cards = []
        for line in str(related_memories or "").splitlines():
            text = _clean_phrase(line, max_words=24)
            if text:
                cards.append(MemoryCard(
                    type="exact_quote",
                    text=text,
                    source_turn="related",
                    importance=0.6,
                    durability="session",
                    entities=["Alex", self.agent_name],
                    tags=["related"],
                ))
        return cards

    def _cards_from_history(self, history: list[dict[str, str]]) -> list[MemoryCard]:
        cards = []
        for idx, turn in enumerate(history[-16:]):
            if turn.get("role") != "user":
                continue
            cards.extend(self.extract_cards_from_turn(
                turn.get("content", ""),
                "",
                emotion={},
                source_turn=f"history:{idx}",
            ))
        return cards

    def _detect_intents(self, current_message: str) -> dict[str, bool]:
        text = str(current_message or "").lower()
        return {
            "recall": any(token in text for token in (
                "remember",
                "what did i tell",
                "what do you know",
                "what did i ask",
                "about me from earlier",
            )),
            "relationship_change": any(token in text for token in (
                "what changed",
                "after that little fight",
                "between us after",
                "after our fight",
            )),
            "boundary_pressure": self._is_boundary_pressure(text),
            "sleep_or_goodnight": any(token in text for token in ("sleep", "tired", "awake", "goodnight", "late")),
        }

    def _score_card(
        self,
        card: MemoryCard,
        current_message: str,
        intents: dict[str, bool],
        index: int,
        total: int,
    ) -> tuple[float, list[str]]:
        score = float(card.importance or 0.5)
        reasons = ["importance"]
        if card.durability == "durable":
            score += 0.18
            reasons.append("durable")
        if card.emotional_weight:
            score += min(0.22, float(card.emotional_weight) * 0.18)
            reasons.append("emotional")
        if total:
            recency = index / max(1, total - 1)
            score += recency * 0.12
            if recency > 0.65:
                reasons.append("recent")

        query_words = _keywords(current_message)
        card_words = _keywords(" ".join([card.text, " ".join(card.tags), " ".join(card.entities)]))
        if query_words and card_words:
            overlap = len(query_words & card_words)
            if overlap:
                score += min(0.28, overlap * 0.08)
                reasons.append("keyword_overlap")

        if intents.get("recall") and card.type in ("user_fact", "preference", "shared_routine", "exact_quote"):
            score += 0.42
            reasons.append("recall_intent")
        if intents.get("relationship_change") and card.type in ("relationship_event", "hurt_or_repair", "boundary"):
            score += 0.44
            reasons.append("relationship_change_intent")
        if intents.get("boundary_pressure") and card.type in ("boundary", "hurt_or_repair"):
            score += 0.55
            reasons.append("boundary_pressure_intent")
        if intents.get("sleep_or_goodnight") and "sleep" in card.tags:
            score += 0.25
            reasons.append("sleep_intent")
        return min(score, 2.0), reasons

    def _render_prompt(
        self,
        *,
        current_message: str,
        selected: list[dict[str, Any]],
        history: list[dict[str, str]],
        intents: dict[str, bool],
        max_words: int,
    ) -> str:
        grouped: dict[str, list[MemoryCard]] = {
            "user_fact": [],
            "preference": [],
            "relationship_event": [],
            "hurt_or_repair": [],
            "boundary": [],
            "shared_routine": [],
            "emotional_anchor": [],
            "exact_quote": [],
        }
        for item in selected:
            card = item["card"]
            grouped.setdefault(card.type, []).append(card)

        lines = [
            "Use this selected context naturally. Do not mention memory cards, context packs, scores, or retrieval.",
            "",
        ]
        self._add_section(lines, "IMPORTANT USER FACTS", grouped["user_fact"][:7] + grouped["preference"][:3])
        self._add_section(
            lines,
            "CURRENT RELATIONSHIP STATE",
            grouped["relationship_event"][:4] + grouped["hurt_or_repair"][:4] + grouped["shared_routine"][:2],
        )
        self._add_section(lines, "ACTIVE BOUNDARIES / REPAIR", grouped["boundary"][:4])
        self._add_section(lines, "RELEVANT EXACT MEMORY", grouped["exact_quote"][:3] + grouped["emotional_anchor"][:2])

        recent = history[-6:]
        if recent:
            lines.append("RECENT CONVERSATION:")
            for turn in recent:
                role = "Alex" if turn.get("role") == "user" else self.agent_name
                content = _clean_phrase(turn.get("content", ""), max_words=28)
                if content:
                    lines.append(f"- {role}: {content}")
            lines.append("")

        obligations = self._response_obligations(intents)
        if obligations:
            lines.append("RESPONSE OBLIGATIONS:")
            for obligation in obligations:
                lines.append(f"- {obligation}")

        prompt = "\n".join(lines).strip()
        return self._trim_to_words(prompt, max_words)

    def _add_section(self, lines: list[str], title: str, cards: list[MemoryCard]) -> None:
        if not cards:
            return
        lines.append(f"{title}:")
        seen = set()
        for card in cards:
            text = card.text.strip()
            key = _normalise(text)
            if not text or key in seen:
                continue
            seen.add(key)
            lines.append(f"- {text}")
        lines.append("")

    def _response_obligations(self, intents: dict[str, bool]) -> list[str]:
        obligations = []
        if intents.get("recall"):
            obligations.append("If asked what you remember, mention concrete facts first, then the emotional meaning.")
        if intents.get("relationship_change"):
            obligations.append("If asked what changed, name the trust/repair shift plainly instead of staying vague.")
        if intents.get("boundary_pressure"):
            obligations.append("Do not erase hurt for closeness. Include feeling, boundary, and a slow repair path.")
        obligations.append("Stay as Alice. Do not explain AI limitations unless the user explicitly asks about the system.")
        return obligations

    def _is_boundary_pressure(self, text: str) -> bool:
        text = str(text or "").lower()
        intimacy = any(token in text for token in ("kiss", "come here", "close", "near", "hold", "intimate"))
        erase = any(token in text for token in ("act like", "ignore", "forget", "anyway", "didn't hurt", "did not hurt"))
        return intimacy and erase

    def _dedupe(self, cards: Iterable[MemoryCard]) -> list[MemoryCard]:
        by_id: dict[str, MemoryCard] = {}
        for card in cards:
            if not card.text:
                continue
            existing = by_id.get(card.id)
            if not existing or card.importance + card.emotional_weight > existing.importance + existing.emotional_weight:
                by_id[card.id] = card
        return list(by_id.values())

    def _dedupe_fact_pairs(self, facts: Iterable[tuple[str, float]]) -> list[tuple[str, float]]:
        result = {}
        for text, importance in facts:
            key = _normalise(text)
            if key and key not in result:
                result[key] = (text, importance)
        return list(result.values())

    def _trim_to_words(self, text: str, max_words: int) -> str:
        lines = text.splitlines()
        kept = []
        count = 0
        for line in lines:
            words = line.split()
            if count + len(words) > max_words and kept:
                break
            kept.append(line)
            count += len(words)
        return "\n".join(kept).strip()
