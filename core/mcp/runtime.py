"""Guarded MCP runtime service.

This module deliberately separates proposal, approval, and execution. Normal
chat generation does not call it directly; owner surfaces can use it to inspect
catalogs and explicitly approve or run a proposed tool call.
"""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass, replace
from pathlib import Path
from typing import Any, Callable, Mapping

from .audit import McpAuditLog
from .catalog import load_catalog, safe_catalog_snapshot
from .client import SdkMcpClient
from .permissions import McpPermissionEngine
from .types import McpServer, McpTool, ToolApproval, ToolProposal, ToolResult


SettingsGetter = Callable[[str, Any], Any]


def _json_default(value: Any) -> Any:
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, tuple):
        return list(value)
    return str(value)


SENSITIVE_KEY_FRAGMENTS = ("secret", "token", "password", "api_key", "apikey", "authorization", "credential")


def _redact_for_storage(value: Any) -> Any:
    if is_dataclass(value):
        value = asdict(value)
    if isinstance(value, Mapping):
        redacted = {}
        for key, child in value.items():
            key_text = str(key)
            if any(fragment in key_text.lower() for fragment in SENSITIVE_KEY_FRAGMENTS):
                redacted[key_text] = "[redacted]"
            else:
                redacted[key_text] = _redact_for_storage(child)
        return redacted
    if isinstance(value, tuple):
        return [_redact_for_storage(item) for item in value]
    if isinstance(value, list):
        return [_redact_for_storage(item) for item in value]
    return value


def _proposal_from_row(row: Mapping[str, Any], proposal_id: str) -> ToolProposal:
    raw = row.get("proposal") or {}
    return ToolProposal(
        server_id=str(raw.get("server_id") or ""),
        tool_name=str(raw.get("tool_name") or ""),
        arguments=raw.get("arguments") or {},
        requested_scopes=tuple(raw.get("requested_scopes") or ()),
        source=str(raw.get("source") or "assistant"),
        id=str(raw.get("id") or proposal_id),
        created_at=str(raw.get("created_at") or ""),
    )


class McpProposalStore:
    def __init__(self, path: Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def _load(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            data = json.loads(self.path.read_text())
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save(self, data: dict[str, dict]) -> None:
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=_json_default) + "\n")
        tmp.replace(self.path)

    def upsert(self, proposal: ToolProposal, *, status: str, decision: Any = None, result: Any = None) -> dict:
        data = self._load()
        existing = data.get(proposal.id, {})
        row = {
            **existing,
            "proposal": _redact_for_storage(asdict(proposal)),
            "status": status,
        }
        if decision is not None:
            row["decision"] = _redact_for_storage(asdict(decision) if is_dataclass(decision) else decision)
        if result is not None:
            row["result"] = _redact_for_storage(asdict(result) if is_dataclass(result) else result)
        data[proposal.id] = row
        self._save(data)
        return row

    def update(self, proposal_id: str, **fields: Any) -> dict | None:
        data = self._load()
        row = data.get(proposal_id)
        if not row:
            return None
        row.update(_redact_for_storage(fields))
        data[proposal_id] = row
        self._save(data)
        return row

    def get(self, proposal_id: str) -> dict | None:
        return self._load().get(proposal_id)

    def list(self, *, status: str | None = None, limit: int = 20) -> list[dict]:
        rows = list(self._load().values())
        if status:
            rows = [row for row in rows if row.get("status") == status]
        rows.sort(key=lambda row: row.get("proposal", {}).get("created_at", ""))
        return rows[-int(limit):] if limit else []


class McpRuntime:
    def __init__(
        self,
        base_path: Path,
        *,
        settings_getter: SettingsGetter | None = None,
        client: Any = None,
    ):
        self.base_path = Path(base_path)
        self._settings_getter = settings_getter
        self._client = client or SdkMcpClient()
        self._settings = self._load_settings()
        self.permission_engine = McpPermissionEngine.from_settings(self._settings)
        self.servers = self._load_servers()
        self.audit = McpAuditLog(self.base_path / "data" / "mcp" / "audit.jsonl")
        self.store = McpProposalStore(self.base_path / "data" / "mcp" / "proposals.json")
        self._live_arguments: dict[str, Mapping[str, Any]] = {}

    def _get(self, key: str, default: Any = None) -> Any:
        if self._settings_getter:
            try:
                return self._settings_getter(key, default)
            except TypeError:
                value = self._settings_getter(key)
                return default if value is None else value
            except Exception:
                return default
        return default

    def _load_settings(self) -> dict:
        settings = {}
        try:
            path = self.base_path / "config" / "settings.json"
            if path.exists():
                loaded = json.loads(path.read_text())
                if isinstance(loaded, dict):
                    settings.update(loaded)
        except Exception:
            pass
        for key in ("MCP_ENABLED", "MCP_MODE", "MCP_ALLOWED_SCOPES", "MCP_SERVERS", "TELEGRAM_OWNER_ID", "OWNER_ID"):
            value = self._get(key, None)
            if value is not None:
                settings[key] = value
        return settings

    def _server_entries(self) -> list[Mapping]:
        nested = self._settings.get("MCP") if isinstance(self._settings.get("MCP"), dict) else {}
        entries = self._settings.get("MCP_SERVERS") or nested.get("SERVERS") or ()
        return list(entries) if isinstance(entries, list) else []

    def _load_servers(self) -> tuple[McpServer, ...]:
        return load_catalog(self._server_entries())

    def refresh(self) -> None:
        self._settings = self._load_settings()
        self.permission_engine = McpPermissionEngine.from_settings(self._settings)
        self.servers = self._load_servers()

    def status(self) -> dict:
        pending = self.store.list(status="pending", limit=100)
        return {
            "enabled": self.permission_engine.enabled,
            "mode": self.permission_engine.mode,
            "allowed_scopes": list(self.permission_engine.allowed_scopes),
            "servers": safe_catalog_snapshot(self.servers),
            "pending_count": len(pending),
            "audit_path": str(self.audit.path),
            "proposal_store": str(self.store.path),
        }

    def _server(self, server_id: str) -> McpServer | None:
        return next((server for server in self.servers if server.id == server_id), None)

    def _catalog_tool(self, server_id: str, tool_name: str) -> McpTool | None:
        server = self._server(server_id)
        if not server:
            return None
        return next((tool for tool in server.tools if tool.name == tool_name), None)

    async def discover_tools(self, server_id: str) -> tuple[McpTool, ...]:
        server = self._server(server_id)
        if not server:
            raise ValueError(f"Unknown MCP server: {server_id}")
        discovered = await self._client.list_tools(server)
        merged = []
        for tool in discovered:
            declared = self._catalog_tool(server.id, tool.name)
            if declared:
                merged.append(McpTool(
                    server_id=server.id,
                    name=tool.name,
                    description=tool.description or declared.description,
                    scopes=declared.scopes,
                    read_only=declared.read_only,
                    input_schema=tool.input_schema or declared.input_schema,
                ))
            else:
                merged.append(tool)
        self.audit.record("discover_tools", {"server_id": server_id, "tool_count": len(merged)})
        return tuple(merged)

    def propose(
        self,
        server_id: str,
        tool_name: str,
        arguments: Mapping[str, Any] | None = None,
        *,
        requester_id: str = "",
        source: str = "assistant",
    ) -> tuple[ToolProposal, Any]:
        tool = self._catalog_tool(server_id, tool_name)
        requested_scopes = tool.scopes if tool else (f"mcp:{server_id}:{tool_name}",)
        proposal = ToolProposal(
            server_id=server_id,
            tool_name=tool_name,
            arguments=arguments or {},
            requested_scopes=requested_scopes,
            source=source,
        )
        self._live_arguments[proposal.id] = dict(arguments or {})
        decision = self.permission_engine.decide(proposal, requester_id=requester_id)
        status = "pending" if decision.status == "requires_approval" else "denied"
        self.store.upsert(proposal, status=status, decision=decision)
        self.audit.record("proposal", {"proposal": proposal, "decision": decision})
        return proposal, decision

    def approve(self, proposal_id: str, *, owner_id: str, reason: str = "") -> ToolApproval:
        row = self.store.get(proposal_id)
        if not row:
            approval = ToolApproval(proposal_id, "denied", owner_id=owner_id, reason="Unknown proposal.")
            self.audit.record("approval_denied", approval)
            return approval
        configured_owner = self.permission_engine.owner_id
        if configured_owner and str(owner_id) != str(configured_owner):
            approval = ToolApproval(proposal_id, "denied", owner_id=owner_id, reason="Only owner can approve MCP proposals.")
            self.audit.record("approval_denied", approval)
            return approval
        if row.get("status") != "pending":
            approval = ToolApproval(
                proposal_id,
                "denied",
                owner_id=owner_id,
                reason=f"Only pending MCP proposals can be approved; current status is {row.get('status') or 'unknown'}.",
            )
            self.audit.record("approval_denied", approval)
            return approval
        proposal = _proposal_from_row(row, proposal_id)
        decision = self.permission_engine.decide(proposal, requester_id=owner_id)
        if decision.status != "requires_approval":
            approval = ToolApproval(
                proposal_id,
                "denied",
                owner_id=owner_id,
                reason=decision.reason or "MCP proposal is no longer allowed.",
            )
            self.store.update(proposal_id, status="denied", decision=asdict(decision), approval=asdict(approval))
            self.audit.record("approval_denied", approval)
            return approval
        approval = ToolApproval(proposal_id, "approved", owner_id=owner_id, reason=reason)
        self.store.update(proposal_id, status="approved", approval=asdict(approval))
        self.audit.record("approval", approval)
        return approval

    def deny(self, proposal_id: str, *, owner_id: str, reason: str = "") -> ToolApproval:
        approval = ToolApproval(proposal_id, "denied", owner_id=owner_id, reason=reason or "Denied by owner.")
        self.store.update(proposal_id, status="denied", approval=asdict(approval))
        self.audit.record("denial", approval)
        return approval

    async def execute(self, proposal_id: str, *, requester_id: str = "") -> ToolResult:
        row = self.store.get(proposal_id)
        if not row:
            return ToolResult(proposal_id, False, "", error="Unknown MCP proposal.")
        if row.get("status") != "approved":
            return ToolResult(proposal_id, False, "", error="MCP proposal is not approved.")
        proposal = _proposal_from_row(row, proposal_id)
        if proposal_id in self._live_arguments:
            proposal = replace(proposal, arguments=dict(self._live_arguments[proposal_id]))
        server = self._server(proposal.server_id)
        if not server:
            result = ToolResult(proposal.id, False, "", error=f"Unknown MCP server: {proposal.server_id}")
            self.store.update(proposal_id, status="failed", result=asdict(result))
            self.audit.record("execution_failed", result)
            return result
        result = await self._client.call_tool(server, proposal)
        self.store.update(proposal_id, status="executed" if result.ok else "failed", result=asdict(result))
        self.audit.record("execution", result)
        return result

    def pending(self, limit: int = 20) -> list[dict]:
        return self.store.list(status="pending", limit=limit)
