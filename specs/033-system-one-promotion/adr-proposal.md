# Feature-local architecture proposal: Shadow validation, promotion, drift and rollback

Status: Proposed, not adopted authority. Date: 2026-10-05.
Constitution Articles 5/6/7/12/13/14/19/20 remain binding.

Context: Operational engineering for opt-in shadow decisions, per-capability promotion, drift monitoring, rollback and bounded closure. No automatic online learning, external telemetry export, paid model calls or milestone closure.
Proposed decision: Use immutable registry manifests binding model/tokenizer/head/calibration/policy/capability and observation contract. Shadow mode cannot affect planning or execution. Compare complete decision chains against no-advisor baseline. Promotion uses separately recorded founder/operator scope and empirical budgets. Drift, out-of-domain input or integrity failures trigger deterministic fallback and reversible rollback; retraining is a separate reviewed offline candidate.
Consequences: explicit optional boundary, provenance, abstention and existing verifier/
grant semantics; increased maintenance and evaluation cost must be demonstrated.
Alternatives: rules, linear, encoder, decoder and no-model option evaluated through
SPEC-029. No constitutional change is requested. Adopt only after a separately
recorded architectural review; canonical ADR addition causes visible authority drift
and requires affected current records to be reviewed again, not silently refreshed.
