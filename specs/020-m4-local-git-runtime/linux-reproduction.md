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

Until an executed record is checked, standalone Linux reproduction remains
pending. Any result covers only the owned fixed-patch software and the recorded
host. It does not establish semantic code correctness, hostile same-UID safety,
power-loss recovery, independent external validation or whole M4 closure.
