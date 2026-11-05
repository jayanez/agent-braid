# VIS.1d — Loom viewer dashboard relaunch (plan)

Planning package for a fourth delivery of SPEC-061 (track VIS.1). Dated 2026-11-05.
Nothing here implements the viewer. The tasks T068 to T074 in [tasks.md](../tasks.md)
are unticked. The owner chose the full dashboard and the redone 3D view (see
"Owner decision").

## Why

The owner judged the viewer very poor before VIS.1c ("no es nada intuitiva la
visualización ni el manejo de la vista 3D… Me parece de muy poca calidad para el
usuario final", 2026-11-04). The owner still judged it very poor after VIS.1c
(T050 to T062) was merged. On 2026-11-05 the owner asked for two things. The viewer
must impress the owner and anyone who sees or uses it. Its page and panels must
follow a dashboard structure.

VIS.1c was planned through about eight overlapping design lenses. That gave
checklist compliance without one direction. VIS.1d uses one direction, written in
[direction.md](direction.md), and one audit pass (Web Interface Guidelines). The
VIS.1c lens findings are history only, not rules.

## What the baseline shows

The baseline was taken on a private instance (port 8791, its own `--runtime-dir`).
The data was synthetic but has the real shapes: five analysis reports from
`agent-braid analyze` (one wave of six operations with dependencies and a shared
write) and Claude-shaped hook traffic for four sessions and three subagents. See
`evidence/before-*.png` (1440×900 and 390×844, dark and light, timeline and 3D).

1. **Plans and live work share one axis.** The analysis reports carry no times, so
   the whole timeline falls back to event order. Planned operations then look like
   bars that never end. Live sessions are pushed into the right third.
2. **The answers are hidden.** Counters, agents and conflicts sit in a "Summary"
   tab below the fold. The header shows one grey sentence.
3. **Lanes cannot be told apart.** The labels read "Claude session #1…#3" with no
   stable short id. In the 3D view they read "Claude session" three times (T064).
4. **Too many words.** Six paragraphs explain the views, and governance text
   appears three times on the first screen.
5. **The 3D view adds no insight.** It shows the same lanes in perspective, with
   "class 0" and "class 1" text labels where pairs cross.
6. **The mobile layout is a squeezed desktop layout.** The labels are cut off, and
   the conflicts overlap the lanes.

## Contents

| File | Purpose |
|---|---|
| [direction.md](direction.md) | The one design direction: the dashboard layout, the live loom, the plan map, tokens, type, motion, copy, the empty, untimed and live states, the 3D Explore view |
| `evidence/before-*.png` | Baseline of `develop` at 28033846 on synthetic data with the real shapes |
| `evidence/mockup-*.png` | Static prototype of the direction (hand-entered data that mirrors the baseline instance) |

The requirements are REQ-024 to REQ-028 in the "VIS.1d amendment" section of
[spec.md](../spec.md). The tasks are T068 to T074 in [tasks.md](../tasks.md).

## Constraints kept

- No new vendored files (D10).
- The CSP stays as it is (`style-src 'self'`, no remote fonts or scripts).
- The server binds loopback only.
- The never-collect list and the hook allowlist do not change.
- Tool duration is shown live only (OD-V4).
- Predicted and observed conflicts use two distinct visual languages (D8).
- When there is no observed-collision source, no counter and no zero is shown
  (SC-023).
- es/en detection and key parity stay as they are (OD-V1).
- The read-only statement stays, as one quiet line plus the About panel (OD-V2).
- The `BUNDLE_FILES` pin test is kept current.

Files that are deliberately not edited: `STATUS.md`, `ROADMAP.md`, the milestone
index, `github-tracking.json`, `CONSTITUTION.md`, the ADRs, and
`specs/065-*` and SPEC-068. `contracts/ui-security-privacy.md` is edited only by
the separate reviewed amendment that T067 needs.

## Owner decision (recorded 2026-11-05)

The owner answered through the orchestrator session; the labels are verbatim.

| Question | Answer | Effect |
|---|---|---|
| «¿Con qué alcance construyo el relanzamiento tipo dashboard del visor Loom?» | "Dashboard + 3D renovado (Recomendado)" | Option 1: the full dashboard and the redone 3D Explore view, plus T064, T065 and T067. **OD-V6 (3D frozen) is reopened** for T072: eased camera presets, fly-to-selected and reset always visible, with no new vendored file and no new data. |
| «¿Puede la otra sesión fusionar el plan (PR #1085, solo documentación) cuando el CI esté en verde?» | "Sí, fusionar con CI verde" | This plan merges once CI is green. |

The owner saw the before captures and the mockups. T068 to T074 are authorized in
this scope. The contract amendment that T067 needs is still a separate, reviewed
change.

### Closure (recorded 2026-11-05)

The owner accepted the VIS.1d closure (T074) with one caveat: the VoiceOver pass of T073
stays pending and does not block. T063 and T064 are paused until the owner resumes them.
T035 waits for real use, with opt-in usage telemetry (T075) and a review on 2026-11-19.
Record: [owner-review-vis1d-closure-20261105.json](../owner-review-vis1d-closure-20261105.json).

## Evidence boundary

The `before-*` screenshots are captures of synthetic input generated on this
machine. The `mockup-*` images are illustrations of a static prototype with
hand-entered data; they are not captures of the viewer. They are not
real-use evidence and grant no approval. No owner results were read or copied.
