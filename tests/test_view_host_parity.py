# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T076 (REQ-029): the host-parity contract is machine-checkable and agrees with the loom contract.

`contracts/host-parity.md` states the rules; the capability table lives in `contracts/surfaces-matrix.json`
under `hostParity`. These tests keep the table closed (three values, known capabilities, known hosts), tie every
cell that claims evidence to a receipt that exists for that host, tie every mapped loom kind and member to the
schemas, and keep the "absent, not zero" and privacy rules in the prose. They check structure, not host behaviour.
"""
import json
import re
import unittest
from pathlib import Path

from agent_braid import view_loom
from agent_braid.view_hooks import OBSERVATIONAL_EVENTS

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs" / "061-activity-viewer"
CONTRACT = SPEC / "contracts" / "host-parity.md"
MATRIX = SPEC / "contracts" / "surfaces-matrix.json"
V01 = SPEC / "contracts" / "loom-event.schema.json"
V02 = SPEC / "contracts" / "loom-event.v0.2.schema.json"

PARITY = json.loads(MATRIX.read_text(encoding="utf-8"))["hostParity"]
PROSE = " ".join(CONTRACT.read_text(encoding="utf-8").lower().split())
HOSTS = ("claude-code", "codex", "opencode")
VALUES = ("provided", "absent", "unknown")
EXPECTED_CAPABILITIES = (
    "session.open", "session.close", "subagent.open", "subagent.close", "tool.call", "tool.duration",
    "waiting", "turn.idle", "outcome",
)


def cells():
    for host, entry in PARITY["hosts"].items():
        for capability, cell in entry["cells"].items():
            yield host, capability, cell


class TableShapeTests(unittest.TestCase):
    def test_the_vocabulary_is_closed(self):
        self.assertEqual(tuple(PARITY["capabilityValues"]), VALUES)
        self.assertEqual(tuple(PARITY["basisValues"]), ("receipt", "policy", "derived", "none"))
        self.assertEqual(tuple(PARITY["hosts"]), HOSTS)
        self.assertEqual(tuple(item["id"] for item in PARITY["capabilities"]), EXPECTED_CAPABILITIES)

    def test_every_host_has_exactly_one_cell_per_capability(self):
        for host, entry in PARITY["hosts"].items():
            with self.subTest(host):
                self.assertEqual(set(entry["cells"]), set(EXPECTED_CAPABILITIES))

    def test_cells_use_the_closed_vocabulary_and_say_why(self):
        for host, capability, cell in cells():
            with self.subTest(host=host, capability=capability):
                self.assertIn(cell["status"], VALUES)
                self.assertIn(cell["basis"], PARITY["basisValues"])
                self.assertTrue(cell["note"].strip())

    def test_basis_and_evidence_agree_with_the_status(self):
        for host, capability, cell in cells():
            with self.subTest(host=host, capability=capability):
                if cell["status"] == "unknown":
                    self.assertEqual(cell["basis"], "none")
                    self.assertIsNone(cell["evidence"])
                else:
                    self.assertNotEqual(cell["basis"], "none")
                if cell["basis"] in ("receipt", "derived"):
                    self.assertTrue(cell["evidence"])
                if cell["basis"] == "policy":
                    self.assertIsNone(cell["evidence"])

    def test_every_evidence_file_is_a_receipt_of_that_host(self):
        for host, capability, cell in cells():
            if cell["evidence"] is None:
                continue
            with self.subTest(host=host, capability=capability):
                path = SPEC / "evidence" / cell["evidence"]
                self.assertTrue(path.is_file(), cell["evidence"])
                receipt = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(receipt["host"]["name"], host)

    def test_a_host_with_no_probe_is_all_unknown(self):
        for capability, cell in PARITY["hosts"]["opencode"]["cells"].items():
            with self.subTest(capability):
                self.assertEqual(cell["status"], "unknown")

    def test_codex_claims_nothing_until_a_completed_turn_is_probed(self):
        for capability, cell in PARITY["hosts"]["codex"]["cells"].items():
            with self.subTest(capability):
                self.assertEqual(cell["status"], "unknown")

    def test_receipt_names_are_really_in_the_cited_receipt(self):
        for host, capability, cell in cells():
            if cell["evidence"] is None:
                self.assertEqual(cell["receiptNames"], [])
                continue
            with self.subTest(host=host, capability=capability):
                self.assertTrue(cell["receiptNames"])
                raw = (SPEC / "evidence" / cell["evidence"]).read_text(encoding="utf-8")
                for name in cell["receiptNames"]:
                    self.assertIn(f'"{name}"', raw)

    def test_the_header_points_at_this_contract(self):
        self.assertEqual(PARITY["schemaVersion"], "agent-braid-view-host-parity/v0.1")
        self.assertTrue((SPEC / "contracts" / PARITY["contract"]).is_file())

    def test_the_markdown_table_agrees_with_the_matrix(self):
        section = CONTRACT.read_text(encoding="utf-8").split("## Capability table", 1)[1].split("\n## ", 1)[0]
        rows = {}
        for line in section.splitlines():
            match = re.match(r"^\| `([a-z.]+)` \| (\w+)[^|]*\| (\w+)[^|]*\| (\w+)[^|]*\|$", line)
            if match:
                rows[match.group(1)] = match.groups()[1:]
        self.assertEqual(set(rows), set(EXPECTED_CAPABILITIES))
        for capability, statuses in rows.items():
            with self.subTest(capability):
                self.assertEqual(statuses, tuple(PARITY["hosts"][host]["cells"][capability]["status"]
                                                 for host in HOSTS))


def enums_by_property(node, found=None):
    """Every enum list found under a property of that name, anywhere in a JSON schema."""
    found = {} if found is None else found
    if isinstance(node, dict):
        for name, child in node.get("properties", {}).items():
            if isinstance(child, dict) and "enum" in child:
                found.setdefault(name, set()).update(child["enum"])
        for child in node.values():
            enums_by_property(child, found)
    elif isinstance(node, list):
        for child in node:
            enums_by_property(child, found)
    return found


class LoomAgreementTests(unittest.TestCase):
    V01_TEXT = V01.read_text(encoding="utf-8")
    V01_SCHEMA = json.loads(V01_TEXT)
    V02_TEXT = V02.read_text(encoding="utf-8")
    V02_SCHEMA = json.loads(V02_TEXT)

    def test_mapped_kinds_and_versions_exist(self):
        for item in PARITY["capabilities"]:
            with self.subTest(item["id"]):
                self.assertIn(item["loomKind"], view_loom.KINDS)
                self.assertIn(item["since"], ("v0.1", "v0.2"))

    def test_v02_members_are_exactly_the_ones_v01_refuses(self):
        members = {item["member"] for item in PARITY["capabilities"] if item["since"] == "v0.2"}
        self.assertEqual(members, {"toolDurationMs", "waitingOn"})
        for item in PARITY["capabilities"]:
            if item["since"] == "v0.1":
                self.assertIsNone(item["member"], item["id"])
        v01_members = set(self.V01_SCHEMA["properties"]["data"].get("properties", {}))
        for member in members:
            self.assertIn(f'"{member}"', self.V02_TEXT)
            self.assertNotIn(f'"{member}"', self.V01_TEXT)
            self.assertNotIn(member, v01_members)

    def test_mapped_values_are_in_the_named_schema_enum(self):
        enums = enums_by_property(self.V02_SCHEMA)
        for item in PARITY["capabilities"]:
            with self.subTest(item["id"]):
                self.assertEqual(bool(item["values"]), "valueProperty" in item)
                if item["values"]:
                    self.assertLessEqual(set(item["values"]), enums[item["valueProperty"]])

    def test_the_claude_column_agrees_with_the_existing_hook_adapter(self):
        provided = {capability for capability, cell in PARITY["hosts"]["claude-code"]["cells"].items()
                    if cell["status"] == "provided"}
        self.assertEqual(provided, {"session.open", "session.close", "subagent.open", "subagent.close",
                                    "tool.call", "tool.duration"})
        self.assertEqual(set(OBSERVATIONAL_EVENTS),
                         {"SessionStart", "SessionEnd", "SubagentStart", "SubagentStop", "PostToolUse"})
        self.assertEqual(PARITY["hosts"]["claude-code"]["cells"]["turn.idle"]["basis"], "policy")

    def test_adapter_and_host_names_are_known_or_declared_unassigned(self):
        for host, entry in PARITY["hosts"].items():
            with self.subTest(host):
                for adapter in entry["adapters"]:
                    self.assertTrue(adapter in view_loom.ADAPTERS or adapter.startswith("unassigned:"), adapter)
                self.assertIn(entry["loomHost"], view_loom.HOSTS)


class ProseTests(unittest.TestCase):
    def test_the_rules_are_stated(self):
        for statement in (
            "absent, not zero", "never shown as zero", "executionauthorization: false", "decision event",
            "empty body", "names, never values", "not a guarantee", "labels only",
            "does not change `agent-braid-loom/v0.1`", "unknown",
        ):
            with self.subTest(statement):
                self.assertIn(statement, PROSE)

    def test_the_prose_names_every_capability_and_host(self):
        for capability in EXPECTED_CAPABILITIES:
            with self.subTest(capability):
                self.assertIn(f"`{capability}`", PROSE)
        for host in ("claude code", "codex", "opencode"):
            self.assertIn(host, PROSE)

    def test_the_open_items_for_later_tasks_are_listed(self):
        for item in ("t077", "t078", "t079", "t080", "t081", "adr 0037"):
            with self.subTest(item):
                self.assertIn(item, PROSE)


if __name__ == "__main__":
    unittest.main()
