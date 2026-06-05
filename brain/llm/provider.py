"""
Brain: LLM - Provider Factory
Creates the appropriate LLM client based on configuration.
Supports both legacy single-provider mode and new unified fallback mode.
"""

import os
from typing import Optional, Tuple
from .base import BaseLLM
from .factory import canonical_provider_name, create_llm_client
from .unified import UnifiedLLM, get_unified_llm
from .fallback_router import FallbackRouter, get_fallback_router


def get_provider_config(task: str = "main") -> Tuple[str, str, str]:
    """Get provider and model for a specific task

    Tasks:
    - main: Main conversation model
    - thinking: Deep reasoning, complex decisions
    - fast: Quick responses, impulses, subconscious

    Returns:
        Tuple of (provider_name, api_key, model_name)
    """
    # Try to get from settings.json first
    try:
        from core.settings import get as settings_get

        # Check if fallback mode is enabled
        llm_fallback = settings_get("LLM_FALLBACK", {})
        if llm_fallback.get("ENABLED", False):
            # Use unified mode - get config from settings
            provider = "unified"
            api_key = ""  # Not used in unified mode
            model = ""    # Not used in unified mode
            return provider, api_key, model

        # Legacy mode - use settings.json
        provider = canonical_provider_name(settings_get("LLM_PROVIDER", "zai"))

        if provider == "openrouter":
            api_key = settings_get("OPENROUTER_API_KEY", "") or os.environ.get("OPENROUTER_API_KEY", "")
            if task == "fast":
                model = settings_get("OPENROUTER_MODEL_FAST", "openai/gpt-4o-mini")
            elif task == "thinking":
                model = settings_get("OPENROUTER_MODEL_THINKING", "anthropic/claude-3.5-sonnet")
            else:
                model = settings_get("OPENROUTER_MODEL_MAIN", "anthropic/claude-3.5-sonnet")
        elif provider == "zai":
            # Default to ZAI
            api_key = settings_get("ZAI_API_KEY", "") or os.environ.get("ZAI_API_KEY", "")
            if task == "fast":
                model = settings_get("ZAI_MODEL_FAST", "glm-4-flash")
            elif task == "thinking":
                model = settings_get("ZAI_MODEL_THINKING", "glm-4.6v")
            else:
                model = settings_get("ZAI_MODEL_MAIN", "glm-4.6v")
        else:
            api_key = ""
            model = (
                settings_get(f"{provider.upper().replace('-', '_')}_MODEL_MAIN", "")
                or settings_get(f"{provider.upper().replace('-', '_')}_MODEL", "")
            )

        return provider, api_key, model

    except ImportError:
        # Fallback to environment variables
        pass

    # Environment variable fallback
    provider = canonical_provider_name(os.environ.get("LLM_PROVIDER", "zai"))

    if provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if task == "fast":
            model = os.environ.get("OPENROUTER_MODEL_FAST", "openai/gpt-4o-mini")
        elif task == "thinking":
            model = os.environ.get("OPENROUTER_MODEL_THINKING", "anthropic/claude-3.5-sonnet")
        else:
            model = os.environ.get("OPENROUTER_MODEL_MAIN", "anthropic/claude-3.5-sonnet")
    elif provider == "zai":
        # Default to ZAI
        api_key = os.environ.get("ZAI_API_KEY", "")
        if task == "fast":
            model = os.environ.get("ZAI_MODEL_FAST", "glm-4-flash")
        elif task == "thinking":
            model = os.environ.get("ZAI_MODEL_THINKING", "glm-4.6v")
        else:
            model = os.environ.get("ZAI_MODEL_MAIN", "glm-4.6v")
    else:
        prefix = provider.upper().replace("-", "_")
        api_key = os.environ.get(f"{prefix}_API_KEY", "")
        model = os.environ.get(f"{prefix}_MODEL_MAIN", os.environ.get(f"{prefix}_MODEL", ""))

    return provider, api_key, model


def get_llm_client(task: str = "main") -> Optional[BaseLLM]:
    """Get LLM client for a specific task

    Usage:
        # Main conversation
        llm = get_llm_client("main")

        # Quick impulse generation
        fast_llm = get_llm_client("fast")

        # Deep thinking
        think_llm = get_llm_client("thinking")
    """
    provider, api_key, model = get_provider_config(task)

    # Handle unified mode
    if provider == "unified":
        return get_unified_llm_client(task)

    client = create_llm_client(provider, task=task)
    if client:
        return client

    if provider in ("zai", "openrouter") and not api_key:
        print(f"[LLM] No API key for provider: {provider}")
    else:
        print(f"[LLM] Unsupported or incomplete provider config: {provider} {model or ''}".strip())
    return None


def get_fast_llm() -> Optional[BaseLLM]:
    """Get fast LLM for quick tasks (impulses, subconscious)"""
    return get_llm_client("fast")


def get_thinking_llm() -> Optional[BaseLLM]:
    """Get thinking LLM for complex reasoning"""
    return get_llm_client("thinking")


def get_main_llm() -> Optional[BaseLLM]:
    """Get main LLM for conversations"""
    return get_llm_client("main")


# ============================================================
# Unified LLM Support
# ============================================================

# Cache for task-specific unified clients
_unified_clients: dict[str, UnifiedLLM] = {}


def get_unified_llm_client(task: str = "main") -> Optional[UnifiedLLM]:
    """
    Get the unified LLM client with fallback chain.

    This is the recommended way to get an LLM client as it:
    - Tries ZAI first
    - Falls back to OpenRouter if ZAI fails
    - Falls back to local Ollama if both fail
    - Handles empty responses and errors gracefully

    Returns:
        UnifiedLLM instance or None if not configured
    """
    global _unified_clients

    task_key = task or "main"
    if task_key in _unified_clients:
        return _unified_clients[task_key]

    try:
        from core.settings import get as settings_get

        # Get fallback configuration
        llm_config = settings_get("LLM_FALLBACK", {})
        if not llm_config.get("ENABLED", False):
            print("[LLM] Fallback not enabled, using single provider")
            return None

        _unified_clients[task_key] = get_unified_llm(settings_getter=settings_get, task=task_key)
        print(f"[LLM] Unified LLM initialized with fallback chain for task={task_key}")
        return _unified_clients[task_key]

    except ImportError:
        print("[LLM] Settings not available for unified LLM")
        return None
    except Exception as e:
        print(f"[LLM] Error creating unified LLM: {e}")
        return None


def get_fallback_llm_client() -> Optional[FallbackRouter]:
    """
    Get the fallback router for LLM requests.

    This provides a simpler interface than UnifiedLLM with:
    - Direct provider list
    - Simple logging
    - No state management

    Returns:
        FallbackRouter instance or None if not configured
    """
    try:
        return get_fallback_router()
    except Exception as e:
        print(f"[LLM] Error creating fallback router: {e}")
        return None


def reset_unified_client():
    """Reset the unified client cache (for testing or reconfiguration)"""
    global _unified_clients
    _unified_clients = {}
