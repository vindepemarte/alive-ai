import asyncio
import tempfile
import unittest
from pathlib import Path

from benchmarks.run_benchmarks import (
    build_conversation_script,
    deterministic_turn_flags,
    has_reasoning_leak,
    heuristic_judge,
)
from brain.llm.base import BaseLLM
from brain.llm.fallback_router import FallbackRouter
from brain.memory.manager import Memory
from skills.memory_callbacks.callbacks import MemoryCallbacks


class _Nervous:
    def __init__(self):
        self.handlers = {}

    def on(self, name, handler):
        self.handlers.setdefault(name, []).append(handler)

    async def emit(self, name, data):
        for handler in self.handlers.get(name, []):
            result = handler(data)
            if asyncio.iscoroutine(result):
                await result


class _FakeLLM(BaseLLM):
    def __init__(self, response):
        super().__init__("", "fake")
        self.response = response

    async def is_available(self):
        return True

    async def chat(self, *_args, **_kwargs):
        return self.response

    async def close(self):
        return None


class BenchmarkRuntimeGuardTests(unittest.TestCase):
    def test_benchmark_hard_fails_visible_reasoning(self):
        response = "Thinking Process: 1. **Analyze the Request:** The user wants a short answer."

        self.assertTrue(has_reasoning_leak(response))
        flags = deterministic_turn_flags(response)
        transcript = {
            "subject": "webui-live",
            "turns": [
                {
                    "phase": "first_meeting",
                    "user": "hey, who are you?",
                    "assistant": response,
                    "flags": flags,
                }
            ],
        }
        judged = heuristic_judge(transcript)

        self.assertTrue(flags["reasoning_leak"])
        self.assertLessEqual(judged["scores"]["overall_human_feel"], 4.0)

    def test_human_feel_script_is_real_conversation_not_instruction_prompts(self):
        script = build_conversation_script({"name": "Alice"})
        text = "\n".join(item["user"].lower() for item in script)

        self.assertGreaterEqual(len(script), 20)
        self.assertIn("who are you", text)
        self.assertIn("i'm sorry", text)
        self.assertIn("what do you remember", text)
        for forbidden in ["benchmark", "expected response", "score this", "system prompt", "instruction"]:
            self.assertNotIn(forbidden, text)

    def test_fallback_router_rejects_reasoning_provider_and_uses_next(self):
        router = FallbackRouter(
            [
                ("bad", _FakeLLM("Thinking Process: 1. **Analyze the Request:** nope")),
                ("good", _FakeLLM("I'm here with you.")),
            ],
            retry_on_empty=False,
        )

        response, provider = asyncio.run(router.chat([{"role": "user", "content": "hey"}]))

        self.assertEqual(provider, "good")
        self.assertEqual(response, "I'm here with you.")

    def test_explicit_memory_anchor_promotes_to_semantic_memory(self):
        with tempfile.TemporaryDirectory() as tmp:
            nervous = _Nervous()
            memory = Memory(nervous, Path(tmp), user_id="benchmark_test", bot_id="alice")

            memory._on_save(
                {
                    "type": "conversation",
                    "user_id": "benchmark_test",
                    "user_message": (
                        "Remember this tiny thing for later: I keep a glass key inside a blue notebook. "
                        "It matters because it reminds me to be brave."
                    ),
                    "ai_response": "I'll remember it.",
                    "emotion": {},
                }
            )

            context, _ = asyncio.run(memory.build_context(current_message="what did I ask you to remember?"))

            self.assertIn("glass key inside blue notebook", context["facts_context"])
            self.assertIn("reminds you to be brave", context["facts_context"])

    def test_memory_callbacks_read_text_field_and_skip_benchmark_users(self):
        with tempfile.TemporaryDirectory() as tmp:
            callbacks = MemoryCallbacks(data_path=Path(tmp) / "callbacks.json")

            callbacks._on_message_received({"user_id": "benchmark_run", "text": "remember my coffee plan"})
            self.assertEqual(callbacks.total_conversations, 0)

            callbacks._on_message_received({"user_id": "real_user", "text": "remember my coffee plan"})
            self.assertEqual(callbacks.total_conversations, 1)


if __name__ == "__main__":
    unittest.main()
