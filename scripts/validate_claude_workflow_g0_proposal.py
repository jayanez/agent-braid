#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only structural check of the unfrozen M4.6 gate G0 preregistration.

It verifies that the proposal bytes, thresholds and required fields have not
drifted from the registered contract. It never runs a workflow, reads a
transcript, calls a network service, or grants execution authority. A passing
check proves only structure and byte binding, not any scientific result.
"""

from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = "docs/experiments/claude-workflow-g0-inputs.json"
PROPOSAL_PATH = "docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md"
DECISION_PATH = "specs/053-claude-transcript-trace-adapter/budget-and-source-decision.md"
HYPOTHESIS_PATH = "research/hypotheses/H-CW1-claude-workflow-integration.md"
RECORD_VERSION = "agent-braid-claude-workflow-g0-input-proposal-1"

REQUIRED_FIELDS = (
    "recordVersion", "status", "frozen", "executionAuthorization", "milestone",
    "gate", "hypothesis", "specs", "proposal", "sourceAndBudgetDecision",
    "runner", "budget", "design", "referenceOutcome", "arms", "probe",
    "metrics", "unknownRate", "thresholds", "decisionRule", "killOutcome",
    "retention", "requiredBeforeFreeze", "claimLimits",
)
EXPECTED_THRESHOLDS = {
    # C1a is commit-level evidence: it informs release R1 and unlocks nothing.
    "C1a": {
        "role": "informs-R1-only-unlocks-nothing",
        "gatesTranscriptRequirements": False,
        "countsTowardPassOrFail": False,
        "minReferenceFailuresMissedByMergeTreeAndFlaggedByBraid": 1,
        "missedBy": ["merge-tree-pairwise", "merge-tree-chained"],
        "flaggedBy": ["braid-analyze-git-primary"],
    },
    # C1b is the only C1 criterion that can unblock PR5 and PR6: it needs a
    # failure that every non-transcript arm missed and only the probe flagged.
    "C1b": {
        "role": "transcript-dependent-gate-for-PR5-and-PR6",
        "gatesTranscriptRequirements": True,
        "countsTowardPassOrFail": True,
        "minReferenceFailuresMissedByAllNonTranscriptArmsAndFlaggedByProbe": 1,
        "missedBy": ["merge-tree-pairwise", "merge-tree-chained",
                     "naive-path-overlap", "braid-analyze-git-primary",
                     "braid-analyze-git-inclusive"],
        "flaggedBy": ["transcript-probe"],
    },
    "C2": {
        "minReadWriteOverlapPrecision": 0.3,
        "mustExceedReferenceFailurePrevalence": True,
        "mustExceedNaivePathOverlapPrecisionWhenDefined": True,
        "prevalenceDenominator": "eligible-runs-with-probe-data",
        "prevalenceReportedBeforeEvaluation": True,
        "minFlaggedRunsToEvaluate": 3,
        "unit": "run",
    },
    "C3": {"maxUnknownRate": 0.4},
}
EXPECTED_DECISION_RULE = {
    "pass": "C1b-and-C2-and-C3-on-at-least-10-eligible-runs-with-probe-data",
    "fail": "C1b-or-C3-unmet-or-C2-unmet-when-evaluated-on-at-least-10-"
            "eligible-runs-with-probe-data",
    "inconclusive": "fewer-than-10-eligible-runs-with-probe-data-or-fewer-than-3-"
                    "probe-flagged-runs-when-C1b-and-C3-are-met",
    "inconclusiveCountsAsPass": False,
    "evaluationOrder": [
        "step-1-fewer-than-10-eligible-runs-with-probe-data-is-inconclusive-and-stops",
        "step-2-evaluate-C1b-and-C3-either-unmet-is-fail-and-stops",
        "step-3-fewer-than-3-probe-flagged-runs-is-inconclusive-and-stops",
        "step-4-evaluate-C2-unmet-is-fail-and-stops",
        "step-5-all-met-is-pass",
    ],
    "precedence": "fail-over-inconclusive-once-10-eligible-runs-with-probe-data-exist",
    "c1aGatesNothing": True,
}
EXPECTED_BUDGET = {
    "additionalSpendEur": 0,
    "billingRoute": "existing-claude-subscription-included-quota",
    "extraUsageEnabled": False,
    "autoRechargeEnabled": False,
    "apiCredentialsUsed": False,
    "stopOnQuotaExhaustion": True,
    "reference": "docs/tooling/BUDGET.md",
}
EXPECTED_KILL = {
    "trigger": "g0-fail",
    "adoptionTrack": "AT-2026-006",
    "adoptionTrackTo": "watch-or-rejected",
    "spec053": "closed-not-adopted",
    "milestone": "M4.6 closes with R1 only",
}
REQUIRED_ARMS = ("merge-tree-pairwise", "merge-tree-chained", "naive-path-overlap",
                 "braid-analyze-git", "transcript-probe")
OPTIONAL_ARMS = ("clash",)
REQUIRED_METRICS = ("hits-misses-vs-reference", "unknown-rate",
                    "replay-ineligible-rate", "share-runs-over-4-agents",
                    "bash-share", "read-write-overlap-precision", "analysis-cost",
                    "reference-failure-prevalence")
REQUIRED_BEFORE_FREEZE = (
    "repository", "baseCommit", "probe.scriptSha256", "runnerScriptSha256",
    "toolVersions", "workflowCensus", "signedSourceAndBudgetDecision",
    "founderDecisionBindingProposalAndInputsBytes",
)
REQUIRED_RETENTION_EXCLUSIONS = ("transcripts", "prompts", "file-contents", "diffs",
                                 "repository-file-paths")
REQUIRED_CLAIM_LIMITS = ("no-speed-claim", "single-owner-repository",
                         "n-small-descriptive-only")
REQUIRED_EXCLUSIONS = ("agent-did-not-commit", "base-tests-fail",
                       "branch-tests-fail-alone", "flaky-final-tests")
# Literal phrases the human-readable proposal must keep in step with the JSON.
REQUIRED_PROPOSAL_PHRASES = (
    "Proposed and not frozen", "at least 10 eligible", "at most 14",
    "C1a", "C1b", "C2", "C3", "0.3", "40%", "at least 3", "AT-2026-006",
    "reference-failure prevalence", "naive path-overlap precision",
    "Order of evaluation", "takes precedence over", "informs R1 only",
    "closes with R1 only", "EUR 0", "founder runs", "prediction file is hashed", "Freezing",
)
REQUIRED_DECISION_PHRASES = ("EUR 0", "Signature:")
REQUIRED_HYPOTHESIS_PHRASES = ("H-CW1", "Falsification", "untested")


class G0ProposalRejected(ValueError):
    """A registered G0 field, threshold or byte binding failed."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise G0ProposalRejected(reason)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_required_fields(proposal: dict) -> None:
    missing = [name for name in REQUIRED_FIELDS if name not in proposal]
    require(not missing, "required field missing: " + ", ".join(missing))
    require(proposal["recordVersion"] == RECORD_VERSION, "record version changed")


def check_thresholds(proposal: dict) -> None:
    thresholds = proposal.get("thresholds")
    require(isinstance(thresholds, dict) and thresholds == EXPECTED_THRESHOLDS,
            "preregistered thresholds changed or removed")
    require(proposal.get("decisionRule") == EXPECTED_DECISION_RULE,
            "decision rule changed or removed")
    require(proposal.get("killOutcome") == EXPECTED_KILL, "kill outcome changed")


def check_design(proposal: dict) -> None:
    design = proposal["design"]
    require(design.get("minEligibleRuns") == 10 and design.get("maxStartedRuns") == 14,
            "run counts changed")
    require(design.get("agentsPerRun") == {"min": 3, "max": 4}, "agent count changed")
    require(design.get("worktreeIsolation") is True and design.get("agentsMustCommit") is True
            and design.get("workflowPerformsMerge") is False,
            "worktree, commit or merge rule changed")
    require(design.get("predictionsHashedBeforeReference") is True
            and design.get("dropRunsAfterSeeingOutcome") is False,
            "prediction-before-reference rule changed")
    require(design.get("serialOrder")
            == "agent-ordinal-order-fixed-in-run-manifest-before-launch",
            "serial merge order rule changed")
    require(all(reason in design.get("exclusionReasons", [])
                for reason in REQUIRED_EXCLUSIONS), "exclusion reason removed")
    overlap = design.get("overlap", {})
    require(overlap.get("minRunsWithDesignedFileOrSymbolOverlapOfFirstTen") == 7
            and overlap.get("minRunsWithCrossFileContractDependencyOfFirstTen") == 3
            and overlap.get("firstTenOrder")
            == "eligible-runs-in-run-ordinal-fixed-in-manifest-before-launch"
            and overlap.get("designPropertiesFixedInManifestBeforeLaunch") is True,
            "overlap design changed")
    require(design.get("probeUnavailableRuns")
            == "counted-and-reported-outside-the-10-run-minimum-and-the-C1b-C2-C3-denominators",
            "probe-unavailable handling changed")
    reference = proposal["referenceOutcome"]
    require(reference.get("method")
            == "serial-git-merge-in-preregistered-order-then-project-tests"
            and reference.get("referenceFailure")
            == ["textual-conflict", "semantic-failure"]
            and reference.get("finalTestExecutions") == 2
            and reference.get("semanticFailureRequiresFailureInBothExecutions") is True,
            "reference outcome definition changed")
    arms = [arm.get("id") for arm in proposal["arms"]]
    require(all(arm in arms for arm in REQUIRED_ARMS), "required arm removed")
    require(set(arms) <= set(REQUIRED_ARMS + OPTIONAL_ARMS), "unregistered arm added")
    for arm in proposal["arms"]:
        if arm["id"] in REQUIRED_ARMS:
            require(arm.get("required") is True, "required arm made optional")
    require(all(metric in proposal["metrics"] for metric in REQUIRED_METRICS),
            "required metric removed")
    unknown = proposal["unknownRate"]
    require(unknown.get("primary")
            == "pooled-share-of-probe-tool-calls-classified-unknown",
            "primary unknown-rate definition changed")
    probe = proposal["probe"]
    require(probe.get("retainsPaths") is False and probe.get("retainsContent") is False
            and probe.get("retainedOutputs") == "integer-counts-only"
            and probe.get("failedCallsCountAsUnknown") is True
            and probe.get("outsideWorktreePathsMatched") is False,
            "probe retention or classification rule changed")
    retention = proposal["retention"]
    require(all(item in retention.get("notRetained", [])
                for item in REQUIRED_RETENTION_EXCLUSIONS),
            "retention exclusion removed")
    require(all(item in proposal["claimLimits"] for item in REQUIRED_CLAIM_LIMITS),
            "claim limit removed")
    require(set(REQUIRED_BEFORE_FREEZE) <= set(proposal["requiredBeforeFreeze"]),
            "pre-freeze binding removed")


def check_authority_and_budget(proposal: dict) -> None:
    require(proposal["status"] == "pending-founder-decision"
            and proposal["frozen"] is False
            and proposal["executionAuthorization"] is False,
            "proposal falsely claims freezing or authorization")
    require(proposal["runner"] == "founder", "runner changed")
    require(proposal["budget"] == EXPECTED_BUDGET, "budget changed")
    require(proposal["gate"] == "G0" and proposal["milestone"].startswith("M4.6"),
            "gate or milestone changed")
    require(proposal["specs"] == {"owner": "SPEC-053", "dependent": "SPEC-052",
                                  "additiveDependency": "SPEC-023"},
            "spec relationships changed")
    require(proposal["hypothesis"].get("id") == "H-CW1"
            and proposal["hypothesis"].get("evidenceStatus") == "untested",
            "hypothesis identity or status changed")
    require(proposal["sourceAndBudgetDecision"]["status"] == "pending-founder-signature",
            "decision record falsely claims a signature")
    require(proposal["design"].get("repository") is None
            and proposal["design"].get("baseCommit") is None
            and proposal["probe"].get("scriptSha256") is None,
            "unfrozen proposal falsely binds a repository, base or script")


def check_proposal_bytes(proposal: dict, data: bytes) -> None:
    require(proposal["proposal"]["path"] == PROPOSAL_PATH, "proposal path changed")
    require(sha(data) == proposal["proposal"]["sha256"],
            "proposal bytes differ from the pinned hash")
    text = data.decode("utf-8", "strict")
    missing = [phrase for phrase in REQUIRED_PROPOSAL_PHRASES if phrase not in text]
    require(not missing, "proposal text lacks: " + ", ".join(missing))


def check_companion_texts(decision: str, hypothesis: str) -> None:
    missing = [p for p in REQUIRED_DECISION_PHRASES if p not in decision]
    require(not missing, "decision record lacks: " + ", ".join(missing))
    require("**Status:** Pending founder signature." in decision,
            "decision record is not pending founder signature")
    missing = [p for p in REQUIRED_HYPOTHESIS_PHRASES if p not in hypothesis]
    require(not missing, "hypothesis record lacks: " + ", ".join(missing))


def negative_controls(proposal: dict, proposal_bytes: bytes) -> list[str]:
    """Exercise rejection paths in memory without touching any file."""
    cases: list[tuple[str, Callable[[], None]]] = []
    for name in REQUIRED_FIELDS:
        removed = deepcopy(proposal)
        del removed[name]
        cases.append(("removed-field-" + name, lambda r=removed: check_required_fields(r)))
    relaxed = deepcopy(proposal)
    relaxed["thresholds"]["C2"]["minReadWriteOverlapPrecision"] = 0.1
    cases.append(("relaxed-precision", lambda: check_thresholds(relaxed)))
    loosened = deepcopy(proposal)
    loosened["thresholds"]["C3"]["maxUnknownRate"] = 0.9
    cases.append(("relaxed-unknown-rate", lambda: check_thresholds(loosened)))
    dropped = deepcopy(proposal)
    del dropped["thresholds"]["C1b"]
    cases.append(("removed-c1", lambda: check_thresholds(dropped)))
    dropped_a = deepcopy(proposal)
    del dropped_a["thresholds"]["C1a"]
    cases.append(("removed-c1a", lambda: check_thresholds(dropped_a)))
    # C1b must not be satisfiable by commit-level evidence or naive overlap.
    commit_level = deepcopy(proposal)
    commit_level["thresholds"]["C1b"]["flaggedBy"] = ["braid-analyze-git-primary",
                                                       "transcript-probe"]
    cases.append(("c1b-satisfiable-by-commit-level-flag",
                  lambda: check_thresholds(commit_level)))
    narrowed = deepcopy(proposal)
    narrowed["thresholds"]["C1b"]["missedBy"].remove("braid-analyze-git-inclusive")
    cases.append(("c1b-ignores-inclusive-braid-flag",
                  lambda: check_thresholds(narrowed)))
    naive = deepcopy(proposal)
    naive["thresholds"]["C1b"]["missedBy"].remove("naive-path-overlap")
    cases.append(("c1b-ignores-naive-path-overlap", lambda: check_thresholds(naive)))
    gating = deepcopy(proposal)
    gating["thresholds"]["C1a"]["gatesTranscriptRequirements"] = True
    cases.append(("c1a-made-gating", lambda: check_thresholds(gating)))
    no_prevalence = deepcopy(proposal)
    no_prevalence["thresholds"]["C2"]["mustExceedReferenceFailurePrevalence"] = False
    cases.append(("c2-drops-prevalence", lambda: check_thresholds(no_prevalence)))
    no_naive = deepcopy(proposal)
    del no_naive["thresholds"]["C2"]["mustExceedNaivePathOverlapPrecisionWhenDefined"]
    cases.append(("c2-drops-naive-precision", lambda: check_thresholds(no_naive)))
    unordered = deepcopy(proposal)
    del unordered["decisionRule"]["evaluationOrder"]
    cases.append(("removed-evaluation-order", lambda: check_thresholds(unordered)))
    reordered = deepcopy(proposal)
    reordered["decisionRule"]["precedence"] = "inconclusive-over-fail"
    cases.append(("inverted-precedence", lambda: check_thresholds(reordered)))
    fewer = deepcopy(proposal)
    fewer["design"]["minEligibleRuns"] = 3
    cases.append(("fewer-runs", lambda: check_design(fewer)))
    spend = deepcopy(proposal)
    spend["budget"]["additionalSpendEur"] = 25
    cases.append(("nonzero-spend", lambda: check_authority_and_budget(spend)))
    frozen = deepcopy(proposal)
    frozen["frozen"] = True
    cases.append(("false-freeze", lambda: check_authority_and_budget(frozen)))
    leaky = deepcopy(proposal)
    leaky["probe"]["retainsPaths"] = True
    cases.append(("probe-retains-paths", lambda: check_design(leaky)))
    cases.append(("changed-proposal-bytes",
                  lambda: check_proposal_bytes(proposal, proposal_bytes + b"\n ")))
    passed = []
    for name, check in cases:
        try:
            check()
        except G0ProposalRejected:
            passed.append(name)
        else:
            raise G0ProposalRejected("negative control was admitted: " + name)
    return passed


def validate_proposal(root: Path = ROOT) -> dict:
    """Check the registered inputs and return a non-authorizing record."""
    input_bytes = (root / INPUT_PATH).read_bytes()
    proposal = json.loads(input_bytes)
    check_required_fields(proposal)
    check_authority_and_budget(proposal)
    check_thresholds(proposal)
    check_design(proposal)
    proposal_bytes = (root / PROPOSAL_PATH).read_bytes()
    check_proposal_bytes(proposal, proposal_bytes)
    check_companion_texts((root / DECISION_PATH).read_text(encoding="utf-8"),
                          (root / HYPOTHESIS_PATH).read_text(encoding="utf-8"))
    controls = negative_controls(proposal, proposal_bytes)
    return {
        "recordVersion": "agent-braid-claude-workflow-g0-structural-check-1",
        "status": "proposal-structure-valid",
        "inputsSha256": sha(input_bytes),
        "proposalSha256": sha(proposal_bytes),
        "negativeControlsRejected": len(controls),
        "frozen": False,
        "executionAuthorization": False,
        "limits": "Structural and byte checks only; no workflow, transcript, Git "
                  "or network operation was performed and no G0 result exists.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        print(json.dumps(validate_proposal(), sort_keys=True, indent=2))
    except (OSError, ValueError, KeyError, TypeError, UnicodeError, IndexError) as exc:
        parser.exit(1, f"G0 proposal check rejected: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
