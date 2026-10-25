# SPDX-License-Identifier: AGPL-3.0-only
"""Offline laboratory record codec controls; no host, model or native acceptance."""
from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import unittest

from agent_braid import harness_journal as journal
from agent_braid import harness_records as records
from agent_braid.system_one import canonical
from tests.test_harness_manifest import make_manifest
from tests.test_harness_refinement import Lab, done, make_policy, proposal

NOW = 1_800_000_000


def decision_wire() -> dict:
    manifest, policy = make_policy()
    lab = Lab(manifest, {"general": proposal(manifest, "general", {"guidance/general.md": b"Be brief.\n"}),
                         "task": None},
              {"base": done(500_000), "general": done(700_000)})
    return lab.run(policy).to_dict()


def status_wire() -> dict:
    return journal.AttemptStatus("attempt-1", "a" * 64, "ended", "completed", "recorded",
                                 "terminal", ("step-1",), (), 3).to_dict()


def wires() -> dict:
    return {"manifest": make_manifest(), "decision": decision_wire(),
            "attempt-status": {"format": records.FORMATS["attempt-status"], **status_wire()}}


class CodecTests(unittest.TestCase):
    def test_every_kind_round_trips_to_identical_canonical_bytes(self):
        for kind, wire in wires().items():
            with self.subTest(kind=kind):
                first = records.encode(kind, wire)
                second = records.decode(first.canonical_bytes)
                self.assertEqual(second.kind, kind)
                self.assertEqual(second.canonical_bytes, first.canonical_bytes)
                self.assertEqual(second.sha256, first.sha256)
                self.assertEqual(second.to_dict(), first.to_dict())
                self.assertEqual(records.encode(kind, second.to_dict()).canonical_bytes,
                                 first.canonical_bytes)

    def test_records_are_immutable_and_never_authorize(self):
        record = records.encode("decision", decision_wire())
        with self.assertRaises(FrozenInstanceError):
            record.kind = "manifest"
        with self.assertRaises(TypeError):
            record.data["decision"] = "candidate"
        record.to_dict()["decision"] = "tampered"  # independent copy
        self.assertEqual(record.to_dict()["decision"], "candidate")
        self.assertIs(record.executionAuthorization, False)

    def test_non_canonical_bytes_refuse_even_when_semantically_equal(self):
        for kind, wire in wires().items():
            spaced = json.dumps(wire, sort_keys=True, indent=1).encode()
            with self.subTest(kind=kind):
                self.assertRefuses(spaced, "non-canonical")

    def test_future_and_unknown_versions_refuse_with_distinct_reasons(self):
        for kind, wire in wires().items():
            future = dict(wire, format=wire["format"].replace("/v0.1", "/v0.2"))
            with self.subTest(kind=kind):
                self.assertRefuses(canonical(future), "unsupported-version")
        self.assertRefuses(canonical(dict(make_manifest(), format="other/v0.1")), "unknown-format")
        self.assertRefuses(canonical({"x": 1}), "unknown-format")

    def test_malformed_bytes_and_shapes_refuse_without_escaping(self):
        manifest = canonical(make_manifest())
        hostile = [b"", b"\xff\xfe", b"[]", b"null", b"1", b'"x"', b"{", b'{"format":1}',
                   b'{"a":1,"a":2}', b"[" * 5000, manifest[:-1], manifest + b" ", b"\x00" * 10,
                   b'{"format":"braid-harness-decision/v0.1"}',
                   b"{" + b'"k":{' * 100 + b"}" * 101]
        for raw in hostile:
            with self.subTest(raw=raw[:30]):
                with self.assertRaises(records.RecordError) as caught:
                    records.decode(raw)
                self.assertRegex(caught.exception.reason, r"^[a-z][a-z-]+\Z")
        for raw in (None, "text", bytearray(b"{}"), 7):
            with self.assertRaises(records.RecordError):
                records.decode(raw)

    def test_oversized_input_refuses_before_parsing(self):
        self.assertRefuses(b"{" + b" " * records.MAX_RECORD_BYTES + b"}", "record-too-large")

    def test_decision_strictness(self):
        base = decision_wire()
        cases = {
            "extra-key": lambda v: v.update(extra=1),
            "missing-key": lambda v: v.pop("losses"),
            "authorization": lambda v: v.update(executionAuthorization=True),
            "bad-decision": lambda v: v.update(decision="promote"),
            "candidate-without-chosen": lambda v: v.update(chosenCandidateSha256=None),
            "keep-base-with-chosen": lambda v: v.update(decision="keep-base", chosenCandidateSha256="b" * 64),
            "bool-as-int": lambda v: v.update(marginMicros=True),
            "bad-hash": lambda v: v.update(policySha256="XYZ"),
            "bad-attempt": lambda v: v["attempts"][0].update(status="winning"),
            "attempt-extra": lambda v: v["attempts"][0].update(note="x"),
            "attempt-count": lambda v: v.update(attempts=v["attempts"] * 4),
            "chosen-not-an-attempt": lambda v: v.update(chosenCandidateSha256="c" * 64),
            "duplicate-attempt-id": lambda v: v["attempts"][1].update(id=v["attempts"][0]["id"]),
            "provenance": lambda v: v["provenance"].update(upstreamRevision="0" * 40),
            "reason-type": lambda v: v.update(reasons="improved"),
            "loss-type": lambda v: v.update(losses=[1]),
        }
        for name, mutate in cases.items():
            wire = deepcopy(base)
            mutate(wire)
            with self.subTest(name=name):
                with self.assertRaises(records.RecordError):
                    records.encode("decision", wire)
                self.assertRefuses(canonical(wire), None)

    def test_attempt_status_never_grants_redispatch_or_renewal(self):
        for field in ("redispatchAllowed", "permissionRenewed", "executionAuthorization"):
            wire = {"format": records.FORMATS["attempt-status"], **status_wire(), field: True}
            with self.subTest(field=field):
                self.assertRefuses(canonical(wire), "invalid-record")
        wire = {"format": records.FORMATS["attempt-status"], **status_wire(), "phase": "paused"}
        self.assertRefuses(canonical(wire), "invalid-record")

    def test_unobserved_terminal_state_is_a_valid_status(self):
        wire = {"format": records.FORMATS["attempt-status"], **status_wire(), "state": "unobserved"}
        self.assertEqual(records.decode(canonical(wire)).to_dict()["state"], "unobserved")

    def test_manifest_codec_reuses_the_manifest_validator(self):
        wire = make_manifest()
        wire["host"]["requested"]["model"] = "gpt-x"  # native request: outside the offline profile
        self.assertRefuses(canonical(wire), "unsupported-profile")

    def test_encode_rejects_unknown_kind_and_wrong_format(self):
        with self.assertRaises(records.RecordError) as caught:
            records.encode("observation", {})
        self.assertEqual(caught.exception.reason, "unknown-kind")
        with self.assertRaises(records.RecordError):
            records.encode("decision", make_manifest())

    def assertRefuses(self, raw, reason):
        with self.assertRaises(records.RecordError) as caught:
            records.decode(raw)
        if reason is not None:
            self.assertEqual(caught.exception.reason, reason)


class ComparisonTests(unittest.TestCase):
    def test_manifest_comparison_names_changed_bindings_and_candidate_files(self):
        left = make_manifest()
        right = deepcopy(left)
        right["task"]["id"] = "C01-002"
        comparison = records.compare(records.encode("manifest", left), records.encode("manifest", right))
        wire = comparison.to_dict()
        self.assertEqual(wire["recordKind"], "manifest")
        self.assertFalse(wire["identical"])
        self.assertIn("task", [row["field"] for row in wire["differences"]])
        self.assertIs(comparison.executionAuthorization, False)
        self.assertEqual(records.decode(comparison.canonical_bytes).canonical_bytes,
                         comparison.canonical_bytes)

    def test_identical_records_have_no_differences(self):
        record = records.encode("decision", decision_wire())
        wire = records.compare(record, record).to_dict()
        self.assertTrue(wire["identical"])
        self.assertEqual(wire["differences"], [])

    def test_decision_comparison_surfaces_outcome_and_evidence_losses(self):
        left = decision_wire()
        right = deepcopy(left)
        right.update(decision="inconclusive", chosenCandidateSha256=None,
                     reasons=["no-scored-candidate"], losses=["budget-exhausted"])
        wire = records.compare(records.encode("decision", left),
                               records.encode("decision", right)).to_dict()
        fields = {row["field"]: row for row in wire["differences"]}
        self.assertEqual(fields["decision"]["left"], "candidate")
        self.assertEqual(fields["decision"]["right"], "inconclusive")
        self.assertEqual(fields["losses"]["right"], "budget-exhausted")
        self.assertIn("reasons", fields)

    def test_mixed_kinds_refuse(self):
        with self.assertRaises(records.RecordError) as caught:
            records.compare(records.encode("manifest", make_manifest()),
                            records.encode("decision", decision_wire()))
        self.assertEqual(caught.exception.reason, "kind-mismatch")

    def test_comparison_record_is_strict(self):
        comparison = records.compare(records.encode("decision", decision_wire()),
                                     records.encode("decision", decision_wire())).to_dict()
        for mutate in (lambda v: v.update(identical="yes"),
                       lambda v: v.update(differences=[{"field": "x", "left": [1], "right": 2}]),
                       lambda v: v.update(differences=[{"field": "x", "left": 1}]),
                       lambda v: v.update(executionAuthorization=True),
                       lambda v: v.update(leftSha256="1")):
            wire = deepcopy(comparison)
            mutate(wire)
            with self.assertRaises(records.RecordError):
                records.decode(canonical(wire))


if __name__ == "__main__":
    unittest.main()
