import os
import tempfile
import unittest


_tmp = tempfile.TemporaryDirectory()
os.environ["ALIVE_AI_DATA_PATH"] = _tmp.name

from heart.emotional_state import EmotionalState
from heart.complex_emotions import ComplexEmotions
from heart.core import Heart


class _Nervous:
    def on(self, *_args, **_kwargs):
        return None


class _Config:
    personality = {}


class EmotionalStateTests(unittest.TestCase):
    def test_negative_emotions_change_core_affect_and_mood(self):
        state = EmotionalState()
        state.joy = 0.2
        state.trust = 0.2
        state.sadness = 0.75
        state.fear = 0.7
        state.arousal = 0.45

        state.recompute_core_affect()

        self.assertLess(state.valence, 0.35)
        self.assertGreater(state.arousal, 0.45)
        self.assertLess(state.dominance, 0.45)
        self.assertIn(state._base_mood, {"fearful", "sad", "low", "uneasy"})

    def test_positive_trust_and_pride_have_repercussions(self):
        state = EmotionalState()
        state.joy = 0.85
        state.love = 0.65
        state.trust = 0.85
        state.pride = 0.65
        state.fear = 0.05
        state.sadness = 0.05

        state.recompute_core_affect()

        self.assertGreater(state.valence, 0.65)
        self.assertGreater(state.dominance, 0.6)
        self.assertTrue(any(token in state.mood_description for token in ("proud", "happy", "connected")))

    def test_complex_emotions_restore_from_persisted_state(self):
        state = EmotionalState()
        state.guilt = 0.7
        state.pride = 0.6
        state.jealousy = 0.5
        state.embarrassment = 0.4
        state.anticipation = 0.8

        complex_state = ComplexEmotions()
        complex_state.load_from_state(state)

        self.assertAlmostEqual(complex_state.guilt.value, 0.7)
        self.assertAlmostEqual(complex_state.pride.value, 0.6)
        self.assertAlmostEqual(complex_state.jealousy.value, 0.5)
        self.assertAlmostEqual(complex_state.embarrassment.value, 0.4)
        self.assertAlmostEqual(complex_state.anticipation.value, 0.8)


class HeartReactionTests(unittest.TestCase):
    def test_hurtful_message_reduces_trust_and_changes_behavior_state(self):
        heart = Heart(_Nervous(), _Config())

        emotion = heart.react("you lied to me, you hurt me, and now I am scared you will leave")

        self.assertGreater(emotion["fear"], 0.1)
        self.assertGreater(emotion["guilt"], 0.0)
        self.assertLess(emotion["trust"], 0.5)
        self.assertLess(emotion["valence"], 0.5)
        self.assertNotEqual(emotion["mood"], "neutral")


if __name__ == "__main__":
    unittest.main()
