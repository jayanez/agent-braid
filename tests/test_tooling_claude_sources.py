# SPDX-License-Identifier: AGPL-3.0-only
"""Offline negative controls; no native-source authentication is claimed."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone, tzinfo
import unittest

from agent_braid import tooling_claude_sources as sources
from agent_braid import tooling_subscription as subscription
from tests.test_tooling_subscription import _operational_policy, _sha


NOW = datetime(2026, 10, 13, 12, tzinfo=timezone.utc)
SUFFIX = "0a1b2c3d"
COLLECTOR = _sha("collector-receipt")


def iso(value):
    return value.isoformat()


def fixture():
    policy = _operational_policy()
    binding = subscription.OperationalProcessRouteBinding(
        "claude-code", _sha("registration"), "slot-1", subscription.policy_sha256(policy),
        _sha("a"), _sha("a-ns"), _sha("build"), _sha("artifact"), _sha("exe"),
        _sha("config"), _sha("argv"), _sha("model"), "observer", _sha("observer"),
        "verifier", _sha("verifier"), 30,
    ).as_dict()
    contract = {
        "schema": sources.CONTRACT_SCHEMA, "binding": binding, "additionalSpendCapEur": 0,
        "isolatedStore": {"keychainSuffix": SUFFIX},
        "organizationScope": {"binding": "owner-declared-single-organization",
                              "declarationSha256": _sha("declaration")},
        "sourceMaxAgeSeconds": {"quota": 30, "autoRecharge": 600, "process": 30},
        "sources": {kind: {"sourceRef": kind, "sourceSha256": _sha(kind),
                           "verifierRef": kind + "-verifier", "verifierSha256": _sha(kind + "-verifier")}
                    for kind in sources.KINDS},
    }
    digest = sources.source_contract_sha256(contract)
    payloads = {
        "quota": {"extraUsageEnabled": False,
                  "quotaWindows": {
                      "fiveHour": {"usedPct": 2.0, "resetsAt": iso(NOW + timedelta(hours=3))},
                      "sevenDay": {"usedPct": 12, "resetsAt": iso(NOW + timedelta(days=6))}}},
        "autoRecharge": {"autoRechargeEnabled": False, "basis": "interface-observation",
                         "accountBound": True,
                         "organizationBinding": "owner-declared-single-organization",
                         "uiObservedAt": iso(NOW - timedelta(seconds=300)),
                         "profileObservedAt": iso(NOW - timedelta(seconds=310)),
                         "collectorReceiptSha256": COLLECTOR,
                         "recorderRecordSha256": _sha("recorder-record")},
        "process": {"authMethod": "claude.ai", "route": "included-subscription-quota",
                    "storeBinding": "bound", "keychainSuffix": SUFFIX, "collectorReceiptSha256": COLLECTOR,
                    **{field: True for field in sources.PROCESS_TRUE | sources.LAUNCH_TRUE},
                    **{field: False for field in sources.PROCESS_FALSE | sources.LAUNCH_FALSE}},
    }
    receipts = {kind: {"schema": sources.RECEIPT_SCHEMA, "kind": kind,
                       "contractSha256": digest, "binding": deepcopy(binding),
                       "phase": "prelaunch", "processId": None, "processBirthSha256": None,
                       "observedSequence": 1, "observedAt": iso(NOW), "payload": payloads[kind],
                       **contract["sources"][kind]} for kind in sources.KINDS}
    return contract, receipts, digest


def get(payload, path):
    for part in path[:-1]:
        payload = payload[part]
    return payload


class ClaudeSourceContractTests(unittest.TestCase):
    def check(self, contract, receipts, digest, **kwargs):
        return sources.compose_claude_sources(contract, receipts,
                                              expected_contract_sha256=digest, now=NOW, **kwargs)

    def refuses(self, contract, receipts, digest, message=None, **kwargs):
        with self.assertRaises(subscription.SubscriptionError) as caught:
            self.check(contract, receipts, digest, **kwargs)
        if message is not None:
            self.assertIn(message, str(caught.exception))

    def test_composes_exact_claims_without_inventing_v3_booleans(self):
        contract, receipts, digest = fixture()
        before = deepcopy((contract, receipts))
        result = self.check(contract, receipts, digest)
        self.assertEqual(result.valid_until, NOW + timedelta(seconds=30))
        self.assertEqual(len(result.receipt_sha256), 3)
        self.assertEqual(result.keychain_suffix, SUFFIX)
        self.assertEqual(result.binding.host, "claude-code")
        self.assertNotIsInstance(result, subscription.OperationalProcessRouteObservation)
        with self.assertRaises(subscription.SubscriptionError):
            subscription.check_observation(result, result.binding, now=NOW)
        self.assertEqual(before, (contract, receipts))

    def test_composition_reads_a_snapshot_not_the_caller_objects(self):
        class Shifty(dict):
            """Serializes safely but would answer unsafely if read again through item access."""
            def __getitem__(self, key):
                return True if key == "extraUsageEnabled" else super().__getitem__(key)
        contract, receipts, digest = fixture()
        receipts["quota"]["payload"] = Shifty(receipts["quota"]["payload"])
        self.assertEqual(self.check(contract, receipts, digest).valid_until, NOW + timedelta(seconds=30))

    def test_refuses_each_missing_unknown_non_boolean_and_unsafe_control(self):
        cases = [
            ("quota", ("extraUsageEnabled",), False),
            ("autoRecharge", ("autoRechargeEnabled",), False),
            ("autoRecharge", ("accountBound",), True),
            *[("process", (field,), True) for field in sources.PROCESS_TRUE | sources.LAUNCH_TRUE],
            *[("process", (field,), False) for field in sources.PROCESS_FALSE | sources.LAUNCH_FALSE],
        ]
        for kind, path, safe in cases:
            for bad in [None, "unknown", 0, 1, not safe, "missing"]:
                with self.subTest(kind=kind, path=path, bad=bad):
                    contract, receipts, digest = fixture()
                    payload = get(receipts[kind]["payload"], path)
                    if bad == "missing":
                        del payload[path[-1]]
                    else:
                        payload[path[-1]] = bad
                    self.refuses(contract, receipts, digest)

    def test_every_source_must_be_fresh_pinned_and_bound(self):
        for kind, limit in (("quota", 30), ("process", 30), ("autoRecharge", 600)):
            mutations = [
                ("observedAt", iso(NOW - timedelta(seconds=limit + 1))),
                ("observedAt", iso(NOW + timedelta(seconds=1))),
                ("observedAt", NOW.replace(tzinfo=None).isoformat()),
                ("observedAt", None), ("sourceSha256", _sha("drift")),
                ("verifierRef", "other"), ("contractSha256", _sha("other")),
                ("observedSequence", 2), ("schema", "v3"),
            ]
            for field, value in mutations:
                with self.subTest(kind=kind, field=field):
                    contract, receipts, digest = fixture()
                    receipts[kind][field] = value
                    self.refuses(contract, receipts, digest)
            for field in ["accountSha256", "accountNamespaceSha256", "candidateArtifactSha256",
                          "executableSha256", "configSha256", "argvSha256", "modelIdentitySha256",
                          "registrationSha256", "hostBuildSha256", "policySha256"]:
                with self.subTest(kind=kind, binding=field):
                    contract, receipts, digest = fixture()
                    receipts[kind]["binding"][field] = _sha("drift")
                    self.refuses(contract, receipts, digest)

    def test_per_source_age_limits_are_independent(self):
        contract, receipts, digest = fixture()
        receipts["autoRecharge"]["observedAt"] = iso(NOW - timedelta(seconds=299))
        receipts["autoRecharge"]["payload"]["uiObservedAt"] = iso(NOW - timedelta(seconds=299))
        receipts["autoRecharge"]["payload"]["profileObservedAt"] = iso(NOW - timedelta(seconds=305))
        self.check(contract, receipts, digest)
        receipts["quota"]["observedAt"] = iso(NOW - timedelta(seconds=299))
        self.refuses(contract, receipts, digest)

    def test_quota_windows_and_extra_usage(self):
        bads = [100, 100.0, 101, -0.1, float("nan"), float("inf"), True, "5", None]
        for window in ("fiveHour", "sevenDay"):
            for bad in bads:
                with self.subTest(window=window, usedPct=bad):
                    contract, receipts, digest = fixture()
                    receipts["quota"]["payload"]["quotaWindows"][window]["usedPct"] = bad
                    self.refuses(contract, receipts, digest)
            for field, value in (("resetsAt", iso(NOW - timedelta(seconds=1))),
                                 ("resetsAt", iso(NOW)), ("resetsAt", NOW.replace(tzinfo=None).isoformat()),
                                 ("resetsAt", None), ("resetsAt", 7)):
                with self.subTest(window=window, field=field, value=str(value)[:12]):
                    contract, receipts, digest = fixture()
                    receipts["quota"]["payload"]["quotaWindows"][window][field] = value
                    self.refuses(contract, receipts, digest)
            contract, receipts, digest = fixture()
            del receipts["quota"]["payload"]["quotaWindows"][window]
            self.refuses(contract, receipts, digest)
        contract, receipts, digest = fixture()
        receipts["quota"]["payload"]["quotaWindows"]["sonnet"] = {"usedPct": 1, "resetsAt": iso(NOW + timedelta(days=1))}
        self.refuses(contract, receipts, digest)
        contract, receipts, digest = fixture()
        receipts["quota"]["payload"]["quotaWindows"]["fiveHour"]["usedPct"] = 99.9
        self.check(contract, receipts, digest)

    def test_auto_recharge_requires_account_bound_interface_basis(self):
        mutations = [
            ("basis", "api-prepaid"), ("basis", None), ("basis", "unknown"),
            ("organizationBinding", "bound"), ("organizationBinding", "unbound"),
            ("organizationBinding", None), ("organizationBinding", "owner-declared-multiple"),
            ("uiObservedAt", iso(NOW + timedelta(seconds=1))),
            ("uiObservedAt", iso(NOW - timedelta(seconds=601))),  # older than the limit

            ("uiObservedAt", (NOW - timedelta(seconds=5)).replace(tzinfo=None).isoformat()),
            ("uiObservedAt", None),
            ("profileObservedAt", iso(NOW - timedelta(seconds=911))),
            ("profileObservedAt", iso(NOW + timedelta(seconds=1))),
            ("profileObservedAt", None),
            ("collectorReceiptSha256", "abc"), ("collectorReceiptSha256", _sha("other-collector")),
            ("recorderRecordSha256", "abc"), ("recorderRecordSha256", None),
        ]
        for field, value in mutations:
            with self.subTest(field=field, value=str(value)[:14]):
                contract, receipts, digest = fixture()
                receipts["autoRecharge"]["payload"][field] = value
                self.refuses(contract, receipts, digest)
        contract, receipts, digest = fixture()
        del receipts["autoRecharge"]["payload"]["basis"]
        self.refuses(contract, receipts, digest)
        contract, receipts, digest = fixture()
        receipts["autoRecharge"]["payload"]["extra"] = 1
        self.refuses(contract, receipts, digest)

    def test_interface_time_must_be_close_to_profile_and_fresh_itself(self):
        contract, receipts, digest = fixture()
        payload = receipts["autoRecharge"]["payload"]
        ui = NOW - timedelta(seconds=300)
        payload["uiObservedAt"] = iso(ui)
        payload["profileObservedAt"] = iso(ui - timedelta(seconds=600))      # exactly 600 s before
        self.check(contract, receipts, digest)
        payload["profileObservedAt"] = iso(ui - timedelta(seconds=600, microseconds=1))
        self.refuses(contract, receipts, digest)
        payload["profileObservedAt"] = iso(ui + timedelta(seconds=5))          # profile after the UI read
        self.check(contract, receipts, digest)
        payload["profileObservedAt"] = iso(NOW + timedelta(microseconds=1))    # profile after the receipt
        self.refuses(contract, receipts, digest)
        payload["uiObservedAt"] = iso(NOW - timedelta(seconds=600))          # exactly at the age limit
        payload["profileObservedAt"] = iso(NOW - timedelta(seconds=610))
        self.check(contract, receipts, digest)
        payload["uiObservedAt"] = iso(NOW - timedelta(seconds=600, microseconds=1))
        self.refuses(contract, receipts, digest)

    def with_limits(self, contract, receipts, **limits):
        contract["sourceMaxAgeSeconds"].update(limits)
        digest = sources.source_contract_sha256(contract)
        for receipt in receipts.values():
            receipt["contractSha256"] = digest
        return digest

    def test_time_ordering_rules_each_refuse_for_their_own_reason(self):
        # quota reset must be in the future at the check time, not only after the receipt
        contract, receipts, digest = fixture()
        receipts["quota"]["observedAt"] = iso(NOW - timedelta(seconds=10))
        receipts["quota"]["payload"]["quotaWindows"]["fiveHour"]["resetsAt"] = iso(NOW - timedelta(seconds=5))
        self.refuses(contract, receipts, digest, "reset is not in the future")
        # the interface read cannot be later than its own receipt
        contract, receipts, digest = fixture()
        receipts["autoRecharge"]["observedAt"] = iso(NOW - timedelta(seconds=100))
        receipts["autoRecharge"]["payload"]["uiObservedAt"] = iso(NOW - timedelta(seconds=50))
        receipts["autoRecharge"]["payload"]["profileObservedAt"] = iso(NOW - timedelta(seconds=60))
        self.refuses(contract, receipts, digest, "from the future")
        # staleness is judged at the check time, not at the receipt time
        contract, receipts, digest = fixture()
        receipts["autoRecharge"]["observedAt"] = iso(NOW - timedelta(seconds=500))
        receipts["autoRecharge"]["payload"]["uiObservedAt"] = iso(NOW - timedelta(seconds=800))
        receipts["autoRecharge"]["payload"]["profileObservedAt"] = iso(NOW - timedelta(seconds=800))
        self.refuses(contract, receipts, digest, "interface observation is stale")
        # skew is symmetric: a profile read long after the interface read is refused too
        contract, receipts, digest = fixture()
        digest = self.with_limits(contract, receipts, autoRecharge=900)
        receipts["autoRecharge"]["payload"]["uiObservedAt"] = iso(NOW - timedelta(seconds=800))
        receipts["autoRecharge"]["payload"]["profileObservedAt"] = iso(NOW - timedelta(seconds=100))
        self.refuses(contract, receipts, digest, "too far from the profile read")
        receipts["autoRecharge"]["payload"]["profileObservedAt"] = iso(NOW - timedelta(seconds=200))
        self.check(contract, receipts, digest)

    def test_accepted_boundaries(self):
        contract, receipts, digest = fixture()
        for kind, limit in (("quota", 30), ("process", 30)):
            receipts[kind]["observedAt"] = iso(NOW - timedelta(seconds=limit))
        result = self.check(contract, receipts, digest)
        self.assertEqual(result.valid_until, NOW)          # inclusive: expiry equals the check time
        contract, receipts, digest = fixture()
        digest = self.with_limits(contract, receipts, autoRecharge=900)
        self.check(contract, receipts, digest)
        contract, receipts, digest = fixture()
        receipts["quota"]["payload"]["quotaWindows"]["fiveHour"]["usedPct"] = 0
        self.check(contract, receipts, digest)

    def test_malformed_values_are_refused_for_the_right_reason(self):
        for suffix in ("0a1b2c3d0", "0a1b2c3d\n", "0a1b2c3", "0a1b2c3g", "0a1b2c3d "):
            with self.subTest(suffix=repr(suffix)):
                contract, receipts, digest = fixture()
                contract["isolatedStore"]["keychainSuffix"] = suffix
                with self.assertRaises(subscription.SubscriptionError) as caught:
                    sources.source_contract_sha256(contract)
                self.assertIn("eight lowercase hex", str(caught.exception))
        # equal on both sides must still be a well-formed SHA-256
        contract, receipts, digest = fixture()
        for kind in ("autoRecharge", "process"):
            receipts[kind]["payload"]["collectorReceiptSha256"] = "abc"
        self.refuses(contract, receipts, digest, "lowercase SHA-256")
        contract, receipts, digest = fixture()
        receipts["autoRecharge"]["payload"]["recorderRecordSha256"] = _sha("x").upper()
        self.refuses(contract, receipts, digest, "lowercase SHA-256")
        contract, receipts, digest = fixture()
        receipts["process"]["payload"]["collectorReceiptSha256"] = "abc"      # process side alone
        self.refuses(contract, receipts, digest, "lowercase SHA-256")

    def test_huge_numbers_refuse_with_the_domain_error(self):
        contract, receipts, digest = fixture()
        receipts["quota"]["payload"]["quotaWindows"]["fiveHour"]["usedPct"] = 10 ** 400
        self.refuses(contract, receipts, digest)
        for kind in sources.KINDS:
            contract, receipts, digest = fixture()
            contract["sourceMaxAgeSeconds"][kind] = 10 ** 400
            with self.assertRaises(subscription.SubscriptionError):
                sources.source_contract_sha256(contract)

    def test_prelaunch_birth_without_pid_and_pid_without_birth_refuse(self):
        contract, receipts, digest = fixture()
        receipts["quota"]["processBirthSha256"] = _sha("birth")
        self.refuses(contract, receipts, digest, "prelaunch")
        contract, receipts, digest = fixture()
        for receipt in receipts.values():
            receipt.update(phase="running", processId=7, processBirthSha256=None)
        self.refuses(contract, receipts, digest)
        for bad in (None, 0, -1, True, "7", 1.0):
            with self.subTest(processId=bad):
                contract, receipts, digest = fixture()
                for receipt in receipts.values():
                    receipt.update(phase="running", processId=bad, processBirthSha256=_sha("birth"))
                self.refuses(contract, receipts, digest, "positive process ID")

    def test_validity_is_each_sources_own_expiry(self):
        contract, receipts, digest = fixture()
        receipts["quota"]["observedAt"] = iso(NOW - timedelta(seconds=25))
        self.assertEqual(self.check(contract, receipts, digest).valid_until, NOW + timedelta(seconds=5))
        contract, receipts, digest = fixture()
        receipts["process"]["observedAt"] = iso(NOW - timedelta(seconds=25))
        self.assertEqual(self.check(contract, receipts, digest).valid_until, NOW + timedelta(seconds=5))
        for window in ("fiveHour", "sevenDay"):
            contract, receipts, digest = fixture()
            receipts["quota"]["payload"]["quotaWindows"][window]["resetsAt"] = iso(NOW + timedelta(seconds=10))
            self.assertEqual(self.check(contract, receipts, digest).valid_until, NOW + timedelta(seconds=10))

    def test_lifecycle_rules_refuse_on_their_own_when_all_receipts_agree(self):
        cases = [
            ("prelaunch with a PID", dict(phase="prelaunch", processId=7, processBirthSha256=None), "prelaunch"),
            ("prelaunch with a birth", dict(phase="prelaunch", processId=None, processBirthSha256=_sha("b")), "prelaunch"),
            ("unknown phase", dict(phase="bogus", processId=7, processBirthSha256=_sha("b")), "invalid source process phase"),
            ("sequence zero", dict(observedSequence=0), "positive integer"),
            ("sequence negative", dict(observedSequence=-1), "positive integer"),
            ("sequence bool", dict(observedSequence=True), "positive integer"),
            ("sequence float", dict(observedSequence=1.0), "positive integer"),
            ("running without birth", dict(phase="running", processId=7, processBirthSha256=None), "lowercase SHA-256"),
        ]
        for label, fields, message in cases:
            with self.subTest(label):
                contract, receipts, digest = fixture()
                for receipt in receipts.values():
                    receipt.update(fields)
                self.refuses(contract, receipts, digest, message)
        contract, receipts, digest = fixture()
        receipts["quota"]["kind"] = "process"
        self.refuses(contract, receipts, digest, "contract or kind mismatch")

    def test_time_values_need_an_explicit_offset_and_are_converted_to_utc(self):
        naive = NOW.replace(tzinfo=None).isoformat()
        contract, receipts, digest = fixture()
        receipts["quota"]["observedAt"] = naive
        self.refuses(contract, receipts, digest, "invalid source timestamp")
        contract, receipts, digest = fixture()
        receipts["quota"]["payload"]["quotaWindows"]["fiveHour"]["resetsAt"] = (NOW + timedelta(hours=3)).replace(tzinfo=None).isoformat()
        self.refuses(contract, receipts, digest, "invalid quota reset time")
        for field in ("uiObservedAt", "profileObservedAt"):
            contract, receipts, digest = fixture()
            receipts["autoRecharge"]["payload"][field] = (NOW - timedelta(seconds=300)).replace(tzinfo=None).isoformat()
            self.refuses(contract, receipts, digest, "interface observation time" if field == "uiObservedAt" else "profile read time")
        past_in_utc = "2026-10-13T13:00:00+05:00"        # 08:00Z, already past at 12:00Z
        future_in_utc = "2026-10-13T20:00:00+05:00"      # 15:00Z
        contract, receipts, digest = fixture()
        receipts["quota"]["payload"]["quotaWindows"]["fiveHour"]["resetsAt"] = past_in_utc
        self.refuses(contract, receipts, digest, "reset is not in the future")
        receipts["quota"]["payload"]["quotaWindows"]["fiveHour"]["resetsAt"] = future_in_utc
        self.assertEqual(self.check(contract, receipts, digest).valid_until, NOW + timedelta(seconds=30))
        class NoOffset(tzinfo):
            def utcoffset(self, value):
                return None
        with self.assertRaises(subscription.SubscriptionError):
            sources.compose_claude_sources(contract, receipts, expected_contract_sha256=digest,
                                           now=datetime(2026, 10, 13, 12, tzinfo=NoOffset()))

    def test_contract_and_receipt_shapes_are_exact(self):
        contract, receipts, digest = fixture()
        contract["schema"] = "agent-braid-claude-source-contract-v2"
        with self.assertRaises(subscription.SubscriptionError) as caught:
            sources.source_contract_sha256(contract)
        self.assertIn("unsupported Claude source contract", str(caught.exception))
        contract, receipts, digest = fixture()
        contract["sources"]["other"] = dict(contract["sources"]["quota"])
        with self.assertRaises(subscription.SubscriptionError) as caught:
            sources.source_contract_sha256(contract)
        self.assertIn("invalid source pins fields", str(caught.exception))
        contract, receipts, digest = fixture()
        contract["sources"]["quota"]["note"] = "x"
        with self.assertRaises(subscription.SubscriptionError) as caught:
            sources.source_contract_sha256(contract)
        self.assertIn("invalid source pin fields", str(caught.exception))
        contract, receipts, digest = fixture()
        contract["isolatedStore"]["keychainSuffix"] = 12345678
        with self.assertRaises(subscription.SubscriptionError) as caught:
            sources.source_contract_sha256(contract)
        self.assertIn("eight lowercase hex", str(caught.exception))
        for kind in sources.KINDS:
            contract, receipts, digest = fixture()
            receipts[kind]["extra"] = 1
            self.refuses(contract, receipts, digest, "invalid source receipt fields")
            contract, receipts, digest = fixture()
            del receipts[kind]["observedSequence"]
            self.refuses(contract, receipts, digest, "invalid source receipt fields")
        contract, receipts, digest = fixture()
        receipts["other"] = receipts["quota"]
        self.refuses(contract, receipts, digest, "invalid source receipts fields")

    def test_contract_field_types_and_pins_are_strict(self):
        for value in (False, 0.0, 1, "0", None):
            with self.subTest(cap=value):
                contract, receipts, digest = fixture()
                contract["additionalSpendCapEur"] = value
                with self.assertRaises(subscription.SubscriptionError) as caught:
                    sources.source_contract_sha256(contract)
                self.assertIn("integer EUR zero", str(caught.exception))
        for field, bad, message in (("sourceRef", "  ", "nonempty"), ("verifierRef", "", "nonempty"),
                                    ("sourceSha256", "a" * 63, "lowercase SHA-256"),
                                    ("verifierSha256", "a" * 65, "lowercase SHA-256"),
                                    ("sourceSha256", ("a" * 63) + "G", "lowercase SHA-256")):
            with self.subTest(pin=field, bad=bad[:6]):
                contract, receipts, digest = fixture()
                contract["sources"]["quota"][field] = bad
                with self.assertRaises(subscription.SubscriptionError) as caught:
                    sources.source_contract_sha256(contract)
                self.assertIn(message, str(caught.exception))
        for bad in ("a" * 63, "a" * 65):
            contract, receipts, digest = fixture()
            with self.assertRaises(subscription.SubscriptionError):
                sources.compose_claude_sources(contract, receipts, expected_contract_sha256=bad, now=NOW)

    def test_process_store_and_cross_source_binding(self):
        mutations = [("storeBinding", "mismatch"), ("storeBinding", "unknown"), ("storeBinding", True),
                     ("keychainSuffix", "ffffffff"), ("keychainSuffix", "0A1B2C3D"), ("keychainSuffix", None),
                     ("authMethod", "chatgpt"), ("authMethod", "claude"), ("route", "api"),
                     ("collectorReceiptSha256", _sha("other-collector")), ("collectorReceiptSha256", "x")]
        for field, value in mutations:
            with self.subTest(field=field, value=str(value)[:10]):
                contract, receipts, digest = fixture()
                receipts["process"]["payload"][field] = value
                self.refuses(contract, receipts, digest)

    def test_process_lifecycle_and_identity_conflicts(self):
        contract, receipts, digest = fixture()
        for receipt in receipts.values():
            receipt.update(phase="running", processId=4321, processBirthSha256=_sha("birth"))
        result = self.check(contract, receipts, digest)
        self.assertEqual(result.process_id, 4321)
        receipts["quota"]["processBirthSha256"] = _sha("another-process")
        self.refuses(contract, receipts, digest)
        contract, receipts, digest = fixture()
        receipts["quota"].update(phase="running")
        self.refuses(contract, receipts, digest)
        contract, receipts, digest = fixture()
        receipts["quota"].update(processId=1)
        self.refuses(contract, receipts, digest)

    def test_validity_is_the_earliest_of_age_limits_ui_time_and_quota_reset(self):
        contract, receipts, digest = fixture()
        self.assertEqual(self.check(contract, receipts, digest).valid_until, NOW + timedelta(seconds=30))
        contract["binding"]["maxAgeSeconds"] = 60
        for receipt in receipts.values():
            receipt["binding"]["maxAgeSeconds"] = 60
        contract["sourceMaxAgeSeconds"].update(quota=60, process=60, autoRecharge=100)
        digest = sources.source_contract_sha256(contract)
        for receipt in receipts.values():
            receipt["contractSha256"] = digest
        receipts["autoRecharge"]["payload"]["uiObservedAt"] = iso(NOW - timedelta(seconds=90))
        receipts["autoRecharge"]["payload"]["profileObservedAt"] = iso(NOW - timedelta(seconds=95))
        self.assertEqual(self.check(contract, receipts, digest).valid_until, NOW + timedelta(seconds=10))
        receipts["autoRecharge"]["payload"]["uiObservedAt"] = iso(NOW - timedelta(seconds=10))
        receipts["autoRecharge"]["payload"]["profileObservedAt"] = iso(NOW - timedelta(seconds=15))
        receipts["quota"]["payload"]["quotaWindows"]["fiveHour"]["resetsAt"] = iso(NOW + timedelta(seconds=20))
        self.assertEqual(self.check(contract, receipts, digest).valid_until, NOW + timedelta(seconds=20))

    def test_contract_validation_and_mutation_refuse(self):
        def mutate(name):
            contract, receipts, digest = fixture()
            if name == "cap":
                contract["additionalSpendCapEur"] = True
            elif name == "cap-nonzero":
                contract["additionalSpendCapEur"] = 1
            elif name == "pin":
                contract["sources"]["quota"]["sourceSha256"] = _sha("changed")
            elif name == "host":
                contract["binding"]["host"] = "codex"
            elif name == "suffix-short":
                contract["isolatedStore"]["keychainSuffix"] = "abc"
            elif name == "suffix-upper":
                contract["isolatedStore"]["keychainSuffix"] = "ABCDEF12"
            elif name == "suffix-extra":
                contract["isolatedStore"]["path"] = "/x"
            elif name == "org-bound":
                contract["organizationScope"]["binding"] = "bound"
            elif name == "org-missing-hash":
                del contract["organizationScope"]["declarationSha256"]
            elif name == "org-bad-hash":
                contract["organizationScope"]["declarationSha256"] = "abc"
            elif name == "org-absent":
                del contract["organizationScope"]
            elif name == "age-ui-ceiling":
                contract["sourceMaxAgeSeconds"]["autoRecharge"] = 901
            elif name == "age-quota-over-binding":
                contract["sourceMaxAgeSeconds"]["quota"] = 31
            elif name == "age-process-over-binding":
                contract["sourceMaxAgeSeconds"]["process"] = 61
            elif name == "age-zero":
                contract["sourceMaxAgeSeconds"]["quota"] = 0
            elif name == "age-bool":
                contract["sourceMaxAgeSeconds"]["process"] = True
            elif name == "age-nan":
                contract["sourceMaxAgeSeconds"]["autoRecharge"] = float("nan")
            elif name == "age-missing":
                del contract["sourceMaxAgeSeconds"]["process"]
            elif name == "age-extra":
                contract["sourceMaxAgeSeconds"]["other"] = 1
            elif name == "extra":
                receipts["quota"]["payload"]["creditsEnabled"] = False
            elif name == "missing":
                del receipts["autoRecharge"]
            elif name == "contract-extra":
                contract["notes"] = "x"
            else:
                digest = _sha("different-contract")
            return contract, receipts, digest
        for name in ["cap", "cap-nonzero", "pin", "host", "suffix-short", "suffix-upper", "suffix-extra",
                     "org-bound", "org-missing-hash", "org-bad-hash", "org-absent", "age-ui-ceiling",
                     "age-quota-over-binding", "age-process-over-binding", "age-zero", "age-bool",
                     "age-nan", "age-missing", "age-extra", "extra", "missing", "contract-extra", "digest"]:
            with self.subTest(mutation=name):
                contract, receipts, digest = mutate(name)
                if name in ("pin", "host", "suffix-short", "suffix-upper", "suffix-extra", "org-bound",
                            "org-missing-hash", "org-bad-hash", "org-absent", "age-quota-over-binding",
                            "age-process-over-binding", "age-zero", "age-bool", "age-nan",
                            "age-missing", "age-extra", "age-ui-ceiling", "cap", "cap-nonzero",
                            "contract-extra"):
                    # the frozen digest is stale after these edits, so refusal also covers drift
                    self.refuses(contract, receipts, digest)
                    if name != "pin":
                        with self.assertRaises(subscription.SubscriptionError):
                            sources.source_contract_sha256(contract)
                else:
                    self.refuses(contract, receipts, digest)

    def test_naive_check_time_is_refused(self):
        contract, receipts, digest = fixture()
        with self.assertRaises(subscription.SubscriptionError):
            sources.compose_claude_sources(contract, receipts, expected_contract_sha256=digest,
                                           now=NOW.replace(tzinfo=None))


if __name__ == "__main__":
    unittest.main()
