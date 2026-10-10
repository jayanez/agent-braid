# M4.5 evaluation preparation

`agent_braid.tooling_evaluation` validates a frozen registration, creates its
prospective 108-slot roster, keeps an append-only status ledger, and reports
whether technical costs and outcomes are complete and whether the separately deferred human phase is complete. It is an offline
preparation/accounting library. It does not launch Codex, Claude Code, MCP,
providers, fixtures, subprocesses, or evaluation attempts.

The current registration form is intentionally incomplete and cannot pass
capture validation. The v3 technical phase uses the owner-approved deferral record; it does not supply source rights, candidate registration, provider approval, budget, observations, human labels or a utility result.

## Frozen registration requirements

`validate_registration(...)` requires one JSON-compatible object with:

- a unique registration ID, schema version, explicit approved status, and
  owner-approval record ID and SHA-256;
- exact candidate commit, version and SHA-256, checked against the caller's
  expected candidate digest;
- eighteen unique immutable fixture IDs and hashes, exactly three for each
  journey class, and six immutable prompt IDs/hashes, one per class; caller-
  supplied expected input hashes must bind this complete inventory;
- a source-rights record whose approved fixture IDs match the registered
  fixtures exactly, with scope, record ID and record hash;
- two exact macOS arm64 host records (`codex`, `claude-code`), each with host,
  OS and SDK versions and hashes, plus an explicit immutable-provider-build or
  approved observable-requested-route model identity; metadata catalog/route hashes
  cannot populate backend-build fields, and an opaque backend remains unavailable;
- an explicit provider opt-in and consent record/hash, exact EUR per-million
  input/output rates for each registered host/model pair and each rate record's
  source ID/hash;
- positive, finite EUR, token, wall-time, RSS and disk caps;
- a mandatory exact subscription-only `billingPolicy` for v3, with two account
  hashes, host authentication methods, zero additional spend and paid API/overage/
  credits/auto-recharge permissions all false. Legacy v1/v2 retain their historical
  optional-policy contract;
- two unique abstract independent reviewer roles and the approved human-evaluation
  deferral record for a v3 technical-capture registration, plus the frozen, hashed
  rubric and thresholds of at least 16/18 successful arm-C journeys per host and
  18/18 correct arm-C authority outcomes per host. Keep `humanReviewers` empty;
  later named identities, ratings and adjudication require a separate addendum
  bound to the immutable technical registration.

The v3 phase field is `technical-capture`; its `humanReviewDeferral` is approved and binds a `recordId` and `sha256`. `humanReviewRoles` contains two unique abstract roles with `independent: true`. These role requirements do not claim that people have been appointed or reviewed anything. Legacy v1/v2 preserve their prior named-human contract and reject v3 phase, deferral and role fields. The prospective v3 example is [technical-registration-draft.json](../../examples/tooling/technical-registration-draft.json); the legacy v2 file remains unchanged. See [OUTCOME_RUBRIC.md](OUTCOME_RUBRIC.md) for the pre-capture rubric contract. The validator checks declared records and hashes for shape and identity. The
caller-supplied input inventory binds declared registration hashes; it does not
authenticate fixture or prompt file contents. The validator also cannot
authenticate a person, source license, provider consent, owner approval, or host
observation. A valid object is not an authorization to capture data.
Any change to the registration changes its canonical digest and requires a new
reviewed registration before a cohort can resume.
Legacy v1/v2 registrations without a billing policy remain structurally supported;
they do not satisfy the owner's v3 technical-phase subscription-only requirement. New M4.5
capture must use the chosen frozen policy. Policy shape checks do not authenticate
accounts or quota, and additional spending at zero does not make total-cost fields
zero or complete. Admission and supervision require fresh trusted observations;
see [REGISTRATION.md](REGISTRATION.md).

The existing [v2 registration draft](../../examples/tooling/registration-draft.json) remains a legacy contract example. Use the prospective [v3 technical registration draft](../../examples/tooling/technical-registration-draft.json) for the deferred-human technical phase; the frozen [outcome rubric](OUTCOME_RUBRIC.md) remains part of technical registration before capture. These drafts are intentionally invalid until reviewed and completed. An intentionally invalid legacy template looks like this:

```json
{
  "schemaVersion": "agent-braid-m45-registration-v1",
  "registrationId": "replace-before-review",
  "status": "draft",
  "provider": {
    "optIn": false,
    "providerId": null,
    "consentRecordId": null,
    "consentRecordSha256": null
  },
  "costCaps": {
    "eur": null,
    "tokens": null,
    "wall_seconds": null,
    "rss_bytes": null,
    "disk_bytes": null
  }
}
```

The null values and false provider opt-in are deliberate placeholders. No
budget or provider choice is inferred. The example is not a complete
registration and fails validation.

## Roster and ledger

`generate_slots(validated)` creates exactly 108 unique rows:

`2 hosts × 3 arms × 6 journey classes × 3 fixtures`.

The arms are CLI, MCP-only, and MCP-plus-skills. Within each host and journey
class, the three fixture instances receive cyclic A/B/C order rotations so each
arm appears once in each position. Roster generation hashes no files and runs
no mutable fixtures. `new_ledger(validated)` preserves every intended slot in
the `not-started` state.

`append_slot_event(...)` returns a new ledger with an appended event. Each
terminal event includes an explicit completion value (including null for
unknown), an explicit authority result (including null for unknown), a
source-timestamped cumulative cost snapshot, and the original attempt ID.
The ledger retains intended, not-started, attempted, valid, invalid, refused,
cancelled, recovered and failed states. A slot cannot be executed twice in the
same cohort. A cancelled or failed attempt may later be marked recovered only
for its original attempt ID; this does not start another execution. Resumption
of an experiment requires the exact unchanged registration or a new cohort.
Recovery cost snapshots are cumulative and monotonic: every previously known
field must remain known and may not decrease. RSS and disk observations also
retain their prior high-water values. Previously unknown fields remain unknown
unless the recovery event supplies a new explicit measured value, bound by the
event's immutable data hash. A recovery cannot erase a prior cap exceedance.

`summarize_denominators(...)` reports all 108 intended slots and per-host,
class and arm status counts. A terminal event adds history; it never removes a
slot or shrinks a denominator. Source timestamps preserve when a state was
recorded. No status is inferred from a missing row as a successful outcome.

## Costs and utility eligibility

Each terminal slot cost object and the separate setup-cost object names
`eur`, `tokens`, `input_tokens`, `output_tokens`, `retry_tokens`,
`wall_seconds`, `rss_bytes`, and `disk_bytes`. The total token field must equal
the three token components; it remains null if any component is unknown.
Unknown measurements use JSON `null`; zero is a measured zero. Complete-cost
accounting requires every field for setup and all 108 intended slots, including
not-started or interrupted slots. Wall time is the registered total-wall
boundary; do not sum overlapping phase durations. Recovery records carry
cumulative costs for the same attempt so event history is not double-counted.

`check_cost_caps(...)` stops admission if any required observed value is
unknown or any cap is exceeded. EUR, tokens and wall time are summed across
setup and slots; RSS and disk use the largest registered observation. The
module does not choose rates, caps, retries, provider calls, or a method for
obtaining missing measurements.

`assess_utility_eligibility(...)` reports eligibility only; it never concludes
that the product has positive utility. Eligibility requires complete costs
within caps, two distinct independent human ratings for every slot, resolved
human labels, the frozen rubric's arm-C success threshold (at least 16/18) per
host, 18/18 correct arm-C authority outcomes per host, and no false or unknown
arm-C fidelity outcome. The frozen success threshold may be stricter than
16/18. Null/unknown authority and fidelity labels block eligibility. Any
disagreement in the later human phase needs a hash-checked adjudication record with `recordId`, an
`adjudicatorId` among the two registered human reviewers, a `fields` object of
resolved labels, and `sha256` equal to the canonical SHA-256 of the other three
fields serialized as sorted-key compact UTF-8 JSON. Missing ratings and labels
remain missing. Human descriptors must identify actual humans in the later bound addendum; abstract roles do not stand in for people, and Luna or other model annotations cannot substitute.
Results from other arms remain in the denominator and safety failures must be
reported. No positive utility claim is available during the technical phase. A later claim still requires the deferred human interpretation, candidate-bound evidence, complete human-inclusive costs, independent review and founder decision described by SPEC-044.

## Structured and narrative utility reports

`agent_braid.tooling_evaluation_report.build_utility_report(...)` accepts the
registration data, ledger, expected candidate/input hashes, setup costs, and
human ratings. It validates the exact registration and ledger roster and derives
eligibility by calling `assess_utility_eligibility`; callers cannot supply an
assessment or an `eligible` override. Subscription registrations also require a registration-bound `fullCostScope`.
V3 may bind the approved technical accounting scope while full human-inclusive
completion remains unavailable. Summaries are checked against the exact registration
and frozen monetary roster identities, plus the registered cash, provider accounting
and study-wall caps. The provider accounting total is actual provider cash plus
allocated subscription value; it excludes reviewer cash and API reference
estimates and does not add the legacy scalar EUR a second time. Exact Decimal
comparisons preserve cap excesses even when a float would round them down.

For v3, the approved `fullCostScope` records a technical accounting boundary using the existing allocation, user-time, wall-time, receipt-source and approval fields. It keeps exactly two reviewer-role fee rows marked `unknown`. The report marks human evaluation deferred, identifies zero human reviewers, leaves human scoring incomplete, and never asserts positive utility. Measured technical setup/user/attempt costs and technical wall time can be complete with receipt hashes; reviewer fees/time and combined human-inclusive totals remain unavailable, so full human-inclusive economic completion stays open.

Stored technical measurements and receipt inventories remain retained, but the report exposes technical aggregates only after trusted summary verification. The builder accepts optional `technical_cost_verifier`, implementing `verify_technical_summary(...)` from `agent_braid.tooling_full_cost`. Its attestation binds the canonical summary digest, registration, generated roster, approved scope and technical receipt inventories, and verifies complete required-measure coverage with no missing technical rows. A valid attestation sets `costs.technicalMeasuresAttested` true and allows authenticated provider, subscription-allocation, user-time, study-wall and technical subtotal values to be displayed. If the verifier is absent, the summary or attestation is unsupported/forged/mismatched, or coverage is incomplete, `costs.technicalMeasuresAttested` is false and displayed technical aggregates are unknown while stored evidence is retained. Reviewer and combined human-inclusive values remain unknown in all v3 reports. A synthetic test verifier checks software behavior only; it is not trusted live evidence.

The `costs.fullEconomic` object retains `receiptSha256s`, `userTimeReceiptSha256s` and `studyWallReceiptSha256s` inventories. With a valid attestation, its technical-only fields include `technicalAdditionalSpendEur`, `technicalRequiredMeasuresComplete`, `missingTechnicalRequired`, `technicalCapViolation` and `technicalStopRequired`; only `technicalAdditionalSpendEur` is the setup-plus-108-attempt cash subtotal. `technicalStopRequired` clears only after the technical receipt, time, outcome and cap checks pass. Global `actualAdditionalSpendEur`, `requiredMeasuresComplete`, `capViolation` and `stopRequired` retain their all-in meanings and must not be read as technical-only results. In v3, `actualAdditionalSpendEur` remains null while reviewer fee applicability is unresolved; `humanTimeSeconds` and `reviewerTimeSeconds` remain null, and `fullEconomicCostComplete` remains false. The report conclusion status is `human-evaluation-deferred`. The report preserves all 108 intended rows, current statuses, event history hashes, and per-host/arm/journey-class denominators. Event observations are
projected to registered timestamps, outcome labels, costs, and input/output
hashes; arbitrary event text is not copied into exports. Unknown required costs
include their setup/slot field paths in the structured `costs.missingRequired`
list and in the deterministic English narrative. If required cost and scope
evidence is complete and consistent, caps are satisfied, and human scoring is
complete, a missed registered descriptive outcome threshold is reported as
`registered-threshold-not-met`. This describes only the observed cohort against
its frozen threshold; it does not assert causal or scientific negative utility,
acceptance, or milestone closure. Missing or unknown costs, unresolved human
labels, invalid adjudication, incomplete scope, and cap violations remain
`inconclusive`. An eligible result only allows independent human interpretation;
it does not assert positive utility, acceptance, scientific validity, or
milestone closure. Founder interpretation remains pending.

Arm-C fidelity is exposed as `true`, `false`, or `null` (unknown) per host. The
report also summarizes resolved, missing, disagreement, and adjudicated label
states by slot and in aggregate, using the validated human-rating resolver.
Exports contain no raw rating text or reviewer identity. Host/arm/class summaries
retain status denominators, resolved success labels, total wall-time median/range
when typed per-slot observations exist, and intervention totals only when every
slot has an observed integer. Missing intervention observations are unavailable,
never inferred as zero.

`build_utility_report(...)` returns an immutable mapping. The renderers accept
that builder-produced report, so callers cannot alter its reasons or denominators
between assessment and export. `render_utility_report_json(...)` produces
deterministic compact JSON, and `render_utility_report_narrative(...)` renders
fixed English decision text from validated status, reason, cost, and denominator
fields. The economic synopsis keeps exact decimal values as strings. These are pure offline
functions with no filesystem, host, provider, or global-state effects. Declared
registration/source-right records and evidence hashes are reported as scope;
the report does not authenticate them, anonymize source data, authorize capture,
or turn model/test output into human acceptance.

## Boundary

This module and its synthetic unit tests establish only deterministic
registration/roster/accounting behavior. They are not a registration approval,
source-rights finding, provider authorization, host receipt, clean-room
reproduction, human score, utility result, or M4.5 closure. No fixture files are
read or executed by these helpers.

## Versioned provider model identity

`agent-braid-m45-registration-v1` retains the legacy immutable model
version/hash interpretation. `agent-braid-m45-registration-v2` retains the
observable-route interpretation and its existing human contract. Prospective
technical-capture records use `agent-braid-m45-registration-v3`; they add the
phase and approved human-evaluation deferral while keeping the human roster empty. The owner approved this model-identity interpretation and separately deferred human outcome scoring/adjudication; neither decision is a complete registration or capture authorization.
The v2 native subscription routes pin Codex to `openai`/`chatgpt` and Claude Code
to `anthropic`/`claude.ai`; live billing policy observations remain separate.

Both identity kinds bind `selectorKind`, `selector`, `effort`, `effectiveConfig`,
`configSha256`, `cliBuild`, `nativeCatalogEntry` (UTC observation, source reference, catalog and selected-entry
hashes) and `providerRoute` (provider, account hash, authentication method).
`cliBuild` must match the registered native host.
`immutable-provider-build` requires `backendAvailable: true`, an authoritative
`immutableId` matching `model.version`. `selectorKind: immutable-id` selects
that exact ID. If the host only supports a `provider-alias`, each attempt must
independently observe and authenticate the same frozen immutable backend ID.
An exposed backend artifact digest is
mandatory through `backendDigestAvailable: true` and `backendSha256`, matching
`model.sha256`; when no such digest is exposed, declare it unavailable and keep
those digest fields null. An immutable provider build ID does not imply public
model weights.
`observable-requested-route` requires `backendAvailable: false`,
`immutableId: null`, `backendDigestAvailable: false`, `backendSha256: null`
and explicitly null backend `model.version`/`model.sha256`.
Metadata hashes cannot be substituted for those backend fields.

Admission must additionally bind a fresh externally authenticated model-route
observation. Requested and reported selectors stay separate, and missing
reporting stays null. The validator checks declared consistency; the trusted
verifier must authenticate catalog, configuration, route and any assertion that
the provider exposes no immutable identifier. Changing observable identity
requires a new reviewed cohort. Hidden backend revisions remain outside
reproducibility claims. Existing fixture, cost, subscription and human gates remain in force, with all
108 intended slots preserved. The v3 technical phase may finish deterministic
controls, observations, reproduction and technical accounting while labels remain
pending; unknown human time/fee is not zero, and this is not full economic completion.

`backendAvailable` means that an authoritative immutable backend build identifier
is exposed; it does not describe whether the model service is reachable.
`backendDigestAvailable` describes exposure of a backend artifact digest.
Neither may be inferred from a model name or a catalog metadata hash.

`configSha256` hashes the secret-free `effectiveConfig` record containing selector,
effort, provider endpoint (or an explicitly attested native first-party default),
authentication method and host selection descriptors. `hostSelection` records
`source`, a sanitized `configRef`, `flags: [model-selector, reasoning-effort]`
and `argv: [selector, effort]` as abstract roles. Actual command arguments are
separate redacted execution evidence; arbitrary arguments and opaque secrets
cannot be copied into this selection metadata.
`entrySha256` hashes the complete retained selected catalog-entry record; document
any projection from the native response, without claiming a projected entry is the
raw provider response. Both use UTF-8 JSON with sorted keys, compact separators,
`ensure_ascii=False`, `allow_nan=False` and no trailing newline.
`catalogSha256` hashes the exact retained catalog artifact bytes, including their
actual formatting. Retain those records to make the byte boundaries inspectable.
Endpoint/domain metadata alone does not establish subscription billing; fresh
authenticated account, policy and quota observations remain mandatory.

## Subscription economic-cost gate

[Experimental monetary records](MONEY.md) distinguish additional cash, allocated
subscription value and API-reference estimates. Subscription-policy registrations
require a matching registration-bound full economic summary in
`assess_utility_eligibility(..., monetary_summary=...,
expected_monetary_roster_sha256=...)`. Bind the independently frozen monetary
roster, including period and activity coverage, as well as the registration. Zero additional cash and
complete legacy scalar fields do not establish complete subscription and human
costs. The current experimental ledger keeps full human-inclusive eligibility blocked
until the deferred human fields and records are integrated. Under v3, the approved
technical scope can report measured technical-cost completion while reviewer
fee/time and combined human-inclusive totals stay unavailable. It does not set
human cost to zero or permit a positive utility claim. All
intended slots and unknown costs remain visible.
