# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic tests for source coverage and safe tracking plans."""

import unittest

from scripts.sync_github_tracking import ROOT, build_plan, source_inventory


class TrackingTests(unittest.TestCase):
    def test_committed_spec_inventory_is_complete(self):
        config, desired = source_inventory()
        self.assertEqual(21, sum(item["kind"] == "spec" for item in desired))
        self.assertEqual(159, sum(item["kind"] == "task" for item in desired))
        open_tasks = {item["key"] for item in desired
                      if item["state"] == "open" and item["kind"] == "task"}
        expected_open = {
            "SPEC-002/T006", "SPEC-009/T009", "SPEC-011/T008",
            "SPEC-019/T001", "SPEC-019/T002", "SPEC-019/T003",
            "SPEC-019/T004", "SPEC-019/T005", "SPEC-019/T007",
        }
        closure_tasks = (ROOT / "specs/017-m2-closure/tasks.md").read_text()
        for task_id in ("T004", "T005", "T006"):
            if f"- [ ] {task_id}:" in closure_tasks:
                expected_open.add(f"SPEC-017/{task_id}")
        runtime_tasks = (ROOT / "specs/020-m4-local-git-runtime/tasks.md").read_text()
        for task_id in ("T001", "T002", "T003", "T004", "T005", "T006", "T007"):
            if f"- [ ] {task_id} " in runtime_tasks:
                expected_open.add(f"SPEC-020/{task_id}")
        expected_open.update(f"SPEC-021/T{i:03d}" for i in (13, 14))
        self.assertEqual("open", config["specs"]["021-m4-alpha-runtime"]["state"])
        self.assertEqual("M4", config["specs"]["021-m4-alpha-runtime"]["milestone"])
        self.assertEqual("M4", config["specs"]["020-m4-local-git-runtime"]["milestone"])
        self.assertNotIn("M4", config["closed_milestones"])
        self.assertEqual(expected_open, open_tasks)
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
