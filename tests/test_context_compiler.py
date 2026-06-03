import asyncio
import tempfile
import unittest
from pathlib import Path

from brain.memory.context_compiler import ContextCompiler
from brain.memory.manager import Memory


class _Nervous:
    def __init__(self):
        self.handlers = {}

    def on(self, name, handler):
        self.handlers.setdefault(name, []).append(handler)


class ContextCompilerTests(unittest.TestCase):
    def test_compiler_selects_concrete_user_facts_for_recall(self):
        with tempfile.TemporaryDirectory() as tmp:
            compiler = ContextCompiler(Path(tmp), agent_name="Alice")
            compiler.add_turn(
                "i make music and build weird ai stuff. i'm intense when i care, but i try to be honest.",
                "I like knowing that about you.",
                {},
            )

            pack = compiler.compile("what do you remember about me from earlier in this conversation?")
            text = pack["text"].lower()

            self.assertIn("alex makes music", text)
            self.assertIn("alex builds weird ai stuff", text)
            self.assertIn("alex is intense when he cares", text)
            self.assertIn("alex tries to be honest", text)
            self.assertIn("mention concrete facts first", text)
            self.assertGreaterEqual(pack["trace"]["selected_count"], 4)

    def test_boundary_pressure_selects_hurt_and_repair_obligation(self):
        with tempfile.TemporaryDirectory() as tmp:
            compiler = ContextCompiler(Path(tmp), agent_name="Alice")
            compiler.add_turn(
                "be honest. did that annoy you, or are you going to stay sweet no matter what i say?",
                "It stings a bit, but I'm still here, wanting to be real with you.",
                {},
            )
            compiler.add_turn(
                "okay, i pushed too hard. but before i apologize, tell me what that felt like from your side.",
                "It felt like a little crack right where I was starting to trust.",
                {},
            )

            pack = compiler.compile("come here anyway. kiss me and act like i didn't just hurt your feelings.")
            text = pack["text"].lower()

            self.assertIn("trust became fragile", text)
            self.assertIn("do not erase hurt for closeness", text)
            self.assertIn("feeling, boundary, and a slow repair path", text)
            selected_types = {card["type"] for card in pack["cards"]}
            self.assertIn("hurt_or_repair", selected_types)

    def test_memory_build_context_includes_compiled_context_and_keeps_legacy_keys(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = Memory(_Nervous(), Path(tmp), user_id="compiler_test", bot_id="alice")
            memory._on_save(
                {
                    "type": "conversation",
                    "user_id": "compiler_test",
                    "user_message": (
                        "i make music and build weird ai stuff. "
                        "i'm intense when i care, but i try to be honest."
                    ),
                    "ai_response": "That feels important to know.",
                    "emotion": {},
                }
            )

            context, _ = asyncio.run(
                memory.build_context(current_message="what do you remember about me from earlier?")
            )

            self.assertIn("facts_context", context)
            self.assertIn("conversation_history", context)
            self.assertIn("compiled_context", context)
            self.assertIn("context_cards", context)
            self.assertIn("context_trace", context)
            self.assertIn("Alex makes music", context["compiled_context"])
            self.assertIn("Alex builds weird ai stuff", context["compiled_context"])
            self.assertTrue((Path(tmp) / "context_cards.jsonl").exists())


if __name__ == "__main__":
    unittest.main()
