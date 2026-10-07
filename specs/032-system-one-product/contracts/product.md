# Deterministic product subset contract v1

Status: technically reviewed contract with selected implementation under validation;
no human acceptance or empirical utility evidence. This proposal selects declared-metadata routing, schema compilation and data-only
hooks/offline packaging from SPEC-032's independent branches. It uses SPEC-028's
[stdlib profile](../../028-system-one-core/contracts/stdlib-v1.md) without changing
existing decision versions, identities, manifests, strict abstention or authority.
[Product decisions](../product-decisions.md) identify every deferred branch.

## Schema compiler interface and bounds

Proposed pure API `compile_schema(schema_bytes) -> immutable compiled packet`
accepts materialized UTF-8 bytes under the exact stdlib parser/canonical profile:
1,048,576 inclusive raw/canonical bytes; duplicate-member rejection; container
depth 16; finite binary64/signed-64-bit numbers; no Unicode normalization. It
performs no I/O, reference download, import, plugin dispatch or model call.

Compiler traversal visits at most 256 schema-node occurrences, follows at most
16 local-reference edges on one expansion path and emits 1..32 questions. Track
active reference targets to refuse cycles before expanding them; repeated acyclic
reuse is permitted but charged to the occurrence budget. No partial packet is
returned for any unsupported field, budget overrun or reference failure. Deadline
is 5,000 monotonic milliseconds from materialized-byte ingress, checked during
traversal and before publication; cancellation suppresses all questions. Hard
CPU termination is not claimed. These limits bound work, not OS peak RSS.

Accepted structural node shapes are exact; additional keywords refuse rather
than silently changing meaning. An optional root `$schema` must equal
`https://json-schema.org/draft/2020-12/schema` and is a dialect label, never a URL
retrieval. Any `type: object` schema node may contain `$defs` with at most 128 named schema nodes;
all definition nodes receive structural keyword/type/reference validation before
emission, even if unused. The combined syntax/expansion visit counter is capped
at 256. Reject reference cycles in the document graph before question traversal;
only referenced definitions contribute emitted questions. Definition/property names are nonempty, have no controls or lone
surrogates and contain at most 256 UTF-8 bytes.

| Node shape | Required fields and meaning |
|---|---|
| Object | Exactly `type: object`, `properties`, `required`, `additionalProperties: false`, plus optional `$defs`; at least one property and every supplied property required, with no duplicate or unknown required names |
| Boolean leaf | Exactly `type: boolean`; two options `false`, `true` in that order |
| Enum leaf | Exactly `enum`, optionally `type`; 2..32 unique finite scalar labels (string <=256 UTF-8 bytes, number, boolean or null), no object/array labels; supplied type must match every label or explicitly include `null` in a two-element type array |
| Ordinal leaf | Exactly `type: integer` or `number`, `enum`, `x-agent-braid-ordinal: true`; 2..32 strictly increasing numeric values in supplied order, excluding booleans, magnitude <=1,000,000 |
| Reference | Exactly `$ref`; nonempty local fragment JSON pointer beginning `#/`, with strict `~0`/`~1` decoding, resolving to an existing schema node in this same document; no siblings, remote/file references, percent-encoded interpretation or dynamic reference |

Nested objects and nested local refs are supported within those bounds. Arrays,
optional properties, unrestricted strings, null-only/singleton enum, recursive
schemas, unions/composition/conditionals, patterns/formats/defaults and unknown
annotations (including title/description) refuse precisely. Nullable enums carry
explicit null option values; omission is unsupported and never equated to null.
Enum uniqueness uses JSON value meaning: equal numeric values such as 1 and 1.0
are duplicates; booleans are a distinct type from numeric values; Unicode strings
compare without normalization. Mixed enums without a supplied type preserve each
scalar type in the option mapping. A provided type array is supported only for
one scalar type plus null and only when both occur in the enum.

Traverse object property names in Unicode code-point order, preserving enum and
ordinal array order. Emit canonical escaped JSON instance pointers (`~` -> `~0`,
`/` -> `~1`) and original schema pointers, including the referenced target pointer.
For expansion without a reference, schemaPointer is the actual leaf node's canonical document pointer, equal to resolvedSchemaPointer. On entering the first $ref during an instance-path expansion, capture that reference node's document pointer as the original source. Preserve this captured schemaPointer through chained references and every descendant emitted from a referenced object, including descendants reached through further references. resolvedSchemaPointer always names the final actual leaf node in the supplied document. The capture ends when that referenced subtree's expansion returns; a sibling expansion establishes its own origin. Never synthesize a document pointer by appending property segments to a reference node. instancePointer follows the emitted instance path and, with schemaPointer, binds each question ID; resolving a reference never changes the instance path.

A question ID is the full 64-character lowercase SHA-256 hex digest of canonical
`{"instancePointer": ..., "schemaPointer": ...}`. Enum/score option IDs are the
full SHA-256 hex digest of canonical `{"type": <scalar-kind>, "value": ...}`;
boolean IDs remain the required literal `false` and `true`. Check generated ID
collisions and refuse them even if cryptographically unlikely. Nonordinal enum leaves compile to `choice` even when their scalar labels are
boolean; the exact `type: boolean` leaf shape compiles to `boolean`. No truncation,
secret identity replacement or pointer alias guessing is allowed.

Instructions are the fixed structural string `Select the explicit schema value.`;
boolean option descriptions are `false`/`true`. Enum/score descriptions are canonical
JSON scalar text, bounded by core's 4,096-byte limit. Score options additionally
carry the exact supplied numeric `value`. Do not treat descriptions as prompts
or infer ordinal values from label positions. Question and option types/limits
remain those of the core profile.

The compiled packet contains exactly `contractVersion: s1-schema-synthetic-v1`,
`schemaDigest`, `questions`, `bindings`, `evidenceClass: heuristic`,
`executionAuthorization: false`, `packetDigest`. Bindings, in question order,
contain exactly `questionId`, `instancePointer`, `schemaPointer`,
`resolvedSchemaPointer`, `options`; options, in supplied order, contain exactly
`optionId`, `scalarKind`, `value`. Packet digest binds every other field using
core canonical bytes. `schemaDigest` binds the entire canonical supplied schema.
Consumers reconstruct values from this table and validate ordinary core requests;
no schema field creates a ruleAnswer or grants permission to answer.

Compiler refusal returns no questions/bindings, null unvalidated schemaDigest and
fixed reason codes `invalid-schema`, `unsupported-keyword`, `unsupported-shape`,
`invalid-local-reference`, `reference-cycle`, `compiler-budget-exceeded`,
`id-collision`, `cancelled`, `deadline-exceeded`. Never echo raw schemas, labels,
field names, URLs or parser exceptions in refusal diagnostics.

## Data-only observation hooks

Proposed API `ObservationBuffer(capacity=64)` has only `record(response_bytes, *, request_bytes)` and `drain()`; no callback/register/import/endpoint interface. Capacity is an
explicit integer 1..64, booleans refused. It holds immutable nested metadata with
at most 64 records and at most 1,024 canonical bytes per record, owner-local lock
protection and no background worker/thread/process. It does not own core admission.

`record` validates bounded materialized UTF-8 response bytes with the core parser
and response validator. Supply the matching request bytes for a bound response;
revalidate those bytes and compare all core request/manifest/response pins.
`request_bytes: null` is permitted only for the exact core pre-validation refusal
shape with null identities/digests. Each raw/canonical document is capped at
1,048,576 bytes; core question/options/type/numeric invariants remain unchanged.
A caller-supplied `verified` flag or dataclass constructor does not bypass these
checks. Validation is same-engine structural consistency, not authentication of
who evaluated the response. No core backend is admitted by this operation.
Store exactly `contractVersion`, responseDigest, backendId, capabilityId, policyId,
status, reasonCodes, usage, evidenceClass and executionAuthorization. Null identity fields are permitted for actual core input
refusal. No state, instructions, descriptions, options, answers, operation/resource
IDs, prompts or filesystem paths enter the buffer. Validate size and immutable
response identity before insertion. Returned values cannot alter active requests
or grant authority. Caller mutation after record cannot affect stored metadata.

Recording/parsing uses a 5,000 ms monotonic cooperative ceiling and cancellation
checks before insertion; invalid, expired or cancelled data inserts no record and
returns fixed `invalid-observation`/`deadline-exceeded`/`cancelled`. `record` is
called explicitly outside core evaluation; there is no automatic observer on its
critical path. Lock acquisition is nonblocking; contention returns explicit `busy` with no
insertion or counter update. The caller observes the refused record and may decide
whether to retry; the buffer never retries or claims that record was captured.

Overflow drops the new observation, increments a saturating signed-64-bit dropped
counter and never blocks core evaluation. No oldest-record eviction or retries.
`drain` attempts the same nonblocking lock. If unavailable it returns an explicit
`busy` result with no records/counter and leaves the buffer unchanged. Otherwise
it atomically returns insertion-ordered immutable records and the dropped counter,
then clears that owner-local buffer/counter. Overflow counts only capacity drops while the lock is held; busy
refusals are separate explicit call outcomes, not silently counted as captured
or claimed as zero-loss delivery. A consumer may copy this
metadata; no automatic storage/export is selected. Record/drain are bounded data
operations, not hooks executing untrusted code. Arbitrary callback mutation/stall
cases are rejected as unsupported interface use, not handled by a fake thread
kill. Process-isolated extensible callbacks need a separate reviewed contract.

## Offline packaging and compatibility

The selected wheel contains the exact core/reference backend/policy, declared-router, compiler and
observation modules implemented for this cut, with stdlib runtime dependencies
only. Discovery advertises only installed selected capabilities; deferred neural,
export, catalogue, learned router and lifecycle backends are absent or unsupported. No
extras may claim availability from a placeholder module or missing artifact.
Core import loads no optional provider/ML package and triggers no network install.

Build the reviewed candidate using an already available isolated build environment,
then install its exact SHA-256-pinned wheel into a fresh isolated environment with
`--no-index --no-deps`. Missing local build/runtime prerequisites are an explicit
blocked check, never fetched silently. Test imported symbol origin against that
fresh installed wheel while running outside the checkout; verify package metadata,
discovery/manifests, one strict abstention request, one explicit diagnostic fixture,
compiler outputs and hook buffer/refusal controls. Pin Python/platform, wheel hash,
actual commands/outcomes and excluded optional capabilities. Reproducible import
and functional parity are software evidence, not scientific or utility results.

Acceptance controls include refs/cycles/escaping, nullable/duplicate enum meaning,
ordinal order/value preservation, optional-field refusal, exact limits, malicious
schema strings, deep mutation, queue overflow/concurrent drain, dependency absence,
wrong-origin imports and installed-wheel capability parity. Leave deferred SPEC-032
scenarios and their tasks pending; selected-subset packet acceptance does not
complete the whole feature or authorize SPEC-033 promotion.


## Declared-metadata rule router (T003)

Proposed pure API `route_metadata(request_bytes, *, expected_registry_digest,
cancellation) -> immutable routing packet` performs deterministic metadata matching
only. Exact request fields are `contractVersion: s1-metadata-router-v1`, `requestId`,
`sourceKind: synthetic`, `languageTag`, `taskId`, `registryDigest`, `deadlineMs`.
All fields required; extra keys refuse. languageTag is a string or null, taskId
is a core-format ID or null; requestId follows core-format identity bounds.
Digest fields are 64 lowercase hex; deadlineMs is an explicit integer 1..5,000,
excluding boolean. Apply core raw/canonical 1 MiB/depth/finite/Unicode parsing
limits before lookup, with one monotonic ingress deadline and final cancellation/
expiry check. No backend admission, text inspection, callback or I/O occurs.

Selected languageTag allowlist is exactly `en`, `es`, representing caller-declared
synthetic labels, not a language detector or accuracy/calibration claim. No case
folding, locale guessing, Unicode normalization, regional-tag collapsing or code-mix
heuristic is permitted. Null/empty/unknown tags, `mixed`, `und`, combined tags and
absent/null task IDs produce unavailable (missing envelope keys still refuse).
Selected taskId allowlist is exactly `boolean-fixture`, `choice-fixture`,
`score-fixture`, `schema-compile-fixture`. Names do not prove task meaning; no
arbitrary instruction or source text is admitted as task metadata.

The immutable installed rule registry contains exactly a version, an ordered route
array and canonical digest. Each route contains languageTag, taskId, capabilityId,
backendId, policyId, installedManifestDigest, supported. Entries are fixed by the
installed package, not caller-provided declarations. Both en/es map boolean/choice/
score fixture tasks to the existing synthetic-reference-v1/stdlib-rule-fixture-v1
capability/backend, with strict-uncalibrated-v1 policy; schema-compile-fixture maps
only to the installed s1-schema-synthetic-v1 compiler capability with backendId null
and policyId null. A missing compiler module/manifest reports unsupported, never
imports it to discover support. Manifest digests are recomputed from exact installed
metadata; unknown/stale supplied or consumer-expected registry digests refuse.
No learned/real-language/calibrated route exists; an explicit diagnostic core policy
requires its original separate request choice and is not silently set by routing.

Response fields are exactly `contractVersion: s1-metadata-router-v1`, requestId,
requestDigest, registryDigest, status, route, reasonCodes, evidenceClass: heuristic,
executionAuthorization: false, packetDigest. Packet digest binds all other fields
using core canonical bytes. Status is `matched` with the exact installed route,
`unavailable` with null route for unsupported declared tags/tasks/capabilities,
`refused` with null route for malformed/source/pin failures, or `defer` for
cancel/expiry. Prevalidation refusal nulls unvalidated IDs/digests. Fixed codes are
`invalid-router-request`, `unsupported-source`, `unsupported-language-tag`,
`unsupported-task-id`, `capability-not-installed`, `registry-pin-mismatch`,
`router-budget-exceeded`, `cancelled`, `deadline-exceeded`. No text, probability,
language confidence or model-quality field is returned. A matched route is advice;
the consumer still validates the unchanged target contract/manifest/policy and
cannot treat the metadata packet as a grant or invocation.

Negative controls pin en/es exact mapping, absent/unknown/mixed/regional/combined
labels, short code and mixed-script strings (as unsupported labels, never detected
text), malformed/extra text fields, unavailable installed module, forged/stale
manifest/registry, deep mutation, deadline/cancellation and zero import/network/model/
process dispatch. Fresh wheel checks include installed router discovery parity.
Learned routing and real-language validation remain separate SPEC-029/030/033 gates.

Exact public signatures, refusal envelopes, cancellation/publication, metadata
registry and observation outcomes are fixed by [API details](api-details.md).
