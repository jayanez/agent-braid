# Proposed parallel integration contract

**Status:** accepted for the bounded T013 prototype on 2026-09-24; it is not an execution authorization.

This contract defines a narrow next experiment for integrating immutable Git
commit results. It is separate from `tracked-tree-v1`: equal replay trees for
fixed base-to-commit patches do not establish that live agents, tests, hooks,
tools, or external effects are safe to run concurrently. The analyzer may
produce evidence and consultative plans; a future coordinator must enforce this
contract at execution time.

## State and isolation

- Name one immutable target base commit and tree. Pin each operation's source
  commit, attempt identity, dependency set, and declared read, write, and shared
  resource footprint. Missing, wildcard, or unbounded footprints are unknown.
- Give each operation a private worktree and index rooted at the same base.
  Agents may not write the integration ref, another operation's worktree, the
  common index, shared caches, or other undeclared mutable resources.
- Keep credentials, network access, hooks, submodules, filters, and arbitrary
  project commands disabled unless a later reviewed execution profile names
  their capability, resource budget, and observation contract explicitly.
- Apply global bounds before launch: operation count, wall time, CPU/memory,
  process count, output bytes, temporary disk, and cancellation cleanup. A
  resource-limit breach is a failed attempt, never evidence of a conflict-free
  result.

## Admission, dependencies, and stale inputs

- Admit only operations with verified identity, complete footprint, and a
  dependency DAG. A dependency must finish and pass its declared checks before
  its dependent can start.
- A parallel wave may contain only operations whose declared writes do not
  overlap another member's reads or writes, and whose shared-resource claims
  have an explicit concurrency policy. Path-disjointness alone is insufficient
  for undeclared build, test, generated-file, or external resources.
- Bind each attempt and result to the base commit, relevant input versions,
  contract version, and policy digest. Before integration, recheck that the
  target ref still equals the pinned base and that every precondition remains
  true. A changed ref or input invalidates the wave; replan or stop.

## Integration and verification

- Agents never update the shared target ref. A single coordinator serializes
  promotion of results. It computes a candidate combined tree in a private
  integration area; the existing worktree and ref remain unchanged while
  validation runs.
- Treat merge conflicts, overlapping undeclared effects, failed checks, missing
  results, cancellation, and non-deterministic checks as abort conditions. Do
  not resolve conflicts automatically in the first prototype.
- Verify source and dependency identities, operation completion, the resulting
  tracked tree, declared checks, and the base-ref compare-and-swap condition.
  Only after all checks pass may an explicitly configured coordinator promote
  the candidate result. A read-only prototype must stop before promotion.
- Preserve the original target ref and all attempt records until promotion is
  verified. On any pre-promotion failure, discard only private scratch state.
  If a later promotion mechanism can partially fail, it needs a separately
  specified atomicity and recovery protocol; compensating commits are not an
  exact rollback.

## Prototype and falsification plan

The gated T013 prototype should be a local, read-only coordinator experiment:
create isolated worktrees for 2–4 deterministic fixture operations, execute
only a pinned allowlist of fixture commands, collect declared footprints,
compute the combined tree in private scratch, and compare with a serial
reference run from the same base. It must never promote a ref or run arbitrary
repository code. Use barriers to force overlap and stale-base changes. Include
disjoint success, read/write race, write/write conflict, undeclared resource,
dependency ordering, stale base, timeout/output/disk exhaustion, cancellation,
failed check, and coordinator restart cases.

Report serial and candidate wall time, CPU, peak memory, scratch usage, Git
command/process counts, rejected unsafe waves, false admissions, false
rejections, and exact reproduction commands. Acceptance requires zero unsafe
admissions in the corpus and agreement with the serial reference for every
admitted case. Any mismatch or missing trace fails closed. A positive speedup
is useful only after those correctness gates pass. Results remain bounded
empirical evidence and cannot widen execution authority.

This proposal implements the boundary required by Constitution Articles 6 and
12 and the measurable-workload requirement of Article 19. It does not claim
semantic independence from Git trees or authorize execution. Human review of
this contract is a prerequisite to implementing T013.
