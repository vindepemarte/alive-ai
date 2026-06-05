"""
Brain: Subconscious - Actions
Action handling for impulses — uses full character voice
"""

import os
from datetime import datetime
from typing import Callable

from core.proactive_safety import sanitize_proactive_message

from .impulses import Impulse, ImpulseType

_INSTRUCTIONS_CACHE = None


def _load_instructions() -> str:
    """Load instructions.md once, cache it"""
    global _INSTRUCTIONS_CACHE
    if _INSTRUCTIONS_CACHE is not None:
        return _INSTRUCTIONS_CACHE
    try:
        path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "instructions.md")
        with open(os.path.normpath(path), "r") as f:
            _INSTRUCTIONS_CACHE = f.read()
    except Exception:
        _INSTRUCTIONS_CACHE = ""
    return _INSTRUCTIONS_CACHE


def _get_user_facts(nervous) -> str:
    """Try to pull user facts from SemanticMemory via nervous system"""
    try:
        memory = getattr(nervous, "_memory", None) or getattr(nervous, "memory", None)
        if memory and hasattr(memory, "semantic"):
            return memory.semantic.get_context() or ""
    except Exception:
        pass
    return ""


def _get_recent_conversation_context(nervous, user_id: str = None) -> str:
    """Get recent conversation topics for contextual follow-ups"""
    try:
        memory = getattr(nervous, "_memory", None) or getattr(nervous, "memory", None)
        if memory:
            # Try to get recent conversation context
            if hasattr(memory, 'get_recent_context'):
                return memory.get_recent_context(user_id, limit=3) or ""
            # Fallback: try working memory
            if hasattr(memory, 'working') and memory.working:
                items = memory.working.get_items()[:3] if hasattr(memory.working, 'get_items') else []
                if items:
                    return "\n".join([str(i)[:100] for i in items])
    except Exception:
        pass
    return ""


class ActionHandler:
    """Handles acting on impulses"""

    def __init__(self, nervous, llm=None, fast_llm=None, on_impulse: Callable = None):
        self.nervous = nervous
        self.llm = llm
        self.fast_llm = fast_llm
        self.on_impulse = on_impulse
        self.recent_actions = []

    async def act_on_impulse(self, impulse: Impulse, working_memory) -> None:
        print(f"[Subconscious] Acting on impulse: {impulse.action_hint}")
        if working_memory.thoughts:
            working_memory.mark_acted(working_memory.thoughts[-1])
        self.recent_actions.append((datetime.now(), impulse.action_hint))
        if len(self.recent_actions) > 20:
            self.recent_actions.pop(0)
        if self.on_impulse:
            await self.on_impulse(impulse)
        await self.nervous.emit("subconscious_impulse", {
            "impulse_type": impulse.type.value, "strength": impulse.strength,
            "thought": impulse.thought, "action_hint": impulse.action_hint
        })

    async def generate_proactive_message(self, impulse: Impulse, working_memory) -> str:
        if not self.fast_llm:
            return ""

        instructions = _load_instructions()
        user_facts = _get_user_facts(self.nervous)
        inner_context = working_memory.get_context_string()
        recent_context = _get_recent_conversation_context(self.nervous)

        system = instructions or (
            "You are the configured identity inside Alive-AI. Use only the provided state, "
            "memory, and relationship context; do not assume romance or familiarity."
        )
        if user_facts:
            system += f"\n\nWhat you know about him:\n{user_facts}"
        if inner_context:
            system += f"\n\nYour inner state right now:\n{inner_context}"
        if recent_context:
            system += f"\n\nRecent things you talked about:\n{recent_context}"
        else:
            system += "\n\nNo recent conversation context available."

        user_prompt = (
            f"You're feeling a {impulse.type.value} impulse. "
            f"Inner thought: \"{impulse.thought}\"\n"
            "Decide whether this impulse should become an outward message right now.\n"
            "Return exactly SILENCE if it does not genuinely fit the current state, relationship, or context.\n"
            "If you send text, let the impulse, memory, emotion, and recent context decide it.\n"
            "Never invent or hallucinate specific events, objects, or topics. Only reference what's in the context above."
        )
        try:
            response = await self.fast_llm.chat(
                messages=[{"role": "system", "content": system},
                          {"role": "user", "content": user_prompt}],
                max_tokens=None, temperature=0.7
            )
            if response:
                if str(response).strip().upper() == "SILENCE":
                    return ""
                message = sanitize_proactive_message(response)
                if message:
                    return message
        except Exception as e:
            print(f"[Subconscious] Error generating message: {e}")
        return ""

    def can_act_now(self, working_memory, min_interval_minutes: float = 30) -> bool:
        return working_memory.can_act_now(min_interval_minutes)
