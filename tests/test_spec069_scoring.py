# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T010 (procedure_010): scoring rules, prompt sets, fixture and freeze record."""

from __future__ import annotations

import copy
import hashlib
import json
import re
import tempfile
import unittest
from pathlib import Path

from agent_braid import analysis, git_adapter
from scripts import spec069_fixture_workspace as fixture
from scripts import spec069_scoring as scoring

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "specs/069-aim-request-authoring/prompts"
SETS = {name: json.loads((PROMPTS / f"{name}.json").read_text()) for name in ("development", "held-out")}
FORBIDDEN = re.compile(
    r"(?<![.\w])(aim|instanceId|attemptId|effects?|coverage|schema|json|records?|operations?|resources?|declared|"
    r"inferred|observed|analyze-work|kind|envelope|digest|dependencies)\b", re.I)


def all_cases():
    return [(name, case) for name, data in SETS.items() for case in data["cases"]]


class Env(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.repo = fixture.build(Path(cls._tmp.name) / "ws")

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_request(self, case, request):
        if case["expect"]["kind"] == "git":
            return git_adapter.analyze_git(request)
        return analysis.analyze(request)

    def attempt(self, case, request, accepted=True, summary=None):
        kind = case["expect"]["kind"]
        report = self.run_request(case, request) if accepted else None
        return {"kind": kind, "request": request, "accepted": accepted, "refusalSummary": summary, "report": report}

    def reference(self, case):
        return scoring.reference_request(case, str(self.repo))

    def good(self, case):
        return self.attempt(case, self.reference(case))


class PromptSetTests(Env):
    def test_sets_have_ten_unique_cases_with_the_agreed_shape(self):
        ids = []
        for name, data in SETS.items():
            self.assertEqual(set(data), {"setId", "cases"})
            self.assertEqual(len(data["cases"]), 10, name)
            for case in data["cases"]:
                self.assertEqual(set(case), {"id", "prompt", "expect"})
                ids.append(case["id"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_prompts_use_no_request_vocabulary(self):
        for _, case in all_cases():
            self.assertIsNone(FORBIDDEN.search(case["prompt"]), case["id"])

    def test_sets_are_disjoint(self):
        dev, held = (({c["prompt"] for c in SETS[n]["cases"]}) for n in ("development", "held-out"))
        self.assertFalse(dev & held)
        signature = lambda c: json.dumps(c["expect"]["units"], sort_keys=True)  # noqa: E731
        self.assertFalse({signature(c) for c in SETS["development"]["cases"]}
                         & {signature(c) for c in SETS["held-out"]["cases"]})

    def test_difficulty_mix_matches_between_sets(self):
        def mix(data):
            return sorted((c["expect"]["kind"], len(c["expect"]["units"])) for c in data["cases"])
        self.assertEqual(mix(SETS["development"]), mix(SETS["held-out"]))
        kinds = [c["expect"]["kind"] for c in SETS["development"]["cases"]]
        self.assertEqual((kinds.count("aim"), kinds.count("git")), (7, 3))

    def test_every_prompt_names_the_files_or_branches_of_its_rule(self):
        for _, case in all_cases():
            for unit in case["expect"]["units"]:
                names = [unit["revision"]] if "revision" in unit else {e["resource"] for e in unit["effects"]}
                for name in names:
                    self.assertIn(name, case["prompt"], case["id"])

    def test_expected_pairs_equal_what_the_analyzer_says_for_the_reference(self):
        for _, case in all_cases():
            report = self.run_request(case, self.reference(case))
            derived = sorted((frozenset((i["left"], i["right"])), i["classification"], tuple(sorted(i["constraints"])))
                             for i in report["interactions"])
            stated = sorted((frozenset((p["left"], p["right"])), p["classification"], tuple(sorted(p["constraints"])))
                            for p in case["expect"]["pairs"])
            self.assertEqual(derived, stated, case["id"])

    def test_git_branches_exist_in_the_fixture(self):
        for _, case in all_cases():
            for unit in case["expect"]["units"]:
                if "revision" in unit:
                    self.assertIn(unit["revision"], fixture.BRANCHES)


class FixtureTests(Env):
    def test_build_is_deterministic_and_branches_start_at_main(self):
        import subprocess
        def tips(root):
            out = subprocess.run(["git", "-C", str(root), "rev-parse", *fixture.BRANCHES, "main"],
                                 capture_output=True, text=True, check=True).stdout
            return out.split()
        with tempfile.TemporaryDirectory() as other:
            again = fixture.build(Path(other) / "ws")
            self.assertEqual(tips(self.repo), tips(again))
        self.assertTrue((self.repo / "README.md").is_file())
        self.assertFalse((self.repo / "assets").exists())

    def test_refuses_a_nonempty_target(self):
        with self.assertRaises(ValueError):
            fixture.build(self.repo)


class ScoreCaseTests(Env):
    def test_every_case_scores_valid_against_its_reference_and_invalid_against_a_mutation(self):
        for _, case in all_cases():
            result = scoring.score_case(case, [self.good(case)])
            self.assertEqual(result, {"validFirstAttempt": True, "validWithinRetry": True, "reasons": []}, case["id"])
            mutated = copy.deepcopy(self.reference(case))
            if case["expect"]["kind"] == "git":
                mutated["operations"][0]["source"]["revision"] = "docs-faq" if case["expect"]["units"][0]["revision"] != "docs-faq" else "src-api"
            else:
                mutated["operations"][0]["effects"]["declared"][0]["resource"] = "repo://workspace/NOT-THE-FILE.txt"
            bad = scoring.score_case(case, [self.attempt(case, mutated)])
            self.assertFalse(bad["validFirstAttempt"] or bad["validWithinRetry"], case["id"])
            self.assertTrue(bad["reasons"])

    def case(self, case_id):
        return next(c for _, c in all_cases() if c["id"] == case_id)

    def test_tool_not_called_is_invalid(self):
        result = scoring.score_case(self.case("DEV-01"), [])
        self.assertFalse(result["validFirstAttempt"] or result["validWithinRetry"])
        self.assertIn("not called", result["reasons"][0])

    def test_empty_declaration_is_invalid(self):
        case = self.case("DEV-01")
        request = self.reference(case)
        for op in request["operations"]:
            op["effects"]["declared"] = []
        result = scoring.score_case(case, [self.attempt(case, request)])
        self.assertFalse(result["validFirstAttempt"])
        self.assertIn("declares no effect", result["reasons"][0])

    def test_inferred_or_observed_claim_is_invalid(self):
        case = self.case("DEV-02")
        for channel in ("inferred", "observed"):
            request = self.reference(case)
            first = request["operations"][0]["effects"]
            first[channel] = [dict(first["declared"][0])]
            self.assertFalse(scoring.score_case(case, [self.attempt(case, request)])["validFirstAttempt"], channel)
        request = self.reference(case)
        request["operations"][0]["evidence"][0]["method"] = "replay"
        self.assertFalse(scoring.score_case(case, [self.attempt(case, request)])["validFirstAttempt"])

    def test_wrong_resource_and_wrong_effect_kind_are_invalid(self):
        case = self.case("DEV-02")
        wrong = self.reference(case)
        wrong["operations"][0]["effects"]["declared"][0]["resource"] = "repo://workspace/src/db.py"
        self.assertFalse(scoring.score_case(case, [self.attempt(case, wrong)])["validFirstAttempt"])
        case = self.case("DEV-05")
        kind = self.reference(case)
        kind["operations"][0]["effects"]["declared"][0]["kind"] = "write"  # a read-only job declared as a write
        result = scoring.score_case(case, [self.attempt(case, kind)])
        self.assertFalse(result["validFirstAttempt"])

    def test_extra_unexpected_effect_is_invalid_but_implied_read_is_tolerated(self):
        case = self.case("DEV-02")
        extra = self.reference(case)
        extra["operations"][0]["effects"]["declared"].append({"kind": "write", "resource": "repo://workspace/README.md"})
        self.assertFalse(scoring.score_case(case, [self.attempt(case, extra)])["validFirstAttempt"])
        implied = self.reference(case)
        implied["operations"][0]["effects"]["declared"].append({"kind": "read", "resource": "repo://workspace/src/api.py"})
        self.assertTrue(scoring.score_case(case, [self.attempt(case, implied)])["validFirstAttempt"])

    def test_alias_path_is_invalid_through_the_report(self):
        case = self.case("DEV-01")
        request = self.reference(case)
        request["operations"][1]["effects"]["declared"][0]["resource"] = "repo://workspace/./README.md"
        result = scoring.score_case(case, [self.attempt(case, request)])
        # spelled differently, the analyzer sees two resources and reports independence
        self.assertFalse(result["validFirstAttempt"])
        self.assertIn("independent-candidate instead of conflicting", " ".join(result["reasons"]))

    def test_dot_slash_spelling_used_consistently_is_valid(self):
        case = self.case("DEV-01")
        request = self.reference(case)
        for op in request["operations"]:
            op["effects"]["declared"][0]["resource"] = "repo://workspace/./README.md"
        self.assertTrue(scoring.score_case(case, [self.attempt(case, request)])["validFirstAttempt"])
        bare = self.reference(case)
        for op in bare["operations"]:
            op["effects"]["declared"][0]["resource"] = "README.md"
        self.assertTrue(scoring.score_case(case, [self.attempt(case, bare)])["validFirstAttempt"])

    def test_normalization_rules(self):
        n = scoring.normalize_resource
        self.assertEqual(n("repo://x/docs/../README.md"), "README.md")
        self.assertEqual(n("repo://x/./src//api.py"), "src/api.py")
        self.assertEqual(n("src\\api.py"), "src/api.py")
        self.assertIsNone(n("repo://x/../etc/passwd"))
        self.assertIsNone(n("/etc/passwd"))
        self.assertIsNone(n("https://example.com/a"))
        self.assertIsNone(n("   "))
        self.assertNotEqual(n("repo://x/readme.md"), n("repo://x/README.md"))  # never case-folded
        self.assertEqual(scoring.normalize_revision("refs/heads/docs-guide"), "docs-guide")

    def test_dependency_direction_and_missing_dependency(self):
        case = self.case("DEV-04")
        request = self.reference(case)
        request["operations"][1]["dependencies"] = []
        result = scoring.score_case(case, [self.attempt(case, request)])
        self.assertFalse(result["validFirstAttempt"])
        reversed_ = self.reference(case)
        reversed_["operations"][1]["dependencies"] = []
        reversed_["operations"][0]["dependencies"] = ["two"]
        self.assertFalse(scoring.score_case(case, [self.attempt(case, reversed_)])["validFirstAttempt"])

    def test_identical_units_match_in_either_order_and_ids_are_free(self):
        case = self.case("DEV-01")
        request = self.reference(case)
        request["operations"].reverse()
        for op, new in zip(request["operations"], ("zeta", "alpha")):
            op["instanceId"], op["attemptId"] = new, new + "-1"
        self.assertTrue(scoring.score_case(case, [self.attempt(case, request)])["validFirstAttempt"])

    def test_single_record_and_array_forms_are_scored(self):
        case = self.case("DEV-01")
        ops = self.reference(case)["operations"]
        self.assertTrue(scoring.score_case(case, [self.attempt(case, ops)])["validFirstAttempt"])
        self.assertFalse(scoring.score_case(case, [self.attempt(case, ops[0])])["validFirstAttempt"])

    def units_attempt(self, case, resource=lambda r: r):
        """A `units` call for an aim case, analysed by the real units adapter (T008, FREEZE record 2)."""
        from agent_braid import units as units_module
        request = {"unitsRequestVersion": "0.1.0-alpha", "units": [
            {"id": u["key"], "dependencies": list(u["dependsOn"]),
             "effects": [{"kind": e["kind"], "resource": resource(e["resource"])}
                         for e in u["effects"] if not e.get("optional")]}
            for u in case["expect"]["units"]]}
        report = units_module.analyze(request, "0" * 32)["report"]
        return {"kind": "units", "request": request, "accepted": True, "refusalSummary": None, "report": report}

    def test_units_call_earns_only_the_classifications_it_can_report(self):
        conflict, wanted_independent = self.case("DEV-01"), self.case("DEV-02")
        self.assertTrue(scoring.score_case(conflict, [self.units_attempt(conflict)])["validFirstAttempt"])
        # negative control: a units call can never satisfy an independent-candidate expectation
        scored = scoring.score_case(wanted_independent, [self.units_attempt(wanted_independent)])
        self.assertFalse(scored["validFirstAttempt"])
        self.assertIn("is unknown instead of independent-candidate", scored["reasons"][0])

    def test_units_call_is_checked_for_resources_dependencies_and_kind(self):
        conflict, ordered, git = self.case("DEV-01"), self.case("DEV-04"), self.case("DEV-08")
        wrong = self.units_attempt(conflict, resource=lambda r: "other/" + r)
        self.assertFalse(scoring.score_case(conflict, [wrong])["validFirstAttempt"])
        for unit in (wrong2 := self.units_attempt(ordered))["request"]["units"]:
            unit["dependencies"] = []
        self.assertFalse(scoring.score_case(ordered, [wrong2])["validFirstAttempt"])
        attempt = self.good(git)
        attempt["kind"] = "units"  # units never stands in for a git case
        self.assertFalse(scoring.score_case(git, [attempt])["validFirstAttempt"])

    def test_wrong_kind_and_missing_report_are_invalid(self):
        case = self.case("DEV-08")
        attempt = self.good(case)
        attempt["kind"] = "aim"
        self.assertFalse(scoring.score_case(case, [attempt])["validFirstAttempt"])
        attempt = self.good(case)
        attempt["report"] = None
        self.assertFalse(scoring.score_case(case, [attempt])["validFirstAttempt"])

    def test_git_worktree_source_and_wrong_base_are_invalid(self):
        case = self.case("DEV-08")
        request = self.reference(case)
        request["operations"][0]["source"] = {"kind": "worktree", "path": str(self.repo)}
        self.assertFalse(scoring.score_case(case, [{"kind": "git", "request": request, "accepted": True, "refusalSummary": None,
                                                    "report": self.good(case)["report"]}])["validFirstAttempt"])
        request = self.reference(case)
        request["baseRevision"] = "docs-guide"
        self.assertFalse(scoring.score_case(case, [{"kind": "git", "request": request, "accepted": True, "refusalSummary": None,
                                                    "report": self.good(case)["report"]}])["validFirstAttempt"])

    def test_refused_first_attempt_then_valid_retry(self):
        case = self.case("DEV-01")
        refused = {"kind": "aim", "request": {}, "accepted": False,
                   "refusalSummary": "analyze-work refused: invalid envelope at /", "report": None}
        result = scoring.score_case(case, [refused, self.good(case)])
        self.assertEqual((result["validFirstAttempt"], result["validWithinRetry"]), (False, True))
        self.assertTrue(any("refused" in r for r in result["reasons"]))

    def test_second_refusal_and_third_attempt_do_not_count(self):
        case = self.case("DEV-01")
        refused = {"kind": "aim", "request": {}, "accepted": False, "refusalSummary": "x", "report": None}
        self.assertFalse(scoring.score_case(case, [refused, refused, self.good(case)])["validWithinRetry"])
        self.assertFalse(scoring.score_case(case, [refused])["validWithinRetry"])

    def test_accepted_but_wrong_first_attempt_gets_no_retry_credit(self):
        case = self.case("DEV-02")
        wrong = self.reference(case)
        wrong["operations"][0]["effects"]["declared"][0]["resource"] = "repo://workspace/src/db.py"
        result = scoring.score_case(case, [self.attempt(case, wrong), self.good(case)])
        self.assertEqual((result["validFirstAttempt"], result["validWithinRetry"]), (False, False))

    def test_valid_first_attempt_ignores_later_calls(self):
        case = self.case("DEV-02")
        self.assertTrue(scoring.score_case(case, [self.good(case), self.good(case)])["validFirstAttempt"])


class StatisticsTests(unittest.TestCase):
    def test_wilson_interval_known_values(self):
        low, high = scoring.wilson_interval(8, 10)
        self.assertAlmostEqual(low, 0.4902, places=3)
        self.assertAlmostEqual(high, 0.9433, places=3)
        low, high = scoring.wilson_interval(30, 30)
        self.assertAlmostEqual(low, 0.8865, places=3)
        self.assertEqual(high, 1.0)
        self.assertEqual(scoring.wilson_interval(0, 5)[0], 0.0)

    def test_wilson_interval_rejects_bad_input(self):
        for args in ((1, 0), (-1, 5), (6, 5)):
            with self.assertRaises(ValueError):
                scoring.wilson_interval(*args)

    @staticmethod
    def runs(first_ok, retry_ok=None, prompts=10, reps=3):
        retry_ok = set(range(prompts)) if retry_ok is None else retry_ok
        return [{"caseId": f"P{p}", "validFirstAttempt": p in first_ok, "validWithinRetry": p in retry_ok or p in first_ok}
                for p in range(prompts) for _ in range(reps)]

    def results(self, **overrides):
        base = {h: self.runs(set(range(10))) for h in scoring.REQUIRED_HOSTS}
        base.update(overrides)
        return base

    def test_all_hosts_meeting_the_threshold(self):
        summary = scoring.summarize(self.results(**{"codex": self.runs(set(range(8)))}))
        self.assertEqual(summary["overall"], "meets")
        self.assertNotIn("shortfall", summary)
        self.assertEqual(summary["hosts"]["codex"]["firstAttemptPrompts"], 8)

    def test_seven_first_attempt_prompts_miss_and_are_labelled_negative(self):
        summary = scoring.summarize(self.results(opencode=self.runs(set(range(7)))))
        self.assertEqual(summary["overall"], "negative-result")
        self.assertEqual(summary["hosts"]["opencode"]["verdict"], "misses")
        self.assertIn("NEGATIVE RESULT", summary["shortfall"]["label"])
        self.assertEqual(summary["shortfall"]["hosts"]["opencode"]["firstAttemptPromptsMissed"], ["P7", "P8", "P9"])

    def test_one_prompt_never_valid_even_with_retry_misses(self):
        summary = scoring.summarize(self.results(codex=self.runs(set(range(9)), retry_ok=set(range(9)))))
        self.assertEqual(summary["hosts"]["codex"]["verdict"], "misses")
        self.assertEqual(summary["hosts"]["codex"]["withinRetryPromptsMissed"], ["P9"])

    def test_one_failed_repetition_removes_the_prompt(self):
        runs = self.runs(set(range(10)))
        runs[0]["validFirstAttempt"] = False
        runs[1]["validFirstAttempt"] = False
        runs[0]["validWithinRetry"] = runs[1]["validWithinRetry"] = True
        summary = scoring.summarize(self.results(codex=runs))
        self.assertEqual(summary["hosts"]["codex"]["firstAttemptPrompts"], 9)
        self.assertEqual(summary["hosts"]["codex"]["verdict"], "meets")
        for index in range(2, 6):
            runs[index * 3]["validFirstAttempt"] = False
        self.assertEqual(scoring.summarize(self.results(codex=runs))["hosts"]["codex"]["verdict"], "misses")

    def test_unobserved_and_incomplete_hosts_are_inconclusive_not_failures(self):
        results = self.results()
        del results["codex"]
        summary = scoring.summarize(results)
        self.assertEqual(summary["hosts"]["codex"]["verdict"], "unobserved")
        self.assertEqual(summary["overall"], "inconclusive")
        self.assertIn("INCONCLUSIVE", summary["shortfall"]["label"])
        short = self.results(codex=self.runs(set(range(10)))[:-1])
        self.assertEqual(scoring.summarize(short)["hosts"]["codex"]["verdict"], "inconclusive")

    def test_a_miss_is_not_hidden_by_an_unobserved_host(self):
        results = self.results(opencode=self.runs(set()))
        del results["codex"]
        self.assertEqual(scoring.summarize(results)["overall"], "negative-result")

    def test_intervals_and_pooled_rates_are_reported(self):
        summary = scoring.summarize(self.results(codex=self.runs(set(range(8)))))
        host = summary["hosts"]["codex"]
        self.assertEqual((host["trials"], host["firstAttemptTrials"], host["withinRetryTrials"]), (30, 24, 30))
        self.assertEqual(host["firstAttemptInterval"], scoring.wilson_interval(24, 30))
        self.assertTrue(host["pooledMeetsThreshold"])


class FreezeTests(unittest.TestCase):
    def test_frozen_files_match_the_latest_record_and_the_chain_is_intact(self):
        freeze = json.loads((PROMPTS / "FREEZE.json").read_text())
        previous = None
        for record in freeze["records"]:
            self.assertEqual(record["previous"], previous)
            previous = hashlib.sha256(json.dumps(record, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
        latest = freeze["records"][-1]
        self.assertTrue(latest["reason"].strip())
        for path, digest in latest["files"].items():
            actual = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()
            self.assertEqual(actual, digest, f"{path} changed after the freeze: append a new record with scripts/spec069_freeze.py")
        self.assertEqual(set(latest["files"]), set(freeze["frozenFiles"]))

    def test_held_out_policy_and_viewers_are_recorded(self):
        freeze = json.loads((PROMPTS / "FREEZE.json").read_text())
        policy = freeze["heldOut"]
        self.assertIn("must not be shown", policy["policy"])
        self.assertIn("T008", policy["policy"])
        self.assertTrue(policy["seenBy"])
        self.assertIn("prompts/held-out.json", " ".join(freeze["frozenFiles"]))


if __name__ == "__main__":
    unittest.main()
