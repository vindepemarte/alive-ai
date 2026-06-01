"""
Core: Settings - Hot-reloadable configuration
settings.json is the SINGLE SOURCE OF TRUTH for all runtime settings.
Changes take effect immediately (file is mounted in Docker).
"""

import json
from contextvars import ContextVar
from pathlib import Path
from typing import Any

# Default path (used outside of specific Self instances)
DEFAULT_SETTINGS_PATH = Path(__file__).parent.parent / "config" / "settings.json"

# Context-local settings path for multi-bot support
# Each bot instance will set this in its async task context
ACTIVE_SETTINGS_PATH: ContextVar[Path] = ContextVar("ACTIVE_SETTINGS_PATH", default=DEFAULT_SETTINGS_PATH)

# Note: We are deprecating the global cache because multiple bots 
# can be running with different paths at the same time.
# Instead, we cache per-path in a global dictionary.
_settings_caches = {}  # Dict[Path, dict]
_last_mtimes = {}      # Dict[Path, float]


def _get_active_path() -> Path:
    """Helper to get the current context's settings file"""
    try:
        return ACTIVE_SETTINGS_PATH.get()
    except LookupError:
        return DEFAULT_SETTINGS_PATH

def _load_settings(path: Path) -> dict:
    """Load settings from settings.json (hot-reloadable)"""
    if not path.exists():
        return {}
    try:
        with open(path) as f:
            return json.load(f)
    except Exception as e:
        print(f"[Settings] Error loading {path}: {e}")
        return {}


def _save_settings(path: Path, settings: dict):
    """Save settings to settings.json"""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"[Settings] Error saving {path}: {e}")


def _reload_if_changed(path: Path):
    """Check if file changed and clear its cache"""
    global _settings_caches, _last_mtimes
    try:
        current_mtime = path.stat().st_mtime if path.exists() else 0
        if current_mtime != _last_mtimes.get(path, 0):
            _settings_caches[path] = None
            _last_mtimes[path] = current_mtime
    except Exception:
        pass


def get(key: str, default: Any = None) -> Any:
    """Get setting value (hot-reloadable from active active settings.json)"""
    global _settings_caches

    path = _get_active_path()
    _reload_if_changed(path)

    if _settings_caches.get(path) is None:
        _settings_caches[path] = _load_settings(path)

    return _settings_caches[path].get(key, default)


def get_float(key: str, default: float = 0.0) -> float:
    """Get setting as float"""
    val = get(key, default)
    try:
        return float(val)
    except (ValueError, TypeError):
        return default


def get_int(key: str, default: int = 0) -> int:
    """Get setting as integer"""
    val = get(key, default)
    try:
        return int(val)
    except (ValueError, TypeError):
        return default


def get_percent(key: str, default: int = 50) -> float:
    """
    Get setting as percentage (0-100) and convert to multiplier (0.0-1.0).
    0% = very slow/hard, 100% = instant/max
    """
    val = get_int(key, default)
    return val / 100.0


def set_value(key: str, value: Any):
    """Set a setting (immediately saved to active settings.json)"""
    global _settings_caches

    path = _get_active_path()
    settings = _load_settings(path)
    settings[key] = value
    _save_settings(path, settings)
    _settings_caches[path] = None  # Force reload
    print(f"[Settings] Updated {key} = {value} in {path.name}")


def get_all() -> dict:
    """Get all current settings"""
    global _settings_caches
    
    path = _get_active_path()
    _reload_if_changed(path)
    
    if _settings_caches.get(path) is None:
        _settings_caches[path] = _load_settings(path)
    return _settings_caches[path].copy()


# Keep old function names for compatibility
set_runtime = set_value


# ============================================================
# Convenience functions
# ============================================================

def get_emotion_multiplier(emotion: str) -> float:
    """Get multiplier for emotion rate (0-100% -> 0.0-1.0)"""
    key = f"EMOTION_RATE_{emotion.upper()}"
    return get_percent(key, 50)


def get_media_cooldown(media_type: str) -> int:
    """Get cooldown in seconds for media type"""
    key = f"MEDIA_COOLDOWN_{media_type.upper()}"
    defaults = {"PHOTO": 300, "VIDEO": 600, "VOICE": 120}
    return get_int(key, defaults.get(media_type.upper(), 300))


def get_media_session_limit(media_type: str) -> int:
    """Get session limit for media type"""
    key = f"MEDIA_SESSION_LIMIT_{media_type.upper()}"
    defaults = {"PHOTO": 5, "VIDEO": 3, "VOICE": 10}
    return get_int(key, defaults.get(media_type.upper(), 5))


def get_random_chance(context: str) -> float:
    """Get random chance as multiplier (0-100% -> 0.0-1.0)"""
    key = f"RANDOM_CHANCE_{context.upper()}"
    return get_percent(key, 8)


def get_trigger_boost(trigger_type: str) -> float:
    """Get boost multiplier for triggers (0-100% -> 0.0-1.0)"""
    key = f"TRIGGER_BOOST_{trigger_type.upper()}"
    return get_percent(key, 100)

