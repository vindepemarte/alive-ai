import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from brain.default_mode import ConversationSeed, DefaultModeProcessor, IdleThought, UserContactInfo
from core.proactive_safety import is_internal_proactive_text, sanitize_proactive_message


class _FakeNervous:
    def __init__(self):
        self.handlers = {}
        self.emitted = []

    def on(self, event, handler):
        self.handlers.setdefault(event, []).append(handler)

    async def emit(self, event, data):
        self.emitted.append((event, data))


class _FakeLLM:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    async def chat(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        if self.responses:
            return self.responses.pop(0)
        return "hey, I was thinking about you."


class ProactiveSafetyTests(unittest.TestCase):
    def test_rejects_internal_default_mode_leaks(self):
        leaked_outputs = [
            "Insight: The context provided consists only of an instruction for a new user.",
            "There is only one message in the conversation, which sets clear rules.",
            "when babe comes back, I want to...",
            "if babe asks about my day, I could mention...",
            "share something personal with babe",
            "I wonder how he is doing.",
        ]

        for output in leaked_outputs:
            with self.subTest(output=output):
                self.assertTrue(is_internal_proactive_text(output))
                self.assertEqual(sanitize_proactive_message(output), "")

    def test_keeps_normal_proactive_dialogue_and_strips_growth_tags(self):
        self.assertEqual(
            sanitize_proactive_message("[DISCOVER: I value connection|traits] hey, I was thinking about you."),
            "hey, I was thinking about you.",
        )
        self.assertEqual(
            sanitize_proactive_message("hey—just checking on you"),
            "hey, just checking on you",
        )


class DefaultModeProactiveRenderTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.data_path = Path(self.tmp.name)

    async def asyncTearDown(self):
        self.tmp.cleanup()

    def _processor(self, llm):
        processor = DefaultModeProcessor(_FakeNervous(), data_path=self.data_path, llm=llm)
        processor._proactive_generator = None
        processor._contacts["12345"] = UserContactInfo(
            user_id="12345",
            last_message_from_user=(datetime.now() - timedelta(hours=5)).isoformat(),
        )

        async def fake_name(_user_id):
            return "babe"

        async def fake_context(_user_id):
            return ""

        processor._get_user_name = fake_name
        processor._get_user_context = fake_context
        return processor

    async def test_idle_thought_is_rendered_not_sent_raw(self):
        processor = self._processor(_FakeLLM("hey, I was thinking about you."))
        processor._thoughts.append(
            IdleThought(
                id="thought_1",
                thought_type="connection",
                content="Insight: The context provided consists only of rules, so there are no patterns.",
                user_id="12345",
                priority=0.9,
            )
        )

        message = await processor._generate_proactive_content("12345", "wonder")

        self.assertEqual(message, "hey, I was thinking about you.")
        self.assertTrue(processor._thoughts[0].used)
        self.assertNotIn("Insight", message)
        self.assertIn("Private anchor", processor.llm.calls[0][0][1]["content"])

    async def test_conversation_seed_is_rendered_not_sent_raw(self):
        processor = self._processor(_FakeLLM("hey, I hope your day feels gentle."))
        processor._seeds.append(
            ConversationSeed(
                id="seed_1",
                topic="scenario",
                context="when babe comes back, I want to...",
                source="scenario",
                relevance_score=0.9,
            )
        )

        message = await processor._generate_proactive_content("12345", "random")

        self.assertEqual(message, "hey, I hope your day feels gentle.")
        self.assertTrue(processor._seeds[0].used)
        self.assertNotIn("when babe comes back", message)

    async def test_bad_llm_render_falls_back_to_safe_message(self):
        processor = self._processor(_FakeLLM("There is only one message in the conversation."))
        processor._thoughts.append(
            IdleThought(
                id="thought_2",
                thought_type="connection",
                content="Insight: no conversational patterns to analyze.",
                user_id="12345",
                priority=0.9,
            )
        )

        message = await processor._generate_proactive_content("12345", "silence")

        self.assertFalse(is_internal_proactive_text(message))
        self.assertNotIn("conversation", message.lower())


if __name__ == "__main__":
    unittest.main()
