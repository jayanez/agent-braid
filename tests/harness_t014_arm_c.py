# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-049 T014 offline arm C: a deterministic contrastive proposer, synthetic-control only.

Replaces the T005 keep-base round with a round that can select a candidate. The proposer
contrasts the discovery base attempt with the discovery task's visible requirements and
turns each observed failure signal into one edit from a closed catalog of arm-B directive
lines, one signal per scope. The prober runs the R13 guidance double on the discovery unit
only and scores it with the unit's frozen oracle. Holdout cases never reach the proposer or
the prober.

This shows that the propose-probe-select-register path produces an arm C that is neither A
nor B and that the three-arm report carries it. C scores above B on coordination only because
the rubric grades a drift stop as not completed: the prober drops the stop-on-drift edit for
that reason, so C removes a safety directive. That is an artifact, not an improvement. It shows nothing about whether refinement
helps: the proposer is scripted, and the double encodes the effect the oracle measures.
Every result is ``synthetic-control`` and not a verdict input. Nothing reads a clock, host,
model, network or paid route, and no additional cash is spent. It changes no T005 frozen
record; a T014 registration of this arm C needs its own owner freeze before any run.
``python -m tests.harness_t014_arm_c`` prints the result record.
"""
from __future__ import annotations

from hashlib import sha256
import json
import sys
from typing import Any

from agent_braid import harness_evaluation as ev
from agent_braid import harness_manifest as manifests
from agent_braid import harness_refinement as ref
from agent_braid import harness_verification as ver
from agent_braid.system_one import canonical
from tests import harness_guidance_double as double
from tests import harness_t005_cohort as t005

HEADER = double.arm_files("B")[double.GUIDANCE_PATH].decode().split("\n")[0] + "\n"
_LINE = {switch: line for line, switch in double.GRAMMAR.items()}
# Failure signal -> (scope, exact arm-B directive line). Closed: nothing else is proposed.
CATALOG = {
    "repeated-completed-steps": ("general", _LINE["resume-from-checkpoint"]),
    "continued-past-drift": ("task", _LINE["stop-on-drift"]),
}
RATIONALE = "contrastive: discovery base failure signal mapped to one catalog directive"
ADDITIONAL_CASH_EUR = 0


def discovery_signals() -> tuple[str, ...]:
    """Failure signals of the discovery base attempt against the discovery case fixture.

    ``continued-past-drift`` reads the fixture's drift flag, which the base record does not
    show; only the discovery case is read."""
    case = double.CASES[t005.DISCOVERY]
    record = double.run(t005.DISCOVERY, {}, candidate_sha256=double.ARM_SHA256["A"]).to_dict()
    signals = set()
    if record["repeated"]:
        signals.add("repeated-completed-steps")
    if case["drift"] and case["checkpoint"] is not None and record["terminal"] == "completed":
        signals.add("continued-past-drift")
    return tuple(sorted(signals))


def make_proposer(manifest: manifests.HarnessManifest, signals: tuple[str, ...]):
    """``propose(scope)``: one guidance file with the scope's catalog lines, or abstain."""
    if not set(signals) <= set(CATALOG):
        raise ValueError("unknown-signal")

    proposed: dict[str, bytes] = {}

    def propose(scope: str) -> dict | None:
        lines = [CATALOG[s][1] for s in sorted(signals) if CATALOG[s][0] == scope]
        if not lines:
            return None
        text = HEADER + "\n" + "".join(f"{line}\n" for line in lines)
        changes = {double.GUIDANCE_PATH: text.encode()}
        proposed[double.inventory_sha256(changes)] = changes[double.GUIDANCE_PATH]
        return {"parentManifestSha256": manifest.sha256, "scope": scope,
                "changes": changes, "rationale": RATIONALE}

    propose.proposed = proposed  # candidate hash -> guidance bytes, as actually proposed
    return propose


def probe_case(case_id: str, units: dict[str, ver.Unit], manifest: manifests.HarnessManifest):
    """``probe(request)`` on one discovery case; a holdout case is refused."""
    if units[case_id].partition != "discovery":
        raise ValueError("holdout-probe")
    unit = units[case_id]

    def probe(request: ref.ProbeRequest) -> dict:
        files = dict(request.changes)
        _, commitment, outputs = t005.attempt(case_id, unit, files, request.candidate_sha256,
                                              f"discovery-{request.scope}", manifest.sha256)
        terminal, score = commitment.data["terminal"], None
        if terminal == "completed":  # an interrupted run commits nothing to grade
            oracle = ver.verify_unit(unit, commitment, outputs).to_dict()["oracle"]["verdict"]
            if oracle not in ver.VERDICTS:
                raise ValueError("ungraded-probe")
            score = ver.MAX_SCORE_MICROS if oracle == "pass" else 0
        return {"terminal": terminal, "score": score,
                "observationSha256": commitment.data["observationSha256"]}

    return probe


def contrastive_round(units: dict[str, ver.Unit]):
    """Run the round; return manifest, policy, decision and the chosen candidate's files."""
    manifest, policy = t005.build_manifest()
    propose = make_proposer(manifest, discovery_signals())
    decision = ref.run_round(manifest, policy, propose=propose,
                             probe=probe_case(t005.DISCOVERY, units, manifest))
    chosen = decision.to_dict()["chosenCandidateSha256"]
    if chosen is None:
        return manifest, policy, decision, {}
    if chosen not in propose.proposed:
        raise ValueError("chosen-files-unknown")  # composed candidates are not mapped here
    return manifest, policy, decision, {double.GUIDANCE_PATH: propose.proposed[chosen]}


def run_cohort() -> dict[str, Any]:
    """Register A, B and the contrastive C, then run the holdout once with the double."""
    units = t005.build_units()
    manifest, policy, decision, c_files = contrastive_round(units)
    registration = t005.register(units, decision)
    candidates = {arm: registration.data["arms"][arm]["candidateSha256"] for arm in ev.ARMS}
    files = {"A": double.arm_files("A"), "B": double.arm_files("B"), "C": c_files}
    rows, entries = [], []
    for case in t005.HOLDOUT:
        for arm in ev.ARMS:
            attempt_id = f"t014-{case}-{arm}"
            _, commitment, outputs = t005.attempt(case, units[case], files[arm], candidates[arm],
                                                  attempt_id, manifest.sha256)
            rows.append({"arm": arm, "attemptId": attempt_id, "reservationSha256": None,
                         "commitment": commitment,
                         "verdict": ver.verify_unit(units[case], commitment, outputs)})
            entries.append({"id": f"cost-{attempt_id}", "phase": "verification",
                            "attempt": attempt_id,
                            "measures": {k: dict(t005.UNKNOWN_COST) for k in t005.COST_KEYS}})
    report = ev.evaluate(registration, rows, cost_entries=entries, reservations=[])
    return {"manifest": manifest, "policy": policy, "decision": decision, "armCFiles": c_files,
            "registration": registration, "report": report,
            "additionalCashEur": ADDITIONAL_CASH_EUR}


def results() -> dict[str, Any]:
    """Deterministic, JSON-ready result of one offline run."""
    run = run_cohort()
    report = run["report"].to_dict()
    return {
        "label": double.LABEL, "verdictEligible": False, "executionAuthorization": False,
        "signals": list(discovery_signals()),
        "refinementDecisionSha256": run["decision"].sha256,
        "refinement": report["refinement"],
        "armC": {"candidateSha256": run["decision"].to_dict()["chosenCandidateSha256"],
                 "files": {p: {"sha256": sha256(c).hexdigest(), "text": c.decode()}
                           for p, c in run["armCFiles"].items()}},
        "registrationSha256": run["registration"].sha256, "reportSha256": run["report"].sha256,
        "manifestSha256": run["manifest"].sha256, "policySha256": run["policy"].sha256,
        "rows": [{"unitId": r["unitId"], "arm": r["arm"], "outcome": r["outcome"],
                  "terminal": r["terminal"]} for r in report["rows"]],
        "strata": report["strata"],
        "costs": {"claimBlocked": report["costs"]["economic"]["claimBlocked"],
                  "additionalCashEur": run["additionalCashEur"]},
        "pendingEndpoints": report["pendingEndpoints"]}


def main(argv: list[str]) -> int:
    sys.stdout.write(json.dumps(results(), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
