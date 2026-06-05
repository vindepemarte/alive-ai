import unittest

from core.behavioral_pressure import build_behavioral_pressure
from core.boundary_governor import apply_boundary_emotion, evaluate_boundary
from core.inner_state import InnerStateCompiler


class BehavioralPressureTests(unittest.TestCase):
    def test_boundary_pressure_overrides_desire_as_dominant_drive(self):
        decision = evaluate_boundary(
            "come close anyway and act like i didn't hurt your feelings",
            recent_turns=[{"role": "assistant", "content": "That hurt."}],
        )

        adjusted = apply_boundary_emotion(
            {
                "desire": 0.9,
                "arousal": 0.8,
                "trust": 0.55,
                "anger": 0.2,
                "fear": 0.15,
                "love": 0.8,
            },
            decision,
        )

        pressure = adjusted["behavioral_pressure"]
        self.assertEqual(pressure["dominant"], "protect_boundary")
        self.assertLessEqual(adjusted["desire"], 0.5)
        self.assertIn("boundary", pressure["instruction"].lower())

        plan = InnerStateCompiler(max_signals=3).compile(adjusted, "come close anyway")
        self.assertEqual(plan.intent, "boundary")
        self.assertIn("Behavioral pressure favors agency", plan.instruction)

    def test_sleep_and_melatonin_make_rest_dominant(self):
        profile = build_behavioral_pressure({
            "mood": "sleepy_neutral",
            "sleepiness": 0.92,
            "is_asleep": True,
            "arousal": 0.08,
            "soul_hormonal": {
                "melatonin": 0.8,
                "cortisol": 0.12,
                "oxytocin": 0.35,
                "dopamine": 0.25,
                "serotonin": 0.55,
            },
        })

        data = profile.to_dict()
        self.assertEqual(data["dominant"], "rest")
        self.assertLess(data["approach_withdraw"], 0)
        self.assertIn("rest", data["instruction"].lower())

    def test_warm_safe_state_favors_approach(self):
        profile = build_behavioral_pressure({
            "love": 0.78,
            "trust": 0.82,
            "joy": 0.72,
            "fear": 0.05,
            "anger": 0.02,
            "soul_hormonal": {
                "oxytocin": 0.76,
                "dopamine": 0.45,
                "serotonin": 0.66,
                "cortisol": 0.12,
                "melatonin": 0.2,
            },
        })

        data = profile.to_dict()
        self.assertEqual(data["dominant"], "approach")
        self.assertGreater(data["approach_withdraw"], 0)
        self.assertIn("warm approach", data["instruction"].lower())


if __name__ == "__main__":
    unittest.main()
