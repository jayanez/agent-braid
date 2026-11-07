# SPEC-071 implementation plan

## Technical context and scope

`scripts/spec069_native_runs.py` already launches Claude Code and OpenCode
headless in disposable profiles under a macOS OS sandbox, parses their streams
and scores attempts with `scripts/spec069_scoring.py`. It authenticates with
`ANTHROPIC_API_KEY` (`KEY_SPECS`), which is the paid route. SPEC-070 provides
`lightning_schema`, `lightning_config` and `lightning_store`. The runtime stays
standard-library only. Scope follows REQ-001 to REQ-014; L1–L5 are binding.

## Constitution check before research

- Clause zero, Article 0: engineering only; no algebraic claim.
- Article 12: bounded concurrency (`parallel` default 1) and the store lock.
- Article 13: rewards are empirical measurements, labelled as such.
- Article 14: hashes of candidate, prompt, transcript and reward for replay.
- Article 19: the measured problem is the T010 negative baseline.
- Article 20: no execution, grants or MCP-started runs.
- Article 23: lab phase; nothing promoted.

No MUST contradiction found. No SHOULD deviation proposed.

## Research and alternatives

See [research.md](research.md). Alternatives rejected: keeping the API-key route
(violates L1 and ADR 0021); an LLM judge (not verifiable); porting the
Kubernetes reconciler (no isolation need beyond the OS sandbox); calling the
SPEC-069 driver as a subprocess (duplicates parsing and hides records).

## Design

| Upstream or local source | New module | Notes |
|---|---|---|
| `scripts/spec069_native_runs.py` (local) | `agent_braid/lightning_hosts.py` | moved functions; driver re-imports them; `KEY_SPECS` stays in the driver |
| v1.0.3 `agentlightning/controller/local_reconciler.py` | `agent_braid/lightning_runner.py` | subprocess, timeout, kill tree, bounded parallel, subscription gate |
| v1.0.3 `agentlightning/hooks.py` | `agent_braid/lightning_hooks.py` | synchronous hooks |
| v1.0.3 `agentlightning/schemas.py` | SPEC-070 `lightning_schema` | rollout record extends it |
| v0.x `agentlightning/emitter/reward.py` | `agent_braid/lightning_reward.py` | vector reward over `score_case` and `analyze_work_schema` |
| v0.x Trainer CLI | `agent_braid/lightning_cli.py` (`run`, `status`, `report`) | registered by SPEC-070 |

Flow: configuration, FREEZE and scoring hash check, environment gate
(REQ-004), isolation probe; then per rollout: profile, hooks, launch, parse,
key-source check, teardown, reward, store; finally the summary.

Each ported file carries the SPDX header and adaptation notice of ADR 0040.

## Constitution check after design

Same result as before research. The design adds no MUST deviation; the
credential path is gated by OD-1.

## Phases

1. P0 — owner review (T001).
2. P1 — extraction (T002) with byte-identical driver evidence.
3. P2 — runner, hooks, reward, controls, CLI (T003–T010) with unit tests.
4. P3 — fake-host pipeline in CI (T011).
5. P4 — owner credential decision and real baseline (T012).
6. Closing — converge (T013).

## Risks

- Hosts change stream formats: parsers record host versions; fake hosts pin
  expected shapes.
- OpenCode may expose no key source (OD-2): the runner refuses rather than
  assumes.
- Quota exhaustion mid-run: recorded stop, resumable; partial results are
  reported as partial.
- Real baseline outside the interval: reported as non-replication; SPEC-072
  then uses the new baseline as its control.
- The OS sandbox is macOS only; Linux CI runs fake hosts only, recorded as a
  limit.
