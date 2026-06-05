"""Generic OpenAI-compatible chat-completions client.

This adapter is intentionally conservative. Local servers such as LM Studio,
llama.cpp, vLLM, and MLX-LM often expose the OpenAI chat-completions shape but
reject provider-specific extras. Keep the payload small and let Alive-AI's
runtime layers handle prompt shaping, memory, and response sanitizing.
"""

from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional

import aiohttp

from .base import BaseLLM
from .capabilities import ModelCapabilities
from .reasoning import visible_answer_from_message


def _normalize_base_url(base_url: str) -> str:
    url = (base_url or "").strip().rstrip("/")
    if not url:
        return ""
    return url


def _model_entries(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, dict):
        raw = data.get("data") or data.get("models") or []
    elif isinstance(data, list):
        raw = data
    else:
        raw = []
    return [item for item in raw if isinstance(item, dict)]


def _model_id(entry: dict[str, Any]) -> str:
    return str(entry.get("id") or entry.get("name") or entry.get("model") or "").strip()


def _context_tokens_from_metadata(entry: dict[str, Any]) -> int | None:
    candidates = [
        entry.get("context_length"),
        entry.get("context_window"),
        entry.get("max_context_length"),
        entry.get("max_context_tokens"),
        entry.get("n_ctx"),
    ]
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else {}
    candidates.extend(
        [
            metadata.get("context_length"),
            metadata.get("context_window"),
            metadata.get("max_context_length"),
            metadata.get("max_context_tokens"),
            metadata.get("n_ctx"),
        ]
    )
    for value in candidates:
        try:
            parsed = int(value)
            if parsed > 0:
                return parsed
        except (TypeError, ValueError):
            continue
    return None


class OpenAICompatibleClient(BaseLLM):
    """OpenAI chat-completions compatible adapter."""

    def __init__(
        self,
        api_key: str = "",
        model: str = "local-model",
        base_url: str = "http://127.0.0.1:8000/v1",
        provider_name: str = "openai-compatible",
        *,
        local: bool = False,
        requires_api_key: bool = False,
        supports_streaming: bool = True,
        supports_tools: bool = False,
        supports_vision: bool = False,
        supports_json_mode: bool = False,
        context_tokens: int | None = None,
        timeout_seconds: float = 60,
        extra_headers: dict[str, str] | None = None,
    ):
        super().__init__(api_key or "", model or "local-model")
        self.base_url = _normalize_base_url(base_url)
        self.provider_name = provider_name
        self.local = local
        self.requires_api_key = requires_api_key
        self.supports_streaming = supports_streaming
        self.supports_tools = supports_tools
        self.supports_vision = supports_vision
        self.supports_json_mode = supports_json_mode
        self.context_tokens = context_tokens
        self.timeout_seconds = timeout_seconds
        self.extra_headers = extra_headers or {}
        self.session: Optional[aiohttp.ClientSession] = None
        self._available: Optional[bool] = None
        self._last_check: float = 0
        self._metadata_source = "settings" if context_tokens else "default"

    def _url(self, suffix: str) -> str:
        return f"{self.base_url}/{suffix.lstrip('/')}"

    def _headers(self) -> dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        headers.update(self.extra_headers)
        return headers

    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session

    def get_capabilities(self) -> ModelCapabilities:
        return ModelCapabilities(
            provider=self.provider_name,
            model=self.model,
            api_style="openai_chat",
            local=self.local,
            requires_api_key=self.requires_api_key,
            context_tokens=self.context_tokens,
            supports_streaming=self.supports_streaming,
            supports_tools=self.supports_tools,
            supports_vision=self.supports_vision,
            supports_json_mode=self.supports_json_mode,
            supported_params=frozenset({"model", "messages", "max_tokens", "temperature", "stream"}),
            metadata_source=self._metadata_source,
        )

    async def refresh_capabilities(self) -> ModelCapabilities:
        await self._discover_models(update_availability=False)
        return self.get_capabilities()

    async def _discover_models(self, update_availability: bool = True) -> bool:
        if not self.base_url:
            if update_availability:
                self._available = False
                self._last_check = time.time()
            return False
        if self.requires_api_key and not self.api_key:
            if update_availability:
                self._available = False
                self._last_check = time.time()
            return False

        session = await self._get_session()
        try:
            async with session.get(
                self._url("models"),
                headers=self._headers(),
                timeout=aiohttp.ClientTimeout(total=5),
            ) as resp:
                if resp.status != 200:
                    if update_availability:
                        self._available = False
                        self._last_check = time.time()
                    return False

                data = await resp.json()
                entries = _model_entries(data)
                ids = [_model_id(entry) for entry in entries]
                ids = [item for item in ids if item]

                if ids and self.model in ("", "auto", "local-model"):
                    self.model = ids[0]
                    print(f"[{self.provider_name}] Auto-selected model: {self.model}")

                selected = next((entry for entry in entries if _model_id(entry) == self.model), None)
                if selected:
                    context = _context_tokens_from_metadata(selected)
                    if context:
                        self.context_tokens = context
                        self._metadata_source = "discovered"

                if update_availability:
                    self._available = True
                    self._last_check = time.time()
                return True
        except Exception as exc:
            print(f"[{self.provider_name}] Model discovery failed: {exc}")
            if update_availability:
                self._available = False
                self._last_check = time.time()
            return False

    async def is_available(self) -> bool:
        if self._available is not None and time.time() - self._last_check < 30:
            return self._available
        return await self._discover_models(update_availability=True)

    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int | None = None,
        temperature: float = None,
    ) -> Optional[str]:
        if not self.base_url:
            print(f"[{self.provider_name}] Missing base URL")
            return None
        if self.requires_api_key and not self.api_key:
            print(f"[{self.provider_name}] Missing API key")
            return None
        if temperature is None:
            temperature = float(os.environ.get("LLM_TEMPERATURE", "0.85"))

        payload = {
            "model": self.model,
            "messages": [
                {"role": msg.get("role", "user"), "content": msg.get("content", "")}
                for msg in messages
                if msg.get("role", "user") in ("system", "user", "assistant")
            ],
            "temperature": temperature,
            "stream": False,
        }
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        session = await self._get_session()
        try:
            async with session.post(
                self._url("chat/completions"),
                headers=self._headers(),
                json=payload,
                timeout=aiohttp.ClientTimeout(total=self.timeout_seconds),
            ) as resp:
                if resp.status != 200:
                    error = await resp.text()
                    print(f"[{self.provider_name}] Error {resp.status}: {error[:300]}")
                    if resp.status in (401, 403, 404):
                        self._available = False
                    return None

                data = await resp.json()

            if not isinstance(data, dict):
                print(f"[{self.provider_name}] Unexpected response type: {type(data).__name__}")
                return None
            if "error" in data:
                print(f"[{self.provider_name}] API Error: {data['error']}")
                return None

            usage = data.get("usage") or {}
            if usage:
                print(
                    f"[LLM:{self.provider_name}] Tokens - "
                    f"Input: {usage.get('prompt_tokens', '?')} | "
                    f"Output: {usage.get('completion_tokens', '?')} | "
                    f"Total: {usage.get('total_tokens', '?')}"
                )

            choices = data.get("choices") or []
            if not choices:
                print(f"[{self.provider_name}] No choices in response: {list(data.keys())}")
                return None

            choice = choices[0] or {}
            message = choice.get("message") or {}
            content = visible_answer_from_message(message)
            if not content and choice.get("text"):
                content = str(choice.get("text") or "")

            if not content or not content.strip():
                finish_reason = choice.get("finish_reason") or choice.get("native_finish_reason")
                print(f"[{self.provider_name}] Empty answer content (finish_reason={finish_reason})")
                return None

            try:
                from core.thinking import sanitize_provider_response

                sanitized = sanitize_provider_response(content)
                if sanitized:
                    content = sanitized
                elif sanitized != content:
                    print(f"[{self.provider_name}] Rejected non-dialogue visible content")
                    return None
            except Exception:
                pass

            self._available = True
            self._last_check = time.time()
            print(f"[{self.provider_name}] Response: {content[:80]}...")
            return content.strip()
        except Exception as exc:
            print(f"[{self.provider_name}] Exception: {exc}")
            self._available = False
            return None

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
