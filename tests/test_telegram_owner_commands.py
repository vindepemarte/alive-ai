import os
import unittest

from input.telegram.commands import OwnerCommands


class TelegramOwnerCommandTests(unittest.TestCase):
    def tearDown(self):
        os.environ.pop("TELEGRAM_OWNER_ID", None)

    def test_owner_id_reads_preserved_settings_when_env_missing(self):
        class FakeConfig:
            settings = {"TELEGRAM_OWNER_ID": "7453886105"}

        class FakeAi:
            config = FakeConfig()

        commands = OwnerCommands(FakeAi(), command_handler=None)

        self.assertEqual(commands._get_owner_id(), "7453886105")

    def test_owner_id_env_overrides_settings(self):
        class FakeConfig:
            settings = {"TELEGRAM_OWNER_ID": "settings-owner"}

        class FakeAi:
            config = FakeConfig()

        os.environ["TELEGRAM_OWNER_ID"] = "env-owner"
        commands = OwnerCommands(FakeAi(), command_handler=None)

        self.assertEqual(commands._get_owner_id(), "env-owner")


if __name__ == "__main__":
    unittest.main()
