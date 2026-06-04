"""
Brain: LLM - Base Client
Abstract base class for LLM providers
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict

from .capabilities import ChatResult, ModelCapabilities


class BaseLLM(ABC):
    """Abstract base class for LLM clients"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    def get_capabilities(self) -> ModelCapabilities:
        """Return descriptive model/provider capabilities."""
        return ModelCapabilities(
            provider=self.__class__.__name__.replace("Client", "").lower() or "unknown",
            model=self.model,
        )

    async def refresh_capabilities(self) -> ModelCapabilities:
        """Refresh capability metadata if the provider supports discovery."""
        return self.get_capabilities()

    async def chat_result(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.85
    ) -> ChatResult:
        """Opt-in richer response wrapper. Legacy callers should keep using chat()."""
        content = await self.chat(messages, max_tokens=max_tokens, temperature=temperature)
        caps = self.get_capabilities()
        return ChatResult(
            content=content,
            provider=caps.provider,
            model=caps.model,
            capabilities=caps,
        )

    @abstractmethod
    async def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = 500,
        temperature: float = 0.85
    ) -> Optional[str]:
        """Send chat completion request"""
        pass

    @abstractmethod
    async def close(self):
        """Close the client session"""
        pass

    def __repr__(self):
        return f"<{self.__class__.__name__} model={self.model}>"
