# Proposed laboratory interface — draft v0.1

This is a design contract, not an implemented API or accepted public schema.
No fields below extend `agent-braid-plugin/v0.1`, AIM, existing runtime grants or
the fixed-patch operation language. Implementation must validate unknown fields,
types, canonical bytes, limits and immutable bindings strictly.

## Records and flow

| Record | Required meaning |
|---|---|
| HarnessManifest | Full SHA-256 identity of base/candidate, source commit plus selected uncommitted input inventory, task/fixture, context entries and their trust class, allowed component paths, host executable/build and requested model/effort/route, observed provider identity or explicit unknown, tool inventory, policy and normalizer/verifier versions; numerical budgets and declared effects |
| HarnessProposal | Parent manifest hash, exact bounded component changes, rationale as untrusted text and declared expected effects; no authority field |
| ProbeAdmission | External issuer, immutable candidate manifest hash, adopted envelope hash, source/host/route/containment observations, permitted filesystem/process/network effects, expiry and independent reservation. It is a new laboratory contract, never an existing runtime grant reused by analogy |
| ProbeAttempt | Durable unique attempt ID and start marker before dispatch; start/terminal observations, actual effects, output hashes, costs or unknowns, cancellation/cleanup and verifier outcome |
| RefinementDecision | Compared attempt IDs, protected selection-policy hash, chosen candidate or keep-base/inconclusive/refused, reasons, evidence losses and consumer verification status |
| HandoffCheckpoint | Exact source/candidate/policy/attempt identity, completed and pending work, artifacts, actual checks/outcomes, open questions and permission state; no inferred renewal |

A bounded dynamic envelope can authorize candidate discovery only after its
specific semantics are adopted. Each generated manifest is independently checked
against that envelope and reserved before dispatch. The model cannot modify the
envelope, issue admission or promote sources. A stale source/tool/model/policy or
expired observation invalidates reuse. Compare private outputs before any
human-controlled promotion.

## Initial surface and isolation

Editable: task-local guidance text and a bounded manifest choosing which already
authorized context entries to expose and in what order. Candidate text may not
alter the trusted policy even if it contains instruction-like content.
Immutable: Constitution, AGENTS/host global instructions, Spec Kit scaffolding,
verifiers/tests used as acceptance oracles, permissions, tools/scripts/hooks,
plugins, model/provider settings, source baselines and output destinations.

All files cross a strict owned-root boundary: reject symlinks, traversal, external
resolved paths, special files, executable additions, unsupported encodings and
size/depth overflow. Read permissions are a positive inventory, not permission
for the host to discover unrelated repositories or credentials.

Containment must enforce the declared threat model outside prompts. The owner
controls the trusted host and OS; hostile same-UID interference needs explicit
handling or exclusion in qualification. A worktree is a Git separation mechanism,
not an arbitrary-code sandbox. Any OS/host profile lacking real enforced effects
must remain deterministic-only or refuse native execution.

## Budget and failure semantics

Proposed algorithm default: one refinement round, one base probe, two scoped
proposal probes and one composed probe. The manifest must separately cap model
sessions, retries, selection/reflection, wall time, processes, CPU/RSS/disk,
input/output/context sizes and concurrent trials. No numerical native envelope
is accepted by this draft; T001 freezes implementable caps before launch. Start
with serial native probes; add concurrency only within a qualified effect contract.

Use explicit states proposed → validated → admitted → started → terminal, with
terminal completed/failed/interrupted/refused. Selection and promotion are separate
state machines. After a durable start, an interruption consumes an attempt; inspect
and reconcile before any separately admitted next attempt. Unknown outcomes/costs
stay unknown. Timeouts must settle child processes and account for cleanup;
failure to observe termination prevents ordinary reuse. No automatic retry may
hide duplicate effects, new cost or a changed denominator.

Native subscription route/quota observations must be fresh and independently
trusted. Missing enforceable zero-spend or containment conditions refuse/stop
native execution; they do not become a fabricated zero-cost success.

## Consumer boundary

Return bounded IDs, provenance, effects and evidence links with
`executionAuthorization: false` for analysis/advice. Journal location and manifest
hash do not constitute permission. The initial integration can use an explicit
experimental CLI; future MCP/plugin exposure needs its own versioned contract,
workspace binding, compatibility and migration review. No tool silently adds a
registered workspace or grants itself broader root access.
