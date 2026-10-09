<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Prospective M4.5 cost contract (experimental)

`agent_braid.tooling_money` and `agent_braid.tooling_full_cost` define an
additive, candidate-bound accounting representation for SPEC-044 T006. They
do not change the legacy v1 scalar ledger or measure provider billing, tokens,
or human activity by themselves. The representation is not an accepted
registration, capture authorization, billing statement, or utility result.

SPEC-044 REQ-006/SC-006 requires complete setup/provider/tool/runtime/export/
user/reviewer cost fields, explicit unknowns, numerical stops, and reconciliation
over the full intended-attempt roster. Its protocol requires setup and per-attempt
discovery, provider wait/latency, tokens and retries, MCP/runtime preparation,
execution, verification, recovery, export, and user/reviewer time. The existing
`tooling_evaluation.assess_cost_completeness` remains the source of the eight
registered scalar fields (`eur`, token fields, wall seconds, RSS and disk) over
setup plus all 108 exact attempt slots. `tooling_measurements.WallClock` records
one total-wall boundary; phase intervals are descriptive and must not be added
to it. Monetary API estimates remain separate from actual cash and allocated
subscription value.

For subscription registrations, the EUR 25 provider accounting ceiling uses
`providerAccountingCostEur`: authenticated setup/attempt cash
(`actualProviderSpendEur`) plus allocated prepaid subscription value, exactly
once. It excludes reviewer cash and API reference estimates. The legacy scalar
`eur` is retained in its ledger but is not added again to this derived total.
The separate EUR 0 additional-cash cap covers all study cash, including any
reviewer fees. Unknown provider cash or allocation leaves the accounting total
unknown and stops eligibility. Exact Decimal comparisons prevent tiny cap
excesses from disappearing through floating-point rounding.

The monetary roster binds the exact validated registration, all 108 generated
slot IDs, setup and the two registered reviewer activities. Receipts bind
account, source-document billing period, cohort coverage period, currency/FX
provenance, registered allocation method and denominator, or matching model
rate record. A monthly invoice may contain the shorter cohort period. External
verifiers authenticate source facts, complete slices, amount/share/FX
calculations and cross-ledger nonoverlap. The module performs no invoice lookup,
provider request, FX conversion, allocation calculation or choice of method.
Within one ledger source slices cannot be reused; allocation totals are capped
per account, statement, method, coverage and denominator. Independent accounts
and statements retain separate denominators. Publication is serialized and
verifier reentry refuses. Decimal inputs are bounded to 30 coefficient digits,
exponents -30 through 30 and 64 serialized characters; aggregates use exact
integer scaling independent of ambient Decimal precision.

The extra `fullCostScope` field is prospective and optional at registration
validation. Missing or `pending` scope never yields a complete monetary summary.
To complete the T006 representation, a future owner-approved registration must
bind all of the following before capture:

- the full study-cash scope, including provider/setup charges and any paid
  reviewer fees, under the registered EUR 0 additional-cash cap;
- explicit `paid` or `unpaid` applicability for each of the two registered
  reviewers; `unknown` remains incomplete, and neither unpaid fees nor zero
  amounts are inferred without source-authenticated receipts;
- subscription allocation for setup and every one of the 108 attempts, plus an
  explicit authenticated `not-applicable` marker for reviewer subscription
  allocation; the method identity, denominator and unit are exact and the
  separate verifiers authenticate the policy and source facts;
- one registered user-time participant covering setup and every attempt, and
  both registered reviewers covering every attempt, through source-authenticated
  active-work intervals. The registration binds the meaning of active work;
  receipts may cover one or more activity IDs, and their sets must exactly cover
  the approved participant/activity scope without duplicate coverage. There is
  no fixed interval count or synthetic per-slot zero.

The scope approval verifier binds the final registration hash, exact monetary
roster hash, scope hash and approval-record identity. This avoids a self-
referential hash. Registration validation and hashes alone do not authenticate
the owner or approval. Each interval verifier binds the exact time receipt. A
separate study-wall verifier authenticates one runtime/setup elapsed interval
for setup and each of the 108 attempts. The registration's elapsed wall cap is
computed from the union of those intervals and authenticated human review
intervals; overlapping time counts once. Human labor totals are separately
reported by participant role, with per-person interval unions preventing double
counting. No hourly rate or monetary value for human time is invented or
required by this representation. Reviewer cash receipts require an
authenticated invoice source even when the amount is zero.

A full summary can be marked complete only when the existing scalar cost
assessment is complete; all 108 attempts have terminal records; all required
cash and subscription receipts are authenticated and within the zero cap; the
allocation method matches the approved scope and its separate policy
attestation; and every registered human-time interval is present and
authenticated. Positive cash, missing or stale scope/roster/registration,
unverified methods, unavailable cost values or time intervals, unknown
reviewer-fee applicability, a missing wall source, cap excess, or incomplete
attempts remain ineligible. API reference estimates never enter
actual or allocated totals. Full cost completion means registered cost
measurements are complete; it does not assign a monetary price to observed
human time, assert utility, or satisfy T006's future capture/reconciliation
evidence on its own.

No current registration includes this approved scope. Fee applicability,
method/denominator/unit, and any additional owner decisions remain draft until
prospectively approved. This document records the interface boundary, not an
owner decision or permission to incur charges. The offline report/export pipeline
composes these fields and suppresses utility claims when required costs or scope
are missing. These synthetic controls do not replace authenticated
T002/T004/T005 capture. All 108 intended slots and human review remain in
scope; missing rows cannot be dropped or relabeled as zero.

`requiredMeasuresComplete` in the base money summary covers the required
additional-cash evidence only. The full-cost composer additionally binds the
existing scalar cost assessment and external approval/time attestations. For a
registration with `billingPolicy`, `assess_utility_eligibility` requires the
matching registration and roster, complete status, available money amounts and
no stop; callers should pass only the summary returned by
`complete_full_cost` when evaluating the prospective full scope. This preserves
the existing non-subscription v1 evaluator behavior.
