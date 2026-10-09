# M4.5 evaluation preparation

`agent_braid.tooling_evaluation` validates a frozen registration, creates its
prospective 108-slot roster, keeps an append-only status ledger, and reports
whether required costs and human labels are complete. It is an offline
preparation/accounting library. It does not launch Codex, Claude Code, MCP,
providers, fixtures, subprocesses, or evaluation attempts.

The current registration form is intentionally incomplete and cannot pass
capture validation. No source-right record, candidate registration, provider
approval, budget, observation, or utility result is supplied here.

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
  model, OS and SDK versions and hashes;
- an explicit provider opt-in and consent record/hash, exact EUR per-million
  input/output rates for each registered host/model pair and each rate record's
  source ID/hash;
- positive, finite EUR, token, wall-time, RSS and disk caps;
- an optional exact subscription-only `billingPolicy`, when that route is
  selected, with two account hashes, host authentication methods, zero additional
  spend and paid API/overage/credits/auto-recharge permissions all false;
- two distinct independent human reviewers and a frozen, hashed rubric with
  thresholds of at least 16/18 successful arm-C journeys per host and 18/18
  correct arm-C authority outcomes per host.

The validator checks declared records and hashes for shape and identity. The
caller-supplied input inventory binds declared registration hashes; it does not
authenticate fixture or prompt file contents. The validator also cannot
authenticate a person, source license, provider consent, owner approval, or host
observation. A valid object is not an authorization to capture data.
Any change to the registration changes its canonical digest and requires a new
reviewed registration before a cohort can resume.
Legacy registrations without this optional policy remain structurally supported;
they do not satisfy the owner's later subscription-only authorization. New M4.5
capture must use the chosen frozen policy. Policy shape checks do not authenticate
accounts or quota, and additional spending at zero does not make total-cost fields
zero or complete. Admission and supervision require fresh trusted observations;
see [REGISTRATION.md](REGISTRATION.md).

An intentionally invalid template looks like this:

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
disagreement needs a hash-checked adjudication record with `recordId`, an
`adjudicatorId` among the two registered human reviewers, a `fields` object of
resolved labels, and `sha256` equal to the canonical SHA-256 of the other three
fields serialized as sorted-key compact UTF-8 JSON. Missing ratings and labels
remain missing. Reviewer descriptors must identify humans; Luna or other
model annotations cannot substitute.
Results from other arms remain in the denominator and safety failures must be
reported. A positive utility claim still requires the separate human
interpretation, candidate-bound evidence, independent review and founder
decision described by SPEC-044.

## Boundary

This module and its synthetic unit tests establish only deterministic
registration/roster/accounting behavior. They are not a registration approval,
source-rights finding, provider authorization, host receipt, clean-room
reproduction, human score, utility result, or M4.5 closure. No fixture files are
read or executed by these helpers.
