# Tasks

- [ ] T001 (REQ-001–002/SC-001–004): implement a private, deterministic
  subset reducer over independently verified divergent replay evidence.
  Implemented in `agent_braid/git_counterexamples.py`: a supervised worker
  subprocess verifies the input with the existing `git_replay.verify`, then
  enumerates dependency-closed 2–(n-1) operation subsets in ascending size
  and stable ID order, replaying each with the existing `git_replay.produce`
  and stopping at the first independently verified smaller divergent
  witness.
- [ ] T002 (REQ-001–003/SC-001–005): add verified, irreducible, tampered-input
  and aggregate-budget regressions. Implemented in
  `tests/test_git_counterexamples.py` (29 tests): real-Git end-to-end cases
  for tampered/non-divergent/missing-object/garbage/invalid-repository input
  and a real process-group timeout, plus deterministic fake-backend cases for
  SC-003 (redundant operation removed), SC-004 (irreducible case unchanged),
  dependency-closure discarding, ascending-order minimality, and budget
  exhaustion by attempt cap and by deadline (SC-005), each asserting no
  minimality claim is made. See `assurance.json` for the run record.
- [ ] T003 (REQ-003/SC-005): validate, capture evidence and obtain scoped
  founder review; leave independent validation pending.

T001 and T002 have implementation and test work in this branch. Their tracking
checklist remains open until both M2 workstream PRs are reviewed and the shared
GitHub tracking inventory can be reconciled together after corpus selection.
