"""Sandboxed MCP runtime support.

MCP is default-off. When enabled, tool calls still move through proposal,
owner approval, explicit execution, and redacted audit records. Normal chat
generation does not execute MCP tools directly.
"""

from .types import McpServer, McpTool, PermissionDecision, ToolApproval, ToolProposal, ToolResult
from .permissions import McpPermissionEngine
from .audit import McpAuditLog
from .runtime import McpRuntime

__all__ = [
    "McpServer",
    "McpTool",
    "PermissionDecision",
    "ToolApproval",
    "ToolProposal",
    "ToolResult",
    "McpPermissionEngine",
    "McpAuditLog",
    "McpRuntime",
]
