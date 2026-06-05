"""MCP client transport wrappers.

The official SDK is imported lazily so MCP remains optional and fails closed
when the package or a configured server is unavailable.
"""

from __future__ import annotations

import sys
from dataclasses import asdict
from datetime import timedelta
from typing import Any

from .types import McpServer, McpTool, ToolProposal, ToolResult


class McpClientError(RuntimeError):
    pass


def _tool_name(raw: Any) -> str:
    return str(getattr(raw, "name", "") or "")


def _tool_description(raw: Any) -> str:
    return str(getattr(raw, "description", "") or "")


def _tool_input_schema(raw: Any) -> dict:
    value = getattr(raw, "inputSchema", None) or getattr(raw, "input_schema", None) or {}
    return value if isinstance(value, dict) else {}


def _tool_read_only(raw: Any) -> bool:
    annotations = getattr(raw, "annotations", None)
    if annotations is None:
        return True
    for attr in ("readOnlyHint", "read_only_hint", "readOnly"):
        if hasattr(annotations, attr):
            return bool(getattr(annotations, attr))
    return True


def _content_preview(result: Any) -> str:
    parts = []
    for item in getattr(result, "content", []) or []:
        text = getattr(item, "text", None)
        if text:
            parts.append(str(text))
            continue
        if hasattr(item, "model_dump"):
            parts.append(str(item.model_dump()))
        else:
            parts.append(str(item))
    preview = "\n".join(parts).strip()
    return preview[:800]


class SdkMcpClient:
    """Small adapter around the official MCP Python SDK."""

    async def list_tools(self, server: McpServer) -> tuple[McpTool, ...]:
        if not server.enabled:
            raise McpClientError(f"MCP server {server.id} is disabled")
        if server.transport != "stdio":
            raise McpClientError(f"Unsupported MCP transport: {server.transport}")
        if not server.command:
            raise McpClientError(f"MCP server {server.id} has no command")

        try:
            from mcp import ClientSession
            from mcp.client.stdio import StdioServerParameters, stdio_client
        except Exception as exc:
            raise McpClientError(f"Official MCP SDK is not installed: {exc}") from exc

        params = StdioServerParameters(
            command=server.command,
            args=list(server.args),
            env=dict(server.env) if server.env else None,
            cwd=server.cwd or None,
        )
        async with stdio_client(params, errlog=sys.stderr) as (read_stream, write_stream):
            async with ClientSession(
                read_stream,
                write_stream,
                read_timeout_seconds=timedelta(seconds=server.timeout_seconds),
            ) as session:
                await session.initialize()
                listed = await session.list_tools()
                tools = []
                for raw in getattr(listed, "tools", []) or []:
                    name = _tool_name(raw)
                    if not name:
                        continue
                    tools.append(McpTool(
                        server_id=server.id,
                        name=name,
                        description=_tool_description(raw),
                        scopes=(f"mcp:{server.id}:{name}",),
                        read_only=_tool_read_only(raw),
                        input_schema=_tool_input_schema(raw),
                    ))
                return tuple(tools)

    async def call_tool(self, server: McpServer, proposal: ToolProposal) -> ToolResult:
        if not server.enabled:
            return ToolResult(proposal.id, False, "", error=f"MCP server {server.id} is disabled")
        if server.transport != "stdio":
            return ToolResult(proposal.id, False, "", error=f"Unsupported MCP transport: {server.transport}")
        if not server.command:
            return ToolResult(proposal.id, False, "", error=f"MCP server {server.id} has no command")

        try:
            from mcp import ClientSession
            from mcp.client.stdio import StdioServerParameters, stdio_client
        except Exception as exc:
            return ToolResult(proposal.id, False, "", error=f"Official MCP SDK is not installed: {exc}")

        params = StdioServerParameters(
            command=server.command,
            args=list(server.args),
            env=dict(server.env) if server.env else None,
            cwd=server.cwd or None,
        )
        try:
            async with stdio_client(params, errlog=sys.stderr) as (read_stream, write_stream):
                async with ClientSession(
                    read_stream,
                    write_stream,
                    read_timeout_seconds=timedelta(seconds=server.timeout_seconds),
                ) as session:
                    await session.initialize()
                    result = await session.call_tool(
                        proposal.tool_name,
                        dict(proposal.arguments or {}),
                        read_timeout_seconds=timedelta(seconds=server.timeout_seconds),
                    )
                    return ToolResult(
                        proposal.id,
                        ok=not bool(getattr(result, "isError", False)),
                        summary=_content_preview(result),
                        data={
                            "server_id": server.id,
                            "tool_name": proposal.tool_name,
                            "structured": getattr(result, "structuredContent", None) or {},
                        },
                        error="" if not bool(getattr(result, "isError", False)) else _content_preview(result),
                    )
        except Exception as exc:
            return ToolResult(proposal.id, False, "", data={"proposal": asdict(proposal)}, error=str(exc))
