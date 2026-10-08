<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Verified cost reconciliation

`agent_braid.tooling_costs` reconciles explicitly supplied, externally verified
cost receipts. It does not fetch invoices, infer billing from host output, or
authorize provider calls. The external `CostVerifier` must authenticate each
source and its complete observation scope, binding its attestation to the exact
receipt digest. A test verifier is only a synthetic control.

Freeze an activity roster before accounting. Include setup, every registered
attempt, and human work outside attempt intervals as separate disjoint activities.
One receipt contains the complete cumulative outer activity; phases are not
added. Distinct activity intervals cannot overlap. Late invoice observation time
is separate from the activity end, so reconciliation does not invent additional
elapsed work. Human time must be observed, never assumed from a review estimate.

Each activity's latest consecutive revision is counted once. All original
receipts and attestations remain inspectable in `history`. Previously measured
costs cannot decrease or become unknown. One physical source cannot be assigned
to multiple activities. Callers must persist this history privately; the book is
an in-memory reconciliation component, not a crash-safe evaluation ledger.
Verification and publication are serialized inside each book, and a verifier
cannot reenter publication. This guard does not coordinate separate books or
processes; durable cohort coordination remains the session ledger's boundary.

Actual invoice and provider meter EUR values are distinct from estimates and
reference prices. Estimates remain in history but contribute unknown EUR to the
measured view. A later authenticated actual receipt may replace an estimate.
Currency conversion, subscription allocation and meter completeness must be
verified at the external source boundary; this module performs none of them.

Total tokens equal primary input plus primary output plus retry tokens. Primary
counts exclude retries. EUR, tokens and activity wall seconds sum across activities;
RSS is the largest declared process-set peak, and disk is the largest declared
cohort retained-byte high water. A per-attempt directory measurement does not
establish the cohort disk total. The verifier must reject incomplete process sets
and incompatible disk scopes.

Missing activities or fields remain `None`, which admission rejects. A derived
snapshot keeps the oldest source observation time. It cannot make stale telemetry
fresh, serve as live billing by itself, or settle terminal evaluation events.
Live supervision still needs a fresh externally verified cumulative source. Final
accounting requires every roster activity, actual cost sources and separately
registered human observations. Passing these synthetic controls does not complete
SPEC-044's registered capture or human evaluation.
