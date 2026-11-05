// SPDX-License-Identifier: AGPL-3.0-only
// Agent Braid activity viewer: the plan map (SPEC-061 VIS.1d, REQ-025, T071).
//
// One analysis report drawn as what it is: operations and their classified pairs, with no time axis. Operations sit
// in columns by the length of their declared-wait chain (state.js derivePlans); pairs are curves between them, in
// one line style per class (may collide, must wait, independent, unknown). Nothing here states or implies a duration,
// an order of execution or a safety ranking. It keeps no state of its own: `render` receives the plan and the
// selection, and clicks go back through `hooks.onSelect`.
//
// No third-party code and no markup strings: elements are made with createElementNS and a fixed allowlist of
// attribute names, every text is a text node.

const NS = "http://www.w3.org/2000/svg";
const ALLOWED = new Set(["x", "y", "width", "height", "rx", "r", "cx", "cy", "d", "class", "viewBox", "role", "tabindex",
  "aria-label", "aria-pressed", "aria-hidden", "text-anchor", "data-seq", "focusable"]);

const NODE_W = 156;
const NODE_H = 30;
const COL_GAP = 64;
const ROW_GAP = 14;
const PAD = 16;

export const PAIR_STYLES = ["conflicting", "ordered", "independent-candidate", "unknown"];

function el(tag, attrs, ...children) {
  const node = document.createElementNS(NS, tag);
  for (const [name, value] of Object.entries(attrs || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (!ALLOWED.has(name)) throw new Error("svg attribute not allowed: " + name);
    node.setAttribute(name, String(value));
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function clip(text, max) {
  return text.length > max ? text.slice(0, Math.max(1, max - 1)) + "…" : text;
}

// Node positions of a plan: column from `plan.columns`, rows in lane order inside each column.
export function layoutPlan(plan) {
  const columns = new Map();
  for (const lane of [...plan.ops].sort((a, b) => a.laneIndex - b.laneIndex)) {
    const column = plan.columns.get(lane.laneIndex) || 0;
    if (!columns.has(column)) columns.set(column, []);
    columns.get(column).push(lane);
  }
  const at = new Map();
  let rows = 0;
  for (const [column, lanes] of columns) {
    lanes.forEach((lane, row) => at.set(lane.laneIndex, { x: PAD + column * (NODE_W + COL_GAP), y: PAD + row * (NODE_H + ROW_GAP), column }));
    rows = Math.max(rows, lanes.length);
  }
  const width = PAD * 2 + (columns.size ? Math.max(...columns.keys()) + 1 : 1) * (NODE_W + COL_GAP) - COL_GAP;
  return { at, width, height: PAD * 2 + rows * (NODE_H + ROW_GAP) - ROW_GAP };
}

export function createPlanMap(container, hooks) {
  const t = (key, params) => hooks.t(key, params);

  function render({ plan, selected }) {
    if (!plan) { container.replaceChildren(); return; }
    const { at, width, height } = layoutPlan(plan);
    const root = el("svg", { viewBox: "0 0 " + width + " " + height, width, height, role: "group", "aria-label": t("plan.aria"), focusable: "false" });
    const edges = el("g", { "aria-hidden": "true" });
    const rings = el("g");
    const hot = new Set();
    // independent pairs first, so the classes that need attention are drawn on top
    const order = (pair) => ["independent-candidate", "unknown", "ordered", "conflicting"].indexOf(pair.classification);
    for (const pair of [...plan.pairs].sort((a, b) => order(a) - order(b))) {
      const [a, b] = pair.lanes.map((index) => at.get(index));
      if (!a || !b) continue;
      const style = PAIR_STYLES.includes(pair.classification) ? pair.classification : "unknown";
      const [left, right] = a.x <= b.x ? [a, b] : [b, a];
      let d;
      let mid;
      if (left.column === right.column) {
        // same column: a loop on the right side of the nodes
        const x = left.x + NODE_W;
        const bulge = 26 + Math.abs(right.y - left.y) * 0.15;
        d = "M" + x + " " + (left.y + NODE_H / 2) + " C" + (x + bulge) + " " + (left.y + NODE_H / 2) + " " + (x + bulge) + " " + (right.y + NODE_H / 2) + " " + x + " " + (right.y + NODE_H / 2);
        mid = { x: x + bulge * 0.75, y: (left.y + right.y) / 2 + NODE_H / 2 };
      } else {
        const ax = left.x + NODE_W;
        const ay = left.y + NODE_H / 2;
        const bx = right.x;
        const by = right.y + NODE_H / 2;
        d = "M" + ax + " " + ay + " C" + (ax + COL_GAP / 2) + " " + ay + " " + (bx - COL_GAP / 2) + " " + by + " " + bx + " " + by;
        mid = { x: (ax + bx) / 2, y: (ay + by) / 2 };
      }
      edges.append(el("path", { class: "pm-edge " + style, d }));
      if (pair.kind === "predicted") {
        for (const index of pair.lanes) hot.add(index);
        const ring = el("circle", { class: "pm-ring" + (selected === pair.seq ? " selected" : ""), cx: mid.x, cy: mid.y, r: 7, role: "button", tabindex: "0",
          "aria-label": hooks.pairText(pair), "aria-pressed": selected === pair.seq ? "true" : "false", "data-seq": pair.seq });
        ring.addEventListener("click", () => hooks.onSelect(pair.seq));
        ring.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); hooks.onSelect(pair.seq); } });
        rings.append(ring);
      }
    }
    const nodes = el("g");
    for (const lane of plan.ops) {
      const p = at.get(lane.laneIndex);
      if (!p) continue;
      const seq = plan.opSeqs && plan.opSeqs.has(lane.laneIndex) ? plan.opSeqs.get(lane.laneIndex) : lane.openSeq;
      const isSelected = selected === seq;
      const name = hooks.nameOf(lane);
      const node = el("g", { class: "pm-node" + (hot.has(lane.laneIndex) ? " hot" : "") + (isSelected ? " selected" : ""), role: "button", tabindex: "0",
        "aria-label": hooks.opText(lane), "aria-pressed": isSelected ? "true" : "false", "data-seq": seq },
      el("rect", { x: p.x, y: p.y, width: NODE_W, height: NODE_H, rx: 8 }),
      el("text", { x: p.x + 12, y: p.y + 19 }, clip(name, 21)));
      node.addEventListener("click", () => hooks.onSelect(seq));
      node.addEventListener("keydown", (event) => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); hooks.onSelect(seq); } });
      nodes.append(node);
    }
    root.append(edges, nodes, rings);
    container.replaceChildren(root);
  }

  return { render, dispose() { container.replaceChildren(); } };
}
