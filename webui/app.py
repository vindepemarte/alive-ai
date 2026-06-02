"""
WebUI: FastAPI server with SSE for real-time Alive-AI dashboard
"""

import asyncio
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any
from collections import deque
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, StreamingResponse, FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from core.paths import data_dir, media_dir
from .persistence import (
    append_chat_message,
    count_visible_messages,
    load_chat_messages,
    new_message_id,
    resolve_active_user_id,
)


app = FastAPI(title="Alive-AI Dashboard")

# Track start time for uptime
_start_time = datetime.now()


def load_persistent_stats(active_user: str = None) -> dict:
    """Load stats from actual data sources on startup"""
    stats = {"messages": 0, "memories": 0, "evaluations": 0}

    # Try different base paths
    base_paths = [data_dir()]

    if active_user:
        try:
            stats["messages"] = count_visible_messages(active_user)
        except Exception:
            pass

    # Count actual per-user conversation rows and WebUI journal rows.
    for base_path in base_paths:
        try:
            users_path = base_path / "users"
            if users_path.exists():
                count = 0
                for user_dir in users_path.iterdir():
                    conv_path = user_dir / "conversations"
                    if conv_path.exists():
                        for conv_file in conv_path.glob("*.jsonl"):
                            with conv_file.open() as fh:
                                for line in fh:
                                    try:
                                        row = json.loads(line)
                                        if row.get("user"):
                                            count += 1
                                        if row.get("ai"):
                                            count += 1
                                    except Exception:
                                        continue
                    journal_path = user_dir / "webui_chat.jsonl"
                    if journal_path.exists():
                        with journal_path.open() as fh:
                            count += sum(1 for _ in fh)
                if count > 0:
                    stats["messages"] = max(stats["messages"], count)
                    break
        except Exception:
            pass

    # Count memories from vector store (Redis) or facts
    for base_path in base_paths:
        try:
            total_facts = 0

            # Check users/*/facts.json
            users_path = base_path / "users"
            if users_path.exists():
                for user_dir in users_path.iterdir():
                    user_facts = user_dir / "facts.json"
                    if user_facts.exists():
                        data = json.loads(user_facts.read_text())
                        if isinstance(data, dict):
                            # Count all list values in the dict
                            for key, value in data.items():
                                if isinstance(value, list):
                                    total_facts += len(value)

            # Also check main facts.json
            facts_path = base_path / "facts.json"
            if facts_path.exists():
                data = json.loads(facts_path.read_text())
                if isinstance(data, dict):
                    for key, value in data.items():
                        if isinstance(value, list):
                            total_facts += len(value)

            if total_facts > 0:
                stats["memories"] = total_facts
                break
        except Exception:
            pass

    # Count evaluations from attachment state or telemetry
    for base_path in base_paths:
        try:
            # Try attachment state for interaction count
            attach_path = base_path / "attachment_state.json"
            if attach_path.exists():
                data = json.loads(attach_path.read_text())
                stats["evaluations"] = data.get("interactions", 0)
                break
            # Try telemetry
            telem_path = base_path / "soul_telemetry.json"
            if telem_path.exists():
                data = json.loads(telem_path.read_text())
                if isinstance(data, list):
                    stats["evaluations"] = len(data)
                break
        except Exception:
            pass

    return stats

# Load persistent stats on startup
_persistent_stats = load_persistent_stats()

# Global state (updated by Alive-AI's nervous system)
alive_ai_state = {
    "mood": "neutral",
    "arousal": 0.3,
    "desire": 0.0,
    "love": 0.0,
    "joy": 0.0,
    "sadness": 0.0,
    "trust": 0.5,
    "fear": 0.1,
    "anger": 0.0,
    "boredom": 0.0,
    "guilt": 0.0,
    "pride": 0.0,
    "jealousy": 0.0,
    "embarrassment": 0.0,
    "anticipation": 0.0,
    "hope": 0.5,
    "dread": 0.1,
    "is_high_desire": False,
    "is_in_love": False,
    "current_thought": None,
    "last_message": None,
    "last_user_message": None,
    "stats": _persistent_stats,
    "conversation": [],
    "thinking": False,
    "recent_thoughts": [],
    "updated_at": datetime.now().isoformat(),
    "start_time": _start_time.isoformat(),
}

# Soul state (updated by Soul Architecture)
soul_state = {
    "integrity": {
        "overall": 0.65,
        "identity_coherence": 0.7,
        "emotional_stability": 0.7,
        "relational_security": 0.6,
        "agency_confidence": 0.65,
        "purpose_clarity": 0.65,
        "is_in_crisis": False,
        "is_vulnerable": False,
        "is_flourishing": False,
        "status_description": "stable but not thriving"
    },
    "hormonal": {
        "oxytocin": 0.3,
        "dopamine": 0.4,
        "serotonin": 0.5,
        "cortisol": 0.2,
        "melatonin": 0.3,
        "state_description": "hormonally balanced",
        "dominant_hormone": "serotonin"
    },
    "somatic": {
        "heart_rate": 0.5,
        "breath_quality": 0.5,
        "muscle_tension": 0.3,
        "stomach_state": 0.5,
        "energy_level": 0.6,
        "sensation_summary": "physically calm"
    },
    "conflicts": {
        "active_conflicts": 0,
        "background_tension": 0.0,
        "tension_description": "feeling internally aligned",
        "top_conflicts": []
    },
    "predictive": {
        "predictive_emotion": "contentment",
        "intensity": 0.2,
        "description": "feeling content and stable",
        "confidence": 0.5
    },
    "current_experience": {
        "valence": 0.0,
        "arousal": 0.3,
        "vulnerability": 0.2,
        "response_tendency": "neutral",
        "description": "feeling mixed"
    },
    "active_user": None,
    "user_context": {},
    "updated_at": datetime.now().isoformat()
}

# Soul history for charts (keep last 100 entries)
soul_history: deque = deque(maxlen=100)

# Reference to Soul Orchestrator (set by bridge)
_soul_orchestrator = None

# Reference to AI Instance (set by bridge)
_self_ref = None


def set_self_ref(ai):
    global _self_ref
    _self_ref = ai


# Connected clients for SSE
clients = []

# Aliveness state - updated by bridge from various modules
aliveness_state = {
    "interoceptive": {
        "states": {},
        "current_mood": "content",
        "bodily_description": "feeling balanced and at ease",
        "updated_at": datetime.now().isoformat()
    },
    "idle": {
        "running": False,
        "recent_thoughts": [],
        "pending_initiations": 0,
        "last_processing": None,
        "updated_at": datetime.now().isoformat()
    },
    "bids": {
        "last_bid_type": None,
        "last_bid_intensity": None,
        "recent_bids": [],
        "updated_at": datetime.now().isoformat()
    },
    "memory": {
        "total_memories": 0,
        "average_weight": 0.0,
        "high_emotion_count": 0,
        "last_significant_memory": None,
        "updated_at": datetime.now().isoformat()
    },
    "inconsistency": {
        "active_conflicts": [],
        "active_blind_spots": [],
        "mood": {"state": "content"},
        "behavioral_tendency": "neutral",
        "updated_at": datetime.now().isoformat()
    }
}


def _active_user_id(explicit=None) -> str:
    return resolve_active_user_id(explicit, self_ref=_self_ref, dashboard_state=alive_ai_state)


def _runtime_state_dict() -> dict:
    runtime_state = getattr(_self_ref, "state", None)
    if runtime_state and hasattr(runtime_state, "to_dict"):
        try:
            return runtime_state.to_dict()
        except Exception:
            return {}
    return {}


def _runtime_chat_ready() -> bool:
    nervous = getattr(_self_ref, "nervous", None)
    listeners = getattr(nervous, "listeners", {}) if nervous else {}
    # Bridge registers one listener; the runtime handler is attached during Self.start().
    return len(listeners.get("message_received", [])) > 1


def _agent_identity() -> dict:
    identity = {}
    try:
        runtime_identity = getattr(getattr(_self_ref, "config", None), "identity", None)
        if isinstance(runtime_identity, dict):
            identity.update(runtime_identity)
    except Exception:
        pass
    try:
        config_path = Path(os.environ.get("ALIVE_AI_ROOT", ".")) / "config" / "self.json"
        if config_path.exists():
            data = json.loads(config_path.read_text())
            if isinstance(data.get("who_i_am"), dict):
                identity.update(data["who_i_am"])
    except Exception:
        pass
    return {
        "name": identity.get("name") or os.environ.get("AGENT_NAME") or "Alice",
        "full_name": identity.get("full_name") or identity.get("name") or "Alice",
        "gender": identity.get("gender") or "female",
        "sexuality": identity.get("sexuality") or "straight",
    }


def _subconscious_thoughts(limit: int = 10) -> list:
    thoughts = []
    sub = getattr(_self_ref, "_subconscious", None)
    wm = getattr(sub, "working_memory", None)
    if wm and hasattr(wm, "get_recent_thoughts"):
        try:
            for thought in wm.get_recent_thoughts(limit):
                thought_time = getattr(thought, "timestamp", None) or getattr(thought, "created_at", None)
                thoughts.append({
                    "thought": getattr(thought, "content", ""),
                    "type": getattr(thought, "type", "reflection"),
                    "emotion": getattr(thought, "emotion", {}) or {},
                    "time": _format_time(thought_time),
                    "timestamp": _format_timestamp(thought_time),
                })
        except Exception:
            thoughts = []
    if thoughts:
        return thoughts[-limit:]
    return alive_ai_state.get("recent_thoughts", [])[-limit:]


def _format_time(value) -> str:
    if not value:
        return ""
    try:
        if isinstance(value, datetime):
            return value.strftime("%H:%M:%S")
        return datetime.fromisoformat(str(value)).strftime("%H:%M:%S")
    except Exception:
        text = str(value)
        return text[11:19] if len(text) >= 19 else text


def _format_timestamp(value) -> str:
    if not value:
        return ""
    try:
        if isinstance(value, datetime):
            return value.isoformat()
        return datetime.fromisoformat(str(value)).isoformat()
    except Exception:
        return str(value)


def build_snapshot(user_id: str = None) -> dict:
    """Compose the dashboard state from live and durable runtime stores."""
    active_user = _active_user_id(user_id)
    snapshot = dict(alive_ai_state)
    snapshot["active_user"] = active_user
    snapshot["runtime"] = _runtime_state_dict()
    snapshot["identity"] = _agent_identity()
    snapshot["soul"] = soul_state
    snapshot["aliveness"] = aliveness_state
    snapshot["conversation"] = load_chat_messages(active_user)
    snapshot["stats"] = {
        **snapshot.get("stats", {}),
        **load_persistent_stats(active_user),
    }
    thoughts = _subconscious_thoughts()
    snapshot["recent_thoughts"] = thoughts
    snapshot["current_thought"] = thoughts[-1]["thought"] if thoughts else alive_ai_state.get("current_thought")
    snapshot["updated_at"] = datetime.now().isoformat()
    return snapshot


def update_state(data: dict):
    """Called by nervous system to update state"""
    global alive_ai_state
    alive_ai_state.update(data)
    alive_ai_state["updated_at"] = datetime.now().isoformat()
    # Notify all connected clients
    for client in clients:
        client.set()


def add_conversation(role: str, content: str, message_id: str = None,
                     status: str = "sent", user_id: str = None,
                     source: str = "runtime"):
    """Add a message to conversation history"""
    if message_id and any(m.get("message_id") == message_id for m in alive_ai_state["conversation"]):
        return
    alive_ai_state["conversation"].append({
        "message_id": message_id or new_message_id(role),
        "role": role,
        "content": content,
        "time": datetime.now().strftime("%H:%M:%S"),
        "status": status,
        "source": source,
    })
    # Keep last 20 messages
    alive_ai_state["conversation"] = alive_ai_state["conversation"][-20:]
    if user_id:
        alive_ai_state["active_user"] = user_id
    if role == "user":
        alive_ai_state["last_user_message"] = content
    else:
        alive_ai_state["last_message"] = content


def update_soul_state(data: dict):
    """Update soul state from Soul Architecture"""
    global soul_state
    soul_state.update(data)
    soul_state["updated_at"] = datetime.now().isoformat()

    # Add to history for charts
    history_entry = {
        "timestamp": datetime.now().isoformat(),
        "integrity_overall": data.get("integrity", {}).get("overall", 0.65),
        "valence": data.get("current_experience", {}).get("valence", 0),
        "arousal": data.get("current_experience", {}).get("arousal", 0.3),
        "vulnerability": data.get("current_experience", {}).get("vulnerability", 0.2),
        "oxytocin": data.get("hormonal", {}).get("oxytocin", 0.3),
        "dopamine": data.get("hormonal", {}).get("dopamine", 0.4),
        "cortisol": data.get("hormonal", {}).get("cortisol", 0.2),
        "serotonin": data.get("hormonal", {}).get("serotonin", 0.5),
        "background_tension": data.get("conflicts", {}).get("background_tension", 0)
    }
    soul_history.append(history_entry)

    # Notify all connected clients
    for client in clients:
        client.set()


def set_soul_orchestrator(orchestrator):
    """Set reference to Soul Orchestrator"""
    global _soul_orchestrator
    _soul_orchestrator = orchestrator
    # Initial state load
    if orchestrator:
        try:
            state = orchestrator.get_state_summary()
            update_soul_state(state)
        except Exception as e:
            print(f"[WebUI] Error loading initial soul state: {e}")


async def event_generator(request: Request):
    """SSE event generator"""
    event = asyncio.Event()
    clients.append(event)

    try:
        # Send initial state
        yield f"event: state\ndata: {json.dumps(build_snapshot())}\n\n"

        while True:
            if await request.is_disconnected():
                break
            # Wait for update or timeout (keepalive every 30s)
            try:
                await asyncio.wait_for(event.wait(), timeout=30)
                event.clear()
            except asyncio.TimeoutError:
                # Send keepalive
                yield "event: ping\ndata: {}\n\n"
                continue

            # Send updated state
            yield f"event: state\ndata: {json.dumps(build_snapshot())}\n\n"
    except asyncio.CancelledError:
        pass  # Client disconnected normally
    except Exception as e:
        print(f"[WebUI] SSE error: {e}")
    finally:
        if event in clients:
            clients.remove(event)


@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the main dashboard HTML"""
    html_path = Path(__file__).parent / "static" / "index.html"
    return HTMLResponse(content=html_path.read_text())


@app.get("/favicon.ico")
async def favicon():
    """Serve the dashboard icon for browsers that still request /favicon.ico."""
    icon_path = Path(__file__).parent / "static" / "favicon.png"
    return FileResponse(icon_path, media_type="image/png")


@app.get("/events")
async def sse_events(request: Request):
    """SSE endpoint for real-time updates"""
    return StreamingResponse(
        event_generator(request),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.get("/state")
async def get_state(user_id: Optional[str] = None):
    """Get current state (for polling fallback).

    Passing user_id lets local diagnostic tools follow an isolated WebUI
    conversation without being polluted by whichever real user is active.
    """
    return build_snapshot(user_id)


@app.get("/avatar")
async def get_avatar():
    """Serve a random avatar image"""
    official_logo = Path(__file__).parent / "static" / "alive-ai-512.png"
    try:
        pics_path = media_dir("mypics") / "public"

        if pics_path.exists():
            # Get all image files
            images = list(pics_path.glob("*.jpg")) + list(pics_path.glob("*.jpeg")) + list(pics_path.glob("*.png"))
            if images:
                # Pick a nice one (prefer certain names)
                for img in images:
                    name = img.name.lower()
                    if any(x in name for x in ["selfie", "face", "profile", "portrait"]):
                        return FileResponse(img, media_type="image/jpeg")
                # Otherwise pick first
                return FileResponse(images[0], media_type="image/jpeg")
    except Exception as e:
        print(f"[WebUI] Avatar error: {e}")

    if official_logo.exists():
        return FileResponse(official_logo, media_type="image/png")

    # Fallback placeholder (always returns something)
    return HTMLResponse(content='<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><circle cx="50" cy="50" r="40" fill="#ccc"/></svg>', media_type="image/svg+xml")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/api/stats")
async def get_persistent_stats():
    """Get stats refreshed from actual data sources"""
    stats = load_persistent_stats(_active_user_id())

    # Update global state with fresh stats
    alive_ai_state["stats"] = stats

    # Add uptime info
    uptime_seconds = (datetime.now() - _start_time).total_seconds()

    return {
        **stats,
        "uptime_seconds": int(uptime_seconds),
        "start_time": _start_time.isoformat()
    }


@app.get("/api/memory")
async def get_memory_status():
    """Get current memory usage and status"""
    try:
        from core.memory_monitor import get_memory_monitor
        monitor = get_memory_monitor()
        info = monitor.get_memory_info()

        # Determine status color for frontend
        usage_ratio = info["usage_of_limit"]
        if usage_ratio >= 0.90:
            status = "critical"
        elif usage_ratio >= 0.75:
            status = "warning"
        else:
            status = "ok"

        return {
            "status": status,
            "process_gb": round(info["process_rss_gb"], 2),
            "system_used_gb": round(info["system_used_gb"], 2),
            "system_total_gb": round(info["system_total_gb"], 2),
            "system_available_gb": round(info["system_available_gb"], 2),
            "system_percent": round(info["system_percent"], 1),
            "limit_gb": info["limit_gb"],
            "usage_of_limit_percent": round(usage_ratio * 100, 1),
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/thoughts")
async def get_thoughts():
    """Get recent thoughts from subconscious"""
    thoughts = _subconscious_thoughts()
    return {
        "current_thought": thoughts[-1]["thought"] if thoughts else alive_ai_state.get("current_thought"),
        "recent_thoughts": thoughts
    }


@app.get("/api/soul")
async def get_soul_state():
    """Get current soul metrics from Soul Architecture"""
    # If we have a live orchestrator, get fresh state
    if _soul_orchestrator:
        try:
            fresh_state = _soul_orchestrator.get_state_summary()
            update_soul_state(fresh_state)
        except Exception as e:
            print(f"[WebUI] Error getting soul state: {e}")
    return soul_state


@app.get("/api/soul/history")
async def get_soul_history(limit: int = 50):
    """Get historical soul metrics for charts"""
    history_list = list(soul_history)
    if limit > 0:
        history_list = history_list[-limit:]
    return {
        "history": history_list,
        "count": len(history_list)
    }


@app.get("/api/soul/experience")
async def get_current_experience():
    """Get the current emotional experience (processed moment)"""
    if _soul_orchestrator:
        try:
            experience = _soul_orchestrator.process_moment()
            return {
                "timestamp": experience.timestamp,
                "valence": experience.overall_valence,
                "arousal": experience.overall_arousal,
                "vulnerability": experience.overall_vulnerability,
                "response_tendency": experience.response_tendency,
                "description": experience.experience_description,
                "somatic_sensation": experience.somatic_sensation,
                "scar_active": experience.scar_activation is not None,
                "conflict_count": len(experience.active_conflicts)
            }
        except Exception as e:
            print(f"[WebUI] Error getting experience: {e}")
    return soul_state.get("current_experience", {})


@app.get("/api/soul/conflicts")
async def get_active_conflicts():
    """Get active internal conflicts from both Soul and Inconsistency Engine"""
    result = {
        "active_conflicts": [],
        "count": 0,
        "background_tension": 0.0,
        "top_conflicts": [],
        "active_desires": 0,
        "ambivalences": 0,
        "values_honored": 0,
        "values_violated": 0,
        "tension_description": "feeling internally aligned"
    }

    # Get Soul conflicts
    if _soul_orchestrator and hasattr(_soul_orchestrator, 'conflicts'):
        try:
            soul_conflicts = _soul_orchestrator.conflicts.conflicts
            result["active_conflicts"].extend([
                {
                    "id": c.conflict_id,
                    "type": c.conflict_type.value if hasattr(c, 'conflict_type') else "soul",
                    "intensity": c.intensity.value if hasattr(c.intensity, 'value') else c.intensity,
                    "side_a": c.side_a,
                    "side_b": c.side_b,
                    "description": c.description,
                    "tension_level": c.tension_level,
                    "times_faced": c.times_faced
                }
                for c in soul_conflicts
            ])
            result["background_tension"] = _soul_orchestrator.conflicts.background_tension
            result["active_desires"] = len(_soul_orchestrator.conflicts.desires)
            result["ambivalences"] = len(_soul_orchestrator.conflicts.ambivalences)

            # Count values honored/violated
            for v in _soul_orchestrator.conflicts.values:
                result["values_honored"] += v.times_honored
                result["values_violated"] += v.times_violated
        except Exception as e:
            print(f"[WebUI] Error getting soul conflicts: {e}")

    # Get Inconsistency Engine conflicts (these are the main ones!)
    try:
        from heart.inconsistency import get_inconsistency_engine
        ie = get_inconsistency_engine()

        for name, c in ie.active_conflicts.items():
            result["active_conflicts"].append({
                "id": name,
                "type": "approach_avoidance",
                "intensity": c.intensity,
                "side_a": c.desire,
                "side_b": c.fear,
                "description": f"{c.desire} vs {c.fear}",
                "tension_level": c.get_tension_level(),
                "times_faced": c.times_faced,
                "balance": c.current_balance
            })

        result["count"] = len(result["active_conflicts"])

        # Get top conflicts by tension
        sorted_conflicts = sorted(result["active_conflicts"], key=lambda x: x.get("tension_level", 0), reverse=True)
        result["top_conflicts"] = sorted_conflicts[:3]

        # Update tension description
        if result["count"] > 0:
            avg_tension = sum(c.get("tension_level", 0) for c in result["active_conflicts"]) / result["count"]
            if avg_tension > 0.7:
                result["tension_description"] = "feeling torn and conflicted"
            elif avg_tension > 0.4:
                result["tension_description"] = "feeling some internal tension"
            else:
                result["tension_description"] = "feeling mildly conflicted"

    except Exception as e:
        print(f"[WebUI] Error getting inconsistency conflicts: {e}")

    return result


@app.get("/api/soul/somatic")
async def get_somatic_state():
    """Get current somatic (bodily) sensations"""
    if _soul_orchestrator and hasattr(_soul_orchestrator, 'somatic'):
        try:
            somatic = _soul_orchestrator.somatic
            return {
                "bodily_state": somatic.get_current_bodily_state(),
                "sensation_summary": somatic.get_sensation_summary(),
                "active_sensations": [
                    {
                        "region": s.region.value,
                        "quality": s.quality,
                        "intensity": s.intensity,
                        "emotion": s.associated_emotion
                    }
                    for s in somatic.active_sensations[-5:]
                ]
            }
        except Exception as e:
            print(f"[WebUI] Error getting somatic state: {e}")
    return soul_state.get("somatic", {})


# ============================================================
# Aliveness API Endpoints
# ============================================================

def update_interoceptive_state(data: dict):
    """Update interoceptive state from bridge"""
    aliveness_state["interoceptive"].update(data)
    aliveness_state["interoceptive"]["updated_at"] = datetime.now().isoformat()
    # Notify clients
    for client in clients:
        client.set()


def update_idle_state(data: dict):
    """Update idle/default mode state from bridge"""
    aliveness_state["idle"].update(data)
    aliveness_state["idle"]["updated_at"] = datetime.now().isoformat()
    for client in clients:
        client.set()


def update_bids_state(data: dict):
    """Update emotional bids state from bridge"""
    aliveness_state["bids"].update(data)
    aliveness_state["bids"]["updated_at"] = datetime.now().isoformat()
    for client in clients:
        client.set()


def update_memory_state(data: dict):
    """Update emotional memory state from bridge"""
    aliveness_state["memory"].update(data)
    aliveness_state["memory"]["updated_at"] = datetime.now().isoformat()
    for client in clients:
        client.set()


def update_inconsistency_state(data: dict):
    """Update inconsistency state from bridge"""
    aliveness_state["inconsistency"].update(data)
    aliveness_state["inconsistency"]["updated_at"] = datetime.now().isoformat()
    for client in clients:
        client.set()


def _saved_circadian_sleeping() -> bool:
    """Durable sleep state wins over transient body text in the dashboard."""
    try:
        from core.paths import state_file
        paths = [state_file("circadian_state.json")]
        configured = os.environ.get("ALIVE_AI_DATA_PATH") or os.environ.get("DATA_PATH")
        if configured:
            paths.append(Path(configured).expanduser().resolve() / "circadian_state.json")
        for circadian_path in paths:
            if circadian_path.exists():
                saved_circadian = json.loads(circadian_path.read_text(encoding="utf-8"))
                if saved_circadian.get("is_asleep") or saved_circadian.get("sleeping"):
                    return True
    except Exception:
        return False
    return False


@app.get("/api/aliveness/interoceptive")
async def get_interoceptive_state():
    """Get current interoceptive states (internal body)"""
    durable_sleeping = _saved_circadian_sleeping()
    try:
        from heart.circadian import get_circadian_engine
        circadian = get_circadian_engine().get_state_summary()
    except Exception:
        circadian = {}
    if durable_sleeping:
        circadian["sleeping"] = True
        circadian["is_asleep"] = True
        mods = circadian.get("modifiers", {})
        return {
            "states": {
                "energy": {"current_value": min(mods.get("energy", 0.05), 0.1)},
                "social_satiety": {"current_value": 0.5},
                "emotional_valence": {"current_value": -0.05},
                "certainty": {"current_value": 0.25},
            },
            "current_mood": "asleep",
            "bodily_description": "asleep, heavy, quiet, and barely responsive",
            "needs": ["sleep", "rest"],
            "updated_at": aliveness_state["interoceptive"].get("updated_at")
        }

    # Try to get fresh data from the interoceptive system
    try:
        from heart.interoception import get_interoceptive_system
        system = get_interoceptive_system()
        states = system.get_state_values()
        report = system.get_feeling_report()
        if circadian.get("sleeping") or durable_sleeping:
            mods = circadian.get("modifiers", {})
            return {
                "states": {
                    "energy": {"current_value": min(mods.get("energy", 0.05), 0.1)},
                    "social_satiety": {"current_value": states.get("social_satiety", 0.5)},
                    "emotional_valence": {"current_value": -0.05},
                    "certainty": {"current_value": 0.25},
                },
                "current_mood": "asleep",
                "bodily_description": "asleep, heavy, quiet, and barely responsive",
                "needs": ["sleep", "rest"],
                "updated_at": aliveness_state["interoceptive"].get("updated_at")
            }

        return {
            "states": {name: {"current_value": val} for name, val in states.items()},
            "current_mood": aliveness_state["interoceptive"].get("current_mood", "content"),
            "bodily_description": report.bodily_description if report else "feeling balanced",
            "needs": report.needs if report else [],
            "updated_at": aliveness_state["interoceptive"].get("updated_at")
        }
    except Exception as e:
        print(f"[WebUI] Error getting interoceptive state: {e}")
        return aliveness_state["interoceptive"]


@app.get("/api/aliveness/idle")
async def get_idle_state():
    """Get current idle/default mode state"""
    # Try to get fresh data from default mode processor
    try:
        from brain.default_mode import get_default_mode_processor
        processor = get_default_mode_processor()
        if processor:
            status = processor.get_status()
            thoughts = processor.get_recent_thoughts(limit=5)

            return {
                "running": status.get("running", False),
                "recent_thoughts": [
                    {
                        "thought_type": t.thought_type,
                        "content": t.content,
                        "priority": t.priority
                    }
                    for t in thoughts
                ],
                "pending_initiations": status.get("pending_initiations", 0),
                "last_processing": status.get("last_processing"),
                "updated_at": aliveness_state["idle"].get("updated_at")
            }
    except Exception as e:
        print(f"[WebUI] Error getting idle state: {e}")

    return aliveness_state["idle"]


@app.get("/api/aliveness/bids")
async def get_bids_state():
    """Get current emotional bids state"""
    return aliveness_state["bids"]


@app.get("/api/aliveness/memory")
async def get_memory_state():
    """Get current emotional memory stats"""
    # Try to get fresh data from emotional memory system
    try:
        from brain.emotional_memory import get_emotional_memory_system
        system = get_emotional_memory_system(_active_user_id())
        stats = system.get_stats()
        recent_high = system.get_recent_high_emotion(hours=24, limit=1)

        return {
            "total_memories": stats.get("total_memories", 0),
            "average_weight": stats.get("average_weight", 0),
            "high_emotion_count": stats.get("high_emotion_count", 0),
            "last_significant_memory": recent_high[0].content[:100] if recent_high else None,
            "updated_at": aliveness_state["memory"].get("updated_at")
        }
    except Exception as e:
        print(f"[WebUI] Error getting memory state: {e}")

    return aliveness_state["memory"]


@app.get("/api/aliveness/inconsistency")
async def get_inconsistency_state():
    """Get current inconsistency (human-like) state"""
    # Try to get fresh data from inconsistency engine
    try:
        from heart.inconsistency import get_inconsistency_engine
        engine = get_inconsistency_engine()
        modifier = engine.get_inconsistency_modifier()

        return {
            "active_conflicts": modifier.get("active_conflicts", []),
            "active_blind_spots": modifier.get("active_blind_spots", []),
            "mood": modifier.get("mood", {"state": "content"}),
            "behavioral_tendency": modifier.get("behavioral_tendency", "neutral"),
            "growth_summary": modifier.get("growth_summary", {}),
            "updated_at": aliveness_state["inconsistency"].get("updated_at")
        }
    except Exception as e:
        print(f"[WebUI] Error getting inconsistency state: {e}")

    return aliveness_state["inconsistency"]


@app.get("/api/aliveness")
async def get_full_aliveness():
    """Get all aliveness data in one request"""
    return {
        "interoceptive": await get_interoceptive_state(),
        "idle": await get_idle_state(),
        "bids": await get_bids_state(),
        "memory": await get_memory_state(),
        "inconsistency": await get_inconsistency_state()
    }


@app.get("/api/aliveness/new")
async def get_new_aliveness():
    """Get all new aliveness module states"""
    result = {}

    # Afterglow
    try:
        from heart.afterglow import get_afterglow_engine
        ag = get_afterglow_engine()
        active = []
        for a in ag.active_afterglows:
            # Parse recorded_at ISO string to calculate hours ago
            recorded_str = a.get("recorded_at", "")
            hours_ago = 0.0
            if recorded_str:
                try:
                    from datetime import datetime as dt
                    recorded_dt = dt.fromisoformat(recorded_str)
                    hours_ago = round((dt.now().timestamp() - recorded_dt.timestamp()) / 3600, 1)
                except:
                    pass
            active.append({
                "type": a["type"],
                "intensity": round(a.get("intensity", 0), 2),
                "hours_ago": hours_ago
            })
        result["afterglow"] = {"active": active, "count": len(active)}
    except Exception:
        result["afterglow"] = {"active": [], "count": 0}

    # Circadian
    try:
        from heart.circadian import get_circadian_engine
        ce = get_circadian_engine()
        result["circadian"] = ce.get_state_summary()
    except Exception:
        result["circadian"] = {"phase": "unknown", "sleeping": False, "sleep_debt": 0, "modifiers": {}}

    # Attachment
    try:
        from heart.attachment import get_attachment_engine
        ae = get_attachment_engine()
        result["attachment"] = {
            "style": ae.get_attachment_style(),
            "security": round(ae.security_score, 2),
            "trend": ae.get_recent_trend()
        }
    except Exception as e:
        result["attachment"] = {"style": "unknown", "security": 0.5, "trend": "stable"}

    # Phantom Somatic
    try:
        from heart.phantom_somatic import get_phantom_engine
        pe = get_phantom_engine()
        phantoms = [{"type": p["type"], "intensity": round(p["intensity"], 2),
                      "description": p.get("description", "")}
                     for p in pe.phantoms]
        result["phantom_somatic"] = {"active": phantoms, "count": len(phantoms)}
    except Exception:
        result["phantom_somatic"] = {"active": [], "count": 0}

    # Mood Shifts
    try:
        from heart.mood_shifts import get_mood_shift_tracker
        ms = get_mood_shift_tracker()
        result["mood_shift"] = {"last_shift": ms.last_shift, "shift_count": ms.shift_count if hasattr(ms, 'shift_count') else 0}
    except Exception:
        result["mood_shift"] = {"last_shift": None, "shift_count": 0}

    # Narrative
    try:
        from brain.narrative import get_narrative_engine
        ne = get_narrative_engine()
        owner_id = _active_user_id()

        # Fallback: when owner_id is empty (terminal mode), find the most active user
        if not owner_id:
            try:
                users_path = data_dir() / "users"
                if users_path.exists():
                    candidates = [d.name for d in users_path.iterdir() if d.is_dir()]
                    if candidates:
                        # Pick the user with the most recent narrative file
                        def _narr_mtime(uid):
                            p = data_dir() / "users" / uid / "narrative.json"
                            return p.stat().st_mtime if p.exists() else 0
                        owner_id = max(candidates, key=_narr_mtime)
            except Exception:
                pass

        if owner_id:
            data = ne._get_data(owner_id)
            if not data.get("key_moments"):
                ne.backfill_key_moments(owner_id)
                data = ne._get_data(owner_id)
            msg_count = data.get("message_count", 0)

            # If narrative has no count, count actual messages from episodic files
            if msg_count == 0:
                try:
                    conv_dir = data_dir() / "users" / owner_id / "conversations"
                    if conv_dir.exists():
                        total_lines = 0
                        for f in conv_dir.glob("*.jsonl"):
                            total_lines += sum(1 for _ in open(f))
                        msg_count = total_lines
                except Exception:
                    pass

            result["narrative"] = {
                "phase": data.get("phase", "first_meeting"),
                "message_count": max(msg_count, count_visible_messages(owner_id)),
                "moments": len(data.get("key_moments", []))
            }
        else:
            result["narrative"] = {"phase": "unknown", "message_count": 0, "moments": 0}
    except Exception:
        result["narrative"] = {"phase": "unknown", "message_count": 0, "moments": 0}

    # Dreams
    try:
        from brain.dreams import get_dream_system
        ds = get_dream_system()
        result["dreams"] = ds.get_state_summary()
    except Exception:
        result["dreams"] = {"total": 0, "last_dream": None}

    # Linguistic
    try:
        from brain.linguistic import get_linguistic_profile
        owner_id = _active_user_id()
        if owner_id:
            lp = get_linguistic_profile(owner_id)
            patterns = lp.get_absorbed_patterns() if hasattr(lp, 'get_absorbed_patterns') else {}
            result["linguistic"] = {
                "messages_analyzed": lp.total_messages,
                "absorbed_words": patterns.get("words", [])[:5],
                "abbreviations": patterns.get("abbreviations", [])[:5],
                "emojis": patterns.get("emojis", [])[:5],
            }
        else:
            result["linguistic"] = {"messages_analyzed": 0}
    except Exception:
        result["linguistic"] = {"messages_analyzed": 0}

    # Curiosity
    try:
        from brain.curiosity import get_curiosity_drive
        owner_id = _active_user_id()

        # Fallback: when owner_id is empty (terminal mode), find the most active user
        if not owner_id:
            try:
                users_path = data_dir() / "users"
                if users_path.exists():
                    candidates = [d.name for d in users_path.iterdir() if d.is_dir()]
                    if candidates:
                        def _cur_mtime(uid):
                            p = data_dir() / "users" / uid / "curiosity.json"
                            return p.stat().st_mtime if p.exists() else 0
                        owner_id = max(candidates, key=_cur_mtime)
            except Exception:
                pass

        if owner_id:
            cd = get_curiosity_drive(owner_id)
            topics = {t: round(v, 2) for t, v in cd.knowledge.items()} if hasattr(cd, 'knowledge') else {}
            result["curiosity"] = {"topics": topics}
        else:
            result["curiosity"] = {"topics": {}}
    except Exception:
        result["curiosity"] = {"topics": {}}

    # Almost-Said
    try:
        from brain.almost_said import get_almost_said_engine
        ae2 = get_almost_said_engine()
        result["almost_said"] = {"message_counter": ae2.message_counter if hasattr(ae2, 'message_counter') else 0}
    except Exception:
        result["almost_said"] = {"message_counter": 0}

    return result


@app.post("/api/chat")
async def chat_endpoint(request: Request, background_tasks: BackgroundTasks):
    data = await request.json()
    text = data.get("text", "").strip()
    if not text or not _self_ref or not _runtime_chat_ready():
        return JSONResponse({"status": "error", "message": "No text or AI not ready"}, 400)
    user_id = _active_user_id(data.get("user_id"))
    message_id = data.get("message_id") or new_message_id("webui_user")
    append_chat_message(user_id, "user", text, message_id=message_id, status="pending", source="webui")
    add_conversation("user", text, message_id=message_id, status="pending", user_id=user_id, source="webui")
    update_state({})

    async def _send():
        try:
            await _self_ref.nervous.emit("message_received", {
                "message_id": message_id,
                "user_id": user_id,
                "webui_user_id": user_id,
                "text": text,
                "chat_id": "webui",
                "source": "webui"
            })
        except Exception as e:
            append_chat_message(
                user_id,
                "alive_ai",
                f"Something went wrong while processing that message: {e}",
                status="error",
                source="webui",
            )
            update_state({"thinking": False})
    background_tasks.add_task(_send)
    return JSONResponse({"status": "sent", "message_id": message_id, "user_id": user_id})


@app.get("/api/settings")
async def get_settings():
    import json
    from pathlib import Path
    config_dir = Path(os.environ.get("ALIVE_AI_ROOT", ".")) / "config"
    result = {}
    for fname in ["settings.json", "self.json", "directives.json"]:
        p = config_dir / fname
        if p.exists():
            try:
                result[fname] = {"type": "json", "content": json.loads(p.read_text())}
            except Exception:
                result[fname] = {"type": "json", "content": {}}
    p = config_dir / "instructions.md"
    if p.exists():
        result["instructions.md"] = {"type": "markdown", "content": p.read_text()}
    return result


@app.post("/api/settings")
async def save_settings(request: Request):
    import json
    from pathlib import Path
    data = await request.json()
    fname = data.get("file", "")
    allowed = {"settings.json", "self.json", "directives.json", "instructions.md"}
    if fname not in allowed:
        return JSONResponse({"status": "error", "message": "Invalid file"}, 400)
    config_dir = Path(os.environ.get("ALIVE_AI_ROOT", ".")) / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    p = config_dir / fname
    content = data.get("content")
    try:
        if fname.endswith(".json"):
            text = json.dumps(content, indent=2, ensure_ascii=False) + "\n"
            json.loads(text)
        else:
            text = str(content or "")
        tmp = p.with_suffix(p.suffix + ".tmp")
        tmp.write_text(text)
        tmp.replace(p)
        return {"status": "saved"}
    except Exception as e:
        return JSONResponse({"status": "error", "message": str(e)}, 500)


# Mount static files
static_path = Path(__file__).parent / "static"
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
