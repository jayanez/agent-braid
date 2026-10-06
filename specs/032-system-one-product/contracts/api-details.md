# SPEC-032 closed API amendment proposal

Status: Luna technical interface review GO; selected source implemented and under validation. SPEC-028/T008
bounded engineering prerequisites completed; human acceptance remains separate. All packets are deeply
immutable mappings; JSON arrays freeze to tuples and thaw only for serialization.
Core canonical bytes and lowercase SHA-256 digest rules apply. No interface admits
backend objects, registry objects, callbacks, imports, filesystem paths or execution
grants. Existing positive fixture packets retain their exact fields and meaning.

## Public signatures

```python
compile_schema(schema_bytes: bytes, *, cancellation: CancellationToken | None = None) -> Mapping
compiler_manifest() -> Mapping
route_metadata(request_bytes: bytes, *, expected_registry_digest: str,
               cancellation: CancellationToken | None = None) -> Mapping
router_registry_manifest() -> Mapping
router_capabilities() -> Mapping
ObservationBuffer(capacity: int = 64)
ObservationBuffer.record(response_bytes: bytes, *, request_bytes: bytes | None,
                         cancellation: CancellationToken | None = None) -> Mapping
ObservationBuffer.drain() -> Mapping
```

Bytes means exact built-in bytes, not arbitrary buffer/iterator/coercion. Invalid
input produces the fixed refusal packet; invalid ObservationBuffer capacity raises
ValueError with the constant message `invalid observation capacity`. Capacity must
be a built-in integer 1..64, excluding bool. No optional dependency is introduced.
A non-null cancellation argument must be a core CancellationToken instance;
otherwise raise TypeError with constant message `invalid cancellation token` before
request processing or buffer mutation. Return annotations describe frozen public
data, not a trusted constructor bypass.

## Compiler complete refusal envelope

Successful packets keep the seven fields already frozen by the contract and
positive corpus: contractVersion, schemaDigest, questions, bindings, evidenceClass,
executionAuthorization, packetDigest. They do not gain status or reasonCodes.
A refusal has exactly these eight fields:

```json
{"contractVersion":"s1-schema-synthetic-v1","schemaDigest":null,
 "questions":[],"bindings":[],"reasonCodes":["invalid-schema"],
 "evidenceClass":"heuristic","executionAuthorization":false,
 "packetDigest":"<sha256 of all other fields>"}
```

Exactly one reason is emitted from the existing fixed compiler reason allowlist.
Even an otherwise parseable unsupported schema has null schemaDigest: refusals do
not publish a partial validated schema identity. Parser failure is invalid-schema;
shape/keyword/reference/cycle/resource/collision/cancel/deadline failures retain
existing precise contract reasons. No partial questions/bindings or source text is
returned. Check pre-existing cancellation before parsing and deadline/cancellation
at traversal boundaries and before publication. Cancellation wins over deadline
when both are observed at the same publication check; otherwise the first terminal
validation failure wins. No global source text or labels appear in exceptions.

## Observation outcomes

Record outcome has exactly contractVersion (`s1-observation-outcome-v1`), status,
reasonCodes, droppedCount, evidenceClass (`heuristic`), executionAuthorization
(false), packetDigest. The digest binds all other fields.

| status | reasonCodes | droppedCount | mutation |
|---|---|---|---|
| recorded | [] | integer snapshot under acquired lock | append one validated immutable metadata record |
| dropped | ["buffer-full"] | incremented saturating signed-64-bit value | discard new record; increment only this counter |
| busy | ["busy"] | null | none; do not read shared counter without lock |
| refused | ["invalid-observation"] | null | none |
| defer | ["cancelled"] or ["deadline-exceeded"] | null | none |

Drain outcome has exactly contractVersion (`s1-observation-outcome-v1`), status,
records, droppedCount, reasonCodes, evidenceClass (`heuristic`), executionAuthorization
(false), packetDigest. On drained: status drained, insertion-ordered immutable
records array (possibly empty), captured integer droppedCount, reasonCodes []; the
buffer and counter are atomically cleared. On contention: status busy, records
null, droppedCount null, reasonCodes ["busy"]; no mutation or claim of zero loss.
Drain accepts no cancellation token because it performs only one nonblocking lock
attempt and bounded metadata copying; record owns the 5,000 ms ingress deadline.
Stored metadata allowlist remains exactly the existing contract/corpus, including
contractVersion of the observed core response. Outcomes never embed that response.

Record validates request/response and record size before lock acquisition. If the
lock is unavailable it returns busy immediately. After acquiring the lock it checks
expiry/cancellation before append or overflow-counter mutation. If cancellation is
supplied, final checking and mutation occur within core token.publish; this creates
an atomic cancellation/insert boundary. A cancellation after completed publication
does not retract the captured record. Lock release is exception-safe. Overflow
increments at most to 9223372036854775807. Invalid/busy/cancelled/expired calls do
not change this counter. No background work or retry exists.

## Deadline and deterministic test seams

Each compiler/router/record call captures time at materialized-byte ingress and
uses monotonic_ns. Compiler/record ceilings are exactly 5,000 ms; router uses the
validated deadlineMs 1..5,000 measured from the same ingress. At exact expiry
(`now >= deadline`) publication is suppressed. Parser work receives a check after
parsing; cooperative limits do not claim interruption inside the stdlib parser.
Final cancellation/publication uses token.publish when a token is supplied. Claim
and release the token around a call so concurrent token reuse is rejected by the
existing core convention; release on every terminal path. No core API changes.

The module-private `_monotonic_ns` binding may be patched by focused tests. It is
not a public argument, accepted JSON field, plugin or callback registration. Tests
supply finite deterministic times and barrier-controlled lock/token scenarios;
production uses the standard monotonic clock. Tests do not invoke feature code to
produce expected fixtures. Exact simultaneous cancel/expiry tests follow the
precedence rule above.

## Installed registry and fixture pin substitution

Production route_metadata has no registry/inventory/backend injection parameter.
Its sole inventory is immutable package-owned static metadata composed and reviewed
by root after the selected compiler bytes stabilize. The registry manifest exposes
exactly version, ordered routes and digest, with digest over version/routes only.
Every route retains the existing exact fields. Pin comparison checks both supplied
request registryDigest and consumer expected_registry_digest against that actual
digest before matching. A malformed consumer digest yields registry-pin-mismatch
with no route. Never overwrite a stale caller pin to make a request pass.

The selected wheel contains the compiler and declares only its real installed
s1-schema-synthetic-v1 metadata. Discovery performs no dynamic module import,
find_spec, installation, model loading or filesystem probing. Runtime metadata
pinning is package metadata consistency, not proof that a missing/tampered artifact
could execute; fresh-wheel origin/capability checks separately establish selected
installation. When package-owned metadata declares a capability unsupported, route
returns unavailable/capability-not-installed. Metadata never authorizes invocation.
Root owns final manifest composition and installed-wheel parity; workers must not
advertise a placeholder compiler as installed while another worker is editing it.

Tests use a module-private pure matcher taking a validated immutable registry as
an internal implementation seam, or patch the package-owned static registry binding
only inside the test. Neither seam is exported, reachable from public request bytes,
or a production metadata constructor API. Registry shape/digest validation applies
before the matcher; test malformed/forged route metadata does not bypass validation.
Public API tests additionally exercise actual installed metadata.

The frozen router corpus uses illustrative placeholder manifest pins. Its adapter
builds a separate derived request/registry view using real installed manifest digests
and recalculates valid fixture registry pins; it never rewrites corpus files or
expected classifications. It substitutes only declared valid placeholder pins.
Cases explicitly marked stale/forged retain deliberately unequal pins, and absent
capability cases use the private synthetic registry seam. Expected outcomes remain
matched/unavailable/refused/defer with the same fixed reasons, route identities,
strict policy, authority false and no dispatch. Assert this substitution mapping
explicitly; report fixture-adapted classification controls separately from actual
installed-package parity. Synthetic fixture metadata is never installation evidence.

## Ownership and handshake

Router worker owns system_one_router.py/test_system_one_router.py; compiler worker
owns system_one_schema.py/test_system_one_schema.py; hooks worker owns
system_one_hooks.py/test_system_one_hooks.py. Root owns shared installed metadata,
packaging and global profiles. No worker edits core028 or another worker's module.
031 owns its separate stage_registry_manifest/stage_capabilities interfaces and
never imports032;032 never imports031. Explicit consumers validate unchanged028
requests before evaluation and use compiler bindings for reconstruction only.
Compiler output creates no ruleAnswers, grant, scheduling change or NLP confidence.
