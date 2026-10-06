# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic metadata controls only; no source or scientific approval."""
from copy import deepcopy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts.check_predictor_readiness import FORMAT, MAX_BYTES, MAX_COUNT, MAX_FAMILIES, MAX_IDS, check_readiness, load_manifest, main


def synthetic_manifest() -> dict:
    families = []
    for i, partition in enumerate(("train", "calibration", "holdout", "holdout", "holdout")):
        families.append({"familyId": f"family-{i}", "partition": partition,
                         "rights": {key: True for key in ("owner", "participants", "data", "privacy")},
                         "eligible": True, "windowFrozen": True, "completenessReviewed": True,
                         "admittedPairs": 20, "positive": 10, "negative": 10, "unknown": 0,
                         "annotationAttempts": 20, "policyBlind": True, "holdoutSealed": True,
                         "sessionIds": [f"session-{i}"], "duplicateGroupIds": [f"group-{i}"]})
    return {"format": FORMAT, "sourceKind": "synthetic",
            "protocol": {"recordedHash": "a" * 64, "currentHash": "a" * 64, "approved": True},
            "rubric": {"recordedHash": "b" * 64, "currentHash": "b" * 64, "approved": True},
            "families": families}


class PredictorReadinessTests(unittest.TestCase):
    def test_synthetic_complete_control_never_admits_or_authorizes(self):
        manifest = synthetic_manifest()
        before = deepcopy(manifest)
        report = check_readiness(manifest)
        self.assertTrue(report["metadataPrerequisitesMet"])
        self.assertEqual(report["reasons"], [])
        self.assertEqual(report["claimedKnownLabels"], 100)
        self.assertEqual(report["realPairsAdmitted"], 0)
        self.assertFalse(report["trainingAuthorization"])
        self.assertFalse(report["executionAuthorization"])
        self.assertFalse(report["humanApprovalVerified"])
        self.assertEqual(manifest, before)

    def test_missing_rights_and_review_are_explicit(self):
        for right in ("owner", "participants", "data", "privacy"):
            manifest = synthetic_manifest()
            manifest["families"][0]["rights"][right] = False
            with self.subTest(right=right):
                self.assertIn("family-0:missing-rights", check_readiness(manifest)["reasons"])
        for record in ("protocol", "rubric"):
            manifest = synthetic_manifest()
            manifest[record]["approved"] = False
            self.assertIn(f"{record}-unapproved", check_readiness(manifest)["reasons"])

    def test_empty_inventory_zero_yield_is_not_ready(self):
        manifest = synthetic_manifest()
        manifest["families"] = []
        report = check_readiness(manifest)
        self.assertFalse(report["metadataPrerequisitesMet"])
        self.assertIn("zero-yield", report["reasons"])
        self.assertIn("insufficient-eligible-families", report["reasons"])

    def test_family_session_and_duplicate_leakage(self):
        for field in ("sessionIds", "duplicateGroupIds"):
            manifest = synthetic_manifest()
            manifest["families"][2][field] = manifest["families"][0][field][:]
            self.assertIn(f"{field}-partition-leakage", check_readiness(manifest)["reasons"])
        manifest = synthetic_manifest()
        manifest["families"].append(deepcopy(manifest["families"][0]))
        with self.assertRaisesRegex(ValueError, "duplicate family"):
            check_readiness(manifest)

    def test_class_thresholds_and_unknown_labels(self):
        for index, partition in ((0, "train"), (1, "calibration")):
            manifest = synthetic_manifest()
            manifest["families"][index].update(positive=0, negative=20)
            self.assertIn(f"{partition}-class-coverage-insufficient", check_readiness(manifest)["reasons"])
        manifest = synthetic_manifest()
        for family in manifest["families"][2:]:
            family.update(positive=0, negative=10, unknown=10)
        report = check_readiness(manifest)
        self.assertIn("holdout-class-coverage-insufficient", report["reasons"])
        self.assertIn("known-label-count-insufficient", report["reasons"])
        self.assertEqual(report["claimedKnownLabels"], 70)

    def test_blinding_attempts_seal_window_and_completeness(self):
        for field, reason in (("policyBlind", "annotation-incomplete-or-unblinded"),
                              ("holdoutSealed", "holdout-unsealed"),
                              ("windowFrozen", "windowFrozen-missing"),
                              ("completenessReviewed", "completenessReviewed-missing")):
            manifest = synthetic_manifest()
            manifest["families"][2][field] = False
            self.assertIn(f"family-2:{reason}", check_readiness(manifest)["reasons"])
        manifest = synthetic_manifest()
        manifest["families"][2].update(positive=5, negative=5, unknown=10, annotationAttempts=10)
        self.assertIn("family-2:annotation-incomplete-or-unblinded", check_readiness(manifest)["reasons"])

    def test_hash_drift_and_malformed_payload_fail_closed(self):
        for record in ("protocol", "rubric"):
            manifest = synthetic_manifest()
            manifest[record]["currentHash"] = "c" * 64
            self.assertIn(f"{record}-hash-drift", check_readiness(manifest)["reasons"])
        for mutate in (lambda value: value.update(sourceKind="prospective"),
                       lambda value: value.update(sourcePath="/private/payload"),
                       lambda value: value["families"][0].update(admittedPairs=True),
                       lambda value: value["families"][0].update(annotationAttempts=21),
                       lambda value: value["families"][0].update(positive=11)):
            manifest = synthetic_manifest()
            mutate(manifest)
            with self.assertRaises(ValueError):
                check_readiness(manifest)

    def test_cli_reads_only_supplied_manifest_and_has_distinct_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "metadata.json"
            manifest = synthetic_manifest()
            manifest["sourceKind"] = "metadata-only"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            original = Path.open
            opened = []
            def open_file(target, *args, **kwargs):
                opened.append(target)
                return original(target, *args, **kwargs)
            with patch.object(Path, "open", open_file), redirect_stdout(io.StringIO()) as stdout:
                self.assertEqual(main([str(path)]), 0)
            self.assertEqual(opened, [path])
            self.assertFalse(json.loads(stdout.getvalue())["trainingAuthorization"])
            manifest["families"] = []
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main([str(path)]), 1)


    def test_strict_json_size_depth_and_private_diagnostics(self):
        from contextlib import redirect_stderr
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory).resolve() / "private-sensitive-name.json"
            for raw in (b'{"sourceKind":"synthetic","sourceKind":"metadata-only"}',
                        b'{"value":NaN}', b'{"value":Infinity}',
                        b"[" * 40 + b"0" + b"]" * 40,
                        b"[" * 2000 + b"0" + b"]" * 2000,
                        b" " * (MAX_BYTES + 1)):
                path.write_bytes(raw)
                with self.assertRaises(ValueError):
                    load_manifest(path)
                with redirect_stderr(io.StringIO()) as stderr:
                    with self.assertRaises(SystemExit) as failure:
                        main([str(path)])
                self.assertEqual(failure.exception.code, 2)
                self.assertNotIn("private-sensitive-name", stderr.getvalue())
                self.assertNotIn("sourceKind", stderr.getvalue())
            missing = path.with_name("missing-private-name.json")
            with redirect_stderr(io.StringIO()) as stderr:
                with self.assertRaises(SystemExit):
                    main([str(missing)])
            self.assertNotIn("missing-private-name", stderr.getvalue())

    def test_count_and_inventory_limits_reject_excess(self):
        manifest = synthetic_manifest()
        manifest["families"] *= MAX_FAMILIES + 1
        with self.assertRaises(ValueError):
            check_readiness(manifest)
        manifest = synthetic_manifest()
        manifest["families"][0]["sessionIds"] = [f"s-{i}" for i in range(MAX_IDS + 1)]
        with self.assertRaises(ValueError):
            check_readiness(manifest)
        manifest = synthetic_manifest()
        manifest["families"][0].update(admittedPairs=MAX_COUNT + 1, positive=MAX_COUNT + 1,
                                       negative=0, annotationAttempts=MAX_COUNT + 1)
        with self.assertRaises(ValueError):
            check_readiness(manifest)
