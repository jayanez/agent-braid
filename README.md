# Agent Braid plugin marketplace

This versioned distribution includes the Agent Braid runtime and skills for Codex
and Claude Code on macOS arm64 and Linux x86_64. Install once per user in each
host, then explicitly select repositories through setup. Git and the selected
native host are prerequisites; Python, pip, uv, Node and Docker are not required.

```sh
codex plugin marketplace add https://github.com/jayanez/agent-braid.git --ref plugin-dist
codex plugin add agent-braid@agent-braid
```

```sh
claude plugin install agent-braid \
  --marketplace 'https://github.com/jayanez/agent-braid.git#plugin-dist' --scope user
```

Or use the [source installer](https://github.com/jayanez/agent-braid/blob/develop/install.sh):

```sh
curl -fsSL https://raw.githubusercontent.com/jayanez/agent-braid/develop/install.sh \
  | sh -s -- --host both
```

Open Agent Braid setup, select repositories, inspect and apply the exact preview,
and reconnect MCP. Availability across repositories does not grant unrestricted
filesystem access. Analysis is the default; setup does not issue execution grants
or start provider sessions. Native managers own updates and removal; private
configuration/results live outside their plugin caches.

This is a research-alpha engineering package. See the [plugin documentation](plugins/agent-braid/README.md),
[provenance](plugins/agent-braid/provenance.json),
[complete file inventory](plugins/agent-braid/package-inventory.json),
[corresponding source](sources/) and [licenses](plugins/agent-braid/LICENSES/).
Software/executable material is AGPL-3.0-only; documentation/skill instructions are
CC-BY-SA-4.0; bundled dependencies retain their included licenses. Inventory
verification is not publisher authentication, scientific acceptance or official
directory approval.

[Full installation guide](https://github.com/jayanez/agent-braid/blob/develop/docs/tooling/NATIVE_PLUGINS.md)
· [Support](https://github.com/jayanez/agent-braid/issues)
