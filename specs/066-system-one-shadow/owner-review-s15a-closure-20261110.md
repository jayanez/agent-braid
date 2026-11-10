# SPEC-066 owner decision: S1.5a closure and S1.5b start, 2026-11-10

Evidence for T032. The owner (jayanez, founder) answered the questions below directly
in the Claude Code coordinator session on 2026-11-10, through interactive prompts.
The answers are recorded verbatim; the session transcript is not stored in the
repository. This is the owner's closure decision. It is not a scientific finding, an
independent technical review, or evidence that any hypothesis holds.

## What the owner reviewed

The S1.5a evidence now in `assurance.json`, every item byte-bound by SHA-256:

| Evidence | What it shows | What it does not show |
|---|---|---|
| `evidence/real-use-shadow-2026-11-09.json` (T030, SC-006) | One owner, shadow week 2026-11-02 to 2026-11-09: 25 episodes on 5 dates, 142 pairs (conflicting 1, independent-candidate 21, ordered 81, unknown 39), DP-1 opportunity share 0.274648, all 25 episodes abstained, no invalid store lines. Counts only. | Accuracy, calibration or utility of System One. The reference backend always abstains. |
| `evidence/overhead-20261107.json` (T021, SC-003) | Worker step median 2.0 to 6.5 ms, p95 2.7 to 7.3 ms on one machine; request-path hand-off at most 0.024 ms p95. A receipt, not a gate. | A bound on any other machine or a stalled filesystem. |
| `evidence/s15a-local-tests-20261110.json` (SC-001 to SC-005, SC-007 to SC-010) | The named scenario tests and the 105-test module run pass at develop `0cb79302`. | The CI `pr` profile (that is the CI `validate` aggregate on the pull request head), independent review, or any scientific claim. |

Reviews of T010 to T022 are in `reviews/T031-r1-20261107.md` (automated same-family
passes, no approval). Disposition of its open minor findings, recorded with this
decision:

| Finding | Disposition |
|---|---|
| R1-04 budget check wording | Kept as built; the plan wording stays as is. The episode is `skipped` and the request path never waits (OD-4). To be reconsidered by the S1.5b plan if it matters. |
| R1-05 `internal-error` versus `unavailable` | Open; carried to the S1.5b plan. No behaviour change in S1.5a. |
| R1-06 validation plan wording and commands | Fixed in this change (`validation-plan.md`). |
| R1-07 assurance still named v0.1 and had no obtained evidence | Fixed in this change (`assurance.json`). |
| R1-08 fixtures directory not created | Recorded in the `tasks.md` preamble: fixtures are built in the test module. |
| R1-09 POSIX-only store | Open; platform limits are taken up by SPEC-069 T014 (REQ-014). |

## Owner decision (T032)

| # | Question (summary) | Owner's answer (verbatim) | Effect |
|---|---|---|---|
| D1 | Close S1.5a and decide whether S1.5b starts (T032) | "Cerrar y arrancar S1.5b (Recommended)" | S1.5a is closed. S1.5b may start. |

Date: 2026-11-10. The same session also recorded the T101 corpus consent in
`evidence/owner-consent-s15b-corpus-20261110.json` (separate change).

## Bounds of this decision

- It closes S1.5a. It does not approve any S1.5b implementation: T102, T103 and T106
  need their own S1.5b plan and review, as `tasks.md` already states.
- It grants no execution authority (`executionAuthorization` stays `false`), no
  promotion to `advise`, no calibration and no utility claim. H-S1 is untested.
- Owner approval of the frozen record is not yet in `assurance.json`:
  `human_review` stays `pending` because approval is valid only against a frozen
  historical commit (docs/development/SPEC_KIT.md). The freeze packet below finishes
  that step after this change merges.

## Freeze packet (run after this change is merged to `develop`)

Same practice as SPEC-061 (#1020) and SPEC-069 (#1147): the candidate merges first,
then a freeze and record change at a `develop` commit. Nothing here needs a secret or
the owner's hands; any agent can run it.

1. `git clone --no-local <repo> <fresh-dir>` and check out the `develop` commit that
   contains this change. Do not prune the shared worktree.
2. In the clone: `python3 -m scripts.validate_spec_kit freeze specs/066-system-one-shadow`.
   This sets `authority_snapshot` and `evidence_snapshot` to `historical` at that
   commit `X` and keeps `human_review` `pending`.
3. Add `specs/066-system-one-shadow/owner-review-s15a-closure-20261110.json`
   (schema `agent-braid-bounded-founder-review-v1`, as in
   `specs/061-activity-viewer/owner-review-vis1a-closure-20261103.json`) with
   `reviewedCommit` and `evidenceCommit` set to `X`, `decision` `accepted`, scope
   "SPEC-066 S1.5a closure only", the verbatim answer D1 above, the three receipt
   hashes of the table above, and `notAccepted` listing: any S1.5b implementation,
   promotion or calibration, any utility or accuracy claim, release or publication.
4. Set `human_review` to `approved` and `review_record` to that JSON in
   `assurance.json`, then run `python3 -m scripts.validate_spec_kit` in the clone.
5. Tick T005 and T032 in `tasks.md` with the commit and PR, in the same change.
6. Open the freeze and record change against `develop`; CI on its head is the `pr`
   evidence.

If a step fails for a reason that needs the founder (for example a decision the
validator cannot take), stop and report; do not edit hashes by hand.
