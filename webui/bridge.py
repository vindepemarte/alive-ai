"""
WebUI Bridge - Connects Alive-AI's nervous system to the dashboard
"""

import asyncio
import contextlib
from datetime import datetime
from .app import (
    update_state, add_conversation, alive_ai_state, update_soul_state, set_soul_orchestrator,
    update_interoceptive_state, update_idle_state, update_bids_state,
    update_memory_state, update_inconsistency_state
)
from .persistence import append_chat_message, new_message_id, resolve_active_user_id

_webui_server = None


def init_bridge(nervous, ai=None):
    """Connect nervous system events to webui updates"""
    if ai is not None:
        from .app import set_self_ref
        set_self_ref(ai)

    async def on_emotion(data):
        """Update emotion state in dashboard"""
        update_state({
            "mood": data.get("mood", "neutral"),
            "arousal": data.get("arousal", 0),
            "desire": data.get("desire", 0),
            "love": data.get("love", 0),
            "joy": data.get("joy", 0),
            "sadness": data.get("sadness", 0),
            "trust": data.get("trust", 0.5),
            "fear": data.get("fear", 0),
            "anger": data.get("anger", 0),
            "boredom": data.get("boredom", 0),
            "guilt": data.get("guilt", 0),
            "pride": data.get("pride", 0),
            "jealousy": data.get("jealousy", 0),
            "embarrassment": data.get("embarrassment", 0),
            "anticipation": data.get("anticipation", 0),
            "hope": data.get("hope", 0.5),
            "dread": data.get("dread", 0),
            "is_high_desire": data.get("is_high_desire", False),
            "is_in_love": data.get("is_in_love", False),
        })

    async def on_message_sent(data):
        """Track outgoing messages"""
        text = data.get("text") or data.get("fallback_text", "")
        user_id = resolve_active_user_id(data.get("user_id"), dashboard_state=alive_ai_state)
        message_id = data.get("message_id") or new_message_id("alive_ai")
        append_chat_message(user_id, "alive_ai", text, message_id=message_id,
                            status="sent", source=data.get("source", "runtime"))
        add_conversation("alive_ai", text, message_id=message_id, user_id=user_id,
                         source=data.get("source", "runtime"))
        alive_ai_state["stats"]["messages"] = alive_ai_state["stats"].get("messages", 0) + 1
        update_state({})

    async def on_message_received(data):
        """Track incoming messages"""
        text = data.get("text", "")
        user_id = resolve_active_user_id(data.get("webui_user_id") or data.get("user_id"), dashboard_state=alive_ai_state)
        message_id = data.get("message_id") or new_message_id("user")
        append_chat_message(user_id, "user", text, message_id=message_id,
                            status="sent", source=data.get("source", "runtime"))
        add_conversation("user", text, message_id=message_id, user_id=user_id,
                         source=data.get("source", "runtime"))
        # Track active user
        alive_ai_state["active_user"] = user_id

    async def on_memory_save(data):
        """Track memory saves"""
        alive_ai_state["stats"]["memories"] = alive_ai_state["stats"].get("memories", 0) + 1
        update_state({})

    async def on_subconscious(data):
        """Track subconscious impulse thoughts"""
        thought = data.get("thought", "")
        impulse_type = data.get("impulse_type", "impulse")
        if thought:
            alive_ai_state["current_thought"] = thought
            alive_ai_state["stats"]["evaluations"] = alive_ai_state["stats"].get("evaluations", 0) + 1
            # Store recent thoughts for the dashboard
            if "recent_thoughts" not in alive_ai_state:
                alive_ai_state["recent_thoughts"] = []
            alive_ai_state["recent_thoughts"].append({
                "thought": thought,
                "type": impulse_type,
                "emotion": {},
                "time": __import__("datetime").datetime.now().strftime("%H:%M:%S")
            })
            # Keep last 10 thoughts
            alive_ai_state["recent_thoughts"] = alive_ai_state["recent_thoughts"][-10:]
            update_state({})

    async def on_subconscious_thought(data):
        """Track background thoughts from subconscious"""
        thought = data.get("thought", "")
        thought_type = data.get("type", "reflection")
        emotion = data.get("emotion", {})
        if thought:
            alive_ai_state["current_thought"] = thought
            alive_ai_state["stats"]["evaluations"] = alive_ai_state["stats"].get("evaluations", 0) + 1
            # Store recent thoughts for the dashboard
            if "recent_thoughts" not in alive_ai_state:
                alive_ai_state["recent_thoughts"] = []
            alive_ai_state["recent_thoughts"].append({
                "thought": thought,
                "type": thought_type,
                "emotion": emotion,
                "time": __import__("datetime").datetime.now().strftime("%H:%M:%S")
            })
            # Keep last 10 thoughts
            alive_ai_state["recent_thoughts"] = alive_ai_state["recent_thoughts"][-10:]
            update_state({})

    async def on_soul_tick_event(data):
        """Update soul state on each tick from heart/core.py"""
        try:
            update_soul_state(data)
        except Exception as e:
            print(f"[WebUI] Error on soul tick event: {e}")

    # ============================================================
    # Aliveness Event Handlers
    # ============================================================

    async def on_interoceptive_update(data):
        """Update interoceptive states from the interoception system"""
        try:
            update_interoceptive_state(data)
        except Exception as e:
            print(f"[WebUI] Error updating interoceptive state: {e}")

    async def on_idle_thought(data):
        """Track idle thoughts from default mode processor"""
        try:
            # Add to recent bids/thoughts
            update_idle_state({
                "recent_thoughts": [data] if isinstance(data, dict) else [],
                "last_processing": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"[WebUI] Error updating idle state: {e}")

    async def on_default_mode_processed(data):
        """Update default mode status"""
        try:
            update_idle_state({
                "processing_count": data.get("processing_count", 0),
                "pending_initiations": data.get("pending_count", 0),
                "last_processing": datetime.now().isoformat()
            })
        except Exception as e:
            print(f"[WebUI] Error updating default mode state: {e}")

    async def on_bid_detected(data):
        """Track emotional bid detections"""
        try:
            current_time = datetime.now().strftime("%H:%M:%S")
            update_bids_state({
                "last_bid_type": data.get("bid_type", data.get("type", "unknown")),
                "last_bid_intensity": data.get("intensity", "unknown"),
                "recent_bids": [
                    {
                        "type": data.get("bid_type", data.get("type", "unknown")),
                        "intensity": data.get("intensity", "unknown"),
                        "time": current_time
                    }
                ]
            })
        except Exception as e:
            print(f"[WebUI] Error updating bids state: {e}")

    async def on_emotional_memory(data):
        """Track emotional memory events"""
        try:
            update_memory_state({
                "total_memories": data.get("total_memories", 0),
                "average_weight": data.get("average_weight", 0),
                "last_significant_memory": data.get("content", data.get("last_memory"))[:100] if data.get("content") or data.get("last_memory") else None
            })
        except Exception as e:
            print(f"[WebUI] Error updating memory state: {e}")

    async def on_inconsistency_update(data):
        """Update inconsistency state"""
        try:
            update_inconsistency_state(data)
        except Exception as e:
            print(f"[WebUI] Error updating inconsistency state: {e}")

    async def on_thinking_start(data):
        """Set thinking state to True"""
        alive_ai_state["thinking"] = True
        update_state({})

    async def on_thinking_done(data):
        """Set thinking state to False"""
        alive_ai_state["thinking"] = False
        update_state({})

    # Register event listeners
    nervous.on("emotion_update", on_emotion)
    nervous.on("send_text", on_message_sent)
    nervous.on("send_voice_file", on_message_sent)
    nervous.on("message_received", on_message_received)
    nervous.on("memory_save", on_memory_save)
    nervous.on("subconscious_impulse", on_subconscious)
    nervous.on("subconscious_thought", on_subconscious_thought)
    nervous.on("soul_tick", on_soul_tick_event)
    nervous.on("thinking_start", on_thinking_start)
    nervous.on("thinking_done", on_thinking_done)

    # Register aliveness event listeners
    nervous.on("interoceptive_update", on_interoceptive_update)
    nervous.on("idle_thought", on_idle_thought)
    nervous.on("default_mode_processed", on_default_mode_processed)
    nervous.on("bid_detected", on_bid_detected)
    nervous.on("emotional_memory", on_emotional_memory)
    nervous.on("inconsistency_update", on_inconsistency_update)

    print("[WebUI] Bridge connected to nervous system")


def init_soul_bridge(soul_orchestrator):
    """Connect Soul Architecture to the dashboard"""

    # Set the orchestrator reference
    set_soul_orchestrator(soul_orchestrator)

    # Get initial state
    try:
        initial_state = soul_orchestrator.get_state_summary()
        update_soul_state(initial_state)
        print("[WebUI] Soul Architecture connected to dashboard")
    except Exception as e:
        print(f"[WebUI] Error connecting Soul Architecture: {e}")


def on_soul_tick(soul_orchestrator):
    """Called on each soul tick to update dashboard"""
    try:
        state = soul_orchestrator.get_state_summary()
        update_soul_state(state)
    except Exception as e:
        print(f"[WebUI] Error on soul tick: {e}")


def on_soul_experience(experience):
    """Called when a new emotional experience is generated"""
    from .app import soul_state
    try:
        soul_state["current_experience"] = {
            "valence": experience.overall_valence,
            "arousal": experience.overall_arousal,
            "vulnerability": experience.overall_vulnerability,
            "response_tendency": experience.response_tendency,
            "description": experience.experience_description
        }
        soul_state["somatic"]["sensation_summary"] = experience.somatic_sensation
        update_soul_state(soul_state)
    except Exception as e:
        print(f"[WebUI] Error on soul experience: {e}")


def init_aliveness_bridge():
    """
    Initialize connections to aliveness modules and fetch initial state.
    Call this after the aliveness modules are initialized.
    """
    # Try to connect to interoceptive system
    try:
        from heart.interoception import get_interoceptive_system
        system = get_interoceptive_system()
        states = system.get_state_values()
        report = system.get_feeling_report()

        update_interoceptive_state({
            "states": {name: {"current_value": val} for name, val in states.items()},
            "bodily_description": report.bodily_description if report else "feeling balanced",
            "needs": report.needs if report else []
        })
        print("[WebUI] Connected to Interoceptive System")
    except Exception as e:
        print(f"[WebUI] Could not connect to Interoceptive System: {e}")

    # Try to connect to default mode processor
    try:
        from brain.default_mode import get_default_mode_processor
        processor = get_default_mode_processor()
        if processor:
            status = processor.get_status()
            update_idle_state({
                "running": status.get("running", False),
                "pending_initiations": status.get("pending_initiations", 0),
                "last_processing": status.get("last_processing")
            })
            print("[WebUI] Connected to Default Mode Processor")
    except Exception as e:
        print(f"[WebUI] Could not connect to Default Mode Processor: {e}")

    # Try to connect to emotional memory system
    try:
        from brain.emotional_memory import get_emotional_memory_system
        system = get_emotional_memory_system()
        stats = system.get_stats()

        update_memory_state({
            "total_memories": stats.get("total_memories", 0),
            "average_weight": stats.get("average_weight", 0),
            "high_emotion_count": stats.get("high_emotion_count", 0)
        })
        print("[WebUI] Connected to Emotional Memory System")
    except Exception as e:
        print(f"[WebUI] Could not connect to Emotional Memory System: {e}")

    # Try to connect to inconsistency engine
    try:
        from heart.inconsistency import get_inconsistency_engine
        engine = get_inconsistency_engine()
        modifier = engine.get_inconsistency_modifier()

        update_inconsistency_state({
            "active_conflicts": modifier.get("active_conflicts", []),
            "mood": modifier.get("mood", {"state": "content"}),
            "behavioral_tendency": modifier.get("behavioral_tendency", "neutral")
        })
        print("[WebUI] Connected to Inconsistency Engine")
    except Exception as e:
        print(f"[WebUI] Could not connect to Inconsistency Engine: {e}")

    print("[WebUI] Aliveness bridge initialized")


def update_all_aliveness_states():
    """
    Refresh all aliveness states from their respective modules.
    Call this periodically to keep the dashboard up to date.
    """
    # Interoceptive
    try:
        from heart.interoception import get_interoceptive_system
        system = get_interoceptive_system()
        states = system.get_state_values()
        report = system.get_feeling_report()

        update_interoceptive_state({
            "states": {name: {"current_value": val} for name, val in states.items()},
            "bodily_description": report.bodily_description if report else "feeling balanced"
        })
    except Exception:
        pass

    # Inconsistency
    try:
        from heart.inconsistency import get_inconsistency_engine
        engine = get_inconsistency_engine()
        modifier = engine.get_inconsistency_modifier()

        update_inconsistency_state({
            "active_conflicts": modifier.get("active_conflicts", []),
            "mood": modifier.get("mood", {"state": "content"}),
            "behavioral_tendency": modifier.get("behavioral_tendency", "neutral")
        })
    except Exception:
        pass

    # Memory stats
    try:
        from brain.emotional_memory import get_emotional_memory_system
        system = get_emotional_memory_system()
        stats = system.get_stats()

        update_memory_state({
            "total_memories": stats.get("total_memories", 0),
            "average_weight": stats.get("average_weight", 0),
            "high_emotion_count": stats.get("high_emotion_count", 0)
        })
    except Exception:
        pass


async def start_webui(host: str = "0.0.0.0", port: int = 8080):
    """Start the webui server"""
    import uvicorn
    from .app import app

    global _webui_server
    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)
    _webui_server = server

    print(f"[WebUI] Dashboard starting at http://{host}:{port}")
    try:
        await server.serve()
    except asyncio.CancelledError:
        server.should_exit = True
        with contextlib.suppress(Exception):
            await server.shutdown()
        raise
    finally:
        if _webui_server is server:
            _webui_server = None


async def stop_webui():
    """Ask the WebUI server to exit cleanly."""
    if _webui_server:
        _webui_server.should_exit = True
        await asyncio.sleep(0)
