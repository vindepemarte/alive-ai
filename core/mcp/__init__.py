"""Sandboxed MCP scaffolding.

MCP execution is intentionally disabled in v0.2.0. These modules define the
catalog, permission, and audit shapes so future tool use can be added behind an
explicit owner approval gate.
"""

from .types import McpServer, McpTool, PermissionDecision, ToolProposal, ToolResult
from .permissions import McpPermissionEngine
from .audit import McpAuditLog

__all__ = [
    "McpServer",
    "McpTool",
    "PermissionDecision",
    "ToolProposal",
    "ToolResult",
    "McpPermissionEngine",
    "McpAuditLog",
]
