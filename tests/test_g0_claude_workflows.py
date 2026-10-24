# SPDX-License-Identifier: AGPL-3.0-only
"""Tests for the G0 experiment kit (census, probe, scorer) on synthetic data only."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

KIT = Path(__file__).resolve().parents[1] / "research" / "g0-claude-workflows"


def load(name):
    spec = importlib.util.spec_from_file_location(f"g0_{name}", KIT / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


probe = load("probe")
scorer = load("scorer")
census = load("census")

ROOT_A = "/w/a"
ROOT_B = "/w/b"


def use(call_id, name, **params):
    return json.dumps({"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": call_id, "name": name, "input": params}]}})


def result(call_id, error=False):
    return json.dumps({"type": "user", "message": {"content": [
        {"type": "tool_result", "tool_use_id": call_id, "is_error": error}]}})


def ok(call_id, name, **params):
    return [use(call_id, name, **params), result(call_id)]


def all_ints(value):
    if isinstance(value, dict):
        return all(isinstance(k, str) and all_ints(v) for k, v in value.items())
    if isinstance(value, list):
        return all(all_ints(v) for v in value)
    return isinstance(value, int) and not isinstance(value, bool)


class ProbeTests(unittest.TestCase):
    def run_probe(self, a_lines, b_lines):
        return probe.probe([(ROOT_A, a_lines), (ROOT_B, b_lines)])

    def test_unreadable_transcript_fails_without_echoing_the_path(self):
        result = subprocess.run(
            [sys.executable, str(KIT / "probe.py"), "--agent", ROOT_A,
             "/nonexistent/private-dir-name/transcript.jsonl"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")
        self.assertNotIn("private-dir-name", result.stderr)

    def test_read_by_one_written_by_other_is_one_ordered_pair(self):
        out = self.run_probe(ok("1", "Read", file_path="/w/a/src/x.py"),
                             ok("2", "Edit", file_path="/w/b/src/x.py"))
        self.assertEqual(out["run"]["ordered_pairs_with_overlap"], 1)
        self.assertEqual(out["run"]["distinct_paths_with_overlap"], 1)
        self.assertEqual(out["agents"][0]["read"], 1)
        self.assertEqual(out["agents"][1]["write"], 1)

    def test_reader_that_also_writes_the_path_is_not_a_hazard(self):
        out = self.run_probe(ok("1", "Read", file_path="/w/a/x.py") + ok("2", "Write", file_path="/w/a/x.py"),
                             ok("3", "Write", file_path="/w/b/x.py"))
        self.assertEqual(out["run"]["ordered_pairs_with_overlap"], 0)

    def test_write_write_and_read_read_are_not_flagged(self):
        out = self.run_probe(ok("1", "Write", file_path="/w/a/x.py") + ok("2", "Read", file_path="/w/a/y.py"),
                             ok("3", "Write", file_path="/w/b/x.py") + ok("4", "Read", file_path="/w/b/y.py"))
        self.assertEqual(out["run"]["ordered_pairs_with_overlap"], 0)

    def test_pairs_are_ordered_and_paths_distinct(self):
        a = ok("1", "Read", file_path="/w/a/p.py") + ok("2", "Edit", file_path="/w/a/q.py")
        b = ok("3", "Read", file_path="/w/b/q.py") + ok("4", "NotebookEdit", notebook_path="/w/b/p.py")
        out = self.run_probe(a, b)
        self.assertEqual((out["run"]["ordered_pairs_with_overlap"],
                          out["run"]["distinct_paths_with_overlap"]), (2, 2))

    def test_failed_and_unpaired_calls_are_never_effects(self):
        a = [use("1", "Read", file_path="/w/a/x.py"), result("1", error=True),
             use("2", "Read", file_path="/w/a/x.py")]
        out = self.run_probe(a, ok("3", "Edit", file_path="/w/b/x.py"))
        self.assertEqual(out["run"]["ordered_pairs_with_overlap"], 0)
        agent = out["agents"][0]
        self.assertEqual((agent["total_calls"], agent["failed_or_unpaired_calls"],
                          agent["failed_read_calls"]), (2, 2, 2))

    def test_failed_reads_are_reported_separately_and_are_not_unknown_writers(self):
        a = [use("1", "Read", file_path="/w/a/x.py"), result("1", error=True),
             use("2", "Read", file_path="/w/a/y.py")] + ok("3", "Read", file_path="/w/a/z.py")
        agent = self.run_probe(a, [])["agents"][0]
        self.assertEqual((agent["denominator_calls"], agent["unknown_writer_calls"],
                          agent["failed_read_calls"]), (3, 0, 2))

    def test_failed_and_resultless_write_class_calls_are_unknown_writers(self):
        a = ([use("1", "Edit", file_path="/w/a/x.py"), result("1", error=True),
              use("2", "Write", file_path="/w/a/y.py")]  # request with no result record
             + ok("3", "NotebookEdit", notebook_path="/w/a/n.ipynb"))
        out = self.run_probe(a, ok("4", "Read", file_path="/w/b/x.py") + ok("5", "Read", file_path="/w/b/y.py"))
        agent = out["agents"][0]
        self.assertEqual((agent["denominator_calls"], agent["unknown_writer_calls"],
                          agent["failed_write_calls"]), (3, 2, 2))
        self.assertEqual(out["run"]["ordered_pairs_with_overlap"], 0)  # failed writes are no effect

    def test_unknown_writer_classes_and_read_only_searches_are_split(self):
        lines = (ok("1", "Bash", command="ls") + ok("2", "Grep", pattern="x")
                 + ok("3", "Glob", pattern="*") + ok("4", "mcp__x__y") + ok("5", "WebFetch")
                 + ok("6", "Read", file_path="/w/a/x.py"))
        out = self.run_probe(lines, [])
        agent = out["agents"][0]
        self.assertEqual((agent["bash"], agent["grep_glob"], agent["mcp"], agent["other"],
                          agent["read"]), (1, 2, 1, 1, 1))
        # Grep and Glob leave numerator and denominator; Bash, MCP and other are unknown writers.
        self.assertEqual((agent["total_calls"], agent["denominator_calls"],
                          agent["unknown_writer_calls"], agent["read_only_search_calls"]),
                         (6, 4, 3, 2))
        self.assertEqual((out["run"]["denominator_calls"], out["run"]["unknown_writer_calls"],
                          out["run"]["read_only_search_calls"]), (4, 3, 2))

    def test_failed_search_calls_stay_out_of_the_denominator(self):
        a = [use("1", "Grep", pattern="x"), result("1", error=True), use("2", "Glob", pattern="y")]
        agent = self.run_probe(a, [])["agents"][0]
        self.assertEqual((agent["denominator_calls"], agent["unknown_writer_calls"],
                          agent["read_only_search_calls"]), (0, 0, 2))

    def test_run_totals_sum_over_agents(self):
        out = self.run_probe(ok("1", "Bash", command="x") + ok("2", "Read", file_path="/w/a/x.py"),
                             ok("3", "mcp__s__t") + ok("4", "Grep", pattern="p"))
        self.assertEqual((out["run"]["denominator_calls"], out["run"]["unknown_writer_calls"],
                          out["run"]["read_only_search_calls"]), (3, 2, 1))

    def test_observed_layout_shape_with_extra_records_and_absent_is_error(self):
        # Shape seen by the census: attachment and thinking records, tool_result without is_error,
        # string message content, repeated assistant records for one tool_use id.
        call = {"type": "assistant", "sessionId": "s", "message": {"content": [
            {"type": "thinking", "thinking": "t", "signature": "g"},
            {"type": "tool_use", "id": "t1", "name": "Edit", "caller": {"type": "direct"},
             "input": {"file_path": "/w/b/x.py", "old_string": "a", "new_string": "b"}}]}}
        lines = [json.dumps({"type": "attachment", "attachment": {"type": "x"}}),
                 json.dumps({"type": "user", "message": {"role": "user", "content": "plain prompt"}}),
                 json.dumps(call), json.dumps(call),
                 json.dumps({"type": "user", "message": {"content": [
                     {"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]}})]
        out = self.run_probe(ok("0", "Read", file_path="/w/a/x.py"), lines)
        self.assertEqual(out["agents"][1]["write"], 1)
        self.assertEqual(out["agents"][1]["failed_or_unpaired_calls"], 0)
        self.assertEqual(out["run"]["ordered_pairs_with_overlap"], 1)

    def test_outside_worktree_and_relative_paths_never_match(self):
        a = (ok("1", "Read", file_path="/w/b/x.py") + ok("2", "Read", file_path="x.py")
             + ok("3", "Read", file_path="/w/a/../b/x.py") + ok("4", "Read", file_path="/w/ax/x.py"))
        b = ok("5", "Write", file_path="/w/b/x.py")
        out = self.run_probe(a, b)
        self.assertEqual(out["run"]["ordered_pairs_with_overlap"], 0)
        self.assertEqual(out["agents"][0]["outside_worktree"], 4)

    def test_duplicate_ids_and_malformed_lines(self):
        line = use("1", "Read", file_path="/w/a/x.py")
        out = self.run_probe([line, line, "{not json", result("1")], [])
        self.assertEqual(out["agents"][0]["total_calls"], 1)
        self.assertEqual(out["agents"][0]["malformed_lines"], 1)

    def test_output_is_integers_only_without_paths_or_content(self):
        secret = "SENTINEL_/w/a/secret-name.py"
        a = ok("1", "Read", file_path="/w/a/secret-name.py") + ok("2", "Bash", command=secret)
        out = self.run_probe(a, ok("3", "Write", file_path="/w/b/secret-name.py"))
        self.assertTrue(all_ints(out))
        text = json.dumps(out)
        self.assertNotIn("secret", text)
        self.assertNotIn("SENTINEL", text)

    def test_cli_prints_counts_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            a, b = Path(tmp, "a.jsonl"), Path(tmp, "b.jsonl")
            a.write_text("\n".join(ok("1", "Read", file_path="/w/a/zz.py")), encoding="utf-8")
            b.write_text("\n".join(ok("2", "Edit", file_path="/w/b/zz.py")), encoding="utf-8")
            proc = subprocess.run(
                [sys.executable, str(KIT / "probe.py"), "--agent", ROOT_A, str(a),
                 "--agent", ROOT_B, str(b)], capture_output=True, text=True, check=True)
        out = json.loads(proc.stdout)
        self.assertEqual(out["run"]["ordered_pairs_with_overlap"], 1)
        self.assertNotIn("zz", proc.stdout)
        self.assertTrue(all_ints(out))

    def test_attribution_counts_are_added_only_when_changed_sets_are_given(self):
        out = self.run_probe(ok("1", "Edit", file_path="/w/a/x.py"), [])
        self.assertNotIn("changed_files", out["run"])
        out = probe.probe([(ROOT_A, ok("1", "Edit", file_path="/w/a/x.py")
                            + ok("2", "Write", file_path="/w/a/new.py")
                            + [use("3", "Edit", file_path="/w/a/failed.py"), result("3", error=True)]
                            + ok("4", "Bash", command="sed -i s/a/b/ bashonly.py")
                            + ok("5", "Edit", file_path="/elsewhere/outside.py")),
                           (ROOT_B, ok("6", "NotebookEdit", notebook_path="/w/b/n.ipynb"))],
                          [{"x.py", "new.py", "failed.py", "bashonly.py", "outside.py"}, {"n.ipynb"}])
        self.assertEqual((out["agents"][0]["changed_files"], out["agents"][0]["attributed_changed_files"]),
                         (5, 2))
        self.assertEqual((out["run"]["changed_files"], out["run"]["attributed_changed_files"]), (6, 3))
        self.assertEqual(out["run"]["bash_calls"], 1)
        self.assertTrue(all_ints(out))
        with self.assertRaises(ValueError):
            probe.probe([(ROOT_A, [])], [set(), set()])

    def test_attribution_requires_a_write_on_the_same_agents_path_not_a_read_or_a_peer(self):
        out = probe.probe([(ROOT_A, ok("1", "Read", file_path="/w/a/x.py")),
                           (ROOT_B, ok("2", "Edit", file_path="/w/b/x.py"))],
                          [{"x.py"}, set()])
        self.assertEqual((out["agents"][0]["changed_files"], out["agents"][0]["attributed_changed_files"]),
                         (1, 0))
        self.assertEqual(out["agents"][1]["attributed_changed_files"], 0)

    def test_probe_is_stdlib_only_and_offline(self):
        source = (KIT / "probe.py").read_text(encoding="utf-8")
        for banned in ("socket", "urllib", "http", "requests", "hashlib", "open(\"w"):
            self.assertNotIn(banned, source)
        # The only subprocess is a hardened, read-only local git.
        self.assertEqual(source.count("subprocess.run("), 1)
        for needed in ("GIT_CONFIG_NOSYSTEM", "core.hooksPath", "--no-ext-diff", "--no-textconv",
                       "--diff-filter=AM", "GIT_CONFIG_GLOBAL"):
            self.assertIn(needed, source)
        for banned in ("shell=True", '"commit"', '"checkout"', '"add"', '"push"', '"fetch"',
                       '"reset"', '"config"'):
            self.assertNotIn(banned, source)


def run_git(cwd, *args):
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin:/opt/homebrew/bin", "GIT_CONFIG_NOSYSTEM": "1",
           "GIT_CONFIG_GLOBAL": "/dev/null"}
    return subprocess.run(["git", "-C", str(cwd), "-c", "user.name=t", "-c", "user.email=t@t.test",
                           "-c", "commit.gpgsign=false", *args], env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


class AttributionGitFixtureTests(unittest.TestCase):
    """A temporary git repository with two agent worktrees and synthetic transcripts."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        tmp = Path(self._tmp.name)
        self.repo = tmp / "repo"
        self.repo.mkdir()
        run_git(self.repo, "init", "-q", "-b", "main")
        for name in ("secret-edit.py", "secret-bash.py", "secret-gone.py", "secret-old.py", "same.py"):
            (self.repo / name).write_text(f"{name}\n", encoding="utf-8")
        (self.repo / "dir with space").mkdir()
        (self.repo / "dir with space" / "secret-sp\u00e9.py").write_text("x\n", encoding="utf-8")
        run_git(self.repo, "add", "-A")
        run_git(self.repo, "commit", "-q", "-m", "base")
        self.base = run_git(self.repo, "rev-parse", "HEAD")
        self.w1, self.w2 = tmp / "w1", tmp / "w2"
        run_git(self.repo, "worktree", "add", "-q", "-b", "a1", str(self.w1), self.base)
        run_git(self.repo, "worktree", "add", "-q", "-b", "a2", str(self.w2), self.base)
        # Agent 1: edit (Edit), add (Write), add via Bash only, modify via Bash only,
        # delete (not a change), rename via Bash (an added path), a path inside a spaced dir.
        (self.w1 / "secret-edit.py").write_text("edited\n", encoding="utf-8")
        (self.w1 / "secret-new.py").write_text("new\n", encoding="utf-8")
        (self.w1 / "secret-gen.py").write_text("generated\n", encoding="utf-8")
        (self.w1 / "secret-bash.py").write_text("sed\n", encoding="utf-8")
        (self.w1 / "secret-gone.py").unlink()
        (self.w1 / "secret-old.py").rename(self.w1 / "secret-moved.py")
        (self.w1 / "dir with space" / "secret-sp\u00e9.py").write_text("y\n", encoding="utf-8")
        run_git(self.w1, "add", "-A")
        run_git(self.w1, "commit", "-q", "-m", "agent 1")
        # Agent 2: one Write on an added file.
        (self.w2 / "secret-two.py").write_text("two\n", encoding="utf-8")
        run_git(self.w2, "add", "-A")
        run_git(self.w2, "commit", "-q", "-m", "agent 2")
        r1, r2 = str(self.w1), str(self.w2)
        self.lines1 = (ok("1", "Edit", file_path=f"{r1}/secret-edit.py")
                       + ok("2", "Write", file_path=f"{r1}/secret-new.py")
                       + ok("3", "Bash", command="sed -i s/a/b/ secret-bash.py; mv secret-old.py secret-moved.py")
                       + ok("4", "Write", file_path=f"{r1}/dir with space/secret-sp\u00e9.py")
                       + [use("5", "Write", file_path=f"{r1}/secret-gen.py"), result("5", error=True)]
                       + ok("6", "Edit", file_path=f"{r1}/same.py")  # written but unchanged in git
                       + ok("7", "Read", file_path=f"{r1}/secret-bash.py"))
        self.lines2 = (ok("8", "Write", file_path=f"{r2}/secret-two.py")
                       + ok("9", "Edit", file_path=f"{r1}/secret-edit.py"))  # a peer's worktree path
        self.changed = [probe.changed_paths(str(self.repo), self.base, r1),
                        probe.changed_paths(str(self.repo), self.base, r2)]

    def test_changed_paths_are_added_or_modified_only_and_renames_are_additions(self):
        self.assertEqual(self.changed[0], {
            "secret-edit.py", "secret-new.py", "secret-gen.py", "secret-bash.py", "secret-moved.py",
            "dir with space/secret-sp\u00e9.py"})
        self.assertEqual(self.changed[1], {"secret-two.py"})

    def test_attribution_counts_from_a_real_git_diff_and_transcripts(self):
        out = probe.probe([(str(self.w1), self.lines1), (str(self.w2), self.lines2)], self.changed)
        a1, a2 = out["agents"]
        # Attributed: edit, new, spaced-dir path. Unattributed: Bash-only modify, Bash-only rename
        # target, and the file whose only Write failed.
        self.assertEqual((a1["changed_files"], a1["attributed_changed_files"]), (6, 3))
        self.assertEqual((a2["changed_files"], a2["attributed_changed_files"]), (1, 1))
        self.assertEqual((out["run"]["changed_files"], out["run"]["attributed_changed_files"]), (7, 4))
        self.assertEqual(out["run"]["bash_calls"], 1)
        self.assertTrue(all_ints(out))
        self.assertNotIn("secret", json.dumps(out))

    def test_cli_prints_integers_only_and_no_path_string_appears(self):
        a, b = Path(self._tmp.name, "a.jsonl"), Path(self._tmp.name, "b.jsonl")
        a.write_text("\n".join(self.lines1), encoding="utf-8")
        b.write_text("\n".join(self.lines2), encoding="utf-8")
        proc = subprocess.run(
            [sys.executable, str(KIT / "probe.py"), "--repo", str(self.repo), "--base", self.base,
             "--agent", str(self.w1), str(a), "--agent", str(self.w2), str(b)],
            capture_output=True, text=True, check=True)
        out = json.loads(proc.stdout)
        self.assertEqual((out["run"]["changed_files"], out["run"]["attributed_changed_files"]), (7, 4))
        self.assertTrue(all_ints(out))
        everything = proc.stdout + proc.stderr
        for fragment in ("secret", "py", "w1", "w2", "repo", "dir with space", "tmp", self.base[:12],
                         "a1", "a2", "/"):
            self.assertNotIn(fragment, everything.replace("denominator_calls", "").replace(
                "ordered_pairs_with_overlap", "").replace("distinct_paths_with_overlap", "").replace(
                "outside_worktree", "").replace("read_only_search_calls", "").replace(
                "unknown_writer_calls", "").replace("failed_or_unpaired_calls", ""), fragment)

    def test_git_ignores_repository_configuration_that_could_run_code(self):
        marker = Path(self._tmp.name, "marker-ran")
        script = Path(self._tmp.name, "hook.sh")
        script.write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
        script.chmod(0o755)
        hooks = self.repo / "evil-hooks"
        hooks.mkdir()
        for name in ("post-checkout", "reference-transaction", "pre-commit"):
            (hooks / name).write_text(f"#!/bin/sh\ntouch '{marker}'\n", encoding="utf-8")
            (hooks / name).chmod(0o755)
        run_git(self.repo, "config", "core.hooksPath", str(hooks))
        run_git(self.repo, "config", "diff.external", str(script))
        run_git(self.repo, "config", "core.fsmonitor", str(script))
        (self.repo / ".gitattributes").write_text("*.py diff=evil\n", encoding="utf-8")
        run_git(self.repo, "config", "diff.evil.textconv", str(script))
        again = probe.changed_paths(str(self.repo), self.base, str(self.w2))
        self.assertEqual(again, {"secret-two.py"})
        self.assertFalse(marker.exists())

    def test_git_failures_are_generic_and_leak_no_path(self):
        with tempfile.TemporaryDirectory() as empty:
            a = Path(empty, "a.jsonl")
            a.write_text("", encoding="utf-8")
            for base in ("0" * 40, "--output=pwned"):
                proc = subprocess.run(
                    [sys.executable, str(KIT / "probe.py"), "--repo", str(self.repo), "--base=" + base,
                     "--agent", str(self.w1), str(a)], capture_output=True, text=True)
                self.assertEqual(proc.returncode, 1)
                self.assertEqual(proc.stdout, "")
                self.assertEqual(proc.stderr.strip(), "probe: git could not compute the changed files")
        self.assertFalse(Path("pwned").exists())

    def test_repo_and_base_must_be_given_together(self):
        a = Path(self._tmp.name, "a.jsonl")
        a.write_text("", encoding="utf-8")
        proc = subprocess.run([sys.executable, str(KIT / "probe.py"), "--repo", str(self.repo),
                               "--agent", str(self.w1), str(a)], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)

    def test_attribution_counts_flow_into_the_scorer_c3(self):
        out = probe.probe([(str(self.w1), self.lines1), (str(self.w2), self.lines2)], self.changed)["run"]
        runs = passing_runs()
        for run in runs:
            run["probe"].update(changed_files=0, attributed_changed_files=0)
        runs[0]["probe"].update(changed_files=out["changed_files"],
                                attributed_changed_files=out["attributed_changed_files"])
        scored = scorer.score({"runs": runs})
        self.assertEqual((scored["counts"]["changedFiles"], scored["counts"]["attributedChangedFiles"]), (7, 4))
        self.assertFalse(scored["c3"]["met"])  # 5*4 < 3*7: 4 of 7 is below 0.60
        self.assertEqual(scored["unmet_or_reason"], ["C3"])


VECTORS = (Path(__file__).resolve().parents[1] / "docs" / "experiments"
           / "claude-workflow-g0-decision-vectors.json")
INPUTS = VECTORS.with_name("claude-workflow-g0-inputs.json")

ZERO_ARMS = dict(pairwise=False, chained=False, naive=False, primary=False)


def make_run(ordinal, reference="clean", *, design=None, pairwise=False, chained=False,
             naive=False, primary=False, inclusive=None, pairs=0, denominator=10, unknown=2,
             search=0, changed=10, attributed=8, status="eligible", attribution=None, clash=None):
    run = {"run_id": f"r{ordinal:02d}", "ordinal": ordinal, "status": status,
           "reference": reference,
           "design": {"overlap": design in ("overlap", "control"),
                      "contract": design == "contract",
                      "negative_control": design == "control"},
           "arms": {"merge-tree-pairwise": pairwise, "merge-tree-chained": chained,
                    "naive-path-overlap": naive, "braid-analyze-git-primary": primary,
                    "braid-analyze-git-inclusive": primary if inclusive is None else inclusive}}
    if attribution:
        run["attribution"] = attribution
    if clash is not None:
        run["arms"]["clash"] = clash
    if status == "eligible":
        run["probe"] = {"denominator_calls": denominator, "unknown_writer_calls": unknown,
                        "read_only_search_calls": search, "ordered_pairs_with_overlap": pairs,
                        "changed_files": changed, "attributed_changed_files": attributed}
    return run


def commit_level(ordinal, reference="clean", design="overlap", **kwargs):
    """An overlap run as the commit-level arms see it: naive and Braid primary flag it."""
    textual = reference == "textual-conflict"
    return make_run(ordinal, reference, design=design, naive=True, primary=True,
                    pairwise=textual, chained=textual, **kwargs)


ATTRIBUTED = {"contract_named_in_manifest": True, "counterfactual_removes_failure": True}


def passing_runs():
    """Mirrors vector v13: 3 probe-flagged runs, all failures; naive precision 2/7."""
    return [
        make_run(1, "semantic-failure", design="contract", pairs=1, attribution=ATTRIBUTED),
        make_run(2, design="contract"),
        make_run(3, design="contract"),
        commit_level(4, "textual-conflict", pairs=1),
        commit_level(5, "semantic-failure", pairs=1),
        commit_level(6), commit_level(7),
        commit_level(8, design="control"), commit_level(9, design="control"),
        commit_level(10, design="control"),
    ]


class DecisionVectorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vectors = json.loads(VECTORS.read_text(encoding="utf-8"))

    def test_scorer_reproduces_every_decision_vector(self):
        self.assertEqual(len(self.vectors["vectors"]), 23)
        for vector in self.vectors["vectors"]:
            with self.subTest(vector=vector["id"]):
                self.assertEqual(scorer.decide(vector["counts"]), vector["expected"])

    def test_scorer_count_fields_are_the_vectors_tuple_fields(self):
        self.assertEqual(list(scorer.COUNT_FIELDS), self.vectors["tupleFields"])
        for vector in self.vectors["vectors"]:
            self.assertEqual(sorted(vector["counts"]), sorted(scorer.COUNT_FIELDS))

    def test_vectors_exercise_every_step_and_the_scorer_stays_integer_only(self):
        steps = {v["expected"]["decidedAtStep"] for v in self.vectors["vectors"]}
        self.assertEqual(steps, {f"step-{n}" for n in range(1, 6)})
        source = (KIT / "scorer.py").read_text(encoding="utf-8")
        decide_source = source[source.index("def c3_met"):source.index("def _decision")]
        for banned in ("float(", "/ ", "round(", "Fraction"):
            self.assertNotIn(banned, decide_source)

    def test_vector_thresholds_match_the_inputs_file(self):
        inputs = json.loads(INPUTS.read_text(encoding="utf-8"))
        quotas = inputs["decisionRule"]["designQuotas"]
        self.assertEqual((scorer.MIN_OVERLAP, scorer.MIN_CONTRACT, scorer.MIN_NEGATIVE_CONTROL),
                         (quotas["minOverlapRuns"], quotas["minContractDependencyRuns"],
                          quotas["minNegativeControlRuns"]))
        self.assertEqual(scorer.MIN_FLAGGED, inputs["thresholds"]["C2"]["minFlaggedRunsToEvaluate"])
        self.assertEqual(scorer.MAX_NEGATIVE_CONTROLS_FLAGGED,
                         inputs["thresholds"]["C4"]["maxNegativeControlRunsFlagged"])
        self.assertEqual(scorer.ANALYSIS_RUNS, inputs["design"]["minEligibleRuns"])
        self.assertEqual(scorer.MAX_STARTED, inputs["design"]["maxStartedRuns"])
        self.assertEqual(sorted(scorer.EXCLUSIONS + ("probe-unavailable",)),
                         sorted(inputs["design"]["exclusionReasons"]))

    def test_decide_rejects_more_attributed_than_changed_files(self):
        counts = dict(self.vectors["vectors"][0]["counts"], attributedChangedFiles=101)
        with self.assertRaises(ValueError):
            scorer.decide(counts)

    def test_c3_vectors_match_the_integer_rule(self):
        for vector in self.vectors["vectors"]:
            counts = vector["counts"]
            expected = counts["changedFiles"] > 0 and 5 * counts["attributedChangedFiles"] >= 3 * counts["changedFiles"]
            with self.subTest(vector=vector["id"]):
                self.assertEqual(scorer.c3_met(counts), expected)

    def test_decide_rejects_malformed_counts(self):
        counts = dict(self.vectors["vectors"][0]["counts"])
        for bad in (-1, True, 1.5, "3"):
            with self.assertRaises(ValueError):
                scorer.decide({**counts, "overlapRuns": bad})
        counts.pop("overlapRuns")
        with self.assertRaises(ValueError):
            scorer.decide(counts)

    def test_run_level_scoring_derives_the_v13_tuple(self):
        out = scorer.score({"runs": passing_runs()})
        vector = next(v for v in self.vectors["vectors"] if v["id"].startswith("v13"))
        expected = dict(vector["counts"], naiveFlaggedRuns=7, naiveFlaggedReferenceFailures=2,
                        referenceFailureRuns=3, probeFlaggedReferenceFailures=3)
        self.assertEqual(out["counts"], expected)
        self.assertEqual(out["outcome"], "g0-pass")


class ScorerTests(unittest.TestCase):
    def outcome(self, runs):
        return scorer.score({"runs": runs})

    def step(self, runs):
        out = self.outcome(runs)
        return out["outcome"], out["decided_at_step"]

    def test_pass_requires_c1b_c2_c3_and_c4(self):
        out = self.outcome(passing_runs())
        self.assertEqual((out["outcome"], out["decided_at_step"]), ("g0-pass", 5))
        self.assertEqual(out["unmet_or_reason"], ["all-met"])
        self.assertTrue(out["c1b"]["met"] and out["c3"]["met"] and out["c4"]["met"])
        self.assertEqual((out["c2"]["precision"], out["c2"]["prevalence"],
                          out["c2"]["naive_precision"]), (1.0, 0.3, 0.2857))
        self.assertEqual(out["c4"]["flag_rate"], 0.0)

    def test_fewer_than_ten_eligible_is_inconclusive_before_anything_else(self):
        runs = passing_runs()[:9]
        runs[0] = make_run(1, "semantic-failure", design="contract", pairs=0, attributed=0)
        out = self.outcome(runs)  # C1b and C3 are unmet, but step 1 stops first
        self.assertEqual((out["outcome"], out["decided_at_step"]), ("g0-inconclusive", 1))
        self.assertEqual(out["unmet_or_reason"], ["eligible-runs", "design-quota"])

    def test_missed_design_quota_is_inconclusive_at_step_one(self):
        runs = passing_runs()
        runs[2] = commit_level(3)  # contract run replaced by plain overlap: 2 contract runs
        out = self.outcome(runs)
        self.assertEqual((out["outcome"], out["decided_at_step"]), ("g0-inconclusive", 1))
        self.assertEqual(out["unmet_or_reason"], ["design-quota"])
        self.assertEqual(out["design_quotas"]["contract_dependency_met"], False)
        runs = passing_runs()
        runs[9] = commit_level(10)  # one negative control fewer
        self.assertEqual(self.outcome(runs)["design_quotas"]["negative_control_met"], False)
        self.assertEqual(self.step(runs), ("g0-inconclusive", 1))

    def test_probe_unavailable_runs_do_not_count_toward_ten(self):
        runs = passing_runs()[:9] + [make_run(10, status="probe-unavailable")]
        out = self.outcome(runs)
        self.assertEqual(out["outcome"], "g0-inconclusive")
        self.assertEqual(out["counts"]["eligibleRunsWithProbeData"], 9)
        self.assertEqual(out["intention_to_treat"]["probe_unavailable_runs"], 1)

    def test_c1b_needs_the_attribution_conditions(self):
        for attribution in (None, {"contract_named_in_manifest": True},
                            {"counterfactual_removes_failure": True}):
            runs = passing_runs()
            runs[0] = make_run(1, "semantic-failure", design="contract", pairs=1,
                               attribution=attribution)
            out = self.outcome(runs)
            self.assertEqual((out["c1b"]["count"], out["outcome"], out["decided_at_step"]),
                             (0, "g0-fail", 2))
            self.assertEqual(out["unmet_or_reason"], ["C1b"])

    def test_c1b_fails_when_any_non_transcript_arm_also_flagged_it(self):
        for kwargs in ({"pairwise": True}, {"chained": True}, {"naive": True},
                       {"primary": True}, {"inclusive": True}):
            runs = passing_runs()
            runs[0] = make_run(1, "semantic-failure", design="contract", pairs=1,
                               attribution=ATTRIBUTED, **kwargs)
            self.assertEqual(self.outcome(runs)["c1b"]["count"], 0, kwargs)

    def test_c1b_needs_a_semantic_failure_the_probe_flagged(self):
        for reference, pairs in (("indeterminate", 1), ("textual-conflict", 1),
                                 ("clean", 1), ("semantic-failure", 0)):
            runs = passing_runs()
            runs[0] = make_run(1, reference, design="contract", pairs=pairs, attribution=ATTRIBUTED)
            self.assertEqual(self.outcome(runs)["c1b"]["count"], 0, (reference, pairs))

    def test_c1b_unmet_fails_even_with_no_probe_flag_at_all(self):
        runs = [commit_level(i, design="control") if i > 7 else
                (make_run(i, design="contract") if i < 4 else commit_level(i)) for i in range(1, 11)]
        self.assertEqual(self.step(runs), ("g0-fail", 2))

    def test_c3_boundary_is_inclusive_at_sixty_percent(self):
        def c3(attributed_last, changed_last=10):
            runs = passing_runs()
            for run in runs:
                run["probe"].update(changed_files=10, attributed_changed_files=6)
            runs[9]["probe"].update(changed_files=changed_last,
                                    attributed_changed_files=attributed_last)
            return self.outcome(runs)
        met = c3(6)  # 60 of 100
        self.assertTrue(met["c3"]["met"])
        self.assertEqual((met["c3"]["attributed_changed_files"], met["c3"]["changed_files"],
                          met["c3"]["coverage"]), (60, 100, 0.6))
        self.assertEqual(met["outcome"], "g0-pass")
        unmet = c3(5)  # 59 of 100
        self.assertFalse(unmet["c3"]["met"])
        self.assertEqual((unmet["outcome"], unmet["unmet_or_reason"]), ("g0-fail", ["C3"]))

    def test_c3_small_boundaries_use_integer_cross_multiplication(self):
        def met(attributed, changed):
            return scorer.c3_met({"attributedChangedFiles": attributed, "changedFiles": changed})
        self.assertTrue(met(3, 5))
        self.assertFalse(met(2, 4))
        self.assertFalse(met(0, 0))
        self.assertTrue(met(1, 1))

    def test_c3_unmet_fails_at_step_two_even_with_few_flagged_runs(self):
        runs = passing_runs()
        for run in runs:
            run["probe"]["attributed_changed_files"] = 5  # 50 of 100
        out = self.outcome(runs)
        self.assertEqual((out["outcome"], out["decided_at_step"], out["unmet_or_reason"]),
                         ("g0-fail", 2, ["C3"]))

    def test_c3_without_any_changed_file_is_unmet(self):
        runs = [dict(r, probe=dict(r["probe"], changed_files=0, attributed_changed_files=0))
                for r in passing_runs()]
        out = self.outcome(runs)
        self.assertFalse(out["c3"]["met"])
        self.assertIsNone(out["c3"]["coverage"])
        self.assertEqual(self.step(runs), ("g0-fail", 2))

    def test_call_mix_is_descriptive_and_never_gates_c3(self):
        runs = passing_runs()
        for run in runs:  # the founder's census mix: almost every call is unknown
            run["probe"].update(denominator_calls=100, unknown_writer_calls=90,
                                read_only_search_calls=50, bash_calls=80)
        out = self.outcome(runs)
        self.assertEqual(out["outcome"], "g0-pass")
        mix = out["descriptive_call_mix"]
        self.assertTrue(mix["gates_nothing"])
        self.assertEqual((mix["denominator_calls"], mix["unknown_writer_calls"],
                          mix["read_only_search_calls"], mix["unknown_call_rate"],
                          mix["bash_share_of_all_calls"]), (1000, 900, 500, 0.9, 0.5333))
        for run in runs:
            del run["probe"]["bash_calls"]
        self.assertIsNone(self.outcome(runs)["descriptive_call_mix"]["bash_share_of_all_calls"])

    def test_c4_two_flagged_negative_controls_fail_at_step_two(self):
        runs = passing_runs()
        runs[7]["probe"]["ordered_pairs_with_overlap"] = 1
        runs[8]["probe"]["ordered_pairs_with_overlap"] = 1
        out = self.outcome(runs)
        self.assertEqual((out["outcome"], out["decided_at_step"], out["unmet_or_reason"]),
                         ("g0-fail", 2, ["C4"]))
        self.assertEqual((out["c4"]["flagged"], out["c4"]["met"]), (2, False))

    def test_c4_allows_one_flagged_negative_control(self):
        runs = passing_runs()
        runs[7]["probe"]["ordered_pairs_with_overlap"] = 1
        out = self.outcome(runs)
        self.assertEqual((out["outcome"], out["c4"]["flagged"], out["c4"]["met"]),
                         ("g0-pass", 1, True))
        self.assertEqual(out["arms"]["transcript-probe"]["fp"], 1)

    def test_fewer_than_three_flagged_with_c1b_c3_c4_met_is_inconclusive(self):
        runs = passing_runs()
        runs[3]["probe"]["ordered_pairs_with_overlap"] = 0
        runs[4]["probe"]["ordered_pairs_with_overlap"] = 0
        out = self.outcome(runs)
        self.assertEqual((out["outcome"], out["decided_at_step"], out["unmet_or_reason"]),
                         ("g0-inconclusive", 3, ["flagged-runs"]))
        self.assertFalse(out["c2"]["evaluable"])

    def test_c2_is_evaluated_at_step_four_against_prevalence_and_naive_precision(self):
        def flag(*indexes):
            runs = passing_runs()
            for i in indexes:
                runs[i]["probe"]["ordered_pairs_with_overlap"] = 1
            return self.outcome(runs)
        # 3 hits of 7 flagged = 0.43: above the floor, the prevalence 0.3 and naive 2/7.
        self.assertEqual(flag(1, 2, 5, 6)["outcome"], "g0-pass")
        # Naive path overlap flags only the three failures: its precision 1.0 is not beaten.
        runs = passing_runs()
        for i in (1, 2, 5, 6, 7, 8, 9):
            runs[i]["arms"]["naive-path-overlap"] = False
        runs[0]["arms"]["naive-path-overlap"] = False
        out = self.outcome(runs)
        self.assertEqual((out["c2"]["naive_precision"], out["outcome"], out["decided_at_step"],
                          out["unmet_or_reason"]), (1.0, "g0-fail", 4, ["C2-naive"]))
        # All ten runs fail and the probe flags three: precision 1.0 equals the prevalence 1.0.
        runs = [make_run(i, "semantic-failure", design=d, pairs=1 if i in (1, 4, 5) else 0,
                         attribution=ATTRIBUTED)
                for i, d in enumerate(["contract"] * 3 + ["overlap"] * 4 + ["control"] * 3, 1)]
        out = self.outcome(runs)
        self.assertEqual((out["c2"]["precision"], out["c2"]["prevalence"]), (1.0, 1.0))
        self.assertEqual((out["outcome"], out["decided_at_step"], out["unmet_or_reason"]),
                         ("g0-fail", 4, ["C2-prevalence"]))

    def test_naive_arm_flagging_nothing_makes_comparison_not_applicable(self):
        runs = passing_runs()
        for run in runs:
            run["arms"]["naive-path-overlap"] = False
        out = self.outcome(runs)
        self.assertEqual(out["c2"]["naive_comparison"], "not-applicable")
        self.assertEqual(out["outcome"], "g0-pass")

    def test_indeterminate_is_a_false_positive_a_prevalence_failure_and_no_hit(self):
        runs = passing_runs()
        runs[5] = commit_level(6, "indeterminate", pairs=1)  # flagged indeterminate
        runs[6] = commit_level(7, "indeterminate")  # unflagged indeterminate
        out = self.outcome(runs)
        self.assertEqual(out["counts"]["referenceFailureRuns"], 5)
        self.assertEqual(out["counts"]["probeFlaggedRuns"], 4)
        self.assertEqual(out["counts"]["probeFlaggedReferenceFailures"], 3)
        probe_arm = out["arms"]["transcript-probe"]
        self.assertEqual((probe_arm["tp"], probe_arm["fp"], probe_arm["indeterminate_flagged"],
                          probe_arm["indeterminate_unflagged"]), (3, 1, 1, 1))
        self.assertEqual(out["intention_to_treat"]["indeterminate_runs"], 2)

    def test_first_ten_rule_later_eligible_runs_are_descriptive_only(self):
        runs = passing_runs() + [
            make_run(11, "semantic-failure", design="contract", pairs=1, changed=50, attribution=ATTRIBUTED),
            commit_level(12, "semantic-failure", pairs=1)]
        random_order = list(reversed(runs))
        out = self.outcome(random_order)
        self.assertEqual((out["outcome"], out["counts"]["analysisSetRuns"],
                          out["counts"]["eligibleRunsWithProbeData"]), ("g0-pass", 10, 12))
        self.assertEqual((out["counts"]["changedFiles"], out["counts"]["attributedChangedFiles"]),
                         (100, 80))
        itt = out["intention_to_treat"]
        self.assertEqual((itt["started_runs"], itt["later_eligible_runs_descriptive_only"]), (12, 2))
        self.assertEqual(itt["arms"]["transcript-probe"]["runs"], 12)
        self.assertEqual(out["arms"]["transcript-probe"]["runs"], 10)

    def test_intention_to_treat_keeps_exclusions_visible(self):
        runs = passing_runs() + [make_run(11, status="flaky-branch-tests"),
                                 make_run(12, status="quota-exhausted")]
        out = self.outcome(runs)
        itt = out["intention_to_treat"]
        self.assertEqual(itt["runs_by_status"], {"eligible": 10, "flaky-branch-tests": 1,
                                                 "quota-exhausted": 1})
        self.assertEqual(out["outcome"], "g0-pass")

    def test_c1a_is_against_naive_overlap_gates_nothing_and_counts_unavailable_runs(self):
        runs = passing_runs()
        runs[9] = make_run(10, "semantic-failure", design="control", primary=True,
                           status="probe-unavailable")  # braid flag, naive miss: a discrepancy
        out = self.outcome(runs)
        self.assertEqual((out["c1a"]["count"], out["c1a"]["met"]), (1, True))
        self.assertEqual(out["outcome"], "g0-inconclusive")  # only 9 eligible; C1a decides nothing
        self.assertEqual(self.outcome(passing_runs())["c1a"]["count"], 0)
        self.assertEqual(self.outcome(passing_runs())["outcome"], "g0-pass")

    def test_c1a_does_not_count_a_failure_naive_overlap_also_flagged(self):
        runs = [make_run(1, "semantic-failure", primary=True, naive=True),
                make_run(2, "textual-conflict", primary=True, naive=True),
                make_run(3, "semantic-failure", pairwise=True, primary=True),
                make_run(4, "semantic-failure", chained=True, primary=True)]
        self.assertEqual(scorer.score({"runs": runs})["c1a"]["count"], 0)
        self.assertEqual(scorer.score({"runs": [make_run(1, "semantic-failure", primary=True)]})
                         ["c1a"]["count"], 1)

    def test_confusion_counts_split_textual_and_semantic(self):
        arm = self.outcome(passing_runs())["arms"]["merge-tree-pairwise"]
        self.assertEqual((arm["tp"], arm["fn"], arm["tp_textual"], arm["fn_semantic"]), (1, 2, 1, 2))

    def test_clash_arm_reported_only_when_present_in_every_scored_run(self):
        runs = passing_runs()
        self.assertNotIn("clash", self.outcome(runs)["arms"])
        for run in runs:
            run["arms"]["clash"] = False
        self.assertEqual(self.outcome(runs)["arms"]["clash"]["fn"], 3)

    def test_invalid_input_is_rejected(self):
        def rejects(mutate):
            bad = passing_runs()
            mutate(bad)
            with self.assertRaises(ValueError):
                self.outcome(bad)
        rejects(lambda r: r[0].update(status="made-up"))
        rejects(lambda r: r[0].update(status="flaky-final-tests"))
        rejects(lambda r: r[0].update(reference="semantic"))
        rejects(lambda r: r[0]["arms"].update({"braid-analyze-git-primary": True}))
        rejects(lambda r: r[0]["arms"].update({"clash": "no"}))
        rejects(lambda r: r[0]["probe"].update(unknown_writer_calls=99))
        rejects(lambda r: r[0]["probe"].update(attributed_changed_files=11))
        rejects(lambda r: r[0]["probe"].pop("changed_files"))
        rejects(lambda r: r[0]["probe"].pop("attributed_changed_files"))
        rejects(lambda r: r[0]["probe"].update(bash_calls=-1))
        rejects(lambda r: r[0]["probe"].pop("read_only_search_calls"))
        rejects(lambda r: r[0]["design"].update(overlap=True))  # contract and overlap
        rejects(lambda r: r[7]["design"].update(overlap=False))  # control without overlap
        rejects(lambda r: r[0]["design"].update(contract="yes"))
        rejects(lambda r: r[0].update(attribution={"contract_named_in_manifest": "yes"}))
        rejects(lambda r: r[0].update(attribution=[]))
        rejects(lambda r: r[1].update(run_id=r[0]["run_id"]))
        rejects(lambda r: r[0].update(ordinal=True))
        with self.assertRaises(ValueError):
            self.outcome(passing_runs() + [make_run(i) for i in range(11, 16)])
        for runs in (None, {"r01": {}}, "runs"):
            with self.assertRaises(ValueError):
                self.outcome(runs)

    def test_missing_or_mistyped_sections_raise_value_error(self):
        for mutate in (lambda r: r.pop("probe"), lambda r: r.pop("arms"),
                       lambda r: r.update(probe=[]), lambda r: r.update(arms="x")):
            bad = passing_runs()
            mutate(bad[0])
            with self.assertRaises(ValueError):
                self.outcome(bad)

    def test_cli_prints_aggregate_json_and_reports_value_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "runs.json")
            path.write_text(json.dumps({"runs": passing_runs()}), encoding="utf-8")
            good = subprocess.run([sys.executable, str(KIT / "scorer.py"), str(path)],
                                  capture_output=True, text=True)
            path.write_text(json.dumps({"runs": [{"run_id": "r01", "ordinal": 1,
                                                 "status": "eligible"}]}), encoding="utf-8")
            bad = subprocess.run([sys.executable, str(KIT / "scorer.py"), str(path)],
                                 capture_output=True, text=True)
        self.assertEqual(good.returncode, 0)
        self.assertEqual(json.loads(good.stdout)["outcome"], "g0-pass")
        self.assertEqual(bad.returncode, 1)
        self.assertIn("run r01", bad.stderr)
        self.assertNotIn("Traceback", bad.stderr)


def census_transcript(*lines):
    return "\n".join(json.dumps(line) for line in lines)


def tool_line(call_id, name, **params):
    return {"type": "assistant", "message": {"content": [
        {"type": "tool_use", "id": call_id, "name": name, "input": params}]}}


def result_line(call_id, error=None):
    block = {"type": "tool_result", "tool_use_id": call_id, "content": "SENTINEL_OUTPUT"}
    if error is not None:
        block["is_error"] = error
    return {"type": "user", "message": {"content": [block]}}


class CensusTests(unittest.TestCase):
    def build(self, root):
        sessions = {"SECRET_SESSION_DIR_ONE": 2, "SECRET_SESSION_DIR_TWO": 1}
        for session, agents in sessions.items():
            directory = Path(root, "SECRET_PROJECT_DIR", session, "subagents")
            directory.mkdir(parents=True)
            for n in range(agents):
                lines = [
                    {"type": "attachment", "attachment": {"type": "x"}},
                    {"type": "user", "message": {"content": "SENTINEL_PROMPT /secret/path.py"}},
                    tool_line("a", "Read", file_path="/secret/path.py"), result_line("a"),
                    tool_line("b", "Edit", file_path="/secret/path.py", old_string="SENTINEL_OLD"),
                    result_line("b", error=True),
                    tool_line("c", "Bash", command="SENTINEL_COMMAND"), result_line("c", error=False),
                    tool_line("d", "mcp__SECRET_SERVER__tool"), result_line("d"),
                    tool_line("e", "Grep", pattern="SENTINEL_PATTERN"), result_line("e"),
                    tool_line("f", "Mystery Tool/with spaces"),  # unpaired, odd name
                ]
                Path(directory, f"agent-{n}.jsonl").write_text(census_transcript(*lines) + "\n{broken",
                                                               encoding="utf-8")
        return root

    def test_census_counts_structure_and_never_prints_content_or_names(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = census.census([self.build(tmp)])
        text = json.dumps(out)
        for leaked in ("SECRET", "SENTINEL", "/secret", "path.py", "Mystery", "spaces"):
            self.assertNotIn(leaked, text)
        self.assertEqual((out["files"], out["sessions_with_subagents"], out["malformed_lines"]),
                         (3, 2, 3))
        self.assertEqual(out["subagents_per_session_histogram"], {"1": 1, "2": 1})
        self.assertEqual(out["tool_names"], {"Read": 3, "Edit": 3, "Bash": 3, "mcp__*": 3,
                                             "Grep": 3, "unprintable": 3})
        self.assertEqual(out["input_keys_by_tool"]["Edit"], {"file_path": 3, "old_string": 3})
        self.assertEqual(out["class_calls"], {"read": 3, "write": 3, "bash": 3, "mcp": 3,
                                              "grep_glob": 3, "other": 3})
        self.assertEqual(out["unpaired_calls"], {"other": 3})
        self.assertEqual(out["errored_calls"], {"write": 3})
        self.assertEqual(out["result_is_error"], {"'absent'": 9, "True": 3, "False": 3})
        self.assertEqual(out["block_types"]["tool_use"], 18)

    def test_shares_follow_the_c3_shape_without_grep_and_glob(self):
        shares = census.shares({"read": 10, "write": 5, "bash": 20, "mcp": 5, "other": 10,
                                "grep_glob": 50})
        self.assertEqual(shares["counted_calls"], 50)
        self.assertEqual(shares["read_only_search_calls"], 50)
        self.assertEqual(shares["unknown_class_share_percent"], 70.0)
        self.assertEqual(census.shares({})["unknown_class_share_percent"], None)

    def test_census_classes_match_the_probe_classes(self):
        for name in ("Read", "Edit", "Write", "NotebookEdit", "Bash", "Grep", "Glob",
                     "mcp__a__b", "MultiEdit", "WebFetch", None):
            self.assertEqual(census.tool_class(name), probe.classify(name), name)

    def test_cli_prints_only_aggregate_json_and_rejects_missing_roots(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.build(tmp)
            proc = subprocess.run([sys.executable, str(KIT / "census.py"), tmp],
                                  capture_output=True, text=True, check=True)
            missing = subprocess.run([sys.executable, str(KIT / "census.py"), str(Path(tmp, "nope"))],
                                     capture_output=True, text=True)
        self.assertNotIn("SECRET", proc.stdout + proc.stderr)
        self.assertNotIn("SENTINEL", proc.stdout)
        self.assertEqual(json.loads(proc.stdout)["files"], 3)
        self.assertEqual(missing.returncode, 2)
        self.assertNotIn("nope", missing.stderr)

    def test_census_is_stdlib_only_offline_and_read_only(self):
        source = (KIT / "census.py").read_text(encoding="utf-8")
        for banned in ("socket", "urllib", "http", "requests", "subprocess", "hashlib",
                       "open(path, \"w", "shutil", "os.remove", "write("):
            self.assertNotIn(banned, source.replace("sys.stdout.write", "").replace("sys.stderr.write", ""))


class KitFilesTests(unittest.TestCase):
    def test_workflow_template_is_plain_js_with_literal_meta_and_no_merge(self):
        source = (KIT / "workflow_template.js").read_text(encoding="utf-8")
        self.assertTrue(source.lstrip().startswith("//") or source.lstrip().startswith("export const meta"))
        self.assertIn("export const meta = {", source)
        self.assertIn("isolation: 'worktree'", source)
        for banned in ("git merge", "git push", "Date.now", "Math.random"):
            self.assertNotIn(banned, source)
        self.assertIn("tasks.length < 3 || tasks.length > 4", source)
        self.assertIn("typeof args.testCommand !== 'string' || !args.testCommand", source)

    def test_workflow_template_validates_the_design_class_and_never_shows_it_to_agents(self):
        source = (KIT / "workflow_template.js").read_text(encoding="utf-8")
        self.assertIn("['overlap', 'contract', 'negative-control'].includes(args.designClass)", source)
        code = "\n".join(line for line in source.splitlines() if not line.lstrip().startswith("//"))
        prompt = code[code.index("agent(\n"):code.index("{ label:")]
        self.assertNotIn("designClass", prompt)
        self.assertNotIn("negative", prompt)
        self.assertIn("designClass: args.designClass", code)

    def test_manifest_template_is_valid_json_with_unset_bindings_and_all_design_classes(self):
        manifest = json.loads((KIT / "run-manifest.template.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["frozen"])
        self.assertIsNone(manifest["repository"])
        classes = {run["designClass"]: run for run in manifest["runs"]}
        self.assertEqual(set(classes), {"overlap", "contract", "negative-control"})
        self.assertTrue(classes["negative-control"]["design"]["negative_control"])
        self.assertTrue(classes["negative-control"]["design"]["overlap"])
        self.assertFalse(classes["contract"]["design"]["overlap"])
        self.assertEqual(set(classes["contract"]["contractDependency"]),
                         {"symbolOrContract", "readerOrdinal", "writerOrdinal"})
        for run in manifest["runs"]:
            self.assertIn("hostRestartsPerAgent", run)
            self.assertIn("branchTestsDoubleRun", run)
        for key in ("plannedRunCount", "eligibleYieldEstimate", "transcriptLayoutCensus",
                    "powerOperatingPointAcceptedByFounder"):
            self.assertIsNone(manifest["preFreeze"][key])
        self.assertEqual(set(manifest["scriptSha256"]), {"census", "probe", "runner", "scorer"})

    def test_manifest_freeze_order_is_the_inputs_file_freeze_order(self):
        manifest = json.loads((KIT / "run-manifest.template.json").read_text(encoding="utf-8"))
        inputs = json.loads(INPUTS.read_text(encoding="utf-8"))
        self.assertEqual(manifest["freezeOrder"], inputs["freezeOrder"])

    def test_runbook_states_the_freeze_order_and_the_kit_files(self):
        runbook = (KIT / "RUNBOOK.md").read_text(encoding="utf-8")
        positions = [runbook.index(marker) for marker in
                     ("**Renew the signature**", "**Census.**", "**Probe written and tested.**",
                      "**Estimate the eligible yield**", "**Hash**", "**Accept the power operating point.**",
                      "**Freeze**")]
        self.assertEqual(positions, sorted(positions))
        for name in ("census.py", "probe.py", "scorer.py", "workflow_template.js",
                     "run-manifest.template.json", "negative control", "flaky-branch-tests",
                     "indeterminate"):
            self.assertIn(name, runbook)
        self.assertNotIn("flaky-final-tests", runbook)


if __name__ == "__main__":
    unittest.main()
