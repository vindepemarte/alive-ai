"""Dreams must have consequences: tone follows the pre-sleep emotional state,
and each dream yields a one-time emotional residue for waking."""

import random
import tempfile
import unittest
from pathlib import Path

import brain.dreams as dreams_mod


FEARFUL_STATE = {"fear": 0.9, "dread": 0.8, "trust": 0.2, "love": 0.05, "joy": 0.2, "sadness": 0.3}
LOVING_STATE = {"love": 0.9, "joy": 0.8, "trust": 0.8, "desire": 0.6, "fear": 0.05, "sadness": 0.05}


class DreamConsequencesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self._old_data_path = dreams_mod.DATA_PATH
        self._old_dreams_file = dreams_mod.DREAMS_FILE
        dreams_mod.DATA_PATH = Path(self.tmp.name)
        dreams_mod.DREAMS_FILE = Path(self.tmp.name) / "dreams.json"
        self.system = dreams_mod.DreamSystem()

    def tearDown(self):
        dreams_mod.DATA_PATH = self._old_data_path
        dreams_mod.DREAMS_FILE = self._old_dreams_file
        self.tmp.cleanup()

    def test_fearful_state_biases_dark_tones(self):
        rng = random.Random(7)
        tones = [dreams_mod.derive_dream_tone(FEARFUL_STATE, rng=rng) for _ in range(300)]
        dark = sum(1 for tone in tones if tone in ("nightmare", "anxious"))
        self.assertGreater(dark, 150, f"expected mostly dark tones, got {dark}/300")

    def test_loving_state_biases_tender_tones(self):
        rng = random.Random(7)
        tones = [dreams_mod.derive_dream_tone(LOVING_STATE, rng=rng) for _ in range(300)]
        tender = sum(1 for tone in tones if tone == "tender")
        nightmares = sum(1 for tone in tones if tone == "nightmare")
        self.assertGreater(tender, nightmares)

    def test_generated_dream_carries_tone_and_residue(self):
        text = self.system.generate_dream(
            memories=["we talked about the sea for hours"],
            sleep_cycle_id="cycle_1",
            force=True,
            emotion_state=FEARFUL_STATE,
            rng=random.Random(3),
        )
        self.assertTrue(text)
        record = self.system.get_recent_dream_record()
        self.assertIn(record["tone"], dreams_mod.DREAM_TONES)
        self.assertTrue(record["feeling"])
        self.assertEqual(record["residue"], dreams_mod.DREAM_TONES[record["tone"]]["residue"])
        self.assertFalse(record["residue_consumed"])

    def test_wake_residue_is_consumed_exactly_once(self):
        self.system.generate_dream(
            memories=["a long quiet evening"],
            sleep_cycle_id="cycle_2",
            force=True,
            emotion_state=LOVING_STATE,
            rng=random.Random(5),
        )
        residue = self.system.consume_wake_residue()
        self.assertTrue(residue.get("deltas"))
        self.assertTrue(residue.get("feeling"))
        self.assertTrue(residue.get("text"))
        self.assertEqual(self.system.consume_wake_residue(), {})

        # Consumption persists across reload.
        reloaded = dreams_mod.DreamSystem()
        self.assertEqual(reloaded.consume_wake_residue(), {})

    def test_residue_keys_are_valid_emotion_dimensions(self):
        from heart.emotional_state import DEFAULTS
        for tone, data in dreams_mod.DREAM_TONES.items():
            for key in data["residue"]:
                self.assertIn(key, DEFAULTS, f"{tone} residue key {key} is not a heart dimension")

    def test_prompt_section_names_the_lingering_feeling(self):
        self.system.generate_dream(
            memories=["we argued about nothing"],
            sleep_cycle_id="cycle_3",
            force=True,
            emotion_state=FEARFUL_STATE,
            rng=random.Random(11),
        )
        section = self.system.get_dream_prompt_section()
        self.assertIn("It left you feeling", section)


if __name__ == "__main__":
    unittest.main()
