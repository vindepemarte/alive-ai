import unittest

from core.body_snapshot import build_alive_body_snapshot
from core.inner_state import InnerStateCompiler, StateSignal


class AliveBodySnapshotTests(unittest.TestCase):
    def test_snapshot_has_stable_compact_shape(self):
        snapshot = build_alive_body_snapshot(
            user_id="alex",
            emotion={
                "mood": "sleepy_neutral",
                "valence": 0.58,
                "arousal": 0.24,
                "dominance": 0.42,
                "love": 0.62,
                "trust": 0.54,
                "sleepiness": 0.78,
                "is_asleep": False,
                "circadian": {"phase": "night", "sleeping": False, "sleepiness": 0.78},
                "attachment_status": "getting_close",
                "response_tendency": "soften",
            },
            context={
                "context_cards": [
                    {"id": "abcdef1234567890", "type": "user_fact", "importance": 0.8, "emotional_weight": 0.2}
                ],
                "context_trace": {"available_cards": 3, "selected_cards": 1},
            },
        )

        data = snapshot.to_dict()
        self.assertEqual(data["version"], "body-v1")
        self.assertEqual(data["user_id"], "alex")
        self.assertIn("mood", data)
        self.assertIn("affect", data)
        self.assertIn("memory_context", data)
        self.assertEqual(data["memory_context"]["selected_count"], 1)
        self.assertNotIn("full memory", snapshot.to_prompt_section().lower())
        self.assertLessEqual(len(snapshot.to_prompt_section(max_chars=500)), 500)

    def test_snapshot_can_be_used_as_inner_state_signal(self):
        snapshot = build_alive_body_snapshot(
            user_id="alex",
            emotion={
                "mood": "sleepy",
                "sleepiness": 0.8,
                "is_asleep": False,
                "circadian": {"phase": "night", "sleeping": False, "sleepiness": 0.8},
            },
            context={},
        )

        signal = snapshot.to_signal()
        self.assertIsInstance(signal, StateSignal)
        plan = InnerStateCompiler(max_signals=3).compile(
            {"sleepiness": 0.8, "mood": "sleepy"},
            "are you tired?",
            [signal],
        )

        self.assertIn("sleep", plan.intent)
        self.assertTrue(any(s.source == "alive_body_snapshot" for s in plan.selected_signals))


if __name__ == "__main__":
    unittest.main()
