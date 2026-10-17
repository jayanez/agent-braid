# Native plugin release acceptance — alpha.2

The `0.1.0-alpha.2` package was built from clean source commit
`1cea4fa` and reproduced from distribution commit
`a47919d` in a fresh Git checkout. The previous alpha.1 controls remain
historical engineering observations; they do not describe the corrected package.
Exact input, package and transcript hashes are in
[evidence/release-alpha2.json](evidence/release-alpha2.json).

## Obtained observations

| Check | macOS arm64 | Linux x86_64 |
| --- | --- | --- |
| Codex native installation, six skills, MCP startup, installed inventory | Passed | Passed in emulated container |
| Claude Code native installation, MCP startup, installed inventory | Passed | Passed in emulated container |
| Real alpha.1 → alpha.2 update in the same host profiles and marketplace | Passed for both hosts | Passed for both hosts in emulated container |
| Registry and result bytes retained through update and uninstall | Passed for both hosts | Passed for both hosts in emulated container |
| Authenticated Codex setup and product-skill interaction | Passed | Not observed |
| Authenticated Claude Code setup and product-skill interaction | Blocked by expired native login | Not observed |

The Codex interaction used the installed `setup` skill, checked package integrity,
suggested only the current repository without scanning, and cancelled without
writing configuration. A subsequent explicitly authorized depth-2/100-entry scan
found two owned fixture repositories. Registration applied only after confirmation
of its exact preview digest. The old MCP connection reported reconnection required;
a new native connection loaded both IDs. The installed analyze skill then called
`analyze-work` for each workspace and read a returned evidence descriptor through
MCP. Both analyses returned `ok` with separate workspace evidence. Runtime stayed
disabled and no operator grant was issued. This was an agent-operated interaction,
not a human usability rating or scientific acceptance.

The native versions were Codex `0.163.0-alpha.10.2` and Claude Code `2.1.292`.
The successful Codex interaction used the existing ChatGPT subscription and native
default model `gpt-6.1-sol`. The Claude interactive session rejected the setup
request with `Login expired · Please run /login`. Its credential-status boolean
was not accepted as a substitute for an actual successful request. No paid/API
fallback was used. The owner must renew the native login before that journey can
continue.

## Defect found and corrected

Actual Codex installation omitted CPython runtime symlinks. Alpha.1's complete
inventory correctly refused that cache; the earlier build-directory doctor and
MCP startup alone had not exposed the omission. Alpha.2 validates all alias targets
before changing any file, requires contained regular-file targets, and copies their
bytes and executable modes before generating the inventory. The strict inventory
and authority checks remain intact. Both installed caches now verify. The update
record explicitly retains the unhealthy alpha.1 Codex baseline.

The version-transition tests kept the same isolated user homes, host profiles,
marketplace path and plugin ID. They verified alpha.1 before updating the local
marketplace to alpha.2, invoked native Codex add and Claude update, verified the
new installed version/cache, and compared registry/result bytes before and after
update and uninstall. These tests establish a real version change from a local
directory marketplace; they do not claim a remote Git refresh or public installer
observation. Failed harness attempts are retained privately with their diagnostic
records; they do not count as successful observations.

## Publication boundary

The owner authorized own-marketplace publication on the condition that both
interactive journeys and the update pass. The update and Codex journey have
passed; Claude's expired login leaves that condition unsatisfied. No public
`plugin-dist` branch or release tag has been pushed. The README's remote curl
installation therefore remains pending publication and a subsequent clean remote
installation check. Local candidate installation remains available.

Official OpenAI/Anthropic eligibility, size/executable exceptions, submissions and
approvals stay in T014/T015. Historical M4.5 attempts, human ratings, ADR adoption,
scientific interpretation and final milestone acceptance are unchanged. Linux
records describe native binaries inside a network-disabled emulated container,
not physical Linux or interactive subscription acceptance.
