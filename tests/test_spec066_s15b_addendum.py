# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T101 addendum: the owner record that adds the git-history-replay source family.

The W0 gate is the validator: it accepts the family only through an addendum bound to the
T101 scope digest and carrying its own digest. These tests check that the committed record
is strict, self-consistent, carries the owner's conditions, widens nothing else and is
accepted by the gate exactly as written; no repository, registry or corpus is read.
"""
import copy
import json
from pathlib import Path
import unittest

from agent_braid.owned_work_authority import OwnedWorkError, digest, parse_json
from research import s15b_corpus_gate as gate

EVIDENCE = Path(__file__).resolve().parents[1] / "specs/066-system-one-shadow/evidence"
RECORD = EVIDENCE / "owner-consent-s15b-git-history-addendum-20261110.json"
BARE = EVIDENCE / "s15b-source-family-addendum-20261110.json"
FAMILY = "git-history-replay"
TOP = {"schema", "specification", "task", "amends", "requirement", "decisionDate", "decision",
       "executionAuthorization", "trainingAdmission", "ownerResponse", "conditions", "addendum", "digests", "limits"}
ADDENDUM = {"schema", "consentScopeDigest", "sourceFamilies", "digest"}
ANSWER_IDS = ["Q1", "Q2", "Q3", "Q4", "Q5", "Q6", "Q7", "Q8"]


def addendum_body(addendum: dict) -> dict:
    return {key: addendum[key] for key in ("schema", "consentScopeDigest", "sourceFamilies")}


def walk_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from walk_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from walk_strings(child)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record_raw = RECORD.read_bytes()
        cls.record = parse_json(cls.record_raw)
        cls.bare = parse_json(BARE.read_bytes())
        cls.consent = gate.load_consent()


class RecordTests(Base):
    def test_shape_and_identity(self):
        self.assertEqual(set(self.record), TOP)
        self.assertEqual((self.record["schema"], self.record["specification"], self.record["task"],
                          self.record["requirement"], self.record["decision"]),
                         ("agent-braid-spec066-s15b-corpus-addendum-record/v0.1", "SPEC-066", "T101", "REQ-101",
                          "adds-source-family-only"))
        self.assertEqual(self.record["decisionDate"], "2026-11-10")
        self.assertTrue((EVIDENCE / Path(self.record["amends"]).name).is_file())

    def test_it_grants_no_authority(self):
        self.assertIs(self.record["executionAuthorization"], False)
        self.assertIs(self.record["trainingAdmission"], False)
        self.assertEqual(self.record["conditions"]["fitting"], "not-admitted")

    def test_every_owner_answer_is_recorded(self):
        answers = self.record["ownerResponse"]["answers"]
        self.assertEqual([a["id"] for a in answers], ANSWER_IDS)
        self.assertTrue(all(set(a) == {"id", "answer"} and a["answer"] for a in answers))
        self.assertIn("not a verbatim transcript", self.record["ownerResponse"]["wording"])

    def test_conditions_match_the_owner_answers(self):
        c = self.record["conditions"]
        self.assertEqual(c["addedSourceFamilies"], [FAMILY])
        self.assertEqual(c["workspaceId"], gate.ADMITTED_WORKSPACE_ID)
        self.assertEqual((c["authorship"], c["thirdPartyAuthors"]), ("owner-authored-commits-only", "excluded"))
        self.assertEqual((c["corpusBuilding"], c["fitting"]), ("within-admitted-scope-only", "not-admitted"))
        self.assertEqual((c["labelOracle"], c["plannerAgreement"]), ("git merge-tree", "recorded-only"))
        self.assertEqual(c["revocationCommand"], "python -m scripts.spec066_s15b_observe --purge")
        self.assertEqual(c["retentionDays"], gate.RETENTION_DAYS)
        self.assertIn("manifest of digests kept", c["afterRetention"])
        self.assertEqual((c["minimumLabelledPairsPerClass"], c["belowMinimum"]), (30, "stop T104 and T105"))
        self.assertEqual(c["excludedWorkspaceEpisodes"], "ignored-not-purged")
        self.assertEqual(c["deferred"], ["Q3"])

    def test_the_excluded_workspaces_are_never_named_as_admitted(self):
        text = self.record_raw.decode()
        self.assertIn(gate.ADMITTED_WORKSPACE_ID, text)
        for identifier in gate.EXCLUDED_WORKSPACE_IDS:
            self.assertNotIn(identifier, text)

    def test_record_holds_no_path_identity_or_repository_name(self):
        for forbidden in ("/Users", "/home", "Repos/", "smart-notes", "kinetiq-core", "@", "Juan"):
            self.assertNotIn(forbidden, self.record_raw.decode())
        self.assertEqual([s for s in walk_strings(self.record) if s.startswith("/") or "\\" in s], [])

    def test_digests_are_recomputed_not_trusted(self):
        digests = self.record["digests"]
        self.assertEqual(digests["addendumDigest"], digest(addendum_body(self.record["addendum"])))
        self.assertEqual(digests["conditionsDigest"], digest(
            {"schema": "agent-braid-spec066-s15b-addendum-conditions/v1", "conditions": self.record["conditions"]}))
        self.assertEqual(digests["ownerReferenceDigest"], digest(
            {"schema": "agent-braid-spec066-s15b-addendum-owner-ref/v1", "date": self.record["decisionDate"],
             "answers": self.record["ownerResponse"]["answers"]}))

    def test_changing_an_answer_or_condition_breaks_a_digest(self):
        changed = copy.deepcopy(self.record)
        changed["ownerResponse"]["answers"][0]["answer"] += " and third parties"
        self.assertNotEqual(changed["digests"]["ownerReferenceDigest"], digest(
            {"schema": "agent-braid-spec066-s15b-addendum-owner-ref/v1", "date": changed["decisionDate"],
             "answers": changed["ownerResponse"]["answers"]}))
        changed = copy.deepcopy(self.record)
        changed["conditions"]["thirdPartyAuthors"] = "included"
        self.assertNotEqual(changed["digests"]["conditionsDigest"], digest(
            {"schema": "agent-braid-spec066-s15b-addendum-conditions/v1", "conditions": changed["conditions"]}))

    def test_duplicate_keys_are_refused_at_parse(self):
        doubled = self.record_raw.replace(b'"executionAuthorization": false,',
                                          b'"executionAuthorization": false, "executionAuthorization": true,')
        self.assertNotEqual(doubled, self.record_raw)
        with self.assertRaises(OwnedWorkError):
            parse_json(doubled)


class GateAcceptanceTests(Base):
    def test_bare_addendum_is_the_nested_one(self):
        self.assertEqual(self.bare, self.record["addendum"])
        self.assertEqual(set(self.bare), ADDENDUM)
        self.assertEqual(self.bare["sourceFamilies"], [FAMILY])

    def test_addendum_is_bound_to_the_t101_scope(self):
        self.assertEqual(self.bare["consentScopeDigest"], self.consent.scope_digest)

    def test_the_gate_admits_the_family_with_the_addendum_and_not_without(self):
        gate.require_source_family(FAMILY, consent=self.consent, addendum=self.bare)
        with self.assertRaises(gate.GateRefusal) as caught:
            gate.require_source_family(FAMILY, consent=self.consent)
        self.assertEqual(caught.exception.code, "source-family-not-admitted")

    def test_the_t101_record_itself_is_unchanged_and_does_not_list_the_family(self):
        self.assertNotIn(FAMILY, self.consent.source_families)

    def test_the_addendum_adds_only_the_family_it_names(self):
        for other in ("git-history replay", "unknown-family", "third-party-transcripts"):
            with self.subTest(other=other), self.assertRaises(gate.GateRefusal):
                gate.require_source_family(other, consent=self.consent, addendum=self.bare)

    def test_a_tampered_addendum_is_refused(self):
        widened = dict(self.bare, sourceFamilies=[FAMILY, "unknown-family"])
        rebound = dict(widened, digest=digest(addendum_body(widened)))
        rescoped_body = dict(addendum_body(self.bare), consentScopeDigest="1" * 64)
        cases = (dict(self.bare, digest="0" * 64), widened, {**self.bare, "extra": 1},
                 dict(rescoped_body, digest=digest(rescoped_body)))
        for addendum in cases:
            with self.subTest(addendum=sorted(addendum)), self.assertRaises(gate.GateRefusal):
                gate.require_source_family("unknown-family" if addendum is rebound else FAMILY,
                                           consent=self.consent, addendum=addendum)
        # a digest-consistent widening is accepted by the gate by design: the records are reviewed
        # in pull requests, which is why the committed file is checked against the owner answers here
        gate.require_source_family("unknown-family", consent=self.consent, addendum=rebound)

    def test_the_cli_reads_the_bare_file(self):
        from scripts import spec066_s15b_replay_labels as script
        loaded = script._load_addendum(str(BARE))
        gate.require_source_family(FAMILY, consent=self.consent, addendum=loaded)
        self.assertEqual(json.loads(BARE.read_text()), loaded)


if __name__ == "__main__":
    unittest.main()
