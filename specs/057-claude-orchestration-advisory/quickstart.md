# Quickstart: SPEC-057

Status: draft. Part A lists commands that exist today and validate the document set. Part B is the host probe protocol: the orchestrating Claude session launches each probe only after the founder authorizes that individual probe. Part C shows the commands that will exist only after implementation and is marked PLANNED: none of it runs today. Part D is the staged, founder-run G1 sequence. Nothing here authorizes launching a workflow, a session or a team, a push, a spend above EUR 0, or autonomous delivery. Obtained evidence: none.

## Part A. Commands that exist today (documents only)

From the repository root, with the isolated Spec Kit environment (never install globally):

```sh
.venv-speckit/bin/python -m scripts.validate_spec_kit snapshot specs/057-claude-orchestration-advisory
.venv-speckit/bin/python -m scripts.validate_spec_kit
.venv-speckit/bin/python scripts/sync_github_tracking.py source
```

- `snapshot` refreshes the authority hashes in `assurance.json` and resets human review to pending; it is not approval.
- The second command validates every specification directory; it fails if a sibling specification directory still lacks its `assurance.json` or `tasks.md`, and that failure is a property of the sibling, not of this specification.
- The third command prints the local tracking inventory; it writes nothing remote. Publication is forbidden in this delivery.
- Check the draft contracts with the pinned `jsonschema`:

```sh
.venv-speckit/bin/python - <<'PY'
import json, glob
from jsonschema import Draft202012Validator
base = "specs/057-claude-orchestration-advisory/contracts/"
for f in sorted(glob.glob(base + "*.schema.json")):
    Draft202012Validator.check_schema(json.load(open(f)))
schema = json.load(open(base + "ownership-declaration.schema.json"))
example = json.load(open(base + "ownership-declaration.example.json"))
print([e.message for e in Draft202012Validator(schema).iter_errors(example)])
PY
```

A valid example is a document property, not evidence for any requirement.

## Part B. Host probes HV-6 to HV-13 (orchestrator-launched after per-probe founder authorization; EUR 0)

Rules for every probe:

1. Use a scratch repository created for the probe, with no remote that accepts pushes beyond the probe's need. Never use a user repository.
2. Use the existing subscription at Sonnet and medium effort, a handful of tiny tasks, and stop on quota exhaustion. Do not enable extra usage or auto-recharge.
3. Probe scripts (log-only hooks, process counters, directory listers) are written outside this repository, kept private, and hashed; the hash goes in the receipt. They record counts and booleans only: no path from a user repository, no prompt, no file content, no command text, no task text.
4. Throwaway settings and plugins are created for the probe and removed afterwards. A probe that leaves a standing hook or setting in a shared configuration has failed.
5. Record the Claude Code version (`claude --version`), operating system, surface and date in the receipt, and the outcome as `pass`, `fail` or `unobserved`. An unobserved probe is a valid report.
6. Coding agents prepare only the log-only probe script text. The orchestrating Claude session launches the probe through a workflow or derived sessions, and only after the founder has authorized that individual probe; an authorization for one probe never covers another. Agent Braid itself launches nothing. Record the authorization reference, and pin the receipt to the host version.

| Probe | What to record (counts and booleans) |
|---|---|
| HV-6 | For each of: workflow agent, `/batch` unit, in-process teammate, split-pane teammate, Desktop worktree session: whether a log-only `PreToolUse` hook fired for a Write and an Edit, whether `agent_id` and `agent_type` were present, which working directory the hook reported; and the same for a hook supplied by settings versus a hook supplied by a plugin |
| HV-7 | Whether the task tools were present by default for the model in use; whether `TaskCreated` fired for an agent team; the same with `CLAUDE_CODE_ENABLE_TODO_TOOLS`; whether a split-pane teammate inherited it |
| HV-8 | Whether a permission deny rule and a sandbox write allowlist were enforced inside each surface; whether `sed -i`, a redirect and `cat >` were stopped outside the allowed path; whether `--settings` reached a dispatched background session |
| HV-9 | The field names and enumerated values printed by `claude agents --json`, `--all` and `--cwd`; whether workflow agents, subagents and teammates were listed; whether a stopped session with uncommitted work stayed listed |
| HV-10 | With the local HEAD ahead of the origin default branch, whether a workflow-agent worktree and a background-session worktree started from the local HEAD or the origin default, under the default and under `worktree.baseRef` set to `head`; which settings keys exposed the effective value |
| HV-11 | The branch-name pattern, whether a pull request or only a branch was created, and where the worktrees lived for `/batch` units (patterns, not names) |
| HV-12 | Whether the agent-teams task directory, the team configuration and the workflow journal could be read by a separate read-only process while a unit was stopped, and their top-level key names |
| HV-13 | The number of plugin MCP server processes while two sessions, a subagent and a teammate ran; the class of text a second concurrent `analyze-work` call received |

Write each receipt under `specs/057-claude-orchestration-advisory/evidence/` (the directory does not exist yet and no agent creates the receipts), then run the receipt checker (planned, T011) and update the matrix cells that the receipts support.

## Part C. Commands that will exist after implementation (PLANNED; do not run)

```sh
# I-1 (after #672): pre-flight. Emits AIM 0.2.0-draft records and the pre-flight evidence block.
python -m agent_braid expand-ownership --declaration declaration.json --repository . --out preflight.json
# The AIM records can then be passed to the existing analyzer.
python -m agent_braid analyze preflight.aim.json

# I-2: checkpoint receipt on committed or quiesced worktrees (read-only, in-process Git; not the plugin MCP).
python -m agent_braid check-ownership --declaration declaration.json --worktree ../wt-a --worktree ../wt-b --out receipt.json

# I-2: configuration observations and read-only recovery report (the operator supplies the host's own JSON).
python -m agent_braid audit-isolation --repository . --out audit.json
python -m agent_braid report-recovery --declaration declaration.json --agents-json agents.json --out recovery.json
```

The subcommand names, option names and the module entry are provisional until the plan's design is accepted. Each command refuses an existing output path, never writes into the repository, and ends every refusal (busy lock, unstable snapshot, unobservable source, over-bound or malformed input, existing output path) with an error code, a nonzero exit and no result object (`contracts/command-error.schema.json`). None of them launches, messages, resumes or authorizes anything, and none is added to SPEC-052's constrained Bash allowlist.

## Part D. G1 (staged; founder-run; planned)

1. Review the G1 proposal against REQ-013, the hypothesis entry H-CW2 and the SPEC-058 wording (T032 produces the findings list).
2. Decide, after the `/batch` layout probe HV-11, whether `batch` has a pre-flight arm (T043), then freeze the proposal in a separate record that also fixes the planned run count and every threshold (T033). No agent edits it after that.
3. Stage 1: run arms A0, A1 and A2 on two surfaces on the existing subscription at EUR 0 with Sonnet at medium effort and small paired designs (T034); the experiment is declared observational before launch if EUR 0 cannot hold the minimums. Raw transcripts, prompts, diffs and merge-tree output stay local.
4. Stage 2 (arms A3a and A3b) starts only after the founder reads the stage 1 report and records a separate decision, and only after SPEC-058 has been implemented as an unreleased engineering candidate (behind the G1 gate); adoption or release happens only after G1 gate GG passes and the ADR is adopted.
5. Write the evidence report with counts, denominators, exclusions and the protocol-adherence assessment (T035) and record the disposition without relabeling a null or inconclusive result (T036).

No speed claim is made at any step.
