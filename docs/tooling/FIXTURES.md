# M4.5 owned synthetic fixture inventory

`examples/tooling/fixture-inventory.json` and `examples/tooling/prompts.json` are
fixed candidate inputs for prospective M4.5 evaluation preparation. They contain
18 independently identified fixture definitions, three per SPEC-044 journey
class, and six fixed English prompts. Twelve runtime classes use Git recipes:
three each for advisory planning, missing-grant refusal, granted-batch
inspection/verification, and interruption/recovery inspection. The analyze and
evidence-export classes each have three AIM 0.2 inputs, including independent,
conflicting, and explicitly unknown-coverage cases. These declared classifications
are deterministic oracles for the exact synthetic inputs, not scientific or
semantic-safety claims. Every fixture also pins scenario preconditions, phases,
expected outcomes, and context status.

The loader pins the complete file hashes and verifies canonical hashes for each
fixture definition and prompt. It reads at most 64 KiB for the fixture inventory
and 8 KiB for prompts before parsing. `load_inventory()` uses installed package
resources at `agent_braid/tooling_assets/fixtures`. Source JSON is available only
through the explicit `load_inventory(source_checkout=True)` path. `fixture_input()`
resolves an AIM request without filesystem effects and returns its immutable
definition hash and canonical input hash.

`materialize_fixture(inventory, fixture_id, destination)` is available only for
a runtime Git recipe. Before making a directory or Git object, it reconstructs
and rechecks the full pinned inventory, definition digest, runtime schema, IDs,
file names and all paths; frozen dataclasses alone do not freeze nested JSON.
The destination must be a new path under the canonical system temporary root.
The helper uses bounded Git commands, fixed author/committer metadata, isolated
home/temp directories and disabled hooks. It creates only an owned synthetic
repository with a base commit, two independent operation commits and the exact
expected final tree. The result exposes the validated runtime request and a
separate read-only Git analysis request. Its root manifest returns fixture ID,
journey class, definition hash, materialized request hash, base commit, final
tree, operation commits and created paths.

The immutable recipe hash is separate from the materialized request hash. The
resolved request includes the selected temporary root and generated Git object
IDs. Runtime prepare validation can consume this request without executing the
batch or creating a run directory; the focused parity test checks that prepared
plan through the core runtime and adapter matches. Materialization creates no
grant and runs no product operation. The execute scenario is only request-ready:
it separately requires an operator-supplied, existing, exact plan-and-destination
bound grant. A missing or mismatched grant must refuse; the fixture helper never
issues one. The recovery scenario additionally requires an existing interrupted
run, its current inspected state, and a matching already-issued recovery grant.
Those contexts are not included in the request recipe, so materialization alone
is not a complete execute or recovery journey.

Focused offline tests separately create grants in private temporary directories
using the existing operator-grant API, and exercise one synthetic execute/verify
sequence and one controlled interruption/recovery/verify sequence. They establish
that these code paths work on those test-owned synthetic inputs; they are not
host sessions, captures, provider observations, or acceptance evidence.

Materialization does not run Agent Braid runtime operations, apply patches,
checkout branches, access repository source code, contact a provider, or perform
a capture. It creates no remote, hook, host configuration, or installation root.
The production fixture module does not import tests. The fixed prompts preserve
unknown coverage and provenance, require clear authority boundaries, prohibit
grant creation/inference, and make no claim that observation or acceptance has
occurred.

The inventory is not a source-rights record or an approved capture registration.
Owners must separately review fixture rights, select the exact candidate/hosts,
set numerical caps, freeze prompts and rubric, and obtain the applicable
registration and capture decisions before any observation. No 108-arm capture is
performed by these definitions or tests.
