# Implementation and evidence plan

## Technical context and scope

This feature defines a successor actual-workload protocol and bounded C08
harness slice. It reuses the SPEC-020 bounded local Git runtime and SPEC-022
accounting vocabulary. It does not change grant semantics, public schemas,
hosting, or external capabilities. Exact source/protocol approval permits C08
implementation and evaluation preparation under the user's M4 authorization;
registered capture is C09 and requires a stable harness, independent review,
and separate exact authorization.

## Constitution check before research

Articles 0, 2–7, 9, 12–15, 19–25 apply. In particular, actual workload relevance
is required (Art. 19), observed effects and uncertainty must remain visible
(Arts. 5, 12, 14), and structural/runtime checks do not prove confluence or
Yang–Baxter claims (Arts. 4, 10, 13, 17–18). SPEC-020 and ADR 0019 bound the
execution contract. SPEC-021's G4 NO-GO and open matrix are retained. SPEC-022
provides synthetic cost-accounting precedents only.

## Research, assumptions, and alternatives

SPEC-013 identifies PR #137 commit `58351f812614058e53a8ee6aef1dd458f1bb70fc`
and PR #138 commit `083f1a390988a9527a5aaeb19133401243b1d714`, from base
`f3c734a1f42d6d5962cfedc57d7f6c1efe40e0a6`. Static diff inventory shows #137
touches 3 paths/64 changed lines (7,872 diff bytes) and #138 touches 5
paths/999 changed lines (55,208 diff bytes). Static shape is 2 disjoint
no-dependency operations, 8 paths, 63,080 bytes, all regular 100644 A/M files
from the same base, within existing caps. PR metadata identifies `jayanez` as
submitter and both commits are authored by Juan Antonio Yáñez García; this is
a provenance/authorship lead, not a new source-rights permission. They remain
candidate source only until current runtime preparation admission, exact source
rights, and protocol review. Do not substitute other commits. If review finds
an unmet cap or rights gate, record infeasible. Existing M2 founder decisions
apply solely to their exact M2 experiment, expressly with execution authorization
false, and cannot satisfy either C07 or C09.

No experiment is authorized or executed during this design increment. No
provider or source-code execution is proposed. Future registered measurements
remain behind their exact review and capture gates. Eligibility is
checked by existing static runtime preparation/verification after future exact
approval, never by broad probes or test execution on the source. Full population
frame, all exclusions, and yield are fixed before any outcomes are seen. If
rights, sufficient eligible operations, immutable common base, or current
contract limits fail, stop with infeasible; no substitute source or scope
expansion.

## Design and compatibility

First gate: independent protocol/source-rights review of the exact source,
provenance, permissions, sampling frame, operation identities, baseline,
order/seed, outcomes/denominators, full phase costs, safety controls, budgets,
and stop/recovery rules. Second gate: after implementation, exact candidate
and stable harness/manifest review before capture approval. Existing grants,
private destinations, fixed patches, and verifier remain unchanged. A proposed
contract change stops this plan and requires a separate ADR/schema decision.

Compare the actual SPEC-021 policy coordinator in serial and parallel modes,
not ordinary replay against SPEC-020 alone. Use the two operation orders AB and
BA, two unscored warm-up pairs per order, then three measured pairs per order
(six measured pairs total). Freeze the exact deterministic seed and pair/treatment
schedule in protocol-review-packet.md and the stable manifest. Retain all ten
pair slots and every refusal, invalid, failure, recovery, and unexecuted status.
The 45-minute dispatch cap starts before the first warm-up and stops new
starts; the 360-second per-treatment observation deadline matches the pinned
SPEC-021 tool timeout and does not authorize hard killing. A fresh Python process
independently inspects all slots and verifies every completed result after the
pair runs. Each treatment's total wall begins before evidence/input production
and ends after consumer verification, report serialization, and cleanup. Record
disjoint input/replay/preparation/grant/execution/verification/report/cleanup
phases and explicit residual; report fresh-process, setup, source/rights,
operator and final observer costs separately, without double-counting nested
views.

## Validation strategy

Trace REQ-001..005 to SC-001..008, protocol procedures in `validation-plan.md`,
planned evidence `evidence/sc-*.json`, and eventual source-integrity and
denominator audit. No test or evidence is obtained in this specification task.
Planned negative controls cover absent/stale rights, changed base/patch,
unlisted path, binary/mode change, cap overflow, invalid dependency, conflict,
missing/stale grant, altered tree, source mutation, invalid destination,
interruption, duplicate resume, refusal and budget exhaustion. Record protocol
adherence separately from measured result. Incomplete/missing/invalid pairs
remain in denominators; no favorable complete-case inference.

## Constitution check after design

No contradiction identified. The plan is subordinate to current grants and
fixed-patch limits. It adds no capability or scientific claim. Article 19
relevance is a rationale for prospective real workload measurement, not proof
that these candidate sources are authorized or eligible.

## Human review and unresolved decisions

Pending: source owner/rightsholder and exact permissions; exact eligible
operation yield under current caps; protocol/source approval; later stable
harness/manifest review; capture-specific authorization; independent evidence
review; and founder whole-M4 decision. No approvals are represented as obtained.
