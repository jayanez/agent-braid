# Feature-local architecture proposal: CPU, multilingual and structured decision capabilities

Status: Proposed, not adopted authority. Date: 2026-10-05.
Constitution Articles 5/6/7/12/13/14/19/20 remain binding.

Context: Independently implement useful product patterns observed in Laya: CPU optimization, multilingual routing, schema-derived questions, large-catalogue retrieval, batching, lifecycle control and telemetry hooks. Defer browser automation, vision, email parsing, multiple language SDKs and framework-specific adapters until demand and evidence justify separate specs.
Proposed decision: Add optional backend exports with reference parity. Language and task routing use declared support and validated metadata before confidence; unsupported or mixed input defers. Schema compiler supports boolean/enums/ordered rubrics only and rejects arbitrary generation. Shortlisting and tournament plans report all candidates, dropped labels, finalist identity and conditional probabilities. Hook observers cannot mutate sealed inputs or grant authority.
Consequences: explicit optional boundary, provenance, abstention and existing verifier/
grant semantics; increased maintenance and evaluation cost must be demonstrated.
Alternatives: rules, linear, encoder, decoder and no-model option evaluated through
SPEC-029. No constitutional change is requested. Adopt only after a separately
recorded architectural review; canonical ADR addition causes visible authority drift
and requires affected current records to be reviewed again, not silently refreshed.
