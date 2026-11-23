# SPEC-080 T001: owner review (2026-11-23)

Guided interactive review by the owner (Juan Antonio Yáñez García, founder), working from
`spec.md`, `plan.md` and ADR 0044 as merged in #1515 (`f0793dfd`) and current on
develop `a9fdacfe`. Answers are the selected options, quoted verbatim. This review
decides the open questions only. It authorizes no code, release or execution
(`executionAuthorization` false); code starts with T003 after T002.

| Decision | Answer | Meaning |
|---|---|---|
| OD-1 ADR 0044 | "Aceptar (Recomendado)" | ADR 0044 is Accepted. Reversible only by a superseding ADR. |
| OD-2 License field | "Moverla a metadata (Recomendado)" | `license: CC-BY-SA-4.0` moves into `metadata` in all skills. ADR 0044 is unchanged. |
| OD-3 Validity target | "Forma de SPEC-077 (Recomendado)" | 10 held-out prompts × 3 repetitions per host, at least 2 forbidden-effect prompts. Pass needs ≥ 8/10 valid at the first attempt and 10/10 within one retry. Fixed before the set is frozen. |
| OD-4 Host registry | "Separar inventario y puerta (Recomendado)" | OpenCode joins the inventory host lists as unqualified and offline only. Native qualification gates stay on an explicit Claude and Codex set. `braid-harness-profile` moves to `v0.2` (three rows), and `v0.1` records are read as legacy. |
| OD-5 Telemetry flag | "Solo si lo pides (Recomendado)" | The skill adds `--telemetry local` only when the current request asks for local telemetry. Consent stays per command. |
| OD-6 Partial validity | "Solo si pasan los tres (Recomendado)" | The skill ships only if Claude Code, Codex and OpenCode all meet the OD-3 target. Otherwise the CLI-only fallback stands. |
| OD-7 Release | "alpha.10, sin cambiar capabilities (Recomendado)" | The target release is alpha.10. `harness capabilities` output is unchanged (`pluginOrMcpSurface: "none"`); only the docstring and docs change. alpha.10 waits for REQ-008. |

Limits:
- The owner is the founder and decides as owner, not as an independent reviewer.
- The Codex review (T002) has not run yet. Any finding it confirms can reopen a
  decision above through a dated amendment.
