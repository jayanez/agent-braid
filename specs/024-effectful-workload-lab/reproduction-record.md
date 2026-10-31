# SPEC-024 clean-clone reproduction record (T007)

Scientific review: pending. Reproduction by the authoring session, not an independent party; it is software-reproduction evidence
only. `executionAuthorization: false` in every output below.

## Setup

- Date: 2026-10-31 (UTC, about 08:40). Host: Darwin arm64.
- Fresh `git clone https://github.com/jayanez/agent-braid.git`, detached at
  `develop` `6f4870ea8a885f3bf5c1e4e563a9a3759886d9aa`, `git status` clean (0
  entries). This commit holds the T005/T006/T008 sources and evidence and
  predates this packet.
- Interpreter: CPython 3.13.11 from the project's `.venv-speckit` (includes
  `jsonschema` 4.25.1). The machine was shared and loaded by other validation
  runs, so timings are not comparable.
- A first attempt with bare Homebrew CPython 3.13.11 (no `jsonschema`) ran 46
  tests with `errors=2` (`ModuleNotFoundError: No module named 'jsonschema'`
  in `test_effectful_workload_contracts` and in
  `WorkloadEvidenceTests.test_report_schema_is_strict_but_never_replaces_replay`).
  It was discarded and repeated with the venv; the README now states the
  `jsonschema` requirement.

## Commands and raw results

1. `python -m unittest tests.test_effectful_workload_model tests.test_effectful_workload_contracts tests.test_effectful_workload_lab tests.test_effectful_workload_controls tests.test_effectful_workload_comparison`
   → `Ran 48 tests in 4.928s` / `OK`.
2. Per-fixture request files written from the frozen manifest, then for each of
   the 17 requests `python -m research.workload_lab explore <request> --output <report>`
   and `... verify <report>`: 17 `"status": "written"` and 17 `"status": "verified"`
   lines, each with `"executionAuthorization": false`. Verdicts: 10
   `terminal-projection-match`, 4 `divergent`, 3 `inconclusive`.
3. `python -m research.workload_lab.controls --manifest examples/workload-lab/manifest.json --registration examples/workload-lab/registration.json --output <controls.json>`
   → `completeCoverage 17, controlFixtures 7, controlStatus {pass: 17}, h2EligibleTerminalCandidates 4, h2Exclusions {non-success-path 1, outside-additive-class 3, unknown-effects 1, version-precondition 1}, h2Fixtures 10, registeredFixtures 17`.
4. `python scripts/run_effectful_workload_experiment.py --manifest examples/workload-lab/manifest.json --output <comparison.json>`
   → `"feasibility": "positive"`, `"executionAuthorization": false`.

## Comparison against the committed evidence

| Artifact | Result |
| --- | --- |
| `controls-20261022.json` (SHA-256 `f97b8d5a…552334`) | Recapture SHA-256 `4178e143…264ae27` differs only in `environment.command` (output path), the `analysis.py` source binding and the 17 per-fixture `reportHash` values; every other field is equal. Same three differences as the T005 closure note (#680 changed only experiment-output compaction in `analysis.py`). The frozen hash is kept. |
| `comparison-20261024.json` (SHA-256 `8635d525…091b2`) | Recapture SHA-256 `30f823cc…59d25` differs only through timings and `environment.command`. Equal: `accounting`, `registration`, `protocol`, `toolBindings`, `contextualEquivalence`, `runtimeSafety`, `scientificReview`, and for all 17 fixtures `deterministicByMethod`, `oracleDigest`, `requestHash`, `control`, `h2`, `matchedCompleteCoverage`, `failures`. |
| Recapture H2 cost | median 1,259 ppm, one-sided 95% upper bound 1,613 ppm over 200 pooled samples (committed: 1,210.5 and 1,510); margin 50,000 ppm; `positive`. |

The recaptured `comparison.json` and `controls.json` are not retained and are
not a second registered run; the outcome was already observed (see the
disclosures in [report.md](report.md)).

## Not covered

No `quick` or `pr` profile run is part of this record (those validate the
branch, not the reproduction); no independent party reproduced it; no real
workload, service or adapter was exercised.
