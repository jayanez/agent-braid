# M1 closure record

**Status:** closed by explicit founder decision

**Decision date:** 2026-09-18

The founder separately approved the final bounded scientific review and M1
closure against candidate `fa958277bd919c827e781df63d8371afd6f111c9`.
The review binds the internal Python 3.12.14 reproduction, corrected Git adapter
evidence, validation-record `0.2.0` evidence, full-history Spec Kit integration
and the approved bounded M1 milestone-radar review. It remains founder-led
internal review, not independent validation.

## What the final candidate established

- deterministic conservative analysis of declared AIM operations;
- an experimental read-only Git/worktree adapter with explicit provenance;
- nine software and six Git scenarios with zero false-safe candidates relative
  to their declared finite ground truth;
- explicit version validation at the point of use for the condition-bound case;
- measured file-overlap and Git merge baselines, each permitting three cases
  that Agent Braid conservatively orders or leaves unknown;
- a Python 3.12.14 clean-room run in a fresh clone and environment with 14/14
  successful observations, 94 tests and clean initial and final repository state;
- an approved offline M1 milestone-radar review that promotes no signal to
  implementation and makes no exhaustive-freshness claim;
- pinned Spec Kit rendering and structural Codex-only, Claude-only and dual
  integration checks in temporary repositories retaining full Git history;
- complete-tree freeze protection that rejects authority, implementation or
  other non-record changes after review.

The [founder review](../../specs/007-m1-closure/founder-review.json),
[reproduction artifact](../../specs/007-m1-closure/reproduction.json) and
[validation status](records/M1.json) preserve the evidence and decision boundary.

## What M1 does not establish

- production safety, authorization to execute concurrently or permission to
  merge Git changes;
- complete discovery of hidden or semantic dependencies;
- general confluence, contextual equivalence or adapter correctness outside the
  tested domain;
- a general Yang–Baxter result;
- external validation, which remains `pending` and publicly invited.

## Corrective history

The first closure decision applied only to candidate
`f8c21ffc7ebb5bce5be1d8df321d3d7040903621`. Review findings reopened M1,
invalidated that decision for subsequent implementation changes and required a
new freeze, reproduction, technical policy review and separate founder decisions.
Git history preserves the earlier artifacts without extending their claim to the
corrected candidate.

The second closure decision applied only to candidate
`3a2e0c439a2c927ea624433c087b6f0de96e1764`. A later complete integration run
found that the Spec Kit fixture discarded Git history. That correction changes a
non-record path, so the freeze gate correctly requires a new candidate,
reproduction and founder review rather than extending the earlier decision.

The third closure decision applied only to candidate
`fa3c9e66a7b1feea7e091d5e2be960a308f7ac9e`. The subsequent complete matrix
correctly rejected closure because the mandatory M1 milestone-radar review was
absent. Its implementation and scientific evidence remain historical; they are
not silently extended to a replacement candidate.

M1 closure is not a package release or repository-visibility decision. M0.5
strategy review and any research-preview proposal remain separate work.
