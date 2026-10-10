# SPDX-License-Identifier: AGPL-3.0-only
"""Run SPEC-040 paired local MCP acceptance procedures and write a private receipt."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
CASE_TESTS = {
    "SC-001": ["test_sc001_optional_sdk_pin_core_import_and_missing_dependency_refusal"],
    "SC-002": ["test_sc002_protocol_modes_and_legacy_endpoint_paired_controls",
               "test_sdk_auto_and_legacy_negotiation_tools_resource_prompt_and_call"],
    "SC-003": ["test_sc003_aim_git_worktree_parity_and_large_unicode_chain_refusals",
               "test_chunk_manifest_and_exact_reconstruction",
               "test_resource_rejects_wrong_owner_hash_and_range",
               "test_sc003_sdk_stdio_large_aim_chunk_chain_and_cli_parity_auto_legacy",
               "test_sc003_sdk_stdio_git_worktree_success_and_unsupported_refusal"],
    "SC-004": ["test_sc004_schema_depth_summary_and_envelope_refusal_controls",
               "test_depth_and_operation_bounds_are_checked_before_core",
               "test_service_validates_call_shape_and_operation_bounds_itself"],
    "SC-005": ["test_sc005_canonical_roots_symlinks_unknown_inventory_and_analysis_only",
               "test_runtime_mutations_are_not_advertised_or_dispatchable_by_default",
               "test_results_and_grants_are_disjoint_from_every_allowlisted_worktree"],
    "SC-006": ["test_sc006_exact_grant_authority_positive_absent_wrong_scope_expired_reused",
               "test_existing_runtime_prepare_grant_execute_status_verify_and_refusal_guards"],
    "SC-007": ["test_sc007_cancellation_stale_base_concurrency_and_recovery_observability",
               "test_cancelled_request_never_dispatches",
               "test_runtime_status_resource_caps_output_and_waits_on_cancellation",
               "test_cancellation_waits_for_dispatched_worker_checkpoint"],
    "SC-008": ["test_sc008_owned_empty_and_multi_chunk_resources_prompts_and_refusals",
               "test_sdk_auto_and_legacy_negotiation_tools_resource_prompt_and_call",
               "test_artifact_corruption_is_rejected_in_manifest_and_chunk_reads",
               "test_sc008_sdk_stdio_owned_empty_and_raw_unicode_manifest_chain"],
}
INPUT_PATHS = [
    "pyproject.toml", "agent_braid/tooling_mcp.py", "agent_braid/mcp_runtime.py",
    "agent_braid/analysis.py", "agent_braid/git_adapter.py", "agent_braid/git_runtime.py",
    "agent_braid/git_replay.py", "agent_braid/runtime_policy.py", "agent_braid/runtime_scheduler.py",
    "agent_braid/cli.py", "agent_braid/tooling_cli.py", "agent_braid/git_process.py",
    "tests/test_tooling_mcp.py", "tests/test_tooling_mcp_acceptance.py",
    "tests/test_git_adapter.py", "tests/test_git_runtime.py",
    "examples/analysis/file-edits.json", "specs/040-portable-mcp-surface/contracts/interface.md",
    "specs/040-portable-mcp-surface/data-model.md", "scripts/run_m45_mcp_acceptance.py",
]
TEST_START = re.compile(r"^(test_[A-Za-z0-9_]+) \(([^)]+)\) \.\.\. (.*)$")


def parse_test_outcomes(text: str) -> list[dict]:
    """Parse unittest progress even when asyncio emits a slow-task line inline."""
    lines = text.splitlines()
    found = []
    for index, line in enumerate(lines):
        match = TEST_START.match(line)
        if not match:
            continue
        test_name, test_case, tail = match.groups()
        outcome_match = re.search(r"\b(ok|FAIL|ERROR|skipped(?:\s+.*)?)$", tail)
        if not outcome_match:
            for following in lines[index + 1:index + 10]:
                if TEST_START.match(following):
                    break
                outcome_match = re.fullmatch(r"\s*(ok|FAIL|ERROR|skipped(?:\s+.*)?)\s*", following)
                if outcome_match:
                    break
        if outcome_match:
            outcome = outcome_match.group(1).split(maxsplit=1)[0]
            found.append({"testName": test_name, "testCase": test_case, "outcome": outcome})
    return found


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def run_capture(command: list[str], *, cwd: Path, env: dict[str, str], timeout: int = 900) -> dict:
    completed = subprocess.run(command, cwd=cwd, capture_output=True, text=True,
                               timeout=timeout, check=False, env=env)
    stdout = completed.stdout.encode("utf-8", "replace")
    stderr = completed.stderr.encode("utf-8", "replace")
    return {"command": command, "exitCode": completed.returncode,
            "stdout": completed.stdout, "stderr": completed.stderr,
            "stdoutSha256": sha256(stdout), "stderrSha256": sha256(stderr)}


def git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True,
                          check=True).stdout.strip()


def file_hashes() -> dict[str, str]:
    hashes = {}
    for relative in INPUT_PATHS:
        path = ROOT / relative
        if path.is_file():
            hashes[relative] = sha256(path.read_bytes())
    return hashes


def expected_test_names() -> set[str]:
    return {name for names in CASE_TESTS.values() for name in names}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tooling-python", type=Path, required=True,
                        help="isolated Python with the pinned mcp==2.3.0 tooling extra")
    parser.add_argument("--core-python", type=Path, required=True,
                        help="isolated core-only Python used for the no-SDK paired control")
    parser.add_argument("--output-root", type=Path, required=True,
                        help="private directory outside the checkout for receipts and raw command results")
    parser.add_argument("--require-clean", action="store_true",
                        help="refuse capture unless the checkout has no tracked or untracked changes")
    args = parser.parse_args(argv)
    # Keep the venv's python symlink intact: resolving it escapes the environment.
    tooling_python = args.tooling_python.expanduser().absolute()
    if not tooling_python.exists():
        parser.error(f"tooling interpreter does not exist: {tooling_python}")
    output_root = args.output_root.expanduser().resolve()
    if output_root == ROOT or ROOT in output_root.parents:
        parser.error("--output-root must be outside the source checkout")
    if output_root.exists():
        parser.error("--output-root must be a new directory; existing receipts are never overwritten")
    output_root.mkdir(parents=True, mode=0o700)
    os.chmod(output_root, 0o700)

    base_commit = git("rev-parse", "HEAD")
    status = git("status", "--porcelain=v1", "--untracked-files=all")
    if args.require_clean and status:
        parser.error("--require-clean requires an empty working tree")
    input_hashes_before = file_hashes()
    missing_inputs = sorted(set(INPUT_PATHS) - set(input_hashes_before))
    if missing_inputs:
        parser.error("acceptance input inventory has missing paths: " + ", ".join(missing_inputs))
    diff = subprocess.run(["git", "diff", "--binary", "HEAD", "--"], cwd=ROOT,
                          capture_output=True, check=True).stdout
    home = output_root / "private-home"
    temporary = output_root / "private-tmp"
    trace_dir = output_root / "sdk-transport-traces"
    home.mkdir(mode=0o700)
    temporary.mkdir(mode=0o700)
    trace_dir.mkdir(mode=0o700)
    os.chmod(home, 0o700)
    os.chmod(temporary, 0o700)
    os.chmod(trace_dir, 0o700)
    git_executable = shutil.which("git") or "/usr/bin/git"
    path_parts = [str(tooling_python.parent), str(Path(git_executable).parent),
                  "/opt/homebrew/bin", "/usr/bin", "/bin", "/usr/sbin", "/sbin"]
    sanitized_env = {"HOME": str(home), "TMPDIR": str(temporary),
                     "PATH": os.pathsep.join(dict.fromkeys(path_parts)), "LANG": "C.UTF-8",
                     "M45_CONTROL_TRACE_DIR": str(trace_dir)}
    command = [str(tooling_python), "-m", "unittest", "-v",
               "tests.test_tooling_mcp", "tests.test_tooling_mcp_acceptance"]
    tooling_run = run_capture(command, cwd=ROOT, env=sanitized_env)
    raw_output = (tooling_run["stderr"] + tooling_run["stdout"]).encode("utf-8", "replace")
    raw_path = output_root / "mcp-acceptance-output.txt"
    raw_path.write_bytes(raw_output)
    os.chmod(raw_path, 0o600)

    observations = parse_test_outcomes(tooling_run["stderr"])
    by_name = {observation["testName"]: observation["outcome"] for observation in observations}
    cases = []
    for scenario, expected_tests in CASE_TESTS.items():
        observed = [{"testName": name, "outcome": by_name.get(name, "not-observed")}
                    for name in expected_tests]
        success = bool(expected_tests) and all(item["outcome"] == "ok" for item in observed)
        cases.append({"scenario": scenario, "outcome": "passed" if success else "incomplete-or-failed",
                      "tests": observed,
                      "limits": ["Local service and SDK protocol peer only; no Codex/Claude host observation."]})

    core_path = args.core_python.expanduser().absolute()
    if not core_path.exists():
        parser.error(f"core interpreter does not exist: {core_path}")
    check = ("import importlib.util,json; "
                 "assert importlib.util.find_spec('mcp') is None; "
                 "import agent_braid.analysis; from agent_braid.tooling_mcp import create_server,ToolingConfig; "
                 "from pathlib import Path; import tempfile; "
                 "t=tempfile.TemporaryDirectory(); p=Path(t.name); s=p/'src';r=p/'res';s.mkdir();r.mkdir(); "
                 "c=ToolingConfig(s,r); "
                 "\ntry: create_server(c)\nexcept RuntimeError as e: assert \"optional 'tooling' extra\" in str(e); print('core-only-analysis-import-and-actionable-refusal: passed')\nelse: raise AssertionError('SDK unexpectedly available')")
    core_command = [str(core_path), "-c", check]
    core_run = run_capture(core_command, cwd=ROOT, env=sanitized_env, timeout=60)
    sdk_command = [str(tooling_python), "-c",
                   "import importlib.metadata; print(importlib.metadata.version('mcp'))"]
    sdk_run = run_capture(sdk_command, cwd=ROOT, env=sanitized_env, timeout=60)

    input_hashes_after = file_hashes()
    base_commit_after = git("rev-parse", "HEAD")
    test_summary = re.search(r"\bRan\s+(\d+)\s+tests?\b", tooling_run["stderr"])
    expected_names = expected_test_names()
    observed_names = {observation["testName"] for observation in observations}
    exact_test_count = (test_summary is not None
                        and int(test_summary.group(1)) == len(observations)
                        and len({observation["testCase"] for observation in observations}) == len(observations))
    all_test_results_ok = (exact_test_count and bool(observations)
                           and all(item["outcome"] == "ok" for item in observations)
                           and expected_names <= observed_names)
    all_cases_passed = len(cases) == len(CASE_TESTS) and all(
        case["outcome"] == "passed" for case in cases)
    inputs_unchanged = input_hashes_before == input_hashes_after
    head_unchanged = base_commit == base_commit_after
    sdk_version_ok = (sdk_run["exitCode"] == 0
                      and re.fullmatch(r"\s*2\.3\.0\s*", sdk_run["stdout"]) is not None)
    core_control_ok = (core_run["exitCode"] == 0
                       and "core-only-analysis-import-and-actionable-refusal: passed"
                       in core_run["stdout"])
    full_success = (tooling_run["exitCode"] == 0 and all_cases_passed
                    and all_test_results_ok and inputs_unchanged and head_unchanged
                    and sdk_version_ok and core_control_ok)

    traces = []
    total_trace_bytes = 0
    for path in sorted(trace_dir.iterdir()):
        if path.is_symlink() or not path.is_file():
            raise RuntimeError("SDK transport trace directory contains a non-regular entry")
        os.chmod(path, 0o600)
        raw = path.read_bytes()
        total_trace_bytes += len(raw)
        traces.append({"path": path.name, "sizeBytes": len(raw), "sha256": sha256(raw)})
    if total_trace_bytes > 5 * 1024 * 1024 * 1024:
        raise RuntimeError("SDK transport traces exceed the 5 GiB evidence bound")

    try:
        environment = {
            "python": subprocess.run([str(tooling_python), "--version"], capture_output=True,
                                      text=True, check=True, env=sanitized_env).stdout.strip(),
            "platform": platform.platform(),
            "mcpSdkVersion": sdk_run["stdout"].strip(),
            "environmentAllowlist": sorted(sanitized_env),
            "pathSha256": sha256(sanitized_env["PATH"].encode()),
        }
    except subprocess.CalledProcessError as exc:
        environment = {"python": str(tooling_python), "platform": platform.platform(),
                       "sdkProbeError": (exc.stderr or str(exc))[-1000:]}

    receipt = {
        "receiptVersion": "m45-mcp-acceptance/v1",
        "capturedAtUtc": datetime.now(timezone.utc).isoformat(),
        "candidate": {"baseCommit": base_commit, "workingTreeStatus": status,
                      "trackedDiffSha256": sha256(diff),
                      "inputSha256": input_hashes_before,
                      "postCaptureHead": base_commit_after,
                      "postCaptureWorkingTreeStatus": git("status", "--porcelain=v1", "--untracked-files=all"),
                      "postCaptureInputSha256": input_hashes_after},
        "environment": environment,
        "commands": [{"purpose": "tooling-sdk-acceptance-tests", "command": command,
                      "exitCode": tooling_run["exitCode"],
                      "stdoutSha256": tooling_run["stdoutSha256"],
                      "stderrSha256": tooling_run["stderrSha256"],
                      "rawOutputPath": raw_path.name, "rawOutputSha256": sha256(raw_output)},
                     {"purpose": "pinned-sdk-version-probe", "command": sdk_command,
                      "exitCode": sdk_run["exitCode"],
                      "stdoutSha256": sdk_run["stdoutSha256"],
                      "stderrSha256": sdk_run["stderrSha256"],
                      "literalStdout": sdk_run["stdout"].strip()
                      if re.fullmatch(r"\s*2\.3\.0\s*", sdk_run["stdout"]) else None},
                     {"purpose": "core-only-paired-control", "command": core_run["command"],
                         "exitCode": core_run["exitCode"],
                         "stdoutSha256": core_run["stdoutSha256"],
                         "stderrSha256": core_run["stderrSha256"],
                         "outcome": "passed" if core_run["exitCode"] == 0 else "failed"}],
        "sdkTransportTrace": {"directory": trace_dir.name, "fileCount": len(traces),
                              "totalSizeBytes": total_trace_bytes, "files": traces,
                              "scope": "Local mcp==2.3.0 stdio Client/server fixtures and exact observed local payloads."},
        "acceptanceDecision": {"outcome": "passed" if full_success else "incomplete-or-failed",
            "checks": {"allEightCasesPassed": all_cases_passed,
                       "allTestsObservedOkNoSkips": all_test_results_ok,
                       "unittestReportedCount": int(test_summary.group(1)) if test_summary else None,
                       "parsedTestCount": len(observations),
                       "allRequiredTestsObserved": expected_names <= observed_names,
                       "sourceInputsUnchanged": inputs_unchanged,
                       "headUnchanged": head_unchanged,
                       "pinnedSdkVersionObserved": sdk_version_ok,
                       "coreOnlyPairedControlPassed": core_control_ok}},
        "cases": cases,
        "testOutcomes": observations,
        "limits": ["Unit and SDK protocol peers establish the recorded local domains only.",
                   "No actual Codex or Claude Code host was launched or observed.",
                   "No clean-room reproduction, human review, founder approval, or scientific claim is implied."],
    }
    receipt_path = output_root / "mcp-acceptance-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    os.chmod(receipt_path, 0o600)
    print(json.dumps({"receipt": str(receipt_path), "receiptSha256": sha256(receipt_path.read_bytes()),
                      "acceptanceOutcome": "passed" if full_success else "incomplete-or-failed",
                      "toolingExitCode": tooling_run["exitCode"],
                      "coreExitCode": core_run["exitCode"] if core_run else None,
                      "scenarioOutcomes": {case["scenario"]: case["outcome"] for case in cases}},
                     sort_keys=True))
    return 0 if full_success else 1


if __name__ == "__main__":
    raise SystemExit(main())
