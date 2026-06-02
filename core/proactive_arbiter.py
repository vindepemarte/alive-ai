"""Contextual proactive-message arbitration.

The arbiter decides whether an autonomous message should actually be sent,
records both accepted and rejected decisions, and keeps proactive behavior
contextual instead of random.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from core.paths import state_file
from core.settings import get, get_int


@dataclass
class ProactiveDecision:
    accepted: bool
    user_id: str
    reason: str
    score: float
    anchor: str
    rejection_reason: str = ""
    created_at: str = ""

    def to_dict(self) -> dict:
        data = asdict(self)
        if not data["created_at"]:
            data["created_at"] = datetime.now().isoformat()
        return data


def _bool_setting(key: str, default: bool) -> bool:
    value = get(key, default)
    return value is True or str(value).lower() == "true"


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    try:
        return max(low, min(high, float(value)))
    except (TypeError, ValueError):
        return low


class ProactiveArbiter:
    def __init__(self, audit_path: Optional[Path] = None):
        self.audit_path = audit_path or state_file("proactive_decisions.jsonl")
        self.audit_path.parent.mkdir(parents=True, exist_ok=True)

    def decide(
        self,
        user_id: str,
        reason: str,
        anchor: str = "",
        emotion: Optional[dict] = None,
        circadian: Optional[dict] = None,
        silence_minutes: float = 0.0,
        scheduled: bool = False,
        now: Optional[datetime] = None,
    ) -> ProactiveDecision:
        now = now or datetime.now()
        emotion = emotion or {}
        circadian = circadian or {}
        reason = reason or "random"
        anchor = (anchor or "").strip()

        if circadian.get("sleeping") and not scheduled:
            return self._record(user_id, reason, 0.0, anchor, "sleeping", False, now)

        if _bool_setting("PROACTIVE_CONTEXTUAL_ONLY", True) and not anchor and not scheduled:
            return self._record(user_id, reason, 0.0, anchor, "missing_contextual_anchor", False, now)

        max_per_day = get_int("PROACTIVE_MAX_PER_DAY", 6)
        if not scheduled and self._count_today(user_id, now) >= max_per_day:
            return self._record(user_id, reason, 0.0, anchor, "daily_cap_reached", False, now)

        min_interval = get_int("PROACTIVE_MIN_INTERVAL_MINUTES", 35)
        last_any = self._last_decision(user_id, accepted_only=True)
        if last_any and not scheduled:
            if now - last_any < timedelta(minutes=min_interval):
                return self._record(user_id, reason, 0.0, anchor, "global_interval", False, now)

        reason_cooldown = get_int("PROACTIVE_REASON_COOLDOWN_MINUTES", 90)
        last_reason = self._last_decision(user_id, reason=reason, accepted_only=True)
        if last_reason and not scheduled:
            if now - last_reason < timedelta(minutes=reason_cooldown):
                return self._record(user_id, reason, 0.0, anchor, "same_reason_cooldown", False, now)

        score = self._score(reason, emotion, circadian, silence_minutes, scheduled, bool(anchor))
        threshold = 0.48
        hour = now.hour
        if 1 <= hour < 7 and not scheduled:
            threshold = 0.78

        accepted = scheduled or score >= threshold
        rejection = "" if accepted else "score_below_threshold"
        return self._record(user_id, reason, score, anchor, rejection, accepted, now)

    def _score(self, reason: str, emotion: dict, circadian: dict, silence: float, scheduled: bool, has_anchor: bool) -> float:
        if scheduled:
            return 1.0
        score = 0.20 + (0.18 if has_anchor else 0.0)
        score += min(0.22, max(0.0, silence) / 360.0)
        love = _clamp(emotion.get("love", 0.0))
        boredom = _clamp(emotion.get("boredom", 0.0))
        anticipation = _clamp(emotion.get("anticipation", 0.0))
        sadness = _clamp(emotion.get("sadness", 0.0))
        desire = _clamp(emotion.get("desire", 0.0))
        sleepiness = _clamp(circadian.get("sleepiness", emotion.get("sleepiness", 0.0)))

        if reason in {"silence", "miss_him", "clingy", "loving", "affectionate"}:
            score += love * 0.28 + sadness * 0.10
        if reason in {"wonder", "curious", "random"}:
            score += anticipation * 0.20 + boredom * 0.18
        if reason in {"follow_up", "question_unanswered"}:
            score += 0.28
        if reason in {"high_desire", "playful"}:
            score += desire * 0.18

        score -= sleepiness * 0.22
        return round(_clamp(score), 3)

    def _record(
        self,
        user_id: str,
        reason: str,
        score: float,
        anchor: str,
        rejection_reason: str,
        accepted: bool,
        now: datetime,
    ) -> ProactiveDecision:
        decision = ProactiveDecision(
            accepted=accepted,
            user_id=str(user_id),
            reason=str(reason),
            score=round(_clamp(score), 3),
            anchor=anchor[:500],
            rejection_reason=rejection_reason,
            created_at=now.isoformat(),
        )
        with self.audit_path.open("a") as f:
            f.write(json.dumps(decision.to_dict(), ensure_ascii=False) + "\n")
        return decision

    def _iter_decisions(self):
        if not self.audit_path.exists():
            return
        try:
            for line in self.audit_path.read_text().splitlines():
                if not line.strip():
                    continue
                yield json.loads(line)
        except Exception:
            return

    def _last_decision(self, user_id: str, reason: str = None, accepted_only: bool = False) -> Optional[datetime]:
        last = None
        for item in self._iter_decisions() or []:
            if str(item.get("user_id")) != str(user_id):
                continue
            if reason and item.get("reason") != reason:
                continue
            if accepted_only and not item.get("accepted"):
                continue
            try:
                ts = datetime.fromisoformat(item["created_at"])
            except Exception:
                continue
            if last is None or ts > last:
                last = ts
        return last

    def _count_today(self, user_id: str, now: datetime) -> int:
        count = 0
        for item in self._iter_decisions() or []:
            if str(item.get("user_id")) != str(user_id) or not item.get("accepted"):
                continue
            try:
                ts = datetime.fromisoformat(item["created_at"])
            except Exception:
                continue
            if ts.date() == now.date():
                count += 1
        return count


_instance: Optional[ProactiveArbiter] = None


def get_proactive_arbiter() -> ProactiveArbiter:
    global _instance
    if _instance is None:
        _instance = ProactiveArbiter()
    return _instance
