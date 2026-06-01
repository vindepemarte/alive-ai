import unittest
from unittest.mock import patch

from brain.subconscious.impulses import ImpulseType
from brain.subconscious.impulse_generator import ImpulseGenerator
from core.thinking import build_mood_instruction
from heart.hormonal import HormonalModulationMatrix
from heart.somatic import SomaticFeedbackSystem


class HormonalRuntimeTests(unittest.TestCase):
    def _matrix(self, **levels):
        matrix = HormonalModulationMatrix()
        matrix.oxytocin = levels.get("oxytocin", matrix.BASELINE_OXYTOCIN)
        matrix.dopamine = levels.get("dopamine", matrix.BASELINE_DOPAMINE)
        matrix.serotonin = levels.get("serotonin", matrix.BASELINE_SEROTONIN)
        matrix.cortisol = levels.get("cortisol", matrix.BASELINE_CORTISOL)
        matrix.melatonin = levels.get("melatonin", matrix.BASELINE_MELATONIN)
        matrix.clear_metabolites()
        return matrix

    def test_stress_hormones_drive_emotion_body_and_prompt_effects(self):
        matrix = self._matrix(cortisol=0.9, serotonin=0.25, dopamine=0.25)

        emotion = matrix.get_emotion_effects()
        somatic = matrix.get_somatic_effects()
        interoceptive = matrix.get_interoceptive_effects()
        guidance = " ".join(matrix.get_prompt_guidance())

        self.assertLess(emotion["valence"], 0)
        self.assertGreater(emotion["fear"], 0)
        self.assertGreater(emotion["arousal"], 0)
        self.assertGreater(somatic["heart_rate"], 0)
        self.assertGreater(somatic["muscle_tension"], 0)
        self.assertGreater(interoceptive["cognitive_load"], 0)
        self.assertIn("stress", guidance)

    def test_bonding_reward_and_recovery_have_positive_runtime_effects(self):
        matrix = self._matrix(
            oxytocin=0.9,
            dopamine=0.85,
            serotonin=0.8,
            cortisol=0.1,
        )

        emotion = matrix.get_emotion_effects()
        interoceptive = matrix.get_interoceptive_effects()
        impulse = matrix.get_impulse_effects()
        guidance = " ".join(matrix.get_prompt_guidance())

        self.assertGreater(emotion["love"], 0)
        self.assertGreater(emotion["trust"], 0)
        self.assertGreater(emotion["anticipation"], 0)
        self.assertGreater(interoceptive["social_satiety"], 0)
        self.assertLess(interoceptive["connection_craving"], 0)
        self.assertGreater(impulse["connection_bias"], 0)
        self.assertGreater(impulse["reward_bias"], 0)
        self.assertIn("bonding", guidance)
        self.assertIn("reward", guidance)

    def test_somatic_system_applies_hormonal_body_state(self):
        matrix = self._matrix(cortisol=0.95)
        body = SomaticFeedbackSystem()
        before_heart_rate = body.heart_rate
        before_tension = body.muscle_tension

        body.apply_hormonal_effects(matrix.get_somatic_effects(), "cortisol")

        self.assertGreater(body.heart_rate, before_heart_rate)
        self.assertGreater(body.muscle_tension, before_tension)
        self.assertTrue(
            any(s.associated_emotion == "hormonal_cortisol" for s in body.active_sensations)
        )

    def test_hormonal_impulse_biases_reach_generator(self):
        matrix = self._matrix(dopamine=0.95, oxytocin=0.75, cortisol=0.1)
        generator = ImpulseGenerator()

        with patch.object(generator, "get_time_of_day", return_value="afternoon"), \
             patch("brain.subconscious.impulse_generator.random.random", return_value=0.0):
            impulse = generator.evaluate(
                emotion={},
                silence_minutes=0,
                love_level=0.2,
                desire_level=0.8,
                is_high_desire=True,
                is_in_love=False,
                learning_success_rates={},
                hormonal_effects=matrix.get_impulse_effects(),
            )

        self.assertIsNotNone(impulse)
        self.assertEqual(impulse.type, ImpulseType.HIGH_DESIRE)
        self.assertGreaterEqual(impulse.strength, 0.5)

    def test_prompt_builder_includes_hormonal_guidance(self):
        emotion = {
            "mood": "neutral",
            "response_tendency": "protective",
            "soul_hormonal": {
                "prompt_guidance": [
                    "stress is high: sound more vigilant, concise, and protective"
                ]
            },
        }

        with patch("core.thinking.random.choice", return_value="NO emoji in this message. Just raw text."):
            prompt = build_mood_instruction(emotion, "hey", "babe")

        self.assertIn("hormonal influence", prompt)
        self.assertIn("stress is high", prompt)
        self.assertIn("scanning for safety", prompt)


if __name__ == "__main__":
    unittest.main()
