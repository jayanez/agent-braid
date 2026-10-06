# Proposed ADR: capability-specific runtime refinement

Status: proposed only; founder adoption pending. No canonical authority is changed.

Problem: private Git result evidence and existing grants do not justify source
publication, project-code checks or external writes. Reusing them would extend
observation and execution scope without verified premises.

Proposal: keep three independently reviewed capability contracts. Source promotion
requires verified result material, exclusive revalidation/CAS and a separate grant.
Code checks require enforceable resource/credential/network isolation demonstrated
by separately authorized harmless probes. External writes require explicit attempts,
idempotency semantics and uncertainty-preserving recovery. Unsupported capabilities
remain NO-GO with read-only/manual fallbacks.

Alternatives: manual integration; offline analysis; abstract failure simulation;
no expanded execution capability. Current assessment prefers these fallbacks until
capability evidence and founder adoption exist. Costs and utility of a later
implementation need their own candidate-bound measurements. M4 remains open and
SPEC-021 NO-GO stays unchanged.
