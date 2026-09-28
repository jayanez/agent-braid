# M3.5 owned-flow source instrumentation

**Status:** synthetic feasibility demonstration. It contains no real editing
sessions, consent record, utility labels or model evidence.

## Event capture and adversarial audit contract

The local instrument accepts an explicitly synthetic source envelope with
`format: "m35-synthetic-window-v1"`, a declared inclusive sequence window
(`window.startSequence` and `window.endSequence`), and `sessions`. Every
session declares its `familyId`, `sessionId`, immutable base and
`baseSequence`, plus exactly two operation events with `sourceSequence`.
Events retain their source order; capture must not sort or otherwise repair the
input. Each event carries a unique event ID and provenance, and each operation
must explicitly name the shared `baseEventId`; capture does not infer a missing
reference from the enclosing session.

The capture writes a new canonical JSONL log with exclusive creation. Its first
line is a manifest (`format: "m35-capture-manifest-v1"`) containing the
declared window bounds and expected event count. Following lines contain the
events in input order, including their sequence, canonical `eventHash` and
`previousHash`; the first event links to the `null` genesis value. The hash is
SHA-256 over the canonical event record excluding only `eventHash`, so the
previous link itself is covered. Each event's `previousHash` equals the prior
event's `eventHash`. The capture also prints the SHA-256 of the complete log.
Keep that digest with an authorized source register; editing the file
invalidates the recorded digest.

The auditor requires the event sequence to cover the declared window exactly,
in order, with no gaps, and the manifest count to match. It fails closed on
missing, added, duplicate, reordered or hash-tampered records, duplicate event
IDs, and family/base/session mismatches. It must not sort, fill gaps, drop
records or regroup inconsistent records to make a log pass. A complete pair
whose operation points to the wrong base is counted as examined and excluded
with `base-mismatch`. The base event must precede both operation events in the
source sequence. Other complete pairs are checked for provenance and
passed unmodified to the `anchored-sequence-v1` request validator. The
instrument does not infer concurrency from Git commits, repair an invalid
anchor or trim a base to three elements. A structurally invalid window fails
the audit instead of yielding a partial success report. A complete but
model-ineligible pair receives one primary exclusion reason.

Hashes provide tamper-evident integrity checks for the captured bytes; they
are not signatures, do not identify who produced the events and do not prove
source authenticity. A successful audit establishes consistency of the
provided log with its manifest and hash chain. It cannot prove that the
upstream feed included every real event or session in the declared window, nor
estimate real-world source yield. The synthetic report therefore states zero
real admitted pairs and is not a source-completeness or prevalence estimate.
The report carries its input log hash, counts for sessions and pairs, reason
counts, zero real admitted pairs and `executionAuthorization: false`. It does
not call the verifier or assign assessed-usefulness labels.

Run from the repository root:

```sh
python3 -m scripts.instrument_m35_flow capture \
  examples/m35/m35-synthetic-sessions.json /tmp/m35-capture.jsonl
python3 -m scripts.instrument_m35_flow audit /tmp/m35-capture.jsonl \
  --output /tmp/m35-report.json
```

Use a fresh output path for each capture: the command refuses to overwrite an
existing log. The checked-in [capture](../../examples/m35/m35-synthetic-capture.jsonl)
and [report](../../examples/m35/m35-synthetic-report.json) are the same
demonstration. Expected result: the manifest window is fully covered by the
declared event count across 18 events; six synthetic sessions and pairs
examined; one pair admitted; one exclusion each for a wrong base reference,
excessive base, unsupported operation, invalid anchor and missing provenance;
zero real pairs. Repeating capture to another path must produce identical
bytes and report. Adversarial mutations that remove, add, duplicate, reorder
or alter an event must fail closed. These checks exercise the instrument
against the supplied synthetic fixture only; they do not validate completeness
of a real source feed.

## Gate for a real owned workflow

Before opening session payloads, record the source owner and explicit use
permission, participant/data rights, privacy decision, editing workflow,
immutable event feed and fixed contiguous window with start/end sequence or
event IDs or UTC timestamps. Capture at the point where the shared base and
each proposed operation are known; establish that the proposals came from the
same base. Do not derive that relationship from final Git patches. Keep private
payloads outside the public repository and publish only reviewed,
non-sensitive counts and hashes.

For the frozen window, preserve an immutable source sequence, declare bounds
and expected event count, enumerate every session and every candidate pair,
record the primary exclusion reason at both levels, and report yield by
repository/workflow family. Reconcile the capture against the source feed's
own completeness controls; a local hash chain alone cannot establish that the
feed omitted nothing. Do not crop or extend the window to satisfy quotas, or
call synthetic pairs real. A separate review must approve the real-source
adapter and revised protocol before utility annotation or training.

## Later existing-source phase

T007 audits existing event logs, including company project logs only after
owner permission, participant/data-rights and privacy decisions are recorded.
First inspect metadata for immutable base and proposal events; then apply the
same frozen-window and exclusion audit. A repository or commit history alone
is not an eligible session feed. If neither route yields the required families
and class coverage, report source feasibility as inconclusive and seek a new
domain decision.
