# SPEC-032 deterministic product subset

Status: feature-local proposal awaiting byte-bound Luna review. This document
selects branches for a future implementation, not task completion, human review,
utility acceptance or capability promotion. The exact boundary is the
[product contract](contracts/product.md). SPEC-028 architecture review does not
complete its still-required T008 PR profile and fresh installed-wheel checks.

| Extension | Disposition | Supported domain / envelope | Prerequisites and reconsideration |
|---|---|---|---|
| Schema compiler (T004) | Selected | Structural local schema subset into 1..32 boolean/choice/score questions; no free-form generation | SPEC-028/T008; this contract review; finite schema/refusal controls |
| Core hooks/offline packaging (T007) | Selected | Data-only immutable metadata capture/pull, no arbitrary callback; stdlib core plus selected modules in fresh offline wheel | SPEC-028/T008; contract review; installed artifact parity; no model selection needed |
| Metadata routing (T003) | Selected | Explicit caller-declared en/es and fixed synthetic task ID allowlists against pinned installed capability manifests; no text detection/confidence/model dispatch | SPEC-028/T008 and exact rule-router technical review; learned routing remains SPEC-030/T008 gated |
| CPU export/quantization (T002) | Deferred | No learned artifact/tokenizer/operator or measured device envelope selected | Exact SPEC-030/T008 model, rights, backend parity and measured resource envelope |
| Catalogue retrieval/tournament (T005) | Deferred | No pruning, conditional probability or recall claims selected | SPEC-029/T009 prospective evidence plus exact catalogue contract; learned scorer additionally SPEC-030/T008 |
| Token batching/model lifecycle (T006) | Deferred | Reference core admission remains one active/eight waiting, not neural serving support | Selected SPEC-030/T008 artifact and reviewed model memory/cache/termination envelope |
| Per-feature packet (T008) | Selected future deliverable | Report only declared-router/compiler/hooks/packaging evidence and deferred reasons | Completed selected T003/T004/T007 and their gates; no whole-spec or SPEC-033 promotion |

CPU/device matrix for this proposal is CPython >=3.12 stdlib on the existing
owned POSIX filesystem domain, with Linux/macOS evidence planned separately.
No measured throughput, memory ceiling, GPU/Windows support, tokenizer, neural
context window or export speedup is asserted. Software allocation is bounded by
input/question/ref/queue limits, not by a claimed kernel memory sandbox.

The router matches declared metadata labels only; en/es labels do not establish
English/Spanish understanding or validated real-language coverage. Unknown, absent
and mixed tags return unavailable; stale manifest pins refuse. It never inspects
text, computes confidence or imports/executes a model.

The compiler produces typed structural questions and a value/pointer table. It
neither evaluates a natural-language question nor validates a generated instance.
The existing synthetic core receives only explicit caller fixture answers after
ordinary request validation; instructions/descriptions have no learned meaning.
Ordinal score values preserve a supplied ordered finite rubric, not confidence.
Nullable enum values preserve null as an explicit option; missing optional fields
are not flattened into null. Optional properties are outside the selected subset.

Hooks use an explicit pullable metadata buffer, not an arbitrary callback API.
This avoids falsely promising hard termination of Python callbacks. Custom observer
code, transport export and live instrumentation are deferred; their acceptance
requires a separate worker/termination/privacy contract. Data capture is independent
of SPEC-031's separately implemented MCP/telemetry chain and cannot complete SPEC-031/T007.

Selected branch implementation may proceed once SPEC-028/T008 and the exact
contracts are reviewable. Its software checks do not require neural source rights,
training, calibration or prospective workload utility. Conversely, they cannot
satisfy SPEC-029 label/evaluation decisions, SPEC-030 model selection or SPEC-033
promotion. Deferred task boxes and their empty evidence remain unchanged. A packet
can complete a scoped engineering cut while whole SPEC-032 remains pending.
