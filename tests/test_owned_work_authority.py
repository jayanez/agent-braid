# SPDX-License-Identifier: AGPL-3.0-only
"""Synthetic software controls; no real consent, roots or observations admitted."""
from dataclasses import FrozenInstanceError, replace
import json
from pathlib import Path
import unittest

from agent_braid.owned_work_authority import (
    OperatorRegistry, OwnedWorkError, authority_schema, canonical_bytes, digest,
    parse_authority, parse_json, resolve_authority,
)

D = lambda char: char * 64
NOW = "2030-01-01T00:00:01Z"


def authority_fixture():
    body = dict(schema="agent-braid-owned-work-authority/v1", decision="admitted",
                authorityId="a" * 32, sourceKind="owned-deterministic-development",
                sourceRootDigest=D("a"), scopeDigest=D("b"), consentReferenceDigest=D("c"),
                reviewRecordDigest=D("d"), featureAllowlistDigest=D("e"),
                oracleContractDigest=D("f"), splitProtocolDigest=D("1"),
                validFromUTC="2030-01-01T00:00:00Z", validUntilUTC="2030-01-02T00:00:00Z",
                allowedActions=["read-metadata", "record-origin", "append-outcome"],
                caps=dict(maxAttempts=1000, maxRecords=4096, maxRecordBytes=65536,
                          maxStoreBytes=10485760, retentionUTCDates=30),
                executionAuthorization=False, trainingAdmission=False, collector047Enabled=False)
    raw = canonical_bytes(body)
    registry = OperatorRegistry((raw,), frozenset({D("c")}), frozenset({D("d")}),
                                frozenset({D("a")}), frozenset(), D("2"))
    return body, raw, registry


def resolve(raw=None, registry=None, **changes):
    _, original, registered = authority_fixture()
    args = dict(source_root_digest=D("a"), scope_digest=D("b"),
                expected_pins={"featureAllowlistDigest": D("e"), "oracleContractDigest": D("f"),
                               "splitProtocolDigest": D("1")}, actions=("record-origin",), now_utc=NOW)
    args.update(changes)
    return resolve_authority(original if raw is None else raw,
                             registered if registry is None else registry, **args)


class AuthorityTests(unittest.TestCase):
    def test_exact_admission_returns_immutable_detached_non_authority_context(self):
        body, raw, reg = authority_fixture()
        ctx = resolve(raw, reg)
        self.assertEqual(ctx.authority_digest, digest(body))
        self.assertEqual(ctx.actions, ("record-origin",))
        self.assertIs(ctx.descriptor["executionAuthorization"], False)
        self.assertIs(ctx.descriptor["trainingAdmission"], False)
        detached = ctx.descriptor
        detached["caps"]["maxAttempts"] = 0
        self.assertEqual(ctx.descriptor["caps"]["maxAttempts"], 1000)
        with self.assertRaises(FrozenInstanceError):
            ctx.actions = ("manual-export",)

    def test_wire_admitted_and_true_callback_do_not_create_registry(self):
        _, raw, _ = authority_fixture()
        for registry in (None, lambda: True, {}, True):
            with self.subTest(registry=type(registry).__name__):
                with self.assertRaisesRegex(OwnedWorkError, "missing-trusted-registry"):
                    resolve_authority(raw, registry, source_root_digest=D("a"), scope_digest=D("b"),
                                      expected_pins={}, actions=("record-origin",), now_utc=NOW)

    def test_registry_and_receipts_are_not_inferred_from_digest_shape(self):
        _, raw, reg = authority_fixture()
        for change, code in [({"descriptors": ()}, "authority-not-registered"),
                             ({"consent_receipts": frozenset()}, "authority-receipts"),
                             ({"review_receipts": frozenset()}, "authority-receipts"),
                             ({"canonical_roots": frozenset()}, "authority-scope"),
                             ({"revoked_ids": frozenset({"a"*32})}, "authority-revoked")]:
            with self.subTest(change=change):
                with self.assertRaisesRegex(OwnedWorkError, code):
                    resolve(raw, replace(reg, **change))

    def test_scope_pins_and_actions_fail_closed(self):
        for changes, code in [({"source_root_digest": D("9")}, "authority-scope"),
                              ({"scope_digest": D("9")}, "authority-scope"),
                              ({"expected_pins": {}}, "authority-pins"),
                              ({"actions": ()}, "authority-actions"),
                              ({"actions": ("manual-export",)}, "authority-actions"),
                              ({"actions": ("record-origin",)*2}, "authority-actions")]:
            with self.subTest(changes=changes), self.assertRaisesRegex(OwnedWorkError, code):
                resolve(**changes)

    def test_expiry_is_half_open_and_now_is_not_in_wire(self):
        resolve(now_utc="2030-01-01T00:00:00Z")
        for now in ("2029-12-31T23:59:59Z", "2030-01-02T00:00:00Z"):
            with self.subTest(now=now), self.assertRaisesRegex(OwnedWorkError, "authority-expired"):
                resolve(now_utc=now)
        body, _, _ = authority_fixture()
        body["nowUTC"] = NOW
        with self.assertRaisesRegex(OwnedWorkError, "schema-extra"):
            parse_authority(canonical_bytes(body))

    def test_unregistered_changed_descriptor_does_not_inherit_receipt(self):
        body, _, reg = authority_fixture()
        body["caps"]["maxAttempts"] = 5
        with self.assertRaisesRegex(OwnedWorkError, "authority-not-registered"):
            resolve(canonical_bytes(body), reg)

    def test_closed_authority_rejects_privilege_and_caps(self):
        mutations = [("executionAuthorization", True), ("executionAuthorization", 0),
                     ("trainingAdmission", True), ("collector047Enabled", True),
                     ("reviewRecordDigest", None), ("validUntilUTC", "2030-01-01T00:00:00Z")]
        for key, value in mutations:
            body, _, _ = authority_fixture(); body[key] = value
            with self.subTest(key=key, value=value), self.assertRaises(OwnedWorkError):
                parse_authority(canonical_bytes(body))
        for key, value in [("maxAttempts", True), ("maxAttempts", 1001),
                           ("maxRecords", 4097), ("maxRecordBytes", 65537),
                           ("maxStoreBytes", 10485761), ("retentionUTCDates", 31)]:
            body, _, _ = authority_fixture(); body["caps"][key] = value
            with self.subTest(key=key), self.assertRaises(OwnedWorkError):
                parse_authority(canonical_bytes(body))

    def test_raw_rejects_duplicates_nonfinite_unicode_depth_and_limits(self):
        cases = [b'{"x":1,"x":2}', b'{"x":NaN}', b'{"x":Infinity}', b'{"x":1e9999}',
                 b'{"x":"\\ud800"}', b'\xff', b'[]', b'{} '*22000,
                 b'{"x":' + b'['*17 + b'0' + b']'*17 + b'}']
        for raw in cases:
            with self.subTest(raw=raw[:30]), self.assertRaises(OwnedWorkError):
                parse_json(raw)
        self.assertEqual(parse_json(b'{"x":"EN/ES: a\\u00f1o"}'), {"x": "EN/ES: año"})

    def test_invalid_utc_dates_and_control_characters(self):
        for date in ("2030-02-30T00:00:00Z", "2030-01-01T00:00:00+00:00", NOW+"\n"):
            body, _, _ = authority_fixture(); body["validUntilUTC"] = date
            with self.subTest(date=date), self.assertRaises(OwnedWorkError):
                parse_authority(canonical_bytes(body))

    def test_registry_copies_mutable_input_and_rejects_duplicate_ids(self):
        _, raw, reg = authority_fixture()
        source = [raw]
        new = replace(reg, descriptors=source)
        source.clear()
        self.assertEqual(new.descriptors, (raw,))
        with self.assertRaisesRegex(OwnedWorkError, "registry-conflict"):
            replace(reg, descriptors=(raw, raw))
        for value in (D("c"), D("c").encode(), [1]):
            with self.assertRaisesRegex(OwnedWorkError, "registry-type"):
                replace(reg, consent_receipts=value)

    def test_embedded_schema_matches_exact_adopted_contract(self):
        root = Path(__file__).resolve().parents[1]
        external = json.loads((root/'specs/051-owned-work-evaluation/contracts/owned-work-authority.schema.json').read_text())
        self.assertEqual(authority_schema(), external)
        from jsonschema import Draft202012Validator, FormatChecker
        validator = Draft202012Validator(external, format_checker=FormatChecker())
        body, raw, _ = authority_fixture()
        validator.validate(body); self.assertEqual(parse_authority(raw), body)
        for key, value in [("executionAuthorization", 0), ("caps", {}), ("authorityId", "user")]:
            body, _, _ = authority_fixture(); body[key] = value
            self.assertTrue(list(validator.iter_errors(body)))
            with self.assertRaises(OwnedWorkError): parse_authority(canonical_bytes(body))
