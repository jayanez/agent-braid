# SPEC-028 standard-library reference profile v1

Status: provisional technical contract resolution, 2026-10-06. This profile
resolves the conditional technical review gaps for T001 and awaits fresh Luna
review. It is not founder acceptance, a canonical ADR, scientific validation,
capability promotion or permission to implement a neural backend. The general
[decision envelope](decision-api.md) remains additive and advisory.

## Input and canonical representation

The first implementation accepts one UTF-8 JSON document. Read at most
1,048,577 bytes to detect the **1,048,576-byte inclusive raw limit before JSON
parsing or backend admission**. Never read an unbounded stream, silently crop,
strip a prefix or replace invalid UTF-8. Reject BOM, trailing non-whitespace,
duplicate object members at every level, NaN/Infinity, lone Unicode surrogates
and unsupported versions. JSON objects/lists are containers; root container
has depth 1 and every nested container adds 1. Maximum container depth is 16.
Use a bounded pre-parse scanner to enforce container depth while respecting
quoted strings and escaped quotes; JSON syntax validation follows. Parse
integers only after checking at most 20 decimal digits excluding sign, and
require signed 64-bit range. Floats use finite binary64; reject overflow.
State booleans are JSON values, but booleans never satisfy numeric fields.
No caller-controlled field invokes code, imports, reads files or selects a URL.

Canonical bytes are UTF-8 from Python standard-library JSON with sorted object
keys, separators `,` and `:`, `ensure_ascii=False`, `allow_nan=False`, no trailing
newline and no Unicode normalization. Preserve every array's supplied order.
Reject canonical output exceeding the same 1,048,576-byte inclusive limit.
Python JSON's binary64 shortest representation is the reference serialization;
this profile makes no cross-language canonical-number compatibility claim.
`-0.0` and `0.0` retain their different reference bytes. Digests are lowercase
SHA-256 hex over canonical bytes. Hashes detect differences relative to pins;
they do not authenticate the source or establish semantic correctness.

Validate the whole request, including types, lengths, numeric limits, duplicate
IDs, supplied digests and backend/capability/policy support, before admitting it
or invoking backend allocation/evaluation. Parsing has bounded allocation from
raw size/depth; this is not a zero-allocation parser promise. Caller-provided
state is deep-copied/frozen only after validation, with immutable object,
array and scalar records throughout. A frozen outer object containing a
mutable nested list/dict does not satisfy this requirement.

## Exact request schema and limits

All keys listed here are required; all additional keys are rejected.
`contractVersion` is `decision-stdlib-v1`. `requestId`, `capabilityId`,
`contextVersion`, `backendId`, `policyId`, every question ID and option ID are
nonempty strings of at most 64 UTF-8 bytes; reject control characters and lone
surrogates, without normalization. Question IDs are unique in a request;
option IDs are unique within a question. IDs need not be ASCII. `state` is a
JSON object. `stateDigest` is 64 lowercase hexadecimal characters and must equal
the recomputed canonical state digest. `questions` is an ordered array of
1 through 32 question records. Identity strings are not filesystem paths,
import names or authorization grants.

A question contains exactly `id`, `type`, `instructions`, `options`. `type` is
`boolean`, `choice` or `score`. `instructions` is a string of 0 through 4,096
UTF-8 bytes. Each option contains exactly `id`, `description`; score options
add required `value`. Descriptions are strings of 0 through 4,096 UTF-8 bytes.
Boolean options are exactly logical IDs `false` and `true`, in that order.
Choice and score contain 2 through 32 options. Score `value` is a finite JSON
integer or binary64 float, excluding boolean, of absolute magnitude at most
1,000,000; score values are strictly increasing in supplied option order.
Choice/boolean options cannot carry rubric values. No singleton certainty,
regression primitive, generated text or hidden rendering/truncation is allowed.

`budgets` contains exactly these required integer ceilings (booleans rejected):

| Field | Inclusive range | Meaning |
| --- | --- | --- |
| `maxInputBytes` | 1..1,048,576 | Caller ceiling on both raw and canonical request bytes; never expands profile hard limit. |
| `maxQuestions` | 1..32 | Caller ceiling on question count. |
| `maxOptions` | 2..32 | Caller ceiling on options in each question. |
| `maxTokens` | 1..1,048,576 | Caller ceiling in the backend's advertised reference token unit. |
| `deadlineMs` | 1..5,000 | Maximum elapsed monotonic milliseconds, starting at ingress. |

There are no implicit missing-budget defaults. The caller supplies ceilings;
the profile's upper endpoints are hard defaults for any future CLI template.
`maxInputBytes` includes its own budget bytes within the complete envelope.
Checks apply before backend admission, including rendered token fit.

The reference renderer is the canonical **entire request**, including state,
questions, options, identities and budgets. Reference `character-token-v1`
counts Unicode code points of that rendered string, with a hard context cap
of 1,048,576 code points. The count is not UTF-8 byte count, model tokenizer
count or a guessed neural context window. Rendering and counting cannot omit
state or options, nor split an over-budget request into partial evaluations.
The backend advertises this renderer/token unit and full context cap. No neural
memory, device support, artifact rights, tokenizer or paid compute limit is
invented by this profile; a neural profile requires a separate frozen envelope.

## Reference backend and policies

Only the explicit `backendId: stdlib-rule-fixture-v1`,
`capabilityId: synthetic-reference-v1`, `contextVersion: synthetic-v1` are
supported initially. No real source is admitted by these identity labels.
Backend discovery is offline, immutable and imports no ML/provider module.
It advertises the three primitives, binary64 numeric representation,
character-token renderer and profile limits. Loading executable artifacts,
networks, training, calibration and resource mutation are absent.

For this explicitly synthetic capability, `state` contains exactly
`sourceKind: synthetic` and `ruleAnswers`, an object mapping supplied question
IDs to one supplied logical option ID. Unknown question IDs, unknown option
IDs, malformed mappings or additional state fields refuse before evaluation.
A missing mapping is an explicit unsupported fixture outcome. An existing
mapping returns a one-hot **hand-authored synthetic rule fixture** distribution.
Instructions and descriptions bind the digest but do not acquire natural-language
interpretation. The result exercises the typed contract, not prediction of
truth, effects or user-derived intent. No verifier is called by this backend.

Supported policies are `strict-uncalibrated-v1` and
`synthetic-diagnostic-v1`. The first is the default reference policy and
abstains because no validated calibration/domain evidence exists. The second
must be selected explicitly and may publish fixture readouts as answered;
it makes no accuracy, calibrated-probability or real workload claim. Both deny
execution authorization and any certificate/grant/verified field. Neither
policy changes existing semantic verification or operator authority.

Reference model, capability and policy manifests have fixed versioned contents
within this profile implementation. Their canonical digests are recomputed,
not accepted as backend-supplied trust. A caller/consumer checks expected
manifest/version identities separately before using any response. No canonical
ADR inventory or legacy evidence snapshot is updated by this profile.

## Exact response and status invariants

A response contains exactly `contractVersion`, `requestId`, `requestDigest`,
`stateDigest`, `questionsDigest`, `backendId`, `capabilityId`, `capabilityVersion`,
`contextVersion`, `policyId`, `status`, `answers`, `calibrationStatus`,
`reasonCodes`, `inputCoverage`, `usage`, `modelManifestDigest`,
`calibrationManifestDigest`, `policyDigest`, `evidenceClass`,
`executionAuthorization`, `responseDigest`. Validated identities match the
request. Request digest binds the entire canonical envelope; questions digest
binds the ordered question array. Response digest binds all response fields
except `responseDigest` itself. Known local manifests supply their digest
fields. `capabilityVersion` is `synthetic-reference-v1`;
`calibrationStatus` is always `absent`; `calibrationManifestDigest` is null.
No `calibratedProbability`, certificate, grant or verified field is permitted.
`evidenceClass` is always `heuristic`; `executionAuthorization` is always false.

| Status | Answers and coverage | Meaning |
| --- | --- | --- |
| `answered` | Exactly one answer per question, in request order; complete distributions; coverage 1.0. | Explicit diagnostic policy, all synthetic fixture mappings supplied, not cancelled or expired. |
| `abstain` | Empty answers; coverage 0.0. | Strict default without calibration, or any missing fixture mapping. Never publish a partial batch or infer a uniform success. |
| `defer` | Empty answers; coverage 0.0. | Valid request cannot complete due to overload, cancellation, deadline or closed backend. No late recommendation. |
| `refused` | Empty answers; coverage 0.0. | Invalid envelope, unsupported domain/identity, stale supplied state digest, invalid output or exceeded budget. Backend must not run for input refusals. |

For input refusal before full validation, `requestId`, input/manifest digests and
requested identity fields are null; `responseDigest` still binds the refusal; fixed contract/evidence/calibration fields remain
present. Do not echo untrusted fragments, private paths or raw exceptions.
`reasonCodes` is a nonempty array from the fixed code set for non-answered
statuses, empty for answered: `invalid-envelope`, `unsupported-identity`,
`state-digest-mismatch`, `input-budget-exceeded`, `render-budget-exceeded`,
`invalid-backend-output`, `calibration-absent`, `fixture-mapping-missing`,
`overloaded`, `cancelled`, `deadline-exceeded`, `backend-closed`. Null identity
fields distinguish pre-validation refusal from a fully bound valid request.

Each answer contains exactly `questionId`, `type`, `distribution`, `choiceId`,
`pTrue`, `expectedScore`, `argmaxScore`, `rawTopProbability`, `concentration`.
Distribution entries contain exactly `optionId`, `probability`, cover every
option once in supplied order, have finite nonnegative binary64 masses, and
sum to 1 within absolute tolerance 1e-6. `choiceId` is the argmax option ID,
breaking exact mass ties by Unicode code-point ascending option ID, independently
of array order. `pTrue` is the true-option mass for boolean and null otherwise.
`expectedScore` is the probability-weighted rubric expectation for score and
null otherwise. `argmaxScore` is the rubric value corresponding to `choiceId`
for score and null otherwise; expectation need not be a discrete level.
`rawTopProbability` is the largest uncalibrated mass. `concentration` contains
exactly `formula: normalized-entropy-v1`, `value: 1-H(p)/ln(N)` with
`H(p)=-sum(p*ln(p))`, zero-mass terms zero, and binary64 rounding clipped to
[0,1]. Neither concentration nor top mass is calibrated correctness.

`usage` contains exactly finite nonnegative binary64 millisecond durations
`queueMs`, `loadMs`, `renderMs`, `inferenceMs`, `totalMs`, plus nonnegative
integer `inputBytes`, `renderTokens`. Unperformed phases are zero; total spans
ingress to attempted publication and includes validation/fallback overhead.
Do not infer savings from these counters. On ingress refusal without a complete
parsed request, input bytes are the observed bounded count, token count zero;
digests and identities stay null. Every reference distribution is uncalibrated.

## Admission, monotonic deadline and cancellation

Reference admission allows one active evaluation, at most eight waiting valid
requests, zero automatic retries and zero background result cache. The ninth
waiting request returns `defer/overloaded`; these are hard reference ceilings,
not measured throughput claims. Each admitted request owns its immutable state,
question/options, renderer offsets, cancellation token and response buffers.
No request-local data is placed in backend globals or reused across requests.

At core API ingress, after receiving already-materialized bounded UTF-8 bytes and before parsing, capture `start=monotonic_ns()`; apply the
5,000 ms hard profile ceiling until the validated caller budget is available,
then tighten to `deadline=start+deadlineMs*1,000,000` without resetting start. Parsing, validation, queueing, rendering,
loading, evaluation, policy and result publication all consume this same budget.
Use the same clock within one process; no wall-clock deadline comparison or
reset on backend entry. A duration equal to the ceiling is expired. Check
cancellation and `now >= deadline` before admission, while waiting, immediately
before evaluation and immediately before result publication. The synchronous
reference backend cooperatively checks during any bounded loop. No transport
or wall-clock adjustment can extend the request deadline.

Cancellation token state is request-local, monotonic and irreversible. Under
a publication lock, recheck cancellation/deadline before publishing exactly
one terminal response; cancel racing before this check wins and suppresses
answers. Cancellation after publication cannot revoke an already delivered
response. A pending cancel/expiry yields empty `defer` even if a backend later
finishes. Release active admission only once backend work actually stops;
never start replacement work while ignored work is still active. Queue entries
can be removed on cancel/expiry without evaluating them.

`close()` prevents new admission and defers queued requests; it releases only
idle resources. Active work remains cooperative and can be marked cancelled.
This profile promises suppression of late recommendations, not hard stopping
CPU/GPU computation. A Python thread timeout cannot kill work. Hard compute
termination, neural/device memory admission, subprocess isolation and recovery
require a separately reviewed worker profile. No late result enters a cache or
subsequent request. Tests use barriers and an injected monotonic clock rather
than timing-dependent sleeps.

Core deadline coverage begins at the materialized-byte API ingress, not at an uninterruptible external read. The CLI accepts only bounded regular local files with nonblocking/no-follow admission; its source I/O is outside the core deadline and must not be described as a guaranteed end-to-end file-ingress deadline. Stdin, sockets and streaming ingress are unsupported. No source I/O latency or total CLI wall bound is claimed by this profile.
