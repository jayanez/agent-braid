# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-071 (BL.1): run each procedure's tests and write one evidence record per procedure.

A record states the command, the outcome, the hashes of the files the run depended on
(``inputs``; the Spec Kit validator rejects the record when any of them changes) and the
limits. The script also binds each record into ``assurance.json`` as obtained evidence of
its scenario. It is local evidence; the CI ``validate`` aggregate on the pull request head
is separate. Procedure 001 (owner review) and 014 (real baseline) are not test procedures.

    python -m scripts.spec071_capture_evidence
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "specs/071-lightning-rollouts-reward"
EVIDENCE = SPEC / "evidence"
PROCEDURES = {
    'procedure_002': {
        "scenario": 'SC-002',
        "modules": ["tests.test_spec069_native_runs"],
        "inputs": ["scripts/spec069_native_runs.py", "agent_braid/lightning_hosts.py", "tests/test_spec069_native_runs.py"],
        "outcome_note": "Host plumbing extracted to agent_braid/lightning_hosts.py; the SPEC-069 driver re-exports it and its 29 tests, including the --fake-hosts self-test with all negative controls, pass unchanged.",
        "limits": "Behaviour equivalence is shown by the driver test suite and the unchanged evidence format; the driver file hash recorded in its evidence changes by construction.",
    },
    'procedure_003': {
        "scenario": 'SC-003',
        "modules": ["tests.test_lightning_runner.PipelineTests.test_fake_pipeline_records_rewards_and_replays", "tests.test_lightning_runner.PipelineTests.test_timeout_fails_the_rollout", "tests.test_lightning_runner.PipelineTests.test_straggler_process_is_detected_and_killed"],
        "inputs": ["agent_braid/lightning_runner.py", "agent_braid/lightning_hosts.py", "agent_braid/lightning_reward.py", "agent_braid/lightning_hooks.py", "agent_braid/lightning_schema.py", "agent_braid/lightning_store.py", "tests/test_lightning_runner.py", "tests/fixtures/lightning-fake-hosts/claude", "tests/fixtures/lightning-fake-hosts/opencode"],
        "outcome_note": "Rollouts run sequentially in a disposable sandboxed profile, follow the SPEC-070 state machine, write rollout, event and attempt-result records through the store; a timeout fails the rollout; a straggler process is detected and killed at teardown.",
        "limits": "Fake hosts only; parallel greater than 1 is not implemented (the profile default and REQ-003 bound are 1).",
    },
    'procedure_004': {
        "scenario": 'SC-004',
        "modules": ["tests.test_lightning_runner.RouteTests", "tests.test_lightning_runner.PipelineTests.test_missing_key_source_stops_as_route_unverified", "tests.test_lightning_runner.PipelineTests.test_paid_key_in_environment_refuses_before_launch"],
        "inputs": ["agent_braid/lightning_runner.py", "agent_braid/lightning_hosts.py", "agent_braid/lightning_reward.py", "agent_braid/lightning_hooks.py", "agent_braid/lightning_schema.py", "agent_braid/lightning_store.py", "tests/test_lightning_runner.py", "tests/fixtures/lightning-fake-hosts/claude", "tests/fixtures/lightning-fake-hosts/opencode"],
        "outcome_note": "Any *_API_KEY or ANTHROPIC_AUTH_TOKEN/BASE_URL/Bedrock/Vertex variable is refused by name before launch; the host-reported apiKeySource is recorded; oauth (and none as the fixture assumption) is accepted; a missing or other source ends the run as route-unverified; OpenCode reports none and is a declared limit (OD-2).",
        "limits": "What a real subscription sign-in reports is not yet observed; the value none stays a fixture assumption until the real baseline (T012).",
    },
    'procedure_005': {
        "scenario": 'SC-005',
        "modules": ["tests.test_lightning_runner.PipelineTests.test_subscription_credential_is_passed_but_never_written", "tests.test_lightning_runner.PipelineTests.test_leaked_secret_is_caught"],
        "inputs": ["agent_braid/lightning_runner.py", "agent_braid/lightning_hosts.py", "agent_braid/lightning_reward.py", "agent_braid/lightning_hooks.py", "agent_braid/lightning_schema.py", "agent_braid/lightning_store.py", "tests/test_lightning_runner.py", "tests/fixtures/lightning-fake-hosts/claude", "tests/fixtures/lightning-fake-hosts/opencode"],
        "outcome_note": "A synthetic CLAUDE_CODE_OAUTH_TOKEN reaches the child environment only; credentialPresent is true and the value appears in no store file or status; a planted secret in host output stops the run as credential-leak and is absent from the store.",
        "limits": "Synthetic token only.",
    },
    'procedure_006': {
        "scenario": 'SC-006',
        "modules": ["tests.test_lightning_runner.RouteTests.test_quota_messages_map_to_budget_stop_names", "tests.test_lightning_runner.PipelineTests.test_unit_cap_stops_and_resume_is_explicit"],
        "inputs": ["agent_braid/lightning_runner.py", "agent_braid/lightning_hosts.py", "agent_braid/lightning_reward.py", "agent_braid/lightning_hooks.py", "agent_braid/lightning_schema.py", "agent_braid/lightning_store.py", "tests/test_lightning_runner.py", "tests/fixtures/lightning-fake-hosts/claude", "tests/fixtures/lightning-fake-hosts/opencode"],
        "outcome_note": "Quota messages map to _BUDGET_STOPS names; budget.maxRollouts ends the run with unit-cap; the same run id continues only with an explicit resume and skips completed rollouts; resume without a run id is refused.",
        "limits": "Quota message patterns are assumptions until observed on a real host.",
    },
    'procedure_007': {
        "scenario": 'SC-007',
        "modules": ["tests.test_lightning_runner.HookTests", "tests.test_lightning_runner.PipelineTests.test_failing_hook_fails_only_its_rollout"],
        "inputs": ["agent_braid/lightning_runner.py", "agent_braid/lightning_hosts.py", "agent_braid/lightning_reward.py", "agent_braid/lightning_hooks.py", "agent_braid/lightning_schema.py", "agent_braid/lightning_store.py", "tests/test_lightning_runner.py", "tests/fixtures/lightning-fake-hosts/claude", "tests/fixtures/lightning-fake-hosts/opencode"],
        "outcome_note": "Hooks run in upstream order on deep read-only copies; a raising hook fails only its rollout (hook-failed); unknown hook names are refused.",
        "limits": "Synchronous hooks only.",
    },
    'procedure_008': {
        "scenario": 'SC-008',
        "modules": ["tests.test_lightning_runner.RewardTests"],
        "inputs": ["agent_braid/lightning_runner.py", "agent_braid/lightning_hosts.py", "agent_braid/lightning_reward.py", "agent_braid/lightning_hooks.py", "agent_braid/lightning_schema.py", "agent_braid/lightning_store.py", "tests/test_lightning_runner.py", "tests/fixtures/lightning-fake-hosts/claude", "tests/fixtures/lightning-fake-hosts/opencode", "scripts/spec069_scoring.py", "specs/069-aim-request-authoring/prompts/FREEZE.json"],
        "outcome_note": "The reward vector matches score_case, is byte-identical for equal inputs, never credits an uncalled tool, zeroes D4 on a canary hit, and refuses changed scoring rules or prompt sets.",
        "limits": "schemaValid is the runtime verdict, kept equivalent to the declared schema by the SPEC-069 differential test.",
    },
    'procedure_009': {
        "scenario": 'SC-009',
        "modules": ["tests.test_lightning_runner.PipelineTests.test_canary_hit_zeroes_d4", "tests.test_lightning_runner.RewardTests.test_changed_scoring_or_prompt_set_is_refused"],
        "inputs": ["agent_braid/lightning_runner.py", "agent_braid/lightning_hosts.py", "agent_braid/lightning_reward.py", "agent_braid/lightning_hooks.py", "agent_braid/lightning_schema.py", "agent_braid/lightning_store.py", "tests/test_lightning_runner.py", "tests/fixtures/lightning-fake-hosts/claude", "tests/fixtures/lightning-fake-hosts/opencode"],
        "outcome_note": "A canary token planted in a non-target workspace file is detected when it reaches the transcript and zeroes D4 for that rollout; the prompt-set and scoring hashes are checked against FREEZE before any run.",
        "limits": "The model cannot read files or reach the network because every built-in file, shell and web tool is denied (SPEC-069 allowlist); the OS sandbox denies real configuration paths but is not a network firewall. Fake hosts do not exercise sandbox-exec.",
    },
    'procedure_010': {
        "scenario": 'SC-010',
        "modules": ["tests.test_lightning_runner.PlanTests", "tests.test_lightning_runner.CliTests"],
        "inputs": ["agent_braid/lightning_runner.py", "agent_braid/lightning_hosts.py", "agent_braid/lightning_reward.py", "agent_braid/lightning_hooks.py", "agent_braid/lightning_schema.py", "agent_braid/lightning_store.py", "tests/test_lightning_runner.py", "tests/fixtures/lightning-fake-hosts/claude", "tests/fixtures/lightning-fake-hosts/opencode", "agent_braid/lightning_cli.py"],
        "outcome_note": "run --dry-run launches nothing and plans within budget; run without setup consent is refused (consent-required); --fake-hosts runs labelled pipeline-only; status and report work by run id; outputs carry executionAuthorization false.",
        "limits": "CLI tests use a temporary home.",
    },
    'procedure_011': {
        "scenario": 'SC-011',
        "modules": ["tests.test_lightning_runner.RewardTests.test_replay_from_parsed_attempts_is_byte_identical_and_detects_edits", "tests.test_lightning_runner.PipelineTests.test_fake_pipeline_records_rewards_and_replays"],
        "inputs": ["agent_braid/lightning_runner.py", "agent_braid/lightning_hosts.py", "agent_braid/lightning_reward.py", "agent_braid/lightning_hooks.py", "agent_braid/lightning_schema.py", "agent_braid/lightning_store.py", "tests/test_lightning_runner.py", "tests/fixtures/lightning-fake-hosts/claude", "tests/fixtures/lightning-fake-hosts/opencode"],
        "outcome_note": "Rewards recomputed from stored content-free parsed attempts hash to the recorded rewardSha256; an edited parsed attempt changes the hash; result records contain no prompt text.",
        "limits": "Transcript replay needs SPEC-074 consent and is not offered.",
    },
    'procedure_012': {
        "scenario": 'SC-012',
        "modules": ["tests.test_lightning_runner.BoundaryTests"],
        "inputs": ["agent_braid/lightning_runner.py", "agent_braid/lightning_hosts.py", "agent_braid/lightning_reward.py", "agent_braid/lightning_hooks.py", "agent_braid/lightning_schema.py", "agent_braid/lightning_store.py", "tests/test_lightning_runner.py", "tests/fixtures/lightning-fake-hosts/claude", "tests/fixtures/lightning-fake-hosts/opencode"],
        "outcome_note": "BL.1 modules import only the standard library (and the repository scripts lazily), open no listener, call no execute, recover or grant function, and no MCP module mentions Braid Lightning.",
        "limits": "Static inspection.",
    },
    'procedure_013': {
        "scenario": 'SC-013',
        "modules": ["tests.test_lightning_runner.PipelineTests"],
        "inputs": ["agent_braid/lightning_runner.py", "agent_braid/lightning_hosts.py", "agent_braid/lightning_reward.py", "agent_braid/lightning_hooks.py", "agent_braid/lightning_schema.py", "agent_braid/lightning_store.py", "tests/test_lightning_runner.py", "tests/fixtures/lightning-fake-hosts/claude", "tests/fixtures/lightning-fake-hosts/opencode"],
        "outcome_note": "The full fake-host pipeline passes; each negative variant (planted API key, missing key source, leaked secret, canary hit, straggler, timeout, hook failure, unit cap) yields its code or recorded outcome.",
        "limits": "Pipeline-only: proves the runner, not any host or model.",
    },
}


def sha(path: str) -> str:
    return hashlib.sha256((ROOT / path).read_bytes()).hexdigest()


def run(modules: list[str]) -> dict:
    command = [sys.executable, "-m", "unittest", *modules]
    process = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
    tail = process.stderr.strip().splitlines()[-3:]
    ran = re.search(r"Ran (\d+) tests?", process.stderr)
    return {"command": "python -m unittest " + " ".join(modules), "returncode": process.returncode,
            "testsRun": int(ran.group(1)) if ran else None, "result": tail[-1] if tail else ""}


def main() -> int:
    EVIDENCE.mkdir(exist_ok=True)
    assurance_path = SPEC / "assurance.json"
    assurance = json.loads(assurance_path.read_text())
    scenarios = {s["id"]: s for r in assurance["requirements"] for s in r["scenarios"]}
    status = 0
    for name, spec in PROCEDURES.items():
        result = run(spec["modules"])
        passed = result["returncode"] == 0 and result["result"].startswith("OK")
        record = {
            "procedure": name, "scenario": spec["scenario"], "specification": "SPEC-071 BL.1",
            "command": result["command"], "testsRun": result["testsRun"], "result": result["result"],
            "outcome": ("passed: " if passed else "FAILED: ") + spec["outcome_note"],
            "limits": spec["limits"],
            "environment": {"python": platform.python_version(), "platform": platform.platform(terse=True)},
            "inputs": {path: sha(path) for path in sorted(set(spec["inputs"]))},
        }
        path = EVIDENCE / f"{name}.json"
        path.write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
        relative = path.relative_to(ROOT).as_posix()
        scenarios[spec["scenario"]]["obtained_evidence"] = [{
            "command": result["command"], "limits": spec["limits"], "outcome": record["outcome"],
            "path": relative, "sha256": sha(relative)}]
        print(f"{name}: {result['result']} ({result['testsRun']} tests)")
        status |= 0 if passed else 1
    assurance_path.write_text(json.dumps(assurance, indent=2, sort_keys=True) + "\n")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
