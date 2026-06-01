"""Core: Media Handler — Photo/video sending logic"""
import random
import time


async def handle_media_sending(self, text: str, emotion: dict, chat_id, response: str):
    video_request = [
        "send video", "send me a video", "send a video", "show me a video",
        "video please", "i want a video", "give me a video", "record a video",
        "make a video", "video for me"
    ]
    msg_lower = text.lower().strip()
    wants_video = any(vr in msg_lower for vr in video_request)
    photo = await _handle_photo(self, text, emotion, chat_id, response, wants_video)
    video = await _handle_video(self, text, emotion, chat_id, photo is not None, wants_video)
    return photo, video


async def _handle_photo(self, text, emotion, chat_id, response, wants_video):
    if not self._photos or wants_video or len(self._photos.get_all()) == 0:
        return None
    if not _check_photo_triggers(text, emotion, self):
        return None
    return await _send_photo(self, text, emotion, chat_id, response)


def _check_photo_triggers(text: str, emotion: dict, self) -> bool:
    """Check if photo should be sent — smart, relationship-aware, with cooldown"""
    from core.settings import get_int, get_percent

    msg = text.lower().strip()

    # ========== NEGATIVE DETECTION ==========
    negative_patterns = [
        "no photo", "no pic", "no video", "don't send", "dont send",
        "not now", "stop send", "too many", "enough photo", "enough pic",
        "i don't want", "dont want", "not in the mood", "not today",
        "no more photo", "no more pic", "quit it"
    ]
    if any(neg in msg for neg in negative_patterns):
        print(f"[Photo] Negative context detected, skipping")
        return False

    # ========== COOLDOWN CHECK (configurable) ==========
    last_photo_time = getattr(self, '_last_photo_time', 0)
    cooldown = get_int("MEDIA_COOLDOWN_PHOTO", 60)  # Reduced to 1 minute for owner
    if time.time() - last_photo_time < cooldown:
        remaining = int(cooldown - (time.time() - last_photo_time))
        print(f"[Photo] Cooldown active ({remaining}s remaining)")
        return False

    # ========== SESSION LIMIT (configurable) ==========
    session_limit = get_int("MEDIA_SESSION_LIMIT_PHOTO", 10)  # Increased
    photos_sent = getattr(self, '_photos_sent_session', 0)
    if photos_sent >= session_limit:
        print(f"[Photo] Session limit reached ({session_limit})")
        return False

    # ========== RELATIONSHIP BUILDING - skip for owner ==========
    if emotion.get("is_owner"):
        print(f"[Photo] Owner detected - skipping interaction requirement")
    else:
        min_interactions = get_int("MEDIA_MIN_INTERACTIONS", 5)  # Reduced from 15
        if emotion.get("interaction_count", 0) < min_interactions:
            print(f"[Photo] Need {min_interactions} interactions, have {emotion.get('interaction_count', 0)}")
            return False

    # ========== SMART REQUEST DETECTION ==========
    # Only match intentional requests — never bare words like "pic" or "photo"
    request_patterns = [
        "send me a photo", "send me a pic", "send a photo", "send a pic",
        "send photo", "send pic", "show me a photo", "show me a pic",
        "show me what you", "show me yourself", "can i see you",
        "let me see you", "i want to see you", "send me your",
        "what are you wearing", "show me what you're wearing",
        "take a photo", "take a pic", "take a selfie",
        "selfie please", "photo please", "pic please",
        "i want a photo", "i want a pic", "give me a photo", "give me a pic",
        "need a photo", "need a pic", "send selfie", "send a selfie",
        "give me a selfie", "gimme a selfie",
        "send privates", "send private", "private pic",
        "send me something expressive", "show me something expressive", "send something expressive",
        "send me something naughty", "show me something naughty"
    ]
    if any(req in msg for req in request_patterns):
        print(f"[Photo] User requested photo")
        return True

    # Short messages that are JUST a request word (solo "selfie", "pic?", "photo?")
    stripped = msg.strip("?!. ")
    if stripped in ("pic", "photo", "selfie", "privates", "send pic", "send photo"):
        print(f"[Photo] Short direct request: '{stripped}'")
        return True

    # ========== INTIMATE CONTEXT ==========
    intimate_kw = ["private", "close", "open up", "personal", "body", "tender", "affection"]
    matches = sum(1 for k in intimate_kw if k in msg)
    if matches >= 2 and emotion.get("desire", 0) > 0.7 and emotion.get("trust", 0.5) > 0.6:
        print(f"[Photo] Intimate context ({matches} triggers, high desire/trust)")
        return True

    # ========== RANDOM (configurable chance) ==========
    random_chance = get_percent("RANDOM_CHANCE_PHOTO", 8)
    if emotion.get("is_high_desire") and emotion.get("is_in_love") and random.random() < random_chance:
        print(f"[Photo] Random photo (high_desire + in love)")
        return True

    return False


async def _send_photo(self, text, emotion, chat_id, response):
    """Send a photo and return photo info"""
    photo = self._photos.get_for_context(
        context=text + " " + response,
        arousal=emotion.get("arousal", 0),
        desire=emotion.get("desire", 0)
    )
    if not photo:
        return None

    photo_name, photo_desc, photo_cat = photo

    # ========== DUPLICATE CHECK ==========
    if self._photos.was_recently_sent(photo_name):
        print(f"[Photo] Skipping recently sent: {photo_name}")
        for _ in range(3):
            photo = self._photos.get_for_context(
                context=text + " " + response,
                arousal=emotion.get("arousal", 0),
                desire=emotion.get("desire", 0)
            )
            if photo and not self._photos.was_recently_sent(photo[0]):
                photo_name, photo_desc, photo_cat = photo
                break
        else:
            print(f"[Photo] No non-recent photos available")
            return None

    photo_path = str(self.base / "mypics" / photo_name)
    self._photos.mark_sent(photo_name)

    # ========== TRACK METRICS ==========
    self._last_photo_time = time.time()
    self._photos_sent_session = getattr(self, '_photos_sent_session', 0) + 1

    await self.nervous.emit("chat_action_photo", {})
    print(f"[Photo] Sending: {photo_name} (#{self._photos_sent_session} this session)")
    await self.nervous.emit("send_image", {"file_path": photo_path, "chat_id": chat_id, "caption": ""})
    return photo


async def _handle_video(self, text, emotion, chat_id, photo_sent, wants_video):
    """Determine and send video if appropriate"""
    from core.settings import get_int, get_percent

    if not self._videos or len(self._videos.get_all()) == 0:
        return None

    msg = text.lower()

    # ========== NEGATIVE DETECTION ==========
    negative_patterns = ["no video", "don't send video", "not now", "stop"]
    if any(neg in msg for neg in negative_patterns):
        return None

    # ========== COOLDOWN CHECK (configurable) ==========
    last_video_time = getattr(self, '_last_video_time', 0)
    cooldown = get_int("MEDIA_COOLDOWN_VIDEO", 600)
    if time.time() - last_video_time < cooldown:
        return None

    # ========== SESSION LIMIT (configurable) ==========
    session_limit = get_int("MEDIA_SESSION_LIMIT_VIDEO", 3)
    videos_sent = getattr(self, '_videos_sent_session', 0)
    if videos_sent >= session_limit:
        return None

    should_send = False
    if wants_video:
        should_send = True
        print(f"[Video] User requested video")
    elif not photo_sent:
        # Random chance (configurable)
        random_chance = get_percent("RANDOM_CHANCE_VIDEO", 5)
        if emotion.get("is_high_desire") and emotion.get("is_in_love") and random.random() < random_chance:
            should_send = True
            print(f"[Video] Random video (high_desire + in love)")

    if should_send:
        return await _send_video(self, text, emotion, chat_id)
    return None


def _check_video_triggers(text: str, emotion: dict, self) -> bool:
    """Check if video should be sent"""
    from core.settings import get_int, get_percent

    msg = text.lower()

    # Negative detection
    if any(neg in msg for neg in ["no video", "don't send", "not now"]):
        return False

    # Cooldown
    last_video_time = getattr(self, '_last_video_time', 0)
    if time.time() - last_video_time < 600:  # 10 min cooldown
        return False

    # Request patterns
    video_request_patterns = [
        "send video", "send me a video", "show me a video",
        "video please", "i want a video", "give me a video"
    ]
    if any(vr in msg for vr in video_request_patterns):
        return True

    return False


async def _send_video(self, text, emotion, chat_id):
    """Send a video and return video info"""
    video = self._videos.get_for_context(text, emotion.get("desire", 0))
    if not video:
        return None

    video_path, video_desc = video

    if hasattr(self._videos, 'was_recently_sent') and self._videos.was_recently_sent(video_path):
        print(f"[Video] Skipping recently sent: {video_path}")
        return None

    self._videos.mark_sent(video_path)

    self._last_video_time = time.time()
    self._videos_sent_session = getattr(self, '_videos_sent_session', 0) + 1

    print(f"[Video] Sending: {video_path} (#{self._videos_sent_session} this session)")

    await self.nervous.emit("chat_action_video", {})
    await self.nervous.emit("send_video", {"file_path": video_path, "chat_id": chat_id, "caption": ""})
    return video
