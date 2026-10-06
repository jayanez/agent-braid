# SPEC-030: Research and alternatives

A causal backbone with its language-model head removed scores dynamically provided option representations against a final decision representation. A bidirectional encoder alternative scores option markers with shared parameters. Train own heads/adapters. Compare frozen encoders, supervised cross-entropy, ordinal soft targets and narrowly approved distillation; add proper-scoring/reward training only through a separately preregistered ablation. Pointer addressing removes slot-specific weights but does not prove order invariance under causal positions.

Primary evidence: [immutable source analysis](../028-system-one-core/reference-analysis.md)
and [source manifest](../028-system-one-core/reference-sources.json). Upstream reported
metrics were not reproduced. Architecture claims and reusable patterns are separated
from known defects and unsupported benchmark comparisons.

Proposed choice: own non-generative neural decision experiment. Alternatives: preserve current behavior,
rules, SPEC-019 linear advice in its eligible domain, compact encoder, causal pointer
head or System 2 fallback with a declared cost boundary. Decision criterion: supported
domain, calibrated selective risk, complete cost and memory at matched coverage/verifier
budget. No option is excluded because it differs from the requested reference order.

No sufficient real workload corpus is currently established. Start with conformance
fixtures to build tools; do not count them toward source yield or product utility.
Feature expansion and base artifact choice remain gates in tasks and the shared protocol.
