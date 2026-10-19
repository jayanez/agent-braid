# Copy-ready assignment: DDP-T01

Mission: Freeze additive contracts and migration map. Owner slot: coordinator.

Readiness: prepared-conditional; dependencies must actually be satisfied: T025 completed engineering receipt checked by coordinator. Prepared-conditional means assignable only after that receipt/contract gate, not authorized to start now. DDP-T09 stays blocked until separate source/budget/research authorization.

Freeze exact field sets, canonicalization, limits, error taxonomy and T024/T025 version mapping; document old-version refusal and no authority escalation.

Owned files only:

- `specs/028-system-one-core/contracts/verified-plan-v1.md`
- `specs/031-system-one-integration/contracts/verified-plan-consumer-v1.md`
- `specs/029-system-one-evaluation/verified-plan-conformance.md`

Acceptance: Contract vectors and migration table reviewed against exact T025 candidate; affected public API/architectural decisions remain proposed until governance review.

Required negative/verification: Malformed/unknown versions, missing pins and probability/coercion attempts are rejected by planned vectors; compare every proposed bound to T024 source. Use focused standard-library unittest modules named by owned tests after implementation, then coordinator validate_change quick/pr under repository policy. No checks were executed by this draft.

Minimum source context: agent_braid/system_one.py and contracts/stdlib-v1.md for old behavior; research/system_one/eof_verification/{verifier,language,adapter,ingress}.py for T024 semantics; consumer_verification/bridge.py for old coupling; actual final T025 receipt for new handoff/tree construction. Inspect only the sections needed by your package, plus its existing mapped spec requirements.

Read AGENTS.md and canonical authorities first. Read the staged README, architecture and your exact backlog/issue entry; inspect current owning source, do not rely on this snapshot for changed behavior. Source snapshot at drafting is the parent-observed 48f4226db1e1b0565b1f8faf0eca81c150a65d30 plus WIP; current head/bytes can differ.

You are not alone in the codebase. Preserve others' edits and adapt to their approved interfaces. Never reset, checkout over, revert or overwrite unrelated WIP. Work only in coordinator-designated isolated implementation location after explicit assignment. The research checkout remains read-only until the coordinator supplies a different explicit integration arrangement. This handoff grants no launch, branch, commit, push, remote issue/PR, experiment, model execution, download, fitting, calibration or activation authority. EUR 0, CPU local only.

Never edit research/system_one/eof_consumers/**, T025 plans/tests/evidence, old research modules/packets, historical assurance, generated plans/skills or global configuration. If a required helper/shared file is outside ownership, return the requested change to coordinator; do not silently claim it. No general EN/ES understanding, independent scientific oracle or Laya parity claims. Never substitute probability for deterministic admissibility.

Stop on dependency/contract/source drift, required authority conflict, target-tree mismatch, need for remote data/spend, unsupported effect domain or inability to enforce declared bounds. Preserve failures and return exact blocker; do not rerun/repair frozen studies.

Return a local result bundle to coordinator: summary, owned changed-file paths, patch/diff relative to assigned baseline, file hashes, contract versions, focused test commands/logs/exits/environment, positive/negative outcomes, source-immutability and no-authority-effect receipts, unresolved findings and pending gates. Return by agreed local path; coordinator reads it. Do not message another conversation or publish externally. Coordinator reviews and applies changes individually with overwrite checks; do not overwrite shared WIP.


## Refined scope and cost acceptance — 2026-10-20

Freeze exact field sets, canonicalization, limits, error taxonomy and T024/T025 version mapping; document old-version refusal and no authority escalation. Freeze separate decision/acquisition/end-to-end prepare budget semantics, nested absolute deadlines, enforceability labels and explicit unsupported/refusal behavior; do not reuse the classifier deadline for prepare.

Negative controls: Malformed/unknown versions, missing pins and probability/coercion attempts are rejected by planned vectors; compare every proposed bound to T024 source. Reject budget reset/enlargement, implicit prepare caps and false hard-termination guarantees.

Closure/evidence: Contract vectors and migration table reviewed against exact T025 candidate; affected public API/architectural decisions remain proposed until governance review.

See [budget boundary](../latency-and-budgets.md) and [whole-program scope](../program-map.md). This amendment governs any broader earlier deadline wording in this draft. The initial three T025 case preparations reported by coordinator at 8.5–15.1 seconds are preliminary; final results remain pending. No speedup or product deadline is asserted.

## T025 dependency meaning — final clarification

“T025 completed engineering receipt checked by coordinator” means the T025 engineering work is completed, its actual commands/results, exact candidate and changed-file/interface bindings are recorded, and the coordinator has checked that receipt. It does not mean human review, scientific admission, representative product acceptance, promotion or activation. Those gates remain pending and independent.

DDP-T01 may begin once that engineering dependency is satisfied and the coordinator explicitly assigns it. No additional human/product acceptance is implied as a prerequisite for this bounded implementation assignment. Later tasks retain their own dependencies, governance and acceptance boundaries. A preflight pass or unfinished preliminary T025 timing is insufficient to satisfy this receipt dependency.

