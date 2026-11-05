# VIS.1d direction: "Loom" dashboard

The direction has one idea: **separate what is happening from what was planned, and
answer the owner's four questions before the user scrolls.**

The four questions are:

- Who is running now?
- Who is waiting on whom?
- What collided, or may collide?
- How long did things take?

## Page structure (dashboard)

```
┌ App bar: mark, "Agent activity", live clock │ Loom | 3D │ ES · ? ──────────────┐
├ Now: one plain sentence that answers the four questions                               ┤
├ KPI strip: Running │ Waiting │ May collide │ Collided* │ Longest tool call              ┤
├ Filter chips: All agents · Running · Waiting · Problems │ Live sessions · Plans         ┤
├─────────────────────────────────────────────────────────────┬──────────────────────────┤
│ Live sessions (HERO): live loom, ruler, now edge,           │ Details rail: selection, │
│ playback docked at the bottom                               │ facts, recent tools,     │
│                                                             │ source and verification  │
├────────────────────────────┬──────────────┬─────────────────┤                          │
│ Plan map: operations,      │ Collisions:  │ How long:       │                          │
│ pairs (may collide, must   │ predicted vs │ running and     │                          │
│ wait, independent)         │ observed     │ waiting per lane│                          │
├────────────────────────────┴──────────────┴─────────────────┴──────────────────────────┤
│ Events table (collapsible, full width): complete text alternative                      │
└ "Read-only. This viewer never starts, schedules or changes work." About this view ─────┘
```

\* The "Collided" tile appears only when an observed-collision source exists
(SC-023). Without one, the tile is not rendered at all, so there is no counter
and no `0`.

Every element drives the same state (`state.js`) and its selection.

- A KPI tile applies its filter.
- A noun in the Now sentence selects that agent or pair.
- A plan node, a collision row or a duration bar selects its element in the loom,
  the details rail and the table.
- The URL hash restores the view, the selection and the filters, as it does today.

| Width | Layout |
|---|---|
| ≥ 1280 px | The full 12-column grid. Hero 9 columns, rail 3. Bottom row: plan 5, collisions 2, durations 2. |
| 768–1279 px | The rail becomes a drawer opened by a selection. The bottom panels go two per row. |
| < 768 px | The KPI strip and the chips scroll sideways. The loom scrolls sideways at a minimum width of 760 px, with labels kept on the left. The panels stack. Details open as a bottom sheet. Playback stays pinned. |

## The hero: the live loom

This is where the boldness is spent.

- Each session and subagent is a **thread**: one line on a real time axis. Planned
  operations never appear here.
- **Running:** a 3 px line in the running hue with a soft glow. The glow is an SVG
  filter in user space units. Without that, a horizontal line has a zero-height box
  and the glow disappears.
- **Waiting:** a dotted amber line. A fine dashed tether curves back to the thread
  it waits on, using `waitingOn` when it is known. When the wait is declared or
  inferred, the tether says so in the details rail.
- **Finished:** a muted grey line.
- A **subagent** branches off its parent with a curve and rejoins it with a curve
  when it stops.
- **Tool calls** are beads on the thread. The longest call is a filled bead. Hovering
  a bead shows the tool name and its live duration.
- **Now** is a dashed vertical edge. Running threads grow into it.
- **Selection:** the selected lane gets a tinted row, and the other lanes dim to 35 %
  when the user hovers one lane.
- **Observed collision** (once T063 exists): a solid red knot joins the two threads
  at that moment. **Predicted conflict** never appears on the loom; it lives in the
  plan map (D8). This keeps the two visual languages apart.
- **One orchestrated moment:** on the first load, the threads draw in from left to
  right in about 700 ms (stroke-dashoffset). The Now sentence counts are already in
  place. With `prefers-reduced-motion`, everything is drawn at once.

## The plan map

Analysis reports carry no times, so each plan gets its own panel instead of a fake
timeline.

- **Columns:** operations are placed in dependency order (column = depth in
  `dependencies`).
- **Edges:** "May collide" is a thick coral line with an open dashed ring.
  "Must wait" is violet. "Independent" is a faint teal line.
- **Hot nodes:** a node that takes part in a predicted conflict has a coral outline.
- **Several reports:** a selector shows how many plans there are and picks one. The
  newest is the default.
- **Untimed by design:** the panel never shows a duration for a plan.

## Tokens

| Token | Dark | Light | Use |
|---|---|---|---|
| ground | `#0d1220` | `#e9edf4` | page |
| panel | `#131a2b` | `#ffffff` | panels |
| panel-2 | `#182136` | `#f3f6fb` | raised rows, selected segment |
| line | `#243049` | `#d7deea` | borders, grid, empty tracks |
| ink / ink-2 / ink-3 | `#e7ecf5` / `#93a0b8` / `#5f6b84` | `#0f1830` / `#4d5a75` / `#7c88a1` | text levels |
| run | `#5aa9ff` | `#1f6fe0` | running (the one live hue) |
| wait | `#f2b54a` | `#b7791f` | waiting |
| predict | `#ff7a85` | `#d6404f` | may collide (outlined, dashed) |
| observed | `#ff3b4e` | `#c1121f` | collided (solid knot) |
| order / indep / done | `#a99cff` / `#3fc1a5` / `#6b7891` | `#6b5bd6` / `#1b8f78` / `#8a96ab` | pair classes, finished |

Every status colour sits next to a word or a distinct shape. Colour never carries
meaning alone. The existing palette test validates both themes, and the existing
3D colours map to these tokens.

## Type, density, copy, motion

- **Type:** the system UI stack only, because the CSP forbids remote fonts.
  - One family, with tabular figures everywhere.
  - Sizes: 26 px Now sentence, 30 px KPI value, 14 px body, 12 to 13 px meta.
  - No all-caps labels and no monospace meta strings.
- **Density:** one screen at 1440×900 holds the Now sentence, the KPIs, the filters,
  the loom and the rail. Panel headers hold a title, a count and at most one action.
  No help paragraphs on the page: those move to the "?" popover.
- **Copy:**
  - Sentence case and plain verbs, from the user's side ("May collide", "Must wait",
    "How long").
  - The governance meaning stays exact: "possible" and "predicted" for analysis,
    "collided" only for observed.
  - es and en with key parity.
- **Motion:** only the first-load draw-in and the advancing now edge. Hover and
  selection change instantly. Everything respects reduced motion.

## States

| State | What the page shows |
|---|---|
| Empty (no source yet) | The Now sentence reads "Nothing to show yet." and is followed by two plain actions: connect Claude Code hooks (the command from `view env`), or run `agent-braid analyze` on a plan. The panels show their empty line, never zeros. |
| Untimed only (reports, no hooks) | The loom panel says "No live sessions. Plans below are ordered, not timed." The plan map becomes the hero, and the KPI strip shows the plan counts. |
| Live | The clock ticks, the now edge advances, and playback follows now. Moving the scrubber pauses the follow mode and shows "Back to now". |
| Disconnected | The live pill turns grey with "Reconnecting…". The data stays on screen. |

## Lane labels (T064)

A hook lane reads **"Session" plus a short id**. The id is the first 5
characters of the salted strand hash, so it adds no new collected data. It is
stable within one server session (the salt is per session). On a collision, both
ids are lengthened until they differ. A subagent
lane reads its `agent_type` and "subagent of <parent short id>". Two lanes of the
same type also get the existing ordinal. Screen readers read the same text as the
visible label.

## Explore 3D

OD-V6 froze 3D to fixes only, so it offers two scopes.

- **Re-skin (inside OD-V6):**
  - Same tokens and thread styles.
  - T064 labels.
  - "class 0" and "class 1" text replaced by the plan-map glyphs.
  - Reset and fit always visible.
- **Explore (reopens OD-V6, owner choice):**
  - Time on x, lanes on y, concurrency in depth.
  - Eased camera presets and "fly to selected" (OrbitControls target tween).
  - Uses the r186 APIs already vendored, so there are no new files.

## Cross-cutting

- **T065 accessibility:**
  - Every panel is a landmark with a heading.
  - The loom lanes form a `listbox`, with arrow-key navigation and Enter to select.
  - The KPI tiles are buttons.
  - Focus rings are visible.
  - Contrast is measured again.
- **T067:** `agent-braid view open` asks the running server, over loopback and
  with an owner-only credential, for a fresh single-use open code. The page's read
  cookie never mints codes. This needs a contract amendment first.
