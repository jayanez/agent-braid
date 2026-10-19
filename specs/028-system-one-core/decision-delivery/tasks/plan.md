# Concrete implementation plan

Draft only. Task tracker target is the local issue drafts and machine-readable backlog.json. No remote tracker mutation. Existing incomplete tasks/plans remain untouched. Contract definitions are in architecture.md; each task owns at most three files. Every task has one proposed DDP-REQ and DDP-SC, mapped to original spec requirements. Detailed acceptance, negatives, evidence and limits are in backlog.json and individual issue bodies.

## Sequence and concurrency

Gate 0: coordinator receives the final T025 receipt, exact candidate and changed-file inventory. Re-read current authority/WIP drift; do not repeat the parent's preflight as a proxy for its result. Resolve T025 interfaces and contract overlap, then DDP-T01. No agent may invent its completion.

Batch 1: DDP-T01 is the first recommended coding preparation after T025. Freeze interfaces and migration vectors before source extraction. If a public API or architectural change is selected, obtain its required governance review before integration; internal drafting can continue.

Batch 2: at most three workers: A=DDP-T02, B=DDP-T03, C=DDP-T04. Their files are disjoint. Registry tests use immutable stubs against frozen contracts; workers exchange data fixtures through coordinator, never edit each other's files. Workers are optional assignments, not launched here.

Checkpoint 1: coordinator validates contract parity, no old-source edits, focused controls and quick profile. If a shared helper needs edits, coordinator serializes ownership or adapts in the new module; do not expand scope silently.

Batch 3: A=DDP-T05 joins interfaces and delivers a usable deterministic source-to-decision slice. B/C wait for the frozen join result; no speculative consumer rewrites. Checkpoint: accepted positive case, correct semantic defer and technical refusal, same legacy default behavior.

Batch 4: B=DDP-T06 handles consumer adapter; A may prepare documentation within its own branch only after releasing all shared files. C performs DDP-T07 after integration is stable. Coordinator may request a separately authorized Luna Latest review, with no more than three concurrent agents total; independent review never counts as human acceptance.

Batch 5: coordinator runs stable pr validation and DDP-T08. A software-complete optional deterministic API is a bounded delivery even if DDP-T09 remains blocked. Public exposure, real-workload shadow, calibration, learned routing and activation are separate decisions. No new experiments are needed to declare the software slice complete within its tested domain.

## Acceptance scenario index

### DDP-T01: Freeze additive contracts and migration map

DDP-REQ-01: Freeze exact field sets, canonicalization, limits, error taxonomy and T024/T025 version mapping; document old-version refusal and no authority escalation.

DDP-SC-01: Given the pinned contracts and dependencies T025 completed engineering receipt checked by coordinator, when the scoped implementation is exercised, then Contract vectors and migration table reviewed against exact T025 candidate; affected public API/architectural decisions remain proposed until governance review.

Negative: Malformed/unknown versions, missing pins and probability/coercion attempts are rejected by planned vectors; compare every proposed bound to T024 source.

Owner: coordinator. Original mappings: SPEC-028/REQ-001, SPEC-028/REQ-002, SPEC-031/REQ-002. Issue key: `jayanez/agent-braid:system-one-decision-delivery:DDP-T01:v1`.

### DDP-T02: Extract EOF IR and controlled interpretation

DDP-REQ-02: Extract pure T024 validation and exact EN/ES parser/renderer with prefix preservation; no source I/O, labels or Git in this module.

DDP-SC-02: Given the pinned contracts and dependencies DDP-T01, when the scoped implementation is exercised, then Golden IR/grammar parity on fixed developer fixtures with original T024 semantics; old sources unmodified.

Negative: Retained-tail versus terminal-edit, forged patch prefixes, ambiguous anchors, BOF, malformed/overbudget text and exact round trip; unrestricted prose refuses.

Owner: agent-A. Original mappings: SPEC-029/REQ-005, SPEC-028/REQ-002. Issue key: `jayanez/agent-braid:system-one-decision-delivery:DDP-T02:v1`.

### DDP-T03: Extract bounded observed-effect acquisition

DDP-REQ-03: Extract read-only pinned source acquisition into the frozen snapshot envelope. Reuse current local Git helpers without editing them; keep declaration/observation channels.

DDP-SC-03: Given the pinned contracts and dependencies DDP-T01, when the scoped implementation is exercised, then Pinned local fixture source/hash manifest, scratch cleanup receipt and no-write assertions; no corpus study.

Negative: Source drift, path escape, wrong revision, non-LF/binary/missing-newline, unsupported mode/rename, incomplete effects and deadline exhaustion refuse; source refs/files remain identical.

Owner: agent-B. Original mappings: SPEC-031/REQ-002, SPEC-029/REQ-005. Issue key: `jayanez/agent-braid:system-one-decision-delivery:DDP-T03:v1`.

### DDP-T04: Implement static domain verifier registry

DDP-REQ-04: Implement immutable allowlisted registry and dispatch validation against a stub data-only verifier result; defer concrete IR import to DDP-T05.

DDP-SC-04: Given the pinned contracts and dependencies DDP-T01, when the scoped implementation is exercised, then Registry identity vectors and bounded negative dispatch tests; no general-domain support claim.

Negative: Unknown domain/version/observation, forged digest, mutable entry and dynamic plugin/callable dispatch refuse; exact supported registration passes.

Owner: agent-C. Original mappings: SPEC-028/REQ-005, SPEC-031/REQ-001. Issue key: `jayanez/agent-braid:system-one-decision-delivery:DDP-T04:v1`.

### DDP-T05: Deliver deterministic verified-plan selection

DDP-REQ-05: Bind acquisition, IR and registry; verify complete offered plans then select stable eligible goal-reaching option or defer. Report technical refusal separately; preserve shared deadline.

DDP-SC-05: Given the pinned contracts and dependencies DDP-T02, DDP-T03, DDP-T04, when the scoped implementation is exercised, then A local vertical-slice receipt from pinned source to verified decision, full per-option consequences and all negative controls. No model invocation.

Negative: No eligible plan, tie, duplicate/omitted option, stale snapshot/registry, unmet dependency, changed goal and exhausted budget; selected result has no probability or authority.

Owner: agent-A. Original mappings: SPEC-028/REQ-003, SPEC-028/REQ-004, SPEC-031/REQ-003. Issue key: `jayanez/agent-braid:system-one-decision-delivery:DDP-T05:v1`.

### DDP-T06: Bind extracted decisions to read-only preparation consumers

DDP-REQ-06: Implement separate adapter calling existing core prepare and ToolingService through approved interfaces plus real stdio tests. Port exact T025 handoff/tree logic without changing its research files or default tool registry.

DDP-SC-06: Given the pinned contracts and dependencies DDP-T05, T025 completed engineering receipt checked by coordinator, when the scoped implementation is exercised, then Core/service/real-stdio parity receipts, exact expected tree, cleanup and source-immutability checks. T024 corpus replay only if separately authorized as software integration regression; never new accuracy.

Negative: Tampered choice/tree/source/prefix/payload, cross-consumer packet replay, frame/cancellation failures and rejected-k0; zero execute/recover/grant/persistent-run effects; evidence chunks checked completely.

Owner: agent-B. Original mappings: SPEC-031/REQ-004, SPEC-031/REQ-005, SPEC-031/REQ-006. Issue key: `jayanez/agent-braid:system-one-decision-delivery:DDP-T06:v1`.

### DDP-T07: Verify integrated compatibility and adversarial boundaries

DDP-REQ-07: Independently test old defaults/new opt-in and adversarial boundary coverage; coordinator runs required validation profiles on stable candidate. Review agent launch needs separate authorization and Luna Latest.

DDP-SC-07: Given the pinned contracts and dependencies DDP-T06, when the scoped implementation is exercised, then Focused tests plus quick during work and pr once stable with exact commands/SHA/environment/skips; findings resolved or explicit blockers. Luna review pending until actually authorized/performed.

Negative: Changed old stdlib response, neural module load on core import, unsupported input accepted, omitted evidence chunk, forged authorization and non-cleaned scratch fail the suite.

Owner: agent-C / later Luna reviewer. Original mappings: SPEC-029/REQ-005, SPEC-029/REQ-006, SPEC-028/REQ-006. Issue key: `jayanez/agent-braid:system-one-decision-delivery:DDP-T07:v1`.

### DDP-T08: Package bounded delivery and adoption gates

DDP-REQ-08: Record delivered capability, exact domain/versions, costs observed or unknown, rollback, task reconciliation proposals and open founder/source/utility gates. Do not mark historical tasks complete by analogy.

DDP-SC-08: Given the pinned contracts and dependencies DDP-T07, when the scoped implementation is exercised, then Candidate-bound software packet and explicit pending-gates matrix; no assurance rewrite, activation, tracking publish or milestone closure.

Negative: Negative utility, absent human approval and missing representative evidence keep relevant promotion gates pending; passing tests cannot set adopted=true.

Owner: coordinator. Original mappings: SPEC-033/REQ-002, SPEC-033/REQ-006. Issue key: `jayanez/agent-braid:system-one-decision-delivery:DDP-T08:v1`.

### DDP-T09: Register learned interpretation and selection follow-up only

DDP-REQ-09: Define a future learned interpreter/ranker experiment only after data rights, blind labels, disjoint calibration and exact budget review; reuse existing runtime rather than rebuilding it.

DDP-SC-09: Given the pinned contracts and dependencies Separate owner authorization; SPEC-029/T008; SPEC-030 rights/budget gates, when the scoped implementation is exercised, then Approved prospective protocol and exact budget/rights records required before any work beyond drafting; this task stays blocked and is not on the deterministic critical path.

Negative: Absent source permission, representative labels, calibration partition or promotion review blocks execution; verifier still rejects unsafe model proposals.

Owner: unassigned / blocked. Original mappings: SPEC-030/REQ-001, SPEC-030/REQ-004, SPEC-033/REQ-002. Issue key: `jayanez/agent-braid:system-one-decision-delivery:DDP-T09:v1`.

## Stop conditions and decisions

Stop the affected package on authority conflict, source/IR/version drift, need to change parent's files, need for remote access/download/spend, unclear observed-effect coverage, mismatch between verifier and native target tree, or missing cancellation/resource bounds. Preserve failure evidence; do not patch frozen research evidence to make it pass.

Open decisions: final T025 version and exported interface; internal module versus later public API packaging; governance approval for any new architectural/public contract; eventual permissioned real workload and human rubric; per-capability learned promotion. This draft selects internal modules, static one-domain registry and stable deterministic choice, so those later decisions do not block the deterministic software path once its actual dependencies pass.


## Whole-program and latency refinement

DDP-T01–T08 deliver only the first deterministic verified-plan lane; DDP-T09 is blocked planning. The [full S1.x map](../program-map.md) keeps boolean/choice/score, unrestricted EN/ES, schema, shortlist/retrieval, lifecycle/telemetry, learning/calibration and promotion assigned to their existing tasks. Do not close any broader capability merely by finishing DDP.

Budget semantics in [latency-and-budgets.md](../latency-and-budgets.md) govern earlier generic shared-deadline wording: decision, acquisition and native prepare have distinct explicit caps within any declared outer deadline. T01 freezes the contract; T05 measures the decision path; T06 must provide explicit prepare envelopes and per-stage repeated-verification/cleanup telemetry. Unknown numeric support or unenforceable termination stays an open acceptance gate. Preserve all freshness/binding/native checks; no cache optimization is authorized here.

## T025 dependency meaning — final clarification

“T025 completed engineering receipt checked by coordinator” means the T025 engineering work is completed, its actual commands/results, exact candidate and changed-file/interface bindings are recorded, and the coordinator has checked that receipt. It does not mean human review, scientific admission, representative product acceptance, promotion or activation. Those gates remain pending and independent.

DDP-T01 may begin once that engineering dependency is satisfied and the coordinator explicitly assigns it. No additional human/product acceptance is implied as a prerequisite for this bounded implementation assignment. Later tasks retain their own dependencies, governance and acceptance boundaries. A preflight pass or unfinished preliminary T025 timing is insufficient to satisfy this receipt dependency.
