# SPEC-085 T001: owner review (2026-11-24)

The owner (Juan Antonio Yáñez García, founder) reviewed `spec.md` and `plan.md` interactively on develop, as merged in #1515 (`f0793dfd`). This spec has no ADR. The answers below are the options the owner selected, quoted verbatim.

This review settles only the open decisions. It authorizes no code, no label move and no execution (`executionAuthorization` false).

| Decision | Answer | Meaning |
|---|---|---|
| OD-1 Storage | "Diario aparte (Recomendado)" | A separate journal, `braid-harness-pointers/v0.1`, cites T013 decision hashes. T013 code and records stay unchanged. |
| OD-2 Protection | "En el repo, vía PR tuya (Recomendado)" | The journal lives in the repository. Every move lands through a pull request the owner merges, so Git history and review show who moved what. |
| OD-3 Write path | "La opción 1 como me recomiendas pero déjame siempre claro en todas las interacciones cuando y donde tengo que lanzar ese script" | An owner-run one-command script outside the plugin `launch`. Added condition: every interaction that needs a move states when to run the script (its precondition), where (terminal and directory) and the exact command. The script itself prints its precondition, working directory and the pull request it prepares before it acts. |
| OD-4 Rollback evidence | "Sin veredicto nuevo si no se revocó (Recomendado)" | Rollback needs no new verdict while the target's cited evidence is not revoked; a revoked target is refused. |
| OD-5 First baseline | "Brazo A de SPEC-049 (Recomendado)" | While `adopted` is empty, the regression verdict compares against the registered SPEC-049 baseline arm A. |
| OD-6 Scope | "Uno por ámbito de T013 (Recomendado)" | One pointer set per T013 registry scope. |
| OD-7 Release | "Decidir al terminar el código (Recomendado)" | The alpha is named when the code and its tests are ready. alpha.10 stays the SPEC-080 skill only. |

## Regression acknowledgement (from the SPEC-083 T002 review)

SPEC-083 finding S83-005 asked that per-task regressions be seen before a move to `candidate`. The owner first chose a mandatory summary with an acknowledgement. Asked for a stronger strategy, analyzed adversarially and counterfactually, the owner then chose "Opción 2, 10 extra por brazo (Recomendado)":

- **Bound acknowledgement.** The move record cites the SPEC-083 verdict hash and its regression summary hash. A mismatch with the current verdict refuses the move.
- **Graded summary.** Hard regressions (baseline pass^n = 1, candidate pass@n = 0) and soft regressions (a drop of at least 0.4 on a task).
- **Confirmation trials.** Pre-registered in SPEC-083: 10 more trials per arm on up to five flagged tasks, inside the same registration; they never change the verdict.
- **Read check.** The owner-run script shows the summary and asks the owner to type the number of hard regressions; an agent cannot fill it in ahead.
- **Private tasks.** The script shows the titles of regressed private tasks only in the owner's terminal, read from the private store, and never writes them to the repository.

Why the confirmation trials: with 5 trials and no real change, a 20-task comparison shows at least one false soft regression 65 to 98 % of the time (binomial calculation for task success rates 0.9 to 0.5); with 15 trials a false flag survives 0.06 to 2 % of the time, and a real drop from 0.9 to 0.4 is confirmed about 82 % of the time. Cost: about 30 % more trials. OD-6 of SPEC-083 is unchanged: the summary does not block on its own.

## Limits

- The owner decides as owner, not as an independent reviewer.
- T002 (the Codex review of this spec) has not run yet. A confirmed finding may reopen a decision through a dated amendment.
- This record authorizes no code, no move and no promotion. `executionAuthorization` stays false.
