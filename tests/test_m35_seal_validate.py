# SPDX-License-Identifier: AGPL-3.0-only
"""Adversarial checks for metadata-only registration and remote seal linkage."""

from datetime import datetime, timezone
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from scripts.m35_sidecar import verify_permission_record, verify_registration
from scripts.m35_seal_validate import validate_link, validate_payload


REGISTER = {"format": "m35-seal-v1", "mode": "register", "windowId": "pilot-k",
            "familyId": "kinetiq-decisions", "startUtc": "2026-10-03T00:00:00Z",
            "endUtc": "2026-10-17T00:00:00Z", "protocolCommit": "a" * 40}
AFTER_WINDOW = datetime(2026, 10, 18, tzinfo=timezone.utc)


def daily(day: int, previous_run: int, events: int = 0) -> dict:
    return {"format": "m35-seal-v1", "mode": "daily", "windowId": "pilot-k",
            "familyId": "kinetiq-decisions", "startUtc": REGISTER["startUtc"],
            "endUtc": REGISTER["endUtc"], "protocolCommit": REGISTER["protocolCommit"],
            "registrationRunId": 100,
            "previousRunId": previous_run, "dayIndex": day, "eventCount": events,
            "sessionCount": 0, "journalCommitment": "b" * 64}


class M35SealValidateTests(unittest.TestCase):
    def test_full_chain_with_complete_final_aggregate(self) -> None:
        now = datetime(2026, 9, 30, tzinfo=timezone.utc)
        validate_link(REGISTER, None, None, now=now)
        previous = REGISTER
        for day in range(1, 15):
            candidate = daily(day, 100 if day == 1 else 100 + day - 1, events=day)
            validate_link(candidate, previous, candidate["previousRunId"], now=AFTER_WINDOW)
            previous = candidate
        final = {**daily(14, 114, events=14), "mode": "final", "pairsExamined": 2,
                 "pairsStructurallyAdmitted": 1,
                 "sessionsExcludedByReason": {"insufficient-proposals": 1},
                 "pairsExcludedByReason": {"invalid-anchor": 1},
                 "reportCommitment": "c" * 64}
        validate_link(final, previous, 114, now=AFTER_WINDOW)

    def test_registration_lead_time_and_shape(self) -> None:
        with self.assertRaisesRegex(ValueError, "at least 24 hours"):
            validate_link(REGISTER, None, None,
                          now=datetime(2026, 10, 2, 1, tzinfo=timezone.utc))
        with self.assertRaises(ValueError):
            validate_payload({**REGISTER, "sourceText": "private"})

    def test_skipped_day_wrong_family_and_replayed_predecessor_fail(self) -> None:
        with self.assertRaises(ValueError):
            validate_link(daily(2, 100), REGISTER, 100, now=AFTER_WINDOW)
        with self.assertRaises(ValueError):
            validate_link({**daily(1, 100), "familyId": "other"}, REGISTER, 100, now=AFTER_WINDOW)
        with self.assertRaises(ValueError):
            validate_link(daily(1, 100), REGISTER, 101, now=AFTER_WINDOW)

    def test_decreasing_counts_and_private_fields_fail(self) -> None:
        previous = daily(1, 100, events=2)
        with self.assertRaises(ValueError):
            validate_link(daily(2, 101, events=1), previous, 101, now=AFTER_WINDOW)
        with self.assertRaises(ValueError):
            validate_payload({**daily(2, 101), "itemSha": "a" * 64})

    def test_final_requires_day14_and_exact_partition(self) -> None:
        candidate = {**daily(14, 114), "mode": "final", "pairsExamined": 2,
                     "pairsStructurallyAdmitted": 1, "sessionsExcludedByReason": {},
                     "pairsExcludedByReason": {}, "reportCommitment": "c" * 64}
        with self.assertRaises(ValueError):
            validate_payload(candidate)
        candidate["pairsExcludedByReason"] = {"invalid-anchor": 1}
        with self.assertRaises(ValueError):
            validate_link(candidate, daily(13, 113), 114, now=AFTER_WINDOW)

    def test_final_accepts_unclosed_session_exclusion(self) -> None:
        final = {**daily(14, 114, events=4), "mode": "final", "sessionCount": 1,
                 "pairsExamined": 1, "pairsStructurallyAdmitted": 0,
                 "sessionsExcludedByReason": {"session-not-closed": 1},
                 "pairsExcludedByReason": {"session-not-closed": 1},
                 "reportCommitment": "c" * 64}
        previous = {**daily(14, 113, events=4), "sessionCount": 1}
        validate_link(final, previous, 114, now=AFTER_WINDOW)

    def test_early_or_retargeted_seal_fails(self) -> None:
        with self.assertRaisesRegex(ValueError, "before the completed UTC day"):
            validate_link(daily(1, 100), REGISTER, 100,
                          now=datetime(2026, 10, 3, 23, tzinfo=timezone.utc))
        with self.assertRaisesRegex(ValueError, "frozen source identity"):
            validate_link({**daily(1, 100), "protocolCommit": "d" * 40},
                          REGISTER, 100, now=AFTER_WINDOW)

    def test_skipped_or_runnerless_registration_cannot_open_capture(self) -> None:
        manifest = {"windowId": "pilot-k", "familyId": "kinetiq-decisions",
                    "startUtc": REGISTER["startUtc"], "endUtc": REGISTER["endUtc"],
                    "protocolCommit": REGISTER["protocolCommit"], "registrationRunId": 100}
        run = {"status": "completed", "conclusion": "success", "event": "workflow_dispatch",
               "path": ".github/workflows/m35-seal.yml@main", "head_branch": "main",
               "head_repository": {"full_name": "jayanez/agent-braid-m35-audit"}}
        with patch("scripts.m35_sidecar._json_from_gh", side_effect=[run, {"jobs": []}]):
            with self.assertRaisesRegex(ValueError, "no executed runner"):
                verify_registration(manifest)
        with patch("scripts.m35_sidecar._json_from_gh", return_value={**run, "head_branch": "other"}):
            with self.assertRaisesRegex(ValueError, "did not complete successfully"):
                verify_registration(manifest)

    def test_future_dated_permission_record_is_not_accepted(self) -> None:
        manifest = {"windowId": "pilot-k", "startUtc": "2100-01-03T00:00:00Z"}
        record = {"format": "m35-source-permission-v1", "windowId": "pilot-k",
                  "sourceOwner": "owner", "workflow": "engineering-options",
                  "permissionGranted": True, "participantRightsReviewed": True,
                  "privacyApproved": True, "labExportReviewed": True,
                  "approvedAtUtc": "2100-01-01T00:00:00Z"}
        with TemporaryDirectory() as root:
            item = Path(root) / "permission.json"
            item.write_text(json.dumps(record), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "incomplete"):
                verify_permission_record(item, manifest)


if __name__ == "__main__":
    unittest.main()
