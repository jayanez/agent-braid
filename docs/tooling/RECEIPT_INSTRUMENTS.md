# Private receipt instruments

`agent_braid.tooling_receipt_instruments` supplies concrete implementations of
`AdmissionVerifier`, `OutcomeVerifier` (including its pre-dispatch start method),
and `CostVerifier`. They read frozen private documents and original evidence,
authenticate the complete boundary, and return the existing typed attestations.
They never start an executable, issue a prompt, read a provider account, create a
grant, operate the human CLI baseline, or claim human/founder acceptance.

This is implementation infrastructure for SPEC-044 and OP005. Installing an
instrument, matching a hash, or passing its synthetic tests does not complete
native evaluation or cost reconciliation.

## Installation and trust

Construct an `InstrumentIdentity` with the four exact registration v6 fields:
`source_ref`, `source_sha256`, `verifier_ref`, and `verifier_sha256`. The instrument
exposes immutable properties with those names. Verification checks the exact
registration hash, registered slot and instrument identity before and after
external verification. The installation must independently authenticate the
source/verifier artifacts and the authenticity root. These labels and digests
identify the installed instrument; they do not establish that it is trusted.

The constructor requires an external `ProvenanceAuthenticator`. There is no
permissive default, self-signed decision reader, synthetic-to-authentic conversion,
or built-in account/invoice authenticator. That callable receives an immutable
`AuthenticationRequest` containing the complete registration, exact slot, all
method inputs, the private wrapper bytes and every original evidence byte string.
It must authenticate the original provenance, applicability and observation
contract of **all** required domains, including facts encoded in the context.
A matching `DocumentAuthentication` is only valid when this substantive verification
has actually happened. A callback that copies request hashes is suitable solely
as a clearly synthetic offline test double.

| Method | Original facts the trust root must authenticate |
|---|---|
| `PrivateAdmissionInstrument.attest` | Exact registration approval; rights; existing authority and its journey scope; cumulative cost coverage; current stop state; every source required by the host composition contract; actual model identity. |
| `PrivateOutcomeInstrument.verify_start` | Applicability of the original admission/approval to the exact slot; existing authority; fresh cumulative measures and stop state; current source composition and model identity. The complete sealed admission and current ledger digest are included. |
| `PrivateOutcomeInstrument.verify_outcome` | Native outcome provenance; independent fixture-oracle evaluation; actual model identity. It includes the complete admission and raw adapter-output hash. |
| `PrivateCostInstrument.verify` | Original activity measurements, complete outer-activity/process-set coverage, revision identity and the stated monetary basis. |

Admitting or starting a journey requires explicit measured nonmonetary fields.
The operational v6 boundary permits unknown additional cash (`eur: null`) and
refuses a known positive additional amount. The concrete reader preserves that
unknown value; the enclosing capture/session validators still enforce budgets,
prior cumulative coverage, source freshness and all registration constraints.
Open incidents, an unrecoverable run, or two consecutive infrastructure failures
prevent an admission/start attestation. An attestation returned by a direct method
call is not an independent execution permission; consumers must use the existing
capture/session pipeline with all of its gates.

An original authorization decision, cumulative cost snapshot and stop snapshot
must each appear under their exact reference and actual source-byte digest.
Authority provenance must additionally authenticate any existing grant, bound
plan, interrupted-run receipt and action included in that complete context. The
instrument never supplies missing authority or creates a test grant in a real
session. The authenticity root must reject synthetic provenance for these real
observation domains, even if all syntactic fields match.

## Private document format

Pass a frozen `documents` map keyed by `(phase, subject_sha256)` and an `evidence`
map keyed by opaque evidence reference. Each value is a `PrivateDocument` with an
absolute canonical path and its expected SHA-256. References never resolve to
paths automatically. The reader rejects symbolic links, missing files, unsafe
modes/ownership, duplicate JSON keys, nonfinite values, oversized documents and
byte drift. Direct containing directories must be owned by the current user and
mode `0700`; files must be owned by that user and mode `0600`. No receipt is
written by these instruments.

Each wrapper has exactly these fields:

```json
{
  "schema": "agent-braid-m45-private-instrument-receipt-v1",
  "phase": "costs",
  "subjectSha256": "<exact caller subject digest>",
  "contextSha256": "<digest of complete canonical context>",
  "observedAt": "<original explicit UTC observation>",
  "decisionSha256": "<authenticated decision digest>",
  "evidence": [
    {"ref": "<opaque source ref>", "sha256": "<source byte digest>",
     "domains": ["cost-accounting"]}
  ],
  "result": "<phase-specific exact object>"
}
```

This schematic JSON is documentation, not a valid receipt. Use
`admission_context`, `start_context`, `outcome_context`, or `cost_context` to form
the full context required by each method. Canonical encoding is sorted JSON,
compact separators, UTF-8 with `ensure_ascii=False`, and `allow_nan=False`.
For admission the result is exactly `{"admitted": true}`; its decision digest
must equal the original `AuthorizationContext.decision_sha256`. For start it is
exactly `{"startVerified": true}`. For costs it is exactly `CostReceipt.subject()`.
The original cost source must be present; an invoice, estimate, reference or
unavailable billing basis keeps its existing meaning. Unknown fields are never
replaced by zero. An estimate/reference cannot become actual cash through this
reader or through a matching digest.

## Independent outcomes

`PrivateOutcomeInstrument` also requires an explicit `OutcomeOracle`. The oracle
receives the immutable authentication request and canonical raw adapter bytes. It
must derive the existing `VerifiedOutcome` fields using the registered fixture's
oracles and the authenticated evidence, rather than echoing JSON labels.

Return an `OracleResult` binding the full context digest, raw-output digest,
evidence digests, typed outcome, and canonical outcome digest. The wrapper result
must match that independent derived output exactly. A declared success that
contradicts the oracle is refused. Invalid, refused, cancelled and failed outcomes
remain valid observations when their provenance and fields are verified. A `valid`
status requires actual completion `true`; authority failure is preserved as
`false`. An unknown outcome or cash label remains `null`. Returned cost mappings
are immutable copies. There is no generic built-in oracle that can establish
native authority correctness from arbitrary prose; installation must provide
and pin the actual registered evaluator.

## Freshness, cancellation and limits

The constructor accepts a UTC clock, a cancellation event and an explicit wrapper
`max_age_seconds` (default 60; bounded to one day for archived accounting). The
reader rejects future dates, expiry, clock regression and cancellation before or
after external evaluation. Original observation timestamps embedded in bound
inputs cannot be later than the wrapper observation. Re-reading a wrapper never
rejuvenates its sources. Source-specific freshness remains the authenticated
composition/runtime contract: Codex sources at most 60 seconds; Claude permits
900 seconds only for recharge. A longer archived accounting wrapper lifetime
does not relax source or process admission freshness.

Every private document and context is rechecked after authentication and the
oracle. Cancelled or changed inputs produce no attestation. Reentrant verification
is refused. Callbacks are synchronous trusted installation code: the reader
cannot forcibly terminate a blocked or malicious Python callback. Caller-level
bounded execution/cancellation and native dispatch serialization remain required.
No transcript is logged by this module and callback error text is not reproduced.
The file checks are point observations under a trusted stable local installation;
they do not protect against arbitrary hostile same-user kernel/process control.

The offline tests use a temporary private directory and explicitly synthetic
trust-root/oracle doubles. Their successful attestations apply only to those
controls. They establish neither native observation authenticity nor experimental
approval, human ratings, actual cash, or milestone acceptance.
