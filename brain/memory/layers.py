"""Layered biological memory snapshot for prompt context.

This module does not create a second memory system. It assembles the memory
stores Alive-AI already has into compact biological layers so small local
models get a stable signal about what is recent, factual, emotionally
important, autobiographical, dreamlike, procedural, and shadow/defensive.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


_DISCOVER_RE = re.compile(r"\[DISCOVER:[^\]]+\]\s*")
_SPACE_RE = re.compile(r"\s+")


@dataclass
class MemoryLayer:
    name: str
    purpose: str
    items: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    count: int = 0
    salience: float = 0.0
    freshness: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["salience"] = round(float(self.salience), 3)
        return data


@dataclass
class LayeredMemorySnapshot:
    user_id: str
    generated_at: str
    layers: list[MemoryLayer]

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": self.user_id,
            "generated_at": self.generated_at,
            "layer_count": len(self.layers),
            "layers": [layer.to_dict() for layer in self.layers],
        }

    def compact_text(self, *, max_items_per_layer: int = 2, max_words: int = 220) -> str:
        """Render a compact prompt block for the LLM."""
        lines: list[str] = []
        for layer in self.layers:
            items = [item for item in layer.items if item][:max_items_per_layer]
            if not items:
                continue
            label = layer.name.replace("_", " ").title()
            lines.append(f"{label}: " + "; ".join(items))

        if not lines:
            return ""

        words = ("MEMORY LAYERS:\n" + "\n".join(f"- {line}" for line in lines)).split()
        if len(words) <= max_words:
            return "MEMORY LAYERS:\n" + "\n".join(f"- {line}" for line in lines)
        return " ".join(words[:max_words]).rstrip(" ,;") + "..."


class MemoryLayerRegistry:
    """Assemble existing memory stores into prompt-ready layers."""

    def __init__(
        self,
        data_path: Path,
        *,
        user_id: str,
        working: Any = None,
        episodic: Any = None,
        semantic: Any = None,
        context_compiler: Any = None,
        agent_name: str = "AI",
    ):
        self.data_path = Path(data_path)
        self.global_data_path = self._resolve_global_data_path(self.data_path)
        self.user_id = str(user_id or "default")
        self.working = working
        self.episodic = episodic
        self.semantic = semantic
        self.context_compiler = context_compiler
        self.agent_name = str(agent_name or "AI")

    def build_snapshot(self, current_message: str = "", *, max_items_per_layer: int = 3) -> LayeredMemorySnapshot:
        layers: list[MemoryLayer] = []
        collectors = (
            self._working_layer,
            self._episodic_layer,
            self._semantic_layer,
            self._emotional_layer,
            self._procedural_layer,
            self._autobiographical_layer,
            self._dream_layer,
            self._shadow_layer,
        )
        for collect in collectors:
            try:
                layer = collect(current_message=current_message, max_items=max_items_per_layer)
            except Exception as exc:
                layer = MemoryLayer(
                    name=collect.__name__.replace("_layer", "").lstrip("_"),
                    purpose="Unavailable layer",
                    items=[f"Layer read failed: {exc.__class__.__name__}"],
                    count=0,
                    salience=0.0,
                )
            if layer and layer.items:
                layers.append(layer)

        layers.sort(key=lambda layer: (layer.salience, layer.count), reverse=True)
        return LayeredMemorySnapshot(
            user_id=self.user_id,
            generated_at=datetime.now().isoformat(),
            layers=layers,
        )

    def _working_layer(self, *, current_message: str, max_items: int) -> MemoryLayer | None:
        history = []
        if self.working and hasattr(self.working, "get_history"):
            history = list(self.working.get_history() or [])
        items = []
        for turn in history[-max_items:]:
            role = "User" if turn.get("role") == "user" else self.agent_name
            snippet = _snippet(turn.get("content", ""), max_words=20)
            if snippet:
                items.append(f"{role}: {snippet}")
        return MemoryLayer(
            name="working",
            purpose="Immediate short-term conversation state",
            items=items,
            sources=["working_memory"],
            count=len(history),
            salience=0.76 if items else 0.0,
        )

    def _episodic_layer(self, *, current_message: str, max_items: int) -> MemoryLayer | None:
        entries = []
        if self.episodic and hasattr(self.episodic, "load_recent"):
            entries = list(self.episodic.load_recent(limit=max(max_items, 3)) or [])
        items = []
        for entry in entries[-max_items:]:
            user = _snippet(entry.get("user", ""), max_words=12)
            ai = _snippet(entry.get("ai", ""), max_words=12)
            if user and ai:
                items.append(f"Recent turn: he said '{user}', I answered '{ai}'")
            elif ai:
                items.append(f"Recent proactive message: {ai}")
        return MemoryLayer(
            name="episodic",
            purpose="Persisted conversation events across restarts",
            items=items,
            sources=["conversations/*.jsonl"],
            count=len(entries),
            salience=0.66 if items else 0.0,
        )

    def _semantic_layer(self, *, current_message: str, max_items: int) -> MemoryLayer | None:
        facts = getattr(self.semantic, "facts", {}) or {}
        items = []
        profile_parts = []
        for key in ("name", "nickname", "gender", "age", "location", "job", "relationship_status"):
            value = facts.get(key)
            if value:
                profile_parts.append(f"{key.replace('_', ' ')}: {_snippet(value, max_words=10)}")
        for key in ("hobbies", "interests", "personality"):
            values = [str(v).strip() for v in facts.get(key, []) if str(v).strip()]
            if values:
                profile_parts.append(f"{key}: {', '.join(values[:4])}")
        if profile_parts:
            items.append("; ".join(profile_parts))

        for memory in (facts.get("shared_memories") or [])[-max_items:]:
            text = _snippet((memory if isinstance(memory, dict) else {}).get("memory", memory), max_words=18)
            if text:
                items.append(f"Shared memory: {text}")

        mentions = facts.get("mentions") or {}
        for key, data in sorted(
            mentions.items(),
            key=lambda item: (item[1] if isinstance(item[1], dict) else {}).get("timestamp", ""),
            reverse=True,
        )[:max_items]:
            value = _snippet((data if isinstance(data, dict) else {}).get("value", data), max_words=16)
            if value:
                items.append(f"Recently mentioned {key}: {value}")

        count = len([item for item in profile_parts if item]) + len(mentions) + len(facts.get("shared_memories") or [])
        return MemoryLayer(
            name="semantic",
            purpose="Stable facts, profile, preferences, and explicit shared memories",
            items=_dedupe(items)[: max_items + 2],
            sources=["facts.json"],
            count=count,
            salience=0.9 if items else 0.0,
        )

    def _emotional_layer(self, *, current_message: str, max_items: int) -> MemoryLayer | None:
        items: list[str] = []
        sources: list[str] = []

        for memory in self._read_emotional_memories(limit=max_items):
            content = _snippet(memory.get("content", ""), max_words=18)
            emotions = ", ".join([str(e) for e in memory.get("emotions_felt", [])[:3] if e])
            weight = memory.get("emotional_weight")
            if content:
                suffix = f" [felt: {emotions}]" if emotions else ""
                if isinstance(weight, (int, float)):
                    suffix += f" [weight {weight:.2f}]"
                items.append(f"High-emotion memory: {content}{suffix}")
        if items:
            sources.append("emotional_memories")

        if self.context_compiler and hasattr(self.context_compiler, "load_cards"):
            cards = list(self.context_compiler.load_cards(limit=120) or [])
            cards.sort(key=lambda card: (getattr(card, "emotional_weight", 0.0), getattr(card, "importance", 0.0)), reverse=True)
            for card in cards[:max_items]:
                text = _snippet(getattr(card, "text", ""), max_words=18)
                card_type = getattr(card, "type", "memory")
                if text:
                    items.append(f"{card_type}: {text}")
            if cards:
                sources.append("context_cards.jsonl")

        return MemoryLayer(
            name="emotional",
            purpose="High-salience moments and affect-weighted memories",
            items=_dedupe(items)[: max_items + 1],
            sources=sources,
            count=len(items),
            salience=0.86 if items else 0.0,
        )

    def _procedural_layer(self, *, current_message: str, max_items: int) -> MemoryLayer | None:
        paths = [
            self.data_path / "procedural_memory.json",
            self.global_data_path / "procedural_memory.json",
        ]
        entries = []
        for path in paths:
            data = _read_json(path)
            if isinstance(data, dict):
                entries.extend(data.get("routines") or data.get("procedures") or [])
            elif isinstance(data, list):
                entries.extend(data)
        items = []
        for entry in entries[:max_items]:
            if isinstance(entry, dict):
                name = entry.get("name") or entry.get("title") or "routine"
                detail = entry.get("description") or entry.get("steps") or entry.get("summary") or ""
                items.append(f"{_snippet(name, max_words=8)}: {_snippet(detail, max_words=18)}")
            else:
                items.append(_snippet(entry, max_words=20))
        return MemoryLayer(
            name="procedural",
            purpose="Learned routines, habits, and repeatable behaviors",
            items=[item for item in items if item],
            sources=["procedural_memory.json"],
            count=len(entries),
            salience=0.48 if items else 0.0,
        )

    def _autobiographical_layer(self, *, current_message: str, max_items: int) -> MemoryLayer | None:
        global_story = _read_json(self.global_data_path / "autobiography.json")
        relationship_story = _read_json(self.data_path / "relationship_autobiography.json")
        items = []
        if isinstance(global_story, dict):
            story = _snippet(global_story.get("self_story", ""), max_words=24)
            if story:
                items.append(f"Self-story: {story}")
            prefs = [str(p).strip() for p in global_story.get("emerging_preferences", []) if str(p).strip()]
            if prefs:
                items.append("Emerging self-preferences: " + "; ".join(prefs[:max_items]))
        if isinstance(relationship_story, dict):
            rel = _snippet(relationship_story.get("relationship_story", ""), max_words=24)
            if rel:
                items.append(f"Relationship story: {rel}")
            loops = [_snippet(loop, max_words=16) for loop in relationship_story.get("open_loops", [])[-max_items:]]
            if loops:
                items.append("Open loops: " + "; ".join([loop for loop in loops if loop]))
            moments = relationship_story.get("recent_meaningful_turns", [])[-max_items:]
            for moment in moments:
                user = _snippet((moment or {}).get("user", ""), max_words=12)
                mood = (moment or {}).get("mood")
                if user:
                    items.append(f"Meaningful recent turn ({mood or 'unknown mood'}): {user}")
        return MemoryLayer(
            name="autobiographical",
            purpose="Self-story and relationship narrative",
            items=_dedupe(items)[: max_items + 2],
            sources=["autobiography.json", "relationship_autobiography.json"],
            count=len(items),
            salience=0.7 if items else 0.0,
        )

    def _dream_layer(self, *, current_message: str, max_items: int) -> MemoryLayer | None:
        data = _read_json(self.global_data_path / "dreams.json")
        dreams = data.get("dreams", []) if isinstance(data, dict) else []
        items = []
        for dream in dreams[-max_items:]:
            text = _snippet((dream or {}).get("text") or (dream or {}).get("content", ""), max_words=22)
            emotions = ", ".join([str(e) for e in (dream or {}).get("emotions", [])[:2] if e])
            if text:
                items.append(f"Recent dream: {text}" + (f" [emotions: {emotions}]" if emotions else ""))
        return MemoryLayer(
            name="dream",
            purpose="Sleep-time symbolic recombination of memory and emotion",
            items=items,
            sources=["dreams.json"],
            count=len(dreams),
            salience=0.42 if items else 0.0,
        )

    def _shadow_layer(self, *, current_message: str, max_items: int) -> MemoryLayer | None:
        items = []
        unconscious = _read_json(self.global_data_path / "unconscious_state.json")
        if isinstance(unconscious, dict):
            conflicts = unconscious.get("unresolved_conflicts", [])[-max_items:]
            for conflict in conflicts:
                desc = _snippet((conflict or {}).get("description", ""), max_words=18)
                tension = (conflict or {}).get("tension_level")
                if desc:
                    suffix = f" [tension {float(tension):.2f}]" if isinstance(tension, (int, float)) else ""
                    items.append(f"Unresolved conflict: {desc}{suffix}")
            associations = unconscious.get("implicit_associations", [])[-max_items:]
            for assoc in associations:
                trigger = _snippet((assoc or {}).get("trigger_pattern", ""), max_words=8)
                response = _snippet((assoc or {}).get("emotional_response", ""), max_words=10)
                if trigger and response:
                    items.append(f"Implicit association: {trigger} -> {response}")

        scars = _read_json(self.global_data_path / "emotional_scars.json")
        if isinstance(scars, dict):
            for scar in (scars.get("scars") or [])[-max_items:]:
                desc = _snippet((scar or {}).get("description", ""), max_words=16)
                behaviors = ", ".join([str(b) for b in (scar or {}).get("protective_behaviors", [])[:2] if b])
                if desc:
                    items.append(f"Protective scar: {desc}" + (f" [protects by: {behaviors}]" if behaviors else ""))

        return MemoryLayer(
            name="shadow",
            purpose="Defensive patterns, unresolved tensions, and protective vulnerabilities",
            items=_dedupe(items)[: max_items + 2],
            sources=["unconscious_state.json", "emotional_scars.json"],
            count=len(items),
            salience=0.72 if items else 0.0,
        )

    def _read_emotional_memories(self, *, limit: int) -> list[dict[str, Any]]:
        path = self.global_data_path / "emotional_memories" / f"{self.user_id}_memories.json"
        data = _read_json(path)
        memories: list[dict[str, Any]] = []
        if isinstance(data, dict):
            if isinstance(data.get("memories"), dict):
                memories = list(data["memories"].values())
            elif isinstance(data.get("memories"), list):
                memories = data["memories"]
            elif isinstance(data.get("_memories"), dict):
                memories = list(data["_memories"].values())
        elif isinstance(data, list):
            memories = data
        memories = [m for m in memories if isinstance(m, dict)]
        memories.sort(
            key=lambda item: (
                _float(item.get("emotional_weight")),
                str(item.get("timestamp") or ""),
            ),
            reverse=True,
        )
        return memories[:limit]

    @staticmethod
    def _resolve_global_data_path(data_path: Path) -> Path:
        path = Path(data_path)
        if path.parent.name == "users":
            return path.parent.parent
        return path


def _read_json(path: Path) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text())
    except Exception:
        return None
    return None


def _snippet(value: Any, *, max_words: int = 18) -> str:
    text = _DISCOVER_RE.sub("", str(value or ""))
    text = _SPACE_RE.sub(" ", text).strip(" \t\r\n.,;:")
    if not text:
        return ""
    words = text.split()
    return " ".join(words[:max_words])


def _float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _dedupe(items: Iterable[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        cleaned = _snippet(item, max_words=40)
        key = cleaned.lower()
        if cleaned and key not in seen:
            seen.add(key)
            result.append(cleaned)
    return result
