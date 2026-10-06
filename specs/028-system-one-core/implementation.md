# SPEC-028 standard-library reference implementation

This implements the technically reviewed [reference profile](contracts/stdlib-v1.md)
for synthetic fixture decisions only. It supplies no learned model, calibration,
source admission, workload benefit, scientific acceptance or execution authority.
Feature acceptance and promotion remain separate. Legacy exports are unchanged.

## API

`agent_braid.system_one.evaluate(raw: bytes, *, cancellation=None) -> dict`
creates an isolated runtime for one already-materialized UTF-8 JSON request.
For repeated or concurrent requests, instantiate
`agent_braid.system_one_backends.DecisionRuntime(clock=monotonic_ns)`
and call its `evaluate(raw, cancellation=token)`. Caller-selected backend injection is not a supported API. Concurrency tests replace
private collaborators explicitly; those test outputs make no source-provenance claim.
The production default lazily constructs the stateless rule fixture backend only
for a valid admitted diagnostic request. No network, artifact, ML package or
resource loader is used. Missing mappings and the strict uncalibrated policy
abstain before backend construction.

`validate_request(raw)` returns a frozen `DecisionRequest`, including frozen
nested envelope/state, typed questions/options/budgets, canonical bytes and
render accounting. `validate_response(payload, request=request)` independently
checks field sets, provenance, authority, status, distribution and derived
readouts and returns a frozen `DecisionResponse`. Both records provide
`to_dict()` with fresh mutable JSON containers. Mutating a returned dictionary
cannot affect another request or a retained validated record.
`canonical`, `digest` and `build_answers` provide the reference serialization,
input commitments and independently derived distribution readouts. Normalized
entropy concentration and maximum uncalibrated mass are separate fields.

`capabilities()` (module or runtime method) returns a deeply immutable mapping.
Use `system_one.thaw` to obtain fresh JSON containers for serialization.
`admission_snapshot()` is an immutable diagnostic observation of active/waiting/
closed state. `close()` refuses new admission, wakes queued requests to defer,
and cooperatively cancels active work. Context-manager exit calls `close()`.
Closing does not claim to kill a stalled backend or release active resources.

`CancellationToken.cancel()` is irreversible and wakes registered waiters.
A token cannot be reused concurrently across requests; this API programming
error raises `ValueError` before admission. Sequential use of an already
cancelled token yields explicit defer. Cancellation arriving before the locked
publication boundary suppresses recommendations; cancellation after publication
cannot revoke the returned response. The admission slot is retained until
backend work actually stops. There is no global runtime, background worker,
shared result cache, retry, neural/device envelope or hard-kill promise.

## Boundaries and observations

Validation rejects duplicate JSON members, invalid UTF-8/BOM/surrogates,
nonfinite or out-of-range numbers, unsupported identity, extra fields,
duplicate IDs, malformed rubrics and over-budget payloads. Container depth is
checked before JSON parsing while respecting quoted/escaped strings. Canonical
bytes and the complete envelope's character-token count are checked against
caller ceilings before admission. State digest is recomputed; a caller's digest
is never treated as authority or source authenticity.

One evaluation and at most eight waiting valid requests are admitted per
explicit runtime. Request-local frozen inputs, renderer accounting, cancellation
and response buffers are isolated. Monotonic deadline starts at materialized-byte
API ingress, includes validation, queueing, rendering, backend/policy and response
construction; completed answers are suppressed if the deadline expires before
publication. Total timing is sampled at final commitment; no accuracy/latency or
production throughput claim follows from counters. External file/source I/O is
outside this API deadline. Threads only cooperate; unsupported hard termination
is not implied by a timeout or cancellation.

Every response denies execution authorization, reports heuristic evidence and
absent calibration, and carries no calibratedProbability, certificate or grant.
Valid diagnostic fixtures may answer; the strict default abstains. Invalid
requests produce a bound sanitized refusal with null unvalidated caller identity
and input/manifest digests; only a fixed reason code and bounded accounting are
returned. Backend output or ordinary backend exceptions fail closed without
publishing raw exception text and release the admission slot after the work stops.

## Focused verification

Separate checkout preflight passed before implementation, with zero-output
`git fsck --full`. The isolated Python 3.13.11 command was:

```sh
/tmp/agent-braid-parallel-20261006/.venv-speckit/bin/python -m unittest \
  tests.test_system_one_core tests.test_system_one_backends \
  tests.test_system_one_policy tests.test_system_one_concurrency -v
```

The executed focused candidate run passed **27 tests**. Controls include exact
1 MiB and 32-question/32-option boundaries, byte-counted Unicode identities,
finite JSON/depth/duplicate rejection, bool-as-number, stale provenance, malformed
score rubrics, uniform/one-hot concentration and stable ties, deep isolation,
full-batch abstention, authority forgery and lazy backend construction. Barrier,
event and injected-clock tests verify one active evaluation, eight waiting plus
ninth overload, queued/active cancellation, same-token misuse, queued expiry,
close, independent options/state and suppression after response construction
crosses the deadline. Tests use no neural inference, private source or network.

Four isolated in-memory mutations were detected: removing authority validation
and a manifest pin each caused one assertion failure in their focused test;
making strict abstention unconditional caused its diagnostic-control assertion
to fail; removing strict abstention caused the independently validating response
boundary to raise a contract exception in the default-policy test. No shared
source file was mutated for these checks. Full profiles, CLI integration,
independent Luna code review and final evidence binding are coordinated separately.
