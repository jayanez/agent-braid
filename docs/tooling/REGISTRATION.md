<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Prepare the M4.5 registration

`examples/tooling/registration-draft.json` binds the proposed eighteen fixture
definitions and six prompts to the pinned source inventory. It is intentionally
invalid for capture: no owner approval, source-rights decision, provider opt-in,
exact model-build selection, EUR rate card, two human reviewers,
or frozen rubric is supplied. The numeric caps in [BUDGET.md](BUDGET.md) were
approved separately; model names remain recommendations. Cap approval does not
approve this registration. A later owner decision authorizes only existing
subscription use within included quotas, with EUR 0 additional spend; read-only
authentication and visible billing controls have been checked privately. That
decision does not approve the full registration or source rights. Missing values are not zero-cost
measurements or decisions.

Copy the draft to a private registration workspace after freezing the integrated
candidate. Record its full Git commit and the SHA-256 of the retained candidate
artifact (state the artifact and hashing procedure). Record wheel/sdist and skill
bundle hashes separately. Fill exact host/model/OS/SDK versions and immutable
records, then obtain protocol, rights, budget and owner review before observations.
Do not infer acceptance from the shape validator or turn a draft into `approved`
without an actual decision record.

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
For the owner's subscription-only route, freeze an exact `billingPolicy` using
`agent-braid-m45-subscription-policy-v1`: both host account hashes and authentication
methods, `mode: included-subscription-only`, `additionalSpendCapEur: 0`, and all
paid API, overage, credits and auto-recharge permissions false. Keep numeric
total-cost caps and cost rates separate. The policy is bound to the registration,
host, slot and account; changing it creates a different registration cohort.
Admission requires a fresh subscription observation and a verifier that explicitly
authenticates it. Host supervision checks a fresh trusted observer before launch,
during execution and at completion. Unknown quota, authentication, extra-spend
or paid-usage controls refuse or stop; no paid fallback is selected. Local process
cleanup does not guarantee cancellation of a provider request already sent.
Historical browser checks are insufficient for this live observer. Exact native
account identity, supported host builds and authoritative ongoing observations
remain capture prerequisites; a synthetic observer cannot supply them.
Register numeric EUR/token/total-wall/RSS/disk caps, rates and provider choice
before capture; retain unavailable values as null. Stop on incidents, exceeded
caps, missing immutable inputs, candidate/build drift, unrecoverable transitions
or two consecutive infrastructure failures. Preserve all intended slots.

The detailed protocol is
`specs/044-ai-tooling-evaluation/evaluation-protocol.md`; accounting behavior and
the validator's limits are in `docs/tooling/EVALUATION.md`. Two independent human
raters and a separate founder decision are required. Model review cannot supply
either. M4.5 closure does not close M3.5, M4 or reverse G4 NO-GO.
