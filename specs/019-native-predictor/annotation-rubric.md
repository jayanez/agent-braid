# SPEC-019 proposed human utility rubric

**Status:** candidate for review before any utility labels are collected. A
human judgment here is a proxy for possible reviewer benefit. It is not an
observation of time saved, a conflict prevented, semantic commutation or an
execution certificate.

Each reviewer sees the original editing context, the two proposed pure
inserts and a standardized question: would a correct bounded answer about
their order help with a documented decision or review step? They judge the
need for advice, not whether the specific pair will verify. The interface
hides model scores, baseline priority, split name, other reviewers' judgments
and the verifier verdict. The original source event and its hash remain
available for audit. Reviewers must cite the source context and the specific
decision their answer concerns.

## Two separate dimensions

1. **Decision aid:** `yes` only if the source shows a concrete manual choice
   about the order of these two edits and displaying the bounded exchange
   analysis would resolve that choice. `no` means there is no such choice or
   the advice would not resolve it. Missing context is `unknown`.
2. **Conflict-review aid:** `yes` only if the source documents an actual
   conflict-review task about the order of these same edits and the bounded
   advice would remove that specific review step. `no` means the task is absent
   or the advice does not address it. Missing context is `unknown`. This is
   never coded as an observed conflict avoided outside the M3 model.

The primary **assessed-usefulness** label is positive if either dimension is
`yes`, negative only if both are `no`, and otherwise unknown. Record the two
dimensions separately so a positive composite can always be explained.
For example, a source showing a reviewer choosing the order of two supported
same-base inserts could support `decision aid=yes`; two already ordered edits
with no pending review give `no/no`; a final patch without the editor's
decision context gives `unknown`, even if its M3 replay verifies.

Two independent, blinded reviewers label both dimensions for every admitted
pair, including every holdout pair, regardless of either policy's ranking.
When they disagree, a third blinded reviewer adjudicates using the frozen
rubric and records a rationale. A remaining disagreement or missing context
stays unknown. Store pseudonymous reviewer IDs, timestamps, raw labels,
adjudicated labels, source hashes and reasons. Report pre-adjudication
disagreement counts and rates per dimension and per workload family, as well
as adjudication and unresolved rates. Do not convert unknowns to negatives.

Freeze this rubric, its example cases and reviewer instructions before
opening any source labels. Example cases must come from an approved source or
be explicitly marked synthetic; they cannot be treated as workload evidence.
A change after labeling requires a new version and
fresh review; do not relabel the existing holdout to rescue a result.
