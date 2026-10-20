# Research decisions — SPEC-048

The [pinned audit](../../research/harness2-source-audit.md) is the shared source record. The [program](../048-harness-variant-laboratory/program.md) owns delivery order; the [idea](../../docs/ideas/harness-improvement.md) owns the agreed product scope.

Decision: Provide a native Agent Braid mechanism to propose, probe and compose small task-local harness variants against an immutable base, first with deterministic fixtures and later through separately qualified Codex/Claude adapters.

Selected reuse: adapt source symbols and architectural seams from the pinned upstream under the [adaptation map](../048-harness-variant-laboratory/upstream-adaptation.md). No clean-room rewrite is required; preserve provenance, notices and Agent Braid semantics.

Alternatives and limits: importing Harness² wholesale would carry execution assumptions and third-party benchmark dependencies that the initial owned-repository pilot does not need. Advisory-only analysis remains a useful fallback when native isolation/source/route gates fail. Unrestricted self-modification and training are deferred. Future automatic promotion remains a separately evaluated option.

Evidence required to revisit: both-axis paired outcomes at frozen quality/effect constraints, complete costs, source/host provenance, negative controls and per-profile promotion decisions. The five passing upstream deterministic tests are evidence about those upstream controls only.
