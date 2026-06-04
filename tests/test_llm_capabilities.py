import asyncio
import unittest
from unittest.mock import patch

from brain.llm.base import BaseLLM
from brain.llm.ollama import OllamaClient
from brain.llm.openrouter import OpenRouterClient
from brain.llm.unified import UnifiedLLM
from brain.llm.zai import ZAIClient


class _FakeLLM(BaseLLM):
    async def chat(self, *_args, **_kwargs):
        return "hello"

    async def close(self):
        return None


class LLMCapabilitiesTests(unittest.TestCase):
    def test_base_chat_result_preserves_legacy_chat_contract(self):
        client = _FakeLLM("", "fake-model")
        result = asyncio.run(client.chat_result([{"role": "user", "content": "hey"}]))

        self.assertEqual(result.content, "hello")
        self.assertEqual(result.model, "fake-model")

    def test_provider_capability_defaults(self):
        openrouter = OpenRouterClient("key", "openai/gpt-4.1-mini").get_capabilities()
        ollama = OllamaClient("", "gemma4:e2b").get_capabilities()
        zai = ZAIClient("key", "glm-4.6v").get_capabilities()

        self.assertEqual(openrouter.provider, "openrouter")
        self.assertTrue(openrouter.requires_api_key)
        self.assertTrue(openrouter.reasoning.supports_exclude_control)

        self.assertEqual(ollama.provider, "ollama")
        self.assertTrue(ollama.local)
        self.assertFalse(ollama.requires_api_key)
        self.assertTrue(ollama.reasoning.supports_disable_control)

        self.assertEqual(zai.provider, "zai")
        self.assertTrue(zai.reasoning.supports_disable_control)

    def test_unified_disabled_mode_returns_tuple_contract(self):
        client = UnifiedLLM(config={"enabled": False, "order": []})

        response, provider = asyncio.run(client.chat_with_provider([{"role": "user", "content": "hey"}]))

        self.assertIsNone(response)
        self.assertEqual(provider, "")

    def test_zai_empty_answer_retry_survives_thinking_control_rejection(self):
        class FakeResponse:
            def __init__(self, status, body):
                self.status = status
                self.body = body

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def text(self):
                return str(self.body)

            async def json(self):
                return self.body

        class FakeSession:
            def __init__(self):
                self.payloads = []
                self.responses = [
                    FakeResponse(200, {"choices": [{"message": {"content": ""}}]}),
                    FakeResponse(422, "unsupported thinking"),
                    FakeResponse(200, {"choices": [{"message": {"content": "Visible answer."}}]}),
                ]

            def post(self, *_args, json=None, **_kwargs):
                self.payloads.append(dict(json or {}))
                return self.responses.pop(0)

        async def run_chat():
            session = FakeSession()
            client = ZAIClient("key", "glm-test")

            async def fake_get_session():
                return session

            client._get_session = fake_get_session
            result = await client.chat([{"role": "user", "content": "hey"}], max_tokens=20)
            return result, session.payloads

        with patch.dict("os.environ", {"LLM_THINKING_ENABLED": "true"}):
            result, payloads = asyncio.run(run_chat())

        self.assertEqual(result, "Visible answer.")
        self.assertNotIn("thinking", payloads[0])
        self.assertIn("thinking", payloads[1])
        self.assertNotIn("thinking", payloads[2])


if __name__ == "__main__":
    unittest.main()
