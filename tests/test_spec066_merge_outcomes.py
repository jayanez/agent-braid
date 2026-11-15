# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T405 (REQ-402): merge-outcome recorder, join, false-independence report and D7 rollback.

Temporary repositories, registries, consent records, secrets and promotion registries only: the owner's
repository, registry, shadow store and promotion registry are never read or written.
"""
from contextlib import redirect_stderr, redirect_stdout
from datetime import date
import io
import json
import os
from pathlib import Path
import shutil
import stat
import tempfile
import unittest
from unittest import mock

from agent_braid import system_one_promotion as promotion, system_one_shadow as shadow
from agent_braid.git_adapter import analyze_git_with_provenance
from research import s15b_corpus_gate as gate
from research import s15b_git_history_replay as replay
from research import s15b_merge_outcomes as outcomes
from research import s15b_outcome_observer as observer
from scripts import spec066_record_merge_outcomes as recorder
from scripts import spec066_s15b_observe as observe_script
from tests.test_spec066_git_history_replay import OWNER, THIRD, Repo
from tests.test_spec066_s15b_corpus_gate import make_record as make_consent, wid

SECRET = bytes(range(32, 64))
TODAY = date(2026, 11, 14)
EPISODE_DAY = date(2026, 11, 12)
EVIDENCE = "e" * 64
MANIFEST = "f" * 64


class Base(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="s1-merge-outcomes-")).resolve()
        self.addCleanup(shutil.rmtree, self.base, True)
        self.home = self.base / "home"
        self.home.mkdir(mode=0o700)
        scratch = self.base / "scratch"
        scratch.mkdir()
        self.repo = Repo(self.base / "admitted", scratch)
        self.exc1, self.exc2 = self.base / "exc1", self.base / "exc2"
        for path in (self.exc1, self.exc2):
            path.mkdir()
        self.unregistered = Repo(self.base / "unregistered", scratch)
        self.admitted_id = wid(self.repo.path)
        excluded = sorted({wid(self.exc1), wid(self.exc2)})
        for patch in (mock.patch.object(gate, "ADMITTED_WORKSPACE_ID", self.admitted_id),
                      mock.patch.object(gate, "EXCLUDED_WORKSPACE_IDS", frozenset(excluded))):
            patch.start()
            self.addCleanup(patch.stop)
        self.consent = self.base / "consent.json"
        self.consent.write_text(json.dumps(make_consent(self.admitted_id, excluded)))
        rows = [{"workspaceId": wid(p), "sourceRoot": str(p), "resultRoot": str(self.home / "results" / wid(p)),
                 "runtimeEnabled": False, "grantStore": None, "worktreeRoots": []}
                for p in (self.repo.path, self.exc1, self.exc2)]
        registry = self.home / "registry.json"
        registry.write_text(json.dumps({"schema": "agent-braid-plugin-registry/v0.2", "telemetry": "off",
                                        "workspaces": rows}))
        os.chmod(registry, 0o600)
        data = self.base / "data"
        data.mkdir(mode=0o700)
        self.store = data / "system-one"
        patch = mock.patch.object(shadow, "default_directory", lambda: self.store)
        patch.start()
        self.addCleanup(patch.stop)
        self.store.mkdir(mode=0o700)
        secret = self.store / shadow.SALT_FILE
        secret.write_bytes(SECRET)
        os.chmod(secret, 0o600)
        self.oids = {}
        self.build_history()

    def build_history(self):
        r = self.repo
        r.write(".gitignore", ".claude/*\n")
        r.write("a.txt", "1\n2\n3\n")
        r.write("c.txt", "x\n")
        r.commit("base")
        self.base_oid = r.git("rev-parse", "HEAD").stdout.strip()
        for name, path, text in (("one", "a.txt", "1\n2\none\n"), ("two", "docs/b.txt", "two\n"),
                                 ("three", "c.txt", "three\n"), ("four", "c.txt", "four\n")):
            r.git("checkout", "-q", "-b", f"secret-branch-{name}", self.base_oid)
            r.write(path, text)
            self.oids[name] = r.commit(f"secret message {name}")
        r.git("checkout", "-q", "-b", "secret-branch-other", self.base_oid)
        r.write("o.txt", "o\n")
        self.oids["other"] = r.commit("other", author=THIRD)
        r.git("checkout", "-q", "main")

    def record(self, *heads, **extra):
        options = dict(owner_email=OWNER, home=self.home, consent_path=self.consent, run_day=TODAY)
        options.update(extra)
        return recorder.record_wave(options.pop("repository", self.repo.path), list(heads), **options)

    # An episode of the same pair, as a live `analyze` call would store it; the answer is set explicitly.
    def episode(self, left, right, *, system2="unknown", choice="likely-independent", day=EPISODE_DAY):
        ctx = replay._Context(self.base / "ctx")
        pair = replay._Pair("branch-tip", self.oids[left], self.oids[right])
        pair.base = self.base_oid
        request = replay._request(self.repo.path.resolve(), pair)
        report, _ = analyze_git_with_provenance(request, env=ctx.env, budget=ctx.budget())
        episode = shadow.build_episode(report, "analyze", "git", request=request,
                                       salt=shadow._repo_salt(SECRET, str(self.repo.path)))
        episode["day"] = day.isoformat()
        episode["pairs"][0]["system2"] = system2
        episode["pairs"][0]["system2Determinate"] = system2 != "unknown"
        episode["classificationCounts"] = {name: int(name == system2) for name in shadow.CLASSIFICATIONS}
        episode["systemOne"]["answers"] = [{"choice": choice, "probabilities": {
            name: 1.0 if name == choice else 0.0 for name in shadow.CHOICES}}]
        shadow.validate_episode(episode)
        return episode

    def put_episodes(self, *episodes):
        by_day = {}
        for episode in episodes:
            by_day.setdefault(episode["day"], []).append(episode)
        for day, items in by_day.items():
            path = self.store / f"episodes-{day}.jsonl"
            path.write_text("".join(json.dumps(item, sort_keys=True) + "\n" for item in items))
            os.chmod(path, 0o600)

    def write_records(self, *heads):
        result = self.record(*heads)
        directory = outcomes.store_directory(home=self.home)
        outcomes.write_records(directory, result["records"], TODAY)
        return directory

    def observe(self):
        return observer.observe(observe_script.default_sources(self.home), TODAY, home=self.home,
                                consent_path=self.consent)

    def go(self, day="2026-11-12"):
        return promotion.record_go(self.home, "DP-1", evidence_digest=EVIDENCE, manifest_digest=MANIFEST,
                                   decided_on=day)


class RecorderTests(Base):
    def test_clean_and_conflicting_pairs_are_labelled_by_the_oracle(self):
        result = self.record("secret-branch-one", "secret-branch-two", "secret-branch-three", "secret-branch-four")
        kinds = sorted(r["outcomeKind"] for r in result["records"])
        self.assertEqual(kinds, ["merge-clean"] * 5 + ["merge-conflict"])
        self.assertEqual(result["evidence"]["pairs"]["enumerated"], 6)
        for record in result["records"]:
            outcomes.validate_record(record)
            self.assertIs(record["executionAuthorization"], False)
            self.assertGreaterEqual(len(record["variants"]), 1)

    def test_records_hold_no_path_ref_author_message_or_commit_id(self):
        result = self.record("secret-branch-one", "secret-branch-three", "secret-branch-four")
        text = json.dumps(result) + json.dumps(result["evidence"])
        directory = self.write_records("secret-branch-one", "secret-branch-three", "secret-branch-four")
        text += (directory / outcomes.FILENAME).read_text()
        for forbidden in ("a.txt", "c.txt", "secret", OWNER, THIRD, "Secret Person", str(self.base), self.admitted_id,
                          *self.oids.values(), self.base_oid, "git://", "refs/"):
            self.assertNotIn(forbidden, text)
        for line in (directory / outcomes.FILENAME).read_text().splitlines():
            record = json.loads(line)
            self.assertEqual(set(record), outcomes.FIELDS)
            with self.assertRaises(outcomes.MergeOutcomeError):
                outcomes.validate_record(dict(record, path="a.txt"))
            with self.assertRaises(outcomes.MergeOutcomeError):
                outcomes.validate_record(dict(record, variants=[{"left": ["a.txt"], "right": ["b"], "shared": []}]))

    def test_pseudonyms_equal_the_episode_pseudonyms_of_the_same_pair(self):
        result = self.record("secret-branch-one", "secret-branch-two")
        episode = self.episode("one", "two")["pairs"][0]["resourceHashes"]
        variants = result["records"][0]["variants"]
        self.assertIn(episode, variants)

    def test_unregistered_repository_is_refused(self):
        with self.assertRaises(gate.GateRefusal) as caught:
            self.record("main", "HEAD", repository=self.unregistered.path)
        self.assertEqual(caught.exception.code, "path-outside-admitted")

    def test_other_authors_are_skipped_and_counted(self):
        result = self.record("secret-branch-one", "secret-branch-other")
        self.assertEqual(result["records"], [])
        self.assertEqual(result["evidence"]["pairs"]["skipped"]["author-excluded"], 1)

    def test_missing_secret_and_bad_heads_are_closed_refusals(self):
        with self.assertRaises(recorder.RecordError) as caught:
            self.record("secret-branch-one", "-not-a-ref")
        self.assertEqual(caught.exception.code, "head-unresolved")
        with self.assertRaises(recorder.RecordError) as caught:
            self.record("secret-branch-one")
        self.assertEqual(caught.exception.code, "too-few-heads")
        (self.store / shadow.SALT_FILE).unlink()
        with self.assertRaises(recorder.RecordError) as caught:
            self.record("secret-branch-one", "secret-branch-two")
        self.assertEqual(caught.exception.code, "secret-absent")

    def test_write_is_private_ignored_deduplicated_and_never_creates_a_ref(self):
        before = sorted(self.repo.git("for-each-ref").stdout.splitlines())
        argv = ["--repository", str(self.repo.path), "--head", "secret-branch-one", "--head", "secret-branch-two",
                "--owner-email", OWNER, "--write", "--day", "2026-11-14"]
        out = io.StringIO()
        with redirect_stdout(out), mock.patch.object(replay, "today", lambda: TODAY):
            self.assertEqual(recorder.main(argv, home=self.home, consent_path=self.consent), 0)
            self.assertEqual(recorder.main(argv, home=self.home, consent_path=self.consent), 0)
        path = outcomes.store_path(home=self.home)
        self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(path.parent.stat().st_mode), 0o700)
        self.assertEqual(len(path.read_text().splitlines()), 1)
        self.assertEqual(json.loads(out.getvalue().split("\n}\n")[1] + "\n}")["store"], {"duplicate": 1})
        self.assertEqual(self.repo.git("status", "--porcelain").stdout, "")
        self.assertEqual(sorted(self.repo.git("for-each-ref").stdout.splitlines()), before)

    def test_write_is_refused_when_the_output_is_not_ignored(self):
        (self.repo.path / ".gitignore").write_text("")
        argv = ["--repository", str(self.repo.path), "--head", "secret-branch-one", "--head", "secret-branch-two",
                "--owner-email", OWNER, "--write"]
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            self.assertEqual(recorder.main(argv, home=self.home, consent_path=self.consent), 2)
        self.assertEqual(err.getvalue().strip(), "refused: output-not-ignored")
        self.assertFalse(outcomes.store_path(home=self.home).exists())

    def test_unregistered_repository_is_refused_by_the_command(self):
        argv = ["--repository", str(self.unregistered.path), "--head", "main", "--head", "HEAD", "--owner-email", OWNER]
        err = io.StringIO()
        with redirect_stdout(io.StringIO()), redirect_stderr(err):
            self.assertEqual(recorder.main(argv, home=self.home, consent_path=self.consent), 2)
        self.assertEqual(err.getvalue().strip(), "refused: path-outside-admitted")


class JoinTests(Base):
    def test_outcome_joins_the_episode_with_its_rule_answer(self):
        self.write_records("secret-branch-one", "secret-branch-two")
        self.put_episodes(self.episode("one", "two"))
        result = self.observe()
        self.assertEqual((result.counts["joined"], result.counts["advised-pairs"]), (1, 1))
        record = result.records[0]
        self.assertEqual((record["outcomeKind"], record["ruleAnswer"], record["pair"]["system2"]),
                         ("merge-clean", "likely-independent", "unknown"))
        observer.validate_record(record)

    def test_no_episode_is_counted_and_nothing_joins(self):
        self.write_records("secret-branch-one", "secret-branch-two")
        result = self.observe()
        self.assertEqual((result.counts["joined"], result.counts["no-episode"]), (0, 1))

    def test_episode_outside_the_window_is_no_episode(self):
        self.write_records("secret-branch-one", "secret-branch-two")
        self.put_episodes(self.episode("one", "two", day=date(2026, 11, 1)))
        self.assertEqual(self.observe().counts["no-episode"], 1)

    def test_two_matching_episodes_are_ambiguous_and_unlabelled(self):
        self.write_records("secret-branch-one", "secret-branch-two")
        self.put_episodes(self.episode("one", "two"), self.episode("one", "two", day=date(2026, 11, 13)))
        result = self.observe()
        self.assertEqual((result.counts["ambiguous"], result.counts["joined"], result.records), (1, 0, []))

    def test_rejoining_the_same_outcome_is_a_duplicate(self):
        self.write_records("secret-branch-one", "secret-branch-two")
        self.put_episodes(self.episode("one", "two"))
        first = observer.write_records(self.observe().records, TODAY)
        second = observer.write_records(self.observe().records, TODAY)
        self.assertEqual((first["written"], second["written"], second["duplicate"]), (1, 0, 1))

    def test_purge_removes_the_merge_outcome_file_only(self):
        directory = self.write_records("secret-branch-one", "secret-branch-two")
        self.assertTrue((directory / outcomes.FILENAME).exists())
        out = io.StringIO()
        with redirect_stdout(out):
            self.assertEqual(observe_script.main(["--purge"], home=self.home), 0)
        self.assertEqual(json.loads(out.getvalue())["mergeOutcomes"]["status"], "purged")
        self.assertFalse((directory / outcomes.FILENAME).exists())
        self.assertEqual(self.repo.git("status", "--porcelain").stdout, "")

    def test_source_outside_the_admitted_workspace_is_never_read(self):
        class Source:
            root = self.base / "elsewhere"
            read = False

            def outcomes(self, window):
                Source.read = True
                return iter(())

        result = observer.observe([Source()], TODAY, home=self.home, consent_path=self.consent)
        self.assertFalse(Source.read)
        self.assertEqual(result.counts["refused:path-outside-admitted"], 1)


class StatisticsTests(unittest.TestCase):
    def test_wilson_upper_bound_values(self):
        self.assertIsNone(observer.wilson_upper(0, 0))
        for failures, trials, expected in ((0, 10, 0.2775), (0, 30, 0.1136), (1, 10, 0.4045), (2, 50, 0.1346),
                                           (10, 10, 1.0)):
            self.assertAlmostEqual(observer.wilson_upper(failures, trials), expected, places=3)

    def test_false_independence_counts_only_conflicts_on_advised_pairs(self):
        def record(kind, answer):
            return {"outcomeKind": kind, "ruleAnswer": answer, "day": "2026-11-12"}

        rows = [record("merge-clean", "likely-independent")] * 3 + [
            record("merge-conflict", "likely-independent"), record("merge-conflict", "undetermined"),
            record("merge-conflict", None), record("merge-clean", "undetermined")]
        value = observer.false_independence(rows, advised_pairs=9)
        self.assertEqual((value["advisedPairsInEpisodes"], value["joinedOutcomes"], value["joinedOnAdvisedPairs"],
                          value["advisedMergeClean"], value["falseIndependent"]), (9, 7, 4, 3, 1))
        self.assertEqual(value["falseIndependenceRate"], 0.25)
        self.assertAlmostEqual(value["wilson95Upper"], observer.wilson_upper(1, 4), places=6)


class RollbackTests(Base):
    def conflict_record(self, answer, kind="merge-conflict", day=EPISODE_DAY):
        return {"outcomeKind": kind, "ruleAnswer": answer, "day": day.isoformat()}

    def state(self):
        return promotion.resolve("advise", promotion.load(self.home), MANIFEST)

    def test_first_false_independent_rolls_dp1_back_once_and_idempotently(self):
        self.go()
        self.assertEqual(self.state()["reason"], "owner-go")
        rows = [self.conflict_record("likely-independent")]
        self.assertTrue(observer.apply_auto_rollback(rows, TODAY, home=self.home))
        self.assertFalse(observer.apply_auto_rollback(rows, TODAY, home=self.home))
        records = promotion.load(self.home)
        self.assertEqual([r["decision"] for r in records], ["go", "rollback"])
        self.assertEqual(records[-1]["reason"], "auto-rollback-false-independence")
        self.assertEqual((self.state()["activeMode"], self.state()["reason"]),
                         ("off", "auto-rollback-false-independence"))
        self.assertIn(self.state()["reason"], promotion.REASONS)
        status = promotion.status(self.home, "advise", MANIFEST)
        self.assertEqual(status["decisionPoints"]["DP-1"]["reason"], "auto-rollback-false-independence")
        self.assertTrue(status["valid"])

    def test_no_rollback_on_clean_undetermined_unanswered_or_without_a_go(self):
        self.go()
        for row in (self.conflict_record("likely-independent", kind="merge-clean"),
                    self.conflict_record("undetermined"), self.conflict_record(None),
                    self.conflict_record("likely-conflicting")):
            self.assertFalse(observer.apply_auto_rollback([row], TODAY, home=self.home))
        self.assertEqual([r["decision"] for r in promotion.load(self.home)], ["go"])
        self.assertFalse(observer.apply_auto_rollback([], TODAY, home=self.home))

    def test_no_rollback_without_an_owner_go(self):
        self.assertFalse(observer.apply_auto_rollback([self.conflict_record("likely-independent")], TODAY,
                                                      home=self.home))
        self.assertEqual(promotion.load(self.home), ())

    def test_a_conflict_older_than_the_go_does_not_trigger_a_new_go(self):
        self.go(day="2026-11-13")
        self.assertFalse(observer.apply_auto_rollback([self.conflict_record("likely-independent")], TODAY,
                                                      home=self.home))
        self.assertTrue(observer.apply_auto_rollback(
            [self.conflict_record("likely-independent", day=date(2026, 11, 14))], TODAY, home=self.home))

    def test_registry_rejects_unknown_reasons_and_reasons_on_a_go(self):
        self.go()
        with self.assertRaises(promotion.PromotionError):
            promotion.rollback(self.home, "DP-1", decided_on="2026-11-14", reason="free text")
        records = promotion.load(self.home)
        self.assertEqual(len(records), 1)
        promotion.rollback(self.home, "DP-1", decided_on="2026-11-14")  # an owner rollback carries no reason
        self.assertNotIn("reason", promotion.load(self.home)[-1])
        path = self.home / promotion.FILENAME
        value = json.loads(path.read_text())
        value["records"][0]["reason"] = "auto-rollback-false-independence"
        path.write_text(json.dumps(value))
        self.assertFalse(promotion.status(self.home, "advise", MANIFEST)["valid"])

    def test_end_to_end_conflict_on_an_advised_pair_rolls_back_through_the_observer(self):
        self.go()
        self.write_records("secret-branch-three", "secret-branch-four")
        self.put_episodes(self.episode("three", "four"))
        evidence_directory = self.base / "evidence"
        evidence_directory.mkdir()
        out = io.StringIO()
        with redirect_stdout(out):
            yield_code = observe_script.main([], today=TODAY, evidence_directory=evidence_directory, home=self.home,
                                             consent_path=self.consent, locations={})
        report = json.loads(out.getvalue())
        self.assertEqual(yield_code, 0)
        self.assertEqual(report["falseIndependence"]["falseIndependent"], 1)
        self.assertEqual(report["falseIndependence"]["advisedPairsInEpisodes"], 1)
        self.assertEqual([r["decision"] for r in promotion.load(self.home)], ["go"])  # the yield report is read-only
        with redirect_stdout(io.StringIO()):
            code = observe_script.main(["--write"], today=TODAY, evidence_directory=evidence_directory,
                                       home=self.home, consent_path=self.consent, locations={})
            observe_script.main(["--write"], today=TODAY, evidence_directory=evidence_directory,
                                home=self.home, consent_path=self.consent, locations={})
        self.assertEqual(code, 0)
        self.assertEqual([r["decision"] for r in promotion.load(self.home)], ["go", "rollback"])
        written = (evidence_directory / f"s15b-observe-{TODAY.isoformat()}.json").read_text()
        for forbidden in (str(self.base), self.admitted_id, "c.txt", OWNER):
            self.assertNotIn(forbidden, written)


if __name__ == "__main__":
    unittest.main()
