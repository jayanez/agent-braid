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
  (REQ-012). The thresholds below are proposed; they bind only after the owner signs them off,
  and they are frozen with the protocol (REQ-008) before the shadow window opens.

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
  session by an `aim` call (recovered); S3 sessions that call `analyze` and never `analyze-work`
  (detours); S4 `analyze-work` `error` outcomes. Proposed pass (owner sign-off pending): S1 Wilson
  lower bound >= 0.70; at least 80 % of S2 refusals recovered; S3 <= 5 % of sessions with any Agent
  Braid analysis call; S4 = 0. Fewer than 30 calls is inconclusive and blocks the release; it is
  not a pass. A failed or inconclusive check is recorded (REQ-010), not retried on the same window.
  - SC-015: Given a shadow window that meets the minimum, when the script runs, then it reports
    S1 to S4 with the preregistered verdict and reads no content beyond the listed fields.
  - SC-016: Given fewer than 30 `analyze-work` calls, when the script runs, then the verdict is
    `inconclusive` and the release stays blocked (negative control).

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
decided; OD-E's thresholds await owner sign-off. No open questions remain at draft stage; the class plan and prompt
authoring are planning work (plan.md), not owner decisions.
Feasibility failure, null and inconclusive outcomes are valid reports.
