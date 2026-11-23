# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-079 T002 (REQ-003, REQ-004 / SC-006, SC-007): frozen analyze-work and analyze descriptions."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest import mock

from agent_braid import analyze_work_schema, plugin_mcp
from agent_braid import tooling_mcp as core
from scripts import spec069_tool_schemas as generator
from tests.test_spec069_schema_delivery import FAKE_TYPES, _Router, cap_violation

PREFIX = "Bounded Agent Braid {}; host permissions and annotations do not grant runtime authority."
# Frozen text: a change to these strings changes what hosts read, so it must fail here on purpose.
UNITS_SENTENCE = "Parallel/overlap: aim; units can't show independence, refused if disjoint."
ANALYZE_WORK_PER_KIND = (
    UNITS_SENTENCE + " Digests: any sha256:<64 hex>, e.g. task-text hash; coverage complete if files named. "
    "git: branches, distinct attemptIds. Example: skill agent-braid-analyze.")
ANALYZE = ("It takes a plan-level request, not an analysis input, and does not compare proposed work for "
           "parallelism or overlap; for parallel or overlap questions use analyze-work.")
OLD_DIGEST_LINE = "aim needs sha256:<64 hex> digests"


class DescriptionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        base = Path(temp.name)
        (base / "s").mkdir(), (base / "r").mkdir()
        self.service = plugin_mcp.WorkspaceService("ws", core.ToolingConfig(base / "s", base / "r"))

    def listed(self, delivery=None):
        with mock.patch.object(analyze_work_schema, "DELIVERY", delivery or analyze_work_schema.DELIVERY):
            return {tool.name: tool for tool in plugin_mcp.tool_listing(
                _Router({"ws": self.service}), FAKE_TYPES)}

    def test_analyze_work_description(self):
        tool = self.listed("per-kind")["analyze-work"]
        self.assertEqual(tool.description, f"{PREFIX.format('analyze-work')} {ANALYZE_WORK_PER_KIND}")
        self.assertNotIn(OLD_DIGEST_LINE, tool.description)
        order = [tool.description.index(part) for part in
                 ("Parallel/overlap: aim", "refused if disjoint", "sha256:", "Example: skill")]
        self.assertEqual(order, sorted(order))
        only = self.listed("description-only")["analyze-work"]
        self.assertIn(UNITS_SENTENCE, only.description)
        self.assertNotIn(OLD_DIGEST_LINE, only.description)
        for delivery in generator.DELIVERIES:
            definition = self.listed(delivery)["analyze-work"]
            self.assertIsNone(cap_violation({"name": definition.name, "description": definition.description,
                                             "inputSchema": definition.input_schema}), delivery)

    def test_analyze_description(self):
        tool = self.listed()["analyze"]
        self.assertEqual(tool.description, f"{PREFIX.format('analyze')} {ANALYZE}")
        self.assertIsNone(cap_violation({"name": tool.name, "description": tool.description,
                                         "inputSchema": tool.input_schema}))
        self.assertNotIn("analyze-work", self.listed()["prepare"].description)


if __name__ == "__main__":
    unittest.main()
