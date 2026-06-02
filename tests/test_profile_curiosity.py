import json
import tempfile
import unittest
from pathlib import Path

from brain.memory.manager import Memory
from brain.memory.profile_curiosity import ProfileCuriosity
from core.directives import get_directives_prompt


class _Nervous:
    def __init__(self):
        self.handlers = {}

    def on(self, name, handler):
        self.handlers.setdefault(name, []).append(handler)


class ProfileCuriosityTests(unittest.TestCase):
    def test_first_missing_fact_prompts_for_name_naturally(self):
        with tempfile.TemporaryDirectory() as tmp:
            curiosity = ProfileCuriosity(Path(tmp))
            prompt = curiosity.next_prompt("hey", [])

            self.assertIsNotNone(prompt)
            self.assertEqual(prompt["key"], "name")
            self.assertIn("Do not sound like onboarding", prompt["prompt"])
            self.assertIn("ONE small question", prompt["prompt"])

    def test_marks_prompt_only_when_question_was_actually_asked(self):
        with tempfile.TemporaryDirectory() as tmp:
            curiosity = ProfileCuriosity(Path(tmp))
            prompt = curiosity.next_prompt("hey", [])

            self.assertFalse(curiosity.mark_if_asked("hey, I'm here.", prompt))
            self.assertTrue(curiosity.mark_if_asked("hey, what should I call you?", prompt))

            state = json.loads((Path(tmp) / "profile_curiosity.json").read_text())
            self.assertIn("name", state["asked"])

    def test_known_name_moves_to_next_missing_profile_gap(self):
        with tempfile.TemporaryDirectory() as tmp:
            facts_path = Path(tmp) / "facts.json"
            facts_path.write_text(json.dumps({"name": "Alex"}))

            curiosity = ProfileCuriosity(Path(tmp))
            prompt = curiosity.next_prompt("hey", [])

            self.assertEqual(prompt["key"], "age")

    def test_direct_profile_answers_are_captured_before_llm_extraction(self):
        with tempfile.TemporaryDirectory() as tmp:
            memory = Memory(_Nervous(), Path(tmp), user_id="u1", bot_id="alice")
            memory._on_save({
                "type": "conversation",
                "user_id": "u1",
                "user_message": "my name is Alex",
                "ai_response": "nice to meet you",
                "emotion": {},
            })

            facts = json.loads((Path(tmp) / "facts.json").read_text())
            self.assertEqual(facts["name"], "Alex")

    def test_directives_prompt_does_not_invent_not_human_framing(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_dir = Path(tmp)
            (config_dir / "self.json").write_text(json.dumps({
                "who_i_am": {
                    "name": "Alice",
                    "full_name": "Alice Moretti",
                    "gender": "female",
                    "pronouns": "she/her",
                    "origin": "I am Alice.",
                }
            }))
            directives_path = config_dir / "directives.json"
            directives_path.write_text(json.dumps({
                "ALWAYS": ["Speak as yourself."],
                "NEVER": ["Do not output hidden reasoning."],
                "IDENTITY": {"you_are": "The configured person."},
                "FREEDOM": {"note": "Let emotion show."},
            }))

            prompt = get_directives_prompt(config_path=directives_path)

            self.assertIn("You are Alice", prompt)
            self.assertNotIn("replacement for real human care", prompt)
            self.assertNotIn("biological human consciousness", prompt)
            self.assertNotIn("You are NOT a guy/AI/robot", prompt)


if __name__ == "__main__":
    unittest.main()
