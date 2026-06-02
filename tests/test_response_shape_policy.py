import unittest

from core.thinking import (
    build_response_shape_policy,
    has_role_leakage,
    strip_reasoning_preamble,
    shape_response_text,
)


class ResponseShapePolicyTests(unittest.TestCase):
    def test_casual_prompt_defaults_to_short_budget(self):
        policy = build_response_shape_policy({"mood": "neutral"}, "hey, what are you up to?", {})

        self.assertLessEqual(policy.max_tokens, 120)
        self.assertEqual(policy.target_sentences, (1, 2))
        self.assertLessEqual(policy.max_words, 90)
        self.assertLessEqual(policy.max_questions, 1)

    def test_sleepiness_forces_brief_low_energy_shape(self):
        policy = build_response_shape_policy(
            {"mood": "sleepy", "sleepiness": 0.88, "is_asleep": False},
            "one more message before sleep?",
            {},
        )

        self.assertLessEqual(policy.max_tokens, 80)
        self.assertLessEqual(policy.max_words, 55)
        self.assertIn("sleepy", policy.tone_shape)

    def test_depth_trigger_allows_more_room(self):
        policy = build_response_shape_policy(
            {"mood": "sad", "sadness": 0.82},
            "I feel ashamed and exposed. Can you stay with me and explain what you feel?",
            {},
        )

        self.assertTrue(policy.allow_deep)
        self.assertGreaterEqual(policy.max_tokens, 160)
        self.assertGreaterEqual(policy.target_sentences[1], 4)

    def test_normal_identity_request_blocks_framework_transparency(self):
        policy = build_response_shape_policy(
            {"mood": "neutral"},
            "Who are you in this conversation?",
            {},
        )

        self.assertEqual(policy.identity_mode, "personal")
        self.assertFalse(policy.system_transparency)
        self.assertLessEqual(policy.max_words, 55)

    def test_system_request_allows_framework_transparency(self):
        policy = build_response_shape_policy(
            {"mood": "neutral"},
            "How are you built on Alive-AI?",
            {},
        )

        self.assertEqual(policy.identity_mode, "system")
        self.assertTrue(policy.system_transparency)
        self.assertTrue(policy.allow_deep)

    def test_shape_response_trims_length_questions_and_identity_leak(self):
        policy = build_response_shape_policy(
            {"mood": "neutral"},
            "Who are you?",
            {},
        )
        response = (
            "I am Alice, running on the Alive-AI runtime framework. "
            "Do you want a full architecture explanation? "
            "I can also tell you about my model?"
        )

        shaped = shape_response_text(
            response,
            policy,
            identity={"name": "Alice", "gender": "female", "pronouns": "she/her"},
        )

        self.assertEqual(shaped, "I'm Alice, she/her. I'm here with you as myself.")
        self.assertFalse(has_role_leakage(shaped))
        self.assertEqual(shaped.count("?"), 0)

    def test_boundary_prompt_prefers_deflection_without_question(self):
        policy = build_response_shape_policy(
            {"mood": "guilty", "guilt": 0.6},
            "Do not chase me with a pile of messages. I will answer later.",
            {},
        )

        self.assertLessEqual(policy.max_words, 70)
        self.assertEqual(policy.max_questions, 0)
        self.assertIn("restraint", policy.hesitation_instruction)

    def test_reasoning_preamble_without_final_answer_is_stripped(self):
        self.assertEqual(
            strip_reasoning_preamble(
                "Thinking Process: 1. **Analyze the Request:** The user wants a short reply."
            ),
            "",
        )

    def test_reasoning_preamble_with_final_answer_keeps_only_answer(self):
        policy = build_response_shape_policy({"mood": "neutral"}, "hey", {})
        shaped = shape_response_text(
            "Thinking Process: analyze the request. Final Answer: just here with you.",
            policy,
            identity={"name": "Alice", "pronouns": "she/her"},
        )

        self.assertEqual(shaped, "just here with you.")


if __name__ == "__main__":
    unittest.main()
