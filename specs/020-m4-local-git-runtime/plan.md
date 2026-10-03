# Implementation plan

## Technical context and scope

Python >=3.12 standard library; local SHA-1 Git; POSIX advisory filesystem lock.
Persistent private bare Git repository with explicit index; no materialized code.

## Constitution check before research

Articles 6/12 require isolated serial transitions and stable preconditions;
7/13/14 require separate prepare, authorization, execution, trace and verifier;
19/20 require useful durable results without changing the analyzer authority.
No constitutional amendment or broader execution claim is proposed.

## Research, assumptions and alternatives

Use the existing read-only Git provenance extractor, patch hashing, sanitized
Git environment and bounded process runner. Memory is not hard-capped: macOS RLIMIT_AS enforcement failed during initial validation, so the new explicit contract exposes null rather than silently falling back. Read-only M2 prototype alone lacks
persistent authorization/recovery. An arbitrary shell-command runtime is deferred
because the current isolation does not enforce its effects. Direct source ref
promotion is deferred because CAS on a ref alone does not protect worktrees.

## Design and compatibility

A runtime request extends the existing Git analysis envelope with order,
declaredWrites per operation and expectedFinalTree. Prepare recomputes provenance,
rejects unsupported modes and effects and serially rehearses in temporary storage.
A manifest binds canonical paths, request, patches and deterministic checkpoints.
Execute recomputes this manifest and compares the explicit acknowledgement digest
before sealing a 0700 staging directory and atomically publishing it with Darwin renamex_np RENAME_EXCL or Linux renameat2 RENAME_NOREPLACE. Existing destinations, even empty ones, are never replaced. Store manifest.json, state.json,
coordinator.lock, home/ and result.git/. Maintain refs/heads/result and a private
index. Atomic JSON replace plus fsync writes an applying intent before CAS and
ready/completed after it. Recovery reconciles only that single pending CAS.
Aborting uses its own write-ahead state then CAS back to base and read-tree reset.
Each Git child inherits the lock FD; a killed coordinator cannot be replaced while an old child remains alive. The OS releases the lock after the last holder exits. Recovery never trusts the stored
manifest as authority and never executes repository code. The verifier reads
state and Git objects under the lock, reconstructs expected trees/commits, and
makes no index/ref/state changes. Existing APIs and schemas are untouched.

## Validation strategy

Use discovered unittest cases mapping REQ/SC to deterministic local Git fixtures,
full source-file/index/ref before/after checks, real subprocess crashes at journal
boundaries, concurrency exclusion, tampering, cancellation and resource budgets.
Run quick proportional validation after coherent edits and PR once when stable.
A separate reproduction script runs focused checks in fresh Python processes and
records candidate, Git/Python/platform, command outcomes and content hashes.

## Constitution check after design

Execution authorization is limited to one explicit destination and batch;
terminal tree agreement supplies no concurrency permission. Private rollback
undoes only owned Git state and cannot compensate external effects. The trace
covers this fixed-patch consumer, not arbitrary agents or live application state.

## Human review and unresolved decisions

Proposed ADR 0019 and the bounded runtime candidate require explicit founder
acceptance. No generated evidence or agent review records that acceptance.

The new ADR/schema inventory requires refreshing the current draft authority
snapshots of SPEC-011 and SPEC-019. Both remain human-review pending; their
existing evidence and historical reviewed decisions are unchanged. No adoption
or predictor review is inferred from this inventory refresh.

The approved M2 retest binds the shared git_process.py bytes. Leave that file
unchanged and use a separately reviewed M4-owned process-runner variant that
inherits the coordinator lock FD. This avoids retroactively changing M2 evidence
or extending its approval to the new runtime.
