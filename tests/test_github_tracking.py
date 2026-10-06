# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic tests for source coverage and safe tracking plans."""

from contextlib import redirect_stdout
from copy import deepcopy
import io
import json
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.sync_github_tracking import (ROOT, apply_plan, build_plan, main,
                                          remote_inventory, source_inventory,
                                          validate_milestone_numbers)


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
        }
        self.assertTrue(required_open <= open_tasks)
        self.assertEqual("closed", next(item["state"] for item in desired
                                        if item["key"] == "SPEC-021/T014"))
        self.assertEqual("open", config["specs"]["021-m4-alpha-runtime"]["state"])
        self.assertEqual("M4 — Agent Braid runtime", config["specs"]["021-m4-alpha-runtime"]["milestone"])
        self.assertEqual("M4 — Agent Braid runtime", config["specs"]["020-m4-local-git-runtime"]["milestone"])
        self.assertNotIn("M4 — Agent Braid runtime", config["closed_milestones"])
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


class MilestoneNamingTests(unittest.TestCase):
    def setUp(self):
        self.name = "M0 — Operational foundations"
        self.config = {"repository": "owner/repo", "project_url": "https://example.test/project",
                       "milestones": {self.name: "description"}, "closed_milestones": [self.name],
                       "milestone_numbers": {self.name: 1}}
        self.remote = {"M0": {"number": 1, "title": "M0", "state": "closed",
                              "description": "historic description", "due_on": None}}
        self.extra = {"children": {}, "unmarked_titles": set()}
        self.rename = {"action": "rename_milestone", "number": 1, "from": "M0", "to": self.name}

    def test_open_and_closed_milestones_are_renamed_without_creation_or_issue_moves(self):
        desired = [{"key": "SPEC-001", "kind": "spec", "parent": None,
                    "title": "One", "milestone": self.name, "state": "open"}]
        issues = {"SPEC-001": {"number": 4, "title": "One", "state": "open",
                              "milestone": {"number": 1, "title": "M0"}}}
        for state in ("open", "closed"):
            with self.subTest(state=state):
                self.remote["M0"]["state"] = state
                self.config["closed_milestones"] = [self.name] if state == "closed" else []
                self.assertEqual([self.rename], build_plan(self.config, desired, self.remote, issues, self.extra))

    def test_title_only_scope_excludes_states_and_issue_drift(self):
        self.remote["M0"]["state"] = "open"
        desired = [{"key": "SPEC-001"}]
        issues = {"SPEC-999": {"number": 99}}
        self.assertEqual([self.rename], build_plan(self.config, desired, self.remote, issues, {},
                                                  milestone_titles_only=True))

    def test_apply_patches_only_title_and_second_plan_is_empty(self):
        updated = {**self.remote["M0"], "title": self.name}
        with patch("scripts.sync_github_tracking.gh_api", return_value=updated) as api:
            apply_plan("owner/repo", self.config, [], self.remote, {}, [self.rename])
        api.assert_called_once_with("repos/owner/repo/milestones/1", method="PATCH", body={"title": self.name})
        self.assertEqual([], build_plan(self.config, [], {self.name: updated}, {}, {},
                                       milestone_titles_only=True))

    def test_missing_registered_number_cannot_be_recreated_or_replaced_by_same_title(self):
        for remote in ({}, {self.name: {"number": 2, "title": self.name, "state": "closed"}}):
            with self.subTest(remote=remote), self.assertRaisesRegex(ValueError, "missing"):
                build_plan(self.config, [], remote, {}, {}, milestone_titles_only=True)

    def test_occupied_target_title_is_rejected_before_writes(self):
        self.remote[self.name] = {"number": 2, "title": self.name, "state": "open"}
        with self.assertRaisesRegex(ValueError, "collision"):
            build_plan(self.config, [], self.remote, {}, {}, milestone_titles_only=True)
        with patch("scripts.sync_github_tracking.gh_api") as api:
            with self.assertRaisesRegex(ValueError, "collision"):
                apply_plan("owner/repo", self.config, [], self.remote, {}, [self.rename])
            api.assert_not_called()

    def test_invalid_and_duplicate_bindings_are_rejected(self):
        for numbers in ({self.name: True}, {self.name: 0}, {self.name: "1"}, {"unknown": 1},
                        {self.name: 1, "Other": 1}):
            config = deepcopy(self.config)
            config["milestones"]["Other"] = "description"
            config["milestone_numbers"] = numbers
            with self.subTest(numbers=numbers), self.assertRaises(ValueError):
                validate_milestone_numbers(config)

    def test_mixed_bindings_cannot_resolve_two_names_to_same_milestone(self):
        self.config["milestones"]["M0"] = "description"
        with self.assertRaisesRegex(ValueError, "multiple configured"):
            build_plan(self.config, [], self.remote, {}, self.extra)

    def test_title_only_scope_requires_complete_number_bindings(self):
        self.config["milestone_numbers"] = {}
        with self.assertRaisesRegex(ValueError, "number for every"):
            build_plan(self.config, [], self.remote, {}, {}, milestone_titles_only=True)

    def test_title_only_inventory_never_reads_issues_or_project(self):
        with patch("scripts.sync_github_tracking.pages", return_value=list(self.remote.values())) as pages:
            self.assertEqual((self.remote, {}, {}), remote_inventory("owner/repo", milestone_titles_only=True))
        pages.assert_called_once_with("repos/owner/repo/milestones?state=all")

    def audit_digest(self, title_only=True):
        args = ["audit"] + (["--milestone-titles-only"] if title_only else [])
        output = io.StringIO()
        with patch("scripts.sync_github_tracking.source_inventory", return_value=(self.config, [])), \
             patch("scripts.sync_github_tracking.remote_inventory", return_value=(self.remote, {}, self.extra)), \
             redirect_stdout(output):
            self.assertEqual(1, main(args))
        return json.loads(output.getvalue())["plan_sha256"]

    def test_full_and_title_only_digest_cannot_be_interchanged(self):
        self.assertNotEqual(self.audit_digest(), self.audit_digest(title_only=False))

    def test_apply_retains_repository_digest_and_clean_develop_guards(self):
        digest = self.audit_digest()
        cases = [
            ("wrong/repo", digest, "develop", ""),
            ("owner/repo", "wrong", "develop", ""),
            ("owner/repo", self.audit_digest(title_only=False), "develop", ""),
            ("owner/repo", digest, "feature", ""),
            ("owner/repo", digest, "develop", " M user-file"),
        ]
        for repo, supplied_digest, branch, dirty in cases:
            with self.subTest(repo=repo, digest=supplied_digest, branch=branch, dirty=dirty), \
                 patch("scripts.sync_github_tracking.source_inventory", return_value=(self.config, [])), \
                 patch("scripts.sync_github_tracking.remote_inventory", return_value=(self.remote, {}, self.extra)), \
                 patch("scripts.sync_github_tracking.subprocess.run", side_effect=[SimpleNamespace(stdout=branch), SimpleNamespace(stdout=dirty)]), \
                 patch("scripts.sync_github_tracking.apply_plan") as apply, \
                 redirect_stdout(io.StringIO()), patch("sys.stderr", new_callable=io.StringIO):
                with self.assertRaises(SystemExit):
                    main(["apply", "--milestone-titles-only", "--confirm-repository", repo,
                          "--plan-sha256", supplied_digest])
                apply.assert_not_called()

    def test_apply_uses_reviewed_title_only_operations(self):
        digest = self.audit_digest()
        with patch("scripts.sync_github_tracking.source_inventory", return_value=(self.config, [])), \
             patch("scripts.sync_github_tracking.remote_inventory", return_value=(self.remote, {}, self.extra)) as inventory, \
             patch("scripts.sync_github_tracking.subprocess.run", side_effect=[SimpleNamespace(stdout="develop"), SimpleNamespace(stdout="")]), \
             patch("scripts.sync_github_tracking.apply_plan") as apply, redirect_stdout(io.StringIO()):
            self.assertEqual(0, main(["apply", "--milestone-titles-only", "--confirm-repository", "owner/repo",
                                     "--plan-sha256", digest]))
        inventory.assert_called_once_with("owner/repo", milestone_titles_only=True)
        apply.assert_called_once_with("owner/repo", self.config, [], self.remote, {}, [self.rename])


if __name__ == "__main__":
    unittest.main()
