# SPDX-License-Identifier: AGPL-3.0-only
"""G0 scorer: C1a, C1b, C2, C3, C4 and the preregistered order of evaluation.

Revision 3 of the preregistration (docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md,
claude-workflow-g0-inputs.json, claude-workflow-g0-decision-vectors.json).

Two layers:
- `decide(counts)` maps the run-level count tuple of the decision vectors file to
  an outcome, the deciding step and the unmet criteria. Integer arithmetic only,
  no floats. The tests load the vectors file and require every vector to be
  reproduced.
- `score(data)` derives that tuple from per-run labels and adds the descriptive
  views (C1a, per-arm confusion counts, intention-to-treat, design adherence).

Input: a JSON file {"runs": [...]}, one object per started run:
  run_id, ordinal (int), status, reference, design, arms, probe, attribution
status is "eligible", "probe-unavailable" or an exclusion reason.
reference (eligible and probe-unavailable runs) is clean | textual-conflict |
  semantic-failure | indeterminate.
design: {overlap, contract, negative_control} booleans fixed in the manifest
  before launch; contract means a declared contract dependency with no shared
  file, so it excludes overlap; a negative control is an overlap run.
arms: merge-tree-pairwise, merge-tree-chained, naive-path-overlap,
  braid-analyze-git-primary, braid-analyze-git-inclusive (booleans; inclusive
  must include primary); clash (optional boolean).
probe (eligible runs): changed_files, attributed_changed_files (C3, gating),
  ordered_pairs_with_overlap (C2 and C4 flags), and the descriptive denominator_calls,
  unknown_writer_calls, read_only_search_calls (integers), as summed over the
  run's agents by probe.py; optional descriptive bash_calls. C3 is attribution
  coverage of changes: summed over the analysis set, met iff
  5*attributed >= 3*changed with changed > 0. The call-share unknown rate and
  the Bash share are descriptive only and never gate.
attribution (optional, default false): contract_named_in_manifest and
  counterfactual_removes_failure, the two conditions of C1b attribution.
Output is aggregate JSON only. Stdlib only.
"""

import json
import sys
from fractions import Fraction

EXCLUSIONS = ("agent-did-not-commit", "base-tests-fail", "branch-tests-fail-alone",
              "flaky-branch-tests", "workflow-aborted", "quota-exhausted",
              "manual-edit-of-agent-branch")
REFERENCES = ("clean", "textual-conflict", "semantic-failure", "indeterminate")
BASELINES = ("merge-tree-pairwise", "merge-tree-chained", "naive-path-overlap",
             "braid-analyze-git-primary", "braid-analyze-git-inclusive")
MAX_STARTED = 14
ANALYSIS_RUNS = 10
MIN_OVERLAP, MIN_CONTRACT, MIN_NEGATIVE_CONTROL = 7, 3, 3
MAX_NEGATIVE_CONTROLS_FLAGGED = 1
MIN_FLAGGED = 3
COUNT_FIELDS = (
    "eligibleRunsWithProbeData", "analysisSetRuns", "overlapRuns", "contractDependencyRuns",
    "negativeControlRuns", "negativeControlRunsFlagged", "c1bQualifyingFailures",
    "attributedChangedFiles", "changedFiles", "probeFlaggedRuns",
    "probeFlaggedReferenceFailures", "referenceFailureRuns", "naiveFlaggedRuns",
    "naiveFlaggedReferenceFailures")


def c3_met(counts):
    """Attribution coverage at least 0.60 (5*attributed >= 3*changed); zero changed is unmet."""
    changed = counts["changedFiles"]
    return changed > 0 and 5 * counts["attributedChangedFiles"] >= 3 * changed


def c2_unmet(counts):
    """Unmet C2 conditions by integer cross-multiplication (empty when met)."""
    hits, flagged, naive_flagged = (counts["probeFlaggedReferenceFailures"],
                                    counts["probeFlaggedRuns"], counts["naiveFlaggedRuns"])
    unmet = []
    if hits * 10 < 3 * flagged:
        unmet.append("C2-threshold")
    if not hits * counts["analysisSetRuns"] > counts["referenceFailureRuns"] * flagged:
        unmet.append("C2-prevalence")
    if naive_flagged > 0 and not hits * naive_flagged > counts["naiveFlaggedReferenceFailures"] * flagged:
        unmet.append("C2-naive")
    return unmet


def decide(counts):
    """Preregistered order of evaluation on integer counts; stops at the first outcome."""
    for field in COUNT_FIELDS:
        value = counts.get(field)
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError(f"counts.{field} must be a non-negative integer")
    if counts["attributedChangedFiles"] > counts["changedFiles"]:
        raise ValueError("counts.attributedChangedFiles exceeds counts.changedFiles")
    reasons = []
    if counts["eligibleRunsWithProbeData"] < ANALYSIS_RUNS:
        reasons.append("eligible-runs")
    if (counts["overlapRuns"] < MIN_OVERLAP or counts["contractDependencyRuns"] < MIN_CONTRACT
            or counts["negativeControlRuns"] < MIN_NEGATIVE_CONTROL):
        reasons.append("design-quota")
    if reasons:
        return _decision("g0-inconclusive", 1, reasons)

    unmet = []
    if counts["c1bQualifyingFailures"] < 1:
        unmet.append("C1b")
    if not c3_met(counts):
        unmet.append("C3")
    if counts["negativeControlRunsFlagged"] > MAX_NEGATIVE_CONTROLS_FLAGGED:
        unmet.append("C4")
    if unmet:
        return _decision("g0-fail", 2, unmet)
    if counts["probeFlaggedRuns"] < MIN_FLAGGED:
        return _decision("g0-inconclusive", 3, ["flagged-runs"])
    unmet = c2_unmet(counts)
    if unmet:
        return _decision("g0-fail", 4, unmet)
    return _decision("g0-pass", 5, ["all-met"])


def _decision(outcome, step, reasons):
    return {"outcome": outcome, "decidedAtStep": f"step-{step}", "unmetOrReason": reasons}


def _section(run, name):
    value = run.get(name)
    if not isinstance(value, dict):
        raise ValueError(f"run {run['run_id']}: {name} must be an object")
    return value


def _flag(run, arm):
    value = _section(run, "arms").get(arm)
    if not isinstance(value, bool):
        raise ValueError(f"run {run['run_id']}: arm {arm} must be a boolean")
    return value


def _count(run, key):
    value = _section(run, "probe").get(key)
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise ValueError(f"run {run['run_id']}: probe.{key} must be a non-negative integer")
    return value


def _opt_bool(run, section, key):
    value = run.get(section, {}).get(key, False)
    if not isinstance(value, bool):
        raise ValueError(f"run {run['run_id']}: {section}.{key} must be a boolean")
    return value


def validate(runs):
    if not isinstance(runs, list) or not all(isinstance(run, dict) for run in runs):
        raise ValueError("runs must be a list of objects")
    if len(runs) > MAX_STARTED:
        raise ValueError(f"more than {MAX_STARTED} started runs")
    ordinals = [run.get("ordinal") for run in runs]
    if (len(set(ordinals)) != len(ordinals)
            or not all(isinstance(o, int) and not isinstance(o, bool) for o in ordinals)):
        raise ValueError("ordinals must be distinct integers")
    run_ids = [run.get("run_id") for run in runs]
    if len(set(run_ids)) != len(run_ids) or not all(isinstance(r, str) and r for r in run_ids):
        raise ValueError("run_id must be a distinct non-empty string per run")
    for run in runs:
        status = run.get("status")
        if status not in ("eligible", "probe-unavailable") + EXCLUSIONS:
            raise ValueError(f"run {run.get('run_id')}: unknown status {status!r}")
        if status not in ("eligible", "probe-unavailable"):
            continue
        if run.get("reference") not in REFERENCES:
            raise ValueError(f"run {run['run_id']}: invalid reference")
        for arm in BASELINES:
            _flag(run, arm)
        if "clash" in run["arms"] and not isinstance(run["arms"]["clash"], bool):
            raise ValueError(f"run {run['run_id']}: arm clash must be a boolean")
        if _flag(run, "braid-analyze-git-primary") and not _flag(run, "braid-analyze-git-inclusive"):
            raise ValueError(f"run {run['run_id']}: inclusive flag must include primary")
        for section in ("design", "attribution"):
            if section in run and not isinstance(run[section], dict):
                raise ValueError(f"run {run['run_id']}: {section} must be an object")
        overlap, contract, control = (_opt_bool(run, "design", key)
                                      for key in ("overlap", "contract", "negative_control"))
        if overlap and contract:
            raise ValueError(f"run {run['run_id']}: a contract-dependency run has no shared file")
        if control and not overlap:
            raise ValueError(f"run {run['run_id']}: a negative control is an overlap run")
        for key in ("contract_named_in_manifest", "counterfactual_removes_failure"):
            _opt_bool(run, "attribution", key)
        if status == "eligible":
            denominator, unknown = _count(run, "denominator_calls"), _count(run, "unknown_writer_calls")
            changed, attributed = _count(run, "changed_files"), _count(run, "attributed_changed_files")
            _count(run, "read_only_search_calls")
            _count(run, "ordered_pairs_with_overlap")
            if "bash_calls" in run["probe"]:
                _count(run, "bash_calls")
            if unknown > denominator:
                raise ValueError(f"run {run['run_id']}: unknown_writer_calls exceeds denominator_calls")
            if attributed > changed:
                raise ValueError(f"run {run['run_id']}: attributed_changed_files exceeds changed_files")


def _num(value):
    return None if value is None else round(float(value), 4)


def _ratio(num, den):
    return Fraction(num, den) if den else None


def wilson(successes, n, z=1.959964):
    """Wilson 95% interval, description only, rounded for display."""
    if n == 0:
        return None
    p = successes / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / denom
    return [round(centre - half, 4), round(centre + half, 4)]


def _is_failure(run):
    return run["reference"] in ("textual-conflict", "semantic-failure")


def _probe_flag(run):
    return run["probe"]["ordered_pairs_with_overlap"] > 0


def _design(run, key):
    return run.get("design", {}).get(key, False)


def _arm_stats(runs, flag_of):
    """Confusion counts. Indeterminate is never a hit; flagged it is a false positive."""
    stats = {"tp": 0, "fp": 0, "fn": 0, "tn": 0, "tp_textual": 0, "tp_semantic": 0,
             "fn_textual": 0, "fn_semantic": 0, "indeterminate_flagged": 0,
             "indeterminate_unflagged": 0}
    for run in runs:
        flagged = flag_of(run)
        if _is_failure(run):
            kind = "textual" if run["reference"] == "textual-conflict" else "semantic"
            key = "tp" if flagged else "fn"
            stats[key] += 1
            stats[f"{key}_{kind}"] += 1
        elif run["reference"] == "indeterminate":
            stats["indeterminate_flagged" if flagged else "indeterminate_unflagged"] += 1
            stats["fp"] += 1 if flagged else 0
        else:
            stats["fp" if flagged else "tn"] += 1
    precision = _ratio(stats["tp"], stats["tp"] + stats["fp"])
    recall = _ratio(stats["tp"], stats["tp"] + stats["fn"])
    stats.update(precision=_num(precision), recall=_num(recall),
                 precision_wilson95=wilson(stats["tp"], stats["tp"] + stats["fp"]),
                 runs=len(runs))
    return stats


def _arms(probed, scored):
    out = {name: _arm_stats(scored, lambda r, name=name: r["arms"][name]) for name in BASELINES}
    out["transcript-probe"] = _arm_stats(probed, _probe_flag)
    if scored and all("clash" in r["arms"] for r in scored):
        out["clash"] = _arm_stats(scored, lambda r: r["arms"]["clash"])
    return out


def _qualifies_c1b(run):
    attribution = run.get("attribution", {})
    return (run["reference"] == "semantic-failure" and _probe_flag(run)
            and not any(run["arms"][arm] for arm in BASELINES)
            and attribution.get("contract_named_in_manifest", False)
            and attribution.get("counterfactual_removes_failure", False))


def derive_counts(analysis, eligible_total):
    controls = [r for r in analysis if _design(r, "negative_control")]
    flagged = [r for r in analysis if _probe_flag(r)]
    naive_flagged = [r for r in analysis if r["arms"]["naive-path-overlap"]]
    return {
        "eligibleRunsWithProbeData": eligible_total,
        "analysisSetRuns": len(analysis),
        "overlapRuns": sum(1 for r in analysis if _design(r, "overlap")),
        "contractDependencyRuns": sum(1 for r in analysis if _design(r, "contract")),
        "negativeControlRuns": len(controls),
        "negativeControlRunsFlagged": sum(1 for r in controls if _probe_flag(r)),
        "c1bQualifyingFailures": sum(1 for r in analysis if _qualifies_c1b(r)),
        "attributedChangedFiles": sum(r["probe"]["attributed_changed_files"] for r in analysis),
        "changedFiles": sum(r["probe"]["changed_files"] for r in analysis),
        "probeFlaggedRuns": len(flagged),
        "probeFlaggedReferenceFailures": sum(1 for r in flagged if _is_failure(r)),
        "referenceFailureRuns": sum(1 for r in analysis if r["reference"] != "clean"),
        "naiveFlaggedRuns": len(naive_flagged),
        "naiveFlaggedReferenceFailures": sum(1 for r in naive_flagged if _is_failure(r)),
    }


def score(data):
    runs = data.get("runs") if isinstance(data, dict) else None
    validate(runs)
    by_status = {}
    for run in runs:
        by_status[run["status"]] = by_status.get(run["status"], 0) + 1
    scored = [r for r in runs if r["status"] in ("eligible", "probe-unavailable")]
    eligible = sorted((r for r in runs if r["status"] == "eligible"), key=lambda r: r["ordinal"])
    analysis = eligible[:ANALYSIS_RUNS]
    counts = derive_counts(analysis, len(eligible))
    decision = decide(counts)

    n = len(analysis)
    unknown_calls = sum(r["probe"]["unknown_writer_calls"] for r in analysis)
    denominator = sum(r["probe"]["denominator_calls"] for r in analysis)
    searches = sum(r["probe"]["read_only_search_calls"] for r in analysis)
    bash = (sum(r["probe"]["bash_calls"] for r in analysis)
            if all("bash_calls" in r["probe"] for r in analysis) else None)
    prevalence = _ratio(counts["referenceFailureRuns"], n)
    precision = _ratio(counts["probeFlaggedReferenceFailures"], counts["probeFlaggedRuns"])
    naive_precision = _ratio(counts["naiveFlaggedReferenceFailures"], counts["naiveFlaggedRuns"])
    c1a_runs = [r for r in scored if _is_failure(r)
                and not r["arms"]["merge-tree-pairwise"] and not r["arms"]["merge-tree-chained"]
                and not r["arms"]["naive-path-overlap"] and r["arms"]["braid-analyze-git-primary"]]
    return {
        "outcome": decision["outcome"],
        "decided_at_step": int(decision["decidedAtStep"].split("-")[1]),
        "unmet_or_reason": decision["unmetOrReason"],
        "decides_on": "first-10-eligible-runs-with-probe-data-in-manifest-ordinal",
        "counts": counts,
        # C1a informs R1 only and gates nothing; a hit is a discrepancy to investigate.
        "c1a": {"count": len(c1a_runs), "met": bool(c1a_runs), "expected_hits": 0,
                "gates_nothing": True},
        "c1b": {"count": counts["c1bQualifyingFailures"],
                "met": counts["c1bQualifyingFailures"] >= 1,
                "meaning_of_pass": "feasibility-not-refuted"},
        "c2": {"evaluable": counts["probeFlaggedRuns"] >= MIN_FLAGGED,
               "flagged_runs": counts["probeFlaggedRuns"], "precision": _num(precision),
               "prevalence": _num(prevalence), "naive_precision": _num(naive_precision),
               "naive_comparison": "applied" if counts["naiveFlaggedRuns"] else "not-applicable",
               "unmet_if_evaluated": c2_unmet(counts) if counts["probeFlaggedRuns"] else None},
        "c3": {"definition": "attribution-coverage-of-changes",
               "attributed_changed_files": counts["attributedChangedFiles"],
               "changed_files": counts["changedFiles"],
               "coverage": _num(_ratio(counts["attributedChangedFiles"], counts["changedFiles"])),
               "threshold_proposal": "0.60",
               "met": c3_met(counts)},
        # Descriptive only since revision 3: reported, never gating.
        "descriptive_call_mix": {
            "gates_nothing": True,
            "unknown_writer_calls": unknown_calls,
            "denominator_calls": denominator,
            "unknown_call_rate": _num(_ratio(unknown_calls, denominator)),
            "read_only_search_calls": searches,
            "bash_share_of_all_calls": (None if bash is None
                                        else _num(_ratio(bash, denominator + searches)))},
        "c4": {"negative_control_runs": counts["negativeControlRuns"],
               "flagged": counts["negativeControlRunsFlagged"],
               "flag_rate": _num(_ratio(counts["negativeControlRunsFlagged"],
                                        counts["negativeControlRuns"])),
               "met": counts["negativeControlRuns"] >= MIN_NEGATIVE_CONTROL
               and counts["negativeControlRunsFlagged"] <= MAX_NEGATIVE_CONTROLS_FLAGGED},
        "reference_failure_prevalence": _num(prevalence),
        "arms": _arms(analysis, analysis),
        "design_quotas": {
            "overlap_met": counts["overlapRuns"] >= MIN_OVERLAP,
            "contract_dependency_met": counts["contractDependencyRuns"] >= MIN_CONTRACT,
            "negative_control_met": counts["negativeControlRuns"] >= MIN_NEGATIVE_CONTROL},
        "intention_to_treat": {
            "started_runs": len(runs),
            "runs_by_status": dict(sorted(by_status.items())),
            "eligible_with_probe_data": len(eligible),
            "later_eligible_runs_descriptive_only": max(0, len(eligible) - ANALYSIS_RUNS),
            "probe_unavailable_runs": by_status.get("probe-unavailable", 0),
            "indeterminate_runs": sum(1 for r in scored if r["reference"] == "indeterminate"),
            "arms": _arms(eligible, scored)},
    }


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 1:
        sys.stderr.write("usage: scorer.py RUNS.json\n")
        return 2
    with open(argv[0], encoding="utf-8") as handle:
        try:
            result = score(json.load(handle))
        except ValueError as error:
            sys.stderr.write(f"scorer: {error}\n")
            return 1
    json.dump(result, sys.stdout, sort_keys=True, indent=2)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
