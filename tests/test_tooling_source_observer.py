# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic boundary controls; no authentic provider evidence is supplied."""

from copy import deepcopy
from datetime import timedelta
import hashlib
import json
import os
from pathlib import Path
import stat
import tempfile
import threading
import time
import unittest

from agent_braid import tooling_source_observer as observer
from agent_braid.tooling_subscription import operational_binding_from_dict
from tests.test_tooling_codex_sources import fixture, NOW
from tests.test_tooling_claude_sources import fixture as claude_fixture, NOW as CLAUDE_NOW


class SyntheticVerifier:
    """Explicit test double, never installed by a production default."""

    def __init__(self):
        self.calls = []
        self.refused_kind = None

    def verify_receipt(self, kind, receipt, pin):
        self.calls.append(kind)
        if kind == self.refused_kind:
            raise ValueError("private raw detail must stay redacted")


def cache(contract=None, digest=None, verifier=None):
    if contract is None:
        contract, _, digest = fixture()
    return observer.SourceObserverCache(contract, expected_contract_sha256=digest,
                                        receipt_verifier=verifier or SyntheticVerifier())


def read(store, contract, *, now=NOW, phase="prelaunch", pid=None, birth=None):
    return store.read(now=now, expected_binding=operational_binding_from_dict(contract["binding"]),
                      phase=phase, process_id=pid, process_birth_sha256=birth)


class SourceCacheTests(unittest.TestCase):
    def test_authenticates_all_exact_receipts_and_reads_without_external_calls(self):
        contract, receipts, digest = fixture()
        verifier = SyntheticVerifier()
        store = cache(contract, digest, verifier)
        store.publish(receipts, now=NOW)
        self.assertEqual(verifier.calls, ["quota", "autoRecharge", "process"])
        verifier.refused_kind = "quota"
        result = read(store, contract, now=NOW + timedelta(seconds=2))
        self.assertIsInstance(result, observer.AuthenticatedSourceObservation)
        self.assertEqual(result.composition.valid_until, NOW + timedelta(seconds=30))
        self.assertEqual(verifier.calls, ["quota", "autoRecharge", "process"])

    def test_deep_snapshot_cannot_be_mutated_or_retimestamped(self):
        contract, receipts, digest = fixture()
        store = cache(contract, digest)
        store.publish(receipts, now=NOW)
        contract["binding"]["slotId"] = "tampered"
        receipts["quota"]["payload"]["ordinaryUsageAllowed"] = False
        result = store.read(now=NOW, expected_binding=store.binding, phase="prelaunch")
        with self.assertRaises(TypeError):
            result.receipts["quota"]["payload"]["credits"]["hasCredits"] = True
        encoded = result.as_dict()
        encoded["receipts"]["quota"]["payload"]["ordinaryUsageAllowed"] = False
        self.assertTrue(result.receipts["quota"]["payload"]["ordinaryUsageAllowed"])
        self.assertEqual(result.receipts["quota"]["observedAt"], NOW.isoformat())

    def test_empty_expired_and_regressed_clock_invalidate(self):
        for failure_time in [NOW + timedelta(seconds=31), NOW - timedelta(seconds=1)]:
            with self.subTest(failure_time=failure_time):
                contract, receipts, digest = fixture()
                store = cache(contract, digest)
                with self.assertRaises(observer.SourceObserverError):
                    read(store, contract)
                store.publish(receipts, now=NOW)
                with self.assertRaises(observer.SourceObserverError):
                    read(store, contract, now=failure_time)
                with self.assertRaises(observer.SourceObserverError):
                    read(store, contract, now=NOW + timedelta(seconds=1))

    def test_verifier_failure_invalidates_existing_snapshot_and_redacts_details(self):
        contract, receipts, digest = fixture()
        verifier = SyntheticVerifier()
        store = cache(contract, digest, verifier)
        store.publish(receipts, now=NOW)
        verifier.refused_kind = "autoRecharge"
        for value in receipts.values():
            value["observedSequence"] = 2
        with self.assertRaises(observer.SourceObserverError) as caught:
            store.publish(receipts, now=NOW)
        self.assertNotIn("private raw", str(caught.exception))
        with self.assertRaises(observer.SourceObserverError):
            read(store, contract)

    def test_interrupt_during_synchronous_verification_invalidates_before_reraising(self):
        for interruption in (KeyboardInterrupt, SystemExit):
            with self.subTest(interruption=interruption):
                contract, receipts, digest = fixture()
                class InterruptedVerifier(SyntheticVerifier):
                    interrupted = False
                    def verify_receipt(self, kind, receipt, pin):
                        if self.interrupted:
                            raise interruption("operator interruption")
                        return super().verify_receipt(kind, receipt, pin)
                verifier = InterruptedVerifier()
                store = cache(contract, digest, verifier)
                store.publish(receipts, now=NOW)
                verifier.interrupted = True
                for receipt in receipts.values():
                    receipt["observedSequence"] = 2
                with self.assertRaises(interruption):
                    store.publish(receipts, now=NOW)
                with self.assertRaises(observer.SourceObserverError):
                    read(store, contract)

    def test_binding_phase_pid_and_birth_drift_refuse_and_invalidate(self):
        for kwargs in [{"phase": "running", "process_id": 42, "process_birth_sha256": "a" * 64},
                       {"phase": "prelaunch", "process_id": 42},
                       {"phase": "prelaunch", "process_birth_sha256": "a" * 64},
                       {"phase": "unknown"}]:
            with self.subTest(kwargs=kwargs):
                contract, receipts, digest = fixture()
                store = cache(contract, digest)
                store.publish(receipts, now=NOW)
                with self.assertRaises(observer.SourceObserverError):
                    store.read(now=NOW, expected_binding=store.binding, **kwargs)
                with self.assertRaises(observer.SourceObserverError):
                    read(store, contract)
        contract, receipts, digest = fixture()
        store = cache(contract, digest)
        store.publish(receipts, now=NOW)
        other = deepcopy(contract["binding"])
        other["accountSha256"] = "a" * 64
        with self.assertRaises(observer.SourceObserverError):
            store.read(now=NOW, expected_binding=operational_binding_from_dict(other), phase="prelaunch")

    def test_new_sequence_does_not_refresh_an_old_recharge_source(self):
        contract, receipts, digest = fixture()
        store = cache(contract, digest)
        store.publish(receipts, now=NOW)
        for kind, receipt in receipts.items():
            receipt["observedSequence"] = 2
            if kind != "autoRecharge":
                receipt["observedAt"] = (NOW + timedelta(seconds=20)).isoformat()
        store.publish(receipts, now=NOW + timedelta(seconds=20))
        self.assertEqual(read(store, contract, now=NOW + timedelta(seconds=30)).composition.valid_until,
                         NOW + timedelta(seconds=30))
        with self.assertRaises(observer.SourceObserverError):
            read(store, contract, now=NOW + timedelta(seconds=31))

    def test_source_clock_sequence_and_lifecycle_cannot_regress(self):
        for mutation in ["sequence", "source_time", "phase", "birth"]:
            with self.subTest(mutation=mutation):
                contract, receipts, digest = fixture()
                for receipt in receipts.values():
                    receipt.update(phase="running", processId=42, processBirthSha256="b" * 64)
                store = cache(contract, digest)
                store.publish(receipts, now=NOW)
                for receipt in receipts.values():
                    receipt["observedSequence"] = 2
                if mutation == "sequence":
                    for receipt in receipts.values():
                        receipt["observedSequence"] = 1
                elif mutation == "source_time":
                    receipts["quota"]["observedAt"] = (NOW - timedelta(seconds=1)).isoformat()
                elif mutation == "phase":
                    for receipt in receipts.values():
                        receipt.update(phase="prelaunch", processId=None, processBirthSha256=None)
                else:
                    for receipt in receipts.values():
                        receipt["processBirthSha256"] = "c" * 64
                with self.assertRaises(observer.SourceObserverError):
                    store.publish(receipts, now=NOW)

    def test_claude_retains_interface_time_and_quota_reset_expiry(self):
        contract, receipts, digest = claude_fixture()
        receipts["quota"]["payload"]["quotaWindows"]["fiveHour"]["resetsAt"] = (
            CLAUDE_NOW + timedelta(seconds=5)).isoformat()
        store = cache(contract, digest)
        store.publish(receipts, now=CLAUDE_NOW)
        result = read(store, contract, now=CLAUDE_NOW)
        self.assertEqual(result.composition.valid_until, CLAUDE_NOW + timedelta(seconds=5))
        with self.assertRaises(observer.SourceObserverError):
            read(store, contract, now=CLAUDE_NOW + timedelta(seconds=5))

    def test_serialized_records_are_checked_claims_not_authenticated(self):
        contract, receipts, digest = fixture()
        store = cache(contract, digest)
        store.publish(receipts, now=NOW)
        raw = read(store, contract).as_dict()
        parsed = observer.source_observation_from_dict(raw, contract,
                    expected_contract_sha256=digest, now=NOW)
        self.assertIsInstance(parsed, observer.SourceObservation)
        self.assertNotIsInstance(parsed, observer.AuthenticatedSourceObservation)
        observer.check_source_observation(parsed, contract, expected_contract_sha256=digest,
                    now=NOW, expected_binding=store.binding, phase="prelaunch")
        raw["receipts"]["autoRecharge"]["observedAt"] = (NOW - timedelta(seconds=31)).isoformat()
        with self.assertRaises(observer.SourceObserverError):
            observer.source_observation_from_dict(raw, contract, expected_contract_sha256=digest, now=NOW)

    def test_valid_lifecycle_checks_typed_originals_and_refuses_forged_composition(self):
        from dataclasses import replace
        contract, receipts, digest = fixture()
        store = cache(contract, digest)
        store.publish(receipts, now=NOW)
        for receipt in receipts.values():
            receipt.update(phase="running", processId=42, processBirthSha256="b" * 64,
                           observedSequence=2)
        store.publish(receipts, now=NOW)
        running = read(store, contract, phase="running", pid=42, birth="b" * 64)
        forged = observer.SourceObservation(replace(running.composition, valid_until=NOW + timedelta(hours=1)),
                                            running.receipts)
        with self.assertRaises(observer.SourceObserverError):
            observer.check_source_observation(forged, contract, expected_contract_sha256=digest,
                now=NOW, expected_binding=store.binding, phase="running", process_id=42,
                process_birth_sha256="b" * 64)
        for receipt in receipts.values():
            receipt.update(phase="completed", observedSequence=3)
        store.publish(receipts, now=NOW)
        completed = read(store, contract, phase="completed", pid=42, birth="b" * 64)
        self.assertEqual(completed.composition.phase, "completed")
        with self.assertRaises(observer.SourceObserverError):
            read(store, contract, phase="completed", pid=43, birth="b" * 64)

    def test_claude_900_second_exception_applies_only_to_original_interface_source(self):
        from agent_braid import tooling_claude_sources as sources
        contract, receipts, _ = claude_fixture()
        contract["sourceMaxAgeSeconds"]["autoRecharge"] = 900
        digest = sources.source_contract_sha256(contract)
        for receipt in receipts.values():
            receipt["contractSha256"] = digest
        recharge = receipts["autoRecharge"]
        recharge["observedAt"] = (CLAUDE_NOW - timedelta(seconds=850)).isoformat()
        recharge["payload"]["uiObservedAt"] = recharge["observedAt"]
        recharge["payload"]["profileObservedAt"] = recharge["observedAt"]
        store = cache(contract, digest)
        store.publish(receipts, now=CLAUDE_NOW)
        self.assertEqual(read(store, contract, now=CLAUDE_NOW).composition.valid_until,
                         CLAUDE_NOW + timedelta(seconds=30))
        receipts["quota"]["observedAt"] = recharge["observedAt"]
        for receipt in receipts.values():
            receipt["observedSequence"] = 2
        with self.assertRaises(observer.SourceObserverError):
            store.publish(receipts, now=CLAUDE_NOW)

    def test_invalidation_while_authenticating_cannot_publish_a_late_snapshot(self):
        contract, receipts, digest = fixture()
        began, release = threading.Event(), threading.Event()
        class SlowVerifier:
            def verify_receipt(self, kind, receipt, pin):
                began.set()
                release.wait(1)
        store = cache(contract, digest, SlowVerifier())
        errors = []
        def publish():
            try:
                store.publish(receipts, now=NOW)
            except observer.SourceObserverError:
                errors.append("refused")
        worker = threading.Thread(target=publish)
        worker.start()
        self.assertTrue(began.wait(.5))
        store.invalidate()
        release.set()
        worker.join(1)
        self.assertFalse(worker.is_alive())
        self.assertEqual(errors, ["refused"])
        with self.assertRaises(observer.SourceObserverError):
            read(store, contract)

    def test_read_racing_with_a_phase_publication_refuses_old_snapshot(self):
        from unittest.mock import patch
        contract, receipts, digest = fixture()
        store = cache(contract, digest)
        store.publish(receipts, now=NOW)
        began, release = threading.Event(), threading.Event()
        compose = observer._compose
        reader_thread = None
        def pause_reader(*args):
            if threading.current_thread() is reader_thread:
                began.set()
                release.wait(1)
            return compose(*args)
        errors = []
        def do_read():
            try:
                read(store, contract)
            except observer.SourceObserverError:
                errors.append("superseded")
        with patch.object(observer, "_compose", side_effect=pause_reader):
            reader_thread = threading.Thread(target=do_read)
            reader_thread.start()
            self.assertTrue(began.wait(.5))
            for receipt in receipts.values():
                receipt.update(phase="running", processId=42, processBirthSha256="b" * 64,
                               observedSequence=2)
            store.publish(receipts, now=NOW)
            release.set()
            reader_thread.join(1)
        self.assertFalse(reader_thread.is_alive())
        self.assertEqual(errors, ["superseded"])

    def test_no_implicit_verifier_or_oversized_records(self):
        contract, receipts, digest = fixture()
        with self.assertRaises(observer.SourceObserverError):
            cache(contract, digest, object())
        receipts["quota"]["payload"]["huge"] = "x" * observer.MAX_RECORD_BYTES
        with self.assertRaises(observer.SourceObserverError):
            cache(contract, digest).publish(receipts, now=NOW)


class PrivateVerifierTests(unittest.TestCase):
    def test_pinned_private_bundle_requires_external_provenance_decision(self):
        contract, receipts, _ = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            paths = {}
            for kind in contract["sources"]:
                source, verify = root / (kind + "-source"), root / (kind + "-verifier")
                source.write_bytes(kind.encode())
                verify.write_bytes((kind + "-verifier").encode())
                paths[kind] = observer.ProcedureFiles(source, verify)
            bundle = root / "provenance.json"
            bundle.write_text(json.dumps({"private": "independently captured witness"}))
            bundle.chmod(0o600)
            sha = hashlib.sha256(bundle.read_bytes()).hexdigest()
            received = []
            def authentic(kind, receipt, pin, source_bytes, verifier_bytes, provenance):
                received.append((kind, provenance["private"]))
                return False
            verifier = observer.FrozenPrivateReceiptVerifier(paths, bundle, expected_bundle_sha256=sha,
                                                             provenance_verifier=authentic)
            with self.assertRaises(observer.SourceObserverError):
                verifier.verify_receipt("quota", receipts["quota"], contract["sources"]["quota"])
            self.assertEqual(received, [("quota", "independently captured witness")])
            bundle.chmod(0o644)
            with self.assertRaises(observer.SourceObserverError):
                verifier.verify_receipt("quota", receipts["quota"], contract["sources"]["quota"])
            self.assertEqual(len(received), 1)

    def test_bundle_pin_procedure_pin_and_symlink_drift_refuse_before_authentication(self):
        contract, receipts, _ = fixture()
        for mutation in ["bundle", "source", "verifier", "symlink"]:
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                source, verify, bundle = root / "source", root / "verify", root / "private"
                source.write_bytes(b"quota")
                verify.write_bytes(b"quota-verifier")
                bundle.write_bytes(b"{}")
                bundle.chmod(0o600)
                digest = hashlib.sha256(bundle.read_bytes()).hexdigest()
                procedures = {kind: observer.ProcedureFiles(source, verify) for kind in contract["sources"]}
                seen = []
                instance = observer.FrozenPrivateReceiptVerifier(procedures, bundle,
                    expected_bundle_sha256=digest, provenance_verifier=lambda *args: seen.append(args) or True)
                if mutation == "bundle":
                    bundle.write_bytes(b'{"changed":true}')
                elif mutation == "source":
                    source.write_bytes(b"changed")
                elif mutation == "verifier":
                    verify.write_bytes(b"changed")
                else:
                    other = root / "other"
                    bundle.rename(other)
                    bundle.symlink_to(other)
                with self.assertRaises(observer.SourceObserverError):
                    instance.verify_receipt("quota", receipts["quota"], contract["sources"]["quota"])
                self.assertEqual(seen, [])


class ProducerTests(unittest.TestCase):
    def test_interrupt_during_wait_cancels_invalidates_and_keeps_lock_until_drained(self):
        from unittest.mock import patch
        for interruption in (KeyboardInterrupt, SystemExit):
            with self.subTest(interruption=interruption), tempfile.TemporaryDirectory() as directory:
                contract, receipts, digest = fixture()
                store = cache(contract, digest)
                store.publish(receipts, now=NOW)
                entered, release = threading.Event(), threading.Event()
                def acquire(cancel):
                    entered.set()
                    release.wait(2)
                    return receipts
                lock = Path(directory).resolve() / "lock"
                producer = observer.SourceProducer(store, acquire, lock_path=lock,
                    timeout_seconds=.5, utc_now=lambda: NOW)
                def interrupt_wait(timeout):
                    self.assertTrue(entered.wait(.5))
                    raise interruption("operator interruption")
                try:
                    with patch.object(producer._done, "wait", side_effect=interrupt_wait):
                        with self.assertRaises(interruption):
                            producer.acquire_once()
                    with self.assertRaises(observer.SourceObserverError):
                        read(store, contract)
                    self.assertTrue(producer._cancel.is_set())
                    self.assertFalse(producer.drain(timeout_seconds=0))
                    other = observer.SourceProducer(cache(contract, digest), lambda cancel: receipts,
                        lock_path=lock, timeout_seconds=.1, utc_now=lambda: NOW)
                    with self.assertRaises(observer.SourceObserverError):
                        other.acquire_once()
                finally:
                    release.set()
                    self.assertTrue(producer.drain(timeout_seconds=1))
                with self.assertRaises(observer.SourceObserverError):
                    read(store, contract)

    def test_successful_one_shot_publishes_and_never_retries(self):
        contract, receipts, digest = fixture()
        store = cache(contract, digest)
        with tempfile.TemporaryDirectory() as directory:
            producer = observer.SourceProducer(store, lambda cancelled: receipts,
                lock_path=Path(directory).resolve() / "serialized.lock", timeout_seconds=.5, utc_now=lambda: NOW)
            producer.acquire_once()
            self.assertEqual(read(store, contract).composition.observed_sequence, 1)
            with self.assertRaises(observer.SourceObserverError):
                producer.acquire_once()
            self.assertTrue(producer.drain(timeout_seconds=.5))

    def test_timeout_invalidates_discard_late_results_and_retains_cross_process_lock(self):
        contract, receipts, digest = fixture()
        store = cache(contract, digest)
        store.publish(receipts, now=NOW)
        release = threading.Event()
        entered = threading.Event()
        def stuck(cancelled):
            entered.set()
            release.wait(2)
            return receipts
        with tempfile.TemporaryDirectory() as directory:
            lock = Path(directory).resolve() / "serialized.lock"
            producer = observer.SourceProducer(store, stuck, lock_path=lock,
                                                timeout_seconds=.05, utc_now=lambda: NOW)
            start = time.monotonic()
            try:
                with self.assertRaises(observer.SourceObserverError):
                    producer.acquire_once()
                self.assertLess(time.monotonic() - start, 1)
                self.assertTrue(entered.is_set())
                self.assertFalse(producer.drain(timeout_seconds=0))
                with self.assertRaises(observer.SourceObserverError):
                    read(store, contract)
                other = observer.SourceProducer(cache(contract, digest), lambda cancel: receipts,
                    lock_path=lock, timeout_seconds=.1, utc_now=lambda: NOW)
                with self.assertRaises(observer.SourceObserverError):
                    other.acquire_once()
                code = "import fcntl,sys;f=open(sys.argv[1],'r+');fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB)"
                import subprocess
                refused = subprocess.run([os.sys.executable, "-c", code, str(lock)], capture_output=True)
                self.assertNotEqual(refused.returncode, 0)
            finally:
                release.set()
                self.assertTrue(producer.drain(timeout_seconds=1))
            with self.assertRaises(observer.SourceObserverError):
                read(store, contract)

    def test_failure_and_stop_invalidate_and_raw_exception_is_redacted(self):
        contract, receipts, digest = fixture()
        with tempfile.TemporaryDirectory() as directory:
            def fail(cancelled):
                raise ValueError("secret provider response")
            store = cache(contract, digest)
            store.publish(receipts, now=NOW)
            producer = observer.SourceProducer(store, fail, lock_path=Path(directory).resolve() / "lock",
                                                timeout_seconds=.5, utc_now=lambda: NOW)
            with self.assertRaises(observer.SourceObserverError) as caught:
                producer.acquire_once()
            self.assertNotIn("secret", str(caught.exception))
            with self.assertRaises(observer.SourceObserverError):
                read(store, contract)
            producer.stop()

    def test_deadline_covers_verification_and_stop_reaches_acquirer(self):
        contract, receipts, digest = fixture()
        with tempfile.TemporaryDirectory() as directory:
            release = threading.Event()
            entered = threading.Event()
            class SlowVerifier:
                def verify_receipt(self, *args):
                    entered.set()
                    release.wait(1)
            store = cache(contract, digest, SlowVerifier())
            producer = observer.SourceProducer(store, lambda cancel: receipts,
                lock_path=Path(directory).resolve() / "lock", timeout_seconds=.05, utc_now=lambda: NOW)
            try:
                with self.assertRaises(observer.SourceObserverError):
                    producer.acquire_once()
                self.assertTrue(entered.is_set())
            finally:
                release.set()
                self.assertTrue(producer.drain(timeout_seconds=1))
            with self.assertRaises(observer.SourceObserverError):
                read(store, contract)
        with tempfile.TemporaryDirectory() as directory:
            entered, cancelled = threading.Event(), threading.Event()
            def acquire(cancel):
                entered.set()
                cancelled.set() if cancel.wait(1) else None
                return receipts
            store = cache(contract, digest)
            producer = observer.SourceProducer(store, acquire,
                lock_path=Path(directory).resolve() / "lock", timeout_seconds=.5, utc_now=lambda: NOW)
            errors = []
            def run():
                try:
                    producer.acquire_once()
                except observer.SourceObserverError:
                    errors.append("stopped")
            runner = threading.Thread(target=run)
            runner.start()
            self.assertTrue(entered.wait(.5))
            producer.stop()
            runner.join(1)
            self.assertTrue(cancelled.is_set())
            self.assertEqual(errors, ["stopped"])
            with self.assertRaises(observer.SourceObserverError):
                read(store, contract)

    def test_private_lock_refuses_symlink_or_permissive_file(self):
        contract, receipts, digest = fixture()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / "target"
            target.touch(mode=0o600)
            lock = root / "lock"
            lock.symlink_to(target)
            for bad in ["symlink", "mode"]:
                if bad == "mode":
                    lock.unlink()
                    lock.touch(mode=0o600)
                    lock.chmod(0o644)
                    self.assertEqual(stat.S_IMODE(lock.stat().st_mode), 0o644)
                producer = observer.SourceProducer(cache(contract, digest), lambda cancel: receipts,
                    lock_path=lock, timeout_seconds=.5, utc_now=lambda: NOW)
                with self.assertRaises(observer.SourceObserverError):
                    producer.acquire_once()


if __name__ == "__main__":
    unittest.main()
