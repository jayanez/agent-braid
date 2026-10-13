<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Prepare the M4.5 registration

`examples/tooling/registration-draft.json` is the existing legacy v2 draft, preserved unchanged, and binds the proposed eighteen fixture
definitions and six prompts to the pinned source inventory. It is intentionally
invalid for capture: no owner approval, source-rights decision, provider opt-in,
exact provider model identity selection, EUR rate card, human identities,
or frozen rubric is supplied. The prospective v3 draft is
`examples/tooling/technical-registration-draft.json`; it shows the v3 phase/deferral/role fields, with placeholder values that must be replaced by the approved deferral record and the two abstract independent reviewer roles. Keep `humanReviewers` empty. The numeric caps in [BUDGET.md](BUDGET.md) were
approved separately; model names remain recommendations. Cap approval does not
approve this registration. A later owner decision authorizes only existing
subscription use within included quotas, with EUR 0 additional spend; read-only
authentication and visible billing controls have been checked privately. That
decision does not approve the full registration or source rights. Missing values are not zero-cost
measurements or decisions.

The owner subsequently approved [the technical cohort model choices](../../specs/044-ai-tooling-evaluation/model-selection-decision.md)
on 2026-10-11: Codex `gpt-6-luna` and Claude Code's observed `sonnet` alias
resolving to Sonnet 5.5, both with medium effort. This separate selection decision
does not approve either example draft or the complete technical registration.

Copy the draft to a private registration workspace after freezing the integrated
candidate. Record its full Git commit and the SHA-256 of the retained candidate
artifact (state the artifact and hashing procedure). Record wheel/sdist and skill
bundle hashes separately. Fill exact host/OS/SDK versions and explicit provider
model identities, then obtain protocol, rights, budget and owner review before observations.
Do not infer acceptance from the shape validator or turn a draft into `approved`
without an actual decision record.

The owner approved the [observable model identity interpretation](../../specs/044-ai-tooling-evaluation/model-identity-clarification.md)
on 2026-10-09. Use immutable provider identifiers when exposed. Otherwise freeze
the requested selector/effort, native executable build/hash, dated catalog artifact
and entry hashes, effective selection/configuration and authenticated account/provider
route; record the backend identity as unavailable. Keep route/catalog metadata
separate from model-build fields. Requested and host-reported selectors are separate
observations. Observable drift requires a new reviewed registration and separate
cohort; hidden backend revisions remain an explicit reproducibility limit. This
approves one interpretation only; all 108 slots and other approvals remain required.

Fixture registration hashes identify canonical definitions; materialization also
records the exact runtime input hash, temporary repository identity, base/operation
commits and expected tree. Keep both identities in each receipt. Temporary paths
vary between isolated attempts and must not silently replace the registered
definition identity. Prompt hashes bind the exact fixed UTF-8 text.

The selected prospective cohort is 108 attempts: two hosts, three arms, six
classes and three fixtures per class. The arms are CLI, MCP only and MCP plus
all five skills. Both actual hosts must first provide candidate-bound discovery,
skill-loading and basic-journey receipts. SDK clients and emulated Linux package
controls do not satisfy that gate. Existing M4 legacy receipts are predecessor
context only.

Use `validate_registration` with the actual candidate digest and the complete
caller-verified fixture/prompt hash inventory; use `new_ledger` only after all
required decisions are authentic and the object validates. The offline evaluator
does not launch or authorize sessions. The session coordinator reserves one
dispatch against a durable cohort ledger head and requires fresh attested
cost/stop observations. Local collectors and one-shot event parsers provide
bounded inputs, with their coverage limits. Explicit host adapters and a
bounded process supervisor are implemented with synthetic process controls.
Authentic decision/outcome verifiers, complete live cost sources, actual host
provenance and verified configuration/isolation remain required before W18/W19.
The software does not authenticate those external facts.
For v3 technical capture, the exact `billingPolicy` is mandatory: freeze it using
`agent-braid-m45-subscription-policy-v1`: both host account hashes and authentication
methods, `mode: included-subscription-only`, `additionalSpendCapEur: 0`, and all
paid API, overage, credits and auto-recharge permissions false. Keep numeric
total-cost caps and cost rates separate. The legacy v1/v2 optional-policy contract
remains unchanged. The policy is bound to the registration,
host, slot and account; changing it creates a different registration cohort.
Admission requires a fresh subscription observation and a verifier that explicitly
authenticates it. Host supervision checks a fresh trusted observer before launch,
during execution and at completion. Unknown quota, authentication, extra-spend
or paid-usage controls refuse or stop; no paid fallback is selected. Local process
cleanup does not guarantee cancellation of a provider request already sent.
Historical browser checks are insufficient for this live observer. Exact native
account identity, supported host builds and authoritative ongoing observations
remain capture prerequisites; a synthetic observer cannot supply them.
The [v2 monetary representation](MONEY.md) is experimental. The full registration
must review allocated subscription value and human-cost applicability separately
from additional cash; no allocation method or reviewer-fee zero is approved here.
A subscription policy cannot support positive full-cost utility from legacy scalar
EUR data alone. Preserve unknowns and all 108 slots.

Register numeric EUR/token/total-wall/RSS/disk caps, rates and provider choice
before capture; retain unavailable values as null. Stop on incidents, exceeded
caps, missing immutable inputs, candidate/build drift, unrecoverable transitions
or two consecutive infrastructure failures. Preserve all intended slots.

For v3 included-subscription-only registration, unavailable reference API prices
are recorded as an explicitly unknown host/model row: both per-token rates,
the rate-record identifier and its hash are null. This does not describe a
zero-price provider, waive the allocated-subscription accounting ceiling or
authorize paid API use. A priced row still needs finite nonnegative rates and
its source record. Legacy v1/v2 rate requirements remain unchanged. An unknown
reference row cannot support an API-equivalent estimate; actual cash,
subscription allocation and live admission measurements retain their separate
verification and completeness requirements.

For v3, include an approved technical `fullCostScope` using the existing scope
shape. It binds technical allocation, user/setup/attempt time, wall-time receipt
sources and scope-approval evidence; both reviewer-role fee rows remain `unknown`.
That scope permits technical accounting only and does not approve any reviewer fee
or complete human-inclusive totals. Preserve legacy v1/v2 scope semantics.

Even with that scope, a report shows technical aggregate values only after a trusted
summary verifier attests the exact summary against the registration, roster, scope,
complete technical measure coverage and receipt inventories. Without a matching, supported attestation, or when the summary is forged or
incomplete, `costs.technicalMeasuresAttested` is false; stored measurement rows
remain retained but displayed aggregates are unknown. A synthetic verifier is not
live evidence. The technical cash subtotal
`technicalAdditionalSpendEur` covers setup plus all 108 attempts;
`technicalStopRequired` clears only after technical receipt/time/outcome/cap checks
pass. Global `actualAdditionalSpendEur`, `requiredMeasuresComplete`, `capViolation`
and `stopRequired` retain their all-in meanings. `actualAdditionalSpendEur` stays null while reviewer fee applicability is unresolved. Reviewer and combined human-inclusive values remain unknown. Freeze the prospective [outcome rubric](OUTCOME_RUBRIC.md) before capture. The detailed protocol is
`specs/044-ai-tooling-evaluation/evaluation-protocol.md`; the owner decision
deferring only human outcome ratings/adjudication is recorded in
`specs/044-ai-tooling-evaluation/human-evaluation-deferral-clarification.md`.
Freeze the rubric before technical capture. T007 remains partially pending; T008/T009
may establish technical readiness with human work pending. Verified technical
setup/user/attempt costs and wall times may be complete while reviewer fee/time
and combined human-inclusive totals remain unavailable. Technical cost completion
is not full human-inclusive economic completion, and no positive utility claim
is available. Later human identities/ratings/adjudication require a separately
bound addendum. Model review cannot replace human review. M4.5 closure does not close
M3.5, M4 or reverse G4 NO-GO.

## Owner-selected estimated subscription convention

On 2026-10-11 the owner selected the [estimated subscription convention](../../specs/044-ai-tooling-evaluation/subscription-estimation-decision.md) and declined further inspection of private billed-period data. The versioned estimate route must reserve EUR 5.045 under its explicit nominal 28-day and 16-active-hour-per-host assumptions. It must bind the input sources and decision, enforce the reservation and time limits, and retain the independent EUR 0 additional-cash gate and EUR 25 ceiling.

This is a prospective estimated accounting route, not actual allocation. Actual `allocatedSubscriptionCostEur` and `providerAccountingCostEur` remain unknown without actual reconciliation. Reports must distinguish technical capture under an estimated bound from actual economic completeness and utility. The versioned v4 estimate implementation is available and has passed synthetic controls; complete registration approval and authenticated native evidence remain pending. Legacy registration v1/v2 and subscription-policy-v1 keep their prior semantics; the native-process-route-policy-v2 contract is additive.

The experimental `agent-braid-m45-registration-v4` route inherits the v3 phase, human deferral, role, subscription-policy and observable-model requirements. It additionally binds `subscriptionAllocationUpperBound` with schema `agent-braid-m45-subscription-estimate-v1` and method `m45-nominal-28day-active-time-upper-bound-v1`. Its exact inputs are `nominalPeriodSeconds: 2419200`, privately retained source-backed per-host monthly planning prices, `maxActiveSecondsPerHost: 57600`, `reservationEur: "5.045"` and `budgetCeilingEur: "25.00"`. Decision and both price-source digests must authenticate their actual records; placeholder digests do not establish approval or source authenticity.

Active-time observations must use an ISO-8601 UTC timestamp ending in `Z`, be no more than 60 seconds old at admission and immediately before process creation, and never be future-dated. Every estimate guard requires a verified, receipt-bound admission lease for the exact registration, host and ledger snapshot. The supervisor consumes that lease once before launching; missing, mismatched or replayed leases refuse execution. Reports must bind the exact digest of the active-time evidence used for their estimate. These checks establish binding and freshness, while source authenticity remains the trusted verifier's responsibility.

[The v4 example](../../examples/tooling/estimated-technical-registration-draft.json) is intentionally invalid: source/decision bindings and other prerequisites remain missing. Preserve the previous v2/v3 examples. Before each dispatch, the active-time snapshot must bind the frozen registration and exact 108-slot ledger head. The budget reserves the whole estimate, rather than treating unused reservation as permission for extra spending. Runtime supervision enforces remaining active-time limits. A prepared configuration is not proof of an actual provider route.

## Native-process route policy v2 contract

The owner approved only the process-scoped observation boundary in
[ADR 0021](../adr/0021-codex-claude-tooling-integration.md#approved-scope-native-process-billing-observation-boundary).
The additive implementation contract and bounded validation work are specified in
[SPEC-044's native-process route policy](../../specs/044-ai-tooling-evaluation/native-process-route-policy.md).
A future v3/v4 registration may select the additive
`agent-braid-m45-native-process-route-policy-v2` policy; this does not alter
legacy v1/v2 registrations or weaken v1's explicit account-wide billing-false
requirement.

The v2 registration binds account and provider namespace digests, every slot's
host/build/candidate/executable/model/configuration/argv digests, and explicit
observer and independent cash source/verifier identities. Its evidence is
process-lifetime scoped: fresh typed route snapshots bind the exact slot and
owned process identity, while a trusted external gate must block startup and
each provider operation until route and cash checks pass. Polling snapshots
alone cannot enforce that gate. Missing or unverifiable trust refuses before
launch; loss, staleness, quota exhaustion, settings/route drift or other failed
controls stop before the next operation, with no paid API or alternate-provider
fallback.

`accountWideApiBilling` stays `unknown-out-of-scope`, never false. Independently
verified, cohort-attributable actual additional cash must equal EUR 0 and cover
setup, all started slots, and completion reconciliation. The EUR 5.045 estimate
remains a separate reservation and is not actual allocation, provider
accounting, or cash. The policy creates no trusted observer, verifier, cash
source, registration approval, or capture authorization. v2 acceptance,
authenticity, and all capture evidence remain pending; no raw credential values
or private billing-period identities belong in the registration record.

## Operational subscription capture policy v3 and registration-v5

On 2026-10-11 the owner approved Alternative B as an additive operational
subscription route. See the [operational policy](../../specs/044-ai-tooling-evaluation/operational-subscription-capture-policy.md)
and [ADR 0021](../adr/0021-codex-claude-tooling-integration.md). The policy
`agent-braid-m45-operational-subscription-policy-v3` and registration-v5 bind
the authenticated native route/account namespace, host/build, executable,
effective configuration, exact argv, model, candidate and slot; fresh
authoritative quota/credits/extra-usage/auto-recharge state; and absence of API
keys, helper credentials, provider overrides and paid fallbacks. A bounded
supervisor polls and refuses further work on quota exhaustion, unknown or stale
state, observer loss, drift or its limits. This operational quota boundary is
not a per-internal-request client veto.

Additional spend remains capped at EUR 0, with no purchases, overages, paid API
or alternate-provider fallback. Actual cohort cash remains unknown/null until
independent authoritative verification covers setup, all started slots and
completion reconciliation. That actual-cash evidence gates acceptance and
positive utility; it is not required before every internal provider request.
The estimate route remains separate from actual allocation, provider
accounting and cash. The existing estimate convention, 108-slot roster,
human-review deferral, candidate/host/resource/rights requirements and
acceptance gates remain in force. Strict registration-v1/v2 and
subscription-policy-v1 semantics are unchanged. The additive implementation
and synthetic controls are available from PR #499. Complete authentic native
admission/supervision evidence, registration approval and capture authorization
remain pending; see the [technical completion preparation](TECHNICAL_COMPLETION_20261011.md).

## Assisted source registration v6

The prospective [v6 draft](../../examples/tooling/assisted-source-registration-draft.json)
uses `agent-braid-m45-registration-v6` and the distinct
`agent-braid-m45-source-subscription-policy-v1`. It preserves the 108 slots,
original cap/estimate/model/rights/deferral requirements and historical schemas.
The draft is intentionally invalid: its exact candidate, approvals, private
account/store/source identities, instruments and audit seed are still missing.
No null or example declaration authorizes capture.

`agent_braid.tooling_registration_v6` adds:

- `sourceContractTemplates`: exactly one approved Codex and Claude source
  contract template. Omit `binding` from templates; per-slot bindings are
  instantiated after the complete registration hash exists, avoiding a circular
  digest. All 108 `billingPolicy.processContracts` are still mandatory.
- `claudeLaunchStore`: the digest of the existing canonical absolute config
  directory's UTF-8 path and its observed Keychain suffix. Directory aliases,
  a different environment path and suffix drift refuse; path hashing alone
  does not authenticate stored credentials or the running route.
- `humanAuditPolicy` and its canonical `humanAuditPolicySha256`: freeze the
  algorithm, seed and escalation rule before results. `audit_selection()`
  derives the same initial 36 cases across all three arms. Admission attests
  both the policy and selection digests. An external owner record must establish
  prospective timing and approval; hashes cannot establish either.
- `instrumentPins`: independently frozen source/verifier references and byte
  digests for `admission`, `outcome`, `costs` and `technicalSummary`. Explicitly
  installed trusted instruments remain necessary. Pin equality is identity,
  not authentication of provider, cost or human facts.

The declaration-only legacy projection reuses existing validators. It never
creates a v3 observation or infers v3 booleans from the new source composition.
`SourceRouteBinding`, source observations and their supervisor path remain
separately typed/versioned. Restoring serialized source bytes produces checked
claims; a trusted runtime verifier must authenticate them again.

The consumer uses the original individual source times: at most 60 seconds
for Codex; Claude allows up to 900 seconds only for recharge. Quota/process
receipts and the earliest source expiry still control availability. Both
`prelaunch` and running/completed phase, exact PID and kernel birth are checked;
stdin is withheld until the process link passes. The supervisor's separate
one-second consumer deadline is retained. See [source acquisition](SOURCE_OBSERVER.md),
[interface observations](INTERFACE_OBSERVER.md) and the
[prospective audit decision](../../specs/044-ai-tooling-evaluation/assisted-audit-decision.md).

`CostBook(..., registration=registration)` binds the costs instrument at
installation and publication for v6. The legacy constructor remains available
for earlier/unregistered controls. Outcome instruments are bound before a
session start. The separate assisted technical report preserves actual automatic,
model and human provenance and explicitly leaves unaudited human cases unaudited;
legacy full-human utility assessment refuses v6. No report records founder
acceptance or turns an estimate into actual cash.
