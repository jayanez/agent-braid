# SPEC-068: OpenCode native integration

**Milestone:** M4.7 — AI tooling integration for OpenCode (proposed; not created)

**Status:** specification only, draft. Nothing is implemented or authorized by
this change. Owner decisions D1 to D11 of 2026-11-02 and 2026-11-03 are recorded
under Clarifications; they authorize no implementation, release or remote tracking.

## Purpose and scope

Bring Agent Braid into OpenCode at parity with the Codex and Claude Code
integration delivered under M4.5: a native user plugin with the bundled runtime,
the `agent-braid-plugin/v0.2` MCP surface, the six product skills, guided setup,
lifecycle operations, the shell installer and a receipt-owned Python fallback
profile. This is engineering, not a research protocol.

This specification opens the "Additional development environments" route of
[SPEC-039 program](../039-ai-tooling-program/program.md#five-future-routes) for
OpenCode only. Its entry requirement (host capability/permission matrix, new
adapter observations, lifecycle controls) is REQ-002, REQ-006 and REQ-012 here.
M4.5 stays closed; its NO-GO records, acceptance limits and historical claims are
not reopened or widened. SPEC-039 REQ-007 deferred OpenCode from v1; this is a
new, additive feature.

Exclusions:

- Claude-only surfaces: dynamic workflows and orchestration guard (SPEC-052 to
  SPEC-059).
- Harness evaluation, attempt corpora and native harness backends (SPEC-044,
  SPEC-049, SPEC-050, SPEC-065).
- Any change to Codex or Claude Code artifacts, contracts or behaviour, other
  than the shared `install.sh --host all` selection that already exists.
- New Agent Braid authority: host permissions, tool approvals or plugin hooks
  never become operator grants.
- Other hosts of the same route (Cursor, VS Code/Copilot, pi).

## Authorities

Constitution clause zero and Articles 0, 5, 6, 12–16, 19, 20 and 23–25;
[GOVERNANCE.md](../../GOVERNANCE.md);
[claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
ADR 0021 (Codex/Claude tooling integration), ADR 0024 (native AI plugins),
ADR 0030 (native plugin surface naming), ADR 0031 (portable prompt names);
precedents [SPEC-039](../039-ai-tooling-program/spec.md),
[SPEC-042](../042-ai-tooling-packaging/spec.md),
[SPEC-046](../046-native-ai-plugins/spec.md),
[SPEC-047](../047-local-technical-telemetry/spec.md),
[SPEC-054](../054-plugin-surface-naming/spec.md),
[SPEC-060](../060-portable-prompt-names/spec.md) and
[SPEC-066](../066-system-one-shadow/spec.md).
A new ADR 0037 records the OpenCode surface (REQ-001).

## Clarifications

Owner decisions, 2026-11-02:

- **D1** New SPEC-068 under proposed milestone M4.7; M4.5 is not reopened.
- **D2** OpenCode skills keep the unprefixed product names (`analyze`, `plan`,
  `evidence`, `execute`, `recover`, `setup`) as in Codex and Claude Code. OpenCode
  does not namespace plugin skills and silently prefers the higher-precedence skill
  of the same name, so collision detection and a warning are mandatory (REQ-004).
- **D3** Distribution reuses the Git `plugin-dist` artifact with the bundled
  runtime. If OpenCode's Git install does not preserve executable bits, bytes,
  `.gitattributes` handling or the artifact size limit (REQ-002), work stops and
  returns to the owner; an npm channel is not implemented without a new decision.
- **D4** The Python `agent-braid tooling install` route is frozen as the fallback
  for platforms without a bundled runtime and for source users, with no contract
  change for Codex or Claude Code, and gains an `opencode` profile (REQ-008).
- **D5** The README presents native installation per platform as the preferred
  quick start; OpenCode is added there when REQ-007 lands.
- **D6** Spec Kit work runs in an independent clean clone.

Owner decisions, 2026-11-03 (`speckit-clarify`; facts checked against the
OpenCode 2.1.2 documentation and the 2.1.4 CLI):

- **D7 (OD-4)** The `agent-braid` MCP server entry sets `codemode: false`, so
  OpenCode lists the tools directly as `agent-braid_<tool>`, matching how the
  skills and the other hosts call them. Host permissions apply per tool either
  way; reverting is one configuration value.
- **D8 (OD-5)** The server entry keeps the host default `protocol: legacy`
  (revisions up to 2025-11-25), which the existing server already speaks; `auto`
  is not used because it starts an extra probe process on every launch.
- **D9 (OD-6)** The native plugin is user-global (`opencode plugin add` writes
  only the global configuration). The legacy profile supports global and project
  scopes, as SPEC-042 does for the other hosts.
- **D10 (OD-7)** The portable server `agent-braid-tooling/v0.2` and its prompts
  reach OpenCode only through the legacy profile, where OpenCode shows them as
  `<server>:<prompt>` commands. The native plugin publishes no MCP prompts.
- **D11 (OD-8)** The first package that includes OpenCode is
  `0.1.0-alpha.6`; the release itself remains a separate owner decision (T011).

## Requirements and acceptance scenarios

### REQ-001 — Specification and architecture

Describe the OpenCode surface, its boundaries and its relation to ADR 0024 and
ADR 0030 in ADR 0037 and an interface contract.

**SC-001:** Given this specification, ADR 0037 and the OpenCode surface contract,
when they are analyzed against ADR 0024, ADR 0030 and the SPEC-046/054 contracts,
then requirements, tasks and procedures agree, existing contracts are unchanged,
and the native-observation and owner gates are explicit.

Verification: [procedure_001](validation-plan.md); T001.

### REQ-002 — Host capability and permission matrix

Record, for the installed OpenCode version, how plugins, MCP servers, skills,
commands, permissions, configuration scopes, reload and Git plugin installation
actually behave, observed in a disposable profile without touching user
configuration.

**SC-002:** Given OpenCode in a disposable profile, when the matrix procedures run,
then each row records the observed behaviour, version, command and limits;
unobserved rows stay `unobserved`; the Git-install row states whether executable
bits, line endings and artifact size survive, and a failure stops D3.

Verification: [procedure_002](validation-plan.md); T002.

### REQ-003 — Native plugin with MCP from the bundled runtime

Ship an OpenCode plugin package that registers the existing
`agent-braid-plugin/v0.2` MCP server (`plugin serve`) through the bundled runtime
launcher as a user-global `local` server with `codemode: false` and the default
`legacy` protocol (D7 to D9), with no change to the server contract.

**SC-003:** Given a built OpenCode package and two registered analysis-only
workspaces, when an MCP client starts the server with the command the OpenCode
entry registers (stdio fixture; the real host under REQ-012) and calls
`workspaces` and `analyze-work` with explicit workspace IDs, then core report values equal the
Codex/Claude results for the same input; unknown IDs, arbitrary roots and
execution without an operator grant refuse.

Verification: [procedure_003](validation-plan.md); T003, T004, T010.

### REQ-004 — Skills, commands and collision warning

Expose the six product skills from the canonical sources without duplicated
text, plus explicit `setup` and reconnect commands. Detect a same-named skill of
higher precedence and warn.

**SC-004:** Given the installed plugin, when OpenCode lists skills and commands,
then the six skills and two commands appear with canonical text; given a
higher-precedence skill named `analyze`, `plugin doctor` reports the collision and
the skill it shadows; no skill, command or hook issues a grant.

Verification: [procedure_004](validation-plan.md); T005.

### REQ-005 — Setup, workspaces and explicit reconnection

Reuse the existing setup wizard and workspace registry. Registry changes keep
the `reconnect-required` semantics: the plugin never reloads MCP automatically;
the operator runs the reconnect command.

**SC-005:** Given a configured plugin, when a workspace is added through setup,
then status reports `reconnectRequired: true` until the reconnect command runs,
and no automatic reload occurs.

Verification: [procedure_005](validation-plan.md); T005.

### REQ-006 — Native lifecycle and legacy migration

Support install, update and removal through OpenCode's plugin manager and the
existing `plugin legacy` migration from a receipt-owned installation.

**SC-006:** Given a public tag, when the plugin is installed, updated to a newer
tag and removed, then each step leaves the documented state; removal leaves user
configuration outside owned entries intact; migration from a legacy receipt
removes only owned entries.

Verification: [procedure_006](validation-plan.md); T006, T007, T010.

### REQ-007 — Shell installer

Add `opencode` to `install.sh --host` and include it in `--host all`. The script
only calls OpenCode's native plugin manager; no sudo and no Python.

**SC-007:** Given fake host executables, when `install.sh` runs with `--host
opencode`, `--host all` and `--dry-run`, then the expected native commands are
printed or run, absent hosts are skipped with a notice under `all`, and an absent
OpenCode refuses under `--host opencode`; Codex and Claude behaviour is unchanged.

Verification: [procedure_007](validation-plan.md); T006.

### REQ-008 — Legacy profile `tooling install --host opencode`

Add an `opencode` host profile to the receipt-owned lifecycle: global and
project `opencode.json`/`opencode.jsonc`, atomic JSONC edits that preserve
foreign keys and comments, preview digest, scope lock, rollback, receipts,
`update`, `uninstall` and `doctor`, reusing the existing lifecycle engine.

**SC-008:** Given an isolated destination with a JSONC config containing comments
and foreign servers, when preview, apply, repeat, update and uninstall run, then
only the owned entry and skills change, comments and foreign bytes are preserved,
repeat runs are idempotent, changed digests and unowned collisions refuse, and a
failed write rolls back.

Verification: [procedure_008](validation-plan.md); T007.

### REQ-009 — Telemetry, System One and session identifiers

Keep SPEC-047 telemetry and SPEC-066 System One contracts unchanged. OpenCode's
per-call session identifier in `_meta` is never stored, exported or used for
authorization.

**SC-009:** Given telemetry `local` and System One `shadow`, when OpenCode calls
`analyze-work` with a session identifier in `_meta`, then envelopes are
byte-identical to a call without it, and no stored artifact contains the
identifier.

Verification: [procedure_009](validation-plan.md); T008.

### REQ-010 — Distribution and provenance

Build the OpenCode package from the same source commit and runtime as the other
hosts, with package-name checks, provenance and inventory entries.

**SC-010:** Given a clean source commit, when the native build runs, then the
OpenCode package, its inventory and provenance are emitted, package-name checks
pass, and Codex/Claude artifacts are byte-identical to a build without the
OpenCode target.

Verification: [procedure_010](validation-plan.md); T004, T008.

### REQ-011 — Documentation

Update user and contributor documentation in English where OpenCode changes
what readers do, and mark the Python route as the frozen fallback.

**SC-011:** Given the candidate, when documentation checks and a manual review
run, then README quick start, native plugin, install, skills, hosts, privacy and
Spec Kit journey documents describe OpenCode consistently, links resolve, and no
document claims an unobserved behaviour.

Verification: [procedure_011](validation-plan.md); T009.

### REQ-012 — Native observation gate

Observe the candidate in a clean OpenCode profile as a separate gate. Passing
checks do not substitute for it.

**SC-012:** Given a frozen candidate, when the owner or an operator runs the
observation procedure in a clean profile, then plugin install, skill listing,
`analyze-work`, reconnect and removal are recorded with versions and limits, and
unobserved items remain open.

Verification: [procedure_012](validation-plan.md); T010.

## Scientific boundaries and compatibility

Engineering only; no hypothesis and no scientific claim. Results describe the
observed OpenCode version and platforms; macOS arm64 and Linux x86_64 are
targets, not compatibility claims, until REQ-012 records them. Additive: the
`agent-braid-plugin/v0.2` and `agent-braid-tooling/v0.2` contracts, Codex and
Claude Code packages, ADR 0030 naming and SPEC-042 receipts are unchanged.
Host permissions are host approvals, not Agent Braid grants; grants stay outside
every tool, skill, command and hook (ADR 0024).

## Evidence and unresolved questions

Planned evidence is in `assurance.json`; obtained evidence is empty. Open
questions OD-4 to OD-8 were decided on 2026-11-03 (see Clarifications). Plan
decisions OD-9 (how SC-010 measures Codex/Claude artifact identity) and OD-10
(default legacy server name for OpenCode) are open in [plan.md](plan.md). New
questions found by REQ-002 return to the owner.

Native observation, human review and founder approval are separate gates; no
green check implies them.
