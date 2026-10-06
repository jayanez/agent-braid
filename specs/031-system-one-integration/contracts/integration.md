# Synthetic advisory integration contract v1

Status: feature-local proposal for byte-bound Luna technical review. No accepted
integration, human review, utility, task completion or capability promotion is
recorded here. This contract selects every deterministic T002–T007 engineering branch of SPEC-031;
[capability map](../capability-map.md) lists the remaining branches. It depends on
SPEC-028's [stdlib profile](../../028-system-one-core/contracts/stdlib-v1.md),
including its exact canonical bytes, parsing/refusal limits and immutable values.
Implementation admission additionally waits for SPEC-028/T008 candidate validation
and fresh-install evidence. A technical architecture GO does not complete T008.

## Interface and identity binding

Proposed library entry point:

```text
advise_synthetic(context_bytes, decision_bytes, *, expected_context_digest,
                 expected_model_digest, expected_policy_digest, cancellation)
    -> immutable advisory packet
```

Inputs are materialized UTF-8 bytes, never paths, URLs, callables or plugins.
Each input is at most 1,048,576 raw and canonical bytes. Parsing uses exactly
`decision-stdlib-v1`'s duplicate-member, container-depth-16, finite-number,
Unicode and signed-64-bit rules. Entire combined raw input is additionally capped
at 1,048,576 bytes; this stricter wrapper ceiling includes both envelopes and
cannot enlarge the core's limits. No truncation or partial operation set is allowed.

`context_bytes` has exactly these keys:

| Field | Exact meaning |
|---|---|
| `contractVersion` | `s1-integration-synthetic-v1` |
| `sourceKind` | `synthetic`; other labels refuse, including sanitized real sources |
| `stage` | `diagnostic` for this core-wrapper context; other selected names use the separate stage envelope below, never arbitrary consumer dispatch |
| `generation` | Explicit integer 0..2^63-1, excluding booleans; synthetic snapshot identity, not a live-resource freshness proof |
| `operations` | Ordered nonempty array of 1..64 AIM 0.2 records; exact existing identity/effect/version/dependency fields and schema constraints |
| `decisionRequestDigest` | SHA-256 lowercase hex of the entire canonical core request |

All operation instance/attempt IDs are unique; dependencies must identify supplied
instances, be acyclic and omit self-dependencies. Definition/input digests are
preserved, not regenerated from missing content. Preserve all effect channels,
coverage uncertainty, read versions and supplied ordering. Declared/observed effect
differences remain visible; do not merge them into asserted complete knowledge.
The wrapper can validate structural AIM fields; it cannot certify declared effects.
No prompts, arbitrary extensions, source files, grants or executable content occur
in this context. Core question instruction/description strings remain bound opaque
fixture text under the existing core contract, never instructions to the wrapper.

The expected context/model/policy digests are explicit trusted consumer pins,
validated as lowercase 64-character hex. Recompute context and request digests
before any backend admission. Check the context's `decisionRequestDigest` against
the canonical request. Core request identities remain exactly
`synthetic-reference-v1`, `synthetic-v1`, `stdlib-rule-fixture-v1`; no new core
capability or state field is introduced. Core state is still exactly synthetic
`ruleAnswers`. The context is a separate wrapper envelope and must not be inserted
into that restricted state or hidden in instruction strings.

Before core admission, create the explicitly bound delegated request described in
the deadline section below. After core evaluation, validate its whole response against
that frozen delegated request
and locally known manifests; compare manifest digests to expected pins. Unknown,
null or mismatched pins cannot be treated as discovered support. Preserve strict
uncalibrated default abstention. Only explicit `synthetic-diagnostic-v1` may return
hand-authored fixture answers. A diagnostic option is a fixture label, not a
judgment about an operation's effects or correctness.

## Packet and consumption

Successful structural processing returns exactly `contractVersion`, `status`,
`contextDigest`, `generation`, `decisionRequestDigest`, `delegatedRequestDigest`,
`delegatedDeadlineMs`, `decisionResponse`,
`stage`, `operationIds`, `fallback`, `evidenceClass`, `executionAuthorization`,
`reasonCodes`, `packetDigest`. Contract version is `s1-integration-synthetic-v1`;
packet digest binds all other fields using core canonical bytes. Context generation
and operationIds preserve input values/order. `decisionRequestDigest` binds the original
consumer-pinned request; `delegatedRequestDigest` binds its explicit deadline-tightened
copy, and `delegatedDeadlineMs` records that integer ceiling. Apart from that ceiling
all request fields, state/questions/order/identities and other budgets are identical. `decisionResponse` is the unchanged
validated core response. Evidence class is `heuristic`; authorization is false.
Fallback is always `keep-original-order-and-run-existing-verifier`.

Status is `diagnostic` only for an explicitly diagnostic core `answered` response;
otherwise `abstain`, `defer` or `refused` mirrors the core status. No partial answers
are published. Malformed/unsupported/pin/budget wrapper rejection produces status `refused`, empty operationIds,
null unvalidated context/generation/original-and-delegated-request/response fields, the same fixed
contract/evidence/authorization/fallback fields, a packet digest and one or more
fixed codes: `invalid-context`, `unsupported-stage`, `unsupported-source`,
`context-pin-mismatch`, `request-pin-mismatch`, `manifest-pin-mismatch`,
`wrapper-budget-exceeded`. Wrapper cancellation/expiry instead produces empty
`defer` with `cancelled`/`deadline-exceeded`; its core decisionResponse is null,
and delegated digest/deadline are null if no delegated request was validated.
Retain context/original-request bindings only after complete validation, otherwise
use null fields and empty operationIds. Never echo rejected
input values, field names, private paths or raw exceptions.

Every later consumer must recompute the whole packet and context digest and compare
its current synthetic generation/operation IDs to the expected snapshot. Mismatch
refuses advice and uses original-order fallback. No numeric probability or high
confidence bypasses this check. Digest consistency detects changes against pins;
it is not source authentication, a clock or a freshness guarantee. Unauthenticated
external packets are not an execution input.

## Threat, resource and compatibility boundary

The pure stage library is read-only and makes zero calls to filesystem, network,
subprocess, provider, model SDK, verifier, scheduler, runtime, grant store or recovery
tools. Its separate stdio transport only reads/writes explicitly bounded MCP frames;
it opens no network listener, source file, runtime store or extra process.
It returns immutable nested records. It does not alter AIM/report/certificate,
exchange eligibility, operation order, runtime manifests, grants or defaults.
Existing CLI/analyzer/verifier/runtime behavior and defaults remain unchanged.
The separately named read-only MCP tools below transport advice only; they cannot
call existing execution tools or automatically register observation exports.

Use one monotonic ingress deadline of 5,000 ms, tightened to the validated core
request's `deadlineMs`; parsing/context validation/core queue/evaluation/response
validation/packet publication all consume it. Check cancellation/expiry before
core admission and packet publication, and recheck the core publication token at
the wrapper publication point. Never reset the deadline on delegation. The wrapper keeps its own absolute ingress deadline. Immediately before core admission,
compute remaining whole milliseconds by flooring `(deadline-now)/1,000,000`.
If fewer than one remains, return empty `defer/deadline-exceeded` without core work.
Otherwise delegate a canonical copy of the validated original request whose
`budgets.deadlineMs` is the smaller of its original ceiling and remaining whole
milliseconds. Revalidate that complete delegated request under core limits,
including changed canonical byte/token counts; it acquires its own explicit
request digest. No other field changes. Core starts its materialized-byte budget
at delegated ingress, while the wrapper independently checks the original
absolute deadline at all stages and immediately before packet publication.
The returned response binds the delegated digest and the outer packet binds both
requests. Consumers reconstruct the delegated request from the original and
recorded `delegatedDeadlineMs`, then validate all digests/unchanged fields.
This uses the existing core API and requires no implicit reset of the wrapper
budget or hidden extension. Cooperative bounded loops and suppression of late
packets are promised; hard CPU termination is not. Core admission remains
one active/eight waiting; wrapper introduces no background queue/retries/cache.

Candidate tests must pin changed generation, identity, request and manifest bytes;
deep mutation; conflicting declared/observed effects; unknown footprints; forged
authority fields; malicious fixture text; cancellation/expiry publication races;
full refusal and zero-dispatch spies. Comparison to legacy outputs establishes
only unchanged behavior under synthetic controls, not shadow utility or a live
host guarantee. Scientific/adoption/real-source acceptance remains separate.


## Deterministic stage request and response envelope

The diagnostic core wrapper above remains one selected path. Other stages use
`advise_stage(request_bytes, *, expected_context_digest, expected_registry_digest,
cancellation) -> immutable stage packet`; they do not manufacture core questions
or diagnostic ruleAnswers. One exact request contains `contractVersion:
s1-stage-advice-v1`, `requestId`, `context`, `contextDigest`, `registryDigest`,
`stage`, `payload`, `budgets`. All keys are required and additional keys refuse.
Request IDs and stable payload IDs follow core's 1..64 UTF-8-byte identity rules.
Context is a frozen synthetic snapshot exactly `sourceKind: synthetic`,
`generation`, `operations` with the operation constraints above; it contains no
core decisionRequestDigest. Digests are 64 lowercase hex and recomputed against
consumer pins before any work. The locally installed static stage registry binds
version, installed modules, available stage names and their rule definitions; its
digest is recomputed locally. Unknown/stale registry/context pins refuse advice.
Registry discovery imports no dynamic package and neither installs nor launches
anything. This is structural/synthetic advice, not admitted real-source processing.

Budgets are exactly `maxInputBytes` (1..1,048,576), `maxCandidates` (1..64), `deadlineMs` (1..5,000), all integers excluding booleans. Raw/canonical size, container-depth-16/finite parser constraints and hard ceilings apply before rule work. Public `advise_stage` starts one monotonic deadline before parsing, tightens it to the validated original request ceiling without resetting its start, claims its request-local cancellation token once, and releases that claim on every terminal path. Check cancellation/expiry during parsing/validation and bounded rule loops and immediately before publication. There are no retries, background queues or caches in the pure stage library. Every stage is linear bounded metadata processing or at most 64-item stable sorting; it executes no consumer action. Consumer callbacks and source paths are outside the interface.

The separate MCP transport delegates only through private `_advise_stage_in_scope(scope)`. Its sole argument is an opaque immutable private transport-call scope created and registered by that transport admission path. The scope binds the exact transport-owner identity, typed request ID, registered token identity and claim owner, original validated canonical request bytes and digest, explicit context/registry pins, and trusted monotonic ingress origin/effective absolute deadline. The transport-owned factory captures the ingress clock before frame parsing and computes the final ceiling from its captured origin and validated original request; it never accepts caller-supplied timestamps. The ceiling is the minimum of the transport ingress deadline, `ingress_started_ns + 5,000,000,000`, and `ingress_started_ns + original validated budgets.deadlineMs * 1,000,000`. No stage field or digest is rewritten. A scope is immutable; lifecycle state lives separately in the transport registry. Scope construction, registration, token claim and deadline computation are private admission operations, not caller-selectable arguments or JSON fields.

Before rule work, the helper asks the owning registry to validate exact object identity and its live registration, active lifecycle state, frozen parameters, canonical request digest, context/registry pins and request-local token/claim owner. A copied, fabricated, unregistered, stale, completed, reused or mismatched scope refuses without rule work or output; impossible future/reversed timestamps or a ceiling outside the computed ingress bounds refuse. Valid scope timestamps are obtained from the same monotonic clock. Full original stage validation and pin checks remain mandatory; ownership validation is additional and cannot stand in for them. The helper never claims/releases a token, installs another token, resets an origin, allocates a queue slot or mutates a deadline. The scope is inaccessible through the wire envelope. Private same-process object/registry checks are engineering ownership controls, not a security boundary against arbitrary same-process Python code. Public direct `advise_stage` continues to own its own token scope and cannot reuse a transport scope.

Queue waiting, parsing, context/registry validation, rule work and packet validation all consume that same absolute transport budget. Expired queued work produces no rule advice. No remaining-budget rewrite, digest substitution, hidden request state or extra packet field is permitted on this stage path. Diagnostic `advise_synthetic` retains its separately specified original/delegated request binding and deadline-tightened copy; these stage rules do not alter that interface.

A stage packet has exactly `contractVersion: s1-stage-advice-v1`, `requestId`,
`requestDigest`, `contextDigest`, `generation`, `registryDigest`, `stage`, `status`,
`advice`, `fallback`, `reasonCodes`, `usage`, `evidenceClass: heuristic`,
`executionAuthorization: false`, `packetDigest`. Request/context/registry digests
bind exact canonical inputs and local rule identities; packetDigest binds all other
fields. Status `advised` means only that a deterministic metadata rule completed;
`unavailable` has null advice for supported syntax with insufficient coverage or
unsupported declared metadata; `refused` denotes malformed/stale pins/identities;
`defer` denotes cancellation/expiry. Input refusal before full validation nulls
unvalidated identity/digest/stage/generation fields and never echoes fragments.
No certificate, verified, grant, confidence or calibratedProbability field exists.

Fixed reason codes are `invalid-stage-request`, `unsupported-stage`,
`unsupported-source`, `context-pin-mismatch`, `registry-pin-mismatch`,
`identity-set-mismatch`, `unknown-metadata`, `unsupported-metadata`,
`stage-budget-exceeded`, `cancelled`, `deadline-exceeded`, `overloaded`. Advice is published only
as a complete stage result. Fallback is exactly `keep-original-order-and-use-existing-consumer`.
Usage contains finite nonnegative millisecond `validationMs`, `ruleMs`, `totalMs`
and integer nonnegative `inputBytes`, `candidateCount`; no workload savings follows.

### Candidate priority and analyzer choice (T003)

`candidate-priority` payload is exactly `domain`, `eligibleIds`, `hints`.
Domain is `spec018-prefiltered` or `spec012-prefiltered`; input eligibleIds is an
ordered unique array of 1..64 stable candidate IDs already filtered by the unchanged
consumer eligibility logic. Hints is an ordered array of exactly one record per
eligible ID, each exactly `candidateId`, `rulePriority` (integer 0..63). Advice is
exactly `orderedIds`, `inputSetDigest`, `rule: stable-priority-v1`: stable sort by
ascending priority with original position breaking ties. The output is a permutation
of precisely the supplied eligible IDs. No ID can be added, deleted, pruned,
merged, regenerated or implicitly verified. Missing/extra/duplicate IDs refuse;
there is no arbitrary eligibility flag by which advice expands SPEC-019's population.
Consumers recompute membership/pins and run the same unchanged verifier for every
original eligible case under the same budget. Advice never enables an early positive
certificate or omits unknown/negative cases. Empty eligible sets return unavailable
rather than claiming an improvement; legacy keep-order is always available.

`analyzer-choice` payload is exactly `populationIds`, `analysisBudgetDigest`,
`availableAnalyzerIds`. Population IDs are unique ordered 1..64 metadata IDs;
analysisBudgetDigest pins the caller's existing unchanged complete analysis budget.
availableAnalyzerIds is a unique array of at most 32 core-format IDs.
For this cut the sole available analyzer ID is `exact-resource-footprints-v1`,
backed by the existing analyzer, and the installed registry must match it. Advice
is exactly `analyzerId: exact-resource-footprints-v1`, `populationDigest`,
`analysisBudgetDigest`. It performs no analysis and changes no classification,
normalizer, observation, population, coverage or depth/budget policy. An unavailable
or alternate analyzer request returns unavailable. Later multiple-analyzer choice
requires a separate same-population/budget refinement contract. Utility is not a
prerequisite for engineering this deterministic explicit fallback interface.

### Effect comparison, shortlist, adequacy and triage (T004)

`effect-review` payload is exactly `comparisons`: 1..64 records each exactly
`comparisonId`, `declared`, `observed`, `declaredCoverage`, `observedCoverage`.
Comparison IDs must be unique. Channels are bounded arrays of at most 64 existing
AIM effect records; coverage
is `complete`, `partial` or `unknown`. Preserve both channels with multiplicities
and supplied order. Advice has one result per input comparison: comparisonId,
declared, observed, declaredCoverage, observedCoverage, relation. Relation is
`equal` only if both coverage labels are complete and canonical effect multisets
match; `different` only when both are complete and those multisets differ;
otherwise `unknown`. These are comparisons of declarations, not actual effect
verification. A declaration/observation mismatch remains visible and never turns
unknown coverage into commuting, certainty or authorization.

`shortlist` payload is exactly `registryEntries`, `requestedCapabilities`,
`argumentNames`. Entries are 0..32 pinned locally installed metadata records,
each exactly `entryId`, `kind` (`tool-metadata`, `model-metadata` or
`reference-rule`), `capabilities`, `requiredArgumentNames`, `allowedArgumentNames`,
`manifestDigest`. Each name array is unique and has at most 32 core-format IDs;
required names are a subset of allowed names. The complete canonical entry array
must equal the stage registry's installed metadata inventory, not an input claim
that an arbitrary model is installed. No source URL, Python import, command,
weights, raw arguments or credential field is allowed. Requested names are bounded
by the same limits. Advice returns matching entryIds in registry order only when
requested capabilities are a subset of declared capabilities and argument names
satisfy required <= supplied <= allowed. Nonmatching entries are retained as
`excludedIds` with fixed `capability-missing` or `argument-shape-mismatch` reasons;
no payload/code is evaluated. Metadata compatibility is neither semantic argument
judgment, model quality nor executable support. The empty inventory is valid syntax
but yields unavailable with null advice and unknown-metadata; it cannot invent a
model/tool match or publish an empty successful shortlist as evidence of support.

The minimal recommended static inventory contains exactly the real local analyzer
entry `exact-resource-footprints-v1` with kind `tool-metadata`, declared capability
`aim-analysis`, requiredArgumentNames [`aimRecords`], allowedArgumentNames
[`aimRecords`]. It is metadata about the installed local analyzer, not a callable
or new model. No nonexistent neural model, placeholder package or runtime tool
is advertised. Implementation freezes a stage registry manifest exactly `version:
s1-stage-registry-v1`, `stages`, `rules`, `inventory`. Stages is the ordered installed
stage-name array; rules contains one exact record per stage with `stage`, `ruleId`,
`implementationSourceDigest` binding reviewed implementation bytes. Unsupported or
missing stage modules are not listed. Inventory is exactly `entries`, `sources`;
its entries is the pinned payload inventory above. Each inventory source is exactly `entryId`,
`module: agent_braid.analysis`, `analyzerVersion: 0.1.0-alpha`,
`ruleSet: exact-resource-footprints-v1`, `moduleSourceDigest` (SHA-256 hex of exact
candidate source bytes), `entryManifestDigest` (SHA-256 hex of canonical entry
fields excluding manifestDigest). Entry manifestDigest must equal that recomputed
source entryManifestDigest. Freeze source/version/entry bytes alongside the
candidate; installed-wheel checks compare packaged analyzer bytes and inventory
against those pins. No dynamic import or file read occurs during shortlist advice:
build/install preparation supplies the immutable candidate-bound inventory and
installed capability status. If the advertised module is absent/unmatched, discovery
uses empty inventory entries/sources and unavailable shortlist status rather than asserting support.
Registry digest is SHA-256 of the complete canonical manifest (there is no digest
field inside that manifest); it must match both the local installed static pin and
explicit expected_registry_digest before payload entries are compared for exact
canonical equality. Module source digests establish artifact consistency only,
not tool correctness, real effect completeness or authorization.

`adequacy` payload is exactly `requiredFields`, `presentFields`, `schemaDigest`,
`expectedSchemaDigest`, `rubric`: unique arrays of at most 32 core-format field
names; rubric is exactly `required-field-completeness-v1`. Advice reports
`presentRequiredCount`, `requiredCount`, `missingFields` and `schemaMatched`.
Required set must be nonempty; expectedSchemaDigest is an explicit consumer pin,
not inferred from advice. Mismatch is refused. Compare names only, preserve missing
names in supplied required order, never assign task-quality/language/confidence
scores or substitute for deterministic schema/argument validation. The rubric
name is not a scientific adequacy label.

`triage` payload is exactly `caseIds`, `categories`: unique ordered 1..64 IDs and
one matching category record per ID, each exactly `caseId`, `category` from
`needs-review`, `unknown`, `counterexample-candidate`. Advice returns those records
with original IDs/order. It neither executes a reducer nor proves divergence,
minimality, falsification or actual counterexample status. Forged categories cannot
change verifier outcomes; no raw failing trace is accepted by this interface.

### Ready-set ranking and unchanged scheduler gates (T005)

`ready-rank` payload is exactly `readyIds`, `hints`, `readySetDigest`,
`schedulerConstraintsDigest`, `grantBindingDigest`. Ready IDs are the existing
scheduler's unique ordered 1..64 already-ready operation IDs. Hints follows the
candidate-priority exact records, with operation IDs as candidateId. The ready-set
digest binds the supplied ordered readyIds; the constraint and grant digests pin
existing consumer-owned constraints/authorization state and are opaque metadata,
never authority. Advice returns only a stable permutation `orderedReadyIds` plus
those unchanged digests. It cannot add operations, edit waves/plans/manifests,
change allocations or generate a grant. Digest shape alone does not certify a grant.

Before consuming rank advice the scheduler always reapplies its existing dependency,
resource-budget, isolation, cancellation, stale-input, plan/grant and recovery gates
against current state. A changed ready set, version, constraint or grant pin rejects
the hint and uses current original-order fallback. Advice is never passed as a
runtime request or authority field. Negative controls must demonstrate that high
priority forged/stale advice cannot alter consumer safety/authorization outcomes.

### Separate read-only MCP advice tools (T006)

Implement a separate advice-only stdio server/class, retaining the current
`agent_braid.mcp_runtime` execution server/tool catalogue unchanged. Selected MCP
protocol is exactly `2025-11-25`, discovered against primary versioned lifecycle,
tools, transport and cancellation documentation via Context7. This is a bounded
host profile, not a generic protocol or cross-version conformance claim. Initialize
rejects another protocol version; advertise only tools capability, no sampling,
elicitation, roots, resources, prompts, tasks or network transport.

Tool names are exactly `s1_advice_capabilities`, `s1_advise_stage`.
Capabilities arguments is an empty object and returns the installed static registry
version/digest/stages/limits and executionAuthorization false.
Stage arguments contains exactly `request` (the stage envelope above),
`expectedContextDigest`, `expectedRegistryDigest`; digests have the same rules.
Tools/list advertises exact additionalProperties-false input/output schemas,
readOnlyHint true, destructiveHint false, openWorldHint false. Annotations provide
no authority; actual no-dispatch implementation is required. No alias can reach
prepare/execute/recover/grant tools or dynamically select an imported function.

Stdio frames are one UTF-8 JSON-RPC message per line, at most 1,048,576 bytes
excluding one newline. Use bounded line admission before parsing and the same
finite/depth/duplicate-member rules. Request IDs are unique active string (core
64-byte limit) or signed-64-bit integer, never boolean/null. Methods are initialize,
notifications/initialized, tools/list, tools/call, notifications/cancelled; unknown
method is -32601. Invalid JSON is -32700; malformed envelope is -32600; invalid
parameters/version/unknown tool is -32602. Messages are fixed sanitized codes,
never echo method/tool names, client content or raw exceptions. Normal advice
refusal/defer is a tool result with structuredContent equal to the whole stage
packet, canonical JSON text content equal to that packet, isError true for
refused/defer and false for advised/unavailable. No unsolicited advice is published. Before publication serialize the entire
JSON-RPC result including both text and structuredContent; if it exceeds the
1,048,576-byte frame limit, return a complete small refused/stage-budget-exceeded
packet instead, never truncate or emit a partial structured result.

Allow one active `tools/call` and at most eight waiting validated calls in an explicitly bounded transport-owned queue; overflow returns bounded `defer/overloaded` without allocating queued work. A request-local irreversible cancellation token is created and claimed once at materialized-frame admission, before queueing, and remains transport-owned through queue removal, delegation and final publication. Request ID registration remains active for that whole scope. Duplicate active IDs refuse; integer and string IDs have distinct typed identities. The mutable owner registry tracks lifecycle separately from the immutable scope. Only the registered active scope may enter delegation/publication; transitioning it to completed permanently consumes it. Mark completed and release the token claim/active-ID registration exactly once on every completion, refusal, cancellation, expiry or shutdown path. A finally cleanup operation is idempotent against a registered completed state and cannot release another scope or token. Transport shutdown cancels each owned token and prevents publication; it makes no hard thread/process termination claim.

The monotonic ingress origin is captured before frame parsing; the initial transport ceiling is at most 5,000 ms. After stage validation its absolute deadline is additionally tightened to the original request's `deadlineMs` measured from that same ingress origin. Queue waiting consumes the budget. Delegation uses only the private `_advise_stage_in_scope(scope)` helper above with the exact admission-registered immutable scope and unchanged original envelope. Pure direct `advise_stage` owns a distinct direct-call scope; neither path nests token claims or resets the ingress clock. Capability discovery obeys the same bounded transport admission and cancellation/publication checks and performs no backend admission.

A cancellation notification contains `requestId` and an optional bounded reason (<=256 UTF-8 bytes). Discard the reason without echo, logging or storage, mark only that registered request's irreversible token, and send no response to the notification. Unknown/completed cancellation cannot affect another request. Cancelled queued work is removed without running stage rules. Cancellation/expiry observed during active work stops cooperative processing and suppresses any late advice packet; it cannot terminate Python work forcibly.

Serialize and size-check the complete JSON-RPC result before publication, including duplicate text and structured packet content and any bounded replacement refusal. Obtain the transport output lock, then enter the token's cancellation/publication lock. Under that same publication boundary, validate exact live scope ownership/state and recheck cancellation, absolute deadline and server-open state, then atomically change the owner-registry lifecycle from `active` to `publishing` immediately before the first output write. This is the write-begin linearization point. No other path may publish or begin a write for this scope. If cancellation or expiry wins this publication boundary, suppress the whole result, including any previously prepared advice or replacement packet. The private helper may construct a `defer` for internal accounting, but transport cancellation/expiry at its final boundary cannot publish late advice. No other path writes a result for that request. Where the owner registry needs its own lock, the simultaneous lock order is output lock, token publication lock, then registry lock. Cancellation/shutdown obtain the token reference under the registry lock and release that lock before calling token cancellation; cleanup never holds a registry lock while acquiring a token/output lock. Cancellation and shutdown must not take locks in the reverse order or wait for the output lock while holding a token lock. If cancellation or expiry precedes the `active` to `publishing` transition, output is wholly suppressed. If publication wins that transition, that single bounded result is final; later cancellation cannot retract bytes or create another result. Complete and release the scope exactly once after the attempted write, including broken-pipe/write-error paths. Blocking transport writes are not hard-terminated and imply no total write wall-clock guarantee. Source stdio blocking read is outside the materialized-frame advice deadline, as with core local-file ingress; never claim a total wall-clock transport-read deadline. There is no client-auto-launch mechanism.

### Stage and fallback telemetry (T007)

After T006 exists, an explicitly caller-owned pull buffer records only validated
stage packets/consumer-measured fallback metadata. It shares SPEC-032's data-only
buffer discipline: at most 64 records, at most 1,024 canonical bytes each,
nonblocking busy/overflow outcomes, no retries/worker/automatic storage/export.
A record has exactly `version: s1-stage-observation-v1`, `stage`, `status`,
`reasonCodes` (<=8 fixed codes), `requestDigest`, `contextDigest`, `registryDigest`,
`adviceDigest`, `cost`, `fallback`. Cost is exactly finite nonnegative measured
`adviceMs`, `fallbackMs`, `verifierMs`, `runtimeMs`, `totalMs`; unobserved consumer
phases are null, not invented zero savings. Total is null unless full chain was
actually measured. Fallback is `kept-original-order`, `used-existing-consumer`,
`not-observed` or `none-needed`; metadata does not execute those choices.

No prompts, answers/distributions, operation/resource/candidate IDs, argument
bodies, filesystem paths or private labels enter telemetry. Request/context/advice
hashes remain opaque correlation metadata, not anonymity guarantees. Consumer
supplied costs are labelled observations of that consumer, not independently
verified timings. Record validates packet/context/registry pins and deep-freezes
all metadata before insertion. Negative controls cover stale/forged pins, dropped
records, busy buffer, cancellation, NaN costs and attempted content export.
Real shadow disagreement/utility, source rights and scientific interpretation remain
SPEC-031/T008 and SPEC-029 gates; all deterministic T002–T007 branches are selected
engineering and do not wait for a positive model/utility result.


## Required deterministic review controls

For T003 pin prefiltered input membership, unsupported domain, missing/duplicate
hint IDs, tied stable order, unchanged full population and budget identity, and
unchanged verifier results for every candidate (including unknown/negative).
For T004 pin complete-equal/complete-different/partial-unknown effects with both
channels retained; registry capability/argument exclusions; forged installed
entries; schema/rubric mismatches; triage IDs with no divergence/reducer dispatch.
For T005 inject forged grant/constraint/ready-set digests and high priorities,
then verify the unchanged scheduler reapplies every existing gate and never edits
plans/waves/manifests or permits previously refused work. For T006 test protocol
mismatch, unknown tool/method, extra parameters, duplicate IDs/members, frame bounds,
queue overflow, cross-request cancellation, late publication and absence of every
runtime/provider/network/process tool. For T007 test metadata field allowlist,
private prompt/answer/resource sentinels, NaN/unknown cost, whole-chain unavailable
cost, size/overflow/busy/deep-mutation refusal and no implicit export. Structural
parity and these negative controls are engineering evidence, never model utility.


### Bound transport failure observations

For a fully validated original stage request, a bound refusal is permitted only
with exactly `reasonCodes: [stage-budget-exceeded]`: the contracted complete
transport-frame replacement (or pure packet-size ceiling). Other refusal codes
cannot be attached to a valid bound request. Structural packet validation binds
request/pins and this closed outcome; it does not authenticate transport provenance
or independently prove the observed serialization size, cancellation or timing.
Consumers retain their original-order fallback and no execution authority. Internal
advisor or encoding exceptions suppress the whole result and release the owned
scope; they never fabricate a bound invalid-stage-request packet or echo exceptions.
External consumer-side binding failures return unbound refusals because those
consumer bindings never became validated stage-request bindings.
