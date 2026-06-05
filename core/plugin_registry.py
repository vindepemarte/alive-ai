"""
Core: Plugin Registry
Typed declarations for optional Alive-AI organs, skills, and connectors.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, replace
import importlib
from typing import Any, Dict, Iterable, List, Optional


_SENSITIVE_MARKERS = ("token", "secret", "key", "password", "authorization", "bearer")


def _redact_error(text: str) -> str:
    """Keep registry diagnostics useful without leaking credentials."""
    if not text:
        return ""
    cleaned = str(text).replace("\n", " ")[:240]
    lowered = cleaned.lower()
    if any(marker in lowered for marker in _SENSITIVE_MARKERS):
        return "[redacted]"
    return cleaned


@dataclass
class PluginDeclaration:
    """A plugin/module declaration that can be probed without instantiation."""

    name: str
    category: str
    import_path: str
    description: str = ""
    events: List[str] = field(default_factory=list)
    prompt_sections: List[str] = field(default_factory=list)
    state_keys: List[str] = field(default_factory=list)
    permissions: List[str] = field(default_factory=list)
    required: bool = False
    enabled: bool = True
    available: bool = False
    error: str = ""

    def probe(self) -> "PluginDeclaration":
        if not self.enabled:
            self.available = False
            self.error = "disabled"
            return self
        try:
            importlib.import_module(self.import_path)
            self.available = True
            self.error = ""
        except Exception as exc:
            self.available = False
            self.error = _redact_error(f"{exc.__class__.__name__}: {exc}")
        return self

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        if data.get("error"):
            data["error"] = _redact_error(data["error"])
        return data


class PluginRegistry:
    """In-memory catalog of runtime-capable modules and their status."""

    def __init__(self):
        self._plugins: Dict[str, PluginDeclaration] = {}

    def register(self, declaration: PluginDeclaration, *, replace_existing: bool = True) -> PluginDeclaration:
        if declaration.name in self._plugins and not replace_existing:
            return self._plugins[declaration.name]
        self._plugins[declaration.name] = declaration
        return declaration

    def register_many(self, declarations: Iterable[PluginDeclaration], *, replace_existing: bool = True) -> None:
        for declaration in declarations:
            self.register(declaration, replace_existing=replace_existing)

    def get(self, name: str) -> Optional[PluginDeclaration]:
        return self._plugins.get(name)

    def update_availability(self, name: str, available: bool, error: str = "") -> None:
        plugin = self._plugins.get(name)
        if not plugin:
            return
        plugin.available = bool(available)
        plugin.error = "" if available else _redact_error(error)

    def probe(self, name: str) -> Optional[PluginDeclaration]:
        plugin = self._plugins.get(name)
        if plugin:
            plugin.probe()
        return plugin

    def probe_all(self) -> None:
        for plugin in self._plugins.values():
            plugin.probe()

    def snapshot(self) -> Dict[str, Any]:
        plugins = sorted((plugin.to_dict() for plugin in self._plugins.values()), key=lambda row: row["name"])
        categories: Dict[str, Dict[str, int]] = {}
        for plugin in plugins:
            category = plugin.get("category") or "uncategorized"
            bucket = categories.setdefault(category, {"total": 0, "available": 0, "enabled": 0})
            bucket["total"] += 1
            bucket["available"] += 1 if plugin.get("available") else 0
            bucket["enabled"] += 1 if plugin.get("enabled") else 0

        return {
            "plugin_count": len(plugins),
            "available_count": sum(1 for plugin in plugins if plugin.get("available")),
            "enabled_count": sum(1 for plugin in plugins if plugin.get("enabled")),
            "categories": categories,
            "plugins": plugins,
        }


_BUILTIN_PLUGINS = (
    PluginDeclaration(
        name="interoception",
        category="body",
        import_path="heart.interoception",
        description="Internal body-state sensing and bodily prompt context.",
        events=["timer_tick", "message_received"],
        prompt_sections=["interoception"],
        state_keys=["bodily_state", "current_mood"],
    ),
    PluginDeclaration(
        name="circadian",
        category="body",
        import_path="heart.circadian",
        description="Sleep pressure, time-of-day shifts, and circadian prompt context.",
        events=["message_received", "timer_tick"],
        prompt_sections=["circadian"],
        state_keys=["sleep_pressure", "melatonin", "is_sleeping"],
    ),
    PluginDeclaration(
        name="behavioral_pressure",
        category="body",
        import_path="core.behavioral_pressure",
        description="Emotion and hormone to action-tendency compiler.",
        events=["message_received"],
        prompt_sections=["behavioral_pressure"],
        state_keys=["dominant", "urgency", "approach_withdraw", "drives"],
        required=True,
    ),
    PluginDeclaration(
        name="attachment",
        category="relationship",
        import_path="heart.attachment",
        description="Attachment pattern and relationship-security context.",
        events=["message_received"],
        prompt_sections=["attachment"],
        state_keys=["style", "security"],
    ),
    PluginDeclaration(
        name="afterglow",
        category="relationship",
        import_path="heart.afterglow",
        description="Persistent emotional residue from intense moments.",
        events=["message_received"],
        prompt_sections=["afterglow"],
        state_keys=["active_afterglows"],
    ),
    PluginDeclaration(
        name="phantom_somatic",
        category="relationship",
        import_path="heart.phantom_somatic",
        description="Lasting body memories from emotionally intense moments.",
        events=["message_received"],
        prompt_sections=["phantom_somatic"],
        state_keys=["active_phantoms"],
    ),
    PluginDeclaration(
        name="inconsistency",
        category="relationship",
        import_path="heart.inconsistency",
        description="Approach/avoidance tension, blind spots, and authentic inconsistency.",
        events=["message_received"],
        prompt_sections=["inconsistency"],
        state_keys=["active_conflicts", "behavioral_tendency"],
    ),
    PluginDeclaration(
        name="mood_shifts",
        category="relationship",
        import_path="heart.mood_shifts",
        description="Mid-conversation emotional transition detection.",
        events=["message_received"],
        prompt_sections=["mood_shifts"],
        state_keys=["recent_shifts"],
    ),
    PluginDeclaration(
        name="bid_detector",
        category="conversation",
        import_path="brain.bid_detector",
        description="Emotional bid detection and response awareness.",
        events=["message_received"],
        prompt_sections=["bid_awareness"],
        state_keys=["recent_bids"],
    ),
    PluginDeclaration(
        name="conversation_flow",
        category="conversation",
        import_path="brain.conversation_flow",
        description="Conversation-health tracking and revival hints.",
        events=["message_received"],
        state_keys=["conversation_health"],
    ),
    PluginDeclaration(
        name="curiosity",
        category="conversation",
        import_path="brain.curiosity",
        description="Knowledge-gap and profile-curiosity drive.",
        events=["message_received"],
        prompt_sections=["curiosity"],
        state_keys=["open_questions"],
    ),
    PluginDeclaration(
        name="linguistic",
        category="conversation",
        import_path="brain.linguistic",
        description="User speech-pattern absorption and mirroring context.",
        events=["message_received"],
        prompt_sections=["linguistic_profile"],
        state_keys=["style_profile"],
    ),
    PluginDeclaration(
        name="almost_said",
        category="conversation",
        import_path="brain.almost_said",
        description="Subvocalized almost-said thoughts.",
        events=["message_received"],
        prompt_sections=["almost_said"],
        state_keys=["recent_almost_said"],
    ),
    PluginDeclaration(
        name="default_mode",
        category="inner_life",
        import_path="brain.default_mode",
        description="Background idle thoughts and default-mode processing.",
        events=["timer_tick", "subconscious_impulse"],
        prompt_sections=["idle_thoughts"],
        state_keys=["recent_thoughts", "pending_initiations"],
    ),
    PluginDeclaration(
        name="dreams",
        category="inner_life",
        import_path="brain.dreams",
        description="Dream and sleep-time recombination context.",
        events=["timer_tick"],
        prompt_sections=["dreams"],
        state_keys=["recent_dreams"],
    ),
    PluginDeclaration(
        name="narrative",
        category="memory",
        import_path="brain.narrative",
        description="Relationship story arc and phase awareness.",
        events=["message_received", "memory_save"],
        prompt_sections=["narrative"],
        state_keys=["phase", "summary"],
    ),
    PluginDeclaration(
        name="emotional_memory",
        category="memory",
        import_path="brain.emotional_memory",
        description="Emotionally weighted memory encoding and retrieval.",
        events=["message_received", "memory_save"],
        prompt_sections=["emotional_memory"],
        state_keys=["total_memories", "average_weight"],
    ),
    PluginDeclaration(
        name="memory_layers",
        category="memory",
        import_path="brain.memory.layers",
        description="Layered memory compiler for episodic, semantic, emotional, and narrative context.",
        events=["message_received", "memory_save"],
        prompt_sections=["memory_layers"],
        state_keys=["layers"],
        required=True,
    ),
    PluginDeclaration(
        name="global_activity",
        category="memory",
        import_path="brain.global_activity",
        description="Owner transparency about activity across users.",
        events=["message_received"],
        state_keys=["last_interaction"],
    ),
    PluginDeclaration(
        name="skills_registry",
        category="skills",
        import_path="core.skills_registry",
        description="Prompt-visible capabilities registry.",
        events=["message_received"],
        prompt_sections=["skills"],
        state_keys=["skill_count"],
    ),
    PluginDeclaration(
        name="message_scheduler",
        category="skills",
        import_path="skills.message_scheduler",
        description="Scheduled local messages.",
        events=["timer_tick"],
        state_keys=["scheduled_messages"],
    ),
    PluginDeclaration(
        name="memory_callbacks",
        category="skills",
        import_path="skills.memory_callbacks",
        description="Conversation memory callbacks and reminders.",
        events=["message_received"],
        state_keys=["callbacks"],
    ),
    PluginDeclaration(
        name="anticipation_engine",
        category="skills",
        import_path="skills.anticipation_engine",
        description="Anticipation and content tease engine.",
        events=["message_received"],
        state_keys=["anticipation"],
    ),
    PluginDeclaration(
        name="relationship_milestones",
        category="skills",
        import_path="skills.relationship_milestones",
        description="Relationship milestones and progression tracking.",
        events=["message_received"],
        state_keys=["milestones"],
    ),
    PluginDeclaration(
        name="content_unlocks",
        category="skills",
        import_path="skills.content_unlocks",
        description="Progressive content access rules.",
        events=["message_received"],
        state_keys=["unlocks"],
    ),
    PluginDeclaration(
        name="intimacy_layers",
        category="skills",
        import_path="skills.intimacy_layers",
        description="Natural intimacy progression tracking.",
        events=["message_received"],
        state_keys=["current_layer"],
    ),
    PluginDeclaration(
        name="exclusive_moments",
        category="skills",
        import_path="skills.exclusive_moments",
        description="Special time-limited relationship moments.",
        events=["message_received"],
        state_keys=["active_moments"],
    ),
    PluginDeclaration(
        name="mcp",
        category="connectors",
        import_path="core.mcp",
        description="Sandboxed Model Context Protocol tool connector runtime.",
        events=["tool_proposed", "tool_executed"],
        state_keys=["servers", "pending_count"],
        permissions=["mcp:read_status"],
    ),
)

_registry: Optional[PluginRegistry] = None


def builtin_plugin_declarations() -> List[PluginDeclaration]:
    return [replace(plugin) for plugin in _BUILTIN_PLUGINS]


def get_plugin_registry() -> PluginRegistry:
    global _registry
    if _registry is None:
        _registry = PluginRegistry()
    return _registry


def register_builtin_plugins(registry: Optional[PluginRegistry] = None, *, probe: bool = False) -> PluginRegistry:
    registry = registry or get_plugin_registry()
    registry.register_many(builtin_plugin_declarations(), replace_existing=False)
    if probe:
        registry.probe_all()
    return registry


def get_plugin_status(*, probe: bool = False) -> Dict[str, Any]:
    registry = register_builtin_plugins(probe=probe)
    return registry.snapshot()
