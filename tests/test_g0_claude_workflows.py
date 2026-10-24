# SPDX-License-Identifier: AGPL-3.0-only
"""Tests for the G0 experiment kit (probe and scorer) on synthetic data only."""

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

    def test_read_by_one_written_by_other_is_one_ordered_pair(self):
        out = self.run_probe(ok("1", "Read", file_path="/w/a/src/x.py"),
                             ok("2", "Edit", file_path="/w/b/src/x.py"))
        self.assertEqual(out["run"], {"ordered_pairs_with_overlap": 1,
                                      "distinct_paths_with_overlap": 1})
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
        self.assertEqual(out["run"], {"ordered_pairs_with_overlap": 2,
                                      "distinct_paths_with_overlap": 2})

    def test_failed_and_unpaired_calls_are_unknown_never_effects(self):
        a = [use("1", "Read", file_path="/w/a/x.py"), result("1", error=True),
             use("2", "Read", file_path="/w/a/x.py")]
        out = self.run_probe(a, ok("3", "Edit", file_path="/w/b/x.py"))
        self.assertEqual(out["run"]["ordered_pairs_with_overlap"], 0)
        agent = out["agents"][0]
        self.assertEqual((agent["total_calls"], agent["unknown_calls"],
                          agent["failed_or_unpaired_calls"]), (2, 2, 2))

    def test_unknown_classes_and_totals(self):
        lines = (ok("1", "Bash", command="ls") + ok("2", "Grep", pattern="x")
                 + ok("3", "Glob", pattern="*") + ok("4", "mcp__x__y") + ok("5", "WebFetch")
                 + ok("6", "Read", file_path="/w/a/x.py"))
        agent = self.run_probe(lines, [])["agents"][0]
        self.assertEqual((agent["bash"], agent["grep_glob"], agent["mcp"], agent["other"],
                          agent["read"]), (1, 2, 1, 1, 1))
        self.assertEqual((agent["total_calls"], agent["unknown_calls"]), (6, 5))

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

    def test_probe_is_stdlib_only_and_offline(self):
        source = (KIT / "probe.py").read_text(encoding="utf-8")
        for banned in ("socket", "urllib", "http", "requests", "subprocess", "hashlib", "open(\"w"):
            self.assertNotIn(banned, source)


def make_run(ordinal, reference="clean", *, pairwise=False, chained=False, naive=False,
             primary=False, inclusive=None, pairs=0, total=10, unknown=2, status="eligible"):
    run = {"run_id": f"r{ordinal:02d}", "ordinal": ordinal, "status": status,
           "reference": reference,
           "design": {"overlap": True, "contract": ordinal <= 3},
           "arms": {"merge-tree-pairwise": pairwise, "merge-tree-chained": chained,
                    "naive-path-overlap": naive, "braid-analyze-git-primary": primary,
                    "braid-analyze-git-inclusive": primary if inclusive is None else inclusive}}
    if status == "eligible":
        run["probe"] = {"total_calls": total, "unknown_calls": unknown,
                        "ordered_pairs_with_overlap": pairs}
    return run


def passing_runs():
    runs = [make_run(1, "semantic-failure", pairs=1),
            make_run(2, "textual-conflict", pairs=1, naive=True, pairwise=True, chained=True),
            make_run(3, "semantic-failure", pairs=2)]
    runs += [make_run(i) for i in range(4, 11)]
    runs[4] = make_run(5, naive=True)  # naive false positive: naive precision 1/2
    return runs


class ScorerTests(unittest.TestCase):
    def outcome(self, runs):
        return scorer.score({"runs": runs})

    def test_pass_requires_c1b_c2_c3(self):
        out = self.outcome(passing_runs())
        self.assertEqual((out["outcome"], out["decided_at_step"]), ("g0-pass", 5))
        self.assertTrue(out["c1b"]["met"] and out["c3"]["met"])
        self.assertEqual(out["c2"]["precision"], 1.0)
        self.assertEqual(out["reference_failure_prevalence"], 0.3)
        self.assertEqual(out["c2"]["naive_precision"], 0.5)

    def test_fewer_than_ten_eligible_is_inconclusive_before_anything_else(self):
        runs = passing_runs()[:9]
        runs[0] = make_run(1, "semantic-failure", pairs=0, unknown=10)  # C1b and C3 unmet
        out = self.outcome(runs)
        self.assertEqual((out["outcome"], out["decided_at_step"]), ("g0-inconclusive", 1))

    def test_probe_unavailable_runs_do_not_count_toward_ten(self):
        runs = passing_runs()[:9] + [make_run(10, status="probe-unavailable")]
        out = self.outcome(runs)
        self.assertEqual(out["outcome"], "g0-inconclusive")
        self.assertEqual(out["eligible_with_probe_data"], 9)
        self.assertEqual(out["runs_by_status"]["probe-unavailable"], 1)

    def test_c1b_unmet_fails_even_with_fewer_than_three_flagged(self):
        runs = [make_run(i) for i in range(1, 11)]
        runs[0] = make_run(1, "semantic-failure", pairs=1, primary=True)  # braid also caught it
        out = self.outcome(runs)
        self.assertFalse(out["c1b"]["met"])
        self.assertEqual((out["outcome"], out["decided_at_step"]), ("g0-fail", 2))

    def test_c1b_requires_inclusive_flag_too(self):
        runs = [make_run(i) for i in range(1, 11)]
        runs[0] = make_run(1, "semantic-failure", pairs=1, inclusive=True)
        out = self.outcome(runs)
        self.assertEqual(out["c1b"]["count"], 0)
        self.assertEqual(out["outcome"], "g0-fail")

    def test_c3_unmet_fails(self):
        runs = [make_run(r["ordinal"], r["reference"], pairs=r["probe"]["ordered_pairs_with_overlap"],
                         naive=r["arms"]["naive-path-overlap"], unknown=5) for r in passing_runs()]
        out = self.outcome(runs)
        self.assertFalse(out["c3"]["met"])
        self.assertEqual((out["outcome"], out["decided_at_step"]), ("g0-fail", 2))

    def test_c3_boundary_is_inclusive_at_forty_percent(self):
        runs = [make_run(i, total=10, unknown=4) for i in range(1, 11)]
        self.assertTrue(self.outcome(runs)["c3"]["met"])
        self.assertFalse(self.outcome([make_run(i, total=10, unknown=5) for i in range(1, 11)])["c3"]["met"])

    def test_c3_without_any_probe_calls_is_unmet(self):
        out = self.outcome([make_run(i, total=0, unknown=0) for i in range(1, 11)])
        self.assertFalse(out["c3"]["met"])
        self.assertIsNone(out["c3"]["rate"])

    def test_fewer_than_three_flagged_with_c1b_and_c3_met_is_inconclusive(self):
        runs = [make_run(i) for i in range(1, 11)]
        runs[0] = make_run(1, "semantic-failure", pairs=1)
        runs[1] = make_run(2, pairs=1)
        out = self.outcome(runs)
        self.assertEqual((out["outcome"], out["decided_at_step"]), ("g0-inconclusive", 3))
        self.assertFalse(out["c2"]["evaluable"])

    def test_c2_below_precision_floor_fails(self):
        runs = [make_run(i) for i in range(1, 11)]
        runs[0] = make_run(1, "semantic-failure", pairs=1)
        for i in (1, 2, 3):
            runs[i] = make_run(i + 1, pairs=1)  # 1 of 4 flagged runs fails: 0.25
        out = self.outcome(runs)
        self.assertEqual((out["outcome"], out["decided_at_step"]), ("g0-fail", 4))

    def test_c2_must_strictly_exceed_prevalence(self):
        # Every run fails and the probe flags exactly three: precision 1.0 == prevalence 1.0.
        runs = [make_run(i, "semantic-failure", pairs=1 if i <= 3 else 0) for i in range(1, 11)]
        out = self.outcome(runs)
        self.assertEqual(out["c2"]["prevalence"], 1.0)
        self.assertEqual((out["outcome"], out["decided_at_step"]), ("g0-fail", 4))

    def test_c2_must_strictly_exceed_naive_precision_when_defined(self):
        runs = passing_runs()
        runs[4] = make_run(5)  # no naive false positive
        runs[0] = make_run(1, "semantic-failure", pairs=1, naive=True)
        runs[2] = make_run(3, "semantic-failure", pairs=2, naive=True)  # naive precision 1.0
        runs[1] = make_run(2, "textual-conflict", pairs=1, naive=True, pairwise=True, chained=True)
        runs[0] = make_run(1, "semantic-failure", pairs=1)  # keep C1b via run 1
        out = self.outcome(runs)
        self.assertEqual(out["c2"]["naive_precision"], 1.0)
        self.assertEqual((out["outcome"], out["decided_at_step"]), ("g0-fail", 4))

    def test_naive_arm_flagging_nothing_makes_comparison_not_applicable(self):
        runs = passing_runs()
        runs[1] = make_run(2, "textual-conflict", pairs=1, pairwise=True, chained=True)
        runs[4] = make_run(5)
        out = self.outcome(runs)
        self.assertEqual(out["c2"]["naive_comparison"], "not-applicable")
        self.assertEqual(out["outcome"], "g0-pass")

    def test_c1a_counts_probe_unavailable_runs_and_gates_nothing(self):
        runs = [make_run(i) for i in range(1, 10)]
        runs.append(make_run(10, "semantic-failure", primary=True, status="probe-unavailable"))
        out = self.outcome(runs)
        self.assertEqual((out["c1a"]["count"], out["c1a"]["met"]), (1, True))
        self.assertEqual(out["outcome"], "g0-inconclusive")

    def test_c1a_unmet_does_not_prevent_pass(self):
        out = self.outcome(passing_runs())
        self.assertFalse(out["c1a"]["met"])
        self.assertEqual(out["outcome"], "g0-pass")

    def test_confusion_counts_split_textual_and_semantic(self):
        arm = self.outcome(passing_runs())["arms"]["merge-tree-pairwise"]
        self.assertEqual((arm["tp"], arm["fn"], arm["tp_textual"], arm["fn_semantic"]), (1, 2, 1, 2))

    def test_invalid_input_is_rejected(self):
        bad = passing_runs()
        bad[0]["status"] = "made-up"
        with self.assertRaises(ValueError):
            self.outcome(bad)
        with self.assertRaises(ValueError):
            self.outcome(passing_runs() + [make_run(i) for i in range(11, 16)])
        bad = passing_runs()
        bad[0]["arms"]["braid-analyze-git-primary"] = True  # inclusive stays False
        with self.assertRaises(ValueError):
            self.outcome(bad)
        bad = passing_runs()
        bad[0]["probe"]["unknown_calls"] = 99
        with self.assertRaises(ValueError):
            self.outcome(bad)

    def test_c2_floor_is_inclusive_at_exactly_three_tenths(self):
        def outcome(flagged, failing):
            runs = [make_run(i, "semantic-failure" if i <= failing else "clean",
                             pairs=1 if i <= flagged else 0) for i in range(1, 15)]
            return self.outcome(runs)
        at_floor = outcome(10, 3)  # precision 3/10, prevalence 3/14
        self.assertEqual(at_floor["c2"]["precision"], 0.3)
        self.assertEqual((at_floor["outcome"], at_floor["decided_at_step"]), ("g0-pass", 5))
        below = outcome(7, 2)  # precision 2/7, just under the floor
        self.assertEqual((below["outcome"], below["decided_at_step"]), ("g0-fail", 4))

    def test_c1a_requires_both_merge_tree_baselines_to_miss(self):
        only_chained = [make_run(1, "semantic-failure", chained=True, primary=True)]
        self.assertEqual(scorer.score({"runs": only_chained})["c1a"]["count"], 0)
        only_pairwise = [make_run(1, "semantic-failure", pairwise=True, primary=True)]
        self.assertEqual(scorer.score({"runs": only_pairwise})["c1a"]["count"], 0)

    def test_c1a_reports_naive_overlap_among_its_runs(self):
        runs = [make_run(1, "semantic-failure", primary=True, naive=True),
                make_run(2, "textual-conflict", primary=True)]
        c1a = scorer.score({"runs": runs})["c1a"]
        self.assertEqual((c1a["count"], c1a["also_flagged_by_naive"]), (2, 1))

    def test_prevalence_counts_only_eligible_runs_with_probe_data(self):
        runs = passing_runs() + [make_run(11, "semantic-failure", status="probe-unavailable")]
        out = self.outcome(runs)
        self.assertEqual(out["reference_failure_prevalence"], 0.3)  # 3 of 10, not 4 of 11
        self.assertEqual(out["c2"]["prevalence"], 0.3)

    def test_adherence_uses_first_ten_eligible_by_ordinal(self):
        runs = [make_run(i) for i in range(1, 13)]
        for run in runs[:10]:
            run["design"] = {"overlap": True, "contract": False}
        runs[10]["design"] = {"overlap": False, "contract": True}  # ordinal 11
        runs[11]["design"] = {"overlap": False, "contract": True}  # ordinal 12
        runs[10]["run_id"] = "aa"  # run_id order differs from ordinal order
        runs.reverse()  # and so does input order
        adherence = self.outcome(runs)["adherence"]
        self.assertEqual((adherence["first_ten_with_designed_overlap"],
                          adherence["first_ten_with_cross_file_contract"]), (10, 0))

    def test_adherence_thresholds_are_seven_overlap_and_three_contract(self):
        def adherence(overlap, contract):
            runs = [make_run(i) for i in range(1, 11)]
            for n, run in enumerate(runs):
                run["design"] = {"overlap": n < overlap, "contract": n < contract}
            return self.outcome(runs)["adherence"]
        self.assertFalse(adherence(6, 3)["overlap_design_met"])
        self.assertTrue(adherence(7, 2)["overlap_design_met"])
        self.assertFalse(adherence(7, 2)["contract_design_met"])
        self.assertTrue(adherence(7, 3)["contract_design_met"])

    def test_missing_or_mistyped_sections_raise_value_error(self):
        for mutate in (lambda r: r.pop("probe"), lambda r: r.pop("arms"),
                       lambda r: r.update(probe=[]), lambda r: r.update(arms="x")):
            bad = passing_runs()
            mutate(bad[0])
            with self.assertRaises(ValueError):
                self.outcome(bad)

    def test_design_flags_must_be_booleans_and_cli_reports_value_errors(self):
        bad = passing_runs()
        bad[0]["design"]["overlap"] = "no"
        with self.assertRaises(ValueError):
            self.outcome(bad)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp, "runs.json")
            path.write_text(json.dumps({"runs": [{"run_id": "r01", "ordinal": 1,
                                                 "status": "eligible"}]}), encoding="utf-8")
            proc = subprocess.run([sys.executable, str(KIT / "scorer.py"), str(path)],
                                  capture_output=True, text=True)
        self.assertEqual(proc.returncode, 1)
        self.assertIn("run r01", proc.stderr)
        self.assertNotIn("Traceback", proc.stderr)

    def test_duplicate_run_ids_boolean_ordinals_and_non_list_runs_are_rejected(self):
        bad = passing_runs()
        bad[1]["run_id"] = bad[0]["run_id"]  # would double count one run
        with self.assertRaises(ValueError):
            self.outcome(bad)
        bad = passing_runs()
        bad[0]["ordinal"] = True  # bool is an int subclass
        with self.assertRaises(ValueError):
            self.outcome(bad)
        for runs in (None, {"r01": {}}, "runs"):
            with self.assertRaises(ValueError):
                self.outcome(runs)

    def test_excluded_runs_are_counted_but_not_scored(self):
        runs = passing_runs() + [make_run(11, status="quota-exhausted")]
        out = self.outcome(runs)
        self.assertEqual(out["runs_by_status"]["quota-exhausted"], 1)
        self.assertEqual(out["eligible_with_probe_data"], 10)


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

    def test_manifest_template_is_valid_json_with_unset_bindings(self):
        manifest = json.loads((KIT / "run-manifest.template.json").read_text(encoding="utf-8"))
        self.assertFalse(manifest["frozen"])
        self.assertIsNone(manifest["repository"])
        self.assertTrue(manifest["runs"])


if __name__ == "__main__":
    unittest.main()
