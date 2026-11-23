# SPEC-083 T001: owner review (2026-11-23)

The owner (Juan Antonio Yáñez García, founder) reviewed `spec.md` and `plan.md` interactively on develop, as merged in #1515 (`f0793dfd`). This spec has no ADR. The answers below are the options the owner selected, quoted verbatim.

All four questions were answered with the recommended option. Together they decide OD-1 to OD-6.

## Decisions

| Decision | Answer | Meaning |
|---|---|---|
| OD-1 Margin and α | "δ = 0,10, α = 0,05 (Recomendado)" | Non-inferiority margin δ = 0.10 with one-sided α = 0.05. Fixed before the first registration record. |
| OD-2 Primary uncertainty method | "Analítico por tarea + sensibilidades (Recomendado)" | The primary estimate is the analytic task-clustered error, which is deterministic. A clustered bootstrap runs as a sensitivity check. |
| OD-3 Cluster level | same answer | Clustering is by task. A lineage-level clustering runs as a sensitivity check. If the primary result and a sensitivity check disagree, the verdict is `inconclusive`. |
| OD-4 Infrastructure thresholds | "Como SPEC-082 + renovar tras 5 usos (Recomendado)" | At most 10 % of trials per arm may be infrastructure errors, with at most a 5-point difference between arms and at most 2 reruns per trial. This matches SPEC-082 OD-5. |
| OD-5 Held-out reuse | same answer | Every use of the gate is logged. The private split is refreshed after 5 uses of the gate, or sooner on any suspected leak. |
| OD-6 Per-task regressions | "Solo informar en v0.1 (Recomendado)" | A task with baseline pass^n = 1 and candidate pass@n = 0 is listed in the verdict for the human per-axis review. In v0.1 it does not block promotion on its own. |

## Limits

- **Power figures:** the figures shown to the owner (about 57 % at δ = 0.10 and 86 % at δ = 0.15, for 30 tasks) are illustrative. They assume a spread of 0.3 and a normal approximation; they are not data.
- **Role of the reviewer:** the owner decides as owner, not as an independent reviewer.
- **Codex review:** T002 has not run yet. Any finding it confirms may reopen a decision through a dated amendment.
- **Authority:** this record authorizes no code, no run and no promotion. `executionAuthorization` stays false.
