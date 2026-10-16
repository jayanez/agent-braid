# Plugin interface v0.1

`agent-braid plugin setup|discover|doctor|workspaces|serve` is additive. Setup accepts repeated source roots, previews exact user-registry/results effects and requires apply plus the matching preview digest. Removal changes only registration. Both hosts share AGENT_BRAID_HOME.

The MCP schema is agent-braid-plugin/v0.1. plugin-status and workspaces are read-only bootstrap tools. Delegated tooling calls require workspaceId; no caller root override is allowed. Each connection snapshots fixed-root services; changes require reconnect. Runtime tools exist only with explicit operator configuration and retain exact grants. Resources use agent-braid-plugin://<workspaceId>/... and remain service-owned. Core results are not rewritten.

Native managers own plugin files. Receipt-owned legacy uninstall remains the explicit migration mechanism. install.sh only invokes native managers at user scope, with explicit host/marketplace/ref and no sudo, Python provisioning or provider session.
