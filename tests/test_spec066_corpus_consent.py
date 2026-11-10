# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T101: the owner consent record admits only the agent-braid workspace corpus.

The SPEC-051 authority validator is reused, not changed. Synthetic roots and pins stand
in for everything the record does not carry; no real root is read.
"""
import copy
import hashlib
import json
from pathlib import Path
import unittest

from agent_braid.owned_work_authority import (
    OperatorRegistry, OwnedWorkError, canonical_bytes, digest, parse_json, resolve_authority,
)

RECORD = Path(__file__).resolve().parents[1] / "specs/066-system-one-shadow/evidence/owner-consent-s15b-corpus-20261110.json"
D = lambda char: char * 64
NOW = "2030-01-01T00:00:01Z"
PINS = {"featureAllowlistDigest": D("e"), "oracleContractDigest": D("f"), "splitProtocolDigest": D("1")}
TOP = {"schema", "specification", "task", "requirement", "decisionDate", "executionAuthorization",
       "trainingAdmission", "decision", "ownerResponse", "corpus", "digests", "validator", "limits"}


def workspace_id(source_root: str) -> str:
    """The plugin registry's rule (agent_braid/plugin_registry.py): sha256 of the canonical source root."""
    return hashlib.sha256(source_root.encode()).hexdigest()[:32]


def root_digest(identifier: str) -> str:
    return digest({"schema": "agent-braid-spec066-s15b-corpus-root/v1", "workspaceId": identifier})


def scope_digest(record: dict) -> str:
    return digest({"schema": "agent-braid-spec066-s15b-corpus-scope/v1", "corpus": record["corpus"]})


def consent_digest(record: dict) -> str:
    response = record["ownerResponse"]
    return digest({"schema": "agent-braid-spec066-s15b-corpus-consent-ref/v1", "date": record["decisionDate"],
                   "answer": response["answer"], "decision": response["decisionAsRecorded"]})


CORPUS = {"admission", "admittedWorkspaces", "excludedWorkspaces", "otherRepositories", "thirdPartySources",
          "sourceFamilies", "dataClass", "retentionDays", "revocation"}


def check_record(record: dict) -> None:
    """Structural check of the record; raises OwnedWorkError with a fixed code."""
    def need(condition, code):
        if not condition:
            raise OwnedWorkError(code)
    need(isinstance(record, dict) and set(record) == TOP, "record-shape")
    need(isinstance(record["corpus"], dict) and set(record["corpus"]) == CORPUS, "record-shape")
    need(isinstance(record["corpus"]["admittedWorkspaces"], list)
         and isinstance(record["corpus"]["excludedWorkspaces"], list), "record-shape")
    need(record["corpus"]["thirdPartySources"] == "excluded" and record["corpus"]["admission"] == "owner-own-work-only"
         and all(w["status"] == "explicitly-not-admitted" for w in record["corpus"]["excludedWorkspaces"]), "record-corpus")
    need(record["executionAuthorization"] is False and record["trainingAdmission"] is False, "record-authority")
    corpus = record["corpus"]
    admitted = [w["workspaceId"] for w in corpus["admittedWorkspaces"]]
    excluded = [w["workspaceId"] for w in corpus["excludedWorkspaces"]]
    need(len(admitted) == 1 and not set(admitted) & set(excluded), "record-corpus")
    need(corpus["admittedWorkspaces"][0]["sourceRootDigest"] == root_digest(admitted[0]), "record-root")
    need(record["digests"]["scopeDigest"] == scope_digest(record), "record-scope")
    need(record["digests"]["consentReferenceDigest"] == consent_digest(record), "record-consent")
    need(corpus["dataClass"] == "structural-only" and corpus["retentionDays"] == 30, "record-bounds")


def authority(record: dict) -> bytes:
    """What an operator would mint from the record; the pins here are synthetic test values."""
    return canonical_bytes(dict(
        schema="agent-braid-owned-work-authority/v1", decision="admitted", authorityId="a" * 32,
        sourceKind="owned-deterministic-development",
        sourceRootDigest=record["corpus"]["admittedWorkspaces"][0]["sourceRootDigest"],
        scopeDigest=record["digests"]["scopeDigest"],
        consentReferenceDigest=record["digests"]["consentReferenceDigest"],
        reviewRecordDigest=D("d"), validFromUTC="2030-01-01T00:00:00Z", validUntilUTC="2030-01-02T00:00:00Z",
        allowedActions=["read-metadata"],
        caps=dict(maxAttempts=1000, maxRecords=4096, maxRecordBytes=65536, maxStoreBytes=10485760,
                  retentionUTCDates=30),
        executionAuthorization=False, trainingAdmission=False, collector047Enabled=False, **PINS))


def resolve(record: dict, *, root: str, scope: str | None = None):
    raw = authority(record)
    registry = OperatorRegistry(
        (raw,), frozenset({record["digests"]["consentReferenceDigest"]}), frozenset({D("d")}),
        frozenset({record["corpus"]["admittedWorkspaces"][0]["sourceRootDigest"]}), frozenset(), D("2"))
    return resolve_authority(raw, registry, source_root_digest=root,
                             scope_digest=scope or record["digests"]["scopeDigest"],
                             expected_pins=PINS, actions=("read-metadata",), now_utc=NOW)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = RECORD.read_bytes()
        cls.record = parse_json(cls.raw)

    def _with(self, path, value):
        changed = copy.deepcopy(self.record)
        node = changed
        for key in path[:-1]:
            node = node[key]
        node[path[-1]] = value
        return changed


    def _rebound(self, path, value):
        changed = self._with(path, value)
        changed["digests"]["scopeDigest"] = scope_digest(changed)
        return changed

    def _overlap(self):
        changed = copy.deepcopy(self.record)
        changed["corpus"]["excludedWorkspaces"].append(dict(changed["corpus"]["admittedWorkspaces"][0], status="explicitly-not-admitted"))
        changed["digests"]["scopeDigest"] = scope_digest(changed)
        return changed

    def _bad_root(self):
        changed = copy.deepcopy(self.record)
        changed["corpus"]["admittedWorkspaces"][0]["sourceRootDigest"] = D("0")
        changed["digests"]["scopeDigest"] = scope_digest(changed)
        return changed


class ConsentRecordTests(Base):
    def test_record_is_strict_json_and_self_consistent(self):
        check_record(self.record)
        self.assertEqual(self.record["decisionDate"], "2026-11-10")
        self.assertEqual(self.record["ownerResponse"]["answer"], "Solo agent-braid (Recommended)")
        self.assertEqual(self.record["corpus"]["retentionDays"], 30)
        self.assertEqual(self.record["corpus"]["dataClass"], "structural-only")
        self.assertIs(self.record["executionAuthorization"], False)
        self.assertIs(self.record["trainingAdmission"], False)

    def test_exactly_the_agent_braid_workspace_is_admitted(self):
        admitted = self.record["corpus"]["admittedWorkspaces"]
        self.assertEqual([w["workspaceId"] for w in admitted], ["eedc05f71069fdb4af00c6b99932195b"])
        self.assertEqual(len(self.record["corpus"]["excludedWorkspaces"]), 2)
        self.assertTrue(all(w["status"] == "explicitly-not-admitted" for w in self.record["corpus"]["excludedWorkspaces"]))
        self.assertIn("separate express owner approval", self.record["corpus"]["otherRepositories"])
        self.assertEqual(self.record["corpus"]["thirdPartySources"], "excluded")

    def test_record_holds_no_path_or_repository_name(self):
        text = self.raw.decode()
        for forbidden in ("/Users", "/home", "smart-notes", "kinetiq-core", "Repos/"):
            self.assertNotIn(forbidden, text)

        def strings(value):
            if isinstance(value, str):
                yield value
            elif isinstance(value, dict):
                for child in value.values():
                    yield from strings(child)
            elif isinstance(value, list):
                for child in value:
                    yield from strings(child)
        self.assertFalse([s for s in strings(self.record) if s.startswith("/") or "\\" in s])

    def test_duplicate_keys_and_wrong_types_are_refused_before_checking(self):
        with self.assertRaises(OwnedWorkError) as caught:
            parse_json(self.raw.replace(b'"executionAuthorization": false,', b'"executionAuthorization": false, "executionAuthorization": true,'))
        self.assertEqual(caught.exception.code, "duplicate-key")
        with self.assertRaises(OwnedWorkError) as caught:
            check_record([])
        self.assertEqual(caught.exception.code, "record-shape")

    def test_registered_worktrees_are_admitted_by_registry_membership_not_by_this_validator(self):
        self.assertIs(self.record["corpus"]["admittedWorkspaces"][0]["includesRegisteredWorktrees"], True)
        worktree = workspace_id("/work/agent-braid/.claude/worktrees")
        with self.assertRaises(OwnedWorkError) as caught:
            resolve(self.record, root=root_digest(worktree))
        self.assertEqual(caught.exception.code, "authority-scope")

    def test_a_registry_root_other_than_the_descriptor_root_is_refused(self):
        other = root_digest(workspace_id("/work/unregistered-repo"))
        raw = json.loads(authority(self.record))
        raw["sourceRootDigest"] = other
        raw = canonical_bytes(raw)
        registry = OperatorRegistry((raw,), frozenset({self.record["digests"]["consentReferenceDigest"]}), frozenset({D("d")}),
                                    frozenset({self.record["corpus"]["admittedWorkspaces"][0]["sourceRootDigest"]}), frozenset(), D("2"))
        with self.assertRaises(OwnedWorkError) as caught:
            resolve_authority(raw, registry, source_root_digest=other, scope_digest=self.record["digests"]["scopeDigest"],
                              expected_pins=PINS, actions=("read-metadata",), now_utc=NOW)
        self.assertEqual(caught.exception.code, "authority-scope")

    def test_a_widened_or_altered_record_is_refused(self):
        smart_notes = workspace_id("/work/smart-notes")
        widened = copy.deepcopy(self.record)
        widened["corpus"]["admittedWorkspaces"].append(
            {"workspaceId": smart_notes, "includesRegisteredWorktrees": False, "sourceRootDigest": root_digest(smart_notes)})
        for changed, code in [
            (widened, "record-corpus"),
            (self._with(("corpus", "retentionDays"), 90), "record-scope"),
            (self._with(("corpus", "dataClass"), "raw"), "record-scope"),
            (self._with(("corpus", "includesNothing"), 1), "record-shape"),
            (self._with(("corpus", "thirdPartySources"), "included"), "record-corpus"),
            (self._with(("corpus", "admittedWorkspaces"), "x"), "record-shape"),
            (self._with(("corpus", "sourceFamilies"), ["everything"]), "record-scope"),
            (self._with(("corpus", "otherRepositories"), "allowed"), "record-scope"),
            (self._with(("extra",), 1), "record-shape"),
            (self._rebound(("corpus", "retentionDays"), 90), "record-bounds"),
            (self._rebound(("corpus", "dataClass"), "raw"), "record-bounds"),
            (self._overlap(), "record-corpus"),
            (self._bad_root(), "record-root"),
            (self._with(("ownerResponse", "decisionAsRecorded"), "Todos"), "record-consent"),
            (self._with(("ownerResponse", "answer"), "Todos"), "record-consent"),
            (self._with(("trainingAdmission",), True), "record-authority"),
            (self._with(("executionAuthorization",), True), "record-authority"),
        ]:
            with self.subTest(code=code), self.assertRaises(OwnedWorkError) as caught:
                check_record(changed)
            self.assertEqual(caught.exception.code, code)


class ValidatorRefusalTests(Base):
    """The SPEC-051 validator admits the agent-braid root and refuses every other root."""

    def test_the_admitted_workspace_resolves_without_authority_to_run_or_train(self):
        context = resolve(self.record, root=self.record["corpus"]["admittedWorkspaces"][0]["sourceRootDigest"])
        self.assertIs(context.descriptor["executionAuthorization"], False)
        self.assertIs(context.descriptor["trainingAdmission"], False)
        self.assertEqual(context.actions, ("read-metadata",))

    def test_unregistered_repository_is_refused(self):
        for source in ("/work/unregistered-repo", "/work/agent-braid-fork", "/work"):
            with self.subTest(source=source), self.assertRaises(OwnedWorkError) as caught:
                resolve(self.record, root=root_digest(workspace_id(source)))
            self.assertEqual(caught.exception.code, "authority-scope")

    def test_smart_notes_and_kinetiq_core_are_refused_by_id_and_by_path(self):
        excluded = [w["workspaceId"] for w in self.record["corpus"]["excludedWorkspaces"]]
        candidates = excluded + [workspace_id(path) for path in (
            "/work/smart-notes", "/work/smart-notes/.claude/worktrees", "/work/kinetiq-core",
            "/work/kinetiq-core/.claude/worktrees")]
        for identifier in candidates:
            with self.subTest(workspace=identifier[:8]), self.assertRaises(OwnedWorkError) as caught:
                resolve(self.record, root=root_digest(identifier))
            self.assertEqual(caught.exception.code, "authority-scope")

    def test_a_widened_scope_digest_is_refused_even_for_the_admitted_root(self):
        widened = copy.deepcopy(self.record)
        widened["corpus"]["excludedWorkspaces"] = widened["corpus"]["excludedWorkspaces"][:1]
        with self.assertRaises(OwnedWorkError) as caught:
            resolve(self.record, root=self.record["corpus"]["admittedWorkspaces"][0]["sourceRootDigest"],
                    scope=scope_digest(widened))
        self.assertEqual(caught.exception.code, "authority-scope")

    def test_no_registry_means_no_admission(self):
        raw = authority(self.record)
        with self.assertRaises(OwnedWorkError) as caught:
            resolve_authority(raw, None, source_root_digest=self.record["corpus"]["admittedWorkspaces"][0]["sourceRootDigest"],
                              scope_digest=self.record["digests"]["scopeDigest"], expected_pins=PINS,
                              actions=("read-metadata",), now_utc=NOW)
        self.assertEqual(caught.exception.code, "missing-trusted-registry")


if __name__ == "__main__":
    unittest.main()
