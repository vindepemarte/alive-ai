"""
Core: Hot Reload System
Watches for file changes and reloads modules safely
"""

import os
import time
import asyncio
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


class HotReloader:
    """Hot reload with guardrails - waits for operations to finish"""

    def __init__(self, nervous_system):
        self.nervous = nervous_system
        self.lock = threading.Lock()  # Acquired during message processing
        self.busy = False
        self.last_reload = 0
        self.debounce_seconds = 2  # Wait 2s after last change
        self.pending_reload = False
        self.observer = None
        self.watched_dirs = ["core", "brain", "heart", "config", "input", "output"]
        self.base_path = Path("/app")

    def start(self):
        """Start watching for file changes"""
        handler = ReloadHandler(self)
        self.observer = Observer()

        for dir_name in self.watched_dirs:
            dir_path = self.base_path / dir_name
            if dir_path.exists():
                self.observer.schedule(handler, str(dir_path), recursive=True)
                print(f"[HotReload] Watching {dir_name}/")

        self.observer.start()
        print("[HotReload] Active - change files to reload")

    def stop(self):
        if self.observer:
            self.observer.stop()
            self.observer.join()

    def mark_busy(self):
        """Call when starting an operation"""
        self.lock.acquire()
        self.busy = True

    def mark_idle(self):
        """Call when operation finishes - safe to call even if lock not held"""
        self.busy = False
        try:
            self.lock.release()
        except RuntimeError:
            pass  # Lock wasn't held, that's OK
        # Check if reload was pending
        if self.pending_reload:
            self.pending_reload = False
            threading.Thread(target=self._delayed_reload, daemon=True).start()

    def request_reload(self, filepath: str):
        """Request a reload - will wait if busy"""
        now = time.time()
        if now - self.last_reload < self.debounce_seconds:
            return  # Too soon, debounce

        print(f"[HotReload] Change detected: {filepath}")

        if self.busy:
            print("[HotReload] Busy - will reload after current operation")
            self.pending_reload = True
            return

        threading.Thread(target=self._delayed_reload, daemon=True).start()

    def _delayed_reload(self):
        """Reload after debounce period"""
        time.sleep(self.debounce_seconds)

        if self.busy:
            self.pending_reload = True
            return

        self._do_reload()

    def _do_reload(self):
        """Actually reload modules"""
        self.last_reload = time.time()
        print("[HotReload] Reloading modules...")

        # Reload settings.json into environment
        self._reload_settings()

        # Clear directives cache so it reloads from file
        try:
            from core.directives import clear_cache
            clear_cache()
        except ImportError:
            pass

        # Get the main event loop (safe for threads)
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None

        # Emit reload event so modules can clean up
        if loop and self.nervous:
            asyncio.run_coroutine_threadsafe(
                self.nervous.emit("hot_reload", {"timestamp": self.last_reload}),
                loop
            )

        # Reload instructions.md if changed
        instructions_path = self.base_path / "config" / "instructions.md"
        if instructions_path.exists():
            # The message_handler reads this fresh each time, so no reload needed
            print("[HotReload] instructions.md will be picked up on next message")

        print("[HotReload] Done - changes apply to next message")

    def _reload_settings(self):
        """Reload settings.json into environment variables"""
        import json
        settings_path = self.base_path / "config" / "settings.json"
        if not settings_path.exists():
            return

        try:
            settings = json.loads(settings_path.read_text())
            count = 0
            for key, value in settings.items():
                if key.startswith("_"):
                    continue
                if isinstance(value, bool):
                    os.environ[key] = "true" if value else "false"
                elif value is not None:
                    os.environ[key] = str(value)
                count += 1
            print(f"[HotReload] Reloaded {count} settings into environment")
        except Exception as e:
            print(f"[HotReload] Error reloading settings: {e}")


class ReloadHandler(FileSystemEventHandler):
    """Handle file change events"""

    def __init__(self, reloader: HotReloader):
        self.reloader = reloader
        self.extensions = {".py", ".md", ".json"}

    def on_modified(self, event: FileModifiedEvent):
        if event.is_directory:
            return

        path = Path(event.src_path)

        # Only reload relevant files
        if path.suffix not in self.extensions:
            return

        # Skip __pycache__ and temp files
        if "__pycache__" in str(path) or path.name.startswith("."):
            return

        # Skip data files (memories, etc) - we don't want to reload on those
        if "data/" in str(path) or "mypics/" in str(path) or "myvids/" in str(path):
            return

        self.reloader.request_reload(str(path.name))
