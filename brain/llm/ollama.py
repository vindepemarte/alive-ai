"""
Brain: LLM - Ollama API Client
Local LLM support via Ollama for ultimate fallback
"""

import aiohttp
import asyncio
from typing import Optional, List, Dict
from .base import BaseLLM


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
        max_tokens: int = 500,
        temperature: float = None
    ) -> Optional[str]:
        """Send chat completion request via Ollama API"""
        import os
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
                "num_predict": max_tokens,
                "temperature": temperature,
                "top_p": 0.9,
                "repeat_penalty": 1.1,
            }
        }

        print(f"[Ollama] Request to {url} with model {self.model}")

        try:
            start_time = time.time()

            async with session.post(
                f"{url}/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=120)  # Local can be slower
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    print(f"[Ollama] Error {resp.status}: {error[:300]}")
                    return None

                data = await resp.json()
                print(f"[Ollama] Raw response keys: {list(data.keys())}")

                # Check for error in response
                if "error" in data:
                    print(f"[Ollama] API Error: {data['error']}")
                    return None

                # Ollama response format
                message = data.get("message", {})
                content = message.get("content", "")

                # Some models expose private reasoning in a separate `thinking`
                # field. Do not send that as visible chat content.
                if not content or not content.strip():
                    thinking = message.get("thinking", "")
                    if thinking and thinking.strip():
                        print("[Ollama] Response had thinking but no visible content")

                if not content or not content.strip():
                    print(f"[Ollama] Empty content in response: {data}")
                    return None

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
