"""Capability metadata for LLM adapters.

These structures are descriptive. They do not change the legacy `chat()`
contract, but they let routing, diagnostics, and benchmark reports understand
which controls a model/provider actually supports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal


ReasoningControlStyle = Literal["none", "openrouter_reasoning", "zai_thinking", "ollama_think"]
ApiStyle = Literal["openai_chat", "ollama_chat"]
MetadataSource = Literal["default", "settings", "discovered"]


@dataclass(frozen=True)
class ReasoningCapabilities:
    supports_hidden_reasoning: bool = False
    supports_disable_control: bool = False
    supports_exclude_control: bool = False
    control_style: ReasoningControlStyle = "none"


@dataclass(frozen=True)
class ModelCapabilities:
    provider: str
    model: str
    api_style: ApiStyle = "openai_chat"
    local: bool = False
    requires_api_key: bool = True
    context_tokens: int | None = None
    max_output_tokens: int | None = None
    supports_streaming: bool = False
    supports_vision: bool = False
    supports_tools: bool = False
    supports_json_mode: bool = False
    supported_params: frozenset[str] = frozenset()
    reasoning: ReasoningCapabilities = field(default_factory=ReasoningCapabilities)
    metadata_source: MetadataSource = "default"

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider": self.provider,
            "model": self.model,
            "api_style": self.api_style,
            "local": self.local,
            "requires_api_key": self.requires_api_key,
            "context_tokens": self.context_tokens,
            "max_output_tokens": self.max_output_tokens,
            "supports_streaming": self.supports_streaming,
            "supports_vision": self.supports_vision,
            "supports_tools": self.supports_tools,
            "supports_json_mode": self.supports_json_mode,
            "supported_params": sorted(self.supported_params),
            "reasoning": {
                "supports_hidden_reasoning": self.reasoning.supports_hidden_reasoning,
                "supports_disable_control": self.reasoning.supports_disable_control,
                "supports_exclude_control": self.reasoning.supports_exclude_control,
                "control_style": self.reasoning.control_style,
            },
            "metadata_source": self.metadata_source,
        }


@dataclass
class ChatResult:
    content: str | None
    provider: str
    model: str
    capabilities: ModelCapabilities
    usage: dict[str, Any] = field(default_factory=dict)
    finish_reason: str | None = None
    raw_had_reasoning: bool = False
    applied_controls: dict[str, Any] = field(default_factory=dict)
