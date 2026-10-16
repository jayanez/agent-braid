# ADR 0024: Native user-scoped AI plugins

- **Status:** Proposed; owner authorized implementation of the plan on 2026-10-16. This is not capability acceptance or publication approval.
- **Date:** 2026-10-16
- **Articles:** 0, 5, 6, 12–16, 19, 20, 23–25

## Context

M4.5 has bounded package/lifecycle acceptance but native plugin discovery and user onboarding need their own evidence. Manual Python setup creates avoidable installation work. A globally installed plugin must not acquire unrestricted repository access.

## Decision proposal

Ship one plugin with portable/OpenAI and Claude manifests, the unchanged five product skills and separately inventoried setup instructions. Include pinned relocatable CPython and tooling wheels; preserve real interpreter/subprocess behavior rather than modifying frozen Git runners for a frozen executable. Runtime dependencies are resolved at build time only. Native host managers own plugin files; a private shared user registry owns workspace bindings and survives cache replacement.

The separate plugin MCP contract adds workspace selection around fixed-root ToolingService instances. Each connection snapshots its bindings; calls require workspaceId and cannot change roots. Resources are namespaced per workspace. Registration changes require reconnecting; execution still needs explicit operator enablement and existing exact grants. No installation/session hooks or provider prompts ship.

A POSIX install.sh is an alternative frontend to native user-scoped managers, not a second Python installer. Repository discovery is read-only, bounded and opt-in beyond current/registered paths.

## Alternatives and consequences

uvx/pipx require another user prerequisite; frozen Python executables change sys.executable semantics used by current runners; a remote MCP changes privacy, transport and execution scope. None is adopted. Bundled runtimes cost download/storage and require per-platform conformance, provenance and license inventories. Directory size/binary policies can block candidacy independently of engineering delivery.

## Compatibility and review

Legacy CLI/MCP/wheel contracts and historical snapshots remain unchanged. SPEC-046 is additive; SPEC-039/040/042 acceptance is not widened. No constitutional amendment is proposed. Luna technical review, real-host observations, founder acceptance and public release retain separate records.
