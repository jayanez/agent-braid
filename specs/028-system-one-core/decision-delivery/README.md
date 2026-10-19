# System One decision delivery supplement

Status: draft implementation program, 2026-10-20. No implementation, agent launch, research run, adoption or remote publication is authorized by this packet. This is a supplement to SPEC-028–033, not a seventh replacement spec or a new assurance record.

Read inventory.md, architecture.md, tasks/plan.md, tasks/backlog.json, then the assigned handoff. Proposed requirement/scenario/task IDs are namespaced DDP-REQ/SC/T; they do not consume existing T026 or replace existing REQ-001. Existing task checkboxes and assurance snapshots remain untouched.

The first coding batch after the coordinator checks the completed T025 engineering receipt is DDP-T01 (interfaces). Next, DDP-T02/03/04 can run with disjoint file ownership; DDP-T05 then joins the deterministic path, followed by consumer integration DDP-T06 and verification DDP-T07. DDP-T08 is documentation/closure. DDP-T09 is an explicitly blocked future learned branch, not a prerequisite for useful deterministic decisions.

Source: research checkout at /Users/juanyanez/Repos/Personal/agent-braid-system-one, parent-observed HEAD 48f4226db1e1b0565b1f8faf0eca81c150a65d30 plus valuable uncommitted files. source-bindings.json in the delivery root binds documentary bytes inspected during drafting; the coordinator must re-read drift before import. T025 is owned by the parent and was not assumed delivered or evaluated.

All documentation is English. External spend EUR 0; local M3 Pro CPU; no downloads, services, fitting, calibration, model evaluation or experiments in this delivery. Preserve accumulated experimental ledger 47058.32509968127/86400 seconds; software validation does not reset it or authorize use of the remainder.

Authority: CONSTITUTION.md; GOVERNANCE.md; docs/development/SPEC_KIT.md and VALIDATION_PROFILES.md; ADRs 0017/0019/0020; OPERATIONAL_SEMANTICS.md and CLAIM_DISCIPLINE.md. Any conflict stops the affected task. Canonical architectural adoption and public contract changes need their governance records; draft feature design is not adoption.


## Complete product scope and latency boundaries

Read [program-map.md](program-map.md) for all S1.x capabilities and their original task owners. DDP covers the first deterministic extraction/integration lane only. Read [latency-and-budgets.md](latency-and-budgets.md) for separate layer-1 and native-prepare envelopes, preliminary T025 caveats and required T06 stage receipts. No end-to-end deadline or speedup is inferred from classifier timing.

## T025 dependency meaning — final clarification

“T025 completed engineering receipt checked by coordinator” means the T025 engineering work is completed, its actual commands/results, exact candidate and changed-file/interface bindings are recorded, and the coordinator has checked that receipt. It does not mean human review, scientific admission, representative product acceptance, promotion or activation. Those gates remain pending and independent.

DDP-T01 may begin once that engineering dependency is satisfied and the coordinator explicitly assigns it. No additional human/product acceptance is implied as a prerequisite for this bounded implementation assignment. Later tasks retain their own dependencies, governance and acceptance boundaries. A preflight pass or unfinished preliminary T025 timing is insufficient to satisfy this receipt dependency.
