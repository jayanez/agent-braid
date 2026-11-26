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

Exclusions (each is a MUST NOT, stated with its REQ ID below):

- No automatic promotion. No code path moves a label without an owner actor.
  `AUTOMATIC_PROMOTION` stays false; the SPEC-049 T008 disposition stays `deferred`
  (REQ-010).
- No execution authority. A label grants no launch, grant, admission or ordinary-use
  activation. `executionAuthorization` is false on every record and view (REQ-011).
- No change to the T013 registry format, its decisions or its journal (OD-1; REQ-012).
- No write through the plugin `launch`, the SPEC-080 skill or any MCP tool (REQ-013).
- No change to host configuration, global instructions or permissions (REQ-014).

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
comes from the mechanism chosen under OD-2, not from the record. Moves are written
only by the owner-run script (OD-3). Before acting, it prints its precondition, its
working directory and the pull request it prepares, and every interaction that asks
the owner for a move states when, where and with which exact command to run it.

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
The move record also carries the owner's acknowledgement of the verdict's graded
regression summary (SPEC-083 REQ-006), citing the verdict hash and the summary hash.
The script asks the owner to type the number of hard regressions shown, and shows the
titles of regressed private tasks only in the owner's terminal, never in the
repository. A missing acknowledgement, a stale hash or a wrong count refuses the move.

- **SC-005:** Given verdicts that are non-inferior, inconclusive, inferior, absent, or
  bound to an older `adopted` hash, when `candidate` is moved, then only the fresh
  non-inferior verdict is accepted; with that verdict, a move without an
  acknowledgement, with a stale summary hash or with a wrong hard-regression count
  refuses.

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

## Requirements: exclusions and privacy

**REQ-010 No automatic promotion.** No code path MUST move a label without an owner
actor. `AUTOMATIC_PROMOTION` MUST stay false and the SPEC-049 T008 disposition MUST
stay `deferred`.

- **SC-010:** Given the code and the T008 disposition, when a code search and the
  actor tests run, then no caller moves a label without an owner actor,
  `AUTOMATIC_PROMOTION` is false and the disposition is `deferred`.

**REQ-011 No execution authority.** A label MUST NOT grant launch, grant, admission
or ordinary-use activation. `executionAuthorization` MUST be false on every record
and view.

- **SC-011:** Given any record or view after a move, when its output is inspected,
  then `executionAuthorization` is exactly `false` and no launch, grant, admission or
  activation follows.

**REQ-012 T013 unchanged.** This specification MUST NOT change the T013 registry
format, its decisions or its journal.

- **SC-012:** Given a move and a view, when the T013 registry files and
  `agent_braid/harness_promotion.py` are compared before and after, then they are
  byte-identical.

**REQ-013 No write through launch, skill or MCP.** The plugin `launch`, the SPEC-080
skill and every MCP tool MUST NOT write a pointer record.

- **SC-013:** Given the plugin launch, the skill text and the MCP tool list, when
  they are inspected for write paths to the pointer journal, then none exists.

**REQ-014 No host change.** No pointer operation MUST NOT change host configuration,
global instructions or permissions.

- **SC-014:** Given a move under a filesystem monitor, when it is applied, then no
  host configuration, global instruction or permission file changes.

**REQ-015 Private task titles stay in the terminal.** The owner script MUST show the
titles of regressed private tasks only in the owner's terminal and MUST NOT write
them to the repository.

- **SC-015:** Given a verdict with regressed private tasks, when the owner script
  runs a move to `candidate`, then the titles appear only in the terminal and no
  repository file contains them.

## Non-functional requirements

Operational and quality constraints, each stated by an existing requirement:

- Bounded records: reason of 1 to 512 characters, at most 16 evidence references
  (REQ-004).
- Append-only and tamper-evident: hash chain, extend-only save and refusal of
  concurrent writers (REQ-004).
- Offline and deterministic: the module reads no clock, host, model or network; the
  caller supplies ticks. State is derived only by replay (REQ-004; plan, Approach).
- Read-only views write nothing (REQ-008).
- Writes touch only the pointer journal (REQ-009).

## Security and privacy

- Private task titles stay in the owner's terminal (REQ-015).
- The owner actor is self-asserted; protection comes from the owner-merged pull
  request chosen under OD-2 (REQ-003).

## Terminology

- **Label:** one of `experimental`, `candidate`, `adopted`; empty or pointing to one
  candidate hash (REQ-002).
- **Pointer journal:** the append-only, hash-chained `braid-harness-pointers/v0.1`
  record sequence (REQ-004).
- **Record kind:** a move or a `rollback` (REQ-007).
- **Reason codes** include `broken-chain`, `concurrent-update` and `revoked-evidence`
  (REQ-002, REQ-004, REQ-007).
- Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md).

## Owner decisions (open)

Open questions: see [Open questions](#open-questions). OD-1 to OD-6 were decided on
2026-11-24 in [the T001 record](evidence/t001-owner-review.md); the options below
are kept as the decision text.

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

Risks and assumptions: each entry below names the REQ or task it affects.

- Risk: The owner actor is self-asserted; without OD-2 (a) or (c) a local edit can forge it (REQ-003).
- Risk: A pointer view may read as approval. Mitigation: every view states that a label
  grants nothing and repeats `executionAuthorization: false` (REQ-008, REQ-011).
- Risk: SPEC-083 or SPEC-082 may not be approved; then `candidate` and `adopted` cannot move
  and only `experimental` is usable. That is a valid outcome (REQ-005, REQ-006).
- Risk: Two sources of truth (pointer journal and T013 active profile) can diverge; REQ-008
  reports it rather than resolving it silently (REQ-008).
- Assumption: The SPEC-049 T003 registration and T013 registry formats stay as merged
  (REQ-002, REQ-006, T004).
- Assumption: SPEC-083 defines a regression verdict record bound to candidate,
  baseline and corpus hashes, and SPEC-082 defines a corpus hash (REQ-005, T005).
- Assumption: Records prove binding, not authenticity (REQ-003).

## Exit criteria

Verification is complete when the obtained evidence listed in
[the validation plan](validation-plan.md) exists for procedures 001 to 012, which map
to SC-001 to SC-015 and to T001 to T012 in [tasks.md](tasks.md), and the T012 release
or no-release record is written. Passing checks are not approval.

## Open questions

- OD-7 Release: which alpha carries the code, if approved. Owner: the founder, who
  decided on 2026-11-24 to decide when the code is finished (T012).

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
