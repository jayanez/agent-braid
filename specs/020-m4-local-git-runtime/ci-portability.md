# CI portability correction

PR #190 initial Linux CI executed 330 tests and failed only the two resume/abort
subcases of test_killed_ref_transaction_is_recovered. The test incorrectly assumed
that every Git version rejects a loose result.lock file during read-only fsck.
The Linux runner's Git permits verification of the unchanged base prefix.

The test now admits either a fsck rejection or a verified empty prefix with the
original base commit. Both paths must leave every private file and the abandoned
lock unchanged. Resume and abort must then remove the abandoned lock under the
coordinator and produce the expected independently verified result. This retains
the recovery regression instead of skipping it. Runtime code, schemas and the
founder-approved executable candidate are unchanged. Original reproduction inputs
and approvals remain historically bound; this records a test portability change.

Failed executed CI: https://github.com/jayanez/agent-braid/actions/runs/37156130149
