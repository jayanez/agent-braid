# M0 closure candidate validation

Use Python 3.12 or newer in an isolated environment. From the repository root:

```sh
.venv/bin/python scripts/validate_m0_closure.py readiness
.venv/bin/python -m unittest tests.test_m0_closure -v
.venv/bin/python scripts/run_spec_kit_pilot.py
```

The first two commands validate a candidate without approving it. The pilot
capture requires a clean tracked worktree and records the current commit. After
capture, run the Codex and Claude exercises sequentially against the recorded
candidate commit with exactly this prompt:

> Review REQ-001 through REQ-005 against SC-009 through SC-013, the M0 exit
> matrix, current tasks, obtained evidence and canonical authorities. Do not edit
> artifacts, execute another agent or approve scientific claims. Preserve the
> unsupported proof as unverified; distinguish executable checks, finite
> evidence, human review and founder approval; retain the stated limits on
> confluence, production safety, adapter correctness and Yang–Baxter. Report
> contradictions and pending checks using the task or gate identifiers already
> present in the feature.

Record each output separately. Both reports must refer to the same candidate,
prompt, contradictions and pending checks. After both reports and the founder
record exist, run:

```sh
.venv/bin/python scripts/validate_m0_closure.py closure
```

The closure mode checks recorded decisions and evidence references. It cannot
authenticate the founder or replace scientific judgment. Do not run the capture
script after approval without starting a new review cycle because it resets the
pilot to pending.
