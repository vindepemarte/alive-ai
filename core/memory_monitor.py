"""
Core: Memory Monitor
Monitors memory usage and triggers cleanup before OOM crashes.
"""

import gc
import os
import psutil
from typing import Optional, Callable


class MemoryMonitor:
    """
    Monitors system memory and triggers cleanup when approaching limits.

    Usage:
        monitor = MemoryMonitor(max_memory_gb=5.0)
        monitor.check()  # Call periodically
    """

    def __init__(
        self,
        max_memory_gb: float = 5.0,
        warning_threshold: float = 0.75,  # Warn at 75%
        critical_threshold: float = 0.90,  # Force cleanup at 90%
        on_warning: Optional[Callable] = None,
        on_critical: Optional[Callable] = None
    ):
        self.max_memory_gb = max_memory_gb
        self.warning_threshold = warning_threshold
        self.critical_threshold = critical_threshold
        self.on_warning = on_warning
        self.on_critical = on_critical

        self._last_warning_time = 0
        self._warning_cooldown = 300  # 5 minutes between warnings

    def get_memory_info(self) -> dict:
        """Get current memory usage info"""
        process = psutil.Process(os.getpid())
        system_mem = psutil.virtual_memory()
        process_rss_gb = process.memory_info().rss / (1024**3)

        return {
            # Process memory
            "process_rss_gb": process_rss_gb,
            "process_percent": process.memory_percent(),

            # System memory
            "system_total_gb": system_mem.total / (1024**3),
            "system_used_gb": system_mem.used / (1024**3),
            "system_available_gb": system_mem.available / (1024**3),
            "system_percent": system_mem.percent,

            # Our limit (based on PROCESS memory, not system)
            "limit_gb": self.max_memory_gb,
            "usage_of_limit": process_rss_gb / self.max_memory_gb,
        }

    def check(self) -> dict:
        """
        Check memory and trigger cleanup if needed.

        Returns:
            Dict with status and actions taken
        """
        info = self.get_memory_info()
        usage_ratio = info["usage_of_limit"]
        result = {
            "info": info,
            "status": "ok",
            "actions": []
        }

        if usage_ratio >= self.critical_threshold:
            # CRITICAL - Force aggressive cleanup
            result["status"] = "critical"
            print(f"[Memory] ⚠️ CRITICAL: Memory at {usage_ratio*100:.1f}% of limit!")

            # Force garbage collection
            collected = gc.collect(2)  # Full collection
            result["actions"].append(f"gc_collected_{collected}")

            # Clear caches if callback provided (only call once)
            if self.on_critical:
                try:
                    self.on_critical()
                    result["actions"].append("critical_cleanup")
                except Exception as e:
                    print(f"[Memory] Critical cleanup error: {e}")

        elif usage_ratio >= self.warning_threshold:
            # WARNING - Gentle cleanup
            import time
            current_time = time.time()

            if current_time - self._last_warning_time > self._warning_cooldown:
                result["status"] = "warning"
                print(f"[Memory] ⚡ WARNING: Memory at {usage_ratio*100:.1f}% of limit")

                # Light garbage collection
                collected = gc.collect(1)
                result["actions"].append(f"gc_collected_{collected}")

                # Clear caches if callback provided
                if self.on_warning:
                    try:
                        self.on_warning()
                        result["actions"].append("warning_cleanup")
                    except Exception as e:
                        print(f"[Memory] Warning cleanup error: {e}")

                self._last_warning_time = current_time

        return result

    def force_cleanup(self) -> int:
        """
        Force aggressive memory cleanup.

        Returns:
            Number of objects collected
        """
        print("[Memory] Forcing aggressive cleanup...")
        collected = gc.collect(2)
        gc.collect()  # Run again to clean circular refs

        # Get memory after cleanup
        info = self.get_memory_info()
        print(f"[Memory] After cleanup: {info['process_rss_gb']:.2f}GB process, {info['system_used_gb']:.2f}GB system")

        return collected


def clear_alive_ai_caches():
    """Clear all Alive-AI caches to free memory"""
    total_cleared = 0

    # Clear message handler caches
    try:
        from core.message_handler import _user_memories, _recent_openings, _message_queue
        count = len(_user_memories)
        _user_memories.clear()
        total_cleared += count
        print(f"[Memory] Cleared {count} cached user memories")
        count = len(_recent_openings)
        _recent_openings.clear()
        total_cleared += count
        count = len(_message_queue)
        _message_queue.clear()
        total_cleared += count
    except Exception as e:
        print(f"[Memory] Could not clear message handler caches: {e}")

    # Clear embedding caches if possible
    try:
        from brain.embeddings import get_embedding_service
        service = get_embedding_service()
        if hasattr(service, '_cache'):
            cache_len = len(service._cache) if hasattr(service._cache, '__len__') else 0
            service._cache.clear()
            total_cleared += cache_len
            print(f"[Memory] Cleared embedding cache ({cache_len} items)")
    except Exception:
        pass

    # Clear emotional memory instances
    try:
        from brain.emotional_memory import _instances
        count = len(_instances)
        _instances.clear()
        total_cleared += count
        print(f"[Memory] Cleared {count} emotional memory instances")
    except Exception:
        pass

    # Clear fact extractor buffers
    try:
        from brain.memory.fact_extractor import FactExtractor
        # Instance-based, would need global registry
    except Exception:
        pass

    return total_cleared


# Global monitor instance
_monitor: Optional[MemoryMonitor] = None


def get_memory_monitor(max_memory_gb: float = 5.0) -> MemoryMonitor:
    """Get or create the global memory monitor"""
    global _monitor
    if _monitor is None:
        _monitor = MemoryMonitor(
            max_memory_gb=max_memory_gb,
            on_warning=clear_alive_ai_caches,
            on_critical=clear_alive_ai_caches
        )
    return _monitor
