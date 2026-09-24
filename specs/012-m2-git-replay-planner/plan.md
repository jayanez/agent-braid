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

The founder approved this bounded first cut and ADR 0013 on 2026-09-24, as
recorded in `founder-review.json`, against frozen candidate commit
`7541ff437e2e2d6f558c5855ae76bb13067256cd`. The approval is limited to the
fixed-patch `tracked-tree-v1` experiment and consultative planning boundary.
M2 remains open; this approval does not authorize concurrent integration,
project-code execution, publication, or a broader semantic claim.

### Open M2 follow-up backlog

The following work is deliberately outside the approved first-cut claim and
remains open for later M2 increments:

- **T009 — Thread-safe Git environment:** pass a sanitized environment directly
  through the M1 adapter instead of mutating process-global `os.environ`; add a
  concurrent-caller regression. Implemented; see `m2-followup-evidence.json`.
- **T010 — End-to-end resource bounds and diagnostics:** bound captured output
  while it is produced, apply an overall replay budget including M1 provenance, and
  distinguish patch rejection from timeout, output-limit and process-start
  failures. Implemented; budget scope and checks are recorded in
  `m2-followup-evidence.json`. Child-process RSS is not hard-limited, and the
  temporary-data cap is sampled during a Git command; both remain explicit
  resource risks for a future sandboxed prototype.
- **T011 — Plan integrity:** add deterministic semantic validation or
  regeneration for plan artifacts, enforce cross-field consistency with
  verified evidence, and retain `executionAuthorization: false`. Implemented
  with `verify-plan`; see `m2-followup-evidence.json`.
- **T012 — Parallel-integration contract:** specify the state, isolation,
  dependency, stale-input, conflict, verification and recovery conditions under
  which integration work could safely proceed in parallel, consistent with
  Constitution Articles 6, 12 and 19. Proposed in ADR 0014 and
  `docs/architecture/PARALLEL_INTEGRATION.md`; accepted for T013 by the founder
  on 2026-09-24, bound by `t012-founder-review.json`.
- **T013 — Bounded parallel-integration prototype and evaluation:** implement a
  gated prototype only after T012 is reviewed; compare it with serial
  integration on representative workloads, measure correctness and overhead,
  retain failed/inconclusive cases, and require human review before expanding
  execution authority. Completed for the accepted local, read-only Git scope
  and candidate `db30bc3`; see `t013-review.json`. This does not expand
  execution authority or close M2.

#### T013 prototype resource profile

The prototype accepts 2–4 operations, at most 16 changed paths and 256 KiB of
aggregate patch data. It uses at most two concurrent Git workers, a 30-second
end-to-end wall limit, 128 Git commands, 8 MiB captured output (2 MiB per
command), 32 MiB sampled temporary data, and a 512 MiB address-space limit per
Git child process. The temporary-data check samples every 50 ms, so a single
in-flight write can overshoot before termination. It executes Git plumbing only;
it runs no repository code, tests, hooks, agents, network actions or promotion.

The profile is a conservative local fixture limit, not a general sandbox or
production setting. Candidate and serial results remain separate from the
source repository. Any unsupported platform that cannot enforce the child
address-space limit fails closed.

The accepted prototype exercises concurrent fixed-patch preparation in isolated
temporary indexes. It computes the candidate combined tree and serial reference
sequentially with `git merge-tree`; it does not exercise concurrent merging,
repository code, or validation commands. The bounded evaluation uses two- and
three-operation disjoint fixtures, different hunks in one file, a conflict, three
repetitions per fixture, a serial reference, an independently computed
path-overlap baseline, pairwise `git merge-tree` timing, and controlled
wall-time, command-count, output, scratch and tree-verification failure cases.
The additional Git-only declared final-tree check has a failed-validation
control. In-flight time and scratch controls terminate an already started child;
a graceful SIGTERM followed by a fresh CLI process checks cancellation, private
scratch cleanup and source immutability. Results remain synthetic and local.
T013 scoped founder human review accepted R1–R6 for candidate `db30bc3` on
2026-09-24; separate independent validation remains pending. Concurrent tree
merging, project validation, recovery after an uncatchable coordinator crash,
and live-agent interleavings remain open M2 work and require an appropriately
reviewed contract before the prototype scope or authority is broadened.

These tasks deepen the residual risks identified in review and advance the
project toward safer, more capable parallel integration. T009–T013 are complete
within their recorded scopes; the remaining M2 risks and capabilities are open
and do not change the accepted first-cut evidence.
