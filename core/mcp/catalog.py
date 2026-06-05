"""MCP catalog loading and normalization."""

from __future__ import annotations

from typing import Iterable, Mapping

from .types import McpServer, McpTool


SENSITIVE_ARG_MARKERS = ("token", "secret", "password", "api-key", "apikey", "authorization", "bearer", "key")


def _redact_args(args: Iterable[str]) -> list[str]:
    safe: list[str] = []
    redact_next = False
    for raw in args:
        arg = str(raw)
        lowered = arg.lower()
        has_marker = any(marker in lowered for marker in SENSITIVE_ARG_MARKERS)
        if redact_next:
            safe.append("[redacted]")
            redact_next = False
            continue
        if has_marker:
            if "=" in arg:
                key, _value = arg.split("=", 1)
                safe.append(f"{key}=[redacted]")
            elif arg.startswith("-"):
                safe.append(arg)
                redact_next = True
            else:
                safe.append("[redacted]")
            continue
        safe.append(arg)
    return safe


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
                input_schema=tool.get("input_schema") if isinstance(tool.get("input_schema"), Mapping) else {},
            )
            for tool in raw.get("tools", ())
            if isinstance(tool, Mapping)
        )
        args = raw.get("args") or ()
        env = raw.get("env") or {}
        servers.append(McpServer(
            id=str(raw.get("id") or ""),
            name=str(raw.get("name") or raw.get("id") or ""),
            tools=tools,
            enabled=bool(raw.get("enabled", False)),
            transport=str(raw.get("transport") or "stdio"),
            command=str(raw.get("command") or ""),
            args=tuple(str(arg) for arg in args if str(arg).strip()),
            env={str(k): str(v) for k, v in env.items()} if isinstance(env, Mapping) else {},
            cwd=str(raw.get("cwd") or ""),
            timeout_seconds=float(raw.get("timeout_seconds") or 30.0),
        ))
    return tuple(server for server in servers if server.id)


def safe_catalog_snapshot(servers: Iterable[McpServer]) -> list[dict]:
    """Return catalog data safe enough for local status endpoints."""
    snapshot = []
    for server in servers:
        snapshot.append({
            "id": server.id,
            "name": server.name,
            "enabled": server.enabled,
            "transport": server.transport,
            "command": server.command,
            "args": _redact_args(server.args),
            "cwd": server.cwd,
            "timeout_seconds": server.timeout_seconds,
            "env_keys": sorted(server.env.keys()),
            "tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "scopes": list(tool.scopes),
                    "read_only": tool.read_only,
                    "has_input_schema": bool(tool.input_schema),
                }
                for tool in server.tools
            ],
        })
    return snapshot
