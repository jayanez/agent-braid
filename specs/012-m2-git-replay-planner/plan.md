# Implementation plan

## Technical context and scope

M1 already resolves Git commit sources and produces syntactic AIM analysis with
separate provenance. Add an experimental replay layer that consumes the same
request shape, applies fixed base-to-commit binary diffs in isolated temporary
Git indexes, and compares all admissible orders. The CLI remains read-only with
respect to the source repository; explicit evidence output is the only persistent
artifact requested by the caller.

The batch is bounded to 2–4 operations, at most 64 distinct changed paths, and
1 MiB aggregate patch bytes. Only commit sources are admitted. All paths,
diffs, ancestry, repository identity and uncertainty are derived with Git
plumbing; no checkout, worktree, user test command, hook, network protocol or
external action is used. The scratch bare repository fetches only the resolved
base/source commits using the local file protocol, with hooks and ambient Git
configuration disabled. Each schedule receives a fresh index and scratch object
directory.

## Constitution check before research

- Clause zero and Articles 2, 4, 6, 7, 9, 12–14, 19–21, 23–25 apply.
- Article 6 permits planning only within an explicit execution contract; the
  implementation emits advisory preparation waves and never executes them.
- Articles 4, 13 and 14 require finite scope, named observations, inspectable
  evidence and a conservative unknown/inconclusive result.
- Article 9 requires common initial state, alternate schedules, retained failures
  and counterexamples. Article 19 requires comparison with practical baselines.
- No normative change is needed. The feature adds separate alpha evidence and
  plan schemas and leaves existing public contracts byte-for-byte unchanged.

## Research, assumptions and alternatives

The observation is `tracked-tree-v1`: the SHA-1 Git tree object after each
successful schedule, with per-step input/output tree IDs and patch digests in the
trace. This includes tracked path names, file modes and blob identities; it
excludes ignored/untracked files, build/test outcomes and all hidden semantic or
external effects. An apply failure is recorded as a failed schedule and makes
equivalence `inconclusive`; complete differing trees make it `divergent`.

Recompute every schedule in the verifier instead of trusting producer verdicts
or hashes alone. Reuse the repository's Git implementation and commit objects;
do not add Git libraries or runtime dependencies. Use a temporary bare repository
and `GIT_INDEX_FILE`, not worktrees or a custom patch interpreter. Full
enumeration is cheaper and easier to audit for at most four operations; partial
order reduction is deferred.

The benchmark's positive thresholds are falsifiable. If the required one-wave
three-operation case or distinct-hunk advantage is not demonstrated, preserve
the negative result and do not report the planner as a successful M2 advance.

## Design and compatibility

Add `agent_braid.git_replay` with `produce`, `verify`, and deterministic plan
functions. It validates M1 request fields, rejects worktrees and invalid graphs,
re-observes the request using the existing Git adapter, captures patch bytes and
compares each patch digest to M1 provenance. It computes all topological orders
(at most 24), starts each from the same base tree, and applies patches in order
using `git apply --cached --binary` against the scratch bare repository. Git
commands use a sanitized environment, a 30-second per-command timeout, disabled
network protocols except local file fetch, and bounded output. Aggregate patch
size and changed-path limits are checked before replay.

The evidence bundle uses `gitReplayEvidenceVersion: 0.1.0-alpha`, binds the
repository ID, resolved base, operation IDs/attempts/dependencies/commits,
patch digests, M1 analysis/provenance digests, contracts, all schedules and
observed results. Its digest uses the repository's strict canonical JSON helper.
The verifier takes the repository path separately, reconstructs the request,
repeats complete enumeration and replay, and checks the entire expected bundle.
It returns `verified`, `rejected` or `unverified`, with the checked finite claim.

The plan uses `gitPlanVersion: 0.1.0-alpha`, binds the evidence digest and
verifier result, and reports `candidate-preparation-waves`, `serial-fallback`,
or `manual-review`. Candidate waves require verified evidence, equivalent
complete observations and supported/certain operations. Wave levels are the
deterministic earliest dependency levels. Any other result uses a lexical
deterministic topological order if its replay succeeds; otherwise manual review
is required. Every branch carries conditions, limits and
`executionAuthorization: false`. No concurrent integration is proposed.

Add `plan-git REQUEST --evidence-output PATH`; it writes the bundle only after
successful producer-side verification and prints the plan as JSON. Add
`verify-git EVIDENCE --repository PATH`; it exits 0 only when the recorded finite
evidence verifies and exits nonzero for rejected/unavailable evidence. Existing
`analyze`, `analyze-git` and `verify` invocations are unchanged. Add standalone
schemas for the new bundle and plan under `schemas/0.1.0-alpha/`.

## Validation strategy

| Requirement | Scenarios | Test and evidence |
|---|---|---|
| REQ-001 | SC-001–002 | `tests/test_git_replay.py`; valid commits, malformed graph, worktree and bounds |
| REQ-002 | SC-003–004 | disjoint, different-hunk, overlapping, failed apply, and source immutability |
| REQ-003 | SC-005 | producer/verifier round trip, tampered digest, omitted/duplicate order, missing commit |
| REQ-004 | SC-006–007 | one-wave case, dependency levels, uncertainty, divergence and serial failure |
| REQ-005 | SC-008 | registered corpus against serial, path-overlap and `git merge-tree` baselines |

Add a six-case-or-larger synthetic benchmark containing three disjoint text
commits, two edits in distinct hunks of one file, overlapping edits, dependency,
uncertain path, deletion, binary, and unavailable-source controls. The benchmark
reports false candidate count against full replay, wave count, runtime and Git
command count. No semantic correctness claim is derived from these fixtures.

After each coherent increment run
`python3 scripts/validate_change.py --base develop --profile quick`; run the
`pr` profile once when stable. Capture feature evidence after the candidate is
stable, snapshot and freeze the authority/evidence records, reproduce from a
clean clone with Python 3.12+, and leave human review pending until an actual
review record exists. GitHub tracking source validation is local; after merge,
only a read-only audit is implied.

## Constitution check after design

The plan preserves the one-way boundary between analysis, evidence and action.
Tree equality is a finite observation of fixed patches, not contextual
equivalence, semantic commutation, confluence, arbitrary concurrent safety or
task correctness. A candidate wave is not execution authorization. Failures,
unknown inputs and negative benchmark outcomes stay visible.

## Human review and unresolved decisions

No unresolved product choice remains for this cut. The architecture ADR and
feature remain drafts until reviewed. The benchmark may fail its utility
threshold; that outcome completes only the research protocol, not the positive
milestone criterion. Founder closure, package publication and repository
publication remain separate decisions.
