# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-070 (BL.0): run each procedure's tests and write one evidence record per procedure.

A record states the command, the outcome, the hashes of the files the run depended on
(``inputs``; the Spec Kit validator rejects the record when any of them changes) and the
limits. The script also binds each record into ``assurance.json`` as obtained evidence of
its scenario. It is local evidence; the CI ``validate`` aggregate on the pull request head
is separate. Procedure 001 (owner review) and 009 (tracking) are not test procedures.

    python -m scripts.spec070_capture_evidence
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
SPEC = ROOT / "specs/070-braid-lightning-foundations"
EVIDENCE = SPEC / "evidence"
MODULES = ["agent_braid/lightning_schema.py", "agent_braid/lightning_config.py",
           "agent_braid/lightning_store.py", "agent_braid/lightning_cli.py"]

PROCEDURES = {
    "procedure_002": {
        "scenario": "SC-002",
        "modules": ["tests.test_lightning_cli.BoundaryTests.test_module_carries_upstream_notice"],
        "inputs": MODULES + ["tests/test_lightning_cli.py", "LICENSES/Agent-Lightning-MIT.txt",
                             "specs/070-braid-lightning-foundations/third-party-inventory.md",
                             "docs/development/THIRD_PARTY.md"],
        "outcome_note": "Every adapted module starts with the AGPL SPDX line and names microsoft/agent-lightning and the MIT License; the upstream license is retained verbatim and the inventory binds both pinned commits and original file hashes.",
        "limits": "The inventory hashes were computed from the pinned upstream commits at authoring time; this run checks notices, not a fresh upstream download.",
    },
    "procedure_003": {
        "scenario": "SC-003",
        "modules": ["tests.test_lightning_schema"],
        "inputs": ["agent_braid/lightning_schema.py", "tests/test_lightning_schema.py"],
        "outcome_note": "Rollout and event records round-trip byte-identically; unknown, missing, duplicate and non-finite inputs are refused with closed codes; transitions follow upstream VALID_TRANSITIONS; records carry no free-text content fields.",
        "limits": "Deterministic unit inputs only; no host, model or store concurrency is exercised.",
    },
    "procedure_004": {
        "scenario": "SC-004",
        "modules": ["tests.test_lightning_config"],
        "inputs": ["agent_braid/lightning_config.py", "tests/test_lightning_config.py",
                   "schemas/0.3.0-experimental/lightning-config.schema.json",
                   "specs/070-braid-lightning-foundations/contracts/lightning-config.md"],
        "outcome_note": "Defaults validate with EUR 0, subscription route, human promotion and executionAuthorization false fixed; every invalid profile in the corpus is refused by both the validator and the published JSON Schema.",
        "limits": "Agreement is shown on the tested corpus, not proven for all documents; the schema check needs the jsonschema development dependency.",
    },
    "procedure_005": {
        "scenario": "SC-005",
        "modules": ["tests.test_lightning_cli.WizardTests"],
        "inputs": ["agent_braid/lightning_cli.py", "agent_braid/lightning_config.py", "tests/test_lightning_cli.py"],
        "outcome_note": "Interactive and non-interactive previews write nothing; only the exact preview digest applies; a stale or wrong digest and --apply without --non-interactive are refused; validate and status report the profile.",
        "limits": "Prompts are simulated with patched input(); terminal behaviour on Windows is not exercised.",
    },
    "procedure_006": {
        "scenario": "SC-006",
        "modules": ["tests.test_lightning_store"],
        "inputs": ["agent_braid/lightning_store.py", "tests/test_lightning_store.py"],
        "outcome_note": "Run directories and files stay owner-only; content-bearing, unknown and mismatched kinds write nothing; symlinks and tampered lines are refused; sweep removes only expired runs and purge only the selected run.",
        "limits": "Single-process tests; the lock refuses a second writer but concurrent writers are not stress-tested.",
    },
    "procedure_007": {
        "scenario": "SC-007",
        "modules": ["tests.test_lightning_cli.SetupTests"],
        "inputs": ["agent_braid/plugin_registry.py", "agent_braid/plugin_cli.py", "tests/test_lightning_cli.py",
                   "integrations/agent-braid/plugin/setup/SKILL.md"],
        "outcome_note": "plugin setup --lightning lab stores the key with effects lines; off removes it and restores the earlier registry bytes and digest; unknown modes are refused; the setup skill describes the step without choosing for the user.",
        "limits": "Registry behaviour only; reconnect behaviour of a running MCP server is unchanged and not exercised here.",
    },
    "procedure_008": {
        "scenario": "SC-008",
        "modules": ["tests.test_lightning_cli.BoundaryTests"],
        "inputs": MODULES + ["tests/test_lightning_cli.py", "agent_braid/tooling_mcp.py", "agent_braid/plugin_mcp.py"],
        "outcome_note": "BL.0 modules import only the standard library and local Braid Lightning or registry modules, import no socket, subprocess, http, urllib or asyncio, and no MCP module mentions Braid Lightning.",
        "limits": "Static import inspection; it does not prove the absence of every possible side effect.",
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
            "procedure": name, "scenario": spec["scenario"], "specification": "SPEC-070 BL.0",
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
