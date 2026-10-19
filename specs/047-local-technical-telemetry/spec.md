# SPEC-047: Local technical telemetry

**Milestone:** M4.5 — AI tooling integrations for Codex and Claude Code

**Status:** implementation integration candidate; [existing b2cf Luna review](integration-review.md) completed; integration-delta review/validation, operational admission and final acceptance remain separate.

[Canonical owner decisions D17/D18/D10](../046-local-technical-telemetry/owner-decisions-20261016.md) record documentary approval, pilot **NO-GO**, and deferred final acceptance. T017/T018/T010 stay open; the original authorities and frozen evidence are not rebound.

[Identity reconciliation from b13737ed4584](identity-reconciliation-b13737ed4584.md) preserves published plugin IDs and historical telemetry evidence.

## Purpose and scope

Implement explicit default-off local telemetry at the portable MCP tool boundary and the `analyze` / `analyze-git` CLI boundaries. Local SQLite and manual export use only the Python standard library. No automatic upload, network service, paid setting, host/provider launch, training data admission or experiment execution is authorized.

## Authorities

Constitution clause zero and Articles 5, 7, 12–15, 19–21; GOVERNANCE.md; operational semantics; claim discipline; ADRs 0007/0008/0013/0019/0020 and proposed ADR 0025. Historical M4 limits and accepted SPEC-039/040/042 scopes remain intact.

## Requirements and scenarios

### REQ-001: Consent and privacy

Default off; explicit local consent; collect only closed numeric aggregates, never content or identity.

**SC-001:** Given the bounded synthetic fixtures in the validation plan, when `procedure_privacy` runs, then the requirement passes its positive and refusal controls with actual evidence and stated limits.

Verification: [validation plan](validation-plan.md); [assurance](assurance.json).

### REQ-002: Aggregate reliability, performance and outcomes

Count each covered boundary once; coarse duration histogram and four fixed analyzer classification totals with missing coverage explicit.

**SC-002:** Given the bounded synthetic fixtures in the validation plan, when `procedure_aggregation` runs, then the requirement passes its positive and refusal controls with actual evidence and stated limits.

Verification: [validation plan](validation-plan.md); [assurance](assurance.json).

### REQ-003: Private bounded local storage

Transactional SQLite outside repositories, private permissions, 30 UTC-day retention and at most 10 MiB including auxiliary files; no daemon.

**SC-003:** Given the bounded synthetic fixtures in the validation plan, when `procedure_storage` runs, then the requirement passes its positive and refusal controls with actual evidence and stated limits.

Verification: [validation plan](validation-plan.md); [assurance](assurance.json).

### REQ-004: MCP integration

Instrument ToolingService.invoke once, without changing tools, permissions, envelopes or runtime authority.

**SC-004:** Given the bounded synthetic fixtures in the validation plan, when `procedure_mcp` runs, then the requirement passes its positive and refusal controls with actual evidence and stated limits.

Verification: [validation plan](validation-plan.md); [assurance](assurance.json).

### REQ-005: CLI integration

Instrument analyze and analyze-git once, retaining their output and exit contracts, including failed input and cancellation.

**SC-005:** Given the bounded synthetic fixtures in the validation plan, when `procedure_cli` runs, then the requirement passes its positive and refusal controls with actual evidence and stated limits.

Verification: [validation plan](validation-plan.md); [assurance](assurance.json).

### REQ-006: Installation consent and diagnosis

Expose off|local in serve and previewed lifecycle configuration, receipts and read-only diagnosis; skills never enable telemetry.

**SC-006:** Given the bounded synthetic fixtures in the validation plan, when `procedure_installation` runs, then the requirement passes its positive and refusal controls with actual evidence and stated limits.

Verification: [validation plan](validation-plan.md); [assurance](assurance.json).

### REQ-007: Report, export, merge and purge

Provide text/JSON reports and strict, bounded manual incremental batches; deduplicate batches without a persistent installation ID; distinguish purge from uninstall.

**SC-007:** Given the bounded synthetic fixtures in the validation plan, when `procedure_exchange` runs, then the requirement passes its positive and refusal controls with actual evidence and stated limits.

Verification: [validation plan](validation-plan.md); [assurance](assurance.json).

### REQ-008: Noninterference and evidence boundaries

Collector faults never change product behavior; measure overhead and expose known/unknown loss; product aggregates do not satisfy native, experimental or acceptance gates.

**SC-008:** Given the bounded synthetic fixtures in the validation plan, when `procedure_noninterference` runs, then the requirement passes its positive and refusal controls with actual evidence and stated limits.

Verification: [validation plan](validation-plan.md); [assurance](assurance.json).

## Exclusions and candidate identity

No telemetry in core algorithms, the legacy `mcp_runtime` endpoint, resource/prompt discovery, forecasts, host SDKs or skills. No per-event record, sub-day timestamps, requests, results, free exceptions, paths, URLs, names, commits, credentials or repository/user/team IDs or hashes. Aggregates are not an anonymity guarantee. Synthetic controls are engineering evidence only. The historical `482fbcc96227769f08768e79bc4d7f47d3445c4e` candidate and SPEC-044/T004 closure keep their identity and scope. The new candidate requires separate SPEC-044/T018 admission before a future pilot.
