# Feature specification: SPEC-079 — Tool-level kind-choice fix (BL.2c)

## Purpose and scope

SPEC-078 converged with a negative result. Two skill-text fixes did not stop
models from choosing `kind: units` for parallel or overlap questions. On the
v3-test split (PR #1490, run `run-20261121T192620Z-61ca8b`) the baseline A0'
scored 91/100 passing prompts and missed OD-1: V3T-002 and V3T-027 were 0/3,
19 of 300 attempts used `units`, and 46 of 300 attempts called the separate
`analyze` tool, 6 of which failed without ever calling `analyze-work`.

`units` records partial coverage by design, so it can never report
`independent-candidate`. A host that picks `units` for an "can these run in
parallel?" question gets `unknown` and answers wrongly. This specification moves
the fix from the skill text to the tool surface and measures it on a fresh
held-out split.

This is engineering plus a research protocol:

- Engineering: `analyze-work` refuses or redirects a `kind: units` request whose
  declared units are pairwise disjoint (REQ-001, REQ-002); the `analyze-work`
  description is rewritten so that its digest line no longer reads as a
  precondition the host must satisfy by hand (REQ-003); the `analyze` tool
  description says what it is for and points at `analyze-work` (REQ-004).
- Research: a fresh held-out v4 split, preregistered hypotheses and a gate
  (REQ-006 to REQ-010).

Out of scope:

- Any change to `scripts/spec069_scoring.py`, the SPEC-069 prompt sets, the
  SPEC-078 splits (`test.json`, `v3-test.json`, feedback, validation), their
  FREEZE files or any other frozen protocol file.
- Reusing, editing or paraphrasing any v2-test or v3-test prompt in v4.
- Further skill-text optimization, APO, weight-level training, promotion
  (SPEC-073), hosts other than `claude-code`, paid routes, API keys, LLM judges.
- Changing the `units` contract for non-disjoint declarations, or the AIM, git
  or report schemas.
- Claims beyond the observed host, model, tool bytes, skill bytes and prompt set.

## Authorities

Constitution clause zero and Articles 9, 12, 13, 14, 19, 20, 21 and 23;
[GOVERNANCE.md](../../GOVERNANCE.md);
[claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
[ADR 0021](../../docs/adr/0021-codex-claude-tooling-integration.md) (EUR 0
spend); [ADR 0039](../../docs/adr/0039-braid-lightning-boundary.md) (Braid
Lightning boundary). Precedents:
[SPEC-069](../069-aim-request-authoring/spec.md) (case format, scorer, `units`
REQ-006, schema delivery D9/D12),
[SPEC-071](../071-lightning-rollouts-reward/spec.md) (runner, canaries, quota stops),
[SPEC-078](../078-lightning-heldout-v2/spec.md) (OD-1 to OD-3, Gate 0, negative
result; its protocol and splits are frozen and are not edited here).

## Clarifications

Owner decisions (2026-11-22, `speckit-clarify`):

- **OD-A — Refuse and redirect.** A disjoint `units` request returns status
  `refused` with code `units-cannot-answer-independence`, a message naming
  `kind: aim` and the skill, and the constructed AIM envelope (coverage still
  partial) for the host to edit and replay. Undo: revert the one branch in
  `analyze-work`; no schema change.
- **OD-B — Gate.** SPEC-078 OD-1 reused unchanged: a prompt passes at >= 2/3
  valid first attempts; the gate is met when the Wilson 95 % lower bound of the
  passing share is >= 0.80 (>= 88/100), every class has at least half its
  prompts passing, and no prompt is 0/3 after the zero-prompt review. 100 test
  prompts x 3 repetitions = 300 rollouts, one pass.
- **OD-C — Host and model.** `claude-code`, model pinned to
  `claude-sonnet-5-5`, subscription route, EUR 0.
- **OD-D — Ship order.** v4 runs against a pinned unreleased commit of the fixed
  plugin; the change ships in an alpha only after the result is recorded.
- **OD-E — Real-session shadow check (owner reliability gate, 2026-11-22).** Approval of
  SPEC-079 also needs a read-only check over the owner's real sessions on the pinned build
  (REQ-012). The owner approved the thresholds as proposed on 2026-11-23
  ([record](https://github.com/jayanez/agent-braid/pull/1625#issuecomment-7116233134)); they are frozen with the protocol (REQ-008) before the shadow window opens.
  On 2026-11-24 the owner approved an S2 clarification without changing a threshold: 0/0
  refusals is "not applicable" and passes, and "recovered" means a valid `aim` call in the same
  session ([record](https://github.com/jayanez/agent-braid/pull/1629#issuecomment-7123466626)).
- **Owner sign-off — T006 protocol (2026-11-23).** `evaluation-protocol.md` approved as written
  ([record](https://github.com/jayanez/agent-braid/pull/1629#issuecomment-7116233460)). T008 (300 rollouts) remains a separate owner decision.

## Requirements and acceptance scenarios

- **REQ-001 — Disjoint `units` redirect.** When `analyze-work` receives
  `kind: units` and the constructed records would be pairwise disjoint (no declared
  dependency between any two units, and no resource shared by two units with a write-like
  effect on it, where write-like is the analyzer's `write`, `transform`, `delete` or `deploy`;
  sharing through `read`, `call` or `emit` only is not overlap), it does not return an `ok`
  report whose pairs are all `unknown`.
  It returns status `refused` (OD-A) with code `units-cannot-answer-independence` and a
  message naming `kind: aim` and the skill. A single-unit declaration, and non-disjoint
  or mixed declarations (any pair overlapping or dependent), keep their current behaviour byte-for-byte.
  - SC-001: Given two units writing different files with no dependency, when
    `analyze-work` is called with `kind: units`, then the response is `refused` with
    code `units-cannot-answer-independence` and no pair verdict is reported as the answer.
  - SC-002: Given two units writing the same file, when called, then the
    response equals the pre-change response (golden comparison).
  - SC-003: Given a malformed `units` request, when called, then the existing
    validation refusal is returned first (refusal order unchanged).
- **REQ-002 — Redirect content is actionable and bounded.** The redirect message
  (the cap applies to the message, not the attached envelope) states in at most
  400 characters why `units` cannot answer independence, and includes the constructed AIM envelope (coverage partial) so that a
  host can replay it as `kind: aim` only after asserting complete coverage. It
  never grants execution authority and never fabricates coverage.
  - SC-004: Given SC-001's request, when the redirect is read, then it names
    `kind: aim`, is within the size cap and `executionAuthorization` is false.
  - SC-005: Given the redirect's envelope replayed unchanged as `kind: aim`,
    when analyzed, then coverage stays partial and no `independent-candidate`
    appears.
- **REQ-003 — `analyze-work` description.** The per-kind description no longer
  says "aim needs sha256:<64 hex> digests" as a bare precondition. It states, in
  order: use `aim` for parallel or overlap questions; `units` cannot report
  independence and is refused for disjoint work; digests are any well-formed
  `sha256:` value identifying the definition and input (example given); the skill
  has a copyable example. The `description-only` delivery carries the same `units` sentence. It stays
  within the SPEC-069 D12 cap (1,500 tokens for the
  compact `analyze-work` definition).
  - SC-006: Given the tool list, when the description is read, then it matches
    the frozen text and length cap, and the old digest line is absent.
- **REQ-004 — `analyze` tool description.** The `analyze` tool's description
  states what request it takes (the plan-level request, not an analysis input),
  that it does not answer parallel or overlap questions about proposed work, and
  that `analyze-work` does.
  - SC-007: Given the tool list, when the `analyze` description is read, then it
    names `analyze-work` for parallel/overlap questions and stays within the cap.
- **REQ-005 — Compatibility record.** The change is recorded in the release record and
  `docs/tooling/NATIVE_PLUGINS.md` as a behaviour change for disjoint `units` requests, with
  the version it ships in.
  - SC-008: Given the release record, when read, then the disjoint `units`
    behaviour change and its code are listed.
- **REQ-006 — Held-out set v4.** A new versioned split of fresh prompts, written
  from a class plan, never by editing, paraphrasing or reusing v2-test or v3-test
  prompts. A build check fails if any v4 prompt's normalized text or fingerprint
  matches a SPEC-069, v2 or v3 prompt. Classes include units/aim kind-choice
  probes and prompts that tempt a call to `analyze`.
  - SC-009: Given the v4 file and all earlier sets, when the build check runs,
    then zero fingerprint or normalized-text collisions are reported.
- **REQ-007 — Gate 0 on v4.** Reference solutions, the guidance-literal follower
  and null baselines from SPEC-078 run on v4 with no rollouts; references must be
  valid and nulls must miss the gate.
  - SC-010: Given v4, when Gate 0 runs, then every reference is valid and no null
    baseline meets the gate.
- **REQ-008 — Preregistered protocol and freeze.** `evaluation-protocol.md`
  preregisters H1 to H4, the gate, split size, repetitions, host and model, the
  analysis and stopping rules, and the v4 sha256. It is frozen on a develop
  commit before any v4 rollout.
  - SC-011: Given the freeze record, when validated, then every hash matches
    develop and no v4 run predates it.
- **REQ-009 — Gate run (owner-authorized).** One arm (fixed tool at a pinned
  unreleased commit + current skill, OD-D) runs once on v4 after the freeze and the owner's yes. Results report the
  passing-prompt share with Wilson bounds, per-class pass rates, the
  `validWithinRetry` passing share (secondary, H4), `units` usage,
  `analyze`-only failures and the zero-prompt review.
  - SC-012: Given the run, when analyzed, then the report carries every
    preregistered statistic and the gate verdict.
- **REQ-010 — Negative and inconclusive outcomes.** A missed gate, a null
  difference or an invalidated run is a valid completion; it is recorded, not
  retried on v4.
  - SC-013: Given a missed gate, when converged, then the spec records the
    negative result and v4 is not reused for a second arm.
- **REQ-011 — Boundaries.** No change touches frozen protocol files, the scorer
  or earlier splits; no quota is spent before the freeze and the owner's yes.
  - SC-014: Given the diff, when the boundary check runs, then no frozen path
    changed.

- **REQ-012 — Real-session shadow check (OD-E).** Before release (T010), the pinned build
  (OD-D) runs in the owner's real `claude-code` sessions for a window of at least 14 days and at
  least 30 `analyze-work` calls. A read-only script reads only local telemetry cells and the
  host transcripts' tool names, `kind` arguments and envelope status and refusal code (no prompt
  or file content, no quota). It reports: S1 the `ok` share of `analyze-work` calls (Wilson 95 %);
  S2 the count of `units-cannot-answer-independence` refusals and how many were followed in the same
  session by a valid `aim` call, one whose envelope status is `ok` (recovered); S3 sessions that call `analyze` and never `analyze-work`
  (detours); S4 `analyze-work` `error` outcomes. Pass (OD-E, owner-approved 2026-11-23): S1 Wilson
  lower bound >= 0.70; at least 80 % of S2 refusals recovered; S3 <= 5 % of sessions with any Agent
  Braid analysis call; S4 = 0. With no redirect refusal in the window (0/0), S2 is not applicable and
  passes; S1, S3 and S4 still apply (owner clarification 2026-11-24,
  [record](https://github.com/jayanez/agent-braid/pull/1629#issuecomment-7123466626)). Fewer than 30 calls is inconclusive and blocks the release; it is
  not a pass. A failed or inconclusive check is recorded (REQ-010), not retried on the same window.
  - SC-015: Given a shadow window that meets the minimum, when the script runs, then it reports
    S1 to S4 with the preregistered verdict and reads no content beyond the listed fields.
  - SC-016: Given fewer than 30 `analyze-work` calls, when the script runs, then the verdict is
    `inconclusive` and the release stays blocked (negative control).

## Non-functional requirements

Operational and quality constraints, each with its source:

- Redirect message at most 400 characters; the attached envelope is outside the cap (REQ-002).
- Compact `analyze-work` definition within the SPEC-069 D12 cap of 1,500 tokens; the `analyze`
  description stays within the cap (REQ-003, REQ-004).
- Refusal order unchanged: the existing validation refusal comes first (REQ-001, SC-003).
- Spend of EUR 0 on the subscription route (OD-C; [ADR 0021](../../docs/adr/0021-codex-claude-tooling-integration.md)); one
  gate run of 100 prompts x 3 repetitions = 300 rollouts (OD-B, REQ-009).
- Shadow window of at least 14 days and at least 30 `analyze-work` calls, read-only (REQ-012).

## Security and privacy

This section adds no REQ. It cites existing requirements and the owner's decision to cite
rather than add REQs ([owner decisions](evidence/owner-decisions-20261126.md)):

- The refusal adds no authority: the redirect never grants execution authority and never
  fabricates coverage (REQ-002); `executionAuthorization` stays false
  (`assurance.json` `execution_contract`).
- The shadow check reads only local telemetry cells and transcript tool names, `kind`
  arguments, envelope status and refusal code, never prompt or file content (REQ-012).
- Frozen protocol files stay untouched and no quota is spent before the freeze and the
  owner's yes (REQ-011).
- Subscription route only, EUR 0, no API keys and no paid routes (OD-C;
  [ADR 0021](../../docs/adr/0021-codex-claude-tooling-integration.md); Out of scope above).
- The zero-prompt review uses redacted transcripts (plan.md, Validation strategy; T009).

## Terminology

- **Disjoint `units` request:** a `kind: units` request whose constructed records have no
  declared dependency and no resource shared with a write-like effect (REQ-001).
- **Write-like effect:** the analyzer's `write`, `transform`, `delete` or `deploy`; `read`,
  `call` and `emit` are not (REQ-001).
- **Redirect:** the `refused` response with code `units-cannot-answer-independence`, a
  message and the constructed AIM envelope (OD-A, REQ-002).
- **Kinds:** `aim` and `units` are the `analyze-work` request kinds this spec compares; `git`
  is named only as a request kind left unchanged (Purpose and scope: AIM, git and report schemas unchanged).
- **Held-out set v4:** the fresh 100-prompt split of REQ-006, in seven classes:
  disjoint-parallel, overlap-write, dependency-order, read-only shared, kind-choice probes,
  analyze-tempting, git-branch (tasks.md T004).
- **Gate 0:** the no-rollout check of REQ-007. **OD-1 gate:** the gate of OD-B.
- **Passing prompt:** at least 2 of 3 valid first attempts (OD-B).
- **`validFirstAttempt` / `validWithinRetry`:** per-trial scorer outcomes; the second allows
  one retry after a refusal (H4, REQ-009).
- **Zero-prompt review:** the owner classifies each 0/3 prompt as `model` or `instrument`
  (plan.md; T009).
- **Shadow check:** the real-session check of REQ-012 (OD-E); statistics S1 to S4 and
  verdicts pass, failed or inconclusive.
- **Hypothesis outcomes:** supported, not supported or inconclusive (tasks.md T010).
- **Pinned build:** the unreleased plugin commit the run installs (OD-D).
- Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md).

## Scientific boundaries and compatibility

Hypotheses (preregistered in REQ-008; none is a completion condition):

- **H1** — With the fixed tool, the share of attempts using `kind: units` on v4
  kind-choice prompts is lower than the 19/300 observed on v3-test (descriptive,
  not a paired comparison: different prompts).
- **H2** — With the fixed tool, the arm meets the gate on v4.
- **H3** — Attempts that call only `analyze` and never `analyze-work` are fewer
  than 6/300.
- **H4** — The share of prompts passing on `validWithinRetry` (first attempt, or
  one retry after a refusal; unchanged SPEC-069 scorer) is at least the
  first-attempt share plus the prompts rescued by the redirect. Secondary and
  descriptive: a refused `units` call is a failed first attempt, so the OD-1 gate
  credits the refusal only when the description already led to `aim`.

Limit: v4 has its own class mix (20 kind-choice probes), so H1 and H3 compare
rates against v3-test descriptively only.

Domain: `claude-code` host, model `claude-sonnet-5-5` (OD-C), the observed tool and skill
bytes, the v4 prompts. Observation contract: `score_case(...)["validFirstAttempt"]`
from the unchanged SPEC-069 scorer, plus transcript counts of tool kinds.
Execution contract: SPEC-071 runner on the subscription route, EUR 0.
Compatibility: disjoint `units` requests change from `ok`/`unknown` to `refused`
(`units-cannot-answer-independence`); all other inputs unchanged. This includes disjoint `units`
declarations whose coverage is partial: they are refused too (OD-A), and v4 holds no partial `units`
case, so the cost of the extra `aim` call for them is not measured. v4 results are not comparable
pairwise to v3-test.

## Evidence and unresolved questions

Planned and obtained evidence are kept in `assurance.json`. Tracking:
milestone [BL.2c #36](https://github.com/jayanez/agent-braid/milestone/36),
epic #1503, tasks T001–T010 as #1504–#1513. OD-A to OD-D are
decided; OD-E's thresholds and the T006 protocol were approved on 2026-11-23. No open questions remain at draft stage; the class plan and prompt
authoring are planning work (plan.md), not owner decisions. The owner's yes for T008
(300 rollouts), the zero-prompt classification (T009) and the release (T010) are pending
gates, not open questions (plan.md, Human review and unresolved decisions).
Feasibility failure, null and inconclusive outcomes are valid reports.

## Risks and assumptions

Each entry names the REQ or task it affects. Sources: [research.md](research.md) and
`assurance.json` (`assumptions`, `scientific_limits`).

- Risk: The mechanism (models ignoring `unknown`) is inferred from transcripts, not tested
  (REQ-001, research.md R1).
- Risk: A host that does not recover in-turn fails its first attempt; this is measured, not
  assumed (REQ-009, H4, research.md R2).
- Risk: Disjoint `units` declarations with partial coverage are refused too, and v4 has no such
  case, so the cost of the extra `aim` call is not measured (REQ-001, research.md R2).
- Risk: The T001 change to `tests/test_spec069_units.py` and `scripts/spec069_generate_corpus.py`
  leaves the sha256 values in SPEC-069 `evidence/procedure_004`, `005`, `006` and `014` stale;
  those closed records are not edited (T001, research.md R2).
- Risk: Attributing the `analyze`-only failures to the digest line is a hypothesis (REQ-003, H3,
  research.md R3).
- Risk: One host, model and synthetic split, correlated repetitions and template clustering;
  comparisons with v3-test are descriptive only (REQ-009, `assurance.json` `scientific_limits`).
- Risk: v4 independence rests on mechanical leakage checks, since the author may have seen some
  earlier wording (REQ-006, T004, research.md R7).
- Assumption: The SPEC-069 scorer and fixture workspace are reused unchanged, and the SPEC-078
  fact generator, Gate 0 and analysis are reused by import (REQ-006, REQ-007, REQ-009;
  `assurance.json` `assumptions`).
- Assumption: Hosts other than `claude-code` and models other than `claude-sonnet-5-5` are out
  of scope (OD-C, Out of scope).

## Exit criteria

Verification is complete when the obtained evidence for SC-001 to SC-016 listed in the
[validation plan](validation-plan.md) exists and the T010 converge record is written. Present
today: `evidence/gate0-v4-report.json` (REQ-007) and `prompts/FREEZE-v4.json` (REQ-008).
Planned and absent: `evidence/gate-v4-report.json` (T008, REQ-009), the owner's zero-prompt
review record under `reviews/` (T009), the shadow report and the release record (T010, REQ-005,
REQ-012). A missed gate is a valid completion when recorded (REQ-010). An inconclusive shadow
check (fewer than 30 calls) is recorded but blocks the release record (REQ-012, T010, SC-016),
so the release record stays absent in that case. Passing checks are not approval.

## Open questions

No unresolved questions; see [Evidence and unresolved questions](#evidence-and-unresolved-questions).
