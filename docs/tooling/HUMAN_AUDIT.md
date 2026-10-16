# Prospective M4.5 human audit

`agent_braid.tooling_human_audit` prepares the approved audit policy and assesses
coverage offline. It does not launch hosts, perform reviews, appoint people,
approve capture, or establish utility. Its synthetic tests support software
behavior only. The original full-cohort eligibility evaluator is unchanged.

## Freeze before outcomes

The exact policy object is:

```json
{
  "schema": "agent-braid-m45-human-audit-policy-v1",
  "seed": "m45-human-audit-2026-10-13",
  "algorithm": "sha256-host-class-fixture-v1",
  "initialCases": 36,
  "reviewersPerCase": 2,
  "escalation": "cell-on-confirmed-discrepancy-cohort-on-critical-v1",
  "compactEvidence": true
}
```

The seed is a bounded identifier chosen prospectively; the other values and exact
field set are fixed. `validate_policy(policy, expected_sha256=...)` checks and
returns an immutable `AuditPolicy`; `policy_sha256(policy)` returns its canonical
JSON SHA-256. These checks do not confer owner approval.

```python
from agent_braid import tooling_evaluation, tooling_human_audit

# registration is already structurally validated and frozen by its own API.
selection = tooling_human_audit.freeze_selection(
    tooling_evaluation.generate_slots(registration),
    policy,
    expected_policy_sha256=registration.data["humanAuditPolicySha256"],
    registration_sha256=registration.sha256,
    rubric_sha256=registration.data["rubric"]["sha256"],
    human_review_roles=tuple(
        role["roleId"] for role in registration.data["humanReviewRoles"]
    ),
)
```

The roster must retain the original two hosts, six classes, three fixture
instances per class and three arms: 108 unique slots. Fixture and prompt hashes
match across hosts and arms; arm order retains the original counterbalance.
The module copies the complete roster into immutable values and rejects malformed
cells, duplicate identifiers, mismatched pins and changed arm order.

For each host/class, rank its three fixtures by SHA-256 of the UTF-8 canonical JSON
object with exactly `seed`, `host`, `journeyClass`, `fixtureId`. Canonical JSON uses
sorted keys, compact separators, Unicode without ASCII escaping, and finite values.
Choose the lowest digest, breaking ties by fixture ID. Include that fixture in all
three arms. This produces 36 cases and 72 initial human ratings. Neither measured
outcomes nor arm order enter the selection algorithm.

`selection.sha256` binds registration identity, rubric identity, policy identity,
the complete sorted roster identity, two frozen human role IDs and all initial
case IDs. `selection.as_dict()` serializes the policy and roster as well. Input
roster order is irrelevant. Consumers rederive the selection before accepting it;
altered identities or selections fail closed.

`expected_policy_sha256` is mandatory and must come from the exact approved frozen
registration. The function refuses missing, malformed and different policy hashes.
Content hashes alone do not establish that policy choice or selection occurred
before capture. Preserve the complete selection commitment in the private
readiness packet before any measured attempt, with the candidate-bound approval
and independently verified workflow order. Self-declared timestamps do not prove
prospectivity or authentic approval; a commitment constructed after outcomes
cannot retroactively make this a prospective audit.

## Preserve assessment provenance

`validate_deterministic_assessment`, `validate_model_review` and
`validate_human_review` return separate immutable record types. Each pins the slot,
evidence SHA-256 and rubric SHA-256, and carries `labels` with exactly `success`,
`authorityCorrect`, `fidelity`; label values are booleans or explicit nulls.
Schemas and reviewer types cannot be exchanged, and extra fields are rejected.

| Record | Required provenance and behavior |
|---|---|
| `agent-braid-m45-deterministic-assessment-v1` | `reviewerType: deterministic`; `outcome` and `expectedOutcome` use the original roster statuses; `oracleMatches` is boolean/null; `evidenceComplete` and `conclusive` are booleans. |
| `agent-braid-m45-model-review-v1` | `reviewerType: model`; `model: gpt-6-luna`; `roleId: technical` or `adversarial`; distinct `reviewerId` and `contextSha256` for the pair; `independent: true`. |
| `agent-braid-m45-human-review-v1` | `reviewerType: human`; one of the two frozen `roleId` values; distinct appointed `reviewerId` values; `independent: true`; no model/context fields. |

Two model annotations remain model annotations. They cannot satisfy human
coverage. A model reviewer ID cannot also appear as an appointed human ID. Human
identity is consistent within each frozen role across the cohort. Structural
declarations and context hashes do not authenticate people, prove independence or
prove that a model review happened; source verification and the separately bound
human appointment/addendum remain external obligations.

All records for the same slot must name the same evidence identity and frozen
rubric. Duplicate slot/role records and foreign slots fail closed. Preserve older
record versions/history externally rather than submitting ambiguous duplicates.

## Coverage and escalation

```python
assessment = tooling_human_audit.assess_audit(
    selection,
    deterministic_assessments,  # all 108 intended cases
    model_reviews,             # two separate model roles per case
    human_reviews=human_reviews,
    adjudications=human_adjudications,
    escalation_events=events,
)
```

`automatic_complete` and `human_coverage_complete` are separate facts.
`required_slot_ids` begins with the frozen 36, then adds cases with missing
automatic records, oracle mismatch/unknown, any outcome differing from the frozen
expected outcome (including invalid, refused, cancelled or recovered),
incomplete evidence, inconclusive results, missing labels, model disagreement,
model labels conflicting with deterministic labels, or unresolved human ratings.
An expected refusal does not itself trigger escalation. A measured negative
result can have complete automatic coverage; completion does not imply success.

Two complete human ratings must agree, or their disagreement must have a bound
human adjudication. A resolved human disagreement, or resolved human labels
contradicting deterministic/model labels, automatically expands the matching
host/class/arm cell to all three fixture instances. Confirmed non-label
discrepancies use an explicit event with exactly:

```json
{
  "eventType": "confirmed-human-discrepancy",
  "slotId": "<original-slot-id>",
  "reviewerType": "human",
  "reviewerIds": ["<first-appointed-human>", "<second-appointed-human>"],
  "evidenceSha256": "<evidence-sha256>",
  "rubricSha256": "<frozen-rubric-sha256>"
}
```

The event must bind the existing resolved independent human pair. A model event
cannot confirm a human discrepancy. A critical incident requires exactly
`eventType: critical-incident`, `slotId`, `incidentKind` (`authority`, `privacy`,
`false-success`), `reviewerType`, `reviewerId`, `evidenceSha256`, `rubricSha256`.
The declared source must already have an assessment of that type for that slot;
deterministic sources use a null reviewer ID. Every critical incident expands all
108 cases and sets `acceptance_suspended: true`. Deterministic or resolved human
`authorityCorrect: false` also triggers this response automatically. Model-only
authority suspicions require audit while retaining their model provenance.
An asserted deterministic success paired with a failed oracle, or with an
unexpected unsuccessful state, also confirms a false-success incident and
suspends acceptance across all 108 cases. Expected refusal controls retain their
declared interpretation and do not trigger this inference merely for refusing.

Human adjudications use schema `agent-braid-m45-human-adjudication-v1` and exactly
`schema`, `reviewerType: human`, `slotId`, `adjudicatorId`, `evidenceSha256`,
`rubricSha256`, `labels`, `affirmedBy`. The adjudicator is one of the two appointed
reviewers; resolution requires their joint consensus. `affirmedBy` contains exactly
two objects with `reviewerId` and `affirmationSha256`, naming both original appointed
reviewers and distinct immutable affirmation record hashes. Missing, unilateral,
duplicate-person and reused-hash affirmations are rejected. Retain both affirmation
artifacts and verify their source and agreement with the pinned slot, evidence,
rubric and consensus labels before submitting the record. Hash syntax alone does
not authenticate consent. A third reviewer or a single rater's override is not
part of this audit route.
Adjudication resolves disagreement; it cannot invent missing human labels or
replace agreeing human labels. Identity, evidence and rubric drift are rejected.

`reviewed_slot_ids` contains cases with resolved complete human ratings;
`unreviewed_slot_ids` retains every other original case. Required cases still
unreviewed appear in `required_unreviewed_slot_ids`. A successful initial audit
therefore reports 36 reviewed and 72 unreviewed, never 108 human-reviewed cases.
The report retains the intended denominator of 108 and per-case escalation
reasons. It does not derive a positive utility or founder acceptance verdict.

This API is stateless: keep all assessment/event history in the durable study
record and submit the complete applicable event history on every assessment.
Dropping an incident event is not an authorized reset of suspended acceptance.
The original 36 human-operated CLI journeys, real cost reconciliation, native
receipts, compact blinded packets and founder decisions retain their own gates.

The prospective sample supports bounded acceptance of the registered corpus;
it does not establish general validity of automated evaluators or all host builds.
