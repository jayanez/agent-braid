# Bounded Git replay and preparation plan

**Status:** experimental, M2 first cut. See [ADR 0013](../adr/0013-isolated-git-replay-and-advisory-planning.md).

`plan-git` consumes the existing Git analysis request and supports 2–4 immutable
commit sources descended from one base. The request, changed paths and aggregate
diff are bounded before replay. Worktrees, uncertain paths, binary/destructive
changes and unsupported Git modes cannot produce candidate waves.

Each operation is the fixed binary diff from the common base to its source
commit. The implementation enumerates all topological orders, fetches the
resolved objects into a temporary bare repository using local file transport,
and applies each schedule to a fresh index. It does not checkout a working tree
or execute project code. The source repository's refs, index, files and object
database remain untouched.

The `tracked-tree-v1` observation is the final Git tree object for a complete
schedule. It covers tracked paths, modes and blob identities. It excludes
untracked/ignored content, build/test results, runtime effects and semantic
dependencies. A complete tree mismatch is `divergent`; an apply failure is
`inconclusive`.

The evidence verifier repeats the full bounded replay. It rejects missing or
duplicate schedules, altered inputs, patch digests, tree IDs or producer
verdicts. `verified` means only that the declared finite replay was reproduced.
The independent `verify-plan` command repeats evidence verification and
regenerates the deterministic plan; a digest alone cannot validate a modified
wave list or a plan bound to different evidence.

Git subprocesses share limits across M1 provenance and each evidence replay:
120 seconds, 512 commands, 16 MiB of captured output, 8 MiB per command, and
64 MiB of temporary data. Output is drained as it is produced. Temporary data
is sampled during a command every 50 ms and checked at command boundaries, so
one in-flight write can overshoot the cap before termination. Git child-process
RSS is not hard-limited. A timeout, output, scratch, command-count or
process-start failure is reported as an infrastructure failure, distinct from
a rejected patch. These controls bound this local Git experiment; they are not
a general sandbox for project code.

Plans are advisory. Candidate preparation waves require verified, complete,
equivalent evidence and supported/certain operations. The planner never applies
changes to the caller's repository and always emits `executionAuthorization:
false`. Other verified outcomes may receive a deterministic serial fallback
when the selected order replays; unverified evidence requires manual review.

This cut does not establish semantic commutation, source-code correctness,
contextual equivalence, arbitrary interleaving safety or production safety.
M2 remains open for reduction, broader replay adapters and any future execution
contract. See the proposed [parallel integration contract](PARALLEL_INTEGRATION.md)
and [ADR 0014](../adr/0014-parallel-integration-contract.md); the contract
requires human review before the gated prototype starts.
