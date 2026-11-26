# GitHub tracking reconciliation

The [Agent Braid Roadmap](https://github.com/users/jayanez/projects/6) is a
private planning view of the repository's Spec Kit records. The Constitution,
applicable ADRs, specs, task lists, assurance records, evidence and review records
retain their own authority. GitHub issue closure is a bounded task-tracking state;
it does not establish scientific validity or grant human or founder approval.

## Source of truth and stable IDs

- `specs/<number>-*/spec.md` provides the feature title; `tasks.md` provides
  `Tnnn` task titles, references and checkbox state. `assurance.json` is the
  source for requirements, scenarios and evidence. New spec directories and
  tasks must have stable IDs before tracking issues are created.
- [github-tracking.json](github-tracking.json) maps each spec to one GitHub
  milestone and explicitly records the parent issue and milestone states. Closed parents may
  have an open follow-up task; this must not be silently inferred away.
- Task state follows the source checkbox except for a documented override.
  Each override cites its evidence in `github-tracking.json`; recorded instances are
  in the [tracking history](GITHUB_TRACKING_HISTORY.md#task-overrides-and-cancellations).
  Remove an override only when its checkbox
  and evidence agree. A newly checked task is a proposed issue-state change,
  not automatic approval.
- `task_cancellations` is a separate owner-adopted noncompletion disposition.
  Each repository-relative decision file has a pinned hash, explicit adopted
  `cancelled-partial-infeasible` decision, owner provenance and the hash of the
  unchanged original unchecked task line. Missing/drifted/symlinked decisions,
  unknown tasks and overlaps with checked tasks/completed overrides refuse.
  This validates source consistency; hashes cannot authenticate a human decision.
  The planner binds `state_reason=not_planned`, including a reason-only repair
  for an already closed issue. It updates only the State-basis annotation while
  preserving the original criterion and other issue prose. Cancellation never
  means completed acceptance, and parent/milestone states remain explicit.
  Recorded cancellations are in the
  [tracking history](GITHUB_TRACKING_HISTORY.md#task-overrides-and-cancellations).
- `task_milestone_overrides` maps a task key `SPEC-NNN/Txxx` to a registered
  milestone title; its S1.5 introduction and procedure are recorded in the
  [tracking history](GITHUB_TRACKING_HISTORY.md#s15-system-one-shadow-activation).
- Issue bodies contain stable `agent-braid-spec-id` or `agent-braid-task-id`
  markers. Do not delete or reuse these markers. The linked repository files
  are current; issue prose may include historical reconciliation context.

## Milestone names and identity

Milestone titles use `ID — Capability` in English and sentence case. Keep the
historic M and S1 IDs stable. PUB, GOV, ADP, LAB and RES identify independent
publication, governance, adapter, workload-laboratory and research tracks; their
numbers do not establish a global implementation sequence. States, dates,
acceptance criteria and approval boundaries belong in fields and descriptions.

`milestone_numbers` binds each existing canonical title to its GitHub repository
milestone number. Renames preserve that identity, URL and issue associations.
A missing registered number, duplicate binding or occupied target title fails
closed. Future milestones without a number retain the existing creation path;
after creation, record their number before using title-only reconciliation.

The historical aliases of the naming migration are in the
[tracking history](GITHUB_TRACKING_HISTORY.md#historical-milestone-aliases).

Frozen evidence, closure records and historical reviews retain their original
names and scope. Current assignments use the canonical titles. The
[spec and milestone index](SPEC_MILESTONE_INDEX.md) lists every current spec
assignment. Current spec headers, planning programs and issue-draft metadata use
these titles; frozen delivery receipts remain historical.

For an authorized naming-only migration, follow the review/merge path below,
then use `audit --milestone-titles-only` and
`apply --milestone-titles-only --confirm-repository jayanez/agent-braid
--plan-sha256 <digest>`. This mode reads only remote milestones and writes only
their titles; unrelated issue text, assignments and state differences are
outside its scope. The digest binds the repository, scope and exact operations;
a full-audit digest cannot authorize a title-only apply or vice versa. Old digests
must be regenerated after upgrading the synchronizer.

For a reviewed single-milestone reconciliation, use `audit --milestone-number
<registered-number>` and then `apply --milestone-number <registered-number>
--confirm-repository jayanez/agent-braid --plan-sha256 <digest>`. The scope
includes source specs and tasks assigned to that registered milestone, together
with that milestone's title and configured state operation. It reads the full
repository issue inventory before narrowing operations. Duplicate markers,
missing selected issues, selected issues moved away from the milestone, or
unknown managed issues assigned to it fail closed. Newly registered source
records assigned to the milestone are included automatically once their managed
issues exist. To bootstrap newly registered records with no remote issue yet,
pass `--new-record-key <stable-id>` once per exact missing ID to both the audit
and reviewed apply. Without this explicit allowlist, every missing selected issue
still fails closed. Allowlist entries must identify known source records assigned
to the selected milestone and absent from the full remote inventory; present,
unselected or unknown IDs are rejected. The sorted allowlist is printed and
bound into the digest, which also binds repository, scope, immutable milestone
number and exact operations. It cannot authorize a full, title-only or
different-milestone apply. The apply still requires a clean `develop` checkout.
This mode does not infer parent closure from child states. `--milestone-number`
and `--milestone-titles-only` cannot be combined.

Capture all milestone identities, states, descriptions and dates plus issue
milestone numbers before and after the migration. Require equality except for
the approved titles, and a second title-only audit with `operations: []`.
Private Project membership and custom status remain a separate verification.

## Change path

1. Change the spec, task list and assurance record through the usual Spec Kit
   process. Update `github-tracking.json` for a new spec, milestone assignment,
   parent closure or evidence-backed checkbox exception. Review and approve the
   repository change independently of the GitHub tracking update.
2. Run `python3 scripts/sync_github_tracking.py source` locally. Pull requests
   run this structural check without writing to GitHub. Existing Spec Kit and
   validation gates still apply.
3. After merge to `develop`, run `python3 scripts/sync_github_tracking.py audit`
   with an authenticated `gh` CLI. The read-only audit lists missing milestones,
   issues, subissue links, title/task-text/requirement-trace drift and
   milestone/state differences. A task update can replace its generated `Trace`
   line while preserving source/state-basis lines and appended reviewer notes.
   Missing or duplicate trace lines require manual review; trace replacements
   are included explicitly in the reviewed plan digest.
   The legacy unreferenced-task fallback is equivalent to the current parent
   reference and is retained without rewriting historical issues.
   A weekly GitHub Actions run also audits repository tracking with
   `contents:read` and `issues:read`. A failed audit requires reconciliation; it
   does not authorize automatic writes.
4. Review the audit operations against the merged spec and actual evidence.
   From a clean `develop` checkout, run `python3 scripts/sync_github_tracking.py
   apply --confirm-repository jayanez/agent-braid --plan-sha256 <digest>` with
   the digest printed by the reviewed audit and a token that can write
   repository Issues. A changed plan is rejected. Apply is
   additive and idempotent: it creates or updates milestones/issues, links
   subissues, and changes state only as recorded in the reviewed sources. It
   refuses to apply if a managed issue has disappeared from the source, a marker
   is duplicated, or an issue body cannot be safely updated. It never deletes
   GitHub records. Rerun `audit` until it reports `operations: []`.
5. Check the private Project's **Specs and tasks**, **By milestone**, and
   **By status** views. The built-in Project workflows add new `spec` or `task`
   issues from `jayanez/agent-braid`, add subissues, set closed items to Done,
   and reopened items to Todo. Milestone and parent fields come from the linked
   issues. Set **Review pending** manually when a human or founder decision is
   still required; it is not inferred from an issue being open. Confirm item
   counts and the `project_review_pending` entries in the mapping after each
   reconciliation. Project membership and
   custom status are not currently audited by the read-only repository token,
   which lacks private user-Project access.

### Deliberately unpublished milestones

`unpublished_milestones` in `github-tracking.json` lists declared milestones that
are deliberately kept off GitHub. It currently names only
`M4.6 — Claude Code dynamic workflows` (SPEC-052, SPEC-053, SPEC-057, SPEC-058
and SPEC-059). Without the list, every post-merge and weekly full audit failed on
the roughly 370 operations that M4.6 always leaves pending, which hid real drift.

The full audit (no scope flag) still computes and prints those operations: they
appear under `skipped_unpublished` in the JSON output, grouped by milestone with a
`pending` count, and a `skipped unpublished milestone` line per milestone goes to
standard error. They are excluded only from the pass/fail decision, which depends
on `operations` alone, and from a full `apply`, which never publishes a listed
milestone. The skipped set is part of the plan digest when it is non-empty.
Operations are attributed by the desired milestone of their source record, or by
the milestone name for a milestone creation; orphan reviews and every operation of
an unlisted milestone count exactly as before. Pull request `source` checks are
unchanged apart from validating the list.

The list is validated by `source` and every audit. An undeclared, duplicate or
non-string entry is a configuration error, and so is an entry with a
`milestone_numbers` binding. A full audit also fails when a listed milestone
already exists on GitHub. Publishing a milestone therefore means removing it from
`unpublished_milestones` in the same change that prepares its publication; its
operations then count again, and once created its number goes in
`milestone_numbers`.

The audit deliberately does not create issues from unchecked speculative text,
declare future M2–M4 tasks, close a parent because every child is closed, or
convert a passing validator into approval. Source deletions and disputed states
require a human decision and a repository record before any remote change.

## Milestone history

Per-milestone publication records (M3.5, SPEC-047/M4.5, VIS.1, S1.5) are in
[GITHUB_TRACKING_HISTORY.md](GITHUB_TRACKING_HISTORY.md). They are dated records,
not procedure.
