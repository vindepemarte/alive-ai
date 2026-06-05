"""
Brain: LLM - ZAI API Client
Uses OpenAI-compatible endpoint for ZAI Coding Plan
"""

import aiohttp
import asyncio
import os
import time
from typing import Optional, List, Dict
from .base import BaseLLM
from .capabilities import ModelCapabilities, ReasoningCapabilities
from .reasoning import has_reasoning_payload, visible_answer_from_message


def _settings_bool(key: str, default: bool) -> bool:
    if key in os.environ:
        return os.environ[key].strip().lower() not in ("0", "false", "no", "off")
    try:
        from core.settings import get_bool
        return get_bool(key, default)
    except Exception:
        return default


class ZAIClient(BaseLLM):
    """ZAI API client (OpenAI-compatible)"""

    # ZAI Coding Plan uses OpenAI-compatible endpoint
    BASE_URL = "https://api.z.ai/api/coding/paas/v4"

    def __init__(self, api_key: str, model: str = "glm-4.6v"):
        super().__init__(api_key, model)
        self.session: Optional[aiohttp.ClientSession] = None
        self._available: Optional[bool] = None
        self._last_check: float = 0

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            provider="zai",
            model=self.model,
            api_style="openai_chat",
            local=False,
            requires_api_key=True,
            supports_streaming=False,
            supported_params=frozenset({"max_tokens", "temperature", "frequency_penalty", "presence_penalty", "thinking"}),
            reasoning=ReasoningCapabilities(
                supports_hidden_reasoning=True,
                supports_disable_control=True,
                supports_exclude_control=False,
                control_style="zai_thinking",
            ),
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def is_available(self) -> bool:
        """Check if ZAI API is accessible and configured"""
        # Cache availability for 60 seconds
        if self._available is not None and time.time() - self._last_check < 60:
            return self._available

        if not self.api_key:
            self._available = False
            self._last_check = time.time()
            return False

        try:
            session = await self._get_session()

            # Simple models list check to verify API is working
            async with session.get(
                f"{self.BASE_URL}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status == 200:
                    self._available = True
                    self._last_check = time.time()
                    return True
                elif resp.status == 401:
                    print("[ZAI] Invalid API key")
                    self._available = False
                    self._last_check = time.time()
                    return False
        except Exception as e:
            print(f"[ZAI] Availability check failed: {e}")

        self._available = False
        self._last_check = time.time()
        return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int | None = None,
        temperature: float = None
    ) -> Optional[str]:
        """Send chat completion request (OpenAI format)"""
        # Use passed temperature, or environment variable, or default high value
        if temperature is None:
            temperature = float(os.environ.get("LLM_TEMPERATURE", "0.95"))

        session = await self._get_session()

        # OpenAI API format with Bearer token
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "frequency_penalty": 0.8,
            "presence_penalty": 0.6,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        thinking_enabled = _settings_bool("LLM_THINKING_ENABLED", True)
        if not thinking_enabled and self.get_capabilities().reasoning.supports_disable_control:
            payload["thinking"] = {"type": "disabled"}

        visible_retry_added = False
        # Try original request, optional visible-answer retry, and optional
        # compatibility retry without rejected thinking controls.
        for _request_attempt in range(4):
            try:
                async with session.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=60)
                ) as resp:
                    if resp.status != 200:
                        error = await resp.text()
                        if "thinking" in payload and resp.status in (400, 422):
                            print("[ZAI] thinking control rejected, retrying without thinking control")
                            payload.pop("thinking", None)
                            continue
                        print(f"[ZAI] Error {resp.status}: {error[:300]}")
                        self._available = False
                        return None

                    data = await resp.json()
                    # Check for error response
                    if "error" in data:
                        print(f"[ZAI] API Error: {data['error']}")
                        self._available = False
                        return None
                    # Log token usage
                    if "usage" in data:
                        usage = data["usage"]
                        print(f"[LLM] Tokens - Input: {usage.get('prompt_tokens', '?')} | Output: {usage.get('completion_tokens', '?')} | Total: {usage.get('total_tokens', '?')}")
                    # OpenAI response format
                    if "choices" not in data or not data["choices"]:
                        print(f"[ZAI] No choices in response: {list(data.keys())}")
                        return None

                    message = data["choices"][0].get("message", {})
                    content = visible_answer_from_message(message)

                    # Log if reasoning_content present (thinking mode leak)
                    if has_reasoning_payload(message):
                        print(f"[ZAI] Note: reasoning_content present but ignored (internal thinking)")

                    # If still empty, retry with intimate instruction
                    if not content or not content.strip():
                        if not visible_retry_added:
                            visible_retry_added = True
                            print(f"[ZAI] Empty answer on first attempt, retrying with explicit visible-answer instruction...")
                            # Add intimate instruction to output dialogue
                            retry_messages = messages.copy()
                            retry_messages.append({
                                "role": "system",
                                "content": "IMPORTANT: Return a visible spoken answer in the message content. Keep private reasoning out of the visible answer."
                            })
                            payload["messages"] = retry_messages
                            if self.get_capabilities().reasoning.supports_disable_control:
                                payload["thinking"] = {"type": "disabled"}
                            continue
                        else:
                            print(f"[ZAI] Empty content after retry")
                            return None

                    try:
                        from core.thinking import sanitize_provider_response
                        sanitized = sanitize_provider_response(content)
                        if sanitized:
                            content = sanitized
                        elif sanitized != content:
                            print("[ZAI] Rejected reasoning-only visible content")
                            return None
                    except Exception:
                        pass

                    print(f"[ZAI] Response: {content[:80]}...")
                    # Mark as available since we got a response
                    self._available = True
                    self._last_check = time.time()
                    return content

            except asyncio.TimeoutError:
                print(f"[ZAI] Timeout (60s)")
                return None
            except Exception as e:
                print(f"[ZAI] Exception: {e}")
                return None

        return None

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
