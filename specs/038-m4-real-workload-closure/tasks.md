# Tasks

## Development status — 2026-10-08

Exact source rights and protocol are approved. The bounded harness is merged and
validated; static admission and technical review cover two frozen operations and
20 treatment slots. See [implementation readiness](implementation-readiness.md)
for the evidence and scope. Earlier proposal descriptions retain their design-time
context. Owner stable-candidate/manifest review, capture and whole-M4 acceptance
remain pending.

T002 approval of the exact source/protocol permits bounded C08 implementation
and evaluation preparation under the user-authorized goal. It does not permit
registered capture. T004 requires a separately reviewed stable candidate and
manifest before exact capture authorization. Dependencies sequence work; they
do not change those boundaries.

- [x] T001 (REQ-001/SC-001,SC-002): Freeze source rights and exact prospective frame.
  Dependencies: none. Targets: `source-rights-manifest.json; exact rights receipts; immutable source commits`.
  Verification and evidence: Nine exact rights/protocol decisions are bound by receipt SHA-256 `160441f088d148210fda174775fc5705fd0e319ccd1ad3b448e2a35cdf96db2f` to the unchanged rights candidate SHA-256 `8f1707b2ae5fc66b5ed5e45fa21d70b9e02a1765ec51c242db96c11bd1e1766d` and protocol packet SHA-256 `656f0b67958e6cf0857bcf3a2908b8235eb2ea43a9a44a8ae18e1c6905790fd2`. Current evidence records the exact two-operation frame and static admission. T001 closes only for bounded local implementation and evaluation preparation; it does not authorize capture.

- [x] T002 (REQ-001,REQ-002,REQ-003/SC-001,SC-002,SC-003,SC-004,SC-005): Obtain exact protocol/source-rights review.
  Dependencies: T001. Targets: `protocol-review-packet.md; separate exact human decision record`.
  Verification and evidence: The exact rights and protocol hashes are bound by the nine-item decision receipt. Its scope is bounded C08 implementation, static admission and evaluation preparation. `evidence/sc-007.json` records this scope and the still-blocked capture boundary. Frozen rights and protocol packets remain unchanged; registered capture and whole-M4 acceptance are not approved.

- [x] T003 (REQ-002,REQ-003/SC-003,SC-004,SC-005): Implement the narrow harness slice and prepare a candidate manifest.
  Dependencies: approved T002 and confirmed exact source feasibility. Targets: `one narrow runner; focused novel-invariant tests; successor plan.md, tasks.md and quickstart.md; candidate manifest`.
  Verification and evidence: Merged candidate `7d73c80f1b8c23a65b33bf584abac29a2e097417` passed static admission for two operations and 20 treatment slots; private manifest SHA-256 `72714511b4506c491f4297c900c40e28c0131cc25c9e6ef2f072fa57f0ff1cac`. It is tree-identical to profile candidate `915e90fcf2f84ea7d9fa46da82aa28a5b3796cc6` (tree OID `8a48146a743cd867a8cc0cff0f112383ef838db6`). Local quick and PR profiles each ran 762 tests (758 passed, 4 skipped); receipts/log hashes and candidate-binding caveats are in `evidence/candidate-validation-status.json`. PR #390 merged at 7d73c80f. Hosted PR checks succeeded for selected validators (special matrix skipped); post-merge validation run 37705172263 also passed selected checks. T003 completes only implementation, preparation and local validation; registered-capture scenarios SC-003 through SC-006 remain pending.

- [ ] T004 (REQ-002,REQ-005/SC-003,SC-007): Freeze and independently review the stable harness and manifest.
  Dependencies: T003. Targets: `frozen candidate; exact workload manifest; independent review record`.
  Verification and evidence (partial): Independent static C08 code/domain/security review and separate read-only manifest review report no actionable findings. The C08 review did not execute tests or capture; its explicit reviewer bindings cover only the trial engine and fresh verifier, with other hashes operator-observed. Owner stable-candidate/manifest review and separate exact capture authorization remain pending; no duplicate technical review is requested. Planned evidence obligations remain open.

- [ ] T005 (REQ-002,REQ-003/SC-003,SC-004,SC-005): Capture only under separate exact authorization.
  Dependencies: approved T004 and exact capture decision. Targets: `raw observation index; environment/candidate receipt; pair outcomes`.
  Verification and planned evidence: Run only the reviewed SPEC-021 policy coordinator in `--mode serial` and `--mode parallel`, using the frozen AB/BA orders, 4 warm-up pairs, 6 measured pairs, exact schedule, budgets, full total-wall phases, and fresh-process control. Preserve all slots, failures, refusals, recoveries and costs. No source-code/test/hook/network/provider execution. Planned: `evidence/sc-003.json` through `evidence/sc-005.json`. Obtained: none.

- [ ] T006 (REQ-003,REQ-004/SC-004,SC-005,SC-006): Reconcile all outcomes and interpret limits.
  Dependencies: T005 or a documented infeasible exit. Targets: `bounded result packet; denominator and source-integrity audit`.
  Verification and planned evidence: Report all intended, attempted, valid, invalid, failed, refused, recovered and unexecuted rows, plus full cost and unsupported yield. Negative, null, inconclusive and infeasible outcomes are valid. Planned: `evidence/sc-004.json` through `evidence/sc-006.json`. Obtained: none.

- [ ] T007 (REQ-004,REQ-005/SC-006,SC-008): Prepare independent review and the whole-M4 decision packet.
  Dependencies: T006. Targets: `bounded packet; SPEC-021 six-row reconciliation; separate founder decision`.
  Verification and planned evidence: Preserve the historical SPEC-021 G4 NO-GO, audit all six rows, and require a new explicit founder whole-M4 decision before changing milestone status. Planned: `evidence/sc-008.json`. Obtained: none.

These future tasks do not authorize concurrent agents, source execution,
registered capture, or milestone acceptance. Research completion does not
depend on a favorable utility result.
