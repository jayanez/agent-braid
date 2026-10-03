# Bounded local runtime quickstart

A request follows the existing Git analysis shape (full immutable commit IDs,
2–4 operations) plus `gitRuntimeRequestVersion: "0.1.0-alpha"` instead of the
analysis version, `order`, `declaredWrites` on each operation and
`expectedFinalTree`. Each `uncertainPaths` must be empty. Choose a new run
directory outside the source and its Git storage, with an existing parent.

```sh
python -m agent_braid prepare-git-run request.json --run-directory /tmp/new-run
python -m agent_braid execute-git-run request.json --run-directory /tmp/new-run --authorize sha256:THE_REVIEWED_MANIFEST_DIGEST
python -m agent_braid verify-git-run request.json --run-directory /tmp/new-run
python -m agent_braid recover-git-run request.json --run-directory /tmp/new-run --authorize sha256:THE_REVIEWED_MANIFEST_DIGEST --action resume
python -m agent_braid recover-git-run request.json --run-directory /tmp/new-run --authorize sha256:THE_REVIEWED_MANIFEST_DIGEST --action abort
```

Prepare emits a manifest without allocating the persistent destination. Review
its paths, order, effects and final tree before acknowledging the digest. The
acknowledgement is local caller authorization, not identity authentication.
Execute retains `result.git` and its private `refs/heads/result`; inspect blobs
with Git plumbing. Recovery retains the evidence and either completes the
pending suffix or restores the private base. Verification is read-only.
No command changes source refs or executes code in its trees.

```sh
python -m unittest -v tests.test_git_runtime
python scripts/reproduce_m4_runtime.py --output /tmp/m4-reproduction.json
python scripts/validate_change.py --base develop --profile pr
```

Native directory publication was exercised on Darwin arm64. The Linux
renameat2 binding is implemented but requires its own host reproduction before
a portability claim. Other platforms fail closed. Death before publication
may leave an unpublished `.RUN_NAME.stage-*` sibling for owner inspection;
the final destination remains absent and a fresh execution can proceed.
