# SPDX-License-Identifier: AGPL-3.0-only
"""Compose offline foundations; no runner, host or native qualification implied."""
from hashlib import sha256
from pathlib import Path
import tempfile
import unittest

from agent_braid.harness_admission import AdmissionError, OperatorScope, reserve_admission
from agent_braid.harness_manifest import parse_manifest
from agent_braid.harness_surface import SurfaceError, import_candidate
from agent_braid.system_one import canonical
from test_harness_manifest import make_manifest


class OfflineFoundationsTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.paths = {name + "_root": self.root / name for name in
                      ("source", "base", "candidate", "context", "operator", "reservation", "lab")}
        for name, path in self.paths.items():
            if name != "lab_root":
                path.mkdir(mode=0o700)
        self.contents = {"source": {"task.txt": b"owned task\n"},
                         "base": {"guidance/main.md": b"Retain the static base.\n"},
                         "candidate": {"guidance/main.md": b"Use a bounded handoff.\n"},
                         "context": {"notes/context.txt": b"owned notes\n"}}
        for name, files in self.contents.items():
            for relative, content in files.items():
                path = self.paths[name + "_root"] / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        self.value = make_manifest()
        self.value["context"][0]["sha256"] = sha256(b"owned notes\n").hexdigest()
        self.value["effects"]["delete"] = ["lab/guidance/main.md"]
        self.value["environment"]["outputDestinationSha256"] = sha256(
            self.paths["lab_root"].as_posix().encode()).hexdigest()
        self.now = 1_800_000_000

    def seal(self):
        initial = parse_manifest(canonical(self.value))
        self.scope = OperatorScope(
            issuer="owned-offline-operator", adopted_profile_sha256="a" * 64,
            expected_bindings={k: v for k, v in initial.bindings.items() if k != "envelope"},
            observed_at=self.now, **self.paths)
        self.value["envelopeSha256"] = self.scope.sha256
        self.raw = canonical(self.value)
        self.manifest = parse_manifest(self.raw)
        admission = {"format": "braid-harness-admission/v0.1", "id": "integration-1",
                     "issuer": self.scope.issuer,
                     "adoptedProfileSha256": self.scope.adopted_profile_sha256,
                     "envelopeSha256": self.scope.sha256,
                     "manifestSha256": self.manifest.sha256,
                     "bindings": dict(self.manifest.bindings), "issuedAt": self.now,
                     "expiresAt": self.now + 300, "reservedJournalBytes": 8_388_608,
                     "executionAuthorization": False}
        # Test-only operator fixture; production has no admission issuance API.
        path = self.paths["operator_root"] / "integration-1.json"
        path.write_bytes(canonical(admission))
        path.chmod(0o600)

    def reserve(self):
        return reserve_admission(self.raw, expected_manifest_sha256=self.manifest.sha256,
                                 scope=self.scope, admission_id="integration-1", now=self.now)

    def materialize(self):
        return import_candidate(self.raw, expected_sha256=self.manifest.sha256,
                                expected_bindings=self.manifest.bindings,
                                destination=self.paths["lab_root"], **{
                                    name: self.paths[name] for name in
                                    ("source_root", "base_root", "candidate_root", "context_root")})

    def test_reservation_precedes_new_import_without_widening_read_inventory(self):
        # Large repositories and hidden/context files are outside the selected reads.
        (self.paths["source_root"] / "unselected-secret").write_bytes(b"not admitted")
        (self.paths["context_root"] / "hidden-grader").write_bytes(b"not admitted")
        self.seal()
        reservation = self.reserve()
        self.assertFalse(self.paths["lab_root"].exists())
        imported = self.materialize()
        self.assertTrue(imported["acceptedPublished"])
        self.assertFalse(imported["executionAuthorization"])
        self.assertFalse(reservation.to_dict()["executionAuthorization"])
        self.assertEqual(imported["manifestSha256"], reservation.to_dict()["manifestSha256"])
        accepted = self.paths["lab_root"] / "candidate" / "guidance/main.md"
        self.assertEqual(accepted.read_bytes(), self.contents["candidate"]["guidance/main.md"])
        self.assertEqual(accepted.stat().st_mode & 0o222, 0)
        for name, files in self.contents.items():
            for relative, content in files.items():
                self.assertEqual((self.paths[name + "_root"] / relative).read_bytes(), content)
        with self.assertRaises(AdmissionError):
            self.reserve()

    def test_failed_import_leaves_reservation_spent_and_destination_unclaimed(self):
        self.seal()
        spent = self.reserve().canonical_bytes
        path = self.paths["candidate_root"] / "guidance/main.md"
        path.write_bytes(b"changed after admission\n")
        with self.assertRaises(SurfaceError):
            self.materialize()
        self.assertFalse(self.paths["lab_root"].exists())
        path.write_bytes(self.contents["candidate"]["guidance/main.md"])
        with self.assertRaises(AdmissionError):
            self.reserve()
        self.assertEqual((self.paths["reservation_root"] / "integration-1.json").read_bytes(), spent)

    def test_missing_cleanup_effect_cannot_materialize_even_after_reservation(self):
        self.value["effects"]["delete"] = []
        self.seal()
        self.reserve()
        with self.assertRaises(SurfaceError):
            self.materialize()
        self.assertFalse(self.paths["lab_root"].exists())
        with self.assertRaises(AdmissionError):
            self.reserve()


if __name__ == "__main__":
    unittest.main()
