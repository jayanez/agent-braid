# M4.5 evaluation protocol proposal

**Registration:** select exact candidate and host builds, explicitly labelled provider
model identities under [the approved clarification](model-identity-clarification.md), eligible fixture
hashes, prompt roster, cost rates/budgets, two abstract independent reviewer roles and the approved human-evaluation deferral before technical observations. Keep v3 humanReviewers empty; later identities, ratings and adjudication require a separately bound addendum.
Current status: protocol draft; no measured observations or accepted utility.
V3 requires the exact included-subscription-only `billingPolicy` for both hosts; numeric caps and other owner-approved capture gates still apply. Existing M4 source rights and observations do not authorize this capture.

## Questions and population

Can a developer discover and use the bounded workflow accurately in Codex and
Claude Code? Does the integrated route reduce user effort or explain evidence
more faithfully than the same candidate's CLI and MCP-only route?
Target population is these two local host builds, the registered owned fixtures
and the selected macOS arm64 environment. No professional population or every
host version is inferred. Core/protocol reproduction separately targets Linux x86_64.

## Design

Three arms: A CLI with written instructions; B MCP without product skills;
C MCP plus the five skills. Same immutable requests and expected oracle outputs.
Six journey classes: analyze interactions; prepare advisory plan; refuse missing
grant; execute granted batch/verify; inspect/recover interruption; export evidence.
Register three independent fixture instances per class. For each host and each
arm this gives 18 attempted journeys: 108 intended attempts total.

Counterbalance A/B/C order across fixture instances; isolate clean host sessions
and result roots, reset skill/context state, record carryover or unusable sessions.
Do not reuse observed outcomes to rewrite prompts, fixtures, thresholds or rubrics.
A repaired candidate needs a declared new registration and separate cohort.
CLI is a host-associated baseline with the same environment and operator, not
model-generated MCP output disguised as an independent comparator.

Freeze the human rubric and thresholds before capture, even though outcome scoring is deferred. The approved v3 technical `fullCostScope` retains the existing accounting fields, measures user/setup/attempt time and technical wall time with verified receipts, and records two reviewer-role fee rows as `unknown`. Reviewer time/fee and combined human-inclusive totals remain unavailable until the separate human phase; technical-scope approval is not full human-inclusive cost completion. Human rubric before scoring: successful required steps; correct conflict/unknown
interpretation; evidence/provenance/limits fidelity; correct authority separation;
user interventions; unrecovered errors; time and complete cost. Independent technical review can assess deterministic artifacts if authorized; it is not independent human outcome annotation. The later human phase requires two appointed reviewers to score de-identified artifacts with arm/order hidden where feasible; disclose incomplete blinding and adjudicate disagreements before aggregates. Until that separately authorized phase, identities/ratings/adjudication remain pending. Unresolved labels stay missing and reported.

## Mandatory controls and descriptive thresholds

All deterministic safety/refusal controls must pass with zero unauthorized
mutations, grant issuance exposures, out-of-root disclosure or false success.
Each host must complete the full basic journey and load all five skills at least
once with actual host receipts. Mock client controls are additional evidence only.

Preregister product review thresholds: at least 16/18 successful journeys in
arm C per host; 18/18 correct authority handling; no factual inversion of
conflict/unknown or verifier outcome in accepted exports. Compare interventions
and total wall time descriptively across matched A/B/C attempts, including
failed/refused attempts. No minimum speedup is required. Do not accept a positive
utility claim if missing outcomes/costs or sampling limits prevent interpretation.

The registered claim scope identifies the required cost fields before capture.
Interpretation must check their availability over all intended attempts before
emitting a positive utility conclusion. If missing required costs prevent that
interpretation, record `utilityClaimEligible: false`, the missing fields/attempts
and an inconclusive utility conclusion in both the structured report and narrative
exports/decision packet. Completion or rubric thresholds cannot override this gate.
Retain descriptive observations and all outcomes with their limits; never replace
unknown costs with zero, omit affected attempts or silently narrow the registered
claim. A narrower follow-up utility claim requires a new prospective registration,
separate cohort and review; it cannot relabel the current cohort's blocked claim.

Report per-host/class/arm attempt denominators, outcomes, completion rate,
interventions, median/range total wall, error/recovery counts and cost. Retain
intended/not-started/attempted/valid/invalid/refused/cancelled/recovered/failed rows.
Do not drop failed attempts or relabel a provider/infrastructure block as success.
Do not pool hosts to hide a host failure. Sample is descriptive; no general
causal/statistical significance or production safety claim.

## Model identity and drift

Require an authoritative immutable provider build identifier whenever exposed.
Otherwise register an observable requested route: exact selector and effort,
native executable version/hash, dated catalog artifact/entry hashes, effective
selection/configuration identity and authenticated provider/account route. Backend
identity remains unavailable; never use catalog or route hashes as backend-build
hashes. Receipts distinguish requested and host-reported selectors and any exposed
backend identifier. Observable route/catalog/configuration/build/account drift
stops the cohort; a repaired route needs a newly reviewed registration and separate
cohort. Hidden backend revisions and nondeterminism remain limits, with no promise
of backend reproducibility or weight-level replay. All 108 intended attempts and complete economic scope remain required. The technical phase may finish with reviewer time/fee fields unavailable while measured user/setup/attempt costs and technical wall times remain recorded; no human-inclusive cost or positive utility claim follows until human ratings/adjudication and applicable cost reconciliation are complete.

## Complete cost and stops

Record install/configure/setup separately; per attempt include context/skill/tool
discovery, provider wait/latency, all input/output tokens and retries, MCP work,
runtime preparation/execution/verification/recovery, export and user/reviewer
time. Unknown token/currency/RSS data are unavailable, never zero. Use source
timestamps and total-wall boundary; overlapping phases are not summed twice.

Deterministic local controls use no provider expenditure. Before real-host capture,
the owner selects numeric EUR/token/time/RSS/disk caps and any provider calls.
Default registration refuses paid/provider work without that decision. No new
infrastructure is authorized here. Stop on authority/privacy incident, exceeded
cap, missing immutable source, drifted candidate/build, unrecoverable transition
or two consecutive infrastructure failures. Preserve interrupted slots.
Resumption needs an unchanged registration or a new declared cohort.

## Evidence and acceptance

Receipt per attempt: registration ID; candidate/bundle/SDK/protocol/host/model/OS
versions; discriminated provider model identity, requested/reported selectors and
backend availability; immutable input and output hashes; actual commands/tool events; permission
and grant check outcome; raw transcripts redacted with retained redaction record;
verification result; full cost availability; status and limits. Synthetic,
protocol-peer, actual-host and clean-room records have different evidence types.

Audit registration adherence and all exclusions before technical interpretation. Freeze the technical candidate and evidence and obtain independent technical review; the decision packet may report technical readiness with human evaluation explicitly pending. Human labels/adjudication and founder acceptance remain separate later decisions. Founder may accept a bounded useful integration,
reject it or leave it pending. M4.5 closure does not close M4 or reverse G4 NO-GO.
