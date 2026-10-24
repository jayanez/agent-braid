# Proposed preregistration: M4.6 gate G0, Claude workflow integration evidence

**Status:** Proposed and not frozen. Nothing in this document authorizes a
workflow run, a concurrent agent, a spend, a push or a remote issue. Freezing is
an explicit founder act (see "Freezing"). The exact machine-readable inputs are in
[claude-workflow-g0-inputs.json](claude-workflow-g0-inputs.json); the executable
decision vectors are in
[claude-workflow-g0-decision-vectors.json](claude-workflow-g0-decision-vectors.json);
the checker is `scripts/validate_claude_workflow_g0_proposal.py`.

**Milestone:** M4.6, Claude Code dynamic workflows. **Hypothesis:**
[H-CW1](../../research/hypotheses/H-CW1-claude-workflow-integration.md).
**Owner of the gate:** [SPEC-053](../../specs/053-claude-transcript-trace-adapter/spec.md).

## Revision 2 (2026-10-24, same day as revision 1)

This revision answers a review of the first draft. It changes bound bytes, so it
changes the signature state. The changes are:

1. **Freeze order.** A pre-freeze step, the transcript layout and tool-name
   census, comes first; the probe is written against the observed layout and
   tested on a de-identified real fixture; the probe and runner are hashed; only
   then is the preregistration frozen; only then do runs start (see
   "Preparation before freezing").
2. **C1b is reframed.** A pass means feasibility not refuted, not worth
   implementing. C1b gains an attribution condition, a fourth criterion C4 adds at
   least 3 designed negative-control runs, and a power table with an operating
   point the founder must accept before freezing is published below.
3. **Braid detection at commit level.** The primary Braid flag equals "two agents
   changed a common path", plus `unknown` labelling. C1a is now reported against
   naive path overlap.
4. **Attrition.** A pre-launch feasibility rule and a recorded planned run count
   are added, with the probability of an inconclusive outcome.
5. **Selection leaks.** Flakiness is decided by a pre-merge double run of each
   branch's own tests, never on the reference outcome. The analysis set is the
   first 10 eligible runs with probe data; an intention-to-treat view is reported
   alongside.
6. **Executable decision rule.** Run-level count tuples map to an expected
   outcome in the decision vectors file, which the structural check validates.
7. **C3 definition.** Read-only searches (`Grep`, `Glob`) are separated from
   unknown writers.
8. **Signature state.** The founder's declaration of 2026-10-24 in the delivery
   session applied to the bytes of revision 1. This revision changes the bound
   bytes, so that signature is **superseded**. A renewal against the new hashes
   is required before freezing. Revision 1 bytes (SHA-256): this proposal
   `02291d0d9cbde74222652ba6b22a4cdd0293fcf7a5aa3c6adf9a119cb6cb3e8d`, the
   inputs file
   `6a5b6167257523947361be3ecba26690a42b5d1316d9045c664f2f71ec628033`, the source
   and budget decision
   `333406c25dbdf87b0cd72c2895f441998710e7f3a477e95c137647e12e4a9c62`. The new
   hashes are computed at renewal; this document does not state them, because a
   file cannot contain its own hash.
9. **Host retries.** The host may restart a stalled workflow agent
   automatically (for example "attempt 2 (stalled)", reported to allow up to five
   restarts) and a script cannot suppress that. In G0 every run records the
   restart count per agent; see "Cost and authority".

Wording items folded in: what a pass means; the AT-2026-006 kill and claim
wording; the bounded free-text channels of the SPEC-052 result schema belong to
SPEC-052, not to this experiment.

## Decision requested

Accept, amend or reject one preregistered feasibility experiment (gate G0). If
the founder freezes it, the founder runs at least 10 eligible ad-hoc Claude
workflows on an owner-controlled repository, and the recorded results decide
whether planning of the transcript adapter is justified (SPEC-053 implementation
requirements and the transcript part of the gate in SPEC-052). Implementation
would still need a separate check on real, undesigned workflows. G0 is an
existence-and-feasibility screen on a small, designed sample. It is not an
effectiveness estimate, a benchmark, a safety proof or a speed claim.

## Question and claim labels

Does Agent Braid evidence (commit-level `analyze-git`, and read/write overlap
derived from Claude subagent transcripts) identify integration failures that
`git merge-tree` baselines do not, with usable precision and an acceptable share
of unknown results?

- Hypothesis (H-CW1): in the stated domain, transcript-derived read/write
  overlap adds a signal that the commit-level arms lack. Untested.
- Heuristic: shared reads and writes across agents predict integration
  failures. Not a soundness claim; transcripts record what an agent asked a tool
  to do, not an independently observed effect.
- Stated plainly: at commit level the Braid primary flag equals "two agents
  changed a common path". The analyzer marks a pair `conflicting` when they share
  a resource with a write-like effect, `analyze-git` emits write effects only for
  added or modified paths, and `ordered` needs declared dependencies, which the
  gate and G0 declare none of. The only addition is the `unknown` label
  (deletions, renames, binaries, symlinks), which is the inclusive flag. So the
  value of release R1 is packaging, labelling, the bounded replay certificate and
  refusal controls, not extra detection. No G0 criterion claims that Braid
  detects more than naive path overlap at commit level.
- Analogy only: no braid or commutation claim is made by G0.
- Negative results are valid. Parallel runtime speedup is already a recorded
  NO-GO (SPEC-021 G4, SPEC-022, SPEC-038); G0 makes no timing claim.

## Population, sampling frame, eligibility

- **Target population:** Claude Code dynamic workflows in which 3 or 4 agents
  run in isolated Git worktrees on overlapping tasks in one repository, each
  agent committing its result.
- **Source and permissions:** one repository controlled by the founder, named in
  the run manifest at freezing (not named here; the repository binding is a
  required pre-freeze field). The founder's own Claude sessions, on the
  founder's existing subscription. Provider-terms review for using one's own
  transcripts as local analysis input is recorded in the
  [source and budget decision](../../specs/053-claude-transcript-trace-adapter/budget-and-source-decision.md),
  whose signature is superseded by this revision until renewed. No third-party
  repository, user or transcript is in scope.
- **Sampling frame:** runs designed by the founder before launch, not sampled
  from history. Each run is an ad-hoc workflow with 3 or 4 agents, `isolation:
  'worktree'`, and a task set written with a stated overlap rationale. Among the
  first 10 eligible runs, taken in the run ordinal fixed in the manifest before
  launch:
  - at least 7 carry a designed file or shared-symbol overlap;
  - at least 3 carry a cross-file contract dependency without a shared file (so
    that read/write hazards, not just write/write overlap, can occur);
  - at least 3 of the overlap runs are **negative-control** runs: overlap with no
    contract dependency, where the manifest states before launch that no agent
    reads a path another agent writes unless it also writes it, so the probe is
    not expected to respond. The probe's response on these runs measures
    precision where the answer is known (criterion C4).
  Each design property, including the negative-control designation and the
  contract (symbol and ordered reader-writer pair) of each dependency run, is
  recorded in the manifest before launch and is never assigned or changed after
  an outcome is seen. The founder reports how each task set was designed;
  designed overlap is a stated limit on generalization and makes the
  reference-failure prevalence high by construction (see C2).
- **Run budget and planned count:** at least 10 eligible runs; at most 14 may be
  started so that ineligible runs can be replaced. The planned run count is
  recorded in the manifest before freezing (`plannedRunCount`, at most 14). No
  run may be dropped or replaced after seeing its reference outcome except for
  the ineligibility reasons below, which are decided mechanically before the
  reference outcome is computed.
- **Pre-launch feasibility rule (attrition).** Eligibility depends on every
  agent committing, passing tests alone and having transcripts, and a run can be
  lost to quota exhaustion at EUR 0. Before freezing the founder records an
  estimated per-run eligible yield (from one throwaway pilot run that is not
  counted, or from the founder's existing workflow history) and the quota share
  per run. If `plannedRunCount` times the estimated yield is below 10, G0 is
  downgraded to an observational description before launch, or the cap is raised
  through a new proposal; it is never launched knowing it cannot reach 10
  eligible runs. For orientation, with 14 starts the probability of at least 10
  eligible runs is 9.0% at a per-run eligibility of 50%, 27.9% at 60%, 58.4% at
  70%, 87.0% at 80% and 99.1% at 90% (binomial, independent runs). So the
  probability of `g0-inconclusive` from attrition alone is 91.0%, 72.1%, 41.6%,
  13.0% and 0.9% at those yields.
- **Eligibility (all required):** every agent commits at least one commit
  different from the base; the base tree passes the project tests; each agent
  branch passes the project tests alone, in two executions that agree; the
  workflow completes without intervention that edits agent branches; transcripts
  for all agents are available for the probe. A run without transcripts is
  reported as `probe-unavailable`: it is counted, contributes to the Git arms and
  to C1a only, and is not part of the 10-run minimum or of the denominators of
  C1b, C2, C3 and C4 (a run counts toward those only when it carries probe data).
- **Exclusions, reported with counts:** `agent-did-not-commit` (an agent whose
  branch equals the base: the known silent false negative of `analyze-git`, so
  it is excluded and counted, never scored as independent),
  `base-tests-fail`, `branch-tests-fail-alone`, `flaky-branch-tests` (the
  agent branch's own test command, run twice before any merge, gives different
  results; this is decided from the branch alone and never from the reference
  outcome), `workflow-aborted`, `quota-exhausted`,
  `manual-edit-of-agent-branch`.
- **Analysis set.** The primary analysis set, used by every criterion, is the
  **first 10 eligible runs with probe data** in manifest ordinal. Eligible runs
  beyond the tenth are reported descriptively and enter no criterion. An
  **intention-to-treat** view, all started runs with each run's exclusion reason
  and every arm label that is computable, is reported alongside, so that
  attrition and exclusions stay visible. Both views are reported; only the first
  decides.

## Preparation before freezing

The order is fixed so that the probe never changes after the preregistration is
frozen:

1. **Renew the signature** of the source and budget declaration against the
   revised bytes (see Revision 2, item 8). The census below reads the founder's
   own transcripts locally, which that declaration covers.
2. **Transcript layout and tool-name census.** The founder reads the founder's
   own existing subagent transcripts locally and retains only a structure and
   tool-name histogram: which record kinds exist, which tool names occur, how
   many per class, how many calls are paired with a result. Nothing else is
   retained; the aggregate-only rule applies. The census also supplies the
   descriptive agent-count census (metric 4) and the tool-class shares used to
   check the C3 cap.
3. **Write the probe against the observed layout** and test it on a
   de-identified real fixture derived from the census material, not on a
   hand-written synthetic transcript. A tool name that writes files but is not
   in the write class (for example a multi-edit tool) is added to the write class
   here, or it would fall into `other`, inflate the unknown rate and hide writes.
4. **Estimate the eligible yield** (attrition rule above).
5. **Hash the probe and the runner** and record the hashes.
6. **Accept the power operating point** (see "Power table"): the founder records
   that the published pass probabilities are acceptable, or the experiment is
   re-parameterized by a new revision.
7. **Freeze** (see "Freezing"), then **start runs**.

If any step changes a byte of this proposal or the inputs file, that is a new
revision and the signature is renewed again.

## Procedure per run

1. **Manifest first.** Before launch the founder records and hashes: run id,
   base commit, task list with overlap rationale, the run's design class
   (overlap, contract dependency, negative control), the contract of each
   dependency run, the serial merge order (the agent ordinal order, fixed here
   and never chosen after seeing results), the test command, agent count, tool
   versions (Git, Claude Code, Agent Braid commit and plugin version, `clash` if
   present).
2. **Run.** The founder starts and approves the workflow in a Claude Code
   session on the existing subscription. The workflow only creates agents and
   returns their branches; it performs no merge. Agents must commit. The number
   of host-initiated agent restarts is recorded per agent.
3. **Collect.** Branch head commits and the subagent transcript files are read
   in place, read-only. The layout was fixed by the pre-freeze census; a layout
   that differs from it is recorded as `probe-unavailable`, not patched.
4. **Predict before reference.** Every arm computes its prediction and the
   prediction file is hashed before any reference outcome exists. This prevents
   policy-dependent labelling.
5. **Reference outcome.** In a throwaway clone at the base commit, merge the
   agent branches in the preregistered order with ordinary Git merges. Outcomes:
   - `textual-conflict`: a merge step conflicts. The fold stops at that step; the
     remaining steps are not evaluated, the chained merge-tree arm is scored on
     the steps it reached, and the run carries no semantic label, because a
     semantic failure after a conflicted step is unobservable.
   - `semantic-failure`: every merge is clean and the project tests fail in both
     of two executions on the final tree.
   - `indeterminate`: every merge is clean and the two executions on the final
     tree differ. It is a third label, never an exclusion. It is not a hit for any
     arm and not a qualifying failure for C1b, it is a false positive for a
     flagging arm, and it counts as a reference failure in the numerator of the
     prevalence. Every one of these choices works against passing.
   - `clean`: clean merges and passing tests.
   A run is a reference failure when it is `textual-conflict` or
   `semantic-failure`.
6. **Record aggregates** (see Retention) and keep raw material private.

## Arms

| Arm | Prediction for a run |
|---|---|
| `merge-tree-pairwise` | Failure if `git merge-tree --write-tree` of any agent pair against the base conflicts. |
| `merge-tree-chained` | Failure if folding the agents in the preregistered order with `merge-tree --write-tree` conflicts at any step; the fold stops at the first conflict. |
| `naive-path-overlap` | Failure if any two agents changed a common path (`diff --name-only --no-renames`). |
| `clash` | Failure if `clash` reports a conflict across the worktrees; `not-installed` is a valid recorded state. Optional; installation is the founder's own decision. |
| `braid-analyze-git` | Primary flag: any pair labelled `conflicting` or `ordered`; at commit level this equals naive path overlap (see "Question and claim labels"). Inclusive flag (secondary): additionally any pair that is `unknown`. Also records `plan-git`/`verify-git` eligibility when the run has at most 4 operations. |
| `transcript-probe` | Flag if any ordered agent pair (i, j) has a path that i read and j wrote with i never writing it. Counts only, see below. |

`merge-tree-pairwise` and `merge-tree-chained` together form the merge-tree
baseline. A failure is "missed by merge-tree" only when both variants predicted a
clean run.

## Transcript read/write probe

The probe reads each subagent transcript locally and in memory, classifies tool
calls (`Read`; `Edit`, `Write`, `NotebookEdit` and any further write tool found by
the census as write; `Bash`; `Grep` and `Glob`; tool names starting `mcp__`;
other), normalizes file paths to repository-relative paths using the worktree
root from the manifest, and counts read/write overlaps. It retains only integer
counts: per agent and per tool class, and per run the number of ordered agent
pairs and distinct paths with a read/write overlap. Paths, file contents, prompts
and tool outputs are never written to any retained artifact. Failed tool calls
count as calls; a failed write-class call is an unknown writer, never an effect.
Paths outside the worktree are counted separately and never matched. A write
request with no result record is counted as a failed call. The probe is a small
stdlib script whose bytes are pinned before freezing; it is a measurement tool for
G0 and not the SPEC-053 mapper.

## Metrics (per arm unless stated)

1. Hits and misses against the reference: the run-level confusion counts
   (true/false positive/negative), reported with the textual, semantic and
   indeterminate classes separately.
2. Unknown rate. Primary (criterion C3): the share of probe tool calls that are
   unknown **writer-capable** calls. Numerator: `Bash`, MCP (`mcp__*`) and other
   calls, and failed write-class calls. Denominator: every counted call except the
   read-only searches `Grep` and `Glob`, which are removed from numerator and
   denominator and reported separately as the read-only search share. Failed
   `Read` calls are reported separately and are not unknown writers. Secondary,
   always reported: the share of `analyze-git` operations with an `unknown` effect
   or partial coverage, the share of agent pairs labelled `unknown`, and the
   read-only search share.
3. Replay-ineligible rate: the share of runs in which `plan-git`/`verify-git`
   cannot certify the batch (more than 4 operations, any unknown effect, partial
   coverage, or refusal).
4. Share of runs with more than 4 agents. Designed runs have 3 or 4 agents by
   construction, so this is read from the descriptive census of the founder's
   existing worktree workflows (agent counts only) taken in the pre-freeze census
   step; it is not a pass criterion.
5. `Bash` share of subagent tool calls.
6. Precision of read/write overlap as a predictor of reference failure:
   flagged runs with a reference failure divided by flagged runs (unit: the run;
   pairs inside a run are not independent). Also reported for every other arm
   (the naive path-overlap precision is the comparison used by C2), with recall
   and a Wilson 95% interval as description, not inference.
7. Analysis cost: wall time of each arm; subscription usage of each workflow run
   when exposed by the host (unavailable is recorded as unavailable, not zero).
8. Reference-failure prevalence: reference-failure runs divided by the 10 runs of
   the analysis set. It is a pre-registered reported denominator, stated before
   C2 is evaluated, and C2 is compared against it.
9. Negative-control flag rate: negative-control runs flagged by the probe divided
   by negative-control runs.
10. Intention-to-treat counts: started, eligible, excluded by reason,
    `probe-unavailable`, `indeterminate`, and host-restart counts.

## Preregistered success thresholds and decision

A reference failure is *missed by an arm* when that arm predicted a clean run for
it. The criteria below are fixed before any data exist.

- **C1a (commit-level consistency; informs R1 only and unlocks nothing):** at
  least 1 reference failure that both merge-tree baselines **and the naive
  path-overlap arm** missed and that the Braid primary flag identified. A hit
  counts only if naive path overlap missed it. Because the Braid primary flag
  equals naive path overlap at commit level, zero hits are expected; a hit would
  point at a discrepancy between the analyzer and the naive rule, to be
  investigated, and not at extra detection. C1a is descriptive evidence about the
  commit-level gate release R1. It is not an input to `g0-pass` or `g0-fail`, and
  it never unblocks the transcript adapter (SPEC-053 PR5) or gate v2 (PR6).
- **C1b (transcript-dependent; the only C1 criterion that gates the transcript
  requirements):** at least 1 reference failure of the semantic class that was
  missed by both merge-tree baselines, by the naive path-overlap arm and by
  `braid-analyze-git` under both its primary flag and its inclusive flag, that the
  transcript probe flagged, **and that is attributable to the flagged pair**.
  Attribution needs both: the failing pair is a contract (symbol and ordered
  reader-writer pair) that the manifest named before launch, and re-running the
  project tests on the merged tree with the flagged writer's changes excluded
  removes the semantic failure. A pass of C1b is an existence and
  positive-control observation: **feasibility not refuted**. It does not show that
  the probe is useful on natural workflows, and it is not a reason to implement.
- **C2:** read/write-overlap precision of at least 0.3, which must also be
  strictly greater than the reference-failure prevalence (metric 8) and strictly
  greater than the naive path-overlap precision, evaluated only when at least 3
  eligible runs with probe data are flagged by the probe. If the naive arm flags
  no run its precision is undefined; that comparison is then recorded as not
  applicable and the other two conditions still bind. Because designed overlap
  makes prevalence high by construction, C2 is a floor against a probe that
  flags nearly every run and not evidence that the probe is useful.
- **C3:** the unknown writer-capable rate (primary definition in metric 2) is at
  most 40%. A zero denominator leaves C3 unmet. The pre-freeze census gives the
  tool-class shares; if the census already shows that the cap would be exceeded on
  the founder's existing transcripts, the founder records before freezing either a
  new revision or the acceptance that a `g0-fail` on tool mix is the likely
  outcome.
- **C4 (negative controls):** among the at least 3 negative-control runs of the
  analysis set, the probe flags at most 1.

**Order of evaluation.** The rule is applied in this order and stops at the first
outcome. The same rule is executable in the decision vectors file:

1. Fewer than 10 eligible runs with probe data, or an analysis set that misses a
   design quota (7 overlap, 3 contract-dependency, 3 negative-control runs):
   `g0-inconclusive`.
2. Evaluate C1b, C3 and C4 on the analysis set. If any is unmet: `g0-fail`. This
   holds even when fewer than 3 runs are flagged by the probe; with no
   probe-flagged run C1b is unmet.
3. Fewer than 3 runs flagged by the probe: `g0-inconclusive`.
4. Evaluate C2. If unmet: `g0-fail`.
5. Otherwise `g0-pass`, which requires C1b, C2, C3 and C4 together.

So `g0-fail` takes precedence over `g0-inconclusive` once 10 eligible runs with
probe data exist, and `g0-inconclusive` never passes: the transcript requirements
stay blocked and a further attempt is a new proposal, never an amendment of this
one after seeing data.

**Executable rule.** The decision vectors file maps run-level count tuples to the
expected outcome, including ties, the undefined naive precision, a zero
denominator, the first-10 rule and the precedence cases. The structural check
validates its structure and that every branch of the evaluation order is covered.
The scorer in the G0 kit (a separate pull request) must pass these vectors before
its bytes are pinned. Comparisons use integer cross-multiplication, not floats.

**Power table.** The table gives the probability of each outcome under stated
assumptions. It is illustrative, it is not a prediction, and it assumes C3 is met.
Model: 10 analysis runs: 4 other overlap runs and 3 negative controls that fail
with probability 0.7, and 3 contract-dependency runs that fail semantically with
probability 0.4 (naive path overlap flags the 7 overlap runs and none of the
contract runs). Monte Carlo, 200,000 trials, seed 20261024, applying the order of
evaluation above.

| Scenario (probe flag probability on failing / non-failing runs; on negative controls; attribution of a flagged contract failure) | pass | fail | inconclusive |
|---|---|---|---|
| Uninformative probe, flags 60% of all runs; attribution 0.2 | 1.7% | 98.3% | 0.1% |
| Uninformative probe, flags 90% of all runs; attribution 0.2 | 0.2% | 99.8% | 0.0% |
| Weaker probe, 80% / 40%; controls 20%; attribution 0.7 | 26.9% | 72.3% | 0.9% |
| Strong probe, 90% / 30%; controls 10%; attribution 0.9 | 45.2% | 53.6% | 1.2% |
| Ideal probe, 100% / 10%; controls 0%; attribution 1.0 | 65.1% | 32.5% | 2.4% |

Reading: an uninformative probe passes in under 2% of simulated experiments,
which is the false-pass rate the founder accepts; a strong probe passes in fewer
than half, and even an ideal probe fails about a third of the time, mainly
because at least one of only 3 contract runs must fail semantically and C2 must
beat the naive precision. The probabilities of attrition (above) come on top.
G0 therefore has low power: a `g0-fail` is weak evidence against the heuristic,
and the founder accepts this operating point, or amends the design in a new
revision, before freezing.

**Kill outcome on `g0-fail`:** adoption track AT-2026-006 moves to
watch or rejected; SPEC-053 is closed as not adopted; M4.6 closes with R1 only.
A pass unblocks the planning of SPEC-053 and the transcript part of SPEC-052; it
does not adopt anything, does not show the probe is worth implementing, and does
not prove the gate prevents conflicts.

## Retention and privacy

Retained in the repository after a run, only after founder review: the manifest
without task prose that names private content, hashes of branch heads, the
prediction file hash, per-arm run-level labels, the probe's integer counts, the
census histogram and the aggregate metrics. Not retained or published:
transcripts, prompts, file contents, diffs, repository file paths, merge-tree
output and workflow journals. The founder keeps raw material locally and may
delete it after reporting. This `aggregate-only` rule is the G0 measurement rule
and is stricter than the product mapper's: the mapper retains allowlisted
metadata (repository-relative paths, base object ids, a transcript digest) and
counts, under its own label `allowlisted-metadata-and-counts` (SPEC-053
contracts). The G0 probe retains no path or path hash.

## Cost and authority

The founder runs the workflows on the existing Claude subscription with included
quota. Additional spend is EUR 0 ([budget](../tooling/BUDGET.md)); API
credentials, purchased credits, overage and auto-recharge are not used, and the
founder stops on quota exhaustion. Running the workflows is not delegated to a
coding agent in this delivery. Each workflow run needs the host's own per-run
approval. Concurrent agents inside a workflow are used only because the founder
freezes this proposal; no command or skill authorizes them (AGENTS.md).
Agent Braid analysis is read-only (Article 20): no grant is issued and no owned
runtime execution happens in G0.

**Host retries.** The host may restart a stalled workflow agent automatically,
from the same prompt, with files that were already changed staying changed, and
a script cannot suppress that. In G0 this means an agent branch may carry work
from more than one attempt. The restart count per agent is recorded in the
manifest and reported; a restarted run is not excluded for that reason alone,
and it is excluded only if the founder edited an agent branch by hand. The
single-caller and no-retry guarantees of the SPEC-052 gate are scoped to the
script, not to the host; that wording and its consequences (idempotent read-only
calls, reported admission-lock refusals, no result trusted from a restarted
attempt without a schema check) belong to SPEC-052.

## Freezing

This proposal becomes the preregistration only when the founder records a
separate decision that binds the exact bytes of this file, of the inputs JSON and
of the decision vectors file, after the renewal of the source and budget
signature and after the preparation steps above, and fills the pre-freeze
bindings listed under `requiredBeforeFreeze` in the inputs file. Until then
`frozen` is false and no run counts toward G0. Changing a threshold, the order
rule, an eligibility rule, a design quota or an arm after the first run starts
requires a new proposal and invalidates earlier runs for G0.

## Limits

Ten or more designed runs on one repository cannot establish prevalence,
generalization, a false-negative rate for the gate or the safety of any
integration. A single hit can satisfy C1a or C1b and is an existence observation;
C2 only guards against a probe that flags nearly every run, and C4 rests on 3
negative controls. The power table shows that a fail is weak evidence and a pass
is a feasibility observation. At commit level the Braid primary flag adds
packaging and labelling, not detection, over naive path overlap.
Transcripts are an agent's recorded intent; `Bash`-driven effects are invisible
to the probe. Host, model and Claude Code versions drift between runs and are
recorded, not controlled. The merge-tree baselines are stronger than file-level
overlap on textual conflicts and weaker on semantic ones, so the arms answer
different questions. Passing deterministic checks of this document proves only
its structure.
