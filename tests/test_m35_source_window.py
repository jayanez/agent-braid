# SPDX-License-Identifier: AGPL-3.0-only
"""Prospective adapter boundary and integrity checks using invented sessions."""

from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

import agent_braid.m35_source_window as source_window

from agent_braid.m35_source_window import (
    audit_window, close_session, create_window, final_seal_payload,
    mark_external_observation, open_session, propose, reveal, seal_payload, view_base,
)
from scripts.m35_seal_validate import validate_payload


START = datetime(2026, 9, 20, tzinfo=timezone.utc)
NOW = START + timedelta(days=1)
SHA = "a" * 40


def manifest(kind: str = "synthetic") -> dict:
    return {"format": "m35-source-window-v1", "sourceKind": kind, "windowId": "pilot-k",
            "familyId": "kinetiq-decisions", "startUtc": "2026-09-20T00:00:00Z",
            "endUtc": "2026-10-04T00:00:00Z", "registrationRunId": 123 if kind == "prospective" else None,
            "protocolCommit": SHA}


def operation(index: int, *, anchor: str = "$root", kind: str = "insert") -> dict:
    return {"id": f"op-{index}", "kind": kind, "anchorId": anchor,
            "newId": f"new-{index}", "value": f"Option {index}"}


class M35SourceWindowTests(unittest.TestCase):
    def _new(self, root: str) -> Path:
        directory = Path(root) / "capture"
        create_window(directory, manifest())
        return directory

    def _open(self, directory: Path, session: str = "s1", *, base: list | None = None,
              participants: list[str] | None = None) -> None:
        open_session(directory, session, participants or ["actor-a", "actor-b"],
                     [] if base is None else base, SHA, "lab://decision", now=NOW)

    def test_independent_proposals_are_counted_and_hidden_until_barrier(self) -> None:
        with TemporaryDirectory() as root:
            directory = self._new(root)
            self._open(directory)
            first = view_base(directory, "s1", "actor-a", now=NOW)
            second = view_base(directory, "s1", "actor-b", now=NOW)
            self.assertEqual(first["baseEventId"], second["baseEventId"])
            propose(directory, "s1", "actor-a", operation(1), "lab://proposal-a", now=NOW)
            with self.assertRaises(ValueError):
                reveal(directory, "s1", "actor-b", now=NOW)
            propose(directory, "s1", "actor-b", operation(2), "lab://proposal-b", now=NOW)
            self.assertEqual(len(reveal(directory, "s1", "actor-a", now=NOW)), 2)
            close_session(directory, "s1", "accepted", now=NOW)
            report = audit_window(directory)
            self.assertEqual((report["sessionsExamined"], report["pairsExamined"],
                              report["pairsStructurallyAdmitted"]), (1, 1, 1))
            self.assertEqual(report["realPairsAdmitted"], 0)
            self.assertFalse(report["executionAuthorization"])
            self.assertNotIn("Option 1", json.dumps(final_seal_payload(directory)))
            self.assertEqual(seal_payload(directory, 1)["sessionCount"], 0)
            self.assertEqual(seal_payload(directory, 2)["sessionCount"], 1)

    def test_three_actors_enumerate_every_unordered_pair(self) -> None:
        with TemporaryDirectory() as root:
            directory = self._new(root)
            self._open(directory, participants=["a", "b", "c"])
            for index, actor in enumerate(("a", "b", "c"), 1):
                view_base(directory, "s1", actor, now=NOW)
                propose(directory, "s1", actor, operation(index), f"lab://{actor}", now=NOW)
            close_session(directory, "s1", "accepted", now=NOW)
            report = audit_window(directory)
            self.assertEqual(report["pairsExamined"], 3)
            self.assertEqual(report["pairsStructurallyAdmitted"], 3)

    def test_unclosed_session_keeps_pairs_but_excludes_them(self) -> None:
        with TemporaryDirectory() as root:
            directory = self._new(root)
            self._open(directory)
            for index, actor in enumerate(("actor-a", "actor-b"), 1):
                view_base(directory, "s1", actor, now=NOW)
                propose(directory, "s1", actor, operation(index), f"lab://{actor}", now=NOW)
            report = audit_window(directory)
            self.assertEqual(report["sessionsExamined"], 1)
            self.assertEqual(report["sessionsAdmitted"], 0)
            self.assertEqual(report["pairsExamined"], 1)
            self.assertEqual(report["pairsStructurallyAdmitted"], 0)
            self.assertEqual(report["sessionsExcludedByReason"], {"session-not-closed": 1})
            self.assertEqual(report["pairsExcludedByReason"], {"session-not-closed": 1})
            close_session(directory, "s1", "accepted", now=NOW)
            self.assertEqual(audit_window(directory)["pairsStructurallyAdmitted"], 1)

    def test_unclosed_prospective_session_has_valid_final_seal(self) -> None:
        with TemporaryDirectory() as root:
            directory = Path(root) / "capture"
            create_window(directory, manifest("prospective"), registration_verified=True,
                          permission_reviewed=True)
            self._open(directory)
            for index, actor in enumerate(("actor-a", "actor-b"), 1):
                view_base(directory, "s1", actor, now=NOW)
                propose(directory, "s1", actor, operation(index), f"lab://{actor}", now=NOW)
            payload = final_seal_payload(directory, now=START + timedelta(days=14))
            payload["previousRunId"] = 114
            validate_payload(payload)
            self.assertEqual(payload["pairsExcludedByReason"], {"session-not-closed": 1})

    def test_exclusions_keep_full_sessions_and_primary_reasons(self) -> None:
        with TemporaryDirectory() as root:
            directory = self._new(root)
            self._open(directory, "empty")
            self._open(directory, "large", base=[{"id": f"b{i}", "value": "B"} for i in range(4)])
            self._open(directory, "delete")
            self._open(directory, "anchor")
            self._open(directory, "observed")
            self._open(directory, "missing")
            for session in ("large", "delete", "anchor", "observed", "missing"):
                view_base(directory, session, "actor-a", now=NOW)
                view_base(directory, session, "actor-b", now=NOW)
                propose(directory, session, "actor-a", operation(1), "lab://a", now=NOW)
                if session == "observed":
                    mark_external_observation(directory, session, "actor-b", now=NOW)
                second = operation(2, kind="delete" if session == "delete" else "insert",
                                   anchor="absent" if session == "anchor" else "$root")
                propose(directory, session, "actor-b", second,
                        "" if session == "missing" else "lab://b", now=NOW)
            for session in ("empty", "large", "delete", "anchor", "observed", "missing"):
                close_session(directory, session, "unresolved", now=NOW)
            report = audit_window(directory)
            self.assertEqual(report["sessionsExamined"], 6)
            self.assertEqual(report["pairsExamined"], 5)
            self.assertEqual(report["pairsStructurallyAdmitted"], 0)
            self.assertEqual(report["pairsExcludedByReason"], {
                "dependent-observation": 1, "invalid-anchor": 1, "invalid-base": 1,
                "missing-provenance": 1, "unsupported-operation": 1,
            })
            self.assertEqual(report["sessionsExcludedByReason"]["insufficient-proposals"], 1)

    def test_admission_mismatch_and_partial_event_fail_closed(self) -> None:
        with TemporaryDirectory() as root:
            directory = self._new(root)
            self._open(directory)
            admissions = directory / "admissions.jsonl"
            admissions.write_bytes(b"")
            with self.assertRaisesRegex(ValueError, "admission ledger"):
                audit_window(directory)
        with TemporaryDirectory() as root:
            directory = self._new(root)
            self._open(directory)
            with (directory / "events.jsonl").open("ab") as stream:
                stream.write(b'{"unfinished":')
            with self.assertRaisesRegex(ValueError, "incomplete record"):
                audit_window(directory)

    def test_interrupted_open_recovers_both_journals(self) -> None:
        with TemporaryDirectory() as root:
            directory = self._new(root)
            append = source_window._append

            def interrupt_before_event(path: Path, record: dict) -> None:
                if path.name == "events.jsonl":
                    raise OSError("simulated interruption between journal writes")
                append(path, record)

            with patch.object(source_window, "_append", side_effect=interrupt_before_event):
                with self.assertRaisesRegex(OSError, "simulated interruption"):
                    self._open(directory)
            self.assertTrue((directory / "session-open.pending").exists())
            report = audit_window(directory)
            self.assertEqual(report["sessionsExamined"], 1)
            self.assertEqual(report["sessionsExcludedByReason"], {"session-not-closed": 1})
            self.assertFalse((directory / "session-open.pending").exists())
            self.assertEqual(len((directory / "events.jsonl").read_bytes().splitlines()), 1)
            self.assertEqual(len((directory / "admissions.jsonl").read_bytes().splitlines()), 1)
            with self.assertRaisesRegex(ValueError, "duplicate session ID"):
                self._open(directory)

    def test_partial_open_append_recovers_only_the_expected_tail(self) -> None:
        for interrupted_name in ("admissions.jsonl", "events.jsonl"):
            with self.subTest(interrupted_name=interrupted_name), TemporaryDirectory() as root:
                directory = self._new(root)
                append = source_window._append

                def interrupt_mid_record(path: Path, record: dict) -> None:
                    if path.name == interrupted_name:
                        with path.open("ab") as stream:
                            stream.write(source_window.canonical(record)[:17])
                        raise OSError("simulated torn append")
                    append(path, record)

                with patch.object(source_window, "_append", side_effect=interrupt_mid_record):
                    with self.assertRaisesRegex(OSError, "simulated torn append"):
                        self._open(directory)
                self.assertTrue((directory / "session-open.pending").exists())
                report = audit_window(directory)
                self.assertEqual(report["sessionsExamined"], 1)
                self.assertFalse((directory / "session-open.pending").exists())
                self.assertEqual(len((directory / "events.jsonl").read_bytes().splitlines()), 1)
                self.assertEqual(len((directory / "admissions.jsonl").read_bytes().splitlines()), 1)

    def test_orphaned_partial_staging_file_has_no_admission(self) -> None:
        with TemporaryDirectory() as root:
            directory = self._new(root)
            staging = directory / "session-open.pending.tmp"
            staging.write_bytes(b'{"incomplete":')
            self.assertEqual(audit_window(directory)["sessionsExamined"], 0)
            self.assertFalse(staging.exists())
            self._open(directory)
            self.assertEqual(audit_window(directory)["sessionsExamined"], 1)

    def test_pending_open_rejects_unrelated_journal_tail(self) -> None:
        with TemporaryDirectory() as root:
            directory = self._new(root)
            with patch.object(source_window, "_append", side_effect=OSError("interrupted")):
                with self.assertRaisesRegex(OSError, "interrupted"):
                    self._open(directory)
            events = directory / "events.jsonl"
            events.write_bytes(events.read_bytes() + b"unrelated")
            with self.assertRaisesRegex(ValueError, "disagrees with the journals"):
                audit_window(directory)
            self.assertEqual(events.read_bytes(), b"unrelated")
            self.assertTrue((directory / "session-open.pending").exists())

    def test_prospective_initialization_needs_both_gates(self) -> None:
        with TemporaryDirectory() as root:
            target = Path(root) / "capture"
            with self.assertRaisesRegex(ValueError, "requires remote registration"):
                create_window(target, manifest("prospective"))
            self.assertFalse(target.exists())
            create_window(target, manifest("prospective"), registration_verified=True,
                          permission_reviewed=True)
            with self.assertRaisesRegex(ValueError, "before it ends"):
                seal_payload(target, 14, now=NOW)

    def test_duplicate_actor_proposal_and_out_of_window_fail(self) -> None:
        with TemporaryDirectory() as root:
            directory = self._new(root)
            self._open(directory)
            view_base(directory, "s1", "actor-a", now=NOW)
            propose(directory, "s1", "actor-a", operation(1), "lab://a", now=NOW)
            with self.assertRaisesRegex(ValueError, "already submitted"):
                propose(directory, "s1", "actor-a", operation(2), "lab://a", now=NOW)
            with self.assertRaisesRegex(ValueError, "capture clock moved"):
                close_session(directory, "s1", "cancelled", now=NOW - timedelta(seconds=1))
            with self.assertRaisesRegex(ValueError, "outside the frozen window"):
                close_session(directory, "s1", "cancelled", now=START + timedelta(days=14))
