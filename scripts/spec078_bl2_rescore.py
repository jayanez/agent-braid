# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T002: derived, content-free receipt of the BL.2 held-out re-scoring behind the HELD-02/04/06 diagnosis.

Re-scores the stored SPEC-072 held-out results (``results.jsonl`` of each arm's run in the local Lightning
lab state) with the unchanged SPEC-069 scorer and records, per failed first attempt, the rollout id, the
request kind and the scorer's first reason. Only the run ids, file hashes and scorer reasons are written.

    python -m scripts.spec078_bl2_rescore [--runs <lab runs directory>] > specs/078-lightning-heldout-v2/evidence/bl2-rescoring-receipt.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

from scripts import spec069_scoring

ROOT = Path(__file__).resolve().parents[1]
HELD_OUT = ROOT / "specs/069-aim-request-authoring/prompts/held-out.json"
ARMS = json.loads((ROOT / "specs/072-lightning-prompt-optimization/evidence/heldout-arms.json").read_text())["arms"]
DEFAULT_RUNS = Path.home() / ".local/state/agent-braid/lightning-lab/lightning/runs"


def receipt(runs: Path) -> dict:
    cases = {c["id"]: c for c in json.loads(HELD_OUT.read_text("utf-8"))["cases"]}
    arms = {}
    for arm, record in sorted(ARMS.items()):
        path = runs / record["runId"] / "results.jsonl"
        raw = path.read_bytes()
        failures = []
        for line in raw.decode("utf-8").splitlines():
            result = json.loads(line)
            case_id = result["rolloutId"].split(".")[1]
            attempts = result["parsedAttempts"]
            score = spec069_scoring.score_case(cases[case_id], attempts)
            if not score["validFirstAttempt"]:
                failures.append({"rolloutId": result["rolloutId"],
                                 "kind": attempts[0]["kind"] if attempts else None,
                                 "reason": score["reasons"][0]})
        arms[arm] = {"runId": record["runId"], "resultsSha256": hashlib.sha256(raw).hexdigest(),
                     "failedFirstAttempts": failures}
    return {"schema": "spec078-bl2-rescoring-receipt/v0.1",
            "scoringSha256": hashlib.sha256((ROOT / "scripts/spec069_scoring.py").read_bytes()).hexdigest(),
            "heldOutSha256": hashlib.sha256(HELD_OUT.read_bytes()).hexdigest(), "arms": arms}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--runs", type=Path, default=DEFAULT_RUNS)
    args = parser.parse_args(argv)
    json.dump(receipt(args.runs), sys.stdout, indent=1, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
