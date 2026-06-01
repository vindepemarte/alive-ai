"""
Core: Events - Nervous System
Connects all modules via events. No module depends directly on another.
"""

from typing import Callable, Dict, List
import asyncio
import traceback

class NervousSystem:
    """Central nervous system - event bus"""

    def __init__(self):
        self.listeners: Dict[str, List[Callable]] = {}
        self.heart = None  # Reference for reactions

    def on(self, event: str, callback: Callable):
        """Register listener for event"""
        if event not in self.listeners:
            self.listeners[event] = []
        self.listeners[event].append(callback)

    async def emit(self, event: str, data: dict = None):
        """Emit event to all listeners"""
        if event in self.listeners:
            for cb in self.listeners[event]:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb(data or {})
                    else:
                        result = cb(data or {})
                        # Handle sync lambda that returns coroutine
                        if asyncio.iscoroutine(result):
                            await result
                except Exception as e:
                    print(f"[NervousSystem] Error in {event}: {e}")
                    traceback.print_exc()

# System events:
# - message_received   -> New message from user
# - thinking_start     -> Started thinking
# - thinking_done      -> Finished thinking
# - emotion_update     -> Emotional state changed
# - memory_save        -> Save to memory
# - send_text          -> Send text response
# - send_voice         -> Send voice message
# - send_image         -> Send image
# - send_reaction      -> Send emoji reaction
# - timer_tick         -> Minute tick (for decay)
# - self_modify        -> Self-modification request
