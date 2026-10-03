# Bounded Linux reproduction

The manually dispatched `Reproduce bounded M4 runtime` workflow captures the
existing fresh-process protocol on a GitHub-hosted Linux runner. It requires a
full public commit SHA, confirms an initially clean checkout and writes the
record and raw log outside that checkout. Each record identifies the actual Git,
Python, operating system and architecture, the source input hashes, the test
result and whether those inputs changed during the run.

This workflow is separate from ordinary push/PR validation. Dispatching it is an
explicit evidence operation; passing CI alone does not produce this record.
Checkout, Python setup and artifact upload are pinned to immutable action commits.
The runner installs only the pinned development schema validator dependencies;
the owned runtime continues to use the standard library and local Git.

The first target is merged PR #190, commit
`9b2c51580f681ad5f3531670e4bdd6825df685c4`. Its tree is byte-identical to PR candidate
`13df5d5169f467c02f1877cbd49c17c91957141b`. The original and corrected founder
approvals and their frozen evidence remain bound to their original commits.

Download both artifact files before the 30-day retention window expires. Check
the JSON candidate identity, clean state, successful exit, unchanged input hashes
and SHA-256 of the raw log before citing the run. Commit the verified files and
run URL in a separate evidence addendum; do not silently replace a prior record.

## Executed and checked record

Run [37158821943](https://github.com/jayanez/agent-braid/actions/runs/37158821943)
completed successfully using workflow commit
`475461a355e7540a86c57fd22eec8087e7e6ee54` and candidate
`9b2c51580f681ad5f3531670e4bdd6825df685c4`. The recorded environment is Linux
x86_64, Python 3.12.14 and Git 2.55.0. All 19 runtime tests passed (no skips),
including real killed-reference-transaction resume/abort and cumulative budgets.

The downloaded [JSON record](../../examples/runtime/m4-linux-reproduction.json)
and [raw log](../../examples/runtime/m4-linux-reproduction.txt) were checked
against all 18 Git input blobs in that exact candidate. The tree was clean and
inputs did not change. The raw log SHA-256 is
`551ad3b04c1c1971feecf59a62ff6c6983d10f570629c6b1fb10e30981f16d0f`.
Artifact 11287370372 has GitHub-reported archive digest
`sha256:14866c94a3e69be7ef528ab6c4ee9e63a6f973ee25c2c2767f4a395ccddf6a1a`;
that archive digest is transport metadata, separate from the checked log hash.
These repository copies preserve the evidence beyond artifact retention.

Standalone Linux software reproduction is now observed on this recorded host.
The original accepted records remain unchanged. This result covers only the
owned fixed-patch software and the recorded host. It does not establish semantic code correctness, hostile same-UID safety,
power-loss recovery, independent external validation or whole M4 closure.
