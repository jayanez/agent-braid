# ADR 0036: Assurance profiles and the standing-authorization record

- **Status:** Proposed. Founder acceptance is a separate act; until then no profile is adopted and no standing authorization may be issued.
- **Date:** 2026-11-02
- **Deciders:** Juan Antonio Yáñez García (founder), pending
- **Constitutional articles:** 0, 4, 5, 12–15, 19, 20, 24
- **Specification:** [SPEC-067](../../specs/067-assurance-profiles/spec.md) (track HAR), task T010

## Context

Pre-PR reviews, clean-clone validation, green CI, serial squash-merge, a conditional
auto-merge authorization, owner-only releases and the no-attribution rule are practised
but live in owner memory and session briefs. Only `quick`, `pr` and `sensitive`
([ADR 0011](0011-risk-based-validation-gates.md)) are documented. SPEC-067 makes these
practices operator-owned, configurable and checkable. The founder decided Q1 to Q6 and
S1, P1, O1 to O3 on 2026-11-02 ([record](../../specs/067-assurance-profiles/evidence/founder-decisions-20261102.json),
[additive record](../../specs/067-assurance-profiles/evidence/founder-decisions-20261102b.json)).
"Review depth" here is unrelated to the compatibility "assurance level" of
[ASSURANCE_LEVELS.md](../architecture/ASSURANCE_LEVELS.md).

## Decision

1. **Checkpoints.** A closed catalog of 16: `intake-spec`, `clarification`, `plan-tasks`,
   `track-dispatch`, `implementation`, `pre-commit`, `pre-pr-review`, `pr-open`, `ci`,
   `merge`, `release`, `post-merge`, `grant`, `harness-self-change`, `auto-promotion`,
   `native-effect`. Each carries an HITL mode; unknown or missing checkpoints are refused.
2. **Review depth ladder (v0.1: `pre-pr-review` only).** `R0` none; `R1` code review;
   `R2` R1 plus quality and simplification review; `R3` R2 plus adversarial/security
   review; `R4` R3 plus an independent multi-agent review (at least two reviewers distinct
   from the author and each other). For documentation-only changes `R1`/`R2` are accuracy,
   claim discipline and concision. A gate passes only with receipts at the required depth,
   bound to the head commit.
3. **HITL modes**, ordered: `autonomous` < `notify` < `standing-authorization` <
   `approve-each` < `human-only`. Presets `lite`, `standard` (default) and `strict`
   (P1) default `pre-pr-review` to `R1`/`R2`/`R3`; Q1 sets `R2` for code and `R1` for
   docs-only under `standard`.
4. **Standing authorization only at `merge`.** Conditions: green CI, receipts present, no
   open review threads. Maximum horizon 30 days, expiry per authorization; only the
   founder issues one, storing the verbatim statement in a hashed JSON record. Anything
   missing, expired, revoked, out of scope, from another issuer, without a statement or
   failing a condition resolves to `approve-each`, never to `autonomous`.
5. **Non-lowerable floors.** `release`, `clarification` (founder decisions), `grant`,
   `native-effect` and `auto-promotion` are `human-only`; no scope or source lowers them,
   and a profile listing one otherwise is refused at compile time. `harness-self-change`
   also admits only `human-only`, so an agent cannot change its own profile or lessons.
   The no-attribution rule is an invariant on `pr-open`, `merge`, `release` and
   `post-merge` that no source can disable.
6. **Raise-only resolution.** Scope precedence is conversation over repository over user,
   with the profile as lowest source, and applies to raising only. The conversation scope
   may only raise depth or mode (S1); lowering requires an operator profile file, and a
   conversation request to lower is refused and recorded. The deterministic risk
   classifier (no network, clock or model) reuses `validate_change.classify()` sensitive
   paths and raises `pre-pr-review` to `R3` for those, for diffs over 400 changed lines
   and for shared files (Q5); it never lowers.
7. **Advisory output.** The compiler emits an immutable artifact with input hashes, a
   digest and `executionAuthorization: false`, plus a track-brief section and a "Pre-PR
   review" block for the PR body. It grants no tool, merge, release or approval.
8. **Receipts.** Each gate emits a canonical-JSON receipt (checkpoint, applied depth and
   mode with sources, base and head commit, reviews with applied and rejected findings,
   commands with exit codes, approval or authorization reference, risk class, profile
   digest). The verifier checks structure, digest, commit and profile binding and
   consistency with the effective depth and mode.
9. **Operator ownership.** Profiles, authorizations, classifier rules and floors are read
   only from operator-controlled locations. A model cannot raise, lower or clear its own
   depth or mode. Profile changes are a human act in a versioned, reversible journal
   following the SPEC-049 `harness_promotion` begin/commit/rollback pattern; that module
   is not used or changed.
10. **H1 is registered, not claimed.** The hypothesis that higher depths reduce rework and
    regressions at acceptable cost is registered in SPEC-049 terms with outcomes fixed
    before observation: at least 20 clusters per depth arm, a 25 percent relative
    reduction for `R2`+ versus `R1`, cost per accepted change up to +30 percent (O1, O2),
    labels proposed by the orchestrator and confirmed by the founder, depth observational
    only (O3). A null or negative result is valid. This ADR makes no utility claim.
11. **Relationships.** SPEC-058 REQ-006 (scope precedence, floors, refusal and recording)
    and SPEC-057 `ownership.resolve_settings` are followed as precedents; this ADR adds
    fixed per-checkpoint floors and two-dimensional (mode, depth) resolution, and the
    SPEC-057 settings schema is not extended. Hook or guard enforcement stays in SPEC-058.
    [ADR 0035](0035-native-claude-laboratory-containment.md) and its human-issued
    qualification record are a precedent for founder-only issuance.

## Alternatives considered

- **Prose only (status quo).** Not checkable; practices drift between sessions.
- **Executing enforcement now.** Rejected by Article 20 and SPEC-058 scope; the artifact
  stays advisory.
- **Standing authorization at more checkpoints.** Rejected (Q2): release, grants, native
  effects and promotion stay human-only.
- **Agent- or conversation-lowerable depth.** Rejected (S1, REQ-008): an agent would
  control its own review.

## Consequences

- Positive: practices become reviewable, versioned and reproducible; a missing receipt is
  visible; the merge authorization has an expiry and a verbatim source.
- Negative: more files to maintain; receipts add ceremony; presets need founder records to
  change.
- Uncertain (H1): higher depth may not pay off; a null result leaves presets as policy
  preferences, not demonstrated improvements.

## Residual risks

- Receipts and compiled profiles record what was reported, not that a review was sound or
  happened as described; review agents can be wrong and correlated (Articles 4, 13, 14).
- The digest detects inconsistent edits only; an author who recomputes it is not detected,
  so receipts need an operator-owned store written by the orchestrator.
- Conversation input is unauthenticated: an actor can assert any conversation scope, which
  can only raise but still costs review time.
- The journal source and actor are caller-declared; a forged or re-registered journal is
  detected only when inconsistent.
- The classifier is a path and size heuristic and can miss risk; a miss leaves the
  configured depth rather than lowering it.
- Issuer identity for standing authorizations is a record, not an authenticated identity.

## Validation

Per the SPEC-067 [validation plan](../../specs/067-assurance-profiles/validation-plan.md)
and [assurance.json](../../specs/067-assurance-profiles/assurance.json). Every refusal
reason has a negative test; goldens prove determinism. Revisit if H1 is later run and
rejects higher depths, or if a floor proves unworkable.

## References

- [Constitution](../../CONSTITUTION.md); [claim discipline](../theory/CLAIM_DISCIPLINE.md)
- [SPEC-067 spec](../../specs/067-assurance-profiles/spec.md) and [plan](../../specs/067-assurance-profiles/plan.md)
- [ADR 0011](0011-risk-based-validation-gates.md), [ADR 0035](0035-native-claude-laboratory-containment.md)
- [SPEC-057](../../specs/057-claude-orchestration-advisory/spec.md), [SPEC-058](../../specs/058-claude-orchestration-guard/spec.md), [SPEC-049](../../specs/049-harness-evaluation-learning/spec.md)
