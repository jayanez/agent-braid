# SPDX-License-Identifier: AGPL-3.0-only
"""Independent finite replay checking; never verifies arbitrary proof languages."""

from .model import (ASSUMPTIONS, EXECUTION, MODEL, Invalid, digest, name, record,
                    require, run, schedules, validate_fixture, verdict)


def produce(fixture, selected=None):
    orders = schedules(fixture)
    kind = "exhaustive-finite" if selected is None else "replay"
    chosen = orders if selected is None else selected
    require(isinstance(chosen, list) and chosen, "empty schedule selection")
    require(all(order in orders for order in chosen), "inadmissible schedule")
    require(len({tuple(o) for o in chosen}) == len(chosen), "duplicate schedules")
    require(kind != "replay" or len(chosen) >= 2, "replay needs two distinct schedules")
    fixture_digest = digest(fixture)
    artifacts = {fixture_digest: fixture}
    outcomes, traces = [], []
    for order in chosen:
        outcome = run(fixture, order)
        outcomes.append(outcome)
        outcome_digest = digest(outcome)
        artifacts[outcome_digest] = outcome
        traces.append({"schedule": order, "outcomeDigest": outcome_digest})
    certificate = {
        "certificateVersion": "0.2.0-draft", "modelVersion": MODEL,
        "initialStateDigest": digest({"state": fixture["state"], "versions": fixture["versions"]}),
        "operations": [{"id": o["id"], "definitionDigest": digest(o)} for o in fixture["operations"]],
        "observation": fixture["observation"], "executionContract": EXECUTION,
        "claim": {"property": "terminal-observation-equivalence", "method": kind,
                  "domain": "fixture:" + fixture_digest, "assumptions": ASSUMPTIONS.copy(),
                  "observationContract": digest(fixture["observation"]),
                  "executionContract": EXECUTION, "assuranceClass": 4 if kind == "exhaustive-finite" else 0},
        "evidence": {"kind": kind, "fixtureDigest": fixture_digest, "traces": traces},
        "result": verdict(outcomes, fixture["observation"]),
    }
    certificate["certificateId"] = digest(certificate)
    return {"certificate": certificate, "artifacts": artifacts}


def verify(bundle):
    """Total report for malformed JSON-shaped input; callers do not trust producer verdicts."""
    try:
        return _verify(bundle)
    except (Invalid, KeyError, TypeError, ValueError, RecursionError) as exc:
        return {"status": "rejected", "reason": str(exc)}


def _verify(bundle):
    record(bundle, ["certificate", "artifacts"])
    cert, artifacts = bundle["certificate"], bundle["artifacts"]
    record(cert, ["certificateVersion", "certificateId", "modelVersion", "initialStateDigest",
                  "operations", "observation", "executionContract", "claim", "evidence", "result"])
    name(cert["certificateId"])
    require(cert["certificateVersion"] == "0.2.0-draft", "unsupported certificate version")
    require(cert["modelVersion"] == MODEL and cert["executionContract"] == EXECUTION, "unsupported execution")
    require(cert["result"] in ("equivalent-observed", "divergent", "inconclusive", "not-applicable"), "invalid result")
    require(isinstance(artifacts, dict), "artifact map required")
    for key, value in artifacts.items():
        require(key == digest(value), "artifact digest mismatch")
    evidence = cert["evidence"]
    require(isinstance(evidence, dict), "evidence object required")
    kind = evidence.get("kind")
    require(kind in ("replay", "exhaustive-finite", "proof-rule"), "unsupported evidence")
    record(evidence, ["kind", "fixtureDigest", "ruleId", "proofDigest"] if kind == "proof-rule"
           else ["kind", "fixtureDigest", "traces"])
    fixture = artifacts.get(evidence["fixtureDigest"])
    require(fixture is not None, "missing fixture artifact")
    validate_fixture(fixture)
    require(cert["initialStateDigest"] == digest({"state": fixture["state"], "versions": fixture["versions"]}),
            "initial state digest mismatch")
    expected = [{"id": o["id"], "definitionDigest": digest(o)} for o in fixture["operations"]]
    require(cert["operations"] == expected, "operation definitions or identities mismatch")
    require(cert["observation"] == fixture["observation"], "observation mismatch")
    claim = cert["claim"]
    record(claim, ["property", "method", "domain", "assumptions", "observationContract",
                   "executionContract", "assuranceClass"])
    require(claim["property"] in ("terminal-observation-equivalence", "independence", "confluence", "braid"), "unknown property")
    require(claim["method"] == kind, "method mismatch")
    require(claim["domain"] == "fixture:" + evidence["fixtureDigest"], "scope mismatch")
    require(claim["observationContract"] == digest(fixture["observation"]), "observation contract mismatch")
    require(claim["executionContract"] == EXECUTION, "execution contract mismatch")
    require(isinstance(claim["assumptions"], list), "assumptions array required")
    for assumption in claim["assumptions"]:
        name(assumption)
    level = claim["assuranceClass"]
    require(type(level) is int and 0 <= level <= 5, "invalid assurance class")
    if kind == "proof-rule":
        name(evidence["ruleId"])
        require(evidence["proofDigest"] in artifacts, "missing proof artifact")
        return {"status": "unverified", "reason": "proof rule not supported; hashes establish identity only"}
    require(claim["assumptions"] == ASSUMPTIONS, "model assumptions mismatch")
    require(claim["property"] == "terminal-observation-equivalence", "replay cannot establish this property")
    require(level <= (3 if kind == "replay" else 4), "unsupported assurance claim")
    traces = evidence["traces"]
    require(isinstance(traces, list) and 1 <= len(traces) <= 720, "trace count must be 1..720")
    admissible = schedules(fixture)
    seen, outcomes = set(), []
    for trace in traces:
        record(trace, ["schedule", "outcomeDigest"])
        order = trace["schedule"]
        require(order in admissible, "unknown, incomplete or inadmissible schedule")
        require(tuple(order) not in seen, "duplicate schedule")
        seen.add(tuple(order))
        actual = run(fixture, order)
        require(trace["outcomeDigest"] in artifacts, "missing outcome artifact")
        require(digest(actual) == trace["outcomeDigest"], "replayed outcome mismatch")
        outcomes.append(actual)
    if kind == "exhaustive-finite":
        require(seen == {tuple(o) for o in admissible}, "incomplete exhaustive coverage")
    else:
        require(len(seen) >= 2, "replay requires distinct schedules")
    computed = verdict(outcomes, fixture["observation"])
    require(computed == cert["result"], "producer verdict mismatch")
    return {"status": "verified", "reason": "finite model evidence checked; no execution authorization",
            "checkedClaim": {"property": claim["property"], "method": kind,
                             "domain": claim["domain"], "result": computed,
                             "schedulesChecked": len(seen)}}


def validate_aim_batch(records):
    """Semantic graph checks after JSON Schema validation; not coverage verification."""
    require(isinstance(records, list) and records, "empty metadata batch")
    ids = [r["instanceId"] for r in records]
    attempts = [r["attemptId"] for r in records]
    require(len(set(ids)) == len(ids), "duplicate instance ID")
    require(len(set(attempts)) == len(attempts), "duplicate attempt ID")
    done = set()
    for item in records:
        require(set(item["dependencies"]) <= set(ids), "unknown dependency")
    while len(done) < len(ids):
        ready = {r["instanceId"] for r in records if set(r["dependencies"]) <= done} - done
        require(bool(ready), "cyclic metadata dependencies")
        done.update(ready)
