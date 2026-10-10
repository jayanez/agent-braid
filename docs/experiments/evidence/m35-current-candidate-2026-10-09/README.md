# SPEC-019 current-worktree software evidence — 2026-10-09

This receipt covers the current uncommitted candidate based on commit
`49fcb2b040334b923206261c8364177b9495521e`. It is a reproducible snapshot of
software and protocol-document changes, not the PR head and not a clean-room
run.

The focused M3.5 suite passed 90 tests under Python 3.13.11. The repository
validator and constitution-replica check passed. The Spec Kit structural
validator and `quick` profile failed in the shared worktree because Git
reported unreachable objects. In a disposable clone of the actual PR head,
after removing unreachable objects only from that temporary clone, structural
validation reached publication checks but failed because the export manifest
does not bind `docs/adr/0019-bounded-local-git-runtime.md`. That unrelated
manifest was left unchanged. After installing the repository's pinned Spec Kit
dependencies in an isolated temporary environment, `scripts/spec_kit.py check`
passed with zero generated changes. The shared worktree and remote were not
cleaned or modified.

A Luna Latest adversarial review confirmed the selected founder rules are
represented but found that the event adapter does not yet model proposal
resolution at the chosen cutoff. It also found that the artifact marker does
not prove the calibration family was preselected. Both remain explicit review
gates; the adapter remains synthetic-only and source admission remains closed.

The current metadata-only readiness report is also attached: the packet is
structurally complete but admits zero real pairs, and capture/training
authorization remain false. Its `basedOnCommit` (`d5f379be…`) is the source
packet's historical basis; the report separately hashes the current inputs.

The read-only milestone-9 tracking audit found one operation: close
SPEC-019/T004 (#184), because its source checkbox is now complete. The audit
returned no other milestone operations. Apply was not attempted because the
candidate is not integrated and the synchronizer requires a clean `develop`
checkout.

This evidence does not establish source rights or yield, complete or approve
the human-label protocol, collect labels, fit on real data, evaluate a real
holdout, or grant human/founder approval. The machine-readable receipt binds
the listed source bytes and test log; those hashes establish identity only.
