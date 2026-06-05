import json
import subprocess
import tempfile
import unittest
from pathlib import Path


class CliUpdateMigrationTests(unittest.TestCase):
    def test_update_preserves_legacy_ollama_model_when_adding_task_models(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp) / "project"
            config = project / "config"
            config.mkdir(parents=True)
            (project / "main.py").write_text("# existing project marker\n")
            (project / "package.json").write_text('{"name":"existing-alive-ai","version":"0.1.25"}\n')
            (config / "settings.json").write_text(json.dumps({
                "AGENT_NAME": "Alice",
                "LLM_PROVIDER": "ollama",
                "OLLAMA_MODEL": "gemma4:e2b",
                "LLM_FALLBACK": {"ENABLED": True, "ORDER": ["ollama"]},
            }, indent=2))
            (config / "self.json").write_text(json.dumps({"who_i_am": {"name": "Alice"}}, indent=2))
            (config / "directives.json").write_text(json.dumps({"OPERATOR": {"owner_id": ""}}, indent=2))

            result = subprocess.run(
                ["node", str(repo / "cli" / "index.js"), "update", "--yes"],
                cwd=project,
                text=True,
                capture_output=True,
                timeout=30,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr or result.stdout)
            settings = json.loads((config / "settings.json").read_text())
            self.assertEqual(settings["OLLAMA_MODEL"], "gemma4:e2b")
            self.assertEqual(settings["OLLAMA_MODEL_MAIN"], "gemma4:e2b")
            self.assertEqual(settings["OLLAMA_MODEL_FAST"], "gemma4:e2b")
            self.assertEqual(settings["OLLAMA_MODEL_THINKING"], "gemma4:e2b")


if __name__ == "__main__":
    unittest.main()
