"""Provider construction helpers for LLM adapters."""

from __future__ import annotations

import os
from typing import Any, Callable, Optional

from .base import BaseLLM
from .ollama import OllamaClient
from .openai_compatible import OpenAICompatibleClient
from .openrouter import OpenRouterClient
from .zai import ZAIClient


SettingsGetter = Callable[[str, Any], Any]


OPENAI_COMPATIBLE_PRESETS: dict[str, dict[str, Any]] = {
    "openai-compatible": {
        "prefix": "OPENAI_COMPATIBLE",
        "base_url": "http://127.0.0.1:8000/v1",
        "model": "local-model",
        "local": False,
        "requires_api_key": False,
    },
    "lmstudio": {
        "prefix": "LMSTUDIO",
        "base_url": "http://127.0.0.1:1234/v1",
        "model": "local-model",
        "local": True,
        "requires_api_key": False,
    },
    "llamacpp": {
        "prefix": "LLAMACPP",
        "base_url": "http://127.0.0.1:8080/v1",
        "model": "local-model",
        "local": True,
        "requires_api_key": False,
    },
    "vllm": {
        "prefix": "VLLM",
        "base_url": "http://127.0.0.1:8000/v1",
        "model": "local-model",
        "local": False,
        "requires_api_key": False,
    },
    "mlx": {
        "prefix": "MLX",
        "base_url": "http://127.0.0.1:8080/v1",
        "model": "local-model",
        "local": True,
        "requires_api_key": False,
    },
}


ALIASES = {
    "local": "ollama",
    "openai_compatible": "openai-compatible",
    "openai-compatible": "openai-compatible",
    "openai compatible": "openai-compatible",
    "oai-compatible": "openai-compatible",
    "openai": "openai-compatible",
    "lm-studio": "lmstudio",
    "lmstudio": "lmstudio",
    "llama.cpp": "llamacpp",
    "llama-cpp": "llamacpp",
    "llamacpp": "llamacpp",
    "mlx-lm": "mlx",
    "mlx_lm": "mlx",
    "mlx": "mlx",
}


def canonical_provider_name(name: str | None) -> str:
    normalized = str(name or "").strip().lower().replace("_", "-")
    return ALIASES.get(normalized, normalized)


def _default_settings_getter() -> SettingsGetter | None:
    try:
        from core.settings import get as settings_get

        return settings_get
    except Exception:
        return None


def _setting(settings_getter: SettingsGetter | None, key: str, default: Any = None) -> Any:
    if settings_getter is None:
        settings_getter = _default_settings_getter()
    env_value = os.environ.get(key)
    if env_value not in (None, ""):
        return env_value
    if settings_getter:
        try:
            value = settings_getter(key, default)
            if value not in (None, ""):
                return value
        except TypeError:
            value = settings_getter(key)
            if value not in (None, ""):
                return value
        except Exception:
            pass
    return default


def _bool_setting(settings_getter: SettingsGetter | None, key: str, default: bool) -> bool:
    value = _setting(settings_getter, key, default)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("1", "true", "yes", "on", "enabled"):
            return True
        if lowered in ("0", "false", "no", "off", "disabled"):
            return False
    return default


def _task_model(
    settings_getter: SettingsGetter | None,
    prefix: str,
    task: str,
    default: str,
) -> str:
    suffix = {
        "fast": "FAST",
        "thinking": "THINKING",
        "main": "MAIN",
    }.get(task, "MAIN")
    return (
        _setting(settings_getter, f"{prefix}_MODEL_{suffix}")
        or _setting(settings_getter, f"{prefix}_MODEL")
        or default
    )


def create_llm_client(
    provider_name: str,
    *,
    task: str = "main",
    settings_getter: SettingsGetter | None = None,
) -> Optional[BaseLLM]:
    """Create a provider client from canonical settings/env names."""
    name = canonical_provider_name(provider_name)

    if name == "zai":
        api_key = _setting(settings_getter, "ZAI_API_KEY", "")
        model = _task_model(settings_getter, "ZAI", task, "glm-4.6v")
        return ZAIClient(api_key, model) if api_key else None

    if name == "openrouter":
        api_key = _setting(settings_getter, "OPENROUTER_API_KEY", "")
        model = _task_model(settings_getter, "OPENROUTER", task, "openai/gpt-4.1-mini")
        return OpenRouterClient(api_key, model) if api_key else None

    if name == "ollama":
        url = _setting(settings_getter, "OLLAMA_URL", "http://172.17.0.1:11434")
        model = _task_model(settings_getter, "OLLAMA", task, "qwen3:4b")
        return OllamaClient("", model, url)

    preset = OPENAI_COMPATIBLE_PRESETS.get(name)
    if preset:
        prefix = preset["prefix"]
        api_key = _setting(settings_getter, f"{prefix}_API_KEY", "")
        base_url = _setting(settings_getter, f"{prefix}_BASE_URL", preset["base_url"])
        model = _task_model(settings_getter, prefix, task, preset["model"])
        local = _bool_setting(settings_getter, f"{prefix}_LOCAL", bool(preset["local"]))
        requires_api_key = _bool_setting(
            settings_getter,
            f"{prefix}_REQUIRES_API_KEY",
            bool(preset["requires_api_key"]),
        )
        context_tokens = _setting(settings_getter, f"{prefix}_CONTEXT_TOKENS")
        try:
            context_tokens = int(context_tokens) if context_tokens not in (None, "") else None
        except (TypeError, ValueError):
            context_tokens = None
        if requires_api_key and not api_key:
            return None
        return OpenAICompatibleClient(
            api_key=api_key,
            model=model,
            base_url=base_url,
            provider_name=name,
            local=local,
            requires_api_key=requires_api_key,
            context_tokens=context_tokens,
        )

    return None
