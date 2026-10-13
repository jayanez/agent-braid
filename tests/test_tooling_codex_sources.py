# SPDX-License-Identifier: AGPL-3.0-only
"""Offline negative controls; no native-source authentication is claimed."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
import unittest

from agent_braid import tooling_codex_sources as sources
from agent_braid import tooling_subscription as subscription
from tests.test_tooling_subscription import _operational_policy, _sha


NOW = datetime(2026, 10, 12, 12, tzinfo=timezone.utc)


def fixture():
    policy = _operational_policy()
    binding = subscription.OperationalProcessRouteBinding(
        "codex", _sha("registration"), "slot-1", subscription.policy_sha256(policy),
        _sha("a"), _sha("a-ns"), _sha("build"), _sha("artifact"), _sha("exe"),
        _sha("config"), _sha("argv"), _sha("model"), "observer", _sha("observer"),
        "verifier", _sha("verifier"), 30,
    ).as_dict()
    contract = {"schema": sources.CONTRACT_SCHEMA, "binding": binding,
                "additionalSpendCapEur": 0, "sources": {
                    kind: {"sourceRef": kind, "sourceSha256": _sha(kind),
                           "verifierRef": kind + "-verifier", "verifierSha256": _sha(kind + "-verifier")}
                    for kind in sources.KINDS}}
    digest = sources.source_contract_sha256(contract)
    payloads = {
        "quota": {"ordinaryUsageAllowed": True, "credits": {"hasCredits": False, "unlimited": False},
                  "spendControlReached": False},
        "autoRecharge": {"autoRechargeEnabled": False},
        "process": {"authMethod": "chatgpt", "route": "included-subscription-quota",
                    **{field: True for field in sources.PROCESS_TRUE},
                    **{field: False for field in sources.PROCESS_FALSE}},
    }
    receipts = {kind: {"schema": sources.RECEIPT_SCHEMA, "kind": kind,
                       "contractSha256": digest, "binding": deepcopy(binding),
                       "phase": "prelaunch", "processId": None, "processBirthSha256": None,
                       "observedSequence": 1, "observedAt": NOW.isoformat(), "payload": payloads[kind],
                       **contract["sources"][kind]} for kind in sources.KINDS}
    return contract, receipts, digest


class CodexSourceContractTests(unittest.TestCase):
    def check(self, contract, receipts, digest, **kwargs):
        return sources.compose_codex_sources(contract, receipts,
                                             expected_contract_sha256=digest, now=NOW, **kwargs)

    def test_composes_exact_native_fields_without_inventing_v3_booleans(self):
        contract, receipts, digest = fixture()
        before = deepcopy((contract, receipts))
        result = self.check(contract, receipts, digest)
        self.assertEqual(result.valid_until, NOW + timedelta(seconds=30))
        self.assertEqual(len(result.receipt_sha256), 3)
        self.assertNotIsInstance(result, subscription.OperationalProcessRouteObservation)
        with self.assertRaises(subscription.SubscriptionError):
            subscription.check_observation(result, result.binding, now=NOW)
        self.assertEqual(before, (contract, receipts))

    def test_refuses_each_missing_unknown_non_boolean_and_unsafe_control(self):
        for kind, path, safe in [
            ("quota", ("ordinaryUsageAllowed",), True),
            ("quota", ("spendControlReached",), False),
            ("quota", ("credits", "hasCredits"), False),
            ("quota", ("credits", "unlimited"), False),
            ("autoRecharge", ("autoRechargeEnabled",), False),
            *[("process", (field,), True) for field in sources.PROCESS_TRUE],
            *[("process", (field,), False) for field in sources.PROCESS_FALSE],
        ]:
            for bad in [None, "unknown", 0, 1, not safe, "missing"]:
                with self.subTest(kind=kind, path=path, bad=bad):
                    contract, receipts, digest = fixture()
                    payload = receipts[kind]["payload"]
                    for part in path[:-1]:
                        payload = payload[part]
                    if bad == "missing":
                        del payload[path[-1]]
                    else:
                        payload[path[-1]] = bad
                    with self.assertRaises(subscription.SubscriptionError):
                        self.check(contract, receipts, digest)

    def test_every_source_must_be_fresh_pinned_and_bound(self):
        for kind in sources.KINDS:
            mutations = [
                ("observedAt", (NOW - timedelta(seconds=31)).isoformat()),
                ("observedAt", (NOW + timedelta(seconds=1)).isoformat()),
                ("observedAt", NOW.replace(tzinfo=None).isoformat()),
                ("observedAt", None), ("sourceSha256", _sha("drift")),
                ("verifierRef", "other"), ("contractSha256", _sha("other")),
                ("observedSequence", 2), ("schema", "v3"),
            ]
            for field, value in mutations:
                with self.subTest(kind=kind, field=field):
                    contract, receipts, digest = fixture()
                    receipts[kind][field] = value
                    with self.assertRaises(subscription.SubscriptionError):
                        self.check(contract, receipts, digest)
            for field in ["accountSha256", "accountNamespaceSha256", "candidateArtifactSha256",
                          "executableSha256", "configSha256", "argvSha256", "modelIdentitySha256",
                          "registrationSha256", "hostBuildSha256", "policySha256"]:
                with self.subTest(kind=kind, binding=field):
                    contract, receipts, digest = fixture()
                    receipts[kind]["binding"][field] = _sha("drift")
                    with self.assertRaises(subscription.SubscriptionError):
                        self.check(contract, receipts, digest)

    def test_process_lifecycle_and_identity_conflicts(self):
        contract, receipts, digest = fixture()
        for receipt in receipts.values():
            receipt.update(phase="running", processId=4321, processBirthSha256=_sha("birth"))
        result = self.check(contract, receipts, digest)
        self.assertEqual(result.process_id, 4321)
        receipts["quota"]["processBirthSha256"] = _sha("another-process")
        with self.assertRaises(subscription.SubscriptionError):
            self.check(contract, receipts, digest)

    def test_contract_mutation_extra_fields_and_partial_receipts_refuse(self):
        for mutation in ["cap", "pin", "host", "extra", "missing", "digest"]:
            with self.subTest(mutation=mutation):
                contract, receipts, digest = fixture()
                if mutation == "cap":
                    contract["additionalSpendCapEur"] = True
                elif mutation == "pin":
                    contract["sources"]["quota"]["sourceSha256"] = _sha("changed")
                elif mutation == "host":
                    contract["binding"]["host"] = "claude-code"
                elif mutation == "extra":
                    receipts["quota"]["payload"]["creditsEnabled"] = False
                elif mutation == "missing":
                    del receipts["autoRecharge"]
                else:
                    digest = _sha("different-contract")
                with self.assertRaises(subscription.SubscriptionError):
                    self.check(contract, receipts, digest)
