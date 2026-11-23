# SPEC-073: Lightning promotion

**Milestone:** BL.3 — Lightning promotion (GitHub milestone created by the
reviewed tracking reconciliation after merge).

**Status:** draft. `human_review` is pending; this specification grants no
execution authority and adopts no automatic promotion.

## Purpose and scope

A Braid Lightning candidate that wins a BL.2 optimization run (SPEC-072) is a
whole prompt or skill text. It is too large for an experience entry (512
characters, `harness_experience.MAX_LESSON`), so it is promoted through the HAR
profile registry of SPEC-049 (`agent_braid/harness_promotion.py`) as a native
profile identified by `candidateSha256`. A human decides, begins and commits the
promotion; the plugin build then ships exactly that text; rollback restores the
previous text. This is engineering, not a research protocol.

In scope:

- `agent_braid/lightning_promote.py`: build a `ProfileRegistry.record` input
  (cohort `native`, `candidateSha256`) from a BL.2 winner and its evaluation;
- a closed mapping from a registry scope to one skill file path in the plugin
  source tree;
- `agent-braid lightning promote --candidate <sha>` producing a preview, and
  `--apply --preview-digest <digest>` writing only the registry and the mapped
  file after a human decision;
- a plugin-build check (`agent_braid/plugin_package.py`) that the shipped
  `SKILL.md` digest equals the registry's active candidate for its scope;
- rollback to the previous digest and revocation of evidence, both reflected
  in the next build;
- optional short GEPA reflections (at most 512 characters each) proposed to
  `ExperienceStore.add`, which stay quarantined until a human activates them.

Exclusions:

- Any automatic decision, begin or commit: `AUTOMATIC_PROMOTION` stays `False`.
- Running optimization or evaluation (SPEC-071, SPEC-072); content traces
  (SPEC-074); dataset export (SPEC-075); weight training (SPEC-076).
- Publication of a plugin release, tags or plugin-dist pushes without the
  owner's explicit yes.
- Changes to `analyze`, `analyze-work`, `prepare`, `execute`, `recover`, grants,
  telemetry or System One.

## Authorities

Constitution clause zero and Articles 13, 14, 16, 19, 20 and 23;
[GOVERNANCE.md](../../GOVERNANCE.md);
[claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
ADR 0024 (native AI plugins), ADR 0027 (Braid Harness offline foundations),
ADR 0039 (Braid Lightning boundary, Proposed in SPEC-070). Precedents:
[SPEC-049](../049-harness-evaluation-learning/spec.md) and its
[promotion policy](../049-harness-evaluation-learning/promotion-policy.md);
program: [SPEC-070 program](../070-braid-lightning-foundations/program.md).

Article 13: a BL.2 score is a claim about a fixed task set, not verified
superiority; the preview states the cohort and evaluation it rests on.
Article 14: every promotion is inspectable by digest in the registry journal.
Article 16: a promoted text changes a shipped surface; the build check makes the
change explicit and versioned. Articles 19, 20 and 23: human authority,
reversibility and no hidden effects.

## Clarifications

Design decisions (approved with T001):

- **P1 — Carrier.** Whole texts use the profile registry; short reflections use
  the experience store. No new store is created.
- **P2 — Cohort.** Lightning candidates are evaluated on native host rollouts
  (SPEC-071), so the profile cohort is `native`; `decide()` already refuses a
  profile whose cohort differs from the evaluated cohort.
- **P3 — Scope map.** One registry scope maps to one file, for example
  `lightning.skill.analyze` → `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md`.
  The map is a closed table in the module; an unknown scope is refused.
- **P4 — Text store.** Candidate texts are stored content-addressed in the
  Lightning run store (SPEC-070) and copied to the mapped file only on
  `--apply`; the registry stores only digests.
- **P5 — Build check.** A packaged `SKILL.md` whose scope has a registry is
  verified against the active candidate; a scope without a registry is not
  checked (existing behaviour).

Owner decisions (T001, guided review on 2026-11-23; recorded here, frozen
with the approval record):

- **OD-1 — Initial scope map: analyze only.** The closed map has one entry,
  `lightning.skill.analyze` → `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md`
  with a 32 KiB text limit. `lightning.skill.plan` is not mapped because no
  producer exists; any other scope is refused with `unknown-scope`. Undo:
  adding a scope is one reviewed change to the closed table.
- **OD-2 — Build check: refuse release builds, warn local builds.** On a
  mismatch a release build fails and a local developer build reports the same
  `lightning-promotion-mismatch` message as a warning and continues. Undo:
  always-refuse is a one-line change.
- **OD-3 — Registry location: plugin home plus committed export.** The working
  registry lives in the private plugin home next to `lightning/`
  (`<plugin home>/lightning-promotion/registry.json`, never in Git). Release
  builds read a committed export at
  `integrations/lightning-promotion/registry-export.json`, outside the
  packaged plugin tree; the owner commits it together with the promoted
  `SKILL.md`. The build check catches an export that lags the file. Undo:
  moving the file is a path constant plus one copy.

Context: BL.2b (SPEC-078) found no candidate that beats A0, so this feature is
plumbing only and promotes nothing; T010 (the owner's rollback drill) is the
first and only real promotion run it plans.

## Requirements

- **REQ-001 — Candidate record.** `lightning_promote.build_record` turns a BL.2
  winner (candidate text digest, scope, and the SPEC-072 REQ-011 SPEC-049
  `Registration`/`EvaluationRecord` pair, A = A0, C = A2 GEPA) into a valid
  `ProfileRegistry.record` input with cohort `native`; a text over the mapped
  file's limit, an unknown scope, or a digest that does not match the stored
  text is refused. `build_record` refuses unless the SPEC-072 report records H1
  `supported` for every host of the scope; otherwise the preview states
  `no-held-out-support` and an apply requires an explicit owner override
  reason, which is recorded in the decision.
- **REQ-002 — Human decision only.** `decide()` is called with the SPEC-072
  `Registration` and `EvaluationRecord` pair and only with a human
  actor; any automatic actor is refused with `automatic-promotion-disabled`;
  `begin` and `commit` run only after an approved decision for the same
  candidate and current identity.
- **REQ-003 — Preview and apply.** `agent-braid lightning promote --candidate
  <sha>` prints the scope, target path, old and new digests, a diff summary,
  cited evidence and a preview digest, and writes nothing. `--apply
  --preview-digest <d>` writes only when the digest, the registry bytes and the
  target file bytes still match the preview. Every output carries
  `executionAuthorization: false`.
- **REQ-004 — Build check.** The plugin build verifies that each mapped
  `SKILL.md` digest equals the registry's active candidate for its scope and
  names the scope, expected and actual digests on mismatch.
- **REQ-005 — Rollback.** `promote --rollback --scope <s>` (preview, then apply)
  restores the previous active digest and its text; the next build carries it.
- **REQ-006 — Revocation.** Revoking an evidence digest cited by the active
  decision deactivates that candidate and restores the previous one through the
  registry; the CLI previews the file change before applying it.
- **REQ-007 — Reflections.** Optional GEPA reflections are proposed through
  `ExperienceStore.add` (poison screening, 512-character limit) and remain
  quarantined; this feature never calls `activate`.
- **REQ-008 — Boundaries.** The module opens no socket, launches no process,
  imports only the standard library and Agent Braid modules, exposes no MCP
  tool, and never writes outside the registry file, the run store and the
  mapped file.

## Success criteria

Each requirement has one acceptance scenario (SC-001 to SC-008) in
[assurance.json](assurance.json), with its procedure in
[validation-plan.md](validation-plan.md). Milestone exit: an owner
decide → begin → commit is recorded, a rebuilt plugin carries the promoted
digest, and rollback is tested.

## Compatibility

Additive. Registry and experience-store formats are unchanged. The build check
applies only to scopes with a registry, so existing builds are unchanged until a
promotion is committed.
