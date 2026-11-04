# VIS.1c design system, page structure and copy guide

Scope: the first-party web bundle (`index.html`, `style.css`, `loom.js`, new modules).
Constraints that bind every rule here: strict CSP (`style-src 'self'`: no `style=`
attribute in HTML, no `<style>`; CSSOM assignment such as `el.style.transform = ...`
and CSS classes are allowed), all event values as text nodes, no `innerHTML`, no
remote resource, no new vendored file (D10), colour never the only carrier of
meaning, and the read-only and non-claim statements stay visible (REQ-010).

Principles (from the design lenses, see [skill-lens-findings.md](skill-lens-findings.md)):

1. **Answer the user's question first**: who is active, what happened, how long,
   where did it conflict. Model vocabulary (compatibility classes, "strand") goes one
   level deeper.
2. **Simplicity, not minimalism**: the common path is visible, advanced options are
   one level down (Apple "Simplicity"); each element earns its place.
3. **One name for one thing** in titles, buttons, legend, tooltips and table headers
   (copy guide below).
4. **Restraint with motion**: purposeful, short, interruptible, reduced-motion aware
   (Emil Kowalski, Apple fluid interfaces).
5. **Honest absence**: unknown, unobserved and unverified are shown as such, once, at
   the right level, never as clean (REQ-003).

## Tokens

Extend the existing custom properties in `style.css` (`--bg --panel --text --muted
--line --accent --warn-* --sel --control-line`); do not rename them. New tokens use the
same light/dark mechanism (`:root`, `@media (prefers-color-scheme: dark)` guarded by
`:root:not([data-theme="light"])`, `:root[data-theme="dark"]`).

### Colour

Host hues keep the values the scene already uses (so 2D, 3D, legend and table agree).
Contrast measured against the panel colour (WCAG 1.4.11 needs 3:1 for graphics):

| Token | Light | on `#ffffff` | Dark | on `#1d1f25` | Use |
|---|---|---|---|---|---|
| `--host-braid` | `#5b7db1` | 4.19 | `#5b7db1` | 3.93 | bars, legend swatch (series, never state) |
| `--host-claude` | `#b0794f` | 3.69 | `#b0794f` | 4.47 | idem |
| `--host-codex` | `#7a8f5a` | 3.56 | `#7a8f5a` | 4.63 | idem |
| `--state-conflict` | `#d1495b` | 4.36 | `#ff6b7d` (6.0) | | glyph and stroke only, always with an icon and a word |
| `--state-conflict-text` | `#b3243a` (6.5) | | `#ff6b7d` | 6.0 | text next to the glyph |
| `--state-attention` | `#b8860b` | 3.25 | `#e0a100` | 7.27 | unverified, unknown, gap markers (icon, never fill) |
| `--state-ok` | `#1d7a6f` (5.17) | | `#3fc1b0` | 7.42 | independent-candidate glyph; never "safe" |
| `--ink`, `--ink-muted` | `--text`, `--muted` | 6.93 for muted | existing | 6.49 muted | all text, including bar labels (ink, not series colour) |

Rules: host colour is a series colour and never encodes status or risk; status and
conflict colours are reserved and never used for series (dataviz lens); bar and glyph
text is ink on the panel, never white on a series fill. The three host hues are
categorical and must stay distinguishable in grayscale by the bar pattern and the
lane label, not by hue alone; T058 validates the palette in both themes with the
dataviz palette validator and records the result as evidence. Values above were
computed from the hex codes, not from a screenshot; contrast over a blended or
translucent surface must be re-measured.

### Type

System font stack (unchanged, platform optical sizing is free). Scale in `rem` so user
text-size settings scale the layout; line-height and tracking vary with size.

| Token | Size | Line height | Tracking | Weight | Use |
|---|---|---|---|---|---|
| `--t-display` | 1.375rem | 1.15 | -0.01em | 650 | page title |
| `--t-title` | 1rem | 1.3 | 0 | 600 | section title |
| `--t-body` | 0.875rem | 1.45 | 0 | 400 | text, table |
| `--t-label` | 0.8125rem | 1.35 | 0.01em | 500 | chips, lane labels, buttons |
| `--t-meta` | 0.75rem | 1.35 | 0.02em | 500 | axis ticks, durations |

Minimum interactive text 13 px; no text under 12 px. `font-variant-numeric:
tabular-nums` on every duration, tick, counter and table number. `text-wrap: balance`
on titles. Use `…` not `...`, curly quotes, a non-breaking space between number and
unit (`44 s`, `1 min 26 s`). Identifiers and file names carry `translate="no"`.

### Space, radius, elevation, size

| Token | Value |
|---|---|
| `--s-1 … --s-6` | 4, 8, 12, 16, 24, 32 px |
| `--r-sm`, `--r-md`, `--r-pill` | 4, 8, 999 px |
| `--hit-min` | 44 px for primary controls (WCAG 2.5.5 target); 32 px minimum with 8 px spacing for dense toolbars on pointer-fine devices |
| `--lane-h` | 28 px (compact), 40 px (comfortable); lane bar 14 px |
| `--elev-1` | `0 1px 2px` at 8 % ink (tooltip, sticky detail); borders, not shadows, separate structure |

Translucency only for floating chrome (the scene HUD and tooltips), with
`backdrop-filter` and a solid fallback under `prefers-reduced-transparency: reduce`
and `prefers-contrast: more`. Never stack a light translucent surface on another.

### Motion

| Token | Value | Use |
|---|---|---|
| `--ease-out` | `cubic-bezier(0.23, 1, 0.32, 1)` | enter, selection, tooltip |
| `--ease-in-out` | `cubic-bezier(0.77, 0, 0.175, 1)` | on-screen movement (view switch, camera preset) |
| `--dur-press` | 120 ms | button press (`scale(0.97)` on `:active`) |
| `--dur-fast` | 160 ms | hover, tooltip, chip |
| `--dur-base` | 220 ms | panel, camera move (cap 300 ms) |

Rules: animate only `transform` and `opacity`; never `transition: all`; no animation
on keyboard-initiated actions repeated often (arrow-key stepping, playback stepping,
view toggle by keyboard); tooltips appear after a short delay and the next one opens
instantly with no animation; popovers and tooltips scale from their anchor
(`transform-origin` at the anchor), not from the centre; nothing enters from
`scale(0)`; exits are faster than enters; transitions rather than keyframes for
anything the user can trigger repeatedly (retarget, never restart); pointer drags in
2D and 3D track 1:1 with pointer capture; camera moves ease out and are interruptible
(a new input retargets from the current pose). `prefers-reduced-motion: reduce`
replaces movement with an opacity cross-fade or an instant change; the live "now"
cursor stops pulsing and the camera jumps. The pulsing material loops of the scene run
only for the selected or hovered element (audit P2-3).

## Page structure (sections, titles, order)

Top to bottom at 1100 px and wider (wireframe:
[audit/wireframes/01-layout-desktop.txt](audit/wireframes/01-layout-desktop.txt)).
The essential task (see the timeline, select a lane, read its detail) fits one screen
without scrolling at 1440 x 900.

| # | Region | Element and role | Title (es / en) | Content |
|---|---|---|---|---|
| 1 | Header (`<header>`) | `h1` | "Actividad de agentes" / "Agent activity" | one-line summary built from the model: duration, agents, conflicts, gaps; connection chip (live or replay) |
| 2 | Boundary strip | `role="note"` strip, one line | "Solo lectura · no autoriza ejecución" / "Read-only · does not authorize execution" | keeps `executionAuthorization: false` visible; link "About this view" opens the panel with the full text (OD-V2 option b) |
| 3 | Toolbar (`role="toolbar"`) | view switch, filters | "Vista", "Filtros" | segmented control `Línea de tiempo | Mapa 3D`; filter menus Sources, Agent, Status; toggle "Solo problemas" |
| 4 | Main view | `<section aria-labelledby>` | "Línea de tiempo" / "Timeline" or "Mapa espacial 3D" / "Spatial 3D map" | 2D or 3D, never both rendered at once |
| 5 | Detail panel | sticky `<aside>`; bottom sheet under 700 px | "Detalle" / "Details" | selected lane or event; Esc deselects |
| 6 | Playback bar | `role="group"` | "Reproducción" / "Playback" | step, play, speed, position `0:52 / 4:22`, "Ir a ahora" |
| 7 | Tabs | `role="tablist"` | "Eventos", "Resumen", "Leyenda", "Ayuda" | table (text alternative), counters and "not shown as clean", legend, help and about |

Heading hierarchy is `h1` (page), `h2` (section), `h3` (inside panels); a skip link
("Saltar a la vista principal") is first in the tab order; every region has an
accessible name. Section order in the DOM equals the visual order.

Titles name the user's thing, not the model's: "Mapa espacial 3D" replaces "Braid
scene (3D)"; "Eventos" replaces "Events"; "Resumen" replaces "Counters"; "No se
muestra como limpio" replaces "Not shown as clean" in the summary tab; "Fuentes"
replaces "Event sources". "Strand" is never user-facing: the word is "agente" (a
lane may be a main session, a subagent, a unit of work or a Codex thread; the lane
label says which).

## Components

Each component lists variants, states and accessibility. All states exist on every
interactive component: default, hover (pointer-fine only), focus-visible (3 px ring,
existing), active, disabled, selected.

| Component | Variants and states | Accessibility and behaviour |
|---|---|---|
| **Button** | primary (one per region), secondary (default), quiet (icon plus label on wide screens); `aria-pressed` for toggles; press feedback `scale(0.97)` | native `<button>`; icon-only buttons need `aria-label` and a tooltip; minimum target above; label is verb plus object |
| **Segmented control** (view switch) | 2 options, one selected | `role="radiogroup"` with native radios; arrow keys move and select; the choice is stored in the URL hash and in per-browser storage (try/catch) |
| **Chip** | filter chip (toggle), status chip (read-only), source chip with count | status chips always carry an icon and a word; filter chips are `<button aria-pressed>` |
| **Lane label** | main, child (indented), ordinal "track-runner #2", status icon, duration | fixed at the left edge, truncates with a tooltip and the full name in the detail panel |
| **Bar** | finished (solid), running (hatched, arrow at the open end), unobserved end (dotted), waiting segments (hatched light) | pattern plus end glyph, never colour alone; `aria-label` "Explore, finished, 0:08 to 0:52, 44 s" |
| **Glyph set** | conflict predicted, conflict observed, independent candidate, ordered, unknown, hazard (observed, not observed), gate, grant, gap, unverified | one SVG symbol each, defined once and reused by timeline, legend, 3D HUD and table so all four agree |
| **Tooltip** | follows the pointer or the focused element; 8 px offset; hover delay 400 ms then instant for neighbours | also opened by keyboard focus; never the only place a fact lives; content is the same as the first lines of the detail panel |
| **Detail panel** | empty, lane, event, conflict | sticky; focus is not moved on selection (it is moved only by "Ver detalle"); lists the model fields behind a "Campos del modelo" disclosure |
| **Legend** | compact line (bottom of the main view) and full list (tab) | each entry is a real glyph plus a short sentence plus a count; clicking toggles the matching filter; the long governance sentences move to "Ayuda" |
| **Help overlay** | opened by `?` or the "Ayuda" button | `role="dialog"`, focus trapped, Esc closes, returns focus to the trigger; lists pointer, touch and keyboard controls for the active view |
| **Empty and error states** | no events yet, no WebGL, replay ended, source hidden | what it is, why it is empty, how to start; the table and timeline remain usable without WebGL |
| **Toast** | none planned | status changes go to a polite live region (`aria-live="polite"`), not to transient popups |

## Copy guide

Voice: plain, direct, second person where the user acts, active voice, no model
jargon, numerals for counts, sentence case for buttons and titles in Spanish (Title
Case in English UI strings). A message says what happened, why and what to do. The
non-claim is stated once in the strip and once in "Ayuda"; elsewhere wording is
descriptive and conditional ("según el análisis", "no verificado").

UI language is decided (OD-V1 as accepted 2026-11-04, see owner-decisions.md): detected
from the browser or desktop-app locale, then the `view serve` process locale, then
English, with a manual choice. All strings live in one module (`strings.js`) as `es` and
`en` tables with a key-parity test. Terms below are the single vocabulary.

| Concept | es | en | Do not say |
|---|---|---|---|
| strand / lane | agente (fila: "Carril" only in help) | agent | strand, hebra |
| lane main | sesión principal | main session | root |
| lane child | subagente | subagent | child strand |
| running / waiting / finished | en curso / esperando / terminado | running / waiting / finished | active, done, success |
| inferred state | "(inferido)" suffix | "(inferred)" | omitted |
| outcome unknown | resultado desconocido | outcome unknown | success (never invented) |
| predicted conflict | posible conflicto (según el análisis) | possible conflict (per analysis) | conflict that occurred |
| observed collision | colisión observada | observed collision | merge conflict (unless the source says so) |
| independent candidate | candidato a independiente | independent candidate | safe, parallelizable |
| ordered | con orden | ordered | sequential guarantee |
| unknown pair | sin clasificar | unclassified | clean |
| unverified | no verificado | unverified | fake, untrusted |
| observation gap | hueco de observación | observation gap | missing, error |
| compressed time | tiempo omitido: 6 min 20 s | omitted time: 6 min 20 s | silent break |
| now | ahora | now | live (as a noun) |
| duration | duración | duration | latency |
| tool duration | duración de la herramienta | tool duration | runtime (ambiguous) |
| gap between events | intervalo entre eventos | time between events | duration |

Buttons and controls (verb plus object, specific):

| Context | es | en | Notes |
|---|---|---|---|
| View switch | Línea de tiempo / Mapa 3D | Timeline / 3D map | |
| Reset the camera | Encuadrar (F) | Frame all (F) | replaces "Reset view"; also resets zoom |
| Camera presets | Lateral, Cenital, Isométrica | Side, Top, Isometric | |
| Help | Ayuda (?) | Help (?) | opens overlay |
| Playback | Inicio, Paso atrás, Reproducir, Pausar, Paso adelante, Ir a ahora | Start, Step back, Play, Pause, Step forward, Go to now | the play button label changes with state |
| Speed | Por eventos / Tiempo real ×1 ×2 ×4 | By events / Real time ×1 ×2 ×4 | audit P2-1 |
| Filters | Fuentes, Agente, Estado, Solo problemas | Sources, Agent, Status, Problems only | menus show counts |
| Clear | Quitar filtros | Clear filters | disabled when none |
| Detail | Ver evidencia | View evidence | |
| About | Acerca de esta vista | About this view | |

Messages:

| Situation | es | en |
|---|---|---|
| Empty (no events) | "Aún no hay actividad. Inicia el visor con --watch o abre un archivo de repetición y los agentes aparecerán aquí." | "No activity yet. Start the viewer with --watch or open a replay file and agents will appear here." |
| Source hidden | "Fuente oculta: 18 eventos. Siguen contando en el resumen; ocultarla no significa que no exista." | "Source hidden: 18 events. They still count in the summary; hiding a source does not mean it is absent." |
| No WebGL | "El mapa 3D necesita WebGL, que este navegador no ofrece. La línea de tiempo y la tabla muestran los mismos eventos." | "The 3D map needs WebGL, which this browser does not provide. The timeline and the table show the same events." |
| Stale live data | "Sin datos nuevos desde hace 30 s. El visor sigue conectado." | "No new data for 30 s. The viewer is still connected." |
| Disconnected | "Conexión perdida. Reintentando… Los eventos ya recibidos siguen visibles." | "Connection lost. Retrying… Events already received stay visible." |
| Tooltip, predicted conflict | "Posible conflicto: Edit ROADMAP y Second ROADMAP edit comparten ROADMAP.md según el análisis. No implica que ocurriera." | "Possible conflict: Edit ROADMAP and Second ROADMAP edit share ROADMAP.md per the analysis. It does not mean it happened." |
| Tooltip, observed collision (phase 4) | "Colisión observada: dos agentes tocaron ROADMAP.md en el mismo periodo." | "Observed collision: two agents touched ROADMAP.md in the same period." |
| Axis break | "Tiempo omitido: 6 min 20 s" | "Omitted time: 6 min 20 s" |
| Boundary strip | "Solo lectura · no autoriza ejecución" | "Read-only · does not authorize execution" |

Resource names in these messages are `sharedResources` ids rendered as text; where an
id is not a readable name the UI shows "recurso 3" and the evidence panel shows the
relative path (never an absolute path).

## Accessibility baseline (WCAG 2.1 AA, plus 2.2 where cheap)

- Every function has a keyboard path; gestures (drag, wheel, pinch) have button and
  key alternatives. 2D bars: roving tabindex over a `role="listbox"` of agents, arrow
  keys move between bars, Enter selects; the table remains the complete text
  alternative and shares selection.
- Focus order follows the DOM order above; sticky regions never cover the focused
  element (`scroll-padding`); focus is visible (existing 3 px) in forced-colors mode.
- Status is exposed as text and role, not only colour; a polite live region announces
  selection and live changes at most once per second.
- Contrast: text 4.5:1, graphics 3:1 (table above); targets as in tokens; page
  reflows at 320 CSS px and at 200 % zoom without horizontal page scroll (the timeline
  scrolls inside its own region, with keyboard-reachable scroll).
- Honour `prefers-reduced-motion`, `prefers-reduced-transparency`, `prefers-contrast`,
  `forced-colors`; no `user-scalable=no`; `color-scheme` and `theme-color` follow the
  active theme.
- `touch-action: manipulation` on controls; the 3D canvas uses `pan-y` by default on
  touch so the page scrolls, with an explicit "lock scene" toggle for one-finger orbit.
- Verified only by automated checks plus manual keyboard review in this plan; a
  VoiceOver pass of the "select a conflict" flow is a closure task (T066). No claim of
  screen-reader verification exists today.
