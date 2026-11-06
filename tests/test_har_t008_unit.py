# SPDX-License-Identifier: AGPL-3.0-only
"""T008 lab driver controls: window, expiry, reading parsing; nothing native runs."""
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import har_t008_unit as driver  # noqa: E402
import har_t009_attempt as t9  # noqa: E402
from agent_braid import harness_hosts_native as hn  # noqa: E402

ISSUED = hn.issued_records((ROOT / driver.ISSUANCE).read_bytes(), **driver.TRUSTED)


class DriverTests(unittest.TestCase):
    def refused(self, when):
        with self.assertRaises(t9.AttemptRefused) as cm:
            driver.check_window(when, ISSUED)
        return cm.exception.reasons

    def test_units_are_limited_to_the_founders_window_and_the_issued_validity(self):
        self.assertEqual(self.refused(datetime(2026, 11, 6, 12, tzinfo=timezone.utc)), ["outside-founder-window"])
        self.assertEqual(self.refused(datetime(2026, 12, 1, tzinfo=timezone.utc)), ["outside-founder-window"])
        driver.check_window(datetime(2026, 11, 10, 12, tzinfo=timezone.utc), ISSUED)

    def test_the_cohort_is_capped_below_the_d2_maximum(self):
        self.assertEqual(driver.MAX_UNITS, 4)
        self.assertEqual(driver.parser().get_default("units"), 4)

    def test_reset_instants_parse_or_are_refused(self):
        day = datetime(2026, 11, 10, 12, tzinfo=timezone.utc)
        self.assertIsNone(driver._local(day, "25:99", driver._CLOCK))
        self.assertIsNone(driver._local(day, "2026-13-40 10:00", driver._DATE_CLOCK))
        self.assertIsInstance(driver._local(day, "2026-11-16 21:00", driver._DATE_CLOCK), int)

    def test_the_pinned_founder_record_parses_to_claude_authorized_and_codex_refused(self):
        from agent_braid import harness_hosts as hh
        raw = (ROOT / driver.FOUNDER_DECISIONS).read_bytes()
        decisions = hh.parse_profile_decisions(raw, expected_sha256=driver.FOUNDER_DECISIONS_SHA256)
        self.assertTrue(decisions["claude"].authorized)
        self.assertEqual(decisions["codex"].reason, "not-qualified: not installed")

    def test_trusted_hashes_are_the_issued_ones(self):
        self.assertEqual(ISSUED.containment_sha256, driver.TRUSTED["containment_sha256"])


if __name__ == "__main__":
    unittest.main()
