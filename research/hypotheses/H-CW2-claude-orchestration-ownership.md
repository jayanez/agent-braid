# H-CW2: Declared ownership adds to the baseline on Claude orchestration surfaces

**Identifier:** H-CW2. **Claim label:** hypothesis (a falsifiable proposition
with a stated domain). **Evidence status:** untested. Milestone M4.6, gate G1.

## Statement

In the domain below, and separately for each surface, three propositions hold
against a baseline of prompt partitioning, the host's isolation flag where
applicable and the SPEC-052 end-of-run gate:

- (a) Advisory (arms A1 and A2): declared ownership with an advisory pre-flight
  and a declared-versus-observed envelope receipt prevents, or where a stage
  order exists catches before the SPEC-052 gate, at least one integration
  failure per claimed surface (a paired catch: the baseline fails in both
  repetitions, the treatment names the failing unit pair and path, and the
  surface passes a noise floor taken from baseline repeats), keeps tracks
  parallel (unnecessary serialization at most 0.25), shows no pre-flight false
  assurance above 0.10 in a screen of at least 6 natural task sets (a screen, not
  a safety gate), and keeps write-set declaration recall at least 0.85 (criteria
  CA1 to CA6; the unit is the task set).
- (b) Pull digests (arm A2 against A1): epoch-stamped pull digests surface at
  least one mid-run drift before the first harm event, earlier than the
  checkpoint receipt does, on a surface with sibling sessions or teammates (CN1,
  CN3). Late notice with measurable harm under pull digests (CN2) is recorded
  separately and is the only G1 record that can support planning an opt-in push.
  This is a prerequisite for planning a ledger, not support for one.
- (c) Opt-in guard (arms A3a and A3b): an enforcement profile compiled from the
  same declaration, in audit then block mode, keeps the false-block rate at most
  0.10, the bypass rate at most 0.20, allows no successful tamper of its own
  control paths, is observed live at least 0.95 of the time on a claimed surface,
  and keeps one designed failure clean that A2 did not (CG0 to CG5). A
  native-controls-only arm (AN, hand-written deny rules and sandbox allowlist)
  is a descriptive comparison only; without it no claim is made against
  `permissions.deny` or sandbox settings alone.

Founder decisions of 2026-10-24 apply: stage 1 runs on two surfaces; CA1 is an
existence screen on designed overlap only; the guard arms run an unreleased
SPEC-058 engineering candidate behind the gate (release only after GG passes and
the ADR is adopted, and the guard ADR proposal is reviewed now and adopted with
the G1 outcome); the default notification strategy is pull notices plus
per-agent context ("Mailbox + Whisper"); recovery is outside G1 evidence.

## Domain

Claude Code only. Four surfaces, each claimed or dropped on its own: dynamic
workflow tracks, sessions launched from another session, agent teams sharing one
working tree, and `/batch` units. Founder-controlled repositories, Sonnet at
medium effort, 3 or 4 tracks per task set (5 or 6 for `/batch`), a natural
stratum from the founder's backlog and a designed-overlap stratum reported
separately. Nothing outside this domain is claimed: not Codex, cloud sessions,
Remote Control, other machines or VS Code; not prevalence of conflicts; not
semantic conflicts beyond declared coverage; not shell-driven writes; not
runtime speed. Declarations are claims, not observations, and an
independent-candidate verdict is not a clean-merge guarantee.

## Falsification condition

Under the frozen preregistration, per gate and with the stated minimums met:

- (a) is falsified by any hard criterion unmet with its denominator met (false
  assurance above 0.10, write recall below 0.85 or precision below 0.40, pair
  unknown share above 0.40), or by an unmet benefit criterion with its
  denominator met (no catch on at least two claimed surfaces that pass the noise
  floor, serialization or overhead above the ceilings).
- (b) is falsified by no drift surfaced earlier by a digest, or more than 3
  digests per track.
- (c) is falsified by any successful tamper, liveness below 0.95 on every
  surface, false-block or bypass rate above its ceiling, no incremental catch, or
  a hook latency or tool-call overhead above its ceiling; it also fails when (a)
  fails.

Order of evaluation: tamper first (guard only); then surface minimums (below
them is not-claimed, and too few claimed surfaces is inconclusive); then hard
criteria with met denominators (fail); then benefit criteria with met
denominators (fail); then any criterion with an unmet denominator
(inconclusive); otherwise pass. Fail therefore takes precedence over
inconclusive once the failing criterion's minimums are met. Inconclusive is not
support, and the guard gate is expected to be inconclusive at the minimum counts
and EUR 0 unless a denominator projection holds. A negative or inconclusive
result is a valid, reportable outcome.

## Evidence status and links

- Obtained evidence: none. The preregistration is not frozen and no run exists.
  The prior dogfood observation (three fan-outs, one stale-read event, no outcome
  measured) is not evidence of prevented failures.
- Preregistration: [proposal](../../docs/experiments/CLAUDE_ORCHESTRATION_G1_PROPOSAL.md)
  and [inputs](../../docs/experiments/claude-orchestration-g1-inputs.json),
  checked by `scripts/validate_claude_orchestration_g1_proposal.py`.
- Specifications: [SPEC-057](../../specs/057-claude-orchestration-advisory/spec.md)
  (owner), [SPEC-058](../../specs/058-claude-orchestration-guard/spec.md)
  (gated by this experiment and an ADR amendment),
  [SPEC-059](../../specs/059-claude-orchestration-ledger/spec.md) (additionally
  blocked by gate G2); integration comparator SPEC-052.
- Related negative result: parallel runtime speedup NO-GO (SPEC-021 G4, SPEC-022,
  SPEC-038); H-CW2 makes no timing claim.
- Related hypothesis: [H-CW1](H-CW1-claude-workflow-integration.md) (transcript
  evidence, gate G0), independent of this one.
- Index: the identifier is indexed only in the hypotheses README (integrator
  change); RESEARCH.md is a separate authority change.
