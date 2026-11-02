# SPEC-067: Tasks

Stable task IDs. Completion requires obtained evidence. A passing unit test is
not evidence that reviews are sound or that higher depths help; only receipts
and the registered evaluation are. Dependencies are ordering facts; they do not
authorize concurrent agents. No task is started by the specification change.

Common verification for code tasks: tests first, then
`.venv-speckit/bin/python -m unittest <module> -v`, then
`.venv-speckit/bin/python -m unittest discover -s tests -p "test_harness_assurance*.py" -v`,
then the `quick` profile; `pr` once on the stable candidate (clean clone while the
shared object store fails the portable-root check).

## Decisions

- [x] T001 (REQ-001 / SC-001; REQ-002 / SC-002; REQ-004 / SC-004): Founder
  decision record for Q1 to Q6 (default depth per checkpoint and default profiles;
  checkpoints admitting `standing-authorization`; expiry; who may issue; risk
  rules and thresholds; depth semantics beyond the review ladder), or any item
  recorded as open with the tasks it keeps blocked. Dependencies: none. Files:
  `specs/067-assurance-profiles/evidence/founder-decisions-<date>.json`; `spec.md`
  (replace each decided `[NEEDS CLARIFICATION]` with the decision and a link).
  Verification: every Q has a decision or an explicit "open" with blocked tasks;
  `validate_spec_kit` passes. Evidence: the record. Negative control: a task
  citing an undecided Q stays blocked. Obtained: Q1 to Q6 decided by the founder on
  2026-11-02 in `evidence/founder-decisions-20261102.json` (none left open;
  authorizes no implementation, standing authorization, merge or release).

## Implementation

- [x] T002 (REQ-001 / SC-001; REQ-003 / SC-003): Catalog, allowed-mode table,
  schema and fixed refusal reasons; floor set. Tests first. Dependencies: T001
  (Q1, Q6). Files: `agent_braid/harness_assurance.py`,
  `tests/test_harness_assurance.py`. Verification: procedure_001. Negative
  controls: unknown or missing checkpoint, unknown depth, disallowed mode,
  unknown key, `release` not `human-only`. Evidence: `evidence/t002.json`. Obtained: `evidence/t002.json` (35 focused tests,
  892 harness tests; PR #944; process logic only, no review-quality or utility claim).

- [x] T003 (REQ-003 / SC-003; REQ-008 / SC-008): Resolver following the SPEC-058
  REQ-006 / `ownership.resolve_settings` precedence (recorded refused lowering),
  the REQ-003 floors, the no-attribution invariant, an operator-owned loader and
  an assurance-profile journal following the `harness_promotion` pattern (that
  module is not changed). Dependencies: T002. Files: `agent_braid/harness_assurance.py`,
  `tests/test_harness_assurance.py`. Verification: procedure_003,
  procedure_008. Negative controls: lowering of each floor at each scope;
  agent-writable source; agent identity; in-place edit of a registered
  version. Evidence: `evidence/t003.json`. Obtained: `evidence/t003.json` (68 focused tests,
  925 harness tests; PR #948; process logic only, no review-quality or utility claim).

- [ ] T004 (REQ-004 / SC-004): Deterministic raise-only risk classifier over a
  diff summary, reusing `validate_change.classify()` path sets and reporting the docs-only class. Pure; no network, clock or model call. Dependencies: T001 (Q5),
  T002. Files: `agent_braid/harness_assurance_risk.py`,
  `tests/test_harness_assurance_risk.py`. Verification: procedure_004. Negative
  controls: rule below configured depth; rule lowering mode; no-match leaves
  depth; repeated input byte-identical. Evidence: `evidence/t004.json`.

- [ ] T005 (REQ-005 / SC-005; REQ-006 / SC-006): Compiler to the advisory artifact with input
  hashes and digest, plus the review-ladder required-review table.
  Dependencies: T002, T003, T004. Files: `agent_braid/harness_assurance.py`,
  `tests/test_harness_assurance.py`. Verification: procedure_006 (artifact
  part). Negative controls: `executionAuthorization: true`; digest mismatch.
  Evidence: `evidence/t005.json`.

- [ ] T006 (REQ-002 / SC-002; REQ-005 / SC-005; REQ-007 / SC-007): Receipt
  builder and verifier, standing-authorization validation with fallback to
  `approve-each`, required-review check per depth. Dependencies: T001 (Q2, Q3,
  Q4), T005. Files: `agent_braid/harness_assurance_receipts.py`,
  `tests/test_harness_assurance_receipts.py`. Verification: procedure_002,
  procedure_005, procedure_007. Negative controls: missing, expired, out-of-scope,
  revoked, non-permitted issuer, non-admitting checkpoint, missing verbatim
  statement, failing condition; missing review;
  lower-depth or other-commit receipt; edit without digest recompute; command without exit code. Evidence:
  `evidence/t006.json`.

- [ ] T007 (REQ-006 / SC-006): Deterministic generators for the track-brief
  section and the PR "Pre-PR review" skeleton. Dependencies: T005, T006. Files:
  `agent_braid/harness_assurance_render.py`,
  `tests/test_harness_assurance_render.py`. Verification: procedure_006
  (generator part). Negative controls: nondeterministic output; section naming
  a review the depth does not require. Evidence: `evidence/t007.json`.

## Evaluation and closure

- [ ] T008 (REQ-010 / SC-010): Non-regression: with no profile, existing
  `validate_change` and test results are unchanged. Dependencies: T002 to T007.
  Files: `evidence/t008.json`. Verification: procedure_010. Evidence: command
  outputs bound to the candidate commit.

- [ ] T009 (REQ-009 / SC-009): Register the H1 evaluation in SPEC-049: arms
  (depths), outcomes (rework, regressions, cost, cycle time) on both axes,
  stop rules, fixed before observation. Registration only; no run. Dependencies:
  T001; SPEC-049 registration procedure as existing. Files:
  `specs/067-assurance-profiles/evidence/t009.json` (and any SPEC-049 record by
  its owner). Verification: procedure_009. Negative control: post-hoc outcome
  change refused. Evidence: the registration record.

- [ ] T010 (REQ-003 / SC-003; REQ-008 / SC-008): ADR for assurance profiles and
  the standing-authorization record, drafted from plan.md "Proposed shared-file
  changes" and accepted by the founder before any profile is adopted.
  Dependencies: T001. Files: `docs/adr/<next>-assurance-profiles.md` (separate PR
  by the owner of shared files). Verification: ADR Accepted with founder
  approval. Evidence: ADR and its PR.

- [ ] T011 (all REQ / SC): Stable-candidate validation and review: `pr`
  profile, code review of T002 to T007, assurance obtained-evidence update,
  authority snapshot, freeze, human review. Dependencies: T002 to T010. Files:
  `assurance.json`, `evidence/t011.json`. Verification: `quick`, `pr`,
  `validate_spec_kit`. Evidence: validation output bound to the candidate
  commit.

## Unblocking map

| Task | Needs |
|---|---|
| T002, T009, T010 | T001 |
| T003 | T002 |
| T004 | T001 (Q5), T002 |
| T005 | T002, T003, T004 |
| T006 | T001 (Q2–Q4), T005 |
| T007 | T005, T006 |
| T008 | T002–T007 |
| T011 | T002–T010 |

Scientific limit: nothing here shows that higher depths improve outcomes; that
claim exists only if T009's registered evaluation is later run and supports it.
