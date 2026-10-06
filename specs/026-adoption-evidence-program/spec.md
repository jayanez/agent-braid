# Adoption and independent-reproduction evidence program

## Purpose and scope

SPEC-026 turns the open-tooling and community strategy into an executable local
program for collecting and auditing evidence of use, integration cost,
contributions, counterexamples and independent reproduction. SPEC-002 already
implements strategy/radar and assumption-driven opportunity proxies; SPEC-011
already implements the technology-adoption pathline. Neither provides an
operational organization/workload frame, measured usability/integration-cost
intake or an independent-reproduction dossier workflow.

The first implementation is a dependency-free, offline evidence register,
metric manifest, validator, synthetic intake fixtures and repeatable report.
Real evidence intake and external participation are later gated increments.
Stars, downloads, market proxies and technology counts are contextual signals;
they cannot demonstrate usefulness, independent validation or research novelty.
Tracking milestone: **GOV.1 — Governance and adoption**; this assignment does not
invent a new product or research phase.

## Authorities

Clause zero and Articles 13, 14, 17, 19, 21, 23 and 25 apply, together with
`GOVERNANCE.md`, ADRs 0005 and 0009, claim discipline,
`docs/strategy/OPEN_TOOLING_STRATEGY.md`, `docs/strategy/COMMUNITY.md`,
`docs/strategy/ECOSYSTEM.md`, `docs/releases/VALIDATION_POLICY.md`,
`schemas/governance/release-validation-record.schema.json`, and SPEC-002,
SPEC-009 and SPEC-011. Source rights and privacy follow `SECURITY.md` and the
license boundary. Software maturity and independent scientific validation remain
separate decisions.

## Clarifications and bounded decisions

- First population: explicitly synthetic organizations and 1–3 local workload
  families (AIM report inspection, Git/CI diagnostic integration, recorded-trace
  mapping). Real population eligibility, permissions and collection window must
  be frozen before collecting real evidence; no organization is contacted here.
- Units: organization, environment/integration, workload family, use episode,
  contribution and reproduction each have distinct identifiers. Report unique
  organizations and workloads separately; do not sum software, platform and
  enterprise labels into extra organizations.
- First empirical opportunity: a prospectively admitted local report-usability
  and integration-cost pilot. It records observed task completion and total
  setup/run/review/debug time separately from participants' judgments. The
  offline synthetic register is engineering evidence only.
- Independent reproduction requires an identified external reviewer, affiliation,
  explicit externality/conflict declaration, exact candidate/input/protocol
  hashes, environment, actual commands, results and limits. A maintainer rerun is
  internal even when it runs in a clean environment.
- Interviews, recruitment, contact, external issue invitations, research claims
  and publication require separate authorization. Intake is a local artifact
  interface and never sends a message or publishes a record automatically.
- Historical SPEC-002 T006 and SPEC-009 T009 require a current evidence-backed
  audit/decision record. Frozen assurance, founder records and task history are
  preserved; an old unchecked task is not silently approved or closed.

## Requirements and acceptance scenarios

### REQ-001 — Freeze an eligible, deduplicated evidence frame

**SC-001:** Given a synthetic organization/workload frame and a proposed future
real collection window, when it is registered, then each unit has a stable ID,
unit type, inclusion/exclusion reason, source permission status and observation
boundary. Duplicate aliases and cross-segment labels cannot create duplicate
organization/workload counts. Unknown ownership remains unresolved; the first
validator rejects real intake without its explicit admitted source/window.

### REQ-002 — Every metric has provenance and a denominator

**SC-002:** Given evidence rows and a metric manifest, when aggregation runs,
then each metric has a formula, unit, eligible population/window, baseline,
observation or proxy label, evidence hashes, denominator, missing/excluded
counts and interpretation limit. Counts, rates and cost totals are reproducible;
no cross-unit sums, duplicate organizations, missing-as-zero substitutions or
stars/market-proxy substitutions establish adoption or benefit.

### REQ-003 — Observe local usability and complete integration cost

**SC-003:** Given prospectively defined report-inspection/integration tasks,
when an admitted pilot episode is recorded, then it preserves workload,
candidate/report/input/environment hashes, task rubric, baseline condition,
completion/errors, timings, failures, unknowns and participant judgment. Setup,
execution, review and debugging time remain visible separately and in total.
A fixed synthetic pilot demonstrates plumbing only; real comparisons freeze
eligibility, allocation/order, rubric and adjudication before results and
report all episodes, abstentions and missing outcomes.

### REQ-004 — Contribution and counterexample intake is reproducible

**SC-004:** Given a local contribution, workload-family addition or counterexample,
when it is ingested, then its source rights, author/conflict status, candidate,
observation boundary, replay inputs/commands, expected/observed divergence,
minimization status and review disposition are recorded. Duplicates, malformed
rights and unreplayable submissions remain rejected/pending with reasons.
Negative or inconclusive contributions can be useful; contribution count alone
cannot establish correctness or research novelty.

### REQ-005 — Reproduction status matches the reviewer's independence

**SC-005:** Given internal and external reproduction dossiers, when their status
is evaluated, then founder/maintainer reruns remain internal and a qualifying
external dossier requires identity, affiliation, externality/conflicts, candidate
and input/protocol hashes, environment, actual commands/outcomes and limits.
Missing, stale or conflicting evidence stays pending or changes-requested.
The program proposes release-record updates only after separate review; it does
not set `independent_validation: completed` from a local pass or an anonymous
claim. External negative/inconclusive outcomes are recorded faithfully.

### REQ-006 — Reconcile old tasks against current evidence

**SC-006:** Given frozen SPEC-002 T006 and SPEC-009 T009 plus current repository,
release, authority and review records, when the audit runs, then each original
obligation has an evidence pointer, observed current state, authorization status,
remaining decision and proposed disposition. Public visibility or a merged PR
alone cannot prove the release, archival, scientific or founder obligations.
Save a separate current reconciliation and decision record; preserve frozen
historical artifacts and leave unsupported obligations pending.

### REQ-007 — Missingness and provenance survive every report

**SC-007:** Given duplicate, stale, missing, withdrawn-permission, failed and
contradictory records, when validation and report generation run, then they are
flagged with reasons, excluded/missing denominators remain visible, and evidence
hash drift invalidates the affected metrics. Re-running the same admitted
synthetic inputs produces the same metrics/report bytes. Reports contain no
sensitive content, unauthorized identity disclosure or hidden sampling changes.

### REQ-008 — Evidence supports explicit decisions with limits

**SC-008:** Given validated registers, metrics, pilot/contribution/reproduction
outcomes and historical reconciliation, when a milestone packet is prepared,
then it states what is observed, proxy, hypothesized, negative or inconclusive,
links raw evidence and unresolved decisions, and proposes a next action without
automatic outreach, publication, contract adoption or scientific approval.
Research/publication decisions must not be inferred from stars, market proxies
or the registry's passing validator. Every proposed public claim retains its
claim level and independent-validation status.

SC identifiers name the future acceptance contracts in `quickstart.md`; no
planned test or real population outcome is represented as already executed.

## Scientific boundaries and compatibility

The hypothesis is that inspectable reports reduce diagnostic uncertainty or
integration effort on admitted workloads. It can be falsified by poor task
completion, hidden costs or no useful difference against the fixed baseline.
This program measures feasibility and scoped local observations before any
inferential or market claim. Small samples, self-selection, owner participation,
missing data and workload clustering must remain visible. If a comparison is
planned, the held-out unit is organization/workload family, and evaluation cases
and adjudication are fixed independently of method results. Synthetic fixtures
cannot establish demand, real adoption, causal benefit, production safety,
scientific novelty, general confluence or Yang–Baxter validity.

New governance intake/metric contracts are versioned in the later implementation
PR. Existing market-proxy, adoption-track and release-validation semantics remain
unchanged. Release status updates and public reports remain reviewed proposals.

## Evidence and unresolved questions

Obtained evidence is empty and human review is pending. The offline synthetic
register is ready for implementation. Real eligibility/permission/yield,
participant availability, externally independent review and founder/publication
acceptance remain explicit gates; absent sources complete a feasibility report
as `inconclusive` rather than inviting unauthorized contact or inventing data.
