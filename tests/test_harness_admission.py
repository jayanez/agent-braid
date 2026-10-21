# SPDX-License-Identifier: AGPL-3.0-only
"""Owned offline admission tests; no issuer API, lab dispatch or native evidence."""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
import os
import multiprocessing
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import harness_admission as admissions
from agent_braid.harness_manifest import parse_manifest
from agent_braid.system_one import canonical
from test_harness_manifest import make_manifest


def _consume_in_process(raw, expected, scope, now, output):
    try:
        receipt = admissions.reserve_admission(raw, expected_manifest_sha256=expected,
                                               scope=scope, admission_id="case-1", now=now)
        output.put(receipt.to_dict()["id"])
    except admissions.AdmissionError:
        output.put(None)


class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name).resolve()
        self.paths = {}
        for name in admissions._ROOTS:
            path = self.root / name
            path.mkdir(mode=0o700)
            self.paths[name] = path
        self.now = 1_800_000_000
        self.value = make_manifest()
        self.value["environment"]["outputDestinationSha256"] = sha256(
            self.paths["lab_root"].as_posix().encode("utf-8")).hexdigest()
        initial = parse_manifest(canonical(self.value))
        self.bindings = {k: v for k, v in initial.bindings.items() if k != "envelope"}
        self.scope = admissions.OperatorScope(
            issuer="owned-offline-operator", adopted_profile_sha256="a" * 64,
            expected_bindings=self.bindings, observed_at=self.now, **self.paths)
        self.bind()
        self.admission = self.wire()
        self.write()

    def bind(self):
        self.value["envelopeSha256"] = self.scope.sha256
        self.raw = canonical(self.value)
        self.manifest = parse_manifest(self.raw)

    def wire(self, admission_id="case-1"):
        return {"format": admissions.FORMAT, "id": admission_id, "issuer": self.scope.issuer,
                "adoptedProfileSha256": self.scope.adopted_profile_sha256,
                "envelopeSha256": self.scope.sha256, "manifestSha256": self.manifest.sha256,
                "bindings": dict(self.manifest.bindings), "issuedAt": self.now,
                "expiresAt": self.now + 300,
                "reservedJournalBytes": self.value["limits"]["maxJournalBytes"],
                "executionAuthorization": False}

    def write(self, raw=None):
        path = self.paths["operator_root"] / (self.admission["id"] + ".json")
        path.write_bytes(canonical(self.admission) if raw is None else raw)
        path.chmod(0o600)
        return path

    def reserve(self, **changes):
        args = {"expected_manifest_sha256": self.manifest.sha256, "scope": self.scope,
                "admission_id": self.admission["id"], "now": self.now}
        args.update(changes)
        return admissions.reserve_admission(self.raw, **args)

    def rejects_without_reservation(self, **changes):
        before = sorted(p.name for p in self.paths["reservation_root"].iterdir())
        with self.assertRaises(admissions.AdmissionError):
            self.reserve(**changes)
        self.assertEqual(sorted(p.name for p in self.paths["reservation_root"].iterdir()), before)

    def test_positive_immutable_receipt_is_durable_accounting_only(self):
        result = self.reserve()
        record = result.to_dict()
        self.assertFalse(record["executionAuthorization"])
        self.assertEqual(record["manifestSha256"], self.manifest.sha256)
        self.assertEqual(record["reservedJournalBytes"], 8_388_608)
        self.assertEqual(result.sha256, sha256(result.canonical_bytes).hexdigest())
        marker = self.paths["reservation_root"] / "case-1.json"
        self.assertEqual(marker.read_bytes(), result.canonical_bytes)
        self.assertEqual(marker.stat().st_mode & 0o777, 0o600)
        record["executionAuthorization"] = True
        self.assertFalse(result.to_dict()["executionAuthorization"])
        with self.assertRaises(FrozenInstanceError):
            result.canonical_bytes = b"forged"
        # No import, source, lab, or operator writes accompany reservation.
        for name in ("source_root", "base_root", "candidate_root", "context_root", "lab_root"):
            self.assertEqual(list(self.paths[name].iterdir()), [])

    def test_replay_and_different_id_cannot_replenish_spent_count(self):
        self.reserve()
        before = (self.paths["reservation_root"] / "case-1.json").read_bytes()
        self.rejects_without_reservation()
        self.admission = self.wire("case-2")
        self.write()
        self.rejects_without_reservation()
        self.assertEqual((self.paths["reservation_root"] / "case-1.json").read_bytes(), before)

    def test_concurrent_trusted_calls_have_one_winner(self):
        def consume(_):
            try:
                return self.reserve().to_dict()["id"]
            except admissions.AdmissionError:
                return None
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(consume, range(8)))
        self.assertEqual(outcomes.count("case-1"), 1)
        self.assertEqual(sorted(p.name for p in self.paths["reservation_root"].iterdir()),
                         [".lock", "case-1.json"])
        self.rejects_without_reservation()

    def test_processes_share_one_durable_consumption(self):
        context = multiprocessing.get_context("fork")
        output = context.Queue()
        processes = [context.Process(target=_consume_in_process,
                                     args=(self.raw, self.manifest.sha256, self.scope,
                                           self.now, output)) for _ in range(4)]
        try:
            for process in processes:
                process.start()
            outcomes = [output.get(timeout=10) for _ in processes]
            for process in processes:
                process.join(timeout=10)
                self.assertEqual(process.exitcode, 0)
            self.assertEqual(outcomes.count("case-1"), 1)
            self.rejects_without_reservation()
        finally:
            for process in processes:
                if process.is_alive():
                    process.terminate()
                    process.join()
            output.close()
            output.join_thread()

    def test_reservation_before_import_accepts_missing_lab_leaf_without_creating_it(self):
        self.paths["lab_root"].rmdir()
        self.reserve()
        self.assertFalse(self.paths["lab_root"].exists())

    def test_wrong_operator_owner_refuses_without_state(self):
        with patch.object(admissions.os, "getuid", return_value=os.getuid() + 1):
            self.rejects_without_reservation()

    def test_expiry_ttl_future_and_stale_observation_refuse_without_state(self):
        for issued, expires, now in ((self.now, self.now, self.now),
                                      (self.now, self.now + 301, self.now),
                                      (self.now + 1, self.now + 300, self.now),
                                      (self.now - 1, self.now + 10, self.now),
                                      (self.now, self.now + 300, self.now + 300),
                                      (self.now, self.now + 300, self.now - 1)):
            with self.subTest(issued=issued, expires=expires, now=now):
                self.admission.update(issuedAt=issued, expiresAt=expires)
                self.write()
                self.rejects_without_reservation(now=now)
        self.admission.update(issuedAt=self.now, expiresAt=self.now + 1)
        self.write()
        self.assertFalse(self.reserve().to_dict()["executionAuthorization"])

    def test_stricter_manifest_lifetime_and_byte_budget_are_enforced(self):
        self.value["limits"]["maxAdmissionSeconds"] = 10
        self.bind()
        self.admission = self.wire()
        self.write()
        self.rejects_without_reservation()
        self.admission["expiresAt"] = self.now + 10
        self.write()
        self.reserve(now=self.now + 9)

    def test_declared_journal_and_receipt_output_cannot_exceed_trusted_caps(self):
        tight = replace(self.scope, max_reserved_journal_bytes=1000)
        self.rejects_without_reservation(scope=tight)
        self.value["limits"]["maxStageOutputBytes"] = 1
        self.bind()
        self.admission = self.wire()
        self.write()
        self.rejects_without_reservation()

    def test_trusted_scope_copies_bindings_and_refuses_partial_or_higher_profile(self):
        original = self.scope.sha256
        self.bindings["host"] = "b" * 64
        self.assertEqual(self.scope.sha256, original)
        with self.assertRaises(TypeError):
            self.scope.expected_bindings["host"] = "b" * 64
        with self.assertRaises(admissions.AdmissionError):
            replace(self.scope, expected_bindings={"host": "b" * 64})
        for count in (0, 2, True):
            with self.assertRaises(admissions.AdmissionError):
                replace(self.scope, max_reservations=count)

    def test_manifest_drift_cannot_be_blessed_by_rehashing_candidate(self):
        self.value["policy"]["sha256"] = "b" * 64
        self.raw = canonical(self.value)
        forged = parse_manifest(self.raw)
        self.admission.update(manifestSha256=forged.sha256, bindings=dict(forged.bindings))
        self.write()
        self.rejects_without_reservation(expected_manifest_sha256=forged.sha256)
        self.rejects_without_reservation()

    def test_envelope_authority_and_all_seal_bindings_are_checked(self):
        for field, value in (("issuer", "other"), ("adoptedProfileSha256", "b" * 64),
                             ("envelopeSha256", "b" * 64), ("manifestSha256", "b" * 64),
                             ("executionAuthorization", True), ("reservedJournalBytes", True),
                             ("bindings", {"host": "b" * 64})):
            with self.subTest(field=field):
                self.admission = self.wire()
                self.admission[field] = value
                self.write()
                self.rejects_without_reservation()
        self.admission = self.wire()
        self.write()
        self.rejects_without_reservation(scope=replace(self.scope, issuer="different"))

    def test_missing_forged_candidate_file_and_duplicate_json_are_not_authority(self):
        path = self.write()
        raw = path.read_bytes()
        path.unlink()
        (self.paths["candidate_root"] / "case-1.json").write_bytes(raw)
        self.rejects_without_reservation()
        self.write(raw=b'{"format":"x","format":"y"}')
        self.rejects_without_reservation()
        self.write(raw=b"{")
        self.rejects_without_reservation()
        self.write(raw=b" " * (admissions.MAX_RECORD_BYTES + 1))
        self.rejects_without_reservation()

    def test_file_symlink_hardlink_and_unsafe_mode_refuse(self):
        path = self.write()
        target = self.root / "forged.json"
        target.write_bytes(path.read_bytes())
        target.chmod(0o600)
        path.unlink()
        path.symlink_to(target)
        self.rejects_without_reservation()
        path.unlink()
        os.link(target, path)
        self.rejects_without_reservation()
        path.unlink()
        self.write().chmod(0o644)
        self.rejects_without_reservation()

    def test_private_root_permissions_symlinks_and_nesting_refuse(self):
        for root in ("operator_root", "reservation_root"):
            self.paths[root].chmod(0o755)
            self.rejects_without_reservation()
            self.paths[root].chmod(0o700)
        alias = self.root / "alias"
        alias.symlink_to(self.paths["operator_root"], target_is_directory=True)
        self.rejects_without_reservation(scope=replace(self.scope, operator_root=alias))
        with self.assertRaises((admissions.AdmissionError, OSError)):
            admissions._roots(replace(self.scope, operator_root=alias))
        for field in ("source_root", "base_root", "candidate_root", "context_root", "lab_root"):
            self.rejects_without_reservation(scope=replace(self.scope, **{field: self.paths["reservation_root"]}))
        nested = self.paths["source_root"] / "nested"
        nested.mkdir(mode=0o700)
        # _roots validates aliases independently of a matching envelope.
        scoped = replace(self.scope, reservation_root=nested)
        with self.assertRaises(admissions.AdmissionError):
            admissions._roots(scoped)
        scoped = replace(self.scope, source_root=self.root)
        with self.assertRaises(admissions.AdmissionError):
            admissions._roots(scoped)

    def assert_case_alias_refused(self, scope):
        # Supply a fully matching trusted envelope and sealed file, so failure
        # specifically exercises filesystem containment rather than hash drift.
        self.scope = scope
        self.value = make_manifest()
        self.value["environment"]["outputDestinationSha256"] = sha256(
            scope.lab_root.as_posix().encode("utf-8")).hexdigest()
        initial = parse_manifest(canonical(self.value))
        self.scope = replace(scope, expected_bindings={
            key: value for key, value in initial.bindings.items() if key != "envelope"})
        self.bind()
        self.admission = self.wire()
        authority = self.scope.operator_root / "case-1.json"
        authority.write_bytes(canonical(self.admission))
        authority.chmod(0o600)
        store = self.scope.reservation_root
        before = sorted(entry.name for entry in store.iterdir())
        with self.assertRaises(admissions.AdmissionError) as caught:
            self.reserve()
        self.assertEqual(caught.exception.reason, "overlapping-roots")
        self.assertEqual(sorted(entry.name for entry in store.iterdir()), before)

    def case_alias(self, path):
        alias = path.with_name(path.name.upper())
        if not alias.exists() or not alias.samefile(path):
            self.skipTest("requires the real case-insensitive filesystem alias")
        return alias

    def test_real_case_alias_protected_roots_inside_source_refuse_before_writes(self):
        original = self.scope
        alias = self.case_alias(original.source_root)
        for protected in ("operator_root", "reservation_root"):
            with self.subTest(protected=protected):
                nested = alias / protected
                nested.mkdir(mode=0o700)
                self.assert_case_alias_refused(replace(original, **{protected: nested}))

    def test_real_case_alias_source_inside_protected_root_refuses_before_writes(self):
        original = self.scope
        for protected in ("operator_root", "reservation_root"):
            with self.subTest(protected=protected):
                alias = self.case_alias(getattr(original, protected))
                nested = alias / "read-child"
                nested.mkdir(mode=0o700)
                self.assert_case_alias_refused(replace(original, source_root=nested))

    def test_real_case_alias_missing_lab_under_protected_root_refuses_before_writes(self):
        original = self.scope
        for protected in ("operator_root", "reservation_root"):
            with self.subTest(protected=protected):
                alias = self.case_alias(getattr(original, protected))
                missing = alias / "new-lab"
                self.assertFalse(missing.exists())
                self.assert_case_alias_refused(replace(original, lab_root=missing))
                self.assertFalse(missing.exists())

    def test_partial_or_unknown_records_refuse_and_are_never_reset(self):
        store = self.paths["reservation_root"]
        for name, raw in (("case-1.json", b"{"), ("case-1.json", b""),
                          ("case-1.json", b"{}"), ("unexpected", b"x")):
            marker = store / name
            marker.write_bytes(raw)
            marker.chmod(0o600)
            before = sorted(p.name for p in store.iterdir())
            with self.assertRaises(admissions.AdmissionError):
                self.reserve()
            self.assertEqual(sorted(p.name for p in store.iterdir()), before)
            self.assertEqual(marker.read_bytes(), raw)
            marker.unlink()  # operator-owned test fixture teardown, never production recovery
        self.reserve()
        self.rejects_without_reservation(now=self.now + 301)

    def test_paid_route_nonzero_dispatch_and_unknown_identity_refuse(self):
        for field in ("maxNativeSessions", "maxModelSessions", "maxChildProcesses",
                      "maxNetworkConnections", "maxAdditionalCashMicros", "maxAutomaticRetries"):
            self.value["limits"][field] = 1
            self.raw = canonical(self.value)
            self.rejects_without_reservation()
            self.value["limits"][field] = 0
        self.value["host"]["requested"]["route"] = "paid-api"
        self.raw = canonical(self.value)
        self.rejects_without_reservation()
        self.value["host"]["requested"]["route"] = "offline"
        self.raw = canonical(self.value)
        self.rejects_without_reservation(expected_manifest_sha256="unknown")


if __name__ == "__main__":
    unittest.main()
