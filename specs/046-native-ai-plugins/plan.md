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

## T018 decision: reconnect-required refusals stay uncounted (owner decision A, 2026-10-24)

Inspection. The SPEC-047 collector (`tooling_telemetry.observe` / `Store.record`) is wrapped only inside `ToolingService.invoke`. `PluginRouter.invoke` refuses before delegating: reconnect-required (`RegistryStale`), unknown or missing `workspaceId`, non-object or oversized arguments, busy global admission and a full plugin inventory. None reach the service, so with consent `local` they write no cell. This matches `docs/tooling/TELEMETRY.md` ("Protocol/schema refusals that never reach the service invocation are outside coverage"). Refusals produced inside the service (invalid call shape, per-service concurrency, per-service inventory) are counted as `refused`.

Decision A (adopted). Router-level refusals, including reconnect-required, are not counted. Stale-connection refusals therefore never appear as usage failures. The SPEC-047 data contract is unchanged: no new outcome value, no schema v2. The refusal cause is deliberately not recorded. The behavior is pinned by `tests/test_plugin_mcp.py` (`test_router_refusals_write_no_telemetry_cell_with_consent_local`, `..._with_consent_off`, with the control `test_refusal_pin_can_fail_because_service_calls_are_counted`), so a refactor that starts counting router refusals fails.

Rejected alternative B. A new outcome value `reconnect-required` under telemetry schema v2 (importer accepting v1 and v2). Rejected because it changes the SPEC-047 data contract for a cause that is already excluded from usage failures. Reconsider only if the owner needs an aggregate count of stale-connection refusals (for example to measure how often setup changes strand running sessions); that would be a new owner-approved contract change, not part of T016-T019.

T018 stays open until the installed/native procedure_003 rerun is recorded, like T016/T017.
