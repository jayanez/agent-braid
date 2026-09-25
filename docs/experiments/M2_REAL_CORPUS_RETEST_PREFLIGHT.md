# M2 real-corpus retest: read-only preflight

The proposed retest is bound to PR #141 at
`87640e950d0ac3231a93446225ef7608ebe3d980`. Run the checker from this
preflight branch with a separate, clean, standalone clone containing the frozen
Git objects and remote-tracking refs:

```sh
python3 scripts/validate_m2_retest_proposal.py --repository /path/to/clean/agent-braid
```

The checker reads the frozen proposal and corpus files, verifies their bytes and
Git ancestry, compares the declared writes with the source commits, checks the
candidate and path-baseline code hashes, dependency files, local image identity,
live branch heads and PR metadata. It checks remote refs again at the end. It
also exercises six in-memory rejection controls: moved base, substituted source
commit, duplicate PR, undeclared write, changed candidate hash and breached
resource limit. A valid result is JSON on stdout with
`status: proposal-preflight-valid` and `executionAuthorization: false`.
The [preparation snapshot](evidence/m2-real-corpus-retest-read-only-preflight.json)
records the checker commit, timestamp, observed refs and rejected controls. It
expires as soon as any bound input or live ref changes.

This is a preparation check. It does not run Git preparation or the project
test command, and it does not authorize either one. The original negative T003
result remains unchanged. After a separate founder decision on the exact inputs,
the preflight and its negative controls must be repeated immediately before any
authorized experiment. The offline Git batches and container test lanes require
their own bounded harness and evidence; this checker does not supply them.
