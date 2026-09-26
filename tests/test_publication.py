# SPDX-License-Identifier: AGPL-3.0-only
"""Publication-provenance acceptance tests for feature 009."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from scripts.closure_anchors import validate_closure_anchor
from scripts.create_public_export import create_export
from scripts.publication import (
    ADDENDUM, MANIFEST, canonical_manifest, redact_local_paths,
    root_manifest_payload, validate_addendum, validate_portable_root,
)
from scripts.validate_publication import (
    PUBLIC_INPUTS,
    PUBLIC_OBSERVATIONS,
    validate_cutover_pending,
    validate_public_reproduction,
)


GIT_ENV = {
    **os.environ,
    "GIT_AUTHOR_NAME": "Publication Test",
    "GIT_AUTHOR_EMAIL": "publication@example.invalid",
    "GIT_COMMITTER_NAME": "Publication Test",
    "GIT_COMMITTER_EMAIL": "publication@example.invalid",
}


def git(root: Path, *args: str) -> str:
    process = subprocess.run(
        ["git", *args], cwd=root, env=GIT_ENV, text=True,
        capture_output=True, check=False,
    )
    if process.returncode:
        raise AssertionError(process.stderr or process.stdout)
    return process.stdout.strip()


def write(path: Path, value: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(value, encoding="utf-8")


def commit(root: Path, message: str) -> str:
    git(root, "add", "-A")
    git(root, "commit", "-m", message)
    return git(root, "rev-parse", "HEAD")


class PublicationTests(unittest.TestCase):
    def test_closure_anchors_bound_interval_not_moving_head(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-b", "main")
            write(root / "protected.txt", "candidate\n")
            candidate = commit(root, "candidate")
            write(root / "protected.txt", "closure\n")
            closure = commit(root, "closure")
            closure_tree = git(root, "rev-parse", f"{closure}^{{tree}}")
            checksum = hashlib.sha256((root / "protected.txt").read_bytes()).hexdigest()
            write(root / "later.txt", "later feature\n")
            commit(root, "later")
            anchor = {
                "candidateCommit": candidate,
                "closureCommit": closure,
                "closureTree": closure_tree,
                "changedPaths": ["protected.txt"],
                "protectedPaths": {"protected.txt": checksum},
            }
            write(root / "docs/releases/closure-anchors.json", json.dumps({
                "recordVersion": "0.1.0",
                "milestones": {"M0": anchor, "M0.5": anchor, "M1": anchor},
            }))
            commit(root, "anchor registry")
            validate_closure_anchor(root, "M0", candidate)
            write(root / "protected.txt", "altered\n")
            with self.assertRaisesRegex(ValueError, "protected closure record changed"):
                validate_closure_anchor(root, "M0", candidate)

    def test_export_is_deterministic_and_rejects_unsafe_inputs(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            source.mkdir()
            git(source, "init", "-b", "main")
            local_fixture = "/" + "Users/test/private/repo"
            write(source / "README.md", f"portable {local_fixture}\n")
            write(source / "specs/001-example/spec.md", "# Example\n")
            write(
                source / "specs/001-example/evidence.json",
                json.dumps({"runner": f"{local_fixture}/.venv/bin/python"}) + "\n",
            )
            source_evidence_hash = hashlib.sha256(
                (source / "specs/001-example/evidence.json").read_bytes()
            ).hexdigest()
            write(
                source / "specs/001-example/assurance.json",
                json.dumps({"evidenceSha256": source_evidence_hash}) + "\n",
            )
            source_assurance_hash = hashlib.sha256(
                (source / "specs/001-example/assurance.json").read_bytes()
            ).hexdigest()
            write(
                source / "specs/001-example/index.json",
                json.dumps({"assuranceSha256": source_assurance_hash}) + "\n",
            )
            exact = commit(source, "source")
            first, second = base / "first", base / "second"
            with mock.patch("scripts.create_public_export.ROOT", source):
                one = create_export(exact, first)
                two = create_export(exact, second)
                self.assertEqual(one, two)
                self.assertEqual((first / MANIFEST).read_bytes(), (second / MANIFEST).read_bytes())
                self.assertEqual(
                    (first / "README.md").read_text(),
                    "portable ${LOCAL_PATH}\n",
                )
                self.assertEqual(one["transformations"][0]["path"], "README.md")
                self.assertIn("local-path-redaction", one["transformations"][0]["rules"])
                published_evidence_hash = hashlib.sha256(
                    (first / "specs/001-example/evidence.json").read_bytes()
                ).hexdigest()
                self.assertEqual(
                    json.loads(
                        (first / "specs/001-example/assurance.json").read_text()
                    )["evidenceSha256"],
                    published_evidence_hash,
                )
                assurance_transform = next(
                    item for item in one["transformations"]
                    if item["path"] == "specs/001-example/assurance.json"
                )
                self.assertEqual(
                    assurance_transform["rules"], ["transformed-digest-rebinding"]
                )
                published_assurance_hash = hashlib.sha256(
                    (first / "specs/001-example/assurance.json").read_bytes()
                ).hexdigest()
                self.assertEqual(
                    json.loads(
                        (first / "specs/001-example/index.json").read_text()
                    )["assuranceSha256"],
                    published_assurance_hash,
                )
                with self.assertRaisesRegex(ValueError, "exact 40-character"):
                    create_export(exact[:12], base / "short")
                with self.assertRaisesRegex(ValueError, "outside the source"):
                    create_export(exact, source / "export")

    def test_portable_validation_requires_root_manifest_and_reports_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "source"
            source.mkdir()
            git(source, "init", "-b", "main")
            local_fixture = "/" + "Users/test/private/repo"
            write(source / "README.md", "portable\n")
            write(
                source / "specs/001-example/evidence.json",
                json.dumps({"runner": f"{local_fixture}/python"}) + "\n",
            )
            source_evidence_hash = hashlib.sha256(
                (source / "specs/001-example/evidence.json").read_bytes()
            ).hexdigest()
            write(source / "specs/001-example/spec.md", "# Example\n")
            write(source / "specs/009-public/spec.md", "# Publication work\n")
            write(source / "docs/releases/closure-anchors.json", json.dumps({
                "recordVersion": "0.1.0", "milestones": {
                    name: {
                        "candidateCommit": "1" * 40,
                        "closureCommit": "2" * 40,
                        "closureTree": "3" * 40,
                        "changedPaths": ["specs/001-example/evidence.json"],
                        "protectedPaths": {
                            "specs/001-example/evidence.json": source_evidence_hash
                        },
                    } for name in ("M0", "M0.5", "M1")
                }
            }))
            exact = commit(source, "source")
            public = base / "public"
            with mock.patch("scripts.create_public_export.ROOT", source):
                create_export(exact, public)
            git(public, "init", "-b", "main")
            commit(public, "clean root")
            manifest = validate_portable_root(public)
            self.assertEqual(
                manifest["historicalEvidence"]["sourceVerification"], "internal-only"
            )
            self.assertIn(
                "specs/001-example/evidence.json", manifest["protectedPaths"]
            )
            self.assertNotIn("specs/009-public/spec.md", manifest["protectedPaths"])
            write(public / "README.md", "future public change\n")
            write(public / "later.txt", "later public evidence\n")
            snapshot = commit(public, "later public work")
            validate_portable_root(public)
            later = (public / "later.txt").read_bytes()
            addendum = {
                "recordVersion": "0.1.0",
                "baseManifestSha256": hashlib.sha256((public / MANIFEST).read_bytes()).hexdigest(),
                "snapshotCommit": snapshot,
                "snapshotTree": git(public, "rev-parse", f"{snapshot}^{{tree}}"),
                "files": [{"path": "later.txt", "sha256": hashlib.sha256(later).hexdigest(),
                           "size": len(later)}],
                "limits": ["Public snapshot only; private ancestry unavailable."],
            }
            (public / ADDENDUM).parent.mkdir(parents=True, exist_ok=True)
            (public / ADDENDUM).write_bytes(canonical_manifest(addendum))
            commit(public, "bind later public evidence")
            validate_portable_root(public)
            self.assertEqual(root_manifest_payload(public, "later.txt"), later)
            write(public / "later.txt", "changed after snapshot\n")
            self.assertEqual(root_manifest_payload(public, "later.txt"), later)
            original_addendum = (public / ADDENDUM).read_bytes()
            (public / ADDENDUM).write_bytes(original_addendum + b" ")
            with self.assertRaisesRegex(ValueError, "canonical|unchanged"):
                validate_portable_root(public)
            (public / ADDENDUM).write_bytes(original_addendum)
            data = json.loads((public / MANIFEST).read_text())
            data["independentValidation"] = "completed"
            write(public / MANIFEST, json.dumps(data, indent=2, sort_keys=True) + "\n")
            with self.assertRaisesRegex(ValueError, "independent validation|unchanged"):
                validate_portable_root(public)

    def test_post_root_addendum_rejects_bad_identity_and_reintroduction(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source, public = base / "source", base / "public"
            source.mkdir()
            git(source, "init", "-b", "main")
            write(source / "README.md", "public\n")
            write(source / "specs/001-example/evidence.json",
                  '{"runner":"/' + 'Users/test/private/python"}\n')
            evidence_hash = hashlib.sha256(
                (source / "specs/001-example/evidence.json").read_bytes()
            ).hexdigest()
            write(source / "docs/releases/closure-anchors.json", json.dumps({
                "recordVersion": "0.1.0", "milestones": {
                    name: {"candidateCommit": "1" * 40, "closureCommit": "2" * 40,
                           "closureTree": "3" * 40,
                           "changedPaths": ["specs/001-example/evidence.json"],
                           "protectedPaths": {"specs/001-example/evidence.json": evidence_hash}}
                    for name in ("M0", "M0.5", "M1")
                },
            }))
            exact = commit(source, "source")
            with mock.patch("scripts.create_public_export.ROOT", source):
                create_export(exact, public)
            git(public, "init", "-b", "main")
            commit(public, "clean root")
            write(public / "later.txt", "later\n")
            snapshot = commit(public, "later public file")
            blob = (public / "later.txt").read_bytes()
            valid = {
                "recordVersion": "0.1.0",
                "baseManifestSha256": hashlib.sha256((public / MANIFEST).read_bytes()).hexdigest(),
                "snapshotCommit": snapshot,
                "snapshotTree": git(public, "rev-parse", f"{snapshot}^{{tree}}"),
                "files": [{"path": "later.txt", "sha256": hashlib.sha256(blob).hexdigest(),
                           "size": len(blob)}],
                "limits": ["Public snapshot only."],
            }
            cases = (
                ("wrong base", {**valid, "baseManifestSha256": "0" * 64}, "identity"),
                ("wrong tree", {**valid, "snapshotTree": "0" * 40}, "ancestry"),
                ("unknown snapshot", {**valid, "snapshotCommit": "f" * 40}, "ancestry"),
                ("duplicate path", {**valid, "files": valid["files"] * 2}, "unique"),
                ("wrong payload", {**valid, "files": [{**valid["files"][0],
                                                        "sha256": "0" * 64}]}, "payload"),
            )
            for title, candidate, error in cases:
                with self.subTest(title=title):
                    (public / ADDENDUM).parent.mkdir(parents=True, exist_ok=True)
                    (public / ADDENDUM).write_bytes(canonical_manifest(candidate))
                    commit(public, title)
                    with self.assertRaisesRegex(ValueError, error):
                        validate_addendum(public)
                    git(public, "reset", "--hard", snapshot)
            (public / ADDENDUM).write_bytes(canonical_manifest(valid))
            commit(public, "valid addendum")
            validate_addendum(public)
            git(public, "rm", ADDENDUM)
            commit(public, "remove addendum")
            with self.assertRaisesRegex(ValueError, "missing after introduction"):
                validate_addendum(public)
            (public / ADDENDUM).write_bytes(canonical_manifest(valid))
            commit(public, "reintroduce addendum")
            with self.assertRaisesRegex(ValueError, "unchanged since introduction"):
                validate_addendum(public)

    def test_release_readiness_rejects_stale_or_overclaimed_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            git(root, "init", "-b", "main")
            for relative in PUBLIC_INPUTS:
                write(root / relative, relative + "\n")
            reviewed = commit(root, "public candidate")
            tree = git(root, "rev-parse", f"{reviewed}^{{tree}}")
            record = {
                "recordVersion": "0.1.0",
                "capturedAt": "2026-09-19T00:00:00+00:00",
                "reviewedCommit": reviewed,
                "tree": tree,
                "platform": "test",
                "python": "3.12.1",
                "git": "git version 2.50.1",
                "cleanRoom": {"freshClone": True, "freshEnvironment": True,
                              "pipCacheDisabled": True, "initialStatus": "", "finalStatus": ""},
                "operator": {"automation": "Codex", "authorization": "founder",
                             "supervisor": "founder", "independent": False},
                "inputs": {
                    relative: hashlib.sha256((root / relative).read_bytes()).hexdigest()
                    for relative in PUBLIC_INPUTS
                },
                "observations": [
                    {"id": identifier,
                     "command": ("/" + "Users/test/tool" if identifier == "install" else identifier),
                     "exitCode": 0,
                     "stdout": "", "stderr": ""}
                    for identifier in PUBLIC_OBSERVATIONS
                ],
                "independentValidation": "pending",
                "limits": ["Internal only."],
            }
            relative = "docs/releases/publication/reproduction.json"
            (root / relative).parent.mkdir(parents=True, exist_ok=True)
            (root / relative).write_bytes(redact_local_paths(
                (json.dumps(record, indent=2) + "\n").encode("utf-8")
            ))
            validate_public_reproduction(root, relative)
            self.assertIn("${LOCAL_PATH}", (root / relative).read_text())
            write(root / relative, json.dumps(record, indent=2) + "\n")
            with self.assertRaisesRegex(ValueError, "prohibited sensitive text"):
                validate_public_reproduction(root, relative)
            record["observations"][0]["command"] = "install"
            record["independentValidation"] = "completed"
            write(root / relative, json.dumps(record, indent=2) + "\n")
            with self.assertRaisesRegex(ValueError, "cannot infer independent validation"):
                validate_public_reproduction(root, relative)

    def test_remote_cutover_requires_explicit_authorization(self):
        root = Path(__file__).resolve().parents[1]
        validate_cutover_pending(root)
        record_path = root / "docs/releases/publication-cutover.json"
        record = json.loads(record_path.read_text())
        with tempfile.TemporaryDirectory() as directory:
            temporary = Path(directory)
            write(temporary / "docs/releases/publication-cutover.json",
                  json.dumps(record, indent=2) + "\n")
            record["remoteOperations"][0]["authorized"] = True
            write(temporary / "docs/releases/publication-cutover.json",
                  json.dumps(record, indent=2) + "\n")
            with self.assertRaisesRegex(ValueError, "unauthorized"):
                validate_cutover_pending(temporary)
