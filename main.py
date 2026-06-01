"""
Alive-AI runtime entrypoint.

Run with:
    npx alive-ai start
or:
    python main.py
"""

import asyncio
import argparse
import json
import os
import sys
from pathlib import Path


ROOT = Path(__file__).parent.resolve()


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        if key.strip():
            os.environ.setdefault(key.strip(), value.strip())


def load_settings_to_env(path: Path) -> dict:
    if not path.exists():
        return {}
    settings = json.loads(path.read_text())
    for key, value in settings.items():
        if key.startswith("_"):
            continue
        if isinstance(value, dict):
            continue
        if isinstance(value, bool):
            os.environ[key] = "true" if value else "false"
        elif value is not None:
            os.environ[key] = str(value)
    return settings


def ensure_config() -> dict:
    config_dir = ROOT / "config"
    settings_path = config_dir / "settings.json"
    missing = [
        name for name in ("settings.json", "self.json", "directives.json", "instructions.md")
        if not (config_dir / name).exists()
    ]
    if missing:
        print("Alive-AI is not configured yet.")
        print(f"Missing: {', '.join('config/' + name for name in missing)}")
        print("Run: npx alive-ai setup")
        sys.exit(2)
    return load_settings_to_env(settings_path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Alive-AI local runtime.")
    parser.add_argument(
        "--input",
        choices=["telegram", "terminal"],
        default=None,
        help="Input channel to use for this run.",
    )
    return parser.parse_args()


async def main() -> None:
    args = parse_args()
    load_env_file(ROOT / ".env")
    load_env_file(ROOT / "config" / "secrets.env")
    settings = ensure_config()

    from core.self import Self

    ai = Self(ROOT)
    webui_enabled = str(settings.get("WEBUI_ENABLED", os.environ.get("WEBUI_ENABLED", "true"))).lower() != "false"
    webui_port = int(settings.get("WEBUI_PORT", os.environ.get("WEBUI_PORT", "8080")))

    if webui_enabled:
        try:
            from webui.bridge import init_bridge, init_soul_bridge, start_webui

            init_bridge(ai.nervous)
            if hasattr(ai, "_heart") and ai._heart and hasattr(ai._heart, "soul"):
                init_soul_bridge(ai._heart.soul)
            asyncio.create_task(start_webui(host="127.0.0.1", port=webui_port))
            print(f"[Alive-AI] Dashboard running at http://127.0.0.1:{webui_port}")
        except Exception as exc:
            print(f"[Alive-AI] WebUI unavailable: {exc}")

    input_channel = args.input or os.environ.get("ALIVE_AI_INPUT_CHANNEL") or settings.get("INPUT_CHANNEL", "telegram")
    await ai.start(input_channel=input_channel)


if __name__ == "__main__":
    asyncio.run(main())
