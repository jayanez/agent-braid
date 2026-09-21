# SPDX-License-Identifier: AGPL-3.0-only

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from scripts.run_m1_clean_room import _clean_environment, _git, _version
from scripts.validate_m1_closure import (
    INPUTS,
    POST_FREEZE_PATHS,
    REPRODUCTION_VERSION,
    REQUIRED_OBSERVATIONS,
    validate_candidate_unchanged,
    validate_founder_review,
    validate_reproduction,
)


class M1ClosureTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        for relative in INPUTS:
            path = self.root / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(f"{relative}\n")
        software = {
            "benchmarkVersion": "software-m1-v2", "falseSafeCount": 0,
            "conditionBoundScenarioCount": 1,
        }
        git = {
            "benchmarkVersion": "git-m1-v2", "falseSafeCount": 0, "coverage": 1.0,
            "baselineComparisons": [
                {"id": name, "measuredHere": True, "gitCommandCount": 1,
                 "elapsedNanoseconds": 1, "results": [{"id": str(i)} for i in range(6)]}
                for name in ("file-overlap", "git-merge")
            ],
        }
        self.record = {
            "recordVersion": REPRODUCTION_VERSION,
            "capturedAt": "2026-09-18T00:00:00+00:00",
            "reviewedCommit": "a" * 40, "tree": "b" * 40, "platform": "test",
            "python": "3.12.1", "git": "git version 2.50.1",
            "cleanRoom": {"freshClone": True, "freshEnvironment": True,
                          "pipCacheDisabled": True, "initialStatus": "", "finalStatus": ""},
            "operator": {"automation": "Codex", "authorization": "founder",
                         "supervisor": "founder", "independent": False},
            "inputs": {
                relative: hashlib.sha256((self.root / relative).read_bytes()).hexdigest()
                for relative in INPUTS
            },
            "observations": [],
            "benchmarks": {"software": software, "git": git},
            "independentValidation": "pending", "limits": ["bounded"],
        }
        for identifier, suffix in REQUIRED_OBSERVATIONS:
            command = (f"{suffix} {'a' * 40}" if identifier == "whitespace"
                       else f"/tmp/venv/python {suffix}")
            stdout = ""
            if identifier == "software-benchmark":
                stdout = json.dumps(software)
            elif identifier == "git-benchmark":
                stdout = json.dumps(git)
            self.record["observations"].append(
                {"command": command, "exitCode": 0, "stdout": stdout, "stderr": ""}
            )
        feature = self.root / "specs/007-m1-closure"
        feature.mkdir(parents=True)
        (feature / "reproduction.json").write_text(json.dumps(self.record))

    def tearDown(self):
        self.temporary.cleanup()

    def write(self, record):
        (self.root / "specs/007-m1-closure/reproduction.json").write_text(json.dumps(record))

    def git_result(self, args, **_kwargs):
        result = Mock(returncode=0, stdout=b"", stderr=b"")
        if args[1] == "rev-parse":
            result.stdout = ("b" * 40 + "\n").encode()
        elif args[1] == "show":
            relative = args[2].split(":", 1)[1]
            result.stdout = (self.root / relative).read_bytes()
        return result

    @patch("scripts.validate_m1_closure.subprocess.run")
    def test_valid_internal_reproduction(self, run):
        run.side_effect = self.git_result
        self.assertEqual(validate_reproduction(self.root)["independentValidation"], "pending")

    def test_clean_room_inventory_includes_pinned_multi_agent_spec_kit_gates(self):
        identifiers = [identifier for identifier, _ in REQUIRED_OBSERVATIONS]
        self.assertIn("spec-kit-render", identifiers)
        self.assertIn("spec-kit-integration", identifiers)
        self.assertIn("m1-radar", identifiers)
        self.assertIn("requirements-speckit.txt", INPUTS)
        self.assertIn("scripts/test_spec_kit_integration.py", INPUTS)

    @patch("scripts.validate_m1_closure.subprocess.run")
    def test_rejects_incompatible_dirty_or_failed_reproduction(self, run):
        run.side_effect = self.git_result
        for mutation in ("python", "clean", "observation"):
            record = deepcopy(self.record)
            if mutation == "python":
                record["python"] = "3.9.6"
            elif mutation == "clean":
                record["cleanRoom"]["finalStatus"] = "dirty"
            else:
                record["observations"][0]["exitCode"] = 1
            self.write(record)
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                validate_reproduction(self.root)

    @patch("scripts.validate_m1_closure.subprocess.run")
    def test_rejects_incomplete_environment_metadata(self, run):
        run.side_effect = self.git_result
        mutations = []
        for field, value in (
            ("capturedAt", "2026-09-18T00:00:00"),
            ("platform", ""),
            ("git", ""),
            ("limits", []),
        ):
            record = deepcopy(self.record)
            record[field] = value
            mutations.append((field, record))
        for field, record in mutations:
            self.write(record)
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_reproduction(self.root)

    @patch("scripts.validate_m1_closure.subprocess.run")
    def test_rejects_stale_hash_and_unmeasured_baseline(self, run):
        run.side_effect = self.git_result
        record = deepcopy(self.record)
        record["inputs"][INPUTS[0]] = "0" * 64
        self.write(record)
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            validate_reproduction(self.root)
        record = deepcopy(self.record)
        record["benchmarks"]["git"]["baselineComparisons"][0]["measuredHere"] = False
        for observation in record["observations"]:
            if observation["command"].endswith("scripts/run_git_benchmark.py"):
                observation["stdout"] = json.dumps(record["benchmarks"]["git"])
        self.write(record)
        with self.assertRaisesRegex(ValueError, "measurements"):
            validate_reproduction(self.root)

    @patch("scripts.validate_m1_closure.subprocess.run")
    def test_rejects_missing_inputs_commands_tree_and_benchmark_binding(self, run):
        run.side_effect = self.git_result
        mutations = []
        missing_input = deepcopy(self.record)
        missing_input["inputs"].pop(INPUTS[0])
        mutations.append((missing_input, "input inventory"))
        missing_command = deepcopy(self.record)
        missing_command["observations"].pop(1)
        mutations.append((missing_command, "observations"))
        ineffective_whitespace = deepcopy(self.record)
        ineffective_whitespace["observations"][-1]["command"] = "git diff --check"
        mutations.append((ineffective_whitespace, "observations"))
        wrong_tree = deepcopy(self.record)
        wrong_tree["tree"] = "c" * 40
        mutations.append((wrong_tree, "tree"))
        detached_benchmark = deepcopy(self.record)
        detached_benchmark["benchmarks"]["software"]["falseSafeCount"] = 1
        mutations.append((detached_benchmark, "does not match"))
        for record, message in mutations:
            self.write(record)
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                validate_reproduction(self.root)

    def test_clean_room_environment_drops_python_and_git_overrides(self):
        env = _clean_environment({
            "PATH": "/usr/bin", "HTTPS_PROXY": "https://proxy.invalid",
            "PYTHONPATH": "/host/code", "PYTHONHOME": "/host/python",
            "GIT_DIR": "/host/repository/.git", "GIT_WORK_TREE": "/host/repository",
            "GIT_CONFIG_GLOBAL": "/host/gitconfig",
        })
        self.assertEqual(env["PATH"], "/usr/bin")
        self.assertEqual(env["HTTPS_PROXY"], "https://proxy.invalid")
        for name in ("PYTHONPATH", "PYTHONHOME", "GIT_DIR", "GIT_WORK_TREE"):
            self.assertNotIn(name, env)
        self.assertEqual(env["GIT_CONFIG_GLOBAL"], os.devnull)

    @patch("scripts.run_m1_clean_room.subprocess.run")
    def test_clean_room_helpers_apply_the_sanitized_environment(self, run):
        env = _clean_environment({"PATH": "/usr/bin", "PYTHONPATH": "/host/code"})
        run.return_value = Mock(returncode=0, stdout="", stderr="")
        _git(self.root, "status", env=env)
        self.assertIs(run.call_args.kwargs["env"], env)
        run.return_value = Mock(returncode=0, stdout="3.12.1\n", stderr="")
        self.assertEqual(_version(Path("/python"), env)[0], "3.12.1")
        self.assertIs(run.call_args.kwargs["env"], env)

    def test_rejects_incomplete_founder_review(self):
        feature = self.root / "specs/007-m1-closure"
        review = {
            "recordVersion": "0.1.0", "feature": "M1", "reviewedCommit": "a" * 40,
            "reviewer": {"name": "Founder", "role": "founder"},
            "conflictsOfInterest": "founder",
            "scientificReview": {"decision": "approved", "date": "2026-09-18", "rationale": "bounded"},
            "milestoneClosure": {"decision": "pending", "date": "", "rationale": ""},
            "independentValidation": "pending", "evidence": [], "limits": ["bounded"],
        }
        (feature / "founder-review.json").write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, "milestoneClosure"):
            validate_founder_review(self.root, "a" * 40)
        review["milestoneClosure"] = {
            "decision": "approved", "date": "2026-09-18", "rationale": "bounded"
        }
        (feature / "founder-review.json").write_text(json.dumps(review))
        with self.assertRaisesRegex(ValueError, "evidence inventory"):
            validate_founder_review(self.root, "a" * 40)

    @patch("scripts.validate_m1_closure.validate_closure_anchor")
    def test_rejects_implementation_or_authority_changes_after_review(self, anchor):
        anchor.side_effect = ValueError("protected closure record changed")
        with self.assertRaisesRegex(ValueError, "protected closure record changed"):
            validate_candidate_unchanged(self.root, "a" * 40)

    @patch("scripts.validate_m1_closure.validate_closure_anchor")
    def test_candidate_gate_allows_only_declared_post_freeze_records(self, anchor):
        anchor.return_value = {"candidateCommit": "a" * 40}
        validate_candidate_unchanged(self.root, "a" * 40)
        anchor.assert_called_once_with(self.root, "M1", "a" * 40)

    @patch("scripts.validate_m1_closure.validate_closure_anchor")
    def test_rejects_candidate_outside_closure_history(self, anchor):
        anchor.side_effect = ValueError("closure commit is not an ancestor")
        with self.assertRaisesRegex(ValueError, "not an ancestor"):
            validate_candidate_unchanged(self.root, "a" * 40)
