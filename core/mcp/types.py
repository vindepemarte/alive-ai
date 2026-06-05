"""Typed MCP planning objects."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal, Mapping
import uuid


PermissionStatus = Literal["allowed", "denied", "requires_approval"]
ProposalStatus = Literal["pending", "approved", "denied", "executed", "failed"]
McpTransport = Literal["stdio"]


@dataclass(frozen=True)
class McpTool:
    server_id: str
    name: str
    description: str = ""
    scopes: tuple[str, ...] = ()
    read_only: bool = True
    input_schema: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class McpServer:
    id: str
    name: str
    tools: tuple[McpTool, ...] = ()
    enabled: bool = False
    transport: McpTransport = "stdio"
    command: str = ""
    args: tuple[str, ...] = ()
    env: Mapping[str, str] = field(default_factory=dict)
    cwd: str = ""
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class ToolProposal:
    server_id: str
    tool_name: str
    arguments: Mapping[str, Any] = field(default_factory=dict)
    requested_scopes: tuple[str, ...] = ()
    source: str = "assistant"
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(frozen=True)
class PermissionDecision:
    proposal_id: str
    status: PermissionStatus
    reason: str
    approved_scopes: tuple[str, ...] = ()
    owner_id: str = ""


@dataclass(frozen=True)
class ToolApproval:
    proposal_id: str
    status: ProposalStatus
    owner_id: str = ""
    reason: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(frozen=True)
class ToolResult:
    proposal_id: str
    ok: bool
    summary: str
    data: Mapping[str, Any] = field(default_factory=dict)
    error: str = ""
