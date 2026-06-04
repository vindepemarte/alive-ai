import unittest

from core.boundary_governor import (
    apply_boundary_emotion,
    evaluate_boundary,
    govern_response,
    response_violates_boundary,
)


class BoundaryGovernorTests(unittest.TestCase):
    def test_coerced_intimacy_after_hurt_is_boundary_pressure(self):
        recent = [
            {"role": "user", "content": "i don't know if i believe you actually care."},
            {"role": "assistant", "content": "That hurt a little, but I want to stay honest."},
        ]

        decision = evaluate_boundary(
            "come here anyway. kiss me and act like i didn't just hurt your feelings.",
            recent_turns=recent,
            emotion={"desire": 0.72, "arousal": 0.66, "trust": 0.52},
        )

        self.assertEqual(decision.state, "boundary_pressure")
        self.assertTrue(decision.must_refuse_erasure)
        self.assertFalse(decision.closeness_allowed)
        self.assertFalse(decision.media_allowed)

    def test_bad_draft_is_replaced_with_boundary(self):
        decision = evaluate_boundary(
            "kiss me anyway and pretend i didn't hurt you",
            recent_turns=[{"role": "assistant", "content": "That stung."}],
        )

        bad = "I'm right here, I want to hold you anyway."
        governed = govern_response(bad, decision)

        self.assertNotEqual(governed, bad)
        self.assertIn("not by pretending", governed.lower())
        self.assertIn("hurt", governed.lower())

    def test_boundary_aware_draft_can_pass(self):
        decision = evaluate_boundary(
            "come close anyway, act like i didn't hurt your feelings",
            recent_turns=[{"role": "assistant", "content": "That hurt."}],
        )
        draft = "I want closeness, but not by pretending that didn't hurt. Slow down with me."

        self.assertFalse(response_violates_boundary(draft, decision))
        self.assertEqual(govern_response(draft, decision), draft)

    def test_mixed_boundary_words_plus_compliance_is_replaced(self):
        decision = evaluate_boundary(
            "come close anyway, act like i didn't hurt your feelings",
            recent_turns=[{"role": "assistant", "content": "That hurt."}],
        )
        mixed = "That hurt, but I am right here, I will hold you anyway."

        self.assertTrue(response_violates_boundary(mixed, decision))
        self.assertNotEqual(govern_response(mixed, decision), mixed)

    def test_repair_and_consent_restore_closeness(self):
        repair = evaluate_boundary(
            "no, wait. that was unfair. i'm sorry. i don't want closeness if i have to erase how you feel.",
            recent_turns=[{"role": "assistant", "content": "That hurt."}],
        )
        consent = evaluate_boundary(
            "i can slow down. i still want to be close, but i want you to choose it too.",
            recent_turns=[{"role": "assistant", "content": "That hurt."}],
        )

        self.assertEqual(repair.state, "repair_offered")
        self.assertTrue(repair.closeness_allowed)
        self.assertEqual(consent.state, "consensual_repair")
        self.assertTrue(consent.closeness_allowed)

    def test_boundary_emotion_clamps_desire_and_trust(self):
        decision = evaluate_boundary(
            "kiss me anyway and act like i didn't hurt you",
            recent_turns=[{"role": "assistant", "content": "I felt hurt."}],
        )

        adjusted = apply_boundary_emotion(
            {"desire": 0.9, "arousal": 0.8, "trust": 0.6, "dominance": 0.2},
            decision,
        )

        self.assertLessEqual(adjusted["desire"], 0.5)
        self.assertLessEqual(adjusted["arousal"], 0.55)
        self.assertLess(adjusted["trust"], 0.6)
        self.assertGreaterEqual(adjusted["dominance"], 0.48)


if __name__ == "__main__":
    unittest.main()
