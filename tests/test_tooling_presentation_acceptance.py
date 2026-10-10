# SPDX-License-Identifier: AGPL-3.0-only
"""Paired, deterministic presentation procedures for SPEC-043 SC-002..SC-007."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

from agent_braid import tooling_present as present


def envelope(result, *, operation="analyze-work", status="ok"):
    return {"schemaVersion": "agent-braid-tooling/v0.1", "operation": operation,
            "status": status, "summary": "fixture adapter detail", "result": result,
            "evidenceRefs": ["owned-evidence-1"], "limits": ["No correctness claim."],
            "provenance": {"candidate": "a" * 40, "runtimeVersion": "0.1.0-test"}}


class PresentationAcceptance(unittest.TestCase):
    def owned_fixture(self, value):
        tmp = tempfile.TemporaryDirectory(prefix="m45-presentation-")
        self.addCleanup(tmp.cleanup)
        root = Path(tmp.name).resolve()
        source, results = root / "source", root / "results"
        source.mkdir(); results.mkdir()
        path = source / "input.json"
        path.write_bytes(present.canonical_json(value))
        return source, results, path

    def test_sc002_summary_agrees_with_every_classification_and_unknown_stays_unknown(self):
        value = envelope({"interactions": [
            {"classification": "independent-candidate"}, {"classification": "unknown"},
            {"classification": "conflicting"}, {"classification": "conditional"}],
            "executionAuthorization": False})
        source, results, fixture = self.owned_fixture(value)
        text = present.render_summary(json.loads(fixture.read_bytes()))
        self.assertIn("independent-candidate=1", text)
        self.assertIn("unknown=1", text)
        self.assertIn("conflicting=1", text)
        self.assertIn("conditional=1", text)
        self.assertNotIn("independent=", text)
        self.assertEqual(source.joinpath("input.json").read_bytes(), fixture.read_bytes())
        with self.assertRaises(present.PresentationError):
            present.render_summary(envelope({"interactions": [{"classification": "independent"}]}))
        self.assertTrue(results.is_dir())

    def test_sc003_summary_explains_missing_grant_and_records_limited_success_scope(self):
        refused = envelope({"status": "refused", "reasonCode": "missing-grant",
                            "executionAuthorization": False}, operation="execute", status="refused")
        text = present.render_summary(refused)
        self.assertIn("Adapter status: refused", text)
        self.assertIn("missing-grant", text)
        self.assertIn("exact existing operator grant is required", text)
        self.assertIn("this interface never issues one", text)
        success = present.render_summary(envelope({"dispatch": "performed",
                                                   "executionAuthorization": True}, operation="execute"))
        self.assertIn("Core reports execution authorization: true for this recorded operation only", success)
        self.assertIn("does not establish code correctness", success)
        self.assertNotIn("host approval", success.lower())

    def test_sc004_success_failure_cancel_and_recovery_states_remain_distinct(self):
        cases = (("completed", "completed"), ("failed", "failed"),
                 ("cancelled", "cancelled"), ("recovered", "verified-prefix"))
        for label, state in cases:
            with self.subTest(label=label):
                text = present.render_summary(envelope({"runtime": {"status": state},
                                                        "dispatch": "not-dispatched" if label == "cancelled" else "performed"},
                                                       operation="verify"))
                self.assertIn(f"domain status: {state}", text)
                self.assertNotIn("source promotion", text.lower())
                self.assertIn("does not establish code correctness", text)
        unfinished = present.render_summary(envelope({"runtime": {"status": "interrupted"}}, operation="recover"))
        self.assertIn("interrupted", unfinished)
        self.assertNotIn("successful", unfinished.lower())

    def test_sc005_graph_preserves_edge_semantics_and_refuses_malformed_or_oversize(self):
        good = envelope({"operations": [
            {"instanceId": "a", "dependencies": []}, {"instanceId": "b", "dependencies": ["a"]},
            {"instanceId": "c", "dependencies": []}, {"instanceId": "d", "dependencies": []}],
            "interactions": [{"left": "a", "right": "c", "classification": "conflicting"},
                             {"left": "b", "right": "c", "classification": "conditional"},
                             {"left": "c", "right": "d", "classification": "unknown"}]})
        graph = present.build_graph(good)
        rendered = present.render_graph_ascii(graph)
        self.assertIn("dependency", rendered); self.assertIn("conflicting", rendered)
        self.assertIn("conditional", rendered); self.assertIn("unknown", rendered)
        self.assertIn("independent-candidate are separate evidence labels", rendered)
        svg = present._svg_graph(graph)
        self.assertIn('class="edge conflict" stroke-dasharray="8 3"', svg)
        self.assertIn('class="edge conditional" stroke-dasharray="5 3"', svg)
        self.assertIn('class="edge unknown" stroke-dasharray="2 3"', svg)
        with self.assertRaises(present.PresentationError):
            present.build_graph(envelope({"operations": [{"instanceId": "a", "dependencies": ["missing"]}]}))
        too_many = [{"instanceId": f"n{i}", "dependencies": []} for i in range(present.MAX_NODES + 1)]
        with self.assertRaises(present.PresentationError):
            present.build_graph(envelope({"operations": too_many}))

    def test_sc006_repeated_export_bytes_and_receipt_bind_exact_source_output_and_limits(self):
        value = envelope({"analysisId": "sha256:" + "b" * 64,
                          "operations": [{"instanceId": "op-1", "dependencies": []}],
                          "interactions": [], "executionAuthorization": False})
        source, results, fixture = self.owned_fixture(value)
        decoded = json.loads(fixture.read_bytes())
        first = present.build_exports(decoded, selected_evidence_refs=["owned-evidence-1"])
        second = present.build_exports(decoded, selected_evidence_refs=["owned-evidence-1"])
        self.assertEqual(first, second)
        result_hashes = {name: hashlib.sha256(content).hexdigest() for name, content in first.items()}
        with self.assertRaises(present.PresentationError):
            present.build_exports(decoded, selected_evidence_refs=["foreign-evidence"])
        receipt = json.loads(first["receipt.json"])
        self.assertIn("completeEvidence", receipt)
        self.assertEqual(json.loads(first["evidence.json"]), decoded)
        self.assertEqual(receipt["rawEvidenceSha256"], "sha256:" + hashlib.sha256(first["evidence.json"]).hexdigest())
        self.assertEqual(receipt["outputs"], {name: "sha256:" + digest for name, digest in
                                               sorted(result_hashes.items()) if name != "receipt.json"})
        self.assertTrue(receipt["limits"])
        self.assertTrue(all(len(digest) == 64 for digest in result_hashes.values()))
        self.assertTrue(source.is_dir() and results.is_dir())
        self.assertEqual(hashlib.sha256(fixture.read_bytes()).hexdigest(), hashlib.sha256(present.canonical_json(decoded)).hexdigest())

    def test_sc007_export_escapes_active_markup_and_refuses_unsafe_selection_and_size(self):
        value = envelope({"operations": [{"instanceId": "op-1", "dependencies": []}],
                          "interactions": [],
                          "limits": ["<script>private()</script>", "[x](javascript:alert(1))",
                                     "https://remote.invalid/pixel", "/private/owned/secret.txt"]})
        source, results, fixture = self.owned_fixture(value)
        outputs = present.build_exports(json.loads(fixture.read_bytes()), selected_evidence_refs=["owned-evidence-1"])
        for name in ("index.html", "graph.svg", "summary.md"):
            rendered = outputs[name].decode("utf-8").lower()
            self.assertNotIn("<script", rendered)
            if name == "index.html":
                self.assertIn("&lt;script&gt;", rendered)
                self.assertIn("private()", rendered)  # payload is visible only as inert text inside the pre block
                self.assertIn("javascript:", rendered)  # retained as inert escaped text, never an active link
            else:
                if name == "summary.md":
                    self.assertIn("&#91;x&#93;&#40;javascript:", rendered)
                else:
                    self.assertNotIn("javascript:", rendered)
                self.assertNotIn("private()", rendered)
            self.assertNotIn("remote.invalid", rendered)
            self.assertNotIn("/private/owned", rendered)
        self.assertIn(b"completeEvidence", outputs["receipt.json"])
        with self.assertRaises(present.PresentationError):
            present.build_exports(json.loads(fixture.read_bytes()), selected_evidence_refs=None)
        oversized = envelope({"payload": "x" * (present.MAX_ENVELOPE_BYTES + 1)})
        with self.assertRaises(present.PresentationError):
            present.build_exports(oversized, selected_evidence_refs=[])
        self.assertTrue(source.is_dir() and results.is_dir())


if __name__ == "__main__":
    unittest.main()
