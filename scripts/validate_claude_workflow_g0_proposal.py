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
from math import comb
from pathlib import Path
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parents[1]

INPUT_PATH = "docs/experiments/claude-workflow-g0-inputs.json"
PROPOSAL_PATH = "docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md"
VECTORS_PATH = "docs/experiments/claude-workflow-g0-decision-vectors.json"
DECISION_PATH = "specs/053-claude-transcript-trace-adapter/budget-and-source-decision.md"
HYPOTHESIS_PATH = "research/hypotheses/H-CW1-claude-workflow-integration.md"
RECORD_VERSION = "agent-braid-claude-workflow-g0-input-proposal-1"
VECTORS_VERSION = "agent-braid-claude-workflow-g0-decision-vectors-1"

REQUIRED_FIELDS = (
    "recordVersion", "revision", "status", "frozen", "executionAuthorization", "milestone",
    "gate", "hypothesis", "specs", "proposal", "sourceAndBudgetDecision",
    "runner", "budget", "design", "referenceOutcome", "arms", "probe",
    "metrics", "unknownRate", "thresholds", "decisionRule", "killOutcome",
    "retention", "requiredBeforeFreeze", "claimLimits", "freezeOrder", "powerTable",
)
EXPECTED_THRESHOLDS = {
    # C1a is commit-level evidence: it informs release R1 and unlocks nothing.
    # The Braid primary flag equals naive path overlap at commit level, so it is
    # reported against naive overlap and zero hits are expected.
    "C1a": {
        "role": "commit-level-consistency-informs-R1-only-unlocks-nothing",
        "gatesTranscriptRequirements": False,
        "countsTowardPassOrFail": False,
        "minReferenceFailuresMissedByMergeTreeAndNaiveAndFlaggedByBraid": 1,
        "missedBy": ["merge-tree-pairwise", "merge-tree-chained", "naive-path-overlap"],
        "flaggedBy": ["braid-analyze-git-primary"],
        "expectedHits": 0,
        "hitMeans": "analyzer-and-naive-rule-discrepancy-to-investigate-not-extra-detection",
    },
    # C1b is the only C1 criterion that can unblock PR5 and PR6. A pass means
    # feasibility not refuted; the failure must be attributable to a flagged pair.
    "C1b": {
        "role": "transcript-dependent-feasibility-check-for-PR5-and-PR6",
        "gatesTranscriptRequirements": True,
        "countsTowardPassOrFail": True,
        "meaningOfPass": "feasibility-not-refuted-existence-and-positive-control-not-worth-implementing",
        "minReferenceFailuresMissedByAllNonTranscriptArmsAndFlaggedByProbe": 1,
        "failureClass": "semantic-failure",
        "missedBy": ["merge-tree-pairwise", "merge-tree-chained",
                     "naive-path-overlap", "braid-analyze-git-primary",
                     "braid-analyze-git-inclusive"],
        "flaggedBy": ["transcript-probe"],
        "attribution": {
            "required": True,
            "manifestNamesContractAndOrderedPairBeforeLaunch": True,
            "counterfactualRerunExcludingFlaggedWriterRemovesFailure": True,
            "bothRequired": True,
        },
    },
    "C2": {
        "minReadWriteOverlapPrecision": 0.3,
        "mustExceedReferenceFailurePrevalence": True,
        "mustExceedNaivePathOverlapPrecisionWhenDefined": True,
        "prevalenceDenominator": "first-10-eligible-runs-with-probe-data",
        "prevalenceReportedBeforeEvaluation": True,
        "minFlaggedRunsToEvaluate": 3,
        "unit": "run",
    },
    "C3": {"maxUnknownRate": 0.4, "definition": "unknownRate.primary",
           "cappedOnWriterCapableClasses": True, "zeroDenominator": "unmet"},
    "C4": {
        "role": "negative-controls-probe-must-not-respond",
        "gatesTranscriptRequirements": True,
        "countsTowardPassOrFail": True,
        "minNegativeControlRuns": 3,
        "maxNegativeControlRunsFlagged": 1,
        "unit": "run",
    },
}
EXPECTED_DECISION_RULE = {
    "pass": "C1b-and-C2-and-C3-and-C4-on-the-first-10-eligible-runs-with-probe-data",
    "fail": "C1b-or-C3-or-C4-unmet-or-C2-unmet-when-evaluated-on-the-first-10-"
            "eligible-runs-with-probe-data",
    "inconclusive": "fewer-than-10-eligible-runs-with-probe-data-or-a-design-quota-"
                    "unmet-or-fewer-than-3-probe-flagged-runs-when-C1b-C3-and-C4-are-met",
    "inconclusiveCountsAsPass": False,
    "evaluationOrder": [
        "step-1-fewer-than-10-eligible-runs-with-probe-data-or-a-design-quota-unmet-"
        "is-inconclusive-and-stops",
        "step-2-evaluate-C1b-C3-and-C4-any-unmet-is-fail-and-stops",
        "step-3-fewer-than-3-probe-flagged-runs-is-inconclusive-and-stops",
        "step-4-evaluate-C2-unmet-is-fail-and-stops",
        "step-5-all-met-is-pass",
    ],
    "precedence": "fail-over-inconclusive-once-10-eligible-runs-with-probe-data-exist",
    "c1aGatesNothing": True,
    "designQuotas": {"minOverlapRuns": 7, "minContractDependencyRuns": 3,
                     "minNegativeControlRuns": 3},
    "comparison": "integer-cross-multiplication-no-floats",
    "vectors": VECTORS_PATH,
    "scorerMustPassVectors": "the-g0-kit-scorer-in-a-separate-pull-request-must-pass-"
                             "every-vector-before-its-bytes-are-pinned",
}
EXPECTED_UNKNOWN_RATE = {
    "primary": "share-of-unknown-writer-capable-calls-excluding-read-only-searches",
    "numerator": ["Bash", "mcp__*", "other", "failed-write-class-calls"],
    "denominator": "all-counted-probe-calls-except-Grep-and-Glob",
    "readOnlySearchesReportedSeparately": True,
    "failedReadsReportedSeparately": True,
    "zeroDenominator": "C3-unmet",
    "secondary": ["share-of-analyze-git-operations-unknown-or-partial",
                  "share-of-pairs-unknown", "read-only-search-share"],
}
EXPECTED_ANALYSIS_SET = {
    "primary": "first-10-eligible-runs-with-probe-data-in-manifest-ordinal",
    "laterEligibleRuns": "reported-descriptively-enter-no-criterion",
    "intentionToTreat": "all-started-runs-reported-alongside-with-exclusion-reasons",
    "decidingView": "primary-only",
}
EXPECTED_HOST_RESTARTS = {
    "hostMayRestartStalledAgents": True, "scriptCanSuppress": False,
    "recordedPerAgentInManifest": True, "restartedRunsExcluded": False,
    "excludedOnlyIf": "agent-branch-edited-by-hand",
}
EXPECTED_INDETERMINATE = {
    "definition": "clean-merges-and-the-two-final-test-executions-differ",
    "isExclusion": False, "isHitForAnyArm": False, "qualifiesForC1b": False,
    "countsAsFalsePositiveForFlaggingArm": True, "countsInPrevalenceNumerator": True,
    "direction": "every-choice-works-against-passing",
}
EXPECTED_TEXTUAL_CONFLICT = {
    "foldStopsAtFirstConflictedStep": True, "laterStepsEvaluated": False,
    "semanticLabel": "none", "chainedMergeTreeScoredOnStepsReached": True,
}
EXPECTED_ATTRITION_RULE = (
    "if-plannedRunCount-times-eligibleYieldEstimate-is-below-10-downgrade-to-"
    "observational-or-raise-cap-by-new-proposal-before-freeze")
FREEZE_ORDER = (
    "renew-source-and-budget-signature-against-revised-bytes",
    "transcript-layout-and-tool-name-census",
    "write-probe-against-observed-layout-and-test-on-deidentified-real-fixture",
    "estimate-eligible-yield-and-record-plannedRunCount",
    "hash-probe-and-runner",
    "founder-accepts-power-operating-point",
    "freeze-decision-binding-proposal-inputs-and-vectors-bytes",
    "runs-start",
)
SIGNATURE_STATUS = "signature-superseded-renewal-required"
SUPERSEDED_BYTES = {
    "specs/053-claude-transcript-trace-adapter/budget-and-source-decision.md":
        "333406c25dbdf87b0cd72c2895f441998710e7f3a477e95c137647e12e4a9c62",
    "docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md":
        "02291d0d9cbde74222652ba6b22a4cdd0293fcf7a5aa3c6adf9a119cb6cb3e8d",
    "docs/experiments/claude-workflow-g0-inputs.json":
        "6a5b6167257523947361be3ecba26690a42b5d1316d9045c664f2f71ec628033",
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
                    "reference-failure-prevalence", "negative-control-flag-rate",
                    "intention-to-treat-counts", "read-only-search-share")
REQUIRED_BEFORE_FREEZE = (
    "repository", "baseCommit", "transcriptLayoutCensus", "probe.scriptSha256",
    "runnerScriptSha256", "toolVersions", "workflowCensus", "plannedRunCount",
    "eligibleYieldEstimate", "powerOperatingPointAcceptedByFounder",
    "signedSourceAndBudgetDecision",
    "founderDecisionBindingProposalInputsAndVectorsBytes",
)
REQUIRED_RETENTION_EXCLUSIONS = ("transcripts", "prompts", "file-contents", "diffs",
                                 "repository-file-paths")
REQUIRED_CLAIM_LIMITS = (
    "no-speed-claim", "single-owner-repository", "n-small-descriptive-only",
    "commit-level-braid-flag-equals-naive-path-overlap-plus-unknown-labelling",
    "pass-means-feasibility-not-refuted", "low-power-fail-is-weak-evidence")
REQUIRED_EXCLUSIONS = ("agent-did-not-commit", "base-tests-fail",
                       "branch-tests-fail-alone", "flaky-branch-tests")
FLAKY_DEFINITION = ("pre-merge-double-run-of-each-agent-branch-own-tests-with-"
                    "differing-results-never-decided-on-the-reference-outcome")
REQUIRED_TOOL_CLASS_SPLIT = (
    ["write:Edit|Write|NotebookEdit", "Bash", "mcp__*", "other"], ["Grep|Glob"])
# Literal phrases the human-readable proposal must keep in step with the JSON.
REQUIRED_PROPOSAL_PHRASES = (
    "Proposed and not frozen", "at least 10 eligible", "at most 14",
    "C1a", "C1b", "C2", "C3", "0.3", "40%", "at least 3", "AT-2026-006",
    "reference-failure prevalence", "naive path-overlap precision",
    "Order of evaluation", "takes precedence over", "informs R1 only",
    "closes with R1 only", "EUR 0", "founder runs", "prediction file is hashed", "Freezing",
    "feasibility not refuted", "transcript layout and tool-name census",
    "negative-control", "Power table", "intention-to-treat", "indeterminate",
    "writer-capable", "superseded", "stalled", "two agents changed a common path",
    "decision vectors", "C4", "plannedRunCount", "first 10 eligible runs with probe data",
    "flaky-branch-tests",
)
REQUIRED_DECISION_PHRASES = ("EUR 0", "Signature:")
# The decision record is not owned by this check: it must claim no valid
# signature, either pending or superseded.
ALLOWED_DECISION_STATUSES = ("**Status:** Pending founder signature.",
                             "**Status:** Signature superseded")
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
    require(unknown.get("primary") == EXPECTED_UNKNOWN_RATE["primary"],
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
    check_revised_design(proposal)


def check_revised_design(proposal: dict) -> None:
    """Rules added by revision 2 of the preregistration."""
    design = proposal["design"]
    overlap = design.get("overlap", {})
    require(overlap.get("minNegativeControlRunsOfFirstTen") == 3
            and overlap.get("negativeControlsAreOverlapRuns") is True
            and overlap.get("negativeControlDefinition")
            == "overlap-without-contract-dependency-no-agent-reads-a-path-another-writes-"
               "unless-it-also-writes-it-declared-in-manifest-before-launch"
            and overlap.get("contractDependencyDeclaredInManifest")
            == "symbol-or-contract-and-ordered-reader-writer-pair-before-launch",
            "negative-control design changed")
    require(design.get("analysisSet") == EXPECTED_ANALYSIS_SET, "analysis set changed")
    require(design.get("hostRestarts") == EXPECTED_HOST_RESTARTS,
            "host restart handling changed")
    require(design.get("flakyDefinition") == FLAKY_DEFINITION
            and "flaky-final-tests" not in design.get("exclusionReasons", []),
            "flaky exclusion is decided on the reference outcome")
    attrition = design.get("attrition", {})
    require(attrition.get("plannedRunCountMax") == 14
            and attrition.get("downgradeRule") == EXPECTED_ATTRITION_RULE
            and attrition.get("model") == "binomial-independent-runs-14-starts"
            and "plannedRunCount" in attrition and "eligibleYieldEstimate" in attrition,
            "attrition feasibility rule changed")
    for key, kind in (("pEligibleAtLeast10With14Starts", "tail"),
                      ("pInconclusiveFromAttritionAlone", "complement")):
        table = attrition.get(key)
        require(isinstance(table, dict) and set(table) == {"0.5", "0.6", "0.7", "0.8", "0.9"},
                "attrition table changed: " + key)
        for yield_text, stated in table.items():
            q = float(yield_text)
            tail = sum(comb(14, k) * q ** k * (1 - q) ** (14 - k) for k in range(10, 15))
            expected = tail if kind == "tail" else 1 - tail
            require(abs(stated - expected) < 0.0006,
                    "attrition probability does not match the binomial model")
    reference = proposal["referenceOutcome"]
    require(reference.get("labels") == ["clean", "textual-conflict", "semantic-failure",
                                        "indeterminate"]
            and reference.get("indeterminate") == EXPECTED_INDETERMINATE
            and reference.get("textualConflictHandling") == EXPECTED_TEXTUAL_CONFLICT,
            "reference outcome handling of indeterminate or conflicted runs changed")
    require(proposal["unknownRate"] == EXPECTED_UNKNOWN_RATE, "unknown-rate definition changed")
    probe = proposal["probe"]
    require([probe.get("writerCapableClasses"), probe.get("readOnlySearchClasses")]
            == list(REQUIRED_TOOL_CLASS_SPLIT)
            and probe.get("writtenAgainstCensusLayout") is True
            and probe.get("testedOnDeidentifiedRealFixture") is True
            and probe.get("writeToolsFromCensus") is True,
            "probe tool classes or census binding changed")
    braid = [arm for arm in proposal["arms"] if arm.get("id") == "braid-analyze-git"][0]
    require(braid.get("commitLevelEquivalence")
            == "primary-flag-equals-two-agents-changed-a-common-path-plus-unknown-labelling"
            and braid.get("detectionClaimOverNaivePathOverlap") is False,
            "commit-level equivalence statement removed")
    check_freeze_order(proposal)
    check_power_table(proposal)


def check_freeze_order(proposal: dict) -> None:
    order = proposal.get("freezeOrder")
    require(order == list(FREEZE_ORDER), "freeze order changed")
    position = {step: index for index, step in enumerate(order)}
    require(position["transcript-layout-and-tool-name-census"]
            < position["write-probe-against-observed-layout-and-test-on-deidentified-real-fixture"]
            < position["hash-probe-and-runner"]
            < position["freeze-decision-binding-proposal-inputs-and-vectors-bytes"]
            < position["runs-start"], "probe is hashed after the freeze or the layout is unobserved")


def check_power_table(proposal: dict) -> None:
    table = proposal.get("powerTable", {})
    require(table.get("kind") == "illustrative-monte-carlo-not-a-prediction"
            and table.get("founderMustAcceptOperatingPointBeforeFreeze") is True
            and table.get("c3AssumedMet") is True
            and table.get("analysisRuns") == 10,
            "power table acceptance rule changed")
    scenarios = table.get("scenarios", [])
    ids = [scenario.get("id") for scenario in scenarios]
    require(ids == ["uninformative-q0.6", "uninformative-q0.9", "weaker", "strong", "ideal"],
            "power table scenarios changed")
    for scenario in scenarios:
        total = scenario["pass"] + scenario["fail"] + scenario["inconclusive"]
        require(abs(total - 1.0) < 0.0025, "power table row does not sum to 1")
    by_id = {scenario["id"]: scenario for scenario in scenarios}
    require(by_id["uninformative-q0.6"]["pass"] <= 0.05
            and by_id["uninformative-q0.9"]["pass"] <= 0.05
            and by_id["strong"]["pass"] > by_id["weaker"]["pass"]
            > by_id["uninformative-q0.6"]["pass"]
            and by_id["ideal"]["pass"] >= by_id["strong"]["pass"],
            "power table is not monotone or hides the false-pass rate")
    require(table.get("reading")
            == "low-power-a-fail-is-weak-evidence-and-a-pass-is-feasibility-not-refuted",
            "power table reading changed")


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
    decision = proposal["sourceAndBudgetDecision"]
    require(decision.get("status") == SIGNATURE_STATUS,
            "decision record falsely claims a valid signature")
    superseded = decision.get("supersededSignature", {})
    require(superseded.get("appliedToRevision") == 1
            and superseded.get("appliedToBytesSha256") == SUPERSEDED_BYTES
            and superseded.get("supersededBy") == "revision-2"
            and superseded.get("newHashes") == "computed-at-renewal"
            and superseded.get("renewalRequiredBeforeFreeze") is True,
            "superseded signature record changed")
    revision = proposal["revision"]
    require(revision.get("number") == 2 and revision.get("date") == "2026-10-24"
            and revision.get("changesBoundBytes") is True
            and revision.get("founderResignatureRequired") is True,
            "revision record changed")
    require(proposal["design"].get("repository") is None
            and proposal["design"].get("baseCommit") is None
            and proposal["probe"].get("scriptSha256") is None,
            "unfrozen proposal falsely binds a repository, base or script")


def check_proposal_bytes(proposal: dict, data: bytes) -> None:
    require(proposal["proposal"]["path"] == PROPOSAL_PATH, "proposal path changed")
    require(sha(data) == proposal["proposal"]["sha256"],
            "proposal bytes differ from the pinned hash")
    text = " ".join(data.decode("utf-8", "strict").split())
    missing = [phrase for phrase in REQUIRED_PROPOSAL_PHRASES if phrase not in text]
    require(not missing, "proposal text lacks: " + ", ".join(missing))


TUPLE_FIELDS = (
    "eligibleRunsWithProbeData", "analysisSetRuns", "overlapRuns",
    "contractDependencyRuns", "negativeControlRuns", "negativeControlRunsFlagged",
    "c1bQualifyingFailures", "unknownWriterCapableCalls", "unknownRateDenominatorCalls",
    "probeFlaggedRuns", "probeFlaggedReferenceFailures", "referenceFailureRuns",
    "naiveFlaggedRuns", "naiveFlaggedReferenceFailures",
)
# Every (step, reason) that must decide at least one vector (sole cause, except
# at step 1).
REQUIRED_VECTOR_BRANCHES = (
    ("step-1", "eligible-runs"), ("step-1", "design-quota"),
    ("step-2", "C1b"), ("step-2", "C3"), ("step-2", "C4"),
    ("step-3", "flagged-runs"),
    ("step-4", "C2-threshold"), ("step-4", "C2-prevalence"), ("step-4", "C2-naive"),
    ("step-5", "all-met"),
)
OUTCOMES = {"step-1": "g0-inconclusive", "step-2": "g0-fail", "step-3": "g0-inconclusive",
            "step-4": "g0-fail", "step-5": "g0-pass"}


def evaluate_g0(counts: dict) -> tuple[str, str, list[str]]:
    """Reference evaluation of the registered order, on integer counts only.

    This function only checks that the decision vectors are self-consistent. It
    is not the G0 scorer; the scorer lives in the kit and must pass the vectors.
    """
    n = min(counts["eligibleRunsWithProbeData"], 10)
    reasons: list[str] = []
    if counts["eligibleRunsWithProbeData"] < 10:
        reasons.append("eligible-runs")
    if (counts["overlapRuns"] < 7 or counts["contractDependencyRuns"] < 3
            or counts["negativeControlRuns"] < 3):
        reasons.append("design-quota")
    if reasons:
        return "g0-inconclusive", "step-1", reasons
    if counts["c1bQualifyingFailures"] < 1:
        reasons.append("C1b")
    denominator = counts["unknownRateDenominatorCalls"]
    if denominator <= 0 or counts["unknownWriterCapableCalls"] * 10 > 4 * denominator:
        reasons.append("C3")
    if counts["negativeControlRunsFlagged"] > 1:
        reasons.append("C4")
    if reasons:
        return "g0-fail", "step-2", reasons
    flagged, hits = counts["probeFlaggedRuns"], counts["probeFlaggedReferenceFailures"]
    if flagged < 3:
        return "g0-inconclusive", "step-3", ["flagged-runs"]
    if hits * 10 < 3 * flagged:
        reasons.append("C2-threshold")
    if hits * n <= counts["referenceFailureRuns"] * flagged:
        reasons.append("C2-prevalence")
    naive = counts["naiveFlaggedRuns"]
    if naive > 0 and hits * naive <= counts["naiveFlaggedReferenceFailures"] * flagged:
        reasons.append("C2-naive")
    if reasons:
        return "g0-fail", "step-4", reasons
    return "g0-pass", "step-5", ["all-met"]


def check_vector_counts(counts: dict) -> None:
    require(isinstance(counts, dict) and set(counts) == set(TUPLE_FIELDS),
            "vector tuple fields changed")
    require(all(isinstance(counts[name], int) and not isinstance(counts[name], bool)
                and counts[name] >= 0 for name in TUPLE_FIELDS),
            "vector counts must be non-negative integers")
    n = min(counts["eligibleRunsWithProbeData"], 10)
    require(counts["analysisSetRuns"] == n, "analysis set is not the first 10 eligible runs")
    require(counts["overlapRuns"] + counts["contractDependencyRuns"] <= n
            and counts["negativeControlRuns"] <= counts["overlapRuns"]
            and counts["negativeControlRunsFlagged"] <= counts["negativeControlRuns"]
            and counts["probeFlaggedRuns"] <= n
            and counts["probeFlaggedReferenceFailures"] <= counts["probeFlaggedRuns"]
            and counts["probeFlaggedReferenceFailures"] <= counts["referenceFailureRuns"] <= n
            and counts["c1bQualifyingFailures"] <= counts["probeFlaggedReferenceFailures"]
            and counts["naiveFlaggedRuns"] <= n
            and counts["naiveFlaggedReferenceFailures"] <= counts["naiveFlaggedRuns"]
            and counts["naiveFlaggedReferenceFailures"] <= counts["referenceFailureRuns"]
            and counts["unknownWriterCapableCalls"] <= counts["unknownRateDenominatorCalls"],
            "vector counts are internally inconsistent")


def check_decision_vectors(vectors: dict, proposal: dict) -> list[str]:
    """Check structure, consistency with the evaluator and branch coverage."""
    require(vectors.get("recordVersion") == VECTORS_VERSION
            and vectors.get("frozen") is False
            and vectors.get("executionAuthorization") is False
            and vectors.get("inputs") == INPUT_PATH
            and vectors.get("tupleFields") == list(TUPLE_FIELDS),
            "decision vectors header changed")
    require(proposal["decisionRule"].get("vectors") == VECTORS_PATH,
            "decision rule does not reference the vectors")
    entries = vectors.get("vectors")
    require(isinstance(entries, list) and entries, "decision vectors missing")
    ids = [entry.get("id") for entry in entries]
    require(len(set(ids)) == len(ids), "duplicate vector id")
    sole: set[tuple[str, str]] = set()
    outcomes: set[str] = set()
    for entry in entries:
        counts = entry.get("counts", {})
        check_vector_counts(counts)
        expected = entry.get("expected", {})
        outcome, step, reasons = evaluate_g0(counts)
        require(expected.get("outcome") == outcome
                and expected.get("decidedAtStep") == step
                and expected.get("unmetOrReason") == reasons
                and OUTCOMES[step] == outcome,
                "vector expectation disagrees with the registered order: " + entry["id"])
        outcomes.add(outcome)
        if len(reasons) == 1 or step == "step-1":
            # Fewer than 10 runs can never meet the quotas, so step-1 reasons
            # co-occur; every other branch must be the sole cause in a vector.
            sole.update((step, reason) for reason in reasons)
    require(outcomes == {"g0-pass", "g0-fail", "g0-inconclusive"},
            "vectors do not cover all three outcomes")
    missing = [branch for branch in REQUIRED_VECTOR_BRANCHES if branch not in sole]
    require(not missing, "vectors do not cover branches: " + ", ".join(map(str, missing)))
    # Precedence and first-10 cases must exist, not only branch coverage.
    by_counts = [(entry["counts"], evaluate_g0(entry["counts"])) for entry in entries]
    require(any(c["probeFlaggedRuns"] < 3 and r[0] == "g0-fail" for c, r in by_counts),
            "no vector shows fail taking precedence over inconclusive")
    require(any(c["c1bQualifyingFailures"] < 1 and r[:2] == ("g0-inconclusive", "step-1")
                for c, r in by_counts),
            "no vector shows step 1 stopping before C1b")
    require(any(c["eligibleRunsWithProbeData"] > 10 for c, r in by_counts),
            "no vector exercises the first-10 rule")
    require(any(c["unknownRateDenominatorCalls"] == 0 for c, r in by_counts),
            "no vector exercises the zero denominator")
    require(any(c["naiveFlaggedRuns"] == 0 and r[0] == "g0-pass" for c, r in by_counts),
            "no vector exercises the undefined naive precision")
    require(any(c["unknownWriterCapableCalls"] * 10 == 4 * c["unknownRateDenominatorCalls"]
                and c["unknownRateDenominatorCalls"] > 0 and r[0] == "g0-pass"
                for c, r in by_counts), "no vector exercises the C3 boundary")
    return ids


def check_companion_texts(decision: str, hypothesis: str) -> None:
    missing = [p for p in REQUIRED_DECISION_PHRASES if p not in decision]
    require(not missing, "decision record lacks: " + ", ".join(missing))
    require(any(status in decision for status in ALLOWED_DECISION_STATUSES),
            "decision record is not pending or superseded")
    missing = [p for p in REQUIRED_HYPOTHESIS_PHRASES if p not in hypothesis]
    require(not missing, "hypothesis record lacks: " + ", ".join(missing))


def revised_negative_controls(proposal: dict, vectors: dict) -> list[tuple[str, Callable[[], None]]]:
    """Rejection paths for the rules added by revision 2."""
    cases: list[tuple[str, Callable[[], None]]] = []

    def mutate(name: str, change: Callable[[dict], None],
               check: Callable[[dict], None]) -> None:
        changed = deepcopy(proposal)
        change(changed)
        cases.append((name, lambda c=changed: check(c)))

    def set_in(path: tuple, value) -> Callable[[dict], None]:
        def apply(target: dict) -> None:
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
        return apply

    mutate("c1b-drops-attribution",
           set_in(("thresholds", "C1b", "attribution", "required"), False), check_thresholds)
    mutate("c1b-attribution-needs-only-one-leg",
           set_in(("thresholds", "C1b", "attribution", "bothRequired"), False), check_thresholds)
    mutate("c1b-pass-claims-worth-implementing",
           set_in(("thresholds", "C1b", "meaningOfPass"), "worth-implementing"),
           check_thresholds)
    mutate("c1b-counts-textual-failures",
           set_in(("thresholds", "C1b", "failureClass"), "any-reference-failure"),
           check_thresholds)
    mutate("c1a-ignores-naive-overlap",
           lambda p: p["thresholds"]["C1a"]["missedBy"].remove("naive-path-overlap"),
           check_thresholds)
    mutate("c1a-expects-extra-detection",
           set_in(("thresholds", "C1a", "expectedHits"), 3), check_thresholds)
    mutate("removed-c4", lambda p: p["thresholds"].pop("C4"), check_thresholds)
    mutate("relaxed-c4", set_in(("thresholds", "C4", "maxNegativeControlRunsFlagged"), 3),
           check_thresholds)
    mutate("c4-stops-counting", set_in(("thresholds", "C4", "countsTowardPassOrFail"), False),
           check_thresholds)
    mutate("c3-reverts-to-searches-as-unknown",
           set_in(("unknownRate", "primary"), "pooled-share-of-probe-tool-calls-classified-unknown"),
           check_design)
    mutate("c3-counts-searches-in-denominator",
           set_in(("unknownRate", "denominator"), "all-counted-probe-calls"), check_design)
    mutate("c3-zero-denominator-passes",
           set_in(("thresholds", "C3", "zeroDenominator"), "met"), check_thresholds)
    mutate("probe-merges-search-and-writer-classes",
           set_in(("probe", "readOnlySearchClasses"), []), check_design)
    mutate("flaky-decided-on-reference-outcome",
           lambda p: p["design"]["exclusionReasons"].append("flaky-final-tests"), check_design)
    mutate("flaky-definition-changed",
           set_in(("design", "flakyDefinition"), "final-test-command-differs-in-two-executions"),
           check_design)
    mutate("analysis-set-all-eligible",
           set_in(("design", "analysisSet", "primary"), "all-eligible-runs"), check_design)
    mutate("analysis-set-drops-itt",
           lambda p: p["design"]["analysisSet"].pop("intentionToTreat"), check_design)
    mutate("negative-controls-removed",
           set_in(("design", "overlap", "minNegativeControlRunsOfFirstTen"), 0), check_design)
    mutate("indeterminate-becomes-exclusion",
           set_in(("referenceOutcome", "indeterminate", "isExclusion"), True), check_design)
    mutate("indeterminate-removed",
           lambda p: p["referenceOutcome"]["labels"].remove("indeterminate"), check_design)
    mutate("conflicted-fold-continues",
           set_in(("referenceOutcome", "textualConflictHandling",
                   "laterStepsEvaluated"), True), check_design)
    mutate("attrition-rule-removed",
           set_in(("design", "attrition", "downgradeRule"), "none"), check_design)
    mutate("attrition-probability-edited",
           set_in(("design", "attrition", "pEligibleAtLeast10With14Starts", "0.7"), 0.95),
           check_design)
    mutate("planned-run-count-over-cap",
           set_in(("design", "attrition", "plannedRunCountMax"), 30), check_design)
    mutate("host-restarts-suppressible",
           set_in(("design", "hostRestarts", "scriptCanSuppress"), True), check_design)
    mutate("restarted-runs-excluded",
           set_in(("design", "hostRestarts", "restartedRunsExcluded"), True), check_design)
    mutate("braid-claims-detection-over-naive",
           lambda p: [arm.update({"detectionClaimOverNaivePathOverlap": True})
                      for arm in p["arms"] if arm["id"] == "braid-analyze-git"],
           check_design)
    mutate("probe-hashed-after-freeze",
           lambda p: p["freezeOrder"].reverse(), check_design)
    mutate("census-step-dropped",
           lambda p: p["freezeOrder"].remove("transcript-layout-and-tool-name-census"),
           check_design)
    mutate("census-not-required-before-freeze",
           lambda p: p["requiredBeforeFreeze"].remove("transcriptLayoutCensus"), check_design)
    mutate("planned-run-count-not-required",
           lambda p: p["requiredBeforeFreeze"].remove("plannedRunCount"), check_design)
    mutate("power-acceptance-not-required",
           set_in(("powerTable", "founderMustAcceptOperatingPointBeforeFreeze"), False),
           check_design)
    mutate("power-row-edited",
           set_in(("powerTable", "scenarios", 0, "pass"), 0.5), check_design)
    mutate("power-table-removed", lambda p: p.pop("powerTable"), check_required_fields)
    mutate("revision-removed", lambda p: p.pop("revision"), check_required_fields)
    mutate("signature-restored-silently",
           set_in(("sourceAndBudgetDecision", "status"), "signed"), check_authority_and_budget)
    mutate("superseded-hash-edited",
           set_in(("sourceAndBudgetDecision", "supersededSignature", "appliedToBytesSha256",
                   "docs/experiments/claude-workflow-g0-inputs.json"), "0" * 64),
           check_authority_and_budget)
    mutate("renewal-not-required",
           set_in(("sourceAndBudgetDecision", "supersededSignature",
                   "renewalRequiredBeforeFreeze"), False), check_authority_and_budget)
    mutate("decision-rule-drops-c4",
           lambda p: p["decisionRule"]["evaluationOrder"].__setitem__(
               1, "step-2-evaluate-C1b-and-C3-either-unmet-is-fail-and-stops"),
           check_thresholds)
    mutate("decision-rule-drops-vectors",
           set_in(("decisionRule", "vectors"), "none"), check_thresholds)
    mutate("decision-rule-drops-quotas",
           lambda p: p["decisionRule"].pop("designQuotas"), check_thresholds)
    mutate("claim-limit-equivalence-removed",
           lambda p: p["claimLimits"].remove(
               "commit-level-braid-flag-equals-naive-path-overlap-plus-unknown-labelling"),
           check_design)

    def vector_case(name: str, change: Callable[[dict], None]) -> None:
        changed = deepcopy(vectors)
        change(changed)
        cases.append((name, lambda c=changed: check_decision_vectors(c, proposal)))

    vector_case("vectors-wrong-expectation",
                lambda v: v["vectors"][0]["expected"].update({"outcome": "g0-fail"}))
    vector_case("vectors-drop-precedence-case",
                lambda v: v.update({"vectors": [e for e in v["vectors"]
                                                if e["id"] not in (
                                    "v06-fail-over-inconclusive-no-flags",
                                    "v07-c3-unmet-with-few-flags")]}))
    vector_case("vectors-drop-c4-branch",
                lambda v: v.update({"vectors": [e for e in v["vectors"]
                                                if e["id"] != "v10-c4-two-controls-flagged"]}))
    vector_case("vectors-drop-naive-branch",
                lambda v: v.update({"vectors": [e for e in v["vectors"]
                                                if e["id"] not in ("v16-c2-naive-tie",
                                                                   "v18-c2-naive-better")]}))
    vector_case("vectors-drop-first-10-case",
                lambda v: v.update({"vectors": [e for e in v["vectors"]
                                                if e["id"] != "v04-first-10-rule"]}))
    vector_case("vectors-float-count",
                lambda v: v["vectors"][0]["counts"].update({"probeFlaggedRuns": 5.0}))
    vector_case("vectors-inconsistent-counts",
                lambda v: v["vectors"][0]["counts"].update({"probeFlaggedReferenceFailures": 9}))
    vector_case("vectors-extra-field",
                lambda v: v["vectors"][0]["counts"].update({"extra": 1}))
    vector_case("vectors-duplicate-id",
                lambda v: v["vectors"].append(deepcopy(v["vectors"][0])))
    vector_case("vectors-claim-frozen", lambda v: v.update({"frozen": True}))
    return cases


def negative_controls(proposal: dict, proposal_bytes: bytes,
                      vectors: dict) -> list[str]:
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
    cases.extend(revised_negative_controls(proposal, vectors))
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
    vector_bytes = (root / VECTORS_PATH).read_bytes()
    vectors = json.loads(vector_bytes)
    vector_ids = check_decision_vectors(vectors, proposal)
    controls = negative_controls(proposal, proposal_bytes, vectors)
    return {
        "recordVersion": "agent-braid-claude-workflow-g0-structural-check-1",
        "status": "proposal-structure-valid",
        "inputsSha256": sha(input_bytes),
        "proposalSha256": sha(proposal_bytes),
        "decisionVectorsSha256": sha(vector_bytes),
        "decisionVectorsChecked": len(vector_ids),
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
