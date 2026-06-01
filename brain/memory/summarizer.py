"""
Brain: Memory - Conversation Summarizer
Periodically summarizes conversations to preserve long-term context
"""

import json
from datetime import datetime
from pathlib import Path

def build_summarize_prompt(agent_name: str) -> str:
    agent = agent_name or "the AI"
    return f"""Summarize this conversation between {agent} (AI companion) and her boyfriend.
Focus on: key topics discussed, emotional moments, important things he shared,
any promises or plans made, and the overall mood/vibe.
Keep it concise (3-5 sentences). Write from {agent}'s perspective."""


class ConversationSummarizer:
    """Summarizes conversations every N messages for long-term memory"""

    def __init__(self, data_path: Path, agent_name: str = "AI"):
        self.summaries_path = data_path / "summaries"
        self.summaries_path.mkdir(parents=True, exist_ok=True)
        self.agent_name = str(agent_name or "AI")
        self._llm = None
        self._turn_buffer = []
        self._summarize_every = 20
        self._total_turns = 0

    def set_llm(self, llm):
        """Set the fast LLM client"""
        self._llm = llm

    def add_turn(self, user_msg: str, ai_msg: str):
        """Buffer a conversation turn"""
        self._turn_buffer.append({"user": user_msg, "ai": ai_msg})
        self._total_turns += 1

    def should_summarize(self) -> bool:
        """Check if we have enough turns to summarize"""
        return len(self._turn_buffer) >= self._summarize_every

    async def summarize(self) -> str:
        """Summarize buffered turns and save to disk"""
        if not self._llm or not self._turn_buffer:
            return ""

        lines = []
        for turn in self._turn_buffer:
            lines.append(f"Him: {turn['user']}")
            lines.append(f"{self.agent_name}: {turn['ai']}")
        conversation = "\n".join(lines)

        try:
            messages = [
                {"role": "system", "content": build_summarize_prompt(self.agent_name)},
                {"role": "user", "content": conversation}
            ]
            summary = await self._llm.chat(messages, max_tokens=300, temperature=0.3)
            if not summary:
                return ""
        except Exception as e:
            print(f"[Summarizer] LLM error: {e}")
            return ""

        # Save summary to dated file
        now = datetime.now()
        filename = now.strftime("%Y-%m-%d_%H%M%S") + ".json"
        entry = {
            "timestamp": now.isoformat(),
            "summary": summary.strip(),
            "turn_count": len(self._turn_buffer)
        }

        try:
            # Ensure folder exists (may have been deleted by Docker or other process)
            self.summaries_path.mkdir(parents=True, exist_ok=True)
            filepath = self.summaries_path / filename
            filepath.write_text(json.dumps(entry, indent=2))
            print(f"[Summarizer] Saved summary: {filename}")
        except Exception as e:
            print(f"[Summarizer] Save error: {e}")

        self._turn_buffer.clear()
        return summary.strip()

    def get_recent_summaries(self, limit: int = 3) -> str:
        """Load recent summaries for context"""
        try:
            # Ensure folder exists
            self.summaries_path.mkdir(parents=True, exist_ok=True)
            files = sorted(self.summaries_path.glob("*.json"), reverse=True)[:limit]
        except Exception:
            return ""

        parts = []
        for f in reversed(files):  # chronological order
            try:
                data = json.loads(f.read_text())
                ts = data.get("timestamp", "")[:10]
                parts.append(f"[{ts}] {data['summary']}")
            except Exception:
                continue

        return "\n".join(parts)
