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
instructions were loaded. Claude's native `Skill(name)` tool selection is not
a grant, and `--allowedTools` is an approval mechanism rather than a tool
allowlist. The adapter does not infer that any host setting successfully
isolates global instructions or disables a feature unless that is established
by a trusted session receipt.

Routes are explicit and supplied by the authenticated caller. Missing or
unknown route, missing model/effort, absent provider opt-in, unresolved
isolation evidence, stale configuration/binary identity, or missing required
attestation fails before handoff. This code does not create or refresh any of
those facts. A failed or ambiguous started attempt is never retried.
For a frozen subscription-only admission, the exact account/cohort/slot binding
is carried into the process supervisor. Its child environment permits only
`PATH`, `LANG`, `LC_ALL`, `TMPDIR` and `CLAUDE_CONFIG_DIR`; provider keys, routing,
proxy and loader overrides refuse. This reduces configuration fallback paths;
it does not authenticate the selected native account. The preparation verifier
must verify the effective route and authentication, and the trusted supervisor
observer must supply fresh account, included-quota and paid-usage facts. See
[REGISTRATION.md](REGISTRATION.md) and [SUPERVISOR.md](SUPERVISOR.md).

## CLI command profiles

The preparation profiles use the documented command surfaces reviewed on
2026-10-08. Codex uses `exec --json --ephemeral --ignore-user-config
--sandbox read-only --model ... --cd ...` and an explicit medium reasoning
effort setting; its MCP/tool and skills configuration is supplied as explicit
TOML overrides and bound by a digest. Claude uses `--bare --strict-mcp-config --mcp-config
... --no-session-persistence --print --verbose --output-format stream-json
--model ... --effort medium`. The MCP-only Claude arm supplies an empty built-in
tool set and disables slash commands. The skills arm selects the five exact
native `Skill(name)` tools and does not disable slash commands. No command uses
permission bypass flags or puts the prompt on argv.

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
explicit MCP. Claude's bare mode is only one part of isolation and still needs
external route/authentication evidence. Host versions and effective model,
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
