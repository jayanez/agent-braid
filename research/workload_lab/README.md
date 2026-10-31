# Bounded effectful workload laboratory

Dependency-free source-checkout package for SPEC-024 (LAB.1). It simulates a
closed set of configuration, key-value and local-event primitives, enumerates
the admissible orders of one finite request and reports what an analysis can and
cannot say about them. It is experimental simulation, not a runtime, an adapter
or an AIM certificate. Every output states `executionAuthorization: false`; no
process, network, import or external mutation exists in the package.

Semantics: [SEMANTICS.md](SEMANTICS.md) and
[simulation-v1](../../specs/024-effectful-workload-lab/contracts/simulation-v1.md)
(adopted by [ADR 0028](../../docs/adr/0028-closed-effectful-workload-simulation.md)).

## Modules

| Module | Role |
| --- | --- |
| `model.py` | closed grammar, validation, private configurations, atomic transitions |
| `explore.py` | complete topological schedules and branch assignments under hard caps |
| `observations.py` | exact and selected-values observation, trace safety |
| `evidence.py` | request-bound report, deterministic replay, `verify` |
| `analysis.py` | conservative, declared-effect, additive-terminal and exhaustive-replay methods, matched-coverage experiment |
| `controls.py` | authored named controls (races, idempotency, hidden effects) |

## Use

Requires CPython 3.12 or newer. Two tests also need `jsonschema`; use the
project's `.venv-speckit` (a bare interpreter reports those two as import
errors, not as failures of the lab).

```sh
python3 -m research.workload_lab explore request.json --output /absolute/new-report.json
python3 -m research.workload_lab verify /absolute/new-report.json
python3 -m research.workload_lab.controls --manifest examples/workload-lab/manifest.json --registration examples/workload-lab/registration.json --output /absolute/new-controls.json
python3 scripts/run_effectful_workload_experiment.py --manifest examples/workload-lab/manifest.json --output /absolute/new-comparison.json
python3 -m unittest tests.test_effectful_workload_model tests.test_effectful_workload_contracts tests.test_effectful_workload_lab tests.test_effectful_workload_controls tests.test_effectful_workload_comparison tests.test_effectful_workload_report
```

Inputs, outputs and every ancestor directory must be non-symlink paths; outputs
are created exclusively; refusals name a reason (`symlink-path`, `output-exists`,
`too-large`, `invalid-json`, `invalid-request`, ...). The frozen corpus is
`examples/workload-lab/manifest.json` with `registration.json`
(17 synthetic fixtures; 7 named controls, 10 H2 fixtures).

## What a result means

- `complete` coverage means every admitted order and branch assignment of that
  finite request was visited. A cap yields `inconclusive`, never an exhaustive
  claim.
- `terminal-projection-match` means the chosen projection agreed on every
  successful path. It is never full-result, trace, contextual or effect
  equivalence; returned-value, version and event differences stay explicit.
- Absent or unknown effect declarations abstain. Aliases are resolved before
  overlap is judged.
- The additive-terminal rule (H2) labels only finite terminal-value candidates
  inside the registered `add-constant` class. It grants no commutation, safe
  parallelism, contextual equivalence or runtime safety.
- Timings live only in the experiment report, are machine-bound and
  descriptive, and support no utility or general claim.

## Review packet and status

The bounded report, the refinement checklist for future real adapters and the
clean-clone reproduction record are in
[`specs/024-effectful-workload-lab/`](../../specs/024-effectful-workload-lab/):
[`report.md`](../../specs/024-effectful-workload-lab/report.md),
[`refinement-checklist.md`](../../specs/024-effectful-workload-lab/refinement-checklist.md) and
[`reproduction-record.md`](../../specs/024-effectful-workload-lab/reproduction-record.md).
Human scientific review is pending; nothing here is evidence of a real
workload, a real service or an independent validation.
