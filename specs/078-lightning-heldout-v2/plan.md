# SPEC-078 implementation plan

## Technical context and scope

SPEC-071 provides the subscription-only runner, rollout records, canaries and
quota stops; SPEC-069 provides the case format, the scorer
(`scripts/spec069_scoring.py`) and the fixture workspace
(`scripts/spec069_fixture_workspace.py`), both frozen by the SPEC-069 FREEZE
record and reused unchanged. SPEC-072 provides the held-out command pattern;
Gate 2 uses a new `lightning_edits` module, not GEPA's Pareto search. The target
guidance is the body of `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md`.
The runtime stays standard-library only. Scope follows REQ-001 to REQ-012.

## Constitution check before research

- Clause zero: a measured claim about guidance text under one scorer; no
  algebraic or semantic claim.
- Article 12: one runner process at a time; no concurrent agents or rollouts
  beyond the SPEC-071 runner's own control.
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
| Set authoring | `scripts/spec078_build_set.py` | builds cases from the class plan and per-split templates with seeded choice; writes all three files; deterministic; runs the REQ-002 build checks (fixture paths, prompt-facts agreement, 8-word window disjointness, v1 overlap) |
| Gate 0 | `scripts/spec078_gate0.py` | reference check, guidance-literal follower, null baselines, v1 overlap check; one JSON report |
| Literal follower | in `spec078_gate0.py` | rules encoded as small functions, each pinned to a sentence of the skill by a test |
| Freeze | `specs/078-lightning-heldout-v2/prompts/FREEZE.json` and `evidence/protocol-freeze.json` | sha256 of the three splits, the protocol, the Gate 0 script and the A0 skill; made on a `develop` commit |
| Runner sets | `agent_braid/lightning_runner` | new `PROMPT_FILES` keys `v2-feedback`, `v2-validation`, `v2-test`, all checked against the SPEC-078 FREEZE instead of the SPEC-069 one (`run()` calls `check_prompt_set` for every set); `check_protocol_freeze` generalized; `canary_note` adds the held-out canary for `v2-test`; `is_train` true for `v2-feedback` only; v2 validation and test paths added to `OPTIMIZER_DENIED`; contamination fingerprints cover v2 validation and test |
| Analysis | `agent_braid/lightning_heldout_v2.py` (new module, kept apart from the SPEC-072 promotion-record code) | per-prompt pass, Wilson, prompt-clustered SE, one-sided exact sign test, OD-1 verdict, all-three count, 0/3 review hold |
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

Budget: Gate 1 = 100 × 3 = 300 rollouts. Gate 2 (conditional, OD-4 caps): A0
on validation 40 × 3 = 120; per round feedback 24 × 1 plus validation 120, at
most 4 rounds = 576; final candidate on test 300; v1 for candidate and A0 in the
same pass 2 × 10 × 3 = 60; ceiling 1056 plus 4 reflection calls. Every real run is preceded by the owner's yes on the stated
count.

## Constitution check after design

Unchanged. The scorer and promotion stay outside the design.

## Human review and unresolved decisions

OD-1 to OD-3 decided 2026-11-20 (OD-1 per-class clause added the same day).
Gate 2 caps decided 2026-11-21 (OD-4): 4 rounds, 400 characters per edit,
ceiling 1056 rollouts. Nothing remains open before the freeze.

Decided:

- the skill's coverage sentence ("it turns every pair into `unknown`") was
  imprecise: the analyzer reports `ordered` and `conflicting` before falling
  back to `unknown` for partial coverage. Owner decision 2026-11-20: correct it
  before the freeze (T003); A0 is the corrected guidance.
