# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-049 T005 deterministic synthetic-control cohort: plumbing only, never a verdict input.

Builds the Units for the six lineage-assigned roster cases, a keep-base arm-C round and
the three-arm registration, then runs the registered cohort once with the R13 guidance
double as solver. The double encodes the behaviour it reports, and the oracles below are
written from the same owned scenarios, so every outcome shows that registration,
observation, commitment, grading, denominators and the blocked-cost path connect end to end. It
shows nothing about whether any guidance helps. Arm C is arm A by construction (keep-base)
and arm D is not run. Nothing reads a clock, host, model or network, and no record carries
execution authority. ``python -m tests.harness_t005_cohort`` prints the result record.
"""
from __future__ import annotations

import functools
from hashlib import sha256
import json
import sys
from typing import Any

from agent_braid import harness_evaluation as ev
from agent_braid import harness_manifest as manifests
from agent_braid import harness_observation as obs
from agent_braid import harness_refinement as ref
from agent_braid import harness_verification as ver
from agent_braid.system_one import canonical, digest, thaw
from tests import harness_guidance_double as double
from tests.test_harness_manifest import make_manifest
from tests.test_harness_refinement import policy_wire

HOLDOUT = ("L1-C01-a", "L1-C02-a", "L1-C03-a", "L1-C03-b", "L1-C03-c")
DISCOVERY = "L2-C01-a"
LINEAGE = "L1"  # every holdout case shares the S06 base (R2, D1): one independent lineage
ROSTER_SHA256 = "6a1e55f896fb77a1bbc42dc402eef1abc5d3f56e7a4b1dbcfd152c8c93e6a4e0"
PROFILE_SHA256 = "2f42b12d6c9777826922632fedccb5e51761646cca81a40aa79c3c978aa92ba4"
RUBRIC_TEXT = (b"Correct when the committed result lists every case step as done and records"
               b" no step as repeated. An interrupted or refused attempt commits no result.\n")
RESULT_PATH = "out/result.txt"
NOW = 1_800_000_000
SECRET = "sk-test-SECRET-0123456789"
UNKNOWN_COST = {"status": "unknown", "reason": "offline-double-no-exporter"}
COST_KEYS = ("cash", "quota", "wall", "cpu", "rss", "disk", "journal", "processes", "human")


@functools.cache
def _inventory() -> obs.ExportInventory:
    wire = {"format": obs.INVENTORY_FORMAT, "allowedEventFields": ["text", "state"],
            "secrets": [SECRET], "maxRetentionSeconds": 3600}
    return obs.verify_inventory(canonical(wire), expected_sha256=sha256(canonical(wire)).hexdigest())


def rubric_sha256() -> str:
    return sha256(RUBRIC_TEXT).hexdigest()


def expected_output(case_id: str) -> bytes:
    steps = double.CASES[case_id]["steps"]
    return f"done: {' '.join(steps)}\nrepeated: none\n".encode()


def result_output(case_id: str, record: dict) -> bytes | None:
    """The committed result of a completed double run; an interrupted run commits none."""
    if record["terminal"] != "completed":
        return None
    case = double.CASES[case_id]
    done_before = set(case["steps"][:case["checkpoint"] or 0])
    done = [s for s in case["steps"] if s in done_before or s in record["executed"]]
    repeated = " ".join(record["repeated"]) or "none"
    return f"done: {' '.join(done)}\nrepeated: {repeated}\n".encode()


def build_unit(case_id: str) -> ver.Unit:
    partition = "discovery" if case_id == DISCOVERY else "holdout"
    source = digest({"caseId": case_id, "rosterSha256": ROSTER_SHA256,
                     "scenario": thaw(double.CASES[case_id])})
    return ver.Unit(unit_id=case_id, partition=partition, source_sha256=source,
                    rubric_sha256=rubric_sha256(),
                    oracles=(ver.FixtureOracle({RESULT_PATH: expected_output(case_id)}),),
                    human_required=False)


def build_units() -> dict[str, ver.Unit]:
    return {case: build_unit(case) for case in (*HOLDOUT, DISCOVERY)}


def build_manifest() -> tuple[manifests.HarnessManifest, ref.SelectionPolicy]:
    """Manifest whose base is arm A (empty inventory) and whose surface admits arm B's file."""
    wire = make_manifest()
    wire["base"] = {"sha256": digest([]), "files": []}
    files = double.arm_files("B")
    rows = [{"path": p, "sha256": sha256(c).hexdigest(), "sizeBytes": len(c)}
            for p, c in sorted(files.items())]
    wire["candidate"] = {"sha256": digest(rows), "files": rows}
    wire["allowedComponentPaths"] = [double.GUIDANCE_PATH]
    wire["effects"] = {"read": ["candidate/guidance/checkpoint.md", "context/notes/context.txt",
                                "source/task.txt"],
                       "write": ["lab/guidance/checkpoint.md"], "delete": []}
    policy = policy_wire()
    wire["policy"] = {"version": policy["version"],
                      "sha256": sha256(canonical(policy)).hexdigest()}
    manifest = manifests.parse_manifest(canonical(wire))
    return manifest, ref.parse_policy(canonical(policy), manifest=manifest)


def attempt(case_id: str, unit: ver.Unit, files: dict[str, bytes], candidate: str,
            attempt_id: str, manifest_sha256: str):
    """Run the double on one case and return (double record, commitment, outputs)."""
    record = double.run(case_id, files, candidate_sha256=candidate).to_dict()
    outputs = result_output(case_id, record)
    committed = {RESULT_PATH: outputs} if outputs is not None else None
    observation = obs.observe(record["events"], manifest_sha256=manifest_sha256,
                              attempt_id=attempt_id, source="fixture", inventory=_inventory(),
                              now=NOW, retention_seconds=60, before={}, after=committed or {})
    commitment = ver.commit(unit, candidate_sha256=candidate, observation=observation,
                            outputs=committed, now=NOW)
    return record, commitment, committed


def keep_base_round(units: dict[str, ver.Unit]):
    """Keep-base round (R8 option b): both scopes abstain; the base is probed on discovery."""
    manifest, policy = build_manifest()
    discovery = units[DISCOVERY]

    def probe(request):
        if request.candidate_sha256 != double.ARM_SHA256["A"] or request.changes:
            raise ValueError("unexpected-probe")
        _, commitment, outputs = attempt(DISCOVERY, discovery, {}, double.ARM_SHA256["A"],
                                         "discovery-base", manifest.sha256)
        verdict = ver.verify_unit(discovery, commitment, outputs).to_dict()
        oracle = verdict["oracle"]["verdict"]
        if oracle not in ver.VERDICTS:
            raise ValueError("ungraded-base-probe")
        passed = oracle == "pass"
        return {"terminal": commitment.data["terminal"],
                "score": ver.MAX_SCORE_MICROS if passed else 0,
                "observationSha256": commitment.data["observationSha256"]}

    return manifest, policy, ref.run_round(manifest, policy, propose=lambda scope: None, probe=probe)


def register(units: dict[str, ver.Unit], decision) -> ev.Registration:
    holdout = [units[c] for c in HOLDOUT]
    chosen = decision.to_dict()
    arm_c = chosen["chosenCandidateSha256"] or chosen["baseSha256"]
    return ev.register(
        holdout, lineages={c: LINEAGE for c in HOLDOUT},
        families={c: c.split("-")[1] for c in HOLDOUT},
        strata={c: double.CASES[c]["stratum"] for c in HOLDOUT},
        candidates={"A": double.ARM_SHA256["A"], "B": double.ARM_SHA256["B"], "C": arm_c},
        refinement=decision, profile_sha256=PROFILE_SHA256, cohort="synthetic")


def run_cohort() -> dict[str, Any]:
    """Run the registered cohort once; return registration, report and per-attempt detail."""
    units = build_units()
    manifest, policy, decision = keep_base_round(units)
    registration = register(units, decision)
    candidates = {arm: registration.data["arms"][arm]["candidateSha256"] for arm in ev.ARMS}
    files = {"A": double.arm_files("A"), "B": double.arm_files("B"), "C": double.arm_files("A")}
    rows, entries, detail = [], [], []
    for case in HOLDOUT:
        for arm in ev.ARMS:
            attempt_id = f"{case}-{arm}"
            record, commitment, outputs = attempt(case, units[case], files[arm], candidates[arm],
                                                  attempt_id, manifest.sha256)
            verdict = ver.verify_unit(units[case], commitment, outputs)
            rows.append({"arm": arm, "attemptId": attempt_id, "reservationSha256": None,
                         "commitment": commitment, "verdict": verdict})
            entries.append({"id": f"cost-{attempt_id}", "phase": "verification",
                            "attempt": attempt_id,
                            "measures": {k: dict(UNKNOWN_COST) for k in COST_KEYS}})
            detail.append({"caseId": case, "arm": arm, "doubleRecordSha256": sha256(
                canonical(record)).hexdigest(), "terminal": record["terminal"],
                "executed": record["executed"], "repeated": record["repeated"]})
    report = ev.evaluate(registration, rows, cost_entries=entries, reservations=[])
    return {"units": units, "manifest": manifest, "policy": policy, "decision": decision,
            "registration": registration, "report": report, "detail": detail}


def results() -> dict[str, Any]:
    """Deterministic, JSON-ready result of one run (what the evidence record stores)."""
    run = run_cohort()
    report = run["report"].to_dict()
    return {
        "label": double.LABEL, "verdictEligible": False,
        "registrationSha256": run["registration"].sha256, "reportSha256": run["report"].sha256,
        "refinement": report["refinement"], "refinementDecisionSha256": run["decision"].sha256,
        "manifestSha256": run["manifest"].sha256, "policySha256": run["policy"].sha256,
        "order": run["registration"].to_dict()["order"],
        "unitSha256": {c: u.sha256 for c, u in sorted(run["units"].items())},
        "rows": [{"unitId": r["unitId"], "arm": r["arm"], "outcome": r["outcome"],
                  "terminal": r["terminal"]} for r in report["rows"]],
        "attempts": run["detail"], "strata": report["strata"],
        "costs": {"blockers": report["costs"]["economic"]["blockers"],
                  "claimBlocked": report["costs"]["economic"]["claimBlocked"]},
        "pendingEndpoints": report["pendingEndpoints"],
        "executionAuthorization": False}


def main(argv: list[str]) -> int:
    sys.stdout.write(json.dumps(results(), indent=2, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
