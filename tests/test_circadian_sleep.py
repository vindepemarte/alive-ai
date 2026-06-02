import asyncio
import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path


_tmp = tempfile.TemporaryDirectory()
os.environ["ALIVE_AI_DATA_PATH"] = _tmp.name
DATA_DIR = Path(_tmp.name)

import brain.dreams as dreams_module
import heart.circadian as circadian_module
from brain.default_mode import DefaultModeProcessor, UserContactInfo
from brain.dreams import DreamSystem
from brain.subconscious.loop import SubconsciousLoop
from heart.circadian import CircadianEngine
from heart.core import Heart


class _Clock:
    def __init__(self, now: datetime):
        self.value = now

    def __call__(self) -> datetime:
        return self.value

    def advance(self, **kwargs):
        self.value = self.value + timedelta(**kwargs)


class _Dreams:
    def __init__(self):
        self.calls = []
        self.last = "dreamed about a quiet room"

    def generate_dream(self, **kwargs):
        self.calls.append(kwargs)
        return self.last

    def get_morning_dream_message(self):
        return "had the weirdest dream last night... " + self.last


class _Nervous:
    def __init__(self):
        self.events = []

    def on(self, *_args, **_kwargs):
        return None

    async def emit(self, event, data=None):
        self.events.append((event, data or {}))


class _Config:
    personality = {}


class CircadianSleepTests(unittest.TestCase):
    def setUp(self):
        circadian_module._instance = None
        dreams_module._instance = None
        dreams_module.DATA_PATH = DATA_DIR
        dreams_module.DREAMS_FILE = DATA_DIR / "dreams.json"
        for path in DATA_DIR.glob("*.json"):
            path.unlink()

    def test_predawn_auto_sleep_persists_and_generates_cycle_dream(self):
        clock = _Clock(datetime(2026, 6, 2, 3, 15))
        fake_dreams = _Dreams()
        path = DATA_DIR / "circadian_state.json"

        engine = CircadianEngine(
            persistence_path=path,
            dream_system=fake_dreams,
            clock=clock,
            auto_update=True,
        )

        self.assertTrue(engine.is_asleep)
        self.assertTrue(path.exists())
        self.assertEqual(engine.last_transition_reason, "circadian_pressure")
        self.assertEqual(fake_dreams.calls[0]["sleep_cycle_id"], engine.sleep_cycle_id)
        self.assertEqual(engine.get_state_summary()["modifiers"]["energy"], 0.05)

    def test_sleep_tick_wakes_and_recovers_debt_after_morning_window(self):
        clock = _Clock(datetime(2026, 6, 2, 3, 30))
        engine = CircadianEngine(
            persistence_path=DATA_DIR / "circadian_state.json",
            dream_system=_Dreams(),
            clock=clock,
            auto_update=True,
        )
        starting_debt = engine.sleep_debt

        clock.value = datetime(2026, 6, 2, 10, 0)
        engine.tick()

        self.assertFalse(engine.is_asleep)
        self.assertEqual(engine.last_transition_reason, "circadian_recovery")
        self.assertLess(engine.sleep_debt, starting_debt)
        self.assertIsNotNone(engine.wake_time)

    def test_user_message_wakes_sleep_and_marks_interruption(self):
        clock = _Clock(datetime(2026, 6, 2, 4, 0))
        engine = CircadianEngine(
            persistence_path=DATA_DIR / "circadian_state.json",
            dream_system=_Dreams(),
            clock=clock,
            auto_update=False,
        )
        engine.fall_asleep(reason="test")
        clock.advance(minutes=20)

        state = engine.handle_user_interaction()

        self.assertTrue(state["woke_from_sleep"])
        self.assertFalse(state["sleeping"])
        self.assertGreater(engine.sleep_debt, 0)
        self.assertIn("dream", engine.last_wake_dream_message)

    def test_deep_night_forced_awake_is_short_and_sleep_pressure_wins(self):
        clock = _Clock(datetime(2026, 6, 2, 2, 30))
        engine = CircadianEngine(
            persistence_path=DATA_DIR / "circadian_state.json",
            dream_system=_Dreams(),
            clock=clock,
            auto_update=False,
        )
        engine.sleep_debt = 5.6

        engine.handle_user_interaction()
        until = datetime.fromisoformat(engine.forced_awake_until)
        self.assertLessEqual((until - clock.value).total_seconds() / 60, 10)

        engine.tick()
        self.assertTrue(engine.is_asleep)
        self.assertEqual(engine.last_transition_reason, "circadian_pressure")

    def test_dream_schema_is_cycle_idempotent_and_runtime_readable(self):
        system = DreamSystem()
        dream = system.generate_dream(
            memories=["we talked about resting after work"],
            emotions=["soft"],
            sleep_cycle_id="cycle-1",
        )

        self.assertIsNotNone(dream)
        self.assertIsNone(system.generate_dream(sleep_cycle_id="cycle-1"))
        summary = system.get_state_summary()
        self.assertEqual(summary["last_dream"], dream)
        self.assertEqual(summary["last_sleep_cycle_id"], "cycle-1")

        restored = DreamSystem()
        self.assertEqual(restored.get_recent_dream(max_age_hours=1), dream)

    def test_subconscious_does_not_act_outward_while_asleep(self):
        engine = CircadianEngine(
            persistence_path=DATA_DIR / "circadian_state.json",
            dream_system=_Dreams(),
            clock=_Clock(datetime(2026, 6, 2, 4, 0)),
            auto_update=False,
        )
        engine.fall_asleep(reason="test")
        circadian_module._instance = engine
        nervous = _Nervous()
        loop = SubconsciousLoop(nervous, heart=None, bot_id="circadian-test")

        self.assertFalse(loop._can_act())
        asyncio.run(loop._evaluate())

        self.assertTrue(any(event == "subconscious_rest" for event, _ in nervous.events))
        self.assertTrue(loop.working_memory.get_recent_thoughts(1))

    def test_default_mode_rests_instead_of_creating_proactive_messages_while_asleep(self):
        engine = CircadianEngine(
            persistence_path=DATA_DIR / "circadian_state.json",
            dream_system=_Dreams(),
            clock=_Clock(datetime(2026, 6, 2, 4, 0)),
            auto_update=False,
        )
        engine.fall_asleep(reason="test")
        circadian_module._instance = engine
        DreamSystem().generate_dream(sleep_cycle_id=engine.sleep_cycle_id, force=True)
        nervous = _Nervous()
        processor = DefaultModeProcessor(nervous, data_path=DATA_DIR, llm=None)
        processor._contacts["12345"] = UserContactInfo(user_id="12345")

        asyncio.run(processor.process_idle())

        emitted = [event for event, _ in nervous.events]
        self.assertIn("default_mode_processed", emitted)
        self.assertNotIn("proactive_message_ready", emitted)
        self.assertTrue(any(t.thought_type == "dream" for t in processor.get_recent_thoughts()))

    def test_heart_state_reflects_sleep_and_suppresses_reactions(self):
        engine = CircadianEngine(
            persistence_path=DATA_DIR / "circadian_state.json",
            dream_system=_Dreams(),
            clock=_Clock(datetime(2026, 6, 2, 4, 0)),
            auto_update=False,
        )
        engine.fall_asleep(reason="test")
        circadian_module._instance = engine
        heart = Heart(_Nervous(), _Config())
        heart.emotion.arousal = 0.8
        heart.emotion.desire = 0.6

        heart._apply_circadian_to_emotion()
        state = heart.get_state()

        self.assertTrue(state["is_asleep"])
        self.assertEqual(state["mood"], "asleep")
        self.assertLess(heart.emotion.arousal, 0.8)
        self.assertIsNone(heart.get_reaction("lol"))


if __name__ == "__main__":
    unittest.main()
