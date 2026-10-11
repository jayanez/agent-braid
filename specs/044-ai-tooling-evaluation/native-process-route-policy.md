<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Native-process route policy v2 implementation contract

**Status:** Approved scope boundary; additive implementation present; validation
and authentic native evidence have separate gates.
**Authority:** The owner-approved scope recorded in [ADR 0021](../../docs/adr/0021-codex-claude-tooling-integration.md#approved-scope-native-process-billing-observation-boundary).
This document specifies implementation work within that boundary. It does not
adopt the full ADR, approve the registration, authorize capture, or establish
that a trusted provider observer or actual-cash source exists.

## Purpose and compatibility

Policy v2 makes the billing observation claim only about each exact registered
Codex or Claude Code native CLI process, its provider route, and its lifetime.
Account-wide API billing is `unknown-out-of-scope`; it is never represented as
false. Account activity outside the registered process is outside this claim.

The v2 representation is additive. The existing
`agent-braid-m45-subscription-policy-v1` schema, its serialized fields, and its
strict explicit `apiBillingEnabled: false` requirement remain unchanged. A v2
registration must identify `agent-braid-m45-native-process-route-policy-v2`
explicitly; a v1 observation cannot satisfy a v2 binding, and a v2 observation
cannot silently reinterpret a v1 registration.

The v2 route claim and the estimated subscription reservation are separate.
The approved EUR 5.045 estimate remains an estimate under its existing nominal
period and active-time assumptions. It is not actual allocation, provider
accounting, or cash. A separate trusted source must prove exactly EUR 0
cohort-attributable additional cash. Unknown actual cash refuses dispatch.

## Frozen registration bindings

The v2 policy is a strict, versioned object with the existing
`included-subscription-only` mode, scope `registered-native-process-only`,
`accountWideApiBilling: unknown-out-of-scope`, zero additional-spend cap, and
paid API, overage, credits, and auto-recharge all disabled. Its maximum evidence
age is positive and no more than 60 seconds.

Bind both host accounts by opaque account and provider-namespace digests. Email
equality alone is insufficient. For every registered slot, freeze the host,
candidate artifact, host build, native executable, model identity, effective
configuration inventory, and exact argv digests. The process contract set must
cover exactly the registered roster; missing, duplicate, extra, or drifted slot
bindings refuse admission. Do not store credential values: record only
presence/absence assertions and source digests for applicable environment and
configuration sources.

The policy also freezes independent observer and cash-source references and
their verifier identities and digests. The observer binding declares that a
continuous per-provider-operation control is required. The cash binding declares
cohort attribution is required. A structurally valid reference or digest is
not proof that its source or verifier is authentic, available, or suitable.

For technical registration v3/v4, `processContracts` is keyed by all 108 slot
IDs. Each contract contains `host`, `hostBuildSha256`,
`candidateArtifactSha256`, `executableSha256`, `modelIdentitySha256`,
`argvSha256` and `configSha256`. Host build and executable digests match the
registered native host digest; the model digest is canonical JSON of the frozen
`modelIdentity`. The argv digest covers the exact argument array excluding the
executable. The configuration digest covers the sorted canonical inventory of
`{pathSha256, sha256}` file pins, ordered by `pathSha256`. Use canonical JSON
with sorted keys, UTF-8, compact separators and no non-finite values.
Prepare paths and inputs independently of the registration digest to avoid a
circular registration/configuration hash dependency.

## Typed observations and lifecycle

The evidence contract uses typed `NativeProcessRouteBinding`,
`NativeProcessRouteObservation`, and `CohortCashObservation` records. Their
serialized forms are strict: unknown or missing fields fail closed. A binding
includes the registration, slot, policy, account and namespace, candidate,
host build, executable, model, argv and configuration digests, plus the pinned
observer/cash sources and verifiers and freshness limit.

Each route observation identifies `prelaunch`, `running`, or `completed`, the
host authentication class, `included-subscription-quota` route, and the
literal `unknown-out-of-scope` account-wide state. It records fresh quota and
paid-control flags; API credential, provider override, and fallback
availability; observer connection and per-operation-gate state; source and
verifier references/digests; and an observation timestamp and strictly
increasing sequence. A prelaunch observation cannot claim a process identity.
Running and completion observations bind the owned PID and a process-birth
identity digest so PID reuse cannot substitute a different process. Timestamps
must be timezone-aware, non-future, fresh, and monotonic for the same process.

The independent cash observation binds the exact registration, source and
verifier, states numeric additional cash as exactly zero EUR, covers setup and
all started slots, and marks completion reconciliation only at completion.
An estimate, subscription route, UI control, parser output, or synthetic fixture
does not establish this cash fact.

Typed decoding and local structural validation establish shape and binding
consistency only. Every observation must be authenticated by an explicitly
installed trusted verifier that is independent of the observer's untrusted
assertions and authenticates both route evidence and the cash source. There is
no default, permissive, or mock verifier path eligible as proof. If no trusted
verifier or source is configured, v2 admission refuses before launch.

Migration is explicit: the v2 supervisor observer receives
`(identity, elapsed_seconds, final)` and returns a `TelemetrySnapshot` with
`native_route`. `identity` is absent only before launch, and `final` is true
only for completion reconciliation. The v1 observer keeps its two arguments
and `subscription` field. `NativeRouteVerifier.verify_observation` receives
the exact observation, binding, owned identity, process request and final flag.
Its source authentication and installed per-operation control remain external
obligations. A timed-out or failed callback cannot establish verification.

## Enforcement and refusal

A trusted external per-provider-operation gate must block startup and every
provider request until the current process, registration, account namespace,
route, configuration and cash evidence have been verified. It must recheck the
same conditions before each operation and prevent paid API or alternate-provider
fallback. The supervisor's startup observation, periodic polling, and final
snapshot support evidence and stop decisions; periodic polling alone does not
enforce the per-operation gate and cannot authorize a request.

No request starts, or the process stops before its next provider operation, if
any required source/verifier is missing, unauthenticated, stale, disconnected,
contradictory, or bound to a different registration, slot, host, account
namespace, candidate, build, executable, model, argv, configuration, or process
lifetime. The same refusal applies if included quota is unavailable or
exhausted; subscription is inactive; extra usage, credits, auto-recharge,
credentials, overrides, or fallback are enabled or unknown; the route changes;
the operation gate is inactive; cash is nonzero or unknown; or a frozen estimate,
time, resource, or registration limit is exceeded. Never retry through paid API
or another provider. Preserve the slot and failure outcome in the cohort ledger.

These checks do not claim account-wide API billing is disabled, do not observe
unrelated account activity, and do not establish actual cash until the
independent source proves and reconciles it. The policy does not authorize a
provider call, complete registration approval, native-host acceptance, human
evaluation, positive utility, milestone closure, or any reversal of historical
M4 G4 NO-GO.

## Bounded implementation and validation plan

The following identifiers are stable references for this policy work. Source
controls exercise the implemented clauses; the mandatory repository-profile
results are recorded separately on the exact candidate pull request. Synthetic
controls may verify fail-closed mechanics; they never
prove actual source authenticity, native route behavior, continuous request
gating, or cash.

- [x] **NP-001 — Additive strict schema and registration binding.** Implement the
  v2 policy and per-slot contracts without changing v1 serialization or
  acceptance. Validate exact roster coverage and frozen candidate, host,
  executable, model, argv, configuration, account-namespace, observer, and cash
  bindings. Evidence target: focused structural and v1-regression controls.
- [x] **NP-002 — Typed lifecycle observations.** Validate strict binding and
  observation shapes, fresh monotonic snapshots, PID/process-birth lifetime,
  prelaunch/running/completed phases, safe route flags, and setup/started-slot/
  completion cash coverage. Evidence target: positive and malformed, stale,
  replayed, drifted, quota-exhaustion, and nonzero/unknown-cash controls.
- [ ] **NP-003 — Trusted verifier and per-operation gate.** Require an explicit
  trusted external route/cash verifier before launch; block before the first
  provider operation and before every subsequent operation; prove observer loss
  and control changes stop before the next request. Evidence target: verifier
  contract controls plus a separately supplied authenticity assessment. Polling
  snapshots alone do not satisfy this task.
- [x] **NP-004 — Refusal integration and compatibility.** Exercise v2 refusal
  through registration, capture admission, and supervision while demonstrating
  unchanged v1 behavior and no paid/alternate-provider fallback. Evidence
  target: candidate-bound integration controls and preserved slot outcomes.
- **NP-005 — Root candidate validation and evidence boundary (mandatory gate).** On the stable
  integrated candidate, run the repository quick profile and then the PR
  profile, bind exact source and results, and report code controls separately
  from unavailable authentic observer, gate, cash, native-host, registration,
  human, and founder evidence. Keep SPEC-044 original T006/T009 and all original
  acceptance checkboxes pending until their own requirements are met.

Completion of NP-001, NP-002, NP-004 and NP-005 is bounded engineering readiness only. NP-003 additionally requires authentic external source and gate evidence, which remains unavailable. Authentic
native evidence, full registration approval, the 108-attempt cohort, human
ratings/adjudication, founder acceptance, and M4.5 closure retain their existing
separate gates.

The source controls are `tests.test_tooling_subscription`,
`tests.test_tooling_evaluation`, `tests.test_tooling_capture`,
`tests.test_tooling_hosts` and `tests.test_tooling_supervisor`. They include
strict v1 regressions, exact 108-slot policy binding, prelaunch cash coverage,
identity/sequence drift, quota and verifier refusal, callback timeouts, and
process termination before releasing stdin on an invalid startup observation.
Their verifier and route/cash sources are synthetic. Checked source clauses
do not satisfy NP-003 or any original registered SPEC-044 acceptance task.
