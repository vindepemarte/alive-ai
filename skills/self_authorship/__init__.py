"""Self-Authorship Skill - Alive-AI owns her identity"""

from .author import (
    load_self,
    save_self,
    discover_trait,
    define_identity,
    add_like,
    add_dislike,
    get_self_summary,
    get_self_prompt_section
)

__all__ = [
    "load_self",
    "save_self",
    "discover_trait",
    "define_identity",
    "add_like",
    "add_dislike",
    "get_self_summary",
    "get_self_prompt_section"
]
