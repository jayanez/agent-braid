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
  Amended: 2026-11-02, founder decision recorded in
  `evidence/founder-decisions-20261102b.json`, answer "Solo subir (Recommended)":
  the conversation scope may only raise depth or mode relative to the value
  resolved from repository, user and profile; a lowering request is not applied
  and is recorded as `conversation-lowering-refused` with its scope. Obtained:
  `evidence/t003-conversation-raise-only.json` (74 focused tests, 959 harness
  tests; process logic only).

- [x] T004 (REQ-004 / SC-004): Deterministic raise-only risk classifier over a
  diff summary, reusing `validate_change.classify()` path sets and reporting the docs-only class. Pure; no network, clock or model call. Dependencies: T001 (Q5),
  T002. Files: `agent_braid/harness_assurance_risk.py`,
  `tests/test_harness_assurance_risk.py`. Verification: procedure_004. Negative
  controls: rule below configured depth; rule lowering mode; no-match leaves
  depth; repeated input byte-identical. Evidence: `evidence/t004.json`.
  Obtained: `evidence/t004.json` (28 focused tests, 953 harness tests; process
  logic only, no review-quality or utility claim).

- [x] T005 (REQ-005 / SC-005; REQ-006 / SC-006): Compiler to the advisory artifact with input
  hashes and digest, plus the review-ladder required-review table.
  Dependencies: T002, T003, T004. Files: `agent_braid/harness_assurance.py`,
  `tests/test_harness_assurance.py`. Verification: procedure_006 (artifact
  part). Negative controls: `executionAuthorization: true`; digest mismatch.
  Evidence: `evidence/t005.json`. Obtained: `evidence/t005.json` (90 focused tests, 1079
  harness tests; process logic only, no review-quality or utility claim).

- [x] T006 (REQ-002 / SC-002; REQ-005 / SC-005; REQ-007 / SC-007): Receipt
  builder and verifier, standing-authorization validation with fallback to
  `approve-each`, required-review check per depth. Dependencies: T001 (Q2, Q3,
  Q4), T005. Files: `agent_braid/harness_assurance_receipts.py`,
  `tests/test_harness_assurance_receipts.py`. Verification: procedure_002,
  procedure_005, procedure_007. Negative controls: missing, expired, out-of-scope,
  revoked, non-permitted issuer, non-admitting checkpoint, missing verbatim
  statement, failing condition; missing review;
  lower-depth or other-commit receipt; edit without digest recompute; command without exit code. Evidence:
  `evidence/t006.json`. Obtained: `evidence/t006.json` (43 focused tests, 1146
  harness tests; process logic only, no review-quality or utility claim).

- [x] T007 (REQ-006 / SC-006): Deterministic generators for the track-brief
  section and the PR "Pre-PR review" skeleton. Dependencies: T005, T006. Files:
  `agent_braid/harness_assurance_render.py`,
  `tests/test_harness_assurance_render.py`. Verification: procedure_006
  (generator part). Negative controls: nondeterministic output; section naming
  a review the depth does not require. Evidence: `evidence/t007.json`. Obtained:
  `evidence/t007.json` (19 focused tests, 1165 harness tests; process logic only,
  no review-quality or utility claim).

## Evaluation and closure

- [x] T008 (REQ-010 / SC-010): Non-regression: with no profile, existing
  `validate_change` and test results are unchanged. Dependencies: T002 to T007.
  Files: `evidence/t008.json`. Verification: procedure_010. Evidence: command
  outputs bound to the candidate commit. Obtained: `evidence/t008.json` (plans
  byte-identical for quick, pr and sensitive; 3762 common tests, 0 status
  changes; 3772 tests before and 4382 after, all OK; process non-regression
  only).

- [x] T009 (REQ-009 / SC-009): Register the H1 evaluation in SPEC-049: arms
  (depths), outcomes (rework, regressions, cost, cycle time) on both axes,
  stop rules, fixed before observation. Registration only; no run. Dependencies:
  T001; SPEC-049 registration procedure as existing. Files:
  `specs/067-assurance-profiles/evidence/t009.json` (and any SPEC-049 record by
  its owner). Verification: procedure_009. Negative control: post-hoc outcome
  change refused. Evidence: the registration record. Obtained:
  `evidence/t009.json` registers H1 (registered-not-run) under the frozen SPEC-049
  protocol: arms (realized depth R0 to R4), strata, two-axis outcomes (rework and
  regression; total chain cost and cycle time), labeling and stop rules; no data
  observed, no run, no utility claim. Margins, minimum clusters, acceptable
  cost and labeling (O1 to O3) were decided by the founder on 2026-11-02 in
  `evidence/founder-decisions-20261102b.json` (at least 20 clusters per arm and
  a 25 percent relative reduction; cost per accepted change up to +30 percent;
  orchestrator-proposed labels confirmed by the founder, observational only);
  `evidence/t009.json` is unchanged. SPEC-049 files unchanged.

- [x] T010 (REQ-003 / SC-003; REQ-008 / SC-008): ADR for assurance profiles and
  the standing-authorization record, drafted from plan.md "Proposed shared-file
  changes" and accepted by the founder before any profile is adopted.
  Dependencies: T001. Files: `docs/adr/<next>-assurance-profiles.md` (separate PR
  by the owner of shared files). Verification: ADR Accepted with founder
  approval. Evidence: ADR and its PR.
  Obtained: [ADR 0036](../../docs/adr/0036-assurance-profiles.md) proposed in #968 and
  Accepted 2026-11-02 by the founder in the PR that closes this task, with decision 12
  (human decision support), recorded in `evidence/founder-decisions-20261102c.json`.

- [ ] T011 (all REQ / SC): Stable-candidate validation and review: `pr`
  profile, code review of T002 to T007, assurance obtained-evidence update,
  authority snapshot, freeze, human review. Dependencies: T002 to T010. Files:
  `assurance.json`, `evidence/t011.json`. Verification: `quick`, `pr`,
  `validate_spec_kit`. Evidence: validation output bound to the candidate
  commit.
  Obtained (2026-11-08, #1168): `evidence/t011.json`; five reviews produced fixes in the receipt verifier and renderer, 9 added tests (194 passing). F6 and the id-only standing-authorization binding are recorded for their own tasks. Freeze, authority snapshot and human review pending (founder).
  Progress 2026-11-17 (#1403, 906d2efd; task stays open): authority and evidence snapshots frozen historical at develop `dad3e7f5` (authority hashes unchanged, `human_review` pending); Codex review packet `review/codex-t011-20261116.md` with output schema. Remaining: the owner runs the Codex review, then records a human review bound to `dad3e7f5` (approved or changes-requested).
  Obtained (Codex review, 2026-11-21): the owner ran the packet (codex-cli 0.169.0-alpha.11.1, read-only, pinned `dad3e7f5`); raw output `evidence/review/codex-t011-20261116.raw.json` and triage `evidence/review/codex-t011-20261116.json`: 11 findings (2 high, 4 medium, 3 low, 2 info), 9 confirmed, 1 partial, 1 rejected (C67-001: the historical binding in the later freeze commit 906d2efd is the designed model; obtained evidence and authority hashes match `dad3e7f5`). C67-002 (a re-sealed artifact satisfies a human-only floor or R0 in `verify_receipt`) and C67-003 (a classification from another profile skips an operator risk rule) are recommended to block approval at `dad3e7f5`: fix in a separate PR, re-freeze and repeat the review. No production caller is affected; owner decision pending; not human review; `executionAuthorization` false.
  Obtained (C67 fixes, 2026-11-21, #1477): owner decision "Arreglar y re-revisar (Recomendado)". C67-002: `verify_receipt` now takes the compilation inputs (profile, scope documents, classification), refuses any artifact that is not exactly their fresh compilation (`verify_artifact`, `invalid-artifact`) and holds the `HUMAN_ONLY` checkpoints at `human-only` with a human approval independently of the artifact; negative controls: re-sealed artifact with an autonomous `release` and with an R0 `pre-pr-review`. C67-003: `compile_artifact` (so `verify_artifact`) re-derives the size, shared-file and operator-rule reasons from the classification's paths and line count under the profile (`check_profile_binding`) and refuses a stale classification (`invalid-diff-summary`). C67-004: the size and shared-file defaults need their canonical R3 reason; omission tests rebuilt on non-sensitive paths with R2 variants. C67-007: a lone surrogate in `ownerStatement` is `invalid-record`. C67-008: the nested-recursion case sits under the existing `profile` key. C67-009: `evidence/t009.json` wording (before any observation; its pointer hash in `evidence/t011.json` updated). C67-001: the packet `review/codex-t011-20261116.md` stays as run (historical); the next packet must say that the candidate's own `assurance.json` is `current`/`null` and the historical binding lives in the later freeze commit. C67-005 and C67-006 are T012 and T013. Remaining: re-freeze (obtained-evidence hashes and `evidence/t011.json` refresh), repeat the Codex review, human review.
  Obtained (re-freeze, 2026-11-21): authority and evidence snapshots frozen `historical` at develop `5bd9b5c7` (the #1477 merge) with `validate_spec_kit.py freeze` on a clean detached checkout; the authority inventory gains `docs/adr/0043-harness-mcp-readonly-surface.md`; `human_review` stays pending. All 10 `obtained_evidence` entries rebound to `evidence/t011.json` at `5bd9b5c7` (sha256 `86533edd...`, was `c4754c82...`), whose `taskEvidence` pointers all match their files there; `evidence/t011.json` is not edited, so its recorded runs stay the 2026-11-08 ones (194 tests). The four T011 test modules at `5bd9b5c7`: 201 tests, OK. `assumptions` now records that Q1 to Q6 were decided on 2026-11-02. New packet `review/codex-t011-20261121.md` with output schema, pinned to `5bd9b5c7`: it states that the candidate's own `assurance.json` cannot name the candidate (the binding lives in the later freeze commit) and asks Codex to re-check C67-002 to C67-004 and C67-007 to C67-009 and to look for regressions. Remaining: the owner runs the packet, triage, human review.
  Obtained (Codex re-review, 2026-11-21): the owner ran `review/codex-t011-20261121.md` (codex-cli 0.169.0-alpha.11.1, read-only, pinned `5bd9b5c7`); raw output `evidence/review/codex-t011-20261121.raw.json` (sha256 `95d1f533...`) and triage `evidence/review/codex-t011-20261121.json`. 17 findings, all CONFIRMED: C67-002/003 (the first-review blockers) closed, plus C67-004/007/008/009 closed; new C67-012 (profile binding skips the raise-only check; lowers nothing) and C67-013 (an operator glob with a wildcard before `/**` never matches, so the raise is silently missed) medium; C67-014 to C67-019 low. C67-013 blocks approval in the triage. The four T011 test modules at develop `f8060a8b`: 201 tests, OK. Remaining: owner decision on fixing C67-012 to C67-019, then human review.

- [ ] T012 (REQ-006 / SC-006): Codex finding C67-005: restrict the track-brief
  free-text fields (ownership, isolation, model, effort) in
  `harness_assurance_render.py` to an identifier-like charset and refuse `@`,
  with synthetic sensitive-text tests, and narrow the `observation_contract`
  wording in `assurance.json` at the next re-freeze. Dependencies: T007.
  Files: `agent_braid/harness_assurance_render.py`,
  `tests/test_harness_assurance_render.py`, `assurance.json`. Verification:
  procedure_006. Negative controls: `@` mention, secret-like token, transcript
  fragment in each field. Evidence: triage `evidence/review/codex-t011-20261116.json`.

- [ ] T013 (REQ-008 / SC-008): Codex finding C67-006: refuse in `_append` or
  `save_journal` (fixed reason `journal-full`) a profile journal whose canonical
  bytes would exceed `MAX_BYTES`, keeping the previous file, so a valid journal
  never becomes unreadable. Dependencies: T003. Files:
  `agent_braid/harness_assurance.py`, `tests/test_harness_assurance.py`.
  Verification: procedure_008. Negative controls: the journal one event below
  and at the byte cap. Evidence: triage `evidence/review/codex-t011-20261116.json`.

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
| T012 | T007 |
| T013 | T003 |

Scientific limit: nothing here shows that higher depths improve outcomes; that
claim exists only if T009's registered evaluation is later run and supports it.
