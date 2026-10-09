# SPEC-044: Implementation plan

## Technical context and scope

Register and execute candidate-bound deterministic controls, clean reproduction, actual Codex/Claude journeys and a complete-cost three-arm comparison.

Prerequisites: Protocol review before capture; stable SPEC-040–043 candidate; exact owner-approved source rights and numeric provider/time/resource budget. Earlier M4 approval is not inherited.

This change prepares implementation specifications. Future modules/tests named below are targets, not existing commands or obtained evidence.

## Constitution check before research

Articles 3–7/12 require effect-aware unchanged runtime checks; 13–16 require explicit evidence and portable semantics; 19–25 require real measurable benefit and bounded claims. Article 20 separates analysis from execution. No MUST contradiction or SHOULD deviation is proposed.

## Research, assumptions and alternatives

Read research.md, the SPEC-039 program and SPEC-044 evaluation protocol. Official docs guide version/configuration selection; actual compatibility is tested later. Trusted owned roots, current accepted runtime contracts and explicit host/tool permissions are assumptions, not inferred source rights. Positive utility is not required to complete a sound evaluation.

## Design and compatibility

Use evaluation-protocol.md. Preregister six classes times three instances, three arms and two hosts (108 intended attempts); freeze inputs, versions, rubric, costs/budgets and reviewers before capture. Preserve every slot and distinguish host versus protocol evidence. Register required claim-cost fields before capture; an explicit complete/missing-cost control verifies that unavailable required costs block positive utility claims in every report/export/decision packet even when completion thresholds pass.

Targets: `specs/044-ai-tooling-evaluation/registration.json (future); research/tooling_evaluation.py (new); tests/test_tooling_evaluation.py (new); specs/044-ai-tooling-evaluation/evidence/ (future); docs/releases/M4_5_CLOSURE.md (future)`.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

Provider model identity follows [the owner-approved clarification](model-identity-clarification.md): immutable provider IDs when exposed; otherwise a labelled exact requested route with backend identity unavailable. Registration, attestation and receipts bind selector/effort, native build, catalog, effective configuration and authenticated account route. Metadata hashes cannot stand in for backend-build hashes. Observable drift requires a new reviewed cohort; hidden revisions and nondeterminism remain limits. All 108 slots and other gates remain required.

## Validation strategy

Each requirement maps to one scenario, named prospective procedure, task and planned evidence in assurance.json. Positive and negative controls are specified in validation-plan.md. Before implementation resolve required contract review and run Spec Kit prerequisites; implement bounded dependency-ordered slices. Run `python3 -m scripts.validate_change --base develop --profile quick` after coherent increments and `--profile pr` once on the stable candidate. Separate actual host/provider capture, clean-room evidence and human review.

## Constitution check after design

The shared core and existing runtime remain authoritative. Descriptive tool/skill annotations cannot grant effects; evidence/rendering cannot widen observation. Missing dependencies, unavailable data or unsupported host features refuse/defer explicitly. No scientific adoption is inferred from engineering.

## Human review and unresolved decisions

Required: architectural/API/lifecycle review for the consumed contract; exact candidate/host/registration and budget decisions before capture; independent technical review and founder capability acceptance. ADR 0021 is proposed. All implementation tasks remain unchecked until actual evidence exists. Creating issues or a source PR is not adoption.
