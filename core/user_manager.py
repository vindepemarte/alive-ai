"""
Core: User Manager
Manages per-user memory instances and settings.
Each user gets their own memory, intimacy state, and content unlocks.
"""

import json
from pathlib import Path
from typing import Dict, Optional, Any
from datetime import datetime


class UserManager:
    """
    Manages per-user state and memory paths.
    Provides user isolation for memory, intimacy layers, and content unlocks.
    """

    def __init__(self, base_path: Path = None):
        """
        Initialize the User Manager.

        Args:
            base_path: Base path for data storage (defaults to /app/data or local data/)
        """
        if base_path:
            self.base_path = base_path
        else:
            # Try Docker path first, then local development path
            docker_path = Path("/app/data")
            local_path = Path(__file__).parent.parent / "data"
            self.base_path = docker_path if docker_path.exists() else local_path

        self.users_path = self.base_path / "users"
        self.users_path.mkdir(parents=True, exist_ok=True)

        # Cache for user data paths
        self._user_paths: Dict[str, Dict[str, Path]] = {}

        # Owner settings cache
        self._owner_settings: Optional[dict] = None

    def get_user_path(self, user_id: str) -> Path:
        """
        Get the base path for a user's data.

        Args:
            user_id: The user's Telegram ID

        Returns:
            Path to the user's data directory
        """
        user_path = self.users_path / str(user_id)
        user_path.mkdir(parents=True, exist_ok=True)
        return user_path

    def get_user_paths(self, user_id: str) -> Dict[str, Path]:
        """
        Get all paths for a user's data files.

        Args:
            user_id: The user's Telegram ID

        Returns:
            Dictionary with paths for all user data files
        """
        if user_id in self._user_paths:
            return self._user_paths[user_id]

        base = self.get_user_path(user_id)
        paths = {
            "base": base,
            "conversations": base / "conversations",
            "facts": base / "facts.json",
            "intimacy_layers": base / "intimacy_layers.json",
            "content_unlocks": base / "content_unlocks.json",
            "summaries": base / "summaries",
        }

        # Ensure directories exist
        paths["conversations"].mkdir(parents=True, exist_ok=True)
        paths["summaries"].mkdir(parents=True, exist_ok=True)

        self._user_paths[user_id] = paths
        return paths

    # -------------------------------------------------------------------------
    # Owner Settings
    # -------------------------------------------------------------------------

    def _load_owner_settings(self) -> dict:
        """Load owner settings from file"""
        if self._owner_settings is not None:
            return self._owner_settings

        settings_path = self.base_path / "owner_settings.json"
        if settings_path.exists():
            try:
                self._owner_settings = json.loads(settings_path.read_text())
            except (json.JSONDecodeError, Exception):
                self._owner_settings = {}
        else:
            self._owner_settings = {}

        return self._owner_settings

    def _save_owner_settings(self, settings: dict):
        """Save owner settings to file"""
        settings_path = self.base_path / "owner_settings.json"
        settings["updated_at"] = datetime.now().isoformat()
        settings_path.write_text(json.dumps(settings, indent=2))
        self._owner_settings = settings

    def is_advanced_enabled(self) -> bool:
        """
        Check if owner has /advanced mode enabled (advanced access).

        Returns:
            True if advanced mode is enabled
        """
        settings = self._load_owner_settings()
        return settings.get("advanced_enabled", False)

    def set_advanced_enabled(self, enabled: bool) -> bool:
        """
        Set the advanced mode status.

        Args:
            enabled: Whether to enable or disable advanced mode

        Returns:
            The new enabled state
        """
        settings = self._load_owner_settings()
        settings["advanced_enabled"] = enabled
        self._save_owner_settings(settings)
        return enabled

    def toggle_advanced(self) -> bool:
        """
        Toggle the advanced mode status.

        Returns:
            The new enabled state
        """
        current = self.is_advanced_enabled()
        return self.set_advanced_enabled(not current)

    def get_owner_settings(self) -> dict:
        """
        Get all owner settings.

        Returns:
            Dictionary with all owner settings
        """
        return self._load_owner_settings().copy()

    # -------------------------------------------------------------------------
    # User Existence & Migration
    # -------------------------------------------------------------------------

    def user_exists(self, user_id: str) -> bool:
        """
        Check if a user has existing data.

        Args:
            user_id: The user's Telegram ID

        Returns:
            True if user has any data
        """
        user_path = self.get_user_path(user_id)
        facts_path = user_path / "facts.json"
        conv_path = user_path / "conversations"

        return facts_path.exists() or (conv_path.exists() and any(conv_path.glob("*.jsonl")))

    def get_all_users(self) -> list:
        """
        Get list of all user IDs that have data.

        Returns:
            List of user ID strings
        """
        users = []
        if self.users_path.exists():
            for user_dir in self.users_path.iterdir():
                if user_dir.is_dir() and user_dir.name.isdigit():
                    users.append(user_dir.name)
        return users

    def migrate_legacy_data(self, owner_id: str):
        """
        Migrate legacy data from the old flat structure to per-user structure.

        Args:
            owner_id: The owner's Telegram ID to migrate data to
        """
        import shutil

        legacy_paths = {
            "conversations": self.base_path / "conversations",
            "facts": self.base_path / "facts.json",
            "intimacy_layers": self.base_path / "intimacy_layers.json",
            "content_unlocks": self.base_path / "content_unlocks.json",
            "summaries": self.base_path / "summaries",
        }

        user_paths = self.get_user_paths(owner_id)

        # Migrate conversations
        if legacy_paths["conversations"].exists():
            for conv_file in legacy_paths["conversations"].glob("*.jsonl"):
                dest = user_paths["conversations"] / conv_file.name
                if not dest.exists():
                    shutil.copy2(conv_file, dest)
                    print(f"[UserManager] Migrated conversation: {conv_file.name}")

        # Migrate facts.json
        if legacy_paths["facts"].exists() and not user_paths["facts"].exists():
            shutil.copy2(legacy_paths["facts"], user_paths["facts"])
            print(f"[UserManager] Migrated facts.json")

        # Migrate intimacy_layers.json
        if legacy_paths["intimacy_layers"].exists() and not user_paths["intimacy_layers"].exists():
            shutil.copy2(legacy_paths["intimacy_layers"], user_paths["intimacy_layers"])
            print(f"[UserManager] Migrated intimacy_layers.json")

        # Migrate content_unlocks.json
        if legacy_paths["content_unlocks"].exists() and not user_paths["content_unlocks"].exists():
            shutil.copy2(legacy_paths["content_unlocks"], user_paths["content_unlocks"])
            print(f"[UserManager] Migrated content_unlocks.json")

        # Migrate summaries
        if legacy_paths["summaries"].exists():
            for summary_file in legacy_paths["summaries"].glob("*.json"):
                dest = user_paths["summaries"] / summary_file.name
                if not dest.exists():
                    shutil.copy2(summary_file, dest)
                    print(f"[UserManager] Migrated summary: {summary_file.name}")

        print(f"[UserManager] Migration complete for user {owner_id}")

    # -------------------------------------------------------------------------
    # User Stats
    # -------------------------------------------------------------------------

    def get_user_stats(self, user_id: str) -> Dict[str, Any]:
        """
        Get statistics for a user.

        Args:
            user_id: The user's Telegram ID

        Returns:
            Dictionary with user statistics
        """
        paths = self.get_user_paths(user_id)

        stats = {
            "user_id": user_id,
            "exists": self.user_exists(user_id),
            "has_facts": paths["facts"].exists(),
            "has_intimacy": paths["intimacy_layers"].exists(),
            "has_unlocks": paths["content_unlocks"].exists(),
            "conversation_files": 0,
            "summary_files": 0,
        }

        if paths["conversations"].exists():
            stats["conversation_files"] = len(list(paths["conversations"].glob("*.jsonl")))

        if paths["summaries"].exists():
            stats["summary_files"] = len(list(paths["summaries"].glob("*.json")))

        return stats


# Global singleton instance
_user_manager: Optional[UserManager] = None


def get_user_manager(base_path: Path = None) -> UserManager:
    """
    Get the global UserManager instance.

    Args:
        base_path: Base path for data storage (only used on first call)

    Returns:
        The UserManager singleton
    """
    global _user_manager
    if _user_manager is None:
        _user_manager = UserManager(base_path)
    return _user_manager


def is_advanced_enabled() -> bool:
    """
    Convenience function to check if advanced mode is enabled.

    Returns:
        True if advanced mode is enabled
    """
    return get_user_manager().is_advanced_enabled()
