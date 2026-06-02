import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch


_tmp = tempfile.TemporaryDirectory()
os.environ["ALIVE_AI_DATA_PATH"] = _tmp.name
DATA_DIR = Path(_tmp.name)

from core.inner_state import InnerStateCompiler, StateSignal
from core.proactive_arbiter import ProactiveArbiter
from core.reflection import PostResponseReflector
from core.thinking import build_mood_instruction


class InnerStateCompilerTests(unittest.TestCase):
    def test_sleep_pressure_overrides_curiosity_and_flirtiness(self):
        plan = InnerStateCompiler(max_signals=3).compile(
            {
                "mood": "sleepy_neutral",
                "sleepiness": 0.92,
                "desire": 0.7,
                "love": 0.8,
            },
            "tell me something cute",
            [
                StateSignal("curiosity", "knowledge_gap", "ask about music", 0.7, 0.8),
                StateSignal("dreams", "dream_residue", "dreamed about clocks", 0.7, 0.75),
            ],
        )

        self.assertEqual(plan.intent, "sleepy_return")
        self.assertIn("sleepy", plan.style)
        self.assertTrue(any(s.kind == "sleep_pressure" for s in plan.selected_signals))

    def test_direct_question_gets_answer_intent(self):
        plan = InnerStateCompiler(max_signals=3).compile(
            {"mood": "neutral", "love": 0.7},
            "how do you work?",
            [StateSignal("curiosity", "knowledge_gap", "ask about childhood", 0.7, 0.8)],
        )

        self.assertEqual(plan.intent, "answer")
        self.assertIn("Answer the user first", plan.instruction)

    def test_prompt_has_compact_inner_state_briefing(self):
        plan = InnerStateCompiler(max_signals=2).compile(
            {"mood": "neutral"},
            "hi",
            [
                StateSignal("memory", "memory", "remembered one thing", 0.9, 0.9),
                StateSignal("dreams", "dream", "dreamed one thing", 0.8, 0.8),
                StateSignal("curiosity", "question", "ask one thing", 0.2, 0.2),
            ],
        )
        prompt = plan.to_prompt()

        self.assertIn("INNER STATE BRIEFING", prompt)
        self.assertEqual(len(plan.selected_signals), 2)
        self.assertIn("Behavior contract", prompt)

    def test_mood_instruction_can_disable_random_humanizer(self):
        with patch("core.thinking.random.choice", return_value="NO emoji in this message. Just raw text."):
            prompt = build_mood_instruction({"mood": "neutral"}, "hi", include_humanizer=False)

        self.assertNotIn("[Humanize:", prompt)


class ProactiveArbiterTests(unittest.TestCase):
    def setUp(self):
        self.audit_path = DATA_DIR / "proactive_test.jsonl"
        if self.audit_path.exists():
            self.audit_path.unlink()

    def test_contextual_only_blocks_anchorless_messages(self):
        arbiter = ProactiveArbiter(self.audit_path)

        decision = arbiter.decide("u1", "random", anchor="", silence_minutes=180)

        self.assertFalse(decision.accepted)
        self.assertEqual(decision.rejection_reason, "missing_contextual_anchor")
        self.assertTrue(self.audit_path.exists())

    def test_lonely_affectionate_contextual_message_can_pass(self):
        arbiter = ProactiveArbiter(self.audit_path)
        now = datetime(2026, 6, 2, 15, 0)

        decision = arbiter.decide(
            "u1",
            "silence",
            anchor="5.0 hours of silence and a remembered goodnight ritual",
            emotion={"love": 0.9, "sadness": 0.5},
            silence_minutes=300,
            now=now,
        )

        self.assertTrue(decision.accepted)
        self.assertGreaterEqual(decision.score, 0.48)

    def test_sleep_blocks_unscheduled_proactive(self):
        arbiter = ProactiveArbiter(self.audit_path)

        decision = arbiter.decide(
            "u1",
            "silence",
            anchor="missed conversation",
            circadian={"sleeping": True},
            silence_minutes=300,
        )

        self.assertFalse(decision.accepted)
        self.assertEqual(decision.rejection_reason, "sleeping")

    def test_same_reason_cooldown_blocks_repeat(self):
        arbiter = ProactiveArbiter(self.audit_path)
        now = datetime(2026, 6, 2, 15, 0)
        first = arbiter.decide(
            "u1",
            "silence",
            anchor="5 hours silent",
            emotion={"love": 0.9},
            silence_minutes=300,
            now=now,
        )
        second = arbiter.decide(
            "u1",
            "silence",
            anchor="still silent",
            emotion={"love": 0.9},
            silence_minutes=330,
            now=now + timedelta(minutes=40),
        )

        self.assertTrue(first.accepted)
        self.assertFalse(second.accepted)
        self.assertEqual(second.rejection_reason, "same_reason_cooldown")


class ReflectionTests(unittest.TestCase):
    def setUp(self):
        for path in DATA_DIR.glob("**/*.json"):
            path.unlink()
        for path in DATA_DIR.glob("**/*.jsonl"):
            path.unlink()

    def test_reflection_writes_journal_and_autobiography(self):
        reflector = PostResponseReflector(DATA_DIR)

        record = reflector.reflect(
            "u1",
            "i had a dream about us",
            "that dream stayed with me too. what did it feel like?",
            {"mood": "loving", "love": 0.8},
            [],
        )

        self.assertTrue(record.memory_worthy)
        self.assertTrue((DATA_DIR / "autobiography.json").exists())
        self.assertTrue((DATA_DIR / "users" / "u1" / "reflection_journal.jsonl").exists())
        self.assertTrue((DATA_DIR / "users" / "u1" / "relationship_autobiography.json").exists())


if __name__ == "__main__":
    unittest.main()
