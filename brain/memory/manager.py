"""Brain: Memory Manager - coordinates all memory subsystems"""
import asyncio
from pathlib import Path
from typing import Optional
from .working import WorkingMemory
from .episodic import EpisodicMemory
from .vector_store import VectorMemoryStore
from .fact_extractor import FactExtractor
from .summarizer import ConversationSummarizer
from .index import MemoryIndex


class Memory:
    """Memory manager - coordinates all memory systems for a specific user"""

    def __init__(self, nervous, data_path, embedding_service=None, user_id: str = "default", bot_id: str = "alive_ai"):
        """
        Initialize memory for a specific user.

        Args:
            nervous: The nervous system for events
            data_path: Base path for data storage
            embedding_service: Optional embedding service for vector store
            user_id: The user's Telegram ID for per-user memory isolation
            bot_id: The Bot instance ID for per-tenant memory isolation
        """
        self.nervous = nervous
        self.user_id = user_id
        self.data_path = Path(data_path)
        self.data_path.mkdir(parents=True, exist_ok=True)

        from . import SemanticMemory
        self.index = MemoryIndex(self.data_path)
        self.working = WorkingMemory()
        self.episodic = EpisodicMemory(self.data_path, user_id=user_id)
        self.semantic = SemanticMemory(self.data_path, user_id=user_id)
        self.agent_name = str(bot_id or "AI")
        self.fact_extractor = FactExtractor(self.data_path / "facts.json", agent_name=self.agent_name)
        self.summarizer = ConversationSummarizer(self.data_path, agent_name=self.agent_name)
        self.vector_store = None
        self.openmind = None
        self.bot_id = bot_id.lower()
        if embedding_service and VectorMemoryStore.enabled():
            self.vector_store = VectorMemoryStore(embedding_service, user_id=user_id, bot_id=bot_id)
            if self.vector_store.connect():
                print(f"[Memory] Vector store ready for user {user_id} on bot {bot_id}! {self.vector_store.count()} memories")
        try:
            from .openmind import OpenMindMemoryBridge
            if OpenMindMemoryBridge.enabled():
                self.openmind = OpenMindMemoryBridge(nervous, user_id=user_id, bot_id=bot_id)
                print(f"[Memory] OpenMind bridge enabled for user {user_id} on bot {bot_id}")
        except Exception as e:
            print(f"[Memory] OpenMind bridge unavailable: {e}")
        self.turn_count = 0
        nervous.on("memory_save", self._on_save)

    def set_llm(self, fast_llm):
        self.fact_extractor.set_llm(fast_llm)
        self.summarizer.set_llm(fast_llm)

    def _on_save(self, data: dict):
        if data.get("type") != "conversation":
            return

        # Check if this event is for this user (for per-user isolation)
        event_user_id = data.get("user_id")
        if event_user_id and event_user_id != self.user_id:
            return  # Not for this user, skip

        user_msg, ai_msg = data.get("user_message", ""), data.get("ai_response", "")
        emotion = data.get("emotion", {})
        is_proactive = emotion.get("proactive", False)

        # For proactive messages, only save AI response (no user message)
        if is_proactive and not user_msg:
            self.working.add("assistant", ai_msg)
            # Also save to episodic so it persists across restarts
            self.episodic.save_proactive(ai_msg, emotion)
            print(f"[Memory] Saved PROACTIVE message to working + episodic for user {self.user_id}")
            return

        self.episodic.save(user_msg, ai_msg, emotion)
        self.working.add("user", user_msg)
        self.working.add("assistant", ai_msg)
        print(f"[Memory] Saved to working memory (now {len(self.working)} items) | User: {user_msg[:30]}...")
        if self.vector_store:
            self.vector_store.store("user", user_msg, {"emotion": emotion})
            self.vector_store.store("assistant", ai_msg, {"emotion": emotion})
        self.fact_extractor.add_turn(user_msg, ai_msg)
        self.summarizer.add_turn(user_msg, ai_msg)
        if self.fact_extractor.should_extract():
            asyncio.ensure_future(self._run_extraction())
        if self.summarizer.should_summarize():
            asyncio.ensure_future(self.summarizer.summarize())
        if emotion.get("is_high_desire") or emotion.get("desire", 0) > 0.6:
            self.semantic.update_last_intimate()
        self.turn_count += 1
        if self.turn_count % 50 == 0 and self.vector_store:
            self.vector_store.archive_old_memories(max_in_redis=500)

    async def _run_extraction(self):
        try:
            await self.fact_extractor.extract_and_merge()
            self.semantic.facts = self.semantic._load()
        except Exception as e:
            print(f"[Memory] Fact extraction error (non-fatal): {e}")

    def search_relevant_memories(self, query: str, limit: int = 5) -> str:
        if not self.vector_store:
            return ""
        memories = self.vector_store.search(query, limit=limit)
        if not memories:
            return ""
        return "\n".join(
            f"{'He said' if m.get('role')=='user' else 'You said'}: {m.get('content','')}"
            for m in memories)

    async def build_context(self, max_tokens: int = None, current_message: str = "") -> tuple:
        import os
        if max_tokens is None:
            max_tokens = int(os.environ.get("LLM_CONTEXT_TOKENS", "500"))
        facts_parts = []
        if self.semantic.is_new_user:
            facts_parts.append("[NEW USER - You don't know him yet. Be curious, ask about him. "
                               "Do NOT pretend you know him or missed him.]")
        semantic_ctx = self.semantic.get_context()
        if semantic_ctx:
            facts_parts.append(semantic_ctx)
        summaries = self.summarizer.get_recent_summaries(limit=3)
        if summaries:
            facts_parts.append(summaries)
        related = ""
        if current_message and self.vector_store:
            related = self.search_relevant_memories(current_message, limit=3)
        if current_message and self.openmind:
            openmind_related = await self.openmind.search_context(current_message, limit=3)
            if openmind_related:
                related = (
                    f"{related}\n\nOpenMind long-term memory:\n{openmind_related}"
                    if related else
                    f"OpenMind long-term memory:\n{openmind_related}"
                )

        # Get working memory (empty after restart)
        history = self.working.get_history()
        print(f"[Memory] Working memory items: {len(history)}")

        # IMPORTANT: Always load from episodic if working memory is empty
        # This ensures conversation context persists across restarts
        if not history:
            # Load more entries to match working memory capacity (14 items = 7 turns)
            recent = self.episodic.load_recent(limit=10)
            for e in recent:
                # For proactive messages (empty user), only add assistant message
                if e.get("user"):
                    history.append({"role": "user", "content": e["user"]})
                history.append({"role": "assistant", "content": e["ai"]})
            if history:
                print(f"[Memory] Loaded {len(history)} messages from episodic storage (restart recovery)")
        else:
            print(f"[Memory] Using working memory directly ({len(history)} items)")

        context = {
            "facts_context": "\n".join(facts_parts),
            "conversation_history": history,
            "related_memories": related,
        }
        return context, self.semantic.get_random_pet_name()
