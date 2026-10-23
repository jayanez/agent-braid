# Quickstart: SPEC-053

Status: draft. Run every command from the repository root with the isolated
environment (`.venv-speckit/bin/python`, Python 3.12 or newer; see
`docs/development/SPEC_KIT.md`). A passing command here proves the stated
structure or bytes only. It is not a G0 result, not a freeze, not a founder
signature and not human review. No command below starts a workflow, spends money,
publishes, creates a remote issue, commits or pushes.

## Part A. Commands that exist today (REQ-001, REQ-002, and the document set)

1. Structural gates for the whole repository:

   ```sh
   .venv-speckit/bin/python -m scripts.validate_spec_kit
   ```

   Expected: `Spec Kit structural gates passed; semantic/human review remains separate.`

2. Refresh the draft assurance snapshot after editing any authority file or this
   feature's record. It rewrites `assurance.json` and resets human review to
   `pending`. Report changed authority hashes before refreshing; do not refresh to
   hide drift.

   ```sh
   .venv-speckit/bin/python -m scripts.validate_spec_kit snapshot specs/053-claude-transcript-trace-adapter
   ```

   Expected: the record validates; `stage` stays `draft`, `human_review` stays
   `pending`, `obtained_evidence` stays empty.

3. G0 proposal structure (REQ-001, REQ-002):

   ```sh
   .venv-speckit/bin/python -m unittest tests.test_claude_workflow_g0_proposal -v
   .venv-speckit/bin/python -m scripts.validate_claude_workflow_g0_proposal
   ```

   Expected: all tests pass and the checker prints `proposal-structure-valid` with
   the pinned proposal hash. Negative controls inside the tests (removed field,
   relaxed threshold, removed C1a or C1b, a C1b that commit-level evidence or
   naive overlap could satisfy, a C1a made gating, a C2 without the prevalence or
   naive-precision comparison, a removed or inverted order of evaluation, fewer
   runs, non-zero spend, false freeze, path-retaining probe, changed bytes,
   approved/supported rewording) must be rejected. Limits: structure and bytes
   only.

4. Contract example and overlays are well formed and analyze or compose as
   documented (structural):

   ```sh
   .venv-speckit/bin/python - <<'PY'
   import json
   from jsonschema import Draft202012Validator
   from agent_braid.analysis import analyze
   schema = json.load(open("schemas/0.2.0-draft/agent-interaction-metadata.schema.json"))
   records = json.load(open("specs/053-claude-transcript-trace-adapter/contracts/aim-trace-record.example.json"))
   validator = Draft202012Validator(schema)
   for record in records:
       validator.validate(record)
   report = analyze(records)
   assert report["summary"]["classifications"]["conflicting"] == 1
   assert all(r["effects"]["coverage"]["status"] == "partial" for r in records)
   import copy
   c = "specs/053-claude-transcript-trace-adapter/contracts/"
   s = "specs/052-claude-workflow-gate/contracts/"
   delta = json.load(open(c + "gate-result-v2.delta.schema.json"))
   args_delta = json.load(open(c + "braid-gate-args-v2.delta.schema.json"))
   v1 = json.load(open(s + "braid-gate-result.schema.json"))
   v1_args = json.load(open(s + "braid-gate-args.schema.json"))
   for fragment in (delta, args_delta):
       Draft202012Validator.check_schema(fragment)
   # Overlay the result delta on a copy of the committed v1 schema.
   v2 = copy.deepcopy(v1)
   props, dp = v2["properties"], delta["properties"]
   props["schemaVersion"] = dp["schemaVersion"]
   props["unobserved"]["allOf"] = dp["unobserved"]["allOf"]
   props["limits"]["allOf"] = dp["limits"]["allOf"]
   props["request"]["properties"]["transcripts"] = dp["request"]["properties"]["transcripts"]
   inter = props["analysis"]["oneOf"][1]["properties"]["interactions"]["items"]["properties"]
   inter["transcriptHazards"] = dp["analysis"]["oneOf"][1]["properties"]["interactions"]["items"]["properties"]["transcriptHazards"]
   props["transcriptEvidence"] = dp["transcriptEvidence"]
   v2["required"] = v1["required"] + ["transcriptEvidence"]
   v2["$defs"] = delta["$defs"]
   Draft202012Validator.check_schema(v2)
   args2 = copy.deepcopy(v1_args)
   args2["properties"].update(args_delta["properties"])
   args2["$defs"].update(args_delta["$defs"])
   Draft202012Validator.check_schema(args2)
   print("contract examples structurally valid")
   PY
   ```

   Expected: prints `contract examples structurally valid`. Limits: the example is
   synthetic; it says nothing about real transcripts or the soundness of the
   mapping, and the overlay check composes schemas only (sample-envelope
   acceptance and rejection are planned tests, task T023).

5. Tracking source inventory (reads only the repository):

   ```sh
   .venv-speckit/bin/python scripts/sync_github_tracking.py source
   ```

   Expected: a source inventory and no remote call. It fails if any spec listed in
   `docs/development/github-tracking.json` lacks `tasks.md` or if a task line does
   not parse. Remote reconciliation (`audit`, `apply`) is a separate, explicitly
   authorized step and is **forbidden** in this delivery.

6. Proportional change validation, once the candidate is stable:

   ```sh
   .venv-speckit/bin/python scripts/validate_change.py --base develop --profile quick
   .venv-speckit/bin/python scripts/validate_change.py --base develop --profile pr
   ```

   Expected: the planner reports the escalation for sensitive paths. `pr` runs once
   on a stable candidate. Clean-room reproduction, evidence capture and human
   review are separate boundary gates.

## Part B. G0 steps (founder; no agent starts the workflows)

These are procedures, not commands this repository runs. The authoritative text is
the [preregistration](../../docs/experiments/CLAUDE_WORKFLOW_INTEGRATION_PROPOSAL.md).

1. Founder reads, amends or signs the
   [budget and source decision](budget-and-source-decision.md) as a separate record
   that binds its bytes with the proposal and inputs file. Expected: a signed
   record exists; until then the draft grants nothing.
2. Founder fills the pre-freeze bindings (`requiredBeforeFreeze` in the inputs
   record) and records the explicit freeze decision. Expected: `frozen` is true only
   through that separate record; changing a threshold or arm afterwards invalidates
   earlier runs.
3. Prepare the ad-hoc workflow script, run manifest and probe script **outside the
   repository** and hash them before the first run.
4. Founder runs at least 10 and at most 14 workflows, each with the host's own
   per-run approval, on the existing subscription, stopping on quota exhaustion.
   Expected per run: manifest hashed first, predictions hashed before the reference
   outcome, reference outcome by serial merge in the preregistered order and two
   test executions.
5. Founder records the aggregate report, the exclusion counts, the costs (or
   "unavailable") and the disposition `g0-pass`, `g0-fail` or `g0-inconclusive`.
   Expected: all three are valid, published with counts; an inconclusive result does
   not pass.

## Part C. Commands that will exist only after `g0-pass` (BLOCKED)

Names are planned, not existing. Do not run them or create the files from this
document.

```sh
# PR5, planned
.venv-speckit/bin/python -m unittest tests.test_claude_transcript_trace -v
.venv-speckit/bin/python -m unittest tests.test_trace_adapter tests.test_trace_lifecycle_spikes -v   # unmodified SPEC-023 suites
git diff --exit-code develop -- agent_braid/trace_adapter.py agent_braid/analysis.py        # must show no change
.venv-speckit/bin/python -m agent_braid analyze-claude-transcripts REQUEST.json --provenance-output PROVENANCE.json
# PR6, planned
.venv-speckit/bin/python -m unittest tests.test_claude_transcript_gate_v2 tests.test_plugin_package -v
```

Expected after implementation (not a current claim): every control in the
[validation plan](validation-plan.md) passes, the unmodified SPEC-023 suites pass,
the two protected files show no diff, and the conversion emits fixed diagnostic
codes with no content. Host-level behavior (plugin MCP tools and plugin agents
inside workflow agents, nested workflow calls, constrained Bash) needs the
founder's native observation and receipts.
