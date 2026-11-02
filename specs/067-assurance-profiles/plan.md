# SPEC-067: Implementation plan

## Technical context and scope

Python 3.12+ standard library only. Planning only: no code, ADR or shared
tracking change in this specification PR. Offline-implementable with
deterministic tests; no network, clock or model call in any gate logic.

Planned target files (after founder decisions):

| File | Change |
|---|---|
| `agent_braid/harness_assurance.py` (new) | schema, catalog, resolver (SPEC-058 REQ-006 precedent), floors, compiler, profile journal |
| `agent_braid/harness_assurance_risk.py` (new) | deterministic raise-only diff classifier |
| `agent_braid/harness_assurance_receipts.py` (new) | receipt builder and verifier, standing-authorization check |
| `agent_braid/harness_assurance_render.py` (new) | track-brief and PR "Pre-PR review" generators |
| `tests/test_harness_assurance*.py` (new) | positive and negative tests, goldens |
| `specs/067-assurance-profiles/evidence/**` | decision records, task evidence |

Not changed: `agent_braid/harness_promotion.py`, SPEC-057/058 modules,
`scripts/validate_change.py`, the PR template. `harness_promotion` commits only
evaluated `PromotionDecision`s, so profile changes use a separate journal that
follows its begin/commit/rollback pattern (REQ-008).

## Constitution check before research

| Article | Obligation | Plan response |
|---|---|---|
| 0, 13 | no inflated claims | receipts are process records; no utility claim (H1 is a hypothesis) |
| 4, 14 | verified, evidence not verdicts | receipts carry commands, exits, digests; verifier checks consistency, not review soundness |
| 5 | effects are first-class | native effect and release are `human-only` floors |
| 12 | concurrency and effect control | operator-owned config; agent-writable paths are never sources; serial orchestrator merge stays the model |
| 15 | declared metadata not blindly trusted | receipts re-verified against commit and profile digest; operator-owned store |
| 20 | analysis separate from execution | `executionAuthorization: false`; no executing path |
| 24 | semantics before production | contracts are proposals until reviewed |

No MUST conflict found. SHOULD deviation: none.

## Design

1. **Catalog and schema.** Closed checkpoint catalog and allowed-mode table in
   one module; unknown keys refused; fixed refusal strings.
2. **Resolver.** Scopes and floors per SPEC-058 REQ-006, with the REQ-003 floor
   set and the no-attribution floor; output records source per value and refused
   lowerings.
3. **Risk classifier.** Pure function from a diff summary (paths, lines, shared
   files) and operator rules to a class and a raise-only adjustment; rules that
   would lower are refused at load.
4. **Compiler.** Resolved view plus classification to an immutable artifact with
   input hashes, digest and `executionAuthorization: false`.
5. **Receipts.** Canonical JSON builder and verifier (REQ-007); standing
   authorization validity check with fallback to `approve-each`.
6. **Renderers.** Deterministic brief and PR-section generators from the
   compiled artifact.
7. **Profile changes.** A human act recorded in the profile journal; the
   loader reads only operator-owned locations.
8. **Evaluation.** A SPEC-049 registration record for H1 (T009), not a run.

## Validation strategy

Requirement to scenario to procedure to evidence in
[validation-plan.md](validation-plan.md) and [assurance.json](assurance.json).
Every refusal reason has a negative test; goldens prove determinism. Unit tests
prove logic, not review quality. `quick` after each increment; `pr` once on the
stable candidate, in a clean clone while the shared object store fails the
portable-root check.

## Constitution check after design

Unchanged: advisory only, human-owned authority, raise-only escalation, floors
that no source lowers.

## Proposed shared-file changes

Not made by this feature; for the orchestrator and founder:

- `docs/development/github-tracking.json` — `specs["067-assurance-profiles"]`
  mapping (validation requires every `specs/` directory to be mapped; see the
  PR description for whether this blocked validation).
- `docs/development/SPEC_MILESTONE_INDEX.md` — SPEC-067 under HAR.
- `ROADMAP.md`, `docs/STATUS.md` — one line each.
- `docs/adr/` — ADR for assurance profiles and the standing-authorization record
  (T010), by the owner of shared files.
- `scripts/validate_change.py` — optional later hook to emit a receipt for
  `quick`/`pr`; not planned in v0.1.
- `AGENTS.md` — point to the compiled profile once adopted.
- `.github/pull_request_template.md` — optional "Pre-PR review" block under
  Evidence; v0.1 renders text for the existing Evidence section.

## Human review and unresolved decisions

Q1 to Q6 decided 2026-11-02 (T001, [record](evidence/founder-decisions-20261102.json)). Pending: human review of this specification; ADR
acceptance (T010) before any profile is adopted.
