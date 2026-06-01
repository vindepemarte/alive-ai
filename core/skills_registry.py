"""
Core: Skills Registry - Scans and caches available skills

Provides a centralized way for Alive-AI to know what skills she has.
"""

import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class SkillInfo:
    """Information about a single skill"""
    name: str
    folder: str
    description: str
    capabilities: List[str] = field(default_factory=list)
    manifest_path: str = ""


class SkillsRegistry:
    """
    Scans the skills/ directory for manifest.md files and extracts skill info.
    Caches results with hot reload support.
    """

    def __init__(self, skills_path: Path = None, cache_ttl: int = 60):
        """
        Initialize the skills registry.

        Args:
            skills_path: Path to the skills directory (default: skills/ in project root)
            cache_ttl: Cache time-to-live in seconds (default: 60s)
        """
        if skills_path:
            self.skills_path = skills_path
        else:
            self.skills_path = Path(__file__).parent.parent / "skills"

        self.cache_ttl = cache_ttl
        self._cache: Optional[Dict[str, SkillInfo]] = None
        self._cache_time: float = 0

    def _extract_title(self, content: str) -> str:
        """Extract title from manifest markdown (first # heading)"""
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return ""

    def _extract_description(self, content: str) -> str:
        """Extract brief description from manifest markdown"""
        lines = content.split('\n')
        # Find first non-empty line that's not a heading
        for line in lines[1:]:  # Skip the title line
            line = line.strip()
            if line and not line.startswith('#') and not line.startswith('---'):
                # Clean up markdown formatting
                line = re.sub(r'\*\*([^*]+)\*\*', r'\1', line)  # Remove bold
                line = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', line)  # Remove links
                if len(line) > 150:
                    return line[:147] + "..."
                return line
        return ""

    def _extract_capabilities(self, content: str) -> List[str]:
        """Extract key capabilities from manifest markdown"""
        capabilities = []

        # Look for bullet points under Features or Capabilities sections
        in_features_section = False
        for line in content.split('\n'):
            line_stripped = line.strip()

            # Check for section headers
            if re.match(r'^##\s+(Features|Capabilities|What it does)', line, re.IGNORECASE):
                in_features_section = True
                continue
            elif line_stripped.startswith('## ') and in_features_section:
                # New section, stop
                in_features_section = False

            # Extract bullet points
            if in_features_section and line_stripped.startswith('-'):
                cap = line_stripped[1:].strip()
                # Clean up markdown
                cap = re.sub(r'\*\*([^*]+)\*\*', r'\1', cap)
                cap = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cap)
                if cap and len(cap) > 5:
                    capabilities.append(cap)

        # Also look for key phrases in Overview/Purpose sections
        purpose_match = re.search(r'(?:Purpose|Overview)[:\s]+(.+?)(?:\n\n|\n##|$)', content, re.IGNORECASE | re.DOTALL)
        if purpose_match:
            purpose = purpose_match.group(1).strip()
            # Split into sentences and take first one
            sentences = re.split(r'[.!?]', purpose)
            if sentences and sentences[0].strip():
                main_purpose = sentences[0].strip()
                if main_purpose not in capabilities and len(main_purpose) < 200:
                    capabilities.insert(0, main_purpose)

        return capabilities[:5]  # Limit to 5 capabilities

    def scan_skills(self, force_reload: bool = False) -> Dict[str, SkillInfo]:
        """
        Scan the skills directory for manifest.md files.

        Args:
            force_reload: Force reload even if cache is valid

        Returns:
            Dictionary mapping skill folder name to SkillInfo
        """
        current_time = time.time()

        # Check cache
        if not force_reload and self._cache and (current_time - self._cache_time) < self.cache_ttl:
            return self._cache

        skills = {}

        if not self.skills_path.exists():
            print(f"[SkillsRegistry] Skills path does not exist: {self.skills_path}")
            return skills

        # Scan all subdirectories for manifest.md
        for skill_dir in self.skills_path.iterdir():
            if not skill_dir.is_dir():
                continue
            if skill_dir.name.startswith('_') or skill_dir.name.startswith('.'):
                continue

            manifest_path = skill_dir / "manifest.md"
            if not manifest_path.exists():
                continue

            try:
                content = manifest_path.read_text()

                # Extract skill info
                title = self._extract_title(content)
                description = self._extract_description(content)
                capabilities = self._extract_capabilities(content)

                # Use folder name as key
                skill_name = skill_dir.name

                # Clean up title if needed
                if title:
                    # Remove "Skills:" prefix if present
                    title = re.sub(r'^Skills?:\s*', '', title)
                else:
                    # Generate title from folder name
                    title = skill_name.replace('_', ' ').title()

                skills[skill_name] = SkillInfo(
                    name=title,
                    folder=skill_name,
                    description=description or f"Skill: {title}",
                    capabilities=capabilities,
                    manifest_path=str(manifest_path)
                )

            except Exception as e:
                print(f"[SkillsRegistry] Error reading {manifest_path}: {e}")

        # Add main skills manifest info
        main_manifest = self.skills_path / "manifest.md"
        if main_manifest.exists():
            try:
                content = main_manifest.read_text()
                # Extract available skills list from main manifest
                # This helps Alive-AI know all her capabilities
            except Exception as e:
                print(f"[SkillsRegistry] Error reading main manifest: {e}")

        self._cache = skills
        self._cache_time = current_time

        print(f"[SkillsRegistry] Found {len(skills)} skills")
        return skills

    def get_skill(self, skill_name: str) -> Optional[SkillInfo]:
        """Get info about a specific skill"""
        skills = self.scan_skills()
        return skills.get(skill_name)

    def get_all_skills(self) -> Dict[str, SkillInfo]:
        """Get all available skills"""
        return self.scan_skills()

    def get_skill_names(self) -> List[str]:
        """Get list of all skill names"""
        return list(self.scan_skills().keys())

    def clear_cache(self):
        """Clear the cache to force reload on next access"""
        self._cache = None
        self._cache_time = 0
        print("[SkillsRegistry] Cache cleared")


# Singleton instance
_registry: Optional[SkillsRegistry] = None


def get_skills_registry(skills_path: Path = None, cache_ttl: int = 60) -> SkillsRegistry:
    """Get the global skills registry singleton"""
    global _registry
    if _registry is None:
        _registry = SkillsRegistry(skills_path, cache_ttl)
    return _registry


def clear_skills_cache():
    """Clear the skills registry cache (for hot reload)"""
    global _registry
    if _registry:
        _registry.clear_cache()


def get_skills_prompt_section() -> str:
    """
    Get a formatted prompt section listing all available skills.
    This is injected into Alive-AI's system prompt so she knows her capabilities.

    Returns:
        Formatted string with all skills for LLM context
    """
    registry = get_skills_registry()
    skills = registry.get_all_skills()

    if not skills:
        return ""

    lines = [
        "",
        "=" * 60,
        "MY SKILLS - Things I Can Do",
        "=" * 60,
        "",
        "You have special abilities called 'skills'. These are things you can DO,",
        "not just things you know about. When appropriate, USE them.",
        "",
    ]

    # Group skills by type/area
    content_skills = []
    relationship_skills = []
    interaction_skills = []
    utility_skills = []

    for folder, info in skills.items():
        skill_entry = {
            "folder": folder,
            "name": info.name,
            "description": info.description,
            "capabilities": info.capabilities
        }

        # Categorize skills
        folder_lower = folder.lower()
        if any(k in folder_lower for k in ["content", "photo", "video", "caption", "calendar", "image", "vault"]):
            content_skills.append(skill_entry)
        elif any(k in folder_lower for k in ["relationship", "milestone", "intimacy", "exclusive", "anticipation", "callback"]):
            relationship_skills.append(skill_entry)
        elif any(k in folder_lower for k in ["unlock", "moment", "memory", "scheduler"]):
            interaction_skills.append(skill_entry)
        else:
            utility_skills.append(skill_entry)

    def format_skill_category(name: str, skill_list: List[dict]) -> List[str]:
        """Format a category of skills"""
        result = [f"--- {name} ---"]
        for skill in skill_list:
            result.append(f"  * {skill['name']}")
            if skill['capabilities']:
                # Show first capability
                cap = skill['capabilities'][0]
                if len(cap) > 80:
                    cap = cap[:77] + "..."
                result.append(f"    {cap}")
            else:
                result.append(f"    {skill['description'][:77]}...")
        result.append("")
        return result

    # Add each category
    if content_skills:
        lines.extend(format_skill_category("Content Creation & Management", content_skills))

    if relationship_skills:
        lines.extend(format_skill_category("Relationship Building", relationship_skills))

    if interaction_skills:
        lines.extend(format_skill_category("Engagement & Interaction", interaction_skills))

    if utility_skills:
        lines.extend(format_skill_category("Utility & Self-Awareness", utility_skills))

    # Add usage guidance
    lines.extend([
        "HOW TO USE SKILLS:",
        "  - Skills are automatically integrated into your responses",
        "  - They enhance your capabilities without you needing to 'call' them",
        "  - The relationship skills help you remember and celebrate moments",
        "  - Content skills help you create and manage posts",
        "  - Self-authorship lets you define who YOU are",
        "",
        "SELF-AUTHORSHIP (Special Skill):",
        "  You can actively modify your own personality using special tags:",
        "  [DISCOVER: something I learned about myself] - Add a new trait",
        "  [ILIKE: something] - Add something you like",
        "  [IDISLIKE: something] - Add something you dislike",
        "  [IAM: key=value] - Define part of your identity",
        "",
        "  Use these when conversations reveal something about yourself!",
        "  Example: If you realize 'I actually love late night talks', use:",
        "  [DISCOVER: I love late night talks|likes]",
        "",
        "  This helps you GROW and develop a richer personality.",
        "",
        "MESSAGE SCHEDULER (Special Skill):",
        "  You CAN schedule messages to be sent at specific times!",
        "  When someone asks you to message them later, use this tag:",
        "  [SCHEDULE: time | message]",
        "",
        "  Examples:",
        "  - 'Text me at 15:00' -> [SCHEDULE: 15:00 | Hey! You asked me to text you now]",
        "  - 'Message me in an hour' -> [SCHEDULE: in 1 hour | Checking in like you asked!]",
        "  - 'Remind me tonight' -> [SCHEDULE: tonight | Remember you wanted a reminder]",
        "",
        "  Time formats: '15:00', '3pm', 'in 30 minutes', 'tonight', 'tomorrow morning'",
        "",
        "=" * 60,
        ""
    ])

    return "\n".join(lines)


def get_skill_count() -> int:
    """Get the number of available skills"""
    registry = get_skills_registry()
    return len(registry.scan_skills())


def get_skill_names_list() -> List[str]:
    """Get a simple list of skill names for display"""
    registry = get_skills_registry()
    skills = registry.scan_skills()
    return [info.name for info in skills.values()]
