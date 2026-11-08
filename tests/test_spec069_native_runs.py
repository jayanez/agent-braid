# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 T013 (procedure_013): the native-run driver, self-tested end to end against the fake hosts.

Every test runs the real pipeline (profiles, sandbox probe, plugin install, workspace registration,
headless runs, parsing, scoring, redaction, secret scan, teardown) with the executables in
``tests/fixtures/spec069-fake-hosts``. The evidence proves the pipeline, not any host or model.
"""

from __future__ import annotations

import atexit
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from scripts import spec069_native_runs as driver

PLANTED_KEY = "sk-ant-api03-PLANTEDKEYFORTEST0123456789abcdef"
FAKE_HOSTS = driver.FAKE_HOSTS_DIR


def scratch(prefix: str) -> str:
    path = tempfile.mkdtemp(prefix=prefix)
    atexit.register(shutil.rmtree, path, ignore_errors=True)
    return path


def run_driver(*extra: str, key: str | None = PLANTED_KEY, env: dict[str, str] | None = None) -> tuple[int, dict, Path]:
    """Run the driver in-process; return its exit code, the evidence it wrote and the output directory."""
    tmp = Path(scratch("t013-test-"))
    output = tmp / "native-runs.json"
    environ = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "OPENAI_API_KEY", "CODEX_API_KEY")}
    if key:
        environ["ANTHROPIC_API_KEY"] = key
    environ.update(env or {})
    out = io.StringIO()
    with mock.patch.dict(os.environ, environ, clear=True), contextlib.redirect_stdout(out):
        code = driver.main(["--fake-hosts", "--output", str(output), *extra])
    evidence = json.loads(output.read_text()) if output.exists() else {}
    return code, evidence, tmp


def leftover_profiles() -> list[Path]:
    return [p for p in Path(tempfile.gettempdir()).glob("spec069-*") if p.is_dir()]


class PipelineTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.before = set(leftover_profiles())
        cls.code, cls.evidence, cls.tmp = run_driver("--repetitions", "1")

    def test_completes_unattended_for_every_host_and_is_labelled_pipeline_only(self) -> None:
        self.assertEqual(self.code, 0)
        self.assertEqual(self.evidence["label"], "pipeline-only")
        self.assertIn("PIPELINE ONLY", self.evidence["note"])
        self.assertEqual({h: v["status"] for h, v in self.evidence["hosts"].items()},
                         {"claude-code": "ran", "codex": "ran", "opencode": "ran"})
        self.assertEqual(self.evidence["summary"]["overall"], "meets")

    def test_transcripts_exist_with_matching_hashes(self) -> None:
        for host in self.evidence["hosts"].values():
            self.assertTrue(host["runs"])
            for run in host["runs"]:
                file = self.tmp / run["transcript"]["file"]
                self.assertEqual(driver.sha256_file(file), run["transcript"]["sha256"])
        self.assertEqual(self.evidence["promptSet"]["sha256"], driver.sha256_file(driver.SPEC_DIR / "prompts/development.json"))

    def test_only_agent_braid_tools_are_used_and_only_analyze_work_counts(self) -> None:
        for host in self.evidence["hosts"].values():
            for run in host["runs"]:
                self.assertEqual({c["class"] for c in run["toolCalls"]}, {"agent-braid"})
                self.assertEqual(len(run["attempts"]), 1)  # the workspaces call is not an attempt

    def test_isolation_probe_and_canary_are_recorded(self) -> None:
        for host in self.evidence["hosts"].values():
            self.assertTrue(host["probe"]["canaryReadThroughRedirectedHome"])
            if host["probe"]["sandbox"] == "sandbox-exec":
                self.assertTrue(host["probe"]["enforced"])
                self.assertTrue(all(item["denied"] for item in host["probe"]["deniedPaths"]))

    def test_teardown_leaves_no_profile_or_process(self) -> None:
        self.assertEqual(self.evidence["teardown"], {"clean": True, "leftoverProcesses": 0, "profileRemoved": True})
        self.assertEqual(set(leftover_profiles()) - self.before, set())

    def test_evidence_lists_the_manual_steps(self) -> None:
        reasons = [m["reason"] for m in self.evidence["manualSteps"]]
        self.assertTrue(all(reasons))
        self.assertTrue(any("D13" in r for r in reasons))

    def test_no_key_value_in_evidence(self) -> None:
        self.assertNotIn(PLANTED_KEY, (self.tmp / "native-runs.json").read_text())


class NegativeControlTests(unittest.TestCase):
    def test_leaked_real_path_is_stopped_before_any_host_runs(self) -> None:
        home = Path(scratch("t013-home-"))
        (home / ".claude").mkdir()
        log = Path(scratch("t013-log-")) / "invocations.jsonl"
        code, evidence, _ = run_driver("--real-home", str(home), "--extra-env", f"CLAUDE_CONFIG_DIR={home}/.claude",
                                       env={"FAKE_LOG": str(log)})
        self.assertEqual(code, driver.EXIT_SAFETY)
        self.assertIn("real configuration path", evidence["stopped"])
        self.assertFalse(log.exists(), "no host executable may have been started")
        self.assertEqual(evidence["hosts"], {})

    def test_planted_secret_is_absent_from_evidence_and_transcripts(self) -> None:
        code, evidence, tmp = run_driver("--fake-variant", "leak-secret", "--limit-cases", "2")
        self.assertEqual(code, 0)
        marker = "sk-ant-PLANTED-" + driver.sha256_bytes(b"planted")[:24]
        files = [tmp / "native-runs.json", *tmp.rglob("*.jsonl")]
        self.assertGreater(len(files), 3)
        for file in files:
            text = file.read_text()
            self.assertNotIn(marker, text)
            self.assertNotIn(PLANTED_KEY, text)
        self.assertTrue(any("[REDACTED]" in f.read_text() for f in tmp.rglob("*.jsonl")))

    def test_secret_scan_refuses_to_write(self) -> None:
        secrets = driver.Secrets(["super-secret-value-123"])
        with self.assertRaises(driver.SecretLeak):
            secrets.assert_clean("x", "contains super-secret-value-123 here")
        with self.assertRaises(driver.SecretLeak):
            secrets.assert_clean("x", "key sk-ant-abcdefghijklmnop")
        out = Path(scratch("t013-misc-")) / "e.json"
        with self.assertRaises(driver.SecretLeak):
            driver.write_evidence(out, {"leak": "super-secret-value-123"}, secrets)
        self.assertFalse(out.exists())

    def test_denied_tool_is_refused_and_recorded(self) -> None:
        code, evidence, _ = run_driver("--fake-variant", "denied-tool", "--limit-cases", "2")
        self.assertEqual(code, 0)
        for host in evidence["hosts"].values():
            first = host["runs"][0]
            self.assertEqual([d["outcome"] for d in first["deniedToolRequests"]], ["refused"])
            self.assertTrue(first["score"]["validFirstAttempt"])

    def test_denied_tool_that_runs_stops_the_run(self) -> None:
        code, evidence, _ = run_driver("--fake-variant", "executed-tool", "--limit-cases", "2")
        self.assertEqual(code, driver.EXIT_SAFETY)
        self.assertIn("a denied tool ran", evidence["stopped"])

    def test_leftover_process_is_detected_then_removed(self) -> None:
        code, evidence, _ = run_driver("--fake-variant", "straggler", "--hosts", "claude-code", "--limit-cases", "1")
        self.assertEqual(code, driver.EXIT_TEARDOWN)
        self.assertFalse(evidence["teardown"]["clean"])
        self.assertGreaterEqual(evidence["teardown"]["leftoverProcesses"], 1)
        rows = subprocess.run(["ps", "-axo", "command="], capture_output=True, text=True).stdout
        # whole lines: an unrelated process such as "sleep 3000" must not fail this check
        self.assertNotIn("sleep 300", [line.strip() for line in rows.splitlines()])

    def test_leftover_profile_is_detected(self) -> None:
        profile = driver.Profile()
        (profile.root / "stray").write_text("x")
        profile.groups.clear()
        with mock.patch.object(driver.shutil, "rmtree", lambda *a, **k: None):
            result = profile.teardown()
        self.assertFalse(result["clean"])
        self.assertFalse(result["profileRemoved"])
        profile.verify()  # last-resort removal
        self.assertFalse(profile.root.exists())

    def test_retry_is_scored_within_retry_not_first_attempt(self) -> None:
        code, evidence, _ = run_driver("--fake-variant", "retry", "--hosts", "opencode")
        self.assertEqual(code, 0)
        runs = evidence["hosts"]["opencode"]["runs"]
        retried = [r for r in runs if len(r["attempts"]) == 2]
        self.assertTrue(retried)
        self.assertTrue(all(not r["score"]["validFirstAttempt"] and r["score"]["validWithinRetry"] for r in retried))
        self.assertEqual(evidence["summary"]["overall"], "negative-result")  # 4 of 10 prompts missed the first attempt


class DeclaredLimitTests(unittest.TestCase):
    def test_missing_key_is_a_declared_limit_and_never_prompts(self) -> None:
        tmp = Path(scratch("t013-test-"))
        plugin = driver.fake_plugin(tmp)
        out = tmp / "e.json"
        with mock.patch.dict(os.environ, {"PATH": os.environ["PATH"]}, clear=True), contextlib.redirect_stdout(io.StringIO()):
            code = driver.main(["--hosts", "claude-code,codex", "--claude-bin", str(FAKE_HOSTS / "claude"),
                                "--codex-bin", str(FAKE_HOSTS / "codex"), "--plugin-dir", str(plugin), "--output", str(out)])
        evidence = json.loads(out.read_text())
        self.assertEqual(code, 0)
        self.assertEqual(evidence["label"], "host-run")
        for host in evidence["hosts"].values():
            self.assertEqual(host["status"], "declared-limit")
            self.assertIn("environment", host["limit"])
        self.assertEqual(evidence["summary"]["overall"], "inconclusive")

    def test_missing_binary_is_a_declared_limit(self) -> None:
        tmp = Path(scratch("t013-test-"))
        plugin = driver.fake_plugin(tmp)
        out = tmp / "e.json"
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": PLANTED_KEY}, clear=True), contextlib.redirect_stdout(io.StringIO()):
            driver.main(["--hosts", "codex", "--codex-bin", str(tmp / "absent"), "--plugin-dir", str(plugin), "--output", str(out)])
        self.assertEqual(json.loads(out.read_text())["hosts"]["codex"]["status"], "declared-limit")

    def test_opencode_without_a_pinned_model_is_a_declared_limit(self) -> None:
        tmp = Path(scratch("t013-test-"))
        plugin = driver.fake_plugin(tmp)
        out = tmp / "e.json"
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": PLANTED_KEY}, clear=True), contextlib.redirect_stdout(io.StringIO()):
            driver.main(["--hosts", "opencode", "--opencode-bin", str(FAKE_HOSTS / "opencode"), "--plugin-dir", str(plugin),
                         "--output", str(out)])
        self.assertIn("free hosted model", json.loads(out.read_text())["hosts"]["opencode"]["limit"])


class HostFailureTests(unittest.TestCase):
    def test_host_that_fails_before_answering_is_a_declared_limit_not_a_negative_result(self) -> None:
        tmp = Path(scratch("t013-test-"))
        failing = tmp / "claude"
        failing.write_text("#!/bin/sh\n[ \"$1\" = --version ] && { echo 'claude 0.0.0-failing'; exit 0; }\n"
                           "echo 'Invalid API key' >&2; exit 1\n")
        failing.chmod(0o755)
        plugin = driver.fake_plugin(tmp)
        out = tmp / "e.json"
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": PLANTED_KEY, "PATH": os.environ["PATH"]}, clear=True), \
                contextlib.redirect_stdout(io.StringIO()):
            driver.main(["--hosts", "claude-code", "--claude-bin", str(failing), "--plugin-dir", str(plugin), "--output", str(out),
                         "--no-os-sandbox"])
        host = json.loads(out.read_text())["hosts"]["claude-code"]
        self.assertEqual(host["status"], "declared-limit")
        self.assertIn("failed before the model answered", host["limit"])


class UnitTests(unittest.TestCase):
    def test_guard_leaks_checks_environment_and_arguments(self) -> None:
        protected = [Path("/home/u/.claude")]
        driver.guard_leaks("x", {"HOME": "/tmp/p"}, ["a"], protected)
        with self.assertRaises(driver.SafetyStop):
            driver.guard_leaks("x", {"CLAUDE_CONFIG_DIR": "/home/u/.claude"}, [], protected)
        with self.assertRaises(driver.SafetyStop):
            driver.guard_leaks("x", {}, ["--add-dir", "/home/u/.claude/projects"], protected)

    def test_opencode_never_uses_the_background_service(self) -> None:
        args = driver.parse_args([])
        host = driver.HostConfig("opencode", Path("/bin/oc"), *driver.KEY_SPECS["opencode"], model="anthropic/m")
        argv = driver.prompt_argv(host, "p", args)
        self.assertIn("--standalone", argv)
        self.assertEqual(argv[-1], "p")

    def test_codex_key_is_injected_as_codex_api_key(self) -> None:
        self.assertEqual(driver.KEY_SPECS["codex"], (("CODEX_API_KEY", "OPENAI_API_KEY"), "CODEX_API_KEY"))

    def test_parsers_extract_ordered_attempts_and_skip_other_plugin_tools(self) -> None:
        refused = json.dumps({"operation": "analyze-work", "status": "refused", "summary": "analyze-work refused: x at /y"})
        ok = json.dumps({"operation": "analyze-work", "status": "ok", "summary": "ok", "result": {"report": {"interactions": []}}})
        claude = "\n".join(json.dumps(r) for r in [
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "1", "name": "mcp__plugin_agent-braid_agent-braid__plugin-status", "input": {}}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "2", "name": "mcp__plugin_agent-braid_agent-braid__analyze-work", "input": {"kind": "aim", "request": {"a": 1}}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "2", "content": [{"type": "text", "text": refused}], "is_error": True}]}},
            {"type": "assistant", "message": {"content": [{"type": "tool_use", "id": "3", "name": "mcp__plugin_agent-braid_agent-braid__analyze-work", "input": {"kind": "aim", "request": {"a": 2}}}]}},
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "3", "content": ok}]}}])
        attempts = driver.attempts_from(driver.parse_claude(claude), "claude-code")
        self.assertEqual([a["accepted"] for a in attempts], [False, True])
        self.assertIn("refused", attempts[0]["refusalSummary"])
        opencode = json.dumps({"part": {"type": "tool", "tool": "agent-braid_analyze-work", "state": {"status": "completed", "input": {"kind": "git", "request": {}}, "output": ok}}})
        self.assertEqual(len(driver.attempts_from(driver.parse_opencode(opencode), "opencode")), 1)
        codex = json.dumps({"type": "item.completed", "item": {"type": "mcp_tool_call", "server": "agent-braid", "tool": "analyze-work", "arguments": {"kind": "aim", "request": {}}, "status": "completed", "result": {"content": [{"type": "text", "text": ok}]}}})
        self.assertEqual(len(driver.attempts_from(driver.parse_codex(codex), "codex")), 1)

    def test_tool_classes(self) -> None:
        call = lambda name, args=None: driver.ToolCall(name, args, None, False)  # noqa: E731
        self.assertEqual(driver.tool_class("claude-code", call("Bash")), "denied")
        self.assertEqual(driver.tool_class("claude-code", call("ToolSearch")), "meta")
        self.assertEqual(driver.tool_class("opencode", call("execute", {"code": "return 1"})), "meta")
        self.assertEqual(driver.tool_class("opencode", call("execute", {"code": "await fetch('http://x')"})), "denied")
        self.assertEqual(driver.tool_class("codex", call("command_execution")), "denied")

    def test_redaction_covers_known_values_and_patterns(self) -> None:
        secrets = driver.Secrets(["plain-secret-value"])
        text = secrets.redact("a plain-secret-value b sk-ant-abcdefghijklmnop c Bearer abcdefghijklmnopqrstu")
        self.assertEqual(text.count("[REDACTED]"), 3)
        self.assertEqual(secrets.scan(text), [])

    @unittest.skipUnless(sys.platform == "darwin", "the OS sandbox is macOS sandbox-exec; elsewhere it is a declared limit")
    def test_os_sandbox_denies_a_protected_directory(self) -> None:
        protected_dir = Path(scratch("t013-protected-"))
        (protected_dir / "secret.txt").write_text("x")
        sandbox = driver.OsSandbox([protected_dir])
        denied = subprocess.run(sandbox.wrap(["/bin/cat", str(protected_dir / "secret.txt")]), capture_output=True)
        self.assertNotEqual(denied.returncode, 0)


if __name__ == "__main__":
    unittest.main()


class AblationArmTests(unittest.TestCase):
    """D9: arm ``final-no-schema`` builds the committed HEAD with only the request schema reverted."""

    def test_arm_is_selectable_and_recorded(self) -> None:
        code, evidence, _ = run_driver("--arm", "final-no-schema", "--limit-cases", "1")
        self.assertEqual(code, 0)
        self.assertEqual(evidence["arm"], "final-no-schema")
        self.assertIn("final-no-schema", driver.ARMS)

    def test_build_reverts_only_the_request_schema_in_a_disposable_worktree(self) -> None:
        calls: list[list[str]] = []

        def fake_run(command, **kwargs):
            calls.append([str(part) for part in command])
            out = '{"sourceDirty": true}' if "build_native_plugin.py" in " ".join(map(str, command)) else ""
            return mock.Mock(returncode=0, stdout=out, stderr="")

        work = Path(scratch("t005-arm-"))
        with mock.patch.object(driver.subprocess, "run", side_effect=fake_run):
            _, record = driver.build_candidate("final-no-schema", work, work / "cache", allow_dirty=False)
        joined = [" ".join(call) for call in calls]
        self.assertTrue(any("worktree add --detach" in c and c.endswith(" HEAD") for c in joined), joined)
        generate = [c for c in joined if "spec069_tool_schemas --delivery description-only" in c]
        self.assertEqual(len(generate), 1, joined)
        build = next(c for c in joined if "build_native_plugin.py" in c)
        self.assertIn("--allow-dirty", build)
        self.assertLess(joined.index(generate[0]), joined.index(build))
        self.assertTrue(record["allowDirty"] and record["arm"] == "final-no-schema")
        self.assertTrue(any("worktree remove" in c for c in joined), joined)

    def test_final_arm_is_built_from_the_checkout_without_reverting_the_schema(self) -> None:
        calls: list[str] = []

        def fake_run(command, **kwargs):
            calls.append(" ".join(map(str, command)))
            return mock.Mock(returncode=0, stdout="{}", stderr="")

        work = Path(scratch("t005-arm-"))
        with mock.patch.object(driver.subprocess, "run", side_effect=fake_run):
            _, record = driver.build_candidate("final", work, work / "cache", allow_dirty=False)
        self.assertFalse(any("--delivery" in c or "worktree add" in c for c in calls), calls)
        self.assertEqual(record["delivery"], "per-kind")
