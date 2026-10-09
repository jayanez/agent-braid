<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Experimental subscription monetary records

`agent_braid.tooling_money` adds v2 monetary receipts alongside the unchanged v1
cost book. It separates actual additional cash, allocated prepaid subscription
value and API-reference estimates. An estimate never counts as money paid.
Permission for EUR 0 additional spend is not an observed zero-cost receipt.
Missing amounts, invoice/fee evidence and reviewer costs remain unknown.

The roster binds the exact validated registration, all 108 generated slot IDs,
setup and the two registered human reviewer activities. Receipts bind account,
source-document billing period, cohort coverage period, currency/FX provenance,
registered allocation method and denominator, or the matching model rate record.
A monthly invoice may contain the shorter cohort period. External verifiers must
authenticate source facts, complete slices, amount/share/FX calculations and
cross-ledger nonoverlap. This module performs no invoice lookup, provider request,
FX conversion, allocation calculation or choice of an allocation method.

Within one ledger, source slices cannot be reused and allocations for the same
account, statement, method, coverage and denominator cannot exceed the whole.
Independent accounts and statements retain separate denominators. Publication
is serialized and verifier reentry refuses. Decimal inputs have at most 30
coefficient digits, exponent from -30 through 30 and 64 serialized characters;
aggregation uses exact integer scaling independent of ambient Decimal precision.

The proposed study cash measure includes setup, provider activity and paid review;
its conservative EUR 0 cash cap is broader than the provider billing policy.
It authorizes no payments or reviewers. Positive observed cash remains recorded
and sets a stop/violation; incomplete cash coverage cannot prove compliance.
This proposed applicability must be reviewed in the full prospective registration.
Human work time remains separately measured by the existing complete-cost protocol;
no hourly valuation, unpaid-fee zero or subscription allocation is invented.

`requiredMeasuresComplete` reports availability for its declared measures only.
`fullEconomicCostComplete` remains false with status
`pending-registered-cost-scope-and-human-cost-fields` until prospective protocol
scope, reviewer-payment applicability, human-cost fields and their pipeline
integration exist. A full summary binds the registration SHA as well as the roster.
For a registration selecting `billingPolicy`, `assess_utility_eligibility` requires
a matching monetary summary and independently frozen monetary roster digest,
with complete economic scope, available actual amounts and no cash stop.
The evaluator checks consistency and bindings; source authenticity remains the
trusted caller/verifier responsibility.
Complete legacy EUR/token/time fields or EUR 0 additional cash cannot bypass that
gate. The existing non-subscription v1 evaluator behavior is preserved.

These are engineering controls and experimental representation, not a complete
native-host utility-cost pipeline or an approved allocation protocol. Founder
registration, source rights, human raters, rubric and capture approval remain
separate; the owner-approved model identity clarification changes none of them.
