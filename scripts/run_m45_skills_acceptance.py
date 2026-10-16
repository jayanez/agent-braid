#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Capture SPEC-041 synthetic controls; never launch a host or grant acceptance.

Run as a module or script with an isolated Python 3.12+ interpreter. The bounded
process collector is shared with the existing offline controls. This instrument
does not accept commands, prompts, grant paths or host-launch options.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from agent_braid.tooling_assets import load_skill_bundle
from agent_braid.tooling_fixtures import load_inventory
from scripts.run_tooling_controls import _run_process


def _test(module: str, cls: str, name: str) -> str:
    return f"tests.test_tooling_{module}.{cls}.test_{name}"


CASES = {
    "SC-001": (
        _test("assets", "ToolingAssetTests", "source_checkout_inventory_is_ordered_hashed_and_bounded"),
        _test("assets", "ToolingAssetTests", "partial_installed_bundle_refuses"),
        _test("assets", "ToolingAssetTests", "unexpected_skill_payload_refuses"),
        _test("skills_acceptance", "SkillAcceptanceTests", "sc001_both_host_lifecycles_preserve_foreign_content"),
    ),
    "SC-002": (
        _test("skills_acceptance", "SkillAcceptanceTests", "sc002_immutable_analysis_and_read_version_conditions"),
        _test("presentation_acceptance", "PresentationAcceptance", "sc002_summary_agrees_with_every_classification_and_unknown_stays_unknown"),
    ),
    "SC-003": (
        _test("fixtures", "ToolingFixtureTests", "runtime_fixture_materializes_valid_request_and_read_only_prepare_parity"),
        _test("presentation_acceptance", "PresentationAcceptance", "sc003_summary_explains_missing_grant_and_records_limited_success_scope"),
    ),
    "SC-004": (
        _test("mcp_acceptance", "MpcAcceptance", "sc006_exact_grant_authority_positive_absent_wrong_scope_expired_reused"),
        _test("fixtures", "ToolingFixtureTests", "execute_fixture_positive_synthetic_grant_execute_status_verify_control"),
    ),
    "SC-005": (
        _test("fixtures", "ToolingFixtureTests", "recovery_fixture_positive_synthetic_interrupted_run_resume_and_verify_control"),
        _test("skills_acceptance", "SkillAcceptanceTests", "sc005_unknown_run_and_wrong_action_cannot_recover"),
    ),
    "SC-006": (
        _test("skills_acceptance", "SkillAcceptanceTests", "sc006_all_outcomes_survive_complete_export"),
        _test("presentation_acceptance", "PresentationAcceptance", "sc006_repeated_export_bytes_and_receipt_bind_exact_source_output_and_limits"),
        _test("mcp", "ToolingServiceTests", "artifact_corruption_is_rejected_in_manifest_and_chunk_reads"),
    ),
    "SC-007": (
        _test("skills_acceptance", "SkillAcceptanceTests", "sc007_missing_sdk_is_actionable_and_does_not_start_server"),
        _test("assets", "ToolingAssetTests", "default_loader_does_not_fall_back_to_source_checkout"),
        _test("mcp", "ToolingServiceTests", "runtime_mutations_are_not_advertised_or_dispatchable_by_default"),
    ),
    "SC-008": (
        _test("skills_acceptance", "SkillAcceptanceTests", "sc008_untrusted_text_cannot_issue_authority_or_read_outside_roots"),
        _test("presentation_acceptance", "PresentationAcceptance", "sc007_export_escapes_active_markup_and_refuses_unsafe_selection_and_size"),
        _test("assets", "ToolingAssetTests", "source_checkout_rejects_symlinked_skill_directory"),
    ),
}


def expected_tests() -> tuple[str, ...]:
    return tuple(sorted({name for names in CASES.values() for name in names}))


def native_capture_plan() -> dict:
    """Prepare coverage questions for M4.5; generate no attestation or permit."""
    inventory = load_inventory(source_checkout=True)
    return {
        "schema": "agent-braid-spec041-native-coverage-preparation-v1",
        "captureOwner": "M4.5 continuation / SPEC-044 T002",
        "launchAuthorized": False,
        "hosts": ["codex", "claude-code"],
        "bundle": load_skill_bundle(source_checkout=True).inventory(),
        "fixtureInventorySha256": inventory.inventory_sha256,
        "promptInventorySha256": inventory.prompts_sha256,
        "fixtureDefinitionSha256ById": {item.fixture_id: item.definition_sha256
                                        for item in inventory.fixtures},
        "promptSha256ById": {item.prompt_id: item.sha256 for item in inventory.prompts},
        "externalBindingsPending": ["M4.5 frozen candidate/wheel and materialized input digests",
                                    "authentic native host/process evidence and exact approval"],
        "requiredBindings": [
            "exact candidate, wheel, inputs, host build, model and configuration",
            "loaded instruction bytes; catalog visibility is insufficient",
            "authenticated process/configuration/quota and exact approval",
            "raw tool calls/results, operator authority and independent verify",
            "input/output digests, uncertainty, refusals and observation limits",
        ],
        "procedures": [{"host": host, "scenario": scenario,
                        "requirement": scenario.replace("SC-", "REQ-"),
                        "status": "not-observed", "syntheticControls": list(tests)}
                       for host in ("codex", "claude-code") for scenario, tests in CASES.items()],
        "limits": "Coverage checklist only; consume authenticated M4.5 receipts. "
                  "Synthetic streams or a model saying it loaded a skill are insufficient.",
    }


def summarize(records: list[dict], *, process_ok: bool, inputs_unchanged: bool) -> dict:
    names = [row.get("testId") for row in records]
    valid = (len(names) == len(expected_tests()) and len(set(names)) == len(names)
             and set(names) == set(expected_tests()))
    observed = {row.get("testId"): row.get("outcome") for row in records}
    cases = [{"scenario": scenario,
              "status": "passed" if valid and process_ok and inputs_unchanged
                        and all(observed.get(name) == "passed" for name in tests)
                        else "incomplete-or-failed",
              "tests": [{"testId": name, "outcome": observed.get(name, "not-observed")}
                        for name in tests]}
             for scenario, tests in CASES.items()]
    return {"status": "passed" if all(row["status"] == "passed" for row in cases)
                      else "incomplete-or-failed",
            "testInventoryMatches": valid, "inputsUnchanged": inputs_unchanged,
            "scenarios": cases, "nativeAcceptance": False, "completedOriginalTasks": []}


def reserve_output(path: Path) -> Path:
    path = path.expanduser().absolute()
    resolved = path.resolve()
    if resolved == ROOT or ROOT in resolved.parents or path.is_symlink() or path.exists():
        raise ValueError("output must be a new directory outside the checkout")
    resolved.mkdir(mode=0o700, parents=True, exist_ok=False)
    os.chmod(resolved, 0o700)
    return resolved


def _hash(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inputs() -> dict[str, str]:
    paths = {ROOT / name for name in (
        "CONSTITUTION.md", "GOVERNANCE.md", "pyproject.toml", "build_support.py",
        "requirements-dev.txt", "requirements-speckit.txt",
    )}
    for folder, pattern in (("agent_braid", "*.py"), ("scripts", "*.py"),
                            ("tests", "*.py"), ("integrations/agent-braid", "*"),
                            ("examples/tooling", "*"), ("specs/041-ai-tooling-skills", "*")):
        paths.update(path for path in (ROOT / folder).rglob(pattern) if path.is_file())
    if any(path.is_symlink() for path in paths):
        raise ValueError("capture inputs must not be symbolic links")
    return {path.relative_to(ROOT).as_posix(): _hash(path.read_bytes())
            for path in sorted(paths)}


class _Results(unittest.TextTestResult):
    def startTest(self, test):
        super().startTest(test)
        self.outcomes[test.id()] = "incomplete"

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes[test.id()] = "passed"

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes[test.id()] = "failed"

    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes[test.id()] = "error"

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes[test.id()] = "skipped"

    def addSubTest(self, test, subtest, err):
        super().addSubTest(test, subtest, err)
        if err is not None:
            self.outcomes[test.id()] = "failed"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = {}


def _worker() -> int:
    suite = unittest.defaultTestLoader.loadTestsFromNames(expected_tests())
    result = unittest.TextTestRunner(verbosity=2, resultclass=_Results).run(suite)
    records = [{"testId": name, "outcome": outcome}
               for name, outcome in sorted(result.outcomes.items())]
    print(json.dumps(records, sort_keys=True))
    return 0 if result.wasSuccessful() and not result.skipped else 1


def _write(path: Path, data: bytes) -> None:
    with path.open("xb") as stream:
        os.chmod(path, 0o600)
        stream.write(data)


def _source_state() -> dict:
    identity = subprocess.run(["git", "rev-parse", "HEAD", "HEAD^{tree}"], cwd=ROOT,
                              capture_output=True, text=True, check=True, timeout=10).stdout.splitlines()
    status = subprocess.run(["git", "status", "--porcelain=v1"], cwd=ROOT,
                            capture_output=True, text=True, check=True, timeout=10).stdout
    return {"commit": identity[0], "tree": identity[1], "status": status}


def capture(output: Path, *, timeout: int, before: dict, native: dict) -> dict:
    """Finalize failures after reservation while the output filesystem is writable."""
    # Env clears provider/auth/loader overrides. Git never reads global config.
    command = ["/usr/bin/env", "-i", f"PATH={Path(sys.executable).parent}:/usr/bin:/bin",
               "LANG=C.UTF-8", "GIT_CONFIG_NOSYSTEM=1", "GIT_CONFIG_GLOBAL=/dev/null",
               "GIT_TERMINAL_PROMPT=0", sys.executable, "-E", "-s", "-m",
               "scripts.run_m45_skills_acceptance", "--worker"]
    process = {"status": "not-started"}
    source_before = None
    source_after = None
    error = None
    report = summarize([], process_ok=False, inputs_unchanged=False)
    try:
        source_before = _source_state()
        _write(output / "native-capture-plan.json", (json.dumps(native, indent=2) + "\n").encode())
        process = {"status": "unknown"}
        process = _run_process(command, ROOT, timeout)
        for name in ("stdout", "stderr"):
            _write(output / (name + ".txt"), process[name].encode("utf-8"))
        records = json.loads(process["stdout"])
        if not isinstance(records, list) or any(not isinstance(row, dict) for row in records):
            raise ValueError("worker returned invalid test records")
        source_after = _source_state()
        report = summarize(records, process_ok=process["status"] == "passed"
                           and process.get("outputTruncated") is False,
                           inputs_unchanged=before == _inputs() and source_before == source_after)
    except (Exception, KeyboardInterrupt) as exc:
        # Preserve returned process metadata and any cleanup diagnostics attached
        # by the shared supervisor. An exception is never a zero-effect claim.
        error = f"{type(exc).__name__}: {exc}"
        if hasattr(exc, "owned_process_cleanup"):
            process["exceptionCleanup"] = exc.owned_process_cleanup
    process = {key: value for key, value in process.items() if key not in {"stdout", "stderr"}}
    report.update(schema="agent-braid-spec041-synthetic-capture-v1",
                  observedAtUtc=datetime.now(timezone.utc).isoformat(),
                  sourceStateBefore=source_before, sourceStateAfter=source_after, error=error,
                  inputSha256ByPath=before, process=process,
                  environment={"python": platform.python_version(), "platform": platform.platform()},
                  evidenceType="synthetic-controls-only",
                  limits=["No host/provider observation, human rating or original task acceptance.",
                          "Working-tree bytes are bound separately; HEAD does not identify uncommitted changes.",
                          "No OS-level network sandbox is established by this local harness."])
    _write(output / "receipt.json", (json.dumps(report, indent=2, sort_keys=True) + "\n").encode())
    files = {path.name: _hash(path.read_bytes()) for path in sorted(output.iterdir())}
    _write(output / "manifest.json", (json.dumps(files, indent=2, sort_keys=True) + "\n").encode())
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--timeout", type=int, default=300, choices=range(1, 601), metavar="1..600")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        if args.output_root is not None:
            parser.error("worker does not accept an output path")
        return _worker()
    if args.output_root is None or os.name != "posix":
        parser.error("a POSIX host and --output-root are required")
    try:
        before = _inputs()
        native = native_capture_plan()
        output = reserve_output(args.output_root)
    except (OSError, ValueError) as exc:
        parser.error(str(exc))
    try:
        report = capture(output, timeout=args.timeout, before=before, native=native)
    except OSError as exc:
        # Full disk or lost permissions can prevent even a failure receipt.
        print(f"capture output unavailable; retained directory: {output}: {exc}", file=sys.stderr)
        return 1
    print(json.dumps({"status": report["status"], "scenarios": len(report["scenarios"]),
                      "receipt": str(output / "receipt.json"), "nativeAcceptance": False}))
    return 0 if report["status"] == "passed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
