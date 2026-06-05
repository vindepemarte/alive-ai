import asyncio
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from brain.llm.base import BaseLLM
from brain.llm.factory import canonical_provider_name, create_llm_client
from brain.llm.ollama import OllamaClient
from brain.llm.openai_compatible import OpenAICompatibleClient
from brain.llm.openrouter import OpenRouterClient
from brain.llm.unified import UnifiedLLM
from brain.llm.zai import ZAIClient
from core.settings import ACTIVE_SETTINGS_PATH


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
        lmstudio = OpenAICompatibleClient(
            model="local-model",
            base_url="http://127.0.0.1:1234/v1",
            provider_name="lmstudio",
            local=True,
        ).get_capabilities()

        self.assertEqual(openrouter.provider, "openrouter")
        self.assertTrue(openrouter.requires_api_key)
        self.assertTrue(openrouter.reasoning.supports_exclude_control)

        self.assertEqual(ollama.provider, "ollama")
        self.assertTrue(ollama.local)
        self.assertFalse(ollama.requires_api_key)
        self.assertTrue(ollama.reasoning.supports_disable_control)

        self.assertEqual(zai.provider, "zai")
        self.assertTrue(zai.reasoning.supports_disable_control)

        self.assertEqual(lmstudio.provider, "lmstudio")
        self.assertTrue(lmstudio.local)
        self.assertFalse(lmstudio.requires_api_key)
        self.assertEqual(lmstudio.reasoning.control_style, "none")

    def test_provider_aliases_normalize_for_local_openai_compatible_servers(self):
        self.assertEqual(canonical_provider_name("lm-studio"), "lmstudio")
        self.assertEqual(canonical_provider_name("llama.cpp"), "llamacpp")
        self.assertEqual(canonical_provider_name("openai_compatible"), "openai-compatible")

    def test_factory_reads_openai_compatible_provider_from_settings(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text(
                """{
                  "LMSTUDIO_BASE_URL": "http://127.0.0.1:1234/v1",
                  "LMSTUDIO_MODEL": "gemma-3-local",
                  "LMSTUDIO_LOCAL": true
                }"""
            )
            token = ACTIVE_SETTINGS_PATH.set(settings_path)
            try:
                client = create_llm_client("lm-studio")
            finally:
                ACTIVE_SETTINGS_PATH.reset(token)

        self.assertIsInstance(client, OpenAICompatibleClient)
        self.assertEqual(client.provider_name, "lmstudio")
        self.assertEqual(client.model, "gemma-3-local")
        self.assertEqual(client.base_url, "http://127.0.0.1:1234/v1")
        self.assertTrue(client.get_capabilities().local)

    def test_unified_disabled_mode_returns_tuple_contract(self):
        client = UnifiedLLM(config={"enabled": False, "order": []})

        response, provider = asyncio.run(client.chat_with_provider([{"role": "user", "content": "hey"}]))

        self.assertIsNone(response)
        self.assertEqual(provider, "")

    def test_unified_registers_openai_compatible_presets(self):
        client = UnifiedLLM(
            config={
                "enabled": True,
                "order": ["llama.cpp"],
                "LLAMACPP_BASE_URL": "http://127.0.0.1:8080/v1",
                "LLAMACPP_MODEL": "tiny-local",
            }
        )
        client._initialize_providers()

        self.assertIn("llamacpp", client._providers)
        caps = client._providers["llamacpp"].capabilities
        self.assertEqual(caps.provider, "llamacpp")
        self.assertEqual(caps.model, "tiny-local")
        self.assertTrue(caps.local)

    def test_unified_uses_task_specific_model_settings(self):
        def settings_getter(key, default=None):
            return {
                "OLLAMA_URL": "http://127.0.0.1:11434",
                "OLLAMA_MODEL": "base-model",
                "OLLAMA_MODEL_MAIN": "main-model",
                "OLLAMA_MODEL_FAST": "fast-model",
                "OLLAMA_MODEL_THINKING": "thinking-model",
            }.get(key, default)

        main = UnifiedLLM(config={"enabled": True, "order": ["ollama"]}, settings_getter=settings_getter, task="main")
        fast = UnifiedLLM(config={"enabled": True, "order": ["ollama"]}, settings_getter=settings_getter, task="fast")
        thinking = UnifiedLLM(config={"enabled": True, "order": ["ollama"]}, settings_getter=settings_getter, task="thinking")
        main._initialize_providers()
        fast._initialize_providers()
        thinking._initialize_providers()

        self.assertEqual(main._providers["ollama"].client.model, "main-model")
        self.assertEqual(fast._providers["ollama"].client.model, "fast-model")
        self.assertEqual(thinking._providers["ollama"].client.model, "thinking-model")

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

    def test_zai_exception_path_returns_none_without_name_error(self):
        class FailingSession:
            def post(self, *_args, **_kwargs):
                raise RuntimeError("network down")

        async def run_chat():
            client = ZAIClient("key", "glm-test")

            async def fake_get_session():
                return FailingSession()

            client._get_session = fake_get_session
            return await client.chat([{"role": "user", "content": "hey"}], max_tokens=20)

        self.assertIsNone(asyncio.run(run_chat()))


if __name__ == "__main__":
    unittest.main()
