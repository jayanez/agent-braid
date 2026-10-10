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

## Exact provisional allocation arithmetic

`agent_braid.tooling_allocation.calculate_subscription_time_allocation` provides
an additive, offline calculator for a supplied fixed-period subscription fee
multiplied by the union of use intervals divided by the actual elapsed period.
It uses integer UTC microseconds and exact rational arithmetic; overlapping
intervals count once. The calculation preserves the supplied currency and does
not convert to EUR or round amounts. String timestamps require explicit UTC
(`Z` or `+00:00`) and at most six fractional-second digits; greater precision is
refused. Input snapshots accept at most 4,096 interval receipts and refuse
excess input without silently truncating it.

Import the calculator, `UsageInterval` and `IntervalCoverage` from
`agent_braid.tooling_allocation`. `IntervalCoverage.unknown()` produces unknown
duration and amount. `IntervalCoverage.declared_complete(())` represents an
explicit caller declaration of complete zero use. The declaration and supplied
source/account/interval references and hashes are unauthenticated inputs. The
payload binds those inputs, period bounds and exact share/amount rationals with
canonical hashes, and labels the result as a provisional calculation. Hashes do
not establish source authenticity or coverage completeness.

This calculator does not choose or approve the registered allocation method,
produce a final `MoneyReceipt`, authenticate a live source, or authorize dispatch.
External source and policy verification, final currency/rounding rules and
closed-period reconciliation remain required. The existing monetary ledger and
its final receipt close-time rule are unchanged.

## Technical and human-inclusive scope

The existing `fullCostScope` shape remains prospective. It is required for v3 and
its approved scope is technical: it binds the already-defined allocation, user-time,
wall-time, receipt-source and approval fields while preserving two reviewer-fee
rows as `unknown`. For v1/v2 it remains optional and retains its prior named-reviewer
semantics. A v3 technical-scope approval is not approval of reviewer fees or reviewer
activity, source rights, capture, or full human-inclusive accounting. Missing or
`pending` scope never yields a technical-scope summary. Before v3
technical capture, the approved scope binds the existing study-cash/accounting
boundary for setup and attempts, subscription allocation and its evidence, one
user-time participant, technical wall-time sources, receipt verification and the
scope approval record. The same existing `reviewerFees` field contains exactly
two rows keyed to the planned roles, each with `unknown` applicability. The
existing reviewer activity field remains part of the scope shape, while reviewer
time receipts are deferred. These unknown reviewer rows do not prevent measured
technical setup/user/108-attempt costs and technical wall time from being complete.

After the human phase, full human-inclusive accounting additionally requires
resolved reviewer fee applicability and any applicable source-authenticated fee
receipts, authenticated active-work time for both reviewers across the registered
attempts, and a wall-time total that includes those human intervals. Unknown fee
applicability or absent reviewer time remains unavailable; no unpaid status, zero
fee, or combined human-inclusive total is inferred. Legacy v1/v2 retain their
existing named-reviewer scope and completion behavior.
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

A v3 technical scope may support completion of measured technical costs when the
existing scalar assessment is complete, all 108 attempts have terminal records,
required technical cash/subscription receipts are authenticated and within caps,
the allocation method matches the approved scope and policy attestation, and
technical setup/user/attempt and wall receipts are verified.

The report still withholds technical aggregate values until a trusted summary
verifier binds the exact summary digest to the registration SHA-256, roster SHA-256,
approved scope SHA-256 and receipt inventories, and verifies complete required
technical measures/coverage with no missing rows. The v3 report builder accepts
`technical_cost_verifier`; its `verify_technical_summary(...)` result is exposed as
`costs.technicalMeasuresAttested`. Missing, mismatched, unsupported, forged or incomplete attestation
means `costs.technicalMeasuresAttested` is false and displayed technical values stay unknown, while stored measurements and
receipt histories remain retained. The technical-only summary fields are
`technicalRequiredMeasuresComplete`, `missingTechnicalRequired`,
`technicalAdditionalSpendEur`, `technicalCapViolation` and
`technicalStopRequired`. `technicalAdditionalSpendEur` covers only actual setup and
108-attempt additional spend. `technicalStopRequired` clears only after technical
receipt, time, outcome and cap checks pass. The legacy `actualAdditionalSpendEur`,
`requiredMeasuresComplete`, `capViolation` and `stopRequired` keep their all-in
meanings and cannot be read as technical-only results; unresolved reviewer fees
keep `actualAdditionalSpendEur` null and completeness incomplete. An
attested technical report may show provider/allocation/user/wall values, but reviewer
and combined human-inclusive totals remain unknown. A test verifier is synthetic
only and does not establish live accounting evidence.The combined
human-inclusive economic summary remains incomplete: reviewer fee applicability,
reviewer time and any total that includes them remain unavailable. Full human-inclusive
completion requires the later human scope/addendum and authenticated reviewer records.
Legacy v1/v2 completion retains the prior full human-cost requirements. Positive
cash, missing or stale scope/roster/registration, unverified methods, unavailable
cost values or time intervals, unknown reviewer-fee applicability, a missing wall
source, cap excess, or incomplete attempts remain ineligible. API reference estimates never enter
actual or allocated totals. Full cost completion means registered cost
measurements are complete; it does not assign a monetary price to observed
human time, assert utility, or satisfy T006's future capture/reconciliation
evidence on its own.

The v3 registration must carry the approved technical accounting scope before it
can validate for technical capture. Reviewer fee applicability remains unknown; no
source or fee approval is inferred. Method/denominator/unit and their approval
records must be bound in the registration. This document records the interface boundary, not an
owner decision or permission to incur charges. The offline report/export pipeline
composes these fields and suppresses utility claims when required costs or scope
are missing. These synthetic controls do not replace authenticated
T002/T004/T005 capture. All 108 intended slots remain in scope; the later human phase remains required
for human-inclusive accounting and interpretation. Missing rows cannot be dropped
or relabeled as zero.

`requiredMeasuresComplete` in the base money summary covers the required
additional-cash evidence only. The full-cost composer additionally binds the
existing scalar cost assessment and external approval/time attestations. For a
registration with `billingPolicy`, `assess_utility_eligibility` requires the
matching registration and roster, complete status, available money amounts and
no stop; callers should pass only the summary returned by
`complete_full_cost` when evaluating the prospective full scope. This preserves
the existing non-subscription v1 evaluator behavior.
