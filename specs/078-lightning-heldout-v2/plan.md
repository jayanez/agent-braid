# SPEC-078 implementation plan

## Technical context and scope

SPEC-071 provides the subscription-only runner, rollout records, canaries and
quota stops; SPEC-069 provides the case format, the scorer
(`scripts/spec069_scoring.py`) and the fixture workspace
(`scripts/spec069_fixture_workspace.py`), both frozen by the SPEC-069 FREEZE
record and reused unchanged. SPEC-072 provides `lightning_gepa` (Pareto
selection over per-case vectors) and the held-out command pattern. The target
guidance is the body of `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md`.
The runtime stays standard-library only. Scope follows REQ-001 to REQ-012.

## Constitution check before research

- Clause zero: a measured claim about guidance text under one scorer; no
  algebraic or semantic claim.
- Article 9: Gate 0 must be able to fail (null baselines, broken-reference
  controls); a negative or null outcome is valid.
- Articles 13, 14: results are empirical, bound to host, model, guidance hash and
  set hash; lineage is recorded.
- Article 19: the problem is the uninterpretable SPEC-072 result.
- Article 20: no execution authority, no promotion.
- Article 21: research value (powered, audited baseline measurement) and
  engineering value (regression suite) are stated.
- Article 23: laboratory phase, off by default.

No MUST contradiction found. No SHOULD deviation proposed.

## Research, assumptions and alternatives

See [research.md](research.md). The data source is project-written synthetic
prompts over the SPEC-069 fixture workspace; no user data, no consent question.
Yield is fixed by construction (164 cases); feasibility is gated by Gate 0, not
by data availability.

## Design and compatibility

| Piece | Location | Notes |
|---|---|---|
| Set v2 (three splits) | `specs/078-lightning-heldout-v2/prompts/{feedback,validation,test}.json` | SPEC-069 case format plus `class` and `facts`; only files and branches of the existing fixture |
| Set authoring | `scripts/spec078_build_set.py` | builds cases from the class plan and templates with seeded choice; writes all three files; deterministic |
| Gate 0 | `scripts/spec078_gate0.py` | reference check, guidance-literal follower, null baselines, v1 overlap check; one JSON report |
| Literal follower | in `spec078_gate0.py` | rules encoded as small functions, each pinned to a sentence of the skill by a test |
| Freeze | `specs/078-lightning-heldout-v2/prompts/FREEZE.json` and `evidence/protocol-freeze.json` | sha256 of the three splits, the protocol and the Gate 0 script; made on a `develop` commit |
| Runner sets | `agent_braid/lightning_runner.PROMPT_FILES` | new keys `v2-feedback`, `v2-validation`, `v2-test`; `v2-test` requires the SPEC-078 freeze and gets the held-out canary; the optimizer contamination scan also covers v2 validation and test fingerprints |
| Analysis | `agent_braid/lightning_evaluation.py` (new functions) | per-prompt pass, Wilson, prompt-clustered SE, exact sign test, OD-1 verdict, D4-style counts, pass^3 |
| Gate 2 arm | `agent_braid/lightning_edits.py` (only if Gate 2 opens) | section-level add/delete/replace edits, character budget, rejected buffer, strict validation improvement, diff |

Case `facts` example (illustrative, not a v2 case):
`{"units": [{"key": "a", "writes": ["src/cli.py"], "uses": [], "after": []}], "allFilesNamed": true, "question": "parallel"}`.

Compatibility: SPEC-069 sets, FREEZE, scorer and fixture untouched; existing
runner prompt sets keep their behaviour; new records reuse SPEC-071 schemas.

## Validation strategy

Requirement → scenario → procedure → evidence is in
[validation-plan.md](validation-plan.md) and `assurance.json`. Negative controls:
a case with a wrong reference blocks Gate 0; a skill edit that removes a pinned
rule fails the pin test; each null baseline fails; a v1 prompt copied into v2 is
refused; a held-out run with an edited set or protocol is refused. The
acceptance rule (OD-1), splits (OD-2), host and model (OD-3), and the analysis
are fixed in `evaluation-protocol.md` and frozen with the set before any rollout.
Class coverage per split is printed by the build script and recorded before the
freeze.

Budget: Gate 1 = 100 × 3 = 300 rollouts. Gate 2 (conditional) = validation
evaluations of 40 × 3 per accepted or rejected candidate, bounded by the
protocol's round and rollout caps, plus 300 test and 30 v1 rollouts. Every real
run is preceded by the owner's yes on the stated count.

## Constitution check after design

Unchanged. The scorer and promotion stay outside the design.

## Human review and unresolved decisions

OD-1 to OD-3 decided 2026-11-20. Open: the Gate 2 round and rollout caps are set
in `evaluation-protocol.md` at T003 and reviewed with the freeze.
