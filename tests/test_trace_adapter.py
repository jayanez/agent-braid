# SPDX-License-Identifier: AGPL-3.0-only
"""Finite synthetic import controls; no real traces or provider clients."""
import copy
import json
import io
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from jsonschema import Draft202012Validator

from agent_braid.analysis import analyze
from agent_braid.cli import main
from agent_braid.trace_adapter import (
    InvalidTrace, MAPPER, MAX_BYTES, VERSION, canonical_bytes,
    digest_bytes, import_trace, read_trace, validate_destination,
)

ROOT = Path(__file__).resolve().parents[1]
FEATURE = ROOT / "specs/023-recorded-trace-adapters"


def request():
    return json.loads((FEATURE / "fixtures/generic.json").read_text())


def encode(value):
    value = copy.deepcopy(value)
    value["source"]["contentDigest"] = digest_bytes(canonical_bytes(
        {"operations": value["operations"], "events": value["events"]}))
    return canonical_bytes(value)


class TraceAdapterTests(unittest.TestCase):
    def import_value(self, value):
        return import_trace(encode(value), mapper=MAPPER)

    def test_schema_baseline_identity_and_digest_parity(self):
        value = request()
        result = self.import_value(value)
        expected = json.loads((FEATURE / "fixtures/direct-aim.json").read_text())
        self.assertEqual(result.projection, expected)
        self.assertEqual(result.report, analyze(expected))
        self.assertEqual(result.report["summary"]["classifications"], {
            "independent-candidate": 1, "ordered": 0, "conflicting": 0, "unknown": 0})
        self.assertFalse(result.report["executionAuthorization"])
        self.assertFalse(result.provenance["executionAuthorization"])
        self.assertEqual(result.provenance["sourceFileDigest"], digest_bytes(encode(value)))
        self.assertEqual(result.provenance["projectionDigest"], digest_bytes(result.projection_bytes))
        self.assertEqual(result.provenance["reportDigest"], digest_bytes(result.report_bytes))
        for operation in result.projection:
            schema = json.loads((ROOT / "schemas/0.2.0-draft/agent-interaction-metadata.schema.json").read_text())
            Draft202012Validator(schema).validate(operation)
        schema = json.loads((ROOT / "schemas/0.1.0-alpha/analysis-report.schema.json").read_text())
        Draft202012Validator(schema).validate(result.report)
        contracts = FEATURE / "contracts/0.1.0-experimental"
        for filename, artifact in (("trace-import.schema.json", json.loads(encode(value))),
                                   ("trace-provenance.schema.json", result.provenance)):
            schema = json.loads((contracts / filename).read_text())
            Draft202012Validator.check_schema(schema)
            Draft202012Validator(schema).validate(artifact)

    def test_determinism_and_no_mutation(self):
        value = request()
        before = copy.deepcopy(value)
        first, second = self.import_value(value), self.import_value(value)
        self.assertEqual(first.report_bytes, second.report_bytes)
        self.assertEqual(first.provenance_bytes, second.provenance_bytes)
        self.assertEqual(first.projection_bytes, second.projection_bytes)
        self.assertEqual(value, before)

    def test_missing_optional_knowledge_never_becomes_independence(self):
        for field in ("effects", "readVersions", "dependencies"):
            with self.subTest(field=field):
                value = request()
                del value["operations"][0][field]
                result = self.import_value(value)
                self.assertEqual(result.report["interactions"][0]["classification"], "unknown")
                self.assertTrue(result.provenance["mappings"][0]["losses"])
        for field in ("coverage", "declared", "inferred", "observed"):
            with self.subTest(effect_field=field):
                value = request()
                del value["operations"][0]["effects"][field]
                self.assertEqual(self.import_value(value).report["interactions"][0]["classification"], "unknown")

    def test_empty_effects_are_unknown_and_explicit_null_is_invalid(self):
        value = request()
        value["operations"][0]["effects"]["declared"] = []
        result = self.import_value(value)
        self.assertEqual(result.report["interactions"][0]["classification"], "unknown")
        self.assertIn("no-known-effect", result.provenance["mappings"][0]["losses"])
        for location in ("effects", "coverage"):
            value = request()
            if location == "effects":
                value["operations"][0]["effects"] = None
            else:
                value["operations"][0]["effects"]["coverage"] = None
            with self.assertRaises(InvalidTrace):
                self.import_value(value)

    def test_missing_read_version_unknown_and_explicit_read_version_retained(self):
        value = request()
        value["operations"][0]["effects"]["declared"] = [{"kind": "read", "resource": "file:a"}]
        result = self.import_value(value)
        self.assertEqual(result.report["interactions"][0]["classification"], "unknown")
        value["operations"][0]["readVersions"] = {"file:a": 0}
        result = self.import_value(value)
        self.assertEqual(result.projection[0]["readVersions"], {"file:a": 0})
        self.assertIn("validate-read-versions-at-use", result.report["interactions"][0]["constraints"])

    def test_conflict_and_dependency_match_direct_baseline(self):
        value = request()
        value["operations"][1]["effects"]["declared"][0]["resource"] = "file:a"
        result = self.import_value(value)
        self.assertEqual(result.report["interactions"][0]["classification"], "conflicting")
        self.assertEqual(result.report, analyze(result.projection))
        value["operations"][1]["dependencies"] = ["left"]
        result = self.import_value(value)
        self.assertEqual(result.report["interactions"][0]["classification"], "ordered")
        self.assertEqual(result.report, analyze(result.projection))

    def test_lifecycle_never_creates_effects_or_dependencies(self):
        for status in ("approved", "rejected", "paused", "resumed", "deferred", "unknown", "started"):
            with self.subTest(status=status):
                value = request()
                value["events"] = [{"eventId": "evt", "instanceId": "left", "attemptId": "left-1",
                                    "status": status, "timestamp": "2026-10-06T10:00:00Z"}]
                result = self.import_value(value)
                self.assertEqual(result.report["interactions"][0]["classification"], "unknown")
                self.assertEqual(result.projection[0]["dependencies"], [])
                self.assertEqual(result.provenance["events"], value["events"])
        value = request()
        value["operations"][0]["effects"]["declared"] = []
        value["events"] = [{"eventId": "evt", "instanceId": "left", "attemptId": "left-1", "status": "completed"}]
        self.assertEqual(self.import_value(value).report["interactions"][0]["classification"], "unknown")

    def test_required_identity_digests_and_duplicate_instances_reject(self):
        for field in ("instanceId", "attemptId", "definition", "inputDigest"):
            with self.subTest(field=field):
                value = request()
                del value["operations"][0][field]
                with self.assertRaises(InvalidTrace):
                    self.import_value(value)
        value = request()
        value["operations"].append({**value["operations"][0], "attemptId": "left-2"})
        with self.assertRaisesRegex(InvalidTrace, "duplicate-instance-or-attempt"):
            self.import_value(value)
        value = request()
        value["operations"][1]["attemptId"] = "left-1"
        with self.assertRaises(InvalidTrace):
            self.import_value(value)
        for field in ("inputDigest",):
            value = request()
            value["operations"][0][field] = "not-a-digest"
            with self.assertRaisesRegex(InvalidTrace, "invalid-source-digest"):
                self.import_value(value)

    def test_cycles_dangling_dependencies_and_definition_rebinding_reject(self):
        for dependencies in (["missing"], ["left"], ["right", "right"]):
            value = request()
            value["operations"][0]["dependencies"] = dependencies
            with self.assertRaisesRegex(InvalidTrace, "invalid-aim-projection"):
                self.import_value(value)
        value = request()
        value["operations"][0]["dependencies"] = ["right"]
        value["operations"][1]["dependencies"] = ["left"]
        with self.assertRaises(InvalidTrace):
            self.import_value(value)
        value = request()
        value["operations"][1]["definition"]["id"] = value["operations"][0]["definition"]["id"]
        with self.assertRaisesRegex(InvalidTrace, "inconsistent-definition-digest"):
            self.import_value(value)

    def test_source_version_mapper_and_content_hash_mismatch_reject(self):
        value = request()
        for where, field in ((value, "traceImportVersion"), (value["source"], "schemaVersion")):
            old = where[field]
            where[field] = "9.9.9"
            with self.assertRaises(InvalidTrace):
                self.import_value(value)
            where[field] = old
        with self.assertRaisesRegex(InvalidTrace, "unsupported-mapper"):
            import_trace(encode(value), mapper="plugin")
        value["source"]["contentDigest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(InvalidTrace, "source-content-digest-mismatch"):
            import_trace(canonical_bytes(value), mapper=MAPPER)

    def test_forbidden_payload_and_real_source_fail_without_disclosure_or_dispatch(self):
        sentinel = "SYNTHETIC_PRIVATE_SENTINEL"
        with patch("subprocess.run") as run, patch("subprocess.Popen") as popen, \
                patch("socket.socket") as socket, patch("urllib.request.urlopen") as network:
            self.import_value(request())
            for field in ("prompt", "arguments", "credential", "person", "command", "url",
                          "plugin", "modelRequest", "grant", "execute"):
                for location in ("root", "operation", "event"):
                    with self.subTest(field=field, location=location):
                        value = request()
                        target = value if location == "root" else value["operations"][0]
                        if location == "event":
                            value["events"] = [{"eventId": "evt", "instanceId": "left", "attemptId": "left-1", "status": "completed"}]
                            target = value["events"][0]
                        target[field] = sentinel
                        with self.assertRaises(InvalidTrace) as context:
                            self.import_value(value)
                        self.assertNotIn(sentinel, str(context.exception))
                        self.assertNotIn(field, str(context.exception))
            for kind in ("real", "sanitized-real"):
                value = request()
                value["admission"] = {"kind": kind}
                with self.assertRaisesRegex(InvalidTrace, "source-not-admitted"):
                    self.import_value(value)
            run.assert_not_called()
            popen.assert_not_called()
            socket.assert_not_called()
            network.assert_not_called()

    def test_duplicate_json_unicode_nonfinite_and_deep_bounds(self):
        for data in (b'{"traceImportVersion":1,"traceImportVersion":2}', b'\xff', b'{',
                     b'{"v":NaN}', b'[' * 20 + b'0' + b']' * 20):
            with self.subTest(data=data[:30]), self.assertRaises(InvalidTrace):
                import_trace(data, mapper=MAPPER)
        with self.assertRaisesRegex(InvalidTrace, "input-byte-limit"):
            import_trace(b' ' * (MAX_BYTES + 1), mapper=MAPPER)
        value = request()
        value["operations"][0]["instanceId"] = "x" * 257
        with self.assertRaisesRegex(InvalidTrace, "metadata-string-limit"):
            self.import_value(value)

    def test_operation_and_event_count_limits_before_analysis(self):
        value = request()
        value["operations"] = value["operations"] * 33
        with patch("agent_braid.trace_adapter.analyze") as analyzer:
            with self.assertRaisesRegex(InvalidTrace, "operation-limit"):
                self.import_value(value)
            value = request()
            value["events"] = [{}] * 513
            with self.assertRaisesRegex(InvalidTrace, "event-limit"):
                self.import_value(value)
            analyzer.assert_not_called()

    def test_exact_maximum_admission_and_oversized_metadata_reject(self):
        value = request()
        template = value["operations"][0]
        value["operations"] = [
            {**copy.deepcopy(template), "instanceId": f"op-{i}", "attemptId": f"attempt-{i}"}
            for i in range(64)
        ]
        value["operations"][0]["effects"]["declared"][0]["resource"] = "r" * 256
        value["events"] = [
            {"eventId": f"event-{i}", "instanceId": "op-0", "attemptId": "attempt-0", "status": "completed"}
            for i in range(512)
        ]
        data = encode(value).ljust(MAX_BYTES, b" ")
        result = import_trace(data, mapper=MAPPER)
        self.assertEqual(result.report["summary"]["operationCount"], 64)
        self.assertEqual(result.report["summary"]["pairCount"], 2016)
        self.assertEqual(len(result.provenance["events"]), 512)
        self.assertEqual(result.provenance["sourceFileDigest"], digest_bytes(data))
        value["operations"][0]["effects"]["declared"][0]["resource"] += "r"
        with self.assertRaisesRegex(InvalidTrace, "metadata-string-limit"):
            self.import_value(value)

    def test_event_duplicates_wrong_attempt_and_invalid_versions_reject(self):
        event = {"eventId": "evt", "instanceId": "left", "attemptId": "left-1", "status": "completed"}
        for events in ([event, event], [{**event, "attemptId": "left-2"}],
                       [{**event, "instanceId": "missing"}], [{**event, "status": []}]):
            value = request()
            value["events"] = events
            with self.assertRaises(InvalidTrace):
                self.import_value(value)
        for version in (-1, True, "stale", None):
            value = request()
            value["operations"][0]["readVersions"] = {"file:a": version}
            with self.assertRaisesRegex(InvalidTrace, "invalid-read-version"):
                self.import_value(value)

    def test_local_source_and_destination_controls_preserve_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, destination = root / "source.json", root / "provenance.json"
            data = encode(request())
            source.write_bytes(data)
            self.assertEqual(read_trace(source), data)
            self.assertEqual(validate_destination(source, destination), destination)
            self.assertFalse(destination.exists())
            for bad in (source, root / "missing" / "p.json", "https://example.invalid/p"):
                with self.assertRaises(InvalidTrace):
                    validate_destination(source, bad)
            destination.write_text("preserve")
            with self.assertRaisesRegex(InvalidTrace, "output-already-exists"):
                validate_destination(source, destination)
            symlink = root / "link"
            symlink.symlink_to(source)
            with self.assertRaisesRegex(InvalidTrace, "symlink-path-refused"):
                read_trace(symlink)
            ancestor = root / "alias"
            ancestor.symlink_to(root, target_is_directory=True)
            with self.assertRaisesRegex(InvalidTrace, "symlink-path-refused"):
                validate_destination(source, ancestor / "new.json")
            fifo = root / "fifo"
            os.mkfifo(fifo)
            with self.assertRaisesRegex(InvalidTrace, "source-not-regular-file"):
                read_trace(fifo)
            with self.assertRaises(InvalidTrace):
                read_trace(root)
            source.write_bytes(b' ' * (MAX_BYTES + 1))
            with self.assertRaisesRegex(InvalidTrace, "input-byte-limit"):
                read_trace(source)
            self.assertEqual(destination.read_text(), "preserve")


class TraceAdapterCliTests(unittest.TestCase):
    def test_cli_json_digest_permissions_and_zero_dispatch(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, output = root / "source.json", root / "provenance.json"
            data = encode(request())
            source.write_bytes(data)
            stdout = io.StringIO()
            with patch("sys.stdout", stdout), patch("subprocess.run") as run, \
                    patch("subprocess.Popen") as popen, patch("socket.socket") as socket, \
                    patch("urllib.request.urlopen") as network:
                status = main(["analyze-trace", str(source), "--mapper", MAPPER,
                               "--provenance-output", str(output)])
            self.assertEqual(status, 0)
            report_bytes = stdout.getvalue().encode()
            report, provenance = json.loads(report_bytes), json.loads(output.read_bytes())
            self.assertEqual(provenance["reportDigest"], digest_bytes(report_bytes))
            self.assertEqual(provenance["sourceFileDigest"], digest_bytes(data))
            self.assertFalse(report["executionAuthorization"])
            self.assertFalse(provenance["executionAuthorization"])
            self.assertEqual(output.stat().st_mode & 0o777, 0o600)
            self.assertEqual(source.read_bytes(), data)
            run.assert_not_called()
            popen.assert_not_called()
            socket.assert_not_called()
            network.assert_not_called()

    def test_cli_rejects_without_partial_output_or_payload_disclosure(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, output = root / "source.json", root / "provenance.json"
            value = request()
            value["operations"][0]["prompt"] = "SYNTHETIC_PRIVATE_SENTINEL"
            source.write_bytes(encode(value))
            stdout = io.StringIO()
            with patch("sys.stdout", stdout), patch("subprocess.Popen") as popen, \
                    patch("socket.socket") as socket:
                status = main(["analyze-trace", str(source), "--mapper", MAPPER,
                               "--provenance-output", str(output)])
            self.assertEqual(status, 2)
            self.assertEqual(json.loads(stdout.getvalue())["status"], "rejected")
            self.assertNotIn("SYNTHETIC_PRIVATE_SENTINEL", stdout.getvalue())
            self.assertFalse(output.exists())
            popen.assert_not_called()
            socket.assert_not_called()
            output.write_bytes(b"preserve")
            with patch("sys.stdout", io.StringIO()):
                self.assertEqual(main(["analyze-trace", str(source), "--mapper", MAPPER,
                                       "--provenance-output", str(output)]), 2)
            self.assertEqual(output.read_bytes(), b"preserve")

    def test_cli_text_format_and_failed_write_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source, output = root / "source.json", root / "provenance.json"
            source.write_bytes(encode(request()))
            stdout = io.StringIO()
            with patch("sys.stdout", stdout):
                status = main(["analyze-trace", str(source), "--mapper", MAPPER,
                               "--provenance-output", str(output), "--format", "text"])
            self.assertEqual(status, 0)
            self.assertIn("left / right: independent-candidate", stdout.getvalue())
            self.assertIn("Execution authorization: false", stdout.getvalue())
            output.unlink()
            stdout = io.StringIO()
            with patch("sys.stdout", stdout), patch("agent_braid.cli.os.fsync", side_effect=OSError("synthetic-disk-full")):
                status = main(["analyze-trace", str(source), "--mapper", MAPPER,
                               "--provenance-output", str(output)])
            self.assertEqual(status, 2)
            self.assertFalse(output.exists())
            self.assertEqual(json.loads(stdout.getvalue())["status"], "rejected")
            self.assertNotIn("analysisId", stdout.getvalue())
