# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-057 T023 / REQ-010 / SC-010: the policy-profile schema, examples and mutations.

Test names say which rule is schema-level and which is validator-level. The
validator-level rules (audit default, mode ladder, envelope digest) need a
compiler or guard, which SPEC-058 owns; here the schema is shown to be silent on
them so that the hand-off is explicit. No compiler, hook or settings writer
exists in this specification's deliverables.
"""

from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "specs" / "057-claude-orchestration-advisory" / "contracts"
SCHEMA = json.loads((CONTRACTS / "policy-profile.schema.json").read_text(encoding="utf-8"))
VALIDATOR = Draft202012Validator(SCHEMA)
EXAMPLES = sorted(CONTRACTS.glob("policy-profile.example*.json"))

# Rules the schema cannot express, with the SPEC-058 task that owns each one.
VALIDATOR_LEVEL_RULES = {
    "audit-default-when-enabled": "SPEC-058 T011",
    "mode-skipping-the-ladder": "SPEC-058 T014",
    "envelope-digest-matches-envelope": "SPEC-058 T015",
}

# A synthetic fixture: HV-8 has not run, so this receipt names no real observation.
BASH_ATTESTATION = {"hostVersion": "0.0.0-test", "surface": "batch", "receipt": "HV-8 synthetic test fixture"}


def example(name: str = "policy-profile.example.json") -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))


def errors(profile: object) -> list:
    return list(VALIDATOR.iter_errors(profile))


def mutate(base: dict, **changes) -> dict:
    profile = deepcopy(base)
    profile.update(changes)
    return profile


class SchemaDocumentTests(unittest.TestCase):
    def test_schema_level_valid_draft_2020_12_document(self):
        self.assertEqual(SCHEMA["$schema"], "https://json-schema.org/draft/2020-12/schema")
        Draft202012Validator.check_schema(SCHEMA)

    def test_schema_level_examples_pass(self):
        self.assertTrue(EXAMPLES)
        for path in EXAMPLES:
            with self.subTest(example=path.name):
                self.assertEqual(errors(json.loads(path.read_text(encoding="utf-8"))), [])

    def test_schema_level_every_object_rejects_unknown_members(self):
        def walk(node, where):
            if isinstance(node, dict):
                if node.get("type") == "object":
                    self.assertIs(node.get("additionalProperties"), False, where)
                for key, value in node.items():
                    walk(value, f"{where}/{key}")
            elif isinstance(node, list):
                for index, value in enumerate(node):
                    walk(value, f"{where}/{index}")

        walk(SCHEMA, "#")

    def test_schema_level_enforcement_observed_default_is_false(self):
        self.assertIs(SCHEMA["properties"]["enforcementObserved"]["default"], False)

    def test_inventory_only_schemas_examples_and_tests(self):
        names = sorted(p.name for p in CONTRACTS.glob("policy-profile*"))
        self.assertEqual(
            names,
            [
                "policy-profile.example-off.json",
                "policy-profile.example.json",
                "policy-profile.schema.json",
            ],
        )
        for pattern in ("*policy_profile*", "*policy_compiler*", "*guard*"):
            with self.subTest(pattern=pattern):
                self.assertEqual(list((ROOT / "agent_braid").glob(pattern)), [])


class SchemaMutationTests(unittest.TestCase):
    """Each mutation is a schema-level rule: the mutated profile must be rejected."""

    def assertRejected(self, profile: object):
        self.assertNotEqual(errors(profile), [])

    def test_schema_level_no_allow_decision(self):
        base = example()
        for vocabulary in (
            ["no-opinion", "ask", "deny", "additionalContext", "allow"],
            ["allow", "ask", "deny", "additionalContext"],
            ["no-opinion", "ask", "deny"],
            ["deny", "ask", "no-opinion", "additionalContext"],
        ):
            with self.subTest(vocabulary=vocabulary):
                self.assertRejected(mutate(base, guardVocabulary=vocabulary))

    def test_schema_level_no_grant_member(self):
        base = example()
        for member in ("grant", "grants", "allow", "permissions", "executionGrant", "authorization"):
            with self.subTest(member=member):
                self.assertRejected(mutate(base, **{member: True}))
        nested = mutate(base)
        nested["envelope"]["grant"] = ["src/"]
        self.assertRejected(nested)
        nested = mutate(base)
        nested["coverageBoundary"]["allow"] = ["Bash"]
        self.assertRejected(nested)

    def test_schema_level_execution_authorization_is_constant_false(self):
        self.assertRejected(mutate(example(), executionAuthorization=True))
        profile = example()
        del profile["executionAuthorization"]
        self.assertRejected(profile)

    def test_schema_level_no_notebook_edit(self):
        profile = example()
        profile["coverageBoundary"]["tools"] = ["Write", "Edit", "NotebookEdit"]
        self.assertRejected(profile)
        profile["coverageBoundary"]["tools"] = ["NotebookEdit"]
        self.assertRejected(profile)
        profile["coverageBoundary"]["tools"] = []
        self.assertRejected(profile)

    def test_schema_level_no_main_plugin_target(self):
        base = example()
        for target in (
            "main-plugin-hooks",
            "agent-braid-hooks",
            "plugin-hooks",
            "main-plugin",
            "settings-hooks",
        ):
            with self.subTest(target=target):
                self.assertRejected(mutate(base, outputs=[target]))
                self.assertRejected(mutate(base, outputs=["native-host-settings", target]))
        self.assertRejected(mutate(base, hooks=[{"event": "PreToolUse"}]))
        self.assertRejected(mutate(base, outputs=[]))
        self.assertRejected(mutate(base, outputs=["settings-snippet"] * 2))
        self.assertRejected(
            mutate(base, outputs=["native-host-settings", "companion-plugin-hooks", "settings-snippet", "x"])
        )

    def test_schema_level_mode_ladder_vocabulary(self):
        base = example()
        for mode in ("enforce", "enabled", "AUDIT", "observe", "", None):
            with self.subTest(mode=mode):
                self.assertRejected(mutate(base, mode=mode))
        for mode in ("off", "audit", "warn", "block"):
            with self.subTest(mode=mode):
                self.assertEqual(errors(mutate(base, mode=mode)), [])

    def test_schema_level_enforcement_observed_requires_attestation(self):
        base = example()
        self.assertRejected(mutate(base, enforcementObserved=True))
        self.assertEqual(
            errors(
                mutate(
                    base,
                    enforcementObserved=True,
                    attestation={"hostVersion": "0.0.0-test", "surface": "batch", "receipt": "receipt"},
                )
            ),
            [],
        )
        self.assertRejected(mutate(base, enforcementObserved="false"))
        profile = deepcopy(base)
        del profile["enforcementObserved"]
        self.assertRejected(profile)

    def test_schema_level_attestation_surface_is_a_closed_id(self):
        for surface in ("batch-unit", "batches", "agent-team", "workflow", "Batch"):
            with self.subTest(surface=surface):
                attestation = {"hostVersion": "0.0.0-test", "surface": surface, "receipt": "receipt"}
                self.assertRejected(mutate(example(), enforcementObserved=True, attestation=attestation))

    def test_schema_level_coverage_boundary(self):
        base = example()
        profile = deepcopy(base)
        del profile["coverageBoundary"]
        self.assertRejected(profile)
        for member in ("tools", "bash", "unattributed"):
            profile = deepcopy(base)
            del profile["coverageBoundary"][member]
            with self.subTest(missing=member):
                self.assertRejected(profile)
        profile = deepcopy(base)
        profile["coverageBoundary"]["unattributed"] = "covered-where-verified"
        self.assertRejected(profile)
        profile = deepcopy(base)
        profile["coverageBoundary"]["bash"] = "covered"
        self.assertRejected(profile)

    def test_schema_level_enabled_mode_requires_protected_control_paths(self):
        for mode in ("audit", "warn", "block"):
            with self.subTest(mode=mode):
                missing = mutate(example(), mode=mode)
                del missing["envelope"]["protectedControlPaths"]
                self.assertRejected(missing)
                empty = mutate(example(), mode=mode)
                empty["envelope"]["protectedControlPaths"] = []
                self.assertRejected(empty)
        absent_mode = example("policy-profile.example-off.json")
        self.assertEqual(errors(absent_mode), [])
        self.assertEqual(errors(mutate(absent_mode, mode="off")), [])

    def test_schema_level_bash_coverage_needs_native_only_output_and_hv8_attestation(self):
        def covered(**changes):
            profile = mutate(example(), outputs=["native-host-settings"], attestation=BASH_ATTESTATION)
            profile["coverageBoundary"]["bash"] = "covered-where-verified"
            profile.update(changes)
            return profile

        self.assertEqual(errors(covered()), [])
        for outputs in (
            ["native-host-settings", "companion-plugin-hooks"],
            ["native-host-settings", "settings-snippet"],
            ["companion-plugin-hooks"],
            ["settings-snippet"],
        ):
            with self.subTest(outputs=outputs):
                self.assertRejected(covered(outputs=outputs))
        without_attestation = covered()
        del without_attestation["attestation"]
        self.assertRejected(without_attestation)
        for receipt in ("HV-7 receipt", "receipt", "HV-80", "HV-81 receipt", "xHV-8"):
            with self.subTest(receipt=receipt):
                self.assertRejected(covered(attestation={**BASH_ATTESTATION, "receipt": receipt}))

    def test_schema_level_failure_behavior_members(self):
        base = example()
        profile = deepcopy(base)
        del profile["failureBehavior"]
        self.assertRejected(profile)
        for member in ("onInternalError", "askScope"):
            profile = deepcopy(base)
            del profile["failureBehavior"][member]
            with self.subTest(missing=member):
                self.assertRejected(profile)
        for member, value in (
            ("onInternalError", "fail-closed"),
            ("onInternalError", "fail-open"),
            ("askScope", "all-paths"),
            ("askScope", "undecidable-paths-in-block"),
        ):
            profile = deepcopy(base)
            profile["failureBehavior"][member] = value
            with self.subTest(member=member, value=value):
                self.assertRejected(profile)
        profile = deepcopy(base)
        profile["failureBehavior"]["onTimeout"] = "deny"
        self.assertRejected(profile)

    def test_schema_level_unit_and_paths_are_bounded_and_clean(self):
        base = example()
        for unit in ("", "-bad", "a" * 65, "unit\n", "unit/with/slash"):
            with self.subTest(unit=unit):
                self.assertRejected(mutate(base, unit=unit))
        profile = deepcopy(base)
        profile["envelope"]["writes"] = ["a‮b"]
        self.assertRejected(profile)
        profile = deepcopy(base)
        profile["envelope"]["writes"] = ["a" * 257]
        self.assertRejected(profile)
        profile = deepcopy(base)
        profile["envelope"]["writes"] = [f"p{i}" for i in range(513)]
        self.assertRejected(profile)
        profile = deepcopy(base)
        profile["envelope"]["writes"] = ["a\n"]
        self.assertRejected(profile)

    def test_schema_level_non_objects_are_rejected(self):
        for value in (None, [], "profile", 1):
            with self.subTest(value=value):
                self.assertRejected(value)


class ValidatorLevelHandOffTests(unittest.TestCase):
    """Rules the schema cannot express are listed with an owner, and the schema is silent on them."""

    def test_validator_level_rules_are_named_with_a_spec_058_owner(self):
        self.assertEqual(len(VALIDATOR_LEVEL_RULES), 3)
        self.assertTrue(all(owner.startswith("SPEC-058 T") for owner in VALIDATOR_LEVEL_RULES.values()))
        description = SCHEMA["description"]
        for phrase in ("audit default", "skips the ladder", "envelope digest"):
            self.assertIn(phrase, description)

    def test_validator_level_mode_is_optional_so_the_schema_cannot_apply_the_audit_default(self):
        self.assertNotIn("mode", SCHEMA["required"])
        self.assertEqual(errors(example("policy-profile.example-off.json")), [])

    def test_validator_level_schema_accepts_block_without_a_prior_audit_stage(self):
        # Skipping the ladder is a relation between a profile and its history; one profile is valid.
        self.assertEqual(errors(mutate(example(), mode="block")), [])

    def test_validator_level_schema_has_no_envelope_digest_member(self):
        self.assertNotIn("envelopeDigest", SCHEMA["properties"])
        self.assertNotIn("envelopeDigest", SCHEMA["properties"]["envelope"]["properties"])


if __name__ == "__main__":
    unittest.main()
