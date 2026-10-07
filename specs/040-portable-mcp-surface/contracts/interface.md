# Portable MCP contract proposal

**Status:** proposed additive experimental contract `agent-braid-tooling/v0.1`.
Implementation and API adoption remain pending. Legacy runtime contracts retain
their own versions; this envelope does not change their interpretation.

## Transport and capabilities

Optional Python extra `tooling`, initial pin `mcp==2.3.0`. The new server delegates
framing, protocol negotiation, cancellation and standard primitives to the official
SDK. stdio only. Support 2026-07-28 discovery and 2025-11-25 initialization through
SDK compatibility; test both paths. Do not hardcode initialization as a requirement
for the new protocol. No remote HTTP, sampling, elicitation, subscriptions, tasks
extension or model-triggered server processes in v1.

Configuration binds canonical source root, owned result root and optional grant
store before launch. Tool arguments cannot override these roots. Analysis is
default; runtime tools require explicit enablement and a configured grant store.
Startup diagnostics go to stderr; stdout contains only protocol frames.

| Tool | Input | Result/effect |
|---|---|---|
| `analyze-work` | `kind` + existing AIM/Git `request`; worktree sources use Git request | Existing analyzer report/provenance; read-only |
| `analyze` | `request`: existing immutable 2–4 patch runtime request | Existing analysis/replay semantics; advisory |
| `prepare` | `request`, `runDirectory`, optional `mode` | Existing policy/schedule/manifest; temporary rehearsal, no persistent result allocation |
| `status` | `plan`: existing policy plan | Existing state, no writes |
| `execute` | `plan`, `grantId` | Existing private Git batch; no source promotion |
| `recover` | `plan`, `grantId`, `action` resume/abort | Existing reconcile/abort contract |
| `verify` | `plan`: existing policy plan | Existing independent verifier result |

The six names retain accepted request semantics and core rejection behavior.
The existing legacy entry point/result format stays available; the additive SDK
endpoint documents its new envelope and migration. Preserve the full original
result inline under `result` or via a hash-bound owned artifact reference there.
CLI parity compares the full dereferenced result, never only the summary.

## Output envelope

Require `schemaVersion`, `operation`, `status` (ok/refused/unknown/error),
`summary`, `result`, `evidenceRefs`, `limits` and `provenance`.
`provenance` carries candidate/runtime/schema version, exact input identifiers,
observation contract and source identity. Consultative results retain
`executionAuthorization: false`; execution results instead report the checked
grant identity/scope and actual effects without suggesting general authority.

Machine output uses declared input/output JSON schemas and `structuredContent`.
Text is a bounded explanation of the same fields, including refusal and unknowns,
not a contradictory second verdict. Return at most 16 KiB summary and 256 KiB
inline result; larger results use hash-bound owned resource references and
bounded chunks. Do not label an executed operation refused solely because its
report needs a reference: preserve its actual outcome and owned result.
Input framing stays at most 1 MiB. Retain existing resource/time/patch bounds
including the 360-second call cap; stricter configured limits may refuse early.
Validate sizes before parsing/traversal and bound nested structure depth.

Resources: `agent-braid://capabilities`, `agent-braid://runs/{id}/status`,
`agent-braid://runs/{id}/evidence/{artifact}`. IDs resolve only through the owned
run inventory; no arbitrary file URI, path traversal, symlink escape or source
content browsing. Missing/stale artifacts refuse. Resource manifests advertise
only configured capabilities. Metadata/evidence is untrusted data.

Prompts: `agent-braid-analyze`, `agent-braid-plan`, `agent-braid-evidence`.
They describe bounded steps and evidence needs, perform no writes and contain no
grant issuance/host permission shortcut. Protocol annotations are hints.

## Cancellation and authority

Cancellation/timeout propagates to existing cancellation controls and leaves an
inspectable recoverable state if a write transition started. Never return success
for an unfinished operation or replay a consumed grant after a retry. Enforce
point-of-use input/base/policy/grant checks, process lock and compare-and-swap.
Read-only analysis never issues a grant. Refuse unsupported operation kinds,
unsafe roots, hidden runtime access, expired/wrong/reused/revoked grants and stale
plans. Do not execute repository code, hooks or arbitrary commands.

## Verification plan

Compare CLI and SDK full results on identical immutable inputs; test both protocol
paths, SDK client discovery/tools/resources/prompts, schema-negative controls,
overlarge/deep input, concurrent requests, cancellation, invalid roots/grants,
stale plans, recover/verify and output agreement. A protocol test is not an actual
Codex/Claude observation. Bind all actual outcomes to hashes and environment.
