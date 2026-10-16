# Agent Braid native plugin distribution candidate

Unpublished engineering candidate. Public distribution requires the founder's
release decision. This branch contains the generated catalogs, bundled runtimes,
license/provenance inventories and corresponding sources. Source development is
on `develop`; inspect `plugins/agent-braid/provenance.json` for the exact candidate.

For a local checkout, use its absolute path as the marketplace source:

```sh
codex plugin marketplace add /absolute/marketplace
codex plugin add agent-braid@agent-braid
claude plugin install agent-braid --marketplace /absolute/marketplace --scope user
```

Open Agent Braid setup, explicitly select repositories, inspect/apply its preview
and reconnect MCP. Git and a supported local host are required; Python and package
managers are included. macOS arm64 and Linux x86_64 are the packaged targets.
The five product skills and separate setup skill are discovered by the host.

Native plugin managers own updates/removal; private Agent Braid state survives.
Official directory approvals and interactive acceptance are separate pending gates.
See `plugins/agent-braid/README.md`, its LICENSE/NOTICE and source installation guide.
