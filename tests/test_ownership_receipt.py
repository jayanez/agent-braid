# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-057 T017/T018/T042: checkpoint comparison, the check-ownership command and the refusal contract."""

from __future__ import annotations

import contextlib
import copy
import io
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from jsonschema import Draft202012Validator

from agent_braid import cli, ownership, ownership_cli

CONTRACTS = Path(__file__).resolve().parents[1] / "specs/057-claude-orchestration-advisory/contracts"
RECEIPT_SCHEMA = json.loads((CONTRACTS / "envelope-receipt.schema.json").read_text(encoding="utf-8"))
ERROR_SCHEMA = json.loads((CONTRACTS / "command-error.schema.json").read_text(encoding="utf-8"))
RECEIPT = Draft202012Validator(RECEIPT_SCHEMA)
ERROR = Draft202012Validator(ERROR_SCHEMA)
BASE = "a" * 40
SECRET = "SECRET-FILE-CONTENT-1f9c"
TREE = ownership.BaseTree(frozenset({"src/a.py", "src/b.py", "docs/x.md", "lib/c.py"}))


def unit(name, **extra):
    data = {"id": name, "surface": "workflow-tracks", "reads": ["docs/x.md"], "writes": [], "complete": True}
    data.update(extra)
    return data


def declaration(units=None, **extra):
    data = {"schemaVersion": ownership.SCHEMA_VERSION, "base": {"commit": BASE},
            "units": units or [unit("a", writes=["src/a.py"]), unit("b", writes=["src/b.py"])]}
    data.update(extra)
    return data


def receipt_for(decl, observations=None, shared=None, tree=TREE):
    expansion = ownership.expand_declaration(decl, tree, repo_root="/repo", pinned_commit=BASE)
    return ownership.build_receipt(decl, expansion, observations or {}, shared)


def observed(*changes, digest="sha256:" + "1" * 64):
    return ownership.Observation(tuple(ownership.Change(k, p) for k, p in changes), digest)


def by_id(receipt, name):
    return next(u for u in receipt["units"] if u["id"] == name)


def assert_valid(case: unittest.TestCase, receipt):
    case.assertEqual([e.message[:120] for e in RECEIPT.iter_errors(receipt)], [])


class ComparisonTests(unittest.TestCase):
    def test_each_fixture_yields_its_entry_and_validates(self):
        receipt = receipt_for(declaration(), {
            "a": observed(("write", "src/a.py"), ("write", "src/new.py"), ("write", "src/b.py")),
            "b": observed(("write", "src/a.py")),
        })
        assert_valid(self, receipt)
        a, b = by_id(receipt, "a"), by_id(receipt, "b")
        self.assertEqual(a["undeclaredWrites"], ["src/new.py"])
        self.assertEqual(a["siblingAreaWrites"], [{"path": "src/b.py", "ownerUnit": "b"}])
        self.assertNotIn("declaredNotObserved", a)
        self.assertEqual(b["siblingAreaWrites"], [{"path": "src/a.py", "ownerUnit": "a"}])
        self.assertEqual(b["declaredNotObserved"], ["src/b.py"])

    def test_declared_creates_count_as_declared_writes(self):
        decl = declaration([unit("a", creates=["src/new.py"]), unit("b", writes=["src/b.py"])])
        receipt = receipt_for(decl, {"a": observed(), "b": observed(("write", "src/b.py"))})
        self.assertEqual(by_id(receipt, "a")["declaredNotObserved"], ["src/new.py"])
        self.assertEqual(by_id(receipt, "b").get("declaredNotObserved"), None)

    def test_region_writes_are_declared_area(self):
        decl = declaration([unit("a", writes=["src/"]), unit("b", writes=["lib/c.py"])])
        receipt = receipt_for(decl, {"a": observed(("write", "src/deep/new.py")), "b": observed(("write", "src/q.py"))})
        self.assertNotIn("undeclaredWrites", by_id(receipt, "a"))
        self.assertEqual(by_id(receipt, "b")["siblingAreaWrites"], [{"path": "src/q.py", "ownerUnit": "a"}])

    def test_unknown_for_deletions_renames_binaries_symlinks_and_submodules(self):
        reasons = ("deleted", "renamed", "binary", "symlink", "submodule", "unsupported")
        receipt = receipt_for(declaration(), {
            "a": observed(*[(reason, f"src/{reason}") for reason in reasons]), "b": observed()})
        assert_valid(self, receipt)
        a = by_id(receipt, "a")
        self.assertEqual({e["reason"] for e in a["unknown"]}, set(reasons))
        self.assertEqual(a["coverage"], "partial")
        self.assertNotIn("undeclaredWrites", a)

    def test_a_deleted_declared_write_is_unknown_not_missing(self):
        receipt = receipt_for(declaration(), {"a": observed(("deleted", "src/a.py")), "b": observed()})
        self.assertNotIn("declaredNotObserved", by_id(receipt, "a"))

    def test_a_case_only_difference_is_reported_not_absorbed(self):
        receipt = receipt_for(declaration(), {"a": observed(("write", "SRC/A.py")), "b": observed()})
        self.assertEqual(by_id(receipt, "a")["undeclaredWrites"], ["SRC/A.py"])
        composed = receipt_for(declaration([unit("a", writes=["caf\u00e9.py"]), unit("b")]),
                               {"a": observed(("write", "cafe\u0301.py")), "b": observed()}, tree=ownership.BaseTree(frozenset()))
        self.assertNotIn("undeclaredWrites", by_id(composed, "a"))

    def test_a_declared_directory_does_not_list_unchanged_members_as_not_observed(self):
        tree = ownership.BaseTree(frozenset({"src/a.py", "src/b.py", "lib/c.py"}))
        decl = declaration([unit("a", writes=["src"]), unit("b", writes=["lib/c.py"])])
        receipt = receipt_for(decl, {"a": observed(("write", "src/a.py")), "b": observed()}, tree=tree)
        self.assertNotIn("declaredNotObserved", by_id(receipt, "a"))
        self.assertEqual(by_id(receipt, "b")["declaredNotObserved"], ["lib/c.py"])

    def test_no_source_and_not_a_descendant_are_not_observed_never_clean(self):
        receipt = receipt_for(declaration(), {"b": "not-a-descendant-of-base"})
        assert_valid(self, receipt)
        a, b = by_id(receipt, "a"), by_id(receipt, "b")
        self.assertEqual((a["observation"], a["notObservedReason"], a["coverage"]),
                         ("not-observed", "no-source-supplied", "partial"))
        self.assertEqual(b["notObservedReason"], "not-a-descendant-of-base")
        self.assertIn(ownership.LIMIT_NOT_OBSERVED, receipt["limits"])
        with self.assertRaises(ValueError):
            receipt_for(declaration(), {"a": "busy"})

    def test_complete_coverage_needs_complete_expansion(self):
        decl = declaration([unit("a", writes=["src/a.py"], complete=False), unit("b", writes=["src/b.py"])])
        receipt = receipt_for(decl, {"a": observed(("write", "src/a.py")), "b": observed(("write", "src/b.py"))})
        self.assertEqual([u["coverage"] for u in receipt["units"]], ["partial", "complete"])

    def test_receipt_is_deterministic_and_digest_follows_observations(self):
        make = lambda digest: receipt_for(declaration(), {"a": observed(digest=digest), "b": observed()})
        self.assertEqual(make("sha256:" + "1" * 64), make("sha256:" + "1" * 64))
        self.assertNotEqual(make("sha256:" + "1" * 64)["snapshot"]["digest"],
                            make("sha256:" + "2" * 64)["snapshot"]["digest"])

    def test_receipt_needs_a_pinned_base_and_a_clean_label(self):
        decl = declaration()
        expansion = ownership.expand_declaration(decl, TREE)
        with self.assertRaises(ValueError):
            ownership.build_receipt(decl, expansion, {})
        pinned = ownership.expand_declaration(decl, TREE, pinned_commit=BASE)
        with self.assertRaises(ValueError):
            ownership.build_receipt(decl, pinned, {}, checkpoint="bad label\n")


class UnattributedWriterTests(unittest.TestCase):
    def test_shared_tree_attributes_nothing_and_lists_every_path(self):
        shared = observed(("write", "src/a.py"), ("deleted", "src/b.py"), ("write", "other.txt"))
        receipt = receipt_for(declaration(), {}, shared)
        assert_valid(self, receipt)
        self.assertEqual([w["path"] for w in receipt["unattributedWriters"]], ["other.txt", "src/a.py", "src/b.py"])
        self.assertTrue(all(w["effect"] == "unknown" for w in receipt["unattributedWriters"]))
        for entry in receipt["units"]:
            self.assertEqual(entry["observation"], "not-observed")
            self.assertEqual(set(entry) - {"id", "observation", "notObservedReason", "coverage"}, set())
        self.assertIn(ownership.LIMIT_SHARED_TREE, receipt["limits"])

    def test_65_changed_paths_give_a_truncated_partial_receipt_not_a_refusal(self):
        shared = observed(*[("write", f"gen/f{i:03}.txt") for i in range(65)])
        receipt = receipt_for(declaration(), {}, shared)
        assert_valid(self, receipt)
        self.assertEqual(len(receipt["unattributedWriters"]), ownership.UNATTRIBUTED_BOUND)
        self.assertEqual(receipt["truncations"], [{"list": "unattributedWriters", "total": 65}])
        self.assertEqual(receipt["unattributedWriters"][0]["path"], "gen/f000.txt")
        self.assertIn(ownership.LIMIT_TRUNCATED, receipt["limits"])
        self.assertTrue(all(u["coverage"] == "partial" for u in receipt["units"]))
        self.assertFalse(any(u.get("undeclaredWrites") or u.get("siblingAreaWrites") for u in receipt["units"]))

    def test_exactly_64_paths_are_not_truncated(self):
        receipt = receipt_for(declaration(), {}, observed(*[("write", f"g/{i}") for i in range(64)]))
        self.assertEqual(receipt["truncations"], [])

    def test_only_a_declared_exemption_rule_excludes_a_path_and_it_is_named(self):
        decl = declaration(
            [unit("a", writes=["src/a.py"], sharedResources=[{"class": "lockfile", "path": "uv.lock"}]),
             unit("b", writes=["src/b.py"])],
            unattributedWriterExemptions=[{"ruleId": "lock-by-human", "writer": "human", "paths": ["uv.lock"]}])
        receipt = receipt_for(decl, {}, observed(("write", "uv.lock"), ("write", "src/a.py")))
        assert_valid(self, receipt)
        self.assertEqual(receipt["exemptedPaths"], [{"path": "uv.lock", "ruleId": "lock-by-human"}])
        self.assertEqual([w["path"] for w in receipt["unattributedWriters"]], ["src/a.py"])
        other_case = receipt_for(decl, {}, observed(("write", "UV.LOCK")))
        self.assertEqual(other_case["exemptedPaths"], [])

    def test_unattributed_writes_are_never_a_units_violation(self):
        receipt = receipt_for(declaration(), {"a": observed(), "b": observed()},
                              observed(("write", "src/a.py"), ("write", "zzz")))
        for entry in receipt["units"]:
            self.assertFalse(entry.get("undeclaredWrites") or entry.get("siblingAreaWrites"))
        self.assertEqual(len(receipt["unattributedWriters"]), 2)

    def test_per_unit_lists_are_cut_with_unit_and_total(self):
        paths = [("write", f"stray/f{i:04}") for i in range(ownership.RECEIPT_LIST_BOUND + 3)]
        receipt = receipt_for(declaration(), {"a": observed(*paths), "b": observed()})
        assert_valid(self, receipt)
        self.assertEqual(len(by_id(receipt, "a")["undeclaredWrites"]), ownership.RECEIPT_LIST_BOUND)
        self.assertEqual(receipt["truncations"],
                         [{"list": "undeclaredWrites", "unitId": "a", "total": ownership.RECEIPT_LIST_BOUND + 3}])
        self.assertEqual(by_id(receipt, "a")["coverage"], "partial")

    def test_worst_case_truncation_entries_fit_the_schema(self):
        many = [("write", f"stray/{i:04}") for i in range(ownership.RECEIPT_LIST_BOUND + 1)]
        unknown = [("deleted", f"gone/{i:04}") for i in range(ownership.RECEIPT_LIST_BOUND + 1)]
        units = [unit(f"u{i}", writes=[f"w/{i}"]) for i in range(32)]
        obs = {f"u{i}": observed(*many, *unknown) for i in range(32)}
        receipt = receipt_for(declaration(units), obs, observed(*[("write", f"s/{i}") for i in range(70)]))
        assert_valid(self, receipt)


class EscapingTests(unittest.TestCase):
    def test_hostile_names_stay_schema_valid(self):
        names = ["a\nb", "x‮y", "z​", "t\U000e0001", "q" * 400, "lone\udc80", "ends\n"]
        receipt = receipt_for(declaration(), {"a": observed(*[("write", n) for n in names]), "b": observed()},
                              observed(*[("write", n) for n in names]))
        assert_valid(self, receipt)
        text = json.dumps(receipt, ensure_ascii=False)
        self.assertNotIn("‮", text)

    def test_escape_is_idempotent_bounded_and_distinguishes_long_names(self):
        for text in ("a‮b", "plain", "\x00" * 300):
            once = ownership.escape_repository_text(text)
            self.assertEqual(ownership.escape_repository_text(once), once)
            self.assertLessEqual(len(once), ownership.MAX_STRING)
        first = ownership.escape_repository_text("n" * 300 + "1")
        self.assertNotEqual(first, ownership.escape_repository_text("n" * 300 + "2"))


class RefusalContractTests(unittest.TestCase):
    def test_every_code_validates_as_an_error_and_no_receipt(self):
        for code in ownership.ERROR_CODES:
            error = ownership.command_error(code, unit_id="a", rule="index-lock")
            self.assertEqual(list(ERROR.iter_errors(error)), [])
            self.assertFalse(error["resultProduced"])
            self.assertTrue(list(RECEIPT.iter_errors(error)), "a refusal must not validate as a receipt")
        self.assertEqual(set(ownership.ERROR_CODES), set(ERROR_SCHEMA["properties"]["errorCode"]["enum"]))

    def test_a_refusal_emitted_as_a_receipt_fails(self):
        receipt = receipt_for(declaration(), {"a": observed(), "b": observed()})
        smuggled = copy.deepcopy(receipt)
        smuggled.update(errorCode="ERR-BUSY", resultProduced=False)
        self.assertTrue(list(RECEIPT.iter_errors(smuggled)))
        self.assertTrue(list(ERROR.iter_errors(receipt)))
        as_error = ownership.command_error("ERR-BUSY")
        as_error.update(snapshot=receipt["snapshot"], units=receipt["units"])
        self.assertTrue(list(ERROR.iter_errors(as_error)))

    def test_errors_refuse_repository_text(self):
        with self.assertRaises(ValueError):
            ownership.command_error("ERR-BUSY", rule="src/a.py")
        with self.assertRaises(ValueError):
            ownership.command_error("ERR-BUSY", unit_id="../x")
        with self.assertRaises(ValueError):
            ownership.command_error("ERR-FINE")
        self.assertTrue(list(ERROR.iter_errors({**ownership.command_error("ERR-BUSY"), "errorCode": "ERR-OK"})))

    def test_not_observed_reasons_are_closed(self):
        enum = RECEIPT_SCHEMA["properties"]["units"]["items"]["properties"]["notObservedReason"]["enum"]
        self.assertEqual(tuple(enum), ownership.NOT_OBSERVED_REASONS)
        bad = receipt_for(declaration(), {})
        bad["units"][0]["notObservedReason"] = "unstable"
        self.assertTrue(list(RECEIPT.iter_errors(bad)))

    def test_constants_equal_the_schema(self):
        self.assertEqual(json.loads(json.dumps(ownership.RECEIPT_ASSURANCE)),
                         {k: (v["const"] if "const" in v else None)
                          for k, v in RECEIPT_SCHEMA["properties"]["assurance"]["properties"].items()})
        self.assertEqual(ownership.RECEIPT_VERSION, RECEIPT_SCHEMA["properties"]["schemaVersion"]["const"])
        self.assertEqual(ownership.ERROR_SCHEMA_VERSION, ERROR_SCHEMA["properties"]["schemaVersion"]["const"])

    def test_receipt_strings_pass_the_wording_lint(self):
        receipt = receipt_for(declaration(), {"b": observed(("deleted", "x"))}, observed(("write", "y")))
        strings = [*receipt["limits"], *receipt["assurance"]["assumptions"],
                   receipt["assurance"]["property"], receipt["assurance"]["observationContract"]]
        for text in strings:
            self.assertEqual(ownership.lint_text(text), [], text)


def git(repo, *args, check=True):
    return subprocess.run(["git", "-C", str(repo), "-c", "user.email=t@e", "-c", "user.name=t", *args],
                          capture_output=True, text=True, check=check).stdout.strip()


class GitFixture:
    """A temporary repository with a base commit and cheap worktrees; removed on cleanup."""

    def __init__(self, case: unittest.TestCase):
        self.dir = Path(tempfile.mkdtemp(prefix="receipt-")).resolve()
        case.addCleanup(self._remove)
        self.repo = self.dir / "repo"
        self.repo.mkdir()
        git(self.repo, "init", "-q", "-b", "main")
        (self.repo / "src").mkdir()
        for name in ("a.py", "b.py"):
            (self.repo / "src" / name).write_text("base\n")
        (self.repo / "docs.md").write_text("docs\n")
        git(self.repo, "add", ".")
        git(self.repo, "commit", "-qm", "base")
        self.base = git(self.repo, "rev-parse", "HEAD")
        self.out = self.dir / "out"
        self.out.mkdir()

    def _remove(self):
        import shutil
        shutil.rmtree(self.dir, ignore_errors=True)

    def worktree(self, name, commit=None):
        path = self.dir / name
        git(self.repo, "worktree", "add", "-q", "-b", name, str(path), commit or self.base)
        return path

    def write(self, root, relative, text="changed\n"):
        target = Path(root) / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self, root, message="work"):
        git(root, "add", "-A")
        git(root, "commit", "-qm", message)

    def declaration(self, **extra):
        data = {"schemaVersion": ownership.SCHEMA_VERSION, "base": {"commit": self.base},
                "units": [unit("a", writes=["src/a.py"]), unit("b", writes=["src/b.py"])]}
        data.update(extra)
        path = self.dir / "declaration.json"
        path.write_text(json.dumps(data))
        return path

    def run(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = cli.main(list(argv))
        return code, out.getvalue(), err.getvalue()

    def check(self, declaration, *extra, output="receipt.json"):
        target = self.out / output
        code, out, err = self.run("check-ownership", str(declaration), "--repository", str(self.repo),
                                  "--output", str(target), *extra)
        return code, out, err, target


class CheckOwnershipTests(unittest.TestCase):
    def setUp(self):
        self.fx = GitFixture(self)

    def test_worktrees_and_commits_yield_a_valid_receipt_without_content(self):
        fx = self.fx
        wa, wb = fx.worktree("ua"), fx.worktree("ub")
        fx.write(wa, "src/a.py", SECRET)
        fx.write(wa, "src/extra.py")
        fx.commit(wa)
        fx.write(wb, "src/a.py")
        fx.commit(wb)
        before = git(fx.repo, "status", "--porcelain")
        code, out, err, target = fx.check(
            fx.declaration(), "--source", f"a=worktree:{wa}", "--source", f"b=commit:ub", "--checkpoint", "cp-1")
        self.assertEqual((code, err), (0, ""))
        receipt = json.loads(target.read_text())
        assert_valid(self, receipt)
        self.assertEqual(receipt["snapshot"]["base"], fx.base)
        self.assertEqual(receipt["snapshot"]["checkpoint"], "cp-1")
        self.assertEqual(json.loads(out)["snapshot"], receipt["snapshot"]["digest"])
        self.assertEqual(by_id(receipt, "a")["undeclaredWrites"], ["src/extra.py"])
        self.assertEqual(by_id(receipt, "b")["siblingAreaWrites"], [{"path": "src/a.py", "ownerUnit": "a"}])
        self.assertNotIn(SECRET, target.read_text() + out)
        self.assertEqual(git(fx.repo, "status", "--porcelain"), before)
        self.assertEqual(os.stat(target).st_mode & 0o777, 0o600)

    def test_deletes_symlinks_binaries_and_untracked_kinds_are_unknown(self):
        fx = self.fx
        wa = fx.worktree("ua")
        (wa / "src/a.py").unlink()
        os.symlink("docs.md", wa / "link")
        fx.write(wa, "blob.bin", "x\0y")
        fx.commit(wa)
        os.symlink("docs.md", wa / "ulink")
        (wa / "ubin").write_bytes(b"\0\0")
        fx.write(wa, "plain.txt")
        code, _, err, target = fx.check(fx.declaration(), "--source", f"a=worktree:{wa}")
        self.assertEqual((code, err), (0, ""))
        receipt = json.loads(target.read_text())
        assert_valid(self, receipt)
        unknown = {e["path"]: e["reason"] for e in by_id(receipt, "a")["unknown"]}
        self.assertEqual(unknown, {"src/a.py": "deleted", "link": "symlink", "blob.bin": "binary",
                                   "ulink": "symlink", "ubin": "binary"})
        self.assertEqual(by_id(receipt, "a")["undeclaredWrites"], ["plain.txt"])
        self.assertEqual(by_id(receipt, "b")["notObservedReason"], "no-source-supplied")

    def test_shared_tree_lists_changes_unattributed_and_nothing_else(self):
        fx = self.fx
        fx.write(fx.repo, "src/a.py")
        fx.write(fx.repo, "untracked.txt")
        code, _, err, target = fx.check(fx.declaration(), "--shared-tree", str(fx.repo))
        self.assertEqual((code, err), (0, ""))
        receipt = json.loads(target.read_text())
        assert_valid(self, receipt)
        self.assertEqual([w["path"] for w in receipt["unattributedWriters"]], ["src/a.py", "untracked.txt"])
        self.assertTrue(all(u["observation"] == "not-observed" for u in receipt["units"]))

    def test_many_changed_paths_on_a_shared_tree_are_truncated_not_refused(self):
        fx = self.fx
        for i in range(70):
            fx.write(fx.repo, f"gen/f{i:03}.txt")
        code, _, _, target = fx.check(fx.declaration(), "--shared-tree", str(fx.repo))
        self.assertEqual(code, 0)
        receipt = json.loads(target.read_text())
        assert_valid(self, receipt)
        self.assertEqual(receipt["truncations"], [{"list": "unattributedWriters", "total": 70}])

    def test_a_branch_off_another_commit_is_not_a_descendant_and_not_clean(self):
        fx = self.fx
        fx.write(fx.repo, "newer.txt")
        fx.commit(fx.repo, "newer")
        # a worktree created at the older base is a descendant; one on an orphan root is not
        git(fx.repo, "checkout", "-q", "--orphan", "other")
        git(fx.repo, "rm", "-rqf", ".")
        fx.write(fx.repo, "z.txt")
        fx.commit(fx.repo, "orphan")
        git(fx.repo, "branch", "-q", "orphan-tip")
        git(fx.repo, "checkout", "-q", "main")
        code, _, _, target = fx.check(fx.declaration(), "--source", "a=commit:orphan-tip")
        self.assertEqual(code, 0)
        a = by_id(json.loads(target.read_text()), "a")
        self.assertEqual((a["observation"], a["notObservedReason"]), ("not-observed", "not-a-descendant-of-base"))

    def test_a_worktree_changing_between_observations_is_refused_without_a_receipt(self):
        fx = self.fx
        wa = fx.worktree("ua")
        original = ownership_cli._observe_once
        calls = []

        def drifting(*args, **kwargs):
            result = original(*args, **kwargs)
            calls.append(1)
            if len(calls) == 1:
                fx.write(wa, "src/a.py", "moved under the checker\n")
            return result

        with mock.patch.object(ownership_cli, "_observe_once", drifting):
            code, out, _, target = fx.check(fx.declaration(), "--source", f"a=worktree:{wa}")
        self.assertEqual(code, 2)
        error = json.loads(out)
        self.assertEqual((error["errorCode"], error["unitId"]), ("ERR-UNSTABLE-SNAPSHOT", "a"))
        self.assertEqual(list(ERROR.iter_errors(error)), [])
        self.assertFalse(target.exists())
        self.assertEqual(list(fx.out.iterdir()), [])

    def test_a_busy_lock_is_refused(self):
        fx = self.fx
        wa = fx.worktree("ua")
        lock = Path(git(wa, "rev-parse", "--absolute-git-dir")) / "index.lock"
        lock.write_text("")
        code, out, _, target = fx.check(fx.declaration(), "--source", f"a=worktree:{wa}")
        self.assertEqual((code, json.loads(out)["errorCode"]), (2, "ERR-BUSY"))
        self.assertFalse(target.exists())

    def test_existing_output_is_refused_and_untouched(self):
        fx = self.fx
        existing = fx.out / "receipt.json"
        existing.write_text("keep")
        code, out, _, _ = fx.check(fx.declaration())
        self.assertEqual((code, json.loads(out)["errorCode"], existing.read_text()), (2, "ERR-OUTPUT-EXISTS", "keep"))
        link = fx.out / "link.json"
        os.symlink(fx.out / "nowhere", link)
        code, out, _, _ = fx.check(fx.declaration(), output="link.json")
        self.assertEqual((code, json.loads(out)["errorCode"]), (2, "ERR-OUTPUT-EXISTS"))
        self.assertFalse((fx.out / "nowhere").exists())

    def test_output_inside_the_repository_or_a_missing_parent_is_refused(self):
        fx = self.fx
        for target, rule in ((fx.repo / "receipt.json", "output-in-repository"),
                             (fx.out / "missing" / "r.json", "output-parent")):
            code, out, _ = fx.run("check-ownership", str(fx.declaration()), "--repository", str(fx.repo),
                                  "--output", str(target))
            self.assertEqual((code, json.loads(out)["rule"]), (2, rule))
            self.assertFalse(target.exists())

    def test_unobservable_and_malformed_inputs_are_refused(self):
        fx = self.fx
        decl = fx.declaration()
        cases = {
            "unobservable worktree": (("--source", f"a=worktree:{fx.dir / 'nowhere'}"), "ERR-UNOBSERVABLE-SOURCE"),
            "unresolvable commit": (("--source", "a=commit:no-such-rev"), "ERR-UNOBSERVABLE-SOURCE"),
            "foreign worktree": (("--source", f"a=worktree:{self._foreign()}"), "ERR-UNOBSERVABLE-SOURCE"),
            "bad source": (("--source", "a=ftp:x"), "ERR-MALFORMED-INPUT"),
            "option-like revision": (("--source", "a=commit:--all"), "ERR-MALFORMED-INPUT"),
            "unknown unit": (("--source", "zz=commit:main"), "ERR-MALFORMED-INPUT"),
            "duplicate unit": (("--source", "a=commit:main", "--source", "a=commit:main"), "ERR-MALFORMED-INPUT"),
            "bad checkpoint": (("--checkpoint", "no spaces"), "ERR-MALFORMED-INPUT"),
        }
        for label, (extra, expected) in cases.items():
            with self.subTest(label):
                code, out, _, target = fx.check(decl, *extra)
                self.assertEqual((code, json.loads(out)["errorCode"]), (2, expected))
                self.assertFalse(target.exists())

    def _foreign(self):
        other = self.fx.dir / "foreign"
        other.mkdir()
        git(other, "init", "-q")
        return other

    def test_declaration_without_base_or_over_bound_is_refused(self):
        fx = self.fx
        no_base = fx.dir / "nobase.json"
        no_base.write_text(json.dumps({"schemaVersion": ownership.SCHEMA_VERSION,
                                       "units": [unit("a", complete=False), unit("b", complete=False)]}))
        code, out, _, _ = fx.check(no_base)
        self.assertEqual((code, json.loads(out)["rule"]), (2, "missing-base"))
        huge = fx.dir / "huge.json"
        huge.write_bytes(b" " * (ownership.MAX_DECLARATION_BYTES + 1))
        code, out, _, _ = fx.check(huge)
        self.assertEqual((code, json.loads(out)["errorCode"]), (2, "ERR-OVER-BOUND"))
        code, out, _, _ = fx.check(fx.dir / "absent.json")
        self.assertEqual((code, json.loads(out)["errorCode"]), (2, "ERR-UNOBSERVABLE-SOURCE"))

    def test_untracked_file_over_the_size_bound_is_refused(self):
        fx = self.fx
        with mock.patch.object(ownership_cli, "MAX_FILE_BYTES", 8):
            fx.write(fx.repo, "big.txt", "x" * 64)
            code, out, _, target = fx.check(fx.declaration(), "--shared-tree", str(fx.repo))
        self.assertEqual((code, json.loads(out)["errorCode"]), (2, "ERR-OVER-BOUND"))
        self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()
