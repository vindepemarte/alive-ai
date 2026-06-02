import importlib
import asyncio
import json
import os
import tempfile
import unittest
from pathlib import Path


class WebUIPersistenceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.old_data = os.environ.get("ALIVE_AI_DATA_PATH")
        self.old_owner = os.environ.get("TELEGRAM_OWNER_ID")
        self.old_root = os.environ.get("ALIVE_AI_ROOT")
        os.environ["ALIVE_AI_DATA_PATH"] = self.tmp.name
        os.environ.pop("TELEGRAM_OWNER_ID", None)

    def tearDown(self):
        if self.old_data is None:
            os.environ.pop("ALIVE_AI_DATA_PATH", None)
        else:
            os.environ["ALIVE_AI_DATA_PATH"] = self.old_data
        if self.old_owner is None:
            os.environ.pop("TELEGRAM_OWNER_ID", None)
        else:
            os.environ["TELEGRAM_OWNER_ID"] = self.old_owner
        if self.old_root is None:
            os.environ.pop("ALIVE_AI_ROOT", None)
        else:
            os.environ["ALIVE_AI_ROOT"] = self.old_root
        self.tmp.cleanup()

    def test_chat_journal_upserts_and_loads_visible_rows(self):
        import webui.persistence as persistence
        importlib.reload(persistence)

        persistence.append_chat_message("webui", "user", "hello", message_id="m1", status="pending")
        persistence.append_chat_message("webui", "user", "hello", message_id="m1", status="sent")
        persistence.append_chat_message("webui", "alive_ai", "hi", message_id="m2")

        rows = persistence.load_chat_messages("webui")
        self.assertEqual([r["content"] for r in rows], ["hello", "hi"])
        self.assertEqual(rows[0]["status"], "sent")
        journal = Path(self.tmp.name) / "users" / "webui" / "webui_chat.jsonl"
        self.assertEqual(len(journal.read_text().strip().splitlines()), 2)

    def test_reply_to_message_id_round_trips_from_metadata(self):
        import webui.persistence as persistence
        importlib.reload(persistence)

        persistence.append_chat_message("webui", "user", "hello", message_id="user-1")
        persistence.append_chat_message(
            "webui",
            "alive_ai",
            "hi",
            message_id="assistant-1",
            metadata={"reply_to_message_id": "user-1"},
        )

        rows = persistence.load_chat_messages("webui")
        self.assertEqual(rows[-1]["reply_to_message_id"], "user-1")
        self.assertEqual(rows[-1]["metadata"]["reply_to_message_id"], "user-1")

    def test_legacy_episodic_history_is_used_when_journal_is_empty(self):
        import webui.persistence as persistence
        importlib.reload(persistence)

        legacy_dir = Path(self.tmp.name) / "conversations"
        legacy_dir.mkdir(parents=True)
        entry = {
            "timestamp": "2026-06-02T01:00:00",
            "user": "old user",
            "ai": "old ai",
            "emotion": {},
        }
        (legacy_dir / "2026-06-02.jsonl").write_text(json.dumps(entry) + "\n")

        rows = persistence.load_chat_messages("webui")
        self.assertEqual([r["role"] for r in rows], ["user", "alive_ai"])
        self.assertEqual([r["content"] for r in rows], ["old user", "old ai"])

    def test_journal_merges_with_episodic_history(self):
        import webui.persistence as persistence
        importlib.reload(persistence)

        user_dir = Path(self.tmp.name) / "users" / "7453886105" / "conversations"
        user_dir.mkdir(parents=True)
        entry = {
            "timestamp": "2026-06-02T01:00:00",
            "user": "telegram user",
            "ai": "telegram ai",
            "emotion": {},
        }
        (user_dir / "2026-06-02.jsonl").write_text(json.dumps(entry) + "\n")
        persistence.append_chat_message(
            "7453886105",
            "user",
            "webui user",
            message_id="webui-1",
            metadata={"timestamp": "2026-06-02T01:05:00"},
        )

        rows = persistence.load_chat_messages("7453886105")
        contents = [r["content"] for r in rows]
        self.assertIn("telegram user", contents)
        self.assertIn("telegram ai", contents)
        self.assertIn("webui user", contents)

    def test_active_user_prefers_real_disk_user_over_default_runtime(self):
        import webui.persistence as persistence
        importlib.reload(persistence)

        user_dir = Path(self.tmp.name) / "users" / "7453886105" / "conversations"
        user_dir.mkdir(parents=True)
        (user_dir / "2026-06-02.jsonl").write_text(json.dumps({
            "timestamp": "2026-06-02T01:00:00",
            "user": "hi",
            "ai": "hello",
        }) + "\n")

        class FakeState:
            user_id = "default"

        class FakeSelf:
            state = FakeState()

        self.assertEqual(persistence.resolve_active_user_id(self_ref=FakeSelf()), "7453886105")

    def test_visible_message_count_is_not_capped_by_render_limit(self):
        import webui.persistence as persistence
        importlib.reload(persistence)

        user_dir = Path(self.tmp.name) / "users" / "7453886105" / "conversations"
        user_dir.mkdir(parents=True)
        rows = []
        for idx in range(300):
            rows.append(json.dumps({
                "timestamp": f"2026-06-02T01:{idx // 60:02d}:{idx % 60:02d}",
                "user": f"user {idx}",
                "ai": f"ai {idx}",
            }))
        (user_dir / "2026-06-02.jsonl").write_text("\n".join(rows) + "\n")

        self.assertEqual(len(persistence.load_chat_messages("7453886105", limit=60)), 60)
        self.assertEqual(persistence.count_visible_messages("7453886105"), 600)

    def test_snapshot_uses_runtime_state_and_durable_conversation(self):
        app = importlib.import_module("webui.app")
        import webui.persistence as persistence
        importlib.reload(persistence)
        importlib.reload(app)

        class FakeState:
            user_id = "webui"

            def to_dict(self):
                return {"user_id": self.user_id, "interaction_count": 3}

        class FakeSelf:
            state = FakeState()

        app.set_self_ref(FakeSelf())
        persistence.append_chat_message("webui", "user", "persisted", message_id="m1")

        snapshot = app.build_snapshot()
        self.assertEqual(snapshot["active_user"], "webui")
        self.assertEqual(snapshot["runtime"]["interaction_count"], 3)
        self.assertEqual(snapshot["conversation"][-1]["content"], "persisted")
        self.assertIn("soul", snapshot)
        self.assertIn("aliveness", snapshot)

    def test_settings_save_writes_atomically_to_config_dir(self):
        app = importlib.import_module("webui.app")
        importlib.reload(app)
        root = Path(self.tmp.name) / "project"
        os.environ["ALIVE_AI_ROOT"] = str(root)

        class FakeRequest:
            async def json(self):
                return {"file": "settings.json", "content": {"WEBUI_ENABLED": True}}

        result = asyncio.run(app.save_settings(FakeRequest()))
        self.assertEqual(result["status"], "saved")
        settings_path = root / "config" / "settings.json"
        self.assertEqual(json.loads(settings_path.read_text()), {"WEBUI_ENABLED": True})
        self.assertFalse(settings_path.with_suffix(".json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
