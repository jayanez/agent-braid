# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T003/T004/T006 (procedures 003, 004 and 006): schema/validator differential test."""

from __future__ import annotations

import copy
import json
import unittest
from unittest.mock import patch

from agent_braid import analysis
from scripts import spec069_generate_corpus as generator
from tests.spec069_differential import (ROOT, UNITS_SCHEMA, Harness, aim_validator, git_validator, load_corpus,
                                        units_validator)
from scripts import spec069_divergence_inventory as inv

DOCUMENTED = {
    # difference id -> why the layers differ on purpose (contract: documented, not resolved)
    "RC-evidence", "RC-batch", "RC-adapter", "RC-adapter-bypass",
    "RC-git-unique", "RC-git-semantic", "RC-git-resolution",
}


class DifferentialTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.harness = Harness()
        cls.aim = load_corpus("aim")
        cls.git = load_corpus("git")

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    def test_corpus_is_current(self):
        self.assertEqual(generator.render(generator.aim_cases(), "aim"), (generator.OUTPUT / "aim.json").read_text())
        self.assertEqual(generator.render(generator.git_cases(), "git"), (generator.OUTPUT / "git.json").read_text())

    def test_every_aim_case_matches_its_expected_verdicts(self):
        self.assertEqual(self.harness.mismatches("aim", self.aim), [])

    def test_every_git_case_matches_its_expected_verdicts(self):
        self.assertEqual(self.harness.mismatches("git", self.git), [])

    def test_structural_cases_have_equal_verdicts_except_documented_differences(self):
        for case in self.aim + self.git:
            expect = case["expect"]
            if expect["schema"] != expect["service"]:
                self.assertTrue(case.get("difference") in DOCUMENTED or case.get("limit"),
                                f"{case['id']} {case['label']}: undocumented difference")
            elif case.get("difference"):
                # equal verdicts with a recorded difference: current behaviour of a known gap
                self.assertEqual(case["difference"], "RC-adapter-bypass", case["id"])

    def test_invalid_structural_cases_name_a_pointer(self):
        for case in self.aim + self.git:
            if case["layer"] == "structural" and case["expect"]["schema"] == "refuses":
                self.assertIsInstance(case["pointer"], str, case["id"])

    def test_corpus_covers_every_field_of_both_schemas(self):
        for kind, path, cases in (("aim", inv.AIM_SCHEMA, self.aim), ("git", inv.GIT_SCHEMA, self.git)):
            keywords = {(p, k) for p, k in self._keywords(kind)}
            seen = {(c["pointer"], c.get("keyword")) for c in cases if c.get("keyword")}
            seen_nodes = {self._strip(p, kind) for p, _ in seen}
            for pointer, _ in keywords:
                self.assertIn(pointer, seen_nodes | {""}, f"{kind}: no corpus case for {pointer}")

    @staticmethod
    def _strip(pointer, kind):
        return pointer[2:] if kind == "aim" and pointer.startswith("/0") else pointer

    @staticmethod
    def _keywords(kind):
        log = []
        if kind == "aim":
            a, _ = inv.aim_pair()
            inv.mutations(json.loads(inv.AIM_SCHEMA.read_text()), a, keyword_log=log)
        else:
            inv.mutations(json.loads(inv.GIT_SCHEMA.read_text()), inv.git_base(), keyword_log=log)
        return [(p, k) for p, k in log if k in {"required", "const", "enum", "minLength", "pattern", "minimum", "maximum", "minItems", "uniqueItems", "additionalProperties", "type"}]

    # --- T003: envelope schema -------------------------------------------------
    def test_envelope_schema_matches_runtime_on_aim_examples(self):
        validator = aim_validator()
        from agent_braid.analysis import analyze, InvalidAnalysis
        for path in sorted((ROOT / "examples/analysis").glob("*.json")):
            request = json.loads(path.read_text())
            if not (isinstance(request, dict) and request.get("source", {}).get("kind") == "aim"):
                continue
            with self.subTest(path.name):
                analyze(request)  # runtime accepts
                self.assertTrue(validator.is_valid(request))

    def test_envelope_schema_negative_controls(self):
        validator = aim_validator()
        valid = json.loads((ROOT / "examples/analysis/file-edits.json").read_text())
        extra = dict(valid, unexpected=1)
        empty = dict(valid, operations=[])
        self.assertFalse(validator.is_valid(extra))
        self.assertFalse(validator.is_valid(empty))
        with self.assertRaises(analysis.InvalidAnalysis):
            analysis.analyze(extra)
        with self.assertRaises(analysis.InvalidAnalysis):
            analysis.analyze(empty)

    # --- T004: negative controls ------------------------------------------------
    def test_negative_control_relaxing_a_schema_keyword_is_detected(self):
        aim_schema = json.loads(inv.AIM_SCHEMA.read_text())
        del aim_schema["properties"]["instanceId"]["pattern"]
        relaxed = Harness(aim=aim_validator(aim_schema=aim_schema))
        try:
            self.assertTrue(relaxed.mismatches("aim", self.aim), "relaxed schema keyword went unnoticed")
        finally:
            relaxed.close()
        git_schema = json.loads(inv.GIT_SCHEMA.read_text())
        git_schema["properties"]["operations"]["minItems"] = 1
        relaxed = Harness(git=git_validator(git_schema))
        try:
            self.assertTrue(relaxed.mismatches("git", self.git), "relaxed git keyword went unnoticed")
        finally:
            relaxed.close()

    def test_negative_control_relaxing_a_validator_check_is_detected(self):
        with patch.object(analysis, "_nonempty", lambda value, label, pointer=None: value):
            self.assertTrue(self.harness.mismatches("aim", self.aim), "relaxed validator check went unnoticed")

    def test_negative_control_tightening_the_validator_is_detected(self):
        original = analysis._validate_record

        def stricter(record):
            original(record)
            if record["evidence"][0].get("assuranceClass") == 5:
                raise analysis.InvalidAnalysis("assurance class 5 refused")

        with patch.object(analysis, "_validate_record", stricter):
            self.assertTrue(self.harness.mismatches("aim", self.aim))


class UnitsDifferentialTests(unittest.TestCase):
    """The units request schema against the complete analyze-work service path (T006)."""

    @classmethod
    def setUpClass(cls):
        cls.harness = Harness()  # its own service: the owned-evidence inventory is capped at 128 artifacts
        cls.units = load_corpus("units")

    @classmethod
    def tearDownClass(cls):
        cls.harness.close()

    def test_units_corpus_is_current(self):
        files = generator.units_files()
        on_disk = {p.relative_to(generator.UNITS_OUTPUT).as_posix(): p.read_text()
                   for p in generator.UNITS_OUTPUT.rglob("*") if p.is_file()}
        self.assertEqual(on_disk, files)

    def test_every_units_case_matches_its_expected_verdicts(self):
        self.assertGreater(len(self.units), 100)
        self.assertEqual(self.harness.mismatches("units", self.units), [])

    def test_units_cases_are_filed_by_service_verdict(self):
        for folder in ("valid", "invalid"):
            for path in (generator.UNITS_OUTPUT / folder).glob("*.json"):
                case = json.loads(path.read_text())
                self.assertEqual(case["expect"]["service"] == "accepts", folder == "valid", path.name)

    def test_units_differences_are_documented(self):
        for case in self.units:
            if case["expect"]["schema"] != case["expect"]["service"]:
                self.assertIn(case.get("difference"), {"RC-batch", "RC-adapter"}, case["id"])
            else:
                self.assertNotIn("difference", case, case["id"])

    def test_units_corpus_covers_every_keyword_of_the_schema(self):
        log = []
        inv.mutations(json.loads(UNITS_SCHEMA.read_text()), generator.units_base(), keyword_log=log)
        pointers = {c["pointer"] for c in self.units if c.get("keyword")}
        for pointer, _ in log:
            self.assertIn(pointer, pointers, f"no units case for {pointer or '/'}")
        # maxItems and maxLength are not walked by the inventory; the corpus adds them explicitly
        keywords = {c.get("keyword") for c in self.units}
        self.assertLessEqual({"maxItems", "maxLength", "pattern", "enum", "const", "uniqueItems", "minItems",
                              "additionalProperties", "required", "type", "minLength"}, keywords)

    def test_units_negative_control_relaxing_a_schema_keyword_is_detected(self):
        schema = json.loads(UNITS_SCHEMA.read_text())
        resource = schema["properties"]["units"]["items"]["properties"]["effects"]["items"]["properties"]["resource"]
        del resource["pattern"]
        relaxed = Harness(units=units_validator(schema))
        try:
            self.assertTrue(relaxed.mismatches("units", self.units), "relaxed resource pattern went unnoticed")
        finally:
            relaxed.close()

    def test_units_negative_control_relaxing_a_validator_check_is_detected(self):
        from agent_braid import units
        with patch.object(units, "EFFECT_KINDS", units.EFFECT_KINDS + ("unknown",)):
            self.assertTrue(self.harness.mismatches("units", self.units), "relaxed effect kind check went unnoticed")
        with patch.object(units, "normalize_resource", lambda value, pointer: value):
            self.assertTrue(self.harness.mismatches("units", self.units), "removed lexical checks went unnoticed")


if __name__ == "__main__":
    unittest.main()
