import asyncio
import importlib
import json
import os
import tempfile
import unittest
from pathlib import Path


class WebUIIdentityStoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data = os.environ.get("ALIVE_AI_DATA_PATH")
        self.old_root = os.environ.get("ALIVE_AI_ROOT")
        os.environ["ALIVE_AI_DATA_PATH"] = self.tmp.name
        os.environ["ALIVE_AI_ROOT"] = self.tmp.name

    def tearDown(self):
        if self.old_data is None:
            os.environ.pop("ALIVE_AI_DATA_PATH", None)
        else:
            os.environ["ALIVE_AI_DATA_PATH"] = self.old_data
        if self.old_root is None:
            os.environ.pop("ALIVE_AI_ROOT", None)
        else:
            os.environ["ALIVE_AI_ROOT"] = self.old_root
        self.tmp.cleanup()

    def test_thought_time_uses_persisted_timestamp_not_now(self):
        app = importlib.import_module("webui.app")
        importlib.reload(app)

        class Thought:
            content = "old thought"
            type = "reflection"
            emotion = {}
            timestamp = "2026-06-02T01:23:45"

        class WorkingMemory:
            def get_recent_thoughts(self, _limit):
                return [Thought()]

        class Subconscious:
            working_memory = WorkingMemory()

        class FakeSelf:
            _subconscious = Subconscious()

        app.set_self_ref(FakeSelf())
        thoughts = app._subconscious_thoughts()
        self.assertEqual(thoughts[0]["time"], "01:23:45")
        self.assertEqual(thoughts[0]["timestamp"], "2026-06-02T01:23:45")

    def test_identity_snapshot_reads_configured_name(self):
        app = importlib.import_module("webui.app")
        importlib.reload(app)

        config_dir = Path(self.tmp.name) / "config"
        config_dir.mkdir(parents=True)
        (config_dir / "self.json").write_text(json.dumps({
            "who_i_am": {
                "name": "Alice",
                "full_name": "Alice Moretti",
                "gender": "female",
                "sexuality": "straight",
            }
        }))

        identity = app.build_snapshot()["identity"]
        self.assertEqual(identity["name"], "Alice")
        self.assertEqual(identity["full_name"], "Alice Moretti")

    def test_asleep_interoception_overrides_awake_body_description(self):
        app = importlib.import_module("webui.app")
        import heart.circadian as circadian_module
        importlib.reload(app)
        importlib.reload(circadian_module)

        circadian_path = Path(self.tmp.name) / "circadian_state.json"
        circadian_path.write_text(json.dumps({
            "is_asleep": True,
            "sleep_start": "2026-06-02T02:00:00",
            "wake_time": None,
            "sleep_debt": 4.0,
            "forced_awake": False,
            "forced_awake_until": None,
            "sleep_cycle_id": "sleep-test",
        }))

        result = asyncio.run(app.get_interoceptive_state())
        self.assertEqual(result["current_mood"], "asleep")
        self.assertIn("asleep", result["bodily_description"])
        self.assertLessEqual(result["states"]["energy"]["current_value"], 0.1)

    def test_narrative_backfills_key_moments_from_history(self):
        import brain.narrative as narrative_module
        importlib.reload(narrative_module)

        user_dir = Path(self.tmp.name) / "users" / "7453886105" / "conversations"
        user_dir.mkdir(parents=True)
        (user_dir / "2026-06-02.jsonl").write_text(
            json.dumps({
                "timestamp": "2026-06-02T02:00:00",
                "user": "good night my love, i will dream of you",
                "ai": "sweet dreams my love",
            }) + "\n"
        )

        engine = narrative_module.NarrativeEngine()
        detected = engine.backfill_key_moments("7453886105")
        data = engine._get_data("7453886105")
        moment_types = {m["type"] for m in data["key_moments"]}
        self.assertTrue(detected)
        self.assertIn("first_i_love_you", moment_types)
        self.assertIn("first_goodnight", moment_types)


if __name__ == "__main__":
    unittest.main()
