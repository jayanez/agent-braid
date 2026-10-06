# SPEC-032: Interface and compatibility proposal

Use the [native v1 decision envelope](../../028-system-one-core/contracts/decision-api.md).
No /v1/systemone or Jev compatibility claim is required; public transport aliases
would need separate conformance/migration decisions. Native logical primitive names
are boolean/choice/score; an optional adapter may translate `noul` explicitly.

Feature boundary: Independently implement useful product patterns observed in Laya: CPU optimization, multilingual routing, schema-derived questions, large-catalogue retrieval, batching, lifecycle control and telemetry hooks. Defer browser automation, vision, email parsing, multiple language SDKs and framework-specific adapters until demand and evidence justify separate specs.
Dependencies: SPEC-028/029 contracts and evaluation; learned extensions require SPEC-030 selection. No advanced feature is an MVP prerequisite.
Every returned decision identifies model, calibration, context and policy; unsupported
versions/fields or stale resources refuse. Decisions cannot change existing certificate,
execution grant, manifest, scheduler, observation or recovery contract. Legacy commands
operate without System 1; optional dependencies never load from core import paths.

Prospective acceptance is [validation-plan.md](../validation-plan.md); no implemented
contract is certified here. New public schema files must use reviewed versioning and
migration notes before integration, rather than updating existing versions in place.

Large catalogue input needs a separately reviewed catalogue envelope, not an oversized
v1 question. Proposed initial catalogue limit: 256 stable-ID entries within the same
1 MiB serialized ceiling. Each group/finalist decision still obeys v1's 32-option cap;
initial tournament groups contain at most 16 entries. A schema enum over 32 labels
must explicitly use this envelope or refuse. Catalogue/shortlist/group/finalist hashes,
retrieval strategy and dropped labels are returned with the conditional distribution.
No context enlargement or silent token budget change is inferred from catalogue size.

An observation hook timeout alone does not stop a Python callback. Restrict the native
interface to immutable metadata and bound queue/workers; for hard termination use an
isolated worker process. Hooks cannot mutate active requests, see private content by
default, register backend code implicitly or acquire authority through returned values.
