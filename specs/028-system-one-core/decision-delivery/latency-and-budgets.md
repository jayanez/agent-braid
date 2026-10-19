# Layer-1 decision and native preparation budgets

Feature-local contract clarification, 2026-10-20. No measurements were executed in this drafting chat. The coordinator reported **preliminary T025** first three preparations of one case at **8.5–15.1 seconds entry-to-result**, spanning native API, ToolingService and real stdio. These are unfinished integration observations, not a completed benchmark, distribution, accepted latency bound or evidence of speedup. Raw stage receipts and final outcomes remain pending. They cannot establish transport rankings or general performance.

## Distinct accounting boundaries

| Boundary | Start → end | Included work and contract |
|---|---|---|
| Layer-1 decision | Admitted canonical decision request → sealed selection/refusal/defer result | IR admission/interpretation as declared, bounded deterministic verification and policy/selection. Report precisely whether acquisition is inside this endpoint; never compare endpoints with different inclusions. Neural profile's classifier deadline applies only to that profile, not this separate capability or downstream prepare. |
| Source acquisition | Explicit pinned source request → complete bound observed snapshot | Source reads, patch parsing/effects and scratch cleanup. Separate from pure selection cost even if an outer decision endpoint includes it. |
| Native preparation chain | External consumer request entry → fully validated prepare result/refusal plus required cleanup | Acquisition, IR decision, expected-tree construction, handoff re-acquisition/revalidation, fresh native check, and prepare which verifies again; service/stdio framing, evidence retrieval/validation and cancellation/cleanup where applicable. Includes repeated checks, not just the classifier. |

Existing neural deadline values and T024's 271.871 ms median have different observation boundaries/populations and cannot be promised for the native prepare chain. Do not reset a decision budget at each stage or carry a narrow classifier deadline forward as if all dependent Git/transport work shared its proven latency.

## DDP-T01 budget contract and DDP-T06 telemetry

Freeze separate explicit caller/coordinator-selected budgets before implementation acceptance:

- `decisionBudgetMs`: deadline for the declared layer-1 decision boundary.
- `acquisitionBudgetMs`: cap for the acquisition component, with precise inclusion in any enclosing budget.
- `prepareBudgetMs`: end-to-end consumer request cap, including nested phases and cleanup handling. A parent absolute deadline constrains each remaining stage; nested caps cannot enlarge or reset it.
- Per-stage limits for tree construction, revalidation, native verification, native prepare, evidence/frame processing and cleanup; include bounds for process cancellation/termination, bytes, operations and scratch resources. If the existing prepare API cannot enforce termination within a cap, label it observed-only/unsupported for that guarantee and keep that acceptance gate open. A timeout response alone does not prove work stopped.

Numeric envelopes are intentionally unresolved: T025 results are pending and owner/coordinator must select useful enforceable bounds from evidence. DDP-T01 freezes fields/semantics and refusal policy; coding can use explicit small test-fixture budgets without claiming product support. DDP-T06 cannot close with an implicit/unbounded prepare budget. No arbitrary fixed value is inferred from three observations. This is a proposed separate envelope, never new keys inserted into decision-stdlib-v1 or existing native request contracts without review.

For every positive, defer, refusal, timeout and cancellation path record monotonic durations/status for source acquisition; IR parsing; deterministic verification; selection; expected-tree construction; handoff re-acquisition/revalidation; fresh native check; native prepare/reverification; transport serialization and evidence chunk read/validation; cleanup. Distinguish independent intervals from nested spans; total entry-to-result is observed directly, not a sum that double counts nested work. Record entry-to-cleanup separately when cleanup extends past response. Unmeasured phases are null, never invented zero. Include exact contract/IR/verifier/policy/source/request/consumer bindings and work/byte counters in a bounded **local test evidence receipt**, not private contents in existing telemetry.

Reuse existing metadata observer allowlists and bounded buffers. Detailed per-stage receipts may live in local test evidence without expanding `s1-stage-observation-v1`. Do not silently add fields to that existing wire version, enable storage/export, or claim a new telemetry backend. Any production telemetry extension needs its own version/size/privacy review.

Required negatives: decision timeout does not start prepare; insufficient remaining prepare budget refuses the next phase; cancellation suppresses late publication and cleans scratch; malformed pins refuse before native side effects; every repeated verifier invocation is counted; incomplete stage measurement remains unknown; response deadline cannot hide an active worker/process.

## Reuse is a separate optimization, never a skipped gate

Initial baseline keeps the existing fresh checks. Do not remove re-acquisition, fresh native checks or native prepare verification merely to meet a time target. Any future observation/proof reuse requires an explicit reviewed reuse contract: exact immutable source/base/patch/goal/option/IR/verifier/observation identities, consumer/request scope, verified complete evidence, freshness checks at use, invalidation and negative controls. Timestamps or matching a producer hash alone do not establish freshness. Changed source, dependency, policy, verifier or consumer binding must reject reuse and follow the authorized fresh path or safely defer within budget.

A prospective cache optimization is not part of T06 acceptance unless separately scoped and reviewed. Report latency/cost of the complete path at matched outcomes before any future speedup claim. Present pending or negative utility as such.
