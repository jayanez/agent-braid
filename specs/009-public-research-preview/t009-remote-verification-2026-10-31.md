# SPEC-009 T009 — remote verification record, 2026-10-31

**Purpose:** give the founder current, read-only evidence to decide each of the 7
T009 obligations. This record is not a decision, not an authorization and not a
retroactive approval. It changes no remote state and no historical record.

- Observed: 2026-10-31, with `gh` (authenticated as `jayanez`, admin on the public
  repository) and `git ls-remote`, read-only calls only.
- Reference: `develop` at `6f4870ea8a885f3bf5c1e4e563a9a3759886d9aa`.
- Compared against: the 7 obligations in
  `specs/026-adoption-evidence-program/legacy-status-reconciliation.json` (lines
  33–130), `specs/009-public-research-preview/founder-review.json`,
  `docs/releases/publication-cutover.json` and
  `docs/releases/publication/CUTOVER_AUDIT_2026-09-25.md`.
- `currentRemoteVerified` in the reconciliation record is still `false`; this
  record does not edit it. Setting it is a founder-decision follow-up (section 4).

## 1. Standing facts

- `independentValidation` is `pending` everywhere; publication does not establish it.
- `founder-review.json`: `remoteCutoverAuthorized: false`,
  `repositoryVisibilityChangeAuthorized: false`, `independentValidation: pending`.
  It approves the bounded local publication evidence and closure of the local
  dossier (`milestoneClosure`), whose rationale states that remote rename,
  repository creation, push, visibility change, release and archival remain
  separately unauthorized and pending.
- `publication-cutover.json`: all 7 operations `authorized: false`,
  `executed: false`; status `pending-authorization`. It is a frozen plan.
- Observing that an operation happened does not show who authorized or performed
  it. The GitHub API for a user-owned repository exposes no audit log, so authorship
  and authorization of each action remain unestablished by this record.

## 2. One line per obligation

Columns: what is observed now, what stays unestablished, and the question the
founder answers; the answer is theirs to record.

| # | Obligation (`id`) | Observed now (2026-10-31) | Still unestablished | Decision for the founder |
|---|---|---|---|---|
| 1 | `rename-private-repository` | `jayanez/agent-braid-private-archive` exists (repo id 1366735468, created 2026-09-11T22:15:33Z, private, archived). The public `jayanez/agent-braid` has a different id (1379980892, created 2026-09-21T15:04:33Z), so it is a new repository, consistent with a rename of the old one. | Rename time and who performed it; no API source for either. | Accept the inferred rename (archive repo id 1366735468, created 2026-09-11) as the intended T009 action, record it as done, or leave it open. |
| 2 | `create-clean-public-repository` | Public, not archived, default branch `develop`, one root commit on every branch (`9b84467d54444138db8c000f442d9aea6040cab2`, tree `33c765440ba52f7e59ba9ecd142140e3b89ff594`), no private ancestry. Created 2026-09-21T15:04:33Z. | `founder-review.json` (`reviewedCommit` `baadba5c`) binds `evidence.json` by SHA-256, which records local candidate root `4481ec6f…` (tree `1e9868ca…`); that root is **not** in the public repository. `evidence.json` `evidenceScope` anticipates that "the final public root receives its own reproduction record"; `docs/releases/publication/reproduction.json` is that internal reproduction, with field `reviewedCommit` = `9b84467d` (an internal reproduction, not a founder review). This record found no committed founder decision binding `9b84467d` to the 2026-09-21 approval. `2026-09-26-restored-history.md` and the ADR 0016 decision (2026-09-26) cover related root/provenance repair but are not a T009 authorization. | Accept `9b84467d` as the clean public root for T009, or require a mapping record before closing. See flag P. |
| 3 | `push-clean-branches-and-tag` | Branches `develop` (`6f4870ea…`) and `main` (`55d0e122…`) exist. Tag `v0.1.0-alpha.1` is annotated: tag object `99fbc39c701ddc13f607a792246fa6de7dd716f9`, peeled commit `55d0e122eaad586afdbfd1422e2d6c487c571048` (equals `main`), tagger Juan Antonio Yáñez García, 2026-09-21T15:04:51Z. `git ls-remote` agrees with the API. Extra refs exist beyond the original scope: `v0.1.0-alpha.2` and later tags, `plugin-dist`, `feat/fc1-real-admission*`, `har/founder-review-20261031`. | Who pushed. `main`'s head commit is not GitHub-verified (unsigned). `develop` and 17 other branches were force-pushed on 2026-10-13 per `2026-10-13-attribution-correction.md`; `main`, the root and the tag were not rewritten. | Accept the two branches and the tag as the T009 push, and say whether the later refs and the 2026-10-13 force-push stay outside T009. |
| 4 | `configure-rules-and-security` | **No repository rulesets** (`rulesets` returns `[]`, including inherited). Classic branch protection on `develop` and `main`: linear history, conversation resolution, admins enforced, force-push and deletion blocked, code-owner review required, stale reviews dismissed; approving reviews required: `develop` 0, `main` 1. Required status checks: none on either branch. Security: secret scanning, push protection and Dependabot security updates enabled; vulnerability alerts enabled. Secret-scanning non-provider patterns and validity checks disabled. `.github/CODEOWNERS` exists. | Whether "rules" in the original task means classic branch protection (observed) or rulesets (absent). Whether zero required approvals on `develop` and no required checks are intended. Continuous effectiveness since cutover. | Accept classic branch protection plus the listed security settings as satisfying "rules and security", or state which missing setting is required. |
| 5 | `change-visibility-to-public` | `visibility: PUBLIC`, `isPrivate: false`. | Time of the change and who made it. `founder-review.json` says visibility change was **not** authorized at the 2026-09-21 review. | Record whether public visibility is accepted as intended and authorized for this reconciliation. It cannot be treated as pre-authorized. |
| 6 | `publish-github-prerelease` | Release `Agent Braid v0.1.0-alpha.1` for tag `v0.1.0-alpha.1`: `prerelease: true`, `draft: false`, 0 assets, created 2026-09-21T15:04:51Z, published 15:04:56Z, author `jayanez`, target `develop`. Body states `independent_validation: pending` and "not production safe". A later prerelease `Agent Braid 0.1.0-alpha.2` (2026-10-27) exists and is outside T009. | Who decided to publish; the release target is `develop` while the tag points at the `main` commit. | Accept alpha.1 as the T009 prerelease, noting that independent validation is still pending. |
| 7 | `archive-private-repository` | `jayanez/agent-braid-private-archive`: `archived: true`, `private: true`, last pushed 2026-09-19T13:02:53Z, last updated 2026-09-21T15:06:08Z (about 72 seconds after the release was published). Default branch `main`; branches include `develop`, `release/public-research-preview`. | Who archived it and exactly when (`updated_at` is only a proxy). | Accept the archived private repository as the T009 archive step. |

Time ordering from the API (2026-09-21): `main` head commit authored 15:03:58Z →
public repository created 15:04:33Z → tag 15:04:51Z → release published 15:04:56Z →
archive repository updated 15:06:08Z. The ordering is consistent with the planned sequence; it does not prove
authorization.

## 2a. Ratification sheet (one line per obligation)

For the owner to ratify or reject each line. Ratification is not recorded here.
"Delta vs audit" compares with `docs/releases/publication/CUTOVER_AUDIT_2026-09-25.md`.
`R` = `repos/jayanez/agent-braid`, `A` = `repos/jayanez/agent-braid-private-archive`.

| # | Obligation | Observed now | Exact evidence (read-only) | Delta vs 2026-09-25 audit |
|---|---|---|---|---|
| 1 | `rename-private-repository` | Archive repo id 1366735468, created 2026-09-11, differs from public id 1379980892 | `gh api A --jq '{id,created_at}'`; `gh api R --jq .id` | None; audit also could not establish rename authorship |
| 2 | `create-clean-public-repository` | Public, unarchived, default `develop`, single root `9b84467d` on all 7 branches | `gh repo view jayanez/agent-braid --json visibility,isArchived,defaultBranchRef`; `git log --max-parents=0` per fetched branch | None on state; flag P (root differs from founder-reviewed `4481ec6f`) was not in the audit |
| 3 | `push-clean-branches-and-tag` | `develop` `6f4870ea`, `main` `55d0e122`, annotated tag `v0.1.0-alpha.1` → `55d0e122` | `git ls-remote https://github.com/jayanez/agent-braid.git`; `gh api R/branches`; `gh api R/git/tags/99fbc39c…` | `develop` moved (normal work, plus 2026-10-13 force-push); `main` and tag unchanged; extra refs and tags now exist |
| 4 | `configure-rules-and-security` | 0 rulesets; classic protection on `develop`/`main`; secret scanning, push protection, Dependabot updates, vulnerability alerts on | `gh api R/rulesets`; `gh api R/branches/{develop,main}/protection`; `gh api R --jq .security_and_analysis`; `gh api R/vulnerability-alerts -i` | Same settings as audit; audit did not mention rulesets, required reviews or status checks (none required) |
| 5 | `change-visibility-to-public` | `PUBLIC` | `gh repo view jayanez/agent-braid --json visibility` | None |
| 6 | `publish-github-prerelease` | `v0.1.0-alpha.1` prerelease, published 2026-09-21T15:04:56Z, body `independent_validation: pending` | `gh api R/releases/tags/v0.1.0-alpha.1` | None; a later `0.1.0-alpha.2` prerelease (2026-10-27) now exists, outside T009 |
| 7 | `archive-private-repository` | `archived: true`, `private: true` | `gh api A --jq '{archived,private,updated_at}'` | None |

Net: no observed state contradicts the 2026-09-25 audit. The open items are
authorization and authorship (not observable), flag P, and the rules-versus-rulesets
reading in row 4.

## 3. Flags

- **P. Public root differs from the founder-reviewed candidate.** The review
  approved bounded local evidence for candidate root `4481ec6f` (tree `1e9868ca`).
  The public repository was published with root `9b84467d` (tree `33c76544`).
  Separate records describe later reproduction on `9b84467d` and two later
  repairs (restored history 2026-09-26, attribution correction 2026-10-13). A
  decision to close T009 should name the root it accepts, so the approval is not
  read as covering `4481ec6f`. The difference was anticipated by `evidence.json`
  `evidenceScope`; what is missing is a founder decision covering `9b84467d`, not
  a technical mapping.
- **Q. Later work on the same repository.** Releases, branches, tags and
  force-pushes after 2026-09-21 are not part of the 7 obligations. This record
  lists them but does not review them.

## 4. What closing T009 would additionally require

Not done here, and not implied by this record:

1. A founder decision per obligation, recorded in a repository file, bound to this
   reconciliation and to a named root (flag P). Visibility (row 5) and the others
   need explicit statements; none may be inferred from the observed state.
2. A follow-up PR that records those decisions, then updates
   `legacy-status-reconciliation.json` (`currentRemoteVerified` and dispositions)
   and checks T009 in `tasks.md`. Tracking files (`github-tracking.json`,
   `STATUS.md`, `ROADMAP.md`, `SPEC_MILESTONE_INDEX.md`) are out of scope for this
   record and untouched here.
3. Closing the parent milestone and issue only after (1) and (2); this record
   closes nothing.

## 5. Method and limits

Commands (read-only): `gh repo view` and `gh api` for `repos/jayanez/agent-braid`,
`…/branches`, `…/branches/{develop,main}/protection`, `…/tags`, `…/releases`,
`…/releases/tags/v0.1.0-alpha.1`, `…/git/tags/99fbc39c…`, `…/rulesets`,
`…/vulnerability-alerts`, `…/automated-security-fixes`, `…/commits/55d0e122…`,
`repos/jayanez/agent-braid-private-archive` and its `…/branches`;
`git ls-remote` for heads and tags; `git log --max-parents=0` per fetched branch.

Limits: a point-in-time read by one authenticated account; no audit-log access;
`updated_at` and `pushed_at` are proxies; this establishes current remote states
only, not who authorized or performed each operation, not continuous effectiveness
since cutover, and not independent validation, production safety or authority to
execute or integrate work.
