# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic tests for source coverage and safe tracking plans."""

import unittest

from scripts.sync_github_tracking import build_plan, source_inventory


class TrackingTests(unittest.TestCase):
    def test_committed_spec_inventory_is_complete(self):
        config, desired = source_inventory()
        self.assertEqual(16, sum(item["kind"] == "spec" for item in desired))
        self.assertEqual(118, sum(item["kind"] == "task" for item in desired))
        self.assertEqual(4, sum(item["state"] == "open" and item["kind"] == "task" for item in desired))
        self.assertEqual({"SPEC-004/T005"}, set(config["task_state_overrides"]))

    def test_plan_is_empty_for_matching_relationships(self):
        config = {"milestones": {"M0": "description"}, "closed_milestones": []}
        desired = [
            {"key": "SPEC-001", "kind": "spec", "title": "[SPEC-001] One", "milestone": "M0", "state": "open", "parent": None},
            {"key": "SPEC-001/T001", "kind": "task", "title": "[SPEC-001 T001] Task", "milestone": "M0", "state": "closed", "parent": "SPEC-001", "task_text": "Task"},
        ]
        issues = {
            "SPEC-001": {"number": 4, "id": 40, "title": desired[0]["title"], "state": "open", "milestone": {"title": "M0"}},
            "SPEC-001/T001": {"number": 5, "id": 50, "title": desired[1]["title"], "state": "closed", "milestone": {"title": "M0"}, "body": "## Task\n\nTask\n\n- Source: source"},
        }
        self.assertEqual([], build_plan(config, desired, {"M0": {"number": 1, "state": "open"}}, issues,
                                        {"children": {"SPEC-001": {50}}, "unmarked_titles": set()}))

    def test_plan_reports_missing_child_and_never_deletes_orphans(self):
        config = {"milestones": {"M0": "description"}, "closed_milestones": []}
        desired = [{"key": "SPEC-001", "kind": "spec", "title": "[SPEC-001] One", "milestone": "M0", "state": "open", "parent": None},
                   {"key": "SPEC-001/T001", "kind": "task", "title": "[SPEC-001 T001] Task", "milestone": "M0", "state": "closed", "parent": "SPEC-001", "task_text": "Task"}]
        issues = {"SPEC-001": {"number": 4, "id": 40, "title": desired[0]["title"], "state": "open", "milestone": {"title": "M0"}},
                  "SPEC-999": {"number": 99}}
        operations = build_plan(config, desired, {"M0": {"number": 1, "state": "open"}}, issues,
                                {"children": {"SPEC-001": set()}, "unmarked_titles": set()})
        self.assertEqual(["review_orphan", "create_issue", "link_subissue", "set_state"],
                         [operation["action"] for operation in operations])

    def test_milestone_closure_requires_explicit_mapping(self):
        config = {"milestones": {"M0": "description"}, "closed_milestones": ["M0"]}
        operations = build_plan(config, [], {"M0": {"number": 1, "state": "open"}}, {},
                                {"children": {}, "unmarked_titles": set()})
        self.assertEqual([{"action": "set_milestone_state", "name": "M0",
                           "from": "open", "to": "closed"}], operations)


if __name__ == "__main__":
    unittest.main()
