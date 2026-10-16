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
