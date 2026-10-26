# Host session adapters

This module prepares one-shot Codex CLI or Claude Code CLI invocations and
hands them to the bounded process supervisor. Preparation does not authorize a
provider, grant a tool, authenticate a route, or prove that a host accepted a
setting. The existing capture admission, authenticated start verifier, explicit
provider opt-in, caller-supplied route attestation, trusted fresh-cost/stop
observer, and outcome verifier remain mandatory. Only the existing session
coordinator may invoke the adapter; a prepared command is not permission to run.

No user prompt is placed on argv or in adapter receipts. It is provided to the
child through stdin and only its SHA-256 is reported. Environment mappings are
explicitly provided by the caller; environment values are never copied to
receipts. The adapter does not read ambient authentication, inspect keychains,
modify global configuration, or rewrite `HOME`/`CODEX_HOME`. Configuration
files are represented by path and content digest and rechecked immediately
before dispatch. Provider/model/network access is not exercised by tests.

## Arms and evidence

Arm A is a human-operated CLI baseline and is never launched by this adapter.
Arm B is configured for the registered MCP-only tool set. Arm C adds exactly
the five canonical Agent Braid skills from the frozen skill bundle. The C arm
requires caller-verified evidence that the native host loaded the expected
skill inventory; prompt injection that imitates skill text is not equivalent.
Codex skill catalog visibility alone does not establish that full skill
instructions were loaded. Claude's `Skill(name)` patterns approve individual skill calls; they are not
built-in availability names or runtime grants. `--allowedTools` is a host tool
approval mechanism rather than an availability allowlist. The adapter does not infer that any host setting successfully
isolates global instructions or disables a feature unless that is established
by a trusted session receipt.

Routes are explicit and supplied by the authenticated caller. Missing or
unknown route, missing model/effort, absent provider opt-in, unresolved
isolation evidence, stale configuration/binary identity, or missing required
attestation fails before handoff. This code does not create or refresh any of
those facts. A failed or ambiguous started attempt is never retried.
For a frozen subscription-only admission, the exact registration, account,
policy and slot binding is carried into the process supervisor. Its child
environment permits only `PATH`, `LANG`, `LC_ALL`, `TMPDIR` and
`CLAUDE_CONFIG_DIR`; provider keys, routing, proxy and loader overrides refuse.
This reduces configuration fallback paths; it does not authenticate the
selected native account. The preparation verifier must verify the effective
route and authentication, and the trusted supervisor observer must supply
fresh account, included-quota and paid-usage facts. See
[REGISTRATION.md](REGISTRATION.md) and [SUPERVISOR.md](SUPERVISOR.md).

## Portable server prompts

Portable server prompts (SPEC-060, ADR 0031; candidate under implementation, no
release exists yet): the surface contract `agent-braid-tooling/v0.2` names the
three MCP prompts `analyze`, `plan` and `evidence`; the host adds its own server
key as a prefix. Tool envelopes stay `agent-braid-tooling/v0.1`. The former names
`agent-braid-analyze`, `agent-braid-plan` and `agent-braid-evidence` remain as
DEPRECATED aliases with identical text for two releases and are removed only in
`agent-braid-tooling/v0.3`, after an owner decision and a repository search; if
the second release has not shipped within 180 days of the first, the owner records
a new decision. See the
[v0.2 delta](../../specs/060-portable-prompt-names/contracts/interface-delta.md)
and [ADR 0031](../adr/0031-portable-prompt-names.md).

Claude Code lists server prompts as `/<server key>:<prompt> (MCP)`; during the
alias window it shows both sets. Codex lists no MCP prompts before or after.

Key collision: do not register the portable server under the key `agent-braid`
next to the native plugin. Its unprefixed prompt `/agent-braid:analyze (MCP)` would
share a slash name with the plugin skill `/agent-braid:analyze`. Install one
surface, or choose another server key for the portable server. Codex lists no MCP
prompts, so this affects Claude Code only.

## CLI command profiles

The preparation profiles use the documented command surfaces reviewed on
2026-10-08 and 2026-10-09. Codex uses `exec --json --ephemeral --ignore-user-config
--sandbox read-only --model ... --cd ...` and an explicit medium reasoning
effort setting; its MCP/tool and skills configuration is supplied as explicit
TOML overrides and bound by a digest. Legacy non-subscription Claude uses
`--bare --strict-mcp-config --mcp-config
... --no-session-persistence --print --verbose --output-format stream-json
--model ... --effort medium`. The MCP-only Claude arm supplies an empty built-in
tool set and disables slash commands. The skills arm selects the five exact
built-in `Skill` tool and separately approves calls to the five exact
`Skill(name)` patterns; it does not disable slash commands. Both arms approve
their configured MCP server namespaces explicitly under `dontAsk`; names are
bounded literals to prevent permission-pattern injection. No command uses
permission bypass flags or puts the prompt on argv.

Subscription-bound Claude instead omits `--bare`: pinned Claude Code 2.1.286
documents bare mode as skipping keychain/OAuth and requiring `ANTHROPIC_API_KEY`
or `apiKeyHelper`, which this subscription profile forbids. It requires a
content-pinned per-invocation settings JSON with exactly
`forceLoginMethod: claudeai`, `fastMode: false`, `disableAllHooks: true`, and
`autoMemoryEnabled: false`; boolean settings require JSON booleans, and the
settings file is limited to 16 KiB. Credentials, helper commands, provider
overrides, duplicate keys, and extra settings are rejected. MCP and settings
argv paths use the canonical paths captured in their pins. The invocation requests `--restricted`, an
empty `--setting-sources` value, `--settings <pinned-file>`, and
`--strict-mcp-config`, while retaining the same exact MCP and arm-specific tool
selection. The settings path and digest are pinned in pre-dispatch checks and
reported without serializing their contents.

`CLAUDE_CONFIG_DIR` remains caller-selected and separately verified. A new or
empty config directory does not inherit first-party Claude login. The caller
must establish first-party account authentication in that namespace before a
subscription run; this adapter neither copies credentials nor performs login,
logout, or refresh. Route, included-quota, zero-paid-usage, isolation, effective
settings, and native-skill attestations remain external required evidence.
Requested CLI flags and settings do not prove that these conditions hold.

The current adapter accepts only the registered Agent Braid MCP stdio command
shape: a pinned executable followed by `-m agent_braid tooling serve`, required
`--source-root` and `--result-root` paths, and optional registered
`--worktree-root` paths. `--enable-runtime` and `--grant-store` are accepted
only when they exactly match the explicit frozen profile. It rejects wrappers,
interpreter snippets, arbitrary flags, environment/header credential channels,
and credential-bearing arguments. Raw inline config and argv values are also
excluded from plan and receipt representations; the caller attestation must
authenticate the exact command path, roots, selected route, runtime setting,
and config digest.

The Claude MCP config pins the exact server inventory, but the host CLI surface
does not provide this adapter a trusted per-server tool inventory. Tool calls
observed in JSONL are evidence of calls made, not proof that no other tools
were available. An external effective-settings attestation is required before
dispatch; unsupported or unverified server/tool restriction semantics keep the
run non-comparable.

These profiles describe requested argv/configuration, not proof of actual
host compatibility. In particular, Codex's ignore-user-config option does not
bypass authentication; ambient instructions and skills are not guaranteed to
be isolated; feature flags may be rejected or have different effects on
explicit MCP. Legacy Claude bare mode is not a subscription authentication
route. Subscription Claude's restricted settings request is only one part of
isolation and still needs external route/authentication evidence. Host versions and effective model,
route, feature settings, MCP inventory, skill loading, and output schema must be
verified from the actual start/outcome receipts before treating an attempt as
comparable. Parser output is an observation of caller-supplied bytes, not an
authentic receipt or a completion attestation.

The supervisor must enforce the externally approved caps: EUR 25, 4,000,000
tokens, 57,600 seconds, 4 GiB RSS, and 5 GiB disk. Those values must come from
the frozen registration and authenticated caller; they are not inferred or
silently defaulted here. Provider-specific budget flags and reported token/cost
fields are not invoices or a guarantee that remote spend stopped at the cap.
Unknown usage or money remains unknown. Partial output and its digest are
preserved when available, with no synthetic zero values.

## Validation boundary

Unit tests use temporary fake executables or injected supervisor functions and
do not launch real hosts. Before any real capture, the owner must separately
approve the exact frozen candidate, route/provider, model, settings, cost and
stop instrumentation, isolation evidence, and the live stop procedure. A
passing test or structural validator is not a clean-room reproduction, human
review, provider authorization, or capture receipt.

The 2026-10-14 correction separates the two layers according to the current
[CLI reference](https://code.claude.com/docs/en/cli-reference) and
[MCP permissions](https://code.claude.com/docs/en/agent-sdk/mcp): `--tools`
selects built-ins, whereas `--allowedTools` approves calls. MCP availability
comes from the exact pinned server configuration. Host approval never creates
an Agent Braid operator grant; execute/recover retain their core authority gates.
Metadata initialization can establish parser acceptance before freeze, but actual
skill loading, tool permissions and journey behavior still require admitted
native receipts after exact registration approval.
