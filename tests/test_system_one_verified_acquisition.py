# SPDX-License-Identifier: AGPL-3.0-only
"""Actual local Git conformance and refusal tests for the owned fixture lane."""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import unittest
from unittest.mock import patch

from agent_braid import git_process
from agent_braid.git_process import GitCommandBudget
from agent_braid import system_one_verified_acquisition as acquisition
from agent_braid.system_one import digest, thaw


class VerifiedAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.owned = self.root / "owned"
        self.owned.mkdir()
        self.repo = self.owned / "fixture"
        self.repo.mkdir()
        self.scratch = self.root / "scratch"
        self.scratch.mkdir()
        self.checks = []
        self.fixture = json.loads((Path(__file__).parent / "fixtures" /
                                  "system_one_verified_acquisition.json").read_text())
        self.git("init", "--initial-branch=main")
        self.git("config", "user.name", "Fixture")
        self.git("config", "user.email", "fixture@invalid")
        self.git("config", "commit.gpgsign", "false")
        (self.repo / ".owned-native-fixture").write_text("owned synthetic software fixture\n")
        for path, lines in self.fixture["base"].items():
            (self.repo / path).write_text("".join(lines))
        self.git("add", ".")
        self.git("commit", "-m", "base")
        self.base = self.git("rev-parse", "HEAD").decode().strip()
        self.sources = {}
        for name, files in self.fixture["operations"].items():
            self.git("reset", "--hard", self.base)
            self.git("clean", "-fd")
            for path, lines in files.items():
                (self.repo / path).write_text("".join(lines))
            self.git("add", ".")
            self.git("commit", "-m", name)
            self.sources[name] = self.git("rev-parse", "HEAD").decode().strip()
        self.git("reset", "--hard", self.base)
        self.source = self.make_source()

    def git(self, *args):
        env = {"PATH": os.environ["PATH"], "LC_ALL": "C", "GIT_CONFIG_NOSYSTEM": "1",
               "GIT_CONFIG_GLOBAL": os.devnull, "GIT_TERMINAL_PROMPT": "0"}
        return subprocess.run(["git", "-C", str(self.repo), *args], env=env,
                              capture_output=True, check=True).stdout

    def make_source(self):
        declared = {}
        for name, files in self.fixture["operations"].items():
            declared[name] = []
            for path in sorted(files):
                before = (self.git("rev-parse", self.base + ":" + path).decode().strip()
                          if path in self.fixture["base"] else "0" * 40)
                after = self.git("rev-parse", self.sources[name] + ":" + path).decode().strip()
                declared[name].append({"path": path, "before": before, "after": after})
        goal = {entry["path"]: entry["after"] for entries in declared.values() for entry in entries}
        return {"format": "t022-ingress-v1", "executionAuthorization": False,
                "declaredEffects": declared,
                "task": {"request": {"gitAnalysisRequestVersion": "0.1.0-alpha",
                    "repository": str(self.repo), "baseRevision": self.base,
                    "operations": [{"instanceId": name, "attemptId": "attempt-" + name,
                        "source": {"kind": "commit", "revision": oid},
                        "dependencies": [], "uncertainPaths": []}
                        for name, oid in self.sources.items()]},
                    "goal": [{"path": p, "blob": v} for p, v in sorted(goal.items())],
                    "options": {"k0": ["a", "b"], "k1": ["b", "a"], "k2": ["a", "a"], "wait": None},
                    "optionOrder": ["k2", "k0", "wait", "k1"]}}

    def budget(self, **changes):
        args = {"temp_root": self.scratch, "wall_seconds": 60,
                "cancel_event": threading.Event()}
        args.update(changes)
        return GitCommandBudget(**args)

    def checkpoint(self, stage, units):
        self.assertEqual((stage, units), ("acquisition", 0))
        self.checks.append((stage, units))

    def acquire(self, source=None, budget=None, **changes):
        kwargs = {"limits": acquisition._BOUNDS, "git_budget": budget or self.budget(),
                  "remaining_ns": lambda stage: 30_000_000_000,
                  "checkpoint": self.checkpoint}
        kwargs.update(changes)
        return acquisition.acquire(source or self.source, self.owned, **kwargs)

    def inventory(self):
        return {str(p.relative_to(self.repo)): (p.stat().st_mode & 0o777, sha256(p.read_bytes()).hexdigest())
                for p in self.repo.rglob("*") if p.is_file() and not p.is_symlink()}

    def test_exact_observed_snapshot_two_hunks_addition_and_no_mutation(self):
        before, caller = self.inventory(), deepcopy(self.source)
        budget = self.budget()
        started = budget.started_at
        result = self.acquire(budget=budget)
        self.assertEqual(set(result), {"program", "binding", "observedEffects", "declaredEffects", "coverage"})
        self.assertEqual(thaw(result["observedEffects"]), self.source["declaredEffects"])
        self.assertEqual(result["binding"]["snapshotDigest"], digest(result["binding"]["snapshot"]))
        self.assertIs(result["binding"]["executionAuthorization"], False)
        self.assertEqual(result["binding"]["snapshot"]["semanticVersion"], "t024-eof-context-v1")
        self.assertEqual(result["binding"]["snapshot"]["taskDigest"], digest(self.source["task"]))
        self.assertEqual(tuple(result["program"]["plans"]), ("k2", "k0", "wait", "k1"))
        change = result["program"]["ops"]["a"]["changes"][0]
        self.assertEqual(len(change["hunks"]), 2)
        self.assertTrue(change["hunks"][0]["atStart"])
        self.assertTrue(change["hunks"][1]["atEnd"])
        self.assertEqual(change["hunks"][0]["patchLines"][0], "-line00\n")
        self.assertEqual(change["hunks"][0]["patchLines"][1], "+changed00\n")
        addition = result["program"]["ops"]["b"]["changes"][0]["hunks"][0]
        self.assertIsNone(addition["old"])
        self.assertEqual((addition["begin"], addition["end"]), (0, 0))
        self.assertEqual(addition["patchLines"], ("+hello\n", "+world\n"))
        self.assertEqual(thaw(result["coverage"]), {"status": "complete", "paths": ["first.txt", "new.txt"], "operations": ["a", "b"]})
        with self.assertRaises(TypeError):
            result["program"]["files"]["first.txt"] = ()
        self.assertEqual(self.inventory(), before)
        self.assertEqual(self.source, caller)
        self.assertEqual(list(self.scratch.iterdir()), [])
        self.assertEqual(budget.started_at, started)
        self.assertGreater(budget.commands, 10)
        self.assertGreater(budget.output_bytes, 0)
        self.assertGreater(len(self.checks), budget.commands)

    def test_reacquisition_preserves_context_counters_and_command_cap(self):
        budget = self.budget()
        first = self.acquire(budget=budget)
        commands, output, started = budget.commands, budget.output_bytes, budget.started_at
        second = self.acquire(budget=budget)
        self.assertEqual(first, second)
        self.assertEqual(budget.commands, 2 * commands)
        self.assertEqual(budget.output_bytes, 2 * output)
        self.assertEqual(budget.started_at, started)
        budget.max_commands = budget.commands
        with patch.object(git_process.subprocess, "Popen", wraps=subprocess.Popen) as spawn:
            with self.assertRaisesRegex(ValueError, "^work-budget-exceeded$"):
                self.acquire(budget=budget)
        self.assertEqual(spawn.call_count, 0)
        self.assertEqual(budget.commands, 2 * commands + 1)
        self.assertTrue(self.scratch.is_dir())
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_v32_one_child_shared_commands_output_and_cancel(self):
        budget = self.budget(max_commands=1)
        reader = acquisition._Reader(self.repo, budget, lambda s: 1_000_000_000, self.checkpoint)
        started = budget.started_at
        with patch.object(git_process.subprocess, "Popen", wraps=subprocess.Popen) as spawn:
            reader.git("rev-parse", "HEAD")
            with self.assertRaises(git_process.GitCommandLimitExceeded):
                reader.git("rev-parse", "HEAD")
        self.assertEqual(spawn.call_count, 1)
        self.assertEqual(budget.commands, 2)
        self.assertEqual(budget.output_bytes, 41)
        self.assertEqual(budget.started_at, started)
        budget = self.budget(max_output_bytes=41)
        reader = acquisition._Reader(self.repo, budget, lambda s: 1_000_000_000, self.checkpoint)
        reader.git("rev-parse", "HEAD")
        with self.assertRaises(git_process.GitOutputLimitExceeded):
            reader.git("rev-parse", "HEAD")
        self.assertEqual(budget.output_bytes, 41)
        self.assertEqual(budget.commands, 2)
        budget = self.budget()
        self.acquire(budget=budget)
        commands, started = budget.commands, budget.started_at
        budget.cancel_event.set()
        with patch.object(git_process.subprocess, "Popen", wraps=subprocess.Popen) as spawn:
            with self.assertRaisesRegex(ValueError, "^cancelled$"):
                self.acquire(budget=budget)
        self.assertEqual(spawn.call_count, 0)
        self.assertEqual(budget.commands, commands)
        self.assertEqual(budget.started_at, started)
        self.assertTrue(budget.cancel_event.is_set())

    def test_expired_or_cancelled_checkpoint_publishes_nothing(self):
        with patch.object(git_process.subprocess, "Popen", wraps=subprocess.Popen) as spawn:
            with self.assertRaisesRegex(ValueError, "^deadline-exceeded$"):
                self.acquire(remaining_ns=lambda s: 0)
        self.assertEqual(spawn.call_count, 0)
        ticks = []
        def stop(stage, units):
            ticks.append(stage)
            if len(ticks) == 8:
                raise ValueError("cancelled")
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "^cancelled$"):
            self.acquire(checkpoint=stop)
        self.assertEqual(self.inventory(), before)
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_envelope_domain_dependencies_and_goals_refuse_before_git(self):
        variants = []
        def variant(edit):
            value = deepcopy(self.source)
            edit(value)
            variants.append(value)
        variant(lambda s: s.update(executionAuthorization=True))
        variant(lambda s: s.update(confidence=1))
        variant(lambda s: s["task"]["request"].update(baseRevision="main"))
        variant(lambda s: s["task"]["request"].update(baseRevision="0" * 40))
        variant(lambda s: s["task"]["request"]["operations"][0].update(uncertainPaths=["first.txt"]))
        variant(lambda s: s["task"]["request"]["operations"][0].update(dependencies=["b", "b"]))
        variant(lambda s: s["task"]["request"]["operations"][0].update(dependencies=["a"]))
        variant(lambda s: s["task"]["request"]["operations"][0]["source"].update(revision="HEAD"))
        variant(lambda s: s["task"]["request"]["operations"].__setitem__(1, deepcopy(s["task"]["request"]["operations"][0])))
        variant(lambda s: s["task"]["goal"].append(deepcopy(s["task"]["goal"][0])))
        variant(lambda s: s["task"].update(optionOrder=["k0"] * 4))
        for value in variants:
            with self.subTest(value=value), patch.object(acquisition, "run_git") as git:
                with self.assertRaises(ValueError):
                    self.acquire(value)
                git.assert_not_called()
        cyclic = deepcopy(self.source)
        cyclic["task"]["request"]["operations"][0]["dependencies"] = ["b"]
        cyclic["task"]["request"]["operations"][1]["dependencies"] = ["a"]
        with self.assertRaisesRegex(ValueError, "^invalid-ir$"):
            self.acquire(cyclic)
        with self.assertRaisesRegex(ValueError, "^invalid-budget$"):
            self.acquire(limits={**acquisition._BOUNDS, "maxFiles": True})
        with self.assertRaisesRegex(ValueError, "^invalid-budget$"):
            self.acquire(limits={**acquisition._BOUNDS, "hiddenContext": 1})

    def test_declaration_goal_and_missing_object_negatives_preserve_source(self):
        before = self.inventory()
        altered = deepcopy(self.source)
        altered["declaredEffects"]["a"][0]["after"] = "1" * 40
        with self.assertRaisesRegex(ValueError, "^declaration-mismatch$"):
            self.acquire(altered)
        altered = deepcopy(self.source)
        altered["task"]["goal"].pop()
        with self.assertRaisesRegex(ValueError, "^invalid-ir$"):
            self.acquire(altered)
        altered = deepcopy(self.source)
        altered["task"]["request"]["operations"][0]["source"]["revision"] = "1" * 40
        with self.assertRaisesRegex(ValueError, "^source-unavailable$"):
            self.acquire(altered)
        self.assertEqual(self.inventory(), before)

    def test_nonancestor_commit_and_deleted_effect_are_unsupported(self):
        changed = deepcopy(self.source)
        changed["task"]["request"]["baseRevision"] = self.sources["a"]
        changed["task"]["request"]["operations"][0]["source"]["revision"] = self.sources["b"]
        with self.assertRaisesRegex(ValueError, "^source-drift$"):
            self.acquire(changed)
        self.git("reset", "--hard", self.base)
        (self.repo / "first.txt").unlink()
        self.git("add", ".")
        self.git("commit", "-m", "delete")
        changed = deepcopy(self.source)
        changed["task"]["request"]["operations"][0]["source"]["revision"] = self.git("rev-parse", "HEAD").decode().strip()
        before = self.inventory()
        with self.assertRaisesRegex(ValueError, "^unsupported-effect$"):
            self.acquire(changed)
        self.assertEqual(self.inventory(), before)

    def test_owned_scope_marker_symlink_alternates_and_no_private_fallback(self):
        marker = self.repo / ".owned-native-fixture"
        marker.unlink()
        with self.assertRaisesRegex(ValueError, "^source-unavailable$"):
            self.acquire()
        marker.write_text("owned\n")
        link = self.owned / "link"
        link.symlink_to(self.repo, target_is_directory=True)
        changed = deepcopy(self.source)
        changed["task"]["request"]["repository"] = str(link)
        with self.assertRaisesRegex(ValueError, "^source-unavailable$"):
            self.acquire(changed)
        changed["task"]["request"]["repository"] = str(self.root / "missing")
        with self.assertRaisesRegex(ValueError, "^source-unavailable$"):
            self.acquire(changed)
        marker.unlink()
        marker.symlink_to(self.repo / "first.txt")
        with self.assertRaisesRegex(ValueError, "^source-unavailable$"):
            self.acquire()
        marker.unlink()
        marker.write_text("owned\n")
        alternate = self.repo / ".git/objects/info/alternates"
        alternate.write_text(str(self.root) + "\n")
        with self.assertRaisesRegex(ValueError, "^unsupported-effect$"):
            self.acquire()

    def test_actual_unsupported_modes_paths_crlf_and_large_sources(self):
        variants = [("script.txt", b"hello\n", "executable"),
                    ("bad/path.txt", b"hello\n", "file"),
                    ("bad.txt", b"hello\r\n", "file"),
                    ("bad.txt", b"x" * 4097 + b"\n", "file"),
                    ("bad.txt", b"x\0y\n", "file"),
                    ("bad.txt", b"hello", "file"),
                    ("bad.txt", b"\n", "file"),
                    ("bad.txt", b"hello\n", "symlink")]
        for path, body, kind in variants:
            with self.subTest(path=path, kind=kind, body=body[:20]):
                self.git("reset", "--hard", self.base)
                self.git("clean", "-fd")
                target = self.repo / path
                target.parent.mkdir(parents=True, exist_ok=True)
                if kind == "symlink":
                    target.symlink_to("first.txt")
                else:
                    target.write_bytes(body)
                    if kind == "executable":
                        target.chmod(0o755)
                self.git("add", ".")
                self.git("commit", "-m", "unsupported")
                changed = deepcopy(self.source)
                changed["task"]["request"]["operations"][1]["source"]["revision"] = self.git("rev-parse", "HEAD").decode().strip()
                before = self.inventory()
                with self.assertRaisesRegex(ValueError, "^unsupported-effect$"):
                    self.acquire(changed)
                self.assertEqual(self.inventory(), before)

    def test_three_four_operations_and_multifile_effects_are_complete(self):
        self.fixture["operations"]["a"]["other.txt"] = ["additional effect\n"]
        self.fixture["operations"]["c"] = {"third.txt": ["third effect\n"]}
        for count in (3, 4):
            if count == 4:
                self.fixture["operations"]["d"] = {"fourth.txt": ["fourth effect\n"]}
            self.sources = {}
            for name, files in self.fixture["operations"].items():
                self.git("reset", "--hard", self.base)
                self.git("clean", "-fd")
                for path, lines in files.items():
                    (self.repo / path).write_text("".join(lines))
                self.git("add", ".")
                self.git("commit", "-m", name)
                self.sources[name] = self.git("rev-parse", "HEAD").decode().strip()
            self.source = self.make_source()
            # Offered candidates may be incomplete or repeated; acquire must not
            # silently select, discard or repair them.
            self.source["task"]["options"]["k0"] = list(self.sources)
            self.source["task"]["options"]["k1"] = list(reversed(self.sources))
            self.source["task"]["request"]["operations"][-1]["dependencies"] = ["a"]
            before = self.inventory()
            result = self.acquire()
            self.assertEqual(len(result["program"]["ops"]), count)
            self.assertEqual(len(result["program"]["ops"]["a"]["changes"]), 2)
            self.assertEqual(len(result["program"]["files"]), count + 1)
            self.assertEqual(result["program"]["ops"][list(self.sources)[-1]]["dependencies"], ("a",))
            self.assertEqual(thaw(result["observedEffects"]), self.source["declaredEffects"])
            self.assertEqual(self.inventory(), before)

    def test_goal_unknown_blob_is_bound_not_guessed_or_selected(self):
        changed = deepcopy(self.source)
        changed["task"]["goal"][0]["blob"] = "1" * 40
        result = self.acquire(changed)
        self.assertEqual(result["program"]["goal"]["first.txt"], "1" * 40)
        self.assertNotIn("choice", result)
        self.assertNotIn("status", result)
        self.assertNotEqual(result["binding"]["snapshotDigest"], self.acquire()["binding"]["snapshotDigest"])

    def test_checkpoint_post_work_suppresses_late_snapshot(self):
        ticks = []
        self.acquire(checkpoint=lambda stage, units: ticks.append((stage, units)))
        remaining = len(ticks)
        def stop(stage, units):
            nonlocal remaining
            remaining -= 1
            if remaining == 0:
                raise ValueError("deadline-exceeded")
        with self.assertRaisesRegex(ValueError, "^deadline-exceeded$"):
            self.acquire(checkpoint=stop)
        self.assertTrue(self.scratch.is_dir())
        self.assertEqual(list(self.scratch.iterdir()), [])

    def test_hostile_diff_config_cannot_execute_and_format_is_pinned(self):
        sentinel = self.root / "must-not-exist"
        self.git("config", "diff.external", "touch " + str(sentinel))
        self.git("config", "diff.context", "0")
        self.git("config", "diff.algorithm", "patience")
        self.git("config", "diff.noprefix", "true")
        self.git("config", "color.ui", "always")
        before = self.inventory()
        result = self.acquire()
        self.assertEqual(len(result["program"]["ops"]["a"]["changes"][0]["hunks"]), 2)
        self.assertFalse(sentinel.exists())
        self.assertEqual(self.inventory(), before)


if __name__ == "__main__":
    unittest.main()
