# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic source-feasibility capture and adversarial integrity tests."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.instrument_m35_flow import audit_capture, capture_synthetic


FIXTURE = Path(__file__).resolve().parents[1] / "examples/m35/m35-synthetic-sessions.json"
FROZEN_CAPTURE = FIXTURE.with_name("m35-synthetic-capture.jsonl")
FROZEN_REPORT = FIXTURE.with_name("m35-synthetic-report.json")


def _canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _read_lines(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines()]


def _write_lines(path: Path, lines: list[dict]) -> None:
    path.write_text("".join(json.dumps(line, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
                            for line in lines), encoding="utf-8")


def _reseal_events(lines: list[dict]) -> None:
    """Recompute the documented per-event hash chain after intentional edits."""
    previous_hash = None
    for record in lines[1:]:
        record["previousHash"] = previous_hash
        record.pop("eventHash", None)
        event_hash = sha256(_canonical(record)).hexdigest()
        record["eventHash"] = event_hash
        previous_hash = event_hash


class M35SourceCaptureTests(unittest.TestCase):
    def _capture(self, directory: str) -> tuple[Path, dict]:
        capture = Path(directory) / "capture.jsonl"
        capture_synthetic(FIXTURE, capture)
        return capture, audit_capture(capture)

    def _assert_integrity_rejected(self, lines: list[dict], case: str) -> None:
        with TemporaryDirectory() as directory:
            capture = Path(directory) / f"{case}.jsonl"
            _write_lines(capture, lines)
            with self.assertRaises(ValueError, msg=case):
                audit_capture(capture)

    def test_fixture_counts_and_reproduction(self) -> None:
        with TemporaryDirectory() as directory:
            first = Path(directory) / "first.jsonl"
            second = Path(directory) / "second.jsonl"
            capture_synthetic(FIXTURE, first)
            capture_synthetic(FIXTURE, second)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(first.read_bytes(), FROZEN_CAPTURE.read_bytes())
            report = audit_capture(first)
            self.assertEqual(report, json.loads(FROZEN_REPORT.read_text(encoding="utf-8")))
            self.assertEqual(report["sessionsExamined"], 6)
            self.assertEqual(report["sessionsAdmitted"], 1)
            self.assertEqual(report["pairsExamined"], 6)
            self.assertEqual(report["pairsAdmitted"], 1)
            self.assertEqual(report["realPairsAdmitted"], 0)
            self.assertFalse(report["executionAuthorization"])
            self.assertEqual(report["pairsExcludedByReason"], {
                "invalid-anchor": 1, "invalid-base": 1,
                "base-mismatch": 1, "missing-provenance": 1, "unsupported-operation": 1,
            })
            with self.assertRaises(FileExistsError):
                capture_synthetic(FIXTURE, first)

    def test_deleted_event_fails_closed_instead_of_admitting_partial_pairs(self) -> None:
        with TemporaryDirectory() as directory:
            capture, _ = self._capture(directory)
            lines = _read_lines(capture)
        self._assert_integrity_rejected([lines[0], *lines[2:]], "deleted-event")

    def test_added_event_fails_closed_against_frozen_manifest_count(self) -> None:
        with TemporaryDirectory() as directory:
            capture, _ = self._capture(directory)
            lines = _read_lines(capture)
        extra = dict(lines[-1])
        extra["eventId"] = "extra-event"
        extra["sourceSequence"] = lines[-1]["sourceSequence"] + 1
        lines.append(extra)
        _reseal_events(lines)
        self._assert_integrity_rejected(lines, "added-event")

    def test_event_payload_change_without_new_hash_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            capture, _ = self._capture(directory)
            lines = _read_lines(capture)
        lines[1]["sourceRef"] = "synthetic://tampered"
        self._assert_integrity_rejected(lines, "changed-payload")

    def test_reordered_event_lines_fail_closed(self) -> None:
        with TemporaryDirectory() as directory:
            capture, _ = self._capture(directory)
            lines = _read_lines(capture)
        lines[1], lines[2] = lines[2], lines[1]
        self._assert_integrity_rejected(lines, "reordered-events")

    def test_sequence_gap_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            capture, _ = self._capture(directory)
            lines = _read_lines(capture)
        lines[2]["sourceSequence"] += 1
        _reseal_events(lines)
        self._assert_integrity_rejected(lines, "sequence-gap")

    def test_duplicate_event_id_across_sessions_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            capture, _ = self._capture(directory)
            lines = _read_lines(capture)
        # Reuse a globally unique ID from another session and make the edited
        # feed internally hash-consistent so this reaches the identity check.
        lines[4]["eventId"] = lines[1]["eventId"]
        _reseal_events(lines)
        self._assert_integrity_rejected(lines, "duplicate-global-event-id")

    def test_capture_requires_explicit_base_reference_for_each_operation(self) -> None:
        envelope = json.loads(FIXTURE.read_text(encoding="utf-8"))
        del envelope["sessions"][0]["events"][0]["baseEventId"]
        with TemporaryDirectory() as directory:
            source = Path(directory) / "window.json"
            output = Path(directory) / "capture.jsonl"
            source.write_text(json.dumps(envelope), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "operation event envelope is incomplete"):
                capture_synthetic(source, output)
            self.assertFalse(output.exists())

    def test_duplicate_session_id_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            capture, _ = self._capture(directory)
            lines = _read_lines(capture)
        # A second base event under an already-used session identity must be
        # rejected as a malformed duplicate session boundary.
        lines[4]["sessionId"] = lines[1]["sessionId"]
        _reseal_events(lines)
        self._assert_integrity_rejected(lines, "duplicate-session-id")

    def test_family_mismatch_within_session_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            capture, _ = self._capture(directory)
            lines = _read_lines(capture)
        lines[2]["familyId"] = "different-family"
        _reseal_events(lines)
        self._assert_integrity_rejected(lines, "family-mismatch")

    def test_operation_with_mismatched_base_is_excluded_not_admitted(self) -> None:
        with TemporaryDirectory() as directory:
            capture, _ = self._capture(directory)
            lines = _read_lines(capture)
        lines[2]["baseEventId"] = "other-base-event"
        _reseal_events(lines)
        with TemporaryDirectory() as directory:
            tampered = Path(directory) / "base-mismatch.jsonl"
            _write_lines(tampered, lines)
            report = audit_capture(tampered)
        self.assertEqual(report["pairsExamined"], 6)
        self.assertEqual(report["pairsAdmitted"], 0)
        self.assertEqual(report["sessionsAdmitted"], 0)
        self.assertEqual(report["pairsExcludedByReason"].get("base-mismatch"), 2)

    def test_base_event_must_precede_both_operations(self) -> None:
        with TemporaryDirectory() as directory:
            capture, _ = self._capture(directory)
            lines = _read_lines(capture)
        # Keep the declared global sequence contiguous but move the base after
        # its first operation in the source event order.
        lines[1]["sourceSequence"], lines[2]["sourceSequence"] = (
            lines[2]["sourceSequence"], lines[1]["sourceSequence"])
        _reseal_events(lines)
        self._assert_integrity_rejected(lines, "base-after-operation")

    def test_previous_hash_tampering_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            capture, _ = self._capture(directory)
            lines = _read_lines(capture)
        lines[2]["previousHash"] = "f" * 64
        self._assert_integrity_rejected(lines, "previous-hash")


if __name__ == "__main__":
    unittest.main()
