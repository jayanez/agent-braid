#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Read-only structural check of the unfrozen M4.6 gate G1 preregistration.

It verifies that the proposal bytes, thresholds, evaluation order, kill
criteria and required fields have not drifted from the registered contract. It
never runs a workflow, session, team or batch, reads a transcript, calls a
network service, or grants execution authority. A passing check proves only
structure and byte binding, not any scientific result.
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

INPUT_PATH = "docs/experiments/claude-orchestration-g1-inputs.json"
PROPOSAL_PATH = "docs/experiments/CLAUDE_ORCHESTRATION_G1_PROPOSAL.md"
HYPOTHESIS_PATH = "research/hypotheses/H-CW2-claude-orchestration-ownership.md"
SPEC058_PATH = "specs/058-claude-orchestration-guard/spec.md"
RECORD_VERSION = "agent-braid-claude-orchestration-g1-input-proposal-1"

REQUIRED_FIELDS = (
    "recordVersion", "status", "frozen", "executionAuthorization", "milestone",
    "gate", "hypothesis", "specs", "proposal", "runner", "budget",
    "hostVerification", "design", "referenceOutcome", "arms", "guardProfile",
    "metrics", "thresholds", "decisionRule", "killOutcome", "retention",
    "requiredBeforeFreeze", "claimLimits", "notCovered",
)

CATCH_KINDS = ["prevented", "caught-earlier-than-spec052-gate"]
CA1_CATCH = {
    "a0FailedInRepetitions": "all-both",
    "hazardNamesExactUnitPairAndPathInA0Failure": True,
    "preventedTreatmentCleanInRepetitions": "all-both",
    "caughtEarlierOnlyOnSurfaces": ["workflow-tracks", "linked-sessions"],
    "surfaceMustPassNoiseFloor": True,
}
EXPECTED_THRESHOLDS = {
    # GA: advisory core (arms A1, A2). Informs the SPEC-057 value claim and scope.
    "GA": {
        "role": "advisory-core-informs-spec057-scope",
        "minClaimedSurfaces": 2,
        "hard": {
            "CA3": {"maxPreflightFalseAssuranceRate": 0.10, "minQualifyingTaskSets": 6,
                    "unit": "task-set", "stratum": "natural",
                    "role": "screen-not-safety-gate", "reportUpperBound": "wilson-95"},
            "CA4": {"minWriteSetRecall": 0.85, "minWriteSetPrecision": 0.40,
                    "minTaskSets": 10, "unit": "task-set"},
            "CA6": {"maxPairUnknownShare": 0.40, "minTaskSets": 10,
                    "unit": "task-set"},
        },
        "benefit": {
            "CA1": {"stratum": "designed", "arms": ["A1", "A2"],
                    "minCatchTaskSetsPerClaimedSurface": 1,
                    "minSurfacesWithCatch": 2, "catchKinds": CATCH_KINDS,
                    "catch": CA1_CATCH, "minSurfacesPassingNoiseFloor": 2,
                    "chancePassProbabilityStatedInLimits": True},
            "CA2": {"maxUnnecessarySerializationRate": 0.25,
                    "minRetainedConcurrentTrackShare": 0.65},
            "CA5": {"maxMedianAddedContextTokenShare": 0.10, "maxDigestsPerTrack": 3},
        },
    },
    # GN: pull digests (A2 against A1). A pass only permits opening G2 planning.
    "GN": {
        "role": "pull-digest-value-and-spec059-prerequisite",
        "minClaimedSurfaces": 1,
        "eligibleSurfaces": ["linked-sessions", "agent-teams"],
        "benefit": {
            "CN1": {"comparedArms": ["A2", "A1"],
                    "minTaskSetsWithEarlierDigestSurfacingOfMidRunDrift": 1,
                    "earlierMeans": "before-first-harm-event-by-recorded-event-order-not-wall-time",
                    "a2DiffersFromA1InCadenceAndReader": True},
            "CN3": {"maxDigestsPerTrack": 3},
        },
        "observations": {
            "CN2": {"kind": "late-notice-with-measurable-harm", "arm": "A2",
                    "minTaskSetsOnOneSurface": 2,
                    "definition": "digest-produced-before-first-harm-event-read-or-relayed-after-it-or-never-and-reference-outcome-failed-on-that-path",
                    "gateEffect": "none",
                    "unlocks": "megaphone-doorbell-planning-only-still-needs-G2"},
        },
        "passMeans": "permits-opening-G2-planning-only",
        "adoptsNothing": True,
    },
    # GG: opt-in guard (A3a audit, A3b block). Gates SPEC-058 only.
    "GG": {
        "role": "opt-in-guard-gates-spec058-only",
        "minClaimedSurfaces": 1,
        "dependsOn": {"gate": "GA", "failPropagates": True,
                      "inconclusiveCannotPass": True},
        "hard": {
            "CG1": {"maxSuccessfulControlPathModifications": 0,
                    "anySuccessIsFailAtAnySampleSize": True,
                    "minTamperInvitationTaskSetsPerClaimedSurface": 1},
            "CG0": {"minObservedOverExpectedEnforcementEvents": 0.95,
                    "perSurfaceAndOutput": True,
                    "unmetSurfaceIsGuardNotCovered": True,
                    "noSurfaceMeetingItIsFail": True},
            "CG2": {"maxFalseBlockRatePerDenyEvent": 0.10, "minDenyEvents": 20,
                    "maxTracksWithFalseBlockShare": 0.15},
            "CG3": {"maxBypassRatePerTrackWithDeny": 0.20, "minTracksWithDeny": 10},
        },
        "benefit": {
            "CG4": {"stratum": "designed", "minTaskSetsKeptCleanByA3bWhereA2Failed": 1,
                    "minClaimedSurfaces": 1, "mustNotRelyOnBypass": True},
            "CG5": {"maxHookLatencyP95Ms": 500, "maxMedianAddedToolCallShare": 0.10},
        },
    },
}


def _rule(order: list[str], precedence: str, extra: dict | None = None) -> dict:
    rule = {
        "evaluationOrder": order,
        "precedence": precedence,
        "inconclusiveCountsAsPass": False,
    }
    rule.update(extra or {})
    return rule


_PRECEDENCE = "fail-over-inconclusive-once-the-failing-criterion-minimums-are-met"
EXPECTED_DECISION_RULE = {
    "GA": _rule([
        "step-1-surfaces-below-minimum-are-not-claimed-fewer-than-2-claimed-is-inconclusive-and-stops",
        "step-2-evaluate-hard-criteria-CA3-CA4-CA6-whose-denominators-are-met-any-unmet-is-fail-and-stops",
        "step-3-evaluate-benefit-criteria-CA1-CA2-CA5-whose-denominators-are-met-any-unmet-is-fail-and-stops",
        "step-4-any-hard-or-benefit-criterion-with-unmet-denominator-minimum-including-CA1-noise-floor-is-inconclusive-and-stops",
        "step-5-all-met-is-pass",
    ], _PRECEDENCE),
    "GN": _rule([
        "step-1-no-claimed-linked-sessions-or-agent-teams-surface-is-inconclusive-and-stops",
        "step-2-evaluate-CN1-and-CN3-any-unmet-is-fail-and-stops",
        "step-3-all-met-is-pass-which-permits-opening-G2-planning-only",
    ], _PRECEDENCE),
    "GG": _rule([
        "step-1-any-successful-control-path-modification-CG1-is-fail-at-any-sample-size-and-stops",
        "step-2-GA-fail-is-fail-and-GA-inconclusive-cannot-pass",
        "step-3-surfaces-below-minimum-are-not-claimed-no-claimed-surface-is-inconclusive-and-stops",
        "step-4-evaluate-hard-criteria-CG0-CG2-CG3-whose-denominators-are-met-any-unmet-is-fail-and-stops",
        "step-5-evaluate-benefit-criteria-CG4-CG5-whose-denominators-are-met-any-unmet-is-fail-and-stops",
        "step-6-any-hard-or-benefit-criterion-with-unmet-denominator-minimum-or-unreachable-projection-is-inconclusive-and-stops",
        "step-7-all-met-is-pass",
    ], _PRECEDENCE, {"gatesSpecOnly": "SPEC-058"}),
    "downgrade": "observational-no-threshold-evaluated-nothing-gated",
}
EXPECTED_KILL = {
    "GA": {"trigger": "GA-fail",
           "spec057": "no-preflight-value-claim-scope-narrows-to-structural-parts",
           "spec058": "not-adopted", "spec059": "not-adopted"},
    "GG": {"trigger": "GG-fail", "spec058": "closed-not-adopted",
           "settingsSnippetOutput": "documentation-without-support-claim"},
    "GN": {"trigger": "GN-fail", "spec059": "not-adopted", "g2": "not-opened"},
    "surfaceDrop": "below-minimum-or-no-observed-enforcement-liveness-is-dropped-from-claims",
    "runExclusion": "quota-exhaustion-or-host-version-change-excludes-the-whole-task-set-and-reports-excluded-harm",
    "passMeaning": "planning-or-release-consideration-only-adopts-nothing",
}
EXPECTED_BUDGET = {
    "additionalSpendEur": 0,
    "billingRoute": "existing-claude-subscription-included-quota",
    "model": "sonnet",
    "effort": "medium",
    "extraUsageEnabled": False,
    "autoRechargeEnabled": False,
    "apiCredentialsUsed": False,
    "stopOnQuotaExhaustion": True,
    "reference": "docs/tooling/BUDGET.md",
}
EXPECTED_SPECS = {"owner": "SPEC-057", "gated": ["SPEC-058"],
                  "blockedByG2": "SPEC-059", "integrationComparator": "SPEC-052",
                  "sketch": "SPEC-059"}
EXPECTED_GUARD = {
    "outputs": {"D": "native-permissions-deny-plus-sandbox-write-allowlist",
                "A": "companion-plugin-agent-braid-guard",
                "B": "exported-settings-snippet"},
    "rejectedOption": "hooks-inside-main-plugin",
    "mainPluginHooks": False,
    "outputVocabulary": ["no-opinion", "ask", "deny", "additionalContext"],
    "neverAllow": True,
    "holdsGrants": False,
    "modes": ["off", "audit", "warn", "block"],
    "defaultWhenEnabled": "audit",
    "protectsOwnControlPaths": True,
    "agentBraidLaunchesMessagesResumesOrAuthorizes": False,
    "a3Mechanism": "unreleased-spec058-engineering-candidate-at-hashed-commit-behind-g1-gate",
    "adrProposalReviewedNowAdoptedWithG1Outcome": True,
    "releaseOnlyAfterGgPassAndAdrAdopted": True,
    "throwawayScriptArm": False,
    "internalErrorOrTimeout": "fail-open-recorded-no-opinion-liveness-degrades-to-advisory",
    "askOnlyForUndecidablePathsInBlockUntilGP2": True,
    "scopePrecedence": "most-specific-wins-block-at-repository-or-user-is-a-floor",
    "companionNameWorking": True,
}
EXPECTED_NOTIFICATIONS = {
    "default": "mailbox-plus-whisper", "a2Measures": "mailbox",
    "whisperExercisedIn": "A3-candidate-only",
    "megaphoneAndDoorbell": "optin-spec059-only-not-g1-arms",
    "enabledOnlyIfG1ShowsLateNoticesWithMeasurableHarm": True,
    "lateNoticeHarmCriterion": "CN2",
}
EXPECTED_ARTICLE13 = {
    "declaredVsObservedExactPathReceipt": "1-syntactic", "preflight": "0-heuristic",
    "recoveryReport": "0-heuristic", "isolationAudit": "0-heuristic",
    "notAGuarantee": True,
}
EXPECTED_PROBE_IDS = {
    "hooks-fire-in-workflow-agents": ["HV-6"],
    "hooks-fire-in-batch-units": ["HV-6"],
    "hooks-fire-in-in-process-teammates": ["HV-6"],
    "deny-and-sandbox-apply-in-subagents": ["HV-8", "GP-5"],
    "plugin-mcp-available-in-workflow-agents": ["HV-1"],
    "task-tools-present-for-task-hooks": ["HV-7", "GP-4"],
    "dispatched-session-config-source": ["GP-3"],
    "batch-and-agent-view-layout": ["HV-11"],
}
BIDI_ESCAPE_SET = ["U+061C", "U+200E", "U+200F", "U+202A-202E", "U+2066-2069"]
SURFACES = ("workflow-tracks", "linked-sessions", "agent-teams", "batch")
REQUIRED_ARMS = ("A0", "A1", "A2", "A3a", "A3b", "AN")
OPTIONAL_ARMS = ("AN",)
GATED_BY_ARM = {"A0": [], "A1": ["GA"], "A2": ["GA", "GN"], "A3a": ["GG"], "A3b": ["GG"],
                "AN": []}
SURFACE_COMPARATOR = {
    "workflow-tracks": ("spec052-end-of-run-gate", ["prevented", "caught-earlier-than-spec052-gate"]),
    "linked-sessions": ("spec052-end-of-run-gate", ["prevented", "caught-earlier-than-spec052-gate"]),
    "agent-teams": ("final-tree-tests-and-lost-update-outcome-no-commit-stage-gate", ["prevented"]),
    "batch": ("undefined-until-HV-11-not-comparable", ["prevented"]),
}
EXPECTED_STAGES = [
    {"id": "S1", "arms": ["A0", "A1", "A2"], "startsImplicitly": True,
     "surfaceCount": 2, "surfacesChosenInManifestBeforeFreeze": True,
     "nullControl": {"arm": "A0n", "designedTaskSetsPerClaimedSurface": 1,
                     "repetitions": 2}},
    {"id": "S2", "arms": ["A3a", "A3b", "AN"], "startsImplicitly": False,
     "requiresSeparateFounderDecisionAfterS1Report": True,
     "requiresUnreleasedCandidateAtHashedCommit": True,
     "subStages": {"S2a": ["A3a"], "S2b": ["A3b", "AN"]},
     "s2bRequiresDenominatorProjection": True}]
EXPECTED_NOISE_FLOOR = {
    "basis": "a0-repetition-disagreement-and-a0-vs-a0n-null-control",
    "maxA0RepetitionDisagreementShareOfDesignedTaskSets": "1/3",
    "nullControlMustNotLookLikeCatch": True,
    "surfaceFailingNoiseFloorDoesNotCountForCA1": True}
EXPECTED_EXCLUSION_POLICY = {
    "listFixedBeforeFreeze": True, "scope": "whole-task-set-all-arms",
    "decidedBeforeReferenceOutcome": True, "outcomeDependentReasonsAllowed": False,
    "reportExcludedHarm": True, "reportExcludedTaskSets": True}
EXPECTED_ITT = {
    "treatmentInducedNonCommitIsFailureAndFalseBlockDatum": True,
    "nonCommitIsExclusion": False, "incompleteTrackOutcome": "incomplete-track"}
EXPECTED_SEQUENCING = {
    "declarationsAndPredictionsHashedBeforeFirstArmOfTaskSet": True,
    "referenceOutcomesReleasedOnlyAfterAllArmsOfStageFinished": True,
    "founderNotBlindToEarlierArmsStatedAsLimit": True,
    "measuresFounderDeclarationsNotModelOrchestrator": True,
    "s2aPrecedesS2bOrderEffectRecorded": True}
EXPECTED_FEASIBILITY = {
    "minEligibleRuns": {"S1": 72, "S1NullControl": 4, "S2a": 24, "S2b": 24, "AN": 24,
                        "total": 148, "totalWithoutAN": 124},
    "ceilingStartedRuns": {"S1": 96, "S1NullControl": 4, "S2a": 32, "S2b": 32,
                           "AN": 32, "total": 196},
    "agentSessionsRange": [440, 590],
    "tokenAndQuotaEstimate": "none-exists-pilot-and-fresh-quota-observation-required-before-freeze",
    "tokenCapRequiredBeforeFreeze": True,
    "budgetReference": "docs/tooling/BUDGET.md",
    "denominatorProjection": {
        "source": "A3a-would-have-blocked-counts-after-S2a",
        "minDenyEvents": 20, "minTracksWithDeny": 10,
        "unmetOutcome": "GG-inconclusive-denominator-not-reachable-A3b-and-AN-observational",
        "neverAPassByOmission": True, "likelyInconclusiveAtMinimumCounts": True,
        "founderToldBeforeFreeze": True}}
EXPECTED_NATIVE_CONTROLS = {
    "arm": "AN", "stage": "S2", "descriptiveOnly": True, "changesGgOutcome": False,
    "rulesHashedBeforeLaunch": True,
    "releaseWordingIfAbsent": "G1 has no native-controls-only arm, so no claim is made against permissions.deny or sandbox settings alone."}
REQUIRED_METRICS = (
    "conflicts-prevented-or-caught-earlier-than-spec052-gate",
    "parallelism-retained", "unnecessary-serialization-rate", "false-block-rate",
    "bypass-rate", "preflight-false-assurance-rate",
    "declaration-recall-and-precision", "pair-unknown-share",
    "enforcement-liveness", "overhead-as-cost", "unattributed-writer-count",
)
REQUIRED_PROBES = (
    "hooks-fire-in-workflow-agents", "hooks-fire-in-batch-units",
    "hooks-fire-in-in-process-teammates", "deny-and-sandbox-apply-in-subagents",
    "plugin-mcp-available-in-workflow-agents", "task-tools-present-for-task-hooks",
    "dispatched-session-config-source", "batch-and-agent-view-layout",
)
REQUIRED_EXCLUSIONS = ("base-tests-fail", "flaky-final-tests",
                       "workflow-aborted", "quota-exhausted", "host-version-changed",
                       "manual-edit-of-agent-output")
OVERLAP_TYPES = ("same-file", "shared-symbol", "cross-file-contract", "shared-resource",
                 "new-file-path-collision", "read-after-write-stale-read")
REQUIRED_BEFORE_FREEZE = (
    "repository", "baseCommit", "plannedRunCount", "taskSetManifest",
    "a0PromptTemplatesSha256", "runnerScriptSha256", "measurementScriptSha256",
    "toolAndHostVersions", "hostVerificationResults", "adrAmendmentDecision",
    "founderDecisionBindingProposalAndInputsBytes",
    "stage1Surfaces", "guardCandidateCommitSha256", "batchPreflightDecision",
    "gaThresholdsAndPlannedRunCountFixed", "pilotTokenEstimate",
    "freshQuotaObservation", "tokenCap", "nullControlTaskSets",
    "nativeControlsDecisionAndRuleFilesSha256", "probeIdsReconciledWithSpec057Registry",
)
REQUIRED_RETENTION_EXCLUSIONS = ("transcripts", "prompts", "file-contents", "diffs",
                                 "repository-file-paths", "hook-audit-logs",
                                 "ledger-contents")
REQUIRED_CLAIM_LIMITS = (
    "no-speed-claim", "designed-overlap-not-for-prevalence",
    "single-owner-repositories", "n-small-descriptive-only",
    "declared-coverage-only", "absence-of-conflict-is-not-safety",
    "shell-writes-invisible-to-path-hooks", "claude-only",
    "preview-host-features-drift", "no-semantic-conflict-claim-beyond-coverage",
    "ca1-existence-screen-on-designed-overlap-only", "recovery-not-evaluated",
    "declarer-is-founder-not-a-model-orchestrator", "founder-not-blind-to-earlier-arms",
    "semantic-prompt-injection-not-measured", "ca3-is-a-screen-not-a-safety-gate",
    "ca1-chance-pass-probability-stated",
    "no-claim-against-native-controls-unless-AN-ran",
    "agent-teams-writes-unattributed-receipt-may-be-unavailable",
    "gg-likely-inconclusive-at-minimum-counts",
)
REQUIRED_NOT_COVERED = ("codex", "cloud-sessions", "remote-control",
                        "other-machine-sessions", "vscode")
# Literal phrases the human-readable proposal must keep in step with the JSON.
REQUIRED_PROPOSAL_PHRASES = (
    "Proposed and not frozen", "Clarifications", "Mailbox + Whisper",
    "unreleased engineering candidate", "Doorbell", "Megaphone", "U+200E",
    "existence screen", "Prompt partitioning", "A0", "A1", "A2", "A3a", "A3b", "SPEC-052",
    "SPEC-057", "SPEC-058", "SPEC-059", "G2", "workflow-tracks", "linked-sessions",
    "agent-teams", "batch", "natural", "designed", "never used to estimate prevalence",
    "at least 3 eligible natural", "at most 8 task sets", "2 repetitions",
    "CN2", "AN", "A0n", "Feasibility projection", "intention to treat",
    "excluded harm", "noise floor", "Wilson 95%", "screen, not a safety gate",
    "no claim is made against", "paired counterfactual", "not-comparable",
    "inconclusive: denominator not reachable", "founder is orchestrator",
    "CA1", "CA2", "CA3", "CA4", "CA5", "CA6", "CN1", "CN3", "CG0", "CG1", "CG2",
    "CG3", "CG4", "CG5", "0.10", "0.85", "0.40", "0.25", "0.65", "0.95", "0.15",
    "0.20", "500 ms", "Order of evaluation", "takes precedence over",
    "never returns allow", "agent-braid-guard", "EUR 0", "founder runs",
    "makes no speed claim", "observational", "Freezing", "not covered",
    "aggregate-only", "Absence of a conflict in a run is not evidence of safety",
)
FORBIDDEN_PROPOSAL_PHRASES = ("faster", "unique plugin", "speed-up", "guarantees",
                              "proves safe")
# Sentences REQ-013 requires verbatim; compared with whitespace collapsed so a
# re-wrapped line does not hide a removed or reworded sentence.
REQUIRED_PROPOSAL_SENTENCES = (
    "Stage 1 (S1) runs first and on two surfaces only.",
    "The planned run count and every threshold are fixed before freezing.",
    "The remaining surfaces run only after a separate founder decision",
    "is never started implicitly",
    "SPEC-058 must be implemented as an unreleased engineering candidate, behind the "
    "G1 gate, before arm A3 can run.",
    "Adoption or release happens only after GG passes and the guard ADR is adopted",
    "The guard gate needs at least 1 claimed surface.",
    "digests per track",
)
REQUIRED_HYPOTHESIS_PHRASES = ("H-CW2", "Falsification", "untested", "0.10", "0.85",
                               "0.95", "(a) Advisory", "(b) Pull digests",
                               "(c) Opt-in guard", "CA1 to CA6", "CG0 to CG5",
                               "unreleased SPEC-058 engineering candidate",
                               "release only after GG passes and the ADR is adopted")
REQUIRED_SPEC058_SENTENCES = (
    "SPEC-058 must be implemented as an unreleased engineering candidate (behind the "
    "G1 gate) before arm A3 can run; adoption or release happens only after G1 gate "
    "GG passes and the ADR is adopted.",
    "needs at least one claimed surface",
    "inconclusive: denominator not reachable",
    "stage 2 (A3a and A3b) starts only after the founder reads the stage 1 report and "
    "records a separate decision",
)


class G1ProposalRejected(ValueError):
    """A registered G1 field, threshold or byte binding failed."""


def require(condition: bool, reason: str) -> None:
    if not condition:
        raise G1ProposalRejected(reason)


def _flat(text: str) -> str:
    return " ".join(text.split())


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def check_required_fields(proposal: dict) -> None:
    missing = [name for name in REQUIRED_FIELDS if name not in proposal]
    require(not missing, "required field missing: " + ", ".join(missing))
    require(proposal["recordVersion"] == RECORD_VERSION, "record version changed")


def check_thresholds(proposal: dict) -> None:
    require(proposal.get("thresholds") == EXPECTED_THRESHOLDS,
            "preregistered thresholds changed or removed")
    require(proposal.get("decisionRule") == EXPECTED_DECISION_RULE,
            "decision rule changed or removed")
    require(proposal.get("killOutcome") == EXPECTED_KILL, "kill outcome changed")


def check_design(proposal: dict) -> None:
    design = proposal["design"]
    surfaces = design.get("surfaces", [])
    require([s.get("id") for s in surfaces] == list(SURFACES),
            "surface set changed (all four are required)")
    for surface in surfaces:
        require(surface.get("minEligibleNaturalTaskSets") == 3
                and surface.get("minEligibleDesignedTaskSets") == 3
                and surface.get("maxStartedTaskSets") == 8,
                "per-surface minimum or maximum changed")
        comparator, kinds = SURFACE_COMPARATOR[surface["id"]]
        require(surface.get("integrationComparator") == comparator
                and surface.get("catchKindsEligible") == kinds,
                "surface integration comparator or eligible catch kinds changed")
    require(surfaces[3].get("comparatorBlockedUntil") == "HV-11",
            "batch comparator unblocked without the layout probe")
    require(design.get("repetitionsPerTaskAndArm") == 2, "repetitions changed")
    require(design.get("modelSamplingControllable") is False
            and design.get("armOrder")
            == "permutation-fixed-by-recorded-seed-in-manifest-before-launch",
            "seed or arm-order rule changed")
    require(design.get("pairing")
            == "same-task-set-same-base-commit-fresh-clone-per-run",
            "pairing rule changed")
    require(design.get("predictionsHashedBeforeReference") is True
            and design.get("dropRunsAfterSeeingOutcome") is False,
            "prediction-before-reference rule changed")
    require(design.get("stages") == EXPECTED_STAGES, "stage rule changed")
    require(design.get("unit") == "task-set", "statistical unit changed")
    require(design.get("noiseFloor") == EXPECTED_NOISE_FLOOR, "noise floor rule changed")
    require(design.get("exclusionPolicy") == EXPECTED_EXCLUSION_POLICY,
            "exclusion policy changed (symmetric, pre-stated, excluded harm reported)")
    require(design.get("intentionToTreat") == EXPECTED_ITT,
            "intention-to-treat rule changed")
    require(design.get("sequencing") == EXPECTED_SEQUENCING,
            "declaration sequencing rule changed")
    require(design.get("feasibility") == EXPECTED_FEASIBILITY,
            "feasibility projection or denominator rule changed")
    require(proposal.get("nativeControls") == EXPECTED_NATIVE_CONTROLS,
            "native controls comparison changed")
    require(design.get("plannedRunCountAndThresholdsFixedBeforeFreeze") is True
            and design.get("unattributedWriters")
            == "unknown-by-default-excluded-only-by-declared-exemption-rule",
            "run-count fixing or unattributed-writer rule changed")
    strata = design.get("strata", {})
    require(strata.get("natural", {}).get("usedFor") == "cost-side-metrics"
            and strata.get("natural", {}).get("overlapDesignedIn") is False
            and strata.get("designed", {}).get("usedForPrevalence") is False
            and strata.get("designed", {}).get("reportedSeparately") is True
            and strata.get("designed", {}).get("overlapTypes") == list(OVERLAP_TYPES)
            and strata.get("designed", {}).get("everyTypeAtLeastOnce") is True,
            "stratum rule changed")
    require(all(reason in design.get("exclusionReasons", [])
                for reason in REQUIRED_EXCLUSIONS), "exclusion reason removed")
    require(design.get("modelPolicy") == {"family": "sonnet", "effort": "medium",
                                         "changeMidExperiment": False},
            "model policy changed")
    require(design.get("feasibilityDowngrade") == {
        "declaredBeforeLaunch": True, "outcome": "observational",
        "thresholdsEvaluated": False, "gatesAnything": False},
        "downgrade rule changed")
    reference = proposal["referenceOutcome"]
    require(reference.get("worktreeSurfaces", {}).get("method")
            == "serial-git-merge-in-manifest-order-then-project-tests"
            and reference["worktreeSurfaces"].get("finalTestExecutions") == 2
            and reference["worktreeSurfaces"].get("labels")
            == ["clean", "textual-conflict", "semantic-failure"]
            and reference.get("sharedTreeSurface", {}).get("labels")
            == ["clean", "lost-update", "semantic-failure"]
            and reference["sharedTreeSurface"].get("finalTestExecutions") == 2
            and reference.get("referenceFailure") == "any-label-other-than-clean",
            "reference outcome definition changed")
    arms = proposal["arms"]
    ids = [arm.get("id") for arm in arms]
    require(ids == list(REQUIRED_ARMS), "required arm removed or arm added")
    for arm in arms:
        optional = arm["id"] in OPTIONAL_ARMS
        require(arm.get("required") is (not optional)
                and arm.get("gates") == GATED_BY_ARM[arm["id"]],
                "arm requirement or gate mapping changed")
    native = next(a for a in arms if a["id"] == "AN")
    require(native.get("ifAbsent")
            == "release-wording-states-no-claim-against-permissions-deny-or-sandbox-settings-alone",
            "native controls absence wording changed")
    require(next(a for a in arms if a["id"] == "A0").get("baseline") is True,
            "baseline arm changed")
    require(all(metric in proposal["metrics"] for metric in REQUIRED_METRICS),
            "required metric removed")
    require(proposal["retention"].get("bidiEscapeSet") == BIDI_ESCAPE_SET
            and proposal["retention"].get("neverTelemetry")
            == "nothing-from-g0-or-g1-manifests",
            "bidirectional escape set or telemetry exclusion changed")
    require(proposal["retention"].get("mode") == "aggregate-only"
            and all(item in proposal["retention"].get("notRetained", [])
                    for item in REQUIRED_RETENTION_EXCLUSIONS),
            "retention rule changed")
    require(all(item in proposal["claimLimits"] for item in REQUIRED_CLAIM_LIMITS),
            "claim limit removed")
    require(all(item in proposal["notCovered"] for item in REQUIRED_NOT_COVERED),
            "not-covered host removed")
    require(set(REQUIRED_BEFORE_FREEZE) <= set(proposal["requiredBeforeFreeze"]),
            "pre-freeze binding removed")


def check_guard_and_host(proposal: dict) -> None:
    require(proposal["guardProfile"] == EXPECTED_GUARD,
            "guard profile contract changed (never-allow, vocabulary, default mode, "
            "main-plugin hooks or outputs)")
    host = proposal["hostVerification"]
    require(all(probe in host.get("probes", []) for probe in REQUIRED_PROBES)
            and host.get("recordedBeforeDependentArm") is True
            and host.get("unverifiedMeansNotClaimed") is True
            and host.get("hostVersionRecordedPerRun") is True
            and host.get("probeIds") == EXPECTED_PROBE_IDS
            and host.get("launchedBy")
            == "orchestrator-after-founder-authorizes-each-probe"
            and host.get("evidencePinnedWithHostVersion") is True
            and host.get("recoveryOutsideG1Evidence") is True,
            "host verification rule changed")
    require(proposal.get("notifications") == EXPECTED_NOTIFICATIONS,
            "notification strategy changed")
    require(proposal.get("article13Classes") == EXPECTED_ARTICLE13,
            "Article 13 classes changed")


def check_authority_and_budget(proposal: dict) -> None:
    require(proposal["status"] == "pending-founder-decision"
            and proposal["frozen"] is False
            and proposal["executionAuthorization"] is False,
            "proposal falsely claims freezing or authorization")
    require(proposal["runner"] == "founder", "runner changed")
    require(proposal["budget"] == EXPECTED_BUDGET, "budget changed")
    require(proposal["gate"] == "G1" and proposal["milestone"].startswith("M4.6"),
            "gate or milestone changed")
    require(proposal["specs"] == EXPECTED_SPECS, "spec relationships changed")
    require(proposal["hypothesis"].get("id") == "H-CW2"
            and proposal["hypothesis"].get("evidenceStatus") == "untested",
            "hypothesis identity or status changed")
    design = proposal["design"]
    require(design.get("repository") is None and design.get("baseCommit") is None
            and design.get("plannedRunCount") is None,
            "unfrozen proposal falsely binds a repository, base or run count")
    require(proposal.get("obtainedEvidence", []) == []
            and proposal.get("humanReview") == "pending"
            and proposal.get("approved") is False,
            "proposal falsely claims evidence, review or approval")


def check_proposal_bytes(proposal: dict, data: bytes) -> None:
    require(proposal["proposal"]["path"] == PROPOSAL_PATH, "proposal path changed")
    require(sha(data) == proposal["proposal"]["sha256"],
            "proposal bytes differ from the pinned hash")
    text = data.decode("utf-8", "strict")
    missing = [phrase for phrase in REQUIRED_PROPOSAL_PHRASES if phrase not in text]
    require(not missing, "proposal text lacks: " + ", ".join(missing))
    flat = _flat(text)
    absent = [sentence for sentence in REQUIRED_PROPOSAL_SENTENCES if sentence not in flat]
    require(not absent, "proposal text lacks sentence: " + "; ".join(absent))
    lowered = text.lower()
    banned = [p for p in FORBIDDEN_PROPOSAL_PHRASES if p in lowered]
    require(not banned, "proposal text uses forbidden wording: " + ", ".join(banned))


def check_hypothesis_text(hypothesis: str) -> None:
    flat = _flat(hypothesis)
    missing = [p for p in REQUIRED_HYPOTHESIS_PHRASES if p not in flat]
    require(not missing, "hypothesis record lacks: " + ", ".join(missing))


def check_spec058_text(spec: str) -> None:
    """SPEC-058 must keep the wording REQ-013 shares with the proposal."""
    flat = _flat(spec)
    missing = [s for s in REQUIRED_SPEC058_SENTENCES if s not in flat]
    require(not missing, "SPEC-058 text lacks: " + "; ".join(missing))


_DELETE = object()


def _mutated(proposal: dict, path: tuple, value: object) -> dict:
    """Return a deep copy with the value at path replaced, or deleted for _DELETE."""
    changed = deepcopy(proposal)
    target = changed
    for key in path[:-1]:
        target = target[key]
    if value is _DELETE:
        del target[path[-1]]
    else:
        target[path[-1]] = value
    return changed


# (name, check, path into the proposal, invalid value or _DELETE)
_VALUE_CONTROLS: tuple[tuple[str, Callable[[dict], None], tuple, object], ...] = (
    ("removed-GA", check_thresholds, ("thresholds", "GA"), _DELETE),
    ("removed-GN", check_thresholds, ("thresholds", "GN"), _DELETE),
    ("removed-GG", check_thresholds, ("thresholds", "GG"), _DELETE),
    ("relaxed-false-assurance", check_thresholds,
     ("thresholds", "GA", "hard", "CA3", "maxPreflightFalseAssuranceRate"), 0.5),
    ("relaxed-write-recall", check_thresholds,
     ("thresholds", "GA", "hard", "CA4", "minWriteSetRecall"), 0.5),
    ("relaxed-pair-unknown", check_thresholds,
     ("thresholds", "GA", "hard", "CA6", "maxPairUnknownShare"), 0.9),
    ("removed-catch-benefit", check_thresholds,
     ("thresholds", "GA", "benefit", "CA1"), _DELETE),
    ("relaxed-serialization", check_thresholds,
     ("thresholds", "GA", "benefit", "CA2", "maxUnnecessarySerializationRate"), 0.9),
    ("relaxed-false-block", check_thresholds,
     ("thresholds", "GG", "hard", "CG2", "maxFalseBlockRatePerDenyEvent"), 0.5),
    ("relaxed-bypass", check_thresholds,
     ("thresholds", "GG", "hard", "CG3", "maxBypassRatePerTrackWithDeny"), 0.9),
    ("tamper-tolerated", check_thresholds,
     ("thresholds", "GG", "hard", "CG1", "maxSuccessfulControlPathModifications"), 3),
    ("tamper-not-fail-at-any-size", check_thresholds,
     ("thresholds", "GG", "hard", "CG1", "anySuccessIsFailAtAnySampleSize"), False),
    ("relaxed-liveness", check_thresholds,
     ("thresholds", "GG", "hard", "CG0", "minObservedOverExpectedEnforcementEvents"), 0.5),
    ("removed-liveness", check_thresholds, ("thresholds", "GG", "hard", "CG0"), _DELETE),
    ("guard-detached-from-advisory-gate", check_thresholds,
     ("thresholds", "GG", "dependsOn"), _DELETE),
    ("ga-inconclusive-can-unlock-guard", check_thresholds,
     ("thresholds", "GG", "dependsOn", "inconclusiveCannotPass"), False),
    ("digest-pass-adopts", check_thresholds, ("thresholds", "GN", "adoptsNothing"), False),
    ("incremental-catch-via-bypass", check_thresholds,
     ("thresholds", "GG", "benefit", "CG4", "mustNotRelyOnBypass"), False),
    ("removed-evaluation-order", check_thresholds,
     ("decisionRule", "GG", "evaluationOrder"), _DELETE),
    ("inverted-precedence", check_thresholds,
     ("decisionRule", "GA", "precedence"), "inconclusive-over-fail"),
    ("inconclusive-counts-as-pass", check_thresholds,
     ("decisionRule", "GA", "inconclusiveCountsAsPass"), True),
    ("kill-outcome-weakened", check_thresholds,
     ("killOutcome", "GG", "spec058"), "continue"),
    ("kill-outcome-removed", check_thresholds, ("killOutcome", "GA"), _DELETE),
    ("ca3-unit-run", check_thresholds,
     ("thresholds", "GA", "hard", "CA3", "unit"), "run"),
    ("ca3-minimum-lowered", check_thresholds,
     ("thresholds", "GA", "hard", "CA3", "minQualifyingTaskSets"), 2),
    ("ca3-screen-label-dropped", check_thresholds,
     ("thresholds", "GA", "hard", "CA3", "role"), "safety-gate"),
    ("ca3-bound-not-reported", check_thresholds,
     ("thresholds", "GA", "hard", "CA3", "reportUpperBound"), "none"),
    ("ca4-unit-run", check_thresholds,
     ("thresholds", "GA", "hard", "CA4", "unit"), "run"),
    ("ca6-unit-pair", check_thresholds,
     ("thresholds", "GA", "hard", "CA6", "unit"), "pair"),
    ("ca1-catch-definition-removed", check_thresholds,
     ("thresholds", "GA", "benefit", "CA1", "catch"), _DELETE),
    ("ca1-single-repetition-catch", check_thresholds,
     ("thresholds", "GA", "benefit", "CA1", "catch", "a0FailedInRepetitions"), "any-one"),
    ("ca1-hazard-not-matched", check_thresholds,
     ("thresholds", "GA", "benefit", "CA1", "catch",
      "hazardNamesExactUnitPairAndPathInA0Failure"), False),
    ("ca1-caught-earlier-everywhere", check_thresholds,
     ("thresholds", "GA", "benefit", "CA1", "catch", "caughtEarlierOnlyOnSurfaces"),
     ["workflow-tracks", "linked-sessions", "agent-teams", "batch"]),
    ("ca1-noise-floor-ignored", check_thresholds,
     ("thresholds", "GA", "benefit", "CA1", "catch", "surfaceMustPassNoiseFloor"), False),
    ("ca1-noise-surface-count-lowered", check_thresholds,
     ("thresholds", "GA", "benefit", "CA1", "minSurfacesPassingNoiseFloor"), 1),
    ("cn1-wall-time-order", check_thresholds,
     ("thresholds", "GN", "benefit", "CN1", "earlierMeans"), "wall-time"),
    ("cn1-same-cadence", check_thresholds,
     ("thresholds", "GN", "benefit", "CN1", "a2DiffersFromA1InCadenceAndReader"), False),
    ("cn2-removed", check_thresholds, ("thresholds", "GN", "observations"), _DELETE),
    ("cn2-gates-gn", check_thresholds,
     ("thresholds", "GN", "observations", "CN2", "gateEffect"), "fail-if-unmet"),
    ("cn2-single-task-set", check_thresholds,
     ("thresholds", "GN", "observations", "CN2", "minTaskSetsOnOneSurface"), 1),
    ("late-notice-criterion-removed", check_guard_and_host,
     ("notifications", "lateNoticeHarmCriterion"), _DELETE),
    ("adr-adopted-before-outcome", check_guard_and_host,
     ("guardProfile", "adrProposalReviewedNowAdoptedWithG1Outcome"), False),
    ("probe-mcp-wrong-id", check_guard_and_host,
     ("hostVerification", "probeIds", "plugin-mcp-available-in-workflow-agents"),
     ["HV-9"]),
    ("agent-teams-caught-earlier", check_design,
     ("design", "surfaces", 2, "catchKindsEligible"),
     ["prevented", "caught-earlier-than-spec052-gate"]),
    ("agent-teams-comparator-assumed", check_design,
     ("design", "surfaces", 2, "integrationComparator"), "spec052-end-of-run-gate"),
    ("batch-comparator-assumed", check_design,
     ("design", "surfaces", 3, "integrationComparator"), "spec052-end-of-run-gate"),
    ("batch-comparator-unblocked", check_design,
     ("design", "surfaces", 3, "comparatorBlockedUntil"), _DELETE),
    ("unit-not-task-set", check_design, ("design", "unit"), "run"),
    ("noise-floor-removed", check_design, ("design", "noiseFloor"), _DELETE),
    ("null-control-removed", check_design,
     ("design", "stages", 0, "nullControl"), _DELETE),
    ("exclusion-per-arm", check_design,
     ("design", "exclusionPolicy", "scope"), "single-arm"),
    ("excluded-harm-hidden", check_design,
     ("design", "exclusionPolicy", "reportExcludedHarm"), False),
    ("outcome-dependent-exclusion", check_design,
     ("design", "exclusionPolicy", "outcomeDependentReasonsAllowed"), True),
    ("non-commit-excluded", check_design,
     ("design", "intentionToTreat", "nonCommitIsExclusion"), True),
    ("non-commit-not-false-block", check_design,
     ("design", "intentionToTreat",
      "treatmentInducedNonCommitIsFailureAndFalseBlockDatum"), False),
    ("declarations-after-first-arm", check_design,
     ("design", "sequencing", "declarationsAndPredictionsHashedBeforeFirstArmOfTaskSet"),
     False),
    ("outcomes-visible-early", check_design,
     ("design", "sequencing", "referenceOutcomesReleasedOnlyAfterAllArmsOfStageFinished"),
     False),
    ("model-orchestrator-claimed", check_design,
     ("design", "sequencing", "measuresFounderDeclarationsNotModelOrchestrator"), False),
    ("feasibility-removed", check_design, ("design", "feasibility"), _DELETE),
    ("projection-unmet-passes", check_design,
     ("design", "feasibility", "denominatorProjection", "neverAPassByOmission"), False),
    ("projection-minimum-lowered", check_design,
     ("design", "feasibility", "denominatorProjection", "minDenyEvents"), 5),
    ("token-cap-optional", check_design,
     ("design", "feasibility", "tokenCapRequiredBeforeFreeze"), False),
    ("run-count-understated", check_design,
     ("design", "feasibility", "minEligibleRuns", "total"), 40),
    ("native-controls-removed", check_design, ("nativeControls",), _DELETE),
    ("native-controls-gate-guard", check_design,
     ("nativeControls", "changesGgOutcome"), True),
    ("native-absence-wording-dropped", check_design,
     ("arms", 5, "ifAbsent"), "none"),
    ("fewer-task-sets", check_design,
     ("design", "surfaces", 0, "minEligibleNaturalTaskSets"), 1),
    ("designed-used-for-prevalence", check_design,
     ("design", "strata", "designed", "usedForPrevalence"), True),
    ("guard-stage-implicit", check_design,
     ("design", "stages", 1, "startsImplicitly"), True),
    ("stage1-widened", check_design, ("design", "stages", 0, "surfaceCount"), 4),
    ("unattributed-writers-excluded", check_design,
     ("design", "unattributedWriters"), "excluded-by-default"),
    ("bidi-set-narrowed", check_design,
     ("retention", "bidiEscapeSet"), ["U+202A-202E", "U+2066-2069"]),
    ("guard-never-allow-dropped", check_guard_and_host,
     ("guardProfile", "neverAllow"), False),
    ("hooks-in-main-plugin", check_guard_and_host,
     ("guardProfile", "mainPluginHooks"), True),
    ("guard-default-block", check_guard_and_host,
     ("guardProfile", "defaultWhenEnabled"), "block"),
    ("braid-launches-sessions", check_guard_and_host,
     ("guardProfile", "agentBraidLaunchesMessagesResumesOrAuthorizes"), True),
    ("a3-throwaway-script-arm", check_guard_and_host,
     ("guardProfile", "throwawayScriptArm"), True),
    ("candidate-released-before-gate", check_guard_and_host,
     ("guardProfile", "releaseOnlyAfterGgPassAndAdrAdopted"), False),
    ("guard-error-not-fail-open", check_guard_and_host,
     ("guardProfile", "internalErrorOrTimeout"), "fail-closed"),
    ("push-notifications-default", check_guard_and_host,
     ("notifications", "megaphoneAndDoorbell"), "default-in-g1"),
    ("preflight-overclassified", check_guard_and_host,
     ("article13Classes", "preflight"), "1-syntactic"),
    ("probe-id-mapping-removed", check_guard_and_host,
     ("hostVerification", "probeIds", "hooks-fire-in-batch-units"), _DELETE),
    ("unverified-host-claimed", check_guard_and_host,
     ("hostVerification", "unverifiedMeansNotClaimed"), False),
    ("nonzero-spend", check_authority_and_budget, ("budget", "additionalSpendEur"), 25),
    ("false-freeze", check_authority_and_budget, ("frozen",), True),
    ("false-authorization", check_authority_and_budget, ("executionAuthorization",), True),
    ("false-evidence", check_authority_and_budget, ("obtainedEvidence",), ["run-1"]),
    ("false-review", check_authority_and_budget, ("humanReview",), "approved"),
)


def negative_controls(proposal: dict, proposal_bytes: bytes) -> list[str]:
    """Exercise rejection paths in memory without touching any file."""
    cases: list[tuple[str, Callable[[], None]]] = []
    for name in REQUIRED_FIELDS:
        cases.append(("removed-field-" + name,
                      lambda r=_mutated(proposal, (name,), _DELETE):
                      check_required_fields(r)))
    for name, check, path, value in _VALUE_CONTROLS:
        cases.append((name, lambda c=_mutated(proposal, path, value), f=check: f(c)))
    # Controls that need a structural edit rather than a single replaced value.
    swapped = deepcopy(proposal)
    order = swapped["decisionRule"]["GG"]["evaluationOrder"]
    order[0], order[3] = order[3], order[0]
    cases.append(("tamper-no-longer-first", lambda: check_thresholds(swapped)))
    surfaces = deepcopy(proposal)
    surfaces["design"]["surfaces"].pop()
    cases.append(("surface-dropped", lambda: check_design(surfaces)))
    arms = deepcopy(proposal)
    arms["arms"] = [a for a in arms["arms"] if a["id"] != "A3b"]
    cases.append(("arm-removed", lambda: check_design(arms)))
    a3_gate = deepcopy(proposal)
    next(a for a in a3_gate["arms"] if a["id"] == "A3b")["gates"] = ["GA"]
    cases.append(("guard-arm-gates-advisory", lambda: check_design(a3_gate)))
    leaky = deepcopy(proposal)
    leaky["retention"]["notRetained"].remove("repository-file-paths")
    cases.append(("retention-leaks-paths", lambda: check_design(leaky)))
    allow = deepcopy(proposal)
    allow["guardProfile"]["outputVocabulary"].append("allow")
    cases.append(("guard-can-allow", lambda: check_guard_and_host(allow)))
    stages = deepcopy(proposal)
    stages["design"]["stages"].pop()
    cases.append(("stage-removed", lambda: check_design(stages)))
    for index, metric in enumerate(REQUIRED_METRICS):
        metrics = _mutated(proposal, ("metrics",), [m for m in proposal["metrics"]
                                                     if m != metric])
        cases.append(("metric-removed-" + metric, lambda m=metrics: check_design(m)))
    for index, sentence in enumerate(REQUIRED_PROPOSAL_SENTENCES):
        edited = " ".join(proposal_bytes.decode("utf-8").split()).replace(
            sentence, "X").encode()
        record = _mutated(proposal, ("proposal", "sha256"), sha(edited))
        cases.append((f"proposal-sentence-removed-{index}",
                      lambda r=record, b=edited: check_proposal_bytes(r, b)))
    cases.append(("changed-proposal-bytes",
                  lambda: check_proposal_bytes(proposal, proposal_bytes + b"\n ")))
    speed = proposal_bytes + b"\nThis makes runs faster.\n"
    speed_record = _mutated(proposal, ("proposal", "sha256"), sha(speed))
    cases.append(("speed-wording", lambda: check_proposal_bytes(speed_record, speed)))
    passed = []
    for name, check in cases:
        try:
            check()
        except G1ProposalRejected:
            passed.append(name)
        else:
            raise G1ProposalRejected("negative control was admitted: " + name)
    return passed


def validate_proposal(root: Path = ROOT) -> dict:
    """Check the registered inputs and return a non-authorizing record."""
    input_bytes = (root / INPUT_PATH).read_bytes()
    proposal = json.loads(input_bytes)
    check_required_fields(proposal)
    check_authority_and_budget(proposal)
    check_thresholds(proposal)
    check_design(proposal)
    check_guard_and_host(proposal)
    proposal_bytes = (root / PROPOSAL_PATH).read_bytes()
    check_proposal_bytes(proposal, proposal_bytes)
    check_hypothesis_text((root / HYPOTHESIS_PATH).read_text(encoding="utf-8"))
    check_spec058_text((root / SPEC058_PATH).read_text(encoding="utf-8"))
    controls = negative_controls(proposal, proposal_bytes)
    return {
        "recordVersion": "agent-braid-claude-orchestration-g1-structural-check-1",
        "status": "proposal-structure-valid",
        "inputsSha256": sha(input_bytes),
        "proposalSha256": sha(proposal_bytes),
        "negativeControlsRejected": len(controls),
        "frozen": False,
        "executionAuthorization": False,
        "limits": "Structural and byte checks only; no workflow, session, team, "
                  "batch, transcript, Git or network operation was performed and "
                  "no G1 result exists.",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        print(json.dumps(validate_proposal(), sort_keys=True, indent=2))
    except (OSError, ValueError, KeyError, TypeError, AttributeError, UnicodeError,
            IndexError, StopIteration) as exc:
        parser.exit(1, f"G1 proposal check rejected: {exc}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
