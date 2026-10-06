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
  `SPEC-004/T005` retains an unchecked checkbox in the frozen public export.
  Its documented override cites the two same-commit agent reports bound by
  `specs/004-m0-closure/founder-review.json` and the approved M0 closure;
  this reconciles historical tracking without changing the published source
  record or making a new review decision.
  `SPEC-011` T001–T007 are checked against [merged PR #3](https://github.com/jayanez/agent-braid/pull/3);
  T008 and human review remain open. Remove an override only when its checkbox
  and evidence agree. A newly checked task is a proposed issue-state change,
  not automatic approval.
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

The naming migration preserves these historical aliases:

| GitHub number | Previous title | Canonical title |
|---|---|---|
| 1 | M0 | M0 — Operational foundations |
| 2 | M0.5 | M0.5 — Open strategy and preview preparation |
| 3 | M1 | M1 — Observable interaction analyzer |
| 4 | M2 | M2 — Confluence lab and scheduler |
| 5 | M3 | M3 — Braid semantics |
| 6 | M4 | M4 — Agent Braid runtime |
| 7 | Public research preview | PUB.1 — Public research preview |
| 8 | Cross-cutting governance | GOV.1 — Governance and adoption |
| 9 | M3.5 | M3.5 — Native proposal predictor |
| 10 | Platform evidence adapters | ADP.1 — Recorded-trace adapters |
| 11 | Workload evidence laboratory | LAB.1 — Effectful workload lab |
| 12 | Formal interaction research | RES.1 — Formal interaction research |
| 13 | S1.0 — Contracts | S1.0 — Decision contracts |
| 14 | S1.1 — Evidence | S1.1 — Decision evaluation |
| 15 | S1.2 — Native model | S1.2 — Native decision model |
| 16 | S1.3 — Integration | S1.3 — Advisory integration |
| 17 | S1.4 — Product and promotion | S1.4 — Product capabilities and promotion |

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

The audit deliberately does not create issues from unchecked speculative text,
declare future M2–M4 tasks, close a parent because every child is closed, or
convert a passing validator into approval. Source deletions and disputed states
require a human decision and a repository record before any remote change.
