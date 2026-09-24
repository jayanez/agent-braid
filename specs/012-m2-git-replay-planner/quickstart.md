# Quickstart

Prepare a JSON request using the existing M1 Git request shape, with two to
four immutable commit sources descending from one base. Each operation has
`instanceId`, `attemptId`, `source`, `dependencies`, and `uncertainPaths`.

Generate evidence and a consultative plan:

```sh
agent-braid plan-git request.json --evidence-output replay-evidence.json
```

Independently replay and verify every recorded order against the local source
repository:

```sh
agent-braid verify-git replay-evidence.json --repository /path/to/repository
```

Verify a saved advisory plan against the evidence and repository. The verifier
independently replays the evidence and regenerates the expected plan:

```sh
agent-braid verify-plan plan.json --evidence replay-evidence.json \
  --repository /path/to/repository
```

Use a preparation wave only as planning input for human review. Integration
remains serial, and both evidence and plan always carry
`executionAuthorization: false`. Stop at the emitted serial or manual-review
fallback if no verified candidate wave is produced.

## T013 local prototype

The prototype accepts a separate request with a pinned `baseRevision`, a local
`targetRef` that must still point to that base, and 2–4 operations. Each
operation uses the immutable `source` commit and declares `dependencies`, exact
`reads` and `writes`, `sharedResources`, and `footprintComplete`. Unknown or
wildcard footprints stop for manual review. The source commits must satisfy the
same M1 ancestry and patch rules as `plan-git`. An optional `expectedFinalTree`
pins one full Git tree ID as an additional tracked-tree check. If it is declared
and does not match the candidate and serial result, the report is inconclusive
even when those two results match each other. This check runs no project code.

Run the prototype with an explicit output path:

```sh
agent-braid prototype-git integration-request.json \
  --report-output integration-report.json
```

The CLI replaces the report file atomically. Exit code 0 means it wrote a
report; inspect `status`, `comparison` and `declaredTrackedTreeCheck` before
using any result. All reports keep `executionAuthorization: false`.

The candidate concurrently prepares fixed patches in separate temporary
worktree indexes, with at most two Git workers. It then serially combines
synthetic operation trees with `git merge-tree` and compares the result with a
serial preparation and integration run. It runs no repository code, tests,
hooks, agents, or network actions, and never promotes a ref. The report binds
the commit and patch digests, declared footprints, observed trees, resource
limits, comparison, and `executionAuthorization: false`. It is a local
engineering experiment, not permission to execute operations concurrently.
On SIGINT or SIGTERM, the CLI cancels its in-flight Git child and removes its
private temporary directory. A later invocation starts a fresh read-only replay;
this is not persistent coordinator recovery after an uncatchable crash.
The production command requires an operating system that can enforce the
configured per-child `RLIMIT_AS` cap. If the host cannot apply it, the command
returns an infrastructure failure and produces no report; it does not fall
back to an unbounded Git child.

### Linux resource validation on macOS

macOS may reject the 512 MiB `RLIMIT_AS` requested by the prototype. Use the pinned
Docker runtime to validate the production profile on Linux without changing the
host checkout:

```sh
sh scripts/docker/t013/build-image.sh
sh scripts/docker/t013/run-validation.sh t013
```

The image pins Python 3.12 by base-image digest, Debian packages and transitive
Python dependencies with local lock files, and the Spec Kit dependency by the
repository's immutable commit. Image construction downloads those dependencies.
The validation container itself has no network, a
read-only root filesystem, read-only mounts for the checkout and its common Git
directory, a 2 GiB container memory cap, two CPUs, a 512-task cap, and a 512 MiB
temporary filesystem. A mandatory preflight checks that a child actually observes
both soft and hard `RLIMIT_AS` values of 512 MiB and successfully runs Git through
the production process wrapper. If the limit is unavailable, the container gate
fails before reporting success.

The T013 mode runs the production-profile regression suite and the fixed synthetic
benchmark. It writes `t013-benchmark.json` to a temporary artifact directory and
prints that directory at the end. Pass a second argument to choose a persistent
artifact directory. `quick` and `pr` modes run the corresponding repository
validation profiles under the same read-only, no-network container policy:

```sh
sh scripts/docker/t013/run-validation.sh quick
sh scripts/docker/t013/run-validation.sh pr
```

The Docker 2 GiB container memory cap bounds the whole container. It is separate
from the prototype's per-Git-child 512 MiB `RLIMIT_AS`; both are checked or set
independently. This environment validates the bounded local prototype only. It
does not authorize result promotion, execution of project operations in parallel,
or M2 closure.
