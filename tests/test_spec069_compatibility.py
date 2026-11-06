# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T009 (procedure_009): schema notes and contract versions match the compatibility note."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from agent_braid import analysis, plugin_mcp, tooling_mcp
from scripts import spec069_divergence_inventory as inv

NOTE = (inv.ROOT / "specs/069-aim-request-authoring/compatibility.md").read_text()
LISTED = {
    inv.AIM_SCHEMA: {
        "/properties/instanceId/pattern", "/properties/attemptId/pattern",
        "/properties/definition/properties/id/pattern", "/properties/readVersions/propertyNames",
        "/properties/effects/properties/declared/items/properties/resource/pattern",
        "/properties/effects/properties/inferred/items/properties/resource/pattern",
        "/properties/effects/properties/observed/items/properties/resource/pattern",
        "/properties/effects/properties/coverage/properties/domain/pattern",
        "/properties/effects/properties/coverage/properties/method/pattern",
    },
    inv.GIT_SCHEMA: {
        "/properties/repository/pattern", "/properties/baseRevision/pattern",
        "/properties/operations/items/properties/instanceId/pattern",
        "/properties/operations/items/properties/attemptId/pattern",
        "/properties/operations/items/properties/source/oneOf/0/properties/revision/pattern",
    },
}


def keys(node, path=()):
    if isinstance(node, dict):
        for key, value in node.items():
            yield path + (key,), value
            yield from keys(value, path + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from keys(value, path + (index,))


def added(schema_path: Path) -> set[str]:
    old = {k: json.dumps(v, sort_keys=True) for k, v in keys(json.loads(inv.schema_text(schema_path, inv.BASELINE_REV)))}
    new = {k: json.dumps(v, sort_keys=True) for k, v in keys(json.loads(inv.schema_text(schema_path, None)))}
    return {"/" + "/".join(map(str, k)) for k, v in new.items()
            if old.get(k) != v and k[-1] != "$comment" and isinstance(k[-1], str) and k[-1] in {"pattern", "propertyNames"}
            and not (k[-1] == "pattern" and k[-2] == "propertyNames")}


class CompatibilityTests(unittest.TestCase):
    def test_tightened_keywords_equal_the_listed_notes(self):
        for schema_path, expected in LISTED.items():
            with self.subTest(schema_path.name):
                self.assertEqual(added(schema_path), expected)
                for pointer in expected:
                    self.assertIn(pointer, NOTE)

    def test_no_other_keyword_of_the_published_schemas_changed(self):
        for schema_path in LISTED:
            old = {k: json.dumps(v, sort_keys=True) for k, v in keys(json.loads(inv.schema_text(schema_path, inv.BASELINE_REV)))}
            new = {k: json.dumps(v, sort_keys=True) for k, v in keys(json.loads(inv.schema_text(schema_path, None)))}
            changed_leaf = [k for k, v in old.items() if k in new and new[k] != v
                            and not isinstance(json.loads(v), (dict, list))]
            self.assertEqual(changed_leaf, [], schema_path.name)

    def test_contract_versions_are_unchanged(self):
        self.assertEqual(plugin_mcp.SCHEMA, "agent-braid-plugin/v0.2")
        self.assertEqual(tooling_mcp.SCHEMA_VERSION, "agent-braid-tooling/v0.1")
        self.assertEqual(analysis.REPORT_VERSION, "0.1.0-alpha")
        self.assertEqual(analysis.ANALYZER_VERSION, "0.1.0-alpha")
        aim = json.loads(inv.AIM_SCHEMA.read_text())
        self.assertEqual(aim["properties"]["aimVersion"]["const"], "0.2.0-draft")
        self.assertEqual(json.loads(inv.GIT_SCHEMA.read_text())["properties"]["gitAnalysisRequestVersion"]["const"], "0.1.0-alpha")
        for version in ("agent-braid-plugin/v0.2", "agent-braid-tooling/v0.1", "0.2.0-draft"):
            self.assertIn(version, NOTE)

    def test_negative_control_an_unlisted_tightening_is_detected(self):
        listed = set(LISTED[inv.AIM_SCHEMA]) - {"/properties/instanceId/pattern"}
        self.assertNotEqual(added(inv.AIM_SCHEMA), listed)


if __name__ == "__main__":
    unittest.main()
