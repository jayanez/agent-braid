# SPEC-054 T010 pr-profile result

Candidate: commit `411f9fab` on branch `spec054-d-alpha4`, built on `origin/develop`
`14bab864`. Observed on 2026-10-24, macOS arm64, CPython 3.13 in an isolated
environment (`requirements-speckit.txt`, `requirements-dev.txt`), in an independent
full clone after `scripts/restore_public_spec_history.py` (a worktree fails the
publication check with unreachable objects).

Command: `python3 scripts/validate_change.py --base origin/develop --profile pr`

Outcome: selected executable validation passed, exit 0. The complete unit suite
ran 2459 tests in 2193 s: OK, 24 skipped. Spec Kit structure, render,
constitution replica, scientific controls and whitespace checks passed.

On a clean clone of `develop` at `14bab864`, `python -m unittest
tests.test_git_counterexamples` reported 3 failures (the three supervisor unit
tests on process-group handling) when run in isolation. They did not fail within
the full profile run on the candidate. They do not involve this change and are
recorded as an environment-dependent pre-existing condition.

GitHub CI on that commit then failed one test, `test_plugin_package.WorkflowPackagingTests.test_opt_in_is_marked_engineering_only_and_keeps_the_version`,
which still pinned `0.1.0-alpha.3`; the local profile run did not report it
(cause not investigated) and it was corrected to `0.1.0-alpha.4` in a follow-up commit, after which it passes
locally. The profile result above is for the earlier commit, not the corrected one.

Limits: the profile's deferred boundary gates (clean-room reproduction, evidence
capture, human review, founder approval) were not executed. Passing the profile
implies no owner release decision, native-host observation (T009), owner review
(T001), publication or approval. Alpha.4 remains an unpublished candidate.
