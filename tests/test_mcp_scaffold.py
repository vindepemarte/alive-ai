import json
import tempfile
import unittest
from pathlib import Path

from core.mcp.audit import McpAuditLog
from core.mcp.catalog import load_catalog
from core.mcp.permissions import McpPermissionEngine
from core.mcp.types import ToolProposal


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


if __name__ == "__main__":
    unittest.main()
