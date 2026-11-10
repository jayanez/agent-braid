# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T101: the owner consent record admits only the agent-braid workspace corpus.

The SPEC-051 authority validator is reused, not changed. Synthetic roots and pins stand
in for everything the record does not carry; no real root is read. The validator
compares digests only: it refuses every root other than the single admitted one, and
which paths belong to a workspace is the plugin registry's decision, not its.
"""
import copy
import hashlib
import json
from pathlib import Path
import re
import unittest

from agent_braid.owned_work_authority import (
    OperatorRegistry, OwnedWorkError, canonical_bytes, digest, parse_json, resolve_authority,
)

RECORD = Path(__file__).resolve().parents[1] / "specs/066-system-one-shadow/evidence/owner-consent-s15b-corpus-20261110.json"
NOW = "2030-01-01T00:00:01Z"
TOP = {"schema", "specification", "task", "requirement", "decisionDate", "executionAuthorization",
       "trainingAdmission", "decision", "ownerResponse", "corpus", "digests", "validator", "limits"}
CORPUS = {"admission", "admittedWorkspaces", "excludedWorkspaces", "otherRepositories", "thirdPartySources",
          "sourceFamilies", "dataClass", "retentionDays", "revocation"}
ADMITTED_ENTRY = {"workspaceId", "includesRegisteredWorktrees", "sourceRootDigest"}
EXCLUDED_ENTRY = {"workspaceId", "status"}
OTHER_REPOSITORIES = "refused until a separate express owner approval names them"


def D(char: str) -> str:
    return char * 64


PINS = {"featureAllowlistDigest": D("e"), "oracleContractDigest": D("f"), "splitProtocolDigest": D("1")}


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


def admitted_root(record: dict) -> str:
    return record["corpus"]["admittedWorkspaces"][0]["sourceRootDigest"]


def _check(record: dict) -> None:
    def need(condition, code):
        if not condition:
            raise OwnedWorkError(code)
    need(isinstance(record, dict) and set(record) == TOP, "record-shape")
    corpus = record["corpus"]
    need(isinstance(corpus, dict) and set(corpus) == CORPUS, "record-shape")
    admitted, excluded = corpus["admittedWorkspaces"], corpus["excludedWorkspaces"]
    need(isinstance(admitted, list) and isinstance(excluded, list), "record-shape")
    need(all(isinstance(w, dict) and set(w) == ADMITTED_ENTRY for w in admitted)
         and all(isinstance(w, dict) and set(w) == EXCLUDED_ENTRY for w in excluded), "record-shape")
    need(isinstance(record["digests"], dict) and isinstance(record["ownerResponse"], dict), "record-shape")
    need(record["schema"] == "agent-braid-spec066-s15b-corpus-consent/v0.1" and record["specification"] == "SPEC-066"
         and record["task"] == "T101" and record["requirement"] == "REQ-101"
         and record["decision"] == "admitted-scope-only", "record-identity")
    need(record["executionAuthorization"] is False and record["trainingAdmission"] is False, "record-authority")
    need(corpus["thirdPartySources"] == "excluded" and corpus["admission"] == "owner-own-work-only"
         and corpus["otherRepositories"] == OTHER_REPOSITORIES
         and corpus["revocation"] == "agent-braid system-one purge", "record-corpus")
    need(all(w["status"] == "explicitly-not-admitted" for w in excluded) and len(excluded) == 2, "record-corpus")
    need(all(type(w["includesRegisteredWorktrees"]) is bool for w in admitted), "record-corpus")
    need(isinstance(corpus["sourceFamilies"], list) and all(isinstance(s, str) for s in corpus["sourceFamilies"]),
         "record-corpus")
    ids = [w["workspaceId"] for w in admitted + excluded]
    need(all(isinstance(i, str) and re.fullmatch(r"[0-9a-f]{32}", i) for i in ids), "record-corpus")
    need(len(admitted) == 1 and len(set(ids)) == len(ids), "record-corpus")
    need(admitted[0]["sourceRootDigest"] == root_digest(admitted[0]["workspaceId"]), "record-root")
    need(record["digests"]["scopeDigest"] == scope_digest(record), "record-scope")
    need(record["digests"]["consentReferenceDigest"] == consent_digest(record), "record-consent")
    need(corpus["dataClass"] == "structural-only" and corpus["retentionDays"] == 30, "record-bounds")


def check_record(record: dict) -> None:
    """Structural check of the record; every refusal is an OwnedWorkError with a fixed code."""
    try:
        _check(record)
    except (KeyError, TypeError, AttributeError):
        raise OwnedWorkError("record-shape") from None


def authority(record: dict) -> bytes:
    """What an operator would mint from the record; the pins here are synthetic test values."""
    return canonical_bytes(dict(
        schema="agent-braid-owned-work-authority/v1", decision="admitted", authorityId="a" * 32,
        sourceKind="owned-deterministic-development", sourceRootDigest=admitted_root(record),
        scopeDigest=record["digests"]["scopeDigest"],
        consentReferenceDigest=record["digests"]["consentReferenceDigest"],
        reviewRecordDigest=D("d"), validFromUTC="2030-01-01T00:00:00Z", validUntilUTC="2030-01-02T00:00:00Z",
        allowedActions=["read-metadata"],
        caps=dict(maxAttempts=1000, maxRecords=4096, maxRecordBytes=65536, maxStoreBytes=10485760,
                  retentionUTCDates=record["corpus"]["retentionDays"]),
        executionAuthorization=False, trainingAdmission=False, collector047Enabled=False, **PINS))


def registry_for(record: dict, raw: bytes) -> OperatorRegistry:
    return OperatorRegistry((raw,), frozenset({record["digests"]["consentReferenceDigest"]}), frozenset({D("d")}),
                            frozenset({admitted_root(record)}), frozenset(), D("2"))


def resolve(record: dict, *, root: str, scope: str | None = None, raw: bytes | None = None, registry="default"):
    raw = raw or authority(record)
    return resolve_authority(raw, registry_for(record, raw) if registry == "default" else registry,
                             source_root_digest=root, scope_digest=scope or record["digests"]["scopeDigest"],
                             expected_pins=PINS, actions=("read-metadata",), now_utc=NOW)


def iter_strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for child in value.values():
            yield from iter_strings(child)
    elif isinstance(value, list):
        for child in value:
            yield from iter_strings(child)


class Base(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = RECORD.read_bytes()
        cls.record = parse_json(cls.raw)

    def mutated(self, change, *, rebind=True):
        """A copy of the record changed by `change`; rebind keeps the scope digest honest so the
        content check, not the digest, has to refuse it."""
        changed = copy.deepcopy(self.record)
        change(changed)
        if rebind:
            changed["digests"]["scopeDigest"] = scope_digest(changed)
        return changed

    def assertRefused(self, code, call, *args, **kwargs):
        with self.assertRaises(OwnedWorkError) as caught:
            call(*args, **kwargs)
        self.assertEqual(caught.exception.code, code)


class ConsentRecordTests(Base):
    def test_record_is_strict_json_and_self_consistent(self):
        check_record(self.record)
        self.assertEqual(self.record["decisionDate"], "2026-11-10")
        self.assertEqual(self.record["ownerResponse"]["answer"], "Solo agent-braid (Recommended)")
        self.assertEqual(self.record["corpus"]["retentionDays"], 30)
        self.assertEqual(self.record["corpus"]["dataClass"], "structural-only")

    def test_exactly_the_agent_braid_workspace_is_admitted(self):
        corpus = self.record["corpus"]
        self.assertEqual([w["workspaceId"] for w in corpus["admittedWorkspaces"]], ["eedc05f71069fdb4af00c6b99932195b"])
        self.assertEqual(len(corpus["excludedWorkspaces"]), 2)
        self.assertEqual({w["status"] for w in corpus["excludedWorkspaces"]}, {"explicitly-not-admitted"})
        self.assertEqual(corpus["otherRepositories"], OTHER_REPOSITORIES)
        self.assertEqual(corpus["thirdPartySources"], "excluded")

    def test_record_holds_no_path_or_repository_name(self):
        text = self.raw.decode()
        for forbidden in ("/Users", "/home", "smart-notes", "kinetiq-core", "Repos/"):
            self.assertNotIn(forbidden, text)
        self.assertEqual([s for s in iter_strings(self.record) if s.startswith("/") or "\\" in s], [])

    def test_duplicate_keys_are_refused_at_parse(self):
        doubled = self.raw.replace(b'"executionAuthorization": false,',
                                   b'"executionAuthorization": false, "executionAuthorization": true,')
        self.assertNotEqual(doubled, self.raw)
        self.assertRefused("duplicate-key", parse_json, doubled)

    def test_malformed_records_are_refused_with_a_fixed_code_not_a_raw_exception(self):
        def drop(*path):
            def change(record):
                node = record
                for key in path[:-1]:
                    node = node[key]
                del node[path[-1]]
            return change
        cases = {
            "not an object": [],
            "missing digests": self.mutated(drop("digests"), rebind=False),
            "missing scopeDigest": self.mutated(drop("digests", "scopeDigest"), rebind=False),
            "missing ownerResponse": self.mutated(drop("ownerResponse"), rebind=False),
            "missing admitted id": self.mutated(drop("corpus", "admittedWorkspaces", 0, "workspaceId"), rebind=False),
            "admitted item not an object": self.mutated(lambda r: r["corpus"]["admittedWorkspaces"].__setitem__(0, "x")),
            "excluded item not an object": self.mutated(lambda r: r["corpus"]["excludedWorkspaces"].__setitem__(0, 7)),
            "admitted list is a string": self.mutated(lambda r: r["corpus"].__setitem__("admittedWorkspaces", "x")),
            "extra corpus key": self.mutated(lambda r: r["corpus"].__setitem__("extra", 1)),
            "extra top key": self.mutated(lambda r: r.__setitem__("extra", 1), rebind=False),
            "extra admitted key": self.mutated(lambda r: r["corpus"]["admittedWorkspaces"][0].__setitem__("extra", 1)),
        }
        for name, changed in cases.items():
            with self.subTest(name):
                self.assertRefused("record-shape", check_record, changed)

    def test_a_widened_or_altered_record_is_refused_for_its_content(self):
        smart_notes = workspace_id("/work/smart-notes")
        entry = {"workspaceId": smart_notes, "includesRegisteredWorktrees": False, "sourceRootDigest": root_digest(smart_notes)}
        first = self.record["corpus"]["admittedWorkspaces"][0]
        cases = [
            ("record-corpus", self.mutated(lambda r: r["corpus"]["admittedWorkspaces"].append(entry))),
            ("record-corpus", self.mutated(lambda r: r["corpus"]["excludedWorkspaces"].append({"workspaceId": first["workspaceId"], "status": "explicitly-not-admitted"}))),
            ("record-corpus", self.mutated(lambda r: r["corpus"]["excludedWorkspaces"].pop())),
            ("record-corpus", self.mutated(lambda r: r["corpus"].__setitem__("thirdPartySources", "included"))),
            ("record-corpus", self.mutated(lambda r: r["corpus"].__setitem__("otherRepositories", "allowed"))),
            ("record-corpus", self.mutated(lambda r: r["corpus"].__setitem__("revocation", "none"))),
            ("record-corpus", self.mutated(lambda r: r["corpus"].__setitem__("sourceFamilies", "everything"))),
            ("record-corpus", self.mutated(lambda r: r["corpus"]["admittedWorkspaces"][0].__setitem__("includesRegisteredWorktrees", "yes"))),
            ("record-corpus", self.mutated(lambda r: r["corpus"]["admittedWorkspaces"][0].__setitem__("workspaceId", "../x"))),
            ("record-corpus", self.mutated(lambda r: r["corpus"]["excludedWorkspaces"][0].__setitem__("workspaceId", ["a"]))),
            ("record-root", self.mutated(lambda r: r["corpus"]["admittedWorkspaces"][0].__setitem__("sourceRootDigest", D("0")))),
            ("record-bounds", self.mutated(lambda r: r["corpus"].__setitem__("retentionDays", 90))),
            ("record-bounds", self.mutated(lambda r: r["corpus"].__setitem__("dataClass", "raw"))),
            ("record-identity", self.mutated(lambda r: r.__setitem__("decision", "admitted"), rebind=False)),
            ("record-identity", self.mutated(lambda r: r.__setitem__("task", "T102"), rebind=False)),
            ("record-authority", self.mutated(lambda r: r.__setitem__("trainingAdmission", True), rebind=False)),
            ("record-authority", self.mutated(lambda r: r.__setitem__("executionAuthorization", True), rebind=False)),
            ("record-consent", self.mutated(lambda r: r["ownerResponse"].__setitem__("decisionAsRecorded", "All"), rebind=False)),
            ("record-consent", self.mutated(lambda r: r["ownerResponse"].__setitem__("answer", "All"), rebind=False)),
            # Content edits that leave the scope digest stale are caught by the digest.
            ("record-scope", self.mutated(lambda r: r["corpus"].__setitem__("sourceFamilies", ["everything"]), rebind=False)),
        ]
        for index, (code, changed) in enumerate(cases):
            with self.subTest(case=index, code=code):
                self.assertRefused(code, check_record, changed)


class ValidatorRefusalTests(Base):
    """The SPEC-051 validator admits the agent-braid root digest and refuses every other root digest."""

    def test_the_admitted_workspace_resolves_without_authority_to_run_or_train(self):
        context = resolve(self.record, root=admitted_root(self.record))
        self.assertIs(context.descriptor["executionAuthorization"], False)
        self.assertIs(context.descriptor["trainingAdmission"], False)
        self.assertEqual(context.actions, ("read-metadata",))

    def test_unregistered_repositories_excluded_workspaces_and_their_paths_are_refused(self):
        excluded = [w["workspaceId"] for w in self.record["corpus"]["excludedWorkspaces"]]
        paths = ("/work/unregistered-repo", "/work/agent-braid-fork", "/work", "/work/smart-notes",
                 "/work/smart-notes/.claude/worktrees", "/work/kinetiq-core", "/work/kinetiq-core/.claude/worktrees",
                 "/work/agent-braid/.claude/worktrees")
        for identifier in excluded + [workspace_id(p) for p in paths]:
            with self.subTest(workspace=identifier[:8]):
                self.assertRefused("authority-scope", resolve, self.record, root=root_digest(identifier))

    def test_the_descriptor_root_must_also_be_registered(self):
        other = root_digest(workspace_id("/work/unregistered-repo"))
        raw = canonical_bytes(dict(json.loads(authority(self.record)), sourceRootDigest=other))
        self.assertRefused("authority-scope", resolve, self.record, root=other, raw=raw)

    def test_a_widened_scope_digest_is_refused_even_for_the_admitted_root(self):
        widened = self.mutated(lambda r: r["corpus"]["excludedWorkspaces"].pop())
        self.assertRefused("authority-scope", resolve, self.record, root=admitted_root(self.record),
                           scope=scope_digest(widened))

    def test_no_registry_means_no_admission(self):
        self.assertRefused("missing-trusted-registry", resolve, self.record, root=admitted_root(self.record),
                           registry=None)


if __name__ == "__main__":
    unittest.main()
