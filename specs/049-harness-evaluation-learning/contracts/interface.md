# Proposed evaluation, experience and promotion records

Status: draft design; no implemented public API or accepted schema. Consume the
[laboratory records](../../048-harness-variant-laboratory/contracts/interface.md)
without changing their authority semantics.

- EvaluationRegistration binds corpus/rights/yield, scenario family, synthetic or
  native cohort, grouped partitions, temporal ordering, frozen comparator roster,
  requested model/host profile, rubric/normalizer and numerical budgets/margins.
- EvaluationRow binds registered unit, started/refused/interrupted/terminal status,
  outcome dimensions, oracle versus human/proxy provenance, missingness reason,
  intervention/review categories, actual or unknown costs and candidate identity.
- ExperienceEntry binds cue, bounded lesson, supporting and contrary evidence,
  domain/source/host/tool applicability, temporal eligibility, trust state,
  expiry/revalidation policy and revocation history. Candidate text is untrusted.
- PromotionDecision names exact variant/profile, human actor or separately adopted
  automatic-policy identity, evidence set, remaining limits, rollback target and
  actual permission. A selector result cannot fill this record by itself.

Experience states: proposed → quarantined → validated → human-approved active,
with revoked/expired terminal exclusions and an inspectable history. Automated
validation never forges human approval. Any future automatic activation replaces
only the explicitly adopted transition for its narrowly eligible class.

Read/query filters must verify temporal prefix, domain and current source/tool/
policy compatibility before including a lesson. Preserve negative and contradictory
results; do not transfer a lesson across domains based on a semantic-similarity
score alone. Retain sufficient source evidence for audit without copying secrets;
private exports, retention and consent belong in the source protocol.

Selection outputs candidate/keep-base/inconclusive/refused. Promotion outputs
approved/rejected/pending only with the actual owning decision. Automatic-policy
assessment outputs disabled/deferred/no-go/go-proposal; none activates it.
No generic confidence score grants permissions or establishes semantic correctness.
