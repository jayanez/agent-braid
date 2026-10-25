# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-057 T014: path identity, expansion, create regions and the single overlap rule."""

from __future__ import annotations

import itertools
from pathlib import Path
import re
import unittest

from agent_braid import ownership, path_overlap, runtime_scheduler
from agent_braid.analysis import analyze

ROOT = Path(__file__).resolve().parents[1]
TREE = ownership.BaseTree(
    frozenset({
        "src/auth/x.py", "src/auth/y.py", "src/b.py", "docs/a.md", "Foo.py",
        "lib/real/m.py", "lib/real/n.py", "caf\u00e9.py", "pkg/one.py",
    }),
    {"lnk": "lib/real", "up": "../outside", "loop-a": "loop-b", "loop-b": "loop-a", "abs": "/etc", "file-link": "src/b.py"},
)


def _unit(name, **extra):
    unit = {"id": name, "surface": "batch", "reads": ["docs/a.md"], "writes": [], "complete": True}
    unit.update(extra)
    return unit


def _classes(units, tree=TREE, root="/repo", base=True):
    declaration = {"schemaVersion": ownership.SCHEMA_VERSION, "units": units}
    if base:
        declaration["base"] = {"ref": "develop"}
    expansion = ownership.expand_declaration(declaration, tree, repo_root=root)
    report = analyze(ownership.to_aim(expansion))
    return {(i["left"], i["right"]): i["classification"] for i in report["interactions"]}, expansion


def _pair(a, b, **kw):
    classes, expansion = _classes([a, b], **kw)
    return classes[("a", "b")], expansion


def reference_overlap(left: str, right: str) -> bool:
    """The rule exactly as runtime_scheduler spelled it before the extraction (regression control)."""
    return left == right or left.startswith(right + '/') or right.startswith(left + '/')


class SingleOverlapRuleTests(unittest.TestCase):
    def test_scheduler_imports_the_neutral_helper(self):
        self.assertIs(runtime_scheduler._overlap, path_overlap.paths_overlap)

    def test_ownership_uses_the_neutral_helper_and_spells_no_second_copy(self):
        self.assertIs(ownership.paths_overlap, path_overlap.paths_overlap)
        spelling = re.compile(r"startswith\(\s*\w+\s*\+\s*['\"]/['\"]\s*\)")
        for name in ("ownership.py", "ownership_cli.py", "runtime_scheduler.py"):
            self.assertIsNone(spelling.search((ROOT / "agent_braid" / name).read_text()), name)
        self.assertIsNotNone(spelling.search((ROOT / "agent_braid" / "path_overlap.py").read_text()))

    def test_pair_table_equals_the_pre_extraction_behaviour(self):
        pool = ["", "a", "a/b", "a/bc", "ab", "a/b/c", "a/", "/a", "a//b", "A", "a b", "\u00e9", "e\u0301", "a/b/", "b/a", "a.b"]
        checked = 0
        for left, right in itertools.product(pool, repeat=2):
            checked += 1
            self.assertEqual(path_overlap.paths_overlap(left, right), reference_overlap(left, right), (left, right))
            self.assertEqual(runtime_scheduler._overlap(left, right), reference_overlap(left, right), (left, right))
        self.assertEqual(checked, len(pool) ** 2)

    def test_scheduler_wave_geometry_is_unchanged_on_a_generated_manifest(self):
        paths = [["a"], ["a/b"], ["c"], ["c/d"], ["e"]]
        operations = [{"instanceId": f"op{i}", "attemptId": f"at{i}", "declaredWrites": w, "dependencies": []}
                      for i, w in enumerate(paths)]
        steps = [{"operationId": op["instanceId"], "inputTree": "t", "commit": "c", "sourceCommit": "s",
                  "patchDigest": "p", "effects": [{"path": op["declaredWrites"][0], "beforeMode": None, "beforeBlob": None}]}
                 for op in operations]
        manifest = {"repositoryId": "r", "steps": steps,
                    "request": {"operations": operations, "order": [o["instanceId"] for o in operations], "baseRevision": "b"}}
        waves, _ = runtime_scheduler._geometry(manifest)
        self.assertEqual(waves, [["op0"], ["op1", "op2"], ["op3", "op4"]])


class NormalizationTests(unittest.TestCase):
    def test_one_rule_for_spellings_of_one_path(self):
        for raw in ("src/b.py", "./src/b.py", "src/../src/b.py", "src//b.py", "src\\b.py", "/repo/src/b.py", "src/./b.py"):
            self.assertEqual(ownership.normalize_path(raw, "/repo"), ("src/b.py", None), raw)

    def test_unicode_composition_is_one_path(self):
        self.assertEqual(ownership.normalize_path("cafe\u0301.py"), ownership.normalize_path("caf\u00e9.py"))

    def test_unresolvable_spellings_name_a_reason(self):
        self.assertEqual(ownership.normalize_path("../x", "/repo"), (None, "outside-repository"))
        self.assertEqual(ownership.normalize_path("/etc/passwd", "/repo"), (None, "outside-repository"))
        self.assertEqual(ownership.normalize_path("/repo2/x", "/repo"), (None, "outside-repository"))
        self.assertEqual(ownership.normalize_path("/repo/x"), (None, "absolute-without-root"))
        self.assertEqual(ownership.normalize_path("C:/x"), (None, "absolute-without-root"))
        self.assertEqual(ownership.normalize_path("lnk/../x", "/repo", {"lnk": "d"}), (None, "symlink-unresolved"))

    def test_absolute_and_relative_spellings_are_one_resource(self):
        verdict, _ = _pair(_unit("a", writes=["/repo/src/b.py"]), _unit("b", writes=["./src/../src/b.py"]))
        self.assertEqual(verdict, "conflicting")


class NegativeControlTests(unittest.TestCase):
    def assertNeverIndependent(self, a, b, allowed=("conflicting", "unknown"), **kw):
        verdict, expansion = _pair(a, b, **kw)
        self.assertIn(verdict, allowed)
        self.assertNotEqual(verdict, "independent-candidate")
        return expansion

    def test_glob_versus_a_path_it_contains(self):
        self.assertNeverIndependent(_unit("a", writes=["src/auth/**"]), _unit("b", writes=["src/auth/x.py"]),
                                    allowed=("conflicting",))

    def test_glob_versus_a_new_path_under_it(self):
        self.assertNeverIndependent(_unit("a", writes=["src/auth/**"]), _unit("b", creates=["src/auth/new.py"]),
                                    allowed=("conflicting",))

    def test_directory_versus_a_file_in_it(self):
        self.assertNeverIndependent(_unit("a", writes=["src/auth"]), _unit("b", writes=["src/auth/x.py"]),
                                    allowed=("conflicting",))

    def test_two_creators_of_one_path(self):
        self.assertNeverIndependent(_unit("a", creates=["src/x/new.py"]), _unit("b", creates=["src/x/new.py"]),
                                    allowed=("conflicting",))

    def test_create_prefix_overlapping_another_units_path(self):
        expansion = self.assertNeverIndependent(_unit("a", creates=["src/x/"]), _unit("b", writes=["src/x/q.py"]),
                                                allowed=("conflicting",))
        self.assertIn({"code": "create-overlap", "units": ["a", "b"]}, expansion.constraints)

    def test_create_prefix_inside_another_create_prefix(self):
        self.assertNeverIndependent(_unit("a", creates=["src/x/"]), _unit("b", creates=["src/x/y/"]),
                                    allowed=("conflicting",))

    def test_file_versus_directory_of_the_same_name(self):
        self.assertNeverIndependent(_unit("a", creates=["src/x"]), _unit("b", creates=["src/x/y.py"]),
                                    allowed=("conflicting",))

    def test_case_only_names(self):
        _, expansion = _pair(_unit("a", writes=["Foo.py"]), _unit("b", writes=["foo.py"]))
        self.assertNeverIndependent(_unit("a", writes=["Foo.py"]), _unit("b", writes=["foo.py"]), allowed=("conflicting",))
        self.assertIn(("a", "b"), expansion.case_aliases)
        self.assertEqual(expansion.units[0].exact["writes"], expansion.units[1].exact["writes"])

    def test_case_alias_with_a_directory_region(self):
        self.assertNeverIndependent(_unit("a", creates=["Src/New/"]), _unit("b", writes=["src/new/q.py"]),
                                    allowed=("conflicting",))

    def test_composed_versus_decomposed_unicode(self):
        self.assertNeverIndependent(_unit("a", writes=["caf\u00e9.py"]), _unit("b", writes=["cafe\u0301.py"]),
                                    allowed=("conflicting",))

    def test_symlinked_directory_alias(self):
        self.assertNeverIndependent(_unit("a", writes=["lnk/m.py"]), _unit("b", writes=["lib/real/m.py"]),
                                    allowed=("conflicting",))

    def test_symlinked_file_alias(self):
        self.assertNeverIndependent(_unit("a", writes=["file-link"]), _unit("b", writes=["src/b.py"]),
                                    allowed=("conflicting",))

    def test_symlink_leaving_the_repository_loop_or_absolute_is_partial_not_disjoint(self):
        for link in ("up", "loop-a", "abs"):
            with self.subTest(link=link):
                expansion = self.assertNeverIndependent(_unit("a", writes=[f"{link}/x.py"]), _unit("b", writes=["z.py"]),
                                                        allowed=("unknown",))
                self.assertEqual(expansion.units[0].coverage, "partial")
                self.assertIn("symlink-unresolved", expansion.units[0].reasons)

    def test_path_outside_the_repository_is_partial(self):
        expansion = self.assertNeverIndependent(_unit("a", writes=["/elsewhere/x"]), _unit("b", writes=["z.py"]),
                                                allowed=("unknown",))
        self.assertIn("outside-repository", expansion.units[0].reasons)

    def test_glob_matching_nothing_is_partial(self):
        expansion = self.assertNeverIndependent(_unit("a", writes=["nothing/**"]), _unit("b", writes=["z.py"]),
                                                allowed=("unknown",))
        self.assertIn("empty-expansion", expansion.units[0].reasons)

    def test_read_glob_matching_nothing_is_partial(self):
        expansion = self.assertNeverIndependent(_unit("a", reads=["nothing/*.md"]), _unit("b", writes=["z.py"]),
                                                allowed=("unknown",))
        self.assertIn("empty-expansion", expansion.units[0].reasons)

    def test_whole_repository_entry_is_partial(self):
        expansion = self.assertNeverIndependent(_unit("a", writes=["."]), _unit("b", writes=["z.py"]), allowed=("unknown",))
        self.assertIn("whole-repository", expansion.units[0].reasons)

    def test_complexity_and_work_bounds_degrade_to_partial(self):
        expansion = self.assertNeverIndependent(_unit("a", writes=["a/**/**/**/**/**/**/x"]), _unit("b", writes=["z.py"]),
                                                allowed=("unknown",))
        self.assertIn("pattern-too-complex", expansion.units[0].reasons)
        big = ownership.BaseTree(frozenset(f"d/f{i}.py" for i in range(ownership.MAX_PATHS + 1)))
        expansion = self.assertNeverIndependent(_unit("a", writes=["d"]), _unit("b", writes=["z.py"]), tree=big,
                                                allowed=("unknown",))
        self.assertIn("expansion-bound", expansion.units[0].reasons)
        expansion = self.assertNeverIndependent(_unit("a", writes=["d/*.py"]), _unit("b", writes=["z.py"]), tree=big,
                                                allowed=("unknown",))
        self.assertIn("expansion-bound", expansion.units[0].reasons)

    def test_no_declared_base_or_tree_is_partial(self):
        verdict, expansion = _pair(_unit("a", writes=["src/b.py"], complete=False),
                             _unit("b", writes=["z.py"], complete=False), base=False)
        self.assertEqual(verdict, "unknown")
        self.assertIn("missing-base-assertion", expansion.units[0].reasons)
        declaration = {"schemaVersion": ownership.SCHEMA_VERSION, "base": {"ref": "develop"},
                       "units": [_unit("a", writes=["x"]), _unit("b", writes=["y"])]}
        self.assertEqual(ownership.expand_declaration(declaration, None).units[0].coverage, "partial")

    def test_unit_not_marked_complete_is_partial(self):
        verdict, _ = _pair(_unit("a", writes=["x.py"], complete=False), _unit("b", writes=["y.py"]))
        self.assertEqual(verdict, "unknown")


class ExpansionTests(unittest.TestCase):
    def test_disjoint_complete_declarations_are_the_only_independent_candidates(self):
        verdict, expansion = _pair(_unit("a", writes=["src/b.py"]), _unit("b", writes=["pkg/one.py"]))
        self.assertEqual(verdict, "independent-candidate")
        self.assertEqual({u.coverage for u in expansion.units}, {"complete"})

    def test_glob_matches_become_exact_paths_at_the_base(self):
        _, expansion = _pair(_unit("a", reads=["src/auth/*.py"]), _unit("b", writes=["z.py"]))
        self.assertEqual(expansion.units[0].exact["reads"], ("src/auth/x.py", "src/auth/y.py"))
        self.assertEqual(expansion.units[0].coverage, "complete")

    def test_directory_read_expands_to_its_files(self):
        _, expansion = _pair(_unit("a", reads=["src/auth"]), _unit("b", writes=["z.py"]))
        self.assertEqual(expansion.units[0].exact["reads"], ("src/auth/x.py", "src/auth/y.py"))

    def test_write_pattern_keeps_exact_matches_and_a_region(self):
        _, expansion = _pair(_unit("a", writes=["src/auth/**"]), _unit("b", writes=["z.py"]))
        unit = expansion.units[0]
        self.assertEqual(unit.exact["writes"], ("src/auth/x.py", "src/auth/y.py"))
        self.assertEqual(unit.regions["writes"], ("src/auth",))
        self.assertEqual(unit.coverage, "partial")

    def test_creates_are_exact_paths_or_prefix_regions(self):
        _, expansion = _pair(_unit("a", creates=["new/file.py", "gen/"]), _unit("b", writes=["z.py"]))
        unit = expansion.units[0]
        self.assertEqual((unit.exact["creates"], unit.regions["creates"]), (("new/file.py",), ("gen",)))
        self.assertIn("prefix-region", unit.reasons)

    def test_double_star_and_class_patterns(self):
        tree = ownership.BaseTree(frozenset({"a/b.py", "a/c/d.py", "a/c/e/f.py", "x.py", "a1.txt"}))
        cases = {"**/*.py": {"a/b.py", "a/c/d.py", "a/c/e/f.py", "x.py"}, "a/*.py": {"a/b.py"},
                 "a/**/*.py": {"a/b.py", "a/c/d.py", "a/c/e/f.py"}, "a?.txt": {"a1.txt"}, "[xa]?.txt": {"a1.txt"},
                 "[!a]*.py": {"x.py"}}
        for pattern, expected in cases.items():
            with self.subTest(pattern=pattern):
                _, expansion = _pair(_unit("a", reads=[pattern]), _unit("b", writes=["z.py"]), tree=tree)
                self.assertEqual(set(expansion.units[0].exact["reads"]), expected)

    def test_expansion_is_deterministic_and_order_independent(self):
        a = _unit("a", writes=["src/b.py", "src/auth/**"], creates=["n/"])
        b = _unit("b", writes=["docs/a.md"])
        first = _classes([a, b])[1]
        second = _classes([dict(b), dict(a, writes=list(reversed(a["writes"])))])[1]
        self.assertEqual(sorted(first.effects.items()), sorted(second.effects.items()))

    def test_invalid_declarations_are_refused_before_expansion(self):
        with self.assertRaises(ownership.DeclarationRefused):
            ownership.expand_declaration({"schemaVersion": ownership.SCHEMA_VERSION, "units": []}, TREE)

    def test_critical_read_hazard_is_a_constraint(self):
        _, expansion = _pair(_unit("a", reads=["src/b.py"], criticalReads=["src/b.py"]), _unit("b", writes=["src/b.py"]))
        self.assertIn({"code": "critical-read-hazard", "units": ["a", "b"]}, expansion.constraints)

    def test_the_comparison_helper_is_the_same_function(self):
        self.assertIs(ownership.paths_overlap, runtime_scheduler._overlap)


if __name__ == "__main__":
    unittest.main()
