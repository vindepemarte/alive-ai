"""
Core: Config
Load and manage configuration from JSON files
All settings live in settings.json - HOT RELOADABLE (mounted in Docker)
Personality/identity now comes from self.json (managed by self_authorship skill)
"""

import json
from pathlib import Path

class Config:
    """Configuration manager - reads from settings.json and self.json"""

    def __init__(self, base_path: Path):
        self.base = base_path
        # Load identity/personality from self.json (the single source of truth)
        self._self_data = self._load("self.json")
        # identity is the who_i_am section for backwards compatibility
        self.identity = self._self_data.get("who_i_am", {})
        # personality is the my_personality section for backwards compatibility
        self.personality = self._self_data.get("my_personality", {})
        self._settings_path = base_path / "settings.json"
        self._settings_mtime = 0
        self._settings_cache = None

    def _load(self, name: str, default=None):
        path = self.base / name
        if path.exists():
            return json.loads(path.read_text())
        return default or {}

    def _reload_settings_if_changed(self):
        """Hot-reload settings if file changed"""
        try:
            mtime = self._settings_path.stat().st_mtime if self._settings_path.exists() else 0
            if mtime != self._settings_mtime:
                self._settings_mtime = mtime
                self._settings_cache = None
        except:
            pass

    @property
    def settings(self):
        """Get settings (hot-reloaded from settings.json)"""
        self._reload_settings_if_changed()
        if self._settings_cache is None:
            self._settings_cache = self._load("settings.json", {})
        return self._settings_cache

    def save(self, name: str, data: dict):
        (self.base / name).write_text(json.dumps(data, indent=2))

    def get(self, key: str, default=None):
        return self.settings.get(key, default)
