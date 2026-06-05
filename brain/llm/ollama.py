"""
Brain: LLM - Ollama API Client
Local LLM support via Ollama for ultimate fallback
"""

import aiohttp
import asyncio
import os
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


class OllamaClient(BaseLLM):
    """Ollama API client for local LLM inference"""

    # Default URLs - try Docker host access first, then localhost
    DEFAULT_URLS = [
        "http://172.17.0.1:11434",  # Docker bridge gateway
        "http://host.docker.internal:11434",  # Docker Desktop
        "http://localhost:11434",  # Local
    ]

    def __init__(self, api_key: str = "", model: str = "phi4:latest", base_url: str = None):
        # Ollama doesn't need an API key, but we keep the interface consistent
        super().__init__(api_key or "local", model)
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None
        self._available: Optional[bool] = None
        self._last_check: float = 0

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            provider="ollama",
            model=self.model,
            api_style="ollama_chat",
            local=True,
            requires_api_key=False,
            supports_streaming=True,
            supported_params=frozenset({"num_predict", "temperature", "top_p", "repeat_penalty", "think"}),
            reasoning=ReasoningCapabilities(
                supports_hidden_reasoning=True,
                supports_disable_control=True,
                supports_exclude_control=False,
                control_style="ollama_think",
            ),
        )

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    async def _discover_url(self) -> Optional[str]:
        """Try to discover a working Ollama URL"""
        if self.base_url:
            return self.base_url

        session = await self._get_session()

        for url in self.DEFAULT_URLS:
            try:
                async with session.get(
                    f"{url}/api/tags",
                    timeout=aiohttp.ClientTimeout(total=2)
                ) as resp:
                    if resp.status == 200:
                        print(f"[Ollama] Discovered at {url}")
                        self.base_url = url
                        return url
            except Exception:
                continue

        return None

    async def is_available(self) -> bool:
        """Check if Ollama is running and the model is available"""
        import time

        # Cache availability for 30 seconds
        if self._available is not None and time.time() - self._last_check < 30:
            return self._available

        try:
            url = await self._discover_url()
            if not url:
                self._available = False
                self._last_check = time.time()
                return False

            session = await self._get_session()

            # Check if model is available
            async with session.get(
                f"{url}/api/tags",
                timeout=aiohttp.ClientTimeout(total=5)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    models = data.get("models", [])
                    model_names = [m.get("name", "") for m in models]

                    # Check if our model (or base model name) is available
                    model_base = self.model.split(":")[0]
                    available = any(
                        self.model in name or model_base in name
                        for name in model_names
                    )

                    if not available and models:
                        # Fall back to first available model
                        self.model = models[0].get("name", self.model)
                        print(f"[Ollama] Model not found, using {self.model}")
                        available = True

                    self._available = available
                    self._last_check = time.time()
                    return available

        except Exception as e:
            print(f"[Ollama] Availability check failed: {e}")

        self._available = False
        self._last_check = time.time()
        return False

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int | None = None,
        temperature: float = None
    ) -> Optional[str]:
        """Send chat completion request via Ollama API"""
        import time

        # Use passed temperature, or environment variable, or default
        if temperature is None:
            temperature = float(os.environ.get("LLM_TEMPERATURE", "0.95"))

        # Discover URL if not set
        if not self.base_url:
            url = await self._discover_url()
            if not url:
                print("[Ollama] No reachable Ollama instance")
                return None
        else:
            url = self.base_url
            print(f"[Ollama] Using configured URL: {url}")

        session = await self._get_session()

        # Convert messages to Ollama format
        # Ollama expects a different format than OpenAI
        ollama_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role in ("user", "assistant", "system"):
                ollama_messages.append({"role": role, "content": content})

        payload = {
            "model": self.model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            }
        }
        if max_tokens is not None:
            payload["options"]["num_predict"] = max_tokens
        thinking_enabled = _settings_bool("LLM_THINKING_ENABLED", True)
        if not thinking_enabled and self.get_capabilities().reasoning.supports_disable_control:
            payload["think"] = False

        print(f"[Ollama] Request to {url} with model {self.model}")

        try:
            start_time = time.time()

            async def post_chat(payload_to_send: Dict) -> tuple[int, object]:
                async with session.post(
                    f"{url}/api/chat",
                    json=payload_to_send,
                    timeout=aiohttp.ClientTimeout(total=120)  # Local can be slower
                ) as resp:
                    if resp.status != 200:
                        return resp.status, await resp.text()
                    return resp.status, await resp.json()

            async def post_with_compat(payload_to_send: Dict) -> tuple[int, object]:
                status, result = await post_chat(payload_to_send)
                if status != 200 and "think" in payload_to_send and status in (400, 422):
                    print("[Ollama] think control rejected, retrying without reasoning control")
                    retry_payload = dict(payload_to_send)
                    retry_payload.pop("think", None)
                    return await post_chat(retry_payload)
                return status, result

            status, result = await post_with_compat(payload)
            if status != 200:
                print(f"[Ollama] Error {status}: {str(result)[:300]}")
                return None

            data = result
            if isinstance(data, dict):
                print(f"[Ollama] Raw response keys: {list(data.keys())}")

                # Check for error in response
                if "error" in data:
                    print(f"[Ollama] API Error: {data['error']}")
                    return None

                # Ollama response format
                message = data.get("message", {})
                content = visible_answer_from_message(message)

                # Some models expose private reasoning in a separate `thinking`
                # field. Do not send that as visible chat content.
                if not content or not content.strip():
                    if has_reasoning_payload(message):
                        print("[Ollama] Response had thinking but no visible answer content")
                        if thinking_enabled:
                            retry_payload = dict(payload)
                            retry_payload["think"] = False
                            status, result = await post_with_compat(retry_payload)
                            if status == 200 and isinstance(result, dict):
                                data = result
                                message = data.get("message", {})
                                content = visible_answer_from_message(message)

                if not content or not content.strip():
                    print(f"[Ollama] Empty content in response: {data}")
                    return None

                try:
                    from core.thinking import sanitize_provider_response
                    sanitized = sanitize_provider_response(content)
                    if sanitized:
                        content = sanitized
                    elif sanitized != content:
                        print("[Ollama] Rejected reasoning-only visible content")
                        return None
                except Exception:
                    pass

                elapsed = time.time() - start_time
                print(f"[Ollama] Response ({elapsed:.1f}s): {content[:80]}...")

                # Mark as available since we got a response
                self._available = True
                self._last_check = time.time()

                return content.strip()

        except asyncio.TimeoutError:
            print(f"[Ollama] Timeout (120s)")
            return None
        except aiohttp.ClientError as e:
            print(f"[Ollama] Connection error: {e}")
            self._available = False
            return None
        except Exception as e:
            print(f"[Ollama] Exception: {e}")
            import traceback
            traceback.print_exc()
            return None

    async def close(self):
        """Close the client session"""
        if self.session and not self.session.closed:
            await self.session.close()
