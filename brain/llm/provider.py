"""
Brain: LLM - Provider Factory
Creates the appropriate LLM client based on configuration.
Supports both legacy single-provider mode and new unified fallback mode.
"""

import os
from typing import Optional, Tuple
from .base import BaseLLM
from .zai import ZAIClient
from .openrouter import OpenRouterClient
from .ollama import OllamaClient
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
        provider = settings_get("LLM_PROVIDER", "zai").lower()

        if provider == "openrouter":
            api_key = settings_get("OPENROUTER_API_KEY", "") or os.environ.get("OPENROUTER_API_KEY", "")
            if task == "fast":
                model = settings_get("OPENROUTER_MODEL_FAST", "openai/gpt-4o-mini")
            elif task == "thinking":
                model = settings_get("OPENROUTER_MODEL_THINKING", "anthropic/claude-3.5-sonnet")
            else:
                model = settings_get("OPENROUTER_MODEL_MAIN", "anthropic/claude-3.5-sonnet")
        else:
            # Default to ZAI
            api_key = settings_get("ZAI_API_KEY", "") or os.environ.get("ZAI_API_KEY", "")
            if task == "fast":
                model = settings_get("ZAI_MODEL_FAST", "glm-4-flash")
            elif task == "thinking":
                model = settings_get("ZAI_MODEL_THINKING", "glm-4.6v")
            else:
                model = settings_get("ZAI_MODEL_MAIN", "glm-4.6v")

        return provider, api_key, model

    except ImportError:
        # Fallback to environment variables
        pass

    # Environment variable fallback
    provider = os.environ.get("LLM_PROVIDER", "zai").lower()

    if provider == "openrouter":
        api_key = os.environ.get("OPENROUTER_API_KEY", "")
        if task == "fast":
            model = os.environ.get("OPENROUTER_MODEL_FAST", "openai/gpt-4o-mini")
        elif task == "thinking":
            model = os.environ.get("OPENROUTER_MODEL_THINKING", "anthropic/claude-3.5-sonnet")
        else:
            model = os.environ.get("OPENROUTER_MODEL_MAIN", "anthropic/claude-3.5-sonnet")
    else:
        # Default to ZAI
        api_key = os.environ.get("ZAI_API_KEY", "")
        if task == "fast":
            model = os.environ.get("ZAI_MODEL_FAST", "glm-4-flash")
        elif task == "thinking":
            model = os.environ.get("ZAI_MODEL_THINKING", "glm-4.6v")
        else:
            model = os.environ.get("ZAI_MODEL_MAIN", "glm-4.6v")

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
        return get_unified_llm_client()

    if not api_key:
        print(f"[LLM] No API key for provider: {provider}")
        return None

    if provider == "openrouter":
        return OpenRouterClient(api_key, model)
    else:
        return ZAIClient(api_key, model)


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

# Cache for the unified client
_unified_client: Optional[UnifiedLLM] = None


def get_unified_llm_client() -> Optional[UnifiedLLM]:
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
    global _unified_client

    if _unified_client is not None:
        return _unified_client

    try:
        from core.settings import get as settings_get

        # Get fallback configuration
        llm_config = settings_get("LLM_FALLBACK", {})
        if not llm_config.get("ENABLED", False):
            print("[LLM] Fallback not enabled, using single provider")
            return None

        _unified_client = get_unified_llm(settings_getter=settings_get)
        print(f"[LLM] Unified LLM initialized with fallback chain")
        return _unified_client

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
    global _unified_client
    _unified_client = None
