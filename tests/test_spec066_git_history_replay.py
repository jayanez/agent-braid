# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 S1.5b T106: git-history replay labels (H-1 to H-11 and the closed-store controls).

Repositories are built in temporary directories by the tests; the owner's repository, registry,
consent addendum and shadow store are never read or written. The real consent record is read once,
as the repository file it is, to prove that the family is refused today.
"""
from contextlib import redirect_stderr, redirect_stdout
from datetime import date, timedelta
import io
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import tempfile
import unittest
from unittest import mock

from agent_braid import git_replay
from agent_braid.git_process import GitCommandResult
from agent_braid.owned_work_authority import digest
from research import s15b_corpus_gate as gate
from research import s15b_git_history_replay as replay
from scripts import spec066_s15b_replay_labels as script
from tests.test_spec066_s15b_corpus_gate import make_record, wid

OWNER = "owner.private@example.invalid"
THIRD = "third.party@example.invalid"
SECRET_NAMES = ("secret-feature-branch", "secret-file-name", OWNER, THIRD, "Secret Person")
RUN_DAY = date(2026, 11, 10)


def addendum_for(consent_path: Path) -> dict:
    body = {"schema": gate.ADDENDUM_SCHEMA, "consentScopeDigest": gate.load_consent(consent_path).scope_digest,
            "sourceFamilies": [replay.FAMILY]}
    return {**body, "digest": digest(body)}


class Repo:
    """A temporary non-bare repository with scripted history."""

    def __init__(self, path: Path, scratch: Path) -> None:
        self.path = path
        self.env = {"PATH": os.environ["PATH"], "HOME": str(scratch), "GIT_CONFIG_GLOBAL": os.devnull,
                    "GIT_CONFIG_NOSYSTEM": "1", "GIT_AUTHOR_NAME": "Secret Person", "GIT_AUTHOR_EMAIL": OWNER,
                    "GIT_COMMITTER_NAME": "Secret Person", "GIT_COMMITTER_EMAIL": OWNER,
                    "GIT_MERGE_AUTOEDIT": "no"}
        path.mkdir(parents=True)
        self.git("init", "-q", "-b", "main")

    def git(self, *args, check=True, author=None):
        env = dict(self.env)
        if author:
            env["GIT_AUTHOR_EMAIL"] = author
        done = subprocess.run(["git", "-C", str(self.path), *args], env=env, capture_output=True, text=True)
        if check and done.returncode:
            raise AssertionError(done.stderr)
        return done

    def write(self, name, text):
        target = self.path / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self, message="c", author=None):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message, author=author)
        return self.git("rev-parse", "HEAD").stdout.strip()

    def tree_state(self):
        git_dir = self.path / ".git"
        listing = sorted((str(p.relative_to(git_dir)), p.stat().st_size) for p in git_dir.rglob("*") if p.is_file())
        return listing


class Base(unittest.TestCase):
    def setUp(self):
        self.base = Path(tempfile.mkdtemp(prefix="s15b-replay-")).resolve()
        self.addCleanup(shutil.rmtree, self.base, True)
        self.home = self.base / "home"
        self.home.mkdir(mode=0o700)
        self.scratch = self.base / "scratch"
        self.scratch.mkdir()
        self.repo = Repo(self.base / "admitted", self.scratch)
        self.exc1, self.exc2, self.other = (self.base / name for name in ("exc1", "exc2", "unregistered"))
        for path in (self.exc1, self.exc2):
            path.mkdir()
        self.other_repo = Repo(self.other, self.scratch)
        self.admitted_id = wid(self.repo.path)
        self.excluded = {wid(self.exc1), wid(self.exc2)}
        for patch in (mock.patch.object(gate, "ADMITTED_WORKSPACE_ID", self.admitted_id),
                      mock.patch.object(gate, "EXCLUDED_WORKSPACE_IDS", frozenset(self.excluded))):
            patch.start()
            self.addCleanup(patch.stop)
        self.consent_path = self.base / "consent.json"
        self.consent_path.write_text(json.dumps(make_record(self.admitted_id, sorted(self.excluded))))
        self.register(self.repo.path, self.exc1, self.exc2)
        self.addendum = addendum_for(self.consent_path)
        self.store = self.base / "store" / replay.STORE_NAME
        self.salt_dir = self.base / "salt"
        self.salt_dir.mkdir(mode=0o700)

    def register(self, *roots):
        rows = [{"workspaceId": wid(p), "sourceRoot": str(p), "resultRoot": str(self.home / "results" / wid(p)),
                 "runtimeEnabled": False, "grantStore": None, "worktreeRoots": []} for p in roots]
        registry = self.home / "registry.json"
        registry.write_text(json.dumps({"schema": "agent-braid-plugin-registry/v0.2", "telemetry": "off",
                                        "workspaces": rows}))
        os.chmod(registry, 0o600)

    def run_replay(self, **kw):
        options = dict(owner_email=OWNER, addendum=self.addendum, home=self.home, consent_path=self.consent_path,
                       salt_dir=self.salt_dir, run_day=RUN_DAY)
        options.update(kw)
        return replay.replay(options.pop("repository", self.repo.path), **options)

    def build_history(self):
        """main with a clean merge, a conflicting merge and an unmerged branch."""
        r = self.repo
        r.write("a.txt", "1\n2\n3\n")
        r.write("c.txt", "x\n")
        r.commit("base")
        r.git("checkout", "-q", "-b", "side-clean")
        r.write("b.txt", "side\n")
        r.commit("side")
        r.git("checkout", "-q", "main")
        r.write("a.txt", "1\n2\nmain\n")
        r.commit("main")
        r.git("merge", "-q", "--no-ff", "-m", "merge clean", "side-clean")
        r.git("checkout", "-q", "-b", "side-conflict")
        r.write("c.txt", "side\n")
        r.commit("sc")
        r.git("checkout", "-q", "main")
        r.write("c.txt", "main\n")
        r.commit("mc")
        r.git("merge", "-q", "--no-ff", "side-conflict", check=False)
        r.write("c.txt", "resolved\n")
        r.commit("merge conflict")
        r.git("checkout", "-q", "-b", "secret-feature-branch")
        r.write("secret-file-name", "branch\n")
        r.commit("branch work")
        r.git("checkout", "-q", "main")
        r.write("d.txt", "later\n")
        r.commit("later main")

    def kinds(self, result):
        return sorted(r["outcomeKind"] or r["unlabelledReason"] for r in result["records"])


class LabelTests(Base):
    def test_h1_h2_clean_and_conflicting_pairs_are_labelled_by_merge_tree(self):
        self.build_history()
        result = self.run_replay()
        self.assertEqual(self.kinds(result), ["merge-clean", "merge-clean", "merge-conflict"])
        evidence = result["evidence"]["pairs"]
        self.assertEqual(evidence["byOrigin"], {"merge-commit": 2, "branch-tip": 1})
        self.assertEqual(evidence["labelled"], {"merge-clean": 2, "merge-conflict": 1})
        for record in result["records"]:
            replay.validate_record(record)
            self.assertEqual(record["source"], "git-history-replay")
            self.assertIs(record["executionAuthorization"], False)
            self.assertEqual(record["day"], "2026-11-10")
            self.assertEqual(record["pair"]["system2"] in ("independent-candidate", "ordered", "conflicting", "unknown"),
                             True)

    def test_h3_pair_without_merge_base_stays_unlabelled(self):
        self.build_history()
        r = self.repo
        r.git("checkout", "-q", "--orphan", "unrelated")
        r.git("rm", "-rfq", ".")
        r.write("z.txt", "z\n")
        r.commit("orphan")
        r.git("checkout", "-q", "main")
        result = self.run_replay()
        self.assertIn("no-merge-base", self.kinds(result))
        orphan = [x for x in result["records"] if x["unlabelledReason"] == "no-merge-base"][0]
        self.assertIsNone(orphan["outcomeKind"])
        self.assertIsNone(orphan["pair"])

    def test_h4_oracle_failure_stays_unlabelled_and_is_never_imputed(self):
        self.build_history()
        real = replay.run_git

        def failing(cwd, args, **kw):
            if "merge-tree" in args:
                return GitCommandResult(b"", b"boom", 2)
            return real(cwd, args, **kw)

        with mock.patch.object(replay, "run_git", failing):
            result = self.run_replay()
        self.assertEqual(self.kinds(result), ["oracle-error"] * 3)
        self.assertEqual(result["evidence"]["pairs"]["labelled"], {"merge-clean": 0, "merge-conflict": 0})

    def test_exit_one_without_tree_line_is_not_a_conflict(self):
        self.build_history()
        real = replay.run_git

        def odd(cwd, args, **kw):
            if "merge-tree" in args:
                return GitCommandResult(b"not a tree\n", b"", 1)
            return real(cwd, args, **kw)

        with mock.patch.object(replay, "run_git", odd):
            self.assertEqual(self.kinds(self.run_replay()), ["oracle-error"] * 3)

    def test_h7c_octopus_merge_is_skipped_with_its_reason(self):
        r = self.repo
        r.write("a.txt", "1\n")
        r.commit("base")
        for name in ("o1", "o2"):
            r.git("checkout", "-q", "-b", name, "main")
            r.write(f"{name}.txt", name)
            r.commit(name)
        r.git("checkout", "-q", "main")
        r.git("merge", "-q", "--no-ff", "-m", "octopus", "o1", "o2")
        result = self.run_replay()
        self.assertEqual(result["evidence"]["pairs"]["skipped"]["octopus"], 1)
        self.assertNotIn("merge-commit", [k for k, v in result["evidence"]["pairs"]["byOrigin"].items() if v])

    def test_h8_pair_over_64_paths_is_unlabelled(self):
        r = self.repo
        r.write("a.txt", "1\n")
        r.commit("base")
        r.git("checkout", "-q", "-b", "wide")
        for index in range(git_replay.MAX_PATHS + 1):
            r.write(f"many/f{index}.txt", "x")
        r.commit("wide")
        r.git("checkout", "-q", "main")
        r.write("m.txt", "m")
        r.commit("main")
        result = self.run_replay()
        self.assertEqual(self.kinds(result), ["too-many-paths"])

    def test_h10_planner_agreement_is_recorded_and_never_changes_the_label(self):
        self.build_history()
        baseline = self.kinds(self.run_replay())
        for outcome, expected in (({"result": "divergent"}, None), ({"result": "equivalent-observed"}, None)):
            with mock.patch.object(git_replay, "produce", return_value=(outcome, {})):
                result = self.run_replay()
            self.assertEqual(self.kinds(result), baseline)
        with mock.patch.object(git_replay, "produce", return_value=({"result": "divergent"}, {})):
            result = self.run_replay()
        by_kind = {r["outcomeKind"]: r["plannerAgrees"] for r in result["records"]}
        self.assertIs(by_kind["merge-conflict"], True)
        self.assertIs(by_kind["merge-clean"], False)
        with mock.patch.object(git_replay, "produce", side_effect=git_replay.InvalidGitReplay("x")):
            result = self.run_replay()
        self.assertEqual({r["plannerAgrees"] for r in result["records"]}, {"unavailable"})
        self.assertEqual(self.kinds(result), baseline)
        real = self.run_replay()  # the real planner answers for at least one fixture pair
        self.assertTrue(any(isinstance(r["plannerAgrees"], bool) for r in real["records"]))

    def test_h11_git_older_than_2_38_is_reported_not_guessed(self):
        self.build_history()
        with mock.patch.object(replay, "git_version", return_value=(2, 37)):
            result = self.run_replay()
        self.assertEqual(self.kinds(result), ["git-too-old"] * 3)
        self.assertIs(result["evidence"]["gitSupportsMergeTree"], False)
        with mock.patch.object(replay, "git_version", return_value=None):
            self.assertEqual(self.kinds(self.run_replay()), ["git-too-old"] * 3)

    def test_shallow_repository_is_objects_missing(self):
        self.build_history()
        with mock.patch.object(replay, "_precheck", wraps=replay._precheck):
            real = replay.run_git

            def shallow(cwd, args, **kw):
                if "--is-shallow-repository" in args:
                    return GitCommandResult(b"true\n", b"", 0)
                return real(cwd, args, **kw)

            with mock.patch.object(replay, "run_git", shallow):
                self.assertEqual(self.kinds(self.run_replay()), ["objects-missing"] * 3)

    def test_cap_samples_deterministically(self):
        self.build_history()
        with mock.patch.object(replay, "MAX_PAIRS", 2):
            first, second = self.run_replay(), self.run_replay()
        self.assertEqual(len(first["records"]), 2)
        self.assertTrue(first["evidence"]["pairs"]["sampledToCap"])
        self.assertEqual(self.kinds(first), self.kinds(second))
        self.assertEqual(first["evidence"]["pairs"]["byOrigin"], second["evidence"]["pairs"]["byOrigin"])

    def test_third_party_authors_are_excluded_and_counted(self):
        self.build_history()
        r = self.repo
        r.git("checkout", "-q", "-b", "theirs")
        r.write("t.txt", "t")
        r.commit("theirs", author=THIRD)
        r.git("checkout", "-q", "main")
        r.write("e.txt", "e")
        r.commit("e")
        result = self.run_replay()
        self.assertEqual(result["evidence"]["pairs"]["skipped"]["author-excluded"], 1)
        self.assertEqual(len(result["records"]), 3)
        self.assertEqual(self.kinds(self.run_replay(owner_email=OWNER.upper())), self.kinds(result))

    def test_owner_identity_is_required(self):
        for bad in ("", "no-at-sign", None):
            with self.assertRaises(replay.ReplayError) as caught:
                self.run_replay(owner_email=bad)
            self.assertEqual(caught.exception.code, "owner-identity-missing")

    def test_join_keys_are_random_across_runs(self):
        self.build_history()
        first = {r["joinKey"] for r in self.run_replay()["records"]}
        second = {r["joinKey"] for r in self.run_replay()["records"]}
        self.assertEqual(len(first), 3)
        self.assertFalse(first & second)


class GateTests(Base):
    def test_h5_unregistered_repository_is_refused(self):
        self.other_repo.write("a", "1")
        self.other_repo.commit("x")
        with self.assertRaises(gate.GateRefusal) as caught:
            self.run_replay(repository=self.other)
        self.assertEqual(caught.exception.code, "path-outside-admitted")
        for excluded in (self.exc1, self.exc2):
            with self.assertRaises(gate.GateRefusal) as caught:
                self.run_replay(repository=excluded)
            self.assertEqual(caught.exception.code, "workspace-excluded")

    def test_h6_admitted_repository_is_refused_without_the_addendum(self):
        self.build_history()
        for addendum in (None, {**self.addendum, "digest": "0" * 64},
                         {**self.addendum, "sourceFamilies": ["other"]}):
            with self.assertRaises(gate.GateRefusal) as caught:
                self.run_replay(addendum=addendum)
            self.assertEqual(caught.exception.code, "source-family-not-admitted")
        self.assertTrue(self.run_replay()["records"])  # the same call with the addendum works

    def test_h6_real_consent_does_not_list_the_family(self):
        record = json.loads(gate.CONSENT_PATH.read_text())
        real_id = record["corpus"]["admittedWorkspaces"][0]["workspaceId"]
        real_excluded = frozenset(w["workspaceId"] for w in record["corpus"]["excludedWorkspaces"])
        with mock.patch.object(gate, "ADMITTED_WORKSPACE_ID", real_id), \
                mock.patch.object(gate, "EXCLUDED_WORKSPACE_IDS", real_excluded), \
                self.assertRaises(gate.GateRefusal) as caught:
            gate.require_source_family(replay.FAMILY)
        self.assertEqual(caught.exception.code, "source-family-not-admitted")

    def test_subdirectory_of_an_outer_repository_is_re_admitted_at_its_toplevel(self):
        outer = Repo(self.base / "outer", self.scratch)
        outer.write("a", "1")
        outer.commit("x")
        inner = outer.path / "inner"
        inner.mkdir()
        self.register(inner, self.exc1, self.exc2)
        with mock.patch.object(gate, "ADMITTED_WORKSPACE_ID", wid(inner)):
            self.consent_path.write_text(json.dumps(make_record(wid(inner), sorted(self.excluded))))
            addendum = addendum_for(self.consent_path)
            with self.assertRaises(gate.GateRefusal) as caught:
                replay.replay(inner, owner_email=OWNER, addendum=addendum, home=self.home,
                              consent_path=self.consent_path, run_day=RUN_DAY)
        self.assertEqual(caught.exception.code, "path-outside-admitted")

    def test_sanitized_environment_keys_are_pinned(self):
        env = replay.sanitized_environment(self.base / "envhome")
        self.assertEqual(tuple(env), replay._ENV_KEYS)
        self.assertEqual(env["GIT_CONFIG_COUNT"], str(len(replay._FORCED_CONFIG)))
        self.assertEqual(env["GIT_CONFIG_GLOBAL"], os.devnull)
        self.assertEqual(env["GIT_CONFIG_NOSYSTEM"], "1")
        # the SPEC-012 environment it was copied from still has the same keys
        self.assertLessEqual(set(git_replay._sanitized_environment(self.base / "other-home")), set(env))


class SafetyTests(Base):
    def test_h7_no_object_or_file_is_written_into_the_repository(self):
        self.build_history()
        before_listing = self.repo.tree_state()
        before_count = self.repo.git("count-objects", "-v").stdout
        self.run_replay()
        self.assertEqual(self.repo.git("count-objects", "-v").stdout, before_count)
        self.assertEqual(self.repo.tree_state(), before_listing)
        self.assertEqual(self.repo.git("status", "--porcelain").stdout, "")

    def test_h7b_merge_drivers_and_attributes_of_the_repository_are_not_used(self):
        self.build_history()
        marker = self.base / "driver-ran"
        self.repo.git("config", "merge.evil.driver", f"touch {marker}; false")
        self.repo.git("config", "core.hooksPath", str(self.base / "hooks"))
        (self.repo.path / ".git" / "info").mkdir(exist_ok=True)
        (self.repo.path / ".git" / "info" / "attributes").write_text("* merge=evil\n")
        self.repo.write(".gitattributes", "* merge=evil\n")
        self.repo.commit("attributes")
        result = self.run_replay()
        self.assertFalse(marker.exists())
        self.assertIn("merge-conflict", self.kinds(result))

    def test_h9_no_commit_path_author_or_ref_in_any_output(self):
        self.build_history()
        result = self.run_replay()
        oids = set(self.repo.git("rev-list", "--all").stdout.split())
        text = json.dumps(result)
        for secret in (*SECRET_NAMES, *oids, str(self.base), "a.txt", "c.txt", "side-clean", "side-conflict"):
            self.assertNotIn(secret, text)
        with self.assertRaises(gate.GateRefusal) as caught:
            self.run_replay(addendum=None)
        self.assertNotIn(str(self.base), str(caught.exception))
        stdout, stderr = io.StringIO(), io.StringIO()
        with redirect_stdout(stdout), redirect_stderr(stderr):
            code = script.main(["--repository", str(self.repo.path), "--owner-email", OWNER, "--dry-run"],
                               home=self.home, consent_path=self.consent_path, salt_dir=self.salt_dir)
        self.assertEqual(code, 2)
        self.assertEqual(stderr.getvalue(), "refused: source-family-not-admitted\n")
        self.assertEqual(stdout.getvalue(), "")

    def test_salt_is_read_never_created(self):
        self.build_history()
        absent = self.run_replay()
        self.assertEqual(os.listdir(self.salt_dir), [])
        self.assertTrue(all(r["pair"]["resourceHashes"] is None for r in absent["records"] if r["pair"]))
        salt = self.salt_dir / "salt.key"
        salt.write_bytes(os.urandom(32))
        os.chmod(salt, 0o600)
        present = self.run_replay()
        self.assertEqual(os.listdir(self.salt_dir), ["salt.key"])
        self.assertTrue(any(r["pair"]["resourceHashes"] for r in present["records"] if r["pair"]))
        os.chmod(salt, 0o644)  # unsafe salt is treated as absent, not repaired
        self.assertIsNone(replay.read_salt(self.salt_dir))

    def test_the_shadow_store_is_not_written(self):
        self.build_history()
        with mock.patch.object(replay.shadow, "append", side_effect=AssertionError("episode store written")), \
                mock.patch.object(replay.shadow, "_secret", side_effect=AssertionError("salt created")):
            self.run_replay()


class HardeningTests(Base):
    def test_repository_config_cannot_run_a_program_through_git_log(self):
        r = self.repo
        r.write("a.txt", "1\n")
        r.commit("base")
        r.git("checkout", "-q", "-b", "feat")
        r.write("b.txt", "2\n")
        r.commit("feat")
        r.git("checkout", "-q", "main")
        r.write("c.txt", "3\n")
        r.commit("main")
        marker = self.base / "gpg-ran"
        program = self.base / "gpg.sh"
        program.write_text(f"#!/bin/sh\ntouch {marker}\nexit 1\n")
        os.chmod(program, 0o755)
        r.git("config", "log.showSignature", "true")
        r.git("config", "gpg.program", str(program))
        r.git("config", "core.fsmonitor", f"touch {marker}")
        result = self.run_replay()
        self.assertFalse(marker.exists())
        self.assertEqual(self.kinds(result), ["merge-clean"])

    def test_fast_forward_shaped_pairs_are_not_diverged_and_not_labelled(self):
        r = self.repo
        r.write("a.txt", "1\n")
        r.commit("base")
        r.git("checkout", "-q", "-b", "ahead")
        r.write("b.txt", "2\n")
        r.commit("ahead")
        r.git("checkout", "-q", "main")
        r.git("merge", "-q", "--no-ff", "-m", "ff-shaped", "ahead")
        r.git("checkout", "-q", "-b", "ahead2")
        r.write("e.txt", "5\n")
        r.commit("ahead2")
        r.git("checkout", "-q", "main")
        result = self.run_replay()
        self.assertEqual(result["records"], [])
        self.assertEqual(result["evidence"]["pairs"]["skipped"]["not-diverged"], 2)

    def test_duplicate_branch_tips_make_one_pair(self):
        self.build_history()
        self.repo.git("branch", "twin", "secret-feature-branch")
        self.assertEqual(self.run_replay()["evidence"]["pairs"]["byOrigin"]["branch-tip"], 1)

    def test_many_local_branches_do_not_exhaust_the_enumeration_budget(self):
        # A real checkout keeps hundreds of merged local branches; enumeration must not spend
        # one git command per branch (a 64-command budget was exhausted and reported as
        # git-unavailable).
        self.build_history()
        for index in range(100):
            self.repo.git("branch", f"merged-{index:03d}", "main~1")
        pairs = self.run_replay()["evidence"]["pairs"]
        self.assertEqual(pairs["byOrigin"]["branch-tip"], 1)

    def test_total_analysis_failure_stops_the_run(self):
        self.build_history()
        with mock.patch.object(replay.shadow, "build_episode", side_effect=KeyError("x")):
            with self.assertRaises(replay.ReplayError) as caught:
                self.run_replay()
        self.assertEqual(caught.exception.code, "analysis-failed")

    def test_wrong_owner_identity_is_visible_in_the_evidence(self):
        self.build_history()
        result = self.run_replay(owner_email="someone.else@example.invalid")
        self.assertEqual(result["records"], [])
        self.assertIs(result["evidence"]["allPairsExcludedByAuthor"], True)

    def test_a_failing_shallow_probe_is_an_error_not_a_data_state(self):
        self.build_history()
        real = replay.run_git

        def broken(cwd, args, **kw):
            if "--is-shallow-repository" in args:
                return GitCommandResult(b"", b"err", 129)
            return real(cwd, args, **kw)

        with mock.patch.object(replay, "run_git", broken), self.assertRaises(replay.ReplayError) as caught:
            self.run_replay()
        self.assertEqual(caught.exception.code, "git-unavailable")

    def test_unexpected_exception_prints_a_closed_message_only(self):
        self.build_history()
        err = io.StringIO()
        with mock.patch.object(replay, "replay", side_effect=RuntimeError(str(self.repo.path))), \
                redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = script.main(["--repository", str(self.repo.path), "--owner-email", OWNER, "--dry-run"])
        self.assertEqual((code, err.getvalue()), (2, "refused: internal-error\n"))


class StoreTests(Base):
    def records(self):
        self.build_history()
        return self.run_replay()["records"]

    def test_write_is_private_atomic_and_replaces_the_same_day(self):
        records = self.records()
        self.assertEqual(replay.write_records(records, store=self.store, run_day=RUN_DAY), 3)
        replay.write_records(records, store=self.store, run_day=RUN_DAY)
        self.assertEqual(os.listdir(self.store), ["replay-2026-11-10.jsonl"])
        self.assertEqual(stat.S_IMODE(os.stat(self.store).st_mode), 0o700)
        path = self.store / "replay-2026-11-10.jsonl"
        self.assertEqual(stat.S_IMODE(os.stat(path).st_mode), 0o600)
        lines = path.read_text().splitlines()
        self.assertEqual(len(lines), 3)
        for line in lines:
            self.assertEqual(set(json.loads(line)), replay.RECORD_KEYS)

    def test_write_supersedes_every_earlier_replay_file_and_keeps_other_names(self):
        records = self.records()
        self.store.mkdir(parents=True, mode=0o700)
        for name in ("replay-2026-10-01.jsonl", "replay-2026-11-09.jsonl", "replay-2026-99-99.jsonl", "keep.txt"):
            (self.store / name).write_text("{}\n")
        replay.write_records(records, store=self.store, run_day=RUN_DAY)
        self.assertEqual(sorted(os.listdir(self.store)), ["keep.txt", "replay-2026-11-10.jsonl"])

    def test_unsafe_store_is_refused(self):
        records = self.records()
        target = self.base / "elsewhere"
        target.mkdir()
        link = self.base / "link"
        link.symlink_to(target)
        for store in (link,):
            with self.assertRaises(replay.ReplayError) as caught:
                replay.write_records(records, store=store, run_day=RUN_DAY)
            self.assertEqual(caught.exception.code, "store-unsafe")
        loose = self.base / "loose"
        loose.mkdir(mode=0o755)
        os.chmod(loose, 0o755)
        with self.assertRaises(replay.ReplayError):
            replay.write_records(records, store=loose, run_day=RUN_DAY)
        self.assertEqual(os.listdir(target), [])

    def test_record_validation_rejects_open_shapes(self):
        record = self.records()[0]
        for edit in (lambda r: r.update(extra=1), lambda r: r.update(source="real-run"),
                     lambda r: r.update(outcomeKind="verify-pass"), lambda r: r.update(joinStatus="unlabelled"),
                     lambda r: r.update(plannerAgrees="maybe"), lambda r: r.update(day="today"),
                     lambda r: r.update(executionAuthorization=True)):
            broken = json.loads(json.dumps(record))
            edit(broken)
            with self.assertRaises(ValueError):
                replay.validate_record(broken)


class ScriptTests(Base):
    def call(self, *args):
        out, err = io.StringIO(), io.StringIO()
        evidence = self.base / "evidence"
        addendum = self.base / "addendum.json"
        addendum.write_text(json.dumps(self.addendum))
        with redirect_stdout(out), redirect_stderr(err):
            code = script.main(["--repository", str(self.repo.path), "--owner-email", OWNER,
                                "--addendum", str(addendum), *args], output_dir=evidence, home=self.home,
                               consent_path=self.consent_path, salt_dir=self.salt_dir, store=self.store)
        return code, out.getvalue(), err.getvalue(), evidence

    def test_dry_run_prints_counts_and_writes_nothing(self):
        self.build_history()
        code, out, err, evidence = self.call("--dry-run")
        self.assertEqual((code, err), (0, ""))
        data = json.loads(out)
        self.assertEqual(data["pairs"]["labelled"], {"merge-clean": 2, "merge-conflict": 1})
        self.assertFalse(evidence.exists())
        self.assertFalse(self.store.exists())

    def test_write_stores_records_and_evidence(self):
        self.build_history()
        code, out, _, evidence = self.call("--write")
        self.assertEqual(code, 0)
        self.assertEqual(json.loads((evidence / "s15b-replay-" f"{json.loads(out)['date']}.json").read_text()),
                         json.loads(out))
        self.assertEqual(len(os.listdir(self.store)), 1)
        for secret in SECRET_NAMES:
            self.assertNotIn(secret, out)

    def test_mode_is_required_and_a_bad_addendum_fails_closed(self):
        with self.assertRaises(SystemExit), redirect_stderr(io.StringIO()):
            script.main(["--repository", str(self.repo.path), "--owner-email", OWNER])
        bad = self.base / "bad.json"
        bad.write_text("not json")
        err = io.StringIO()
        with redirect_stderr(err), redirect_stdout(io.StringIO()):
            code = script.main(["--repository", str(self.repo.path), "--owner-email", OWNER, "--addendum", str(bad),
                                "--dry-run"], home=self.home, consent_path=self.consent_path)
        self.assertEqual((code, err.getvalue()), (2, "refused: source-family-not-admitted\n"))


if __name__ == "__main__":
    unittest.main()
