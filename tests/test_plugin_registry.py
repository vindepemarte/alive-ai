import asyncio
import importlib
import unittest

from core.plugin_registry import PluginDeclaration, PluginRegistry, register_builtin_plugins


class PluginRegistryTests(unittest.TestCase):
    def test_builtin_registry_has_runtime_organs(self):
        registry = PluginRegistry()
        register_builtin_plugins(registry, probe=False)

        snapshot = registry.snapshot()
        names = {plugin["name"] for plugin in snapshot["plugins"]}

        self.assertIn("interoception", names)
        self.assertIn("memory_layers", names)
        self.assertIn("mcp", names)
        self.assertIn("behavioral_pressure", names)
        self.assertIn("body", snapshot["categories"])
        self.assertGreaterEqual(snapshot["plugin_count"], 20)
        pressure = next(plugin for plugin in snapshot["plugins"] if plugin["name"] == "behavioral_pressure")
        self.assertIn("dominant", pressure["state_keys"])
        self.assertIn("drives", pressure["state_keys"])

    def test_probe_marks_missing_plugin_unavailable_and_redacts_error(self):
        registry = PluginRegistry()
        registry.register(PluginDeclaration(
            name="secret_plugin",
            category="test",
            import_path="missing_secret_token_plugin",
        ))

        registry.probe_all()
        row = registry.snapshot()["plugins"][0]

        self.assertFalse(row["available"])
        self.assertEqual(row["error"], "[redacted]")

    def test_register_builtin_plugins_is_idempotent(self):
        registry = PluginRegistry()
        register_builtin_plugins(registry, probe=False)
        registry.update_availability("interoception", True)

        register_builtin_plugins(registry, probe=False)
        row = registry.get("interoception")

        self.assertIsNotNone(row)
        self.assertTrue(row.available)

    def test_message_handler_status_keeps_legacy_booleans_and_plugins(self):
        handler = importlib.import_module("core.message_handler")

        status = handler.get_aliveness_module_status()

        self.assertIn("interoception", status)
        self.assertIn("modules_active", status)
        self.assertIn("plugins", status)
        self.assertIn("plugin_categories", status)

    def test_webui_plugin_endpoint_uses_runtime_registry(self):
        registry = PluginRegistry()
        registry.register(PluginDeclaration(
            name="runtime_test",
            category="test",
            import_path="json",
            available=True,
        ))

        class FakeSelf:
            _plugins = registry

        app = importlib.import_module("webui.app")
        app.set_self_ref(FakeSelf())
        status = asyncio.run(app.get_plugins_status())

        self.assertEqual(status["plugin_count"], 1)
        self.assertEqual(status["available_count"], 1)
        self.assertEqual(status["plugins"][0]["name"], "runtime_test")


if __name__ == "__main__":
    unittest.main()
