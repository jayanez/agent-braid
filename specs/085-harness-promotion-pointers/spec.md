# SPEC-085: Harness promotion pointers

**Milestone:** HAR.4 — Harness evaluation platform. Implements owner decision F5 of
the [harnessing benchmark](../../docs/strategy/HARNESSING_BENCHMARK.md) (2026-11-22).

**Status:** draft. Documentation only; nothing is implemented, moved or published by
this specification's first PR. The harness stays experimental under SPEC-050 D7.

## Purpose and scope

The SPEC-049 T013 profile registry (`agent_braid/harness_promotion.py`) binds human
promotion decisions to exact candidate hashes, but there is no pointer model.
Promoting and rolling back are not single, auditable operations, and no record says
which candidate is the current reference for the next regression gate. This
specification adds three protected labels, `experimental`, `candidate` and
`adopted`. Each points to one immutable harness candidate hash. Only the owner moves
a label. Every move is an append-only record with a reason and evidence references.

Langfuse protected labels, LangSmith environment tags and Braintrust environments
use the same pointer idea (cited in the benchmark). This specification keeps Agent
Braid's evidence rules on top: a SPEC-083 regression verdict and, for `adopted`, a
human per-axis promotion record.

This is engineering, not a research protocol. It makes no claim that any candidate
is useful. That pointers make promotion and rollback easier to audit is a design
expectation, not a measured result. Under clause zero, a review that finds no value
over the T013 registry, or gates that never open, is a valid outcome.

In scope:

- the closed label set, the move and rollback record format, and the replay rules;
- evidence gates for each label;
- a read-only view in `harness registry-status` and in the SPEC-080 `harness` skill.

Exclusions (each is a MUST NOT):

- No automatic promotion. No code path moves a label without an owner actor.
  `AUTOMATIC_PROMOTION` stays false; the SPEC-049 T008 disposition stays `deferred`.
- No execution authority. A label grants no launch, grant, admission or ordinary-use
  activation. `executionAuthorization` is false on every record and view.
- No change to the T013 registry format, its decisions or its journal (OD-1).
- No write through the plugin `launch`, the SPEC-080 skill or any MCP tool.
- No change to host configuration, global instructions or permissions.

## Requirements and acceptance scenarios

**REQ-001 Owner review.** The owner reviews this spec and plan before any code.

- **SC-001:** Given this spec, plan and tasks, when the owner reviews them, then OD-1
  to OD-7 are decided or deferred in a dated record and the spec is accepted, amended
  or rejected.

**REQ-002 Closed labels over immutable hashes.** The label set is exactly
`experimental`, `candidate`, `adopted`. A label is empty or points to a 64-hex
candidate hash that has a verified SPEC-049 T003 registration. A pointer never
changes the candidate it names; it only names another hash.

- **SC-002:** Given a pointer journal, when a move names an unknown label, a malformed
  hash or a hash without a registration, then it is refused with a fixed reason code
  and the journal is unchanged.

**REQ-003 Owner-only moves.** A move record names a human owner actor. An agent,
automatic-policy or missing actor is refused. The actor is self-asserted; protection
comes from the mechanism chosen under OD-2, not from the record.

- **SC-003:** Given move requests whose actor is the owner, an agent, the automatic
  policy or absent, when each is applied, then only the owner request is accepted, and
  a code search finds no caller that moves a label from an evaluation result.

**REQ-004 Append-only, hash-chained history.** Each record carries a sequence number,
the hash of the previous record, label, from-hash, to-hash, actor, a reason (1 to 512
characters), evidence references (path and SHA-256, at most 16) and a caller-supplied
tick. State is derived only by replaying the journal. A write whose journal does not
extend the stored one is refused.

- **SC-004:** Given a valid journal, when an earlier record is edited, deleted or
  reordered, or two writers race, then load refuses with `broken-chain` or the second
  write refuses with `concurrent-update`, and no state is served.

**REQ-005 Evidence gate for `candidate`.** Moving `candidate` requires a SPEC-083
regression verdict of non-inferiority for the target hash. The verdict must be bound
to the current `adopted` hash (or the OD-5 baseline when `adopted` is empty) and to
the SPEC-082 corpus hash. An inconclusive, inferior, missing or stale verdict blocks.

- **SC-005:** Given verdicts that are non-inferior, inconclusive, inferior, absent, or
  bound to an older `adopted` hash, when `candidate` is moved, then only the fresh
  non-inferior verdict is accepted.

**REQ-006 Evidence gate for `adopted`.** Moving `adopted` requires, in addition to
REQ-005, that `candidate` currently points to the target hash and that a T013 human
decision `approved` exists for that hash on every axis in its scope.

- **SC-006:** Given a target with all axes approved, one axis pending, one rejected,
  or a target not currently at `candidate`, when `adopted` is moved, then only the
  first case is accepted.

**REQ-007 Rollback is a repoint.** Rollback moves a label to a hash it pointed to
before, with its own record and reason. History is never deleted. A target whose cited
evidence was revoked in the T013 registry is refused (rule set by OD-4).

- **SC-007:** Given a label with two prior targets, one with revoked evidence, when
  rollback is requested to each, then the valid one is recorded as `rollback` and the
  revoked one is refused with `revoked-evidence`.

**REQ-008 Read-only surface.** `harness registry-status` and the SPEC-080 skill
report each label's hash, its last record and the history length. They report a
divergence when `adopted` differs from the T013 active profile's candidate. Neither
can write a record.

- **SC-008:** Given a journal and a registry, when the CLI view runs under a write
  monitor, then it writes nothing, its output lists the three labels and any
  divergence, and no skill instruction invokes a write.

**REQ-009 A label grants nothing.** Moving any label writes only the pointer journal.
It begins no T013 transaction, activates nothing and changes no host file.

- **SC-009:** Given a move to `adopted`, when it is applied under a filesystem
  monitor, then only the pointer journal changes and every output has
  `executionAuthorization` exactly `false`.

## Owner decisions (open)

- **OD-1 Storage.** (a) A separate pointer journal, `braid-harness-pointers/v0.1`,
  that cites T013 decision hashes; (b) new events in the T013 journal (format v0.2).
  Recommended: (a). It leaves verified T013 code and records unchanged.
- **OD-2 Protection.** (a) The journal lives in the repository and every move lands
  through an owner-merged pull request; (b) a local file with a self-asserted actor;
  (c) records signed with an owner key. Recommended: (a). It reuses existing review and
  git history; (c) adds key management.
- **OD-3 Write path.** (a) An owner-run one-command script outside the plugin
  `launch`; (b) a `harness` CLI subcommand that the skill must not call. Recommended:
  (a). The plugin launch keeps `prepare` as its only effect.
- **OD-4 Rollback evidence.** (a) Rollback needs no new verdict if the target's cited
  evidence is not revoked; (b) rollback needs a fresh verdict. Recommended: (a), so
  rollback stays fast.
- **OD-5 First baseline.** When `adopted` is empty, the verdict compares against
  (a) the SPEC-049 registered baseline arm A or (b) a named candidate. Recommended: (a).
- **OD-6 Scope.** (a) One pointer set per T013 registry scope; (b) one global set.
  Recommended: (a), matching T013 task-local scopes.
- **OD-7 Release.** Which alpha carries the code, if approved.

## Non-goals

Automatic promotion, ordinary-use activation, a write MCP tool, a hosted registry,
reopening SPEC-050 D7, and new statistics (SPEC-083 owns them).

## Risks

- The owner actor is self-asserted; without OD-2 (a) or (c) a local edit can forge it.
- A pointer view may read as approval. Mitigation: every view states that a label
  grants nothing and repeats `executionAuthorization: false`.
- SPEC-083 or SPEC-082 may not be approved; then `candidate` and `adopted` cannot move
  and only `experimental` is usable. That is a valid outcome.
- Two sources of truth (pointer journal and T013 active profile) can diverge; REQ-008
  reports it rather than resolving it silently.

## Dependencies

SPEC-049 (T003 registration, T007 decisions, T013 registry, T008 disposition);
SPEC-050 D7; SPEC-082 (corpus hash); SPEC-083 (regression verdict); SPEC-080 (skill
surface; ADR 0044); SPEC-084 and ADR 0045 (produce the evaluation evidence); SPEC-086
(may observe pointer reads). No dependency blocks drafting.

## References

- [Harnessing benchmark](../../docs/strategy/HARNESSING_BENCHMARK.md), section 3 and F5.
- [ADR 0044](../../docs/adr/0044-harness-portability-tiers-skill-surface.md),
  [ADR 0045](../../docs/adr/0045-hybrid-harness-evaluation-substrate.md).
- [SPEC-049](../049-harness-evaluation-learning/spec.md),
  [promotion policy](../049-harness-evaluation-learning/promotion-policy.md),
  [SPEC-050 owner decisions](../050-braid-harness-adaptation/owner-decisions-20261113.md).
- [CONSTITUTION.md](../../CONSTITUTION.md), [GOVERNANCE.md](../../GOVERNANCE.md).
- External, as cited in the benchmark:
  [Langfuse](https://langfuse.com/docs/prompt-management/features/prompt-version-control),
  [LangSmith](https://docs.langchain.com/langsmith/manage-prompts),
  [Braintrust](https://docs.braintrust.dev/deploy/environments).
