# Proposed founder decision: M2 real-corpus performance retest

**Status:** Proposed. No new real-corpus run or repository-code command is
authorized by this document. The exact machine-readable inputs are in
[m2-real-corpus-retest-inputs.json](m2-real-corpus-retest-inputs.json).

## Decision requested

Accept or reject one new ADR 0015 experiment using the exact frozen corpus,
candidate implementation, timed path-overlap baseline, image, dependency
bytes, command, limits and observation protocol below. Acceptance would
authorize implementing the fail-closed retest harness and then running it
only after its fresh read-only preflight passes. It would not revise the
negative T003 result, merge a PR, authorize execution beyond the experiment,
establish external validation or close M2.

## Why a new decision is needed

The founder accepted the [T006 review](../../specs/013-m2-real-workload/t006-founder-review.json)
at `60d6bcaba7245e9864298321b1038cddfde6fd9e`: the two completed
real-corpus runs showed no speedup. The follow-up [PR #140](https://github.com/jayanez/agent-braid/pull/140)
changes the prototype and its Git process polling. The original T003 runner
rejects that code by hash. The two 30-pair synthetic shape-proxy batches in
[the performance report](M2_PARALLEL_PREPARATION.md) exceed 10% versus serial
and the timed path baseline, but do not reproduce the real corpus's content,
Git history or patch hunks. They are engineering evidence, not an ADR 0015
execution or a positive real-corpus result.

## Immutable inputs and comparison

- Repository and target: `jayanez/agent-braid`, `refs/heads/develop` at
  `f3c734a1f42d6d5962cfedc57d7f6c1efe40e0a6`.
- Workstreams: [PR #137](https://github.com/jayanez/agent-braid/pull/137)
  at `58351f812614058e53a8ee6aef1dd458f1bb70fc` and
  [PR #138](https://github.com/jayanez/agent-braid/pull/138) at
  `083f1a390988a9527a5aaeb19133401243b1d714`, with no dependencies.
  The [manifest](../../specs/013-m2-real-workload/m2-corpus-manifest.json)
  and [selection](../../specs/013-m2-real-workload/m2-corpus-selection.json)
  must retain the SHA-256 values in the input proposal.
- Candidate: PR #140 code commit `7d1a07775c2663da93e369ceccf5a8b352c28e78`.
  The prototype, Git process helper and benchmark script hashes in the input
  proposal bind the 1 ms poll and measurement implementation. Candidate and
  equally optimized serial preparation use the same code and poll interval.
- Timed path baseline: the byte-verified T003 prototype module from
  `60d6bcaba7245e9864298321b1038cddfde6fd9e`, with the conservative
  tracked-write overlap scheduler and the bound Git process helper's 10 ms
  default poll. This baseline runs the same real corpus and records elapsed
  Git lane time, rather than only a wave count.
- Accepted profile: [ADR 0015](../adr/0015-real-repository-validation-profile.md),
  Linux ARM64 image
  `sha256:edddb1cbcbccb0e1af6505f9ff9938905da6f79303c97d1d12092ef61508f005`,
  and the five exact dependency-file hashes in the input proposal.

## Observation and fail-closed gates

Run two independent batches of 30 **paired Git-only samples** in the pinned,
offline container. Alternate current versus path-baseline process order and
candidate versus serial lane order within each batch. Keep every raw timing,
tree, source-state, command-count and resource observation. In every pair,
candidate, serial and path-baseline trees must match, the local source state
must remain unchanged, all lanes must complete, and unsafe admissions must be
zero. The host must verify live remote refs before and after each offline
batch. For each batch and for both baselines, require a median paired
fractional improvement of at least 10% and a seeded 10,000-resample bootstrap
95% interval with lower bound above zero. Report any failure as a negative or
inconclusive result, not as a performance gain.

After the Git checks pass, materialize the verified candidate and serial trees
in separate private containers for two clean-room pairs. In each lane, run
only `python -m unittest discover -s tests` once. Both lanes must pass the same
declared tests and retain the tracked tree. Use the same image and dependency
bytes, no network, hooks, credentials, source-repository writes or ref updates.
Only the designated evidence artifact directory may receive host output. Cap
each container at two CPUs, 2 GiB, 512 processes, 180 seconds and 8 MiB
captured output. Preserve timeout, output truncation, test failure, stale base,
missing inputs and hidden effects as inconclusive or rejected outcomes.

Before any execution, a fresh preflight must verify the exact code and corpus
commits, PR branch heads, `origin/develop`, manifest, footprint declarations,
image and dependency hashes. It must also exercise negative controls for a
moved base, substituted commit, duplicate PR, undeclared write, changed code
hash and breached resource limit. The accepted T003 runner must continue to
reject changed prototype bytes; the new harness must require a separate,
byte-bound founder decision record for this proposal and input file.

## Limits

The [current read-only preflight](evidence/m2-real-corpus-retest-proposal-preflight.json)
is a preparation snapshot;
they must be repeated immediately before any authorized run. Static tracked
paths and finite test outcomes cannot establish all runtime effects,
semantic equivalence, general confluence or live-agent safety. The path-only
and candidate schedulers currently form the same wave on this corpus, so a
gain against the path baseline would reflect implementation cost, not a
scheduling advantage. External human validation and M2 closure remain
separate decisions.
