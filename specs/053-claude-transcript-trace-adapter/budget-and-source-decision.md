# Draft decision record: G0 budget and transcript source rights

**Status:** Signature superseded by revisions 2 and 3 of the preregistration
(2026-10-24); renewal against the final bytes, recorded after merge, is required
before the freeze. This is a draft for
the founder to accept, amend or reject. It records no approval, no provider
permission and no spend, and it authorizes no workflow run. It supports the
[G0 preregistration](../../docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md).

## State of decisions

This table is the single statement of state; other files link here instead of
restating it.

| Item | State |
|---|---|
| Founder chat declaration of 2026-10-24 (EUR 0, own-transcript scope, provider-terms position) | Declared in chat and transcribed by an agent in [founder-decision-20261024.md](founder-decision-20261024.md); it applied to the bytes of revision 1 and is **superseded** by revision 2, which changes the bound bytes. It is not a signature. |
| Binding founder record for the final revision-3 bytes (task T001) | **Pending.** Produced by the founder in a location the founder chooses; it binds the new hashes of this file, the proposal, the inputs file and the decision vectors file, computed at renewal. |
| Provider-terms confirmation | Pending; an owner declaration, not an authenticated observation. |
| Freeze of the preregistration | Not done; follows the renewal and the pre-freeze preparation (T002, T003). |

**Revision 3 (2026-10-24):** a founder decision redefined criterion C3 of the
preregistration (attribution coverage of changes), which changes the bound bytes
again. The revision-2 hashes are superseded as well as the revision-1 hashes
below. The renewal is to be recorded against the final bytes after merge; this
note does not state new hashes (a file cannot contain its own hash) and does not
claim a renewal or a signature. The state column above is unchanged: the binding
record stays pending, `signature-superseded-renewal-required`.

Revision 1 bytes (SHA-256) that the earlier declaration applied to: this file
`333406c25dbdf87b0cd72c2895f441998710e7f3a477e95c137647e12e4a9c62`, the proposal
`02291d0d9cbde74222652ba6b22a4cdd0293fcf7a5aa3c6adf9a119cb6cb3e8d`, the inputs
file `6a5b6167257523947361be3ecba26690a42b5d1316d9045c664f2f71ec628033`.

## Decision requested

1. Confirm that gate G0 of M4.6 runs on the founder's existing Claude
   subscription with included quota and **EUR 0 additional spend**.
2. Confirm that the founder's own Claude Code subagent transcripts, produced in
   the founder's own sessions on an owner-controlled repository, may be read
   locally as measurement input under the retention rules below.

## Budget

- Authority: [first-cohort budget limits](../../docs/tooling/BUDGET.md). On
  2026-10-09 the owner selected existing subscriptions within included quotas and
  set additional spending at EUR 0. The decision of 2026-10-23 for M4.6 applies
  the same rule to G0 and does not raise any cap.
- Billing route: existing subscription, included quota only. No API key, paid
  API call, purchased credit, overage, extra usage, auto-recharge or subscription
  upgrade. The founder stops on quota exhaustion; a run cut short is excluded as
  `quota-exhausted`, never completed with paid capacity.
- Quantities kept separate and recorded when the host exposes them: subscription
  usage, any additional charge (expected zero), allocated subscription value and
  API-equivalent estimates. Unavailable is recorded as unavailable, not zero.
- Who runs: the founder. No coding agent starts the workflows in this delivery.
  Each workflow run also needs the host's own per-run approval.
- Not used: the Claude source composition receipts of
  [CLAUDE_SOURCE_CONTRACT](../../docs/tooling/CLAUDE_SOURCE_CONTRACT.md). They
  check a Braid-supervised launch and G0 has none; the founder instead states in
  the founder's binding record that extra usage and auto-recharge are off, as a manual
  declaration, not an authenticated observation.

## Transcript source rights

Following the precedent of the Claude source contract (owner-declared
single-organization scope, no credential handling, claims not authenticated by
the document that states them):

- **Source:** subagent transcripts of the founder's own sessions, on the
  founder's machine, produced from the founder's own repository.
- **Not in scope:** any other person's transcripts, any repository the founder
  does not control, any shared or hosted session store.
- **Provider terms:** the founder confirms that using the founder's own session
  files for local analysis is consistent with the applicable provider terms for
  the account. This draft does not assert that confirmation. Status: pending.
- **Sensitive content:** transcripts may contain prompts, file contents, command
  output and secrets present in the repository or environment. The founder
  chooses a repository without secrets for G0 and reviews the manifest before any
  retention.
- **Real-source admission for the product:** if G0 passes, the product adapter
  still needs the separately reviewed admission record required by SPEC-023
  (rights, allowed fields, transformations, retention, privacy) before any real
  transcript is accepted by the code. This record does not substitute for it.

## Retention and aggregation

| Item | Rule |
|---|---|
| Transcripts, prompts, file contents, diffs, repository file paths, merge-tree output, workflow journals | Read in place or kept locally; never copied into the project repository; not published. The founder may delete them after reporting. |
| Probe output | Integer counts only: tool-call counts per class per agent, and per run the count of ordered agent pairs and distinct paths with a read/write overlap. No path strings or path hashes. |
| Retained after founder review | Manifest without private task prose, branch-head hashes, prediction-file hash, per-arm run-level labels, probe counts, aggregate metrics. |
| Pre-freeze layout and tool-name census | Read in place from the founder's own existing subagent transcripts; only a structure and tool-name histogram is retained (record kinds, tool names per class, calls paired with a result, agent counts), aggregate-only; no path, path hash, prompt, file content or tool output. A de-identified fixture derived from it stays local. |
| Probe and runner scripts | Bytes hashed before the freeze. |
| Run manifest | Bytes hashed before each run. |

This table is the G0 retention rule (`aggregate-only`). It is stricter than the
product mapper's retention, which keeps allowlisted metadata (repository-relative
paths, base object ids, a transcript digest) and counts under the label
`allowlisted-metadata-and-counts` and needs its own reviewed admission record.

## Signature

Founder decision: pending renewal.
Signature: pending (the declaration of 2026-10-24 is superseded).
Date: pending.
Amendments: this file was edited on 2026-10-24 (same day) for revisions 2 and 3, so the
bytes the earlier declaration applied to no longer exist.

Nothing here becomes effective until the founder signs a separate record that
binds the bytes of this file together with the proposal, its inputs file and the
decision vectors file.
