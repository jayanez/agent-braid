# M3.5 owned-flow source instrumentation

**Status:** synthetic feasibility demonstration. It contains no real editing
sessions, consent record, utility labels or model evidence.

## Event capture and adapter

The local instrument accepts a list of explicitly synthetic sessions and
writes one new, canonical JSONL event log with exclusive creation. Each session
has one base event and exactly two operation events. Every event carries a
family, session and unique event ID; operation events bind to the immutable
base event. The source reference records provenance for the base and each
operation. The capture prints the SHA-256 of the complete event log. Keep that
digest with the source register if a later authorized capture uses the same
pattern; editing the file afterward invalidates its recorded digest.

The auditor enumerates each complete session and its one candidate pair. It
checks provenance and passes the unmodified base and operations to the
`anchored-sequence-v1` request validator. It does not infer concurrent events
from Git commits, repair an invalid anchor or trim a base to three elements.
Incomplete sessions have zero examined pairs; a complete but ineligible pair
receives one primary exclusion reason. The report carries its input log hash,
counts for sessions and pairs, reason counts, zero real admitted pairs and
`executionAuthorization: false`. It does not call the verifier or assign
assessed-usefulness labels.

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
demonstration. Expected result: five sessions and five pairs examined; one
synthetic pair admitted; one exclusion each for excessive base, unsupported
operation, invalid anchor and missing provenance; zero real pairs. Repeating
capture to another path must produce identical bytes and report.

## Gate for a real owned workflow

Before opening session payloads, record the source owner and explicit use
permission, participant/data rights, privacy decision, editing workflow,
immutable event feed and fixed contiguous window with start/end event IDs or
UTC timestamps. Capture at the point where the shared base and each proposed
operation are known; establish that the proposals came from the same base.
Do not derive that relationship from final Git patches. Keep private payloads
outside the public repository and publish only reviewed, non-sensitive counts
and hashes.

For the frozen window, enumerate every session and every candidate pair,
record the primary exclusion reason at both levels, and report yield by
repository/workflow family. Do not crop, extend the window to satisfy quotas
or call synthetic pairs real. A separate review must approve the real-source
adapter and the revised protocol before utility annotation or training.

## Later existing-source phase

T007 audits existing event logs, including company project logs only after
owner permission, participant/data-rights and privacy decisions are recorded.
First inspect metadata for immutable base and proposal events; then apply the
same frozen-window and exclusion audit. A repository or commit history alone
is not an eligible session feed. If neither route yields the required families
and class coverage, report source feasibility as inconclusive and seek a new
domain decision.
