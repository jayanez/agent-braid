# SPDX-License-Identifier: AGPL-3.0-only
"""Explicitly fake browser controls; these tests establish no native UI evidence."""

from dataclasses import replace
from datetime import timedelta
import hashlib
import hmac
import json
import threading
import unittest
from unittest.mock import patch

from agent_braid import tooling_interface_observer as ui
from agent_braid.tooling_subscription import operational_binding_from_dict
from tests.test_tooling_codex_sources import fixture, NOW


KEY = b"synthetic-test-key-with-32-bytes!!"
EMAIL = "Owner@Example.test"


class FakeBrowserVerifier:
    def __init__(self):
        self.calls = []
        self.refuse = False

    def verify_browser_read(self, observed, profile, binding, pin, review_sha256, organization_sha256):
        self.calls.append(observed)
        if self.refuse:
            raise ValueError("private browser body and account")


def fixture_ui(host="codex"):
    contract, _, _ = fixture()
    binding = operational_binding_from_dict({**contract["binding"], "host": host})
    profile = ui.NativeProfileWitness(binding.account_sha256, binding.account_namespace_sha256,
        ui.private_email_binding(EMAIL, KEY), ui.key_fingerprint(KEY), NOW, "b" * 64)
    pin = ui.InterfaceSourcePin("browser-reader", "c" * 64, "browser-verifier", "d" * 64)
    raw = ui.BrowserInterfaceRead(EMAIL, False, NOW, "e" * 64, b"fake authenticated interface trace",
        "https://chatgpt.com" if host == "codex" else "https://claude.ai")
    return binding, profile, pin, raw


def adapter(raw=None, host="codex", profile=None, verifier=None, reader=None, **kwargs):
    binding, default_profile, pin, default_raw = fixture_ui(host)
    return ui.InterfaceObserver(binding, profile or default_profile, pin, private_hmac_key=KEY,
        review_sha256="a" * 64, browser_reader=reader or (lambda cancel: raw or default_raw),
        provenance_verifier=verifier or FakeBrowserVerifier(), utc_now=lambda: NOW, **kwargs)


class InterfaceObserverTests(unittest.TestCase):
    def test_actual_read_callback_and_external_verifier_are_both_required(self):
        _, _, _, raw = fixture_ui()
        seen = []
        verifier = FakeBrowserVerifier()
        result = adapter(reader=lambda cancel: seen.append(cancel) or raw, verifier=verifier).capture()
        self.assertEqual(len(seen), 1)
        self.assertEqual(verifier.calls, [raw])
        self.assertFalse(result.auto_recharge_enabled)
        self.assertEqual(result.observed_at, NOW)
        self.assertEqual(result.as_auto_recharge_payload(), {"autoRechargeEnabled": False})
        self.assertNotIn(EMAIL, repr(result))
        self.assertNotIn(EMAIL, json.dumps(result.as_dict()))
        self.assertNotIn("fake authenticated interface trace", json.dumps(result.as_dict()))

    def test_hmac_canonicalization_and_key_fingerprint_match_native_profile(self):
        self.assertEqual(ui.private_email_binding("  OWNER@example.test ", KEY),
                         ui.private_email_binding(EMAIL, KEY))
        _, profile, _, raw = fixture_ui()
        for changed in [replace(profile, email_binding_sha256="f" * 64),
                        replace(profile, key_fingerprint_sha256="f" * 64),
                        replace(profile, account_sha256="f" * 64),
                        replace(profile, account_namespace_sha256="f" * 64)]:
            with self.subTest(changed=changed), self.assertRaises(ui.InterfaceObserverError):
                adapter(raw, profile=changed).capture()
        for email in [None, "", "foo", "a@", "@b", "a@@b", "a b@c"]:
            with self.subTest(email=email), self.assertRaises(ui.InterfaceObserverError):
                ui.private_email_binding(email, KEY)
        with self.assertRaises(ui.InterfaceObserverError):
            ui.private_email_binding(EMAIL, b"weak")

    def test_unicode_casefold_cannot_merge_distinct_profile_emails(self):
        self.assertNotEqual(ui.private_email_binding("strasse@example.test", KEY),
                            ui.private_email_binding("stra\u00dfe@example.test", KEY))

    def test_string_subclass_cannot_rewrite_account_correspondence(self):
        class OtherAccount(str):
            def strip(self):
                return self

            def translate(self, table):
                return "owner@example.test"

        with self.assertRaises(ui.InterfaceObserverError):
            ui.private_email_binding(OtherAccount("attacker@evil.test"), KEY)
        _, _, _, raw = fixture_ui()
        with self.assertRaises(ui.InterfaceObserverError):
            adapter(replace(raw, account_email=OtherAccount("attacker@evil.test"))).capture()

    def test_malformed_email_or_method_has_redacted_typed_refusal(self):
        for email, method in (("\ud800@example.test", "interface-email-v1"), (EMAIL, []),
                              (EMAIL, {}), (EMAIL, "unknown")):
            with self.subTest(method=type(method).__name__), self.assertRaises(ui.InterfaceObserverError):
                ui.private_email_binding(email, KEY, method=method)
        for method in ([], {}, None):
            with self.assertRaises(ui.InterfaceObserverError):
                ui.key_fingerprint(KEY, method=method)

    def test_archived_claude_hmac_method_is_explicit_and_matches_independent_vectors(self):
        method = "claude-account-email-v1"
        expected = hmac.new(KEY, b"agent-braid-m45-account-email-v1\0owner@example.test",
                            hashlib.sha256).hexdigest()
        short_fingerprint = hmac.new(KEY, b"agent-braid-m45-key-fingerprint-v1",
                                     hashlib.sha256).hexdigest()[:16]
        fingerprint_digest = hashlib.sha256(short_fingerprint.encode("ascii")).hexdigest()
        self.assertEqual(expected, ui.private_email_binding(EMAIL, KEY, method=method))
        self.assertEqual(fingerprint_digest, ui.key_fingerprint(KEY, method=method))
        binding, profile, pin, raw = fixture_ui("claude-code")
        archived = replace(profile, email_binding_sha256=expected,
                           key_fingerprint_sha256=fingerprint_digest, email_binding_method=method)
        value = adapter(raw, host="claude-code", profile=archived,
                        organization_declaration_sha256="f" * 64).capture()
        self.assertFalse(value.auto_recharge_enabled)
        self.assertEqual(method, value.as_dict()["emailBindingMethod"])
        with self.assertRaises(ui.InterfaceObserverError):
            adapter(raw, host="claude-code", profile=replace(archived, email_binding_method="interface-email-v1"),
                    organization_declaration_sha256="f" * 64).capture()

    def test_unknown_missing_non_boolean_and_enabled_controls_refuse(self):
        _, _, _, raw = fixture_ui()
        for bad in [None, "false", 0, 1, True]:
            with self.subTest(bad=bad), self.assertRaises(ui.InterfaceObserverError):
                adapter(replace(raw, auto_recharge_enabled=bad)).capture()
        with self.assertRaises(ui.InterfaceObserverError):
            adapter(reader=lambda cancel: {"autoRechargeEnabled": False}).capture()

    def test_same_authenticated_session_origin_and_trace_are_verified(self):
        _, _, _, raw = fixture_ui()
        for changed in [replace(raw, session_binding_sha256=None), replace(raw, trace=b""),
                        replace(raw, origin="https://untrusted.test"),
                        replace(raw, origin="https://chatgpt.com?token=private"),
                        replace(raw, account_email="other@example.test")]:
            verifier = FakeBrowserVerifier()
            with self.subTest(changed=changed), self.assertRaises(ui.InterfaceObserverError):
                adapter(changed, verifier=verifier).capture()
            self.assertEqual(verifier.calls, [])
        verifier = FakeBrowserVerifier()
        verifier.refuse = True
        with self.assertRaises(ui.InterfaceObserverError) as caught:
            adapter(raw, verifier=verifier).capture()
        self.assertNotIn("private browser", str(caught.exception))

    def test_codex_freshness_has_no_900_second_exception(self):
        _, profile, _, raw = fixture_ui()
        for seconds in [61, -1]:
            with self.subTest(seconds=seconds), self.assertRaises(ui.InterfaceObserverError):
                adapter(replace(raw, observed_at=NOW - timedelta(seconds=seconds))).capture()
        with self.assertRaises(ui.InterfaceObserverError):
            adapter(max_age_seconds=900)
        result = adapter(replace(raw, observed_at=NOW - timedelta(seconds=60)),
                         profile=replace(profile, observed_at=NOW - timedelta(seconds=60))).capture()
        self.assertEqual(result.valid_until, NOW)

    def test_claude_org_declaration_and_original_900_second_observation(self):
        _, profile, _, raw = fixture_ui("claude-code")
        old = NOW - timedelta(seconds=850)
        result = adapter(replace(raw, observed_at=old), host="claude-code",
            profile=replace(profile, observed_at=old), max_age_seconds=900,
            organization_declaration_sha256="f" * 64).capture()
        payload = result.as_auto_recharge_payload()
        self.assertEqual(payload["organizationBinding"], "owner-declared-single-organization")
        self.assertEqual(payload["uiObservedAt"], old.isoformat())
        self.assertEqual(payload["profileObservedAt"], old.isoformat())
        self.assertEqual(result.valid_until, old + timedelta(seconds=900))
        self.assertEqual(payload["collectorReceiptSha256"], profile.profile_receipt_sha256)
        with self.assertRaises(ui.InterfaceObserverError):
            adapter(host="claude-code")
        with self.assertRaises(ui.InterfaceObserverError):
            adapter(host="claude-code", max_age_seconds=901, organization_declaration_sha256="f" * 64)

    def test_profile_ui_skew_future_timestamps_and_clock_regression_refuse(self):
        _, profile, _, raw = fixture_ui()
        for changed in [replace(raw, observed_at=NOW.replace(tzinfo=None)),
                        replace(raw, observed_at=NOW + timedelta(seconds=1))]:
            with self.subTest(changed=changed), self.assertRaises(ui.InterfaceObserverError):
                adapter(changed).capture()
        with self.assertRaises(ui.InterfaceObserverError):
            adapter(profile=replace(profile, observed_at=NOW + timedelta(seconds=1))).capture()
        with self.assertRaises(ui.InterfaceObserverError):
            adapter(profile=replace(profile, observed_at=NOW - timedelta(seconds=61))).capture()
        instance = adapter()
        instance._now = iter([NOW, NOW - timedelta(seconds=1)]).__next__
        with self.assertRaises(ui.InterfaceObserverError):
            instance.capture()

    def test_deadline_covers_browser_and_verification_and_late_result_is_discarded(self):
        for slow_stage in ["browser", "verifier"]:
            with self.subTest(slow_stage=slow_stage):
                release, entered = threading.Event(), threading.Event()
                _, _, _, raw = fixture_ui()
                def reader(cancel):
                    if slow_stage == "browser":
                        entered.set()
                        release.wait(1)
                    return raw
                class Verifier(FakeBrowserVerifier):
                    def verify_browser_read(self, *args):
                        if slow_stage == "verifier":
                            entered.set()
                            release.wait(1)
                instance = adapter(reader=reader, verifier=Verifier(), timeout_seconds=.02)
                try:
                    with self.assertRaises(ui.InterfaceObserverError):
                        instance.capture()
                    self.assertTrue(entered.is_set())
                    self.assertFalse(instance.drain(timeout_seconds=0))
                    with self.assertRaises(ui.InterfaceObserverError):
                        instance.capture()
                finally:
                    release.set()
                    self.assertTrue(instance.drain(timeout_seconds=1))

    def test_cancellation_and_interrupts_propagate_after_cleanup(self):
        _, _, _, raw = fixture_ui()
        external_cancel = threading.Event()
        external_cancel.set()
        seen = []
        with self.assertRaises(ui.InterfaceObserverError):
            adapter(reader=lambda cancel: seen.append(1) or raw).capture(cancel_event=external_cancel)
        self.assertEqual(seen, [])
        for interruption in (KeyboardInterrupt, SystemExit):
            instance = adapter()
            with patch.object(instance._done, "wait", side_effect=interruption):
                with self.assertRaises(interruption):
                    instance.capture()
            self.assertTrue(instance._cancel.is_set())
            self.assertTrue(instance.drain(timeout_seconds=1))

    def test_verifier_unavailable_or_non_acceptance_cannot_bless_a_false_boolean(self):
        with self.assertRaises(ui.InterfaceObserverError):
            adapter(verifier=object())
        class AmbiguousVerifier:
            def verify_browser_read(self, *args):
                return False
        with self.assertRaises(ui.InterfaceObserverError):
            adapter(verifier=AmbiguousVerifier()).capture()

    def test_original_reader_and_profile_objects_cannot_mutate_checked_snapshot(self):
        _, profile, _, raw = fixture_ui()
        class Verifier:
            def verify_browser_read(self, observed, native, *args):
                self_observed = observed
                object.__setattr__(raw, "auto_recharge_enabled", True)
                object.__setattr__(profile, "account_sha256", "f" * 64)
                self.assertion = (self_observed.auto_recharge_enabled, native.account_sha256)
        verifier = Verifier()
        result = adapter(raw, profile=profile, verifier=verifier).capture()
        self.assertEqual(verifier.assertion, (False, result.binding.account_sha256))
        self.assertFalse(result.auto_recharge_enabled)
        self.assertEqual(result.native_profile.account_sha256, result.binding.account_sha256)

    def test_validation_runs_after_slow_verification_without_retimestamping(self):
        instance = adapter()
        instance._now = iter([NOW, NOW, NOW + timedelta(seconds=61)]).__next__
        with self.assertRaises(ui.InterfaceObserverError):
            instance.capture()

    def test_pending_external_cancellation_reaches_reader_and_discards_output(self):
        entered, release, external = threading.Event(), threading.Event(), threading.Event()
        _, _, _, raw = fixture_ui()
        def reader(cancel):
            entered.set()
            release.wait(1)
            return raw
        instance = adapter(reader=reader, timeout_seconds=.5)
        errors = []
        def capture():
            try:
                instance.capture(cancel_event=external)
            except ui.InterfaceObserverError:
                errors.append("cancelled")
        worker = threading.Thread(target=capture)
        worker.start()
        try:
            self.assertTrue(entered.wait(.5))
            external.set()
            worker.join(.5)
            self.assertFalse(worker.is_alive())
            self.assertTrue(instance._cancel.is_set())
            self.assertEqual(errors, ["cancelled"])
        finally:
            release.set()
            self.assertTrue(instance.drain(timeout_seconds=1))

    def test_external_cancellation_at_completed_wait_boundary_discards_verified_result(self):
        external = threading.Event()
        instance = adapter()
        real_wait = instance._done.wait
        def cancel_after_completion(timeout):
            completed = real_wait(timeout)
            if completed:
                external.set()
            return completed
        with patch.object(instance._done, "wait", side_effect=cancel_after_completion):
            with self.assertRaises(ui.InterfaceObserverError):
                instance.capture(cancel_event=external)
        self.assertTrue(instance._cancel.is_set())
        self.assertTrue(instance.drain(timeout_seconds=1))
        with self.assertRaises(ui.InterfaceObserverError):
            instance.capture(cancel_event=external)


if __name__ == "__main__":
    unittest.main()
