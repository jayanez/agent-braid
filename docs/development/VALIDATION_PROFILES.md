# Validation profiles

Agent Braid preserves complete normative, scientific, contract and publication
gates while scheduling them at the point where their evidence is useful. Path-based
selection shortens the development loop; it is not semantic dependency analysis or
proof that a change is safe.

## Development loop

Run after a coherent group of edits:

```sh
python3 scripts/validate_change.py --base develop --profile quick
```

The command discovers committed, staged, unstaged and non-ignored untracked paths,
prints its reasons and runs fast repository invariants plus affected-domain tests.
Use `--plan-only` to inspect without executing, `--format json` for tooling or
repeat `--path` to inspect explicit paths.

Unknown paths fail closed to sensitive validation. This makes a stale path map
slower, not less safe.

## Stable pull-request candidate

Run once after implementation has converged:

```sh
python3 scripts/validate_change.py --base develop --profile pr
```

The PR profile includes repository and contract validators, release/publication
checks, the complete unit suite, finite scientific controls, Spec Kit structure and
rendering, Constitution replica and whitespace. It does not capture evidence or run
a clean-room protocol.

## Sensitive changes

Normative authorities, public schemas, scientific algorithms, supply-chain inputs,
validation infrastructure, assurance records and unknown paths are sensitive. A
requested quick profile escalates automatically. Use an explicit review run when
needed:

```sh
python3 scripts/validate_change.py --base develop --profile sensitive
```

Inputs capable of changing Codex or Claude scaffolding additionally activate the
pinned temporary-repository matrix. This includes `.specify` templates and scripts,
generated agent skills, `scripts/spec_kit.py`, the integration test and the pinned
requirements. An unrelated README, analyzer or research-radar edit does not run
that matrix.

## Evidence boundaries

Milestone closure, release, public-repository cutover and refreshed scientific
claims use their applicable feature-specific clean-room or capture command only
after a stable commit is frozen. The planner reports these as deferred gates and
never executes them implicitly. A successful quick, PR or sensitive profile does
not establish:

- clean-room reproduction;
- scientific validity or production safety;
- human or founder approval;
- independent validation.

Evidence-only packaging after a frozen reproduction validates binding and record
integrity; it does not repeat the experiment unless its bound candidate or inputs
changed.

## Continuous integration

CI keeps the complete candidate gate but runs independent jobs in parallel:

- fast repository invariants;
- the complete Python suite;
- governance, contracts and scientific controls;
- Spec Kit structure and rendering.

The Codex/Claude solo-and-dual matrix is a visibly conditional specialist job. A
skipped job is not described as passed. Clean-room reproduction remains outside
ordinary push and pull-request CI because it produces candidate-bound evidence.

### Story branches and integration candidates

Accumulate a user story on one branch and prepare one final pull request. Pushes
on story branches run validation through their open PR; direct pushes to `develop`
and `main` retain the complete post-merge gate. Before opening a PR, use the local
profiles above. Every PR commit, including drafts and documentation-only changes,
keeps the complete mandatory CI jobs and the stable `validate` aggregate check.
A new commit requires its own successful validation; an earlier SHA's result does
not cover the new candidate.

Only superseded PR validation runs share a cancelable concurrency group. Each
non-PR run has a unique group, preserving pending and running post-merge jobs.
The aggregate rejects workflow cancellation, missing or failed mandatory jobs,
malformed classification outputs and incorrectly skipped specialist validation.
Unknown paths select the specialist matrix conservatively; a skipped unselected
matrix is visible as skipped, not described as passed. Existing download caches
still require dependency installation and validation on every run.

Deferring heavy CI until a draft becomes a stable integration candidate remains
a proposal. It requires an enforceable merge boundary tied to the exact candidate
and invalidation when its inputs change. Until that boundary is established and
reviewed, full PR and post-merge validation remain active. Tracking audits keep
their read-only permissions, relevant-path events and weekly/manual cadence.
Release/artifact validation, publication provenance and candidate-bound evidence
remain separate gates; ordinary CI neither publishes nor authorizes a release.

## Maintaining the path map

Update `scripts/validate_change.py` and `tests/test_validation_profiles.py` when a
new top-level artifact class, validator, public contract or integration input is
introduced. The classifier classifies its own files as sensitive. Do not add a
catch-all rule merely to silence unknown-path fallback; assign an owner, tests and
any evidence boundary explicitly.
