# VIS.1c owner decisions

## Recorded 2026-11-04 (verbatim)

Owner answers given in the planning session of 2026-11-04. They authorize planning
only. They are not an acceptance of this plan, of the ADR amendment or of the
contract amendment (see "Gates").

| ID | Question (verbatim) | Answer (verbatim) | Consequence |
|---|---|---|---|
| D7 | "¿La vista 2D pasa a ser la vista por defecto del visor?" | "Sí, 2D por defecto (Recommended)" | 2D timeline is the default view; 3D stays as a secondary spatial view. ADR 0033 says SVG 2D is "kept as the frame and table fallback, not as the primary surface the owner chose", so an amendment is needed: [draft](adr-0033-amendment-draft.md); accepted on 2026-11-04 (see "Gate answers" below) and applied to the ADR. |
| D8 | "¿Qué debe significar 'conflicto' en el visor?" | "Ambos, distinguidos (Recommended)" | Two meanings, never merged: **predicted** (analysis class `conflicting`, available now) and **observed** runtime collision (same file touched by two agents; later phase, needs new data). Distinct glyph and wording each ([timeline-2d.md](timeline-2d.md#conflict-vocabulary)). |
| D9 | Contract fields | "axis.nowMs, waitingOn, Duración de herramienta, Sugiéreme alguno más que marque un valor diferencial para este visor y además revisa el diseño de las secciones, títulos y botones para que sea todo coherente y con un diseño moderno" | Contract draft [v0.2](contract-v0.2-amendment-draft.md) with `axis.nowMs`, `waitingOn` and tool duration, each through privacy review; 2 to 4 further differential fields proposed below as owner-decision items (none accepted); section, title and button review delivered as [design-system.md](design-system.md). |
| D10 | Vendor | "No, overlays HTML propios (Recommended)" | No new vendor file (no `CSS2DRenderer`, `Line2`, `MapControls`). Fixed-size HTML labels positioned by projection. ADR 0033 vendor list is unchanged. |

Earlier owner direction (recorded as given in the planning session, not a quoted
question): 3D fixes are guided camera, auto-framing, legend, legible labels, controls
with a help overlay and a reset button; plus a 2D view "precisa clara y fiable con las
mismas estrategias y funciones que la visualización 3D en cuanto a filtros, leyendas,
etiquetas, etc" (one shared state model for 2D, 3D and table). Owner pain points: does
not understand what is seen; camera; visual look; missing information (which agent is
active, what conflicted, how long).

## Gates (what still needs a human)

Status after the second session of 2026-11-04: G1 and G2 are done; G3 and G4 are authorised and not done.

| Gate | Owner action | Blocks |
|---|---|---|
| G1 | Accept (or change) this plan and the open decisions below (T051) | every task T052 onwards |
| G2 | Accept ADR 0033 amendment (accepted 2026-11-04) | making 2D the default (T059); the 2D view itself can ship behind a view switch (T057) |
| G3 | Accept contract v0.2 and its privacy review (precedes the code of T052) | T060 to T063 |
| G4 | Owner-run host probe authorization (T053) | tool duration from hooks (T062) |

## Open decisions (with recommendation)

Each was a guided question for the owner; the recommendation was the planner's. All were answered on 2026-11-04 (see "Other open decisions as accepted" below; OD-V1 was changed).

| ID | Decision | Options | Recommendation and why |
|---|---|---|---|
| OD-V1 | UI language | (a) Spanish only; (b) English only; (c) Spanish default plus English, one `strings` module, language switch remembered per browser | (c). The owner works in Spanish and the repository documentation is English; text is already isolated for translation by the design in [design-system.md](design-system.md#copy-guide). Cost: two string tables to keep in sync, tested by a key-parity test. Undo: drop one table. |
| OD-V2 | Placement of the governance text ("what a shape means and does not mean", the no-claim statement) | (a) always-visible long banner (today); (b) one-line permanent strip plus an "About this view" panel with the full text; (c) only in the panel | (b). The non-claim and `executionAuthorization: false` stay visible on every screen (REQ-010, Article 17 discipline) but stop occupying the first fold. (c) is rejected: hiding it would weaken the visible-boundary requirement. |
| OD-V3 | Differential fields beyond D9 (below) | accept F1 to F4 individually | See table below; F1 and F2 are the cheapest and most on-brand. |
| OD-V4 | Tool duration retention | (a) memory only, shown live, absent in replays and default exports; (b) also kept in recordings as exact value; (c) kept in recordings and exports as coarse bucket | (a) first; revisit (c) after real use. Matches the existing "Exact durations" row of the deviation table (D4). |
| OD-V5 | Observed collision source | (a) derive from `ownership-receipt` and ownership notice adapters only; (b) also from hook `PostToolUse` tool names plus path-free resource ids | (a). It adds no host payload field. (b) needs a probe and a new allowlist entry and is a separate review. |
| OD-V6 | 3D after 2D becomes default | (a) keep as "Spatial map" with the fixes; (b) freeze 3D (fixes only, no new features) | (b) after Phase 2: the audit finds the third axis encodes nothing; keep the capability, stop investing. |

## Proposed differential fields (not accepted)

Update: F1 to F4 were accepted on 2026-11-04 (F4 not before T035); the table is kept as proposed.

Chosen because they answer the owner's questions ("who is active, what conflicted, how
long") in ways only a coordination layer can. All are descriptive; none is presented
as speedup, efficiency or safety (REQ-010, Article 17).

| ID | Field | Source and privacy justification | Value |
|---|---|---|---|
| F1 | **Lane parallelism and overlap**: concurrency band (number of lanes open at each instant), peak concurrency, overlap time per lane pair | Derived client-side from `strand.open`/`strand.close` `relMs`, already retained ("Sub-day relative time" row). No new data, no collection. | Shows the "several agents at once" the product is about, and shows where a predicted conflict pair actually overlapped in time. |
| F2 | **Waiting time**: total and current time a lane spent in `waiting`, with `waitingOn` when known | `strand.update.state` (already allowlisted shape) plus `waitingOn` salted strand id (HMAC identifier, already permitted class). No tool input or output. Observed waiting is only as good as the host signal; hook-only sessions emit none, so the UI labels it "inferred". | Answers "why is it stuck" and "how long". |
| F3 | **Prediction versus observation link**: for each pair the analysis called `conflicting`, `independent-candidate` or `ordered`, show whether the two lanes overlapped in time and (phase 4) whether an observed collision occurred | Uses `crossing.classified` (existing), lane times (existing) and, later, resource ids only (no paths beyond the existing `evidenceRef`/`sharedResources`). Wording is descriptive ("overlapped", "no collision observed in this session"), never "the analysis was right". | The distinctive Braid view: analysis next to what happened. Also feeds the Q-VIS1 observation descriptively. Risk: reads as validation; mitigated by wording and by not counting percentages. |
| F4 | **Effort per lane** (tokens, cost) as an optional column | `effort.sample` already exists, is ephemeral (REQ-007), `host-estimate`, in memory, omitted from default export; D4 deviation table already covers it. Needs VIS.1b ingest (T014, T018) to carry data. | Cost next to duration. Depends on VIS.1b; do not schedule before T035 decides it. |

Considered and not proposed: lane goal or prompt text (prohibited, never-retained list);
file paths per tool call (prohibited beyond relative `evidenceRef`); tool input or output.

## Gate answers recorded 2026-11-04 (second session, verbatim)

Given after the plan merged (#1050). They authorize the implementation tasks listed
in the "Effect" column and nothing else.

| Gate | Question (verbatim where the owner was asked one; otherwise the item) | Answer (verbatim; the OD-V3 cell is a summary of the answer) | Effect |
|---|---|---|---|
| G1 | "¿Aceptas el plan VIS.1c con las recomendaciones para las decisiones abiertas?" | "Me parece todo correcto pero me gustaría si no es mucha complicación que el idioma fuese el que se detecte del TUI, Desktop App del usuario y el fallback al inglés. Es muy complicado?" | Plan accepted. OD-V2, OD-V4, OD-V5 and OD-V6 accepted as recommended. OD-V1 **changed**: see "OD-V1 as accepted". |
| G2 | ADR 0033 amendment | "Aceptar (Recommended)" | The amendment is applied to `docs/adr/0033-vendored-threejs-mit-boundary.md` with status accepted (see its "Amendment 2026-11-04" section). The 2D timeline may become the default view (T059). |
| OD-V3 | Differential fields | F1, F2, F3 and F4 all accepted. F4 (effort per lane) still depends on VIS.1b and the T035 decision: it is accepted but not scheduled before T035. | T064 may implement F1 to F3. F4 waits. |
| G3 | Contract v0.2 privacy review (T052) | "Sí, ambas (Recommended)" | Authorised. **Not done in this change**; scheduled next. |
| G4 | Owner-run host probe (T053) | "Sí, ambas (Recommended)" | Authorised. **Not done in this change**; scheduled next. |

G3 and G4 were one two-part question answered "Sí, ambas (Recommended)". Authorising
the review (T052) and the probe (T053) does not accept contract v0.2: the contract
amendment stays a draft until the T052 privacy review concludes.

### OD-V1 as accepted (UI language)

The owner asked whether the language could follow the one detected from the user's
TUI and Desktop App, with English as the fallback. It is not complicated, and it is
implemented as follows (T058):

1. Supported languages: Spanish (`es`) and English (`en`). One `strings.js`, two tables,
   a key-parity test, English fallback per key.
2. Detection order, first match wins:
   1. a manual choice in the UI, remembered per viewer in the browser (`localStorage`,
      every access in `try/catch`; the page works without it);
   2. the browser or desktop-app locale (`navigator.languages`, first supported entry);
   3. a hint from the `view serve` process (`LC_ALL`, then `LC_MESSAGES`, then `LANG`,
      as the terminal that started the viewer sees them), delivered with the snapshot
      as a bare language tag (`es` or `en`) and nothing else; an unsupported or unset
      locale sends no hint;
   4. English.
3. The hint is a two-letter tag chosen from the supported set. The full locale string,
   the environment and any path never leave the process.
4. Limits (stated, not hidden): "TUI" means the terminal environment of the process that
   started `view serve`. The Desktop App is reached through the locale its embedded
   browser reports. A user whose browser locale is supported but differs from the
   terminal locale gets the browser locale (rule 2 before rule 3); the manual choice
   overrides both.

### Other open decisions as accepted

| ID | Accepted |
|---|---|
| OD-V2 | (b): one-line permanent strip plus an "About this view" panel with the full text |
| OD-V3 | F1, F2, F3, F4 (F4 not before T035) |
| OD-V4 | (a): tool duration kept in memory only, absent in replays and default exports |
| OD-V5 | (a): observed collision derived from `ownership-receipt` and ownership notice adapters only |
| OD-V6 | (b): freeze 3D (fixes only, no new features) after Phase 2 |

### Decisions after T052 and T053 (2026-11-04)

Verbatim answers to the guided questions:

| Question | Answer | Effect |
|---|---|---|
| T053: the probe saw no tool call; how do we close the duration question? | "Aceptar T030" (after asking "No me recomiendas repetir la sonda?" and hearing the trade-off) | T053 closed without a rerun. The T030 receipt (Claude Code 2.1.292) naming `duration_ms` in `PostToolUse` is the evidence; T062 accepts only a strict integer and drops any other shape. |
| Is `collision.observed` added later, in T063, as a new contract version? | "Sí, en T063 (Recommended)" | R13 to R15 stay deferred; T063 writes the per-adapter definition of "touched" first, then an additive contract version. |
| Should tool duration ever appear in recordings or exports? | "Nunca, solo en vivo (Recommended)" | OD-V4 (a) confirmed, including with `--record-effort` and `--include-effort` (R10). |

