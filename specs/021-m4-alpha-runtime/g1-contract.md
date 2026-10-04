# G1 pinned implementation boundary

Status: implementation preflight reviewed on 2026-10-04 under the approved
SPEC-021 scope. This is not independent review or whole-M4 acceptance.

## Protocol and dependency decision

MCP 2025-11-25, stdio only, tool capability only. Official schema revision and
SHA-256 are in g1-evidence/protocol-pin.json. No SDK or new runtime dependency.
Implement the small pinned lifecycle/tool surface directly with stdlib; unsupported
features are unadvertised. A 2026 discovery probe receives method-not-found so the
observed Claude client can fall back to its supported initialize lifecycle.
Initialize negotiates the one supported version; unsupported clients disconnect.
Pin Codex 0.159.0-alpha.12.1 and Claude Code 2.1.236 for current host evidence.
Both actual clients accepted the server version, initialized and requested tools;
these no-model handshakes do not discharge the real-host execution/recovery exit.

## Admission, phase and transport budgets

Retain SPEC-020 request limits: 2–4 operations, 16 paths, 256 KiB aggregate patch.
Each existing M2 replay/verification phase retains its existing pinned budget:
120 s Git wall budget, 512 commands, 16 MiB aggregate capture, 8 MiB per command,
64 MiB sampled scratch. Each existing serial-runtime admission/execute/recovery/
verification invocation retains 60 s, 256 commands, 8 MiB aggregate capture,
2 MiB per command and 64 MiB sampled scratch. No hard child memory cap is claimed.
The policy path calls at most one replay consumer verification and one runtime
preparation before dispatch. It does not claim a shared hard deadline across these
independent stages. Expose stage limits in the bound policy and report stage costs.
C2 worker preparation has one shared 60 s / 256-command / 8 MiB capture /
2 MiB-command / 64 MiB sampled scratch budget across at most four workers.
Coordinator execution remains a separate existing SPEC-020 invocation.
A caller must acknowledge the entire stage-budget policy. Repeated invocations
consume new bounded work and are reported separately, not described as free.
MCP frame/result cap: 1 MiB each; in-flight operations: one; tool timeout 360 s.
Cancellation/disconnect stop new phases and owned runtime children; M2 consumer
verification retains its existing bounded completion behavior, so it must not
be described as immediately cancellable. No post-disconnect durable phase starts.

## Operator grants and retry semantics

A dedicated owned POSIX grant store (0700, current UID, no symlink) is configured
by the operator at server launch. No tool argument may select another store or
supply a grant body. Only local Python/CLI operator paths issue grants after
matching explicit plan-digest acknowledgement and consumer verification.
Bind policy revision, whole plan, canonical destination/source, fixed identities,
limits, action execute/resume/abort and expiry (1–900 seconds; default 300).
Consume one-purpose grants durably under an exclusive store lock before write
dispatch. Repeated execute calls may independently inspect an existing verified
result, but cannot execute again. Prefixes require a fresh explicit resume grant;
absence after consumption remains an unknown/refused outcome requiring operator
inspection. Recovery never changes the logical run destination. No authentication
against a hostile same-UID process, signature or source-promotion authority.

## Fixture and model-consumption boundary

Owned temporary Git fixtures and deterministic peers are authorized implementation
checks; source repositories remain read-only. No credentials or hosts are installed.
Handshake probes use existing clients without model calls or persistent host config
changes. Model-backed real-host exercises remain pending a separately agreed
consumption budget. Current incremental model spend is zero; no positive spend
is authorized by this preflight. CI exercises deterministic peers without model
credentials. G3/G4 remain open.
