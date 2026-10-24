# Quickstart: SPEC-058

Status: draft. Part A lists commands that exist today and validate the document set. Part B is the guard probe protocol, in which each probe is launched by the orchestrating session after the founder authorizes that probe. Part C shows commands that will exist only after implementation of the unreleased candidate and is marked PLANNED: none of it runs today. Part D is the release sequence. Nothing here authorizes launching a workflow, a session or a team, installing a hook, pushing, a spend above EUR 0, or autonomous delivery. Obtained evidence: none.

## Part A. Commands that exist today (documents only)

From the repository root, with the isolated Spec Kit environment (never install globally):

```sh
.venv-speckit/bin/python -m scripts.validate_spec_kit snapshot specs/058-claude-orchestration-guard
.venv-speckit/bin/python -m scripts.validate_spec_kit
.venv-speckit/bin/python scripts/sync_github_tracking.py source
```

- `snapshot` refreshes the authority hashes in `assurance.json` and resets human review to pending; it is not approval.
- The second command validates every specification directory and fails if a sibling directory still lacks `assurance.json` or `tasks.md`; that failure is a property of the sibling.
- The third prints the local tracking inventory and writes nothing remote. Publication is forbidden in this delivery.
- Check the draft contracts with the pinned `jsonschema`:

```sh
.venv-speckit/bin/python - <<'PY'
import json, glob
from jsonschema import Draft202012Validator
base = "specs/058-claude-orchestration-guard/contracts/"
for f in sorted(glob.glob(base + "*.schema.json")):
    Draft202012Validator.check_schema(json.load(open(f)))
print("schemas valid")
PY
```

A valid schema or example is a document property, not evidence for any requirement.

## Part B. Guard probes GP-1 to GP-5 (launched by the orchestrating session after the founder authorizes each probe; EUR 0)

Rules for every probe:

0. The founder authorizes each probe separately (decided 2026-10-24); the orchestrating (Claude main) session then launches it through a workflow or a derived session; agents only prepare the log-only scripts; the evidence is pinned with the host version. Agent Braid itself launches nothing.
1. Use a scratch repository created for the probe; never a user repository. Do not run a probe before the SPEC-057 receipts it extends are recorded or listed as unobserved, unless the probe states it is independent.
2. Use the existing subscription at Sonnet and medium effort, a handful of tiny tasks, and stop on quota exhaustion. Do not enable extra usage or auto-recharge.
3. Probe scripts (log-only hooks, throwaway settings, counters) are prepared by agents, written outside this repository, kept private and hashed; the hash goes in the receipt. They record counts and booleans only, never content, prompts, user paths or transcripts.
4. A probe leaves no standing hook or setting behind. Remove throwaway settings and plugins afterwards and record that you did.
5. A probe never emits `allow` or `defer`; GP-2 asserts that.

| Probe | Question |
|---|---|
| GP-1 | What happens on hook crash, timeout, malformed output and a non-blocking exit status, in a main session and a subagent, for settings-provided and plugin-provided hooks? Is the failure visible anywhere? |
| GP-2 | Do `deny` and `ask` decisions cancel the call inside workflow agents, `/batch` units, in-process and split-pane teammates and non-interactive sessions? Does the reason reach the model? What does `ask` do where no person is present? Is `additionalContext` from `TaskCreated` shown to anyone? |
| GP-3 | How does a hook find an operator-owned profile and envelope outside the repository on each surface? Which working directory and configuration root does it see in a Desktop worktree session and a dispatched session? Can an agent read or overwrite that location? |
| GP-4 | Does a structured footprint marker survive task creation intact for the model in use? Does `TaskCreated` fire with and without the task tools? Does exit status 2 roll creation back? |
| GP-5 | What permission rule and sandbox write-allowlist syntax and path semantics does the installed host accept? Is the allowlist additive to the default working-directory write access or restrictive? Does `--settings` carry them to a dispatched session? Do they stop Edit, Write, `sed -i` and a shell redirect outside the allowlist? |

Each receipt goes under `specs/058-claude-orchestration-guard/evidence/` with the outcome (`pass`, `fail`, `unobserved`) per surface or condition, the Claude Code version, operating system, date and probe script hashes. An unobserved probe is a valid report and keeps the capability labelled inferred or unconfirmed; a failed probe removes the capability from the matrix.

## Part C. Commands that will exist after implementation (PLANNED; do not run)

```text
agent-braid compile-policy --declaration decl.json --unit track-a --mode audit \
    --output D --output A --output B --out-dir NEW_PRIVATE_DIR      # writes a profile and outputs; applies nothing
agent-braid report-guard --audit AUDIT.jsonl --receipt RECEIPT.json --out NEW_PRIVATE_FILE
```

Names and flags are provisional. `compile-policy` writes only to a new private directory and never edits a settings file; the operator then loads the unreleased candidate as a local plugin directory, supplies the settings document through their own launcher, or pastes the snippet. A refusal of either command is an error with a stable code and no result. `report-guard` is read-only, local and offline. Neither starts, stops, messages or authorizes anything.

## Part D. Sequence (founder acts; planned)

1. Record the answers to the open questions (T001) and the review disposition of the ADR proposal (T002; adoption waits for the G1 outcome).
2. Authorize and record the GP probes (T005 to T009) and the SPEC-057 HV-6 to HV-8, HV-10 receipts, or list them as unobserved.
3. After SPEC-057's I-3 has merged, implement the unreleased engineering candidate (T010 to T021, T023 to T025) at a recorded commit. It is not packaged, listed or published; the founder installs it as an explicit local opt-in. SPEC-058 must be implemented as an unreleased engineering candidate (behind the G1 gate) before arm A3 can run.
4. Wait for SPEC-057's G1: freeze, stage 1 report, the separate stage-2 decision, stage 2 (arms A3a and A3b on the candidate) and the report. A downgraded G1 evaluates no threshold and cannot release the guard.
5. Record the release decision (T027) conforming to `contracts/release-decision.schema.json`. A `fail` or `inconclusive` GG, or a GG over a GA that did not pass, closes SPEC-058 as not adopted. A `pass` permits release consideration only; adoption or release happens only after G1 gate GG passes and the ADR is adopted.
6. Only then build the package through the release gate, write the recipe and close (T022, T026, T028). Names, distribution, version number and publication are separate founder decisions taken after G1.
