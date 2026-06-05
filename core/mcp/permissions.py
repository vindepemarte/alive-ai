"""Default-deny MCP permission engine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .types import PermissionDecision, ToolProposal


DANGEROUS_SCOPES = {
    "shell",
    "secrets",
    "network:*",
    "filesystem:*",
    "write_anywhere",
}
DANGEROUS_PREFIXES = ("filesystem:", "shell:", "secrets:")


@dataclass
class McpPermissionEngine:
    enabled: bool = False
    mode: str = "off"  # off | catalog | propose | approve_each_time
    allowed_scopes: tuple[str, ...] = ()
    owner_id: str = ""

    def decide(self, proposal: ToolProposal, *, requester_id: str = "") -> PermissionDecision:
        if not self.enabled or self.mode == "off":
            return PermissionDecision(proposal.id, "denied", "MCP is disabled.")
        if self.mode == "catalog":
            return PermissionDecision(proposal.id, "denied", "MCP catalog mode does not execute tools.")
        requested = tuple(proposal.requested_scopes or ())
        denied = [scope for scope in requested if self._dangerous_or_unallowed(scope)]
        if denied:
            return PermissionDecision(proposal.id, "denied", f"Denied scopes: {', '.join(denied)}")
        if self.owner_id and str(requester_id) != str(self.owner_id):
            return PermissionDecision(proposal.id, "requires_approval", "Owner approval required.")
        return PermissionDecision(proposal.id, "requires_approval", "Explicit approval required.")

    def _dangerous_or_unallowed(self, scope: str) -> bool:
        if scope in DANGEROUS_SCOPES or any(scope.startswith(prefix) for prefix in DANGEROUS_PREFIXES):
            return True
        if scope.startswith("network:") and "network:*" not in self.allowed_scopes and scope not in self.allowed_scopes:
            return True
        if not self.allowed_scopes:
            return True
        return scope not in self.allowed_scopes

    @classmethod
    def from_settings(cls, settings: dict | None = None) -> "McpPermissionEngine":
        settings = settings or {}
        nested = settings.get("MCP") if isinstance(settings.get("MCP"), dict) else {}
        enabled = str(settings.get("MCP_ENABLED", nested.get("ENABLED", "false"))).lower() in ("1", "true", "yes", "on")
        mode = str(settings.get("MCP_MODE", nested.get("MODE", "off")) or "off")
        scopes: Iterable[str] = settings.get("MCP_ALLOWED_SCOPES") or nested.get("ALLOWED_SCOPES") or ()
        if isinstance(scopes, str):
            scopes = tuple(item.strip() for item in scopes.split(",") if item.strip())
        return cls(
            enabled=enabled,
            mode=mode,
            allowed_scopes=tuple(scopes),
            owner_id=str(settings.get("TELEGRAM_OWNER_ID") or settings.get("OWNER_ID") or ""),
        )
