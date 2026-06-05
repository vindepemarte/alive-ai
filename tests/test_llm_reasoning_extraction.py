import unittest
import asyncio
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from brain.llm.openai_compatible import OpenAICompatibleClient
from brain.llm.openrouter import OpenRouterClient, _extract_openrouter_answer, _has_reasoning_activity, _openrouter_thinking_enabled
from brain.llm.reasoning import has_reasoning_payload, visible_answer_from_message
from core.settings import ACTIVE_SETTINGS_PATH, get_bool
from core.thinking import sanitize_provider_response
from input.telegram.commands import OwnerCommands


class LLMReasoningExtractionTests(unittest.TestCase):
    def test_normal_content_is_answer(self):
        message = {"content": "I'm here with you."}

        self.assertEqual(visible_answer_from_message(message), "I'm here with you.")
        self.assertFalse(has_reasoning_payload(message))

    def test_deepseek_zai_reasoning_content_is_ignored(self):
        message = {
            "reasoning_content": "private reasoning",
            "content": "Just the visible answer.",
        }

        self.assertEqual(visible_answer_from_message(message), "Just the visible answer.")
        self.assertTrue(has_reasoning_payload(message))

    def test_ollama_thinking_field_is_ignored(self):
        message = {
            "thinking": "private thoughts",
            "content": "yeah, I'm awake.",
        }

        self.assertEqual(visible_answer_from_message(message), "yeah, I'm awake.")
        self.assertTrue(has_reasoning_payload(message))

    def test_anthropic_openrouter_blocks_skip_thinking_and_keep_text(self):
        message = {
            "content": [
                {"type": "thinking", "text": "private chain"},
                {"type": "redacted_thinking", "data": "opaque"},
                {"type": "text", "text": "I'm here."},
            ]
        }

        self.assertEqual(visible_answer_from_message(message), "I'm here.")
        self.assertTrue(has_reasoning_payload(message))

    def test_openrouter_answer_extracts_only_message_content(self):
        data = {
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {
                        "role": "assistant",
                        "reasoning": "private",
                        "content": [{"type": "text", "text": "Short answer."}],
                    },
                }
            ],
            "usage": {"completion_tokens_details": {"reasoning_tokens": 12}},
        }

        self.assertEqual(_extract_openrouter_answer(data), "Short answer.")
        self.assertTrue(_has_reasoning_activity(data))

    def test_inline_think_block_is_stripped_from_visible_content(self):
        self.assertEqual(
            sanitize_provider_response("<think>private chain</think>\nFinal answer only."),
            "Final answer only.",
        )

    def test_reasoning_without_answer_returns_empty(self):
        message = {"reasoning": "private chain", "content": None}

        self.assertEqual(visible_answer_from_message(message), "")
        self.assertTrue(has_reasoning_payload(message))

    def test_openrouter_thinking_is_provider_specific_opt_in(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {}, clear=True):
            old_settings_path = Path(tmp) / "old-settings.json"
            old_settings_path.write_text('{"LLM_THINKING_ENABLED": true}')
            token = ACTIVE_SETTINGS_PATH.set(old_settings_path)
            try:
                self.assertFalse(_openrouter_thinking_enabled())
            finally:
                ACTIVE_SETTINGS_PATH.reset(token)

            explicit_settings_path = Path(tmp) / "explicit-settings.json"
            explicit_settings_path.write_text(
                '{"LLM_THINKING_ENABLED": true, "OPENROUTER_THINKING_ENABLED": true}'
            )
            token = ACTIVE_SETTINGS_PATH.set(explicit_settings_path)
            try:
                self.assertTrue(_openrouter_thinking_enabled())
            finally:
                ACTIVE_SETTINGS_PATH.reset(token)

    def test_openrouter_omits_reasoning_control_by_default(self):
        class FakeResponse:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def json(self):
                return {"choices": [{"message": {"content": "I'm here."}}]}

        class FakeSession:
            def __init__(self):
                self.payloads = []

            def post(self, *_args, json=None, **_kwargs):
                self.payloads.append(json)
                return FakeResponse()

        async def run_chat():
            session = FakeSession()
            client = OpenRouterClient("test-key", "openai/test")

            async def fake_get_session():
                return session

            client._get_session = fake_get_session
            result = await client.chat(
                [{"role": "user", "content": "hey"}],
                max_tokens=60,
                temperature=0.7,
            )
            return result, session.payloads

        with tempfile.TemporaryDirectory() as tmp, patch.dict("os.environ", {}, clear=True):
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text('{"LLM_THINKING_ENABLED": true}')
            token = ACTIVE_SETTINGS_PATH.set(settings_path)
            try:
                result, payloads = asyncio.run(run_chat())
            finally:
                ACTIVE_SETTINGS_PATH.reset(token)

        self.assertEqual(result, "I'm here.")
        self.assertEqual(len(payloads), 1)
        self.assertNotIn("reasoning", payloads[0])

    def test_openai_compatible_client_sends_no_provider_reasoning_controls(self):
        class FakeResponse:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def json(self):
                return {"choices": [{"message": {"content": "Visible local answer."}}]}

        class FakeSession:
            def __init__(self):
                self.payloads = []

            def post(self, *_args, json=None, **_kwargs):
                self.payloads.append(dict(json or {}))
                return FakeResponse()

        async def run_chat():
            session = FakeSession()
            client = OpenAICompatibleClient(
                model="local-model",
                base_url="http://127.0.0.1:1234/v1",
                provider_name="lmstudio",
                local=True,
            )

            async def fake_get_session():
                return session

            client._get_session = fake_get_session
            result = await client.chat([{"role": "user", "content": "hey"}], max_tokens=60)
            return result, session.payloads

        result, payloads = asyncio.run(run_chat())

        self.assertEqual(result, "Visible local answer.")
        self.assertEqual(len(payloads), 1)
        self.assertNotIn("reasoning", payloads[0])
        self.assertNotIn("thinking", payloads[0])
        self.assertNotIn("think", payloads[0])

    def test_openrouter_omits_max_tokens_when_uncapped(self):
        class FakeResponse:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def json(self):
                return {"choices": [{"message": {"content": "I'm here."}}]}

        class FakeSession:
            def __init__(self):
                self.payloads = []

            def post(self, *_args, json=None, **_kwargs):
                self.payloads.append(dict(json or {}))
                return FakeResponse()

        async def run_chat():
            session = FakeSession()
            client = OpenRouterClient("test-key", "openai/test")

            async def fake_get_session():
                return session

            client._get_session = fake_get_session
            result = await client.chat([{"role": "user", "content": "hey"}], max_tokens=None)
            return result, session.payloads

        result, payloads = asyncio.run(run_chat())

        self.assertEqual(result, "I'm here.")
        self.assertNotIn("max_tokens", payloads[0])

    def test_openai_compatible_omits_max_tokens_when_uncapped(self):
        class FakeResponse:
            status = 200

            async def __aenter__(self):
                return self

            async def __aexit__(self, *_args):
                return False

            async def json(self):
                return {"choices": [{"message": {"content": "Visible local answer."}}]}

        class FakeSession:
            def __init__(self):
                self.payloads = []

            def post(self, *_args, json=None, **_kwargs):
                self.payloads.append(dict(json or {}))
                return FakeResponse()

        async def run_chat():
            session = FakeSession()
            client = OpenAICompatibleClient(
                model="local-model",
                base_url="http://127.0.0.1:1234/v1",
                provider_name="lmstudio",
                local=True,
            )

            async def fake_get_session():
                return session

            client._get_session = fake_get_session
            result = await client.chat([{"role": "user", "content": "hey"}], max_tokens=None)
            return result, session.payloads

        result, payloads = asyncio.run(run_chat())

        self.assertEqual(result, "Visible local answer.")
        self.assertNotIn("max_tokens", payloads[0])


class _FakeMessage:
    def __init__(self):
        self.replies = []

    async def reply_text(self, text, **_kwargs):
        self.replies.append(text)


class _FakeUpdate:
    def __init__(self):
        self.message = _FakeMessage()


class ThinkingCommandTests(unittest.TestCase):
    def test_thinking_command_updates_hot_reload_setting(self):
        with tempfile.TemporaryDirectory() as tmp:
            settings_path = Path(tmp) / "settings.json"
            settings_path.write_text("{}")
            token = ACTIVE_SETTINGS_PATH.set(settings_path)
            try:
                owner = OwnerCommands(SimpleNamespace(), SimpleNamespace())
                update = _FakeUpdate()

                asyncio.run(owner._cmd_thinking(update, ["false"]))
                self.assertFalse(get_bool("LLM_THINKING_ENABLED", True))
                self.assertFalse(get_bool("OPENROUTER_THINKING_ENABLED", True))
                self.assertIn("OFF", update.message.replies[-1])

                asyncio.run(owner._cmd_thinking(update, ["true"]))
                self.assertTrue(get_bool("LLM_THINKING_ENABLED", False))
                self.assertTrue(get_bool("OPENROUTER_THINKING_ENABLED", False))
                self.assertIn("ON", update.message.replies[-1])
            finally:
                ACTIVE_SETTINGS_PATH.reset(token)


if __name__ == "__main__":
    unittest.main()
