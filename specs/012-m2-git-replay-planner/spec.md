# Feature specification: bounded Git replay and consultative planning

## Purpose and scope

Provide a deterministic local experiment for a small batch of immutable Git
commits. Replay every admissible topological order from one base tree, record
tree observations, and produce an advisory preparation plan. This is an
engineering and bounded research feature within M2.

The feature accepts 2–4 commit sources, no more than 64 changed paths, and at
most 1 MiB of aggregate binary diffs. It uses no checkout, worktree source,
project test command, network access, or external effect. The repository remains
unchanged. The cut does not implement partial-order reduction, patch minimization,
provider adapters, or concurrent execution.

## Authorities

The feature follows constitutional clause zero and Articles 2, 4, 6, 7, 9,
12–14, 19–21, 23–25. Applicable authorities include `ROADMAP.md`,
`docs/adr/0008-read-only-git-worktree-adapter.md`,
`docs/theory/OPERATIONAL_SEMANTICS.md`,
`docs/architecture/DRAFT_0_2.md`, and the M1 Git request/provenance schemas.
ADR 0013 records the replay and advisory-planning boundary.

## Requirements and acceptance scenarios

- **REQ-001 — bounded immutable input.** Accept only a valid M1-shaped Git
  request with 2–4 unique operations whose source commits descend from the same
  resolved base. Enforce path and aggregate diff bounds. Reject malformed,
  oversized, missing, unrelated, or unavailable commit inputs.
  - **SC-001:** A valid two-commit request resolves stable commit IDs and emits
    replay evidence.
  - **SC-002:** A worktree, five-operation batch, invalid dependency graph,
    unavailable commit, or oversized diff is rejected or retained as unknown
    according to the input failure category; it never emits candidate waves.
- **REQ-002 — isolated exhaustive replay.** Reconstruct each base-to-commit
  patch, enumerate every topological order, and apply each order in a fresh
  temporary bare repository/index. Observe the Git tracked tree under
  `tracked-tree-v1`. No source repository files, refs, index, or objects may
  change.
  - **SC-003:** Disjoint patches and different-hunk edits replay in every order
    and produce the same tree.
  - **SC-004:** Overlapping patches that apply to different final trees produce
    `divergent`; an order that fails to apply makes the result `inconclusive`.
- **REQ-003 — evidence and independent verification.** Emit a versioned evidence
  bundle bound to repository identity, base/source commits, dependencies, patch
  digests, observation/execution contracts, and every enumerated schedule.
  `verify-git` must reconstruct and replay all schedules without trusting the
  producer's verdict. Missing schedules, altered fields/digests, wrong tree
  observations, and unavailable objects are rejected or unverified, never
  silently accepted.
  - **SC-005:** A valid bundle verifies with the original repository; modified
    evidence and omitted/duplicated schedules fail verification.
- **REQ-004 — conservative advisory plan.** Produce dependency waves only when
  verification succeeds, every schedule completes with the same tracked tree,
  and every operation is eligible. Otherwise produce a deterministic serial
  fallback when that order applies; if it does not, require manual review.
  Every plan includes conditions, limits, and `executionAuthorization: false`.
  - **SC-006:** A supported three-commit equivalent batch yields one advisory
    wave; dependencies preserve their order.
  - **SC-007:** Uncertain, unsupported, divergent, or inconclusive inputs never
    yield candidate waves; a failed serial fallback requires manual review.
- **REQ-005 — measurable bounded comparison.** Compare the planner with serial,
  path-overlap, and Git merge baselines on a committed synthetic corpus. Report
  replay outcomes, wave count, wall time, command count, and false-candidate
  count. The benchmark claim is restricted to the fixed-patch tracked-tree model.
  - **SC-008:** The corpus has zero candidate waves with divergent/incomplete
    replay, one three-operation case reduces the plan from three serial waves to
    one candidate wave, and the distinct-hunk case improves over path-overlap.
    If these thresholds fail, record the negative result and keep M2 open.

## Scientific boundaries and compatibility

The result concerns only fixed patches from the named commits and the
`tracked-tree-v1` observation. It does not establish source-code correctness,
hidden semantic independence, contextual equivalence, arbitrary interleaving
safety, general confluence, or runtime authorization. A candidate wave is a
review aid for preparation planning; integration remains serial.

Existing AIM, analysis-report, Git request/provenance, and 0.2.0-draft
certificate contracts remain unchanged. New replay-evidence and plan records use
their own `0.1.0-alpha` contracts. The runtime remains standard-library-only
and requires local Git.

## Evidence and review

Acceptance tests bind each requirement to a scenario and actual command output.
Evidence is captured only after a stable implementation candidate. Human review,
clean-room reproduction, and any M2 closure decision remain separate gates.
