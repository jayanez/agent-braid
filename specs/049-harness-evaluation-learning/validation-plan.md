# Prospective validation

No feature acceptance checks have run. Implementation tests named below are planned, not existing files.

## procedure_req_001

Trace: REQ-001 / SC-001.

Given owned regression fixtures and candidate real task families are identified, exercise: the corpus is frozen before method evaluation. Required observation: it records eligibility, rights, source yield, initial state, exclusions, expected outcomes and synthetic/native status for both strata; unavailable native sources produce a feasibility result.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_002

Trace: REQ-002 / SC-002.

Given eligible task families and available budgets are known, exercise: the protocol is registered. Required observation: it fixes base and simple-intervention comparators, grouped held-out units, budgets, task order, rubric, annotation/adjudication, missingness rules and acceptance margins independently of candidate rankings.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_003

Trace: REQ-003 / SC-003.

Given a registered attempt is started, refused, interrupted or scored, exercise: the report computes performance. Required observation: it reports task correctness, interventions, rework, recovery correctness, conflict precision/recall, unsafe admissions, useful parallelism and coverage with explicit denominators, uncertainty and per-axis results; unknowns never become success.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_004

Trace: REQ-004 / SC-004.

Given setup, improvements, probes, selection, reflection, verification, human review and cleanup consume resources, exercise: costs and utility are reconciled. Required observation: it reports all attempts and actual or unknown cash, quota/tokens, wall/resource and human time; EUR 0 extra spend is enforced operationally and unknown cash blocks an economic acceptance claim.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_005

Trace: REQ-005 / SC-005.

Given an observed contrast suggests a lesson, including a negative or inconclusive one, exercise: the experience store is updated or queried. Required observation: it stores cue, bounded claim, evidence, applicability, provenance, trust state and revocation; quarantine/unvalidated lessons cannot become active instructions and only earlier eligible entries reach an online task.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_006

Trace: REQ-006 / SC-006.

Given a variant is selected by a model or passes deterministic tests, exercise: promotion to an ordinary workspace or product is requested. Required observation: it requires the explicit human decision for the exact candidate, effects, version and observation scope with rollback; missing approval, native evidence or regression coverage refuses promotion.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_007

Trace: REQ-007 / SC-007.

Given a narrowly eligible low-risk class is proposed for automatic promotion, exercise: the offline policy is assessed against adverse, stale, drifted and contaminated evidence. Required observation: it returns a documented go/no-go proposal and remains disabled until separately adopted criteria, independent verification, canary/rollback and operator authority exist; synthetic results can qualify controls but cannot accept native utility.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_008

Trace: REQ-008 / SC-008.

Given evidence is positive, negative, mixed, infeasible or incomplete, exercise: the program reports or proposes an advisory interface. Required observation: it preserves each axis and cohort result, baselines, costs, uncertainty and open gates; no blended score hides safety loss and no new MCP execution surface or forecast/model promotion is implied.

Use positive, adversarial and unavailable-observation controls. Bind candidate and source/harness/policy versions; retain failures and unknowns. The mapped implementation task supplies planned test modules. A document procedure is a prospective test specification, not an executed test.

## procedure_req_009

Trace: REQ-009 / SC-009.

Given a candidate supplies outputs and may contain forged scores or hidden-grader cues, exercise the registered verifier and adjudication workflow evaluate committed outputs. Required observation: they ignore candidate-supplied acceptance, retain oracle/proxy/human provenance, disagreement and missing labels, and prevent held-out verdicts reaching refinement. Use positive, adversarial, interruption and unavailable-observation controls with frozen candidate/source identities; no test execution is claimed.

## procedure_req_010

Trace: REQ-010 / SC-010.

Given a valid human decision, stale profile or interrupted profile update exists, exercise the registry applies or rolls back a promotion transaction. Required observation: it verifies exact evidence/authority/profile identity, applies only the approved scope atomically, preserves the previous usable profile and refuses absent decisions or implicit automatic activation. Use positive, adversarial, interruption and unavailable-observation controls with frozen candidate/source identities; no test execution is claimed.

## Candidate checks

Run `python3 scripts/validate_change.py --base develop --profile quick` after implementation increments and `--profile pr` once stable, with the isolated configured interpreter. Feature-specific frozen-candidate evidence and human review remain separate.

## T001 registration checks (prospective, 2026-10-27)

These describe what the T001 evidence and any later corpus validator must show.
Only the checks listed under "Obtained for T001" were run; the rest are planned.

Obtained for T001 (see `evidence/t001.json` for commands and exits): recomputed
Git blob IDs and SHA-256 values of the 11 registered source files against the
pinned values, confirmed the seven named test anchors by symbol and line, and ran
`scripts/validate_spec_kit.py` for structure. No unit test of an anchor was rerun.

Planned positive controls: every registered case has a source path, hash, lineage
group, `synthetic`/`native` label, rights basis and expected oracle; the observed
and planned yield columns reconcile with the inventory.

Planned negative controls: a corpus that places one lineage group in both
discovery and holdout is refused; an anchor whose hash differs from the pin is
refused as drift; a case labelled `native` without a permission receipt is refused;
an unresolved lineage cannot be assigned a partition; a recorded intervention
history without a source record is refused; zero native yield yields a feasibility
result and not a synthetic substitution.
