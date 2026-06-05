"""
Brain: LLM - Fallback Router
Simple router that tries providers in order with logging and error handling.
"""

import asyncio
import time
from typing import Optional, List, Dict, Tuple, Callable
from dataclasses import dataclass
from enum import Enum

from .base import BaseLLM
from .factory import canonical_provider_name, create_llm_client


class FallbackResult(Enum):
    """Result of a fallback attempt"""
    SUCCESS = "success"
    EMPTY_RESPONSE = "empty_response"
    TIMEOUT = "timeout"
    ERROR = "error"
    UNAVAILABLE = "unavailable"


@dataclass
class FallbackLog:
    """Log entry for a fallback attempt"""
    provider: str
    result: FallbackResult
    latency_ms: float
    error: Optional[str] = None
    response_preview: Optional[str] = None


class FallbackRouter:
    """
    Simple fallback router for LLM providers.

    Tries providers in configured order:
    1. ZAI (primary)
    2. OpenRouter (cloud fallback)
    3. Ollama (local fallback)

    Features:
    - Automatic failover on errors or empty responses
    - Configurable timeouts
    - Detailed logging of all attempts
    - Health tracking
    """

    def __init__(
        self,
        providers: List[Tuple[str, BaseLLM]],
        timeout_seconds: float = 60,
        retry_on_empty: bool = True
    ):
        """
        Initialize the fallback router.

        Args:
            providers: List of (name, client) tuples in fallback order
            timeout_seconds: Maximum time per provider
            retry_on_empty: Whether to retry once on empty response
        """
        self.providers = providers
        self.timeout_seconds = timeout_seconds
        self.retry_on_empty = retry_on_empty
        self._log: List[FallbackLog] = []
        self._max_log_size = 100

    def _log_attempt(self, entry: FallbackLog):
        """Log an attempt"""
        self._log.append(entry)
        # Trim log if too large
        if len(self._log) > self._max_log_size:
            self._log = self._log[-self._max_log_size:]

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int | None = None,
        temperature: float = None
    ) -> Tuple[Optional[str], str]:
        """
        Try providers in order until one succeeds.

        Args:
            messages: Chat messages
            max_tokens: Optional provider output cap. None lets the provider decide.
            temperature: Sampling temperature

        Returns:
            Tuple of (response, provider_name) or (None, "") if all fail
        """
        for provider_name, client in self.providers:
            response = await self._try_provider(
                provider_name, client, messages, max_tokens, temperature
            )

            if response:
                return response, provider_name

        return None, ""

    async def _try_provider(
        self,
        name: str,
        client: BaseLLM,
        messages: List[Dict[str, str]],
        max_tokens: int | None,
        temperature: float
    ) -> Optional[str]:
        """Try a single provider"""
        start_time = time.time()

        # Check availability if supported
        if hasattr(client, 'is_available'):
            try:
                available = await asyncio.wait_for(
                    client.is_available(),
                    timeout=5
                )
                if not available:
                    self._log_attempt(FallbackLog(
                        provider=name,
                        result=FallbackResult.UNAVAILABLE,
                        latency_ms=(time.time() - start_time) * 1000,
                        error="Provider not available"
                    ))
                    return None
            except Exception as e:
                self._log_attempt(FallbackLog(
                    provider=name,
                    result=FallbackResult.UNAVAILABLE,
                    latency_ms=(time.time() - start_time) * 1000,
                    error=f"Availability check failed: {e}"
                ))
                return None

        # Try the chat request
        try:
            response = await asyncio.wait_for(
                client.chat(messages, max_tokens=max_tokens, temperature=temperature),
                timeout=self.timeout_seconds
            )

            latency_ms = (time.time() - start_time) * 1000

            if response and response.strip():
                try:
                    from core.thinking import sanitize_provider_response
                    sanitized = sanitize_provider_response(response)
                    if sanitized:
                        response = sanitized
                    elif sanitized != response:
                        print(f"[FallbackRouter] Reasoning-only response from {name}, treating as empty")
                        response = None
                except Exception:
                    pass

            if not response or not response.strip():
                # Empty response - retry once if configured
                if self.retry_on_empty:
                    print(f"[FallbackRouter] Empty response from {name}, retrying...")
                    response = await asyncio.wait_for(
                        client.chat(messages, max_tokens=max_tokens, temperature=0.7),
                        timeout=self.timeout_seconds
                    )
                    if response and response.strip():
                        try:
                            from core.thinking import sanitize_provider_response
                            sanitized = sanitize_provider_response(response)
                            if sanitized:
                                response = sanitized
                            elif sanitized != response:
                                print(f"[FallbackRouter] Reasoning-only response from {name} retry, treating as empty")
                                response = None
                        except Exception:
                            pass

                if not response or not response.strip():
                    self._log_attempt(FallbackLog(
                        provider=name,
                        result=FallbackResult.EMPTY_RESPONSE,
                        latency_ms=latency_ms
                    ))
                    return None

            # Success!
            self._log_attempt(FallbackLog(
                provider=name,
                result=FallbackResult.SUCCESS,
                latency_ms=latency_ms,
                response_preview=response[:50] if response else None
            ))
            print(f"[FallbackRouter] Success from {name} in {latency_ms:.0f}ms")
            return response

        except asyncio.TimeoutError:
            latency_ms = (time.time() - start_time) * 1000
            self._log_attempt(FallbackLog(
                provider=name,
                result=FallbackResult.TIMEOUT,
                latency_ms=latency_ms,
                error=f"Timeout after {self.timeout_seconds}s"
            ))
            print(f"[FallbackRouter] Timeout from {name}")
            return None

        except Exception as e:
            latency_ms = (time.time() - start_time) * 1000
            self._log_attempt(FallbackLog(
                provider=name,
                result=FallbackResult.ERROR,
                latency_ms=latency_ms,
                error=str(e)
            ))
            print(f"[FallbackRouter] Error from {name}: {e}")
            return None

    def get_log(self, limit: int = 20) -> List[FallbackLog]:
        """Get recent log entries"""
        return self._log[-limit:]

    def get_stats(self) -> dict:
        """Get statistics about fallback attempts"""
        if not self._log:
            return {"total": 0}

        success_count = sum(1 for e in self._log if e.result == FallbackResult.SUCCESS)
        by_provider = {}
        for entry in self._log:
            if entry.provider not in by_provider:
                by_provider[entry.provider] = {"total": 0, "success": 0}
            by_provider[entry.provider]["total"] += 1
            if entry.result == FallbackResult.SUCCESS:
                by_provider[entry.provider]["success"] += 1

        return {
            "total": len(self._log),
            "success_rate": success_count / len(self._log),
            "by_provider": by_provider
        }


def create_fallback_router_from_settings(settings_getter: Callable = None) -> FallbackRouter:
    """
    Create a FallbackRouter from settings.json configuration.

    Args:
        settings_getter: Function to get settings

    Returns:
        Configured FallbackRouter
    """
    # Get settings getter if not provided
    if settings_getter is None:
        try:
            from core.settings import get as settings_get
            settings_getter = settings_get
        except ImportError:
            settings_getter = lambda k, d=None: d

    # Get LLM fallback config
    llm_config = settings_getter("LLM_FALLBACK", {})
    if not llm_config:
        llm_config = {}

    # Get fallback order
    order = llm_config.get("ORDER", ["zai", "openrouter", "ollama"])
    timeout = llm_config.get("TIMEOUT_SECONDS", 60)
    retry_on_empty = llm_config.get("RETRY_ON_EMPTY", True)

    providers = []

    for name in order:
        name_lower = canonical_provider_name(name)
        client = create_llm_client(name_lower, task="main", settings_getter=settings_getter)

        if client:
            providers.append((name_lower, client))
            print(f"[FallbackRouter] Added provider: {name_lower}")

    if not providers:
        print("[FallbackRouter] Warning: No providers configured!")

    return FallbackRouter(
        providers=providers,
        timeout_seconds=timeout,
        retry_on_empty=retry_on_empty
    )


# Singleton instance
_router: Optional[FallbackRouter] = None


def get_fallback_router() -> FallbackRouter:
    """Get the global FallbackRouter instance"""
    global _router

    if _router is None:
        _router = create_fallback_router_from_settings()

    return _router


def reset_fallback_router():
    """Reset the singleton (for testing)"""
    global _router
    _router = None
