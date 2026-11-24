# SPEC-086 T001: owner review (2026-11-24)

The owner (Juan Antonio Yáñez García, founder) reviewed `spec.md` and `plan.md` interactively on develop, as merged in #1515 (`f0793dfd`). The ADR this spec plans is drafted later (T003). The answers below are the options the owner selected, quoted verbatim.

This review settles only the open decisions. It authorizes no code, no emission, no export and no execution (`executionAuthorization` false).

| Decision | Answer | Meaning |
|---|---|---|
| OD-1 Span store | "Almacén privado aparte (Recomendado)" | A separate private local store with the SPEC-047 safety controls (private, outside repositories, bounded). The SPEC-047 store is unchanged. |
| OD-2 Emission path | "Derivar offline con un comando (Recomendado)" | Spans are derived offline from existing records by an explicit command. No code on the harness hot path. |
| OD-3 Agent identity | "Nombre fijo + perfil + hash (Recomendado)" | `gen_ai.agent.name = agent-braid-harness`, `gen_ai.agent.id` = SPEC-049 profile id, `gen_ai.agent.version` = candidate hash. The host goes in its own attribute. |
| OD-4 Content capture | "Nunca en v0.1 + nota de vía futura (Recomendado)" | No prompt, message, instruction, tool definition, argument, result, path or name in v0.1. Future path, noted only: any content capture needs its own specification and consent, and never includes `private-holdout` tasks (SPEC-082). |
| OD-5 Export transport | "OTLP/HTTP JSON, solo loopback (Recomendado)" | Explicit export only, OTLP/HTTP JSON with the standard library, to a loopback collector (127.0.0.1 or ::1). |
| OD-6 Evaluation results | "Podemos ir claramente a la opción recomendada pero dejar eventos gen_ai.evaluation.* como vía futura?" | Option (a): only `agent_braid.*` outcome classes, no numeric score. Future path, noted only: `gen_ai.evaluation.*` events need their own specification, and would carry a SPEC-083 verdict with its bounded claim text, never a bare score. |
| OD-7 ADR and adoption track | "ADR nuevo + versión al terminar (Recomendado)" | A new ADR (T003) pins one convention revision; AT-2026-004 moves to `adopted` with limits only after the T015 decision. |
| OD-8 Release | same answer | The alphas for emission and for export are named when the code and its tests are ready. |

## Limits

- The OpenTelemetry GenAI conventions are in status Development; the mapping is pinned to one revision and expected to change.
- The owner decides as owner, not as an independent reviewer.
- T002 (the Codex review of this spec) has not run yet. A confirmed finding may reopen a decision through a dated amendment.
- This record authorizes no code, no emission, no export and no promotion. `executionAuthorization` stays false.
