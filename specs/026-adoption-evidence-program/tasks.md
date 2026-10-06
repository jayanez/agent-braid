# Tasks

All tasks are unchecked implementation work. Targets describe planned files.
Dependencies order the work; they do not authorize agents, contact or publication.
Use `quickstart.md` acceptance contracts until concrete tests are added. Record
actual input/candidate/protocol hashes, commands, outcomes and limits before
checking any task or adding obtained evidence.

- [ ] T001 (REQ-001/SC-001): Define the prospective organization and workload evidence frame
  - Dependencies: none; inspect SPEC-002, SPEC-011 and community/release policy.
  - Targets: `research/adoption/evidence-program/` frame/protocol/fixture files, new versioned governance intake contracts selected in the implementation PR, and `tests/test_adoption_evidence.py`.
  - Deliverable: synthetic canonical organization/workload/episode IDs, alias and overlapping-segment deduplication, unit distinctions, source permission/inclusion/exclusion/retention rules and a frozen collection-window format. Real intake requires a reviewed admitted source; actual yield stays explicit.
  - Verification/evidence: SC-001 contract; duplicate aliases/cross-label cases count once, distinct workloads remain distinct, unresolved joins and non-admitted real evidence reject. Save frame/version/migration note and independently fixed eligible counts.
- [ ] T002 (REQ-002/SC-002): Implement the provenance-bearing metric manifest and aggregation
  - Dependencies: T001.
  - Targets: metric manifest/schema, stdlib aggregation module and synthetic expected outputs under `research/adoption/evidence-program/`, `tests/test_adoption_evidence.py`.
  - Deliverable: formulas/units, fixed baselines, observed-versus-proxy label, source window, eligibility, denominator/missing/excluded counts, input hashes and interpretation limits for use/usability/cost/contribution/reproduction metrics.
  - Verification/evidence: SC-002 contract; independently fixed arithmetic, wrong-unit/cross-unit/duplicate/missing-as-zero controls and popularity/market-proxy rejection. Save manifest/input/output hashes and raw aggregation results.
- [ ] T003 (REQ-003/SC-003): Add a local report-usability and integration-cost pilot protocol
  - Dependencies: T002.
  - Targets: pilot protocol, synthetic baseline/report episode intake and fixtures under `research/adoption/evidence-program/`, `tests/test_adoption_evidence.py`.
  - Deliverable: task completion/error/unknown observations separate from judgment, candidate/input/report/environment binding, setup/run/review/debugging time and failures/abandonments. Freeze real eligibility/rights/yield, rubric, baseline, allocation/order, adjudication and organization/workload holdout before any real comparison.
  - Verification/evidence: SC-003 contract; complete totals and missing/abstention visibility on synthetic episodes. Save predeclared expected episode outcomes, protocol and raw outputs. No interviews/contact or real benefit claim is part of this task.
- [ ] T004 (REQ-004/SC-004): Implement contribution and counterexample intake with replay disposition
  - Dependencies: T001.
  - Targets: local contribution/counterexample intake and fixtures under `research/adoption/evidence-program/`, `tests/test_adoption_evidence.py`.
  - Deliverable: rights/author/conflict metadata, observed boundary, replay candidate/inputs/commands, expected/observed divergence, minimization and reviewer state; explicit duplicate/rejected/pending reasons preserve negative/inconclusive cases.
  - Verification/evidence: SC-004 contract; synthetic replayable divergence plus missing-rights, duplicate and unreplayable controls. Save replay output and intake dispositions; contribution counts alone support no correctness or novelty claim.
- [ ] T005 (REQ-005/SC-005): Implement internal and independent-reproduction dossier checks
  - Dependencies: T001, T004.
  - Targets: reproduction dossier/proposal module and synthetic fixtures under `research/adoption/evidence-program/`, `tests/test_adoption_evidence.py`, release-validation compatibility note.
  - Deliverable: structured reviewer identity/affiliation/externality/conflicts, exact candidate/input/protocol/environment/command/outcome/limits binding, internal versus qualifying external status and reviewed release-update proposals only.
  - Verification/evidence: SC-005 contract; maintainer-as-external, anonymous, stale hash, missing environment/command/conflict and negative outcome cases. Preserve pending status when evidence is incomplete; do not update release validation automatically or contact reviewers.
- [ ] T006 (REQ-006/SC-006): Audit historical strategy and publication tasks against current evidence
  - Dependencies: T001; independent of implementation tasks once evidence sources are pinned.
  - Targets: this feature's `legacy-status-reconciliation.json` and current decision packet; inspect frozen SPEC-002 T006, SPEC-009 T009, founder/authority/release and current repository records without editing them.
  - Deliverable: original obligation-by-obligation current state, evidence/authorization pointers, remaining decision and proposed disposition. Verify each publication/tag/prerelease/archive obligation separately; unsupported actions and founder/scientific review remain pending.
  - Verification/evidence: SC-006 contract; compare frozen source hashes before/after, bind exact observed current evidence, and reject aggregate closure inferred from public visibility or merge. This audit does not mark old tasks approved or authorize residual remote work.
- [ ] T007 (REQ-007/SC-007): Add deterministic audit/report controls for drift, rights and missingness
  - Dependencies: T002, T003, T004, T005.
  - Targets: evidence validator/report builder, synthetic negative fixtures and `tests/test_adoption_evidence.py`.
  - Deliverable: stale/contradictory/missing/withdrawn records invalidate affected metrics, reasons/denominators persist, private identities/content stay outside public output, and frozen windows cannot be silently changed.
  - Verification/evidence: SC-007 contract and `python3 -m unittest discover -s tests -p 'test_adoption_evidence.py'` after implementation. Save twice-run byte parity, fixed expected audit counts and all negative-case diagnostics with actual environment/commands.
- [ ] T008 (REQ-008/SC-008): Capture program evidence and prepare the milestone decision packet
  - Dependencies: T006, T007.
  - Targets: this feature's evidence/decision packet, `assurance.json`, `readiness.md` and current cross-cutting governance review references.
  - Deliverable: traceable observed/proxy/hypothesis and positive/negative/inconclusive findings, raw evidence links, independence/claim status, historical pending decisions and a bounded next action. Separate real-source pilot, external contact/reproduction, research claims and publication decisions.
  - Verification/evidence: SC-008 contract; run `python3 scripts/validate_spec_kit.py`, `python3 scripts/validate_change.py --base develop --profile quick`, then `--profile pr` once on the stable candidate. Freeze the clean candidate for review. Empty real yield or no external reviewer remains an honest feasibility outcome, not fabricated adoption.
