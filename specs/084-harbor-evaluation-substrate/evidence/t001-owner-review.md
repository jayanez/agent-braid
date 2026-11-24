# SPEC-084 T001: owner review, part 1 (2026-11-24)

The owner (Juan Antonio Yáñez García, founder) reviewed `spec.md` and `plan.md` interactively on develop, as merged in #1515 (`f0793dfd`). The answers below are the options the owner selected, quoted verbatim.

OD-1 (ADR 0045) is deferred, as the spec recommends: the owner decides it after the T002 Codex review is triaged. T001 stays open until then. This record authorizes no install, no job and no execution (`executionAuthorization` false).

| Decision | Answer | Meaning |
|---|---|---|
| OD-1 ADR 0045 | deferred | Decided after T002 triage. Accepting it authorizes no job. |
| OD-2 Container runtime | "Docker Desktop ya instalado (Recomendado)" | Use the Docker Desktop already installed on this Mac (observed 2026-11-24: `/usr/local/bin/docker`, Docker.app; Podman and Colima absent). Nothing is installed. T003 pins its version and every image digest. |
| OD-3 Credential method | "Proxy en el host; si no, montaje de solo lectura (Recomendado)" | (a) A host-side model proxy keeps the credential outside the container. If Harbor or a proxy cannot support it, (b) a read-only credential mount during the run phase only, followed by a scan that no copy remains. Never (c), a paid API key. The provider terms for automated subscription use are checked first (T004). |
| OD-4 Shadow subset and agreement | "1 tarea por estrato, mayoría por tarea (Recomendado)" | At least one task per SPEC-082 stratum, within the D2 caps. Agreement means the same per-task majority outcome over the shadow trials. |
| OD-5 Host order | "Claude primero; si falla, infeasible (Recomendado)" | `claude-code` first (the only host with a qualified macOS shadow, SPEC-065), then `codex`, `opencode` and `pi`, labelled container-only until a shadow exists for them. |
| OD-6 Fallback | same answer | A failed gate is recorded as `infeasible` and work stays on the current laboratory path. A separate Inspect AI spec opens only by a later owner decision. |

## Why now

The owner took this review early, before the SPEC-080 code, because the feasibility gates T003 to T006 (runtime, subscription credential inside a container, EUR 0 cost, network allowlist) are the largest unknowns of HAR.4. An `infeasible` result changes SPEC-082 (the exploit agent stays `qa-incomplete`) and SPEC-083 (trials would come from the current laboratory). Each gate still runs only after its own owner go.

## Limits

- The owner decides as owner, not as an independent reviewer.
- T002 has not run yet. A confirmed finding may reopen a decision through a dated amendment.
- This record authorizes no install, no job, no credential use and no promotion. `executionAuthorization` stays false.
