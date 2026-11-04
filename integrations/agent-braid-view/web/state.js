// SPDX-License-Identifier: AGPL-3.0-only
// Agent Braid activity viewer: the shared state and the derived model of VIS.1c (SPEC-061 REQ-016, T054).
//
// One state object and one derived model feed every view (the 2D timeline, the 3D map and the events table).
// Nothing in this file touches the DOM or the network, except the two per-viewer preferences at the end, which
// are guarded and optional. Every derivation reads only fields the model already carries (`lanes`, `elements`,
// `axis`); no new data is collected. All times are the model's `relMs` and `x` (the compressed axis position).

export const VIEWS = ["timeline", "map3d"];
export const LANE_STATES = ["running", "waiting", "finished", "unknown"];

const NBSP = " ";

export function createState() {
  return {
    model: null,
    dropped: [],
    cursor: 0,
    playing: false,
    timer: null,
    selected: null,
    hovered: null,
    filterKind: "",
    hiddenSources: new Set(),
    filters: { agents: new Set(), status: new Set(), onlyProblems: false },
    view: "timeline",
    viewport: null, // { x0, x1 } in axis x, or null for the whole axis
    lang: "en",
    langChoice: "auto",
    languageHint: null,
    lastId: "",
  };
}

// ---------------------------------------------------------------- time text

// m:ss, or h:mm:ss from one hour.
export function formatClock(ms) {
  if (typeof ms !== "number" || !Number.isFinite(ms) || ms < 0) return "–";
  const total = Math.floor(ms / 1000);
  const seconds = String(total % 60).padStart(2, "0");
  const minutes = Math.floor(total / 60) % 60;
  const hours = Math.floor(total / 3600);
  return hours > 0 ? hours + ":" + String(minutes).padStart(2, "0") + ":" + seconds : minutes + ":" + seconds;
}

// "850 ms", "44 s", "1 min 26 s", "1 h 02 min": a non-breaking space between number and unit.
export function formatDuration(ms) {
  if (typeof ms !== "number" || !Number.isFinite(ms) || ms < 0) return "–";
  if (ms < 1000) return Math.round(ms) + NBSP + "ms";
  const total = Math.round(ms / 1000);
  if (total < 60) return total + NBSP + "s";
  const seconds = total % 60;
  const minutes = Math.floor(total / 60);
  if (minutes < 60) return minutes + NBSP + "min" + (seconds ? " " + seconds + NBSP + "s" : "");
  const rest = minutes % 60;
  return Math.floor(minutes / 60) + NBSP + "h" + (rest ? " " + String(rest).padStart(2, "0") + NBSP + "min" : "");
}

// ---------------------------------------------------------------- element facts shared by the views

const KNOWN_VERIFICATION = new Set(["rehashed", "derived", "unverified"]);

// The marks of an element, in a fixed order. Same rules as the table has always used.
export function marksOf(element) {
  const marks = [];
  if (element.unverified || !KNOWN_VERIFICATION.has(element.verification)) marks.push("unverified");
  if (element.uncertain) marks.push("uncertain");
  if (element.incompleteCoverage) marks.push("partial");
  if (element.absence) marks.push("absence");
  if (element.element === "gap") marks.push("gap");
  if (element.timeKnown === false) marks.push("notime");
  return marks;
}

// A "problem" is something the viewer cannot show as clean: a conflicting or unknown pair, partial coverage,
// an unobserved hazard, a gap or an unrecognised verification value. "Unverified" alone is the state of every
// replayed or host-reported event, so it is stated once at source level and does not count as a problem.
export function isProblem(element) {
  if (element.element === "crossing" && (element.classification === "conflicting" || element.classification === "unknown")) return true;
  if (!KNOWN_VERIFICATION.has(element.verification)) return true;
  return marksOf(element).some((mark) => mark !== "unverified" && mark !== "notime");
}

// ---------------------------------------------------------------- event sources

// The page offers one checkbox per source of events. The event contract names no adapter and no root, so the source
// is inferred from fields every element has (see the comments of the former page code, kept in the docs):
//   rehashed or derived, with an evidence reference and a root label "root N": watched:root N
//   rehashed or derived, with an evidence reference, no usable root label: watched
//   rehashed or derived, without a reference: viewer (produced by the viewer itself)
//   anything else with an evidence reference: replay; without one: hook
export const SOURCE_KEYS = ["watched", "replay", "hook", "viewer"];
export const ROOT_PREFIX = "watched:";
const ROOT_LABEL = /^root ([1-9][0-9]?)$/;

export function sourceOf(element) {
  const referenced = Boolean(element.evidenceRef);
  if (element.verification === "rehashed" || element.verification === "derived") {
    if (!referenced) return "viewer";
    return typeof element.root === "string" && ROOT_LABEL.test(element.root) ? ROOT_PREFIX + element.root : "watched";
  }
  return referenced ? "replay" : "hook";
}

// The roots by number, then the unlabelled watched group, then the other sources in their fixed order.
export function sourceKeys(counts) {
  const number = (key) => Number(ROOT_LABEL.exec(key.slice(ROOT_PREFIX.length))[1]);
  const roots = Object.keys(counts).filter((key) => key.startsWith(ROOT_PREFIX)).sort((a, b) => number(a) - number(b));
  return [...roots, ...SOURCE_KEYS.filter((key) => counts[key])];
}

// The model's rows in model order (time, then seq), each with its element.
export function orderedRows(model) {
  const bySeq = new Map(model.elements.map((element) => [element.seq, element]));
  return model.table
    .map((row) => ({ row, element: bySeq.get(row.seq) }))
    .filter((entry) => entry.element)
    .sort((a, b) => a.element.order - b.element.order || a.row.seq - b.row.seq);
}

// ---------------------------------------------------------------- the time axis

const TICK_STEPS = [100, 200, 500, 1000, 2000, 5000, 10000, 15000, 30000, 60000, 120000, 300000, 600000, 900000, 1800000, 3600000];

// Moments are the distinct stated times with their compressed position. Inside one run of moments closer than the
// model's gap threshold the axis is linear; across a compression it is not, and no tick is drawn there.
export function deriveAxis(model) {
  const source = model && model.axis ? model.axis : {};
  const elements = model && Array.isArray(model.elements) ? model.elements : [];
  const seen = new Map();
  for (const element of elements) if (element.timeKnown !== false && !seen.has(element.relMs)) seen.set(element.relMs, element.x);
  const moments = [...seen].map(([ms, x]) => ({ ms, x })).sort((a, b) => a.ms - b.ms);
  const threshold = typeof source.gapThresholdMs === "number" ? source.gapThresholdMs : 5000;
  const minMs = typeof source.minMs === "number" ? source.minMs : moments.length ? moments[0].ms : 0;
  const spanX = Math.max(typeof source.shownSpan === "number" ? source.shownSpan : 0, 0);

  function xOfMs(ms) {
    if (moments.length === 0) return 0;
    if (ms <= moments[0].ms) return moments[0].x;
    const last = moments[moments.length - 1];
    if (ms >= last.ms) return last.x;
    let low = 0;
    let high = moments.length - 1;
    while (high - low > 1) {
      const mid = (low + high) >> 1;
      if (moments[mid].ms <= ms) low = mid;
      else high = mid;
    }
    const a = moments[low];
    const b = moments[high];
    return a.x + ((ms - a.ms) / (b.ms - a.ms)) * (b.x - a.x);
  }

  const breaks = (Array.isArray(source.compressions) ? source.compressions : []).map((cut) => ({
    x1: xOfMs(cut.fromMs), x2: xOfMs(cut.toMs), fromMs: cut.fromMs, toMs: cut.toMs, spanMs: cut.spanMs,
  }));

  // Ticks in elapsed time inside [x0, x1], at a step that leaves about 4 to 10 labels.
  function ticks(x0 = 0, x1 = spanX) {
    const range = Math.max(x1 - x0, 1);
    const step = TICK_STEPS.find((candidate) => range / candidate <= 9) || TICK_STEPS[TICK_STEPS.length - 1];
    const out = [];
    let lastAt = -Infinity;
    const runs = moments.length ? moments.slice(0, -1).map((a, i) => [a, moments[i + 1]]) : [];
    if (moments.length === 1) runs.push([moments[0], moments[0]]);
    for (const [a, b] of runs) {
      if (b.ms - a.ms > threshold) continue;
      const first = Math.ceil((a.ms - minMs) / step);
      const last = Math.floor((b.ms - minMs) / step);
      for (let k = first; k <= last; k += 1) {
        const at = minMs + k * step;
        const x = a.x + (at - a.ms);
        if (x < x0 || x > x1 || at <= lastAt) continue;
        lastAt = at;
        out.push({ x, ms: at - minMs, label: formatClock(at - minMs) });
      }
    }
    return out;
  }

  return { basis: source.basis || "sequence-only", minMs, maxMs: typeof source.maxMs === "number" ? source.maxMs : minMs,
    spanMs: source.spanMs || 0, spanX, moments, breaks, xOfMs, ticks, nowMs: null };
}

// ---------------------------------------------------------------- lanes

function laneRecord(bySeq, lane, rec, sessionEndMs, sessionEndX) {
  const opener = bySeq.get(lane.seq);
  const openKnown = Boolean(opener) && opener.timeKnown !== false;
  const openMs = opener ? opener.relMs : null;
  const openX = opener ? opener.x : 0;
  const close = rec.close;
  const closeKnown = Boolean(close) && close.timeKnown !== false;
  const updates = rec.updates;
  const lastUpdate = updates.length ? updates[updates.length - 1] : null;
  let state = "unknown";
  let idle = false;
  if (close) state = "finished";
  else if (lastUpdate && (lastUpdate.state === "running" || lastUpdate.state === "waiting")) state = lastUpdate.state;
  else if (lastUpdate && lastUpdate.state === "idle") { state = "running"; idle = true; }
  const timed = [opener, ...rec.touched].filter((element) => element && element.timeKnown !== false);
  const lastMs = timed.length ? Math.max(...timed.map((element) => element.relMs)) : openMs;
  const lastX = timed.length ? Math.max(...timed.map((element) => element.x)) : openX;

  const waitSpans = [];
  let waiting = null;
  const endOf = (element) => ({ ms: element.relMs, x: element.x });
  for (const update of updates) {
    if (waiting) {
      waiting.toMs = update.relMs; waiting.toX = update.x; waiting.open = false;
      waitSpans.push(waiting);
      waiting = null;
    }
    if (update.state === "waiting") waiting = { seq: update.seq, fromMs: update.relMs, fromX: update.x, toMs: null, toX: null, open: true };
  }
  if (waiting) {
    if (close) { const end = endOf(close); waiting.toMs = end.ms; waiting.toX = end.x; waiting.open = false; }
    waitSpans.push(waiting);
  }

  return {
    laneIndex: lane.laneIndex, strandId: lane.strandId, label: lane.label, displayLabel: lane.label, ordinal: null,
    host: lane.host, role: lane.role, declared: lane.declared, unverified: Boolean(lane.unverified),
    parentStrandId: lane.parentStrandId === undefined ? null : lane.parentStrandId, parentLane: null, orphan: false, depth: 0,
    openSeq: lane.seq, openMs, openX, openKnown,
    closeSeq: close ? close.seq : null, closeMs: close ? close.relMs : null, closeX: close ? close.x : null, closeKnown,
    outcome: close ? (typeof close.outcome === "string" ? close.outcome : "unknown") : null,
    state, idle, inferred: !close && state !== "unknown",
    durationMs: close && openKnown && closeKnown ? Math.max(0, close.relMs - openMs) : null,
    observedMs: openKnown && lastMs !== null ? Math.max(0, (close && closeKnown ? close.relMs : lastMs) - openMs) : null,
    endMs: close && closeKnown ? close.relMs : sessionEndMs, endX: close ? close.x : sessionEndX,
    lastMs, lastX,
    toolMarks: updates.filter((update) => typeof update.toolName === "string" && update.toolName)
      .map((update) => ({ seq: update.seq, ms: update.relMs, x: update.x, toolName: update.toolName, state: update.state })),
    waitSpans,
    gaps: rec.gaps.map((gap) => ({ seq: gap.seq, ms: gap.relMs, x: gap.x, reason: gap.reason })),
    seqs: [],
  };
}

// Agents with opening, closing, state and duration, ordered for display (each parent followed by its children).
export function deriveLanes(model) {
  const empty = { lanes: [], rows: [], byIndex: new Map(), byStrand: new Map(), sessionEndMs: null, sessionEndX: 0 };
  if (!model || !Array.isArray(model.lanes) || !Array.isArray(model.elements)) return empty;
  const bySeq = new Map(model.elements.map((element) => [element.seq, element]));
  const perStrand = new Map();
  const touchedBy = new Map();
  const timedElements = model.elements.filter((element) => element.timeKnown !== false);
  const sessionEndMs = timedElements.length ? Math.max(...timedElements.map((element) => element.relMs)) : null;
  const sessionEndX = timedElements.length ? Math.max(...timedElements.map((element) => element.x)) : 0;
  const record = (strandId) => {
    if (!perStrand.has(strandId)) perStrand.set(strandId, { close: null, updates: [], gaps: [], touched: [] });
    return perStrand.get(strandId);
  };
  const ordered = [...model.elements].sort((a, b) => a.order - b.order || a.seq - b.seq);
  for (const element of ordered) {
    for (const index of Array.isArray(element.lanes) ? element.lanes : []) {
      if (!touchedBy.has(index)) touchedBy.set(index, []);
      touchedBy.get(index).push(element);
    }
    if (element.strandId === undefined || element.strandId === null) continue;
    const rec = record(element.strandId);
    if (element.element === "strand-end" && !rec.close) rec.close = element;
    else if (element.element === "strand-state") rec.updates.push(element);
    else if (element.element === "gap") rec.gaps.push(element);
  }
  const lanes = model.lanes.map((lane) => {
    const rec = record(lane.strandId);
    rec.touched = (touchedBy.get(lane.laneIndex) || []).filter((element) => element.element === "strand-state" || element.element === "strand-end");
    const built = laneRecord(bySeq, lane, rec, sessionEndMs, sessionEndX);
    built.seqs = (touchedBy.get(lane.laneIndex) || []).map((element) => element.seq);
    return built;
  });
  const byIndex = new Map(lanes.map((lane) => [lane.laneIndex, lane]));
  const byStrand = new Map(lanes.map((lane) => [lane.strandId, lane]));
  for (const lane of lanes) {
    if (lane.parentStrandId === null) continue;
    const parent = byStrand.get(lane.parentStrandId);
    if (parent && parent !== lane) lane.parentLane = parent.laneIndex;
    else lane.orphan = true; // named a parent that is not among the lanes: never attached by guesswork
  }
  // Agents with the same label are told apart by the order they opened in; a label seen once gets no number.
  const groups = new Map();
  for (const lane of lanes) {
    if (!groups.has(lane.label)) groups.set(lane.label, []);
    groups.get(lane.label).push(lane);
  }
  for (const group of groups.values()) {
    if (group.length < 2) continue;
    group.sort((a, b) => a.openX - b.openX || a.openSeq - b.openSeq).forEach((lane, index) => {
      lane.ordinal = index + 1;
      lane.displayLabel = lane.label + " #" + lane.ordinal;
    });
  }
  const rows = [];
  const placed = new Set();
  const children = (parent) => lanes.filter((lane) => lane.parentLane === parent.laneIndex).sort((a, b) => a.laneIndex - b.laneIndex);
  const place = (lane, depth) => {
    if (placed.has(lane.laneIndex)) return;
    placed.add(lane.laneIndex);
    lane.depth = depth;
    rows.push({ laneIndex: lane.laneIndex, depth, orphan: lane.orphan });
    for (const child of children(lane)) place(child, depth + 1);
  };
  for (const lane of lanes.filter((item) => item.parentStrandId === null)) place(lane, 0);
  for (const lane of lanes.filter((item) => item.orphan)) place(lane, 0);
  for (const lane of lanes) place(lane, 0); // a parent cycle can reach no root: still shown, flat
  return { lanes, rows, byIndex, byStrand, sessionEndMs, sessionEndX };
}

// Time two lanes were open together. Null when either start or the basis is not a comparable time.
function overlapBetween(a, b, axisBasis) {
  if (!a || !b || !a.openKnown || !b.openKnown || a.openMs === null || b.openMs === null) return null;
  if (axisBasis === "mixed" || axisBasis === "sequence-only" || a.endMs === null || b.endMs === null) return null;
  const from = Math.max(a.openMs, b.openMs);
  const to = Math.min(a.endMs, b.endMs);
  return { fromMs: from, toMs: Math.max(from, to), ms: Math.max(0, to - from), inferred: !(a.closeKnown && b.closeKnown) };
}

// Every classified pair that is placed on two lanes, with whether its lanes overlapped in time (F3). A predicted
// conflict is the analysis class `conflicting`; an observed collision is a different kind that no source feeds yet.
export function deriveCrossings(model, derived) {
  if (!model || !Array.isArray(model.elements)) return [];
  const basis = model.axis ? model.axis.basis : "sequence-only";
  const out = [];
  for (const element of model.elements) {
    if (element.element !== "crossing") continue;
    const [a, b] = Array.isArray(element.lanes) ? element.lanes : [];
    const overlap = overlapBetween(derived.byIndex.get(a), derived.byIndex.get(b), basis);
    out.push({
      seq: element.seq, classification: element.classification, drawAs: element.drawAs,
      kind: element.classification === "conflicting" ? "predicted" : null,
      lanes: [a, b].filter((index) => index !== undefined), left: element.left, right: element.right,
      resources: Array.isArray(element.sharedResources) ? element.sharedResources : [],
      reasons: Array.isArray(element.reasons) ? element.reasons : [],
      uncertain: Boolean(element.uncertain), incomplete: Boolean(element.incompleteCoverage),
      ms: element.relMs, x: element.x, timeKnown: element.timeKnown !== false, overlap,
    });
  }
  return out;
}

export function conflictsOf(crossings) {
  return crossings.filter((crossing) => crossing.kind === "predicted");
}

// Number of agents open at each instant (F1), as steps in session time, with the peak. A lane still open at the
// end of the session counts up to the last event.
export function deriveConcurrency(derived) {
  const edges = [];
  for (const lane of derived.lanes) {
    if (!lane.openKnown || lane.openMs === null || lane.endMs === null) continue;
    edges.push([lane.openMs, 1], [Math.max(lane.endMs, lane.openMs), -1]);
  }
  edges.sort((a, b) => a[0] - b[0] || a[1] - b[1]); // closing before opening at the same instant
  const steps = [];
  let open = 0;
  let peak = 0;
  let peakMs = null;
  for (const [ms, change] of edges) {
    open += change;
    if (steps.length && steps[steps.length - 1].ms === ms) steps[steps.length - 1].open = open;
    else steps.push({ ms, open });
    if (open > peak) { peak = open; peakMs = ms; }
  }
  return { steps, peak, peakMs };
}

// Pairs of agents and the time they were open together (F1). Capped so a very large session stays cheap.
export function deriveOverlaps(model, derived, crossings, limit = 64) {
  const basis = model && model.axis ? model.axis.basis : "sequence-only";
  const wanted = new Map();
  const add = (a, b) => { if (a !== undefined && b !== undefined && a !== b) wanted.set(Math.min(a, b) + ":" + Math.max(a, b), [Math.min(a, b), Math.max(a, b)]); };
  for (const crossing of crossings) add(crossing.lanes[0], crossing.lanes[1]);
  if (derived.lanes.length <= limit) {
    for (const a of derived.lanes) for (const b of derived.lanes) if (a.laneIndex < b.laneIndex) add(a.laneIndex, b.laneIndex);
  }
  const out = [];
  for (const [a, b] of wanted.values()) {
    const overlap = overlapBetween(derived.byIndex.get(a), derived.byIndex.get(b), basis);
    if (overlap && overlap.ms > 0) out.push({ lanes: [a, b], ...overlap });
  }
  return out.sort((x, y) => y.ms - x.ms || x.lanes[0] - y.lanes[0] || x.lanes[1] - y.lanes[1]);
}

// Total and current time an agent spent in `waiting` (F2): only the time the events state, never a guess.
export function waitingTime(lane) {
  let total = 0;
  let known = true;
  for (const span of lane.waitSpans) {
    if (span.toMs === null) known = false;
    else total += Math.max(0, span.toMs - span.fromMs);
  }
  return { totalMs: total, open: lane.waitSpans.some((span) => span.open), complete: known };
}

export function derive(model) {
  const lanes = deriveLanes(model);
  const crossings = deriveCrossings(model, lanes);
  return {
    ...lanes, axis: deriveAxis(model), crossings, conflicts: conflictsOf(crossings),
    concurrency: deriveConcurrency(lanes), overlaps: deriveOverlaps(model, lanes, crossings),
  };
}

// The one-line summary of the header, as numbers; the wording is in strings.js.
export function summarize(model, derived) {
  const count = (name) => derived.lanes.filter((lane) => lane.state === name).length;
  const gaps = model && model.counters && model.counters.gaps ? model.counters.gaps.total : 0;
  return {
    agents: derived.lanes.length, running: count("running"), waiting: count("waiting"), finished: count("finished"),
    unknown: count("unknown"), durationMs: model && model.axis ? model.axis.spanMs : 0,
    predictedConflicts: derived.conflicts.length, gaps, peak: derived.concurrency.peak,
  };
}

// ---------------------------------------------------------------- filters shared by every view

export function laneStateOf(derived, laneIndex) {
  const lane = derived.byIndex.get(laneIndex);
  return lane ? lane.state : null;
}

// Whether an element passes the agent, status and problems filters (sources and the playback position are
// applied by the caller). An element tied to no agent (a session origin, a report, a grant) is not hidden by
// the agent or status filter.
export function passesFilters(element, derived, filters) {
  const lanes = Array.isArray(element.lanes) ? element.lanes : [];
  if (filters.agents.size > 0 && lanes.length > 0 &&
      !lanes.some((index) => { const lane = derived.byIndex.get(index); return lane && filters.agents.has(lane.strandId); })) return false;
  if (filters.status.size > 0 && lanes.length > 0 &&
      !lanes.some((index) => filters.status.has(laneStateOf(derived, index)))) return false;
  if (filters.onlyProblems && !isProblem(element)) return false;
  return true;
}

export function hasFilters(state) {
  const f = state.filters;
  return f.agents.size > 0 || f.status.size > 0 || f.onlyProblems || state.hiddenSources.size > 0;
}

// ---------------------------------------------------------------- the URL hash

const HASH_ITEM = /^[A-Za-z0-9._:#-]{1,64}$/;
const MAX_HASH_ITEMS = 64;

// view, selection, filters and viewport only. The hash never carries an event value, a path or a label: only
// ids the page already shows (a sequence number, a source key, a strand id).
export function encodeHash(state) {
  const parts = [];
  if (VIEWS.includes(state.view)) parts.push("v=" + state.view);
  if (Number.isInteger(state.selected)) parts.push("sel=" + state.selected);
  const safe = (values) => [...values].filter((value) => HASH_ITEM.test(value)).slice(0, MAX_HASH_ITEMS).map(encodeURIComponent);
  if (state.hiddenSources.size) parts.push("hide=" + safe(state.hiddenSources).join(","));
  if (state.filters.agents.size) parts.push("ag=" + safe(state.filters.agents).join(","));
  if (state.filters.status.size) parts.push("st=" + [...state.filters.status].filter((value) => LANE_STATES.includes(value)).join(","));
  if (state.filters.onlyProblems) parts.push("pr=1");
  if (state.viewport && Number.isFinite(state.viewport.x0) && Number.isFinite(state.viewport.x1)) {
    parts.push("x=" + Math.round(state.viewport.x0) + "-" + Math.round(state.viewport.x1));
  }
  return parts.length ? "#" + parts.join("&") : "";
}

export function decodeHash(text) {
  const out = { view: null, selected: null, hide: [], agents: [], status: [], onlyProblems: false, viewport: null };
  if (typeof text !== "string" || text.length > 4096) return out;
  for (const part of text.replace(/^#/, "").split("&")) {
    const at = part.indexOf("=");
    if (at < 0) continue;
    const key = part.slice(0, at);
    const value = part.slice(at + 1);
    const list = () => value.split(",").map((item) => { try { return decodeURIComponent(item); } catch (error) { return ""; } })
      .filter((item) => HASH_ITEM.test(item)).slice(0, MAX_HASH_ITEMS);
    if (key === "v" && VIEWS.includes(value)) out.view = value;
    else if (key === "sel" && /^[0-9]{1,12}$/.test(value)) out.selected = Number(value);
    else if (key === "hide") out.hide = list();
    else if (key === "ag") out.agents = list();
    else if (key === "st") out.status = list().filter((item) => LANE_STATES.includes(item));
    else if (key === "pr") out.onlyProblems = value === "1";
    else if (key === "x") {
      const match = /^(-?[0-9]{1,12})-(-?[0-9]{1,12})$/.exec(value);
      if (match && Number(match[1]) < Number(match[2])) out.viewport = { x0: Number(match[1]), x1: Number(match[2]) };
    }
  }
  return out;
}

// ---------------------------------------------------------------- per-viewer preferences

// Only the language choice and the last view are stored, in this browser, never sent anywhere. Every access is
// guarded: private windows and blocked storage must leave the page working.
const PREFERENCE_KEYS = new Set(["lang", "view"]);
const PREFERENCE_PREFIX = "agent-braid-view.";

export function readPreference(key) {
  if (!PREFERENCE_KEYS.has(key)) return null;
  try {
    return typeof localStorage === "undefined" ? null : localStorage.getItem(PREFERENCE_PREFIX + key);
  } catch (error) {
    return null;
  }
}

export function writePreference(key, value) {
  if (!PREFERENCE_KEYS.has(key)) return;
  try {
    if (typeof localStorage === "undefined") return;
    if (value === null || value === undefined) localStorage.removeItem(PREFERENCE_PREFIX + key);
    else localStorage.setItem(PREFERENCE_PREFIX + key, String(value));
  } catch (error) {
    // storage is optional
  }
}
