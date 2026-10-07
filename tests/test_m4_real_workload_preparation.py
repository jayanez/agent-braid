# SPDX-License-Identifier: AGPL-3.0-only
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import m4_real_workload as workload
from scripts import prepare_m4_real_workload as command


class SyntheticSource:
    def __init__(self, root: Path):
        self.root = root
        self._git("init", "--quiet")
        self._git("config", "user.name", "Synthetic Fixture")
        self._git("config", "user.email", "fixture@example.invalid")
        (root / "base.txt").write_text("base\n")
        self._commit("base")
        self.base = self._git("rev-parse", "HEAD")
        self._git("checkout", "-b", "op-a", self.base)
        (root / "a.txt").write_text("operation a\n")
        self._commit("operation a")
        self.a = self._git("rev-parse", "HEAD")
        self._git("checkout", "-b", "op-b", self.base)
        (root / "b.txt").write_text("operation b\n")
        self._commit("operation b")
        self.b = self._git("rev-parse", "HEAD")
        self._git("checkout", "--detach", self.base)

    def _git(self, *args: str) -> str:
        return subprocess.check_output(["git", "-C", str(self.root), *args],
                                      stderr=subprocess.PIPE).decode().strip()

    def _commit(self, message: str) -> None:
        self._git("add", "--all")
        self._git("commit", "--quiet", "-m", message)


class M4RealWorkloadPreparationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="m4-real-prep-test-")
        self.root = Path(self.temporary.name)
        self.source_dir = self.root / "source"
        self.source_dir.mkdir()
        self.source = SyntheticSource(self.source_dir)
        self.candidate = self.root / "candidate"
        self.candidate.mkdir()
        self.output_dir = self.root / "external"
        self.output_dir.mkdir()
        self.namespace = self.output_dir / "trial-space"
        self._bind_fixture()

    def tearDown(self):
        self.temporary.cleanup()

    def _bind_fixture(self):
        a_id, b_id = "synthetic-operation-a", "synthetic-operation-b"
        commits = {a_id: self.source.a, b_id: self.source.b}
        seed = f"synthetic-spec038|base={self.source.base}|a={self.source.a}|b={self.source.b}"
        seed_hash = hashlib.sha256(seed.encode()).hexdigest()
        self.commits = commits
        self.seed = seed
        self.seed_hash = seed_hash

    def _prepare(self):
        state = {"candidateCommit": "1" * 40, "candidateInputs": {"synthetic": "d" * 64}}
        with patch.multiple(workload, ROOT=self.candidate, BASE=self.source.base,
                            COMMITS=self.commits, SEED=self.seed, SEED_SHA256=self.seed_hash,
                            PREPARATION_INPUTS=("synthetic",),
                            APPROVED_SOURCE_RIGHTS_SHA256="a" * 64,
                            APPROVED_PROTOCOL_SHA256="b" * 64,
                            APPROVAL_RECEIPT_SHA256="c" * 64), \
             patch.object(workload, "_candidate_state", return_value=state), \
             patch.object(workload, "_approved_receipt", return_value={"sha256": "c" * 64}), \
             patch.object(workload, "_harness_input_hashes", return_value={"synthetic": "d" * 64}):
            return workload.prepare_workload(self.source_dir, self.namespace, self.root / "unused-receipt")

    def _synthetic_manifest(self):
        source_repository = str(self.source_dir.resolve())
        order_ops = {
            "synthetic-operation-a": {"instanceId": "synthetic-operation-a", "attemptId": "spec038-v1-synthetic-operation-a",
                                       "source": {"kind": "commit", "revision": self.source.a}, "dependencies": [],
                                       "uncertainPaths": [], "declaredWrites": ["a.txt"]},
            "synthetic-operation-b": {"instanceId": "synthetic-operation-b", "attemptId": "spec038-v1-synthetic-operation-b",
                                       "source": {"kind": "commit", "revision": self.source.b}, "dependencies": [],
                                       "uncertainPaths": [], "declaredWrites": ["b.txt"]},
        }
        tree = self.source._git("rev-parse", self.source.base + "^{tree}")
        runtime = {}
        replay = {}
        for order, identifiers in (("AB", ["synthetic-operation-a", "synthetic-operation-b"]),
                                   ("BA", ["synthetic-operation-b", "synthetic-operation-a"])):
            runtime[order] = {"gitRuntimeRequestVersion": "0.1.0-alpha", "repository": source_repository,
                              "baseRevision": self.source.base,
                              "operations": [order_ops[key] for key in sorted(order_ops)],
                              "order": identifiers, "expectedFinalTree": tree}
            replay[order] = {"gitAnalysisRequestVersion": "0.1.0-alpha", "repository": source_repository,
                             "baseRevision": self.source.base,
                             "operations": [{key: value for key, value in row.items() if key != "declaredWrites"}
                                            for row in runtime[order]["operations"]]}
        payload = {
            "version": "spec038-real-workload-preparation-v1", "candidateCommit": "1" * 40,
            "candidateInputs": {"synthetic": "d" * 64}, "harnessInputHashes": {"synthetic": "d" * 64},
            "sourceRepository": source_repository, "sourceFingerprint": workload.source_fingerprint(self.source_dir),
            "sourceRightsApproval": {"candidateSha256": "a" * 64, "receiptSha256": "c" * 64,
                                     "scope": "local-preparation-and-evaluation-preparation", "record": "external exact approval receipt"},
            "protocolApproval": {"candidateSha256": "b" * 64, "receiptSha256": "c" * 64},
            "captureAuthorization": False, "m4Acceptance": False,
            "seed": self.seed, "seedSha256": self.seed_hash,
            "operations": [
                {"operationId": key, "sourceCommit": commit, "changedPaths": 1, "changedBytes": 20,
                 "dependencies": [], "paths": ["a.txt" if key == "synthetic-operation-a" else "b.txt"],
                 "patchSha256": "sha256:" + "e" * 64, "tree": self.source._git("rev-parse", commit + "^{tree}"),
                 "blobTransitions": [{"path": "a.txt" if key == "synthetic-operation-a" else "b.txt",
                                      "status": "A", "beforeMode": "000000", "afterMode": "100644",
                                      "beforeBlob": "0" * 40, "afterBlob": "f" * 40}]}
                for key, commit in self.commits.items()],
            "expectedFinalTrees": {"AB": tree, "BA": tree},
            "expectedStepTrees": {
                "AB": [{"operationId": "synthetic-operation-a", "inputTree": tree, "outputTree": tree},
                       {"operationId": "synthetic-operation-b", "inputTree": tree, "outputTree": tree}],
                "BA": [{"operationId": "synthetic-operation-b", "inputTree": tree, "outputTree": tree},
                       {"operationId": "synthetic-operation-a", "inputTree": tree, "outputTree": tree}],
            }, "slots": workload._slots(self.namespace.parent.resolve() / self.namespace.name),
            "dispatchBudgetMinutes": 45, "treatmentDeadlineSeconds": 360,
            "runtimeCaps": {"operations": 4, "changedPaths": 16, "patchBytes": 262144,
                            "wallSeconds": 60, "gitCommands": 256, "outputBytes": 8388608,
                            "commandOutputBytes": 2097152, "scratchBytes": 67108864,
                            "workers": 4, "sourcePromotion": False},
            "exclusions": [], "runtimeInputs": runtime, "replayInputs": replay,
        }
        return workload._canonical(payload) + b"\n"

    def test_static_admission_builds_exact_20_slots_without_allocating_treatments(self):
        raw = self._prepare()
        manifest = self._validate_with_fixture_ids(raw)
        self.assertEqual(len(manifest["slots"]), 20)
        self.assertEqual([slot["globalPairDispatch"] for slot in manifest["slots"]][::2], list(range(1, 11)))
        self.assertEqual({slot["mode"] for slot in manifest["slots"]}, {"serial", "parallel"})
        self.assertEqual(manifest["captureAuthorization"], False)
        self.assertEqual(manifest["m4Acceptance"], False)
        self.assertEqual(set(manifest["expectedFinalTrees"]), {"AB", "BA"})
        self.assertEqual(manifest["expectedFinalTrees"]["AB"], manifest["expectedFinalTrees"]["BA"])
        self.assertFalse(any(Path(slot["runPath"]).exists() for slot in manifest["slots"]))
        self.assertFalse(any(Path(slot["grantPath"]).exists() for slot in manifest["slots"]))
        self.assertEqual({row["changedPaths"] for row in manifest["operations"]}, {1})

    def test_verifier_is_bound_as_a_harness_input(self):
        relative = "scripts/verify_m4_real_workload.py"
        self.assertIn(relative, workload.PREPARATION_INPUTS)
        hashes = workload._harness_input_hashes()
        self.assertEqual(hashes[relative], hashlib.sha256(
            (workload.ROOT / relative).read_bytes()).hexdigest())

    def _validate_with_fixture_ids(self, raw):
        with patch.multiple(workload, BASE=self.source.base, COMMITS=self.commits,
                            PREPARATION_INPUTS=("synthetic",),
                            SEED=self.seed, SEED_SHA256=self.seed_hash,
                            APPROVED_SOURCE_RIGHTS_SHA256="a" * 64,
                            APPROVED_PROTOCOL_SHA256="b" * 64,
                            APPROVAL_RECEIPT_SHA256="c" * 64):
            return workload.validate_manifest(raw)

    def test_manifest_requires_canonical_bytes_and_exact_schedule(self):
        raw = self._synthetic_manifest()
        with patch.multiple(workload, ROOT=self.candidate, BASE=self.source.base, COMMITS=self.commits,
                            SEED=self.seed, SEED_SHA256=self.seed_hash, PREPARATION_INPUTS=("synthetic",),
                            APPROVED_SOURCE_RIGHTS_SHA256="a" * 64,
                            APPROVED_PROTOCOL_SHA256="b" * 64,
                            APPROVAL_RECEIPT_SHA256="c" * 64):
            with self.assertRaisesRegex(workload.InvalidRealWorkload, "canonical"):
                workload.validate_manifest(raw.replace(b"{", b"{ ", 1))
            value = workload.validate_manifest(raw)
            value["slots"].pop()
            value.pop("manifestSha256")
            with self.assertRaisesRegex(workload.InvalidRealWorkload, "20 treatment slots"):
                workload.validate_manifest(workload._canonical(value) + b"\n")

    def test_changed_source_identity_and_existing_private_paths_are_refused(self):
        raw = self._synthetic_manifest()
        with patch.multiple(workload, BASE=self.source.base, COMMITS=self.commits,
                            SEED=self.seed, SEED_SHA256=self.seed_hash,
                            PREPARATION_INPUTS=("synthetic",),
                            APPROVED_SOURCE_RIGHTS_SHA256="a" * 64,
                            APPROVED_PROTOCOL_SHA256="b" * 64,
                            APPROVAL_RECEIPT_SHA256="c" * 64):
            value = workload.validate_manifest(raw)
            slot = value["slots"][0]
            changed = dict(value)
            changed["slots"] = [dict(row) for row in value["slots"]]
            changed["operations"] = [dict(row) for row in value["operations"]]
            changed["operations"][0]["sourceCommit"] = "f" * 40
            self.assert_refuses_rehashed(changed, "source commit identity")
            changed = dict(value)
            changed["slots"] = [dict(row) for row in value["slots"]]
            changed["slots"][0]["runPath"] = str(Path(value["sourceRepository"]) / "private-run")
            changed["slots"][0]["grantPath"] = changed["slots"][0]["runPath"] + ".grants"
            self.assert_refuses_rehashed(changed, "inside source")

    def test_destinations_inside_candidate_or_through_symlink_ancestor_are_refused(self):
        with patch.multiple(workload, ROOT=self.candidate, BASE=self.source.base, COMMITS=self.commits,
                            SEED=self.seed, SEED_SHA256=self.seed_hash, PREPARATION_INPUTS=("synthetic",),
                            APPROVED_SOURCE_RIGHTS_SHA256="a" * 64,
                            APPROVED_PROTOCOL_SHA256="b" * 64,
                            APPROVAL_RECEIPT_SHA256="c" * 64):
            value = workload.validate_manifest(self._synthetic_manifest())
            changed = dict(value)
            changed.pop("manifestSha256", None)
            changed["slots"] = [dict(row) for row in value["slots"]]
            changed["slots"][0]["runPath"] = str(self.candidate.resolve() / "private-run")
            changed["slots"][0]["grantPath"] = changed["slots"][0]["runPath"] + ".grants"
            with self.assertRaisesRegex(workload.InvalidRealWorkload, "inside source or candidate"):
                workload.validate_manifest(workload._canonical(changed) + b"\n")

            alias = self.root / "external-alias"
            alias.symlink_to(self.output_dir, target_is_directory=True)
            changed["slots"][0]["runPath"] = str(alias / "private-run")
            changed["slots"][0]["grantPath"] = changed["slots"][0]["runPath"] + ".grants"
            with self.assertRaisesRegex(workload.InvalidRealWorkload, "symlink or path aliases"):
                workload.validate_manifest(workload._canonical(changed) + b"\n")
            self.assertFalse((self.candidate.resolve() / "private-run").exists())
            self.assertFalse((self.candidate.resolve() / "private-run.grants").exists())
            self.assertFalse((self.output_dir / "private-run").exists())
            self.assertFalse((self.output_dir / "private-run.grants").exists())

    def assert_refuses_rehashed(self, value, message):
        value = dict(value)
        value.pop("manifestSha256", None)
        with self.assertRaisesRegex(workload.InvalidRealWorkload, message):
            workload.validate_manifest(workload._canonical(value) + b"\n")

    def test_runtime_input_accessor_binds_only_existing_slot(self):
        raw = self._synthetic_manifest()
        with patch.multiple(workload, BASE=self.source.base, COMMITS=self.commits,
                            SEED=self.seed, SEED_SHA256=self.seed_hash,
                            PREPARATION_INPUTS=("synthetic",),
                            APPROVED_SOURCE_RIGHTS_SHA256="a" * 64,
                            APPROVED_PROTOCOL_SHA256="b" * 64,
                            APPROVAL_RECEIPT_SHA256="c" * 64):
            value = workload.validate_manifest(raw)
            selected = value["slots"][0]
            payload = workload.runtime_inputs_for_slot(value, selected)
            self.assertEqual(payload["runtimeRequest"]["order"], ["synthetic-operation-a", "synthetic-operation-b"])
            forged = dict(selected, runPath=selected["runPath"] + "-changed")
            with self.assertRaisesRegex(workload.InvalidRealWorkload, "not bound"):
                workload.runtime_inputs_for_slot(value, forged)

    def test_source_fingerprint_disables_fsmonitor_and_ignores_ambient_git_redirects(self):
        marker = self.root / "fsmonitor-was-run"
        hook = self.root / "fsmonitor-hook"
        hook.write_text(f"#!/bin/sh\ntouch {marker}\nprintf 'token'\n")
        hook.chmod(0o755)
        self.source._git("config", "core.fsmonitor", str(hook))
        index = self.source_dir / ".git" / "index"
        before = hashlib.sha256(index.read_bytes()).hexdigest()
        expected_patch = subprocess.check_output(
            ["git", "-C", str(self.source_dir), "--no-replace-objects", "-c",
             "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "diff", "--binary",
             "--no-ext-diff", "--no-textconv", "--no-renames", self.source.base,
             self.source.a, "--"], env=workload._safe_git_environment())
        other = self.root / "other"
        other.mkdir()
        subprocess.run(["git", "init", "--quiet", str(other)], check=True)
        with patch.dict(os.environ, {"GIT_DIR": str(other / ".git"),
                                     "GIT_WORK_TREE": str(other),
                                     "GIT_CONFIG_COUNT": "1",
                                     "GIT_CONFIG_KEY_0": "core.fsmonitor",
                                     "GIT_CONFIG_VALUE_0": str(hook)}, clear=False):
            fingerprint = workload.source_fingerprint(self.source_dir)
            patch_bytes = workload._git_bytes(self.source_dir, "diff", "--binary", "--no-renames",
                                               self.source.base, self.source.a, "--")
        after = hashlib.sha256(index.read_bytes()).hexdigest()
        self.assertEqual(fingerprint["repository"], str(self.source_dir.resolve()))
        self.assertEqual(before, after)
        self.assertFalse(marker.exists())
        self.assertEqual(patch_bytes, expected_patch)

    def test_cli_explicit_capture_flags_are_refused_before_input_access(self):
        for flag in ("--run", "--execute", "--registered"):
            self.assertEqual(command.main([flag]), 2)

    def test_approval_receipt_scope_and_bytes_are_exact(self):
        with tempfile.NamedTemporaryFile() as file:
            file.write(b'{"decision":"approved-implementation-and-evaluation-preparation-only"}')
            file.flush()
            with self.assertRaisesRegex(workload.InvalidRealWorkload, "receipt bytes differ"):
                workload._approved_receipt(Path(file.name))


if __name__ == "__main__":
    unittest.main()
