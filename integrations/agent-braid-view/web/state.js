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
    filters: { agents: new Set(), status: new Set(), kinds: new Set(), onlyProblems: false },
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

// The legend entries that act as filters: the kind of marker an element is, or null for everything else (agents,
// their states and ends are never hidden by a legend filter).
export const MARKER_KINDS = ["conflict", "independent", "ordered", "unknown", "hazard", "gap", "gate", "grant"];

export function markerKind(element) {
  switch (element.element) {
    case "crossing":
      return { "conflicting": "conflict", "independent-candidate": "independent", "ordered": "ordered" }[element.classification] || "unknown";
    case "hazard-cone": return "hazard";
    case "gap": return "gap";
    case "gate-ring": return element.ringKind === "grant" ? "grant" : "gate";
    default: return null;
  }
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

// ---------------------------------------------------------------- the sequence axis

// When any event states no time (an analysis report, for one, carries only its order), a time axis cannot place
// it without inventing a time. The views then use a sequence axis instead: every event gets its own slot in the
// model's `order` (stated time, then sequence number), SEQUENCE_STEP apart. Times and durations stay what the
// events state: a sequence position is never turned into a duration.
export const SEQUENCE_STEP = 1000;

const timeKnownOf = (element) => Boolean(element) && element.timeKnown !== false;
// Whether an element has a position on the axis in use: a stated time, or a slot of the sequence axis.
export const positioned = (element) => timeKnownOf(element) || Boolean(element && element.placed);

export function needsSequenceAxis(model) {
  return Boolean(model && Array.isArray(model.elements) && model.elements.some((element) => element.timeKnown === false));
}

// The model with every element at its sequence slot (`x`) and `placed: true`; the model itself when every event
// states a time. Nothing else changes: `relMs`, `basis` and `timeKnown` are the event's own.
export function placeBySequence(model) {
  if (!needsSequenceAxis(model)) return model;
  const elements = model.elements.map((element) => ({ ...element, x: (element.order + 0.5) * SEQUENCE_STEP, placed: true }));
  return { ...model, elements };
}

function deriveSequenceAxis(model) {
  const source = model.axis || {};
  const ordered = [...model.elements].sort((a, b) => a.x - b.x);
  const spanX = ordered.length * SEQUENCE_STEP;
  const untimed = model.elements.filter((element) => element.timeKnown === false).length;
  // Ticks name events by sequence number, at a step that leaves about 4 to 10 labels.
  function ticks(x0 = 0, x1 = spanX) {
    const visible = ordered.filter((element) => element.x >= x0 && element.x <= x1);
    const step = Math.max(1, Math.ceil(visible.length / 9));
    return visible.filter((_, index) => index % step === 0).map((element) => ({ x: element.x, ms: null, label: "#" + element.seq }));
  }
  return { basis: source.basis || "sequence-only", sequence: true, untimed, total: model.elements.length,
    minMs: typeof source.minMs === "number" ? source.minMs : 0, maxMs: typeof source.maxMs === "number" ? source.maxMs : 0,
    spanMs: source.spanMs || 0, spanX, moments: [], breaks: [], xOfMs: () => 0, ticks,
    live: source.live === true, nowMs: null, nowX: null };
}

// T060: the live "now" on the compressed axis, or null. Only a live model whose events all state a time has one
// (`axis.live` and `axis.nowMs` come from the server clock); `nowMs` may be the server value advanced by the page's
// own clock between snapshots. It is never before the last stated time. Past that time the axis runs linearly up to
// the gap threshold and is then compressed to the nominal width, like any other long span.
export function liveNow(model, nowMs) {
  const axis = model && model.axis;
  if (!axis || axis.live !== true || !Array.isArray(model.elements) || needsSequenceAxis(model)) return null;
  const stated = typeof nowMs === "number" && Number.isFinite(nowMs) ? nowMs : axis.nowMs;
  if (typeof stated !== "number" || !Number.isFinite(stated)) return null;
  let last = null;
  for (const element of model.elements) {
    if (timeKnownOf(element) && (!last || element.relMs > last.relMs || (element.relMs === last.relMs && element.x > last.x))) last = element;
  }
  if (!last) return null; // no stated time to place now against
  const threshold = typeof axis.gapThresholdMs === "number" ? axis.gapThresholdMs : 5000;
  const nominal = typeof axis.gapNominalMs === "number" ? axis.gapNominalMs : 1000;
  const ms = Math.max(stated, last.relMs);
  const compressed = ms - last.relMs > threshold;
  return { ms, x: last.x + (compressed ? nominal : ms - last.relMs), fromMs: last.relMs, fromX: last.x, compressed };
}

// Moments are the distinct stated times with their compressed position. Inside one run of moments closer than the
// model's gap threshold the axis is linear; across a compression it is not, and no tick is drawn there.
export function deriveAxis(model, live = null) {
  const source = model && model.axis ? model.axis : {};
  const elements = model && Array.isArray(model.elements) ? model.elements : [];
  const seen = new Map();
  for (const element of elements) if (element.timeKnown !== false && !seen.has(element.relMs)) seen.set(element.relMs, element.x);
  const moments = [...seen].map(([ms, x]) => ({ ms, x })).sort((a, b) => a.ms - b.ms);
  const threshold = typeof source.gapThresholdMs === "number" ? source.gapThresholdMs : 5000;
  const minMs = typeof source.minMs === "number" ? source.minMs : moments.length ? moments[0].ms : 0;
  const spanX = Math.max(typeof source.shownSpan === "number" ? source.shownSpan : 0, live ? live.x : 0, 0);

  function xOfMs(ms) {
    if (moments.length === 0) return 0;
    if (live && ms > live.fromMs) {
      return live.ms === live.fromMs ? live.x : live.fromX + ((Math.min(ms, live.ms) - live.fromMs) / (live.ms - live.fromMs)) * (live.x - live.fromX);
    }
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
  if (live && live.compressed) breaks.push({ x1: live.fromX, x2: live.x, fromMs: live.fromMs, toMs: live.ms, spanMs: live.ms - live.fromMs, live: true });
  // The ticks run on to now unless that last span is compressed (no tick is drawn inside a compression).
  const tickMoments = live && !live.compressed && live.ms > live.fromMs ? [...moments, { ms: live.ms, x: live.x }] : moments;

  // Ticks in elapsed time inside [x0, x1], at a step that leaves about 4 to 10 labels.
  function ticks(x0 = 0, x1 = spanX) {
    const range = Math.max(x1 - x0, 1);
    const step = TICK_STEPS.find((candidate) => range / candidate <= 9) || TICK_STEPS[TICK_STEPS.length - 1];
    const out = [];
    let lastAt = -Infinity;
    const runs = tickMoments.length ? tickMoments.slice(0, -1).map((a, i) => [a, tickMoments[i + 1]]) : [];
    if (tickMoments.length === 1) runs.push([tickMoments[0], tickMoments[0]]);
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

  return { basis: source.basis || "sequence-only", sequence: false, untimed: 0, total: elements.length, minMs, maxMs: typeof source.maxMs === "number" ? source.maxMs : minMs,
    spanMs: source.spanMs || 0, spanX, moments, breaks, xOfMs, ticks,
    live: source.live === true, nowMs: live ? live.ms : null, nowX: live ? live.x : null };
}

// ---------------------------------------------------------------- lanes

function laneRecord(bySeq, lane, rec, sessionEndMs, sessionEndX) {
  const opener = bySeq.get(lane.seq);
  const openKnown = timeKnownOf(opener);
  const openMs = opener ? opener.relMs : null;
  const openX = opener ? opener.x : 0;
  const close = rec.close;
  const closeKnown = timeKnownOf(close);
  const updates = rec.updates;
  const lastUpdate = updates.length ? updates[updates.length - 1] : null;
  let state = "unknown";
  let idle = false;
  if (close) state = "finished";
  else if (lastUpdate && (lastUpdate.state === "running" || lastUpdate.state === "waiting")) state = lastUpdate.state;
  else if (lastUpdate && lastUpdate.state === "idle") { state = "running"; idle = true; }
  const timed = [opener, ...rec.touched].filter(timeKnownOf);
  const placedAt = [opener, ...rec.touched].filter(positioned);
  const lastMs = timed.length ? Math.max(...timed.map((element) => element.relMs)) : openMs;
  const lastX = placedAt.length ? Math.max(...placedAt.map((element) => element.x)) : openX;

  const waitSpans = [];
  let waiting = null;
  // A span's time is known only when both of its ends state one; on the sequence axis it still has a position.
  const msOf = (element) => (timeKnownOf(element) ? element.relMs : null);
  for (const update of updates) {
    if (!positioned(update)) continue; // an update with no position starts or ends no span
    if (waiting) {
      waiting.toMs = waiting.fromMs === null ? null : msOf(update); waiting.toX = update.x; waiting.open = false;
      waitSpans.push(waiting);
      waiting = null;
    }
    // T061: what the event says it waits on and on what basis; a v0.1 wait states neither (both null).
    if (update.state === "waiting") {
      waiting = { seq: update.seq, fromMs: msOf(update), fromX: update.x, toMs: null, toX: null, open: true,
        waitingOn: typeof update.waitingOn === "string" ? update.waitingOn : null,
        basis: update.waitingBasis === "declared" || update.waitingBasis === "observed" ? update.waitingBasis : null };
    }
  }
  if (waiting) {
    if (close && positioned(close)) {
      waiting.toMs = waiting.fromMs === null ? null : msOf(close); waiting.toX = close.x; waiting.open = false;
    }
    waitSpans.push(waiting);
  }

  return {
    laneIndex: lane.laneIndex, strandId: lane.strandId, label: lane.label, displayLabel: lane.label, ordinal: null,
    host: lane.host, role: lane.role, declared: lane.declared, unverified: Boolean(lane.unverified),
    parentStrandId: lane.parentStrandId === undefined ? null : lane.parentStrandId, parentLane: null, orphan: false, depth: 0,
    openSeq: lane.seq, openMs, openX, openKnown,
    closeSeq: close ? close.seq : null, closeMs: close && closeKnown ? close.relMs : null, closeX: close ? close.x : null, closeKnown,
    outcome: close ? (typeof close.outcome === "string" ? close.outcome : "unknown") : null,
    state, idle, inferred: !close && state !== "unknown",
    durationMs: close && openKnown && closeKnown ? Math.max(0, close.relMs - openMs) : null,
    observedMs: openKnown && lastMs !== null ? Math.max(0, (close && closeKnown ? close.relMs : lastMs) - openMs) : null,
    endMs: close && closeKnown ? close.relMs : sessionEndMs, endX: close ? close.x : sessionEndX,
    lastMs, lastX,
    // T062: `durationMs` only when the host stated it (`toolDurationMs`, live only); otherwise `intervalMs` is the
    // time to the agent's next event that states one, labelled as an interval and never as a duration.
    toolMarks: updates.filter((update) => typeof update.toolName === "string" && update.toolName)
      .map((update) => {
        const next = timeKnownOf(update) ? rec.touched.find((other) => other.order > update.order && timeKnownOf(other)) : null;
        return { seq: update.seq, ms: update.relMs, x: update.x, toolName: update.toolName, state: update.state,
          timeKnown: timeKnownOf(update),
          durationMs: Number.isInteger(update.toolDurationMs) && update.toolDurationMs >= 0 ? update.toolDurationMs : null,
          intervalMs: next ? Math.max(0, next.relMs - update.relMs) : null };
      }),
    waitSpans,
    gaps: rec.gaps.map((gap) => ({ seq: gap.seq, ms: gap.relMs, x: gap.x, reason: gap.reason, timeKnown: timeKnownOf(gap), placed: Boolean(gap.placed) })),
    seqs: [],
  };
}

// Agents with opening, closing, state and duration, ordered for display (each parent followed by its children).
export function deriveLanes(model, live = null) {
  const empty = { lanes: [], rows: [], byIndex: new Map(), byStrand: new Map(), sessionEndMs: null, sessionEndX: 0 };
  if (!model || !Array.isArray(model.lanes) || !Array.isArray(model.elements)) return empty;
  const bySeq = new Map(model.elements.map((element) => [element.seq, element]));
  const perStrand = new Map();
  const touchedBy = new Map();
  const timedElements = model.elements.filter(timeKnownOf);
  const placedElements = model.elements.filter(positioned);
  // An agent still open ends at the session's last event, or at now in live mode (T060: running bars grow).
  const sessionEndMs = live ? live.ms : timedElements.length ? Math.max(...timedElements.map((element) => element.relMs)) : null;
  const sessionEndX = live ? live.x : placedElements.length ? Math.max(...placedElements.map((element) => element.x)) : 0;
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
      ms: element.relMs, x: element.x, timeKnown: element.timeKnown !== false, positioned: positioned(element), overlap,
    });
  }
  return out;
}

export function conflictsOf(crossings) {
  return crossings.filter((crossing) => crossing.kind === "predicted");
}

// Number of agents open at each instant (F1), as steps in session time, with the peak. A lane still open at the
// end of the session counts up to the last event.
export function deriveConcurrency(derived, basis) {
  const edges = [];
  if (basis === "mixed" || basis === "sequence-only") return { steps: [], peak: 0, peakMs: null };
  for (const lane of derived.lanes) {
    // only lanes whose state is known count: an agent with no update and no close is not shown as open
    if (!lane.openKnown || lane.openMs === null || lane.endMs === null || lane.state === "unknown") continue;
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
export function deriveOverlaps(model, derived, crossings, limit = 64, axisBasis = null) {
  const basis = axisBasis || (model && model.axis ? model.axis.basis : "sequence-only");
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
    if (span.fromMs === null || span.toMs === null) known = false;
    else total += Math.max(0, span.toMs - span.fromMs);
  }
  return { totalMs: total, open: lane.waitSpans.some((span) => span.open), complete: known };
}

// ---------------------------------------------------------------- VIS.1d: live loom, plan map, lane ids

// The part of the model the live loom draws (REQ-025): the events that state a time and the agents they open.
// Events that state no time (analysis reports and their operations) go to the plan map instead, so the loom keeps
// a real time axis and never falls back to event order. The axis basis is recomputed over the kept events.
export function liveSubset(model) {
  if (!model || !Array.isArray(model.elements) || !Array.isArray(model.lanes)) return model;
  if (!needsSequenceAxis(model)) return model;
  const elements = model.elements.filter(timeKnownOf);
  const kept = new Set(elements.map((element) => element.seq));
  const lanes = model.lanes.filter((lane) => kept.has(lane.seq));
  const bases = new Set(elements.map((element) => element.basis).filter((basis) => typeof basis === "string"));
  const basis = bases.size === 1 ? [...bases][0] : bases.size ? "mixed" : "sequence-only";
  return { ...model, elements, lanes, axis: { ...(model.axis || {}), basis } };
}

// The plans of the plan map: one per analysis report, with its operations in dependency order and its classified
// pairs. An operation's column is the length of the longest chain of declared waits (T061 `waitingOn`) that leads to
// it; an operation with no declared wait is in column 0. Nothing here states a duration.
export function derivePlans(model, derived) {
  if (!model || !Array.isArray(model.elements) || !derived) return [];
  const plans = new Map();
  const keyOf = (element) => (element && element.evidenceRef && typeof element.evidenceRef.path === "string" ? element.evidenceRef.path : "plan");
  const planOf = (element) => {
    const key = keyOf(element);
    if (!plans.has(key)) plans.set(key, { key, seq: null, ops: [], opSeqs: new Map(), pairs: [], columns: new Map(), waits: [] });
    return plans.get(key);
  };
  // Operations come from each report's own strand openings: one strand id can appear in several reports, while the
  // model keeps one lane per strand id, so a lane may belong to more than one plan.
  for (const element of model.elements) {
    if (element.timeKnown !== false) continue;
    if (element.element === "report") {
      const plan = planOf(element);
      plan.seq = plan.seq === null ? element.seq : Math.max(plan.seq, element.seq);
    } else if (element.element === "strand") {
      const lane = derived.byIndex.get(Array.isArray(element.lanes) ? element.lanes[0] : undefined);
      const plan = planOf(element);
      if (lane && !plan.ops.includes(lane)) { plan.ops.push(lane); plan.opSeqs.set(lane.laneIndex, element.seq); }
    } else if (element.element === "strand-state" && element.state === "waiting" && typeof element.waitingOn === "string") {
      planOf(element).waits.push({ from: element.strandId, on: element.waitingOn });
    }
  }
  for (const crossing of derived.crossings) {
    if (crossing.timeKnown) continue;
    const element = model.elements.find((item) => item.seq === crossing.seq);
    if (plans.has(keyOf(element))) plans.get(keyOf(element)).pairs.push(crossing);
  }
  // An operation's column is the length of the longest chain of this report's declared waits that leads to it.
  for (const plan of plans.values()) {
    const on = new Map();
    for (const wait of plan.waits) {
      if (!on.has(wait.from)) on.set(wait.from, []);
      on.get(wait.from).push(wait.on);
    }
    const depth = new Map();
    const visit = (strandId, trail) => {
      if (depth.has(strandId)) return depth.get(strandId);
      if (trail.has(strandId)) { cyclic = true; return 0; } // a cycle of declared waits is drawn flat, never resolved by guesswork
      trail.add(strandId);
      let column = 0;
      for (const target of on.get(strandId) || []) {
        if (plan.ops.some((lane) => lane.strandId === target)) column = Math.max(column, visit(target, trail) + 1);
      }
      trail.delete(strandId);
      depth.set(strandId, column);
      return column;
    };
    let cyclic = false;
    for (const lane of plan.ops) visit(lane.strandId, new Set());
    // with a cycle, depths would depend on the order operations were visited: draw the whole plan flat instead
    for (const lane of plan.ops) plan.columns.set(lane.laneIndex, cyclic ? 0 : depth.get(lane.strandId));
    delete plan.waits;
  }
  // Newest first: report folders carry a UTC stamp ("analysis-<stamp>-<id>"), so the key order is the time order.
  return [...plans.values()].filter((plan) => plan.ops.length > 0)
    .sort((a, b) => (a.key < b.key ? 1 : a.key > b.key ? -1 : 0));
}

// T064: a short id per host lane, the first characters of its salted strand id (stable within one server session,
// since the salt is per session). Ids that would collide are lengthened together until they differ. No new data.
export const SHORT_ID_LENGTH = 5;
export function shortIds(lanes) {
  const out = new Map();
  const ids = [...new Set(lanes.filter((lane) => lane.host !== "braid" && typeof lane.strandId === "string").map((lane) => lane.strandId))];
  let pending = ids;
  let length = SHORT_ID_LENGTH;
  while (pending.length) {
    const groups = new Map();
    for (const id of pending) {
      const prefix = id.slice(0, length);
      if (!groups.has(prefix)) groups.set(prefix, []);
      groups.get(prefix).push(id);
    }
    const next = [];
    for (const [prefix, members] of groups) {
      if (members.length === 1 || members.every((id) => id.length <= length)) for (const id of members) out.set(id, prefix);
      else next.push(...members);
    }
    pending = next;
    length += 1;
  }
  return out;
}

// The facts of the Now sentence and the KPI strip (REQ-024), as numbers and lane references; wording is in strings.js.
// `loom` is the derived live part, `plans` the plan map. A collision count exists only when an observed-collision
// source exists (SC-023): today none does, so `collided` is null and no tile or zero is shown.
export function nowFacts(loom, plans) {
  const lanes = loom ? loom.lanes : [];
  const running = lanes.filter((lane) => lane.state === "running");
  const waiting = lanes.filter((lane) => lane.state === "waiting");
  const sessions = lanes.filter((lane) => lane.parentLane === null && lane.role !== "subagent");
  const waits = waiting.map((lane) => {
    const span = lane.waitSpans.length ? lane.waitSpans[lane.waitSpans.length - 1] : null;
    return { lane, on: span && span.waitingOn !== null ? loom.byStrand.get(span.waitingOn) || null : null };
  });
  let longest = null;
  for (const lane of lanes) {
    for (const mark of lane.toolMarks) {
      if (mark.durationMs !== null && (!longest || mark.durationMs > longest.mark.durationMs)) longest = { lane, mark };
    }
  }
  const conflicts = [];
  for (const plan of plans) for (const pair of plan.pairs) if (pair.kind === "predicted") conflicts.push({ plan, pair });
  return {
    running, waiting, waits, sessions, subagents: lanes.length - sessions.length, live: lanes.length > 0,
    conflicts, plans: plans.length, operations: plans.reduce((total, plan) => total + plan.ops.length, 0),
    longest, collided: null,
  };
}

// `placedModel` is the model the views draw: the model itself, or its sequence placement when an event states no
// time (see placeBySequence). Every derivation reads the placed model, so the views agree on positions.
// `options.nowMs` advances the live "now" with the page's clock between snapshots (T060); ignored unless live.
export function derive(model, options = {}) {
  const placedModel = placeBySequence(model);
  const live = placedModel === model ? liveNow(model, options.nowMs) : null;
  const lanes = deriveLanes(placedModel, live);
  const crossings = deriveCrossings(placedModel, lanes);
  const axis = placedModel !== model ? deriveSequenceAxis(placedModel) : deriveAxis(model, live);
  const basis = axis.sequence ? "sequence-only" : model && model.axis ? model.axis.basis : "sequence-only";
  return {
    ...lanes, axis, crossings, conflicts: conflictsOf(crossings), placedModel,
    placedBySeq: new Map(placedModel && Array.isArray(placedModel.elements) ? placedModel.elements.map((element) => [element.seq, element]) : []),
    concurrency: deriveConcurrency(lanes, basis), overlaps: deriveOverlaps(model, lanes, crossings, 64, basis),
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
  if (filters.kinds && filters.kinds.size > 0) {
    const kind = markerKind(element);
    if (kind !== null && !filters.kinds.has(kind)) return false;
  }
  return true;
}

export function hasFilters(state) {
  const f = state.filters;
  return f.agents.size > 0 || f.status.size > 0 || f.kinds.size > 0 || f.onlyProblems || state.hiddenSources.size > 0;
}

// ---------------------------------------------------------------- the URL hash

const HASH_ITEM = /^[\x20-\x7e]{1,64}$/; // printable ASCII; items travel percent-encoded and never as markup
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
  if (state.filters.kinds && state.filters.kinds.size) parts.push("kd=" + [...state.filters.kinds].filter((value) => MARKER_KINDS.includes(value)).join(","));
  if (state.filters.onlyProblems) parts.push("pr=1");
  if (state.viewport && Number.isFinite(state.viewport.x0) && Number.isFinite(state.viewport.x1)) {
    parts.push("x=" + Math.round(state.viewport.x0) + "-" + Math.round(state.viewport.x1));
  }
  return parts.length ? "#" + parts.join("&") : "";
}

export function decodeHash(text) {
  const out = { view: null, selected: null, hide: [], agents: [], status: [], kinds: [], onlyProblems: false, viewport: null };
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
    else if (key === "kd") out.kinds = list().filter((item) => MARKER_KINDS.includes(item));
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
