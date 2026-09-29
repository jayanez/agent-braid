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

### Recommended signaling boundary for Kinetiq and SmartNotes

Use an opt-in **Agent Braid local sidecar at the authoring boundary**, before a
proposal is incorporated into a document or pull request. An editor/plugin is
not required for the first pilot: a small authoring wrapper presents the base
through the sidecar and submits each proposal through it. A manual statement
that an actor saw a base is not an acceptable substitute for that read event.
The sidecar owns the append-only event journal and the eligibility adapter;
the host repositories keep their normal files and review process. Git hooks,
commit timestamps, Issues, final diffs and product audit logs are downstream
corroboration only, never the source of the shared-base relation.

The proposed real-source contract is distinct from the synthetic
`m35-synthetic-window-v1` format above. Before any real capture, version and
review a `source-window` contract with these signals:

| Signal | Required evidence at emission time |
| --- | --- |
| `session-open` | Repository/workflow family, opt-in participants, source list identity, complete ordered base (including an empty base), immutable item IDs and values, base version/digest, source reference and capture-window sequence. |
| `base-seen` | Participant/actor pseudonym, the exact base event/version presented to that actor, and a source receipt. Merely sharing a hash in a later PR does not prove what was seen. |
| `insert-proposed` | Unique event/operation/new-item IDs, actor, base event ID, base/root anchor, value, source reference and journal sequence. Emit on proposal submission, before another proposal can be folded into that actor's view. |
| `session-close` | All proposals and non-insert edits, cancellations, accepted/rejected outcomes, final source reference, sequence and completeness reconciliation against the authoring process. Do not drop unsuccessful proposals. |

Concurrent intent here means two proposals were made from the same **observed**
immutable base, with neither actor observing or depending on the other's
proposal before submission. Sequential journal writes can record such intents;
wall-clock overlap alone cannot establish them. A second actor who refreshed
after the first proposal is a dependency and must be excluded. The process
must provide the two `base-seen` receipts and independence evidence; if those
are unavailable, record `concurrency-unproven`. Do not have an agent recreate
the receipts after the fact. `sourceRef` and hashes prove neither participant
identity nor upstream completeness; separately reconcile journal sequence and
session IDs with the process's own admission register.

The real adapter must enumerate **every** session opened in the frozen window,
all its proposals and every unordered same-base candidate pair. It must retain
sessions with zero, one or more than two proposals and count them with a
primary exclusion reason where appropriate. Pairs sharing a base but lacking
independence evidence are excluded; cancellations and unsupported edits remain
visible. Only then does it pass unmodified pure-insert pairs to the M3 request
validator. The current synthetic CLI requires exactly two operations per
session, accepts only `sourceKind: synthetic` and groups three adjacent events;
it is an integrity rehearsal, **not** an adapter for these real signals.

For Kinetiq, pilot the evidence pipeline's **ordered shortlist of candidate
literature/measurement decisions** before promotion into a ruleset or ADR.
Instrument a naturally occurring shortlist with at most three existing items;
each independently proposed new item needs a stable ID and an anchor. Keep
threshold values, athlete material, goldens and customer data outside this
pilot. The versioned ruleset JSON and its PR remain output artifacts, not the
source event feed. A full ruleset or long task list is not a three-item base.

For SmartNotes, pilot **non-clinical architecture or Spec Kit decision-option
lists** before they become an ADR/spec. Record only repository engineering
options; never use consultation worklists, patient tasks, review actions,
STT corrections, clinical drafts, `PA-NNNN` or product audit events. The
existing ADR and spec are output artifacts. Do not slice a longer decision
list or invent a second actor to obtain a pair.

The same contract can cover further workflows, but each repository plus
workflow is a separate family only after its source and sampling rule are
reviewed. These two pilots alone cannot satisfy the five-family protocol, and
neither is claimed to yield any pair. A dry run using invented content can
exercise signal ordering and failures; it remains synthetic even when emitted
through the future real-source adapter.

### Scenario coverage to measure, not manufacture

| Observed signal pattern | Audit disposition |
| --- | --- |
| Two independent pure inserts from the same base, same anchor | Admit if the entire base and both payloads satisfy `anchored-sequence-v1`; record the verifier's bounded result separately. |
| Two independent pure inserts from the same base, distinct root/base anchors | Admit under the same checks; preserve the exact anchors so policy and verifier can distinguish topology. |
| Second actor saw the first proposal or the two operations reference different bases | Exclude as dependent/base mismatch; chronological closeness is insufficient. |
| A delete, replacement, nested anchor, reused item ID or invalid root/base anchor | Retain in the session ledger, exclude the invalid pair with a primary reason; do not translate to a pure insert. |
| More than three base items, one/no proposal, missing receipt/provenance, or an unreconciled sequence gap | Count the session and all applicable attempts; exclude or fail the window integrity audit as appropriate. Never select a three-item slice. |

After source admission, the separate human rubric still needs policy-blind
attempts on every holdout pair, including cases the baseline would keep in
order. Neither Kinetiq nor SmartNotes has supplied observed positive/negative
utility labels, class coverage, five families or 100 adjudicated pairs. A
capture pilot can establish whether those requirements are feasible; it must
not tune the workflow to meet them.

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
