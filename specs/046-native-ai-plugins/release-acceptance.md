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
| Authenticated Claude Code setup and product-skill interaction | Passed after native login renewal | Not observed |
| Public README curl install, both native managers/cache/MCP | Passed | Passed in network-enabled emulated container |

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
Both interactions used native authentication. Claude initially refused with
`Login expired · Please run /login`; that failed observation remains in
`evidence/claude-interactive-auth-blocker.json`. Native login renewal succeeded,
and actual subsequent completed requests established authentication. No paid/API
fallback was used.

Claude's installed setup skill checked the bundled doctor, suggested the current
repository without a scan, then performed the explicit bounded project scan.
Both repositories were registered only after confirmation of the exact preview
digest. The old connection retained empty bindings and reported reconnection
required. A fresh native process loaded both IDs; the installed analyze skill
returned `ok` for both, read a workspace evidence descriptor and chunk through
MCP, and verified the decoded 1,732-byte payload hash. Native local-directory
Claude execution used its `readFromFolder` package; the installed cache was
verified separately. Native manual permission mode approved only the displayed
owned operations once. See `evidence/claude-interactive-alpha2.json`.

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

## Published own marketplace

After both interactive journeys and the version-changing update passed, the
owner's conditional authorization was satisfied. The reviewed distribution was
published atomically as `plugin-dist` and annotated tag
`agent-braid--v0.1.0-alpha.2`, both resolving to
`6649c73d088799201bf9ab6e030f258e346e8062`. Its only difference from reproduced
`a47919d` is the root distribution README; package/source payload bytes are unchanged.

A fresh public Git clone matched every inventory entry, including sizes, hashes
and executable flags: 7,737 regular files, 390,788,156 bytes, no missing or extra
package files. The literal README `curl … | sh -s -- --host both` succeeded in
fresh user homes and both host profiles on macOS and emulated Linux. Both actual
installed caches verified; native Codex loaded six skills and configured MCP
tools, and native Claude reported Connected. The PATH exposed native hosts plus
shell/Git/curl utilities, with no Python or external environment manager. Public
installation uses network access to GitHub; the earlier protocol/container
controls were network-disabled. Initial harness failures from missing Git
ancillary shell utilities and absent test-image curl remain private failed
attempts, never passing product observations. See `evidence/publication-alpha2.json`.

Official OpenAI/Anthropic eligibility, size/executable exceptions, submissions and
approvals stay in T014/T015. Historical M4.5 attempts, human ratings, ADR adoption,
scientific interpretation and final milestone acceptance are unchanged. Linux
records describe native binaries inside emulation, not physical Linux or
interactive subscription acceptance. Only owned test workspace registrations
were removed after closing native sessions; source and results were preserved.
