# SPEC-084: Harbor evaluation substrate with a macOS shadow

**Milestone:** HAR.4 — Harness evaluation platform

**Status:** draft, documentation-only. Nothing is implemented, installed or run by
this specification's first PR. It implements owner decision F2 of the
[harnessing benchmark](../../docs/strategy/HARNESSING_BENCHMARK.md) through
[ADR 0045](../../docs/adr/0045-hybrid-harness-evaluation-substrate.md) (Proposed).
The founder accepts or rejects ADR 0045 in T001.

## Purpose and scope

Each host today needs its own qualified native laboratory before it can be evaluated
(SPEC-065 for Claude; nothing for Codex, OpenCode or Pi). This specification plans
cross-host harness evaluations as Harbor jobs, plus a small registered subset on the
real macOS host under ADR 0035 containment as a fidelity shadow. Agent Braid keeps
registration, statistics (SPEC-083), task QA and infrastructure controls (SPEC-082),
promotion pointers (SPEC-085) and human promotion.

This is engineering plus one research question. Whether container results agree
with the shadow is a hypothesis (H1). Whether the substrate is feasible on the
operator machine is a hypothesis (H2). Clause zero applies: an infeasible gate, a
disagreement or an inconclusive result is a valid outcome and is recorded as such.

In scope: four feasibility gates; the job shape (Harbor adapters `claude-code`,
`codex`, `opencode`, `pi`; pins, resources, candidate hash); the per-phase network
policy; ATIF ingestion; the macOS shadow and its agreement rule; negative controls.

Exclusions (each is a MUST NOT):

- The first PR MUST NOT install Harbor, a container runtime or an image, and MUST NOT
  run any job, trial or native session.
- Harbor's default metric (a mean with missing rewards counted as 0) MUST NOT be used
  as a verdict or as an input to promotion.
- A credential, token or secret MUST NOT enter any image, layer, exported job
  config, trajectory or committed evidence.
- No paid route: cash spend MUST stay at EUR 0.
- The substrate MUST NOT grant execution authority, promote a candidate or move a
  SPEC-085 pointer. `executionAuthorization` is false on every record.
- No change to the ADR 0035 mechanism or to the frozen SPEC-065 files.
- Native Pi sessions on the host are out of scope (SPEC-081 covers Pi installation).

## Requirements and acceptance scenarios

**REQ-001 Owner review and ADR 0045 decision.** The spec, plan and ADR 0045 are
reviewed before any implementation.

- **SC-001:** Given this spec, plan and ADR 0045, when the founder reviews them, then
  ADR 0045 is accepted, amended or rejected and OD-1 to OD-6 are decided or deferred
  in a dated record.

**REQ-002 Credential gate.** Subscription authentication works inside a trial
container with no secret in any image, layer or exported config. The credential is
present only during the run phase, by the method chosen under OD-3.

- **SC-002:** Given a built image, its layer history, the exported job config, the
  trial logs and the trajectories, when they are scanned for credential material,
  then none is found; if authentication needs a secret in an image, the gate fails
  and the substrate is recorded as infeasible.

**REQ-003 Runtime and pinning gate.** Docker or Podman is available on the operator
machine (OD-2). Harbor, each agent adapter version and each image are pinned by
version and digest. A job that names a tag without a digest refuses.

- **SC-003:** Given a job config, when it is validated before launch, then every
  image reference carries a digest, every adapter and Harbor version is exact, and a
  config with a floating tag or missing runtime refuses with a recorded reason.

**REQ-004 Cost gate.** Cash spend stays at EUR 0. Quota is read before and after
each trial batch, and the SPEC-049 D2 stop conditions apply (stale or missing
reading, weekly window above 80 %, extra usage enabled).

- **SC-004:** Given a quota reading that is stale, missing or over a cap, when a
  batch is about to start, then it does not start and the stop is recorded; no route
  that needs a paid API key is accepted.

**REQ-005 Reproducible job shape.** Each job records one container per trial, `-k`
attempts, CPU, memory and timeout, model and reasoning effort, a fresh run id, the
SPEC-082 task ids and the harness candidate hash verified inside the container.
The exported config reruns the same job.

- **SC-005:** Given one completed job, when it is rerun from its exported config,
  then the config hash, image digests, resources, model, effort and candidate hash
  are identical, the run id is new, and no cached result is reused.

**REQ-006 Per-phase network policy.** Install has public network, the agent run has
an allowlist limited to the provider API host, and the verifier has no network.

- **SC-006:** Given a trial whose agent tries a host outside the allowlist and a
  verifier that tries any network, when the trial runs, then both connections are
  denied and logged, and the denial is recorded per phase.

**REQ-007 ATIF ingestion.** Harbor trajectories are hashed and mapped into the Agent
Braid evidence format with task id, trial, attempt, candidate hash, resources and
outcome class (pass, fail, infra error, missing). Unknown or missing outcomes never
become success. Infra errors stay separate from agent failures (SPEC-082).

- **SC-007:** Given trajectories with passes, failures, infra errors and a missing
  reward, when they are ingested, then each record keeps its class, the trajectory
  hash matches the source bytes, and a malformed trajectory refuses with a reason.

**REQ-008 No Harbor verdict.** Verdicts come only from the SPEC-083 decision rules.
Harbor's mean may be stored as a labelled descriptive field and is never read by
promotion.

- **SC-008:** Given a job with missing rewards, when the report is built, then the
  missing rewards stay missing, the SPEC-083 verdict is computed on its own rules,
  and no promotion input reads the Harbor mean.

**REQ-009 macOS shadow.** A small registered subset (OD-4) runs on the real macOS
host under ADR 0035 containment, with the same tasks, candidate hash, model and
effort. The agreement rule is registered before any data. A disagreement blocks
promotion until an explanation is recorded.

- **SC-009:** Given container and shadow outcomes on the registered subset, when the
  agreement rule is applied, then agreement or disagreement is recorded per task; a
  disagreement sets a promotion block that only a recorded explanation clears.

**REQ-010 Negative controls.** Blocked network, missing credential and stale image
each fail closed with a distinct infra-error reason, never as an agent failure.

- **SC-010:** Given each control injected into one trial, when the trial runs, then
  it ends as an infra error with the expected reason code and is excluded from the
  agent-failure count.

**REQ-011 No authority.** Every substrate record carries `executionAuthorization:
false`. Each real job needs an owner go recorded before it starts.

- **SC-011:** Given any substrate record, when it is inspected, then
  `executionAuthorization` is exactly false, no pointer or registry write is present,
  and a job without a recorded owner go refuses to start.

## Owner decisions open

- **OD-1 ADR 0045.** Accept as proposed, amend, or reject. Recommended: accept after
  the T002 review findings are triaged; acceptance authorizes no job.
- **OD-2 Container runtime.** (a) Docker Desktop, (b) Podman, (c) Colima. Recommended:
  use the runtime already installed if any; otherwise Podman (Apache-2.0, no licence
  fee). Install only in an isolated environment after the owner's go.
- **OD-3 Credential method.** (a) a host-side model proxy that holds the credential
  outside the container; (b) a read-only credential mount during the run phase only;
  (c) a paid API key, which breaks EUR 0. Recommended: (a) if Harbor or a proxy
  supports it, else (b); reject (c). Provider terms for subscription use in automated
  containers must be checked first.
- **OD-4 Shadow subset and agreement rule.** Size and rule. Recommended: at least one
  task per SPEC-082 stratum, within the D2 caps; agreement means the same per-task
  majority outcome over the shadow trials.
- **OD-5 Host order.** Recommended: `claude-code` first, because only Claude has a
  qualified macOS shadow (SPEC-065); then `codex`, `opencode`, `pi`, labelled
  container-only until a shadow exists for them.
- **OD-6 Fallback if a gate fails.** (a) record infeasible and stay on the current
  laboratory path; (b) open a separate Inspect AI spec. Recommended: (a) now, (b) only
  by a later owner decision.

## Non-goals

No new statistics (SPEC-083), no task corpus (SPEC-082), no pointers (SPEC-085), no
telemetry format (SPEC-086), no daily-use sandbox, no claim that container results
transfer to the user's install without the shadow.

## Risks

- Subscription auth in containers may be infeasible or not allowed by provider terms.
- Linux containers differ from macOS; the shadow covers only Claude at first.
- On macOS the runtime is a Linux VM; policy enforcement there is unverified.
- Pulled images are a new trust and supply-chain boundary; digests pin them.
- Quota burn from `-k` attempts; the D2 caps and stop rules are the control.

## Dependencies

ADR 0045, ADR 0035, SPEC-065 (shadow containment), SPEC-049 (registry, D2 caps, D3),
SPEC-082 (corpus, infra controls), SPEC-083 (statistics, verdict), SPEC-085
(consumes verdicts), SPEC-047 (local telemetry consent), SPEC-086 (optional spans).

## References

- [Harnessing benchmark](../../docs/strategy/HARNESSING_BENCHMARK.md) (F2),
  [ADR 0045](../../docs/adr/0045-hybrid-harness-evaluation-substrate.md),
  [ADR 0035](../../docs/adr/0035-native-claude-laboratory-containment.md)
- [Harbor](https://docs.harborframework.com/),
  [pre-integrated agents](https://docs.harborframework.com/agents/pre-integrated-agents.md),
  [network policies](https://docs.harborframework.com/tasks/network-policies.md),
  [Terminal-Bench 2.0](https://arxiv.org/html/2601.11868v1)
- [Inspect agent bridge](https://inspect.aisi.org.uk/agent-bridge.html),
  [Anthropic, infrastructure noise](https://www.anthropic.com/research/infrastructure-noise)
