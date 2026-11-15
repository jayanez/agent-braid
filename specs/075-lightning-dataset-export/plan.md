# SPEC-075: Plan

## Technical context and scope

Python 3, standard library only (`pyproject.toml` `dependencies = []`). Inputs:
the SPEC-070 store (`lightning/runs/<run-id>/` under the plugin home) read
through SPEC-074 `agent_braid/lightning_adapter.py`. Outputs: a local export
directory. Serialization reuses `agent_braid/trace_adapter.canonical_bytes`.
No network, process, GPU or model.

## Constitution check before research

| Article | Check | Status |
|---|---|---|
| 13 | datasets make no improvement claim | pass |
| 14 | per-record hashes and manifest digest allow replay | pass |
| 15–16 | limits (`text-level-merge`, exclusions) declared, not hidden | pass |
| 19 | consent and redaction precede export | pass, depends on SPEC-074 |
| 20 | `executionAuthorization` false; no execute/grant path | pass |
| 23–24 | owner gates (T001, OD-1) explicit | pass |

## Research, assumptions and alternatives

See [research.md](research.md). Assumptions: SPEC-074 exposes consent level and
redaction version per trace; the SPEC-071 reward vector is stable. Checked at
T003 against the frozen adapter: triplets carry `redaction.scanClean`, consent
loss notes and the `attempt-<hmac16>` pseudonym but no redaction version (the
builder defines it, T006); the rollout reader notes `content-consent-required`
both without consent and for an unlisted source, so the export reads the
SPEC-074 gate's refusal for `rollout` itself to tell `consent-none` from
`no-consent`. Task and group ids come from the content-free rollout records.
Alternatives: Parquet, HF `datasets`, random order — rejected (dependencies,
network, non-determinism).

## Design and compatibility

| Upstream file (v1.0.3) | New module | Port |
|---|---|---|
| `agentlightning/verl/rollout_adapter.py` (trace aggregation, length bounds) | `agent_braid/lightning_export.py` | concepts only; text-level merge; no tensors |
| `agentlightning/server/store.py` (rollout/attempt query) | read via `agent_braid/lightning_adapter.py` (SPEC-074) | none here |
| — | `agent_braid/cli.py` `lightning export` subcommand | new |
| — | `schemas/0.3.0-experimental/lightning-dataset-manifest.schema.json` | new (lead) |

Pipeline: terms gate (if any candidate source is `host-model`) → select →
consent/redaction filter (counted) → aggregate (level) → balance (seeded, `rollout` kind only) →
canonical lines → canary scan → write `records.jsonl` then `manifest.json`
atomically (temporary directory, then rename). Compatibility: additive only.

## Validation strategy

Unit and fixture tests per [validation-plan.md](validation-plan.md), with a
negative control for every gate; CI `quick` profile.

## Constitution check after design

Unchanged: all gates pass; the terms gate is an owner record, never inferred.

## Phases

- P0: T001 owner review.
- P1: T002 schema, T003 filter, T004–T005 formats, T006 manifest and
  determinism, T007 balance.
- P2: T008 terms gate, T009 CLI, T010 canary scan, T011 boundaries, T013
  source retention.
- Closing: T012 documentation and converge.

## Risks

| Risk | Mitigation |
|---|---|
| Redaction misses a secret | canary scan aborts (REQ-010) |
| Provider terms forbid training use | OD-1 gate; fixtures-only export |
| Text-level merge misaligns turns | declared limit; transition level available |
| Hidden non-determinism (dict order, locale, paths) | canonical bytes; rerun in another directory |

## Human review and unresolved decisions

T001 owner review done 2026-11-14 ([record](reviews/owner-t001-20261114.md)):
E1–E5 accepted, OD-2 decided (equal cap 1:1 per task, no ratio parameter). OD-1
is deferred: the terms gate (T008) ships closed and refuses every host-model
export with `terms-gate-missing`; only fixtures and non-host content export.
`human_review` stays `pending`.
