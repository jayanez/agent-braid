# SPEC-031: Interface and compatibility proposal

Use the [native v1 decision envelope](../../028-system-one-core/contracts/decision-api.md).
No /v1/systemone or Jev compatibility claim is required; public transport aliases
would need separate conformance/migration decisions. Native logical primitive names
are boolean/choice/score; an optional adapter may translate `noul` explicitly.

Feature boundary: Expose native System 1 recommendations for every architectural stage through an explicit registry of capabilities. Only enabled, evidenced consumers are integrated; arbitrary host actions and runtime scope expansion are excluded.
Dependencies: SPEC-028 accepted contracts; implementation can use a rule backend while SPEC-030 research remains pending. Live learned use waits for SPEC-030 selection and SPEC-033 promotion.
Every returned decision identifies model, calibration, context and policy; unsupported
versions/fields or stale resources refuse. Decisions cannot change existing certificate,
execution grant, manifest, scheduler, observation or recovery contract. Legacy commands
operate without System 1; optional dependencies never load from core import paths.

Prospective acceptance is [validation-plan.md](../validation-plan.md); no implemented
contract is certified here. New public schema files must use reviewed versioning and
migration notes before integration, rather than updating existing versions in place.
