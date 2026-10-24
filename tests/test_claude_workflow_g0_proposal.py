# SPDX-License-Identifier: AGPL-3.0-only
"""Fail-closed controls for the unfrozen M4.6 gate G0 preregistration."""

from __future__ import annotations

from copy import deepcopy
import json
import unittest

from scripts.validate_claude_workflow_g0_proposal import (
    DECISION_PATH, EXPECTED_THRESHOLDS, HYPOTHESIS_PATH, INPUT_PATH,
    PROPOSAL_PATH, REQUIRED_FIELDS, ROOT, VECTORS_PATH, G0ProposalRejected,
    ALLOWED_DECISION_STATUSES, check_authority_and_budget, check_companion_texts, check_decision_vectors,
    check_design, check_proposal_bytes, check_required_fields, check_thresholds,
    evaluate_g0, negative_controls, validate_proposal,
)


class ClaudeWorkflowG0ProposalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.proposal = json.loads((ROOT / INPUT_PATH).read_text())
        self.proposal_bytes = (ROOT / PROPOSAL_PATH).read_bytes()
        self.vectors = json.loads((ROOT / VECTORS_PATH).read_text())

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
        for criterion in ("C1a", "C1b", "C2", "C3", "C4"):
            changed = deepcopy(self.proposal)
            del changed["thresholds"][criterion]
            with self.subTest(removed=criterion), self.assertRaisesRegex(
                    G0ProposalRejected, "thresholds"):
                check_thresholds(changed)
        for criterion, field, value in (
                ("C1a", "minReferenceFailuresMissedByMergeTreeAndNaiveAndFlaggedByBraid", 0),
                ("C1a", "expectedHits", 5),
                ("C1a", "gatesTranscriptRequirements", True),
                ("C1b", "minReferenceFailuresMissedByAllNonTranscriptArmsAndFlaggedByProbe", 0),
                ("C1b", "gatesTranscriptRequirements", False),
                ("C1b", "flaggedBy", ["braid-analyze-git-primary", "transcript-probe"]),
                ("C1b", "missedBy", ["merge-tree-pairwise", "merge-tree-chained"]),
                ("C1b", "failureClass", "any-reference-failure"),
                ("C1b", "meaningOfPass", "worth-implementing"),
                ("C4", "maxNegativeControlRunsFlagged", 5),
                ("C2", "minReadWriteOverlapPrecision", 0.1),
                ("C2", "minFlaggedRunsToEvaluate", 1),
                ("C2", "mustExceedReferenceFailurePrevalence", False),
                ("C2", "mustExceedNaivePathOverlapPrecisionWhenDefined", False),
                ("C2", "prevalenceReportedBeforeEvaluation", False),
                ("C3", "minAttributionCoverage", 0.3),
                ("C3", "minAttributionCoverage", 0.9),
                ("C3", "comparison", "attributed/changed>0.5"),
                ("C3", "zeroDenominator", "met"),
                ("C3", "countsTowardPassOrFail", False),
                ("C3", "callShareUnknownRateAndBashShare", "gating")):
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
        for phrase in ("0.3", "0.60", "at least 10 eligible", "Revision 3",
                       "5*attributed >= 3*changed", "AT-2026-006",
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
        registered = next((s for s in ALLOWED_DECISION_STATUSES if s in decision), None)
        self.assertIsNotNone(registered, "decision record carries no registered status")
        with self.assertRaisesRegex(G0ProposalRejected, "not pending or superseded"):
            check_companion_texts(decision.replace(registered, "**Status:** Approved."), hypothesis)
        with self.assertRaisesRegex(G0ProposalRejected, "hypothesis record lacks"):
            check_companion_texts(decision, hypothesis.replace("untested", "supported"))

    def test_every_negative_control_is_actually_exercised(self) -> None:
        rejected = negative_controls(self.proposal, self.proposal_bytes, self.vectors)
        self.assertGreaterEqual(len(rejected), len(REQUIRED_FIELDS) + 17 + 40 + 30)
        for name in ("relaxed-precision", "relaxed-attribution-coverage", "removed-c1",
                     "removed-c1a", "c1b-satisfiable-by-commit-level-flag",
                     "c1b-ignores-inclusive-braid-flag",
                     "c1b-ignores-naive-path-overlap", "c1a-made-gating",
                     "c2-drops-prevalence", "c2-drops-naive-precision",
                     "removed-evaluation-order", "inverted-precedence",
                     "fewer-runs", "nonzero-spend", "false-freeze",
                     "probe-retains-paths", "changed-proposal-bytes",
                     "c1b-drops-attribution", "removed-c4", "relaxed-c4",
                     "c3-counts-searches-in-denominator", "flaky-decided-on-reference-outcome",
                     "analysis-set-all-eligible", "indeterminate-becomes-exclusion",
                     "conflicted-fold-continues", "attrition-rule-removed",
                     "attrition-probability-edited", "host-restarts-suppressible",
                     "braid-claims-detection-over-naive", "probe-hashed-after-freeze",
                     "census-not-required-before-freeze", "power-row-edited",
                     "signature-restored-silently", "renewal-not-required",
                     "vectors-wrong-expectation", "vectors-drop-precedence-case",
                     "vectors-drop-c4-branch", "vectors-drop-first-10-case",
                     "c3-reverts-to-call-share-cap", "c3-coverage-floor-relaxed",
                     "c3-coverage-floor-raised", "c3-comparison-changed",
                     "c3-stops-counting", "c3-stops-gating-transcript-requirements",
                     "call-share-unknown-rate-gates-again",
                     "call-share-bash-share-gates-again", "attribution-coverage-removed",
                     "attribution-counts-bash-writes", "attribution-accepts-failed-writes",
                     "attribution-counts-deleted-files",
                     "attribution-zero-denominator-passes",
                     "attribution-comparison-uses-floats", "attribution-stops-gating",
                     "attribution-output-retains-paths",
                     "attribution-output-not-counts-only",
                     "attribution-bash-only-changes-attributed",
                     "attribution-metric-removed", "census-evidence-edited",
                     "census-raw-output-committed", "census-evidence-removed",
                     "revision-reverts-to-2", "revision-adds-renewal",
                     "revision-changes-other-criteria",
                     "revision2-superseded-hash-edited",
                     "revision2-superseded-list-dropped",
                     "superseded-by-wrong-revision",
                     "vectors-drop-c3-boundary-case", "vectors-drop-c3-59-of-100-case",
                     "vectors-drop-c3-zero-denominator-case",
                     "vectors-c3-expectation-flipped",
                     "vectors-c3-attributed-exceeds-changed",
                     "vectors-old-call-share-field"):
            self.assertIn(name, rejected)

    def test_signature_is_superseded_not_valid(self) -> None:
        decision = self.proposal["sourceAndBudgetDecision"]
        self.assertEqual(decision["status"], "signature-superseded-renewal-required")
        self.assertEqual(decision["supersededSignature"]["newHashes"], "computed-at-renewal")
        self.assertEqual(self.proposal["revision"]["number"], 3)
        self.assertFalse(self.proposal["revision"]["renewalAddedByThisRevision"])
        superseded = decision["supersededSignature"]
        self.assertEqual(superseded["supersededBy"], "revision-3")
        self.assertEqual(len(superseded["supersededRevision2BytesSha256"]), 4)
        self.assertEqual(self.proposal["thresholds"]["C3"]["minAttributionCoverage"], 0.6)
        self.assertTrue(self.proposal["revision"]["founderResignatureRequired"])
        changed = deepcopy(self.proposal)
        changed["sourceAndBudgetDecision"]["status"] = "pending-founder-signature"
        with self.assertRaisesRegex(G0ProposalRejected, "valid signature"):
            check_authority_and_budget(changed)

    def test_freeze_order_hashes_the_probe_before_the_freeze(self) -> None:
        order = self.proposal["freezeOrder"]
        self.assertLess(order.index("transcript-layout-and-tool-name-census"),
                        order.index("hash-probe-and-runner"))
        self.assertLess(order.index("hash-probe-and-runner"),
                        order.index("freeze-decision-binding-proposal-inputs-and-vectors-bytes"))
        for binding in ("transcriptLayoutCensus", "plannedRunCount",
                        "eligibleYieldEstimate", "powerOperatingPointAcceptedByFounder"):
            self.assertIn(binding, self.proposal["requiredBeforeFreeze"])

    def test_decision_vectors_are_checked_and_cover_every_branch(self) -> None:
        ids = check_decision_vectors(self.vectors, self.proposal)
        self.assertGreaterEqual(len(ids), 19)
        self.assertGreaterEqual(len(ids), 23)
        for entry in self.vectors["vectors"]:
            with self.subTest(vector=entry["id"]):
                outcome, step, reasons = evaluate_g0(entry["counts"])
                self.assertEqual(outcome, entry["expected"]["outcome"])
                self.assertEqual(step, entry["expected"]["decidedAtStep"])
                self.assertEqual(reasons, entry["expected"]["unmetOrReason"])

    def test_evaluator_boundaries_and_precedence(self) -> None:
        base = {entry["id"]: entry["counts"] for entry in self.vectors["vectors"]}["v01-pass-base"]
        self.assertEqual(evaluate_g0(base)[0], "g0-pass")
        cases = (
            ({"attributedChangedFiles": 60}, "g0-pass"),
            ({"attributedChangedFiles": 59}, "g0-fail"),
            ({"attributedChangedFiles": 3, "changedFiles": 5}, "g0-pass"),
            ({"attributedChangedFiles": 2, "changedFiles": 4}, "g0-fail"),
            ({"attributedChangedFiles": 0, "changedFiles": 0}, "g0-fail"),
            ({"attributedChangedFiles": 100, "changedFiles": 100}, "g0-pass"),
            ({"negativeControlRunsFlagged": 1}, "g0-pass"),
            ({"negativeControlRunsFlagged": 2}, "g0-fail"),
            ({"contractDependencyRuns": 2}, "g0-inconclusive"),
            ({"probeFlaggedRuns": 2, "probeFlaggedReferenceFailures": 2}, "g0-inconclusive"),
            ({"probeFlaggedRuns": 2, "probeFlaggedReferenceFailures": 2,
              "c1bQualifyingFailures": 0}, "g0-fail"),
            ({"probeFlaggedReferenceFailures": 3, "referenceFailureRuns": 6}, "g0-fail"),
            ({"naiveFlaggedRuns": 5, "naiveFlaggedReferenceFailures": 4}, "g0-fail"),
            ({"naiveFlaggedRuns": 0, "naiveFlaggedReferenceFailures": 0}, "g0-pass"),
            ({"eligibleRunsWithProbeData": 9, "analysisSetRuns": 9, "overlapRuns": 6,
              "c1bQualifyingFailures": 0}, "g0-inconclusive"),
        )
        for change, expected in cases:
            with self.subTest(change=change):
                self.assertEqual(evaluate_g0({**base, **change})[0], expected)

    def test_c3_is_attribution_coverage_and_call_share_is_descriptive(self) -> None:
        c3 = self.proposal["thresholds"]["C3"]
        self.assertEqual(c3["comparison"], "5*attributedChangedFiles>=3*changedFiles")
        self.assertEqual(c3["zeroDenominator"], "unmet")
        self.assertFalse(self.proposal["unknownRate"]["gatesAnyCriterion"])
        self.assertEqual(self.proposal["unknownRate"]["role"], "descriptive-only-never-gating")
        self.assertEqual(self.proposal["probe"]["attributionOutputs"]["fields"],
                         ["changedFiles", "attributedChangedFiles"])
        self.assertEqual(self.proposal["censusEvidence"]["toolCalls"], 65639)
        self.assertFalse(self.proposal["censusEvidence"]["rawOutputCommitted"])
        base = {e["id"]: e["counts"] for e in self.vectors["vectors"]}["v01-pass-base"]
        # A call-share style field can no longer be smuggled into a vector.
        self.assertNotIn("unknownWriterCapableCalls", base)
        # A Bash-heavy call mix does not gate: only attribution coverage does.
        self.assertEqual(evaluate_g0({**base, "attributedChangedFiles": 6,
                                      "changedFiles": 10})[0], "g0-pass")
        self.assertEqual(evaluate_g0({**base, "attributedChangedFiles": 5,
                                      "changedFiles": 10})[:3],
                         ("g0-fail", "step-2", ["C3"]))

    def test_power_table_and_attrition_tables_are_published_and_consistent(self) -> None:
        table = self.proposal["powerTable"]
        self.assertTrue(table["founderMustAcceptOperatingPointBeforeFreeze"])
        passes = {row["id"]: row["pass"] for row in table["scenarios"]}
        self.assertLessEqual(passes["uninformative-q0.6"], 0.05)
        self.assertLess(passes["ideal"], 0.7)
        attrition = self.proposal["design"]["attrition"]
        self.assertAlmostEqual(attrition["pEligibleAtLeast10With14Starts"]["0.7"], 0.584)
        self.assertIsNone(attrition["plannedRunCount"])
        text = self.proposal_bytes.decode("utf-8")
        for phrase in ("58.4%", "Power table", "feasibility not refuted",
                       "transcript layout and tool-name"):
            self.assertIn(" ".join(phrase.split()), " ".join(text.split()))


if __name__ == "__main__":
    unittest.main()
