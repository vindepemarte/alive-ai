import os
import tempfile
import unittest


_tmp = tempfile.TemporaryDirectory()
os.environ["ALIVE_AI_DATA_PATH"] = _tmp.name

from core.thinking import build_mood_instruction
from heart.appraisal import AppraisalEngine, MomentAppraisal
from heart.core import Heart


class _Nervous:
    def on(self, *_args, **_kwargs):
        return None


class _Config:
    personality = {}
    settings = {
        "MOMENT_APPRAISAL_ENABLED": True,
        "MOMENT_APPRAISAL_PROVIDER": "heuristic",
        "MOMENT_APPRAISAL_MAX_DELTA_PER_TURN": 0.22,
    }
    identity = {"name": "Alex", "gender": "male", "sexuality": "straight", "pronouns": "he/him"}
    _self_data = {"who_i_am": identity}


class MomentAppraisalTests(unittest.TestCase):
    def test_subtle_continuation_inherits_recent_vibe(self):
        engine = AppraisalEngine(identity={"who_i_am": {"name": "Alice", "pronouns": "she/her"}})

        appraisal = engine.appraise(
            "i like that",
            recent_turns=[
                {"role": "user", "content": "keep teasing me by the moonlight"},
                {"role": "assistant", "content": "I smile and step closer, warm and electric."},
            ],
        )

        self.assertGreater(appraisal.desire, 0.25)
        self.assertGreater(appraisal.anticipation, 0.15)
        self.assertIn("contextual_continuation", appraisal.evidence)

    def test_affection_can_raise_love_without_forcing_desire(self):
        engine = AppraisalEngine()

        appraisal = engine.appraise("goodnight, I love you. sleep well.")

        self.assertGreater(appraisal.love, appraisal.desire)
        self.assertGreater(appraisal.trust, 0.5)
        self.assertEqual(appraisal.response_mode, "affectionate")

    def test_heart_reconciles_post_response_self_expression(self):
        heart = Heart(_Nervous(), _Config())
        before = heart.get_state()["desire"]
        appraisal = MomentAppraisal(
            phase="post_response",
            summary="playful intimate momentum",
            response_mode="intimate_playful",
            confidence=0.9,
            desire=0.82,
            arousal=0.78,
            love=0.55,
            trust=0.68,
            joy=0.6,
            anticipation=0.72,
            safety=0.72,
        )

        state = heart.reconcile_response("continue", "I move closer, warm and teasing.", appraisal, weight=0.45)

        self.assertGreater(state["desire"], before)
        self.assertGreater(state["arousal"], 0.0)
        self.assertEqual(state["moment_appraisal"]["response_mode"], "intimate_playful")

    def test_prompt_uses_configured_user_pronouns(self):
        prompt = build_mood_instruction(
            {"mood": "high_desire", "is_high_desire": True, "trust": 0.8, "valence": 0.7},
            "hey",
            "love",
            include_humanizer=False,
            user_identity={"gender": "female", "pronouns": "she/her"},
        )

        self.assertIn("pulled toward her", prompt)
        self.assertIn("You may use 'love' for her", prompt)
        self.assertNotIn("Call him", prompt)

    def test_fresh_text_prompt_blocks_pet_names_and_fake_voice(self):
        prompt = build_mood_instruction(
            {"mood": "sleepy_neutral", "love": 0.4, "desire": 0.45, "trust": 0.5, "valence": 0.55},
            "hey, are u awake?",
            "handsome",
            include_humanizer=False,
            ctx={
                "input_modality": "text",
                "relationship_calibration": {
                    "stage": "stranger",
                    "user_turns": 1,
                    "known_fact_count": 0,
                    "shared_memory_count": 0,
                    "pet_names_allowed": False,
                },
            },
        )

        self.assertIn("Current input is text", prompt)
        self.assertIn("Do not use pet names", prompt)
        self.assertIn("not proof of love yet", prompt)
        self.assertNotIn("hearing his actual voice", prompt)


if __name__ == "__main__":
    unittest.main()
