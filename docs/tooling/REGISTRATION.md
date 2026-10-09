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
