<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Owner decision: estimated subscription accounting for technical capture

Date: 2026-10-11. The owner selected the conservative planning estimate and
instructed the project not to inspect further private billed-period data:
“Quédate en esa estimación. No vamos a bajar al detalle de los datos privados del periodo facturado”.
The convention is approved; its versioned implementation and complete technical
registration remain separately pending. This is not capture approval, ADR adoption,
founder acceptance or milestone closure.

## Declared convention

Reserve EUR 5.045 for subscription value under the following planning assumptions:
the two privately retained per-host monthly planning amounts, a nominal 28-day denominator
(2,419,200 seconds), and at most 57,600 active technical seconds per host. The approved reservation is retained as a declared budget bound. Individual
planning inputs and source records remain private; no actual invoice amount or
billed period is published here.
These prices are retained source observations; the denominator is a declared
planning assumption, not an observed billed period. This bound is conditional on
the fixed assumptions and active-time limits. Do not retrieve exact invoice periods
to implement this decision, or infer them from a renewal date.

Register the estimate/reservation separately from actual monetary measures,
binding the convention, input evidence and owner decision by digest. Reserve the
full amount before the first dispatch and enforce the per-host active-time limits
without counting overlapping intervals twice. Missing active-time evidence,
changed assumptions, an exhausted reservation or exceeded numerical caps refuse
or stop. All 108 intended slots remain in the denominator, including refusals and
interrupted attempts. This convention does not permit silent retries.

The EUR 25 ceiling includes the estimate reservation plus separately verified
provider cash. EUR 0 additional spend remains a hard independent constraint;
unknown cash does not become zero. Existing token, total-wall, RSS and disk caps,
source rights, host/configuration identity and fresh subscription observations
remain required. The 16-hour total-wall cap is not enlarged by the per-host
planning allowance.

## Interpretation boundary

Expose an explicitly named estimate/reservation and a separate bounded technical
capture status. Do not populate `allocatedSubscriptionCostEur` or
`providerAccountingCostEur` from this estimate. Their actual values remain unknown
without source-backed reconciliation. Existing actual-economic completion and
positive utility gates stay closed when actual costs or deferred human fields
are missing. Estimated-budget technical readiness is not measured cost, savings,
human-inclusive economic completion or empirical utility.

Two independent human evaluations and adjudication remain deferred. No reviewer
fee or time is assumed zero. Any later actual accounting is a separate optional
source-backed addendum; the technical route under this decision must not demand
additional private period disclosure.

This decision changes only the estimated subscription accounting convention.
The existing policy's account-wide API-billing observation requirement remains
unchanged. Narrowing that observation to a selected native process route would
require a separate versioned policy decision. No API calls, credits, overage,
auto-recharge or additional payment are authorized.

The prospective requirements are recorded in [the draft assurance addendum](subscription-estimation-assurance-addendum.json). The inherited assurance record and obtained historical evidence remain unchanged; no evidence is rebound to the new estimated route.
