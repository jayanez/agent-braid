# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-057 T020: the isolation and base audit and the audit-isolation command."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import unittest
from unittest import mock

from agent_braid import ownership
from tests.test_ownership_receipt import ERROR, GitFixture, git

ENV_VALUE = "ENV-VALUE-7c1e-seeded"
TOKEN = "ghp_SeededTokenValue0123456789abcdef"
HOOK = "curl https://example.invalid/hook"
SESSION_NAME = "SESSION-NAME-refactor-the-billing-module"
WAITING = "WAITING-TEXT-needs-approval-for-deploy"
SEEDS = (ENV_VALUE, TOKEN, HOOK, SESSION_NAME, WAITING)
VERDICT_WORDS = ("safe", "unsafe", "isolated", "clean", "ok", "fine", "dangerous", "risky")


def settings_text(**worktree) -> str:
    return json.dumps({"env": {"API": ENV_VALUE}, "apiKey": TOKEN, "hooks": {"Stop": [{"command": HOOK}]},
                       "worktree": worktree})


def listing_text(*cwds: str) -> str:
    return json.dumps([{"id": f"s{i}", "name": SESSION_NAME, "waitingFor": WAITING, "cwd": cwd, "state": "working",
                        "kind": "background", "pid": 1} for i, cwd in enumerate(cwds)])


def strings(value):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for key, item in value.items():
            yield key
            yield from strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from strings(item)


def observation(report, name, source=None):
    return next(o for o in report["observations"]
                if o["observation"] == name and (source is None or o["source"] == source))


class AuditCommandTests(unittest.TestCase):
    def setUp(self):
        self.fx = GitFixture(self)

    def run_audit(self, *extra, cwd=None, stdin=None):
        argv = ["audit-isolation", "--repository", str(self.fx.repo), *extra]
        with contextlib.ExitStack() as stack:
            if cwd:
                stack.enter_context(contextlib.chdir(cwd))
            if stdin is not None:
                stack.enter_context(mock.patch("sys.stdin", mock.Mock(buffer=mock.Mock(read=lambda n: stdin.encode()))))
            status, out, err = self.fx.run(*argv)
        return status, out, err

    def audit(self, *extra, **kw):
        status, out, err = self.run_audit(*extra, **kw)
        self.assertEqual((status, err), (0, ""), out)
        return json.loads(out), out

    def write(self, name, text):
        path = self.fx.dir / name
        path.write_text(text)
        return str(path)

    def test_report_shape_class_and_no_authorization(self):
        report, _ = self.audit()
        self.assertEqual(report["schemaVersion"], ownership.AUDIT_VERSION)
        self.assertIs(report["executionAuthorization"], False)
        self.assertEqual(report["assurance"]["compatibilityClass"], "0-heuristic")
        self.assertIs(report["assurance"]["notAGuarantee"], True)
        for item in report["observations"]:
            self.assertIn(item["outcome"], ("observed", "unknown"))
            self.assertTrue(item["source"])

    def test_linked_worktrees_and_current_directory(self):
        wa, _ = self.fx.worktree("ua"), self.fx.worktree("ub")
        for cwd, expected in ((self.fx.repo, "main-worktree"), (wa, "linked-worktree"), (self.fx.dir, "outside-repository")):
            with self.subTest(cwd=expected):
                layout = observation(self.audit(cwd=cwd)[0], "working-tree-layout")
                self.assertEqual((layout["worktrees"], layout["currentDirectory"]), (3, expected))
                self.assertIn(expected, ownership.CWD_LOCATIONS)

    def test_local_head_ahead_of_origin_default_branch(self):
        fx = self.fx
        git(fx.repo, "update-ref", "refs/remotes/origin/main", fx.base)
        git(fx.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/main")
        head = observation(self.audit()[0], "local-head-against-origin-default")
        self.assertEqual((head["commitsAhead"], head["originDefaultMissesLocalCommits"]), (0, False))
        fx.write(fx.repo, "src/a.py")
        fx.commit(fx.repo)
        head = observation(self.audit()[0], "local-head-against-origin-default")
        self.assertEqual((head["commitsAhead"], head["originDefaultMissesLocalCommits"]), (1, True))

    def test_unknown_origin_default_and_unobservable_repository(self):
        self.assertEqual(observation(self.audit()[0], "local-head-against-origin-default")["outcome"], "unknown")
        status, out, _ = self.fx.run("audit-isolation", "--repository", str(self.fx.dir / "nowhere"))
        report = json.loads(out)
        self.assertEqual(status, 0)
        self.assertEqual({o["outcome"] for o in report["observations"] if o["source"].startswith("git")}, {"unknown"})

    def test_settings_absent_head_and_unreadable(self):
        absent = self.write("absent.json", settings_text())
        head = self.write("head.json", settings_text(baseRef="head", bgIsolation="none"))
        report, _ = self.audit("--settings", f"user={absent}", "--settings", f"project={head}",
                               "--settings", f"local={self.fx.dir / 'missing.json'}")
        value = lambda key, scope: next(o for o in report["observations"]
                                         if o["observation"] == f"setting:{key}" and o["source"] == f"settings-file:{scope}")
        self.assertEqual(value("worktree.baseRef", "user")["value"], "unset")
        self.assertEqual(value("worktree.baseRef", "project")["value"], "head")
        self.assertEqual(value("worktree.bgIsolation", "project")["value"], "none")
        self.assertEqual(value("worktree.baseRef", "local")["outcome"], "unknown")
        self.assertNotIn("value", value("worktree.baseRef", "local"))

    def test_no_settings_file_supplied_is_unknown(self):
        report, _ = self.audit()
        self.assertEqual([o["outcome"] for o in report["observations"] if o["observation"].startswith("setting:")],
                         ["unknown", "unknown"])

    def test_bad_or_repeated_settings_scope_is_refused(self):
        path = self.write("s.json", settings_text())
        for value in (f"team={path}", f"user={path}", "user="):
            args = ["--settings", f"user={path}", "--settings", value] if value == f"user={path}" else ["--settings", value]
            with self.subTest(value=value[:5]):
                status, out, _ = self.run_audit(*args)
                self.assertEqual((status, json.loads(out)["errorCode"]), (2, "ERR-MALFORMED-INPUT"))

    def test_only_the_closed_key_list_is_read_and_nothing_seeded_leaks(self):
        self.assertEqual(ownership.SETTINGS_KEYS, ("worktree.baseRef", "worktree.bgIsolation"))
        found = ownership.read_settings(settings_text(baseRef="head", bgIsolation="none", other="x").encode())
        self.assertEqual(set(found), set(ownership.SETTINGS_KEYS))
        self.assertEqual(ownership.read_settings(settings_text(baseRef=TOKEN).encode())["worktree.baseRef"],
                         ownership.UNRECOGNISED)
        self.assertEqual(ownership.read_settings(settings_text(baseRef={"env": ENV_VALUE}).encode())["worktree.baseRef"],
                         ownership.UNRECOGNISED)
        for raw in (b"{", b"[]", b'{"a":1,"a":2}', b"\xff", None, b" " * (ownership.MAX_SETTINGS_BYTES + 1)):
            self.assertIsNone(ownership.read_settings(raw))
        mixed = self.write("mixed.json", settings_text(baseRef="head"))
        listing = self.write("agents.json", listing_text("/work/one", "/work/one"))
        script = self.write("script.js", f"agent('{ENV_VALUE}')")
        with mock.patch("sys.stderr") as stderr:
            report, out = self.audit("--settings", f"user={mixed}", "--agents-json", listing, "--script", script)
        logged = "".join(str(call) for call in stderr.mock_calls)
        for seed in SEEDS:
            self.assertNotIn(seed, out + logged)

    def test_session_listing_yields_counts_and_never_text_or_directories(self):
        fx = self.fx
        wa = fx.worktree("ua")
        listing = self.write("agents.json", listing_text(str(fx.repo), str(fx.repo), str(wa), "/elsewhere/x"))
        report, out = self.audit("--agents-json", listing)
        counts = observation(report, "session-working-directories", "agents-json")
        self.assertEqual({k: v for k, v in counts.items() if isinstance(v, int)}, {
            "sessions": 4, "sessionsWithoutDirectory": 0, "distinctDirectories": 3, "sessionsSharingADirectory": 2,
            "sessionsInRepositoryRoot": 2, "sessionsInLinkedWorktrees": 1})
        for forbidden in (SESSION_NAME, WAITING, str(fx.repo), str(wa), "/elsewhere"):
            self.assertNotIn(forbidden, out)

    def test_symlinked_session_directory_matches_and_unobserved_git_leaves_counts_unknown(self):
        link = self.fx.dir / "link"
        link.symlink_to(self.fx.repo)
        report, _ = self.audit("--agents-json", self.write("a.json", listing_text(str(link))))
        self.assertEqual(observation(report, "session-working-directories")["sessionsInRepositoryRoot"], 1)
        status, out, _ = self.fx.run("audit-isolation", "--repository", str(self.fx.dir / "nowhere"),
                                     "--agents-json", self.write("b.json", listing_text("/a")))
        counts = observation(json.loads(out), "session-working-directories")
        self.assertEqual((counts["sessionsInRepositoryRoot"], counts["sessionsInLinkedWorktrees"]), ("unknown", "unknown"))

    def test_a_dangling_origin_default_keeps_the_layout_observation(self):
        git(self.fx.repo, "symbolic-ref", "refs/remotes/origin/HEAD", "refs/remotes/origin/gone")
        report, _ = self.audit()
        self.assertEqual(observation(report, "working-tree-layout")["outcome"], "observed")
        self.assertEqual(observation(report, "local-head-against-origin-default")["outcome"], "unknown")

    def test_agents_listing_from_standard_input(self):
        report, _ = self.audit("--agents-json", "-", stdin=listing_text("/a", "/a", "/b"))
        self.assertEqual(observation(report, "session-working-directories")["sessionsSharingADirectory"], 2)

    def test_listing_refusals_and_drift(self):
        for label, text, code in (
            ("not json", "{nope", "ERR-MALFORMED-INPUT"), ("not a list", "{}", "ERR-MALFORMED-INPUT"),
            ("not objects", "[1]", "ERR-MALFORMED-INPUT"), ("duplicate key", '[{"cwd":"a","cwd":"b"}]', "ERR-MALFORMED-INPUT"),
            ("too many", json.dumps([{}] * (ownership.MAX_SESSIONS + 1)), "ERR-OVER-BOUND"),
            ("too large", " " * (ownership.MAX_AGENTS_BYTES + 1), "ERR-OVER-BOUND"),
        ):
            with self.subTest(label):
                status, out, _ = self.run_audit("--agents-json", self.write("l.json", text))
                error = json.loads(out)
                self.assertEqual((status, error["errorCode"], list(ERROR.iter_errors(error))), (2, code, []))
        status, out, _ = self.run_audit("--agents-json", str(self.fx.dir / "absent.json"))
        self.assertEqual(json.loads(out)["errorCode"], "ERR-UNOBSERVABLE-SOURCE")
        report, _ = self.audit("--agents-json", self.write("d.json", json.dumps([{"state": "napping"}, {"cwd": "/a", "kind": "x"}])))
        counts = observation(report, "session-working-directories")
        self.assertEqual((counts["sessions"], counts["sessionsWithoutDirectory"], counts["unreadableFields"]),
                         (2, 1, ["cwd", "kind", "state"]))

    def test_script_lint_with_and_without_the_isolation_option(self):
        lint = ownership.lint_agent_isolation
        cases = (
            ("agent('a', {isolation: \"worktree\"})", (1, 0, 0)),
            ("agent('a', {isolation: 'worktree', prompt: f(x)})", (1, 0, 0)),
            ("agent('a', {prompt: 'isolation: \"worktree\"'})", (1, 1, 0)),
            ("agent('a')\nagent('b', {isolation: 'worktree'})\nagent ( 'c' )", (3, 2, 0)),
            ("agent('a', {prompt: ')'})", (1, 1, 0)),
            ("agent('unterminated", (1, 0, 1)),
            ("subagent_run(); plain()", (0, 0, 0)),
        )
        for text, (calls, without, unparsed) in cases:
            with self.subTest(text=text):
                got = lint(text)
                self.assertEqual((got["agentCalls"], got["callsWithoutWorktreeIsolation"], got["unparsedCalls"]),
                                 (calls, without, unparsed))
        report, _ = self.audit("--script", self.write("w.js", "agent('a')\nagent('b', {isolation: 'worktree'})"))
        item = observation(report, "agent-isolation-option", "script-text")
        self.assertEqual((item["label"], item["agentCalls"], item["callsWithoutWorktreeIsolation"]), ("inferred", 2, 1))
        self.assertEqual([o["observation"] for o in self.audit()[0]["observations"]].count("agent-isolation-option"), 0)
        status, out, _ = self.run_audit("--script", str(self.fx.dir / "absent.js"))
        self.assertEqual((status, json.loads(out)["errorCode"]), (2, "ERR-UNOBSERVABLE-SOURCE"))

    def test_no_verdict_wording_and_instruction_lint(self):
        listing = self.write("a.json", listing_text("/a", "/a"))
        report, _ = self.audit("--agents-json", listing, "--script", self.write("w.js", "agent('a')"),
                               "--settings", f"user={self.write('s.json', settings_text(baseRef='head'))}")
        text = " ".join(strings(report)).lower()
        self.assertEqual(ownership.lint_text(text), [])
        for word in VERDICT_WORDS:
            self.assertNotRegex(text, rf"\b{word}\b")

    def test_every_observation_names_its_source(self):
        report, _ = self.audit("--agents-json", self.write("a.json", listing_text("/a")), "--script", self.write("w.js", ""))
        self.assertTrue(report["observations"])
        self.assertTrue(all(isinstance(o["source"], str) and o["source"] for o in report["observations"]))

    def test_only_git_is_ever_launched_and_nothing_is_written(self):
        launched = []
        real = subprocess.Popen

        def spy(argv, *args, **kwargs):
            launched.append(os.path.basename(argv[0]))
            return real(argv, *args, **kwargs)

        before = git(self.fx.repo, "status", "--porcelain")
        with mock.patch("subprocess.Popen", spy), mock.patch("subprocess.run", side_effect=AssertionError):
            self.audit("--agents-json", self.write("a.json", listing_text("/a")))
        self.assertTrue(launched)
        self.assertEqual(set(launched), {"git"})
        self.assertEqual(git(self.fx.repo, "status", "--porcelain"), before)
        self.assertEqual(list(self.fx.out.iterdir()), [])


if __name__ == "__main__":
    unittest.main()
