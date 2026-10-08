# SPDX-License-Identifier: AGPL-3.0-only
"""Deterministic tests for source coverage and safe tracking plans."""

from contextlib import redirect_stdout
from copy import deepcopy
import hashlib
import io
import json
import re
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from scripts.sync_github_tracking import (ROOT, apply_plan, build_plan, main,
                                          milestone_plan,
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
        self.assertEqual("closed", config["specs"]["021-m4-alpha-runtime"]["state"])
        self.assertEqual("M4 — Agent Braid runtime", config["specs"]["021-m4-alpha-runtime"]["milestone"])
        self.assertEqual("M4 — Agent Braid runtime", config["specs"]["020-m4-local-git-runtime"]["milestone"])
        # The separate item22 founder decision accepts bounded M4 completion;
        # remote closure still requires the reviewed guarded tracking apply.
        self.assertIn("M4 — Agent Braid runtime", config["closed_milestones"])
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


class TaskTraceTests(unittest.TestCase):
    def setUp(self):
        self.config = {"milestones": {"M4": "bounded runtime"}, "closed_milestones": []}
        self.milestones = {"M4": {"number": 6, "state": "open"}}
        self.old_trace = "- Trace: REQ-001 / SC-001"
        self.new_trace = "- Trace: REQ-001 REQ-002 / SC-001 SC-002"
        body = "## Task\n\nSelect subset.\n\n- Source: source\n" + self.new_trace + "\n- State basis: checkbox.\n"
        self.item = {"key": "SPEC-032/T001", "kind": "task", "parent": None,
                     "title": "Task", "state": "open", "milestone": "M4",
                     "task_text": "Select subset.", "body": body}
        self.issues = {self.item["key"]: {"number": 99, "title": "Task", "state": "open",
                                       "milestone": {"title": "M4", "number": 6},
                                       "body": body.replace(self.new_trace, self.old_trace)}}
        self.extra = {"children": {}, "unmarked_titles": set()}

    def plan(self):
        return build_plan(self.config, [self.item], self.milestones, self.issues, self.extra)

    def test_trace_only_change_is_audited_applied_and_idempotent_with_notes_retained(self):
        notes = "\nReviewer note: retain this annotation.\n"
        self.issues[self.item["key"]]["body"] += notes
        operations = self.plan()
        self.assertEqual([{"action": "update_task_text", "key": self.item["key"],
                           "trace_from": self.old_trace, "trace_to": self.new_trace}], operations)
        updated = {**self.issues[self.item["key"]], "body": self.item["body"] + notes}
        with patch("scripts.sync_github_tracking.gh_api", return_value=updated) as api:
            apply_plan("owner/repo", self.config, [self.item], self.milestones, self.issues, operations)
        api.assert_called_once_with("repos/owner/repo/issues/99", method="PATCH",
                                    body={"body": self.item["body"] + notes})
        self.assertEqual([], self.plan())

    def test_missing_or_duplicate_trace_requires_review_before_any_write(self):
        original = self.issues[self.item["key"]]["body"]
        for body in (original.replace(self.old_trace + "\n", ""), original + self.old_trace + "\n"):
            with self.subTest(body=body):
                self.issues[self.item["key"]]["body"] = body
                operations = self.plan()
                self.assertEqual([{"action": "review_body", "key": self.item["key"]}], operations)
                with patch("scripts.sync_github_tracking.gh_api") as api:
                    with self.assertRaisesRegex(ValueError, "manual review"):
                        apply_plan("owner/repo", self.config, [self.item], self.milestones, self.issues, operations)
                    api.assert_not_called()

    def test_equivalent_legacy_unreferenced_trace_is_retained_without_operations(self):
        canonical = "- Trace: See the parent issue and assurance record."
        legacy = "- Trace: No direct REQ/SC reference in tasks.md; see the parent issue and assurance record."
        self.item["body"] = self.item["body"].replace(self.new_trace, canonical)
        self.issues[self.item["key"]]["body"] = self.item["body"].replace(canonical, legacy)
        self.assertEqual([], self.plan())

    def test_trace_drift_after_review_is_rejected_without_writing(self):
        operations = self.plan()
        self.issues[self.item["key"]]["body"] = self.issues[self.item["key"]]["body"].replace(
            self.old_trace, "- Trace: another candidate")
        with patch("scripts.sync_github_tracking.gh_api") as api:
            with self.assertRaisesRegex(ValueError, "trace changed"):
                apply_plan("owner/repo", self.config, [self.item], self.milestones, self.issues, operations)
            api.assert_not_called()


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


class ScopedMilestoneTests(unittest.TestCase):
    def setUp(self):
        self.name = "M4 — Agent Braid runtime"
        self.other = "M3 — Braid semantics"
        self.config = {"repository": "owner/repo", "project_url": "https://example.test/project",
                       "milestones": {self.name: "runtime", self.other: "semantics"},
                       "closed_milestones": [], "milestone_numbers": {self.name: 6, self.other: 5}}
        self.milestones = {self.name: {"number": 6, "title": self.name, "state": "open"},
                           self.other: {"number": 5, "title": self.other, "state": "open"}}
        self.desired = []
        self.issues = {}
        self.extra = {"children": {}, "unmarked_titles": set()}
        for idx in range(14):
            key = f"SPEC-022/T{idx + 1:03}"
            task_text = f"Selected task {idx}"
            body = f"## Task\n\n{task_text}\n\n- Source: source\n- Trace: REQ-001 / SC-001\n"
            item = {"key": key, "kind": "task", "parent": None,
                    "title": f"[{key.replace('/', ' ')}] {task_text}", "state": "closed",
                    "milestone": self.name, "task_text": task_text, "body": body}
            issue = {"number": 100 + idx, "id": 1000 + idx, "title": item["title"],
                     "state": "open" if idx < 10 else "closed",
                     "milestone": {"number": 6, "title": self.name}, "body": body}
            if idx in {10, 11}:
                issue["title"] = f"stale title {idx}"
            if idx in {12, 13}:
                issue["body"] = body.replace(task_text, f"stale task {idx}")
            self.desired.append(item)
            self.issues[key] = issue
        # Deliberately noisy records outside M4 must not leak into its plan.
        for idx in range(56):
            key = f"SPEC-001/T{idx + 1:03}"
            self.desired.append({"key": key, "kind": "task", "parent": None,
                                 "title": f"desired {key}", "state": "closed",
                                 "milestone": self.other, "task_text": "other", "body": ""})
            self.issues[key] = {"number": 200 + idx, "id": 2000 + idx, "title": f"stale {key}",
                                "state": "open", "milestone": {"number": 5, "title": self.other},
                                "body": ""}

    def test_exactly_fourteen_selected_operations_exclude_fifty_six_unrelated(self):
        _, _, _, operations = milestone_plan(self.config, self.desired, self.milestones,
                                             self.issues, self.extra, 6)
        self.assertEqual(14, len(operations))
        self.assertEqual(10, sum(op["action"] == "set_state" for op in operations))
        self.assertEqual(2, sum(op["action"] == "update_title" for op in operations))
        self.assertEqual(2, sum(op["action"] == "update_task_text" for op in operations))
        self.assertTrue(all(op.get("key", "").startswith("SPEC-022/") for op in operations))

    def test_missing_moved_and_unknown_assigned_records_fail_closed(self):
        missing = deepcopy(self.issues)
        del missing["SPEC-022/T001"]
        with self.assertRaisesRegex(ValueError, "missing"):
            milestone_plan(self.config, self.desired, self.milestones, missing, self.extra, 6)
        moved = deepcopy(self.issues)
        moved["SPEC-022/T001"]["milestone"] = {"number": 5, "title": self.other}
        with self.assertRaisesRegex(ValueError, "moved"):
            milestone_plan(self.config, self.desired, self.milestones, moved, self.extra, 6)
        unknown = deepcopy(self.issues)
        unknown["SPEC-999/T001"] = {"number": 999, "milestone": {"number": 6}}
        with self.assertRaisesRegex(ValueError, "unknown or out-of-scope"):
            milestone_plan(self.config, self.desired, self.milestones, unknown, self.extra, 6)

    def test_only_selected_milestone_title_and_configured_state_are_included(self):
        config = deepcopy(self.config)
        config["closed_milestones"] = [self.name]
        milestones = deepcopy(self.milestones)
        milestones[self.name]["title"] = "M4"
        _, _, _, operations = milestone_plan(config, self.desired, milestones,
                                             self.issues, self.extra, 6)
        milestone_operations = [op for op in operations if op["action"].endswith("milestone")
                                or op["action"] in {"rename_milestone", "set_milestone_state"}]
        self.assertEqual(["rename_milestone", "set_milestone_state"],
                         [op["action"] for op in milestone_operations])
        self.assertTrue(all(op.get("number", 6) == 6 for op in milestone_operations))

    def test_digest_binds_selected_number_and_rejects_other_scope_replay(self):
        def digest(extra_args):
            output = io.StringIO()
            with patch("scripts.sync_github_tracking.source_inventory",
                       return_value=(self.config, self.desired)), \
                 patch("scripts.sync_github_tracking.remote_inventory",
                       return_value=(self.milestones, self.issues, self.extra)), \
                 redirect_stdout(output):
                self.assertIn(main(["audit", *extra_args]), (0, 1))
            return json.loads(output.getvalue())
        selected = digest(["--milestone-number", "6"])
        other = digest(["--milestone-number", "5"])
        full = digest([])
        title_only = digest(["--milestone-titles-only"])
        self.assertEqual("milestone:6", selected["scope"])
        self.assertEqual(6, selected["milestone_number"])
        self.assertNotEqual(selected["plan_sha256"], other["plan_sha256"])
        self.assertNotEqual(selected["plan_sha256"], full["plan_sha256"])
        self.assertNotEqual(selected["plan_sha256"], title_only["plan_sha256"])

    def test_scope_flags_are_mutually_exclusive_and_task_registration_is_dynamic(self):
        with patch("scripts.sync_github_tracking.source_inventory", return_value=(self.config, self.desired)), \
             patch("scripts.sync_github_tracking.remote_inventory", return_value=(self.milestones, self.issues, self.extra)), \
             redirect_stdout(io.StringIO()), patch("sys.stderr", new_callable=io.StringIO), \
             self.assertRaises(SystemExit):
            main(["audit", "--milestone-number", "6", "--milestone-titles-only"])
        key = "SPEC-022/T015"
        body = f"## Task\n\n{key}\n\n- Source: source\n- Trace: See the parent issue and assurance record.\n"
        self.desired.append({"key": key, "kind": "task", "parent": None, "title": key,
                             "state": "open", "milestone": self.name, "task_text": key, "body": body})
        self.issues[key] = {"number": 999, "milestone": {"number": 6, "title": self.name},
                            "title": key, "state": "open", "body": body}
        _, selected, _, operations = milestone_plan(self.config, self.desired, self.milestones,
                                                    self.issues, self.extra, 6)
        self.assertIn(key, {item["key"] for item in selected})
        self.assertEqual([], [op for op in operations if op.get("key") == key])

    def test_apply_rejects_plan_drift_and_passes_only_scoped_records(self):
        def audit_digest():
            output = io.StringIO()
            with patch("scripts.sync_github_tracking.source_inventory", return_value=(self.config, self.desired)), \
                 patch("scripts.sync_github_tracking.remote_inventory", return_value=(self.milestones, self.issues, self.extra)), \
                 redirect_stdout(output):
                main(["audit", "--milestone-number", "6"])
            return json.loads(output.getvalue())["plan_sha256"]

        digest = audit_digest()
        changed_issues = deepcopy(self.issues)
        changed_issues["SPEC-022/T001"]["title"] = "concurrent remote change"
        for issues in (changed_issues, self.issues):
            with patch("scripts.sync_github_tracking.source_inventory", return_value=(self.config, self.desired)), \
                 patch("scripts.sync_github_tracking.remote_inventory", return_value=(self.milestones, issues, self.extra)), \
                 patch("scripts.sync_github_tracking.subprocess.run", side_effect=[SimpleNamespace(stdout="develop"), SimpleNamespace(stdout="")]), \
                 patch("scripts.sync_github_tracking.apply_plan") as apply, \
                 redirect_stdout(io.StringIO()), patch("sys.stderr", new_callable=io.StringIO):
                if issues is changed_issues:
                    with self.assertRaises(SystemExit):
                        main(["apply", "--milestone-number", "6", "--confirm-repository", "owner/repo",
                              "--plan-sha256", digest])
                    apply.assert_not_called()
                else:
                    self.assertEqual(0, main(["apply", "--milestone-number", "6", "--confirm-repository",
                                              "owner/repo", "--plan-sha256", digest]))
                    _, selected, selected_issues, _ = milestone_plan(self.config, self.desired, self.milestones,
                                                                     self.issues, self.extra, 6)
                    self.assertEqual({item["key"] for item in selected}, set(selected_issues))
                    apply.assert_called_once()
                    args = apply.call_args.args
                    self.assertEqual({item["key"] for item in selected}, {item["key"] for item in args[2]})
                    self.assertEqual(set(selected_issues), set(args[4]))

    def new_spec_fixture(self):
        name = self.name
        spec_key = "SPEC-038"
        desired = [{"key": spec_key, "kind": "spec", "parent": None, "title": "[SPEC-038] Closure",
                    "state": "open", "milestone": name, "body": "spec body"}]
        for idx in range(1, 9):
            key = f"SPEC-038/T{idx:03}"
            task_text = f"Work package {idx}"
            desired.append({"key": key, "kind": "task", "parent": spec_key,
                            "title": f"[SPEC-038 T{idx:03}] {task_text}", "state": "open",
                            "milestone": name, "task_text": task_text,
                            "body": f"## Task\n\n{task_text}\n\n- Source: source\n- Trace: See the parent issue and assurance record.\n"})
        return desired

    def test_new_spec_bootstrap_requires_exact_allowlist_and_plans_only_creates(self):
        desired = self.new_spec_fixture()
        keys = {item["key"] for item in desired}
        with self.assertRaisesRegex(ValueError, "missing for selected"):
            milestone_plan(self.config, desired, self.milestones, {}, self.extra, 6)
        _, _, selected_issues, operations = milestone_plan(
            self.config, desired, self.milestones, {}, self.extra, 6, keys)
        self.assertEqual({}, selected_issues)
        self.assertEqual(9, sum(op["action"] == "create_issue" for op in operations))
        self.assertEqual(8, sum(op["action"] == "link_subissue" for op in operations))
        self.assertTrue(all(op["action"] not in {"update_title", "update_milestone", "set_state"}
                            for op in operations))

    def test_registered_spec038_source_records_can_be_bootstrapped_explicitly(self):
        config, all_desired = source_inventory()
        desired = [item for item in all_desired if item["key"] == "SPEC-038"
                   or item["key"].startswith("SPEC-038/")]
        self.assertTrue(desired)
        name = config["specs"]["038-m4-real-workload-closure"]["milestone"]
        milestone_number = config["milestone_numbers"][name]
        milestones = {name: {"number": milestone_number, "title": name, "state": "open"}}
        allowlist = {item["key"] for item in desired}
        with self.assertRaisesRegex(ValueError, "missing for selected"):
            milestone_plan(config, desired, milestones, {}, self.extra, milestone_number)
        _, _, _, operations = milestone_plan(config, desired, milestones, {}, self.extra,
                                             milestone_number, allowlist)
        self.assertEqual(len(desired), sum(op["action"] == "create_issue" for op in operations))
        self.assertEqual(len(desired) - 1, sum(op["action"] == "link_subissue" for op in operations))

    def test_new_record_allowlist_rejects_unknown_present_and_unselected_keys(self):
        desired = self.new_spec_fixture()
        with self.assertRaisesRegex(ValueError, "unknown source record"):
            milestone_plan(self.config, desired, self.milestones, {}, self.extra, 6, {"SPEC-999/T001"})
        existing = {"SPEC-038": {"number": 400, "milestone": {"number": 6}}}
        with self.assertRaisesRegex(ValueError, "already exists remotely"):
            milestone_plan(self.config, desired, self.milestones, existing, self.extra, 6, {"SPEC-038"})
        other = {"key": "SPEC-001/T001", "kind": "task", "parent": None, "title": "Other",
                 "state": "open", "milestone": self.other, "task_text": "Other", "body": ""}
        with self.assertRaisesRegex(ValueError, "outside milestone"):
            milestone_plan(self.config, [*desired, other], self.milestones, {}, self.extra, 6,
                           {"SPEC-001/T001"})
        with patch("scripts.sync_github_tracking.source_inventory", return_value=(self.config, desired)), \
             redirect_stdout(io.StringIO()), patch("sys.stderr", new_callable=io.StringIO):
            with self.assertRaises(SystemExit):
                main(["audit", "--milestone-number", "6", "--new-record-key", "SPEC-038",
                      "--new-record-key", "SPEC-038"])

    def test_allowlist_is_sorted_in_output_and_bound_to_apply_digest(self):
        desired = self.new_spec_fixture()
        keys = {item["key"] for item in desired}
        output = io.StringIO()
        with patch("scripts.sync_github_tracking.source_inventory", return_value=(self.config, desired)), \
             patch("scripts.sync_github_tracking.remote_inventory",
                   return_value=(self.milestones, {}, self.extra)), redirect_stdout(output):
            self.assertEqual(1, main(["audit", "--milestone-number", "6", *sum(
                (["--new-record-key", key] for key in reversed(sorted(keys))), [])]))
        audited = json.loads(output.getvalue())
        self.assertEqual(sorted(keys), audited["new_record_keys"])
        # A digest from an allowlist that omits one creation cannot authorize this plan.
        altered = {"repository": "owner/repo", "scope": "milestone:6", "milestone_number": 6,
                   "new_record_keys": sorted(keys)[:-1], "operations": audited["operations"]}
        stale_digest = hashlib.sha256(json.dumps(altered, sort_keys=True, ensure_ascii=False,
                                                  separators=(",", ":")).encode("utf-8")).hexdigest()
        with patch("scripts.sync_github_tracking.source_inventory", return_value=(self.config, desired)), \
             patch("scripts.sync_github_tracking.remote_inventory",
                   return_value=(self.milestones, {}, self.extra)), \
             redirect_stdout(io.StringIO()), patch("sys.stderr", new_callable=io.StringIO), \
             self.assertRaises(SystemExit):
            main(["apply", "--milestone-number", "6",
                  *sum((["--new-record-key", key] for key in sorted(keys)), []),
                  "--confirm-repository", "owner/repo", "--plan-sha256", stale_digest])


if __name__ == "__main__":
    unittest.main()
