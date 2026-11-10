# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 S1.5b W0: the corpus gate enforces the T101 consent on paths (G-1 to G-8).

Synthetic temporary workspaces, registries and consent records only: no real registry,
root or corpus is read. The real record is read once, as the repository file it is, to
prove that the shipped constants and the shipped record agree. The admitted and excluded
ids are patched to synthetic ones where a registry has to be built (a registry only
accepts a workspace id equal to the hash of its own source root).
"""
from datetime import date, datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
import unittest
from unittest import mock

from agent_braid.owned_work_authority import digest
from research import s15b_corpus_gate as gate

REAL = gate.CONSENT_PATH
MARK = "very-private-name"


def wid(root: Path) -> str:
    # the plugin registry's rule (agent_braid/plugin_registry.py, _workspace)
    return hashlib.sha256(str(root).encode()).hexdigest()[:32]


def resign(record: dict) -> dict:
    owner = record["ownerResponse"]
    record["digests"]["scopeDigest"] = digest({"schema": gate._SCOPE, "corpus": record["corpus"]})
    record["digests"]["consentReferenceDigest"] = digest(
        {"schema": gate._CONSENT_REF, "date": record["decisionDate"], "answer": owner["answer"],
         "decision": owner["decisionAsRecorded"]})
    return record


def make_record(admitted: str, excluded: list) -> dict:
    record = json.loads(REAL.read_text())
    corpus = record["corpus"]
    corpus["admittedWorkspaces"] = [{"workspaceId": admitted, "includesRegisteredWorktrees": True,
                                     "sourceRootDigest": digest({"schema": gate._ROOT, "workspaceId": admitted})}]
    corpus["excludedWorkspaces"] = [{"workspaceId": i, "status": "explicitly-not-admitted"} for i in excluded]
    return resign(record)


class RealRecordTests(unittest.TestCase):
    def test_shipped_constants_equal_the_real_record_and_it_verifies(self):
        record = json.loads(REAL.read_text())
        spec = importlib.util.spec_from_file_location("gate_fresh", gate.__file__)
        fresh = importlib.util.module_from_spec(spec)
        sys.modules["gate_fresh"] = fresh
        self.addCleanup(sys.modules.pop, "gate_fresh", None)
        spec.loader.exec_module(fresh)  # unpatched constants
        self.assertEqual(fresh.ADMITTED_WORKSPACE_ID, record["corpus"]["admittedWorkspaces"][0]["workspaceId"])
        self.assertEqual(fresh.EXCLUDED_WORKSPACE_IDS,
                         {w["workspaceId"] for w in record["corpus"]["excludedWorkspaces"]})
        consent = fresh.load_consent()
        self.assertEqual(consent.retention_days, 30)
        self.assertEqual(record["corpus"]["admittedWorkspaces"][0]["sourceRootDigest"],
                         digest({"schema": gate._ROOT, "workspaceId": fresh.ADMITTED_WORKSPACE_ID}))
        self.assertIn("System One shadow episodes", consent.source_families)
        self.assertNotIn("git-history replay", consent.source_families)


class GateTests(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="s15b-gate-")).resolve()
        self.addCleanup(shutil.rmtree, self.base, True)
        self.home = self.base / "home"
        self.home.mkdir(mode=0o700)
        self.adm, self.adm_wt = self.root("admitted"), self.root("admitted-wt")
        self.exc1, self.exc2, self.exc1_wt = self.root("smart-notes"), self.root("kinetiq-core"), self.root("sn-wt")
        self.other = self.root("unregistered")
        self.admitted_id, self.excluded_ids = wid(self.adm), {wid(self.exc1), wid(self.exc2)}
        for patch in (mock.patch.object(gate, "ADMITTED_WORKSPACE_ID", self.admitted_id),
                      mock.patch.object(gate, "EXCLUDED_WORKSPACE_IDS", frozenset(self.excluded_ids))):
            patch.start()
            self.addCleanup(patch.stop)
        self.consent_path = self.base / "consent.json"
        self.write_consent(make_record(self.admitted_id, sorted(self.excluded_ids)))
        self.register([(self.adm, [self.adm_wt]), (self.exc1, [self.exc1_wt]), (self.exc2, [])])

    def root(self, name):
        path = self.base / name
        (path / "src").mkdir(parents=True)
        (path / "src" / f"{MARK}.py").write_text("x")
        return path

    def write_consent(self, record):
        self.consent_path.write_text(json.dumps(record))

    def mutate(self, edit, *, sign=True):
        record = json.loads(self.consent_path.read_text())
        edit(record)
        self.write_consent(resign(record) if sign else record)

    def register(self, entries, *, mode=0o600):
        rows = [{"workspaceId": wid(src), "sourceRoot": str(src), "resultRoot": str(self.home / "results" / wid(src)),
                 "runtimeEnabled": False, "grantStore": None, "worktreeRoots": [str(w) for w in wts]}
                for src, wts in entries]
        path = self.home / "registry.json"
        path.write_text(json.dumps({"schema": "agent-braid-plugin-registry/v0.2", "telemetry": "off",
                                    "workspaces": rows}))
        os.chmod(path, mode)

    def admit(self, path):
        return gate.admit_path(path, home=self.home, consent_path=self.consent_path)

    def refused(self, path, code):
        with self.assertRaises(gate.GateRefusal) as caught:
            self.admit(path)
        self.assertEqual(caught.exception.code, code)
        self.assertNotIn(MARK, str(caught.exception))
        self.assertNotIn(str(self.base), str(caught.exception))

    def consent_refused(self, path=None):
        with self.assertRaises(gate.GateRefusal) as caught:
            gate.load_consent(self.consent_path if path is None else path)
        self.assertEqual(caught.exception.code, "consent-invalid")

    # G-1
    def test_admits_source_root_and_registered_worktree(self):
        self.assertEqual(self.admit(self.adm / "src" / f"{MARK}.py"),
                         {"workspaceId": self.admitted_id, "rootKind": "source-root"})
        self.assertEqual(self.admit(self.adm_wt / "src"), {"workspaceId": self.admitted_id, "rootKind": "worktree"})

    def test_missing_worktree_root_does_not_admit(self):
        shutil.rmtree(self.adm_wt)
        self.refused(self.adm_wt, "path-outside-admitted")

    # G-2
    def test_refuses_unregistered_excluded_and_their_worktrees(self):
        self.refused(self.other, "path-outside-admitted")
        for excluded in (self.exc1, self.exc2, self.exc1_wt):
            self.refused(excluded / "src", "workspace-excluded")

    def test_refuses_path_nested_under_admitted_and_excluded(self):
        nested = self.adm / "nested-excluded"
        nested.mkdir()
        self.register([(self.adm, [self.adm_wt]), (self.exc1, [nested]), (self.exc2, [])])
        self.refused(nested, "workspace-excluded")
        self.assertEqual(self.admit(self.adm / "src")["rootKind"], "source-root")

    def test_admitted_workspace_missing_from_registry(self):
        self.register([(self.exc1, [])])
        self.refused(self.adm, "workspace-not-registered")
        self.register([])
        self.refused(self.adm, "workspace-not-registered")

    def test_quarantined_admitted_row_is_not_registered(self):
        data = json.loads((self.home / "registry.json").read_text())
        data["workspaces"][0]["worktreeRoots"] = ["relative/root"]
        (self.home / "registry.json").write_text(json.dumps(data))
        self.refused(self.adm, "workspace-not-registered")

    # G-3
    def test_refuses_symlink_and_dotdot_escape(self):
        (self.adm / "escape").symlink_to(self.other)
        self.refused(self.adm / "escape" / "src", "path-outside-admitted")
        self.refused(str(self.adm / "src" / ".." / ".." / "unregistered"), "path-outside-admitted")
        self.refused(str(self.adm) + "/src/../src", "path-outside-admitted")
        (self.adm / "toexcluded").symlink_to(self.exc1)
        self.refused(self.adm / "toexcluded", "workspace-excluded")

    def test_refuses_bad_path_types(self):
        for bad in (None, 5, "a\0b"):
            self.refused(bad, "path-outside-admitted")

    def test_excluded_root_not_bypassed_by_case(self):
        nested = self.adm / "Excl"
        nested.mkdir()
        (nested / "f").write_text("x")
        self.register([(self.adm, []), (self.exc1, [nested]), (self.exc2, [])])
        self.refused(str(self.adm / "EXCL" / "f"), "workspace-excluded")

    def test_too_broad_worktree_root_is_dropped(self):
        for broad in (Path("/"), Path.home()):
            self.register([(self.adm, [broad])])
            with self.assertRaises(gate.GateRefusal):  # dropped here or quarantined by the registry
                self.admit(self.other)

    # G-4
    def test_refuses_widened_swapped_or_flagged_record(self):
        def widen(r):
            r["corpus"]["admittedWorkspaces"].append(dict(r["corpus"]["admittedWorkspaces"][0], workspaceId="1" * 32))

        def swap(r):
            r["corpus"]["admittedWorkspaces"][0]["workspaceId"] = "2" * 32

        def drop_excluded(r):
            r["corpus"]["excludedWorkspaces"].pop()

        def other_excluded(r):
            r["corpus"]["excludedWorkspaces"][0]["workspaceId"] = "3" * 32

        def execution(r):
            r["executionAuthorization"] = True

        def training(r):
            r["trainingAdmission"] = True

        def data_class(r):
            r["corpus"]["dataClass"] = "content"

        def retention(r):
            r["corpus"]["retentionDays"] = 90

        for edit in (widen, swap, drop_excluded, other_excluded, execution, training, data_class, retention):
            self.write_consent(make_record(self.admitted_id, sorted(self.excluded_ids)))
            self.mutate(edit)
            with self.subTest(edit.__name__):
                self.consent_refused()

    def test_refuses_unsigned_edits(self):
        self.mutate(lambda r: r["corpus"]["sourceFamilies"].append("git-history replay"), sign=False)
        self.consent_refused()
        self.write_consent(make_record(self.admitted_id, sorted(self.excluded_ids)))
        self.mutate(lambda r: r["ownerResponse"].update(answer="Everything"), sign=False)
        self.consent_refused()

    def test_refuses_unreadable_or_malformed_record(self):
        for content in ("", "{", "[]", '{"a":1,"a":2}'):
            self.consent_path.write_text(content)
            self.consent_refused()
        self.consent_refused(self.base / "missing.json")
        self.consent_refused(self.base)
        self.write_consent(make_record(self.admitted_id, sorted(self.excluded_ids)))
        link = self.base / "link.json"
        link.symlink_to(self.consent_path)
        self.consent_refused(link)

    def test_admit_path_without_valid_consent_fails_closed(self):
        with self.assertRaises(gate.GateRefusal) as caught:
            gate.admit_path(self.adm, home=self.home, consent_path=self.base / "gone.json")
        self.assertEqual(caught.exception.code, "consent-invalid")

    # G-5
    def test_refuses_missing_or_unreadable_registry(self):
        (self.home / "registry.json").unlink()
        self.refused(self.adm, "workspace-not-registered")
        self.register([(self.adm, [])], mode=0o644)
        self.refused(self.adm, "registry-unavailable")
        self.register([(self.adm, [])])
        (self.home / "registry.json").write_text("{not json")
        self.refused(self.adm, "registry-unavailable")
        (self.home / "registry.json").write_text("{}")
        self.refused(self.adm, "registry-unavailable")

    # G-6
    def test_source_families(self):
        consent = gate.load_consent(self.consent_path)
        for name in consent.source_families:
            gate.require_source_family(name, consent=consent)
        for name in ("git-history replay", "", None, "System One shadow episodes "):
            with self.assertRaises(gate.GateRefusal) as caught:
                gate.require_source_family(name, consent=consent)
            self.assertEqual(caught.exception.code, "source-family-not-admitted")

    def test_addendum_must_be_digest_and_scope_bound(self):
        consent = gate.load_consent(self.consent_path)
        body = {"schema": gate.ADDENDUM_SCHEMA, "consentScopeDigest": consent.scope_digest,
                "sourceFamilies": ["git-history replay"]}
        good = dict(body, digest=digest(body))
        gate.require_source_family("git-history replay", consent=consent, addendum=good)
        wrong_scope = dict(body, consentScopeDigest="1" * 64)
        for addendum in (dict(good, digest="0" * 64), dict(good, sourceFamilies=["x"]),
                         dict(good, consentScopeDigest="1" * 64), {**good, "extra": 1}, {}, "nope",
                         dict(wrong_scope, digest=digest(wrong_scope))):
            with self.subTest(addendum=str(addendum)[:30]), self.assertRaises(gate.GateRefusal):
                gate.require_source_family("git-history replay", consent=consent, addendum=addendum)
        with self.assertRaises(gate.GateRefusal):  # an addendum adds only the families it names
            gate.require_source_family("other", consent=consent, addendum=good)

    def test_retention(self):
        today = date(2026, 12, 10)
        self.assertEqual(gate.retention_cutoff(today), date(2026, 11, 10))
        gate.require_retained(date(2026, 11, 10), today)
        with self.assertRaises(gate.GateRefusal):
            gate.require_retained(datetime(2026, 11, 20), today)
        with self.assertRaises(gate.GateRefusal) as caught:
            gate.require_retained(date(2026, 11, 9), today)
        self.assertEqual(caught.exception.code, "retention-expired")

    # G-7
    def test_no_input_in_any_refusal_and_counter_is_closed(self):
        counter = gate.RefusalCounter()
        (self.adm / "escape").symlink_to(self.other)
        for target in (self.other, self.exc1, self.adm / "escape", "a/../b"):
            with self.assertRaises(gate.GateRefusal) as caught:
                self.admit(target)
            refusal = caught.exception
            counter.record(refusal)
            text = f"{refusal} {refusal!r} {refusal.args}"
            for secret in (MARK, str(self.base), self.admitted_id, *self.excluded_ids):
                self.assertNotIn(secret, text)
        self.assertEqual(tuple(counter.counts()), gate.CODES)
        self.assertEqual(sum(counter.counts().values()), 4)
        with self.assertRaises(ValueError):
            gate.GateRefusal("anything else")

    # G-8
    def test_gate_writes_nothing(self):
        def snapshot():
            return sorted((str(p), p.lstat().st_mtime_ns, p.lstat().st_size) for p in self.base.rglob("*"))
        before = snapshot()
        consent = gate.load_consent(self.consent_path)
        for target in (self.adm, self.other, self.exc1):
            try:
                self.admit(target)
            except gate.GateRefusal:
                pass
        gate.require_source_family("System One shadow episodes", consent=consent)
        self.assertEqual(snapshot(), before)


if __name__ == "__main__":
    unittest.main()
