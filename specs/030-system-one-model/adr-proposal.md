# Feature-local architecture proposal: Own non-generative neural decision experiment

Status: Proposed, not adopted authority. Date: 2026-10-05.
Constitution Articles 5/6/7/12/13/14/19/20 remain binding.

Context: Implement and compare native decoder/pointer and encoder/option-scoring prototypes using approved base models. No Laya or Strands package, checkpoint, adapter, runtime service or copied corpus is a product dependency.
Proposed decision: A causal backbone with its language-model head removed scores dynamically provided option representations against a final decision representation. A bidirectional encoder alternative scores option markers with shared parameters. Train own heads/adapters. Compare frozen encoders, supervised cross-entropy, ordinal soft targets and narrowly approved distillation; add proper-scoring/reward training only through a separately preregistered ablation. Pointer addressing removes slot-specific weights but does not prove order invariance under causal positions.
Consequences: explicit optional boundary, provenance, abstention and existing verifier/
grant semantics; increased maintenance and evaluation cost must be demonstrated.
Alternatives: rules, linear, encoder, decoder and no-model option evaluated through
SPEC-029. No constitutional change is requested. Adopt only after a separately
recorded architectural review; canonical ADR addition causes visible authority drift
and requires affected current records to be reviewed again, not silently refreshed.
