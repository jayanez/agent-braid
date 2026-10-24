# G0 founder runbook (SPEC-053)

**Status:** preparation kit. It authorizes nothing: no workflow run, no spend, no
freeze. The preregistration is
[the proposal](../../docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md) and
[its inputs](../../docs/experiments/claude-workflow-g0-inputs.json); if this runbook
disagrees with them, they win. The founder runs every workflow; no coding agent
starts one.

Kit files (all stdlib or plain JS, no network):

| File | Role |
|---|---|
| `probe.py` | Reads subagent transcripts, prints integer counts only |
| `scorer.py` | Computes C1a, C1b, C2, C3 and the order of evaluation from per-run labels |
| `workflow_template.js` | Ad-hoc workflow: 3 or 4 worktree agents that must commit; no merge |
| `run-manifest.template.json` | Run manifest to fill and hash before launch |

Tests: `tests/test_g0_claude_workflows.py` (synthetic data only).

Note on the T003 wording ("outside the repository and never committed"): this kit
is committed as a *template*; the founder still copies the files outside the
repository, and the hashes bound at freezing are those of the copies. Pin the
copies against the committed bytes with `shasum -a 256` before use.

## 0. Prerequisites (all required before run 1)

1. PR1 (#671) is merged and the founder has recorded a separate freeze decision on
   the merged commit, binding the proposal and inputs bytes
   (`02291d0d...cb3e8d` for the proposal; the inputs hash is in
   `founder-decision-20261024.md`). Until then no run counts toward G0.
2. Claude **extra usage is off and auto-recharge is off**, declared manually by the
   founder in the account settings (not checked by any script). No API key, credits
   or overage. Additional spend: EUR 0. Stop on quota exhaustion; never finish a run
   on paid capacity.
3. The test repository is owner-controlled, contains no secrets, and its base tests
   pass. Name the repository and base commit in the manifest.
4. Tool versions recorded: Git, Claude Code, Agent Braid commit and plugin version,
   `clash` or `not-installed`.
5. Copy `probe.py`, `scorer.py` and `workflow_template.js` outside the repository
   and hash them:

   ```bash
   shasum -a 256 probe.py scorer.py workflow_template.js
   ```

   Put the probe hash in `probe.scriptSha256` of the freeze record and the
   workflow-template hash in `runnerScriptSha256`. Do not edit the copies after the
   freeze; a change invalidates earlier runs.
6. Take the workflow census (agent counts of existing worktree workflows, counts
   only) and record it at freezing.

## 1. Design the task sets (before launch, never revised after results)

- 10 to 14 runs, 3 or 4 agents each. Among the first 10 eligible runs by ordinal:
  at least 7 with a designed file or shared-symbol overlap, at least 3 with a
  cross-file contract dependency and no shared file.
- Fill `run-manifest.template.json`: one entry per run with overlap rationale,
  `design.overlap` / `design.contract`, the serial merge order (agent ordinal
  order), worktree roots and the shared test command. Hash the filled manifest.
- Do not commit task prose that names private content.

## 2. Per run

1. In a Claude Code session on the existing subscription, start the workflow from
   `workflow_template.js`, passing one manifest run entry as `args`
   (`runId`, `taskSet`, `testCommand`). Approve it with the host's own prompt.
   The workflow creates agents and returns branches; it never merges.
2. Check eligibility mechanically (proposal, Eligibility): every agent branch has a
   commit different from the base, base tests pass, each branch passes alone, no
   manual edit of agent branches, transcripts available. Record exclusions by the
   named reasons; a run without transcripts is `probe-unavailable`.
3. Confirm the transcript layout on the first run (assumption documented at the top
   of `probe.py`) and record it in the manifest. If it differs, stop: the probe is
   pinned and changing it requires a new proposal.
4. Run the probe, agents in ordinal order, read-only, one `--agent` per transcript:

   ```bash
   python3 probe.py --agent /path/to/worktree1 t1.jsonl --agent /path/to/worktree2 t2.jsonl --agent /path/to/worktree3 t3.jsonl > counts-r01.json
   ```

   The output is integers only. Keep the transcripts local; do not copy them into
   any repository.
5. Compute every arm's prediction (merge-tree pairwise and chained, naive path
   overlap, `clash` if installed, `braid-analyze-git` primary and inclusive), write
   the prediction file and **hash it before any reference outcome exists**.
6. In a throwaway clone at the base, merge the agent branches in the fixed order
   with ordinary Git merges; run the project tests twice on the final tree.
   `textual-conflict`, `semantic-failure` (fails both times) or `clean`. Flaky final
   tests exclude the run (`flaky-final-tests`).
7. Append the run to `runs.json` (see below).

## 3. Scoring

`runs.json` holds one object per started run (at most 14). Counts come from
`counts-rNN.json` (`total_calls`, `unknown_calls` and `ordered_pairs_with_overlap`
summed or taken per the probe output: sum `total_calls` and `unknown_calls` over
the run's agents):

```json
{"runs": [{
  "run_id": "r01", "ordinal": 1, "status": "eligible",
  "reference": "semantic-failure",
  "design": {"overlap": true, "contract": false},
  "arms": {"merge-tree-pairwise": false, "merge-tree-chained": false,
           "naive-path-overlap": false, "braid-analyze-git-primary": false,
           "braid-analyze-git-inclusive": false},
  "probe": {"total_calls": 0, "unknown_calls": 0, "ordered_pairs_with_overlap": 0}
}]}
```

(Values above are placeholders, not data.) `status` is `eligible`,
`probe-unavailable` or an exclusion reason; `reference` and `arms` are required for
the first two, `probe` for `eligible` only.

```bash
python3 scorer.py runs.json
```

The scorer prints the outcome (`g0-pass`, `g0-fail`, `g0-inconclusive`), the step
that decided it, C1a/C1b/C2/C3, reference-failure prevalence (reported before C2),
per-arm confusion counts with precision, recall and Wilson 95% intervals
(description, not inference), run counts by status, and design adherence kept apart
from the result. Report C1a separately: it informs R1 only. Negative and
inconclusive outcomes are valid and are recorded as they are.

## 4. Retention

Retain in the repository, only after founder review: the manifest without private
task prose, branch-head hashes, the prediction-file hash, per-arm run-level labels,
the probe integer counts and the scorer output. Keep local and never publish:
transcripts, prompts, file contents, diffs, repository paths, merge-tree output,
workflow journals.
