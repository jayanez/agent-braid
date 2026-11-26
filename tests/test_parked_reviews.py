# SPDX-License-Identifier: AGPL-3.0-only
"""Parked-work review dates warn near their date and retire themselves; they never fail an audit."""
from copy import deepcopy
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.sync_github_tracking import (
    ROOT, main, parked_review_warnings, source_inventory, validate_parked_reviews)

MILESTONE = "Deferred"
ENTRY = {"review_by": "2027-04-25", "source": "docs/note.md#q1-parked-first"}


class ParkedReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        folder = self.root / "specs/001-example"
        folder.mkdir(parents=True)
        (folder / "spec.md").write_text("# Example\n")
        (folder / "assurance.json").write_text('{"requirements": []}')
        (folder / "tasks.md").write_text("- [ ] T001: Open task.\n- [x] T002: Done task.\n")
        (self.root / "docs").mkdir()
        (self.root / "docs/note.md").write_text("# Note\n\n### Q1. Parked: first\n")
        self.config = dict(repository="owner/repo", project_url="example", milestones={MILESTONE: "parked"},
                           specs={"001-example": {"milestone": MILESTONE, "state": "open"}},
                           closed_milestones=[], task_state_overrides={}, project_review_pending=[],
                           parked_reviews={"SPEC-001/T001": dict(ENTRY)})
        self.path = self.root / "config.json"

    def inventory(self, config=None):
        self.path.write_text(json.dumps(config or self.config))
        return source_inventory(self.root, self.path)

    def refused(self, mutate, text):
        config = deepcopy(self.config)
        mutate(config["parked_reviews"])
        with self.assertRaisesRegex(ValueError, text):
            self.inventory(config)

    def test_valid_entry_is_accepted_and_absent_member_is_optional(self):
        self.inventory()
        del self.config["parked_reviews"]
        self.inventory()

    def test_invalid_entries_are_refused(self):
        self.refused(lambda p: p.update({"SPEC-001/T002": dict(ENTRY)}), "open tracked record")
        self.refused(lambda p: p.update({"SPEC-001/T009": dict(ENTRY)}), "open tracked record")
        self.refused(lambda p: p["SPEC-001/T001"].update(review_by="2027-4-25"), "YYYY-MM-DD")
        self.refused(lambda p: p["SPEC-001/T001"].update(review_by="2027-02-30"), "calendar date")
        self.refused(lambda p: p["SPEC-001/T001"].update(extra=1), "exactly")
        self.refused(lambda p: p["SPEC-001/T001"].update(source=""), "needs a source")
        self.refused(lambda p: p["SPEC-001/T001"].update(source="docs/missing.md"), "existing repository file")
        self.refused(lambda p: p["SPEC-001/T001"].update(source="docs/note.md#q9-missing"), "anchor does not resolve")
        self.refused(lambda p: p["SPEC-001/T001"].update(source="specs/001-example/assurance.json#x"), "anchor does not resolve")
        self.refused(lambda p: p["SPEC-001/T001"].update(source="../outside.md"), "existing repository file")
        self.refused(lambda p: p["SPEC-001/T001"].update(source="/etc/hosts"), "existing repository file")
        config = deepcopy(self.config)
        config["parked_reviews"] = []
        with self.assertRaisesRegex(ValueError, "mapping"):
            self.inventory(config)

    def warnings(self, today, open_issues=3, config=None):
        milestones = {MILESTONE: {"number": 24, "open_issues": open_issues}}
        return parked_review_warnings(config or self.config, milestones, today)

    def test_warns_only_from_thirty_days_before_the_review_date(self):
        self.assertEqual([], self.warnings(date(2027, 3, 25)))
        near = self.warnings(date(2027, 3, 26))
        self.assertEqual(1, len(near))
        self.assertTrue(near[0].startswith("::warning "))
        self.assertIn("SPEC-001/T001 review by 2027-04-25 is due in 30 days", near[0])
        self.assertIn("is due in 29 days", self.warnings(date(2027, 3, 27))[0])
        self.assertIn("is due in 0 days", self.warnings(date(2027, 4, 25))[0])
        self.assertIn("was due 6 days ago", self.warnings(date(2027, 5, 1))[0])
        self.assertIn("is due in 1 day;", self.warnings(date(2027, 4, 24))[0])

    def test_empty_or_absent_entries_are_a_no_op_even_when_deferred_is_empty(self):
        for config in (dict(self.config, parked_reviews={}), {k: v for k, v in self.config.items() if k != "parked_reviews"}):
            self.assertEqual([], self.warnings(date(2030, 1, 1), open_issues=0, config=config))

    def test_empty_deferred_milestone_emits_one_retirement_warning(self):
        lines = self.warnings(date(2027, 1, 1), open_issues=0)
        self.assertEqual(1, len(lines))
        self.assertIn("Deferred is empty: close the milestone, remove the STATUS parked table "
                      "and parked_reviews, and remove this step.", lines[0])
        both = self.warnings(date(2027, 5, 1), open_issues=0)
        self.assertEqual(2, len(both))
        self.assertEqual([], self.warnings(date(2027, 1, 1), open_issues=1))

    def test_a_malformed_date_cannot_reach_the_warning_step(self):
        # main() builds the inventory first, and that refuses a bad date, so the
        # warning function only ever sees validated ISO dates.
        self.refused(lambda p: p["SPEC-001/T001"].update(review_by="soon"), "YYYY-MM-DD")

    def audit(self, plan_issues_open, today):
        """Run main(["audit"]) against a fake remote; return (rc, stderr)."""
        config, desired = self.inventory()
        issues = {item["key"]: dict(number=i + 1, id=i + 1, title=item["title"], body=item["body"],
                                   state=item["state"], milestone={"title": MILESTONE, "number": 24})
                  for i, item in enumerate(desired)}
        if not plan_issues_open:
            issues.pop("SPEC-001/T001")  # one create_issue operation
        milestones = {MILESTONE: {"number": 24, "title": MILESTONE, "state": "open", "open_issues": 2}}
        extra = {"children": {"SPEC-001": {issue["id"] for issue in issues.values()}}, "unmarked_titles": set()}
        config = dict(config, milestone_numbers={MILESTONE: 24})
        err = io.StringIO()
        with patch("scripts.sync_github_tracking.source_inventory", return_value=(config, desired)), \
                patch("scripts.sync_github_tracking.remote_inventory", return_value=(milestones, issues, extra)), \
                redirect_stdout(io.StringIO()), redirect_stderr(err):
            rc = main(["audit"], today=today)
        return rc, err.getvalue()

    def test_audit_prints_the_warning_and_the_exit_status_depends_only_on_operations(self):
        rc, err = self.audit(True, date(2027, 4, 20))
        self.assertEqual(0, rc)
        self.assertIn("::warning title=Parked work review::SPEC-001/T001 review by 2027-04-25 is due in 5 days", err)
        rc, err = self.audit(False, date(2027, 4, 20))
        self.assertEqual(1, rc)
        self.assertIn("::warning title=Parked work review::", err)
        rc, err = self.audit(True, date(2026, 1, 1))
        self.assertEqual((0, ""), (rc, err))

    def test_missing_milestone_never_raises(self):
        self.assertEqual([], parked_review_warnings(self.config, {}, date(2027, 1, 1)))

    def test_committed_entries_validate_against_the_repository(self):
        config, desired = source_inventory()
        entries = validate_parked_reviews(ROOT, config, desired)
        self.assertIn("SPEC-060/T011", entries)
        self.assertEqual("2027-04-25", entries["SPEC-060/T011"]["review_by"])
        self.assertEqual(MILESTONE, config["specs"]["060-portable-prompt-names"]["milestone"])

    def test_closed_parent_carries_a_state_reason_only_when_closed_and_known(self):
        config = deepcopy(self.config)
        config["parked_reviews"] = {}
        config["specs"]["001-example"] = {"milestone": MILESTONE, "state": "closed", "state_reason": "not_planned"}
        _, desired = self.inventory(config)
        self.assertEqual("not_planned", desired[0]["state_reason"])
        for bad in ({"state": "open", "state_reason": "not_planned"}, {"state": "closed", "state_reason": "wontfix"}):
            config["specs"]["001-example"] = {"milestone": MILESTONE, **bad}
            with self.assertRaisesRegex(ValueError, "parent state reason"):
                self.inventory(config)

    def test_committed_spec077_parent_closes_as_not_planned(self):
        _, desired = source_inventory()
        parent = next(item for item in desired if item["key"] == "SPEC-077")
        self.assertEqual(("closed", "not_planned"), (parent["state"], parent["state_reason"]))


if __name__ == "__main__":
    unittest.main()
