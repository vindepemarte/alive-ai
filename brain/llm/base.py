"""
Brain: LLM - Base Client
Abstract base class for LLM providers
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict


class BaseLLM(ABC):
    """Abstract base class for LLM clients"""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

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
