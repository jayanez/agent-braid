# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-057 T021: the recovery and orphan report and the report-recovery command."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from jsonschema import Draft202012Validator

from agent_braid import ownership, ownership_cli
from agent_braid.path_overlap import paths_overlap
from tests.test_ownership_receipt import CONTRACTS, ERROR, GitFixture, git

SCHEMA = json.loads((CONTRACTS / "recovery-report.schema.json").read_text(encoding="utf-8"))
REPORT = Draft202012Validator(SCHEMA)
SESSION_NAME = "SESSION-NAME-refactor-the-billing-module"
WAITING = "WAITING-TEXT-needs-approval-for-deploy"


def session(cwd, state="stopped", kind="background", **extra):
    data = {"id": "s", "name": SESSION_NAME, "waitingFor": WAITING, "cwd": str(cwd), "state": state, "kind": kind}
    data.update(extra)
    return data


class RecoveryFixture(GitFixture):
    def report(self, *argv, listing=None, stdin=None):
        args = ["report-recovery", str(self.declaration()), "--repository", str(self.repo), *argv]
        if listing is not None:
            path = self.dir / "agents.json"
            path.write_text(listing if isinstance(listing, str) else json.dumps(listing))
            args += ["--agents-json", str(path)]
        status, out, err = self.run(*args)
        return status, out, err

    def unit(self, out, name):
        return next(u for u in json.loads(out)["units"] if u["id"] == name)


class RecoveryCommandTests(unittest.TestCase):
    def setUp(self):
        self.fx = RecoveryFixture(self)

    def ok(self, *argv, **kw):
        status, out, err = self.fx.report(*argv, **kw)
        self.assertEqual((status, err), (0, ""), out)
        report = json.loads(out)
        self.assertEqual([e.message[:100] for e in REPORT.iter_errors(report)], [])
        return report, out

    def of(self, report, name):
        return next(u for u in report["units"] if u["id"] == name)

    def test_untouched_dirty_and_published_worktrees(self):
        fx = self.fx
        wa, wb = fx.worktree("ua"), fx.worktree("ub")
        fx.write(wb, "src/b.py")
        report, _ = self.ok("--source", f"a=worktree:{wa}", "--source", f"b=worktree:{wb}")
        self.assertEqual(self.of(report, "a")["classification"], "untouched")
        self.assertNotIn("warnings", self.of(report, "a"))
        b = self.of(report, "b")
        self.assertEqual((b["classification"], b["warnings"]), ("dirty", ["worktree-has-uncommitted-work"]))
        fx.commit(wb)
        report, _ = self.ok("--source", f"b=worktree:{wb}")
        b = self.of(report, "b")
        self.assertEqual((b["classification"], b["warnings"]), ("dirty", ["unpublished-commits"]))
        git(fx.repo, "update-ref", "refs/remotes/origin/ub", git(wb, "rev-parse", "HEAD"))
        report, _ = self.ok("--source", f"b=worktree:{wb}")
        b = self.of(report, "b")
        self.assertEqual(b["classification"], "published")
        self.assertNotIn("warnings", b)

    def test_a_remote_ref_at_the_base_does_not_make_an_untouched_unit_published(self):
        fx = self.fx
        git(fx.repo, "update-ref", "refs/remotes/origin/main", fx.base)
        report, _ = self.ok("--source", f"a=worktree:{fx.worktree('ua')}")
        self.assertEqual(self.of(report, "a")["classification"], "untouched")

    def test_commit_sources_are_never_dirty_by_uncommitted_work(self):
        fx = self.fx
        wa = fx.worktree("ua")
        fx.write(wa, "src/a.py")
        fx.commit(wa)
        report, _ = self.ok("--source", "a=commit:ua")
        self.assertEqual(self.of(report, "a")["classification"], "dirty")
        self.assertEqual(self.of(report, "a")["warnings"], ["unpublished-commits"])

    def test_overlapping_units_are_conflicting_and_live_siblings_are_listed(self):
        fx = self.fx
        wa, wb, wc = fx.worktree("ua"), fx.worktree("ub"), fx.worktree("uc")
        for root in (wa, wb):
            fx.write(root, "src/a.py", f"{root.name}\n")
            fx.commit(root)
        listing = [session(wb, state="working", kind="interactive")]
        report, out = self.ok("--source", f"a=worktree:{wa}", "--source", f"b=worktree:{wb}", listing=listing)
        a, b = self.of(report, "a"), self.of(report, "b")
        self.assertEqual((a["classification"], b["classification"]), ("conflicting", "conflicting"))
        self.assertEqual(a["liveSiblingOverlap"], ["b"])
        self.assertNotIn("liveSiblingOverlap", b)
        self.assertEqual(b["session"], {"state": "working", "kind": "interactive"})
        self.assertEqual(a["session"], {"state": "unknown", "kind": "unknown"})

    def test_a_unit_without_a_source_or_with_a_bad_source_is_unknown_never_untouched(self):
        fx = self.fx
        report, _ = self.ok()
        self.assertEqual([(u["classification"], u["unknownReason"]) for u in report["units"]],
                         [("unknown", "no-source-supplied")] * 2)
        self.assertIs(report["inputs"]["git"]["observed"], False)
        report, _ = self.ok("--source", f"a=worktree:{fx.dir / 'nowhere'}", "--source", "b=commit:no-such-rev")
        self.assertEqual([u["unknownReason"] for u in report["units"]], ["unobservable", "unobservable"])
        fx.write(fx.repo, "src/a.py")
        fx.commit(fx.repo)
        git(fx.repo, "branch", "other", fx.base)
        git(fx.repo, "checkout", "-q", "--orphan", "island")
        fx.write(fx.repo, "z.txt")
        fx.commit(fx.repo)
        report, _ = self.ok("--source", "a=commit:island")
        self.assertEqual(self.of(report, "a")["unknownReason"], "not-a-descendant-of-base")

    def test_busy_and_unstable_sources_are_unknown_for_that_unit_only(self):
        fx = self.fx
        wa, wb = fx.worktree("ua"), fx.worktree("ub")
        lock = Path(git(wa, "rev-parse", "--absolute-git-dir")) / "index.lock"
        lock.write_text("")
        report, _ = self.ok("--source", f"a=worktree:{wa}", "--source", f"b=worktree:{wb}")
        self.assertEqual((self.of(report, "a")["unknownReason"], self.of(report, "b")["classification"]),
                         ("busy", "untouched"))
        lock.unlink()
        original, calls = ownership_cli._observe_once, []

        def drifting(*args, **kwargs):
            result = original(*args, **kwargs)
            calls.append(1)
            if len(calls) == 1:
                fx.write(wa, "src/a.py", "moved\n")
            return result

        with mock.patch.object(ownership_cli, "_observe_once", drifting):
            report, _ = self.ok("--source", f"a=worktree:{wa}")
        self.assertEqual(self.of(report, "a")["unknownReason"], "unstable")

    def test_uncommitted_work_that_agent_view_delete_would_discard_is_a_warning(self):
        fx = self.fx
        wa = fx.worktree("ua")
        fx.write(wa, "src/new.py")
        report, _ = self.ok("--source", f"a=worktree:{wa}", listing=[session(wa, state="stopped")])
        a = self.of(report, "a")
        self.assertEqual(a["warnings"], ["worktree-has-uncommitted-work", "agent-view-delete-discards-uncommitted-work"])
        self.assertEqual(a["session"]["state"], "stopped")
        report, _ = self.ok("--source", f"a=worktree:{wa}")
        self.assertEqual(self.of(report, "a")["warnings"], ["worktree-has-uncommitted-work"])

    def test_missing_or_drifted_fields_yield_unknown_naming_the_field(self):
        fx = self.fx
        wa, wb = fx.worktree("ua"), fx.worktree("ub")
        listing = [session(wa, state="napping"), {"cwd": str(wb), "state": "done"}, {"state": "done"}]
        report, _ = self.ok("--source", f"a=worktree:{wa}", "--source", f"b=worktree:{wb}", listing=listing)
        a, b = self.of(report, "a"), self.of(report, "b")
        self.assertEqual((a["classification"], a["unknownReason"], a["unknownFields"]), ("unknown", "field-drift", ["state"]))
        self.assertEqual((b["classification"], b["unknownFields"]), ("unknown", ["kind"]))
        self.assertEqual(report["inputs"]["agentsJson"]["driftedFields"], ["cwd", "kind", "state"])
        self.assertEqual(a["session"], {"state": "unknown", "kind": "background"})

    def test_two_sessions_in_one_worktree_leave_disagreeing_values_unknown(self):
        wa = self.fx.worktree("ua")
        report, _ = self.ok("--source", f"a=worktree:{wa}",
                            listing=[session(wa, state="working"), session(wa, state="done")])
        self.assertEqual(self.of(report, "a")["session"], {"state": "unknown", "kind": "background"})

    def test_input_refusals_have_a_code_and_no_report(self):
        wa = self.fx.worktree("ua")
        src = ["--source", f"a=worktree:{wa}"]
        cases = (
            ("not json", "{nope", "ERR-MALFORMED-INPUT"), ("not a list", '{"agents": []}', "ERR-MALFORMED-INPUT"),
            ("duplicate key", '[{"cwd":"a","cwd":"b"}]', "ERR-MALFORMED-INPUT"), ("bad utf-8", "\udcff", "ERR-MALFORMED-INPUT"),
            ("too many sessions", json.dumps([{}] * (ownership.MAX_SESSIONS + 1)), "ERR-OVER-BOUND"),
            ("oversized", " " * (ownership.MAX_AGENTS_BYTES + 1), "ERR-OVER-BOUND"),
        )
        for label, text, code in cases:
            with self.subTest(label):
                path = self.fx.dir / "agents.json"
                path.write_bytes(text.encode("utf-8", "surrogateescape"))
                status, out, _ = self.fx.run("report-recovery", str(self.fx.declaration()), "--repository",
                                             str(self.fx.repo), *src, "--agents-json", str(path))
                error = json.loads(out)
                self.assertEqual((status, error["errorCode"], list(ERROR.iter_errors(error))), (2, code, []))
                self.assertNotIn("units", error)
        status, out, _ = self.fx.run("report-recovery", str(self.fx.declaration()), "--repository", str(self.fx.repo),
                                     "--agents-json", str(self.fx.dir / "absent.json"))
        self.assertEqual((status, json.loads(out)["errorCode"]), (2, "ERR-UNOBSERVABLE-SOURCE"))

    def test_declaration_and_source_refusals(self):
        fx = self.fx
        bad = fx.dir / "bad.json"
        bad.write_text("{")
        nobase = fx.dir / "nobase.json"
        nobase.write_text(json.dumps({"schemaVersion": ownership.SCHEMA_VERSION, "units": [
            {"id": "a", "surface": "batch", "reads": [], "writes": []}, {"id": "b", "surface": "batch", "reads": [], "writes": []}]}))
        for argv, code in (
            ([str(bad), "--repository", str(fx.repo)], "ERR-MALFORMED-INPUT"),
            ([str(nobase), "--repository", str(fx.repo)], "ERR-MALFORMED-INPUT"),
            ([str(fx.declaration()), "--repository", str(fx.repo), "--source", "zzz"], "ERR-MALFORMED-INPUT"),
            ([str(fx.declaration()), "--repository", str(fx.repo), "--source", "q=commit:x"], "ERR-MALFORMED-INPUT"),
            ([str(fx.declaration()), "--repository", str(fx.dir / "nowhere")], "ERR-UNOBSERVABLE-SOURCE"),
        ):
            status, out, _ = fx.run("report-recovery", *argv)
            self.assertEqual((status, json.loads(out)["errorCode"]), (2, code), argv)

    def test_standard_input_listing(self):
        wa = self.fx.worktree("ua")
        text = json.dumps([session(wa, state="failed")])
        stdin = mock.Mock(buffer=mock.Mock(read=lambda n: text.encode()))
        with mock.patch("sys.stdin", stdin):
            status, out, _ = self.fx.run("report-recovery", str(self.fx.declaration()), "--repository",
                                         str(self.fx.repo), "--source", f"a=worktree:{wa}", "--agents-json", "-")
        report = json.loads(out)
        self.assertEqual((status, self.of(report, "a")["session"]["state"]), (0, "failed"))
        self.assertEqual(report["inputs"]["agentsJson"]["sha256"], "sha256:" + __import__("hashlib").sha256(text.encode()).hexdigest())

    def test_no_session_text_or_directory_is_persisted_and_only_git_is_launched(self):
        fx = self.fx
        wa = fx.worktree("ua")
        fx.write(wa, "src/a.py")
        launched, real = [], subprocess.Popen

        def spy(argv, *args, **kwargs):
            launched.append(os.path.basename(argv[0]))
            return real(argv, *args, **kwargs)

        before = git(fx.repo, "status", "--porcelain")
        with mock.patch("subprocess.Popen", spy), mock.patch("subprocess.run", side_effect=AssertionError):
            report, out = self.ok("--source", f"a=worktree:{wa}", listing=[session(wa)])
        for forbidden in (SESSION_NAME, WAITING, str(wa), str(fx.repo)):
            self.assertNotIn(forbidden, out)
        self.assertEqual(report["actionsTaken"], [])
        self.assertIs(report["executionAuthorization"], False)
        self.assertEqual(set(launched), {"git"})
        self.assertEqual(git(fx.repo, "status", "--porcelain"), before)
        self.assertEqual(list(fx.out.iterdir()), [])


class PureReportTests(unittest.TestCase):
    def test_schema_rejects_actions_and_unlisted_members(self):
        report = {"schemaVersion": ownership.RECOVERY_VERSION, "executionAuthorization": False, "actionsTaken": [],
                  "assurance": dict(ownership.RECOVERY_ASSURANCE), "inputs": {"agentsJson": {"provided": False},
                  "git": {"observed": False}}, "units": [], "limits": list(ownership.RECOVERY_LIMITS)}
        self.assertEqual(list(REPORT.iter_errors(report)), [])
        for mutation in ({"actionsTaken": ["delete"]}, {"executionAuthorization": True}, {"name": "x"},
                         {"units": [{"id": "a", "classification": "unknown", "session": {"state": "x", "kind": "unknown"}}]},
                         {"units": [{"id": "a", "classification": "unknown", "session": {"state": "done", "kind": "unknown"},
                                     "cwd": "/x"}]}):
            self.assertTrue(list(REPORT.iter_errors({**report, **mutation})), mutation)

    def test_schema_enumerations_equal_the_module_constants(self):
        unit = SCHEMA["properties"]["units"]["items"]["properties"]
        self.assertEqual(tuple(unit["classification"]["enum"]), ownership.CLASSIFICATIONS)
        self.assertEqual(tuple(unit["unknownReason"]["enum"]), ownership.UNKNOWN_UNIT_REASONS)
        self.assertEqual(tuple(unit["session"]["properties"]["state"]["enum"]), (*ownership.SESSION_STATES, "unknown"))
        self.assertEqual(tuple(unit["session"]["properties"]["kind"]["enum"]), (*ownership.SESSION_KINDS, "unknown"))
        self.assertEqual(set(unit["unknownFields"]["items"]["enum"]), {"cwd", "kind", "state"})

    def test_limits_are_within_the_schema_and_use_no_instruction_wording(self):
        self.assertEqual(ownership.lint_text(" ".join(ownership.RECOVERY_LIMITS)), [])

    def test_overlap_agrees_with_the_shared_prefix_rule(self):
        paths = ["a", "a/b", "a/b/c", "a/bc", "ab", "b", "A/B"]
        for left in paths:
            for right in paths:
                self.assertEqual(ownership.changes_overlap([left], [right]),
                                 paths_overlap(ownership.fold(left), ownership.fold(right)), (left, right))

    def test_parse_names_only_closed_fields(self):
        listing = ownership.parse_agents_listing(json.dumps([{"cwd": "/a", "state": SESSION_NAME, "kind": 5, SESSION_NAME: 1}]).encode())
        self.assertEqual(listing.drifted, ("kind", "state"))
        self.assertTrue(set(listing.drifted) <= set(ownership.AGENTS_FIELDS))
        self.assertNotIn(SESSION_NAME, json.dumps(listing.drifted))
        self.assertEqual(ownership.parse_agents_listing(b"[]").sessions, ())

    def test_module_does_not_execute_or_write(self):
        tree = ast.parse(Path(ownership_cli.__file__).read_text(encoding="utf-8"))
        calls = {n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)}
        self.assertEqual(calls & {"system", "popen", "Popen", "run", "unlink", "rmtree", "mkdir", "write_text", "write_bytes"}, set())
        imports = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
        self.assertNotIn("subprocess", imports)


if __name__ == "__main__":
    unittest.main()
