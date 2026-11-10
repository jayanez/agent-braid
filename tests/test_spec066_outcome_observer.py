# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 S1.5b T102: outcome observer (T102-1 to T102-11 and boundary controls).

Synthetic roots, salts, registries, stores and outcome sources only: no real registry,
store, run record or corpus of the owner is read. Episodes are built through the shadow
module's `build_episode`, so the pseudonym derivation is the real one.
"""
from collections import Counter
from contextlib import redirect_stdout
from datetime import date
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest import mock

from agent_braid import system_one_shadow as shadow
from research import s15b_corpus_gate as gate
from research import s15b_outcome_observer as observer
from scripts import spec066_s15b_observe as script
from tests.test_spec066_s15b_corpus_gate import make_record as make_consent, wid

FIXTURE = json.loads((Path(__file__).parent / "fixtures/spec066_s15b/outcomes/synthetic.json").read_text())
SECRET = bytes.fromhex(FIXTURE["secretHex"])
TODAY = date(2026, 11, 10)
EPISODE_DAY = date(2026, 11, 8)
OUTCOME_DAY = date(2026, 11, 9)
MARK = "very-private-name"


class FakeSource:
    def __init__(self, root, rows):
        self.root, self.rows, self.read = root, rows, False

    def outcomes(self, window):
        self.read = True
        return iter(self.rows)


class Base(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="s15b-obs-")).resolve()
        self.addCleanup(shutil.rmtree, self.base, True)
        self.home = self.base / "plugin-home"
        self.home.mkdir(mode=0o700)
        self.adm, self.adm_wt = self.base / "admitted", self.base / "admitted-wt"
        self.exc1, self.exc2, self.other = self.base / "smart-notes", self.base / "kinetiq-core", self.base / "other"
        for root in (self.adm, self.adm_wt, self.exc1, self.exc2, self.other):
            (root / "src").mkdir(parents=True)
        self.admitted_id = wid(self.adm)
        self.excluded_ids = {wid(self.exc1), wid(self.exc2)}
        for patch in (mock.patch.object(gate, "ADMITTED_WORKSPACE_ID", self.admitted_id),
                      mock.patch.object(gate, "EXCLUDED_WORKSPACE_IDS", frozenset(self.excluded_ids))):
            patch.start()
            self.addCleanup(patch.stop)
        self.consent = self.base / "consent.json"
        self.consent.write_text(json.dumps(make_consent(self.admitted_id, sorted(self.excluded_ids))))
        rows = [{"workspaceId": wid(src), "sourceRoot": str(src), "resultRoot": str(self.home / "results" / wid(src)),
                 "runtimeEnabled": False, "grantStore": None, "worktreeRoots": [str(w) for w in wts]}
                for src, wts in ((self.adm, [self.adm_wt]), (self.exc1, []), (self.exc2, []))]
        registry = self.home / "registry.json"
        registry.write_text(json.dumps({"schema": "agent-braid-plugin-registry/v0.2", "telemetry": "off",
                                        "workspaces": rows}))
        os.chmod(registry, 0o600)
        data = self.base / ".local" / "share" / "agent-braid"
        data.mkdir(parents=True, mode=0o700)
        self.store = data / "system-one"
        self.patch = mock.patch.object(shadow, "default_directory", lambda: self.store)
        self.patch.start()
        self.addCleanup(self.patch.stop)
        self.own = data / observer.STORE_NAME

    # fixtures ---------------------------------------------------------------------
    def put_secret(self, secret=SECRET):
        self.store.mkdir(parents=True, mode=0o700, exist_ok=True)
        path = self.store / shadow.SALT_FILE
        path.write_bytes(secret)
        os.chmod(path, 0o600)

    def episode(self, name, root, day=EPISODE_DAY, secret=SECRET):
        pair = FIXTURE["pairs"][name]
        return observer.synthetic_episode(secret, root, pair["left"], pair["right"], day)

    def put_episodes(self, episodes):
        self.store.mkdir(parents=True, mode=0o700, exist_ok=True)
        by_day = {}
        for episode in episodes:
            by_day.setdefault(episode["day"], []).append(episode)
        for day, items in by_day.items():
            path = self.store / f"episodes-{day}.jsonl"
            path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in items))
            os.chmod(path, 0o600)

    def outcome(self, name="conflicting", kind="merge-conflict", day=OUTCOME_DAY, swap=False):
        pair = FIXTURE["pairs"][name]
        left, right = (pair["right"], pair["left"]) if swap else (pair["left"], pair["right"])
        return (kind, day, left, right)

    def observe(self, rows, root=None):
        source = FakeSource(self.adm / "src" if root is None else root, rows)
        result = observer.observe([source], TODAY, home=self.home, consent_path=self.consent)
        return result, source

    def listing(self, root):
        return sorted(str(p.relative_to(root)) for p in root.rglob("*")) if root.exists() else None


class JoinTests(Base):
    # T102-1
    def test_matching_outcome_joins_exactly_one_pair_with_random_key(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm)), self.episode("disjoint", str(self.adm))])
        first, source = self.observe([self.outcome()])
        second, _ = self.observe([self.outcome()])
        self.assertTrue(source.read)
        self.assertEqual(len(first.records), 1)
        record = first.records[0]
        self.assertEqual((record["outcomeKind"], record["joinStatus"], record["day"]),
                         ("merge-conflict", "joined", EPISODE_DAY.isoformat()))
        self.assertEqual(record["pair"]["system2"], "conflicting")
        self.assertNotEqual(record["joinKey"], second.records[0]["joinKey"])
        text = json.dumps(record["pair"], sort_keys=True).encode()
        for derived in (hashlib.sha256(text).hexdigest(), hashlib.sha256(text).hexdigest()[:32]):
            self.assertNotIn(derived.replace("-", ""), record["joinKey"].replace("-", ""))
        self.assertEqual(first.counts["joined"], 1)

    def test_side_order_does_not_matter(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm))])
        result, _ = self.observe([self.outcome(swap=True)])
        self.assertEqual(len(result.records), 1)

    # T102-2
    def test_no_outcome_leaves_pairs_unlabelled_and_writes_nothing(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm))])
        result, _ = self.observe([])
        self.assertEqual(result.records, [])
        self.assertEqual(observer.write_records(result.records, TODAY)["written"], 0)
        self.assertEqual(observer.load_records(TODAY), [])

    def test_no_match_counters_are_split(self):
        self.put_secret()
        none, _ = self.observe([self.outcome()])
        self.assertEqual((none.counts["no-episode"], none.counts["salt-unmatched"]), (1, 0))
        self.put_episodes([self.episode("conflicting", str(self.adm))])
        miss, _ = self.observe([self.outcome("disjoint")])
        self.assertEqual((miss.counts["no-episode"], miss.counts["salt-unmatched"]), (0, 1))
        self.assertEqual(miss.records, [])

    def test_episode_outside_the_seven_day_window_does_not_join(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm), day=date(2026, 11, 1))])
        result, _ = self.observe([self.outcome()])
        self.assertEqual((result.records, result.counts["no-episode"]), ([], 1))

    def test_outcome_before_the_episode_does_not_join(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm), day=EPISODE_DAY)])
        self.assertEqual(self.observe([self.outcome(day=date(2026, 11, 7))])[0].records, [])

    # T102-3
    def test_two_candidate_pairs_are_ambiguous_and_unlabelled(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm)),
                           self.episode("conflicting", str(self.adm), day=date(2026, 11, 7))])
        result, _ = self.observe([self.outcome()])
        self.assertEqual((result.records, result.counts["ambiguous"]), ([], 1))

    # T102-4
    def test_episode_without_pseudonyms_is_never_joined(self):
        self.put_secret()
        episode = self.episode("conflicting", str(self.adm))
        episode["pairs"][0]["resourceHashes"] = None
        self.put_episodes([episode])
        result, _ = self.observe([self.outcome()])
        self.assertEqual(result.records, [])
        self.assertEqual(result.counts["episodes-unattributable"], 1)
        self.assertEqual(result.counts["no-episode"], 1)

    # T102-5 and Q8
    def test_episode_from_another_workspace_salt_never_joins_and_is_never_persisted(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.exc1))])
        result, _ = self.observe([self.outcome()])
        self.assertEqual(result.records, [])
        self.assertEqual(result.counts["salt-unmatched"], 1)
        before = self.listing(self.store)
        observer.write_records(result.records, TODAY)
        observer.purge()
        self.assertEqual(self.listing(self.store), before)  # shadow store untouched, excluded episode kept

    def test_excluded_and_admitted_episodes_side_by_side_join_only_admitted(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.exc1)), self.episode("conflicting", str(self.exc2)),
                           self.episode("conflicting", str(self.adm))])
        result, _ = self.observe([self.outcome()])
        self.assertEqual(len(result.records), 1)
        self.assertEqual(result.records[0]["pair"]["resourceHashes"]["left"],
                         self.episode("conflicting", str(self.adm))["pairs"][0]["resourceHashes"]["left"])

    def test_missing_secret_joins_nothing_and_is_counted(self):
        self.put_episodes([self.episode("conflicting", str(self.adm))])
        result, _ = self.observe([self.outcome()])
        self.assertEqual((result.records, result.counts["secret-absent"]), ([], 1))

    # T102-11
    def test_end_to_end_with_source_root_string_and_worktree_string(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm))])
        self.assertEqual(len(self.observe([self.outcome()])[0].records), 1)
        pairs = observer.read_episodes(TODAY, Counter())
        outcome = observer.Outcome("merge-conflict", OUTCOME_DAY, {}, *[frozenset(FIXTURE["pairs"]["conflicting"][s])
                                                                        for s in ("left", "right")])
        only_worktree = observer.candidate_salts(SECRET, [str(self.adm_wt)])
        self.assertEqual(observer.match(outcome, [pairs[0]], only_worktree)[0], "no-match")
        self.assertEqual(observer.match(outcome, [pairs[0]], observer.candidate_salts(SECRET, [str(self.adm)]))[0],
                         "joined")
        self.put_episodes([self.episode("conflicting", str(self.adm_wt))])
        self.assertEqual(len(self.observe([self.outcome()])[0].records), 1)  # a worktree string is a candidate too

    def test_trailing_slash_and_realpath_variants_are_candidates(self):
        link = self.base / "link"
        link.symlink_to(self.adm)
        row = {"workspaceId": self.admitted_id, "sourceRoot": str(link), "worktreeRoots": [str(self.adm_wt)]}
        with mock.patch.object(observer.plugin_registry, "inspect_registry",
                               return_value={"value": {"workspaces": [row]}}):
            roots = observer.candidate_roots(home=self.home)
        for expected in (str(link), str(link) + "/", str(self.adm), str(self.adm_wt)):
            self.assertIn(expected, roots)
        self.assertNotIn(str(self.exc1), roots)  # only the admitted workspace's roots

    def test_positive_control(self):
        self.assertEqual(observer.positive_control(),
                         {"sourceRootStringJoins": True, "worktreeStringDoesNotJoin": True})


class GateTests(Base):
    # T102-6
    def test_non_admitted_source_is_refused_before_any_read(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm))])
        for root, code in ((self.other / "src", "path-outside-admitted"), (self.exc1 / "src", "workspace-excluded")):
            result, source = self.observe([self.outcome()], root=root)
            self.assertFalse(source.read)
            self.assertEqual((result.records, result.counts["refused:" + code]), ([], 1))
            self.assertEqual(result.counts["outcomes-seen"], 0)

    def test_invalid_outcomes_are_dropped_and_counted(self):
        self.put_secret()
        bad = [("label", OUTCOME_DAY, ["a"], ["b"]), ("merge-conflict", "2026-11-09", ["a"], ["b"]),
               ("merge-conflict", OUTCOME_DAY, [], ["b"]), ("merge-conflict", OUTCOME_DAY, ["a"], [5])]
        result, _ = self.observe(bad)
        self.assertEqual((result.counts["outcomes-seen"], result.counts["outcomes-invalid"]), (4, 4))

    def test_step_zero_inventory_on_empty_home_reports_zero(self):
        empty = self.base / "empty-home"
        empty.mkdir()
        report = observer.inventory(home=empty, consent_path=self.consent,
                                    locations={"runtime-state": self.base / "nothing"})
        self.assertEqual(report["runtime-state"]["status"], "refused")
        self.assertEqual(report["runtime-state"]["recordsByDay"], {})

    def test_inventory_counts_records_by_day_only_when_admitted(self):
        run = self.adm / "src" / "runs"
        run.mkdir()
        (run / f"{MARK}.json").write_text("{}")
        (run / "note.txt").write_text("x")
        report = observer.inventory(home=self.home, consent_path=self.consent, locations={"in": self.adm / "src"})
        self.assertEqual(report["in"]["status"], "read")
        self.assertEqual(sum(report["in"]["recordsByDay"].values()), 1)
        self.assertNotIn(MARK, json.dumps(report))


class RobustnessTests(Base):
    def test_registry_and_secret_failures_are_not_honest_absence(self):
        self.put_episodes([self.episode("conflicting", str(self.adm))])
        (self.store / shadow.SALT_FILE).write_bytes(b"short")
        os.chmod(self.store / shadow.SALT_FILE, 0o600)
        result, _ = self.observe([self.outcome()])
        self.assertEqual((result.counts["secret-unsafe"], result.counts["no-salt"], result.counts["salt-unmatched"]),
                         (1, 1, 0))
        self.put_secret()
        (self.home / "registry.json").unlink()
        result, _ = self.observe([self.outcome()], root=self.adm / "src")
        self.assertEqual(result.counts["refused:workspace-not-registered"], 1)  # the gate refuses first
        self.assertEqual(observer.candidate_roots(home=self.home), [])

    def test_source_errors_and_future_outcomes_are_contained(self):
        self.put_secret()

        class Boom(FakeSource):
            def outcomes(self, window):
                raise KeyError(str(self.root))

        result = observer.observe([Boom(self.adm / "src", [])], TODAY, home=self.home, consent_path=self.consent)
        self.assertEqual(result.counts["source-error"], 1)
        future = self.observe([self.outcome(day=date(2026, 11, 11))])[0]
        self.assertEqual(future.counts["outcomes-invalid"], 1)
        short = self.observe([("merge-conflict", OUTCOME_DAY)])[0]
        self.assertEqual(short.counts["source-error"], 1)

    def test_malformed_day_filename_does_not_break_the_store(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm))])
        records = self.observe([self.outcome()])[0].records
        observer.write_records(records, TODAY)
        (self.own / "outcomes-2026-13-45.jsonl").write_text("junk")
        self.assertEqual(len(observer.load_records(TODAY)), 1)
        self.assertEqual(observer.purge()["leftoverEntries"], 1)

    def test_episode_older_than_window_inside_a_retained_file_is_ignored(self):
        self.put_secret()
        episode = self.episode("conflicting", str(self.adm), day=date(2026, 9, 1))
        path = self.store / f"episodes-{EPISODE_DAY.isoformat()}.jsonl"
        path.write_text(json.dumps(episode) + "\n")
        os.chmod(path, 0o600)
        self.assertEqual(observer.read_episodes(TODAY, Counter()), [])

    def test_inventory_cap_stops_the_walk_and_says_so(self):
        run = self.adm / "src" / "runs"
        run.mkdir()
        for n in range(5):
            (run / f"{n}.json").write_text("{}")
        with mock.patch.object(observer, "MAX_INVENTORY_ENTRIES", 2):
            report = observer.inventory(home=self.home, consent_path=self.consent, locations={"in": self.adm / "src"})
        self.assertTrue(report["in"]["truncated"])
        self.assertLessEqual(sum(report["in"]["recordsByDay"].values()), 2)


class RecordTests(Base):
    def joined(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm))])
        return self.observe([self.outcome()])[0].records[0]

    # T102-7
    def test_record_has_only_closed_fields_and_no_identifier(self):
        record = self.joined()
        self.assertEqual(set(record), observer.RECORD_FIELDS)
        self.assertIs(record["executionAuthorization"], False)
        text = json.dumps(record)
        for forbidden in ("episodeId", "src/", ".py", str(self.base), "pkg", MARK):
            self.assertNotIn(forbidden, text)
        shadow.validate_episode(self.episode("conflicting", str(self.adm)))
        observer.validate_record(record)

    def test_validate_record_rejects_widening_and_unjoined(self):
        record = self.joined()
        for edit in (lambda r: r.update(episodeId="x"), lambda r: r.update(joinStatus="ambiguous"),
                     lambda r: r.update(outcomeKind="label"), lambda r: r.update(source="git-history-replay"),
                     lambda r: r.update(executionAuthorization=True), lambda r: r.update(joinKey="not-a-uuid"),
                     lambda r: r["pair"].update(resourceHashes=None), lambda r: r["pair"].update(path="src/a.py"),
                     lambda r: r["pair"]["resourceHashes"]["left"].append("zz")):
            broken = json.loads(json.dumps(record))
            edit(broken)
            with self.assertRaises(observer.ObserverRefused):
                observer.validate_record(broken)


class StoreTests(Base):
    def make(self, day=EPISODE_DAY):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm), day=day)])
        return self.observe([self.outcome(day=day if day > EPISODE_DAY else OUTCOME_DAY)])[0].records

    def test_write_is_private_deduplicated_and_beside_the_shadow_store(self):
        records = self.make()
        self.assertEqual(observer.write_records(records, TODAY)["written"], 1)
        again = self.make()
        self.assertEqual(observer.write_records(again, TODAY)["duplicate"], 1)
        self.assertEqual(len(observer.load_records(TODAY)), 1)
        self.assertEqual(self.own.parent, self.store.parent)
        self.assertEqual(oct(self.own.stat().st_mode & 0o777), "0o700")
        day_file = self.own / f"outcomes-{EPISODE_DAY.isoformat()}.jsonl"
        self.assertEqual(oct(day_file.stat().st_mode & 0o777), "0o600")
        self.assertFalse(any(path.name.startswith("outcomes-") for path in self.store.iterdir()))

    # T102-8
    def test_retention_anchors_to_episode_day_and_purge_removes_all(self):
        records = self.make()
        observer.write_records(records, TODAY)
        self.assertEqual(len(observer.load_records(date(2026, 12, 7))), 1)  # episode day + 29
        self.assertEqual(observer.load_records(date(2026, 12, 9)), [])  # expired by episode day, not join time
        self.assertEqual(self.listing(self.own), ["store.lock"])
        (self.store / f"episodes-{EPISODE_DAY.isoformat()}.jsonl").unlink()
        self.assertEqual(self.make(day=date(2026, 9, 1)), [])  # episode older than the window is not read
        observer.write_records(records, TODAY)
        stale = observer.write_records(records, date(2026, 12, 20))
        self.assertEqual(stale["refused:retention-expired"], 1)
        observer.write_records(records, TODAY)
        self.assertEqual(observer.purge()["status"], "purged")
        self.assertFalse(self.own.exists())
        self.assertEqual(observer.purge()["status"], "empty")

    def test_purge_never_touches_the_shadow_store(self):
        observer.write_records(self.make(), TODAY)
        before = self.listing(self.store)
        observer.purge()
        self.assertEqual(self.listing(self.store), before)

    def test_unsafe_store_and_files_are_refused(self):
        observer.write_records(self.make(), TODAY)
        day_file = self.own / f"outcomes-{EPISODE_DAY.isoformat()}.jsonl"
        os.chmod(day_file, 0o644)
        with self.assertRaises(observer.ObserverRefused):
            observer.load_records(TODAY)
        os.chmod(day_file, 0o600)
        day_file.write_text("not json\n")
        with self.assertRaises(observer.ObserverRefused):
            observer.load_records(TODAY)
        day_file.unlink()
        os.chmod(self.own, 0o755)
        with self.assertRaises(observer.ObserverRefused):
            observer.load_records(TODAY)

    def test_symlinked_episode_file_is_refused_not_followed(self):
        self.put_secret()
        target = self.base / "elsewhere.jsonl"
        target.write_text(json.dumps(self.episode("conflicting", str(self.adm))) + "\n")
        os.chmod(target, 0o600)
        (self.store / f"episodes-{EPISODE_DAY.isoformat()}.jsonl").symlink_to(target)
        counts = Counter()
        self.assertEqual(observer.read_episodes(TODAY, counts), [])
        self.assertEqual(counts["episode-files-refused"], 1)


class ConformanceTests(Base):
    # T102-9
    def test_observer_pseudonyms_equal_build_episode_for_a_fixture(self):
        pair = FIXTURE["pairs"]["conflicting"]
        episode = self.episode("conflicting", str(self.adm))
        salt = shadow._repo_salt(SECRET, str(self.adm))
        hashes = episode["pairs"][0]["resourceHashes"]
        outcome = observer.Outcome("merge-conflict", OUTCOME_DAY, {}, frozenset(pair["left"]), frozenset(pair["right"]))
        (sides, shared) = observer._expected(salt, outcome)
        self.assertEqual(sorted([hashes["left"], hashes["right"]]), sides)
        self.assertEqual(hashes["shared"], shared)
        self.assertEqual(hashes["left"], sorted({shadow._pseudonym(salt, r) for r in pair["left"]})[:shadow.MAX_HASHES])

    def test_hash_lists_truncate_like_the_shadow_store_and_never_join(self):
        left = [f"src/p/{n:03}.py" for n in range(40)]
        episode = observer.synthetic_episode(SECRET, str(self.adm), left, ["src/q/z.py"], EPISODE_DAY)
        self.assertEqual(len(episode["pairs"][0]["resourceHashes"]["left"]), shadow.MAX_HASHES)
        outcome = observer.Outcome("verify-fail", OUTCOME_DAY, {}, frozenset(left), frozenset(["src/q/z.py"]))
        salts = observer.candidate_salts(SECRET, [str(self.adm)])
        verdict = observer.match(outcome, [(EPISODE_DAY, episode["pairs"][0])], salts)
        self.assertEqual((verdict[0], verdict[3]), ("no-match", "truncated"))  # 32-lowest lists prove nothing

    def test_reader_never_creates_salt_or_store(self):
        self.assertIsNone(observer.read_secret())
        self.assertEqual(observer.read_episodes(TODAY, Counter()), [])
        self.assertFalse(self.store.exists())
        self.store.mkdir(mode=0o700)
        self.observe([self.outcome()])
        with redirect_stdout(io.StringIO()):
            script.main([], today=TODAY, home=self.home, consent_path=self.consent, locations={})
        self.assertEqual(self.listing(self.store), [])
        self.assertFalse(self.own.exists())

    def test_private_helpers_still_have_the_pinned_behaviour(self):
        salt = shadow._repo_salt(SECRET, "/r")
        self.assertEqual(len(salt), 32)
        self.assertIsNone(shadow._repo_salt(None, "/r"))
        self.assertRegex(shadow._pseudonym(salt, "a"), r"^[0-9a-f]{16}$")
        self.put_secret()
        self.assertEqual(shadow._read_secret(self.store / shadow.SALT_FILE), SECRET)
        self.assertEqual(shadow._store_root(create=False), self.store)
        self.assertEqual((shadow.SALT_FILE, shadow.MAX_HASHES, shadow.SCHEMA),
                         ("salt.key", 32, "agent-braid-s1-episode/v0.2"))


class ScriptTests(Base):
    def run_script(self, argv, rows=None):
        evidence = self.base / "evidence"
        evidence.mkdir(exist_ok=True)
        sources = [FakeSource(self.adm / "src", rows)] if rows is not None else None
        out = io.StringIO()
        with redirect_stdout(out):
            code = script.main(argv, today=TODAY, evidence_directory=evidence, home=self.home,
                               consent_path=self.consent, sources=sources, locations={})
        return code, out.getvalue(), evidence

    def test_yield_report_is_default_and_writes_nothing(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm))])
        code, out, evidence = self.run_script([], [self.outcome()])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["counts"]["joined"], 1)
        self.assertEqual(self.listing(evidence), [])
        self.assertFalse(self.own.exists())

    def test_write_appends_records_and_counts_only_evidence(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm))])
        code, out, evidence = self.run_script(["--write"], [self.outcome()])
        self.assertEqual(code, 0)
        written = json.loads((evidence / f"s15b-observe-{TODAY.isoformat()}.json").read_text())
        self.assertEqual((written["counts"]["written"], written["joinedByOutcomeKind"]["merge-conflict"]), (1, 1))
        self.assertEqual(len(observer.load_records(TODAY)), 1)
        text = (evidence / f"s15b-observe-{TODAY.isoformat()}.json").read_text()
        for forbidden in (str(self.base), self.admitted_id, "src/", "episodeId", MARK):
            self.assertNotIn(forbidden, text)
        self.assertIs(written["executionAuthorization"], False)

    def test_default_sources_yield_zero_and_report_the_inventory(self):
        code, out, _ = self.run_script([])
        value = json.loads(out)
        self.assertEqual((code, value["counts"]["outcomes-seen"], value["counts"]["joined"]), (0, 0, 0))
        self.assertEqual(value["counts"]["secret-absent"], 1)
        self.assertTrue(all(value["positiveControl"].values()))

    def test_purge_flag(self):
        self.put_secret()
        self.put_episodes([self.episode("conflicting", str(self.adm))])
        self.run_script(["--write"], [self.outcome()])
        code, out, _ = self.run_script(["--purge"])
        self.assertEqual((code, json.loads(out)["status"]), (0, "purged"))
        self.assertFalse(self.own.exists())

    def test_modes_are_mutually_exclusive(self):
        with self.assertRaises(SystemExit):
            with mock.patch("sys.stderr", io.StringIO()):
                script.main(["--write", "--purge"])


if __name__ == "__main__":
    unittest.main()
