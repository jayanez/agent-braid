# SPEC-073 implementation plan

## Technical context and scope

Python standard library only; Agent Braid modules `harness_promotion`,
`harness_experience`, `plugin_package` and the SPEC-070 Lightning store and
configuration. Input: a BL.2 winner record (SPEC-072) with candidate text,
evaluation and cost report. Output: a registry journal entry, an updated
`SKILL.md`, and a build that verifies it. No host, model or network calls.

## Constitution check before research

| Article | Check | Status |
|---|---|---|
| 13 | scores presented as fixed-task-set evidence, not superiority | planned (preview `evidence`, cohort) |
| 14 | every change inspectable by digest | planned (journal, preview) |
| 16 | shipped surface change versioned and checked | planned (build check) |
| 19 | human-only decision | held by `AUTOMATIC_PROMOTION = False` |
| 20 | reversible | planned (rollback, revoke) |
| 23 | no hidden effects | planned (preview digest, bounded writes) |

## Research, assumptions and alternatives

See [research.md](research.md). Assumptions: SPEC-072 emits the winner with
evaluation and cost report digests compatible with `decide()`; skill texts fit
the scope map limits. Rejected alternatives: a new Lightning registry;
automatic hot-swap of resources as upstream does; whole texts in the experience
store; manual skill edits after an approval.

## Design and compatibility

| Upstream file (agl-v0 6db3c73) | New or reused module | Adaptation |
|---|---|---|
| `agentlightning/store/base.py` (versioned resources) | `agent_braid/lightning_promote.py` (new) | resources become registry candidates; never served automatically |
| `agentlightning/store/memory.py` (latest resource lookup) | `ProfileRegistry.active` (reused) | active digest derived by journal replay |
| — | `agent_braid/harness_promotion.py` (reused) | unchanged |
| — | `agent_braid/harness_experience.py` (reused) | reflections only |
| — | `agent_braid/plugin_package.py` (extended) | registry digest check |

Functions: `build_record(winner, scope)`, `preview(action, scope, candidate)`,
`apply(preview_digest, decision)`, `check_build(root, registries)`,
`propose_reflections(store, texts, at)`. CLI `agent-braid lightning promote`
per [contracts/promotion-preview.md](contracts/promotion-preview.md); scope map
per [contracts/scope-map.md](contracts/scope-map.md). Compatibility: additive.

## Validation strategy

Deterministic unit tests with temporary plugin homes and a copied plugin tree;
a negative control for every refusal; one owner-run promotion recorded as
real-use evidence. Procedures in [validation-plan.md](validation-plan.md).

## Constitution check after design

No article is weakened: the only mutation path requires a human decision and a
matching preview digest; the build check binds shipped text to the journal;
rollback and revocation reuse the registry replay. Residual risk: a developer
can still edit `SKILL.md` by hand; the build check detects it.

## Phases

- P1: module, scope map, record and preview (REQ-001, REQ-003, REQ-008).
- P2: apply with human decision; build check (REQ-002, REQ-004).
- P3: rollback, revocation, reflections (REQ-005, REQ-006, REQ-007).
- Closing: owner promotion, rebuild and rollback evidence.

## Risks

| Risk | Mitigation |
|---|---|
| promoted text regresses host behaviour | one-command rollback; native cohort only |
| registry and file diverge after a crash | begin/commit with atomic rename; abort restores |
| hand edit bypasses the registry | build check refuses release builds |
| reflection carries an injected instruction | experience poison screening; quarantine |

## Human review and unresolved decisions

OD-1 to OD-3 in [spec.md](spec.md); owner review is T001.
