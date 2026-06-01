"""
Brain: LLM Module
Multi-provider LLM support with automatic fallback (ZAI, OpenRouter, Ollama)
"""

from .base import BaseLLM
from .zai import ZAIClient
from .openrouter import OpenRouterClient
from .ollama import OllamaClient
from .unified import (
    UnifiedLLM,
    ProviderStatus,
    get_unified_llm,
    reset_unified_llm
)
from .fallback_router import (
    FallbackRouter,
    FallbackResult,
    create_fallback_router_from_settings,
    get_fallback_router,
    reset_fallback_router
)
from .provider import (
    get_llm_client,
    get_fast_llm,
    get_thinking_llm,
    get_main_llm,
    get_provider_config,
    get_unified_llm_client
)

__all__ = [
    # Base classes
    'BaseLLM',

    # Provider clients
    'ZAIClient',
    'OpenRouterClient',
    'OllamaClient',

    # Unified interface
    'UnifiedLLM',
    'ProviderStatus',
    'get_unified_llm',
    'reset_unified_llm',

    # Fallback router
    'FallbackRouter',
    'FallbackResult',
    'create_fallback_router_from_settings',
    'get_fallback_router',
    'reset_fallback_router',

    # Legacy factory functions
    'get_llm_client',
    'get_fast_llm',
    'get_thinking_llm',
    'get_main_llm',
    'get_provider_config',

    # New unified factory
    'get_unified_llm_client',
]
