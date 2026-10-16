# SPEC-041: Implementation plan

## Technical context and scope

Ship five portable product skills guiding analysis, planning, already-granted execution, recovery and evidence in Codex and Claude Code.

Prerequisites: SPEC-039 scope and stable SPEC-040 schemas; lifecycle consumed by SPEC-042.

The five canonical skills, resource loader, lifecycle and deterministic service
controls are implemented. T011–T019 retain their historical technical evidence;
T001–T010 remain pending their original procedures. The current bounded work is
mapped in [implementation status](implementation-status.md).

## Constitution check before research

Articles 3–7/12 require effect-aware unchanged runtime checks; 13–16 require explicit evidence and portable semantics; 19–25 require real measurable benefit and bounded claims. Article 20 separates analysis from execution. No MUST contradiction or SHOULD deviation is proposed.

## Research, assumptions and alternatives

Read research.md, the SPEC-039 program and SPEC-044 evaluation protocol. Official docs guide version/configuration selection; actual compatibility is tested later. Trusted owned roots, current accepted runtime contracts and explicit host/tool permissions are assumptions, not inferred source rights. Positive utility is not required to complete a sound evaluation.

## Design and compatibility

Canonical product skills live in integrations/agent-braid/skills, separately from generated Spec Kit adapters. Minimal host metadata supplies discovery; instructions describe workflow and refusal paths without hooks or grant creation.

The canonical bundle is `integrations/agent-braid/skills/`; host metadata is
`integrations/agent-braid/hosts.json`. The existing resource loader and lifecycle
remain shared. [Skill documentation](../../docs/tooling/SKILLS.md), supplemental
acceptance tests and the local capture runner cover the remaining engineering
work without creating another host adapter or registration route.

## Coordinated delivery tracks

1. Reconcile requirements, scenarios, tasks, actual modules and evidence; inspect
   the FC.1 and M4.5 continuation deltas before each lot.
2. Verify the source/package/installed bundle and both temporary host layouts,
   including preservation and refusal controls.
3. Capture scenario-specific synthetic counterparts, reusing the frozen 18-input
   inventory and keeping supplementary controls outside the registered roster.
4. Prepare the per-host capture coverage checklist. The M4.5 continuation owns
   SPEC-044/T002 admission, pre-prompt observation and exact launch packages.
5. After authentic admission and specific approval, obtain both hosts' original
   procedures; reconcile evidence and T009, then prepare T010's real decision.

FC.1's complete closure is not a predecessor for local controls. Consume its
reviewed interfaces without repeating its failed resource-profile control or
starting model/VM work. Preserve #509's frozen candidate and pins; do not rebase
or refresh them as an implicit consequence of newer develop code. A shared
receipt is reusable only for the exact bytes and assertions it covers.

Existing AIM/runtime/grant/verifier contracts remain unchanged. Analysis and preparation are consultative; host permission never substitutes for operator grants. No source ref promotion, repository-code/hook execution, arbitrary network effects or new scientific guarantee. Existing M4 G4 NO-GO and independent M3/M3.5 gates remain in effect.

## Validation strategy

Each requirement maps to one scenario, named prospective procedure, task and planned evidence in assurance.json. Positive and negative controls are specified in validation-plan.md. Before implementation resolve required contract review and run Spec Kit prerequisites; implement bounded dependency-ordered slices. Run `python3 -m scripts.validate_change --base develop --profile quick` after coherent increments and `--profile pr` once on the stable candidate. Separate actual host/provider capture, clean-room evidence and human review.

## Constitution check after design

The shared core and existing runtime remain authoritative. Descriptive tool/skill annotations cannot grant effects; evidence/rendering cannot widen observation. Missing dependencies, unavailable data or unsupported host features refuse/defer explicitly. No scientific adoption is inferred from engineering.

## Human review and unresolved decisions

Required: architectural/API/lifecycle review for the consumed contract; exact candidate/host/registration and budget decisions before capture; independent technical review and founder capability acceptance. ADR 0021 is proposed. Task completion requires actual evidence; separately verified technical clauses are recorded in `tasks.md` and `evidence/technical-clauses.json`, with native/registered/human/founder obligations preserved. Creating issues or a source PR is not adoption.
