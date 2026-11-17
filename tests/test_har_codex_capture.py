# SPDX-License-Identifier: AGPL-3.0-only
"""Offline tests for scripts/har_codex_capture.py with a fake codex binary: no model, credential or network."""

from datetime import datetime, timezone
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

from scripts import har_codex_capture as capture

SECRET = "ASSISTANT-PRIVATE-TEXT"
EVENTS = [
    {"type": "thread.started", "thread_id": "0199-private-id"},
    {"type": "turn.started"},
    {"type": "item.completed", "item": {"id": "item_0", "type": "reasoning", "text": SECRET}},
    {"type": "item.started", "item": {"id": "item_1", "type": "command_execution", "command": "ls",
                                      "aggregated_output": "", "exit_code": None, "status": "in_progress"}},
    {"type": "item.completed", "item": {"id": "item_1", "type": "command_execution", "command": "ls",
                                        "aggregated_output": "README.txt\n" + SECRET, "exit_code": 0,
                                        "status": "completed"}},
    {"type": "item.completed", "item": {"id": "item_2", "type": "agent_message", "text": SECRET}},
    {"type": "turn.completed", "usage": {"input_tokens": 10, "cached_input_tokens": 0, "output_tokens": 2}},
]
FAKE = '''#!PYTHON
import json, os, sys, time
args = sys.argv[1:]
mode = os.environ.get("CODEX_HOME", "") + "/mode"
mode = open(mode).read().strip() if os.path.exists(mode) else "ok"
log = os.path.join(os.environ["CODEX_HOME"], "calls.log")
with open(log, "a") as f:
    f.write(json.dumps({"args": args, "env": sorted(os.environ)}) + "\\n")
if args == ["--version"]:
    print("not-codex" if mode == "badversion" else "codex-cli 0.169.0-alpha.11.1")
elif args == ["login", "status"]:
    print("Logged in using an API key" if mode == "apikey" else "Logged in using ChatGPT")
elif args[:1] == ["exec"]:
    if mode == "hang":
        time.sleep(30)
    for event in EVENTS:
        print(json.dumps(event))
    print("stderr " + "SECRET", file=sys.stderr)
    sys.exit(3 if mode == "fail" else 0)
'''


class CaptureTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name)
        self.codex = base / "bin" / "codex"
        self.codex.parent.mkdir()
        self.codex.write_text(FAKE.replace("EVENTS", repr(EVENTS)).replace("PYTHON", sys.executable))
        self.codex.chmod(0o755)
        self.auth = base / "auth"
        self.auth.mkdir(mode=0o700)
        (self.auth / "auth.json").write_text("{}")
        self.private, self.evidence = base / "private", base / "evidence"

    def tearDown(self):
        self.tmp.cleanup()

    def run_main(self, *argv):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = capture.main(list(argv), codex=self.codex, auth_dir=self.auth,
                                private_base=self.private, evidence_dir=self.evidence,
                                now=datetime(2026, 11, 17, tzinfo=timezone.utc))
        return code, out.getvalue(), err.getvalue()

    def calls(self):
        return [json.loads(line) for line in (self.auth / "calls.log").read_text().splitlines()]

    def mode(self, value):
        (self.auth / "mode").write_text(value)

    def test_dry_run_sends_no_prompt_and_writes_nothing(self):
        code, out, _ = self.run_main("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("no prompt was sent", out)
        self.assertEqual([c["args"] for c in self.calls()], [["--version"], ["login", "status"]])
        self.assertFalse(self.private.exists())
        self.assertFalse(self.evidence.exists())

    def test_capture_writes_redacted_summary_and_private_raw(self):
        code, out, _ = self.run_main()
        self.assertEqual(code, 0)
        execs = [c for c in self.calls() if c["args"][:1] == ["exec"]]
        self.assertEqual(len(execs), capture.RUNS)
        args = execs[0]["args"]
        for flag in ("--json", "--ephemeral", "--ignore-user-config", "--skip-git-repo-check"):
            self.assertIn(flag, args)
        self.assertEqual(args[args.index("-s") + 1], "read-only")
        env = [k for k in execs[0]["env"] if not k.startswith("__CF_")]  # added by macOS at exec
        self.assertEqual(env, ["CODEX_HOME", "HOME", "LANG", "NO_COLOR", "PATH", "TMPDIR"])
        [record_path] = list(self.evidence.iterdir())
        text = record_path.read_text()
        self.assertNotIn(SECRET, text)
        self.assertNotIn("0199-private-id", text)
        self.assertNotIn("README.txt\\n", text)
        record = json.loads(text)
        self.assertFalse(record["executionAuthorization"])
        self.assertEqual(record["binary"]["version"], "codex-cli 0.169.0-alpha.11.1")
        run = record["runs"][0]
        self.assertEqual(run["exit"], 0)
        self.assertEqual(run["events"]["item.completed/command_execution"], 1)
        self.assertEqual(run["adapterFit"]["hostTerminal"], "completed")
        self.assertEqual(run["adapterFit"]["errors"], [])
        self.assertNotIn("unknown", run["adapterFit"]["kinds"])
        self.assertIn({"count": 1, "shape": {"type": "=thread.started", "thread_id": "string"}},
                      run["shapes"])
        raw_dir = self.private / "20261117T000000Z"
        self.assertEqual(os.stat(raw_dir).st_mode & 0o777, 0o700)
        raw = (raw_dir / "run-0.jsonl").read_bytes()
        self.assertIn(SECRET.encode(), raw)
        self.assertEqual(run["stdoutSha256"], capture.hashlib.sha256(raw).hexdigest())
        self.assertIn("sha256 ", out)

    def test_failed_run_exits_two_but_keeps_record(self):
        self.mode("fail")
        code, _, _ = self.run_main()
        self.assertEqual(code, 2)
        [record_path] = list(self.evidence.iterdir())
        self.assertEqual(json.loads(record_path.read_text())["runs"][0]["exit"], 3)

    def test_timeout_kills_the_run(self):
        self.mode("hang")
        with mock.patch.object(capture, "RUN_TIMEOUT_SECONDS", 1), \
                mock.patch.object(capture, "RUNS", 1):
            code, _, _ = self.run_main()
        self.assertEqual(code, 2)
        [record_path] = list(self.evidence.iterdir())
        self.assertEqual(json.loads(record_path.read_text())["runs"][0]["exit"], "timeout")

    def assert_stops(self, reason):
        code, _, err = self.run_main()
        self.assertEqual(code, 1)
        self.assertIn(reason, err)
        self.assertFalse(self.evidence.exists())

    def test_api_key_login_refused(self):
        self.mode("apikey")
        self.assert_stops("not signed in with ChatGPT")

    def test_bad_version_refused(self):
        self.mode("badversion")
        self.assert_stops("did not report a codex-cli build")

    def test_missing_sign_in_refused(self):
        (self.auth / "auth.json").unlink()
        self.assert_stops("no sign-in")

    def test_open_auth_dir_refused(self):
        self.auth.chmod(0o755)
        self.assert_stops("mode 0700")

    def test_default_codex_home_refused(self):
        with mock.patch.object(capture.Path, "home", return_value=self.auth.parent):
            self.auth.rename(self.auth.parent / ".codex")
            self.auth = self.auth.parent / ".codex"
            self.assert_stops("never ~/.codex")

    def test_symlinked_binary_refused(self):
        link = self.codex.parent / "link"
        link.symlink_to(self.codex)
        self.codex = link
        self.assert_stops("not a link")

    def test_writable_binary_refused(self):
        self.codex.chmod(0o777)
        self.assert_stops("non-writable")

    def test_canonical_constants(self):
        self.assertEqual(str(capture.CODEX), "/Applications/ChatGPT.app/Contents/Resources/"
                         "codex-cli/CodexCLI.app/Contents/MacOS/codex")
        self.assertEqual(capture.AUTH_DIR, Path.home() / "agent-braid-auth" / "codex")
        self.assertNotIn(".codex", capture.AUTH_DIR.parts)


if __name__ == "__main__":
    unittest.main()
