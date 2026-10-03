# SPEC-020: Bounded local Git runtime

## Purpose and scope

Turn immutable fixed-patch Git operations into a persistent, inspectable local
result under a separate execution authorization. This is the first engineering
increment of M4, independent of M3/M3.5. It does not close the entire M4 milestone.
The source repository is read-only. Execution writes only a newly allocated
private run directory, using serial Git plumbing and an isolated index. No
checkout, repository code, hooks, network service, external target ref promotion,
agent execution or parallel interleaving is admitted.

## Authorities

Constitution Articles 0, 2–7, 9, 12–16, 19–25; GOVERNANCE.md; ADRs 0008, 0013,
0014 and proposed ADR 0019. Existing M1/M2 contracts remain consultative and keep
`executionAuthorization: false`. A new runtime capability cannot be inferred
from an analysis classification or a certificate.

## Requirements and acceptance scenarios

- REQ-001: Accept only 2–4 distinct immutable commit operations derived from one
  immutable base, an explicit dependency-respecting serial order and complete
  declared changed-path sets. Limit to 16 changed paths, 256 KiB patch bytes,
  ordinary text A/M changes and a declared final tree. Reject unknown coverage,
  unsafe paths, binaries, symlinks, submodules, invalid dependencies and conflicting
  patches before allocating a persistent destination.
  - SC-001: A disjoint batch produces a manifest with per-step expected trees,
    patch hashes, identities, limits and a digest; source state is unchanged.
  - SC-002: Invalid or unsupported inputs fail closed with no run allocation.
- REQ-002: Separate preparation from execution. Bind authorization to the full
  prepared manifest, including canonical source and destination paths, base,
  commits, identities, order, effects, expected trees and contracts. Recompute
  it at use time; wrong, missing or stale authorization causes no durable write.
  - SC-003: A matching explicit digest authorizes only that local run; edited
    input, manifest or destination cannot reuse it. Destination must be new,
    outside the source (including its common Git directory), and not a symlink.
- REQ-003: Apply fixed patches serially to a private bare repository and index.
  Check actual path/mode/blob changes against the admitted effects and per-step
  expected tree. Create deterministic private checkpoint commits and use CAS to
  advance only the private result ref. Preserve source files, index and refs.
  - SC-004: The durable result has the declared tree and dependency order;
    hooks/configured external diff/filter/merge commands are never run.
- REQ-004: Persist a write-ahead state before each private ref transition.
  On recovery reconstruct the manifest and accept only the expected predecessor
  or successor of an interrupted transition. Resume without duplicating a
  completed step, or abort to the immutable base without deleting evidence.
  A POSIX advisory lock admits one coordinator. Seal manifest and initializing state in same-parent staging, then publish the directory atomically with exclusive no-replace rename (Darwin/Linux). Death before publication may leave unpublished staging but cannot reserve an unrecognizable run path. Other POSIX platforms fail closed at publication. Aborted runs cannot resume.
  - SC-005: Process death before/after a ref transition, interrupted abort,
    repeated resume and repeated abort preserve exactly one logical step per
    operation and recover the named private tree.
  - SC-006: Altered state/ref/tree, symlink artifacts and a concurrent owner are
    rejected, retaining evidence. Resource failures and cancellation stop Git
    children and retain a recoverable prefix, never report completion.
- REQ-005: A read-only consumer reconstructs the expected steps and checks the
  stored manifest, state, private commit graph and tracked trees; it reports
  verified-completed, verified-prefix or verified-aborted distinctly. Reports
  name the authorization scope and excluded effects. Expose prepare, execute,
  recover and verify via Python and CLI. Preserve existing command behavior.
  - SC-007: Verification rejects forged terminal results and altered evidence;
    independent CLI invocations reproduce completion and recovery.

## Scientific boundaries and compatibility

Observation: `runtime-private-tracked-tree-v1`; execution:
`authorized-serial-index-patch-v1`. Effects are Git path/mode/blob transitions,
private objects/ref/index and runtime metadata, not source-code semantic effects.
No live read/write footprints of arbitrary agents are inferred. Authorization
is a caller-supplied digest acknowledgement, not authentication or a signature.
The owned POSIX filesystem and installed Git are trusted; a hostile same-UID
writer, power-loss durability, physical quotas and hostile Git executables are
outside the tested boundary. Child memory is not hard-capped; temporary storage is sampled and can overshoot between checks. File fsync and directory fsync are used, but tested
recovery concerns process interruption. Index locks left by a killed owned Git
child are removed only under the coordinator lock after validating ownership.
M3 exchanges and M3.5 scores have no role in runtime admission.
New records use separate 0.1.0-alpha contracts. Runtime dependencies stay empty.

## Evidence and unresolved questions

Acceptance and negative tests plus a fresh-process reproduction bind observed
results to a candidate. Independent Luna review is separate from founder review.
ADR adoption and founder acceptance of the bounded increment remain explicit
human decisions after the concrete candidate is available. No M4-wide closure,
production safety, throughput improvement or scientific theorem is claimed.

## Alpha interfaces

Python: `prepare_run(request, run_directory) -> manifest`,
`execute_run(request, run_directory, authorization) -> report`,
`recover_run(request, run_directory, authorization, action="resume") -> report`,
`verify_run(request, run_directory) -> report`. Execution/recovery optionally
accept a threading cancellation event. Preparation accepts it as well.
CLI: `prepare-git-run`, `execute-git-run`, `recover-git-run`, `verify-git-run`
accept a request JSON file and required `--run-directory`; execute/recover require
`--authorize` with the prepared manifest digest; recovery also requires
`--action resume|abort`. Output is JSON. Exit 0 is success, 2 rejects input,
authority or private state, 3 is infrastructure failure/cancellation. The report
names completed operations, private result commit/tree, phase, digest, contracts,
private-only authorization scope and explicit sourcePromotion false. A verifier
reports verified-completed, verified-prefix or verified-aborted; prefixes are
not completions. Input error messages do not grant authority.

Commit derivation uses SHA-1 Git objects with exact UTF-8 canonical-JSON message
`{"executionContract": EXECUTION, "operation": operation}` plus a newline,
one prior checkpoint parent, the observed tree, author and committer
`Agent Braid local runtime <runtime@example.invalid>`, and both dates
`2000-01-01T00:00:00+00:00`. Operation records include instance/attempt identity,
source commit, dependencies and declared writes. No inherited Git identity,
signing, encoding or commit-message hook is used. Nonempty dependencies are
supported and must precede their consumers in the acknowledged serial order.
