# SPEC-046 implementation plan

## Technical context and scope

Python stdlib registry/CLI, pinned optional mcp==2.3.0, included CPython 3.12.15+20261013 for macOS arm64/Linux x86_64. Native plugin managers own package files; no first-run dependency downloads.

## Constitution check before research

Articles 5–6/12 require declared bounded configuration effects and isolation; 13–16 require evidence and transport-neutral core; 19–20/23–25 require useful engineering without scientific overclaim. No MUST contradiction or SHOULD deviation is proposed.

## Research, assumptions and alternatives

See research.md. Existing host and Git executables are prerequisites. Runtime provisioning and official eligibility are separate from provider sessions.

## Design and compatibility

Add plugin registry/discovery/CLI/router modules, package builder and installer. Snapshot explicit roots per MCP connection, namespace resources, delegate to existing services. Preserve legacy endpoints and the exact five-skill contract; setup is an additional plugin-only skill. Atomic preview/digest apply and owner receipts protect registration/migration.

## Validation strategy

Requirements/scenarios/tasks map in assurance.json. Test registry and router in owned fixtures, build both platform packages, validate relocated offline installation, then separately observe native hosts. Quick/PR gates do not replace those observations.

## Constitution check after design

No source promotion, arbitrary repository code, grants, cloud endpoint or provider launch is added. Setup is not execution authority.

## Human review and unresolved decisions

Owner approved implementation scope. ADR/capability adoption, provider candidacies and public release remain separate. Record blockers and actual outcomes without marking unfinished tasks complete.


External approvals are tracked as T014 (OpenAI) and T015 (Anthropic), separate
from the documentary T011/T012 acceptance. This implements the approved separation
between preparation and provider approval. The owner-added shell entrypoint is
T013. The extension therefore has 15 stable task IDs; no historical task is reused.

## T018 proposal: telemetry of stale-connection refusals (owner decision required)

Inspection (2026-10-24). The SPEC-047 collector (`tooling_telemetry.observe` / `Store.record`) is wrapped only inside `ToolingService.invoke`. `PluginRouter.invoke` produces its refusals before delegating: reconnect-required (`RegistryStale`), unknown or missing `workspaceId`, non-object or oversized arguments, busy global admission and a full plugin inventory. None reach the service, so with consent `local` they write no cell at all. A throwaway probe confirmed it: after a registry rewrite, a stale call, an unknown-workspace call and a malformed-argument call all return `refused` and `Store.report()` stays empty. This matches the documented coverage statement in `docs/tooling/TELEMETRY.md` ("Protocol/schema refusals that never reach the service invocation are outside coverage"). Refusals produced inside the service (invalid call shape, per-service concurrency, per-service inventory) are counted as `refused`.

Consequence. Today stale-connection refusals are not counted as usage failures: the stated T018 goal holds by omission. What is missing is a recorded *cause*. The collector's data contract (`surface` cli|mcp; `outcome` ok|refused|error|cancelled|unknown; numeric aggregates only) offers no value that expresses it:

- Counting the stale refusal as `refused` would conflate it with real usage refusals, the opposite of the goal.
- Counting it as `unknown` or `error` is misleading and equally a usage-failure signal.
- A distinct cause therefore needs a new versioned value (for example outcome `reconnect-required`), which changes the SPEC-047 data contract (`agent-braid-local-telemetry-batch/v1` enums, stored cell validation, batch import/export compatibility, `user_version`). Per the task and the owner rule, this is not implemented without approval.

Options for the owner:

1. **A, no contract change (recommended default).** Keep router-level refusals uncounted, pin the behavior with a test (consent `local` and `off` both write nothing for a stale refusal) and state it in `TELEMETRY.md` and the plugin contract. T018 then reads "stale refusals are excluded from usage failures"; the refusal cause is not recorded.
2. **B, new category value.** Add one outcome value `reconnect-required` (surface `mcp`, operation of the called tool), version it as telemetry schema `v2` with an importer that accepts `v1` and `v2`, count only the reconnect-required refusal in the router (other router-level refusals stay uncounted unless separately decided), and add tests for consent `local` (one cell, no content or identity) and `off` (nothing written).

No code is changed by this proposal. T018 stays open until the owner chooses; T019 documents the reconnect behavior that already exists and states the telemetry coverage as it is today.

