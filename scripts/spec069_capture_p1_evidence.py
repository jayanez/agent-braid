# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-069 P1: run each procedure's tests and write one evidence record per procedure.

A record states the command, the outcome, the hashes of the files the run depended
on (``inputs``; the Spec Kit validator rejects the record when any of them changes)
and the limits. It is local evidence; the CI ``validate`` aggregate on the pull
request head is separate.

    python -m scripts.spec069_capture_p1_evidence
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
EVIDENCE = ROOT / "specs/069-aim-request-authoring/evidence"
SHARED_INPUTS = [
    "agent_braid/analysis.py", "agent_braid/git_adapter.py", "agent_braid/tooling_mcp.py",
    "schemas/0.2.0-draft/agent-interaction-metadata.schema.json",
    "schemas/0.1.0-alpha/analysis-input.schema.json",
    "schemas/0.1.0-alpha/git-analysis-request.schema.json",
    "schemas/0.1.0-alpha/analysis-report.schema.json",
]
PROCEDURES = {
    "procedure_002": {
        "requirement": "SC-002",
        "modules": ["tests.test_spec069_divergence_inventory"],
        "inputs": ["scripts/spec069_divergence_inventory.py", "tests/test_spec069_divergence_inventory.py",
                   "specs/069-aim-request-authoring/evidence/divergence-inventory.json",
                   "specs/069-aim-request-authoring/evidence/divergence-inventory-after-decisions.json"],
        "outcome_note": "Baseline inventory: 404 probes, 166 divergent, 10 root causes (threshold 15 not exceeded); the three 2026-11-05 divergences, adapter bounds, whitespace semantics and the missing envelope schema have rows; after the D8 decisions 74 probes remain divergent, all documented. Negative controls: a missing row and a stale inventory are detected.",
        "limits": "Probes are generated from schema keywords and a curated runtime-check catalogue; this is not an exhaustive proof over all inputs. Decisions are proposals under D8; no runtime acceptance changed.",
    },
    "procedure_003": {
        "requirement": "SC-003",
        "modules": ["tests.test_spec069_differential.DifferentialTests.test_envelope_schema_matches_runtime_on_aim_examples",
                    "tests.test_spec069_differential.DifferentialTests.test_envelope_schema_negative_controls"],
        "inputs": ["tests/test_spec069_differential.py", "tests/spec069_differential.py"],
        "outcome_note": "The envelope schema accepts every aim example under examples/analysis/ as the runtime does; an envelope with an extra field and one with empty operations are refused by both.",
        "limits": "Two example files have sourceKind aim; the 429-case corpus is covered by procedure_004.",
    },
    "procedure_004": {
        "requirement": "SC-004",
        "modules": ["tests.test_spec069_differential"],
        "inputs": ["scripts/spec069_generate_corpus.py", "tests/test_spec069_differential.py", "tests/spec069_differential.py",
                   "tests/fixtures/analysis-requests/aim.json", "tests/fixtures/analysis-requests/git.json"],
        "outcome_note": "429 corpus cases (310 aim, 119 git): every case matches its constructed expectation on the schema and on the complete service path; undocumented differences fail. Negative controls: a relaxed schema keyword (aim and git), a relaxed validator check and a tightened validator each fail the comparison.",
        "limits": "Corpus agreement is not proof over all inputs. Declared limits (ECMAScript whitespace, trailing newline after a digest, JSON 1.0) are tagged in the corpus. Git cases run against a one-commit temporary repository.",
    },
    "procedure_007": {
        "requirement": "SC-007",
        "modules": ["tests.test_spec069_refusals"],
        "inputs": ["tests/test_spec069_refusals.py", "tests/fixtures/analysis-requests/aim.json",
                   "tests/fixtures/analysis-requests/git.json"],
        "outcome_note": "Every structural refusal in the corpus names its JSON Pointer and expected form through the MCP analyze-work path; batch refusals carry fixed codes; messages are bounded. Negative controls: a secret-shaped unknown key and request values are not echoed, git output stays masked, and a missing path and an outside path return the same refusal.",
        "limits": "Pointers are checked against the corpus expectation (readVersions keys tokenized). The refusal text is not a versioned contract. No host model was involved.",
    },
    "procedure_009": {
        "requirement": "SC-009",
        "modules": ["tests.test_spec069_alpha7_replay", "tests.test_spec069_compatibility"],
        "inputs": ["scripts/spec069_record_alpha7.py", "tests/test_spec069_alpha7_replay.py", "tests/test_spec069_compatibility.py",
                   "specs/069-aim-request-authoring/evidence/alpha7-replay.json", "specs/069-aim-request-authoring/compatibility.md"],
        "outcome_note": "317 aim requests recorded from the alpha.7 runtime (source 0eb75d84): 103 accepted stay accepted with identical reports once the T015 label is stripped and analysisId recomputed; 214 not accepted stay not accepted. Tightened keywords equal the compatibility note; contract versions unchanged. Negative controls: a new refusal, changed report bytes and a loosened validator are detected.",
        "limits": "aim kind through ToolingService only; git requests are covered by the corpus, not replayed against alpha.7. The alpha.7 reports are bound by digest, not stored.",
    },
    "procedure_013": {
        "requirement": "SC-013",
        "shared": False,
        "modules": ["tests.test_spec069_native_runs"],
        "inputs": ["scripts/spec069_native_runs.py", "agent_braid/lightning_hosts.py", "tests/test_spec069_native_runs.py",
                   "specs/069-aim-request-authoring/runbook.md",
                   "tests/fixtures/spec069-fake-hosts/_fake.py", "tests/fixtures/spec069-fake-hosts/claude",
                   "tests/fixtures/spec069-fake-hosts/codex", "tests/fixtures/spec069-fake-hosts/opencode",
                   "tests/fixtures/spec069-fake-hosts/security",
                   "specs/069-aim-request-authoring/evidence/native-runs-baseline-anthropic.json"],
        "outcome_note": "The --fake-hosts self-test runs the whole pipeline (profiles, sandbox workspace, plugin install, headless runs, parsing, scoring, redaction, secret scan, evidence with hashes, teardown) with negative controls: a leaked real path stops the run, a planted fake secret is absent from the evidence, a denied tool is refused and one that runs stops the run, a leftover profile or process is detected. Real runs through the same driver completed unattended on Claude Code 2.1.292 and OpenCode 2.1.4 (60 runs, claude-sonnet-5-5, evidence/native-runs-baseline-anthropic.json, teardown clean, secret scan passed); the first real pass stopped on a built-in tool not in the deny list, which is now not offered at all.",
        "limits": "Codex: through the owner's subscription sign-in the driver completed real runs on 2026-11-11 (T010 evidence: 30 runs per arm, parser and MCP transcript shape exercised; the model id is not named in the stream and was read from the disposable Codex session logs), so Codex is no longer a declared limit for the development set; the ChatGPT usage limit can still stop a later run. The OS sandbox is macOS sandbox-exec only; the driver does not run on Windows or Linux real runs. The self-test proves the pipeline, not any host or model.",
    },
    "procedure_015": {
        "requirement": "SC-015",
        "modules": ["tests.test_spec069_declared_label",
                    "tests.test_spec069_alpha7_replay.ReplayTests.test_the_label_appears_exactly_for_declared_only_independent_candidates"],
        "inputs": ["tests/test_spec069_declared_label.py", "tests/test_spec069_alpha7_replay.py"],
        "outcome_note": "A declared-only independent-candidate pair carries completenessBasis; replay evidence on either record removes it; other classifications are never labelled; classification, reasons, constraints and evidence are unchanged; across the 103 replayed requests the label appears exactly for declared-only independent candidates.",
        "limits": "analysisId changes with the label because it digests the whole report; SC-015's 'byte-identical' holds after stripping the label and recomputing the digest.",
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
    status = 0
    only = set(sys.argv[1:])
    for name, spec in PROCEDURES.items():
        if only and name not in only:
            continue
        result = run(spec["modules"])
        passed = result["returncode"] == 0 and result["result"].startswith("OK")
        inputs = sorted(set((SHARED_INPUTS if spec.get("shared", True) else []) + spec["inputs"]))
        record = {
            "procedure": name, "scenario": spec["requirement"], "specification": "SPEC-069 P1",
            "command": result["command"], "testsRun": result["testsRun"], "result": result["result"],
            "outcome": ("passed: " if passed else "FAILED: ") + spec["outcome_note"],
            "limits": spec["limits"],
            "environment": {"python": platform.python_version(), "platform": platform.platform(terse=True)},
            "inputs": {path: sha(path) for path in inputs},
        }
        (EVIDENCE / f"{name}.json").write_text(json.dumps(record, indent=1, sort_keys=True) + "\n")
        print(f"{name}: {result['result']} ({result['testsRun']} tests)")
        status |= 0 if passed else 1
    return status


if __name__ == "__main__":
    raise SystemExit(main())
