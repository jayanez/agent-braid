# SPEC-067: Braid Harness assurance profiles

**Track:** HAR (parallel to the native chain; no dependency on SPEC-065)

**Status:** specification only, draft. Nothing is implemented or authorized by
this change. The founder decided Q1 to Q6 on 2026-11-02 (see Clarifications and
the [founder record](evidence/founder-decisions-20261102.json), T001); the
decisions authorize no implementation or standing authorization.

## Purpose and scope

The robustness practices of agentic development in this repository are not
recorded as checkable artifacts: three pre-PR reviews (code review, quality,
simplification), clean-clone `quick`/`pr` validation, green CI, serial
squash-merge by an orchestrator, a standing auto-merge authorization with
conditions, releases only with owner approval, and no AI attribution live in
owner memory, session briefs and the user's global instructions. Only `quick`,
`pr` and `sensitive` validation are documented in
[VALIDATION_PROFILES.md](../../docs/development/VALIDATION_PROFILES.md). This
specification turns these practices into **operator-owned, configurable
assurance profiles** across the agentic software lifecycle, with explicit
human-in-the-loop (HITL) modes. It is engineering, not a research protocol,
except for the evaluation hypothesis H1, which may fail.

A profile assigns each lifecycle **checkpoint** an HITL mode (and, for the
pre-PR review checkpoint, a review depth), compiles to an **advisory** artifact
that generates track briefs and a "Pre-PR review" block for the PR body, and
requires each gate to emit a **receipt**. The profile never executes, merges,
releases or approves anything.

"Review depth" is unrelated to the "assurance level" of
[TERMINOLOGY.md](../../TERMINOLOGY.md) and
[ASSURANCE_LEVELS.md](../../docs/architecture/ASSURANCE_LEVELS.md) (compatibility
classes under Article 13); this specification does not use or modify them.

Exclusions:

- Any executing enforcement: the compiled profile is advisory
  (`executionAuthorization: false`). Hook or guard enforcement belongs to
  [SPEC-058](../058-claude-orchestration-guard/spec.md) and is not extended here.
- Changing `scripts/validate_change.py`, CI, branch protection, merge settings,
  release tooling or the PR template. Integration points are proposals in
  [plan.md](plan.md#proposed-shared-file-changes).
- Native execution of any host, the SPEC-049 evaluation run itself, and any
  automatic promotion (SPEC-050 T009 stays disabled by default).
- Code, ADRs, tracking files, `docs/STATUS.md`, `ROADMAP.md` and
  `SPEC_MILESTONE_INDEX.md` in this specification change.

## Authorities

Constitution clause zero and Articles 0, 4, 5, 12, 13, 14, 15, 19, 20 and 24;
[GOVERNANCE.md](../../GOVERNANCE.md);
[claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
[validation profiles](../../docs/development/VALIDATION_PROFILES.md).
Precedents (followed or reused; each states below which):
[SPEC-058](../058-claude-orchestration-guard/spec.md) REQ-006 (scope precedence
conversation over repository over user, floors, refusal and recording of
lowering; draft, implemented for settings by `ownership.resolve_settings`
under [SPEC-057](../057-claude-orchestration-advisory/spec.md));
[SPEC-049](../049-harness-evaluation-learning/spec.md) (REQ-006 human promotion
and the begin/commit/rollback journal pattern of `harness_promotion`; REQ-007
disabled automatic promotion);
[SPEC-050](../050-braid-harness-adaptation/tasks.md) T002, T006, T009, T011;
`scripts/validate_change.py` (`classify()` and the `quick`/`pr`/`sensitive`
profiles, ADR 0011 risk-based validation gates); `agent_braid/harness_quota.py`
(plan-usage readings, a cost proxy).

## Vocabulary

- **Checkpoint**: a lifecycle point where a gate runs (closed catalog, REQ-001).
- **Review depth** `R0`..`R4`: how many reviews the `pre-pr-review` gate
  requires (REQ-005). Other checkpoints carry a mode only in v0.1 (Q6).
- **HITL mode** (ordered): `autonomous` < `notify` < `standing-authorization` <
  `approve-each` < `human-only` (REQ-002). "Raise" means moving up this order.
- **Floor**: a depth or mode a lower-precedence source cannot reduce (REQ-003).
- **Receipt**: the record a gate emits (REQ-007).

## Requirements and acceptance scenarios

Each requirement has one acceptance scenario; procedures are in
[validation-plan.md](validation-plan.md) and the trace is in
[assurance.json](assurance.json). Normative shapes are in
[contracts/assurance-profile.md](contracts/assurance-profile.md).

**REQ-001 Closed checkpoint catalog.** The profile schema defines a closed,
versioned catalog of checkpoints, each with an HITL mode; `pre-pr-review` also
has a review depth: `intake-spec`; `clarification` (founder decisions);
`plan-tasks`; `track-dispatch` (ownership declaration, isolation, model/effort);
`implementation` (TDD, focused tests); `pre-commit` (`quick`); `pre-pr-review`;
`pr-open`; `ci`; `merge`; `release`; `post-merge` (tracking sync, issue close,
memory, archiving); `grant`; `harness-self-change` (lesson/profile promotion);
`auto-promotion`; `native-effect`. An unknown or missing checkpoint, a depth on
any other checkpoint, or a depth or mode outside its allowed set is refused with
a fixed reason and no partial view.
- **SC-001** Given a profile covering every checkpoint, when compiled, then the
  view lists each checkpoint with mode, depth (for `pre-pr-review`) and source;
  and given an unknown or missing checkpoint, a depth on another checkpoint, an
  unknown depth, or a mode not allowed for that checkpoint, when compiled, then
  it is refused with a fixed reason.

**REQ-002 HITL modes with recorded standing authorization.** Five modes with
fixed meaning: `autonomous` (agent proceeds, receipt only); `notify` (agent
proceeds and the operator is told); `standing-authorization` (agent acts under a
recorded human authorization); `approve-each` (a fresh human approval per
action); `human-only` (the agent prepares, a human acts). A standing
authorization record carries scope (checkpoint, repository, branch pattern),
conditions, expiry, issuer, and the **verbatim owner statement**. Only `merge` admits it (conditions: green CI, receipts present, no open review threads); the maximum horizon is 30 days with expiry per authorization; only the founder may issue, with the verbatim statement stored in a hashed JSON record (Q2, Q3, Q4, decided in the [founder record](evidence/founder-decisions-20261102.json)). An authorization that is missing, expired,
revoked, out of scope, issued by a non-permitted issuer, for a checkpoint that
does not admit the mode, without a verbatim statement, or whose conditions fail
resolves to `approve-each`, never to `autonomous`.
- **SC-002** Given a valid standing authorization, when a gate in scope runs
  within its conditions, then the receipt cites it; and given an authorization
  that is missing, expired, revoked, out of scope, from a non-permitted issuer,
  for a non-admitting checkpoint, without a verbatim statement, or with a
  failing condition, then the gate resolves to `approve-each` and the receipt
  records the fallback reason.

**REQ-003 Non-lowerable authority floors and precedence.** The checkpoints
`release`, `clarification`, `grant`, `native-effect` and `auto-promotion` are
`human-only` and no scope or source may lower them. The no-attribution rule (no
AI attribution in commits, PRs, work items or other published content) is a
profile invariant applying to every publishing checkpoint (`pr-open`, `merge`,
`release`, `post-merge`) that no source can disable. Scope precedence
(conversation over repository over user, the profile as lowest source) and the
refusal-and-recording of an attempted lowering follow the precedent of SPEC-058
REQ-006 / `ownership.resolve_settings`; the fixed per-checkpoint floors and the
two-dimensional (mode, depth) resolution are this specification's own. Scope
values are read from an operator-owned assurance settings source named by the
profile; the SPEC-057 settings schema is not extended.
- **SC-003** Given a lower-scope setting that would reduce a floor or disable the
  no-attribution invariant, when resolved, then the floor holds, the lowering is
  refused and recorded with its source; and given a profile that lists a floor
  checkpoint as anything other than `human-only`, then it is refused at compile
  time.

**REQ-004 Raise-only risk escalation.** A deterministic classifier over a diff
summary (changed paths, size, shared files) maps it to a risk class using
operator-owned rules. The default rules reuse the `sensitive` path
classification of `scripts/validate_change.py` (`classify()`, ADR 0011); sensitive paths raise `pre-pr-review` to `R3`, as does a diff over 400 changed lines or one touching a shared file (`docs/STATUS.md`, `ROADMAP.md`, `docs/development/SPEC_MILESTONE_INDEX.md`, `agent_braid/cli.py`, `agent_braid/ownership.py`, `docs/development/github-tracking.json`) (Q5, decided in the [founder record](evidence/founder-decisions-20261102.json)). It also reports whether the change is documentation-only. It can only
**raise** a checkpoint's depth or mode, never lower either. Equal input yields
equal output, with no network, clock or model call.
- **SC-004** Given a diff touching a sensitive path, when classified, then the
  pre-PR depth is raised to at least the rule's depth and the reason is
  recorded; given a diff matching no rule, then the configured depth is
  unchanged; given any rule whose result is below the configured depth or mode,
  then the configured value stands; given a documentation-only diff, then that
  class is reported; and the same diff yields byte-identical output twice.

**REQ-005 Pre-PR review ladder.** `R0` none; `R1` code review; `R2` R1 plus
quality review and simplification review; `R3` R2 plus adversarial/security
review; `R4` R3 plus an independent multi-agent review (at least two reviewer
agents distinct from the author and from each other, one receipt each). For
documentation-only changes the `R1` and `R2` reviews are accuracy, claim
discipline and concision; `R3` and `R4` are as for code. A gate is satisfied only
by receipts for every required review at its own depth or higher, bound to the
head commit.
- **SC-005** Given depth `R2`, when the gate evaluates receipts, then it passes
  only with receipts for code review, quality and simplification; and given a
  missing review, a receipt of lower depth than required, or a receipt bound to
  another head commit, then it fails with a fixed reason naming the unsatisfied
  review.

**REQ-006 Compiled advisory profile and generated artifacts.** The compiler
produces an immutable profile artifact with `executionAuthorization: false`,
its input hashes and a digest. From it, deterministic generators produce (a) a
track-brief section stating ownership, isolation, model/effort, required
reviews, depth and modes, and (b) a "Pre-PR review" block for the PR body
(listing required reviews with applied and rejected findings placeholders,
destined for the existing Evidence section; the PR template itself is
unchanged). The artifact grants nothing: no tool, merge, release or approval.
- **SC-006** Given the same profile and diff, when compiled and generated twice,
  then artifacts are byte-identical and `executionAuthorization` is false; and
  given an input that sets it true, or an artifact whose digest does not match
  its inputs, then compile or verification refuses.

**REQ-007 Checkable gate receipts.** Each gate emits a receipt: checkpoint,
depth and mode actually applied, source of each, base and head commit, reviews
run with findings applied and rejected (with reasons), commands with exit codes,
approvals or standing-authorization reference, risk class and the profile
digest. A receipt is canonical JSON with a content digest. The verifier checks
structure, digest, commit binding, profile binding and consistency with the
effective depth and mode. The digest detects inconsistent edits only: an author
who recomputes it is not detected, so receipts are stored in an operator-owned
location written by the orchestrator, not by the reviewed agent. A receipt is a
record of what was reported, not proof that a review was sound or happened as
described (claim discipline).
- **SC-007** Given a receipt for a commit, when verified, then it passes; and
  given an edit that does not recompute the digest, a wrong commit, a profile
  digest mismatch, a depth below the effective depth, or a command without an
  exit code, then verification refuses with a fixed reason.

**REQ-008 Operator-owned configuration; no self-modification.** Profiles,
standing authorizations, classifier rules and floors are read only from
operator-controlled locations, never from a model, tool call or file a guarded
agent can write. A model or agent cannot raise, lower or clear its own depth or
mode; an attempt is refused and recorded. Changing a profile is a human act
recorded in an assurance-profile journal that follows the begin/commit/rollback
pattern of SPEC-049 `harness_promotion` (versioned, reversible); that module
itself is not used or changed, because its decisions require an evaluation
candidate that an assurance profile does not have.
- **SC-008** Given a change request originating from an agent-writable path or an
  agent identity, when resolved, then it is refused and recorded and the
  effective profile is unchanged; and given a human change, then a new version
  is journaled and the previous remains restorable.

**REQ-009 Measurable evaluation without a utility claim.** Whether higher depths
reduce rework or regressions at acceptable cost is registered as a SPEC-049
hypothesis (H1, below) with outcome definitions fixed before observation, on both
axes (correctness and optimization), including full chain cost. No claim of
utility is made by this specification or by compiling a profile.
- **SC-009** Given the registration record, when inspected, then outcome
  definitions, comparison arms and stop rules are fixed before any data is
  observed, and a null or negative result is a valid outcome; and given a claim
  of benefit without that record, then it is refused by review.

**REQ-010 Compatibility and non-regression.** Existing `quick`, `pr` and
`sensitive` profiles, SPEC-057/058 settings, `harness_promotion`, SPEC-050
policies and the PR template keep their behavior. Introducing a profile changes
no default until the operator adopts it. With no profile the baseline is the
validation profiles documented today; the undocumented practices above remain
prose until Q1 defines default profiles.
- **SC-010** Given no assurance profile, when `validate_change` and the
  existing tests run, then results equal the pre-change results.

## Clarifications

Decided by the founder on 2026-11-02 and recorded verbatim (as the option label
chosen) in the [founder record](evidence/founder-decisions-20261102.json)
(T001). The decisions authorize no implementation, standing authorization,
merge or release; the REQ-003 floors stay human-only.

- **Q1 Default depth and mode per checkpoint, and the no-profile baseline.**
  Decided ("R2 código / R1 docs"): `pre-pr-review` is `R2` for code and `R1`
  for docs-only; `pre-commit` = `quick`; `ci` and `merge` require green. Ship
  profiles `lite`, `standard` and `strict` with `standard` as the default. The
  currently undocumented practice becomes the documented baseline.
- **Q2 Which checkpoints admit `standing-authorization`.** Decided ("Solo
  merge, 30 días"): `merge` only, with conditions green CI, receipts present and
  no open review threads. Never the REQ-003 floors: release, founder decisions,
  grants, native execution and auto-promotion are always human-only.
- **Q3 Expiry.** Decided (same answer): maximum horizon 30 days; expiry is per
  authorization.
- **Q4 Who may issue.** Decided ("Propuesta conservadora"): the founder only; the
  verbatim statement is stored in a hashed JSON record.
- **Q5 Risk classifier rules.** Decided (same answer): `validate_change`
  sensitive paths raise `pre-pr-review` to `R3`; a diff over 400 changed lines
  or touching a shared file (`docs/STATUS.md`, `ROADMAP.md`,
  `docs/development/SPEC_MILESTONE_INDEX.md`, `agent_braid/cli.py`,
  `agent_braid/ownership.py`, `docs/development/github-tracking.json`) raises to
  `R3`. Raise-only.
- **Q6 Depth beyond the review ladder.** Decided (same answer): in v0.1 depth
  applies only to `pre-pr-review`; other checkpoint families are deferred.

## Scientific boundaries and compatibility

- **H1 (evaluation hypothesis, may fail):** higher pre-PR depths reduce
  post-merge rework and regressions relative to lower depths at a total chain
  cost the operator accepts. Measured on both axes (correctness: rework and
  regression rate; optimization: cost and cycle time) through SPEC-049; arms,
  outcome definitions and stop rules are fixed before observation. A null,
  negative or inconclusive result is valid; no requirement needs H1 to be true.
- Receipts and a compiled profile describe recorded process, not review quality
  or code correctness (Articles 4, 13, 14). Review agents can be wrong and are
  correlated; a higher depth is more review, not a guarantee.
- Risk classification is a heuristic over paths and size; it can miss risk, and
  it can only raise, so a miss leaves the configured depth, never lowers it.
- Compatibility: additive and advisory. No existing format changes; any schema
  change becomes a new version, never an in-place edit.

## Evidence and unresolved questions

Obtained evidence: none for any scenario. Planned evidence per scenario is in
[assurance.json](assurance.json). Q1 to Q6 are decided (T001); the integration
points in the plan are proposals for the owners of shared files. Human review
pending.
