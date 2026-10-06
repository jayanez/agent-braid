# Feature-local architecture proposal: Advisory integration across Agent Braid decision stages

Status: Proposed, not adopted authority. Date: 2026-10-05.
Constitution Articles 5/6/7/12/13/14/19/20 remain binding.

Context: Expose native System 1 recommendations for every architectural stage through an explicit registry of capabilities. Only enabled, evidenced consumers are integrated; arbitrary host actions and runtime scope expansion are excluded.
Proposed decision: Build an adapter-specific immutable decision context and capability registry. First integrate read-only candidate priority and analyzer selection. Then effect-review suggestions, model/tool shortlists, adequacy scoring and diagnostic categorization. The current scheduler can consume priority hints only after its exact constraints are preserved; executor selection is limited to supported fixed-patch policies. Deterministic gates verify parameters, effects, enabledness, versions and grants.
Consequences: explicit optional boundary, provenance, abstention and existing verifier/
grant semantics; increased maintenance and evaluation cost must be demonstrated.
Alternatives: rules, linear, encoder, decoder and no-model option evaluated through
SPEC-029. No constitutional change is requested. Adopt only after a separately
recorded architectural review; canonical ADR addition causes visible authority drift
and requires affected current records to be reviewed again, not silently refreshed.
