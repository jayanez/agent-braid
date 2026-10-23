# SPDX-License-Identifier: AGPL-3.0-only
"""Fail-closed controls for the unfrozen M4.6 gate G0 preregistration."""

from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_claude_workflow_g0_proposal import (
    DECISION_PATH, EXPECTED_THRESHOLDS, HYPOTHESIS_PATH, INPUT_PATH,
    PROPOSAL_PATH, REQUIRED_FIELDS, ROOT, G0ProposalRejected,
    check_authority_and_budget, check_companion_texts, check_design,
    check_proposal_bytes, check_required_fields, check_thresholds,
    negative_controls, validate_proposal,
)


class ClaudeWorkflowG0ProposalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.proposal = json.loads((ROOT / INPUT_PATH).read_text())
        self.proposal_bytes = (ROOT / PROPOSAL_PATH).read_bytes()

    def test_committed_inputs_pass_every_structural_check(self) -> None:
        record = validate_proposal()
        self.assertEqual(record["status"], "proposal-structure-valid")
        self.assertFalse(record["frozen"])
        self.assertFalse(record["executionAuthorization"])

    def test_removing_any_required_field_is_rejected(self) -> None:
        check_required_fields(self.proposal)
        for field in REQUIRED_FIELDS:
            changed = deepcopy(self.proposal)
            del changed[field]
            with self.subTest(field=field), self.assertRaisesRegex(
                    G0ProposalRejected, "required field missing"):
                check_required_fields(changed)

    def test_removing_or_relaxing_a_threshold_is_rejected(self) -> None:
        check_thresholds(self.proposal)
        self.assertEqual(self.proposal["thresholds"], EXPECTED_THRESHOLDS)
        for criterion in ("C1a", "C1b", "C2", "C3"):
            changed = deepcopy(self.proposal)
            del changed["thresholds"][criterion]
            with self.subTest(removed=criterion), self.assertRaisesRegex(
                    G0ProposalRejected, "thresholds"):
                check_thresholds(changed)
        for criterion, field, value in (
                ("C1a", "minReferenceFailuresMissedByMergeTreeAndFlaggedByBraid", 0),
                ("C1a", "gatesTranscriptRequirements", True),
                ("C1b", "minReferenceFailuresMissedByAllNonTranscriptArmsAndFlaggedByProbe", 0),
                ("C1b", "gatesTranscriptRequirements", False),
                ("C1b", "flaggedBy", ["braid-analyze-git-primary", "transcript-probe"]),
                ("C1b", "missedBy", ["merge-tree-pairwise", "merge-tree-chained"]),
                ("C2", "minReadWriteOverlapPrecision", 0.1),
                ("C2", "minFlaggedRunsToEvaluate", 1),
                ("C2", "mustExceedReferenceFailurePrevalence", False),
                ("C2", "mustExceedNaivePathOverlapPrecisionWhenDefined", False),
                ("C2", "prevalenceReportedBeforeEvaluation", False),
                ("C3", "maxUnknownRate", 0.9)):
            changed = deepcopy(self.proposal)
            changed["thresholds"][criterion][field] = value
            with self.subTest(relaxed=field), self.assertRaisesRegex(
                    G0ProposalRejected, "thresholds"):
                check_thresholds(changed)
        changed = deepcopy(self.proposal)
        del changed["thresholds"]["C2"]["minReadWriteOverlapPrecision"]
        with self.assertRaisesRegex(G0ProposalRejected, "thresholds"):
            check_thresholds(changed)

    def test_decision_rule_and_kill_outcome_cannot_be_weakened(self) -> None:
        changed = deepcopy(self.proposal)
        changed["decisionRule"]["inconclusiveCountsAsPass"] = True
        with self.assertRaisesRegex(G0ProposalRejected, "decision rule"):
            check_thresholds(changed)
        for field, value in (("precedence", "inconclusive-over-fail"),
                             ("c1aGatesNothing", False),
                             ("fail", "any-evaluated-criterion-not-met")):
            changed = deepcopy(self.proposal)
            changed["decisionRule"][field] = value
            with self.subTest(rule=field), self.assertRaisesRegex(
                    G0ProposalRejected, "decision rule"):
                check_thresholds(changed)
        changed = deepcopy(self.proposal)
        del changed["decisionRule"]["evaluationOrder"]
        with self.assertRaisesRegex(G0ProposalRejected, "decision rule"):
            check_thresholds(changed)
        changed = deepcopy(self.proposal)
        changed["decisionRule"]["evaluationOrder"].reverse()
        with self.assertRaisesRegex(G0ProposalRejected, "decision rule"):
            check_thresholds(changed)
        changed = deepcopy(self.proposal)
        changed["killOutcome"]["adoptionTrackTo"] = "continue"
        with self.assertRaisesRegex(G0ProposalRejected, "kill outcome"):
            check_thresholds(changed)

    def test_design_rules_reject_fewer_runs_and_content_retention(self) -> None:
        check_design(self.proposal)
        for path, value in ((("design", "minEligibleRuns"), 5),
                            (("design", "maxStartedRuns"), 30),
                            (("design", "workflowPerformsMerge"), True),
                            (("design", "predictionsHashedBeforeReference"), False),
                            (("probe", "retainsPaths"), True),
                            (("probe", "retainsContent"), True)):
            changed = deepcopy(self.proposal)
            changed[path[0]][path[1]] = value
            with self.subTest(change=path), self.assertRaises(G0ProposalRejected):
                check_design(changed)
        for key, value in (("firstTenOrder", "any-order"),
                           ("designPropertiesFixedInManifestBeforeLaunch", False)):
            changed = deepcopy(self.proposal)
            changed["design"]["overlap"][key] = value
            with self.subTest(overlap=key), self.assertRaisesRegex(
                    G0ProposalRejected, "overlap design"):
                check_design(changed)
        changed = deepcopy(self.proposal)
        changed["design"]["probeUnavailableRuns"] = "counted-as-eligible"
        with self.assertRaisesRegex(G0ProposalRejected, "probe-unavailable"):
            check_design(changed)
        changed = deepcopy(self.proposal)
        changed["arms"] = [arm for arm in changed["arms"]
                           if arm["id"] != "merge-tree-chained"]
        with self.assertRaisesRegex(G0ProposalRejected, "required arm"):
            check_design(changed)
        changed = deepcopy(self.proposal)
        changed["metrics"].remove("read-write-overlap-precision")
        with self.assertRaisesRegex(G0ProposalRejected, "required metric"):
            check_design(changed)
        changed = deepcopy(self.proposal)
        changed["metrics"].remove("reference-failure-prevalence")
        with self.assertRaisesRegex(G0ProposalRejected, "required metric"):
            check_design(changed)

    def test_proposal_cannot_claim_freeze_authorization_or_spend(self) -> None:
        check_authority_and_budget(self.proposal)
        for path, value in ((("frozen",), True),
                            (("executionAuthorization",), True),
                            (("budget", "additionalSpendEur"), 25),
                            (("budget", "extraUsageEnabled"), True),
                            (("budget", "apiCredentialsUsed"), True),
                            (("runner",), "coding-agent")):
            changed = deepcopy(self.proposal)
            target = changed
            for key in path[:-1]:
                target = target[key]
            target[path[-1]] = value
            with self.subTest(change=path), self.assertRaises(G0ProposalRejected):
                check_authority_and_budget(changed)
        changed = deepcopy(self.proposal)
        changed["design"]["repository"] = "owner/repository"
        with self.assertRaisesRegex(G0ProposalRejected, "falsely binds"):
            check_authority_and_budget(changed)

    def test_proposal_bytes_are_pinned_and_keep_the_registered_phrases(self) -> None:
        check_proposal_bytes(self.proposal, self.proposal_bytes)
        with self.assertRaisesRegex(G0ProposalRejected, "pinned hash"):
            check_proposal_bytes(self.proposal, self.proposal_bytes + b"x")
        text = self.proposal_bytes.decode("utf-8")
        for phrase in ("0.3", "40%", "at least 10 eligible", "AT-2026-006",
                       "C1b", "Order of evaluation", "reference-failure prevalence"):
            self.assertIn(phrase, text)
        stripped = self.proposal_bytes.replace(b"0.3", b"0.1")
        changed = deepcopy(self.proposal)
        import hashlib
        changed["proposal"]["sha256"] = hashlib.sha256(stripped).hexdigest()
        with self.assertRaisesRegex(G0ProposalRejected, "proposal text lacks"):
            check_proposal_bytes(changed, stripped)

    def test_decision_record_and_hypothesis_stay_pending_and_untested(self) -> None:
        decision = (ROOT / DECISION_PATH).read_text()
        hypothesis = (ROOT / HYPOTHESIS_PATH).read_text()
        check_companion_texts(decision, hypothesis)
        with self.assertRaisesRegex(G0ProposalRejected, "not pending"):
            check_companion_texts(
                decision.replace("Pending founder signature.", "Approved."), hypothesis)
        with self.assertRaisesRegex(G0ProposalRejected, "hypothesis record lacks"):
            check_companion_texts(decision, hypothesis.replace("untested", "supported"))

    def test_every_negative_control_is_actually_exercised(self) -> None:
        rejected = negative_controls(self.proposal, self.proposal_bytes)
        self.assertGreaterEqual(len(rejected), len(REQUIRED_FIELDS) + 17)
        for name in ("relaxed-precision", "relaxed-unknown-rate", "removed-c1",
                     "removed-c1a", "c1b-satisfiable-by-commit-level-flag",
                     "c1b-ignores-inclusive-braid-flag",
                     "c1b-ignores-naive-path-overlap", "c1a-made-gating",
                     "c2-drops-prevalence", "c2-drops-naive-precision",
                     "removed-evaluation-order", "inverted-precedence",
                     "fewer-runs", "nonzero-spend", "false-freeze",
                     "probe-retains-paths", "changed-proposal-bytes"):
            self.assertIn(name, rejected)


if __name__ == "__main__":
    unittest.main()
