# Tasks

## Current status — 2026-10-09

The founder approved bounded whole-M4 alpha engineering/evaluation completion
with negative utility. The decision accepts six bounded exit rows and preserves
the historical SPEC-021 G4 NO-GO. See the [decision record](whole-m4-founder-decision-20261009.json),
[closure packet](whole-m4-closure-packet.md), and [SC-008 evidence](evidence/sc-008.json).
Current GitHub tracking is shown in the [live M4 milestone](https://github.com/jayanez/agent-braid/milestone/6).

## Capture status — 2026-10-08

The exact successor candidate `e66f9a1b94fc5ebfbf784d9c48a76f53c1a656ee`
and manifest received independent review, owner stable-candidate approval
(item 18) and separate capture authorization (item 19). The single registered
capture completed all 20 treatments: 10 complete pairs, including four warm-up
and six measured pairs. All treatments were valid; the separate fresh-process
verifier inspected all 20 before conditional cleanup removed 40 run/grant paths.
The measured median serial/parallel total-wall ratio was `0.6538998702917553`,
favoring serial execution in this finite, uncontrolled sample.

See the [derived registered capture summary](evidence/registered-capture-summary-e66f9a1.json)
for exact bindings, complete denominators, costs, controls and unavailable
observations. The two historical `b85f7e5` pre-dispatch failures remain retained
in the [attempt summary](evidence/pre-dispatch-attempt-summary.json). No capture
was retried or resumed. Historical SPEC-021 G4 NO-GO remains visible. At this
capture-status snapshot, the later founder decision had not yet been recorded.
Source-project code and tests were not executed under this protocol.

T002 approval of the exact source/protocol permits bounded C08 implementation
and evaluation preparation under the user-authorized goal. That approval alone does not permit
registered capture; items 18 and 19 separately approved the e66f9a1 candidate
and its capture. T004 requires a separately reviewed stable candidate and
manifest before exact capture authorization. Dependencies sequence work; they
do not change those boundaries.

- [x] T001 (REQ-001/SC-001,SC-002): Freeze source rights and exact prospective frame.
  Dependencies: none. Targets: `source-rights-manifest.json; exact rights receipts; immutable source commits`.
  Verification and evidence: Nine exact rights/protocol decisions are bound by receipt SHA-256 `160441f088d148210fda174775fc5705fd0e319ccd1ad3b448e2a35cdf96db2f` to the unchanged rights candidate SHA-256 `8f1707b2ae5fc66b5ed5e45fa21d70b9e02a1765ec51c242db96c11bd1e1766d` and protocol packet SHA-256 `656f0b67958e6cf0857bcf3a2908b8235eb2ea43a9a44a8ae18e1c6905790fd2`. Current evidence records the exact two-operation frame and static admission. T001 closes only for bounded local implementation and evaluation preparation; it does not authorize capture.

- [x] T002 (REQ-001,REQ-002,REQ-003/SC-001,SC-002,SC-003,SC-004,SC-005): Obtain exact protocol/source-rights review.
  Dependencies: T001. Targets: `protocol-review-packet.md; separate exact human decision record`.
  Verification and evidence: The exact rights and protocol hashes are bound by the nine-item decision receipt. Its scope is bounded C08 implementation, static admission and evaluation preparation. `evidence/sc-007.json` records this scope and its separate capture boundary. Frozen rights and protocol packets remain unchanged; items 18/19 later authorized e66f9a1 capture. The subsequent whole-M4 decision is recorded in the current status above.

- [x] T003 (REQ-002,REQ-003/SC-003,SC-004,SC-005): Implement the narrow harness slice and prepare a candidate manifest.
  Dependencies: approved T002 and confirmed exact source feasibility. Targets: `one narrow runner; focused novel-invariant tests; successor plan.md, tasks.md and quickstart.md; candidate manifest`.
  Verification and evidence: Merged candidate `7d73c80f1b8c23a65b33bf584abac29a2e097417` passed static admission for two operations and 20 treatment slots; private manifest SHA-256 `72714511b4506c491f4297c900c40e28c0131cc25c9e6ef2f072fa57f0ff1cac`. It is tree-identical to profile candidate `915e90fcf2f84ea7d9fa46da82aa28a5b3796cc6` (tree OID `8a48146a743cd867a8cc0cff0f112383ef838db6`). Local quick and PR profiles each ran 762 tests (758 passed, 4 skipped); receipts/log hashes and candidate-binding caveats are in `evidence/candidate-validation-status.json`. PR #390 merged at 7d73c80f. Hosted PR checks succeeded for selected validators (special matrix skipped); post-merge validation run 37705172263 also passed selected checks. T003 completes only implementation, preparation and local validation; registered-capture scenarios were pending at that historical implementation stage and are now separately recorded for e66f9a1.

- [x] T004 (REQ-002,REQ-005/SC-003,SC-007): Freeze and independently review the stable harness and manifest.
  Dependencies: T003. Targets: `frozen candidate; exact workload manifest; independent review record`.
  Verification and evidence (historical and successor candidates): Independent static C08 code/domain/security review and separate read-only manifest review reported no actionable findings; exact owner stable-candidate review and capture authorization were also granted for `b85f7e5`. The candidate then failed twice before dispatch, with zero actual treatments. These reviews and authorization do not cover a repaired harness candidate. A new candidate and manifest require new exact owner review and capture authorization. See `evidence/pre-dispatch-attempt-summary.json`. Successor e66f9a1 then received fresh independent review and exact owner approvals 18/19; the single authorized capture completed 20 valid treatments with fresh verification before cleanup.

- [x] T005 (REQ-002,REQ-003/SC-003,SC-004,SC-005): Capture only under separate exact authorization.
  Dependencies: approved T004 and exact capture decision. Targets: `raw observation index; environment/candidate receipt; pair outcomes`.
  Verification and planned evidence: Run only the reviewed SPEC-021 policy coordinator in `--mode serial` and `--mode parallel`, using the frozen AB/BA orders, 4 warm-up pairs, 6 measured pairs, exact schedule, budgets, full total-wall phases, and fresh-process control. Preserve all slots, failures, refusals, recoveries and costs. No source-code/test/hook/network/provider execution. Obtained: `evidence/sc-003.json` through `evidence/sc-005.json` and `evidence/registered-capture-summary-e66f9a1.json`: all 20 intended treatments valid, ten pairs retained, fresh verifier inspected 20 before cleanup. Source refusal/recovery controls were not exercised; negative controls remain owned-synthetic evidence.

- [x] T006 (REQ-003,REQ-004/SC-004,SC-005,SC-006): Reconcile all outcomes and interpret limits.
  Dependencies: T005 or a documented infeasible exit. Targets: `bounded result packet; denominator and source-integrity audit`.
  Verification and planned evidence: Report all intended, attempted, valid, invalid, failed, refused, recovered and unexecuted rows, plus full cost and unsupported yield. Negative, null, inconclusive and infeasible outcomes are valid. Obtained: `evidence/sc-004.json` through `evidence/sc-006.json`; independent read-only arithmetic/binding review found no actionable discrepancies, reconciled all phases/residuals and six measured ratios. Median 0.6538998702917553 favors serial in this finite uncontrolled sample; complete costs and unavailable observations are disclosed. Whole-M4 founder acceptance remains separate.

- [x] T007 (REQ-004,REQ-005/SC-006,SC-008): Prepare independent review and the whole-M4 decision packet.
  Dependencies: T006. Targets: `bounded packet; SPEC-021 six-row reconciliation; separate founder decision`.
  Verification and obtained evidence: Preserved historical SPEC-021 G4 NO-GO; the six-row review accepted bounded engineering/evaluation evidence with the stated limits. The founder approved the bounded whole-M4 decision on 2026-10-09. `evidence/sc-008.json` binds the decision SHA-256 `10a88fd2814187fddfb385d8a59dc6a7fc3d326cd6de3f43a4980a208b47d9ce`, six-row review SHA-256 `f2b1a721aaf671edd6b325a3b6703d877064f6eb5ab979eabb6053017bfe3b6d`, closure packet SHA-256 `d832743e8d77cb798dc1aa223a8b45fabdf78f7377ed1d2d3a83bec86a49e83f`, and owner decision receipt SHA-256 `6c4f6a0c6634dfc72f4f5fa2c053627c54c8a1beb741e6d609487d85fa5e3764`. GitHub issue/milestone reconciliation remains pending guarded apply, empty follow-up audit, and Project/milestone verification.

These future tasks do not authorize concurrent agents, source execution,
registered capture, or milestone acceptance. Research completion does not
depend on a favorable utility result.
