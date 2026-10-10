<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Verified cost reconciliation

`agent_braid.tooling_costs` reconciles explicitly supplied, externally verified
cost receipts. It does not fetch invoices, infer billing from host output, or
authorize provider calls. The external `CostVerifier` must authenticate each
source and its complete observation scope, binding its attestation to the exact
receipt digest. A test verifier is only a synthetic control.
For v3 reporting, receipt verification is followed by a separate technical-summary
attestation. `agent_braid.tooling_full_cost.TechnicalCostSummaryAttestation` binds
the exact registration, generated roster, approved `fullCostScope`, summary digest
and technical receipt inventories through `verifier_id`, `summary_sha256`,
`registration_sha256`, `roster_sha256`, `scope_sha256`, `receipt_sha256s`,
`human_time_receipt_sha256s`, `study_wall_receipt_sha256s` and `verified_at`. It also binds `technical_activity_ids`, `actual_spend_activity_ids`,
`allocated_activity_ids`, `user_time_activity_ids` and `study_wall_activity_ids`;
each must exactly equal the sorted setup activity plus all 108 registered slot
IDs. The report builder's optional
`technical_cost_verifier.verify_technical_summary(...)` must confirm complete
required technical measures and coverage with no missing technical rows. This
summary attestation controls whether aggregate values may be displayed; it does not
replace or discard the stored receipt history. If absent, mismatched, unsupported, forged or incomplete,
`costs.technicalMeasuresAttested` is false and report technical aggregate values
are unknown. Technical summary fields are
`technicalAdditionalSpendEur`, `technicalRequiredMeasuresComplete`,
`missingTechnicalRequired`, `technicalCapViolation` and `technicalStopRequired`;
the cash subtotal covers setup and the 108 attempts only. `technicalStopRequired`
clears only after technical receipt/time/outcome/cap checks pass. Legacy all-in fields
`actualAdditionalSpendEur`, `requiredMeasuresComplete`, `capViolation` and
`stopRequired` keep their original scope and are not redefined as technical-only;
`actualAdditionalSpendEur` stays null while reviewer-fee applicability is unresolved. Synthetic verifier output is not trusted live accounting evidence. Reviewer
time/fee and combined human-inclusive totals remain unavailable throughout the v3
technical phase.

Freeze an activity roster for the approved accounting scope. The v3 technical
scope covers setup and every registered attempt; full human-inclusive accounting
later adds reviewer work outside attempt intervals as separate disjoint activities.
Legacy scopes retain their registered activity set.
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
Live supervision still needs a fresh externally verified cumulative source. For v3, the approved technical scope can complete measured setup, user, all 108
attempt and technical wall costs when their source receipts and hashes are verified.
The two reviewer-role fees stay `unknown`; reviewer time and any combined
human-inclusive totals stay unavailable until a later human addendum and verified
records. Legacy v1/v2 still require their named-reviewer accounting. Passing these
synthetic controls does not complete SPEC-044's registered capture or human
evaluation.
