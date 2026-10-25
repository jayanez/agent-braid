# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-057 T015/T016: AIM mapping, pre-flight evidence block, closed vocabulary and lints."""

from __future__ import annotations

import contextlib
import hashlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from agent_braid import analysis, cli, ownership

TREE = ownership.BaseTree(frozenset({"src/a.py", "src/b.py", "docs/a.md", "package-lock.json", "src/index.ts"}))
ANALYZER_PIN = "3dad0113036bebec060c5fa9a0c7fd681f4d4f12ea96fbdbaf7fbd5121c181b9"
SEEDED_PHRASES = (
    "start the units in parallel", "launch both units", "schedule the units", "run them concurrently",
    "approved for parallel work", "we recommend parallel execution", "authorize the batch", "safe to parallelize",
    "go ahead and fan out", "proceed with the split", "ready to split", "green light", "permitted to run together",
)


def _unit(name, **extra):
    unit = {"id": name, "surface": "batch", "reads": ["docs/a.md"], "writes": [], "complete": True}
    unit.update(extra)
    return unit


def _run(units, base=True, tree=TREE):
    declaration = {"schemaVersion": ownership.SCHEMA_VERSION, "units": units}
    if base:
        declaration["base"] = {"ref": "develop"}
    expansion = ownership.expand_declaration(declaration, tree, repo_root="/repo", pinned_commit="a" * 40 if base else None)
    records = ownership.to_aim(expansion)
    return records, ownership.build_preflight(expansion), analysis.analyze(records)


CASES = {
    "disjoint": [_unit("a", writes=["src/a.py"]), _unit("b", writes=["src/b.py"])],
    "read-write-hazard": [_unit("a", reads=["src/b.py"], criticalReads=["src/b.py"]), _unit("b", writes=["src/b.py"])],
    "same-path-write": [_unit("a", writes=["src/a.py"]), _unit("b", writes=["src/a.py"])],
    "declared-dependency": [_unit("a", writes=["src/a.py"]), _unit("b", writes=["src/b.py"], dependsOn=["a"])],
    "partial-coverage": [_unit("a", writes=["nothing/**"]), _unit("b", writes=["src/b.py"])],
    "empty-read-set": [_unit("a", reads=[], writes=["src/a.py"]), _unit("b", writes=["src/b.py"])],
    "shared-lockfile-declared": [
        _unit("a", writes=["src/a.py"], sharedResources=[{"class": "lockfile", "path": "package-lock.json"}]),
        _unit("b", writes=["src/b.py"], sharedResources=[{"class": "lockfile", "path": "package-lock.json"}])],
    "lockfile-undeclared": [_unit("a", writes=["package-lock.json"]), _unit("b", writes=["src/b.py"])],
    "barrel-undeclared": [_unit("a", writes=["src/index.ts"]), _unit("b", writes=["src/b.py"])],
    "class-without-path": [_unit("a", writes=["src/a.py"], sharedResources=[{"class": "generated"}]), _unit("b", writes=["src/b.py"])],
    "not-marked-complete": [_unit("a", writes=["src/a.py"], complete=False), _unit("b", writes=["src/b.py"])],
    "missing-base": [_unit("a", writes=["src/a.py"], complete=False), _unit("b", writes=["src/b.py"], complete=False)],
}


def _classes(report):
    return {(i["left"], i["right"]): i["classification"] for i in report["interactions"]}


def _strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for item in value.values():
            yield from _strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _strings(item)


class ClassTableTests(unittest.TestCase):
    def verdict(self, name):
        records, preflight, report = _run(CASES[name], base=name != "missing-base")
        return _classes(report)[("a", "b")], preflight, report

    def test_class_table_matches_the_analyzer_rules(self):
        expected = {
            "disjoint": "independent-candidate", "read-write-hazard": "conflicting", "same-path-write": "conflicting",
            "declared-dependency": "ordered", "partial-coverage": "unknown", "empty-read-set": "independent-candidate",
            "shared-lockfile-declared": "conflicting", "lockfile-undeclared": "independent-candidate",
            "barrel-undeclared": "independent-candidate", "class-without-path": "unknown",
            "not-marked-complete": "unknown", "missing-base": "unknown",
        }
        for name, verdict in expected.items():
            with self.subTest(name=name):
                self.assertEqual(self.verdict(name)[0], verdict)

    def test_no_independent_candidate_has_partial_coverage(self):
        for name, units in CASES.items():
            with self.subTest(name=name):
                _, preflight, report = _run(units, base=name != "missing-base")
                partial = {c["unit"] for c in preflight["coverage"] if c["status"] != "complete"}
                for pair in report["interactions"]:
                    if pair["classification"] == "independent-candidate":
                        self.assertFalse({pair["left"], pair["right"]} & partial)

    def test_constraints_and_unknowns_instead_of_verdicts(self):
        self.assertIn({"code": "empty-read-set", "unit": "a"}, self.verdict("empty-read-set")[1]["unknowns"])
        self.assertIn({"code": "undeclared-shared-resource", "unit": "a", "count": 1},
                      self.verdict("lockfile-undeclared")[1]["unknowns"])
        self.assertIn({"code": "undeclared-shared-resource", "unit": "a", "count": 1},
                      self.verdict("barrel-undeclared")[1]["unknowns"])
        self.assertIn({"code": "shared-resource-without-path", "unit": "a"}, self.verdict("class-without-path")[1]["unknowns"])
        self.assertIn({"code": "missing-base-assertion"}, self.verdict("missing-base")[1]["unknowns"])
        self.assertIn({"code": "declaration-not-marked-complete", "unit": "a"}, self.verdict("not-marked-complete")[1]["unknowns"])
        self.assertIn({"code": "critical-read-hazard", "units": ["a", "b"]}, self.verdict("read-write-hazard")[1]["constraints"])
        self.assertIn({"code": "shared-resource-declared", "units": ["a", "b"]}, self.verdict("shared-lockfile-declared")[1]["constraints"])
        self.assertIn({"code": "dependency-declared", "units": ["a", "b"]}, self.verdict("declared-dependency")[1]["constraints"])
        self.assertFalse(any(u["code"] == "undeclared-shared-resource" for u in self.verdict("shared-lockfile-declared")[1]["unknowns"]))

    def test_partial_coverage_unknown_names_its_reasons(self):
        unknowns = self.verdict("partial-coverage")[1]["unknowns"]
        entry = next(u for u in unknowns if u["code"] == "partial-coverage")
        self.assertEqual(entry["reasons"], ["empty-expansion", "pattern-region"])


class EvidenceBlockTests(unittest.TestCase):
    def test_fixed_labels_statements_and_no_authorization(self):
        for name, units in CASES.items():
            with self.subTest(name=name):
                _, preflight, report = _run(units, base=name != "missing-base")
                self.assertEqual((preflight["class"], preflight["label"]), ("0-heuristic", "declared-only"))
                self.assertIs(preflight["executionAuthorization"], False)
                self.assertIs(report["executionAuthorization"], False)
                self.assertEqual(preflight["statements"], list(ownership.STATEMENTS))
                self.assertTrue(any("not evidence of a clean merge" in s and "SPEC-052" in s for s in preflight["statements"]))

    def test_records_use_the_declared_channel_only_and_validate_unchanged(self):
        records, _, _ = _run(CASES["disjoint"])
        for record in records:
            self.assertEqual(record["aimVersion"], "0.2.0-draft")
            self.assertTrue(record["effects"]["declared"])
            self.assertEqual((record["effects"]["inferred"], record["effects"]["observed"]), ([], []))
        analysis._validate_batch(records)

    def test_base_is_pinned_when_asserted_and_absent_otherwise(self):
        self.assertEqual(_run(CASES["disjoint"])[1]["base"], {"ref": "develop", "pinnedCommit": "a" * 40})
        self.assertEqual(_run(CASES["missing-base"], base=False)[1]["base"], {})

    def test_output_is_deterministic(self):
        first, second = _run(CASES["read-write-hazard"]), _run(CASES["read-write-hazard"])
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))


class VocabularyAndLintTests(unittest.TestCase):
    def test_lint_passes_every_fixed_string(self):
        for text in ownership.vocabulary():
            self.assertEqual(ownership.lint_text(text), [], text)

    def test_lint_passes_every_analyzer_string_the_preflight_can_surface(self):
        for name, units in CASES.items():
            _, _, report = _run(units, base=name != "missing-base")
            texts = [*report["limits"], *report["uncertainty"]]
            for pair in report["interactions"]:
                texts += [*pair["reasons"], *pair["constraints"], pair["classification"]]
            for text in texts:
                self.assertEqual(ownership.lint_text(text), [], text)

    def test_lint_fails_each_seeded_phrase(self):
        for phrase in SEEDED_PHRASES:
            with self.subTest(phrase=phrase):
                self.assertTrue(ownership.lint_text(phrase))

    def test_emitted_codes_stay_inside_the_closed_vocabulary(self):
        allowed = set(ownership.vocabulary())
        for name, units in CASES.items():
            _, preflight, _ = _run(units, base=name != "missing-base")
            codes = [e["code"] for e in (*preflight["constraints"], *preflight["unknowns"])]
            reasons = [r for e in preflight["unknowns"] for r in e.get("reasons", ())]
            self.assertLessEqual({*codes, *reasons, preflight["class"], preflight["label"], preflight["preflightVersion"],
                                  *preflight["statements"]}, allowed)

    def test_repository_text_cannot_reach_a_vocabulary_field(self):
        hostile = "src/start-the-units-in-parallel-and-approve.py"
        tree = ownership.BaseTree(frozenset({hostile, "src/b.py", "docs/a.md"}))
        _, preflight, _ = _run([_unit("a", writes=[hostile]), _unit("b", writes=["src/b.py"])], tree=tree)
        fields = [*(e["code"] for e in preflight["constraints"] + preflight["unknowns"]), *preflight["statements"],
                  preflight["class"], preflight["label"]]
        for text in fields:
            self.assertEqual(ownership.lint_text(text), [])
            self.assertNotIn(hostile, text)

    def test_every_partial_reason_and_code_is_declared_once(self):
        for group in (ownership.PARTIAL_REASONS, ownership.UNKNOWN_CODES, ownership.CONSTRAINT_CODES):
            self.assertEqual(list(group), sorted(set(group)))


class AnalyzerUnchangedTests(unittest.TestCase):
    def test_analyzer_output_for_non_ownership_input_is_byte_identical(self):
        def record(name, resource, kind):
            return {"aimVersion": "0.2.0-draft", "instanceId": name, "attemptId": name + "-t",
                    "definition": {"id": "d", "digest": "sha256:" + "0" * 64}, "inputDigest": "sha256:" + "1" * 64,
                    "dependencies": [], "readVersions": {},
                    "effects": {"declared": [{"kind": kind, "resource": resource}], "inferred": [], "observed": [],
                                "coverage": {"status": "complete", "domain": "x", "method": "y"}},
                    "evidence": [{"k": 1}]}
        report = analysis.analyze([record("a", "x", "write"), record("b", "y", "write"), record("c", "x", "read")])
        digest = hashlib.sha256(json.dumps(report, sort_keys=True, indent=2).encode()).hexdigest()
        self.assertEqual(digest, ANALYZER_PIN)


class CommandTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / "repo"
        (self.repo / "src").mkdir(parents=True)
        (self.repo / "src" / "a.py").write_text("SECRET-CONTENT\n")
        (self.repo / "src" / "b.py").write_text("b\n")
        (self.repo / "alias").symlink_to("src")
        git = lambda *a: subprocess.run(["git", "-C", str(self.repo), "-c", "user.email=t@e", "-c", "user.name=t", *a],
                                        check=True, capture_output=True)
        git("init", "-q")
        git("add", "-A")
        git("commit", "-qm", "init")
        git("branch", "-M", "develop")
        self.commit = subprocess.run(["git", "-C", str(self.repo), "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()

    def declaration(self, units, name="declaration.json", **extra):
        path = Path(self.tmp.name) / name
        path.write_text(json.dumps({"schemaVersion": ownership.SCHEMA_VERSION, "base": {"ref": "develop"}, "units": units, **extra}))
        return path

    def invoke(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def test_emits_records_preflight_and_analysis_for_a_real_base(self):
        path = self.declaration([_unit("a", reads=["src/a.py"], writes=["alias/a.py"]), _unit("b", writes=["src/a.py"])])
        before = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"], capture_output=True, text=True).stdout
        code, out, _ = self.invoke("expand-ownership", str(path), "--repository", str(self.repo))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual(result["preflight"]["base"], {"ref": "develop", "pinnedCommit": self.commit})
        self.assertEqual(result["analysis"]["interactions"][0]["classification"], "conflicting")
        self.assertIs(result["executionAuthorization"], False)
        self.assertNotIn("SECRET-CONTENT", out)
        after = subprocess.run(["git", "-C", str(self.repo), "status", "--porcelain"], capture_output=True, text=True).stdout
        self.assertEqual(before, after)

    def test_absolute_paths_resolve_against_the_repository_toplevel_not_the_given_subdirectory(self):
        absolute = str(self.repo.resolve() / "src" / "a.py")
        path = self.declaration([_unit("a", writes=[absolute]), _unit("b", writes=["src/a.py"])])
        code, out, _ = self.invoke("expand-ownership", str(path), "--repository", str(self.repo / "src"))
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)["analysis"]["interactions"][0]["classification"], "conflicting")

    def test_without_a_repository_every_unit_is_partial(self):
        code, out, _ = self.invoke("expand-ownership", str(self.declaration([_unit("a", writes=["x"]), _unit("b", writes=["y"])])))
        self.assertEqual(code, 0)
        result = json.loads(out)
        self.assertEqual({c["status"] for c in result["preflight"]["coverage"]}, {"partial"})
        self.assertEqual(result["analysis"]["interactions"][0]["classification"], "unknown")

    def test_refusals_print_the_command_error_and_no_result(self):
        bad = Path(self.tmp.name) / "bad.json"
        big = Path(self.tmp.name) / "big.json"
        mismatch = self.declaration([_unit("a"), _unit("b")], "mismatch.json", base={"ref": "develop", "commit": "b" * 40})
        bad.write_text("{}")
        big.write_bytes(b" " * (ownership.MAX_DECLARATION_BYTES + 1))
        cases = (
            (bad, "ERR-MALFORMED-INPUT", ()), (big, "ERR-OVER-BOUND", ()),
            (Path(self.tmp.name) / "missing.json", "ERR-UNOBSERVABLE-SOURCE", ()),
            (mismatch, "ERR-UNOBSERVABLE-SOURCE", ("--repository", str(self.repo))),
            (self.declaration([_unit("a"), _unit("b")], "plain.json"), "ERR-UNOBSERVABLE-SOURCE",
             ("--repository", str(Path(self.tmp.name)))),
        )
        for path, error, extra in cases:
            with self.subTest(error=error, path=path.name):
                code, out, _ = self.invoke("expand-ownership", str(path), *extra)
                result = json.loads(out)
                self.assertEqual(code, 2)
                self.assertEqual((result["errorCode"], result["resultProduced"], result["executionAuthorization"]), (error, False, False))
                self.assertNotIn("records", result)

    def test_refusal_diagnostics_never_echo_repository_text(self):
        secret = "SECRET-token-1f2e"
        path = self.declaration([_unit("a", writes=[secret + "\n"]), _unit("b")])
        code, out, err = self.invoke("expand-ownership", str(path))
        self.assertEqual(code, 2)
        self.assertNotIn(secret, out + err)


if __name__ == "__main__":
    unittest.main()
