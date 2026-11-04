// SPDX-License-Identifier: AGPL-3.0-only
// Agent Braid activity viewer: the 2D timeline (SPEC-061 VIS.1c, REQ-017, T057).
//
// A first-party SVG drawing of the shared derived model (state.js): one row per agent (children under their parent),
// a time axis proportional to the model's compressed axis with every compression drawn as a labelled break, bars with
// a state pattern and an outcome glyph, tool ticks, waiting stretches, observation gaps, hazards, the predicted conflict
// and the other classified pairs as connectors with glyphs, a concurrency band and the playback cursor. It keeps no
// selection, filter or cursor of its own: `render` receives them and the user's actions go back through `hooks`.
//
// No third-party code and no markup strings: elements are made with createElementNS and a fixed allowlist of
// attribute names, every text is a text node, and nothing here reads the network. Glyphs are `<use>` references to the
// symbols defined once in index.html, the same ones the legend and the 3D map use.
//
// When any event states no time the axis is the event order (state.js, placeBySequence): the ruler names sequence
// numbers, every event has its own slot and no duration is drawn or derived from a slot.

import { formatClock, formatDuration, positioned } from "./state.js";

const NS = "http://www.w3.org/2000/svg";
const ALLOWED = new Set(["x", "y", "x1", "y1", "x2", "y2", "width", "height", "rx", "r", "cx", "cy", "d", "points", "transform",
  "class", "fill", "stroke", "stroke-width", "stroke-dasharray", "text-anchor", "dominant-baseline", "viewBox", "role", "tabindex",
  "aria-label", "aria-selected", "aria-hidden", "aria-orientation", "clip-path", "href", "data-tip", "data-lane", "data-seq", "id",
  "focusable", "preserveAspectRatio"]);

const ROW_HEIGHT = 34;
const BAR_HEIGHT = 14;
const RULER_HEIGHT = 40;
const BAND_HEIGHT = 30;
const GOVERNANCE_HEIGHT = 30;
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

  function draw() {
    if (!input || disposed) return;
    hideTip(); // the node under the pointer is about to be replaced
    const { model, derived, shown, cursorX, selected } = input;
    const width = Math.max(container.clientWidth || 720, 320);
    const narrow = width < 520; // on a phone the duration leaves the label column; it stays in the tooltip and the details
    const labelW = narrow ? 118 : Math.round(Math.min(260, Math.max(130, width * 0.3)));
    const plotW = Math.max(width - labelW - LEFT_PAD - RIGHT_PAD, 100);
    const [x0, x1] = currentRange();
    const sx = (x) => labelW + LEFT_PAD + ((x - x0) / (x1 - x0)) * plotW;
    const rows = derived.rows.map((row) => derived.byIndex.get(row.laneIndex));
    const top = RULER_HEIGHT + BAND_HEIGHT + GOVERNANCE_HEIGHT;
    const height = top + rows.length * ROW_HEIGHT + 12;
    const rowY = new Map(rows.map((lane, index) => [lane.laneIndex, top + index * ROW_HEIGHT]));
    const center = (lane) => rowY.get(lane.laneIndex) + ROW_HEIGHT / 2;
    const bySeq = new Map(model.elements.map((element) => [element.seq, element]));
    const minMs = derived.axis.minMs;
    const visibleLane = (lane) => shown.has(lane.openSeq);
    geometry = { labelW, plotW, x0, x1, sx, rowY, rows };

    const root = el("svg", { class: "tl-svg", viewBox: "0 0 " + width + " " + height, width, height, role: "group",
      "aria-label": t("tl.aria"), focusable: "false" });
    root.append(el("defs", null, el("clipPath", { id: "tl-clip" }, el("rect", { x: labelW, y: 0, width: plotW + LEFT_PAD + RIGHT_PAD, height }))));

    // background: drag to pan
    const background = el("rect", { class: "tl-bg", x: labelW, y: 0, width: plotW + LEFT_PAD + RIGHT_PAD, height });
    root.append(background);

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

    // ruler: ticks in elapsed time, none inside a compressed span; on the sequence axis, event numbers
    if (derived.axis.sequence) root.append(el("text", { class: "tl-axis-label", x: 8, y: RULER_HEIGHT - 8 }, t("tl.axisSequence")));
    layer.append(el("line", { class: "tl-axis", x1: labelW, y1: RULER_HEIGHT - 2, x2: labelW + plotW, y2: RULER_HEIGHT - 2 }));
    let lastLabelX = -Infinity;
    for (const tick of derived.axis.ticks(x0, x1)) {
      const x = sx(tick.x);
      layer.append(el("line", { class: "tl-tick", x1: x, y1: RULER_HEIGHT - 2, x2: x, y2: RULER_HEIGHT + 4 }));
      if (x - lastLabelX < 40) continue; // a label too close to the previous one would overlap it
      lastLabelX = x;
      layer.append(el("text", { class: "tl-tick-label", x, y: RULER_HEIGHT - 8, "text-anchor": "middle" }, tick.label));
    }

    // concurrency band (F1): how many agents were open at each instant, a count and nothing more
    const bandTop = RULER_HEIGHT + 6;
    const peak = derived.concurrency.peak;
    root.append(el("text", { class: "tl-band-label", x: 8, y: bandTop + 18 }, peak > 0 ? clip(t("tl.concurrency", { n: peak }), Math.floor((labelW - 12) / 5.8)) : ""));
    const steps = derived.concurrency.steps;
    if (peak > 0 && steps.length) {
      let path = "";
      for (let i = 0; i < steps.length; i += 1) {
        const x = sx(derived.axis.xOfMs(steps[i].ms));
        const y = bandTop + BAND_HEIGHT - 8 - (steps[i].open / peak) * (BAND_HEIGHT - 16);
        path += (i === 0 ? "M" : " H" + x + " V") + (i === 0 ? x + " " + y : y);
      }
      layer.append(tip(el("path", { class: "tl-concurrency", d: path }), t("tl.concurrencyTip", { n: peak })));
    }

    // governance row: grants, gates and wave markers at their position
    const govY = RULER_HEIGHT + BAND_HEIGHT + GOVERNANCE_HEIGHT / 2;
    for (const element of model.elements) {
      if (!shown.has(element.seq) || !positioned(element)) continue;
      let id = null;
      if (element.element === "gate-ring") id = element.ringKind === "grant" ? "g-grant" : "g-gate";
      else if (element.element === "wave-marker") id = "g-wave";
      else if (element.element === "wave-plane") id = "g-wave-plan";
      if (!id) continue;
      const x = sx(element.x);
      const label = element.element === "gate-ring"
        ? t(element.ringKind === "grant" ? "tl.tip.grant" : "tl.tip.gate", { subject: String(element.subject), status: String(element.status) })
        : t(element.element === "wave-plane" ? "tl.tip.wavePlan" : "tl.tip.waveMarker", { subject: String(element.subject) });
      const marker = el("g", { class: "tl-mark" + (selected === element.seq ? " selected" : ""), role: "button", tabindex: "-1", "aria-label": label },
        glyph(id, x, govY, 14, "gl"), el("rect", { class: "tl-hit", x: x - 9, y: govY - 10, width: 18, height: 20 }));
      marker.addEventListener("click", (event) => { event.stopPropagation(); hooks.onSelect(element.seq); });
      layer.append(tip(marker, label));
    }

    root.append(layer);
    root.append(el("text", { class: "tl-gov-label", x: 8, y: govY + 4 }, t("tl.governance")));

    // lanes
    const listbox = el("g", { role: "listbox", "aria-label": t("tl.lanes"), "aria-orientation": "vertical" });
    const tabStop = rows.some((lane) => lane.laneIndex === focusedLane) ? focusedLane : (rows[0] ? rows[0].laneIndex : null);
    const selectedLane = selected === null ? null : rows.find((lane) => lane.openSeq === selected || lane.seqs.includes(selected));
    for (const lane of rows) {
      const y = rowY.get(lane.laneIndex);
      const cy = y + ROW_HEIGHT / 2;
      const drawn = visibleLane(lane);
      const info = hooks.describe(lane);
      const row = el("g", { class: "tl-row" + (drawn ? "" : " pending") + (selectedLane === lane ? " selected" : ""), role: "option",
        tabindex: lane.laneIndex === tabStop ? "0" : "-1", "aria-selected": selectedLane === lane ? "true" : "false",
        "aria-label": info.aria, "data-lane": lane.laneIndex });
      row.append(el("rect", { class: "tl-row-bg", x: 0, y, width: width, height: ROW_HEIGHT }));
      // label column (fixed): indent, state mark, name, duration
      const indent = 8 + lane.depth * 14;
      row.append(el("text", { class: "tl-state state-" + lane.state, x: indent, y: cy + 4 }, info.mark));
      const room = Math.floor((labelW - indent - (narrow ? 22 : 74)) / 6.4);
      row.append(el("text", { class: "tl-label", x: indent + 16, y: cy + 4 }, clip(lane.displayLabel, room), el("title", null, lane.displayLabel)));
      if (!narrow) row.append(el("text", { class: "tl-duration", x: labelW - 8, y: cy + 4, "text-anchor": "end" }, info.duration));
      const plot = el("g", { "clip-path": "url(#tl-clip)" });
      if (drawn) {
        const startX = sx(lane.openX);
        const limit = cursorX === null ? lane.endX : Math.min(lane.endX, cursorX);
        const endX = sx(Math.max(limit, lane.openX));
        const barW = Math.max(endX - startX, 3);
        const closedShown = lane.closeSeq !== null && shown.has(lane.closeSeq);
        const status = closedShown ? "finished" : lane.state === "unknown" ? "unknown" : "running";
        const bar = el("g", { class: "tl-bar host-" + lane.host + " " + status });
        bar.append(el("rect", { class: "tl-bar-fill", x: startX, y: cy - BAR_HEIGHT / 2, width: barW, height: BAR_HEIGHT, rx: 3 }));
        if (status === "running") bar.append(el("rect", { class: "tl-bar-hatch", x: startX, y: cy - BAR_HEIGHT / 2, width: barW, height: BAR_HEIGHT, rx: 3 }));
        // T061: a wait names its target and its basis only when the event states them; declared waits are outlined
        for (const span of lane.waitSpans) {
          const from = sx(span.fromX);
          const to = sx(span.toX === null ? Math.max(limit, span.fromX) : Math.min(span.toX, Math.max(limit, span.fromX)));
          const target = span.waitingOn === null ? null : derived.byStrand.get(span.waitingOn);
          const text = span.waitingOn === null ? t("tl.tip.waitUnstated")
            : t("tl.tip.wait", { target: target ? target.displayLabel : span.waitingOn, basis: t("wait.basis." + span.basis) });
          bar.append(tip(el("rect", { class: "tl-wait" + (span.basis ? " basis-" + span.basis : ""), x: from, y: cy - BAR_HEIGHT / 2,
            width: Math.max(to - from, 2), height: BAR_HEIGHT }), text));
        }
        // T062: a duration only when the host stated one; otherwise the interval to the next event, labelled as such
        for (const mark of lane.toolMarks) {
          if (!shown.has(mark.seq)) continue;
          const x = sx(mark.x);
          const params = { name: mark.toolName, time: mark.timeKnown ? formatClock(mark.ms - minMs) : "#" + mark.seq };
          const text = mark.durationMs !== null ? t("tl.tip.toolDuration", { ...params, text: formatDuration(mark.durationMs) })
            : mark.intervalMs !== null ? t("tl.tip.toolInterval", { ...params, text: formatDuration(mark.intervalMs) })
              : t("tl.tip.tool", params);
          bar.append(tip(el("line", { class: "tl-tool" + (mark.durationMs !== null ? " stated" : ""), x1: x, y1: cy - BAR_HEIGHT / 2 + 2,
            x2: x, y2: cy + BAR_HEIGHT / 2 - 2 }), text));
        }
        if (status === "running") bar.append(el("path", { class: "tl-open-end", d: "M" + (startX + barW) + " " + (cy - 6) + " l6 6 l-6 6" }));
        if (closedShown) {
          bar.append(el("text", { class: "tl-outcome outcome-" + lane.outcome, x: startX + barW + 4, y: cy + 4 }, OUTCOME_MARK[lane.outcome] || "?"));
        }
        for (const gap of lane.gaps) {
          if (!shown.has(gap.seq) || !positioned(gap)) continue;
          const x = sx(gap.x);
          const g = el("g", { class: "tl-gap" }, glyph("g-gap", x, cy, 14, "gl"));
          bar.append(tip(g, t("tl.tip.gap", { reason: String(gap.reason) })));
        }
        plot.append(tip(bar, info.tip));
        // events of this lane that are markers: hazards
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
      row.addEventListener("click", () => { if (!dragged && drawn) hooks.onSelect(lane.openSeq); });
      row.addEventListener("focus", () => { focusedLane = lane.laneIndex; });
      listbox.append(row);
    }
    root.append(listbox);

    // crossings: a connector between the two agents' rows at the pair's position
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
        // near the right edge the word goes to the left of the glyph, so the clip does not cut it
        const flip = x + 110 > labelW + LEFT_PAD + plotW;
        group.append(el("text", { class: "tl-cross-word", x: flip ? x - 14 : x + 14, y: mid + 4, "text-anchor": flip ? "end" : null }, t("tl.conflictWord")));
      }
      group.addEventListener("click", (event) => { event.stopPropagation(); hooks.onSelect(crossing.seq); });
      connectors.append(tip(group, text));
    }
    root.append(connectors);

    // T060: the live "now" marker, from the server clock advanced by the page clock; open bars run up to it
    const nowX = derived.axis.nowX;
    if (typeof nowX === "number" && nowX >= x0 && nowX <= x1) {
      const x = sx(nowX);
      const now = el("g", { class: "tl-now" },
        el("line", { class: "tl-now-line", x1: x, y1: RULER_HEIGHT - 10, x2: x, y2: height - 6 }),
        el("text", { class: "tl-now-label", x: x - 4, y: 11, "text-anchor": "end" }, t("tl.now")));
      root.append(tip(now, t("tl.tip.now", { time: formatClock(derived.axis.nowMs - minMs) })));
    }

    // playback cursor, one line across every lane
    if (cursorX !== null && cursorX >= x0 && cursorX <= x1) {
      root.append(el("line", { class: "tl-cursor", x1: sx(cursorX), y1: RULER_HEIGHT - 2, x2: sx(cursorX), y2: height - 6 }));
    }

    const hadFocus = typeof document !== "undefined" && container.contains && document.activeElement && container.contains(document.activeElement);
    host.replaceChildren(root);
    if (hadFocus && focusedLane !== null) focusLane(rows.some((lane) => lane.laneIndex === focusedLane) ? focusedLane : (rows[0] ? rows[0].laneIndex : null), true);
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
