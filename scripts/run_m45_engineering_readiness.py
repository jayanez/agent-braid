#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Run bounded offline M4.5 engineering controls into a private receipt.

This procedure runs source-level deterministic tests only. It does not read
provider credentials, create or approve a registration, admit capture, or
observe Codex/Claude hosts. Its balanced 108-slot roster result is the
synthetic unit-test contract, not an actual registered roster.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import signal
import subprocess
import sys
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
TEST_MODULES = (
    "tests.test_tooling_assets",
    "tests.test_tooling_evaluation",
    "tests.test_tooling_subscription",
    "tests.test_tooling_capture",
    "tests.test_tooling_model_identity",
    # T013's current engineering boundary: cost accounting and resource/cap
    # enforcement are tested together with the original admission surfaces.
    "tests.test_tooling_money",
    "tests.test_tooling_costs",
    "tests.test_tooling_allocation",
    "tests.test_tooling_full_cost",
    "tests.test_tooling_measurements",
    "tests.test_tooling_supervisor",
    "tests.test_tooling_incremental_usage",
    "tests.test_tooling_sessions",
    "tests.test_tooling_host_events",
    "tests.test_tooling_evaluation_report",
)
INPUT_PATHS = (
    "scripts/run_m45_engineering_readiness.py",
    "agent_braid/tooling_assets.py",
    "agent_braid/tooling_evaluation.py",
    "agent_braid/tooling_subscription.py",
    "agent_braid/tooling_capture.py",
    "agent_braid/tooling_model_identity.py",
    "agent_braid/tooling_money.py",
    "agent_braid/tooling_costs.py",
    "agent_braid/tooling_allocation.py",
    "agent_braid/tooling_full_cost.py",
    "agent_braid/tooling_measurements.py",
    "agent_braid/tooling_supervisor.py",
    "agent_braid/tooling_incremental_usage.py",
    "agent_braid/tooling_sessions.py",
    "agent_braid/tooling_host_events.py",
    "agent_braid/tooling_evaluation_report.py",
    "tests/test_tooling_assets.py",
    "tests/test_tooling_evaluation.py",
    "tests/test_tooling_subscription.py",
    "tests/test_tooling_capture.py",
    "tests/test_tooling_model_identity.py",
    "tests/test_tooling_money.py",
    "tests/test_tooling_costs.py",
    "tests/test_tooling_allocation.py",
    "tests/test_tooling_full_cost.py",
    "tests/test_tooling_measurements.py",
    "tests/test_tooling_supervisor.py",
    "tests/test_tooling_incremental_usage.py",
    "tests/test_tooling_sessions.py",
    "tests/test_tooling_host_events.py",
    "tests/test_tooling_evaluation_report.py",
    "specs/044-ai-tooling-evaluation/spec.md",
    "specs/044-ai-tooling-evaluation/evaluation-protocol.md",
    "specs/044-ai-tooling-evaluation/human-evaluation-deferral-clarification.md",
    "specs/044-ai-tooling-evaluation/model-identity-clarification.md",
    "specs/044-ai-tooling-evaluation/tasks.md",
    "specs/044-ai-tooling-evaluation/assurance.json",
)
EXPECTED_SKILLS = (
    "agent-braid-analyze",
    "agent-braid-plan",
    "agent-braid-execute",
    "agent-braid-recover",
    "agent-braid-evidence",
)
MAX_SECONDS = 900
MAX_RAW_BYTES = 64 * 1024 * 1024


class ReadinessError(RuntimeError):
    pass


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("ascii")


def write_private(path: Path, data: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def git(args: list[str]) -> bytes:
    return subprocess.run(["git", *args], cwd=ROOT, check=True,
                          stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          timeout=30).stdout


def candidate_inventory() -> tuple[str, dict[str, str]]:
    paths = git(["ls-files", "-co", "--exclude-standard", "-z"]).split(b"\0")
    inventory: dict[str, str] = {}
    for raw in paths:
        if not raw:
            continue
        name = raw.decode("utf-8", "strict")
        path = ROOT / name
        if path.is_file() and not path.is_symlink():
            inventory[name] = sha256(path.read_bytes())
    return sha256(json_bytes(inventory)), inventory


def skill_inventory() -> dict[str, object]:
    from agent_braid import tooling_assets

    source_root = ROOT / "integrations/agent-braid/skills"
    rows = []
    for name in EXPECTED_SKILLS:
        path = source_root / name / "SKILL.md"
        if path.is_symlink() or not path.is_file():
            raise ReadinessError(f"required source skill is unavailable: {name}")
        raw = path.read_bytes()
        rows.append({"name": name, "path": path.relative_to(ROOT).as_posix(),
                     "bytes": len(raw), "sha256": sha256(raw)})
    present = sorted(p.name for p in source_root.iterdir() if p.is_dir())
    if present != sorted(EXPECTED_SKILLS):
        raise ReadinessError("source skill directory roster differs from the five-skill contract")
    bundle_hash = hashlib.sha256()
    bundle_hash.update(b"agent-braid-skill-bundle\0")
    bundle_version = tooling_assets.SKILL_BUNDLE_VERSION
    bundle_hash.update(bundle_version.encode("ascii"))
    bundle_hash.update(b"\0")
    for row in rows:
        bundle_hash.update(row["name"].encode("utf-8"))
        bundle_hash.update(b"\0")
        bundle_hash.update(bytes.fromhex(row["sha256"]))
    return {"kind": "static-source-contract", "nativeHostBehaviorObserved": False,
            "skillCount": len(rows), "bundleVersion": bundle_version,
            "bundleSha256": bundle_hash.hexdigest(), "skills": rows}


def process_group(argv: list[str], *, cwd: Path, env: dict[str, str],
                  stdout_path: Path, stderr_path: Path) -> dict[str, object]:
    started = datetime.now(timezone.utc).isoformat()
    monotonic_start = time.monotonic()
    timed_out = False
    with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
        os.chmod(stdout_path, 0o600)
        os.chmod(stderr_path, 0o600)
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=stdout, stderr=stderr,
                                start_new_session=True)
        try:
            return_code = proc.wait(timeout=MAX_SECONDS)
        except subprocess.TimeoutExpired:
            timed_out = True
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
            try:
                return_code = proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                return_code = proc.wait(timeout=5)
    stdout_raw, stderr_raw = stdout_path.read_bytes(), stderr_path.read_bytes()
    return {
        "argv": argv,
        "cwd": str(cwd),
        "startedAtUtc": started,
        "finishedAtUtc": datetime.now(timezone.utc).isoformat(),
        "durationMs": int((time.monotonic() - monotonic_start) * 1000),
        "timeoutSeconds": MAX_SECONDS,
        "returnCode": return_code,
        "timedOut": timed_out,
        "outputLimitBytes": MAX_RAW_BYTES,
        "outputLimitExceeded": len(stdout_raw) > MAX_RAW_BYTES or len(stderr_raw) > MAX_RAW_BYTES,
        "stdout": {"path": stdout_path.name, "bytes": len(stdout_raw), "sha256": sha256(stdout_raw)},
        "stderr": {"path": stderr_path.name, "bytes": len(stderr_raw), "sha256": sha256(stderr_raw)},
    }


def parse_unittest(stdout_path: Path, stderr_path: Path) -> dict[str, object]:
    raw = stdout_path.read_bytes() + b"\n" + stderr_path.read_bytes()
    text = raw.decode("utf-8", "replace")
    matches = re.findall(r"Ran (\d+) tests? in [^\n]+", text)
    if not matches:
        return {"testCount": None, "failures": None, "errors": None,
                "skipped": None, "summaryParsed": False}
    test_count = int(matches[-1])
    failure_match = re.search(r"FAILED \(([^)]*)\)", text)
    if failure_match:
        summary = failure_match.group(1)
        values = {name: int(value) for name, value in
                  re.findall(r"(failures|errors|skipped)=(\d+)", summary)}
        failures = values.get("failures", 0)
        errors = values.get("errors", 0)
        skipped = values.get("skipped", 0)
    else:
        skipped_match = re.search(r"OK \(skipped=(\d+)\)", text)
        failures, errors = 0, 0
        skipped = int(skipped_match.group(1)) if skipped_match else 0
    return {"testCount": test_count, "failures": failures, "errors": errors,
            "skipped": skipped, "summaryParsed": True,
            "balancedRosterTestObserved": "test_roster_has_108_slots_and_balances_order_per_host_and_class" in text,
            "registrationGuardTestsObserved": [
                name for name in (
                    "test_v3_technical_capture_requires_deferral_roles_and_every_existing_admission_gate",
                    "test_v3_technical_capture_admits_one_slot_only_with_all_frozen_and_live_gates",
                    "test_registration_requires_exact_hashes_rights_provider_opt_in_and_caps",
                    "test_registration_refuses_nonfinite_values_and_unfrozen_rubric",
                ) if name in text
            ]}


def readiness_facts() -> dict[str, object]:
    from agent_braid import tooling_evaluation as evaluation

    registration_path = ROOT / "specs/044-ai-tooling-evaluation/registration.json"
    registration_present = registration_path.is_file() and not registration_path.is_symlink()
    registration = {
        "path": registration_path.relative_to(ROOT).as_posix(),
        "present": registration_present,
        "sha256": sha256(registration_path.read_bytes()) if registration_present else None,
        "approvalInterpreted": False,
        "captureAdmissionExecuted": False,
    }
    roster = {
        "hosts": list(evaluation.HOSTS),
        "arms": list(evaluation.ARMS),
        "journeyClasses": list(evaluation.JOURNEY_CLASSES),
        "fixtureInstancesPerJourney": 3,
        "expectedIntendedSlots": len(evaluation.HOSTS) * len(evaluation.ARMS)
                                  * len(evaluation.JOURNEY_CLASSES) * 3,
        "meaning": "protocol shape exercised by synthetic unit tests; not a frozen registered roster",
    }
    return {
        "registration": registration,
        "rosterContract": roster,
        "providerCalls": 0,
        "providerCredentialsRead": False,
        "accountIdentityOrHashCollected": False,
        "modelIdentity": "synthetic validator tests only; no live provider model was observed",
        "humanRatingsOrAdjudication": "not performed; human phase remains a separate gate",
        "actualCodexOrClaudeHostObservation": False,
        "sourceRightsDecision": "not made by this engineering procedure",
        "captureAuthorizationOrApprovalClaimed": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True,
                        help="new private evidence directory outside the source checkout")
    args = parser.parse_args()
    output = Path(args.output).expanduser().absolute()
    if output.resolve(strict=False).is_relative_to(ROOT):
        parser.error("evidence output must be outside the source checkout")
    if output.exists() or output.is_symlink():
        parser.error("evidence output must be a new non-symlink path")
    if sys.version_info < (3, 12):
        parser.error("Python 3.12 or newer is required; no dependencies are installed by this procedure")

    missing = [name for name in INPUT_PATHS if not (ROOT / name).is_file()]
    if missing:
        parser.error("required engineering inputs unavailable: " + ", ".join(missing))
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    output.chmod(0o700)
    private_home, private_tmp = output / "home", output / "tmp"
    private_home.mkdir(mode=0o700)
    private_tmp.mkdir(mode=0o700)

    try:
        git_head = git(["rev-parse", "HEAD"]).decode().strip()
        git_status_raw = git(["status", "--porcelain=v1", "--untracked-files=all"])
        inventory_sha, inventory = candidate_inventory()
        skills = skill_inventory()
        facts = readiness_facts()
    except (subprocess.SubprocessError, OSError, UnicodeError, ReadinessError) as exc:
        parser.error(f"candidate preflight failed: {exc}")

    inputs = {
        name: {"bytes": (ROOT / name).stat().st_size,
               "sha256": sha256((ROOT / name).read_bytes())}
        for name in INPUT_PATHS
    }
    for row in skills["skills"]:
        inputs[row["path"]] = {"bytes": row["bytes"], "sha256": row["sha256"]}

    # Strip provider tokens and global host configuration. Unit tests get a
    # private HOME/TMPDIR and cannot inherit API-key environment variables.
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": str(private_home),
        "TMPDIR": str(private_tmp),
        "TMP": str(private_tmp),
        "TEMP": str(private_tmp),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "PIP_CONFIG_FILE": "/dev/null",
        "PIP_NO_INDEX": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    }
    argv = [sys.executable, "-m", "unittest", "-v", *TEST_MODULES]
    stdout_path, stderr_path = output / "stdout.raw", output / "stderr.raw"
    command = process_group(argv, cwd=ROOT, env=env,
                            stdout_path=stdout_path, stderr_path=stderr_path)
    test_result = parse_unittest(stdout_path, stderr_path)
    required_control_tests = (
        "test_provider_cash_excludes_reviewer_fees_and_unknown_provider_coverage",
        "test_missing_registered_cost_component_is_unknown_and_stops",
        "test_subscription_only_preflight_and_periodic_stop",
        "test_live_cap_reached_stops_without_claiming_success",
        "test_sample_count_limit_fails_closed",
        "test_file_and_directory_inventory_limits_fail_closed",
        "test_full_cost_scope_must_be_present_approved_and_resolved",
        "test_provider_accounting_cap_cannot_be_hidden_by_zero_cash_or_reference_estimates",
        "test_registration_or_ledger_mismatch_is_rejected",
    )
    raw_output = stdout_path.read_bytes() + b"\n" + stderr_path.read_bytes()
    visible_tests = [name for name in required_control_tests if name.encode("ascii") in raw_output]
    test_result["requiredCostCapAndAdmissionControls"] = list(required_control_tests)
    test_result["observedCostCapAndAdmissionControls"] = visible_tests
    test_result["allRequiredCostCapAndAdmissionControlsObserved"] = len(visible_tests) == len(required_control_tests)
    inventory_after_sha, inventory_after = candidate_inventory()
    git_status_after_raw = git(["status", "--porcelain=v1", "--untracked-files=all"])
    candidate_stable = inventory_after_sha == inventory_sha and git_status_after_raw == git_status_raw
    raw_size_ok = (command["stdout"]["bytes"] <= MAX_RAW_BYTES
                   and command["stderr"]["bytes"] <= MAX_RAW_BYTES)
    success = bool(command["returnCode"] == 0 and not command["timedOut"]
                   and not command["outputLimitExceeded"] and raw_size_ok
                   and test_result["summaryParsed"] and test_result["testCount"]
                   and test_result["failures"] == 0 and test_result["errors"] == 0
                   and test_result["skipped"] == 0
                   and test_result["balancedRosterTestObserved"]
                   and test_result["allRequiredCostCapAndAdmissionControlsObserved"]
                   and candidate_stable)

    status_raw = git_status_raw.decode("utf-8", "replace")
    receipt = {
        "schema": "agent-braid-m45-engineering-readiness/v1",
        "observedAtUtc": datetime.now(timezone.utc).isoformat(),
        "outcome": "passed" if success else "failed",
        "candidate": {"gitHead": git_head, "inventorySha256": inventory_sha,
                      "inventoryFileCount": len(inventory),
                      "inventoryFiles": inventory,
                      "inventoryAfterSha256": inventory_after_sha,
                      "inventoryStableDuringRun": candidate_stable,
                      "gitStatusSha256": sha256(git_status_raw),
                      "gitStatus": status_raw.splitlines(),
                      "gitStatusAfter": git_status_after_raw.decode("utf-8", "replace").splitlines()},
        "inputs": inputs,
        "execution": {
            "command": argv,
            "cwd": str(ROOT),
            "environment": {
                "python": sys.version,
                "pythonExecutable": sys.executable,
                "implementation": platform.python_implementation(),
                "platform": platform.platform(),
                "osName": os.name,
                "providerEnvironmentVariablesInherited": False,
                "privateHome": True,
                "privateTemporaryDirectory": True,
                "networkCalls": "none by test procedure design; no host/provider is invoked; OS network isolation is not enforced",
            },
            "timeoutSeconds": MAX_SECONDS,
            "testRun": command,
            "testSummary": test_result,
        },
        "staticSkillSourceContract": skills,
        "readiness": facts,
        "limits": [
            "The 108-slot balance is a synthetic protocol/unit-test contract, not an approved or actual registered roster.",
            "Registration presence is recorded only; approval and source-right values are not inferred or adjudicated here.",
            "No native host behavior, provider/account identity, live model identity, capture, human scoring, legal review, or scientific result was observed.",
            "This receipt is bound to the recorded HEAD and worktree inventory; later candidate changes require a new run.",
        ],
    }
    receipt_path = output / "receipt.json"
    write_private(receipt_path, json_bytes(receipt))
    result = {"outcome": receipt["outcome"], "receipt": str(receipt_path),
              "receiptSha256": sha256(receipt_path.read_bytes()),
              "testCount": test_result["testCount"], "failures": test_result["failures"],
              "errors": test_result["errors"], "skipped": test_result["skipped"],
              "candidateHead": git_head, "inventorySha256": inventory_sha}
    print(json.dumps(result, sort_keys=True))
    return 0 if success else 1


if __name__ == "__main__":
    raise SystemExit(main())
