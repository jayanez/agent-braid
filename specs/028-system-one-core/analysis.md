# Cross-artifact planning assessment

Scope: SPEC-028–033 drafts, 2026-10-05. This is a read-only interpretation of the
planned artifacts, not independent scientific review or implementation acceptance.
The machine-readable [planning inspection](planning-inspection.json) records stable
ID coverage, dependency graph and resolved local links. Requirements reference
prospective procedures rather than pretending nonexistent tests have run.

| Finding | Severity / boundary | Location and authority | Disposition |
|---|---|---|---|
| ANA-001 | High; blocks fitting, not planning | SPEC-029 evaluation-protocol.md / source rights and yield; SPEC-019 spec.md; Constitution 9/19/25 | Source permission and eligible real data are not established. T001–T008 precede training; report infeasibility instead of inventing a corpus. |
| ANA-002 | High; blocks paid/real training and device claims | SPEC-029 evaluation-protocol.md / budget matrix; SPEC-030 tasks T001/T006; GOVERNANCE.md | Available hardware, base-model/corpus licenses and compute/provider caps need actual review. No reference weights or benchmarks were executed here. |
| ANA-003 | High; blocks accepted architecture/promotion | Every assurance.json / human_review; each adr-proposal.md; SPEC-033 T008 | All six records remain draft/pending. Feature-local proposals are not canonical ADRs. Contract review and later exact-capability acceptance remain explicit. |
| ANA-004 | High; blocks a misleading correctness target | SPEC-019 spec.md; reference-analysis.md / Existing constraints; SPEC-029 evaluation-protocol.md | Current valid finite-domain verifier outcomes do not establish a learnable diverse correctness label. Human utility proxy, deterministic semantic status and observed outcomes stay separate. |
| ANA-005 | Medium; limits comparative claims | reference-analysis.md / both performance sections; reference-sources.json | Public numbers use different benchmarks, adaptations and hardware; Laya's fine-tuned row lacks a committed result file and Strands docs lag version updates. No quantitative winner inferred. |
| ANA-006 | Medium; pre-implementation traceability obligation | Every validation-plan.md and assurance.json / test_file; SPEC_KIT.md / assurance requirements | Planned procedure references are permitted for drafts. Replace with actual named executable checks/reports and captured evidence before setting validated or checking implementation tasks. |
| ANA-007 | Administrative; publication authorization recorded | issues/index.json / publicationStatus; speckit-taskstoissues policy; GITHUB_TRACKING.md | Prepared five milestones and 55 marked issue drafts. User authorized publication on 2026-10-06, scoped to jayanez/agent-braid System 1; whole-repository historical sync is outside this scope. |
| ANA-008 | Informational; not a blocker | SPEC-029/T009 → SPEC-030/T006, SPEC-030/T008 → SPEC-029/T009 | Dependencies form a DAG. Evaluation waits for trained candidates; final architecture selection waits for evaluation. No task waits on itself. |

No unresolved contradiction with a constitutional MUST was found in the proposed
planning boundaries. This assessment does not prove complete semantic consistency.
Known tradeoffs are exposed: adding inference may increase total cost; narrowing may
lose the correct label; encoder/pointer models can be confidently wrong; calibration
and language/domain support are population-specific; request-level timeouts require
killable worker boundaries for a hard resource guarantee.

Coverage: all 36 REQ and 36 SC IDs are present in tasks; 49 pending tasks have target
files, prerequisites, prospective verification commands and evidence obligations.
Five new milestone mappings and six review-pending parent mappings preserve historical
checkbox/issue states. No task, experiment, review or milestone is marked complete.

Planning convergence: specification artifacts and traceability are assembled.
Implementation convergence: pending for all 36 scenarios. Research conclusions:
unobserved for the native proposed models. Source analysis: bounded inspection only.
Validation output is recorded separately; structural checks are not human approval.
