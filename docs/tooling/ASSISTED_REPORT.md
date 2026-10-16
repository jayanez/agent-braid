# V6 assisted technical report

`agent_braid.tooling_assisted_report` produces an immutable technical report for
the registered M4.5 sampled audit. It is separate from the legacy full-cohort
human utility report: v6 cannot enter that legacy eligibility route. This report
does not authorize capture or assert human acceptance, founder approval, utility
or milestone closure.

## Frozen inputs and integration API

`freeze_report_inputs(registration, ledger, selection=..., ...)` requires a
`ValidatedRegistration` with the v6 schema, its exact
`tooling_registration_v6.audit_selection(registration)`, and the actual
`EvaluationLedger`. The optional independent record collections are:

- `deterministic_assessments`, `model_reviews` and `human_reviews`, using the
  existing human-audit record types or their exact serialized representations;
- `adjudications` and `escalation_events`, using the registered audit interfaces;
- `setup_costs`, retaining every measurement field and explicit nulls;
- `monetary_summary`, an existing `MoneySummary`, paired with the independently
  frozen `expected_monetary_roster_sha256`.

The builder validates the registration, roster, ledger history, review role
separation and adjudication shape. Every assessment binds the current terminal
output SHA-256 and exact rubric; every deterministic outcome status must match its
ledger event. Missing source verification cannot repair conflicting declarations.
Current human adjudication requires both original independent ratings and their
joint affirmation records.

The returned `ReportInputs` stores immutable JSON copies. `.sha256` identifies
the frozen inputs; `.subjects` returns immutable `ReportSubject` values with
`kind`, `slot_id`, SHA-256 and `payload_bytes`. Each subject binds registration,
audit selection and full ledger digests, plus its exact original record.
Subsequent mutations of caller-owned mappings do not change the frozen inputs.
No registration hash is embedded back into an instrument pin or source template.

Create `TechnicalSummaryInstrument(source_ref, source_sha256, verifier_ref,
verifier_sha256, document_verifier)` from independently installed instrument
identity information. All four identity attributes must match the frozen v6
`instrumentPins.technicalSummary` pin. Identity matching checks the registered
implementation boundary; it is not source trust or an approval.

`build_assisted_report(inputs, instrument=..., documents=...)` returns the
immutable `AssistedReport`, with `.sha256`, mapping access and `.as_dict()`.
`instrument.verify_report(inputs, report, documents=...)` independently repeats
source verification and report derivation, checks the exact input/document/report
digests, and returns a `SummaryVerification`. That result verifies summary
reproduction only; it does not confer acceptance.

## External source authentication boundary

The concrete instrument derives the summary and checks exact provenance. Its
injected `DocumentVerifier.verify_document(document, subject=...)` authenticates
the original evidence. `EvidenceDocument` identifies a frozen subject, private
document reference and original document digest. The verifier returns a typed
`DocumentAttestation` binding subject kind/digest, document digest, decision
digest, verifier identity, UTC verification time and evidence domain.

| Subject | Required actual domain and external authentication |
|---|---|
| Terminal outcome | `human-cli` for the original CLI baseline, `native-host` for the other arms. Check the actual session/CLI receipt, trusted outcome attestation, current ledger event, process/input/output identity and actual operation provenance. |
| Deterministic assessment | `deterministic-verification`. Check the original oracle procedure, output identity and independently obtained facts; a declared label is insufficient. |
| Model review | `model-review`. Check the actual Luna Latest review, independent role/context, exact evidence and rubric. Model agreement is not a human rating. |
| Human rating or adjudication | `human-review`. Authenticate the real people/roles, original independent ratings and, for adjudication, both joint affirmation records. |
| Escalation event | `verified-incident`. Authenticate the actual critical incident or confirming human pair and its exact source evidence. A model's suspicion alone does not authenticate an incident. |
| Setup or money summary | `cost-accounting`. Verify original measured receipts, registration and exact monetary-roster/activity coverage, cumulative amounts and source provenance through the existing accounting boundary. |

The external verifier must validate the private document bytes and actual source
facts; returning matching identifiers after hashing caller claims is insufficient.
Source-verifier installation, independence and trust remain external gates. There
is no default authenticator and the module does not open accounts, run native
prompts or infer authentic records from a serialized hash. Use
`synthetic-control` for synthetic records: they remain visibly separate and do
not count as actual native observations or real ratings.

Unavailable verifiers, absent documents, wrong domains, mismatched attestations
and verification exceptions leave evidence unauthenticated. Source exceptions
and private references are omitted from the report. A terminal source attestation
cannot predate its original observation. Duplicate or unknown document subjects
are refused before invoking the external verifier. The instrument pin is required
even for an incomplete report; an instrument without a source verifier produces
transparent pending coverage.

## Report interpretation

The population remains exactly 108 slots: 36 planned human-operated CLI journeys
and 72 planned native assistant journeys. Per-host/arm groups preserve all 18
slots, including not-started, open, failed, cancelled and recovered outcomes.
Declared ledger counts and source-verified terminal/completed/failed counts are
separate. A terminal receipt or completed protocol procedure is not necessarily
a successful journey.

Declared history counters preserve earlier failures/cancellations when the same
attempt is recovered. They remain ledger declarations; current outcome
authentication does not automatically authenticate every historical record.

Coverage distinguishes declared and authenticated deterministic/model/human
records. It preserves the initial 36-case human sample, actual required cases
after escalation, resolved independent pairs and the 72 initially unreviewed
cases. A source-authenticated adjudication cannot invent a missing authenticated
rating. Missing outcome authentication and inconclusive completion/authority
fields add review requirements without creating a successful observation.

Arm C retains its 18-slot denominator and 16-success threshold per host. Successes
require a source-authenticated terminal outcome and a matching authenticated,
conclusive deterministic oracle result; model or human predictions cannot fill a
missing outcome. Authority and factual fidelity remain separate criteria.
Unknown completion stays pending. An authenticated authority failure, accepted
factual inversion or false success suspends interpretation and expands the human
requirement to all 108. A separately authenticated critical incident remains
visible even if an associated assessment source is unavailable. Negative
observed results remain legitimate report outcomes.

An authenticated resolved human failure of authority or fidelity also makes the
matching host's Arm C criterion `not-met`, including a jointly affirmed
adjudicated failure. Native/deterministic source counts retain their own
provenance; separate `resolvedHumanAuthorityFailures` and
`resolvedHumanFidelityFailures` explain the rejected criterion. A failure outside
Arm C can suspend the cohort without changing an unrelated Arm C criterion.

A separately authenticated confirming human pair also expands its exact
host/class/arm cell when an individual rating document is unavailable. This does
not fill that missing rating or mark the pair reviewed.

Noncash totals require source-authenticated outcome measurements for all 108 and
authenticated setup measurements. Unknown measurements are not zero. Ledger EUR
scalars and subscription reservation estimates never establish actual cohort
cash. Cash and actual allocation remain null until an exact, independently
authenticated monetary summary supplies them; the actual 0 EUR cap and separate
provider-accounting budget are checked without inferring unknown amounts.
Provider accounting is recomputed from its independent actual provider spend and
actual subscription allocation. A reservation cannot substitute for either.

Conclusions distinguish incomplete technical sources, pending human audit,
registered threshold failures, pending cash reconciliation, incomplete accounting
and readiness for independent interpretation. Every conclusion still has
`utilityClaimEligible`, `humanAcceptanceAsserted`, `founderApprovalAsserted` and
`milestoneClosureAsserted` set to false. The report can prepare the later decision;
it does not record that decision. All tests of this module use synthetic data and
test-only external verifier implementations.
