"""Optional OpenMind semantic memory bridge."""

import asyncio
import os
from typing import Any, Dict, List, Optional

import aiohttp

from core.settings import get as settings_get


class OpenMindMemoryBridge:
    """Syncs Alive-AI turns to OpenMind and retrieves long-term semantic context."""

    def __init__(self, nervous, user_id: str, bot_id: str):
        self.nervous = nervous
        self.user_id = str(user_id or "default")
        self.agent_name = str(bot_id or "Alive-AI")
        self.bot_id = self.agent_name.lower()
        nervous.on("memory_save", self._on_memory_save)

    @staticmethod
    def enabled() -> bool:
        return str(settings_get("OPENMIND_ENABLED", os.environ.get("OPENMIND_ENABLED", "false"))).lower() in (
            "1", "true", "yes", "on"
        )

    @staticmethod
    def base_url() -> str:
        return str(settings_get("OPENMIND_BASE_URL", os.environ.get("OPENMIND_BASE_URL", "https://theopenmind.pro"))).rstrip("/")

    @staticmethod
    def api_key() -> str:
        return str(settings_get("OPENMIND_API_KEY", os.environ.get("OPENMIND_API_KEY", ""))).strip()

    def _headers(self) -> Dict[str, str]:
        headers = {"content-type": "application/json"}
        key = self.api_key()
        if key:
            headers["authorization"] = f"Bearer {key}"
        return headers

    def _on_memory_save(self, data: dict):
        if not self.enabled() or data.get("type") != "conversation":
            return
        event_user_id = data.get("user_id")
        if event_user_id:
            if str(event_user_id) != self.user_id:
                return
        elif self.user_id != "default":
            return
        asyncio.ensure_future(self.capture_turn(data))

    async def capture_turn(self, data: dict) -> Optional[dict]:
        user_msg = (data.get("user_message") or "").strip()
        ai_msg = (data.get("ai_response") or "").strip()
        if not user_msg and not ai_msg:
            return None

        emotion = data.get("emotion") or {}
        mood = emotion.get("mood", "unknown")
        content = "\n".join(
            part for part in [
                f"{self.agent_name} agent id: {self.bot_id}",
                f"User id: {self.user_id}",
                f"Mood: {mood}",
                f"User: {user_msg}" if user_msg else "",
                f"{self.agent_name}: {ai_msg}" if ai_msg else "",
            ] if part
        )
        tags = ["alive-ai", self.bot_id, f"user-{self.user_id}", f"mood-{mood}"]
        payload = {
            "content": content,
            "source": "alive-ai",
            "type": "conversation",
            "tags": tags,
        }

        try:
            timeout = aiohttp.ClientTimeout(total=12)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(f"{self.base_url()}/capture", json=payload, headers=self._headers()) as resp:
                    if resp.status >= 400:
                        body = await resp.text()
                        print(f"[OpenMind] Capture failed ({resp.status}): {body[:200]}")
                        return None
                    result = await resp.json()
                    print(f"[OpenMind] Captured memory: {result.get('status', 'ok')}")
                    return result
        except Exception as exc:
            print(f"[OpenMind] Capture unavailable: {exc}")
            return None

    async def search_context(self, query: str, limit: int = 3) -> str:
        if not self.enabled() or not query.strip():
            return ""
        try:
            timeout = aiohttp.ClientTimeout(total=10)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(
                    f"{self.base_url()}/search",
                    params={"q": query, "limit": str(limit)},
                    headers=self._headers(),
                ) as resp:
                    if resp.status >= 400:
                        body = await resp.text()
                        print(f"[OpenMind] Search failed ({resp.status}): {body[:200]}")
                        return ""
                    rows = await resp.json()
        except Exception as exc:
            print(f"[OpenMind] Search unavailable: {exc}")
            return ""

        if not isinstance(rows, list):
            return ""
        return self._format_results(rows[:limit])

    def _format_results(self, rows: List[Dict[str, Any]]) -> str:
        lines = []
        for row in rows:
            content = str(row.get("content") or row.get("summary") or "").strip()
            if not content:
                continue
            similarity = row.get("similarity")
            prefix = "OpenMind"
            if isinstance(similarity, (int, float)):
                prefix = f"OpenMind {round(similarity * 100)}%"
            lines.append(f"{prefix}: {content[:700]}")
        return "\n".join(lines)
