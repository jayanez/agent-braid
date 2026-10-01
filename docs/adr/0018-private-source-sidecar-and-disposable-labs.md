# ADR 0018: Private authoring sidecar and disposable decision labs

- **Status:** proposed for M3.5 source-feasibility review; no real capture approved by this ADR
- **Date:** 2026-09-30
- **Decider:** Juan Antonio Yáñez García, founder, after source and privacy review
- **Constitutional articles:** 0, 6, 9, 13–14, 17–20, 23–25

## Context

SPEC-019 has no admitted real editing-session pair. Git history, pull requests,
timestamps and final document diffs cannot establish that two participants
proposed independent inserts against the same observed base. A public event
journal would also retain private decisions in Git history after branch deletion.

## Decision

Use an opt-in local Agent Braid sidecar at the authoring boundary for the two
candidate non-clinical workflows. It presents the immutable base to each actor,
records that receipt, accepts each proposal before revealing another, records
external observations and close outcomes, and enumerates all opened sessions
and unordered proposal pairs in a frozen 14-day UTC window. The adapter calls
the unchanged `anchored-sequence-v1` request validator. The private local
admission register and hash-chained journal are reconciled; neither proves
that work outside the wrapper was captured or that actor identity is authentic.

Before prospective capture, require a source-owner/participant-rights/privacy
record and a successful remote registration at least 24 hours before the
window begins. The registration and daily/final remote seals contain only
window identity, commit reference, cumulative counts, exclusion counts and
keyed commitments. The key and journal remain local. An actual successful
GitHub Actions job with runner and steps is required; queued, skipped and
billing-blocked checks do not satisfy this gate. Register separately for
Kinetiq and SmartNotes. No utility label, model training or execution follows.

Use separate private, disposable lab repositories for decision-context
snapshots. Each source's `main` and `develop` is exported to `lab/main` and
`lab/develop` as **exact-file, content-pinned filtered snapshots**, with no
source Git ancestry. Each changed blob requires review before the next sync.
Experiments work on `experiment/*` lab branches. These branches and repos are
not production mirrors and cannot validate naturally occurring production
concurrency. No original Kinetiq or SmartNotes workflow or experiment commit
is required. Each source has its own read-only SSH deploy key, available only
as an Actions secret in its corresponding lab. The keys grant Git read access
to one source repository apiece, cannot call the GitHub API and must be
explicitly revoked after the pilot. The lab's own token writes only its lab
repo. A CLI-managed deploy key avoids requiring a GitHub App credential or
installation for this two-repository pilot; any broader source integration
would need a new credential decision.

## Alternatives considered

- Experimental branches in the source repositories would leave Git and PR
  traces in their private history and confuse source and experimental events.
- Git-derived sessions cannot recover receipts or independent intent.
- An unfiltered mirror would copy unrelated application and sensitive files.
- GitHub Actions as the event journal would publish granular authoring data to
  logs and artifacts, and scheduled runs cannot replace the local admission
  boundary.

## Consequences

This adds a local operational path but no public API or production runtime
dependency. Deleting lab branches or repositories later is cleanup, not a
guaranteed erasure of GitHub metadata or backups. The local journal retention,
participant notice and final publication review require separate records.
The two candidate families cannot meet SPEC-019's five-family threshold by
themselves. A dry run through the same code remains synthetic. All results
remain provisional until upstream completeness and eligibility are reviewed.

## Validation

Reproduce synthetic admissions and exclusions, incomplete/tampered journal
rejection, hidden-proposal barrier, content-pin failure, filtered branch
ancestry, and remote seal chain rejection. Confirm actual GitHub runner and
steps before a real window. Record observed real yield and exclusions for
both workflows, including zero yield or infrastructure failure. Revisit the
domain rather than extend a window or manufacture a quota.

## References

- [Constitution](../../CONSTITUTION.md)
- [Bounded M3 exchange](0017-bounded-structured-exchange.md)
- [SPEC-019](../../specs/019-native-predictor/spec.md)
- [Source instrumentation](../../specs/019-native-predictor/instrumentation.md)
