"""
Core path helpers.

Alive-AI can run from Docker at /app or from an npm-created project folder.
All runtime state must resolve through this module so local installs never try
to write into a read-only container path.
"""

import os
from pathlib import Path


def project_root() -> Path:
    configured = os.environ.get("ALIVE_AI_ROOT")
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(__file__).parent.parent.resolve()


def _resolve_under_root(value: str) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = project_root() / path
    return path.resolve()


def data_dir() -> Path:
    configured = os.environ.get("ALIVE_AI_DATA_PATH") or os.environ.get("DATA_PATH")
    path = _resolve_under_root(configured) if configured else project_root() / "data"
    path.mkdir(parents=True, exist_ok=True)
    return path


def state_file(name: str) -> Path:
    return data_dir() / name


def media_dir(name: str) -> Path:
    path = project_root() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def cache_dir(name: str = "") -> Path:
    base = project_root() / ".cache"
    path = base / name if name else base
    path.mkdir(parents=True, exist_ok=True)
    return path
