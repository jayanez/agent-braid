# SPDX-License-Identifier: AGPL-3.0-only
"""Adversarial tests for the metadata-only M3.5 packet checker."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from scripts.check_m35_review_packet import FILES, PacketError, check_packet, main


def candidate_manifest() -> dict:
    return {
        "format": "m35-source-candidates-v1",
        "sourceKind": "metadata-only",
        "basedOnCommit": "a" * 40,
        "families": [
            {"familyId": f"family-{index}",
             "repository": ("jayanez/agent-braid", "jayanez/kinetiq-core", "jayanez/smart-notes")[index % 3],
             "workflow": f"workflow {index}", "decisionContext": f"context {index}",
             "naturalTrigger": f"trigger {index}", "distinctnessReview": "pending",
             "permissionReview": "pending", "eligibilityReview": "pending"}
            for index in range(5)
        ],
    }


class M35ReviewPacketTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        for relative in FILES:
            target = self.root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            if relative == FILES[0]:
                target.write_text(json.dumps(candidate_manifest()), encoding="utf-8")
            else:
                target.write_text(f"Fixed review input: {relative}\n", encoding="utf-8")

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_deterministic_packet_pin_and_all_authority_stays_false(self) -> None:
        first = check_packet(self.root)
        second = check_packet(self.root)
        self.assertEqual(first, second)
        self.assertTrue(first["packetStructurallyComplete"])
        self.assertEqual(first["realPairsAdmitted"], 0)
        for key in ("sourceCaptureAuthorization", "trainingAuthorization",
                    "executionAuthorization", "humanApprovalVerified"):
            self.assertIs(first[key], False)
        self.assertEqual(len(first["inputSha256"]), 6)
        self.assertEqual(check_packet(self.root, first["packetSha256"]), first)
        with self.assertRaisesRegex(PacketError, "packet-commitment-drift"):
            check_packet(self.root, "0" * 64)

    def test_each_fixed_file_is_covered_by_packet_pin(self) -> None:
        pin = check_packet(self.root)["packetSha256"]
        for relative in FILES:
            with self.subTest(relative=relative):
                path = self.root / relative
                original = path.read_bytes()
                path.write_bytes(original + b"changed\n")
                with self.assertRaisesRegex(PacketError, "packet-commitment-drift"):
                    check_packet(self.root, pin)
                path.write_bytes(original)

    def test_candidate_shape_and_pending_status_are_strict(self) -> None:
        mutations = (
            lambda value: value.update(unexpected=True),
            lambda value: value["families"][0].update(extra="x"),
            lambda value: value["families"][0].update(permissionReview="approved"),
            lambda value: value["families"][0].update(repository="evil/private"),
            lambda value: value["families"][1].update(familyId=value["families"][0]["familyId"]),
            lambda value: value["families"].pop(),
            lambda value: value.update(basedOnCommit="bad"),
            lambda value: value["families"][0].update(workflow=" " * 3),
            lambda value: value["families"][0].update(permissionReview=[]),
        )
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                value = candidate_manifest()
                mutate(value)
                (self.root / FILES[0]).write_text(json.dumps(value), encoding="utf-8")
                with self.assertRaises(PacketError):
                    check_packet(self.root)

    def test_duplicate_json_and_nonfinite_values_rejected(self) -> None:
        path = self.root / FILES[0]
        path.write_text('{"format":"m35-source-candidates-v1","format":"bad"}', encoding="utf-8")
        with self.assertRaisesRegex(PacketError, "duplicate-json-member"):
            check_packet(self.root)
        path.write_text('{"x":NaN}', encoding="utf-8")
        with self.assertRaisesRegex(PacketError, "nonfinite-json-value"):
            check_packet(self.root)

    def test_json_depth_limit_rejected(self) -> None:
        path = self.root / FILES[0]
        path.write_text('{"nested":' + "[" * 34 + "0" + "]" * 34 + "}", encoding="utf-8")
        with self.assertRaisesRegex(PacketError, "json-depth-limit"):
            check_packet(self.root)

    def test_symlink_outside_and_missing_files_fail_without_following(self) -> None:
        target = self.root / FILES[1]
        original = target.read_bytes()
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory) / "outside.txt"
            outside.write_text("must not read", encoding="utf-8")
            target.unlink()
            target.symlink_to(outside)
            with self.assertRaisesRegex(PacketError, "input-symlink-rejected"):
                check_packet(self.root)
            target.unlink()
        with self.assertRaisesRegex(PacketError, "required-input-missing"):
            check_packet(self.root)
        target.write_bytes(original)

    def test_intermediate_directory_symlink_and_symlink_root_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as outside_directory:
            outside = Path(outside_directory)
            for relative in FILES:
                destination = outside / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = self.root / relative
                destination.write_bytes(source.read_bytes())
            spec_dir = self.root / "specs/019-native-predictor"
            saved = self.root / "specs/019-native-predictor-saved"
            spec_dir.rename(saved)
            spec_dir.symlink_to(outside / "specs/019-native-predictor", target_is_directory=True)
            with self.assertRaisesRegex(PacketError, "input-symlink-rejected"):
                check_packet(self.root)
            spec_dir.unlink()
            saved.rename(spec_dir)
            root_link = self.root.parent / (self.root.name + "-link")
            try:
                root_link.symlink_to(self.root, target_is_directory=True)
                with self.assertRaisesRegex(PacketError, "repository-root-not-directory"):
                    check_packet(root_link)
            finally:
                root_link.unlink(missing_ok=True)

    @unittest.skipUnless(hasattr(os, "mkfifo") and hasattr(os, "O_NONBLOCK"),
                         "FIFO controls require POSIX FIFO support")
    def test_fifo_rejected_without_blocking_subprocess(self) -> None:
        target = self.root / FILES[1]
        target.unlink()
        os.mkfifo(target)
        code = ("from scripts.check_m35_review_packet import check_packet; "
                f"check_packet({str(self.root)!r})")
        process = subprocess.run([sys.executable, "-c", code], cwd=Path(__file__).resolve().parents[1],
                                 capture_output=True, text=True, timeout=3)
        self.assertNotEqual(process.returncode, 0)
        self.assertIn("input-not-regular-file", process.stderr)

    def test_size_limit_and_cli_diagnostics_are_redacted(self) -> None:
        target = self.root / FILES[2]
        target.write_bytes(b"x" * (1024 * 1024 + 1))
        with self.assertRaisesRegex(PacketError, "input-size-limit"):
            check_packet(self.root)
        target.write_text("private snippet should not appear", encoding="utf-8")
        target.unlink()
        from io import StringIO
        from contextlib import redirect_stderr
        error = StringIO()
        with redirect_stderr(error), self.assertRaises(SystemExit) as raised:
            main(["--root", str(self.root)])
        self.assertEqual(raised.exception.code, 2)
        self.assertIn("required-input-missing", error.getvalue())
        self.assertNotIn(str(self.root), error.getvalue())
        self.assertNotIn("private snippet", error.getvalue())

    def test_checker_does_not_change_packet_inputs(self) -> None:
        before = {relative: hashlib.sha256((self.root / relative).read_bytes()).hexdigest()
                  for relative in FILES}
        check_packet(self.root)
        after = {relative: hashlib.sha256((self.root / relative).read_bytes()).hexdigest()
                 for relative in FILES}
        self.assertEqual(before, after)


if __name__ == "__main__":
    unittest.main()
