# SPEC-039: Implementation plan

## Technical context and scope

Define the adjacent M4.5 program, current capability inventory, adoption decisions and exact delivery/closure boundaries for Codex and Claude Code.

Prerequisites: Existing accepted M1/M2 analysis and ADRs 0019/0020; the M4 historical utility decision is preserved.

This change prepares implementation specifications. Future modules/tests named below are targets, not existing commands or obtained evidence.

## Constitution check before research

Articles 3–7/12 require effect-aware unchanged runtime checks; 13–16 require explicit evidence and portable semantics; 19–25 require real measurable benefit and bounded claims. Article 20 separates analysis from execution. No MUST contradiction or SHOULD deviation is proposed.

## Research, assumptions and alternatives

Read research.md, the SPEC-039 program and SPEC-044 evaluation protocol. Official docs guide version/configuration selection; actual compatibility is tested later. Trusted owned roots, current accepted runtime contracts and explicit host/tool permissions are assumptions, not inferred source rights. Positive utility is not required to complete a sound evaluation.

## Design and compatibility

Use program.md, capability-matrix.md and ADR 0021 as the shared portfolio. SPEC-040 supplies the contract, 041 guidance, 042 lifecycle, 043 presentation and 044 independent bounded evaluation. Keep the five future routes documentation-only.

Targets: `ROADMAP.md; docs/adr/0021-codex-claude-tooling-integration.md; docs/development/github-tracking.json; specs/039-ai-tooling-program/`.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

## Validation strategy

Each requirement maps to one scenario, named prospective procedure, task and planned evidence in assurance.json. Positive and negative controls are specified in validation-plan.md. Before implementation resolve required contract review and run Spec Kit prerequisites; implement bounded dependency-ordered slices. Run `python3 -m scripts.validate_change --base develop --profile quick` after coherent increments and `--profile pr` once on the stable candidate. Separate actual host/provider capture, clean-room evidence and human review.

## Constitution check after design

The shared core and existing runtime remain authoritative. Descriptive tool/skill annotations cannot grant effects; evidence/rendering cannot widen observation. Missing dependencies, unavailable data or unsupported host features refuse/defer explicitly. No scientific adoption is inferred from engineering.

## Human review and unresolved decisions

Required: architectural/API/lifecycle review for the consumed contract; exact candidate/host/registration and budget decisions before capture; independent technical review and founder capability acceptance. ADR 0021 is proposed. Task completion requires actual evidence; current bounded obtained procedures and remaining interventions are linked in `tasks.md`, `assurance.json` and `../../docs/tooling/AUTONOMOUS_COMPLETION.md`. Creating issues or a source PR is not adoption.
