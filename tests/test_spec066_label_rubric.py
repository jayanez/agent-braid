# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T103: the amended label rubric (REQ-103), frozen before any fit.

The table in MAPPING is hard-coded here on purpose: an edit to the rubric JSON
fails the digest pin until it is re-pinned in a reviewed change. No corpus is read.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path
import re
import tempfile
import unittest

from research import s15b_label_rubric as rubric

PINNED_DIGEST = "6f3d9fede30aa1b9908e77b3a55e7028e0cee1bc382c92ee12cc120c570edccf"
MAPPING = {
    "runtime-conflict": "conflict",
    "merge-conflict": "conflict",
    "merge-clean": "textually-clean",
    "verify-pass": "no-conflict-observed",
    "verify-fail": "integration-failure",
}
GOLDEN_DRAW = ["real-run-conflict-2", "real-run-conflict-7"]
MANIFEST = "ab" * 32
OTHER_MANIFEST = "cd" * 32
ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "specs" / "066-system-one-shadow" / "contracts"


def items(counts):
    """counts: {(source, label): n} -> synthetic joinKeys."""
    return [{"joinKey": f"{source}-{label}-{index}", "source": source, "label": label}
            for (source, label), n in sorted(counts.items()) for index in range(n)]


class MappingTests(unittest.TestCase):
    def setUp(self):
        self.rubric = rubric.load_rubric()

    def test_r1_every_outcome_kind_maps_to_exactly_one_label(self):
        self.assertEqual(self.rubric["outcomeToLabel"], MAPPING)
        self.assertEqual(rubric.OUTCOME_KINDS, frozenset(MAPPING))
        for kind, label in MAPPING.items():
            self.assertEqual(rubric.label_for(kind), label)
        with self.assertRaises(rubric.RubricError):
            rubric.label_for("runtime-timeout")

    def test_r2_verify_fail_is_not_conflict_and_clean_labels_stay_apart(self):
        self.assertNotEqual(rubric.label_for("verify-fail"), "conflict")
        self.assertNotEqual(rubric.label_for("verify-pass"), rubric.label_for("merge-clean"))
        self.assertIn("integration-failure", self.rubric["dp1"]["unscoredLabels"])
        self.assertFalse(self.rubric["dp1"]["poolLabelsByDefault"])

    def test_dp1_truth_vocabulary(self):
        self.assertEqual(rubric.dp1_truth("likely-conflicting", "conflict"), "right")
        self.assertEqual(rubric.dp1_truth("likely-conflicting", "textually-clean"), "wrong")
        self.assertEqual(rubric.dp1_truth("likely-independent", "textually-clean"), "right")
        self.assertEqual(rubric.dp1_truth("likely-independent", "no-conflict-observed"), "right")
        self.assertEqual(rubric.dp1_truth("likely-independent", "conflict"), "wrong")
        self.assertEqual(rubric.dp1_truth("likely-independent", "integration-failure"), "unscored")
        self.assertEqual(rubric.dp1_truth("undetermined", "conflict"), "counted")
        with self.assertRaises(rubric.RubricError):
            rubric.dp1_truth("maybe", "conflict")


class PolicyTests(unittest.TestCase):
    def test_r3_missing_label_policy_present_and_imputing_variants_rejected(self):
        base = rubric.load_rubric()
        policy = base["missingLabelPolicy"]
        self.assertFalse(policy["impute"])
        self.assertFalse(policy["dropSilently"])
        self.assertTrue(policy["excludeFromFitAndEvaluation"])
        self.assertTrue(policy["reportUnlabelledShare"])
        for key, value in (("impute", True), ("dropSilently", True),
                           ("excludeFromFitAndEvaluation", False),
                           ("reportUnlabelledShare", False),
                           ("worstCaseBound", "none"),
                           ("countBy", ["class"])):
            bad = copy.deepcopy(base)
            bad["missingLabelPolicy"][key] = value
            with self.assertRaises(rubric.RubricError, msg=key):
                rubric.validate_rubric(bad)
        bad = copy.deepcopy(base)
        del bad["missingLabelPolicy"]
        with self.assertRaises(rubric.RubricError):
            rubric.validate_rubric(bad)

    def test_validator_rejects_structural_damage(self):
        base = rubric.load_rubric()
        mutations = []
        for path, value in ((("outcomeToLabel", "merge-conflict"), "textually-clean"),
                            (("outcomeToLabel", "merge-clean"), "conflict"),
                            (("oracles", "real-run"), "none"),
                            (("missingLabelPolicy", "impute"), 0),
                            (("missingLabelPolicy", "reportUnlabelledShare"), 1),
                            (("adjudication", "sample", "fractionPercent"), 20.0),
                            (("adjudication", "sample", "drawKey"), "random"),
                            (("adjudication", "packetLimitation"), ""),
                            (("adjudication", "populationLimitation"), None)):
            wrong = copy.deepcopy(base)
            node = wrong
            for part in path[:-1]:
                node = node[part]
            node[path[-1]] = value
            mutations.append(wrong)
        wrong = copy.deepcopy(base)
        wrong["outcomeToLabel"]["verify-fail"] = "conflict"
        mutations.append(wrong)
        wrong = copy.deepcopy(base)
        wrong["outcomeToLabel"]["verify-pass"] = "undefined-label"
        mutations.append(wrong)
        wrong = copy.deepcopy(base)
        del wrong["outcomeToLabel"]["merge-clean"]
        mutations.append(wrong)
        wrong = copy.deepcopy(base)
        wrong["executionAuthorization"] = True
        mutations.append(wrong)
        wrong = copy.deepcopy(base)
        wrong["extra"] = 1
        mutations.append(wrong)
        wrong = copy.deepcopy(base)
        wrong["dp1"]["truth"]["likely-independent"].append("integration-failure")
        mutations.append(wrong)
        wrong = copy.deepcopy(base)
        wrong["dp1"]["poolLabelsByDefault"] = True
        mutations.append(wrong)
        wrong = copy.deepcopy(base)
        wrong["adjudication"]["sample"]["perSourceCap"] = 41
        mutations.append(wrong)
        for index, bad in enumerate(mutations):
            with self.assertRaises(rubric.RubricError, msg=index):
                rubric.validate_rubric(bad)

    def test_loader_rejects_bad_files(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "r.json"
            good = (CONTRACTS / "label-rubric-v0.1.json").read_text(encoding="utf-8")
            dup = good.replace('"schemaVersion"', '"labels": [], "schemaVersion"', 1)
            nan = good.replace('"fractionPercent": 20', '"fractionPercent": NaN', 1)
            for text in ("{", "[]", dup, nan, "[" * 3000 + "]" * 3000):
                target.write_text(text, encoding="utf-8")
                with self.assertRaises(rubric.RubricError):
                    rubric.load_rubric(target)
            link = Path(temp) / "link.json"
            target.write_text(good, encoding="utf-8")
            link.symlink_to(target)
            with self.assertRaises(rubric.RubricError):
                rubric.load_rubric(link)
            with self.assertRaises(rubric.RubricError):
                rubric.load_rubric(Path(temp) / "missing.json")
            target.write_bytes(b"{" + b" " * rubric.MAX_BYTES + b"}")
            with self.assertRaises(rubric.RubricError):
                rubric.load_rubric(target)
            target.write_text(good, encoding="utf-8")
            self.assertEqual(rubric.load_rubric(target), rubric.load_rubric())


class SampleTests(unittest.TestCase):
    def test_r4_deterministic_for_a_digest_and_differs_for_another(self):
        population = items({("real-run", "conflict"): 30, ("real-run", "textually-clean"): 30})
        first = rubric.select_adjudication_sample(population, MANIFEST)
        again = rubric.select_adjudication_sample(list(reversed(population)), MANIFEST)
        other = rubric.select_adjudication_sample(population, OTHER_MANIFEST)
        self.assertEqual(first, again)
        self.assertNotEqual(first, other)
        self.assertEqual(len(first), len(other))

    def test_r5_stratified_and_size_rule(self):
        population = items({("real-run", "conflict"): 150, ("real-run", "no-conflict-observed"): 50,
                            ("git-history-replay", "conflict"): 10,
                            ("git-history-replay", "textually-clean"): 5,
                            ("git-history-replay", "integration-failure"): 0})
        sample = rubric.select_adjudication_sample(population, MANIFEST)
        lookup = {entry["joinKey"]: (entry["source"], entry["label"]) for entry in population}
        by = {}
        for key in sample:
            source, label = lookup[key]
            by.setdefault(source, {}).setdefault(label, 0)
            by[source][label] += 1
        # real-run: 200 labelled -> min(40, 40) = 40, proportional 30 / 10
        self.assertEqual(by["real-run"], {"conflict": 30, "no-conflict-observed": 10})
        # replay: 15 labelled -> ceil(3) = 3, proportional 2 / 1
        self.assertEqual(sum(by["git-history-replay"].values()), 3)
        self.assertEqual(by["git-history-replay"], {"conflict": 2, "textually-clean": 1})
        self.assertEqual(len(sample), len(set(sample)))
        self.assertEqual(sample, sorted(sample))

    def test_golden_draw_pins_the_ranking_rule(self):
        population = items({("real-run", "conflict"): 10})
        sample = rubric.select_adjudication_sample(population, MANIFEST)
        self.assertEqual(sample, GOLDEN_DRAW)

    def test_size_rule_edges(self):
        self.assertEqual(rubric.sample_size(0), 0)
        self.assertEqual(rubric.sample_size(1), 1)
        self.assertEqual(rubric.sample_size(5), 1)
        self.assertEqual(rubric.sample_size(6), 2)
        self.assertEqual(rubric.sample_size(200), 40)
        self.assertEqual(rubric.sample_size(5000), 40)
        with self.assertRaises(rubric.RubricError):
            rubric.sample_size(-1)

    def test_sample_is_independent_of_unrelated_strata(self):
        small = items({("real-run", "conflict"): 20, ("real-run", "textually-clean"): 20})
        both = small + items({("git-history-replay", "conflict"): 20})
        picked = set(rubric.select_adjudication_sample(small, MANIFEST))
        self.assertEqual(picked, {k for k in rubric.select_adjudication_sample(both, MANIFEST)
                                  if k.startswith("real-run")})

    def test_selector_refuses_bad_input(self):
        good = items({("real-run", "conflict"): 3})
        for bad in ([{"joinKey": "a", "source": "real-run", "label": "unknown"}],
                    [{"joinKey": "a", "source": "elsewhere", "label": "conflict"}],
                    [{"joinKey": "", "source": "real-run", "label": "conflict"}],
                    [{"joinKey": "a", "source": "real-run", "label": "conflict", "path": "x"}],
                    good + good[:1], "not-a-list"):
            with self.assertRaises(rubric.RubricError):
                rubric.select_adjudication_sample(bad, MANIFEST)
        for digest in ("", "AB" * 32, "ab" * 31, None):
            with self.assertRaises(rubric.RubricError):
                rubric.select_adjudication_sample(good, digest)
        self.assertEqual(rubric.select_adjudication_sample([], MANIFEST), [])


class NoiseTests(unittest.TestCase):
    def test_r6_wilson_known_values(self):
        result = rubric.estimate_noise(5, 20)
        self.assertAlmostEqual(result["rate"], 0.25)
        self.assertAlmostEqual(result["lower"], 0.1119, places=4)
        self.assertAlmostEqual(result["upper"], 0.46871, places=4)
        zero = rubric.estimate_noise(0, 10)
        self.assertAlmostEqual(zero["lower"], 0.0, places=6)
        self.assertAlmostEqual(zero["upper"], 0.27753, places=4)
        full = rubric.estimate_noise(10, 10)
        self.assertAlmostEqual(full["upper"], 1.0, places=6)
        self.assertAlmostEqual(full["lower"], 0.72247, places=4)

    def test_noise_empty_and_invalid(self):
        empty = rubric.estimate_noise(0, 0)
        self.assertIsNone(empty["rate"])
        self.assertIsNone(empty["lower"])
        self.assertEqual(empty["n"], 0)
        for args in ((-1, 5), (6, 5), (1, -1), (True, 5), (1.5, 5), ("1", 5)):
            with self.assertRaises(rubric.RubricError):
                rubric.estimate_noise(*args)

    def test_noise_reports_limitation_not_a_quality_claim(self):
        result = rubric.estimate_noise(1, 40)
        self.assertIn("limitation", result)
        self.assertTrue(result["limitation"])


class DigestTests(unittest.TestCase):
    def test_r7_digest_equals_pinned_constant(self):
        self.assertEqual(rubric.rubric_digest(), PINNED_DIGEST)

    def test_digest_is_content_bound_and_format_independent(self):
        base = rubric.load_rubric()
        changed = copy.deepcopy(base)
        changed["adjudication"]["sample"]["fractionPercent"] = 25
        self.assertNotEqual(rubric.rubric_digest(base), rubric.rubric_digest(changed))
        reordered = dict(reversed(base.items()))
        self.assertEqual(rubric.rubric_digest(reordered), rubric.rubric_digest(base))

    def test_changed_file_fails_digest_pin(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "r.json"
            text = (CONTRACTS / "label-rubric-v0.1.json").read_text(encoding="utf-8")
            target.write_text(text.replace('"fractionPercent": 20', '"fractionPercent": 20 '),
                              encoding="utf-8")
            self.assertEqual(rubric.rubric_digest(rubric.load_rubric(target)), PINNED_DIGEST)
            target.write_text(text.replace("A structural-only", "A structural"), encoding="utf-8")
            self.assertNotEqual(rubric.rubric_digest(rubric.load_rubric(target)), PINNED_DIGEST)

    def test_markdown_and_json_agree_on_the_mapping(self):
        text = (CONTRACTS / "label-rubric-v0.1.md").read_text(encoding="utf-8")
        for kind, label in MAPPING.items():
            self.assertRegex(text, rf"`{re.escape(kind)}`\s*\|\s*`{re.escape(label)}`")
        self.assertIn(PINNED_DIGEST, text)


class WordingAndPrivacyTests(unittest.TestCase):
    FORBIDDEN = re.compile(r"accura|utility|useful|validated|proves|calibrated", re.IGNORECASE)

    def test_r8_no_accuracy_or_utility_wording(self):
        for name in ("label-rubric-v0.1.md", "label-rubric-v0.1.json"):
            text = (CONTRACTS / name).read_text(encoding="utf-8")
            self.assertIsNone(self.FORBIDDEN.search(text), name)
        source = (ROOT / "research" / "s15b_label_rubric.py").read_text(encoding="utf-8")
        self.assertIsNone(self.FORBIDDEN.search(source))

    def test_noise_output_has_no_forbidden_wording(self):
        self.assertIsNone(self.FORBIDDEN.search(json.dumps(rubric.estimate_noise(3, 30))))

    def test_module_has_no_io_beyond_the_rubric_and_no_corpus_reference(self):
        source = (ROOT / "research" / "s15b_label_rubric.py").read_text(encoding="utf-8")
        for token in ("subprocess", "socket", "urllib", "system_one_shadow", "plugin_registry",
                      "episodes-", "salt.key"):
            self.assertNotIn(token, source)


if __name__ == "__main__":
    unittest.main()
