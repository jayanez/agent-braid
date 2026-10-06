# Feature-local architecture proposal: Native typed advisory decision foundation

Status: Proposed, not adopted authority. Date: 2026-10-05.
Constitution Articles 5/6/7/12/13/14/19/20 remain binding.

Context: Engineering foundation for a local, non-generative, typed decision API with a deterministic reference backend. This milestone does not ship a pretrained general-purpose model.
Proposed decision: Use standard-library immutable records, strict JSON validation and a backend protocol. Keep optional ML imports outside core imports. The first rule backend returns explicit unknown or uncalibrated outputs where it lacks evidence. Implement a feature-local additive CLI namespace only after its contract is reviewed.
Consequences: explicit optional boundary, provenance, abstention and existing verifier/
grant semantics; increased maintenance and evaluation cost must be demonstrated.
Alternatives: rules, linear, encoder, decoder and no-model option evaluated through
SPEC-029. No constitutional change is requested. Adopt only after a separately
recorded architectural review; canonical ADR addition causes visible authority drift
and requires affected current records to be reviewed again, not silently refreshed.
