"""
Alive-AI runtime entrypoint.

Run with:
    npx alive-ai start
or:
    python main.py
"""

import asyncio
import argparse
import contextlib
import json
import os
import signal
import sys
import traceback
from pathlib import Path


ROOT = Path(__file__).parent.resolve()
os.environ.setdefault("ALIVE_AI_ROOT", str(ROOT))
os.environ.setdefault("ALIVE_AI_DATA_PATH", str(ROOT / "data"))
os.environ.setdefault("DATA_PATH", str(ROOT / "data"))
os.environ.setdefault("HF_HOME", str(ROOT / ".cache" / "huggingface"))
os.environ.setdefault("SENTENCE_TRANSFORMERS_HOME", str(ROOT / ".cache" / "sentence-transformers"))
os.environ.setdefault("TRANSFORMERS_CACHE", str(ROOT / ".cache" / "huggingface"))
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")


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
    webui_task = None
    runtime_task = None
    stop_task = None
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def request_stop(signame: str) -> None:
        if stop_event.is_set():
            return
        print(f"\n[Alive-AI] Stopping ({signame})...")
        stop_event.set()

    signal_handlers = []
    for signame in ("SIGINT", "SIGTERM"):
        signum = getattr(signal, signame, None)
        if signum is None:
            continue
        try:
            loop.add_signal_handler(signum, request_stop, signame)
            signal_handlers.append(signum)
        except (NotImplementedError, RuntimeError, ValueError):
            pass

    webui_enabled = str(settings.get("WEBUI_ENABLED", os.environ.get("WEBUI_ENABLED", "true"))).lower() != "false"
    webui_port = int(settings.get("WEBUI_PORT", os.environ.get("WEBUI_PORT", "8080")))

    try:
        if webui_enabled:
            try:
                from webui.bridge import init_bridge, init_soul_bridge, start_webui

                init_bridge(ai.nervous)
                if hasattr(ai, "_heart") and ai._heart and hasattr(ai._heart, "soul"):
                    init_soul_bridge(ai._heart.soul)
                webui_task = asyncio.create_task(start_webui(host="127.0.0.1", port=webui_port))
                print(f"[Alive-AI] Dashboard running at http://127.0.0.1:{webui_port}")
            except Exception as exc:
                print(f"[Alive-AI] WebUI unavailable: {exc}")

        input_channel = args.input or os.environ.get("ALIVE_AI_INPUT_CHANNEL") or settings.get("INPUT_CHANNEL", "telegram")
        runtime_task = asyncio.create_task(ai.start(input_channel=input_channel))
        stop_task = asyncio.create_task(stop_event.wait())
        done, _pending = await asyncio.wait(
            {runtime_task, stop_task},
            return_when=asyncio.FIRST_COMPLETED,
        )

        if stop_task in done:
            if runtime_task and not runtime_task.done():
                runtime_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await runtime_task
            return

        if stop_task and not stop_task.done():
            stop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await stop_task
        await runtime_task
    except KeyboardInterrupt:
        print("\n[Alive-AI] Stopping...")
    except Exception as exc:
        if os.environ.get("ALIVE_AI_DEBUG") == "1":
            traceback.print_exc()
        else:
            print(f"[Alive-AI] Runtime stopped: {exc}")
            if exc.__class__.__module__.startswith("telegram") or "telegram" in str(exc).lower():
                print("[Alive-AI] Telegram could not start. Check the bot token/network, or run `npx . chat` for terminal mode.")
        sys.exit(1)
    finally:
        for signum in signal_handlers:
            with contextlib.suppress(Exception):
                loop.remove_signal_handler(signum)
        if stop_task and not stop_task.done():
            stop_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await stop_task
        if runtime_task and not runtime_task.done():
            runtime_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await runtime_task
        with contextlib.suppress(Exception):
            await ai.stop()
        if webui_task:
            with contextlib.suppress(Exception):
                from webui.bridge import stop_webui
                await stop_webui()
            if not webui_task.done():
                webui_task.cancel()
                with contextlib.suppress(asyncio.CancelledError):
                    await webui_task


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Alive-AI] Stopped.")
