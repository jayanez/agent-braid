# Agent Braid native plugin — unpublished candidate

This distribution branch descends from the source history. The generated plugin
contains both supported runtimes, both host catalogs, five canonical product
skills plus setup, dependency/license inventories and corresponding sources.

Version: 0.1.0-alpha.1. Source candidate: 9641fd6. Public branch/tag publication
requires the founder decision; no official directory approval is claimed.
Use the absolute directory path as a local native marketplace until publication.

```sh
codex plugin marketplace add /absolute/marketplace
codex plugin add agent-braid@agent-braid
claude plugin install agent-braid --marketplace /absolute/marketplace --scope user
```

Open setup, select repositories, inspect/apply its digest and reconnect MCP.
Git and an existing supported host are required; no external Python/package
manager is needed. Targets: macOS arm64, Linux x86_64 with glibc 2.28+.

Private configuration/results survive native update/removal. See the packaged
README, LICENSE/NOTICE, provenance.json and package-inventory.json. Public source
and installation documentation live on develop. Actual interactive skill journeys,
version-changing native upgrade and directory eligibility/approval remain separate.
