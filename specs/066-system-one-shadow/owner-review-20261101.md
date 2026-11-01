# SPEC-066 owner review — 2026-11-01

Evidence for T001. The owner (jayanez, founder) answered these questions directly in
the Claude Code coordinator session on 2026-11-01, through interactive prompts. The
answers are recorded verbatim; the session transcript is not stored in the
repository. This is the owner's specification review and decision record. It is
not a scientific finding, an independent technical review, or evidence that any
hypothesis holds.

## Specification review

| # | Question (summary) | Owner's answer (verbatim) | Effect |
|---|---|---|---|
| R1 | Accept the SPEC-066 scope: S1.5a implemented, with S1.5b–e as outline stages that each need their own plan and review | "Aceptar (Recommended)" | OD-1 decided; T001 complete |
| R2 | H-S1 thresholds | "≤2% error, ≥30% cobertura (Recommended)" | H-S1 unchanged |
| R3 | Is it enough for episodes to hold only structural data? | "Mantener estructural (Recommended)" | No names, paths or identifiers in episodes |
| R4 | Confirm the background single-slot worker instead of the synchronous call (OD-4) | "Confirmar worker (Recommended)" | OD-4 decided: background worker |
| R5 | Instrument CLI `analyze` and `analyze-git` (OD-7) | "Después del primer report (Recommended)" | OD-7 deferred until after the first report |
| R6 | How to move the 15 absorbed issues (OD-5) | "Override por tarea (Recommended)" | OD-5 decided: T003 task-level override |

## Native-only direction

Asked about Jev and about ADR 0034, the owner answered:

> "Espera que no sé si nos hemos colado. No quiero que te apoyes en nada que tenga
> que ver con servicios externos ni otros backends locales como Laya/Von/Keb. Lo que
> quiero es que Agent Braid tenga un sistema de decisión de capa 1 como ellos pero no
> que que los usemos por debajo. Asegúrate de que lo has entendido y dime si estamos
> alineados o has patinado en todo este análisis y planificación y tenemos que
> reconducirlo"

The coordinator confirmed a slip: S1.5d had proposed Laya- or Von-class backends
as an optional extra, and Jev as excluded only until a later decision. It proposed
a native-only direction instead. The owner then answered:

| # | Question (summary) | Owner's answer (verbatim) | Effect |
|---|---|---|---|
| R7 | Limit on third-party components for the S1.5d model | "OK, quiero un sistema 100% propio (Recommended) pero aclárame cómo lo entrenaríamos. ¿Lo podríamos hacer enriqueciendo la información de telemetría y entrenándolo con nuestro propio trabajo en este u otros repos? O tenemos que acudir a modelos externos o encoders genéricos preentrenados? Pregunta interactiva de nuevo" | Native model only: own architecture, training and weights. No external services, third-party decision models or pretrained encoders |
| R8 | Approve ADR 0034, amended to forbid external services and third-party decision models | "Aceptar enmendado (Recommended)" | ADR 0034 accepted as amended |
| R9 | Label sources for S1.5b | "Ejecuciones reales (Recommended),Replay de historial git (Recommended)" | Labels come from real runs and from git-history replay |
| R10 | Repositories | "Workspaces registrados (Recommended) y futuros para los que te dé la orden bajo aprobación expresa" | Registered plugin workspaces only; other repositories need express approval each time |
| R11 | Structural features and salted hashes, after the coordinator explained the trade-offs | "Ambos + ablación (Recommended)" | Episode v0.2 carries both. The S1.5d ablation keeps hashes only if they measurably help |
| R12 | When to implement v0.2 | "En este PR (Recommended)" | v0.2 ships with S1.5a |

## SC-006 real-use session (OD-6)

| # | Question (summary) | Owner's answer (verbatim) | Effect |
|---|---|---|---|
| R13 | When and for how long | "Tras el merge, 1 semana (Recommended)" | One week of normal work after merge |
| R14 | Who enables shadow mode | "Yo te guío, tú lo aplicas (Recommended)" | The owner runs `plugin setup --system-one shadow` with guidance, then reconnects |
| R15 | Commit a redacted receipt | "Sí, recibo redactado (Recommended)" | Derived receipt under `docs/development/REAL_USE_EVIDENCE.md` rules; zero episodes is a valid result |

## Not decided here

Calibration, promotion to `advise`, and any S1.5b–e implementation still need
their own plans and reviews. Answer R7 rules out pretrained encoders entirely.
Using free-text task descriptions as features is therefore outside SPEC-066.
