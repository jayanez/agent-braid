# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
import threading
import unittest

from agent_braid import tooling_present as present
from agent_braid.tooling_mcp import ToolingConfig, ToolingService


def envelope(result: dict, *, operation: str = "analyze-work", status: str = "ok") -> dict:
    return {
        "schemaVersion": "agent-braid-tooling/v0.1",
        "operation": operation,
        "status": status,
        "summary": "adapter text is deliberately not trusted as the core result",
        "result": result,
        "evidenceRefs": ["artifact-1"],
        "limits": ["No code correctness or execution claim."],
        "provenance": {"candidate": "candidate-test"},
    }


class SummaryTests(unittest.TestCase):
    def test_adapter_ok_does_not_hide_unknown_domain_or_authorize_execution(self):
        report = envelope({
            "analysisId": "sha256:" + "a" * 64,
            "interactions": [
                {"left": "one", "right": "two", "classification": "unknown"},
                {"left": "one", "right": "three", "classification": "conflicting"},
            ],
            "executionAuthorization": False,
            "limits": ["Observation only; does not establish correctness."],
        })

        text = present.render_summary(report)

        self.assertIn("Adapter status: ok (not a domain-success verdict)", text)
        self.assertIn("Interaction classifications: conflicting=1, unknown=1", text)
        self.assertIn("Execution authorization: false", text)
        self.assertIn("does not establish code correctness or a theorem", text)
        self.assertNotIn("independent=", text)

    def test_refusal_cancel_and_verifier_states_remain_distinct(self):
        cases = [
            ("refused", {"dispatch": "not-dispatched", "status": "refused"}, "not-dispatched"),
            ("unknown", {"status": "cancelled", "recovery": "inspect"}, "cancelled"),
            ("ok", {"verificationStatus": "verified"}, "verified"),
        ]
        for adapter_status, result, domain in cases:
            with self.subTest(adapter_status=adapter_status, domain=domain):
                text = present.render_summary(envelope(result, status=adapter_status))
                self.assertIn(f"Adapter status: {adapter_status}", text)
                self.assertIn(domain, text)
        verified = present.render_summary(envelope({"verificationStatus": "verified"}))
        self.assertIn("does not establish code correctness", verified)

    def test_real_analyze_work_envelope_renders_nested_report_and_full_provenance(self):
        sample_path = Path(__file__).resolve().parents[1] / "examples/analysis/file-edits.json"
        request = json.loads(sample_path.read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source, results = base / "source", base / "results"
            source.mkdir()
            results.mkdir()
            service = ToolingService(ToolingConfig(source, results))
            result = service.invoke("analyze-work", {"kind": "aim", "request": request}, threading.Event())

        summary = present.render_summary(result)
        graph = present.build_graph(result)
        encoded_result = json.loads(present.canonical_result_json(result))
        self.assertEqual(result["status"], "ok")
        self.assertIn("Interaction classifications:", summary)
        self.assertIn("independent-candidate=", summary)
        self.assertIn("candidateVersion=", summary)
        self.assertIn("runtimePolicyVersion=", summary)
        self.assertIn("schemaVersion=", summary)
        self.assertIn("inputDigest=", summary)
        self.assertIn("sourceIdentity=", summary)
        self.assertIn("observationContract=", summary)
        self.assertIn("Core report limits:", summary)
        self.assertTrue(graph["nodes"])
        self.assertEqual(encoded_result, result["result"])
        self.assertIn("report", encoded_result)
        self.assertIn("provenance", encoded_result)

    def test_real_refusal_renders_reason_without_fabricating_core_result(self):
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            source, results = base / "source", base / "results"
            source.mkdir()
            results.mkdir()
            service = ToolingService(ToolingConfig(source, results))
            result = service.invoke("analyze-work", {"kind": "unknown", "request": {}}, threading.Event())

        summary = present.render_summary(result)
        self.assertEqual(result["status"], "refused")
        self.assertIn("Core result: unavailable", summary)
        self.assertIn("Adapter detail:", summary)
        self.assertIn("Adapter status: refused", summary)
        for function in (present.canonical_result_json, present.build_graph):
            with self.subTest(function=function.__name__), self.assertRaises(present.PresentationError):
                function(result)

    def test_sensitive_paths_and_terminal_controls_are_not_rendered(self):
        hostile = "repo\x1b[31m\n/private/tmp/private-checkout/README.md token=topsecret src/private/key.txt"
        text = present.render_summary(envelope({
            "executionAuthorization": False,
            "limits": [hostile],
        }, operation=hostile))

        self.assertNotIn("\x1b", text)
        self.assertNotIn("\n/private/tmp", text)
        self.assertNotIn("private-checkout", text)
        self.assertNotIn("topsecret", text)
        self.assertNotIn("src/private/key.txt", text)
        self.assertIn("\\x1b[31m\\x0a", text)
        self.assertIn("<local-path>", text)

    def test_advisory_order_is_not_execution_authority(self):
        text = present.render_summary(envelope({
            "orderedReadyIds": ["first", "second"],
            "executionAuthorization": False,
        }))
        self.assertIn("Advisory order: first -> second", text)
        self.assertIn("does not issue authority or dispatch work", text)

    def test_execute_refusal_explains_operator_grant_without_claiming_host_approval(self):
        text = present.render_summary(envelope(
            {"status": "refused", "reasonCode": "missing-grant", "executionAuthorization": False},
            operation="execute",
            status="refused",
        ))
        self.assertIn("reasonCode: missing-grant", text)
        self.assertIn("exact existing operator grant is required", text)
        self.assertIn("this interface never issues one", text)

    def test_true_authorization_is_scoped_to_recorded_operation(self):
        text = present.render_summary(envelope({"executionAuthorization": True}))
        self.assertIn("Core reports execution authorization: true for this recorded operation only", text)


class GraphTests(unittest.TestCase):
    def test_graph_preserves_dependency_conflict_conditional_and_unknown_labels(self):
        report = envelope({
            "operations": [
                {"instanceId": "a", "dependencies": []},
                {"instanceId": "b", "dependencies": ["a"]},
                {"instanceId": "c", "dependencies": []},
                {"instanceId": "d", "dependencies": []},
                {"instanceId": "e", "dependencies": []},
            ],
            "interactions": [
                {"left": "a", "right": "c", "classification": "conflicting"},
                {"left": "b", "right": "d", "classification": "conditional"},
                {"left": "c", "right": "e", "classification": "unknown"},
            ],
        })

        graph = present.build_graph(report)
        text = present.render_graph_ascii(graph)
        kinds = [edge["kind"] for edge in graph["edges"]]
        self.assertCountEqual(kinds, ["dependency", "conflicting", "conditional", "unknown"])
        self.assertIn("a --[dependency]--> b", text)
        self.assertIn("a --[conflicting]--> c", text)
        self.assertIn("b --[conditional]--> d", text)
        self.assertIn("c --[unknown]--> e", text)
        self.assertNotIn("independent-candidate", kinds)

    def test_graph_rejects_malformed_and_oversized_inputs(self):
        with self.assertRaises(present.PresentationError):
            present.build_graph(envelope({"operations": [{"instanceId": "a", "dependencies": ["missing"]}]}))
        many = [{"instanceId": str(index), "dependencies": []} for index in range(present.MAX_NODES + 1)]
        with self.assertRaises(present.PresentationError):
            present.build_graph(envelope({"operations": many}))

    def test_ascii_graph_escapes_terminal_controls_and_unicode(self):
        graph = {"nodes": [{"id": "a\x1b[2Jé"}], "edges": [], "legend": []}
        text = present.render_graph_ascii(graph)
        self.assertNotIn("\x1b", text)
        self.assertNotIn("é", text)
        self.assertIn("a%5Cx1b%5B2J%5Cxe9", text)
        self.assertIn("no independence is inferred", text)

    def test_identifier_cannot_impersonate_an_independence_edge(self):
        graph = {"nodes": [{"id": "x --[independent-candidate]--> y"}], "edges": [], "legend": []}
        text = present.render_graph_ascii(graph)
        self.assertIn("x%20--%5Bindependent-candidate%5D--%3E%20y", text)
        self.assertNotIn("x --[independent-candidate]--> y", text)


class ExportTests(unittest.TestCase):
    def sample(self) -> dict:
        value = envelope({
            "analysisId": "sha256:" + "b" * 64,
            "operations": [{"instanceId": "op-1", "dependencies": []}],
            "interactions": [],
            "executionAuthorization": False,
            "privatePath": "/Users/example/private/repo",
            "payload": "<script>steal()</script>",
            "api_token": "never-render-this",
            "limits": ["[open](javascript:alert(1)) `</code><script>bad()</script>"],
        })
        value["provenance"] = {
            "schemaVersion": "agent-braid-tooling/v0.1",
            "runtimeVersion": "0.1.0-alpha",
            "candidate": "c" * 40,
            "sourceIdentity": "/private/tmp/private-repository",
        }
        return value

    def test_exports_are_deterministic_safe_and_keep_complete_evidence_separate(self):
        source = self.sample()
        first = present.build_exports(source, selected_evidence_refs=["artifact-1"])
        second = present.build_exports(source, selected_evidence_refs=["artifact-1"])
        self.assertEqual(first, second)
        self.assertEqual(json.loads(first["evidence.json"]), source)
        html_text = first["index.html"].decode("utf-8")
        svg_text = first["graph.svg"].decode("utf-8")
        markdown = first["summary.md"].decode("utf-8")
        self.assertNotIn("<script", html_text.lower())
        self.assertNotIn("steal()", html_text)
        self.assertNotIn("steal()", svg_text)
        self.assertNotIn("steal()", markdown)
        self.assertNotIn("](javascript:", markdown)
        self.assertNotIn("<script", markdown.lower())
        self.assertNotIn("/Users/example", html_text + svg_text + markdown)
        self.assertNotIn("private-repository", html_text + svg_text + markdown)
        self.assertNotIn("never-render-this", html_text + svg_text + markdown)
        self.assertIn("Complete evidence is in", html_text)
        self.assertIn("candidate=" + "c" * 40, html_text)
        self.assertIn("artifact-1", markdown)
        self.assertIn("completeEvidence", first["receipt.json"].decode("ascii"))
        self.assertNotIn("<script", svg_text.lower())
        self.assertNotIn("foreignObject", svg_text)

    def test_export_requires_explicit_selection_and_refuses_unowned_references(self):
        with self.assertRaises(present.PresentationError):
            present.build_exports(self.sample(), selected_evidence_refs=None)
        with self.assertRaises(present.PresentationError):
            present.build_exports(self.sample(), selected_evidence_refs=["not-owned"])

    def test_export_requires_private_new_directory_and_preserves_existing_collision(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            parent.chmod(0o700)
            destination = parent / "bundle"
            result = present.write_exports(self.sample(), destination, selected_evidence_refs=[])
            self.assertTrue(result["completeEvidence"])
            self.assertEqual((destination.stat().st_mode & 0o777), 0o700)
            self.assertEqual((destination / "evidence.json").stat().st_mode & 0o777, 0o600)
            before = (destination / "evidence.json").read_bytes()
            with self.assertRaises(present.PresentationError):
                present.write_exports(self.sample(), destination, selected_evidence_refs=[])
            self.assertEqual((destination / "evidence.json").read_bytes(), before)

    def test_export_rejects_shared_parent_permissions(self):
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            parent.chmod(0o755)
            with self.assertRaises(present.PresentationError):
                present.write_exports(self.sample(), parent / "bundle", selected_evidence_refs=[])

    def test_complete_result_json_matches_for_raw_and_enveloped_values(self):
        core = {"status": "unknown", "nested": [1, {"x": "y"}]}
        self.assertEqual(present.canonical_result_json(core), present.canonical_result_json(envelope(core)))
        self.assertNotEqual(
            present.canonical_result_json(envelope(core)),
            present.canonical_result_json(envelope({**core, "nested": [1, {"x": "z"}]})),
        )

    def test_artifact_reference_is_not_mistaken_for_complete_result(self):
        reference = {"type": "evidence-artifact-reference", "artifactId": "ev-x",
                     "uri": "agent-braid://runs/x", "sha256": "a" * 64, "sizeBytes": 3}
        for function in (present.canonical_result_json, present.render_summary, present.build_graph):
            with self.subTest(function=function.__name__), self.assertRaises(present.PresentationError):
                function(envelope(reference))


if __name__ == "__main__":
    unittest.main()
