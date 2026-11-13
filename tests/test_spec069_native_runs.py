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
OPENROUTER_KEY = "sk-or-v1-PLANTEDOPENROUTERKEY0123456789abcdef"
PLANTED_CREDENTIAL = '{"accessToken": "sk-ant-oat01-PLANTEDSUBSCRIPTIONTOKEN0123456789"}'
OPENED: list[str] = []
WATCHED: set[str] = set()


def _audit(event: str, args: tuple) -> None:
    if event == "open" and WATCHED and isinstance(args[0], (str, os.PathLike)) and os.fspath(args[0]) in WATCHED:
        OPENED.append(os.fspath(args[0]))


sys.addaudithook(_audit)
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


class RegistryHomeTests(unittest.TestCase):
    def test_codex_registry_is_the_default_state_root_under_home(self) -> None:
        profile = driver.Profile(Path(scratch("t013-test-")))
        codex = driver.HostConfig("codex", Path("/bin/true"), (), "")
        home = driver.agent_braid_home(profile, codex)
        self.assertEqual(home, profile.make("hosts", "codex", "home") / "Library/Application Support/AgentBraid")
        other = driver.HostConfig("opencode", Path("/bin/true"), (), "")
        self.assertEqual(driver.agent_braid_home(profile, other).name, "agent-braid-home")


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
        # Codex's read-only MCP resource listing is a discovery helper (observed in T010), not a denied tool.
        self.assertEqual(driver.tool_class("codex", call("codex__list_mcp_resources", {})), "meta")

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


def keychain(**items: str) -> dict[str, str]:
    return {"FAKE_KEYCHAIN": json.dumps({f"agent-braid-{name}": value for name, value in items.items()})}


def all_text(tmp: Path) -> str:
    return "".join(f.read_text() for f in [tmp / "native-runs.json", *tmp.rglob("*.jsonl")])


class OpenRouterTests(unittest.TestCase):
    MODEL = "opencode=openrouter/anthropic/claude-sonnet-5-5"

    def test_openrouter_route_is_configured_keyed_and_recorded(self) -> None:
        code, evidence, tmp = run_driver("--hosts", "opencode", "--model", self.MODEL, "--limit-cases", "2",
                                         env={"OPENROUTER_API_KEY": OPENROUTER_KEY})
        host = evidence["hosts"]["opencode"]
        self.assertEqual((code, host["status"], host["route"]), (0, "ran", "openrouter"))  # the fake refuses a missing provider or key
        self.assertTrue(any("not strictly comparable" in note for note in host["notes"]))
        self.assertNotIn(OPENROUTER_KEY, all_text(tmp))

    def test_direct_route_is_unchanged_and_openrouter_needs_its_own_key(self) -> None:
        _, evidence, _ = run_driver("--hosts", "opencode", "--model", "opencode=anthropic/m", "--limit-cases", "1")
        self.assertEqual((evidence["hosts"]["opencode"]["route"], evidence["hosts"]["opencode"]["notes"]), ("direct", []))
        with mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": PLANTED_KEY}, clear=True):
            host = driver.HostConfig("opencode", Path("/bin/oc"), *driver.key_spec("opencode", "openrouter/x/y"), model="openrouter/x/y")
            with self.assertRaises(driver.DeclaredLimit) as raised:
                driver.acquire_credential(host, driver.parse_args(["--model", self.MODEL]))
        self.assertIn("OPENROUTER_API_KEY", str(raised.exception))

    def test_command_line_selects_the_openrouter_id(self) -> None:
        host = driver.HostConfig("opencode", Path("/bin/oc"), *driver.key_spec("opencode", "openrouter/anthropic/m"), model="openrouter/anthropic/m")
        self.assertEqual(driver.prompt_argv(host, "p", driver.parse_args([]))[-3:-1], ["-m", "openrouter/anthropic/m"])
        self.assertEqual(host.key_target, "OPENROUTER_API_KEY")


class KeychainTests(unittest.TestCase):
    ALL = keychain(anthropic=PLANTED_KEY, openai="sk-openai-PLANTEDOPENAIKEY0123456789", openrouter=OPENROUTER_KEY)

    def test_keys_come_from_the_keychain_and_never_reach_evidence_or_transcripts(self) -> None:
        code, evidence, tmp = run_driver("--keys-from-keychain", "--fake-variant", "leak-secret", "--limit-cases", "2",
                                         "--model", "opencode=openrouter/anthropic/m", key=None, env=self.ALL)
        self.assertEqual(code, 0)
        self.assertEqual({n: (h["status"], h["keySource"]) for n, h in evidence["hosts"].items()},
                         {n: ("ran", "keychain") for n in ("claude-code", "codex", "opencode")})
        text = all_text(tmp)
        for secret in (PLANTED_KEY, OPENROUTER_KEY, "sk-openai-PLANTEDOPENAIKEY0123456789"):
            self.assertNotIn(secret, text)
        self.assertTrue(any("[REDACTED]" in f.read_text() for f in tmp.rglob("*.jsonl")))

    def test_missing_item_is_a_declared_limit_for_that_host_only_and_the_environment_is_not_used(self) -> None:
        code, evidence, _ = run_driver("--keys-from-keychain", "--limit-cases", "1", key=PLANTED_KEY,
                                       env={**keychain(anthropic=PLANTED_KEY), "OPENAI_API_KEY": "env-openai-value-123456"})
        self.assertEqual(code, 0)
        hosts = evidence["hosts"]
        self.assertEqual((hosts["claude-code"]["status"], hosts["opencode"]["status"]), ("ran", "ran"))
        self.assertEqual(hosts["codex"]["status"], "declared-limit")
        self.assertIn("agent-braid-openai", hosts["codex"]["limit"])
        self.assertNotIn("env-openai-value-123456", json.dumps(evidence))

    def test_environment_key_is_ignored_when_the_keychain_is_empty(self) -> None:
        _, evidence, _ = run_driver("--keys-from-keychain", "--hosts", "claude-code", "--limit-cases", "1", key=PLANTED_KEY, env=keychain())
        self.assertEqual(evidence["hosts"]["claude-code"]["status"], "declared-limit")

    def test_security_cli_is_called_with_the_service_and_its_output_is_not_kept(self) -> None:
        with mock.patch.dict(os.environ, self.ALL):
            self.assertEqual(driver.keychain_secret("agent-braid-anthropic", str(FAKE_HOSTS / "security")), PLANTED_KEY)
            self.assertIsNone(driver.keychain_secret("agent-braid-absent", str(FAKE_HOSTS / "security")))
        self.assertIsNone(driver.keychain_secret("x", "/nonexistent/security"))


def auth_dir(claude: bool = True, codex: bool = True) -> Path:
    root = Path(scratch("t013-auth-")) / "profile"
    for host, enabled in (("claude", claude), ("codex", codex)):
        if enabled:
            (root / host).mkdir(parents=True)
            (root / host / (".credentials.json" if host == "claude" else "auth.json")).write_text(PLANTED_CREDENTIAL)
    return root


class SubscriptionTests(unittest.TestCase):
    def test_subscription_runs_without_any_key_and_keeps_the_profile(self) -> None:
        profile = auth_dir()
        files = [profile / "claude/.credentials.json", profile / "codex/auth.json"]
        before = [f.read_bytes() for f in files]
        WATCHED.update(str(f) for f in files)
        OPENED.clear()
        self.addCleanup(WATCHED.clear)
        code, evidence, tmp = run_driver("--auth", "subscription", "--auth-profile-dir", str(profile), "--hosts", "claude-code,codex",
                                         "--limit-cases", "2", key=None)
        self.assertEqual(code, 0)
        opened = list(OPENED)  # before this test reads the files itself
        for name in ("claude-code", "codex"):
            host = evidence["hosts"][name]
            self.assertEqual((host["status"], host["auth"], host["keySource"]), ("ran", "interactive-once", "profile"))
            self.assertTrue(any("subscription" in note for note in host["notes"]))
            self.assertEqual(host["probe"]["authProfile"]["bytes"], len(PLANTED_CREDENTIAL))
            self.assertTrue(host["probe"]["authProfile"]["usableUnderSandbox"] and host["probe"]["canaryReadThroughRedirectedHome"])
        self.assertEqual([f.read_bytes() for f in files], before, "teardown must keep the sign-in")
        self.assertEqual(profile.stat().st_mode & 0o777, 0o700)
        self.assertEqual(opened, [], "the driver must not open a credential file")
        self.assertNotIn("PLANTEDSUBSCRIPTIONTOKEN", all_text(tmp))

    def test_credential_echoed_by_a_leaky_host_is_redacted(self) -> None:
        profile = auth_dir()
        code, evidence, tmp = run_driver("--auth", "subscription", "--auth-profile-dir", str(profile), "--hosts", "claude-code,codex",
                                         "--fake-variant", "echo-credentials", "--limit-cases", "1", key=None)
        self.assertEqual(code, 0)
        self.assertEqual(evidence["hosts"]["codex"]["status"], "ran")
        self.assertNotIn("PLANTEDSUBSCRIPTIONTOKEN", all_text(tmp))
        self.assertTrue(any("[REDACTED]" in f.read_text() for f in tmp.rglob("*.jsonl")))

    def test_missing_sign_in_is_a_declared_limit(self) -> None:
        _, evidence, _ = run_driver("--auth", "subscription", "--auth-profile-dir", str(auth_dir(claude=False, codex=False)),
                                    "--hosts", "claude-code", "--limit-cases", "1", key=None)
        self.assertEqual(evidence["hosts"]["claude-code"]["status"], "declared-limit")

    def test_opencode_still_uses_a_key_in_subscription_mode(self) -> None:
        _, evidence, _ = run_driver("--auth", "subscription", "--auth-profile-dir", str(auth_dir()), "--hosts", "opencode",
                                    "--model", "opencode=anthropic/m", "--limit-cases", "1")
        self.assertEqual(evidence["hosts"]["opencode"]["auth"], "env-key")

    def test_profile_on_a_real_config_path_is_refused_before_any_host_runs(self) -> None:
        home = Path(scratch("t013-home-"))
        (home / ".codex").mkdir()
        (home / ".config/opencode").mkdir(parents=True)
        link = Path(scratch("t013-link-")) / "innocent"
        link.symlink_to(home / ".codex")
        log = Path(scratch("t013-log-")) / "invocations.jsonl"
        for target in (home / ".codex", home / ".config/opencode/sub", home, link, driver.ROOT / "evidence-profile"):
            with self.subTest(target=str(target)):
                code, evidence, _ = run_driver("--real-home", str(home), "--auth", "subscription", "--auth-profile-dir", str(target),
                                               "--limit-cases", "1", key=None, env={"FAKE_LOG": str(log)})
                self.assertEqual(code, driver.EXIT_SAFETY)
                self.assertIn("auth profile", evidence["stopped"])
                self.assertFalse(log.exists())
        self.assertFalse((home / ".config/opencode/sub").exists())

    def test_subscription_flags_need_a_profile_directory(self) -> None:
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            driver.parse_args(["--auth", "subscription"])


class LoginTests(unittest.TestCase):
    def call(self, *argv: str, env: dict[str, str] | None = None) -> tuple[int, str, str]:
        out, err = io.StringIO(), io.StringIO()
        with mock.patch.dict(os.environ, env or {}), contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = driver.main(["--fake-hosts", *argv])
        return code, out.getvalue(), err.getvalue()

    def test_login_only_prints_the_exact_commands_and_creates_nothing(self) -> None:
        profile = Path(scratch("t013-login-")) / "p"
        code, out, _ = self.call("--login", "claude-code", "--auth-profile-dir", str(profile))
        self.assertEqual(code, 0)
        self.assertIn(f"CLAUDE_CONFIG_DIR={os.path.realpath(profile)}/claude claude", out)
        code, out, _ = self.call("--login", "codex", "--auth-profile-dir", str(profile))
        self.assertIn(f"CODEX_HOME={os.path.realpath(profile)}/codex codex login", out)
        self.assertFalse(profile.exists())

    def test_login_refuses_a_real_config_path(self) -> None:
        home = Path(scratch("t013-home-"))
        code, out, err = self.call("--login", "claude-code", "--auth-profile-dir", str(home / ".claude"), "--real-home", str(home))
        self.assertEqual(code, driver.EXIT_SAFETY)
        self.assertEqual(out, "")
        self.assertIn("refused", err)

    def test_check_login_reports_existence_and_size_and_answers_a_prompt(self) -> None:
        profile = auth_dir()
        WATCHED.add(str(profile / "claude/.credentials.json"))
        OPENED.clear()
        self.addCleanup(WATCHED.clear)
        code, out, _ = self.call("--check-login", "claude-code", "--auth-profile-dir", str(profile))
        result = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual((result["ok"], result["credential"]), (True, {"file": ".credentials.json", "exists": True, "bytes": len(PLANTED_CREDENTIAL)}))
        self.assertTrue(result["usableUnderSandbox"])
        self.assertTrue(result["teardown"]["clean"])
        self.assertEqual(OPENED, [])
        self.assertNotIn("PLANTEDSUBSCRIPTIONTOKEN", out)

    def test_check_login_without_a_sign_in_fails_cleanly(self) -> None:
        code, out, _ = self.call("--check-login", "codex", "--auth-profile-dir", str(auth_dir(codex=False)))
        result = json.loads(out)
        self.assertEqual((code, result["ok"], result["credential"]["exists"]), (1, False, False))
        self.assertIn("Not logged in", result["error"])

    def test_check_login_leaky_host_output_is_redacted(self) -> None:
        code, out, _ = self.call("--check-login", "claude-code", "--auth-profile-dir", str(auth_dir()), env={"FAKE_VARIANT": "echo-credentials"})
        self.assertEqual(code, 0)
        self.assertNotIn("PLANTEDSUBSCRIPTIONTOKEN", out)


OAUTH_TOKEN = "sk-ant-oat01-PLANTEDOAUTHTOKENFORTEST0123456789abcdef"


def oauth_keychain(token: str = OAUTH_TOKEN) -> dict[str, str]:
    return keychain(**{"claude-oauth": token})


class TokenAuthTests(unittest.TestCase):
    def run_token(self, *extra: str, env: dict[str, str] | None = None, key: str | None = None) -> tuple[int, dict, Path, Path]:
        log = Path(scratch("t013-log-")) / "invocations.jsonl"
        code, evidence, tmp = run_driver("--auth", "token", "--limit-cases", "2", "--extra-env", f"FAKE_LOG={log}", *extra, key=key, env=env)
        return code, evidence, tmp, log

    def test_token_from_the_keychain_reaches_only_claude_code_without_an_api_key(self) -> None:
        code, evidence, tmp, log = self.run_token("--keys-from-keychain", "--fake-variant", "leak-secret", key=None,
                                                  env={**oauth_keychain(), **keychain(**{"claude-oauth": OAUTH_TOKEN, "openai": "sk-openai-PLANTEDOPENAIKEY0123456789", "anthropic": PLANTED_KEY})})
        self.assertEqual(code, 0)
        host = evidence["hosts"]["claude-code"]
        self.assertEqual((host["status"], host["auth"], host["keySource"]), ("ran", "oauth-token-env", "keychain"))
        self.assertTrue(any("oauth-token-env" in note for note in host["notes"]))
        self.assertTrue(any("may differ" in note for note in host["notes"]))
        self.assertEqual({n: h["auth"] for n, h in evidence["hosts"].items() if n != "claude-code"}, {"codex": "env-key", "opencode": "env-key"})
        seen = {}
        for line in log.read_text().splitlines():
            row = json.loads(line)
            seen.setdefault(row["host"], set()).update(row["credentialVars"])
        self.assertEqual(seen["claude"], {"CLAUDE_CODE_OAUTH_TOKEN"})
        for other in ("codex", "opencode"):
            self.assertNotIn("CLAUDE_CODE_OAUTH_TOKEN", seen[other])
        text = all_text(tmp)
        self.assertNotIn(OAUTH_TOKEN, text)
        self.assertNotIn("PLANTEDOAUTHTOKEN", text)

    def test_token_from_the_environment_and_an_api_key_in_the_driver_environment_is_not_forwarded(self) -> None:
        code, evidence, _, log = self.run_token("--hosts", "claude-code", key=PLANTED_KEY, env={"CLAUDE_CODE_OAUTH_TOKEN": OAUTH_TOKEN})
        self.assertEqual((code, evidence["hosts"]["claude-code"]["keySource"]), (0, "environment"))
        self.assertTrue(all(json.loads(line)["credentialVars"] == ["CLAUDE_CODE_OAUTH_TOKEN"] for line in log.read_text().splitlines()))

    def test_api_key_extra_env_cannot_override_the_token(self) -> None:
        code, evidence, _, _ = self.run_token("--hosts", "claude-code", "--extra-env", "ANTHROPIC_API_KEY=sk-ant-api03-EXTRAENVKEY0123456789",
                                              env={"CLAUDE_CODE_OAUTH_TOKEN": OAUTH_TOKEN})
        self.assertEqual((code, evidence["hosts"]["claude-code"]["status"]), (0, "ran"))

    def test_absent_token_is_a_declared_limit_for_claude_code_only(self) -> None:
        code, evidence, _, _ = self.run_token(key=PLANTED_KEY)
        self.assertEqual(code, 0)
        self.assertEqual(evidence["hosts"]["claude-code"]["status"], "declared-limit")
        self.assertIn("CLAUDE_CODE_OAUTH_TOKEN", evidence["hosts"]["claude-code"]["limit"])
        self.assertEqual(evidence["hosts"]["codex"]["status"], "ran")

    def test_missing_keychain_item_is_a_declared_limit_and_the_environment_is_not_used(self) -> None:
        _, evidence, _, _ = self.run_token("--keys-from-keychain", "--hosts", "claude-code", env={"CLAUDE_CODE_OAUTH_TOKEN": OAUTH_TOKEN, **keychain()})
        self.assertEqual(evidence["hosts"]["claude-code"]["status"], "declared-limit")
        self.assertIn("agent-braid-claude-oauth", evidence["hosts"]["claude-code"]["limit"])
        self.assertNotIn(OAUTH_TOKEN, json.dumps(evidence))

    def test_token_printed_by_a_host_is_caught_by_the_secret_scan_without_the_literal(self) -> None:
        secrets = driver.Secrets()  # no literal known: only the token shape
        text = f"model said {OAUTH_TOKEN} and bearer {OAUTH_TOKEN[:20]}"
        self.assertNotIn("PLANTEDOAUTH", secrets.redact(text))
        with self.assertRaises(driver.SecretLeak):
            secrets.assert_clean("transcript.jsonl", text)
        with self.assertRaises(driver.SecretLeak):
            secrets.assert_clean("evidence.json", json.dumps({"x": "sk-ant-oat01-ABCDEFGHIJKLMNOPQRSTUVWX"}))

    def test_token_mode_does_not_need_a_profile_directory_and_is_claude_code_only(self) -> None:
        driver.parse_args(["--auth", "token"])
        driver.parse_args(["--auth", "token", "--check-login", "claude-code"])
        with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
            driver.parse_args(["--auth", "token", "--check-login", "codex"])

    def test_the_token_is_never_prompted_for_or_stored_by_login(self) -> None:
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(driver.main(["--fake-hosts", "--auth", "token", "--login", "claude-code"]), 0)
        self.assertIn("claude setup-token", out.getvalue())
        self.assertIn("agent-braid-claude-oauth", out.getvalue())


class TokenCheckLoginTests(unittest.TestCase):
    call = LoginTests.call

    def test_check_login_passes_when_the_token_is_present_and_reports_presence_and_length_only(self) -> None:
        code, out, _ = self.call("--check-login", "claude-code", "--auth", "token", env={"CLAUDE_CODE_OAUTH_TOKEN": OAUTH_TOKEN})
        result = json.loads(out)
        self.assertEqual((code, result["ok"]), (0, True))
        self.assertEqual(result["credential"], {"auth": "oauth-token-env", "source": "environment", "present": True, "length": len(OAUTH_TOKEN)})
        self.assertNotIn("PLANTEDOAUTH", out)

    def test_check_login_from_the_keychain(self) -> None:
        code, out, _ = self.call("--check-login", "claude-code", "--auth", "token", "--keys-from-keychain", env=oauth_keychain())
        self.assertEqual((code, json.loads(out)["credential"]["source"]), (0, "keychain"))

    def test_check_login_without_a_token_reports_a_declared_limit(self) -> None:
        code, out, _ = self.call("--check-login", "claude-code", "--auth", "token", env={"CLAUDE_CODE_OAUTH_TOKEN": ""})
        result = json.loads(out)
        self.assertEqual((code, result["ok"]), (1, False))
        self.assertIn("declared limit", result["error"])

    def test_check_login_with_a_rejected_token_reports_a_declared_limit_without_the_token(self) -> None:
        rejected = "sk-ant-oat01-REJECTEDTOKEN0123456789abcdef"
        code, out, _ = self.call("--check-login", "claude-code", "--auth", "token", env={"CLAUDE_CODE_OAUTH_TOKEN": rejected})
        result = json.loads(out)
        self.assertEqual((code, result["ok"]), (1, False))
        self.assertIn("declared limit", result["error"])
        self.assertNotIn(rejected, out)

    def test_check_login_leaky_host_prints_the_token_and_it_is_redacted(self) -> None:
        code, out, _ = self.call("--check-login", "claude-code", "--auth", "token", env={"CLAUDE_CODE_OAUTH_TOKEN": OAUTH_TOKEN, "FAKE_VARIANT": "leak-secret"})
        self.assertNotIn(OAUTH_TOKEN, out)


class OpenCodeUsageTests(unittest.TestCase):
    def test_usage_is_summed_over_steps_and_a_named_model_is_kept(self) -> None:
        rows = [{"type": "step_finish", "part": {"type": "step-finish", "cost": 0.5, "tokens": {"input": 2, "output": 10, "cache": {"read": 5}}}},
                {"type": "step_finish", "part": {"type": "step-finish", "cost": 0.25, "tokens": {"input": 3, "output": 4, "cache": {"read": 1}}, "modelID": "m/x"}}]
        transcript = driver.parse_opencode_run("\n".join(json.dumps(r) for r in rows))
        self.assertEqual(transcript.usage, {"cost": 0.75, "tokens": {"input": 5, "output": 14, "cache": {"read": 6}}})
        self.assertEqual(transcript.models, ["m/x"])


class SchemaProbeTests(unittest.TestCase):
    """--probe-schema (T005 / procedure_005): recording relay in the installed copy, verdict per host, byte identity."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.code, cls.evidence, cls.tmp = run_driver("--probe-schema", "--arm", "final")

    def test_every_host_passes_with_object_requests_for_both_branches(self) -> None:
        self.assertEqual(self.code, 0)
        self.assertEqual(self.evidence["label"], "pipeline-only")
        for name in driver.HOSTS:
            verdict = self.evidence["summary"][name]
            self.assertEqual(verdict["verdict"], "pass", name)
            self.assertTrue(verdict["requestAlwaysObject"])
            self.assertEqual(verdict["kindsAtServer"], ["aim", "units"])
            self.assertTrue(verdict["exposedToModel"])
            self.assertEqual(verdict["loading"], "eager")
            self.assertNotIn("score", self.evidence["hosts"][name]["runs"][0])

    def test_raw_listing_line_is_saved_with_its_hash_and_matches_the_build_fingerprint(self) -> None:
        expected = self.evidence["schemaProbe"]["expectedFingerprint"]["sha256"]
        self.assertEqual(expected, driver.expected_fingerprints()["per-kind"]["sha256"])
        for name in driver.HOSTS:
            (connection,) = self.evidence["hosts"][name]["schemaProbe"]["connections"]
            self.assertTrue(connection["complete"])
            self.assertRegex(connection["protocolVersion"], r"^\d{4}-\d{2}-\d{2}$")
            (listing,) = connection["listings"]
            raw = (self.tmp / listing["rawLineFile"]).read_bytes()
            self.assertEqual(driver.sha256_bytes(raw), listing["lineSha256"])
            self.assertEqual(listing["modelFacingSha256"], expected)
            self.assertTrue(listing["matchesFingerprint"] and listing["servedKeyOrderEqualsFingerprint"])
        cross = self.evidence["schemaProbe"]["crossHost"]
        self.assertTrue(all(group["identical"] for group in cross["byProtocolVersion"].values()))
        self.assertTrue(cross["modelFacingIdenticalAcrossVersions"])

    def test_stringified_request_is_a_declared_limit_not_a_pass(self) -> None:
        code, evidence, _ = run_driver("--probe-schema", "--arm", "final", "--fake-variant", "stringify", "--hosts", "codex")
        self.assertEqual(code, 0)
        verdict = evidence["summary"]["codex"]
        self.assertFalse(verdict["requestAlwaysObject"])
        self.assertTrue(verdict["verdict"].startswith("declared-limit"), verdict["verdict"])

    def test_description_only_arm_compares_against_its_own_fingerprint(self) -> None:
        code, evidence, _ = run_driver("--probe-schema", "--arm", "final-no-schema", "--hosts", "opencode")
        self.assertEqual(code, 0)
        self.assertEqual(evidence["schemaProbe"]["delivery"], "description-only")
        self.assertEqual(evidence["schemaProbe"]["expectedFingerprint"]["sha256"],
                         driver.expected_fingerprints()["description-only"]["sha256"])
        self.assertEqual(evidence["summary"]["opencode"]["verdict"], "pass")

    def test_probe_needs_a_d9_arm_and_a_single_prompt(self) -> None:
        for extra in (["--arm", "baseline"], ["--arm", "final", "--repetitions", "3"]):
            with self.assertRaises(SystemExit), contextlib.redirect_stderr(io.StringIO()):
                driver.parse_args(["--probe-schema", *extra])

    def test_wrapper_relays_only_plugin_serve_and_is_restored(self) -> None:
        root = Path(scratch("t005-wrap-"))
        (root / "launch").write_text("#!/bin/sh\necho real \"$@\"\n")
        (root / "launch").chmod(0o755)
        receipts = root / "receipts"
        receipts.mkdir()
        restore = driver.wrap_launcher(root, receipts)
        self.assertEqual(subprocess.run([str(root / "launch"), "plugin", "setup"], capture_output=True, text=True).stdout, "real plugin setup\n")
        self.assertEqual(list(receipts.iterdir()), [])
        with self.assertRaises(driver.SafetyStop):
            driver.wrap_launcher(root, receipts)
        restore()
        self.assertEqual((root / "launch").read_text(), "#!/bin/sh\necho real \"$@\"\n")
        self.assertFalse((root / "launch.real").exists() or (root / "probe-relay.py").exists())

    def test_loading_mode_is_read_from_the_order_of_calls(self) -> None:
        call = lambda tool: driver.ToolCall(tool, {}, None, False)  # noqa: E731
        work = call("mcp__plugin_agent-braid_agent-braid__analyze-work")
        self.assertEqual(driver.loading_mode("claude-code", driver.Transcript([call("ToolSearch"), work])), "deferred")
        self.assertEqual(driver.loading_mode("claude-code", driver.Transcript([call("Skill"), work])), "eager")
        self.assertEqual(driver.loading_mode("opencode", driver.Transcript([call("execute"), call("agent-braid_analyze-work")])), "helper-before-call")
        self.assertEqual(driver.loading_mode("codex", driver.Transcript([])), "not-observed")
