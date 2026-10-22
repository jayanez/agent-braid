# Owned work evaluation v1

Adopted for local pure implementation on 2026-10-21 by the owner's explicit
instruction to adopt SPEC-051 and implement RF-T01/RF-T02. Publication, source
admission, real capture and human/scientific approval remain pending. The schema
URNs retain their original `proposed` namespace for byte-exact lineage; this does
not create an active service or consent route.

# RF-T02: proposed private ledger contract and semantic validator obligations

Original design provenance follows. Pure implementation adoption is recorded above; source admission remains absent. Schema names are
`agent-braid-owned-work-authority/v1` and
`agent-braid-owned-work-evaluation/v1`; they are distinct from the existing
synthetic recorder, metadata prefilter and SPEC-047 aggregate batch. The two
[event schema](owned-work-evaluation.schema.json) and [authority schema](owned-work-authority.schema.json) are exact closed structural contracts with internal refs only.
They do not resolve trust, admit a source, implement storage or validate cross-event
causality. The examples are fictional shape controls with zero placeholder pins;
they must fail real source/chain admission and are not observations or authority.

## Serialization, identity and immutability

The parser must reject duplicate JSON members, NaN/infinity, invalid Unicode,
non-object events, bool-as-integer, depth greater than 16 and bytes beyond 64 KiB
before append. Authority validity requires validFromUTC < validUntilUTC, exact
actions within the trusted scope and current out-of-wire revocation checks;
matching descriptor bytes alone never satisfies them. Canonical digest bytes use UTF-8 JSON, sorted keys, compact separators,
`ensure_ascii=True`, `allow_nan=False`, no trailing newline. `recordDigest` is SHA256
of the entire event with only `recordDigest` removed. `previousRecordDigest` binds
the immediately preceding global record; sequence starts at zero with null predecessor
and increases by one. A digest chain is integrity under trusted owned storage,
not a signature, consent or resistance to a malicious owner rewriting the chain.

Exactly one origin per attempt; a retry has a fresh attempt ID and keeps task and
family grouping. Sequence, attempt/task/family IDs, authority, source state, config,
toolchain and partition identities are checked against the frozen lot registry,
not accepted merely because they match a regex. An identical duplicate event is
idempotent; reuse of a sequence/digest/attempt origin with different bytes refuses.
An outcome references the exact origin digest. Subsequent maturity/correction
records append with `supersedesRecordDigest` and `amendmentReason`; they must refer
to an earlier outcome of the same attempt and preserve origin and source identity.
Never overwrite or remove a failed/immature outcome to prefer a later success.
The store/replay implementation, torn writes and atomicity remain RF-T03 work.

## Prediction origin and availability

Freeze the registered task population, source, method/baseline, feature allowlist,
oracle, validation-command digest, partition/family mapping and follow-up rule
before observation. Register refused, unsupported, cancelled, error, missing,
abandoned and not-selected attempts too. RF-T10 metadata is not this registry.
No complete-case filtering or retry-selected denominator. Related task families,
language variants and retries cannot cross development/evaluation partitions.
Time cutoff and embargo are frozen in the split protocol before any outcomes;
this ledger authorizes no fitting, calibration or threshold selection.

T0 is the immutable pre-action publication/sealing instant of the forecast/advice.
Method computation may precede it; no terminal result of the chosen work may be
used to choose that origin or fill its features. Later actual action belongs in
the outcome's `chosenAction`, with not-observed retained when unavailable.

An origin uses one trusted clock domain and `cutoffNs == originNs`.
Each present T0 feature must satisfy `eventNs <= availableAtNs <= cutoffNs`.
A missing value requires null event/availability and a fixed missing reason.
Duplicate feature/capability names refuse. Unit/name/scope must match the exact
allowlist, not a caller-defined counter. Prospective capability evidence must
be available by T0; an unperformed probe stays not-probed with null evidence/time.
Resolved toolchain provenance is bound if actually observed; inherited PATH alone
is not proof of the executable used. A later passing run cannot fill old fields.
Capabilities are not source permission and no current probe is authorized here.

## Horizons, outcomes and maturity

This first proposed forecasting target is `validation_wall_ns`: duration of the
prospectively bound validation command, from its launch to terminal exit and
required cleanup within its explicitly declared process/observer scope. It is not
whole-development cost, semantic accuracy or human acceptance. Future queue,
phase and resource metrics remain distinct fields. A point/interval uses ns, never
an invented probability. No forecast is produced in this proposal.

`status=not-produced` requires null horizon/point/interval/method and an explicit
reason. For a separately admitted produced forecast, freeze a method digest,
point and positive follow-up horizon of at most 24 hours at T0. An interval is
either absent as two nulls or complete with `0 <= lower <= point <= upper`.
The method and any actual model load require their own exact authority; a ledger
schema or valid method digest does not authorize them.

The horizon is the maximum follow-up after T0, not a fabricated time-grid step.
A result matures only with the bound command's terminal/cleanup evidence, verified
oracle, same-clock `originNs <= terminalNs <= availableAtNs <= maturityNs`, and
terminal within `originNs + horizonNs` when a forecast exists. If the command has
not terminated by the follow-up cutoff, it is right-censored, not zero-duration
or a point-error observation. Refusal before command launch/not-selection is
not-applicable/censored for this target. Missing outcome, invalid oracle and
revocation remain explicit. Later completion can append late-maturity evidence,
but cannot retroactively change the frozen horizon or the original censored lot.

An outcome's workflow terminal, product disposition and verification disposition
are separate. Verification unavailable must not be silently called product failure;
semantic-defer is neither a verified success nor an exception. Oracle `verified`
means the exact operational command/artifact check was obtained. Human labels and
semantic correctness remain `unknown`, even with exit 0, passing CI or a mature
numeric outcome. No gold labels, forecast error or selective-risk estimate follow
without the separately frozen rubric and eligible labels.

Cross-clock subtraction, clock regression and absent clock mappings refuse numeric
maturity or remain unavailable/censored. UTC recording dates support retention;
they are never substituted for monotonic elapsed time. Exact UTC/IDs/digests stay
inside this proposed private contract and never enter SPEC-047.

## Stage/resource and diagnostic semantics

Outcome spans have fixed stages, scoped IDs, parent relationships, clock domain,
complete/interrupted/unavailable state and inclusive/exclusive accounting.
Validate unique span IDs, acyclic/existing parents and ordered start/finish in the
same clock. Missing spans stay unavailable; inclusive nested spans are reconciled
by interval union, never summed. CPU user/system belong to their declared process
scope; sampled peak RSS is not enforced memory capacity. Git/output counts include
only the instrumented boundary, with missing/partial coverage explicit. Observer
wall is separate and cannot be inferred from the profile's total runtime.

Diagnostics use a fixed layer/code, claim level and admitted evidence digest.
`unknown` must use `unassigned`; observed-mechanism requires actual supporting
source, not just a sanitized `transport-failure` code. A hypothesis stays a
hypothesis. Raw stderr/stdout/transcript bodies are not ledger fields. An optional
bounded sanitized annex is a separate source/privacy decision, counts in the
store cap and must be digest-bound; absent annex is null. A reported symptom,
extra output-byte count or later CI success is insufficient causal evidence.

## Required refusals beyond JSON Schema

Refuse fabricated/expired/revoked authority, mismatched root/scope/pins, unobserved
source/toolchain claims, untrusted source verifier, broken chain, conflicting ID,
wrong origin/supersession, duplicate feature/metric/span names, future features,
unit/scope mismatch, cross-clock arithmetic, family overlap, immature oracle,
false maturity, incomplete interval, cap overflow or hidden content/identity field.
Reject unsupported contract versions; no implicit conversion of old records.
Do not silently drop malformed attempts: preserve their failure only under a
separately admitted registry and disclose any inaccessible denominator.
Pure behavior controls are implemented in the paired RF-T01/RF-T02 tests.
Storage, observer and real-source admission controls remain pending. Structural
checking does not establish source admission, a secure store, scientific validity
or production activation.

## Coordinator clarification RF-DEC-002 — late completion

For an origin with a produced forecast, if `terminalNs > originNs + horizonNs`, a
later outcome may be appended as new evidence but must retain `labelState=censored`
and `censoring.state=right-censored` for that origin's fixed horizon. It is excluded
from point/interval forecast-error observations for the original registered lot.
`amendmentReason=late-maturity` describes newly obtained operational evidence; it
is not permission to set `labelState=mature`, extend the origin's frozen horizon,
backfill T0 features, delete the earlier censored record or retry-select a result.
The cross-record state validator must enforce this even if each event separately
passes JSON Schema. RF-T02 enforces this rule in its pure state validator; the proposal packet itself
remains historical design, not implementation evidence.

## Adopted Python seam (RF-T01/RF-T02)

`OperatorRegistry` is an immutable snapshot supplied through trusted Python code;
there is deliberately no loader, wire adapter or callback verifier. Its approved
consent/review/root sets are host attestations, not authenticated by this module.
`resolve_authority` checks exact registered descriptor bytes, current supplied UTC,
revocations, actions and frozen root/scope/allowlist/oracle/split pins. It returns
validation context, never permission to execute or capture. Every `validate_append`
call resolves the supplied fresh registry again and revalidates bounded supplied
history. Freshness and truthful physical root/artifact verification remain external
operator obligations; a malicious in-process caller is outside this trust model.

`AttemptRegistration` freezes identities, source/config/toolchain/model pins,
partition, clock and prospective capability/recommendation evidence.
`FrozenRegistration` freezes lot/population/split, allowed method identities and
trusted oracle/diagnostic attestations, with at most one oracle attestation per
attempt so a correction cannot rebind a failed attempt to a later passing run.
Expected evidence must be supplied by an
independently admitted host path; creating an attestation is not evidence capture.
`validate_append` returns immutable canonical bytes in `ValidatedState`, duplicate
status, eligible mature forecast-outcome digests and every supplied population
member's missing/latest label. No file append occurs. A caller must never turn
parse success or the eligible tuple into a source/forecast/scientific admission.

This increment narrows the schema's generic scope enum: T0 predictors use attempt
scope, validation wall/exit metrics use validation-process scope. Numeric validation
wall and exit values bind trusted operational attestations. Other numeric metrics
are supplied observations, whose measurement truth is not independently checked.
Unknown capabilities must be explicitly frozen as not-probed, not relabeled later.
Spans require same clock, existing acyclic parents and containment; completed
spans cannot extend past supplied outcome availability/maturity. The descriptive
helper computes interval union of completed inclusive spans for one stage;
exclusive/incomplete rows return unavailable rather than an invented duration.

Record caps here cover supplied canonical event bytes only. Total physical storage
including journal/index/root maps/annexes and safe links/ownership, atomic append,
concurrency and purge belong to RF-T03. Diagnostic annexes are refused outright in
this increment. No observer/noninterference or actual population completeness is
claimed. An incomplete supplied population is not silently called complete.
