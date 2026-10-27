# SPEC-060 T010 pr-profile result

**Outcome: the profile exited 1 at `full-tests`.** Three tests that also fail on
clean `develop` failed (pre-existing, see below). The remaining 2966 tests and the
checks that ran before `full-tests` passed. Stages ordered after `full-tests` were
not run locally. The owner decided to tick T010 on this basis, anticipating the
three pre-existing failures; this is not a clean profile pass. GitHub CI jobs
(complete Python suite, fast invariants, governance, Spec Kit structure and render,
tracking, validate) were green on the head before this record and are re-checked on
the final head.

Candidate: branch `spec060-i3-release-prep` at commit `3f39128a` (merge of develop
`965883ae` included), observed 2026-10-27 on macOS arm64, CPython 3.13.11 in an
independent full clone after `scripts/restore_public_spec_history.py` (a worktree
fails the publication check with unreachable objects). Dependencies from
`requirements-speckit.txt` and `requirements-dev.txt` only, in a virtual
environment located outside the clone; the optional `mcp` SDK was not installed,
so SDK-client tests were skipped locally.

Command: `python3 scripts/validate_change.py --base origin/develop --profile pr`

Result: repository, contract corpus, release records, export integrity, research
radar and adoption-track checks passed. The complete unit suite ran 2969 tests in
2359 s: 3 failures, 31 skipped. The profile reported
`Validation failed at full-tests (exit 1)`, so any stage ordered after
`full-tests` did not run.

## The three failures are pre-existing

`tests/test_git_counterexamples.py`: `test_exited_worker_cannot_orphan_grouped_git_child`,
`test_git_command_limit_kills_child_without_killing_worker_group`,
`test_timeout_kills_git_child_confined_to_worker_group`. They fail when
`python -m unittest tests.test_git_counterexamples` runs on a clean clone of
`origin/develop` (no SPEC-060 change) in this environment (3 failures of 29), and
they involve process-group handling, not this change. In the SPEC-054 profile run
they did not fail inside the full run; here they did.

An earlier attempt with the virtual environment inside the clone additionally
failed `test_claude_workflow_corpus_comparison.test_scrub_replaces_machine_specific_paths`
(it scrubs `sys.executable` under the repository root); it also fails on clean
develop in that layout and passes with the environment outside the clone.

## Frozen-path comparison (procedure_011)

`git diff --name-only origin/develop...HEAD` (18 files before this record):
`README.md`, `ROADMAP.md`, `agent_braid/__init__.py`, `docs/STATUS.md`,
`docs/development/SPEC_MILESTONE_INDEX.md`, `docs/development/github-tracking.json`,
`docs/tooling/INSTALLED_VERIFIERS.md`, `docs/tooling/M45_ALIGNMENT.md`,
`docs/tooling/README.md`, `docs/tooling/TECHNICAL_STATUS.md`, `pyproject.toml`,
`scripts/verify_installed_tooling_v2.py`,
`specs/047-local-technical-telemetry/alignment.json`,
`specs/060-portable-prompt-names/assurance.json`,
`specs/060-portable-prompt-names/evidence/release-readiness.md`,
`specs/060-portable-prompt-names/release-notes-0.1.0a2.md`,
`specs/060-portable-prompt-names/tasks.md`, `tests/test_spec060_release.py`.

Intersection with the frozen set (`scripts/verify_installed_tooling.py`, any
`specs/*/evidence/**` other than SPEC-060's own, `docs/tooling/evidence/**`,
SPEC-040/046/054 files, accepted ADRs, `tooling_install`, `tooling_hosts`,
`tooling_telemetry` sources): empty. `specs/047-local-technical-telemetry/alignment.json`
is the pinned M4.5 task-count file the owner asked to update; it is not evidence.
This is a path comparison, not a claim of semantic equivalence.

## GitHub CI

Pull request #754 is a draft. At the time of writing its checks (complete Python
suite, fast invariants, governance, Spec Kit structure, tracking, validate)
passed on the head before this record; the final head is checked again after this
commit. Whether CI installs the optional SDK was not checked here.

Limits: not a native-host observation (T009), not owner review (T001), not a
release decision, not clean-room reproduction or founder approval. T010 is ticked by owner decision despite the profile exit 1 above.
