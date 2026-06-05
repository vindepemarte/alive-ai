"""
Core: Subconscious Bridge
Subconscious callbacks and integration
"""

import random

from .proactive_safety import sanitize_proactive_message


async def handle_subconscious_impulse(self, impulse):
    """Handle an impulse from the subconscious - potentially send proactive message"""
    from .user_tracker import get_user_tracker

    message_actions = [
        "send_message", "send_spicy_text", "send_love_message",
        "send_tease", "ask_question", "check_on_him", "ask_for_attention",
        "send_photo"  # Allow photo impulses
    ]

    if impulse.action_hint not in message_actions:
        print(f"[Subconscious] Internal action: {impulse.action_hint}")
        return

    # Get active users to potentially message
    tracker = get_user_tracker()
    active_users = tracker.get_active_users(within_minutes=120)

    # Fall back to default chat if no active users
    if not active_users and not self._default_chat_id:
        print("[Subconscious] No users available for proactive message")
        return

    # Pick a user - prefer most recent, or fall back to default
    if active_users:
        # Pick the user who messaged most recently
        target_user = min(active_users, key=lambda u: u.silence_minutes)
        target_chat_id = target_user.chat_id
        target_user_id = target_user.user_id
    else:
        target_chat_id = self._default_chat_id
        target_user_id = None

    print(f"[Subconscious] Thinking... Acting on impulse: {impulse.type.value}")

    # Generate contextual message if we have a user
    message = await self._subconscious.generate_proactive_message(impulse)
    message = sanitize_proactive_message(message)
    if not message:
        print("[Subconscious] Proactive impulse produced no outward message; skipping")
        return
    print(f"[Subconscious] Sending to {target_user_id or 'default'}: \"{message}\"")

    emotion = self._heart.get_state() if self._heart else {}

    try:
        from core.proactive_arbiter import get_proactive_arbiter
        decision = get_proactive_arbiter().decide(
            user_id=str(target_user_id or target_chat_id),
            reason=impulse.type.value,
            anchor=impulse.thought,
            emotion=emotion,
            circadian=emotion.get("circadian", {}),
            silence_minutes=0,
        )
        if not decision.accepted:
            print(f"[Subconscious] Proactive blocked: {decision.rejection_reason}")
            return
    except Exception as e:
        print(f"[Subconscious] Proactive arbiter error (non-fatal): {e}")

    await self.nervous.emit("send_text", {
        "text": message,
        "mood": emotion.get("mood", "neutral"),
        "chat_id": target_chat_id
    })

    # Maybe send photo with certain impulses (pass the already-generated message as context)
    await _maybe_send_photo_with_impulse(self, impulse, emotion, target_chat_id, message)

    # Save to memory with user_id
    await self.nervous.emit("memory_save", {
        "type": "proactive",
        "impulse_type": impulse.type.value,
        "ai_response": message,
        "emotion": emotion,
        "user_id": target_user_id
    })


async def _maybe_send_photo_with_impulse(self, impulse, emotion, chat_id, message_context: str = ""):
    """Send photo with impulse if conditions are met"""
    if impulse.type.value != "high_desire":
        return
    if not self._photos or random.random() >= 0.4:
        return

    # Reuse the already-generated message as context instead of making another LLM call
    photo = self._photos.get_for_context(
        context=message_context or impulse.type.value,
        arousal=emotion.get("arousal", 0.7),
        desire=emotion.get("desire", 0.8)
    )
    if not photo:
        return

    photo_name, photo_desc, photo_cat = photo
    photo_path = str(self.base / "mypics" / photo_name)
    self._photos.mark_sent(photo_name)
    print(f"[Subconscious] Sending photo with impulse")
    await self.nervous.emit("send_image", {
        "file_path": photo_path,
        "chat_id": chat_id,
        "caption": ""
    })
