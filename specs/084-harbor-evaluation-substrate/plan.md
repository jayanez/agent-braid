# Implementation plan: SPEC-084 Harbor evaluation substrate with a macOS shadow

## Approach

- **This PR.** Spec, plan, tasks, validation plan and assurance record. ADR 0045 is
  already drafted (Proposed). No code, no install, no job.
- **Gates first.** After T001 and T002, the four feasibility gates (credential,
  runtime and pinning, cost, network policy) run as owner-started, one-command
  checks. Each gate records pass or fail. Any fail records the substrate as
  infeasible (OD-6) and the later phases do not start.
- **Thin adapter layer.** Agent Braid builds and exports Harbor job configs, checks
  pins before launch, and ingests ATIF trajectories. It does not fork or vendor
  Harbor. Harbor runs from an isolated environment chosen under OD-2.
- **Statistics stay in Agent Braid.** Ingested records feed SPEC-083 decision rules.
  The Harbor mean is stored only as a labelled descriptive field.
- **Shadow last.** The macOS shadow runs the OD-4 subset through the existing
  SPEC-065 launch path, unchanged, after the container job for the same tasks exists.

## Constitution check

| Article | Obligation | How the plan meets it |
|---|---|---|
| 0 | Negative or inconclusive results are valid | Infeasible gates and shadow disagreement are recorded outcomes (H1, H2) |
| 4–7 | Effects declared and bounded | Phase network policy, pinned resources, no secret in images, EUR 0 |
| 12 | Isolation failures are systems problems | Containers per trial; negative controls fail closed as infra errors |
| 13, 14 | Evidence, not verdicts | Harbor mean is never a verdict; SPEC-083 rules decide |
| 15 | Tools carry effect semantics | Each job config declares phases, network and resources before launch |
| 19 | Real, measurable problem | Gates and the rerun check measure feasibility before any claim |
| 20 | Analysis and execution are separate | `executionAuthorization` false; each job needs an owner go |
| 24 | Semantics before production | Spec and review precede code and any install |

No MUST conflict found.

## Affected files for the later code phase (named, not edited here)

- New: `agent_braid/harness_harbor.py` (job config build, pin check, export).
- New: `agent_braid/harness_atif.py` (ATIF ingestion into evidence records).
- New: `scripts/har_harbor_gates.py` (one-command feasibility gates).
- New: `scripts/har_harbor_job.py` (owner-started job runner and rerun).
- New: `tests/test_harness_harbor.py`, `tests/test_harness_atif.py`.
- Read, not changed: `agent_braid/harness_quota.py` (quota stops),
  `agent_braid/harness_records.py` (codec pattern for new record formats),
  `agent_braid/harness_evaluation.py` (consumer).
- Frozen, untouched: `agent_braid/harness_containment_macos.py`,
  `agent_braid/harness_lab.py`, `agent_braid/harness_host_claude.py`,
  `agent_braid/harness_transport_claude.py` and the SPEC-065 launchers.
- Documentation at the end: `docs/tooling/HARNESSING.md`; ADR 0045 status.

## Phases

1. **P0 review.** T001 owner review and ADR 0045 decision; T002 Codex review.
2. **P1 gates.** Runtime and pinning, credential, cost, network policy. Stop on any
   failed gate.
3. **P2 adapter.** Job config builder with pin check, ATIF ingestion, tests with
   recorded fixtures (no network).
4. **P3 first job.** One small job on one host (OD-5), rerun from its exported
   config, negative controls.
5. **P4 shadow.** Register the OD-4 subset and agreement rule, run the shadow, apply
   the rule.
6. **P5 report.** Feasibility and agreement report; documentation update only if the
   substrate is feasible.

## Validation profile

- This PR touches only `specs/084-harbor-evaluation-substrate/`. The assurance
  record is a sensitive path, so `quick` escalates per
  [VALIDATION_PROFILES.md](../../docs/development/VALIDATION_PROFILES.md). Run
  `python3 -m scripts.validate_spec_kit`; the CI `validate` aggregate is the `pr`
  evidence.
- Later code: targeted tests and `quick` while iterating; CI `pr` on the candidate.
  Gate checks and jobs are real-use evidence, captured separately from any profile.

## Rollback

- This PR: revert the spec folder.
- Later: the adapter modules are additive. Removing them and the isolated Harbor
  environment restores the current laboratory path. No stored state other than
  evidence records, which stay as history. SPEC-065 artifacts are unchanged.
