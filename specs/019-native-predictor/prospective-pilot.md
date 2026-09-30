# M3.5 prospective owned-flow pilot runbook

**State:** tooling prepared; no real window registered or opened. Kinetiq and
SmartNotes each currently contribute zero observed eligible pairs. This
runbook implements only source feasibility under proposed ADR 0018. P019-01,
the complete evaluation protocol and T001 remain open.

## Trust boundaries and source families

Use `jayanez/kinetiq-braid-lab` and `jayanez/smartnotes-braid-lab` as private,
disposable engineering-decision contexts. Their `main` branch is control code;
`lab/main` and `lab/develop` are filtered, exact-file snapshots of each
source branch. `experiment/*` branches may start from a lab snapshot. The
snapshots contain no original source Git ancestry and are not production
mirrors. Reconcile a real source's branch SHA separately if it matters.

The first proposed Kinetiq family is an ordered shortlist of literature or
measurement decisions for the evidence pipeline. The first proposed
SmartNotes family is an ordered non-clinical architecture or Spec Kit option
list. Do not include athlete, customer, patient, audio, transcript, clinical,
consultation or product audit material. A source review must confirm each
selected file and its full text before export. The allowlist pins **Git blob
SHAs per branch**; even an approved source edit stops the next Action until
someone reviews and updates the matching pin. No live application code,
datasets, secret files or whole-repository mirror enters the lab branches.

The lab Actions run only after a GitHub App is installed on the specific
source repo with `Contents:read`; `M35_SOURCE_APP_CLIENT_ID` is a lab variable
and `M35_SOURCE_APP_PRIVATE_KEY` a lab secret. The lab's own `GITHUB_TOKEN`
has `Contents:write` only in that lab. Check actual runner and steps after
billing becomes available. Scheduled runs may be delayed or missed; a missing
sync must be reported as a gap. Manual dispatch is available. A pin mismatch
is a review request, not an occasion to auto-approve changed content.

`jayanez/agent-braid-m35-audit` is a separate private metadata repository.
Its `m35-seal.yml` accepts only versioned registration and aggregate seal
fields and retains `seal.json` for 180 days. It is not a content backup.
Neither GitHub Actions nor the lab repositories receive the event journal,
participant map, item text, local HMAC key or per-item hashes.

## Before any prospective window

For each family, record the actual source owner, editing workflow, all
participant/data rights and privacy decision, eligible and excluded material,
participant notice, authorized publication level, local journal custody and
90-day post-review deletion rule. Review the lab export allowlist. Put the
signed-off `m35-source-permission-v1` record **outside every Git repository**;
its schema has exactly `format`, `windowId`, `sourceOwner`, `workflow`,
`permissionGranted`, `participantRightsReviewed`, `privacyApproved`,
`labExportReviewed`, `approvedAtUtc`. The four flags are explicit decisions,
not defaults; the CLI checks their shape but cannot grant legal or human
permission. Record the source admission mechanism so all opened sessions can
be reconciled against the local ledger. An actor may use a pseudonym, but a
separate private mapping and participant notice remain the owner's duty.

Choose an unaltered 14-day UTC window beginning at midnight at least 24 hours
after remote registration. Create an unbound `m35-source-window-v1` JSON with
`sourceKind: "prospective"`, stable `windowId` and `familyId`, `startUtc`,
`endUtc`, `protocolCommit` (full Agent Braid Git SHA) and
`registrationRunId: null`. Use different window IDs for the two families.
After approval, emit the metadata-only registration payload:

```sh
python3 -m scripts.m35_sidecar /private/m35/kinetiq registration \
  /private/m35/kinetiq-window.json \
  --permission-record /private/m35/kinetiq-permission.json
```

Dispatch the printed JSON as the single `payload` input of
`m35-seal.yml` on the audit repository's `main` branch. Inspect the run, its
job, runner, steps and `m35-seal` artifact. A queued, skipped or billing-blocked
workflow is **not** registration. Record its real run ID, then initialize:

```sh
python3 -m scripts.m35_sidecar /private/m35/kinetiq init \
  /private/m35/kinetiq-window.json \
  --permission-record /private/m35/kinetiq-permission.json \
  --registration-run-id 123456789
```

The CLI verifies the remote artifact, run execution and 24-hour lead again.
The journal directory must be new, local and outside all Git worktrees. It
creates 0700 storage and 0600 files. Backups, host access and deletion are
managed under the source privacy decision. No source window has been
initialized by this document.

## At the authoring boundary

Use the CLI as the **only presented base and proposal submission path** in
the pilot. A session JSON contains exactly `participants` (distinct
pseudonyms), `base` (the complete ordered sequence of `{id,value}` items),
`contextSha` (the specific lab snapshot commit), and `sourceRef` (a private
source reference). Open it before any proposal. Every participant runs `view`
and keeps the returned receipt, then submits a proposal JSON with exactly
`operation` and `sourceRef`. An insertion names `kind: "insert"`, unique
`id`, `newId`, `value` and `anchorId` (`$root` or a base item ID). `propose`
requires that actor's preceding sidecar `view`. `reveal` refuses to show any
proposal until every registered actor has submitted. If an actor may have
seen another proposal outside the wrapper, record `external-observation`
before their own proposal. Close every session, including cancellation,
rejection and unresolved outcomes. Do not crop long lists, substitute shorter
values or recreate missing receipts.

The wrapper cannot prove a participant did not observe an outside screen or
that all natural work went through it. Reconcile every admitted session with
the separately controlled workflow register and record any bypass. A bypass
or unreconciled upstream count is an integrity limitation; do not present the
local hash chain as independent completeness evidence.

Run `audit` at any point to enumerate all local sessions and all unordered
proposal pairs. A base over three elements, invalid anchor, non-insert,
missing provenance or dependent observation remains in the ledger and is
excluded with a recorded primary reason. The report states
`realPairsAdmitted: 0` even for a prospective source until separate human
source review accepts its completeness and provenance. It does not invoke the
verifier or create usefulness labels. Any admissible count is structural and
provisional.

## Remote daily and final seals

After each UTC day ends, run `seal N --previous-run-id ID` and dispatch the
resulting JSON to the audit workflow. Day 1 links to the registration run;
each later day links to the immediately previous successful daily seal run.
The remote validator checks the predecessor artifact, frozen identity,
incrementing day and nondecreasing cumulative counts. Store run IDs in the
private operations register. If an Action is delayed or fails, retain the gap
and report the actual timing; do not assert a seal executed when it did not.
After day 14's successful seal, run `final-seal --previous-run-id ID` and
dispatch it. Final payload has aggregate counts, reason partition and keyed
journal/report commitments. The local key is never uploaded. These
commitments detect later change relative to a recorded seal; they do not
authenticate authors or independently certify source completeness.

Within 30 days after the window ends, compare the private ledger, admission
register and each seal to the predefined source workflow; report every
missing or excluded case and actual yield by family. Record reviewer decision
before any controlled aggregate publication. Retain the journal only as long
as the reviewed privacy decision permits; the proposed limit is deletion 90
days after that review. Confirm deletion of local copies and separately
assess backup retention. Optional lab-repo removal and GitHub App revocation
follow evidence review; deletion does not guarantee immediate removal of
GitHub PR metadata or backups.

## Decision after the pilot

Report observed sessions, pairs, exclusions, bypasses and all failed or
missing Actions for each family. Five families, sufficient labels and the
revised SPEC-019 protocol still require separate approval. If the two pilots
yield no eligible cases, record an inconclusive source-feasibility outcome and
seek a different domain decision. Never extend a window or select a three-item
slice to reach a quota.
