# SPEC-074 implementation plan

## Technical context and scope

Python standard library only. Reads SPEC-070 `lightning_config` and
`lightning_store`, `trace_adapter`, `tooling_claude_observer`,
`tooling_codex_observer`, `view_loom` and `system_one_shadow`. New modules:
`agent_braid/lightning_redact.py` and `agent_braid/lightning_adapter.py`. The
spec069 secret patterns move to `lightning_redact` (the script imports them).
No network, model or subprocess.

## Constitution check before research

| Article | Check | Status |
|---|---|---|
| 13 | redaction claims bounded to the canary corpus | planned (residual risks stated) |
| 14 | outputs inspectable: digests, redaction counts, losses | planned |
| 16 | new record schemas versioned as experimental | planned |
| 19 | consent is a human, previewed act | planned |
| 20 | purge and lowering consent reverse collection | planned |
| 23 | no hidden collection; default `none` | planned |

## Research, assumptions and alternatives

See [research.md](research.md). Assumptions: SPEC-070 store, configuration
schema `traces` section (extended here) and `lightning purge` exist; host transcript readers expose turn-level records.
Rejected: a `raw` level, export-time redaction, OpenTelemetry tracers.

## Design and compatibility

| Upstream file (agl-v0 6db3c73) | New module | Adaptation |
|---|---|---|
| `agentlightning/adapter/triplet.py` (`TraceTree`, `TracerTraceToTriplet`, `RewardMatchPolicy`) | `agent_braid/lightning_adapter.py` | stdlib dataclasses over Agent Braid records; redaction mandatory; no pydantic/OTel |
| `agentlightning/adapter/messages.py` (`TraceToMessages`) | `agent_braid/lightning_adapter.py` | role/content lists; tool calls kept as redacted text |
| `agentlightning/adapter/base.py` (`TraceAdapter`) | `agent_braid/lightning_adapter.py` | one `adapt(source, records, consent)` entry point |
| `agentlightning/tracer/*` | not ported | Agent Braid reads existing local records |
| `agentlightning/store/*` (span storage) | SPEC-070 `lightning_store` (reused) | consent gate and retention added |
| — (`scripts/spec069_native_runs.py` patterns) | `agent_braid/lightning_redact.py` | shared pattern set, typed placeholders, encoded forms |

Contracts: [trace-consent](contracts/trace-consent.md),
[triplet](contracts/triplet.md); privacy: [privacy-review.md](privacy-review.md).
Compatibility: additive; default unchanged.

## Validation strategy

Deterministic tests with a committed canary corpus, injected clock for
retention, temporary homes, and fixture transcripts, Loom streams and shadow
episodes. Procedures in [validation-plan.md](validation-plan.md).

## Constitution check after design

Collection is opt-in, previewed and reversible; redaction precedes storage; the
System One boundary is enforced by read-only access and a negative test. Residual
risks are listed in the privacy review and shown in the consent preview.

## Phases

- P1: consent contract, schema corpus, refusal without consent (REQ-001, REQ-002).
- P2: redaction and canary corpus (REQ-003, REQ-004).
- P3: retention and purge (REQ-005).
- P4: adapter and source readers, System One isolation (REQ-006, REQ-007).
- Closing: boundaries, privacy review sign-off, converge (REQ-008).

## Risks

| Risk | Mitigation |
|---|---|
| redaction misses a shape | canary corpus grows with every finding; post-scan refusal |
| host transcript format drift | losses recorded; fixture per host version |
| moving spec069 patterns breaks the script | script imports the shared list; its tests run in `quick` |
| performance on large transcripts | streaming read with size caps from `trace_adapter` bounds |

## Human review and unresolved decisions

OD-1 to OD-3 in [spec.md](spec.md); owner review is T001.
