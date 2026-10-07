# Installation and lifecycle proposal

Future CLI: `agent-braid tooling` with `serve`, `configure`, `install`,
`doctor`, `update` and `uninstall`. Exact flags are adopted with the API PR.
Examples in this planning packet are prospective, not available commands.

## Scope and ownership

Install the package and optional tooling dependencies into an isolated user-owned
environment. Package wheel/sdist include canonical skills and host metadata;
runtime resolution uses installed package resources, never a checkout-relative
path. Record artifact hashes, SDK/transitive dependency inventory and licenses.
No global pip modification, repo-local dependency clutter or implicit provider use.

User installation makes tools/skills reusable across repositories. Configuration
still binds each server to an explicit source/result root. A project installation
requires opt-in and names its owned project files. Host config scopes are adapted
to their actual version; do not assume Claude local/project/user are equivalent
to Codex scopes. Respect CODEX_HOME and existing host conventions.

## Configuration transaction

Default operation emits a preview of exact destination, server name, executable
and args, scope, roots, enabled tools and changes. Apply only the user-selected
operation. Use a destination inventory, content hashes, backup, atomic replacement
and a receipt; preserve unrelated keys/comments/skills where supported. Existing
unknown or concurrently edited targets refuse. No shell interpolation of paths,
silent wildcard root access, approval-policy edits, secrets or absolute personal
paths in distributable manifests.

Idempotent repeat install makes no extra entries. Name collisions and user edits
require a concrete diff; no silent overwrite. Update removes/replaces only bytes
owned by the receipt, verifies the new bundle/version and preserves user changes.
Uninstall removes only matching owned entries; modified/shared data remains with
an explicit unresolved report. Configuration changes do not create runtime grants.

## Doctor

Report separate results for executable resolution, Python/package/SDK versions,
asset integrity, selected host version, config scope, root permissions, stdio
discovery, schema/version support, analysis availability and runtime enablement.
Missing host authentication or an interactive approval is `blocked`/`pending`,
not green. Doctor never calls execute/recover, obtains a grant or starts a paid
session. Actual host health requires the later observation receipt.

## Host adapters and portability

Use each official host's supported configuration operation or a conservative
parser preserving untouched bytes. Test spaces/unicode paths, relocated package,
empty/malformed configs, collisions, interrupted apply, unavailable host, repeat
install/update/remove, two source roots and clean core install without the extra.
Initial lifecycle platform macOS arm64; Linux x86_64 package/protocol reproduction.
Remote executors, containers and cloud hosts need separate installation.
