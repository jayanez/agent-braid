# SPDX-License-Identifier: AGPL-3.0-only
"""G0 scorer: C1a, C1b, C2, C3 and the preregistered order of evaluation.

Input: a JSON file {"runs": [...]} of per-run labels, one object per started run:
  run_id, ordinal (int), status, reference, design{overlap, contract},
  arms{merge-tree-pairwise, merge-tree-chained, naive-path-overlap,
       braid-analyze-git-primary, braid-analyze-git-inclusive, clash?},
  probe{total_calls, unknown_calls, ordered_pairs_with_overlap}
status is "eligible", "probe-unavailable" or an exclusion reason. `reference`
is clean | textual-conflict | semantic-failure (required for eligible and
probe-unavailable runs). `probe` is required for eligible runs. Output is
aggregate JSON only. The rule mirrors the proposal and inputs JSON; it
computes nothing the founder has not preregistered. Stdlib only.
"""

import json
import math
import sys
from fractions import Fraction

EXCLUSIONS = ("agent-did-not-commit", "base-tests-fail", "branch-tests-fail-alone",
              "flaky-final-tests", "workflow-aborted", "quota-exhausted",
              "manual-edit-of-agent-branch")
REFERENCES = ("clean", "textual-conflict", "semantic-failure")
BASELINES = ("merge-tree-pairwise", "merge-tree-chained", "naive-path-overlap",
             "braid-analyze-git-primary", "braid-analyze-git-inclusive")
MAX_STARTED = 14
MIN_ELIGIBLE = 10
MIN_FLAGGED = 3
C2_PRECISION = Fraction(3, 10)
C3_MAX_UNKNOWN = Fraction(2, 5)


def _flag(run, arm):
    value = run["arms"].get(arm)
    if not isinstance(value, bool):
        raise ValueError(f"run {run['run_id']}: arm {arm} must be a boolean")
    return value


def _count(run, key):
    value = run["probe"].get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"run {run['run_id']}: probe.{key} must be a non-negative integer")
    return value


def validate(runs):
    if len(runs) > MAX_STARTED:
        raise ValueError(f"more than {MAX_STARTED} started runs")
    ordinals = [run.get("ordinal") for run in runs]
    if len(set(ordinals)) != len(ordinals) or not all(isinstance(o, int) for o in ordinals):
        raise ValueError("ordinals must be distinct integers")
    for run in runs:
        status = run.get("status")
        if status not in ("eligible", "probe-unavailable") + EXCLUSIONS:
            raise ValueError(f"run {run.get('run_id')}: unknown status {status!r}")
        if status in ("eligible", "probe-unavailable"):
            if run.get("reference") not in REFERENCES:
                raise ValueError(f"run {run['run_id']}: invalid reference")
            for arm in BASELINES[:4]:
                _flag(run, arm)
            if _flag(run, "braid-analyze-git-primary") and not _flag(run, "braid-analyze-git-inclusive"):
                raise ValueError(f"run {run['run_id']}: inclusive flag must include primary")
            _flag(run, "braid-analyze-git-inclusive")
        if status == "eligible":
            total, unknown = _count(run, "total_calls"), _count(run, "unknown_calls")
            _count(run, "ordered_pairs_with_overlap")
            if unknown > total:
                raise ValueError(f"run {run['run_id']}: unknown_calls exceeds total_calls")


def wilson(successes, n, z=1.959964):
    if n == 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round(centre - half, 4), round(centre + half, 4)]


def _ratio(num, den):
    return Fraction(num, den) if den else None


def _num(value):
    return None if value is None else round(float(value), 4)


def _arm_stats(runs, flag_of):
    stats = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "tp_textual": 0, "tp_semantic": 0,
             "fn_textual": 0, "fn_semantic": 0}
    for run in runs:
        failure = run["reference"] != "clean"
        flagged = flag_of(run)
        kind = "textual" if run["reference"] == "textual-conflict" else "semantic"
        if failure:
            key = "tp" if flagged else "fn"
            stats[f"{key}_{kind}"] += 1
        else:
            key = "fp" if flagged else "tn"
        stats[key] += 1
    precision = _ratio(stats["tp"], stats["tp"] + stats["fp"])
    recall = _ratio(stats["tp"], stats["tp"] + stats["fn"])
    return stats, precision, recall


def score(data):
    runs = data["runs"]
    validate(runs)
    by_status = {}
    for run in runs:
        by_status[run["status"]] = by_status.get(run["status"], 0) + 1
    scored = [r for r in runs if r["status"] in ("eligible", "probe-unavailable")]
    probed = sorted((r for r in runs if r["status"] == "eligible"), key=lambda r: r["ordinal"])
    n = len(probed)

    def probe_flag(run):
        return run["probe"]["ordered_pairs_with_overlap"] > 0

    # C1a: commit-level evidence over every run with Git arms; informs R1 only.
    c1a_runs = [r for r in scored if r["reference"] != "clean"
                and not r["arms"]["merge-tree-pairwise"] and not r["arms"]["merge-tree-chained"]
                and r["arms"]["braid-analyze-git-primary"]]
    c1a = {"count": len(c1a_runs), "met": len(c1a_runs) >= 1,
           "also_flagged_by_naive": sum(1 for r in c1a_runs if r["arms"]["naive-path-overlap"]),
           "gates_nothing": True}

    c1b_count = sum(1 for r in probed if r["reference"] != "clean" and probe_flag(r)
                    and not any(r["arms"][arm] for arm in BASELINES))
    c1b = {"count": c1b_count, "met": c1b_count >= 1}

    total = sum(r["probe"]["total_calls"] for r in probed)
    unknown = sum(r["probe"]["unknown_calls"] for r in probed)
    rate = _ratio(unknown, total)
    # No probe calls at all: the unknown rate is undefined, so C3 is unmet.
    c3 = {"unknown_calls": unknown, "total_calls": total, "rate": _num(rate),
          "met": rate is not None and rate <= C3_MAX_UNKNOWN}

    flagged = [r for r in probed if probe_flag(r)]
    failures = sum(1 for r in probed if r["reference"] != "clean")
    prevalence = _ratio(failures, n)
    precision = _ratio(sum(1 for r in flagged if r["reference"] != "clean"), len(flagged))
    naive_flagged = [r for r in probed if r["arms"]["naive-path-overlap"]]
    naive_precision = _ratio(sum(1 for r in naive_flagged if r["reference"] != "clean"),
                             len(naive_flagged))
    c2_met = (precision is not None and precision >= C2_PRECISION and precision > prevalence
              and (naive_precision is None or precision > naive_precision))
    c2 = {"evaluable": len(flagged) >= MIN_FLAGGED, "flagged_runs": len(flagged),
          "precision": _num(precision), "prevalence": _num(prevalence),
          "naive_precision": _num(naive_precision),
          "naive_comparison": "not-applicable" if naive_precision is None else "applied",
          "met_if_evaluated": c2_met}

    # Preregistered order of evaluation; stops at the first outcome.
    if n < MIN_ELIGIBLE:
        outcome, step = "g0-inconclusive", 1
    elif not (c1b["met"] and c3["met"]):
        outcome, step = "g0-fail", 2
    elif len(flagged) < MIN_FLAGGED:
        outcome, step = "g0-inconclusive", 3
    elif not c2_met:
        outcome, step = "g0-fail", 4
    else:
        outcome, step = "g0-pass", 5

    arms = {}
    arm_flags = {
        "merge-tree-pairwise": lambda r: r["arms"]["merge-tree-pairwise"],
        "merge-tree-chained": lambda r: r["arms"]["merge-tree-chained"],
        "naive-path-overlap": lambda r: r["arms"]["naive-path-overlap"],
        "braid-analyze-git-primary": lambda r: r["arms"]["braid-analyze-git-primary"],
        "braid-analyze-git-inclusive": lambda r: r["arms"]["braid-analyze-git-inclusive"],
        "transcript-probe": probe_flag,
    }
    for name, flag_of in arm_flags.items():
        population = probed if name == "transcript-probe" else scored
        stats, prec, rec = _arm_stats(population, flag_of)
        stats.update(precision=_num(prec), recall=_num(rec),
                     precision_wilson95=wilson(stats["tp"], stats["tp"] + stats["fp"]),
                     runs=len(population))
        arms[name] = stats

    first_ten = probed[:MIN_ELIGIBLE]
    adherence = {  # reported separately from the result
        "first_ten_with_designed_overlap": sum(1 for r in first_ten if r.get("design", {}).get("overlap")),
        "first_ten_with_cross_file_contract": sum(1 for r in first_ten if r.get("design", {}).get("contract")),
        "overlap_design_met": sum(1 for r in first_ten if r.get("design", {}).get("overlap")) >= 7,
        "contract_design_met": sum(1 for r in first_ten if r.get("design", {}).get("contract")) >= 3,
    }
    return {
        "outcome": outcome, "decided_at_step": step,
        "started_runs": len(runs), "eligible_with_probe_data": n,
        "runs_by_status": dict(sorted(by_status.items())),
        "c1a": c1a, "c1b": c1b, "c2": c2, "c3": c3,
        "reference_failure_prevalence": _num(prevalence),
        "arms": arms, "adherence": adherence,
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        sys.stderr.write("usage: scorer.py RUNS.json\n")
        return 2
    with open(argv[0], encoding="utf-8") as handle:
        result = score(json.load(handle))
    json.dump(result, sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
