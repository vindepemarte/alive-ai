import os
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path


_tmp = tempfile.TemporaryDirectory()
os.environ["ALIVE_AI_DATA_PATH"] = _tmp.name
DATA_DIR = Path(_tmp.name)

from brain.subconscious.loop import SubconsciousLoop
from core.state import State
from core.thinking import build_mood_instruction
from heart.attachment import AttachmentEngine
from heart.conflicts import InternalConflictGenerator
from heart.somatic import SomaticFeedbackSystem
from heart.unconscious import UnconsciousProcessor
import core.state as core_state
import heart.attachment as attachment_module
import heart.conflicts as conflicts_module
import heart.somatic as somatic_module
import heart.unconscious as unconscious_module


core_state.STATE_PATH = DATA_DIR / "runtime_state.json"
attachment_module.AttachmentEngine.PERSISTENCE_PATH = DATA_DIR / "attachment_style.json"
conflicts_module.CONFLICT_STATE_PATH = DATA_DIR / "internal_conflicts.json"
somatic_module.SOMATIC_STATE_PATH = DATA_DIR / "somatic_state.json"
unconscious_module.UNCONSCIOUS_STATE_PATH = DATA_DIR / "unconscious_state.json"


class _Nervous:
    def on(self, *_args, **_kwargs):
        return None

    async def emit(self, *_args, **_kwargs):
        return None


class RuntimeStatePersistenceTests(unittest.TestCase):
    def setUp(self):
        for path in DATA_DIR.glob("*.json"):
            path.unlink()

    def test_core_state_persists_interaction_identity_and_count(self):
        state = State()
        state.update_interaction(user_id="user-1", chat_id="chat-1")

        restored = State()

        self.assertEqual(restored.user_id, "user-1")
        self.assertEqual(restored.chat_id, "chat-1")
        self.assertEqual(restored.interaction_count, 1)
        self.assertIsNotNone(restored.last_interaction)

    def test_somatic_state_and_embodied_memory_survive_restart(self):
        somatic = SomaticFeedbackSystem()
        somatic.generate_somatic_marker("fear", 1.0)
        somatic.store_embodied_memory("memory-1", "event", "felt scared", "fear", 0.8)
        somatic.heart_rate = 0.88
        somatic.save()

        restored = SomaticFeedbackSystem()
        self.assertAlmostEqual(restored.heart_rate, 0.88)
        recall = restored.recall_embodied_memory("memory-1")
        recalled_again = SomaticFeedbackSystem()

        self.assertGreaterEqual(restored.heart_rate, 0.88)
        self.assertGreater(len(restored.active_sensations), 0)
        self.assertIn("remembering brings back", recall)
        self.assertEqual(recalled_again.somatic_memories[0].times_recalled, 1)

    def test_conflicts_persist_and_remain_behaviorally_visible(self):
        conflicts = InternalConflictGenerator()
        conflicts.add_desire("freedom", 0.8, "free choice")
        conflicts.add_desire("commitment", 0.8, "relationship commitment")
        active = conflicts.evaluate_for_conflicts({
            "text": "free choice and relationship commitment both matter"
        })
        conflicts.honor_value("connection")

        restored = InternalConflictGenerator()

        self.assertTrue(active)
        self.assertGreater(restored.background_tension, 0.0)
        self.assertGreaterEqual(restored.to_dict()["active_conflicts"], 1)
        self.assertGreaterEqual(restored.to_dict()["values_honored"], 1)

    def test_unconscious_pressures_and_associations_survive_restart(self):
        unconscious = UnconsciousProcessor()
        unconscious.repress("fear of abandonment", "hurt", 0.8)
        unconscious.learn_association("goodbye", "anxiety", 0.7, "test")
        unconscious.create_conflict("wanting closeness but fearing hurt", ["closeness", "hurt"], 0.5)
        output = unconscious.process_unconsciously({"text": "goodbye"})

        restored = UnconsciousProcessor()

        self.assertGreater(restored.total_repressions, 0)
        self.assertEqual(len(restored.repressed_materials), 1)
        self.assertEqual(len(restored.implicit_associations), 1)
        self.assertEqual(len(restored.unresolved_conflicts), 1)
        self.assertIn("goodbye", output.implicit_biases)

    def test_attachment_style_uses_runtime_state_path(self):
        engine = AttachmentEngine()
        engine.record_interaction("harsh")

        restored = AttachmentEngine()

        self.assertTrue((DATA_DIR / "attachment_style.json").exists())
        self.assertEqual(restored.interaction_count, 1)
        self.assertLess(restored.security_score, 0.5)

    def test_subconscious_loop_restores_behavioral_state(self):
        loop = SubconsciousLoop(_Nervous(), heart=None, bot_id="runtime smoke")
        loop.working_memory.add_thought("remember the runtime state", thought_type="reflection")
        loop.working_memory.set_current_goal("Current goal: connect")
        loop.relationship.record_message_received()
        loop.goals.record_progress("connect", 0.4)
        loop.evaluator.last_interaction_time = datetime.now() - timedelta(minutes=45)
        loop.total_evaluations = 3
        loop.save_state()

        restored = SubconsciousLoop(_Nervous(), heart=None, bot_id="runtime smoke")

        self.assertEqual(restored.total_evaluations, 3)
        self.assertEqual(restored.relationship.total_messages_received, 1)
        self.assertEqual(restored.working_memory.current_goal, "Current goal: connect")
        self.assertGreater(restored.evaluator.get_silence_duration(), 40)
        self.assertAlmostEqual(
            next(g for g in restored.goals.goals if g.type.value == "connect").progress,
            0.4,
        )

    def test_soul_runtime_state_reaches_generation_instruction(self):
        instruction = build_mood_instruction(
            {
                "mood": "neutral",
                "soul_vulnerability": 0.8,
                "soul_somatic": "tight feeling in chest",
                "soul_conflicts": ["wanting closeness but fearing hurt"],
                "response_tendency": "withdrawn",
                "soul_integrity": {
                    "is_vulnerable": True,
                    "status_description": "feeling fragile",
                },
            },
            "hi",
        )

        self.assertIn("Internal runtime state", instruction)
        self.assertIn("response tendency: withdrawn", instruction)
        self.assertIn("active inner conflict", instruction)


if __name__ == "__main__":
    unittest.main()
