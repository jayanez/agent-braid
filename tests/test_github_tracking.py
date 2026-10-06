# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic tests for source coverage and safe tracking plans."""

import re
import unittest

from scripts.sync_github_tracking import ROOT, build_plan, source_inventory


class TrackingTests(unittest.TestCase):
    def test_committed_spec_inventory_is_complete(self):
        config, desired = source_inventory()
        folders = sorted(path for path in (ROOT / "specs").iterdir()
                         if path.name[:3].isdigit() and (path / "spec.md").is_file())
        self.assertTrue(folders)
        self.assertEqual({path.name for path in folders}, set(config["specs"]))
        source_specs = [f"SPEC-{path.name[:3]}" for path in folders]
        self.assertEqual(len(source_specs), len(set(source_specs)))
        source_tasks = {}
        for folder, spec_id in zip(folders, source_specs):
            task_lines = re.findall(r"^- \[([ x])\] (T\d{3})\b",
                                    (folder / "tasks.md").read_text(), re.MULTILINE)
            self.assertTrue(task_lines, folder.name)
            for checked, task_id in task_lines:
                key = f"{spec_id}/{task_id}"
                self.assertNotIn(key, source_tasks, f"duplicate source task: {key}")
                source_tasks[key] = {
                    "parent": spec_id,
                    "milestone": config["specs"][folder.name]["milestone"],
                    "state": "closed" if checked == "x" or key in config["task_state_overrides"] else "open",
                }
        keys = [item["key"] for item in desired]
        self.assertEqual(len(keys), len(set(keys)), "duplicate tracking identity")
        self.assertEqual(set(source_specs), {item["key"] for item in desired if item["kind"] == "spec"})
        self.assertEqual(set(source_tasks), {item["key"] for item in desired if item["kind"] == "task"})
        self.assertEqual(set(source_specs) | set(source_tasks), set(keys))
        for item in desired:
            with self.subTest(key=item["key"]):
                if item["kind"] == "task":
                    expected = source_tasks[item["key"]]
                else:
                    folder = next(path for path in folders if f"SPEC-{path.name[:3]}" == item["key"])
                    expected = {"parent": None, **config["specs"][folder.name]}
                for field in ("parent", "milestone", "state"):
                    self.assertEqual(expected[field], item[field])
        open_tasks = {item["key"] for item in desired
                      if item["state"] == "open" and item["kind"] == "task"}
        required_open = {
            "SPEC-002/T006", "SPEC-009/T009", "SPEC-011/T008",
            "SPEC-019/T001", "SPEC-019/T002", "SPEC-019/T003",
            "SPEC-019/T004", "SPEC-019/T005", "SPEC-019/T007",
            "SPEC-021/T014",
        }
        self.assertTrue(required_open <= open_tasks)
        self.assertEqual("open", config["specs"]["021-m4-alpha-runtime"]["state"])
        self.assertEqual("M4", config["specs"]["021-m4-alpha-runtime"]["milestone"])
        self.assertEqual("M4", config["specs"]["020-m4-local-git-runtime"]["milestone"])
        self.assertNotIn("M4", config["closed_milestones"])
        self.assertEqual({key for key, task in source_tasks.items() if task["state"] == "open"}, open_tasks)
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
