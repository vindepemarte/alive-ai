import asyncio
import json
import tempfile
import unittest
from pathlib import Path

from core.mcp.audit import McpAuditLog
from core.mcp.catalog import load_catalog, safe_catalog_snapshot
from core.mcp.permissions import McpPermissionEngine
from core.mcp.runtime import McpRuntime
from core.mcp.types import McpTool, ToolProposal, ToolResult


class McpScaffoldTests(unittest.TestCase):
    def test_catalog_is_declaration_only(self):
        servers = load_catalog([
            {
                "id": "local",
                "name": "Local",
                "enabled": False,
                "tools": [{"name": "read_file", "scopes": ["read_project"], "read_only": True}],
            }
        ])

        self.assertEqual(len(servers), 1)
        self.assertFalse(servers[0].enabled)
        self.assertEqual(servers[0].tools[0].name, "read_file")

    def test_catalog_snapshot_redacts_sensitive_args(self):
        servers = load_catalog([
            {
                "id": "local",
                "name": "Local",
                "enabled": False,
                "command": "example",
                "args": ["--api-key", "secret-value", "--token=abc123", "Bearer real-token"],
                "env": {"TOKEN": "secret"},
            }
        ])

        snapshot = safe_catalog_snapshot(servers)
        serialized = json.dumps(snapshot)

        self.assertEqual(
            snapshot[0]["args"],
            ["--api-key", "[redacted]", "--token=[redacted]", "[redacted]"],
        )
        self.assertEqual(snapshot[0]["env_keys"], ["TOKEN"])
        self.assertNotIn("secret-value", serialized)
        self.assertNotIn("abc123", serialized)
        self.assertNotIn("real-token", serialized)

    def test_permission_engine_default_denies(self):
        engine = McpPermissionEngine()
        proposal = ToolProposal(server_id="local", tool_name="read_file", requested_scopes=("read_project",))

        decision = engine.decide(proposal, requester_id="owner")

        self.assertEqual(decision.status, "denied")

    def test_permission_engine_requires_approval_even_for_allowed_scope(self):
        engine = McpPermissionEngine(enabled=True, mode="approve_each_time", allowed_scopes=("read_project",), owner_id="owner")
        proposal = ToolProposal(server_id="local", tool_name="read_file", requested_scopes=("read_project",))

        decision = engine.decide(proposal, requester_id="owner")

        self.assertEqual(decision.status, "requires_approval")

    def test_enabled_engine_without_allowlist_still_denies_scopes(self):
        engine = McpPermissionEngine(enabled=True, mode="approve_each_time")
        proposal = ToolProposal(server_id="local", tool_name="read_file", requested_scopes=("read_project",))

        decision = engine.decide(proposal, requester_id="owner")

        self.assertEqual(decision.status, "denied")

    def test_filesystem_prefix_scope_is_dangerous(self):
        engine = McpPermissionEngine(
            enabled=True,
            mode="approve_each_time",
            allowed_scopes=("read_project", "filesystem:/Users/vdpm/.ssh"),
            owner_id="owner",
        )
        proposal = ToolProposal(
            server_id="local",
            tool_name="read_secret",
            requested_scopes=("filesystem:/Users/vdpm/.ssh",),
        )

        decision = engine.decide(proposal, requester_id="owner")

        self.assertEqual(decision.status, "denied")

    def test_audit_redacts_sensitive_payload(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "mcp.jsonl"
            audit = McpAuditLog(path)

            audit.record("proposed", {"token": "secret", "safe": "ok"})

            row = json.loads(path.read_text().splitlines()[0])
            self.assertEqual(row["payload"]["token"], "[redacted]")
            self.assertEqual(row["payload"]["safe"], "ok")

    def test_runtime_status_hides_env_values_and_counts_pending(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = base / "config"
            config.mkdir()
            (config / "settings.json").write_text(json.dumps({
                "MCP_ENABLED": True,
                "MCP_MODE": "approve_each_time",
                "MCP_ALLOWED_SCOPES": ["read_project"],
                "TELEGRAM_OWNER_ID": "owner",
                "MCP_SERVERS": [
                    {
                        "id": "local",
                        "enabled": True,
                        "command": "example",
                        "env": {"TOKEN": "secret"},
                        "tools": [{"name": "read_file", "scopes": ["read_project"]}],
                    }
                ],
            }))

            runtime = McpRuntime(base)
            proposal, decision = runtime.propose(
                "local",
                "read_file",
                {"path": "README.md"},
                requester_id="owner",
            )
            status = runtime.status()

            self.assertEqual(decision.status, "requires_approval")
            self.assertEqual(status["pending_count"], 1)
            self.assertEqual(status["servers"][0]["env_keys"], ["TOKEN"])
            self.assertNotIn("secret", json.dumps(status))
            self.assertEqual(proposal.tool_name, "read_file")

    def test_runtime_approval_required_before_execution(self):
        class FakeClient:
            def __init__(self):
                self.calls = []

            async def call_tool(self, server, proposal):
                self.calls.append((server.id, proposal.tool_name, dict(proposal.arguments)))
                return ToolResult(proposal.id, True, "read ok", data={"safe": True})

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = base / "config"
            config.mkdir()
            (config / "settings.json").write_text(json.dumps({
                "MCP_ENABLED": True,
                "MCP_MODE": "approve_each_time",
                "MCP_ALLOWED_SCOPES": ["read_project"],
                "TELEGRAM_OWNER_ID": "owner",
                "MCP_SERVERS": [
                    {
                        "id": "local",
                        "enabled": True,
                        "command": "example",
                        "tools": [{"name": "read_file", "scopes": ["read_project"]}],
                    }
                ],
            }))

            fake = FakeClient()
            runtime = McpRuntime(base, client=fake)
            proposal, _decision = runtime.propose(
                "local",
                "read_file",
                {"path": "README.md"},
                requester_id="owner",
            )

            blocked = asyncio.run(runtime.execute(proposal.id, requester_id="owner"))
            self.assertFalse(blocked.ok)
            self.assertEqual(fake.calls, [])

            approval = runtime.approve(proposal.id, owner_id="owner")
            result = asyncio.run(runtime.execute(proposal.id, requester_id="owner"))

            self.assertEqual(approval.status, "approved")
            self.assertTrue(result.ok)
            self.assertEqual(result.summary, "read ok")
            self.assertEqual(fake.calls, [("local", "read_file", {"path": "README.md"})])

    def test_runtime_denies_dangerous_scope_even_if_configured(self):
        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = base / "config"
            config.mkdir()
            (config / "settings.json").write_text(json.dumps({
                "MCP_ENABLED": True,
                "MCP_MODE": "approve_each_time",
                "MCP_ALLOWED_SCOPES": ["filesystem:/Users/vdpm/.ssh"],
                "MCP_SERVERS": [
                    {
                        "id": "local",
                        "enabled": True,
                        "command": "example",
                        "tools": [{"name": "read_secret", "scopes": ["filesystem:/Users/vdpm/.ssh"]}],
                    }
                ],
            }))

            runtime = McpRuntime(base)
            _proposal, decision = runtime.propose("local", "read_secret", {}, requester_id="owner")

            self.assertEqual(decision.status, "denied")

    def test_denied_runtime_proposal_cannot_be_approved_or_executed(self):
        class FakeClient:
            def __init__(self):
                self.calls = []

            async def call_tool(self, server, proposal):
                self.calls.append((server.id, proposal.tool_name, dict(proposal.arguments)))
                return ToolResult(proposal.id, True, "should not run")

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = base / "config"
            config.mkdir()
            (config / "settings.json").write_text(json.dumps({
                "MCP_ENABLED": True,
                "MCP_MODE": "approve_each_time",
                "MCP_ALLOWED_SCOPES": ["filesystem:/Users/vdpm/.ssh"],
                "TELEGRAM_OWNER_ID": "owner",
                "MCP_SERVERS": [
                    {
                        "id": "local",
                        "enabled": True,
                        "command": "example",
                        "tools": [{"name": "read_secret", "scopes": ["filesystem:/Users/vdpm/.ssh"]}],
                    }
                ],
            }))

            fake = FakeClient()
            runtime = McpRuntime(base, client=fake)
            proposal, decision = runtime.propose("local", "read_secret", {}, requester_id="owner")
            approval = runtime.approve(proposal.id, owner_id="owner")
            result = asyncio.run(runtime.execute(proposal.id, requester_id="owner"))

            self.assertEqual(decision.status, "denied")
            self.assertEqual(approval.status, "denied")
            self.assertFalse(result.ok)
            self.assertEqual(fake.calls, [])

    def test_proposal_store_redacts_sensitive_arguments_but_live_execution_keeps_args(self):
        class FakeClient:
            def __init__(self):
                self.calls = []

            async def call_tool(self, server, proposal):
                self.calls.append(dict(proposal.arguments))
                return ToolResult(proposal.id, True, "ok")

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = base / "config"
            config.mkdir()
            (config / "settings.json").write_text(json.dumps({
                "MCP_ENABLED": True,
                "MCP_MODE": "approve_each_time",
                "MCP_ALLOWED_SCOPES": ["read_project"],
                "TELEGRAM_OWNER_ID": "owner",
                "MCP_SERVERS": [
                    {
                        "id": "local",
                        "enabled": True,
                        "command": "example",
                        "tools": [{"name": "read_file", "scopes": ["read_project"]}],
                    }
                ],
            }))

            fake = FakeClient()
            runtime = McpRuntime(base, client=fake)
            proposal, decision = runtime.propose(
                "local",
                "read_file",
                {"path": "README.md", "api_key": "secret-value"},
                requester_id="owner",
            )
            stored = (base / "data" / "mcp" / "proposals.json").read_text()
            runtime.approve(proposal.id, owner_id="owner")
            result = asyncio.run(runtime.execute(proposal.id, requester_id="owner"))

            self.assertEqual(decision.status, "requires_approval")
            self.assertNotIn("secret-value", stored)
            self.assertIn("[redacted]", stored)
            self.assertTrue(result.ok)
            self.assertEqual(fake.calls, [{"path": "README.md", "api_key": "secret-value"}])

    def test_runtime_discovery_merges_declared_scopes(self):
        class FakeClient:
            async def list_tools(self, server):
                return (
                    McpTool(server_id=server.id, name="read_file", scopes=("mcp:raw",), input_schema={"type": "object"}),
                )

        with tempfile.TemporaryDirectory() as tmp:
            base = Path(tmp)
            config = base / "config"
            config.mkdir()
            (config / "settings.json").write_text(json.dumps({
                "MCP_ENABLED": True,
                "MCP_MODE": "approve_each_time",
                "MCP_ALLOWED_SCOPES": ["read_project"],
                "MCP_SERVERS": [
                    {
                        "id": "local",
                        "enabled": True,
                        "command": "example",
                        "tools": [{"name": "read_file", "scopes": ["read_project"], "description": "declared"}],
                    }
                ],
            }))

            runtime = McpRuntime(base, client=FakeClient())
            tools = asyncio.run(runtime.discover_tools("local"))

            self.assertEqual(tools[0].scopes, ("read_project",))
            self.assertEqual(tools[0].input_schema, {"type": "object"})


if __name__ == "__main__":
    unittest.main()
