# G0 founder runbook (SPEC-053)

**Status:** preparation kit for revision 3 of the preregistration (C3 is
attribution coverage of changes). It authorizes
nothing: no workflow run, no spend, no freeze. The preregistration is
[the proposal](../../docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md),
[its inputs](../../docs/experiments/claude-workflow-g0-inputs.json) and
[its decision vectors](../../docs/experiments/claude-workflow-g0-decision-vectors.json);
if this runbook disagrees with them, they win. The founder runs every workflow; no
coding agent starts one.

Kit files (all stdlib or plain JS, no network):

| File | Role |
|---|---|
| `census.py` | Pre-freeze layout census: prints aggregate structure and tool-name histograms only |
| `probe.py` | Reads subagent transcripts and, with `--repo` and `--base`, the local git diff of each agent; prints integer counts only |
| `scorer.py` | `decide()` on the vectors' count tuples; run-level C1a, C1b, C2, C3 (attribution coverage), C4 and the order of evaluation |
| `workflow_template.js` | The runner: ad-hoc workflow, 3 or 4 worktree agents that must commit; no merge |
| `run-manifest.template.json` | Run manifest to fill and hash before launch (overlap, contract and negative-control entries) |

Tests: `tests/test_g0_claude_workflows.py` (synthetic data only). Its scorer tests
load `docs/experiments/claude-workflow-g0-decision-vectors.json` and require the
scorer to reproduce every vector; the scorer bytes may be pinned only after that.

Note on the T003 wording ("outside the repository and never committed"): this kit
is committed as a *template*; the founder still copies the files outside the
repository, and the hashes bound at freezing are those of the copies. Pin the
copies against the committed bytes with `shasum -a 256` before use.

## 0. Order of preparation (fixed by `freezeOrder` in the inputs file)

The probe must never change after the preregistration is frozen, so the order is:

1. **Renew the signature** of the source and budget declaration against the
   revision-3 bytes of the proposal, inputs and vectors (the revision-2 hashes are
   superseded; the renewal record is redone against the final bytes after merge). Until then nothing below
   counts toward G0. Claude extra usage and auto-recharge stay off, declared
   manually by the founder in the account settings (not checked by any script); no
   API key, credits or overage; additional spend EUR 0; stop on quota exhaustion.
2. **Census.** Run `census.py` on your own local subagent transcripts:

   ```bash
   python3 census.py            # defaults to ~/.claude/projects
   python3 census.py ROOT ...   # or explicit roots
   ```

   It prints only counts: record kinds, content-block kinds, tool names (MCP names
   collapsed into one bucket, names that are not plain identifiers bucketed),
   input key names per tool, calls paired with a result, error counts, subagent
   files per parent session, and the tool-class shares. It prints no path, file
   name, hash, prompt, content or tool output. Keep the output as a private
   working file. Read it for three things: (a) the record layout the probe will
   assume; (b) every tool name that writes files and is not `Edit`, `Write` or
   `NotebookEdit` (for example a multi-edit tool) - it must join the probe's write
   class or it falls into `other`, inflates the unknown rate and hides writes;
   (c) the call mix (`shares` in the output): since revision 3 the call-share
   unknown rate and the `Bash` share are descriptive only and never gate. The
   pre-freeze census on the founder's transcripts (1,418 subagent files, 65,639
   tool calls) gave `Bash` 80.2% and 85.4% of calls in the unknown class, which is
   why C3 became attribution coverage of changes; the raw census output is not
   committed. The agent count histogram is the
   descriptive input for the "more than 4 agents" metric; it counts subagent files,
   not workflow runs.
3. **Probe written and tested.** Edit `probe.py` only now, against the observed
   layout and the revision-3 attribution counts (`changed_files`,
   `attributed_changed_files`), and test it on a de-identified real fixture derived from the census
   material (strip content and paths, keep the record shape), not on a
   hand-written synthetic transcript. The committed tests use synthetic lines
   shaped like the observed layout; they do not replace the real fixture.
4. **Estimate the eligible yield** (one throwaway pilot run that is not counted, or
   your existing workflow history) and record `plannedRunCount` (at most 14) and the
   quota share per run. If `plannedRunCount` times the yield is below 10, downgrade
   to an observational description or raise the cap by a new proposal; never launch
   knowing 10 eligible runs cannot be reached.
5. **Hash** the probe and the runner (and the census and scorer, for the record):

   ```bash
   shasum -a 256 census.py probe.py workflow_template.js scorer.py
   ```

   Put the probe hash in `probe.scriptSha256` and the runner hash in
   `runnerScriptSha256` of the freeze record. Do not edit the copies afterwards; a
   change invalidates earlier runs.
6. **Accept the power operating point.** Read the power table in the proposal: an
   uninformative probe passes in under 2% of simulated experiments, a strong probe in
   fewer than half, and even an ideal probe fails about a third of the time. Record
   that this operating point is acceptable
   (`powerOperatingPointAcceptedByFounder`), or amend the design in a new revision.
7. **Freeze** with the separate founder decision that binds the proposal, inputs
   and vectors bytes. Only then start runs.

## 1. Design the task sets (before launch, never revised after results)

- 10 to `plannedRunCount` runs, 3 or 4 agents each. Among the first 10 eligible runs
  with probe data, by manifest ordinal: at least 7 with a designed file or
  shared-symbol overlap, at least 3 with a cross-file contract dependency and no
  shared file, and at least 3 **negative controls**.
- A negative control is an overlap run with no contract dependency: the manifest
  states before launch that no agent reads a path another agent writes unless it
  also writes it, so the probe is not expected to respond. Its entry has
  `designClass: "negative-control"` and `design.negative_control: true` (it is also
  an overlap run, so `design.overlap` is true).
- A contract-dependency run names its contract (symbol or contract plus the ordered
  reader-writer pair) in `contractDependency` before launch. Without that naming a
  run cannot qualify for C1b.
- Fill `run-manifest.template.json`: one entry per run with overlap rationale, the
  design class, the serial merge order (agent ordinal order), worktree roots and the
  shared test command. Hash the filled manifest.
- Do not commit task prose that names private content.

## 2. Per run

1. In a Claude Code session on the existing subscription, start the workflow from
   `workflow_template.js`, passing one manifest run entry as `args` (`runId`,
   `designClass`, `taskSet`, `testCommand`). The design class is never shown to the
   agents. Approve it with the host's own prompt. The workflow creates agents and
   returns branches; it never merges. The host may restart a stalled agent
   automatically and the script cannot suppress that: record the restart count per
   agent in the manifest. A restarted run is not excluded unless a branch was edited
   by hand.
2. Check eligibility mechanically, before any merge or reference outcome: every
   agent branch has a commit different from the base, base tests pass, **each branch
   passes its own tests in two executions that agree**, no manual edit of agent
   branches, transcripts available. Record exclusions by the named reasons:
   `agent-did-not-commit`, `base-tests-fail`, `branch-tests-fail-alone`,
   `flaky-branch-tests` (the two executions of a branch differ; decided from the
   branch alone, never from the reference outcome), `workflow-aborted`,
   `quota-exhausted`, `manual-edit-of-agent-branch`. A run without usable
   transcripts is `probe-unavailable`, counted outside the 10-run minimum and the
   C1b, C2, C3 and C4 denominators.
3. If the transcript layout differs from the census, record the run as
   `probe-unavailable`. The probe is pinned; it is not patched.
4. Run the probe, agents in ordinal order, read-only, one `--agent` per transcript,
   with the repository and the run's base commit:

   ```bash
   python3 probe.py --repo /path/to/repo --base BASE_COMMIT --agent /path/to/worktree1 t1.jsonl --agent /path/to/worktree2 t2.jsonl --agent /path/to/worktree3 t3.jsonl > counts-r01.json
   ```

   Run it while each agent worktree still exists: the changed files of an agent are
   the paths added or modified (`git diff --name-only --diff-filter=AM`, no rename
   detection) between `BASE_COMMIT` and the `HEAD` of that worktree, its final
   branch state. Git runs locally with hooks, system and user configuration,
   external diff and textconv disabled; it never writes. A changed file is
   attributed when the transcript has at least one successful `Write`, `Edit` or
   `NotebookEdit` call on that repository-relative path; files changed only through
   `Bash` (`sed -i`, `mv`, generators, formatters) are unattributed by definition.
   The output is integers only (no path, name or hash). Keep the transcripts local; do not copy them into
   any repository.
5. Compute every arm's prediction (merge-tree pairwise and chained, naive path
   overlap, `clash` if installed, `braid-analyze-git` primary and inclusive), write
   the prediction file and **hash it before any reference outcome exists**.
6. In a throwaway clone at the base, merge the agent branches in the fixed order
   with ordinary Git merges; run the project tests twice on the final tree.
   - a merge step conflicts: `textual-conflict`; stop folding at that step, no
     semantic label;
   - every merge clean and both executions fail: `semantic-failure`;
   - every merge clean and the two executions differ: `indeterminate`, a third
     label and never an exclusion (not a hit for any arm, a false positive for a
     flagging arm, counted in the prevalence numerator);
   - otherwise `clean`.
7. For a semantic failure the probe flagged and the manifest named, re-run the
   project tests on the merged tree with the flagged writer's changes excluded and
   record whether the failure disappears (`counterfactual_removes_failure`).
8. Append the run to `runs.json` (see below).

## 3. Scoring

`runs.json` holds one object per started run (at most 14). `probe` takes the `run`
section of the probe output (already summed over the run's agents):

```json
{"runs": [{
  "run_id": "r01", "ordinal": 1, "status": "eligible",
  "reference": "semantic-failure",
  "design": {"overlap": false, "contract": true, "negative_control": false},
  "arms": {"merge-tree-pairwise": false, "merge-tree-chained": false,
           "naive-path-overlap": false, "braid-analyze-git-primary": false,
           "braid-analyze-git-inclusive": false},
  "attribution": {"contract_named_in_manifest": true,
                  "counterfactual_removes_failure": true},
  "probe": {"changed_files": 0, "attributed_changed_files": 0,
            "ordered_pairs_with_overlap": 0, "denominator_calls": 0,
            "unknown_writer_calls": 0, "read_only_search_calls": 0, "bash_calls": 0}
}]}
```

(Values above are placeholders, not data.) `status` is `eligible`,
`probe-unavailable` or an exclusion reason; `reference` and `arms` are required for
the first two, `probe` for `eligible` only (`changed_files` and `attributed_changed_files` required,
the first not below the second; `bash_calls` optional). `reference` is `clean`,
`textual-conflict`, `semantic-failure` or `indeterminate`. `design.contract` and
`design.overlap` exclude each other; a negative control has `overlap` true.
`attribution` defaults to false for both conditions, so C1b needs it set explicitly.

```bash
python3 scorer.py runs.json
```

The scorer decides on the **first 10 eligible runs with probe data** in manifest
ordinal and applies the preregistered order of evaluation, stopping at the first
outcome: step 1 fewer than 10 such runs or a missed design quota (7 overlap, 3
contract, 3 negative control) is `g0-inconclusive`; step 2 C1b, C3 or C4 unmet is
`g0-fail`; step 3 fewer than 3 probe-flagged runs is `g0-inconclusive`; step 4 C2
unmet is `g0-fail`; step 5 is `g0-pass`. It prints the outcome, the deciding step,
the unmet criteria, the count tuple, C1a (against naive overlap; it informs R1 only
and gates nothing), C1b (a pass means feasibility not refuted), C2 against the
prevalence and the naive precision, C3 as attribution coverage of changes
(`5*attributed >= 3*changed` summed over the analysis set; a zero `changed` leaves
C3 unmet; the 0.60 threshold is a proposal the founder may amend before the freeze;
C3 answers whether transcript evidence can explain the writes at all, the
precondition for C1b and C2), the descriptive call mix (unknown call rate, Bash
share, read-only searches; never gating), C4 on the negative controls, per-arm confusion counts with
Wilson 95% intervals (description, not inference) and, alongside, the
intention-to-treat view of all started runs with exclusion reasons. Later eligible
runs are descriptive only. Negative and inconclusive outcomes are valid and are
recorded as they are.

## 4. Retention

Retain in the repository, only after founder review: the manifest without private
task prose, branch-head hashes, the prediction-file hash, per-arm run-level labels,
the probe integer counts, the census histogram (counts only) and the scorer output.
Keep local and never publish: transcripts, prompts, file contents, diffs,
repository paths, merge-tree output, workflow journals.
