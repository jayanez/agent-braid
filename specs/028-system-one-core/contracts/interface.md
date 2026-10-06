# SPEC-028: Interface and compatibility proposal

Use the [native v1 decision envelope](../../028-system-one-core/contracts/decision-api.md).
No /v1/systemone or Jev compatibility claim is required; public transport aliases
would need separate conformance/migration decisions. Native logical primitive names
are boolean/choice/score; an optional adapter may translate `noul` explicitly.

Feature boundary: Engineering foundation for a local, non-generative, typed decision API with a deterministic reference backend. This milestone does not ship a pretrained general-purpose model.
Dependencies: None; preserve SPEC-018/019/020/021 boundaries.
Every returned decision identifies model, calibration, context and policy; unsupported
versions/fields or stale resources refuse. Decisions cannot change existing certificate,
execution grant, manifest, scheduler, observation or recovery contract. Legacy commands
operate without System 1; optional dependencies never load from core import paths.

Prospective acceptance is [validation-plan.md](../validation-plan.md); no implemented
contract is certified here. New public schema files must use reviewed versioning and
migration notes before integration, rather than updating existing versions in place.
