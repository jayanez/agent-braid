# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic controls for additive registration and source-route isolation."""
import copy
import unittest

from agent_braid import tooling_evaluation as evaluation
from agent_braid import tooling_registration_v6 as v6
from tests.test_tooling_evaluation import _registration_v4, _with_operational_policy, _inputs, _sha


def registration_v6():
    data = _with_operational_policy(_registration_v4())
    data["schemaVersion"] = v6.REGISTRATION_SCHEMA
    data["billingPolicy"]["schema"] = v6.SOURCE_POLICY_SCHEMA
    pins = {kind: {"sourceRef": kind, "sourceSha256": _sha(kind),
                   "verifierRef": "reviewed-" + kind, "verifierSha256": _sha("reviewed-" + kind)}
            for kind in ("quota", "autoRecharge", "process")}
    data["sourceContractTemplates"] = {
        "codex": {"schema": "agent-braid-codex-source-contract-v1",
                  "additionalSpendCapEur": 0, "sources": copy.deepcopy(pins)},
        "claude-code": {"schema": "agent-braid-claude-source-contract-v1",
                        "additionalSpendCapEur": 0, "sources": copy.deepcopy(pins),
                        "isolatedStore": {"keychainSuffix": "0123abcd"},
                        "organizationScope": {"binding": "owner-declared-single-organization",
                                              "declarationSha256": _sha("declaration")},
                        "sourceMaxAgeSeconds": {"quota": 30, "process": 30, "autoRecharge": 900}},
    }
    data["humanAuditPolicy"] = {
        "schema": "agent-braid-m45-human-audit-policy-v1", "seed": "frozen-before-observation",
        "algorithm": "sha256-host-class-fixture-v1", "initialCases": 36,
        "reviewersPerCase": 2,
        "escalation": "cell-on-confirmed-discrepancy-cohort-on-critical-v1", "compactEvidence": True,
    }
    from agent_braid import tooling_human_audit as audit
    data["humanAuditPolicySha256"] = audit.policy_sha256(data["humanAuditPolicy"])
    data["instrumentPins"] = {name: copy.deepcopy(pins["process"])
                              for name in ("admission", "outcome", "costs", "technicalSummary")}
    data["claudeLaunchStore"] = {"canonicalConfigDirSha256": _sha("frozen-canonical-directory"),
                               "keychainSuffix": "0123abcd"}
    return data


def validated_v6(data=None):
    data = registration_v6() if data is None else data
    return evaluation.validate_registration(data, expected_candidate_sha256=data["candidate"]["sha256"],
                                            expected_input_hashes=_inputs(data))


class RegistrationV6Tests(unittest.TestCase):
    def test_roster_and_new_source_binding_do_not_synthesize_v3_observation(self):
        reg = validated_v6()
        slots = evaluation.generate_slots(reg)
        self.assertEqual(108, len(slots))
        for host in evaluation.HOSTS:
            slot = next(row for row in slots if row.host == host)
            binding = v6.binding_from_registration(reg, slot.slot_id, host)
            self.assertEqual(reg.sha256, binding.registration_sha256)
            self.assertEqual(host, binding.host)
            self.assertEqual(slot.slot_id, binding.slot_id)
            self.assertNotIn("subscriptionActive", binding.as_dict())
            self.assertEqual(reg.data["billingPolicy"]["schema"], v6.SOURCE_POLICY_SCHEMA)
        self.assertEqual(2, len(evaluation.expected_reviewer_participants(reg)))

    def test_previous_versions_cannot_opt_into_new_fields_or_policy(self):
        for version in (evaluation.REGISTRATION_SCHEMA, evaluation.REGISTRATION_SCHEMA_V2,
                        evaluation.REGISTRATION_SCHEMA_V3, evaluation.REGISTRATION_SCHEMA_V4,
                        evaluation.REGISTRATION_SCHEMA_V5):
            data = registration_v6()
            data["schemaVersion"] = version
            with self.subTest(version=version), self.assertRaises(evaluation.EvaluationError):
                validated_v6(data)

    def test_missing_or_drifted_source_contracts_and_instruments_refuse(self):
        for mutate in (lambda d: d.pop("sourceContractTemplates"),
                       lambda d: d["sourceContractTemplates"].pop("codex"),
                       lambda d: d["sourceContractTemplates"]["codex"].update(additionalSpendCapEur=1),
                       lambda d: d["sourceContractTemplates"]["claude-code"]["sourceMaxAgeSeconds"].update(quota=900),
                       lambda d: d["instrumentPins"].pop("outcome"),
                       lambda d: d["instrumentPins"]["costs"].update(sourceSha256="bad"),
                       lambda d: d["humanAuditPolicy"].update(initialCases=35)):
            data = registration_v6()
            mutate(data)
            with self.assertRaises(evaluation.EvaluationError):
                validated_v6(data)

    def test_all_slot_candidate_and_model_bindings_remain_required(self):
        for key in ("configSha256", "hostBuildSha256", "candidateArtifactSha256", "modelIdentitySha256"):
            data = registration_v6()
            slot = next(iter(data["billingPolicy"]["processContracts"]))
            data["billingPolicy"]["processContracts"][slot][key] = "bad" if key == "configSha256" else "0" * 64
            with self.subTest(key=key), self.assertRaises(evaluation.EvaluationError):
                validated_v6(data)

    def test_used_registration_cannot_be_mutated_or_cross_host_rebound(self):
        reg = validated_v6()
        slot = evaluation.generate_slots(reg)[0]
        with self.assertRaises(evaluation.EvaluationError):
            v6.binding_from_registration(reg, slot.slot_id, "claude-code")
        reg.data["sourceContractTemplates"]["codex"]["additionalSpendCapEur"] = 1
        with self.assertRaises(evaluation.EvaluationError):
            v6.binding_from_registration(reg, slot.slot_id, "codex")
