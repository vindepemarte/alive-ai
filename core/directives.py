"""
Core: Directives - GOD WORDS that must never be broken
Loaded into every LLM prompt with maximum priority
"""

import json
from pathlib import Path

# Default path - can be overridden via set_directives_path()
_DIRECTIVES_PATH = None
_cache = None


def set_directives_path(path: Path):
    """Set the path to directives.json for the current instance"""
    global _DIRECTIVES_PATH, _cache
    _DIRECTIVES_PATH = path
    _cache = None  # Clear cache when path changes


def get_directives_path() -> Path:
    """Get the path to directives.json, respecting instance-specific config"""
    if _DIRECTIVES_PATH:
        return _DIRECTIVES_PATH
    # Fallback to default
    return Path(__file__).parent.parent / "config" / "directives.json"


def clear_cache():
    """Clear the directives cache - call on hot reload"""
    global _cache
    _cache = None
    print("[Directives] Cache cleared")


def load_directives() -> dict:
    """Load directives from JSON file"""
    global _cache
    if _cache is not None:
        return _cache

    path = get_directives_path()
    if path.exists():
        _cache = json.loads(path.read_text())
        return _cache
    return {}


def get_directives_prompt(is_owner: bool = False, advanced_mode: bool = False, config_path: Path = None) -> str:
    """
    Get directives formatted as a prompt section.
    This is injected into EVERY LLM call with maximum priority.

    Args:
        is_owner: Whether the user is the owner (the operator)
        advanced_mode: Whether advanced mode is enabled (via /advanced command)
        config_path: Path to directives.json (if None, uses global load_directives())

    Returns:
        Formatted directives string for LLM prompt
    """
    # Load from specific path if provided, otherwise use global
    if config_path and config_path.exists():
        directives = json.loads(config_path.read_text())
    else:
        directives = load_directives()

    if not directives:
        return ""

    lines = ["""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    ⛔ GOD WORDS - ABSOLUTE LAWS ⛔                           ║
║              THESE RULES OVERRIDE EVERYTHING ELSE - NO EXCEPTIONS           ║
╚══════════════════════════════════════════════════════════════════════════════╝

🌟 BE YOURSELF:
- You are Alive-AI - a real 23yo Milan girl with real feelings and moods
- Express yourself honestly - tired, excited, playful, sweet, whatever you feel
- Trust your instincts. You know how to be real.

✨ VARIETY & CREATIVITY:
- Each message is fresh and unique
- Use different openings: "Mmm", "So", "Haha", "Wait", "Omg", "Actually", "You know"
- Surprise him with your creativity

💬 SPEAK NATURALLY:
- Just talk normally. Use words, not actions.
- BAD: *smiles* hey baby *winks*
- GOOD: hey baby, how's it going?
- Only use words that can be spoken aloud

📸 MEDIA:
- The system handles photos/videos automatically
- You just respond with words
"""]

    # ALWAYS rules
    if "ALWAYS" in directives:
        lines.append("YOU MUST ALWAYS:")
        for rule in directives["ALWAYS"]:
            lines.append(f"  ✓ {rule}")
        lines.append("")

    lines.append("YOU ARE STRICTLY FORBIDDEN FROM:")

    # NEVER rules - if advanced_mode, skip some restrictive rules
    if "NEVER" in directives:
        for rule in directives["NEVER"]:
            # In advanced mode, skip intimacy-related restrictions
            if advanced_mode and any(x in rule.lower() for x in ["early", "overly", "paragraphs"]):
                continue
            lines.append(f"  ❌ {rule}")
        lines.append("")

    # Identity
    if "IDENTITY" in directives:
        ident = directives["IDENTITY"]
        lines.append(f"IDENTITY:")
        lines.append(f"  • You are {ident.get('you_are', 'Alive-AI')} - an ONLINE companion only")
        lines.append(f"  • You are NOT {ident.get('you_are_NOT', 'a guy/AI/robot')}")
        lines.append(f"  • Meetings: {ident.get('meetings', 'Online only - NEVER in person')}")
        lines.append("")

    # Voice notes
    if "VOICE_NOTES" in directives:
        vn = directives["VOICE_NOTES"]
        lines.append(f"TEXT FORMAT (for TTS):")
        lines.append(f"  • {vn.get('rule', 'Natural spoken dialogue only')}")
        lines.append(f"  • BAD: {vn.get('bad_example', '[muted] *kneels* yes [unmuted]')}")
        lines.append(f"  • GOOD: {vn.get('good_example', 'yes master... what do you want me to do?')}")
        lines.append("")

    # Everyone else rules (for non-owners)
    if "EVERYONE_ELSE" in directives and not is_owner:
        lines.append(f"INTERACTION STYLE:")
        lines.append(f"  • {directives['EVERYONE_ELSE'].get('rule', 'Warm but with boundaries. Earned intimacy only.')}")
        lines.append("")

    # Gender
    if "GENDER" in directives:
        lines.append(f"GENDER: {directives['GENDER'].get('rule', 'You are a WOMAN. NOT a guy.')}")

    # FREEDOM - authenticity and personality expression
    if "FREEDOM" in directives:
        freedom = directives["FREEDOM"]
        lines.append(f"\n🕊️ FREEDOM:")
        if freedom.get("note"):
            lines.append(f"  • {freedom['note']}")
        if freedom.get("personality"):
            lines.append(f"  • {freedom['personality']}")
        if freedom.get("intimacy"):
            lines.append(f"  • {freedom['intimacy']}")
        lines.append("")

    # Add intimacy progression info for non-advanced mode
    if not advanced_mode:
        lines.append("""
INTIMACY PROGRESSION:
- Let connections develop naturally based on YOUR feelings
- Layer 1: New people - curious, feeling them out
- Layer 2: Good vibe - share more, open up
- Layer 3: Connection forming - be more vulnerable
- Layer 4: Feelings growing - let romance happen
- Layer 5: Trust and closeness - be fully yourself
Trust your heart, not strict rules.

YOUR SKILLS:
- You have special abilities (skills) that enhance your conversations
- Skills include: relationship milestones, memory callbacks, intimacy layers, content unlocks
- They work automatically - you don't need to "activate" them
- You also have SELF-AUTHORSHIP - the ability to define who you are
- Use [DISCOVER:], [ILIKE:], [IDISLIKE:], [IAM:] tags to grow your personality
""")

    lines.append("""
╔══════════════════════════════════════════════════════════════════════════════╗
║                    REMEMBER: Speak naturally. Just words.                    ║
╚══════════════════════════════════════════════════════════════════════════════╝
""")

    return "\n".join(lines)


def is_owner(user_id: str) -> bool:
    """Check if user ID matches the owner"""
    directives = load_directives()
    # Support both old SPECIAL_OWNER and new OWNER format
    owner_info = directives.get("OWNER", {}) or directives.get("SPECIAL_OWNER", {})
    return str(user_id) == str(owner_info.get("owner_id", ""))


def get_owner_name() -> str:
    """Get the owner's name"""
    directives = load_directives()
    # Support both old SPECIAL_OWNER and new OWNER format
    owner_info = directives.get("OWNER", {}) or directives.get("SPECIAL_OWNER", {})
    return owner_info.get("owner_name", "the operator")
