# Founder decisions — 2026-11-01

Successor of [FOUNDER_DECISIONS_20261031.md](FOUNDER_DECISIONS_20261031.md). This
record holds the owner's (jayanez, founder) decision of 2026-11-01 on System One.
The owner made it directly in the Claude Code planning session that produced the
[System One completeness audit](../system-one/addenda/completeness-audit-20261101/README.md);
the transcript itself is not stored in the repository. It is a direction and
tracking decision, not a scientific finding, review or acceptance.

## Decision (verbatim)

| # | Scope | Question | Owner's answer | Recorded effect |
|---|---|---|---|---|
| 1 | System One after the 2026-10-31 deferral | "System One está incompleta y nadie la usa: el código existe, pero ningún flujo del producto lo llama. ¿Cómo quieres seguir?" | "Quiero la opción Shadow + datos propios (Recommended) pero también quiero que vuelvas sobre el repo de Laya e incluso sobre las features de Jev y que las explores para añadir a nuestro sistema de System One las funcionalidades más potentes de esas dos referencias para que nuestro producto sea puntero y super eficaz y fiable en ese sentido" | See below |

The owner then approved the plan built on that answer, and asked that the project
documentation be updated as part of it.

## Recorded effect

- **Amends 2026-10-31 decision 3.** System One work resumes as track S1.5
  ([SPEC-066](../../specs/066-system-one-shadow/spec.md)), starting with shadow
  mode (S1.5a).
- **New reopen condition** for the deferred SPEC-029–033 tasks that SPEC-066
  absorbs: the owner's own sources are admitted under SPEC-066 REQ-101. This
  replaces "SPEC-029 T001 source permissions are granted and admitted real
  groups are greater than zero" for the owned population only. Third-party
  sources keep the old condition.
- **Absorbed tasks.** These move from milestone `Deferred` (#24) to the new
  milestone S1.5 once it is created:
  - SPEC-029 T001–T009
  - SPEC-031 T008
  - SPEC-033 T002, T003, T004, T006 and T008

  SPEC-030 and SPEC-032 stay in `Deferred`. Their parent issues stay open.
- **Advisory boundary.** [ADR 0034](../adr/0034-system-one-shadow-advisory-boundary.md)
  is accepted through the owner's approval of the plan that defined it. Confidence never grants authority,
  and `executionAuthorization` stays false.
- **Laya and Jev.** Their strongest capabilities are adopted as
  SPEC-066 S1.5c–d requirements. Laya and the open replicas run locally. Jev is a
  hosted paid service that receives the decision state, so it stays excluded
  until a separate owner decision on egress, consent and cost.
- **Not decided here, still pending:** human review of SPEC-066 (T001); the owner-run
  real-use check (SC-006); scientific, calibration, promotion and activation
  gates; and any `advise` mode.
