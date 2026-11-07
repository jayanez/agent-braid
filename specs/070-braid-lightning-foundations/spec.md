# SPEC-070: Braid Lightning foundations

**Milestone:** BL.0 — Braid Lightning foundations (GitHub milestone created by the
reviewed tracking reconciliation after merge).

**Status:** draft. Owner decisions L1–L5 of 2026-11-08 are recorded in the
[program](program.md). `human_review` is pending; this specification grants no
execution authority.

## Purpose and scope

Braid Lightning is an off-by-default optimization layer that improves the text
artifacts Agent Braid owns from recorded rollouts and verifiable rewards,
adapting microsoft/agent-lightning (MIT) to Agent Braid's governance. This
specification delivers its foundations: the governing ADRs, the vendoring
provenance, a standard-library data model, a validated configuration profile
with a wizard, a private append-only run store, and the setup opt-in. It is
engineering, not a research protocol; BL.1 and BL.2 carry the measurements.

In scope:

- ADRs 0039 (boundary), 0040 (MIT vendoring into AGPL), 0041 (content-bearing
  traces) and 0042 (deferred fine-tuning carve-out), as Proposed;
- the upstream license, third-party record and per-file adaptation notices;
- `agent_braid/lightning_schema.py`: Rollout, Attempt, Event, Model and Reward
  records with exact-key validation and the upstream state machine;
- `agent_braid/lightning_config.py`, the `braid-lightning-config/v0.1` schema
  and the `agent-braid lightning init|validate|status` commands;
- `agent_braid/lightning_store.py`: per-run private JSONL directories, file lock,
  retention sweep and purge;
- `plugin setup --lightning {off,lab}` and its registry key.

Exclusions:

- Launching hosts, calling any model, or computing rewards (SPEC-071).
- Optimization algorithms (SPEC-072), promotion (SPEC-073), content-bearing
  traces (SPEC-074), dataset export (SPEC-075), weight training (SPEC-076).
- Any network listener, MCP tool, or new runtime dependency.
- Any change to `analyze`, `analyze-work`, `prepare`, `execute`, `recover`,
  grants, telemetry or System One behaviour.

## Authorities

Constitution clause zero and Articles 0, 12, 13, 14, 16, 19, 20, 23 and 25;
[GOVERNANCE.md](../../GOVERNANCE.md); [claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
ADR 0012 and ADR 0033 (vendored-code license boundaries), ADR 0021 (EUR 0 spend),
ADR 0024 (native plugins), ADR 0025 (local telemetry), ADR 0027 (Braid Harness
offline foundations), ADR 0034 (System One advisory boundary). Precedents:
[SPEC-048](../048-harness-variant-laboratory/spec.md),
[SPEC-049](../049-harness-evaluation-learning/spec.md),
[SPEC-066](../066-system-one-shadow/spec.md),
[SPEC-069](../069-aim-request-authoring/spec.md). Research basis:
[research.md](research.md).

The ROADMAP lists "specific model/runtime integrations" as a deferred decision
requiring an ADR; ADR 0039 is that record for Braid Lightning. Changing the
license boundary requires an ADR and the founder (GOVERNANCE.md); ADR 0040 is
that record. Neither is accepted by this specification.

## Clarifications

Owner decisions L1–L5 (2026-11-08) are binding; see [program.md](program.md).
Additional design decisions recorded here:

- **F1 — State location.** Configuration and run state live under the plugin
  home (`plugin_registry.home_path()`, honouring `AGENT_BRAID_HOME`):
  `lightning/lightning.json` and `lightning/runs/<run-id>/`. Same privacy rules
  as the registry (owner-only modes, no symlinks).
- **F2 — Registry key.** `lightning` is an optional registry key with values
  `off` (never stored) and `lab`; absent means off; it enters the configuration
  digest only when not off, so existing registries keep their digest. `lab`
  only records the owner's consent to run the CLI laboratory; the MCP server
  never starts a run.
- **F3 — Fixed values.** The configuration schema enforces `budget.eurCap = 0`,
  `optimizer.route = "subscription"`, `promotion.mode = "human"` and
  `promotion.executionAuthorization = false`. They are constants, not options.
- **F4 — No Kubernetes, no Hydra.** Upstream Hydra YAML becomes one JSON
  document with a JSON Schema; the Kubernetes runner is not ported.

## Requirements

- **REQ-001 — Governance records.** ADRs 0039–0042 exist with status Proposed,
  each with context, decision, alternatives and consequences; 0039 states the
  advisory boundary, EUR 0 subscription route, human-only promotion, and that
  the "no fine-tuning" statements of SPEC-034 to SPEC-037 are scoped to
  forecasting; 0042 is marked deferred to BL.6.
- **REQ-002 — Provenance.** The MIT license text is kept in
  `LICENSES/Agent-Lightning-MIT.txt`; `docs/development/THIRD_PARTY.md` records
  both pinned upstream commits and the file map; every adapted module carries
  `SPDX-License-Identifier: AGPL-3.0-only` plus an adaptation notice naming the
  upstream path, commit and MIT license; `third-party-inventory.md` lists the
  upstream file hashes.
- **REQ-003 — Data model.** `lightning_schema` provides immutable Rollout,
  Attempt, Event, Model and Reward records. Parsing refuses unknown or missing
  keys, non-finite numbers, wrong types and invalid identifiers; rollout state
  transitions follow upstream `VALID_TRANSITIONS` (queuing→running|failed,
  running→succeeded|failed, terminal states final); serialization is canonical
  and round-trips byte-identically.
- **REQ-004 — Configuration.** `lightning_config` validates a
  `braid-lightning-config/v0.1` document against
  `schemas/0.3.0-experimental/lightning-config.schema.json` semantics (exact
  keys, closed enumerations, bounded integers, F3 constants), merges defaults,
  and computes a digest over canonical bytes. The schema file and the validator
  agree on a shared corpus of valid and invalid documents.
- **REQ-005 — Wizard.** `agent-braid lightning init` builds a configuration
  interactively (prompts with defaults; closed choices validated) or from flags
  (`--non-interactive`), prints a preview with effects and a preview digest, and
  writes only with `--apply --preview-digest <digest>` when the digest and the
  file's prior bytes still match. `validate` checks an existing profile;
  `status` reports it with the setup consent and run directories.
- **REQ-006 — Store.** `lightning_store` creates per-run directories with
  owner-only modes, appends canonical JSON lines for rollouts and events under
  an exclusive lock, refuses symlinks and unknown record kinds, refuses
  content-bearing fields while trace consent is `none`, sweeps runs older than
  the configured retention, and purges a run on request.
- **REQ-007 — Setup opt-in.** `plugin setup --lightning {off,lab}` previews and
  applies the registry key per F2, with an effects line; registries without the
  key keep their digest; the setup skill describes the step only when asked and
  never chooses for the user.
- **REQ-008 — Boundaries.** BL.0 code opens no network socket, launches no
  process, imports nothing outside the standard library, exposes no MCP tool,
  and emits `executionAuthorization: false` in every CLI output.

## Success criteria

Each requirement has one acceptance scenario (SC-001 to SC-008) in
`assurance.json`, with its test or procedure in
[validation-plan.md](validation-plan.md).

## Compatibility

Additive. The registry schema identifier stays `agent-braid-plugin-registry/v0.2`;
a registry that stores `lightning: "lab"` is refused by earlier plugin versions
(effects line and migration note). No existing output changes.
