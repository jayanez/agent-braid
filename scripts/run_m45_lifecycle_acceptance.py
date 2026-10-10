#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Run bounded M4.5 lifecycle/presentation acceptance controls into private evidence."""
from __future__ import annotations

import argparse
import ast
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
INPUTS = (
    "agent_braid/tooling_install.py",
    "agent_braid/tooling_present.py",
    "agent_braid/tooling_mcp.py",
    "scripts/run_m45_lifecycle_acceptance.py",
    "tests/test_tooling_lifecycle_acceptance.py",
    "tests/test_tooling_presentation_acceptance.py",
    "tests/test_tooling_mcp.py",
    "tests/test_tooling_mcp_acceptance.py",
    "scripts/run_m45_mcp_acceptance.py",
    "specs/042-ai-tooling-packaging/validation-plan.md",
)
TEST_MODULES = (
    "tests/test_tooling_lifecycle_acceptance.py",
    "tests/test_tooling_presentation_acceptance.py",
)
EXPECTED_TESTS = {
    "test_sc002_preview_selected_apply_and_refusal_keep_stdout_protocol": "m45_acceptance_test_tooling_lifecycle_acceptance.LifecycleAcceptance",
    "test_sc002_cli_emits_only_typed_json_and_requires_selected_preview_digest": "m45_acceptance_test_tooling_lifecycle_acceptance.LifecycleAcceptance",
    "test_sc003_user_project_and_codex_home_are_explicit_and_root_scoped": "m45_acceptance_test_tooling_lifecycle_acceptance.LifecycleAcceptance",
    "test_sc004_idempotent_owned_change_preserves_unrelated_bytes_and_refuses_collision": "m45_acceptance_test_tooling_lifecycle_acceptance.LifecycleAcceptance",
    "test_sc005_doctor_separates_healthy_static_checks_from_unavailable_host_and_pending_auth": "m45_acceptance_test_tooling_lifecycle_acceptance.LifecycleAcceptance",
    "test_sc006_older_owned_bundle_updates_with_receipt_and_modified_asset_refuses": "m45_acceptance_test_tooling_lifecycle_acceptance.LifecycleAcceptance",
    "test_sc007_uninstall_twice_removes_owned_and_preserves_modified_and_shared_data": "m45_acceptance_test_tooling_lifecycle_acceptance.LifecycleAcceptance",
    "test_sc002_summary_agrees_with_every_classification_and_unknown_stays_unknown": "m45_acceptance_test_tooling_presentation_acceptance.PresentationAcceptance",
    "test_sc003_summary_explains_missing_grant_and_records_limited_success_scope": "m45_acceptance_test_tooling_presentation_acceptance.PresentationAcceptance",
    "test_sc004_success_failure_cancel_and_recovery_states_remain_distinct": "m45_acceptance_test_tooling_presentation_acceptance.PresentationAcceptance",
    "test_sc005_graph_preserves_edge_semantics_and_refuses_malformed_or_oversize": "m45_acceptance_test_tooling_presentation_acceptance.PresentationAcceptance",
    "test_sc006_repeated_export_bytes_and_receipt_bind_exact_source_output_and_limits": "m45_acceptance_test_tooling_presentation_acceptance.PresentationAcceptance",
    "test_sc007_export_escapes_active_markup_and_refuses_unsafe_selection_and_size": "m45_acceptance_test_tooling_presentation_acceptance.PresentationAcceptance",
}


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("ascii")


def candidate_inventory() -> tuple[str, dict[str, str]]:
    listed = subprocess.run(
        ["git", "ls-files", "-co", "--exclude-standard", "-z"], cwd=ROOT,
        check=True, stdout=subprocess.PIPE,
    ).stdout.split(b"\0")
    inventory = {}
    for raw in listed:
        if not raw:
            continue
        relative = raw.decode("utf-8", "strict")
        path = ROOT / relative
        if path.is_file() and not path.is_symlink():
            inventory[relative] = sha256(path.read_bytes())
    return sha256(json_bytes(inventory)), inventory


def git_text(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          stdout=subprocess.PIPE, text=True).stdout.strip()


def declared_mcp_inputs() -> list[str]:
    source = (ROOT / "scripts/run_m45_mcp_acceptance.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign) and any(
                isinstance(target, ast.Name) and target.id == "INPUT_PATHS" for target in node.targets):
            paths = ast.literal_eval(node.value)
            if isinstance(paths, list) and all(isinstance(path, str) for path in paths):
                return paths
    raise ValueError("MCP runner INPUT_PATHS inventory is missing or not a literal list")


def raw_test_outcomes(raw: str) -> list[dict[str, str]]:
    """Parse unittest progress from retained raw output, including interleaved async diagnostics."""
    found = []
    lines = raw.splitlines()
    start = re.compile(r"^(test_[A-Za-z0-9_]+) \(([^)]+)\) \.\.\. (.*)$")
    result = re.compile(r"\b(ok|FAIL|ERROR|skipped(?:\s+[^\r\n]*)?)\s*$")
    for index, line in enumerate(lines):
        match = start.match(line)
        if not match:
            continue
        test_name, test_case, tail = match.groups()
        outcome = result.search(tail)
        if outcome is None and index + 1 < len(lines):
            outcome = result.fullmatch(lines[index + 1].strip())
        if outcome is not None:
            found.append({"testName": test_name, "testCase": test_case,
                          "outcome": outcome.group(1).split(maxsplit=1)[0]})
    return found


def expected_roster() -> list[dict[str, str]]:
    return [{"testName": name, "testCase": case, "outcome": "ok"}
            for name, case in EXPECTED_TESTS.items()]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True, help="new private proof directory outside the checkout")
    parser.add_argument("--protocol-receipt", required=True,
                        help="private receipt from the actual local MCP SDK stdio peer run")
    args = parser.parse_args()
    output = Path(args.output).expanduser().absolute()
    if output.resolve(strict=False).is_relative_to(ROOT):
        parser.error("proof output must be outside the source checkout")
    if output.exists() or output.is_symlink():
        parser.error("proof output must be a new, non-symlink path")
    output.mkdir(mode=0o700, parents=True)
    output.chmod(0o700)

    missing = [name for name in INPUTS if not (ROOT / name).is_file()]
    if missing:
        parser.error("required acceptance inputs are unavailable")
    inputs = {name: sha256((ROOT / name).read_bytes()) for name in INPUTS}
    try:
        head = git_text("rev-parse", "HEAD")
        initial_status = git_text("status", "--porcelain=v1", "--untracked-files=all")
    except (subprocess.CalledProcessError, FileNotFoundError):
        head = None
        initial_status = "unavailable"
    if head is None or initial_status:
        parser.error("lifecycle/presentation capture requires a clean frozen candidate")
    protocol_path = Path(args.protocol_receipt).expanduser().absolute()
    if protocol_path.resolve(strict=False).is_relative_to(ROOT) or not protocol_path.is_file() or protocol_path.is_symlink():
        parser.error("protocol receipt must be an existing regular private file outside the checkout")
    protocol_stat = protocol_path.stat()
    protocol_parent_stat = protocol_path.parent.stat()
    if (protocol_stat.st_uid != os.getuid() or stat.S_IMODE(protocol_stat.st_mode) & 0o077
            or protocol_parent_stat.st_uid != os.getuid() or stat.S_IMODE(protocol_parent_stat.st_mode) & 0o077):
        parser.error("protocol receipt must be user-owned with no group/other permissions")
    protocol_bytes = protocol_path.read_bytes()
    try:
        protocol_receipt = json.loads(protocol_bytes.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        parser.error(f"protocol receipt is not valid JSON ({type(exc).__name__})")
    expected_test = {
        "testName": "test_sdk_auto_and_legacy_negotiation_tools_resource_prompt_and_call",
        "testCase": "tests.test_tooling_mcp.SdkClientIntegrationTests.test_sdk_auto_and_legacy_negotiation_tools_resource_prompt_and_call",
        "outcome": "ok",
    }
    if not isinstance(protocol_receipt, dict):
        parser.error("protocol receipt must be a JSON object")
    if protocol_receipt.get("receiptVersion") != "m45-mcp-acceptance/v1":
        parser.error("protocol receipt has an unsupported schema")
    candidate = protocol_receipt.get("candidate")
    if not isinstance(candidate, dict) or candidate.get("baseCommit") != head:
        parser.error("protocol receipt does not bind the current candidate base commit")
    if candidate.get("workingTreeStatus") != "" or candidate.get("trackedDiffSha256") != sha256(b""):
        parser.error("protocol receipt was not captured from the clean frozen candidate")
    environment = protocol_receipt.get("environment")
    if not isinstance(environment, dict) or environment.get("mcpSdkVersion") != "2.3.0":
        parser.error("protocol receipt does not confirm the pinned MCP SDK version")
    commands = protocol_receipt.get("commands")
    if not isinstance(commands, list):
        parser.error("protocol receipt lacks command records")
    by_purpose = {item.get("purpose"): item for item in commands if isinstance(item, dict)}
    test_command = by_purpose.get("tooling-sdk-acceptance-tests")
    version_command = by_purpose.get("pinned-sdk-version-probe")
    core_command = by_purpose.get("core-only-paired-control")
    expected_argv = ["-m", "unittest", "-v", "tests.test_tooling_mcp", "tests.test_tooling_mcp_acceptance"]
    if (not isinstance(test_command, dict) or test_command.get("exitCode") != 0
            or not isinstance(test_command.get("command"), list)
            or test_command["command"][1:] != expected_argv):
        parser.error("protocol receipt does not show the expected successful MCP SDK test command")
    test_executable = test_command["command"][0]
    if (not isinstance(test_executable, str) or not Path(test_executable).is_absolute()
            or not Path(test_executable).is_file() or not os.access(test_executable, os.X_OK)):
        parser.error("protocol test command does not bind an executable Python interpreter")
    if (not isinstance(version_command, dict) or version_command.get("purpose") != "pinned-sdk-version-probe"
            or version_command.get("exitCode") != 0
            or version_command.get("command") != [test_executable, "-c",
                "import importlib.metadata; print(importlib.metadata.version('mcp'))"]
            or version_command.get("literalStdout") != "2.3.0"
            or version_command.get("stdoutSha256") != sha256(b"2.3.0\n")
            or version_command.get("stderrSha256") != sha256(b"")):
        parser.error("protocol receipt lacks a successful executable probe for pinned MCP SDK 2.3.0")
    if (not isinstance(core_command, dict) or core_command.get("exitCode") != 0
            or core_command.get("outcome") != "passed" or not isinstance(core_command.get("command"), list)
            or len(core_command["command"]) < 3 or core_command["command"][1] != "-c"
            or "core-only-analysis-import-and-actionable-refusal: passed" not in core_command["command"][2]):
        parser.error("protocol receipt lacks the successful mandatory core-only paired control")
    core_executable = core_command["command"][0]
    if (not isinstance(core_executable, str) or not Path(core_executable).is_absolute()
            or not Path(core_executable).is_file() or not os.access(core_executable, os.X_OK)):
        parser.error("core-only paired control does not bind an executable interpreter")
    cases = protocol_receipt.get("cases")
    if (not isinstance(cases, list) or {case.get("scenario") for case in cases if isinstance(case, dict)}
            != {f"SC-{index:03}" for index in range(1, 9)}
            or any(not isinstance(case, dict) or case.get("outcome") != "passed"
                   or not isinstance(case.get("tests"), list)
                   or any(test.get("outcome") != "ok" for test in case["tests"] if isinstance(test, dict)
                          ) or any(not isinstance(test, dict) for test in case.get("tests", []))
                   for case in cases)):
        parser.error("MCP protocol control cases are incomplete, skipped, or failed")
    mcp_outcomes = protocol_receipt.get("testOutcomes")
    if (not isinstance(mcp_outcomes, list) or not mcp_outcomes
            or any(not isinstance(item, dict) or item.get("outcome") != "ok" for item in mcp_outcomes)):
        parser.error("MCP test outcomes contain missing, skipped, or failed controls")

    raw_name = test_command.get("rawOutputPath")
    if not isinstance(raw_name, str) or Path(raw_name).is_absolute() or ".." in Path(raw_name).parts:
        parser.error("protocol raw-output reference must be a relative path inside its private receipt directory")
    raw_path = protocol_path.parent / raw_name
    if (raw_path.is_symlink() or not raw_path.is_file()
            or raw_path.resolve(strict=True).parent != protocol_path.parent.resolve(strict=True)):
        parser.error("protocol raw output is unavailable or escapes its private receipt directory")
    raw_stat = raw_path.stat()
    if raw_stat.st_uid != os.getuid() or stat.S_IMODE(raw_stat.st_mode) & 0o077:
        parser.error("protocol raw output must be user-owned with no group/other permissions")
    raw_bytes = raw_path.read_bytes()
    if sha256(raw_bytes) != test_command.get("rawOutputSha256"):
        parser.error("protocol raw output digest does not match its retained bytes")
    parsed_raw = raw_test_outcomes(raw_bytes.decode("utf-8", "replace"))
    if (expected_test not in parsed_raw or parsed_raw != mcp_outcomes
            or any(item.get("outcome") != "ok" for item in parsed_raw)):
        parser.error("retained raw output does not confirm every SDK test outcome, including the live stdio peer")
    protocol_sha256 = sha256(protocol_bytes)
    mcp_input_paths = declared_mcp_inputs()
    if not mcp_input_paths or len(mcp_input_paths) != len(set(mcp_input_paths)):
        parser.error("MCP runner input inventory is empty or contains duplicates")
    mcp_inputs = candidate.get("inputSha256")
    if not isinstance(mcp_inputs, dict) or set(mcp_inputs) != set(mcp_input_paths):
        parser.error("protocol receipt does not bind the runner's complete MCP input inventory")
    for name in mcp_input_paths:
        relative = Path(name)
        path = ROOT / relative
        if (relative.is_absolute() or ".." in relative.parts or path.is_symlink() or not path.is_file()
                or not path.resolve(strict=True).is_relative_to(ROOT)):
            parser.error(f"MCP input is not a regular in-checkout file: {name}")
        digest = sha256(path.read_bytes())
        if mcp_inputs.get(name) != digest:
            parser.error(f"protocol input hash differs from frozen candidate: {name}")
        inputs.setdefault(name, digest)
    inventory_digest, inventory = candidate_inventory()
    stdout, stderr = io.StringIO(), io.StringIO()
    loader = unittest.defaultTestLoader
    suite = unittest.TestSuite()
    for name in TEST_MODULES:
        spec = importlib.util.spec_from_file_location("m45_acceptance_" + Path(name).stem, ROOT / name)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"cannot load acceptance input: {name}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        suite.addTests(loader.loadTestsFromModule(module))
    runner = unittest.TextTestRunner(stream=stdout, verbosity=2, buffer=True)
    result = runner.run(suite)
    actual_outcomes = raw_test_outcomes(stdout.getvalue())
    required_outcomes = expected_roster()
    roster_valid = (
        result.testsRun == len(required_outcomes) and not result.skipped
        and sorted(actual_outcomes, key=lambda item: (item["testCase"], item["testName"]))
        == sorted(required_outcomes, key=lambda item: (item["testCase"], item["testName"]))
    )
    case_outcomes = {
        f"SC-{number:03}": [item for item in required_outcomes if f"test_sc{number:03}_" in item["testName"]]
        for number in range(2, 8)
    }
    if any(not case for case in case_outcomes.values()):
        raise RuntimeError("lifecycle/presentation acceptance roster has a missing SC-002..SC-007 case")
    post_head = git_text("rev-parse", "HEAD")
    post_status = git_text("status", "--porcelain=v1", "--untracked-files=all")
    post_inventory_digest, post_inventory = candidate_inventory()
    post_protocol_sha256 = sha256(protocol_path.read_bytes()) if protocol_path.is_file() else None
    post_raw_sha256 = sha256(raw_path.read_bytes()) if raw_path.is_file() else None
    candidate_stable = (
        post_head == head and not post_status and post_inventory_digest == inventory_digest
        and post_inventory == inventory and post_protocol_sha256 == protocol_sha256
        and post_raw_sha256 == test_command["rawOutputSha256"]
    )
    successful = result.wasSuccessful() and roster_valid and candidate_stable
    raw_stdout, raw_stderr = stdout.getvalue().encode("utf-8"), stderr.getvalue().encode("utf-8")
    (output / "stdout.txt").write_bytes(raw_stdout)
    (output / "stderr.txt").write_bytes(raw_stderr)
    (output / "stdout.txt").chmod(0o600); (output / "stderr.txt").chmod(0o600)
    proof = {
        "schema": "m45-lifecycle-presentation-acceptance/v1",
        "candidate": {"gitHead": head, "preRunInventorySha256": inventory_digest,
                      "preRunInventoryFileCount": len(inventory), "postRunGitHead": post_head,
                      "postRunStatus": post_status, "postRunInventorySha256": post_inventory_digest,
                      "postRunInventoryFileCount": len(post_inventory), "stableForFullRun": candidate_stable},
        "inputs": {name: {"sha256": digest, "bytes": (ROOT / name).stat().st_size}
                   for name, digest in inputs.items()},
        "execution": {
            "command": [sys.executable, *sys.argv],
            "cwd": str(ROOT),
            "environment": {"python": sys.version.split()[0], "implementation": platform.python_implementation(),
                            "platform": platform.platform(), "osName": os.name},
            "testCount": result.testsRun,
            "failures": len(result.failures),
            "errors": len(result.errors),
            "skipped": len(result.skipped),
            "expectedTestCount": len(required_outcomes),
            "expectedRosterCompleteAllOkAndNoSkips": roster_valid,
            "expectedTestRoster": required_outcomes,
            "rawTestOutcomes": actual_outcomes,
            "scenarioOutcomes": {scenario: {"outcome": "passed" if roster_valid else "incomplete_or_failed",
                                             "tests": [item for item in actual_outcomes
                                                       if item["testName"] in {test["testName"] for test in tests}]}
                                  for scenario, tests in case_outcomes.items()},
            "testsSuccessful": result.wasSuccessful(),
            "successful": successful,
            "networkOrHostProviderCalls": "none by procedure design; local temporary fixtures only",
        },
        "rawOutcomes": {
            "stdout": {"path": "stdout.txt", "sha256": sha256(raw_stdout), "bytes": len(raw_stdout)},
            "stderr": {"path": "stderr.txt", "sha256": sha256(raw_stderr), "bytes": len(raw_stderr)},
        },
        "protocolObservation": {
            "status": "healthy-local-sdk-stdio-peer",
            "receiptVersion": protocol_receipt["receiptVersion"],
            "receiptPath": str(protocol_path),
            "receiptSha256": protocol_sha256,
            "rawOutputPath": str(raw_path),
            "rawOutputSha256": test_command["rawOutputSha256"],
            "candidateBaseCommit": protocol_receipt["candidate"]["baseCommit"],
            "testOutcome": expected_test,
            "domain": "Actual MCP Python SDK stdio client against a local Agent Braid server; not a Codex or Claude host observation.",
            "doctorStatus": "remains intentionally pending; this peer receipt is separate and does not rewrite doctor output.",
        },
        "domain": "Local deterministic synthetic controls for SPEC-042 SC-002..SC-007 and SPEC-043 SC-002..SC-007.",
        "limits": [
            "Does not establish actual Codex or Claude host behavior, native rendering, provider behavior, clean-room reproduction, scientific validity, human review, or founder acceptance.",
            "Candidate inventory hash binds tracked and non-ignored untracked regular files at run time; output is stored outside the checkout.",
        ],
    }
    proof_path = output / "proof.json"
    proof_path.write_bytes(json_bytes(proof)); proof_path.chmod(0o600)
    print(json.dumps({"proof": str(proof_path), "successful": successful,
                      "tests": result.testsRun, "failures": len(result.failures), "errors": len(result.errors)},
                     sort_keys=True))
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
