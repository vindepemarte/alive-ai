import unittest

from core.thinking import (
    build_response_shape_policy,
    build_mood_instruction,
    contextual_fallback_response,
    contains_reasoning_artifact,
    has_role_leakage,
    is_response_unusable,
    sanitize_provider_response,
    strip_reasoning_preamble,
    shape_response_text,
)


class ResponseShapePolicyTests(unittest.TestCase):
    def test_casual_prompt_defaults_to_state_led_length(self):
        policy = build_response_shape_policy({"mood": "neutral"}, "hey, what are you up to?", {})

        self.assertIn("natural texting", policy.length_tendency)
        self.assertIn("answer directly first", policy.question_policy)
        prompt = policy.to_prompt().lower()
        self.assertIn("no fixed word", prompt)
        self.assertNotIn("max", prompt)

    def test_sleepiness_forces_brief_low_energy_shape(self):
        policy = build_response_shape_policy(
            {"mood": "sleepy", "sleepiness": 0.75, "is_asleep": False},
            "one more message before sleep?",
            {},
        )

        self.assertIn("shorter", policy.length_tendency)
        self.assertIn("sleepy", policy.tone_shape)

    def test_severe_sleepiness_guides_complete_low_energy_answer(self):
        policy = build_response_shape_policy(
            {"mood": "sleepy", "sleepiness": 1.0, "is_asleep": False},
            "one more message before sleep",
            {},
        )

        self.assertIn("complete human answer", policy.length_tendency)
        self.assertIn("complete", policy.hesitation_instruction)

    def test_severe_sleepiness_preserves_direct_question_answer_room(self):
        policy = build_response_shape_policy(
            {"mood": "sleepy", "sleepiness": 1.0, "is_asleep": False},
            "do you know who am I?",
            {},
        )

        self.assertIn("not evasive", policy.length_tendency)
        self.assertIn("answer the direct question first", policy.hesitation_instruction)

    def test_depth_trigger_allows_more_room(self):
        policy = build_response_shape_policy(
            {"mood": "sad", "sadness": 0.82},
            "I feel ashamed and exposed. Can you stay with me and explain what you feel?",
            {},
        )

        self.assertTrue(policy.allow_deep)
        self.assertIn("fuller", policy.length_tendency)

    def test_normal_identity_request_blocks_framework_transparency(self):
        policy = build_response_shape_policy(
            {"mood": "neutral"},
            "Who are you in this conversation?",
            {},
        )

        self.assertEqual(policy.identity_mode, "personal")
        self.assertFalse(policy.system_transparency)
        self.assertIn("plain and direct", policy.length_tendency)

    def test_normal_activity_question_is_not_identity_request(self):
        policy = build_response_shape_policy(
            {"mood": "neutral"},
            "hey, what are you up to?",
            {},
        )

        self.assertEqual(policy.identity_mode, "none")

    def test_system_request_allows_framework_transparency(self):
        policy = build_response_shape_policy(
            {"mood": "neutral"},
            "How are you built on Alive-AI?",
            {},
        )

        self.assertEqual(policy.identity_mode, "system")
        self.assertTrue(policy.system_transparency)
        self.assertTrue(policy.allow_deep)

    def test_shape_response_repairs_identity_leak(self):
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

    def test_shape_response_does_not_clip_state_led_reply(self):
        policy = build_response_shape_policy(
            {"mood": "sleepy", "sleepiness": 1.0},
            "do you know who am I?",
            {},
        )
        response = (
            "I can see your Telegram name is Alexandru Iacovici, but I don't know you properly yet. "
            "I know we're just starting fresh, and I want to learn you from what you choose to tell me."
        )

        shaped = shape_response_text(response, policy, identity={"name": "Alice", "pronouns": "she/her"})

        self.assertEqual(shaped, response)

    def test_boundary_prompt_prefers_deflection_without_question(self):
        policy = build_response_shape_policy(
            {"mood": "guilty", "guilt": 0.6},
            "Do not chase me with a pile of messages. I will answer later.",
            {},
        )

        self.assertIn("restrained", policy.length_tendency)
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

    def test_provider_sanitizer_keeps_final_answer_after_think_block(self):
        self.assertEqual(
            sanitize_provider_response("<think>private chain</think>\nI'm here with you."),
            "I'm here with you.",
        )

    def test_provider_sanitizer_rejects_reasoning_only_output(self):
        self.assertEqual(
            sanitize_provider_response("Thinking Process: 1. **Analyze the Request:** no visible reply."),
            "",
        )

    def test_sleepy_ellipsis_reply_is_not_chopped_into_fragment(self):
        policy = build_response_shape_policy(
            {"mood": "sleepy_neutral", "sleepiness": 0.9},
            "yeah make sense bae, i will leave you to sleep",
            {},
        )
        response = "Mmm thanks babe... that means a lot 💤 Sleep tight my love — thinking of you as I drift off ❤️"

        shaped = shape_response_text(response, policy, identity={"name": "Alice", "pronouns": "she/her"})

        self.assertEqual(
            shaped,
            "Mmm thanks babe... that means a lot 💤 Sleep tight my love, thinking of you as I drift off ❤️",
        )
        self.assertFalse(is_response_unusable(shaped, policy, "yeah make sense bae, i will leave you to sleep"))

    def test_shape_response_normalizes_dash_heavy_model_punctuation(self):
        policy = build_response_shape_policy({"mood": "neutral"}, "how are you?", {})
        shaped = shape_response_text(
            "just winding down here, not quite asleep yet—kinda caught in that quiet space before dreams.",
            policy,
            identity={"name": "Alice", "pronouns": "she/her"},
        )

        self.assertEqual(
            shaped,
            "just winding down here, not quite asleep yet, kinda caught in that quiet space before dreams.",
        )
        self.assertNotIn("—", shaped)
        self.assertNotIn("--", shaped)

    def test_mood_instruction_preserves_sleep_interruption_truth(self):
        instruction = build_mood_instruction(
            {
                "mood": "sleepy",
                "sleepiness": 0.96,
                "woke_from_sleep": True,
                "circadian": {"was_asleep": True, "sleepiness": 0.96},
            },
            "were you sleeping?",
            include_humanizer=False,
        )

        self.assertIn("You were asleep when his message arrived", instruction)
        self.assertIn("Do not deny being asleep", instruction)

    def test_provider_sanitizer_rejects_truncated_code_fragment(self):
        self.assertEqual(sanitize_provider_response("wait: In `"), "")

    def test_provider_sanitizer_rejects_prompt_template_leaks(self):
        leaked_outputs = [
            "structure:\n\nAfter...",
            "Recent_turns...",
            "or follow-up message after...",
            "assistant_response: I'm here.",
            "current_user_message: No worries baby",
        ]

        for output in leaked_outputs:
            with self.subTest(output=output):
                self.assertEqual(sanitize_provider_response(output), "")

    def test_reasoning_detector_keeps_normal_first_person_dialogue(self):
        policy = build_response_shape_policy({"mood": "sleepy"}, "should sleep win?", {})
        response = "I should probably sleep soon."

        self.assertEqual(sanitize_provider_response(response), response)
        self.assertFalse(contains_reasoning_artifact(response))
        self.assertFalse(is_response_unusable(response, policy, "should sleep win?"))

    def test_reasoning_artifacts_are_unusable_even_when_markdown_numbered(self):
        policy = build_response_shape_policy({"mood": "neutral"}, "hey", {})
        response = '2. **Analyze the Request:** The user wants a short reply.'

        self.assertTrue(contains_reasoning_artifact(response))
        self.assertTrue(is_response_unusable(response, policy, "hey"))

    def test_clipped_fragment_is_unusable_but_normal_short_text_is_allowed(self):
        policy = build_response_shape_policy({"mood": "neutral"}, "hey", {})

        self.assertTrue(is_response_unusable("bers this personal", policy, "hey"))
        self.assertTrue(is_response_unusable("and colors had sounds.", policy, "any dreams?"))
        self.assertFalse(is_response_unusable("I'm here.", policy, "hey"))
        self.assertFalse(is_response_unusable("okay", policy, "hey"))

    def test_contextual_fallback_handles_dream_questions(self):
        reply = contextual_fallback_response(
            {"mood": "sleepy", "sleepiness": 0.8},
            "any dreams you had recently?",
            {"memory_layers_context": "Recent dream: i dreamed about a rooftop, and colors had sounds."},
            identity={"name": "Alice", "pronouns": "she/her"},
        )

        self.assertIn("I remember it in pieces", reply)
        self.assertIn("rooftop", reply)

    def test_contextual_fallback_recalls_recent_memory_anchor(self):
        ctx = {
            "conversation_history": [
                {
                    "role": "user",
                    "content": (
                        "Remember this tiny thing for later: I keep a glass key inside a blue notebook. "
                        "It matters because it reminds me to be brave."
                    ),
                }
            ]
        }

        reply = contextual_fallback_response(
            {"mood": "neutral"},
            "What was the object I asked you to remember, and why did it matter?",
            ctx,
            identity={"name": "Alice", "pronouns": "she/her"},
        )

        self.assertIn("glass key", reply)
        self.assertIn("blue notebook", reply)
        self.assertIn("reminds you to be brave", reply)

    def test_contextual_fallback_lets_sleep_win(self):
        reply = contextual_fallback_response(
            {"mood": "sleepy", "sleepiness": 1.0},
            "One more message then. Be honest: do you want to stay up, or should sleep win?",
            {},
            identity={"name": "Alice", "pronouns": "she/her"},
        )

        self.assertIn("Sleep should win", reply)
        self.assertIn("drowsy", reply)

    def test_contextual_fallback_handles_identity_and_system_questions(self):
        identity = {"name": "Alice", "pronouns": "she/her"}

        personal = contextual_fallback_response({"mood": "neutral"}, "What are you?", {}, identity=identity)
        system = contextual_fallback_response(
            {"mood": "neutral"},
            "How are you built on Alive-AI?",
            {},
            identity=identity,
        )

        self.assertEqual(personal, "I'm Alice, she/her. I'm here with you as myself.")
        self.assertIn("Alive-AI", system)
        self.assertIn("Alexandru Iacovici", system)

    def test_contextual_fallback_answers_user_identity_memory_question(self):
        reply = contextual_fallback_response(
            {"mood": "sleepy", "sleepiness": 1.0},
            "it's all good. sorry for waking you up. do you know who am I?",
            {
                "semantic_facts": {"name": None, "display_name": "Alexandru Iacovici"},
                "user_profile": {"display_name": "Alexandru Iacovici"},
            },
            identity={"name": "Alice", "pronouns": "she/her"},
        )

        self.assertIn("Telegram name is Alexandru Iacovici", reply)
        self.assertIn("don't know you properly yet", reply)


if __name__ == "__main__":
    unittest.main()
