// SPDX-License-Identifier: AGPL-3.0-only
// Agent Braid activity viewer: the live loom (SPEC-061 VIS.1c REQ-017, VIS.1d REQ-025 and REQ-026, T069).
//
// A first-party SVG drawing of the live part of the shared derived model (state.js liveSubset): one thread per agent
// on a real time axis, children branching off their parent's thread and rejoining it when they stop, waiting stretches
// with a tether to the agent they wait on, tool calls as beads (the longest stated one filled), observation gaps,
// hazards, every compression drawn as a labelled break, the live "now" edge and the playback cursor. Plans (events
// that state no time) are not drawn here: they go to the plan map. On the first drawing the threads draw in once,
// unless the reader asked for reduced motion. It keeps no selection, filter or cursor of its own: `render` receives
// them and the user's actions go back through `hooks`.
//
// No third-party code and no markup strings: elements are made with createElementNS and a fixed allowlist of
// attribute names, every text is a text node, and nothing here reads the network. Glyphs are `<use>` references to the
// symbols defined once in index.html, the same ones the legend and the 3D map use.
//
import { formatClock, formatDuration, positioned } from "./state.js";

const NS = "http://www.w3.org/2000/svg";
const ALLOWED = new Set(["x", "y", "x1", "y1", "x2", "y2", "width", "height", "rx", "r", "cx", "cy", "d", "points", "transform",
  "class", "fill", "stroke", "stroke-width", "stroke-dasharray", "text-anchor", "dominant-baseline", "viewBox", "role", "tabindex",
  "aria-label", "aria-selected", "aria-hidden", "aria-orientation", "clip-path", "href", "data-tip", "data-lane", "data-seq", "id",
  "focusable", "preserveAspectRatio"]);

const ROW_HEIGHT = 46;
const RULER_HEIGHT = 34;
const GOVERNANCE_HEIGHT = 28;
const MIN_SPAN = 500;
const RIGHT_PAD = 28;
const LEFT_PAD = 14;
const HOVER_DELAY_MS = 400;

const CROSSING_GLYPH = {
  "conflicting": "g-conflict-predicted", "independent-candidate": "g-independent", "ordered": "g-ordered", "unknown": "g-unknown",
};
const OUTCOME_MARK = { ok: "✓", error: "✕", unknown: "?", cancelled: "⊘" };

function el(tag, attrs, ...children) {
  const node = document.createElementNS(NS, tag);
  for (const [name, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (!ALLOWED.has(name)) throw new Error("svg attribute not allowed: " + name);
    if (name === "href" && !/^#[A-Za-z0-9_-]+$/.test(String(value))) throw new Error("svg href must name a local symbol");
    node.setAttribute(name, String(value));
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function glyph(id, x, y, size, className) {
  return el("use", { href: "#" + id, x: x - size / 2, y: y - size / 2, width: size, height: size, class: className || null });
}

// A small inline icon that references one of the shared symbols (used by the legend line and the 3D HUD as well).
export function iconNode(id) {
  return el("svg", { class: "glyph-icon", viewBox: "0 0 16 16", "aria-hidden": "true", focusable: "false" },
    el("use", { href: "#" + id, x: 0, y: 0, width: 16, height: 16 }));
}

function clip(text, max) {
  return text.length > max ? text.slice(0, Math.max(1, max - 1)) + "…" : text;
}

export function createTimeline(container, hooks) {
  const t = (key, params) => hooks.t(key, params);
  const tooltip = document.createElement("div");
  tooltip.className = "tl-tooltip";
  tooltip.hidden = true;
  tooltip.setAttribute("role", "tooltip");
  const host = document.createElement("div");
  host.className = "tl-host";
  container.replaceChildren(host, tooltip);

  let input = null;
  let geometry = null;
  let focusedLane = null;
  let hoverTimer = null;
  let tooltipWarm = false;
  let drag = null;
  let dragged = false;
  let disposed = false;
  // the one orchestrated moment: threads draw in once, unless the reader asked for reduced motion
  let intro = !(typeof matchMedia === "function" && matchMedia("(prefers-reduced-motion: reduce)").matches);

  // ---------------------------------------------------------------- viewport

  function fullSpan() {
    return Math.max(input ? input.derived.axis.spanX : 0, 1000);
  }

  function currentRange() {
    const full = fullSpan();
    const view = input && input.viewport;
    if (!view || !(view.x1 > view.x0)) return [0, full];
    const from = Math.max(0, view.x0);
    const to = Math.min(full, view.x1);
    return to > from ? [from, to] : [0, full]; // a viewport outside the data (stale link) shows everything
  }

  function emitViewport(x0, x1) {
    const full = fullSpan();
    const span = Math.min(Math.max(x1 - x0, MIN_SPAN), full);
    let start = Math.max(0, Math.min(x0, full - span));
    if (span >= full - 1) start = 0;
    hooks.onViewport(span >= full - 1 ? null : { x0: start, x1: start + span });
  }

  function zoomAt(factor, centerX) {
    const [x0, x1] = currentRange();
    const center = centerX === undefined ? (x0 + x1) / 2 : centerX;
    const span = (x1 - x0) / factor;
    const ratio = (center - x0) / (x1 - x0);
    emitViewport(center - span * ratio, center - span * ratio + span);
  }

  function pan(deltaX) {
    const [x0, x1] = currentRange();
    emitViewport(x0 + deltaX, x1 + deltaX);
  }

  // ---------------------------------------------------------------- tooltip

  function showTip(target, event) {
    const text = target.getAttribute("data-tip");
    if (!text) return;
    const place = () => {
      tooltip.textContent = text;
      tooltip.hidden = false;
      const box = container.getBoundingClientRect ? container.getBoundingClientRect() : { left: 0, top: 0, width: 600 };
      let at = event ? event.clientX - box.left + container.scrollLeft + 12 : 40;
      const top = event ? event.clientY - box.top + container.scrollTop + 14 : 40;
      at = Math.max(4, Math.min(at, Math.max(4, box.width - 280)));
      tooltip.style.transform = "translate(" + Math.round(at) + "px, " + Math.round(top) + "px)";
      tooltipWarm = true;
    };
    clearTimeout(hoverTimer);
    if (tooltipWarm) place(); // the next tip after one is open appears at once
    else hoverTimer = setTimeout(place, HOVER_DELAY_MS);
  }

  function hideTip() {
    clearTimeout(hoverTimer);
    tooltip.hidden = true;
    hoverTimer = setTimeout(() => { tooltipWarm = false; }, 300);
  }

  function tip(node, text) {
    node.setAttribute("data-tip", text);
    node.addEventListener("pointerenter", (event) => showTip(node, event));
    node.addEventListener("pointermove", (event) => { if (!tooltip.hidden) showTip(node, event); });
    node.addEventListener("pointerleave", hideTip);
    return node;
  }

  // ---------------------------------------------------------------- drawing

  function emptyState() {
    const text = hooks.empty ? hooks.empty() : null;
    const box = document.createElement("div");
    box.className = "tl-empty";
    const strong = document.createElement("strong");
    strong.textContent = text ? text.title : t("tl.empty.title");
    box.append(strong, document.createTextNode(text ? text.body : ""));
    host.replaceChildren(box);
    geometry = null;
  }

  function draw() {
    if (!input || disposed) return;
    hideTip(); // the node under the pointer is about to be replaced
    const { model, derived, shown, cursorX, selected } = input;
    const rows = derived.rows.map((row) => derived.byIndex.get(row.laneIndex));
    if (!rows.length) { emptyState(); return; }
    // a phone scrolls the loom sideways instead of squeezing the time axis
    const width = Math.max(container.clientWidth || 720, 720);
    const narrow = (container.clientWidth || 720) < 560; // on a phone the duration leaves the label column; it stays in the tooltip and the details
    const labelW = narrow ? 132 : Math.round(Math.min(220, Math.max(150, width * 0.2)));
    const plotW = Math.max(width - labelW - LEFT_PAD - RIGHT_PAD, 100);
    const [x0, x1] = currentRange();
    const sx = (x) => labelW + LEFT_PAD + ((x - x0) / (x1 - x0)) * plotW;
    const governance = model.elements.filter((element) => shown.has(element.seq) && positioned(element) &&
      (element.element === "gate-ring" || element.element === "wave-marker" || element.element === "wave-plane"));
    const top = RULER_HEIGHT + (governance.length ? GOVERNANCE_HEIGHT : 0);
    const height = top + rows.length * ROW_HEIGHT + 10;
    const rowY = new Map(rows.map((lane, index) => [lane.laneIndex, top + index * ROW_HEIGHT]));
    const center = (lane) => rowY.get(lane.laneIndex) + ROW_HEIGHT / 2;
    const bySeq = new Map(model.elements.map((element) => [element.seq, element]));
    const minMs = derived.axis.minMs;
    const visibleLane = (lane) => shown.has(lane.openSeq);
    geometry = { labelW, plotW, x0, x1, sx, rowY, rows };

    const root = el("svg", { class: "tl-svg" + (intro ? " intro" : ""), viewBox: "0 0 " + width + " " + height, width, height, role: "group",
      "aria-label": t("tl.aria"), focusable: "false" });
    root.append(el("defs", null, el("clipPath", { id: "tl-clip" }, el("rect", { x: labelW, y: 0, width: plotW + LEFT_PAD + RIGHT_PAD, height }))));
    root.append(el("rect", { class: "tl-bg", x: labelW, y: 0, width: plotW + LEFT_PAD + RIGHT_PAD, height }));

    // breaks: a faint column through every lane and a zigzag with the omitted time on the ruler
    const layer = el("g", { "clip-path": "url(#tl-clip)" });
    for (const cut of derived.axis.breaks) {
      if (cut.x2 < x0 || cut.x1 > x1) continue;
      const a = sx(cut.x1);
      const b = Math.max(sx(cut.x2), a + 6);
      layer.append(el("rect", { class: "tl-break", x: a, y: RULER_HEIGHT - 6, width: b - a, height: height - RULER_HEIGHT + 6 }));
      const zig = "M" + a + " " + (RULER_HEIGHT - 2) + " l3 -4 l3 8 l3 -8 l3 8 l3 -4";
      layer.append(tip(el("path", { class: "tl-zigzag", d: zig, transform: "translate(" + ((b - a) / 2 - 7) + " 0)" }),
        t("tl.omitted", { text: formatDuration(cut.spanMs) })));
      if (b - a >= 26) {
        layer.append(el("text", { class: "tl-break-label", x: (a + b) / 2, y: RULER_HEIGHT - 14, "text-anchor": "middle" }, "⋯ " + formatDuration(cut.spanMs)));
      }
    }

    // ruler: elapsed time with a faint grid line per tick (the loom only ever draws events that state a time)
    if (derived.axis.sequence) root.append(el("text", { class: "tl-axis-label", x: 12, y: RULER_HEIGHT - 12 }, t("tl.axisSequence")));
    let lastLabelX = -Infinity;
    const nowAt = typeof derived.axis.nowX === "number" ? sx(derived.axis.nowX) : null;
    for (const tick of derived.axis.ticks(x0, x1)) {
      const x = sx(tick.x);
      layer.append(el("line", { class: "tl-grid", x1: x, y1: RULER_HEIGHT - 4, x2: x, y2: height - 6 }));
      if (x - lastLabelX < 48) continue; // a label too close to the previous one would overlap it
      if (nowAt !== null && x > nowAt - 64 && x < nowAt + 8) continue; // nor may it run into the "now" label
      lastLabelX = x;
      layer.append(el("text", { class: "tl-tick-label", x: x + 4, y: RULER_HEIGHT - 12 }, tick.label));
    }

    // governance row, only when something sits on it: grants, gates and wave markers at their position
    const govY = RULER_HEIGHT + GOVERNANCE_HEIGHT / 2;
    for (const element of governance) {
      const id = element.element === "gate-ring" ? (element.ringKind === "grant" ? "g-grant" : "g-gate") : element.element === "wave-marker" ? "g-wave" : "g-wave-plan";
      const x = sx(element.x);
      const label = element.element === "gate-ring"
        ? t(element.ringKind === "grant" ? "tl.tip.grant" : "tl.tip.gate", { subject: String(element.subject), status: String(element.status) })
        : t(element.element === "wave-plane" ? "tl.tip.wavePlan" : "tl.tip.waveMarker", { subject: String(element.subject) });
      const marker = el("g", { class: "tl-mark" + (selected === element.seq ? " selected" : ""), role: "button", tabindex: "-1", "aria-label": label },
        glyph(id, x, govY, 14, "gl"), el("rect", { class: "tl-hit", x: x - 9, y: govY - 10, width: 18, height: 20 }));
      marker.addEventListener("click", (event) => { event.stopPropagation(); hooks.onSelect(element.seq); });
      layer.append(tip(marker, label));
    }
    if (governance.length) root.append(el("text", { class: "tl-gov-label", x: 12, y: govY + 4 }, t("tl.governance")));
    root.append(layer);

    // lanes: one thread per agent; children branch off their parent's thread and rejoin it when they stop
    const listbox = el("g", { role: "listbox", "aria-label": t("tl.lanes"), "aria-orientation": "vertical" });
    const threads = el("g", { "clip-path": "url(#tl-clip)", "aria-hidden": "true" });
    const tabStop = rows.some((lane) => lane.laneIndex === focusedLane) ? focusedLane : rows[0].laneIndex;
    const selectedLane = selected === null ? null : rows.find((lane) => lane.openSeq === selected || lane.seqs.includes(selected));
    const longest = hooks.longestSeq ? hooks.longestSeq() : null;
    const drawn = [];
    for (const lane of rows) {
      const y = rowY.get(lane.laneIndex);
      const cy = y + ROW_HEIGHT / 2;
      const isDrawn = visibleLane(lane);
      const info = hooks.describe(lane);
      const row = el("g", { class: "tl-row" + (isDrawn ? "" : " pending") + (selectedLane === lane ? " selected" : "") + (lane.state === "finished" ? " finished-lane" : ""),
        role: "option", tabindex: lane.laneIndex === tabStop ? "0" : "-1", "aria-selected": selectedLane === lane ? "true" : "false",
        "aria-label": info.aria, "data-lane": lane.laneIndex });
      row.append(el("rect", { class: "tl-row-bg", x: 4, y: y + 2, width: width - 8, height: ROW_HEIGHT - 4, rx: 8 }));
      const indent = 12 + Math.min(lane.depth, 3) * 16;
      const room = Math.floor((labelW - indent - (narrow ? 8 : 52)) / 6.6);
      row.append(el("text", { class: "tl-label", x: indent, y: cy - 2 }, clip(info.name, room), el("title", null, info.name)));
      row.append(el("text", { class: "tl-sublabel", x: indent, y: cy + 13 }, clip(info.sub, room + 2)));
      if (!narrow) row.append(el("text", { class: "tl-duration", x: labelW - 6, y: cy + 4, "text-anchor": "end" }, info.duration));
      const plot = el("g", { "clip-path": "url(#tl-clip)" });
      if (isDrawn) {
        const startX = sx(lane.openX);
        const limit = cursorX === null ? lane.endX : Math.min(lane.endX, cursorX);
        const endX = Math.max(sx(Math.max(limit, lane.openX)), startX + 3);
        const closedShown = lane.closeSeq !== null && shown.has(lane.closeSeq);
        const status = closedShown ? "finished" : lane.state === "unknown" ? "unknown" : "running";
        // the thread, split where it waits; a wait names its target and basis only when the event states them (T061)
        const spans = lane.waitSpans.map((span) => ({ span, from: sx(span.fromX),
          to: sx(span.toX === null ? Math.max(limit, span.fromX) : Math.min(span.toX, Math.max(limit, span.fromX))) }))
          .filter((item) => item.to > item.from || item.span.open);
        let at = startX;
        const pieces = [];
        for (const item of spans) {
          if (item.from > at) pieces.push({ from: at, to: item.from, kind: status });
          pieces.push({ from: Math.max(item.from, at), to: Math.max(item.to, item.from + 2), kind: "waiting", span: item.span });
          at = Math.max(at, item.to);
        }
        if (endX > at) pieces.push({ from: at, to: endX, kind: status });
        for (const piece of pieces) {
          const d = "M" + piece.from + " " + cy + " H" + piece.to;
          if (piece.kind === "running") threads.append(el("path", { class: "thread-glow", d }));
          const path = el("path", { class: "thread " + piece.kind + (piece.span && piece.span.basis ? " basis-" + piece.span.basis : ""), d });
          if (intro && piece.kind !== "waiting" && path.style && typeof path.style.setProperty === "function") path.style.setProperty("--len", String(Math.ceil(piece.to - piece.from) + 2));
          if (piece.span) {
            const target = piece.span.waitingOn === null ? null : derived.byStrand.get(piece.span.waitingOn);
            const text = piece.span.waitingOn === null ? t("tl.tip.waitUnstated")
              : t("tl.tip.wait", { target: target ? hooks.nameOf(target) : piece.span.waitingOn, basis: t("wait.basis." + piece.span.basis) });
            plot.append(tip(path, text));
            if (target && rowY.has(target.laneIndex)) {
              const ty = center(target);
              const tx = piece.from - Math.min(48, Math.max(18, (piece.from - startX) / 2));
              threads.append(el("path", { class: "tether", d: "M" + piece.from + " " + cy + " C" + (piece.from - 14) + " " + cy + " " + (tx + 10) + " " + ty + " " + tx + " " + ty }));
            }
          } else {
            plot.append(tip(path, info.tip));
          }
        }
        // a child branches off its parent's thread and, once closed, rejoins it
        const parent = lane.parentLane === null ? null : derived.byIndex.get(lane.parentLane);
        if (parent && rowY.has(parent.laneIndex) && visibleLane(parent)) {
          const py = center(parent);
          const bx = Math.max(sx(parent.openX), startX - 26);
          threads.append(el("path", { class: "branch" + (status === "finished" ? " finished" : ""), d: "M" + bx + " " + py + " C" + (startX - 6) + " " + py + " " + (startX - 12) + " " + cy + " " + startX + " " + cy }));
          if (status === "finished") {
            const ex = endX;
            threads.append(el("path", { class: "branch finished", d: "M" + ex + " " + cy + " C" + (ex + 12) + " " + cy + " " + (ex + 6) + " " + py + " " + (ex + 26) + " " + py }));
          }
        }
        // T062: tool calls are beads; a duration only when the host stated it, else the interval, labelled as such
        for (const mark of lane.toolMarks) {
          if (!shown.has(mark.seq)) continue;
          const x = sx(mark.x);
          const params = { name: mark.toolName, time: mark.timeKnown ? formatClock(mark.ms - minMs) : "#" + mark.seq };
          const text = mark.durationMs !== null ? t("tl.tip.toolDuration", { ...params, text: formatDuration(mark.durationMs) })
            : mark.intervalMs !== null ? t("tl.tip.toolInterval", { ...params, text: formatDuration(mark.intervalMs) })
              : t("tl.tip.tool", params);
          const isLongest = longest === mark.seq;
          plot.append(tip(el("circle", { class: "bead" + (mark.durationMs !== null ? " stated" : "") + (isLongest ? " longest" : ""), cx: x, cy, r: isLongest ? 5 : 3.5 }), text));
        }
        if (closedShown && lane.outcome !== "ok") {
          plot.append(el("text", { class: "tl-outcome outcome-" + lane.outcome, x: endX + 6, y: cy + 4 }, OUTCOME_MARK[lane.outcome] || "?"));
        }
        for (const gap of lane.gaps) {
          if (!shown.has(gap.seq) || !positioned(gap)) continue;
          plot.append(tip(el("g", { class: "tl-gap" }, glyph("g-gap", sx(gap.x), cy, 14, "gl")), t("tl.tip.gap", { reason: String(gap.reason) })));
        }
        for (const seq of lane.seqs) {
          const element = bySeq.get(seq);
          if (!element || !shown.has(seq) || element.element !== "hazard-cone" || !positioned(element)) continue;
          const x = sx(element.x);
          const id = element.absence ? "g-hazard-unobserved" : "g-hazard-observed";
          // inside an option the marker is not a control: it is reached with Left and Right and named by the row
          const hazardText = t("tl.tip.hazard", { kind: String(element.hazardKind), observed: t(element.absence ? "tl.notObserved" : "tl.observed") });
          const mark = el("g", { class: "tl-mark hazard" + (selected === seq ? " selected" : ""), "aria-hidden": "true" },
            glyph(id, x, cy - 13, 13, "gl"), el("rect", { class: "tl-hit", x: x - 8, y: cy - 22, width: 16, height: 14 }));
          mark.addEventListener("click", (event) => { event.stopPropagation(); if (!dragged) hooks.onSelect(seq); });
          plot.append(tip(mark, hazardText));
        }
      }
      row.append(plot);
      row.addEventListener("click", () => { if (!dragged && isDrawn) hooks.onSelect(lane.openSeq); });
      row.addEventListener("focus", () => { focusedLane = lane.laneIndex; });
      row.addEventListener("pointerenter", () => { if (root.classList) root.classList.add("lens"); });
      row.addEventListener("pointerleave", () => { if (root.classList) root.classList.remove("lens"); });
      drawn.push(row);
    }
    listbox.append(...drawn);
    root.append(threads, listbox);

    // crossings that state a time: a connector between the two agents' rows (plans live in the plan map)
    const connectors = el("g", { class: "tl-connectors", "clip-path": "url(#tl-clip)" });
    for (const crossing of derived.crossings) {
      if (!shown.has(crossing.seq) || !crossing.positioned || crossing.lanes.length < 2) continue;
      const [a, b] = crossing.lanes.map((index) => derived.byIndex.get(index));
      if (!a || !b || !rowY.has(a.laneIndex) || !rowY.has(b.laneIndex)) continue;
      const x = sx(crossing.x);
      const ya = center(a);
      const yb = center(b);
      const id = CROSSING_GLYPH[crossing.classification] || "g-unknown";
      const kind = crossing.kind === "predicted" ? "predicted" : crossing.classification;
      const text = hooks.crossingTip(crossing);
      const group = el("g", { class: "tl-cross cls-" + kind + (selected === crossing.seq ? " selected" : ""), role: "button", tabindex: "-1", "aria-label": text });
      group.append(el("line", { class: "tl-link", x1: x, y1: ya, x2: x, y2: yb }));
      const mid = (ya + yb) / 2;
      group.append(glyph(id, x, mid, 18, "gl"), el("rect", { class: "tl-hit", x: x - 11, y: mid - 11, width: 22, height: 22 }));
      if (crossing.kind === "predicted") {
        const flip = x + 110 > labelW + LEFT_PAD + plotW;
        group.append(el("text", { class: "tl-cross-word", x: flip ? x - 14 : x + 14, y: mid + 4, "text-anchor": flip ? "end" : null }, t("tl.conflictWord")));
      }
      group.addEventListener("click", (event) => { event.stopPropagation(); hooks.onSelect(crossing.seq); });
      connectors.append(tip(group, text));
    }
    root.append(connectors);

    // T060: the live "now" edge, from the server clock advanced by the page clock; running threads grow into it
    const nowX = derived.axis.nowX;
    if (typeof nowX === "number" && nowX >= x0 && nowX <= x1) {
      const x = sx(nowX);
      const now = el("g", { class: "tl-now" },
        el("line", { class: "tl-now-line", x1: x, y1: RULER_HEIGHT - 4, x2: x, y2: height - 6 }),
        el("text", { class: "tl-now-label", x: x - 4, y: RULER_HEIGHT - 12, "text-anchor": "end" }, t("tl.now")));
      root.append(tip(now, t("tl.tip.now", { time: formatClock(derived.axis.nowMs - minMs) })));
    }

    // playback cursor, one line across every lane
    if (cursorX !== null && cursorX >= x0 && cursorX <= x1) {
      root.append(el("line", { class: "tl-cursor", x1: sx(cursorX), y1: RULER_HEIGHT - 4, x2: sx(cursorX), y2: height - 6 }));
    }

    const hadFocus = typeof document !== "undefined" && container.contains && document.activeElement && container.contains(document.activeElement);
    host.replaceChildren(root);
    intro = false; // the draw-in plays once, on the first drawing with agents
    if (hadFocus && focusedLane !== null) focusLane(rows.some((lane) => lane.laneIndex === focusedLane) ? focusedLane : rows[0].laneIndex, true);
  }

  // ---------------------------------------------------------------- keyboard

  function laneNodes() {
    return host.querySelectorAll ? [...host.querySelectorAll("[role='option']")] : [];
  }

  // `quiet` restores focus after a redraw without scrolling the page (playback redraws on every step).
  function focusLane(index, quiet) {
    for (const node of laneNodes()) {
      const mine = Number(node.getAttribute("data-lane")) === index;
      node.setAttribute("tabindex", mine ? "0" : "-1");
      if (mine && node.focus) node.focus({ preventScroll: Boolean(quiet) });
    }
    focusedLane = index;
  }

  function onKey(event) {
    if (!input || event.ctrlKey || event.metaKey || event.altKey) return;
    const rows = geometry ? geometry.rows : [];
    const at = rows.findIndex((lane) => lane.laneIndex === focusedLane);
    const key = event.key;
    if (key === "ArrowDown" || key === "ArrowUp") {
      if (!rows.length) return;
      event.preventDefault();
      const next = key === "ArrowDown" ? Math.min(rows.length - 1, at + 1) : Math.max(0, at < 0 ? 0 : at - 1);
      focusLane(rows[Math.max(0, next)].laneIndex);
    } else if ((key === "Enter" || key === " ") && at >= 0) {
      event.preventDefault();
      if (input.shown.has(rows[at].openSeq)) hooks.onSelect(rows[at].openSeq);
    } else if ((key === "ArrowLeft" || key === "ArrowRight") && at >= 0) {
      event.preventDefault();
      const seqs = rows[at].seqs.filter((seq) => input.shown.has(seq));
      if (!seqs.length) return;
      const here = seqs.indexOf(input.selected);
      const next = key === "ArrowRight" ? Math.min(seqs.length - 1, here + 1) : Math.max(0, here < 0 ? 0 : here - 1);
      hooks.onSelect(seqs[next]);
    } else if (key === "+" || key === "=") {
      event.preventDefault();
      zoomAt(1.5);
    } else if (key === "-" || key === "_") {
      event.preventDefault();
      zoomAt(1 / 1.5);
    } else if (key === "0" || key === "f" || key === "F") {
      event.preventDefault();
      hooks.onViewport(null);
    } else if (key === "Home" || key === "End") {
      event.preventDefault();
      const [a, b] = currentRange();
      const full = fullSpan();
      if (key === "Home") emitViewport(0, b - a);
      else emitViewport(full - (b - a), full);
    }
  }

  function onWheel(event) {
    // the page scrolls over the timeline unless Ctrl or Cmd is held (a trackpad pinch arrives as Ctrl + wheel)
    if (!event.ctrlKey && !event.metaKey) return;
    event.preventDefault();
    if (!geometry) return;
    const box = host.getBoundingClientRect ? host.getBoundingClientRect() : { left: 0 };
    const [a, b] = currentRange();
    const x = a + ((event.clientX - box.left - geometry.labelW - LEFT_PAD) / geometry.plotW) * (b - a);
    zoomAt(Math.exp(-Math.max(-60, Math.min(60, event.deltaY)) * 0.01), x); // a pinch is many small events
  }

  // Pan by dragging anywhere on the plot. The handlers sit on the persistent host (the drawing is replaced on every
  // change), and a drag that moved swallows the click that follows it.
  function onPointerDown(event) {
    if (event.button !== 0 || !event.isPrimary || !geometry || event.clientX - (host.getBoundingClientRect ? host.getBoundingClientRect().left : 0) < geometry.labelW) return;
    drag = { id: event.pointerId, x: event.clientX, moved: false, start: currentRange() };
  }
  function onPointerMove(event) {
    if (!drag || drag.id !== event.pointerId) return;
    if (event.buttons === 0) { drag = null; return; }
    const dx = event.clientX - drag.x;
    if (!drag.moved && Math.abs(dx) < 4) return;
    if (!drag.moved && host.setPointerCapture) host.setPointerCapture(event.pointerId);
    drag.moved = true;
    dragged = true;
    const span = drag.start[1] - drag.start[0];
    const target = drag.start[0] - (dx / geometry.plotW) * span;
    emitViewport(target, target + span);
  }
  function onPointerEnd(event) {
    if (!drag || drag.id !== event.pointerId) return;
    drag = null;
    setTimeout(() => { dragged = false; }, 0); // after the click that ends the drag
  }
  host.addEventListener("pointerdown", onPointerDown);
  host.addEventListener("pointermove", onPointerMove);
  host.addEventListener("pointerup", onPointerEnd);
  host.addEventListener("pointercancel", onPointerEnd);
  host.addEventListener("lostpointercapture", onPointerEnd);
  container.addEventListener("keydown", onKey);
  container.addEventListener("wheel", onWheel, { passive: false });
  const observer = typeof ResizeObserver === "function" ? new ResizeObserver(() => draw()) : null;
  if (observer) observer.observe(container);

  return {
    // input: { model, derived, shown:Set, cursorX, selected, viewport }
    render(next) {
      input = next;
      draw();
    },
    zoomIn() { zoomAt(1.5); },
    zoomOut() { zoomAt(1 / 1.5); },
    frame() { hooks.onViewport(null); },
    dispose() {
      disposed = true;
      clearTimeout(hoverTimer);
      host.removeEventListener("pointerdown", onPointerDown);
      host.removeEventListener("pointermove", onPointerMove);
      host.removeEventListener("pointerup", onPointerEnd);
      host.removeEventListener("pointercancel", onPointerEnd);
      host.removeEventListener("lostpointercapture", onPointerEnd);
      container.removeEventListener("keydown", onKey);
      container.removeEventListener("wheel", onWheel);
      if (observer) observer.disconnect();
      container.replaceChildren();
    },
  };
}
