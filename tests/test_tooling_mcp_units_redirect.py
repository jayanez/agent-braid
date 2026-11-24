# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-079 T001 (REQ-001, REQ-002 / SC-001..SC-005): disjoint ``units`` requests are refused and redirected."""

from __future__ import annotations

import copy
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import patch

from agent_braid import analysis, tooling_mcp, units
from agent_braid.tooling_mcp import ToolingConfig, ToolingService
from scripts.spec069_generate_corpus import unit, units_request as request

CODE = "units-cannot-answer-independence"
DISJOINT = request(unit("edit-readme", ("write", "README.md")), unit("edit-guide", ("write", "docs/guide.md")))


def _pre_change_units(self, args):
    """The SPEC-069 `units` path before SPEC-079: construct, bound, analyze, return ok."""
    built = units.construct(args["request"], units.workspace_scope(self.config.source_root))
    tooling_mcp._validate_operation_bounds(args["request"])
    tooling_mcp._validate_operation_bounds(built["constructedRequest"])
    return self._advised({"report": analysis.analyze(built["constructedRequest"]), **built},
                         "units", built["constructedRequest"])


class UnitsRedirectTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        source, results = Path(temp.name) / "source", Path(temp.name) / "results"
        source.mkdir(), results.mkdir()
        self.service = ToolingService(ToolingConfig(source, results))

    def call(self, kind, value):
        return self.service.invoke("analyze-work", {"kind": kind, "request": value}, threading.Event())

    def stable(self, envelope):
        """Envelope without the per-call identifiers (run and artifact ids)."""
        value = copy.deepcopy(envelope)
        for ref in value["evidenceRefs"]:
            ref.pop("artifactId"), ref.pop("uri")
        return value

    def test_disjoint_units_are_refused(self):
        """SC-001: every declaration whose pre-change report has only `unknown` pairs is refused.

        Sharing a resource conflicts only through a write-like effect (`analysis.WRITE_LIKE`), so units
        that share a `call` or an `emit`/`read` target are disjoint too.
        """
        cases = {
            "different writes": DISJOINT,
            "shared read": request(unit("a", ("read", "README.md"), ("write", "a.txt")),
                                   unit("b", ("read", "README.md"), ("write", "b.txt")),
                                   unit("c", ("emit", "events/c"))),
            "call/call": request(unit("a", ("call", "api/x")), unit("b", ("call", "api/x"))),
            "emit/read": request(unit("a", ("emit", "events/x")), unit("b", ("read", "events/x"))),
        }
        for label, value in cases.items():
            with self.subTest(label):
                with patch.object(ToolingService, "_analyze_work", lambda s, a: _pre_change_units(s, a)):
                    before = self.call("units", value)
                self.assertEqual({pair["classification"] for pair in before["result"]["report"]["interactions"]},
                                 {"unknown"})
                envelope = self.call("units", value)
                self.assertEqual(envelope["status"], "refused", envelope["summary"])
                self.assertTrue(envelope["summary"].endswith(f"[{CODE}]"), envelope["summary"])
                self.assertNotIn("report", envelope["result"])
                self.assertEqual(envelope["evidenceRefs"], [])

    def test_refusal_reason_reaches_the_observation(self):
        observation = type("Observation", (), {"reason": None})()
        envelope = self.service.invoke("analyze-work", {"kind": "units", "request": DISJOINT},
                                       threading.Event(), observation)
        self.assertEqual(envelope["status"], "refused")
        self.assertEqual(observation.reason, CODE)

    def test_overlapping_units_unchanged(self):
        """SC-002 golden comparison: every non-disjoint or single-unit declaration keeps the pre-change envelope."""
        cases = {
            "same write": request(unit("a", ("write", "README.md")), unit("b", ("write", "README.md"))),
            "write/read": request(unit("a", ("write", "docs/guide.md")), unit("b", ("read", "docs/guide.md"))),
            "dependency": request(unit("a", ("write", "a.txt")), unit("b", ("write", "b.txt"), dependencies=["a"])),
            "mixed": request(unit("a", ("write", "a.txt")), unit("b", ("write", "b.txt")),
                             unit("c", ("delete", "a.txt"))),
            "single unit": request(unit("a", ("write", "a.txt"))),
            "alias overlap": request(unit("a", ("write", "README.md")), unit("b", ("write", "./README.md"))),
            "call/transform": request(unit("a", ("call", "api/x")), unit("b", ("transform", "api/x"))),
            "emit/deploy": request(unit("a", ("emit", "events/x")), unit("b", ("deploy", "events/x"))),
        }
        for label, value in cases.items():
            with self.subTest(label):
                with patch("uuid.uuid4") as fake:
                    fake.return_value.hex = "0" * 32
                    after = self.call("units", value)
                with patch.object(ToolingService, "_analyze_work", lambda s, a: _pre_change_units(s, a)), \
                        patch("uuid.uuid4") as fake:
                    fake.return_value.hex = "0" * 32
                    before = self.call("units", value)
                self.assertEqual(after["status"], "ok", after["summary"])
                if len(value["units"]) > 1:
                    self.assertNotEqual({pair["classification"] for pair in after["result"]["report"]["interactions"]},
                                        {"unknown"})
                self.assertEqual(tooling_mcp._json_bytes(after), tooling_mcp._json_bytes(before))

    def test_validation_refusal_first(self):
        """SC-003: a malformed declaration gets the existing validation refusal, never the redirect."""
        malformed = {
            "dot-dot": request(unit("a", ("write", "../x")), unit("b", ("write", "b"))),
            "duplicate id": request(unit("a", ("write", "a")), unit("a", ("write", "b"))),
            "bad version": {"unitsRequestVersion": "9", "units": DISJOINT["units"]},
        }
        for label, value in malformed.items():
            with self.subTest(label):
                envelope = self.call("units", value)
                self.assertEqual(envelope["status"], "refused")
                self.assertNotIn(CODE, envelope["summary"])
                self.assertIsNone(envelope["result"])

    def test_redirect_is_bounded(self):
        """SC-004: the message names kind aim and the skill within 400 characters; no execution authority."""
        envelope = self.call("units", DISJOINT)
        message = envelope["summary"].removeprefix("analyze-work refused: ")
        self.assertLessEqual(len(message), 400)
        self.assertIn("kind aim", message)
        self.assertIn("agent-braid-analyze", message)
        self.assertIs(envelope["provenance"]["executionAuthorization"], False)
        self.assertIs(envelope["result"]["provenance"]["executionAuthorization"], False)
        self.assertEqual(envelope["result"]["provenance"]["coverage"], "partial")

    def test_replay_cannot_fabricate_coverage(self):
        """SC-005: the attached envelope replayed unchanged as kind aim stays partial and never independent."""
        constructed = self.call("units", DISJOINT)["result"]["constructedRequest"]
        self.assertEqual({op["effects"]["coverage"]["status"] for op in constructed["operations"]}, {"partial"})
        replay = self.call("aim", constructed)
        self.assertEqual(replay["status"], "ok", replay["summary"])
        classes = {pair["classification"] for pair in replay["result"]["report"]["interactions"]}
        self.assertNotIn("independent-candidate", classes)


if __name__ == "__main__":
    unittest.main()
