# SPEC-019 synthetic implementation evidence — 2026-10-09

## Scope

This record binds a focused software test run to the exact working-tree files
listed below. It covers synthetic trainer, evaluator, adapter, verifier-boundary
and readiness-checker behavior only. It is not a real-source experiment, a
training result on admitted workload data, scientific review, production
validation, or founder approval. These tests exercise REQ-003/SC-005's software
contract boundary only; source eligibility, annotation, scientific review and
real evaluation gates remain open.

## Reproduction

Base repository commit: `d5f379be` (`develop` in the active conversation worktree). The candidate files were previously validated on descendant `9dfd9fdf52e688e7225af1f7644f41b6ba92b780`; that commit contains unrelated M4-only history relative to this base.
The changed modules and tests were uncommitted working-tree files with the
SHA-256 values below.

Environment: CPython 3.13.11 (`python3.13`; no third-party dependencies).

```sh
python3.13 -m unittest -v \
  tests.test_native_predictor_training \
  tests.test_native_predictor_evaluation \
  tests.test_native_predictor_adapter \
  tests.test_native_predictor_contract \
  tests.test_predictor_readiness
```

Outcome on the current candidate: **92 tests passed** in 6.051 seconds. Full captured output is in
[`focused-tests.txt`](focused-tests.txt), SHA-256
`13445f775376a9d4abc27713ded79c241919e8e233b75bb1996c75b170defa39`.

## File commitments

| File | SHA-256 |
| --- | --- |
| `agent_braid/native_predictor_training.py` | `5c77eb3c134ed8bdb8f1a6f7ab5a46b3fda62014282d7da0211863e7d3b2d8a3` |
| `agent_braid/native_predictor_evaluation.py` | `355e0e0e058dbc33605d41cb7089242138c479c7f899f20b9f5f865a3283848b` |
| `agent_braid/native_predictor_adapter.py` | `ecaa6c037e1af6f02e737f61cadcc2a88f44e4f7161ed52625da66123b7fd43c` |
| `tests/test_native_predictor_training.py` | `a7023106c9f57e8ab961e6874c43316dc813eb17015b936b8f1e5a320127c392` |
| `tests/test_native_predictor_evaluation.py` | `097da1b7a064eab64c5deb598de4a61479da09c1b9c83a3af7577253a71cd93d` |
| `tests/test_native_predictor_adapter.py` | `d41741dd233a797be8161662b3bad0ba974ac567e3736b57663a88cd410058fc` |
| `tests/test_native_predictor_contract.py` | `0d8cc1b21e9a8d87645e7b2fc15d4134ec0f7dbcd08ff63e44af19cf85c75c03` |
| `tests/test_predictor_readiness.py` | `5a14dc3a7296e6c471acee12207aaeb5e3f0e696f8738ea2b59ba101b5f7b06e` |

## Limits

The independent [Luna Latest adversarial code review](adversarial-code-review.md)
found no confirmed defect in the synthetic controls, but recorded unresolved
real-use gates for cutoff resolution events, trustworthy holdout isolation,
and source-bound human label provenance. It authorizes no real-data use.

All records and labels exercised by this focused run are synthetic fixtures.
The trainer records its caller's synthetic designation as unverified; it
cannot authenticate the row origin. The adapter's caller-supplied source,
family, partition and session metadata is not an authenticated cohort
manifest. Its provisional synthetic grouping applies NFKC/casefold/whitespace
normalization, positional anchors and unordered operation pairing; it joins
identical pair fingerprints and stable same-family session records, and fails
closed on cross-partition components. It cannot authenticate lineage,
completeness or permission. Prospective adaptation continues to fail closed.
For synthetic pairs, the adapter records a distinct cutoff at the later
proposal and commits the complete global input-event prefix through that point;
regression tests include an earlier session and verify that later events are
excluded. This commitment is not a completeness proof, a resolution taxonomy,
or a reviewed annotation context.
The inventory exposes `auditOnlySessionCommitments` separately; those full-
session hashes may cover events after an individual pair's cutoff and must not
appear in annotator views or count as cutoff evidence.
No private journal or context was used by these tests. The evaluator requires
explicit attempts from two reviewers with distinct opaque IDs, a distinct
third-review attempt for each disagreement, and reasons for unknowns. It
derives/validates metric labels against consensus or adjudication and rejects
contradictory maps and malformed record states. These IDs and fields remain
synthetic caller inputs, not authenticated reviewer identities or source-bound
human evidence. Real use must bind each label to a trusted roster, independent
reviewer attempts, authorized context and any required adjudication. Protocol
choices, source rights, human labels, real coverage and
end-to-end workload costs remain unresolved.

## Repository validation

The managed worktree's shared Git object store contains unreachable objects and
Spec Kit tests expect `.git` to be a directory. No object cleanup was attempted.
Validation therefore ran in a fresh independent clone at
`/private/tmp/m35-independent-validation-20261009`, based on
`d5f379be20eb99a584cf71deb853cd68f3722834` with `develop` aligned to that base.
The Spec Kit candidate was restored and anchored there, and its preflight passed.

An earlier candidate run passed both required profiles with Python 3.13.11:

- `python3 scripts/validate_change.py --base develop --profile quick` — passed;
  escalated to sensitive; **840 tests passed, 1 skipped** (the expected
  unavailable private historical commit).
- `python3 scripts/validate_change.py --base develop --profile pr` — passed;
  **840 tests passed, 1 skipped** (same expected historical-commit skip).

Both profiles reported that deferred boundary gates remain unexecuted. These
results validate repository software only; they do not constitute an experiment
or evidence from real sources. The focused test receipt above binds the feature
modules to exact hashes.

An earlier focused receipt reported 91 tests, and an earlier post-regression
run reported 82 predictor tests. Those counts/hashes are historical; the
current 92-test receipt above binds the tree after the latest contract and
resolution-event checks.

After the 2026-10-09 owner-only source-scope documentation update, an initial
quick-profile rerun omitted the virtual environment from `PATH`. Although the
suite itself ran under Python 3.13.11, subprocess tests resolved `python3` to
the system Python 3.9.6. Three process-supervision tests then failed because
their worker subprocess could not import the repository package; an isolated
rerun reproduced those environment-dependent failures. The 81 focused
native-predictor tests passed on the updated tree.

The quick profile was rerun with the environment consistently pinned:

```sh
PATH="$PWD/.venv-speckit/bin:$PATH" .venv-speckit/bin/python scripts/validate_change.py --base develop --profile quick
```

It escalated to `sensitive` and passed all selected executable validation,
including **840 tests passed, 1 skipped** (the unavailable private historical
commit), Spec Kit structure and rendering, Constitution replica, and
whitespace checks. After adding the explicit fail-closed regression for an
unreviewed resolution event before the second proposal, the same pinned quick
profile was run again; it passed with **841 tests passed, 1 skipped**. The
82 focused predictor tests also passed. Luna Latest reviewed that regression
and confirmed it checks refusal only, without inventing resolution semantics.
Feature-specific evidence capture, freeze, clean-room reproduction, scientific
and human review, and founder decision remain deferred. The broad `pr` profile
is also deferred under the founder's reliability-test disposition.

## Founder disposition of broad reliability profiles — 2026-10-09

The founder directed that the general repository test families be treated as
reliability verification rather than gates for closing independently complete
M3.5 software tasks. The current `quick` run was stopped during unrelated M4
tests by that direction (exit 130). Its partial output is preserved in
[`current-quick-profile.txt`](current-quick-profile.txt); it is not a pass.
M3.5-focused tests remain required evidence for the trainer and verifier
boundary tasks. Real-source feasibility, evaluation, human review and the
parent/milestone closure conditions remain unchanged.

Feature-specific evidence capture, freeze, clean-room reproduction, scientific
and human review, and founder decision remain deferred. This synthetic package
is not a real-source experiment or approval.
