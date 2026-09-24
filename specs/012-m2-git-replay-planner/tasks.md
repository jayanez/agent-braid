# Tasks

- [x] T001 (REQ-001/SC-001–002): finalize the specification, assurance record,
  ADR and M2 tracking entry; verify clean Python 3.12+ Spec Kit prerequisites.
- [x] T002 (REQ-001/SC-001–002): implement strict request validation, commit
  resolution, shared-base/dependency checks, patch/path bounds and stable patch
  digests in `agent_braid/git_replay.py`.
- [x] T003 (REQ-002/SC-003–004): implement isolated bare-repository/index replay,
  exhaustive topological enumeration and tracked-tree observation; prove source
  repository state is unchanged.
- [x] T004 (REQ-003/SC-005): add versioned evidence schema, producer bundle,
  independent replay verifier and mutation/coverage rejection tests.
- [x] T005 (REQ-004/SC-006–007): add deterministic candidate waves, serial
  fallback and manual-review states; expose `plan-git` and `verify-git` while
  preserving existing CLI behavior.
- [x] T006 (REQ-005/SC-008): add plan schema, documentation, registered benchmark
  corpus, sequential/path-overlap/Git-merge baselines and measured thresholds.
- [x] T007 (REQ-001–005/SC-001–008): run paired tests and proportional quick
  validation after coherent increments; record obtained evidence and task state.
- [x] T008 (REQ-001–005/SC-001–008): run the stable PR profile, capture/freeze
  evidence, perform clean-clone reproduction, run tracking source validation,
  and record the bounded human review. The cut approval does not close M2.

## M2 remains open — post-cut follow-up backlog

These tasks are beyond the approved first cut and remain uncompleted. They
strengthen the recorded residual risks and build toward safer parallel
integration. They do not authorize execution or close M2.

- [x] T009 (M2-RISK-01): remove process-global environment mutation from Git
  provenance and add a concurrent-caller regression.
- [x] T010 (M2-RISK-02): enforce end-to-end time, captured-output and temporary-
  data budgets,
  including M1 provenance, and report infrastructure failures distinctly from
  patch rejection.
- [x] T011 (M2-RISK-03): add deterministic semantic validation or regeneration
  for plan artifacts and verify their consistency with replayed evidence.
- [x] T012 (M2-PARALLEL-01): review and accept ADR 0014 and the execution
  contract for safe parallel integration,
  including isolation, dependencies, stale inputs, conflicts, resource limits,
  verification and recovery. Founder acceptance is recorded in
  `t012-founder-review.json`.
- [x] T013 (M2-PARALLEL-02): implement and benchmark a bounded parallel-
  integration prototype after T012 review; retain negative cases and require
  human review before widening execution authority. **Scoped founder review
  accepted for candidate `db30bc3` and checklist R1–R6:** see
  `m2-followup-t013-benchmark.json`, `m2-followup-evidence.json` and the
  decision in `t013-review.json`. The checked-in prototype remains local and
  read-only; promotion and execution authority remain false.

The T009–T013 implementation and obtained evidence are recorded in
`m2-followup-evidence.json`. T012 acceptance is limited to the reviewed hashes
in `t012-founder-review.json`; T013 cannot promote results or expand execution
authority. M2 remains open.

**T013 resource and bounded-evaluation profile:** the pinned Linux Docker runtime
verified and exercised the production 512 MiB per-child `RLIMIT_AS` profile. The
expanded benchmark now covers two- and three-operation disjoint changes,
same-file distinct hunks, conflicts, three repetitions, serial comparison,
path-overlap waves, pairwise `git merge-tree` measurements, resource-exhaustion
controls, a deliberately mismatched tree-verification control, a failed declared
Git tracked-tree check, in-flight child termination and graceful coordinator
stop/fresh replay. Its synthetic
measurements and limits are recorded in `m2-followup-t013-benchmark.json` and
`m2-followup-evidence.json`. This closes the macOS resource-validation blocker and
the bounded automated evaluation. Scoped founder human review is recorded in
`t013-review.json`; separate independent validation remains pending. Concurrent
tree merging, project validation commands, recovery after uncatchable crashes and
live-agent interleavings remain outside this accepted read-only T013 profile;
M2 remains open.
