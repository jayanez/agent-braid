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
  `SPEC-004/T005` is checked against the two same-commit agent reports bound
  by `specs/004-m0-closure/founder-review.json` and the approved M0 closure;
  this reconciles a historical source checkbox, not a new review decision.
  `SPEC-011` T001–T007 are checked against [merged PR #3](https://github.com/jayanez/agent-braid/pull/3);
  T008 and human review remain open. Remove an override only when its checkbox
  and evidence agree. A newly checked task is a proposed issue-state change,
  not automatic approval.
- Issue bodies contain stable `agent-braid-spec-id` or `agent-braid-task-id`
  markers. Do not delete or reuse these markers. The linked repository files
  are current; issue prose may include historical reconciliation context.

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
   issues, subissue links, title/task-text drift and milestone/state differences.
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
