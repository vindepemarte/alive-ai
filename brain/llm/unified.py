"""
Brain: LLM - Unified LLM Interface with Fallback Chain
Manages multiple LLM providers with automatic fallback when one fails.
"""

import asyncio
import time
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .base import BaseLLM
from .capabilities import ChatResult, ModelCapabilities
from .zai import ZAIClient
from .openrouter import OpenRouterClient
from .ollama import OllamaClient


class ProviderStatus(Enum):
    """Status of an LLM provider"""
    UNKNOWN = "unknown"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    RATE_LIMITED = "rate_limited"
    ERROR = "error"


@dataclass
class ProviderInfo:
    """Information about a provider in the fallback chain"""
    name: str
    client: BaseLLM
    status: ProviderStatus = ProviderStatus.UNKNOWN
    last_success: float = 0
    last_failure: float = 0
    consecutive_failures: int = 0
    total_requests: int = 0
    successful_requests: int = 0

    @property
    def capabilities(self) -> ModelCapabilities:
        return self.client.get_capabilities()


class UnifiedLLM(BaseLLM):
    """
    Unified LLM interface with automatic fallback chain.

    Tries providers in order until one succeeds:
    1. ZAI (primary)
    2. OpenRouter (fallback)
    3. Ollama (local fallback)

    Features:
    - Automatic failover on errors or empty responses
    - Provider health tracking
    - Configurable timeouts and retries
    - Detailed logging
    - Compatible with BaseLLM interface
    """

    # Default configuration
    DEFAULT_CONFIG = {
        "enabled": True,
        "order": ["zai", "openrouter"],
        "timeout_seconds": 60,
        "retry_on_empty": True,
        "max_consecutive_failures": 3,
        "backoff_seconds": 30,
        "ollama_url": "http://172.17.0.1:11434",
        "ollama_model": "phi4:latest",
    }

    def __init__(self, config: dict = None, settings_getter=None):
        """
        Initialize the unified LLM with fallback chain.

        Args:
            config: Configuration dictionary (merged with defaults)
            settings_getter: Function to get settings from settings.json
        """
        # BaseLLM requires api_key and model - use placeholder values
        super().__init__("unified", "fallback-chain")
        self._explicit_config = config or {}
        self.config = {**self.DEFAULT_CONFIG, **self._explicit_config}
        self._settings_getter = settings_getter
        self._providers: Dict[str, ProviderInfo] = {}
        self._active_provider: Optional[str] = None
        self._initialized = False

        # Import os for env vars
        import os
        self._os = os

    def _get_setting(self, key: str, default: Any = None) -> Any:
        """Get a setting from config or settings.json"""
        # 1. Try explicit config first
        if key in self._explicit_config:
            return self._explicit_config[key]

        # 2. Try settings getter (root level)
        if self._settings_getter:
            value = self._settings_getter(key)
            if value is not None:
                return value

        # 3. Try LLM_FALLBACK nested config
        if self._settings_getter:
            all_settings = self._settings_getter("LLM_FALLBACK") or {}
            if key.upper() in all_settings:
                return all_settings[key.upper()]
            if key in all_settings:
                return all_settings[key]

        # 4. Fall back to DEFAULT_CONFIG
        if key in self.DEFAULT_CONFIG:
            return self.DEFAULT_CONFIG[key]

        return default

    def _initialize_providers(self):
        """Initialize all configured providers"""
        if self._initialized:
            return

        order = self._get_setting("order", self.config["order"])

        for provider_name in order:
            client = self._create_provider(provider_name)
            if client:
                self._providers[provider_name] = ProviderInfo(
                    name=provider_name,
                    client=client
                )
                print(f"[UnifiedLLM] Initialized provider: {provider_name}")

        self._initialized = True

    def _create_provider(self, name: str) -> Optional[BaseLLM]:
        """Create a provider client by name"""
        name = name.lower()

        if name == "zai":
            api_key = self._get_setting("ZAI_API_KEY") or self._os.environ.get("ZAI_API_KEY", "")
            model = self._get_setting("ZAI_MODEL_MAIN") or self._os.environ.get("ZAI_MODEL_MAIN", "glm-4.6v")
            if api_key:
                return ZAIClient(api_key, model)

        elif name == "openrouter":
            api_key = self._get_setting("OPENROUTER_API_KEY") or self._os.environ.get("OPENROUTER_API_KEY", "")
            model = self._get_setting("OPENROUTER_MODEL_MAIN") or self._os.environ.get("OPENROUTER_MODEL_MAIN", "anthropic/claude-3.5-sonnet")
            if api_key:
                return OpenRouterClient(api_key, model)

        elif name == "ollama":
            url = self._get_setting("OLLAMA_URL") or self._get_setting("ollama_url", "http://172.17.0.1:11434")
            model = self._get_setting("OLLAMA_MODEL") or self._get_setting("ollama_model", "phi4:latest")
            # Ollama doesn't require an API key
            return OllamaClient("", model, url)

        return None

    async def _check_provider_available(self, name: str) -> bool:
        """Check if a provider is available for use"""
        if name not in self._providers:
            return False

        info = self._providers[name]

        # Check if we're in backoff due to consecutive failures
        max_failures = self._get_setting("max_consecutive_failures", 3)
        backoff = self._get_setting("backoff_seconds", 30)

        if info.consecutive_failures >= max_failures:
            if time.time() - info.last_failure < backoff:
                print(f"[UnifiedLLM] Provider {name} in backoff ({info.consecutive_failures} failures)")
                return False
            else:
                # Reset after backoff period
                info.consecutive_failures = 0

        # Check actual availability if provider supports it
        client = info.client
        if hasattr(client, 'is_available'):
            try:
                available = await client.is_available()
                info.status = ProviderStatus.AVAILABLE if available else ProviderStatus.UNAVAILABLE
                return available
            except Exception as e:
                print(f"[UnifiedLLM] Error checking {name} availability: {e}")
                info.status = ProviderStatus.ERROR
                return False

        # Assume available if we can't check
        return True

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = None
    ) -> Optional[str]:
        """
        Send a chat request through the fallback chain.

        This method is compatible with BaseLLM interface - returns just the response string.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = use default)

        Returns:
            Response text string, or None if all providers fail
        """
        response, _ = await self.chat_with_provider(messages, max_tokens, temperature)
        return response

    def get_capabilities(self) -> ModelCapabilities:
        self._initialize_providers()
        if self._active_provider and self._active_provider in self._providers:
            return self._providers[self._active_provider].capabilities
        if self._providers:
            return next(iter(self._providers.values())).capabilities
        return super().get_capabilities()

    async def chat_result(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = None
    ) -> ChatResult:
        response, provider = await self.chat_with_provider(messages, max_tokens, temperature)
        info = self._providers.get(provider) if provider else None
        caps = info.capabilities if info else self.get_capabilities()
        return ChatResult(
            content=response,
            provider=provider or caps.provider,
            model=caps.model,
            capabilities=caps,
        )

    async def chat_with_provider(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = None,
        provider_hint: str = None
    ) -> Tuple[Optional[str], str]:
        """
        Send a chat request through the fallback chain, returning provider info.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature (None = use default)
            provider_hint: Optional hint for which provider to try first

        Returns:
            Tuple of (response_text, provider_name_used)
            Returns (None, "") if all providers fail
        """
        self._initialize_providers()
        if not self._get_setting("enabled", True):
            # Fallback mode disabled, use only first provider
            first_provider = list(self._providers.keys())[0] if self._providers else None
            response = await self._try_single_provider(first_provider, messages, max_tokens, temperature)
            return response, first_provider or ""

        if not self._providers:
            print("[UnifiedLLM] No providers configured!")
            return None, ""

        # Determine order to try providers
        order = list(self._providers.keys())

        # If we have an active provider that recently succeeded, try it first
        if self._active_provider and self._active_provider in order:
            order.remove(self._active_provider)
            order.insert(0, self._active_provider)

        # Apply provider hint
        if provider_hint and provider_hint in order:
            order.remove(provider_hint)
            order.insert(0, provider_hint)

        # Try each provider in order
        last_error = None
        for provider_name in order:
            # Check if provider is available
            if not await self._check_provider_available(provider_name):
                continue

            try:
                response = await self._try_single_provider(
                    provider_name, messages, max_tokens, temperature
                )

                if response:
                    return response, provider_name
            except Exception as e:
                last_error = e
                print(f"[UnifiedLLM] Provider {provider_name} failed: {e}")

        # All providers failed
        print(f"[UnifiedLLM] All providers failed. Last error: {last_error}")
        return None, ""

    async def _try_single_provider(
        self,
        provider_name: str,
        messages: List[Dict[str, str]],
        max_tokens: int,
        temperature: float
    ) -> Optional[str]:
        """Try to get a response from a single provider"""
        if not provider_name or provider_name not in self._providers:
            return None

        info = self._providers[provider_name]
        client = info.client
        timeout = self._get_setting("timeout_seconds", 60)
        retry_on_empty = self._get_setting("retry_on_empty", True)

        info.total_requests += 1

        try:
            # Add timeout wrapper
            response = await asyncio.wait_for(
                client.chat(messages, max_tokens=max_tokens, temperature=temperature),
                timeout=timeout
            )

            # Check for empty or non-dialogue response
            if response and response.strip():
                try:
                    from core.thinking import sanitize_provider_response
                    sanitized = sanitize_provider_response(response)
                    if sanitized:
                        response = sanitized
                    elif sanitized != response:
                        print(f"[UnifiedLLM] Reasoning-only response from {provider_name}, treating as failure")
                        response = None
                except Exception:
                    pass

            if not response or not response.strip():
                if retry_on_empty:
                    print(f"[UnifiedLLM] Empty response from {provider_name}, retrying...")
                    # One retry with different temperature
                    response = await asyncio.wait_for(
                        client.chat(messages, max_tokens=max_tokens, temperature=0.7),
                        timeout=timeout
                    )
                    if response and response.strip():
                        try:
                            from core.thinking import sanitize_provider_response
                            sanitized = sanitize_provider_response(response)
                            if sanitized:
                                response = sanitized
                            elif sanitized != response:
                                print(f"[UnifiedLLM] Reasoning-only response from {provider_name} retry, treating as failure")
                                response = None
                        except Exception:
                            pass

            if response and response.strip():
                # Success!
                info.last_success = time.time()
                info.consecutive_failures = 0
                info.successful_requests += 1
                info.status = ProviderStatus.AVAILABLE
                self._active_provider = provider_name
                return response

            # Empty response after retry
            info.last_failure = time.time()
            info.consecutive_failures += 1
            return None

        except asyncio.TimeoutError:
            print(f"[UnifiedLLM] Timeout from {provider_name} after {timeout}s")
            info.last_failure = time.time()
            info.consecutive_failures += 1
            info.status = ProviderStatus.ERROR
            return None

        except Exception as e:
            print(f"[UnifiedLLM] Error from {provider_name}: {e}")
            info.last_failure = time.time()
            info.consecutive_failures += 1
            info.status = ProviderStatus.ERROR
            return None

    def get_active_provider(self) -> Optional[str]:
        """Get the name of the currently active provider"""
        return self._active_provider

    def get_provider_status(self) -> Dict[str, dict]:
        """Get status of all providers"""
        return {
            name: {
                "status": info.status.value,
                "last_success": info.last_success,
                "last_failure": info.last_failure,
                "consecutive_failures": info.consecutive_failures,
                "total_requests": info.total_requests,
                "successful_requests": info.successful_requests,
                "success_rate": info.successful_requests / max(1, info.total_requests),
                "capabilities": info.capabilities.to_dict(),
            }
            for name, info in self._providers.items()
        }

    def reset_provider(self, name: str):
        """Reset a provider's failure count"""
        if name in self._providers:
            self._providers[name].consecutive_failures = 0
            self._providers[name].status = ProviderStatus.UNKNOWN
            print(f"[UnifiedLLM] Reset provider: {name}")

    def set_provider_config(self, name: str, **kwargs):
        """Update configuration for a provider"""
        if name in self._providers:
            client = self._providers[name].client
            for key, value in kwargs.items():
                if hasattr(client, key):
                    setattr(client, key, value)
                    print(f"[UnifiedLLM] Updated {name}.{key} = {value}")

    async def close(self):
        """Close all provider sessions"""
        for name, info in self._providers.items():
            try:
                if hasattr(info.client, 'close'):
                    await info.client.close()
            except Exception as e:
                print(f"[UnifiedLLM] Error closing {name}: {e}")

    def __repr__(self):
        providers = list(self._providers.keys())
        active = self._active_provider or "none"
        return f"<UnifiedLLM providers={providers} active={active}>"


# Singleton instance
_unified_llm: Optional[UnifiedLLM] = None


def get_unified_llm(config: dict = None, settings_getter=None) -> UnifiedLLM:
    """
    Get the global UnifiedLLM instance.

    Args:
        config: Configuration (only used on first call)
        settings_getter: Function to get settings from settings.json

    Returns:
        The UnifiedLLM singleton
    """
    global _unified_llm

    if _unified_llm is None:
        # Get settings getter if not provided
        if settings_getter is None:
            try:
                from core.settings import get as settings_get
                settings_getter = settings_get
            except ImportError:
                pass

        _unified_llm = UnifiedLLM(config, settings_getter)
        _unified_llm._initialize_providers()

    return _unified_llm


def reset_unified_llm():
    """Reset the singleton (for testing)"""
    global _unified_llm
    _unified_llm = None
