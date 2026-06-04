"""Declaration-only MCP catalog.

The catalog deliberately does not connect to or execute MCP servers. It only
holds allowlisted declarations that a future approval UI can display.
"""

from __future__ import annotations

from typing import Iterable, Mapping

from .types import McpServer, McpTool


def load_catalog(entries: Iterable[Mapping] | None = None) -> tuple[McpServer, ...]:
    servers: list[McpServer] = []
    for raw in entries or ():
        tools = tuple(
            McpTool(
                server_id=str(raw.get("id") or ""),
                name=str(tool.get("name") or ""),
                description=str(tool.get("description") or ""),
                scopes=tuple(str(scope) for scope in tool.get("scopes", ()) if str(scope).strip()),
                read_only=bool(tool.get("read_only", True)),
            )
            for tool in raw.get("tools", ())
            if isinstance(tool, Mapping)
        )
        servers.append(McpServer(
            id=str(raw.get("id") or ""),
            name=str(raw.get("name") or raw.get("id") or ""),
            tools=tools,
            enabled=bool(raw.get("enabled", False)),
        ))
    return tuple(server for server in servers if server.id)
