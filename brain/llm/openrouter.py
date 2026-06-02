"""
Brain: LLM - OpenRouter API Client
OpenRouter provides unified access to many LLM providers
"""

import aiohttp
import asyncio
import os
import time
from typing import Optional, List, Dict, Any
from .base import BaseLLM
from .reasoning import has_reasoning_payload, visible_answer_from_message


_MISSING = object()


def _coerce_bool(value: Any, default: bool) -> bool:
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


def _settings_value(key: str, default: Any = _MISSING) -> Any:
    if key in os.environ:
        return os.environ[key]
    try:
        from core.settings import get
        return get(key, default)
    except Exception:
        return default


def _openrouter_thinking_enabled() -> bool:
    """OpenRouter reasoning controls are opt-in because some models leak labels."""
    value = _settings_value("OPENROUTER_THINKING_ENABLED", _MISSING)
    if value is _MISSING:
        return False
    return _coerce_bool(value, False)


def _extract_openrouter_answer(data: dict) -> str:
    """Extract only visible assistant answer text, never reasoning fields."""
    choices = data.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    return visible_answer_from_message(message)


def _has_reasoning_activity(data: dict) -> bool:
    usage = data.get("usage") or {}
    details = usage.get("completion_tokens_details") or {}
    try:
        if int(details.get("reasoning_tokens") or 0) > 0:
            return True
    except (TypeError, ValueError):
        pass
    choices = data.get("choices") or []
    if not choices:
        return False
    message = choices[0].get("message") or {}
    return has_reasoning_payload(message)


class OpenRouterClient(BaseLLM):
    """OpenRouter API client - unified access to many models"""

    BASE_URL = "https://openrouter.ai/api/v1"

    # Site URL for rankings (required by OpenRouter)
    SITE_URL = "https://alive_ai.ai"
    SITE_NAME = "Alive-AI Girlfriend"

    def __init__(self, api_key: str, model: str = "anthropic/claude-3.5-sonnet"):
        super().__init__(api_key, model)
        self.session: Optional[aiohttp.ClientSession] = None
        self._available: Optional[bool] = None
        self._last_check: float = 0

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def is_available(self) -> bool:
        """Check if OpenRouter API is accessible and configured"""
        # Cache availability for 60 seconds
        if self._available is not None and time.time() - self._last_check < 60:
            return self._available

        if not self.api_key:
            self._available = False
            self._last_check = time.time()
            return False

        try:
            session = await self._get_session()

            # Check API key validity by listing models
            async with session.get(
                f"{self.BASE_URL}/models",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                },
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    self._available = True
                    self._last_check = time.time()
                    return True
                elif resp.status == 401:
                    print("[OpenRouter] Invalid API key")
                    self._available = False
                    self._last_check = time.time()
                    return False
        except Exception as e:
            print(f"[OpenRouter] Availability check failed: {e}")

        self._available = False
        self._last_check = time.time()
        return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = None
    ) -> Optional[str]:
        """Send chat completion request via OpenRouter"""
        # Use passed temperature, or environment variable, or default high value
        if temperature is None:
            temperature = float(os.environ.get("LLM_TEMPERATURE", "0.95"))

        session = await self._get_session()

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": self.SITE_URL,
            "X-Title": self.SITE_NAME
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "frequency_penalty": 0.8,  # Penalize repeated phrases - increased from 0.5
            "presence_penalty": 0.6,   # Encourage topic diversity - increased from 0.3
        }
        thinking_enabled = _openrouter_thinking_enabled()
        if thinking_enabled:
            payload["reasoning"] = {
                "effort": "low",
                "exclude": True,
            }

        try:
            async def post_chat(payload_to_send: dict) -> tuple[int, object]:
                async with session.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload_to_send,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status != 200:
                        return resp.status, await resp.text()
                    return resp.status, await resp.json()

            status, result = await post_chat(payload)
            if status != 200 and "reasoning" in payload and status in (400, 422):
                print("[OpenRouter] reasoning control rejected, retrying without reasoning control")
                retry_payload = dict(payload)
                retry_payload.pop("reasoning", None)
                status, result = await post_chat(retry_payload)

            if status != 200:
                print(f"[OpenRouter] Error {status}: {str(result)[:300]}")
                self._available = False
                return None

            data = result
            if isinstance(data, dict):
                # Check for error response
                if "error" in data:
                    print(f"[OpenRouter] API Error: {data['error']}")
                    self._available = False
                    return None
                # Log token usage
                if "usage" in data:
                    usage = data["usage"]
                    print(f"[LLM] Tokens - Input: {usage.get('prompt_tokens', '?')} | Output: {usage.get('completion_tokens', '?')} | Total: {usage.get('total_tokens', '?')}")
                if "choices" not in data or not data["choices"]:
                    print(f"[OpenRouter] No choices in response: {list(data.keys())}")
                    return None

                content = _extract_openrouter_answer(data)
                if (not content or not content.strip()) and thinking_enabled and _has_reasoning_activity(data):
                    print("[OpenRouter] Thinking produced no answer field, retrying without reasoning control")
                    retry_payload = dict(payload)
                    retry_payload.pop("reasoning", None)
                    status, result = await post_chat(retry_payload)
                    if status == 200 and isinstance(result, dict):
                        data = result
                        if "usage" in data:
                            usage = data["usage"]
                            print(f"[LLM] Retry tokens - Input: {usage.get('prompt_tokens', '?')} | Output: {usage.get('completion_tokens', '?')} | Total: {usage.get('total_tokens', '?')}")
                        content = _extract_openrouter_answer(data)
                    elif status in (400, 422):
                        retry_payload.pop("reasoning", None)
                        status, result = await post_chat(retry_payload)
                        if status == 200 and isinstance(result, dict):
                            data = result
                            content = _extract_openrouter_answer(data)

                if not content or not content.strip():
                    choice = data["choices"][0] if data.get("choices") else {}
                    finish_reason = choice.get("finish_reason") or choice.get("native_finish_reason")
                    print(f"[OpenRouter] Empty answer content (finish_reason={finish_reason})")
                    return None

                try:
                    from core.thinking import sanitize_provider_response
                    sanitized = sanitize_provider_response(content)
                    if sanitized:
                        content = sanitized
                    elif sanitized != content:
                        print("[OpenRouter] Rejected non-dialogue visible content")
                        return None
                except Exception:
                    pass

                print(f"[OpenRouter] Response: {content[:100]}...")

                # Mark as available since we got a response
                self._available = True
                self._last_check = time.time()
                return content

        except asyncio.TimeoutError:
            print(f"[OpenRouter] Timeout (60s)")
            return None
        except Exception as e:
            print(f"[OpenRouter] Exception: {e}")
            return None

    async def close(self):
        """Close the client session"""
        if self.session and not self.session.closed:
            await self.session.close()
