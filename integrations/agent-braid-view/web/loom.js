// SPDX-License-Identifier: AGPL-3.0-only
// Agent Braid activity viewer: first-party table view of the Loom model, plus the optional 3D scene.
//
// The table view, evidence panel, counters and playback work on their own. The Three.js scene
// (braid-scene.js) is loaded afterwards with a dynamic import and only when WebGL2 exists; if it is
// missing, refused or fails, the page says so and keeps the table. The scene is bound to this model,
// this playback position and this evidence panel: it only calls `select` and reads `state`.
//
// Read-only. It fetches /snapshot (the model built by the server) and follows /events
// (Server-Sent Events, resumed with Last-Event-ID) only to learn that the model changed.
// Every value from an event reaches the page as a text node: elements are built with
// createElement and textContent, never from markup strings, which the Trusted Types
// directive of the content security policy would refuse anyway. Nothing here sends data
// anywhere except same-origin GET requests, and nothing is an authorization.

const CLASS_LABELS = ["heuristic", "syntactic", "semantic", "transactional", "confluence", "Yang–Baxter"];

const VERIFICATION = {
  rehashed: ["✓", "rehashed", "An adapter read the artifact and this viewer session computed the hash."],
  derived: ["≈", "derived", "Derived by the viewer from rehashed events."],
  unverified: ["⚠", "unverified", "Replayed or host-reported. Nothing here was checked by this viewer."],
};

const CROSSING_SHAPES = {
  "swap": ["⇄", "swap: independent candidate"],
  "ordered-link": ["→", "ordered link"],
  "conflict-knot": ["✕", "conflict knot"],
  "unknown-link": ["?", "unknown link"],
  "bridge": ["⌒", "bridge: passes over lanes, does not cross"],
  "unplaced": ["·", "unplaced pair"],
};

const ELEMENT_SHAPES = {
  "strand": ["│", "strand"],
  "strand-state": ["│", "strand state"],
  "strand-end": ["└", "strand end"],
  "effort": ["Σ", "effort (host estimate)"],
  "wave-plane": ["▤", "planned waves (advisory)"],
  "wave-marker": ["▸", "wave marker"],
  "hazard-cone": ["△", "hazard"],
  "gap": ["▯", "observation gap"],
  "runtime-phase": ["○", "runtime phase"],
  "session": ["□", "session"],
  "report": ["¶", "analysis report"],
};

const RING_SHAPES = {
  "grant": ["◯", "grant"],
  "workflow-phase": ["◎", "gate phase"],
  "workflow-result": ["◉", "gate result"],
};

const MARKS = {
  unverified: ["unverified", "Not checked by this viewer. Never counted as a verified fact."],
  uncertain: ["uncertain", "Unknown classification or incomplete coverage. Not independent, not clean."],
  partial: ["partial coverage", "Coverage is not complete: what is not listed is not shown to be absent."],
  absence: ["not observed", "A hazard that was not observed or only partly observed. This is not evidence that none exists."],
  gap: ["gap", "The viewer or a host did not observe this range."],
  notime: ["no time", "The event states no time. It is placed after its predecessor, no time is invented."],
};

const SCENE_LEGEND = [
  "Tube: one strand per agent or unit. Its colour is the host, never a status.",
  "Two tubes exchanging lanes: an independent candidate pair. The swap is layout only and not a guarantee.",
  "Arc over other lanes: an independent candidate pair between lanes that are not adjacent. It does not cross them.",
  "Arrow: an ordered pair. Red knot between two stubs: a conflicting pair, never a swap.",
  "Dashed pulsing link: an unknown pair. It is not independent and not clean.",
  "Polygon badge on a crossing: the compatibility class. The sides are 3 plus the class number. Every badge looks the same otherwise: a class is a categorical label, not a guarantee and not a safety ordering.",
  "Translucent slabs: planned waves, an advisory plan, not a runtime measurement. Framed slabs: runtime wave markers.",
  "Thin ring: a grant. Thick ring: a workflow gate or gate phase. The sides and colour follow the state or result, and the label names it.",
  "Cone with sparks: an observed hazard. Dashed pulsing wire cone: a hazard that was not observed. Absence of observation is not evidence that none exists.",
  "Broken strand with a grey dashed stub: an observation gap. Pulsing ring on a crossing: partial coverage, so what is not listed is not shown to be absent.",
  "Grey shapes: a value this viewer does not recognise (a pair classification, a gate state or a grant state). The label says unrecognized.",
  "Amber wire octahedron: unverified. Replayed or host-reported, and not checked by this viewer.",
  "Effort and tokens are not drawn in this release.",
];

const ATTRS = /^(type|title|value|data-[a-z-]+|aria-[a-z-]+)$/;
const STEP_MS = 700;

const state = {
  model: null,
  dropped: [],
  cursor: 0,
  playing: false,
  timer: null,
  selected: null,
  filterKind: "",
  filterUncertain: false,
  hiddenSources: new Set(),
  lastId: "",
};

// ---------------------------------------------------------------- DOM helpers

function h(tag, props, ...children) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props || {})) {
    if (value === null || value === undefined || value === false) continue;
    if (key === "class") node.className = value;
    else if (key === "on") for (const [name, fn] of Object.entries(value)) node.addEventListener(name, fn);
    else if (ATTRS.test(key)) node.setAttribute(key, value === true ? "" : String(value));
    else throw new Error("attribute not allowed: " + key);
  }
  for (const child of children.flat()) {
    if (child === null || child === undefined || child === false) continue;
    node.append(child instanceof Node ? child : document.createTextNode(String(child)));
  }
  return node;
}

function $(id) {
  return document.getElementById(id);
}

function fill(id, ...children) {
  $(id).replaceChildren(...children.flat().filter((child) => child !== null && child !== undefined));
}

// ---------------------------------------------------------------- labels

function classLabel(value) {
  if (value === null || value === undefined) return "none (not a per-pair analysis result)";
  const name = CLASS_LABELS[value];
  return name === undefined ? "unrecognized class " + String(value) : "class " + value + " · " + name;
}

function shapeOf(element) {
  if (element.element === "crossing") {
    const [glyph, label] = CROSSING_SHAPES[element.drawAs] || ["?", "crossing"];
    return [glyph, element.incompleteCoverage && element.isSwap ? label + " (partial coverage)" : label];
  }
  if (element.element === "gate-ring") return RING_SHAPES[element.ringKind] || ["◯", "gate"];
  return ELEMENT_SHAPES[element.element] || ["·", element.element];
}

function marksOf(element) {
  const marks = [];
  if (element.unverified || !VERIFICATION[element.verification]) marks.push("unverified");
  if (element.uncertain) marks.push("uncertain");
  if (element.incompleteCoverage) marks.push("partial");
  if (element.absence) marks.push("absence");
  if (element.element === "gap") marks.push("gap");
  if (element.timeKnown === false) marks.push("notime");
  return marks;
}

function markNode(key) {
  const [label, meaning] = MARKS[key];
  return h("span", { class: "mark " + key, title: meaning }, label);
}

function verificationNode(value) {
  const entry = VERIFICATION[value];
  if (!entry) return h("span", { class: "mark uncertain" }, "unrecognized: " + String(value));
  return h("span", { class: "mark " + (value === "unverified" ? "unverified" : ""), title: entry[2] },
    entry[0] + " " + entry[1]);
}

function timeText(element) {
  if (!element.timeKnown) return "sequence only";
  return String(element.relMs) + " ms";
}

// ---------------------------------------------------------------- event sources

// The page offers one checkbox per source of events, all checked by default. The model carries no adapter name and
// no root, so the source is derived from the two fields every element has from its event's source block: the
// verification status and whether an evidence reference exists. Nothing is added to the event contract.
//   rehashed or derived, with an evidence reference: read from a watched root by an adapter
//   rehashed or derived, without one: produced by the viewer itself (for example a ring-eviction gap)
//   anything else, with an evidence reference: a replay file (every replayed event is unverified)
//   anything else, without one: a host report (hook or telemetry ingest)
const SOURCES = {
  watched: ["Watched artifacts", "Read from the watched or discovered artifact roots and re-hashed by this session. The model does not name the root, so all roots form one source."],
  replay: ["Replay file", "Recorded events loaded with --replay. Never re-hashed by this session."],
  hook: ["Hook and telemetry ingest", "Reported by a host with no artifact behind it. Recorded host events in a replay file without an artifact also appear here. Not checked by this viewer."],
  viewer: ["Derived by the viewer", "Produced by this viewer itself, such as gaps for evicted or truncated ranges."],
};

function sourceOf(element) {
  const referenced = Boolean(element.evidenceRef);
  if (element.verification === "rehashed" || element.verification === "derived") return referenced ? "watched" : "viewer";
  return referenced ? "replay" : "hook";
}

function countSources(elements) {
  const counts = {};
  for (const element of elements) counts[sourceOf(element)] = (counts[sourceOf(element)] || 0) + 1;
  return counts;
}

function isSourceShown(element, hidden) {
  return !hidden.has(sourceOf(element));
}

function hiddenEventCount(counts, hidden) {
  let total = 0;
  for (const key of hidden) total += counts[key] || 0;
  return total;
}

function hiddenText(hidden, total) {
  return hidden === 0
    ? "All sources are shown: 0 events hidden."
    : hidden + " of " + total + " retained events are hidden because their source is unchecked. Hidden is not absent: " +
      "the counters and the list of what is not shown as clean still count them.";
}

// ---------------------------------------------------------------- legend (static tables above)

function renderLegend() {
  fill("legend-classes", CLASS_LABELS.map((name, index) => h("li", null, "class " + index + " · " + name)),
    h("li", null, "no class: the event is not a per-pair analysis result"));
  fill("legend-shapes",
    Object.values(CROSSING_SHAPES).map(([glyph, label]) => h("li", null, h("span", { class: "glyph" }, glyph), label)),
    Object.values(ELEMENT_SHAPES).map(([glyph, label]) => h("li", null, h("span", { class: "glyph" }, glyph), label)),
    Object.values(RING_SHAPES).map(([glyph, label]) => h("li", null, h("span", { class: "glyph" }, glyph), label)));
  fill("legend-verification", Object.values(VERIFICATION).map(([glyph, label, meaning]) =>
    h("li", null, h("span", { class: "glyph" }, glyph), label + ": " + meaning)));
  fill("legend-marks", Object.keys(MARKS).map((key) => h("li", null, markNode(key), " " + MARKS[key][1])));
  fill("legend-scene", SCENE_LEGEND.map((text) => h("li", null, text)));
}

// ---------------------------------------------------------------- data

let rowsCache = null;
let elementsCache = null;

// The model's elements by seq, built once per model.
function elementOf(seq) {
  if (!state.model) return undefined;
  if (!elementsCache || elementsCache.model !== state.model) {
    elementsCache = { model: state.model, bySeq: new Map(state.model.elements.map((element) => [element.seq, element])) };
  }
  return elementsCache.bySeq.get(seq);
}

let countsCache = null;

// Events per source of the current model, counted once per model.
function sourceCounts() {
  if (!state.model) return {};
  if (!countsCache || countsCache.model !== state.model) {
    countsCache = { model: state.model, counts: countSources(state.model.elements) };
  }
  return countsCache.counts;
}

function hiddenCount() {
  return hiddenEventCount(sourceCounts(), state.hiddenSources);
}

function rowsInOrder() {
  if (!state.model) return [];
  if (rowsCache && rowsCache.model === state.model) return rowsCache.rows;
  const rows = state.model.table
    .map((row) => ({ row, element: elementOf(row.seq) }))
    .filter((entry) => entry.element)
    .sort((a, b) => a.element.order - b.element.order || a.row.seq - b.row.seq);
  rowsCache = { model: state.model, rows };
  return rows;
}

function setNotice(text) {
  const box = $("notice");
  box.textContent = text || "";
  box.hidden = !text;
}

let snapshotRequest = 0;

async function loadSnapshot() {
  const request = ++snapshotRequest;
  let response;
  try {
    response = await fetch("/snapshot", { cache: "no-store", credentials: "same-origin" });
  } catch (error) {
    setNotice("The viewer server cannot be reached.");
    return;
  }
  if (response.status === 404) {
    setNotice("This session is not open. Use the open link printed by the server; it works once.");
    return;
  }
  if (!response.ok) {
    setNotice("The snapshot could not be produced (status " + response.status + "). The last model stays on screen.");
    return;
  }
  let document_;
  try {
    document_ = await response.json();
    if (!document_ || typeof document_.model !== "object" || document_.model === null) throw new Error("no model");
  } catch (error) {
    setNotice("The snapshot is not valid JSON.");
    return;
  }
  if (request !== snapshotRequest) return; // a newer request supersedes this response
  setNotice("");
  const atEnd = state.cursor >= totalCount();
  state.model = document_.model;
  const authorization = $("authorization");
  authorization.textContent = "executionAuthorization: " + String(state.model.executionAuthorization);
  authorization.className = state.model.executionAuthorization === false ? "badge" : "badge mark unverified";
  state.dropped = Array.isArray(document_.droppedAttributeNames) ? document_.droppedAttributeNames : [];
  state.cursor = atEnd ? totalCount() : Math.min(state.cursor, totalCount());
  if (state.selected !== null && !state.model.elements.some((element) => element.seq === state.selected)) {
    state.selected = null;
  }
  try {
    renderAll();
  } catch (error) {
    console.error(error);
    setNotice("The snapshot does not match the model contract and could not be rendered.");
  }
}

function totalCount() {
  return state.model ? state.model.elements.length : 0;
}

// ---------------------------------------------------------------- server-sent events

let refreshTimer = null;

function scheduleRefresh() {
  if (refreshTimer !== null) return;
  refreshTimer = setTimeout(() => {
    refreshTimer = null;
    loadSnapshot();
  }, 150);
}

function setConnection(text) {
  $("connection").textContent = text;
}

function parseBlock(block) {
  let id = null;
  const data = [];
  for (const line of block.split("\n")) {
    if (line.startsWith(":")) continue;
    if (line.startsWith("id:")) id = line.slice(3).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trimStart());
  }
  return { id, data: data.join("\n") };
}

async function followEvents() {
  let delay = 1000;
  for (;;) {
    try {
      const headers = { Accept: "text/event-stream" };
      if (state.lastId) headers["Last-Event-ID"] = state.lastId;
      const response = await fetch("/events", { headers, cache: "no-store", credentials: "same-origin" });
      if (response.status === 404) {
        setConnection("not open");
        return;
      }
      if (!response.ok || !response.body) throw new Error("status " + response.status);
      setConnection("live");
      scheduleRefresh();
      delay = 1000;
      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";
      for (;;) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
        let cut = buffer.indexOf("\n\n");
        while (cut !== -1) {
          const { id, data } = parseBlock(buffer.slice(0, cut));
          buffer = buffer.slice(cut + 2);
          if (id !== null && /^[0-9]{1,16}$/.test(id)) state.lastId = id;
          if (data) {
            scheduleRefresh();
          }
          cut = buffer.indexOf("\n\n");
        }
      }
    } catch (error) {
      // fall through to the reconnect below
    }
    setConnection("reconnecting");
    await new Promise((resolve) => setTimeout(resolve, delay));
    delay = Math.min(delay * 2, 15000);
  }
}

// ---------------------------------------------------------------- counters

function kv(list, label, value, sub) {
  list.push(h("dt", { class: sub ? "sub" : "" }, label), h("dd", null, String(value)));
}

function renderCounters() {
  const model = state.model;
  if (!model) {
    fill("counters");
    fill("absence");
    $("counters-scope").textContent = "";
    return;
  }
  const c = model.counters;
  $("counters-scope").textContent = "Counts over all " + model.eventCount +
    " retained events. They are counts of observed or declared facts, never a speedup or a ratio against serial execution.";
  const out = [];
  kv(out, "conflicts flagged", c.conflictsFlagged);
  kv(out, "ordered pairs", c.orderedPairs);
  kv(out, "independent candidates (complete coverage)", c.independentCandidates);
  kv(out, "unknown pairs", c.unknownPairs);
  kv(out, "drawn as swap", c.swaps);
  kv(out, "drawn as bridge", c.bridges);
  kv(out, "planned wave width (maximum)", c.plannedWaveWidth.maxWidth === null ? "none planned" : c.plannedWaveWidth.maxWidth);
  out.push(h("dd", { class: "full" }, c.plannedWaveWidth.label + " (" + c.plannedWaveWidth.plans + " plan(s))"));
  kv(out, "hazards", c.hazards.total);
  for (const [name, count] of Object.entries(c.hazards.byKind)) kv(out, name, count, true);
  kv(out, "gaps", c.gaps.total);
  for (const [name, count] of Object.entries(c.gaps.byReason)) if (count) kv(out, name, count, true);
  kv(out, "gate phases", c.gates.phases);
  kv(out, "gate results", c.gates.results);
  kv(out, "grants", c.grants.total);
  for (const name of ["issued", "consumed", "expired", "refused"]) kv(out, name, c.grants[name], true);
  kv(out, "unverified elements", c.unverifiedElements);
  fill("counters", out);

  const a = c.absence;
  const gone = [];
  kv(gone, "unknown pairs", a.unknownPairs);
  kv(gone, "independent with incomplete coverage", a.independentWithIncompleteCoverage);
  kv(gone, "hazards not observed or partly observed", a.hazardsNotObserved);
  kv(gone, "observation gaps", a.gaps);
  kv(gone, "elements dropped by a cap", a.truncated);
  for (const cut of model.truncated) kv(gone, "cap on " + cut.what + " (limit " + cut.limit + ")", cut.dropped + " dropped", true);
  fill("absence", gone);
}

function renderLanes() {
  const lanes = state.model ? state.model.lanes : [];
  fill("lanes", lanes.map((lane) => h("li", null,
    lane.label + " ",
    h("span", { class: "hint" }, "(" + (lane.declared ? lane.host + " " + lane.role : "named by a crossing, not declared") + ") "),
    lane.unverified ? markNode("unverified") : null)));
}

function renderDropped() {
  fill("dropped-list", state.dropped.length ? state.dropped.map((name) => h("li", null, name)) : [h("li", null, "none recorded")]);
}

// ---------------------------------------------------------------- source checkboxes

const sourceNodes = new Map();

function renderSources() {
  const counts = sourceCounts();
  const keys = Object.keys(SOURCES).filter((key) => counts[key]);
  $("sources").hidden = keys.length === 0;
  const signature = keys.join("|");
  if ($("source-list").dataset.keys !== signature) {
    // Rebuilt only when the set of sources changes, so a live refresh never takes focus from a checkbox.
    $("source-list").dataset.keys = signature;
    sourceNodes.clear();
    fill("source-list", keys.map((key) => {
      const input = h("input", { type: "checkbox", "data-source": key,
        on: { change: (event) => toggleSource(key, event.target.checked) } });
      const count = h("span", { class: "source-count" });
      sourceNodes.set(key, { input, count });
      return h("label", { class: "source", title: SOURCES[key][1] }, input, " ", SOURCES[key][0], " ", count);
    }));
  }
  for (const key of keys) {
    const node = sourceNodes.get(key);
    node.input.checked = !state.hiddenSources.has(key);
    node.count.textContent = "(" + counts[key] + " events)";
  }
  $("source-status").textContent = hiddenText(hiddenCount(), totalCount());
}

function toggleSource(key, shown) {
  if (shown) state.hiddenSources.delete(key);
  else state.hiddenSources.add(key);
  const selected = state.selected === null ? undefined : elementOf(state.selected);
  if (selected && !isSourceShown(selected, state.hiddenSources)) state.selected = null;
  renderSources();
  renderTable();
  renderEvidence();
}

// ---------------------------------------------------------------- table

function visibleRows() {
  return rowsInOrder().slice(0, state.cursor).filter(({ row, element }) => {
    if (!isSourceShown(element, state.hiddenSources)) return false;
    if (state.filterKind && element.element !== state.filterKind) return false;
    if (state.filterUncertain && marksOf(element).length === 0) return false;
    return true;
  });
}

function renderKindFilter() {
  const select = $("filter-kind");
  const kinds = [...new Set((state.model ? state.model.elements : []).map((element) => element.element))].sort();
  if (state.filterKind && !kinds.includes(state.filterKind)) state.filterKind = "";
  const key = kinds.join("|");
  if (select.dataset.kinds === key) return;
  select.dataset.kinds = key;
  select.replaceChildren(h("option", { value: "" }, "all"),
    ...kinds.map((kind) => h("option", { value: kind }, kind)));
  select.value = state.filterKind;
}

function renderTable() {
  const rows = visibleRows();
  const last = state.cursor > 0 ? rowsInOrder()[state.cursor - 1] : null;
  const active = document.activeElement;
  const focusedSeq = active && active.dataset ? active.dataset.seq : null;
  fill("events-body", rows.map(({ row, element }) => {
    const [glyph, label] = shapeOf(element);
    const selected = state.selected === row.seq;
    return h("tr", { class: (selected ? "selected " : "") + (last && last.row.seq === row.seq ? "current" : "") },
    h("td", null, h("button", {
      type: "button", class: "row-button", "aria-label": "Select event " + row.seq,
      "aria-pressed": selected ? "true" : "false", "data-seq": row.seq,
      on: { click: () => select(row.seq) },
    }, (selected ? "\u25B6 " : "") + row.seq)),
    h("td", null, timeText(element)),
    h("td", null, h("span", { class: "glyph", "aria-hidden": "true" }, glyph), label),
    h("td", null, String(row.subject === null || row.subject === undefined ? "" : row.subject)),
    h("td", null, row.status === null || row.status === undefined ? "—" : String(row.status)),
    h("td", null, classLabel(row.compatibilityClass)),
    h("td", null, verificationNode(element.verification)),
    h("td", null, marksOf(element).map(markNode)));
  }));
  if (focusedSeq !== null) {
    const again = $("events-body").querySelector('[data-seq="' + CSS.escape(focusedSeq) + '"]');
    if (again) again.focus({ preventScroll: true });
  }
  $("table-empty").hidden = rows.length > 0;
  const hidden = hiddenCount();
  $("table-empty").textContent = (state.model && totalCount() > 0 && rows.length === 0
    ? "No events at this position or filter." : "No events to show.") +
    (hidden ? " " + hiddenText(hidden, totalCount()) : "");
  syncScene();
}

function select(seq) {
  state.selected = seq;
  renderTable();
  renderEvidence();
}

// ---------------------------------------------------------------- evidence

function listOrNone(values, none) {
  if (!Array.isArray(values) || values.length === 0) return h("span", null, none);
  return h("ul", null, values.map((value) => h("li", null, String(value))));
}

function definitions(pairs) {
  const nodes = [];
  for (const [label, value] of pairs) nodes.push(h("dt", null, label), h("dd", null, value));
  return h("dl", null, nodes);
}

function section(title, ...body) {
  return h("section", { class: "evidence-section" }, h("h3", null, title), body);
}

function detailPairs(element) {
  switch (element.element) {
    case "crossing": {
      const evidence = element.evidence || {};
      const coverage = Array.isArray(evidence.coverage) ? evidence.coverage : [];
      const report = element.report;
      return [
        ["classification", element.classification],
        ["drawn as", shapeOf(element)[1]],
        ["left strand", element.left],
        ["right strand", element.right],
        ["shared resources", listOrNone(element.sharedResources, "none recorded")],
        ["evidence method", String(evidence.method)],
        ["rule set", String(evidence.ruleSet)],
        ["coverage", coverage.join(", ") + (element.incompleteCoverage
          ? " (incomplete: resources not listed are not shown to be absent)" : "")],
        ["reasons", listOrNone(element.reasons, "none recorded")],
        ["constraints", listOrNone(element.constraints, "none recorded")],
        ["lanes passed over", element.passesOverLanes.length ? element.passesOverLanes.join(", ") : "none"],
        ["report uncertainty", report ? listOrNone(report.uncertainty, "none recorded") : "no report in the retained events"],
        ["report limits", report ? listOrNone(report.limits, "none recorded") : "no report in the retained events"],
      ];
    }
    case "hazard-cone":
      return [["hazard", element.hazardKind], ["stage", element.stage], ["units", listOrNone(element.units, "none")],
        ["not observed", element.absence ? "yes: absence of observation is not evidence that no hazard exists" : "no"]];
    case "gap":
      return [["reason", element.reason], ["strand", element.strandId === null ? "none" : element.strandId],
        ["from seq", element.fromSeq === null ? "unknown" : element.fromSeq],
        ["to seq", element.toSeq === null ? "unknown" : element.toSeq]];
    case "wave-plane":
      return [["plan", element.planId], ["mode", element.mode], ["label", element.label],
        ["waves", listOrNone(element.waves.map((wave) => wave.width + " wide: " + wave.strands.join(", ")), "none")]];
    case "wave-marker":
      return [["schedule", element.scheduleId], ["wave", element.wave], ["phase", element.phase],
        ["strands", listOrNone(element.strands, "none")]];
    case "gate-ring":
      return element.ringKind === "grant"
        ? [["grant", element.grantId], ["action", element.action], ["state", element.state],
          ["derived by the viewer", element.derived ? "yes" : "no"]]
        : [["gate", element.gateId], ["status", element.gateStatus],
          element.ringKind === "workflow-phase" ? ["phase", element.phase] : ["operation count", element.operationCount]];
    case "effort":
      return [["basis", element.effortBasis], ["known tokens (input + output)", element.knownTokens === null ? "unknown" : element.knownTokens]];
    default:
      return [];
  }
}

function renderEvidence() {
  const element = state.selected === null ? undefined : elementOf(state.selected);
  if (!element) {
    fill("evidence", h("p", { class: "hint" },
      "Select an event to see its source event, class, verification and evidence reference."));
    return;
  }
  const ref = element.evidenceRef;
  const marks = marksOf(element);
  fill("evidence",
    h("p", null, h("strong", null, "Event " + element.seq + " · " + element.kind), " ", marks.map(markNode)),
    section("Event", definitions([
      ["element", element.element],
      ["subject", String(element.subject === null || element.subject === undefined ? "" : element.subject)],
      ["status", element.status === null || element.status === undefined ? "—" : String(element.status)],
      ["host", element.host],
      ["time", timeText(element) + " (" + element.basis + ")"],
    ])),
    section("Compatibility class", h("p", null, classLabel(element.compatibilityClass)),
      h("p", { class: "hint" }, "A categorical label, not a guarantee and not a safety ordering.")),
    section("Verification", h("p", null, verificationNode(element.verification)),
      h("p", { class: "hint" }, (VERIFICATION[element.verification] || ["", "", ""])[2])),
    section("Evidence reference", ref
      ? definitions([["path", ref.path], ["sha256", ref.sha256]])
      : h("p", null, "None: the event is host-reported or derived by the viewer, so there is no artifact to open.")),
    detailPairs(element).length ? section("Details", definitions(detailPairs(element))) : null,
    h("details", null, h("summary", null, "All model fields"), h("pre", null, JSON.stringify(element, null, 2))));
}

// ---------------------------------------------------------------- playback

function renderPlayback() {
  const total = totalCount();
  const range = $("pb-range");
  range.max = String(total);
  range.value = String(state.cursor);
  $("pb-count").textContent = state.cursor + " of " + total;
  range.setAttribute("aria-valuetext", state.cursor + " of " + total + " events");
  $("pb-back").disabled = state.cursor <= 0;
  $("pb-start").disabled = state.cursor <= 0;
  $("pb-forward").disabled = state.cursor >= total;
  $("pb-play").setAttribute("aria-pressed", state.playing ? "true" : "false");
}

function setCursor(value) {
  state.cursor = Math.max(0, Math.min(totalCount(), value));
  renderTable();
  renderPlayback();
}

function stopPlayback() {
  state.playing = false;
  if (state.timer !== null) clearTimeout(state.timer);
  state.timer = null;
}

function tick() {
  state.timer = null;
  if (!state.playing) return;
  if (state.cursor >= totalCount()) {
    stopPlayback();
    renderPlayback();
    return;
  }
  setCursor(state.cursor + 1);
  const speed = Number($("pb-speed").value) || 1;
  state.timer = setTimeout(tick, STEP_MS / speed);
}

function togglePlay() {
  if (state.playing) {
    stopPlayback();
  } else {
    if (state.cursor >= totalCount()) state.cursor = 0;
    state.playing = true;
    state.timer = setTimeout(tick, 0);
  }
  renderTable();
  renderPlayback();
}

function bindControls() {
  $("pb-start").addEventListener("click", () => { stopPlayback(); setCursor(0); });
  $("pb-back").addEventListener("click", () => { stopPlayback(); setCursor(state.cursor - 1); });
  $("pb-forward").addEventListener("click", () => { stopPlayback(); setCursor(state.cursor + 1); });
  $("pb-end").addEventListener("click", () => { stopPlayback(); setCursor(totalCount()); });
  $("pb-play").addEventListener("click", togglePlay);
  $("pb-range").addEventListener("input", (event) => { stopPlayback(); setCursor(Number(event.target.value)); });
  $("filter-kind").addEventListener("change", (event) => { state.filterKind = event.target.value; renderTable(); });
  $("filter-uncertain").addEventListener("change", (event) => { state.filterUncertain = event.target.checked; renderTable(); });
  $("scene-reset").addEventListener("click", () => { if (scene) scene.resetView(); });
}

// ---------------------------------------------------------------- 3D scene (optional)

let scene = null;
let sceneModel = null;
let sceneCursor = -1;
let sceneSelected = null;
let sceneHidden = "";

function showHover(seq) {
  const element = seq === null ? undefined : elementOf(seq);
  $("scene-hover").textContent = element
    ? "Event " + element.seq + " · " + element.kind + " · " + String(element.subject === null || element.subject === undefined ? "" : element.subject) +
      " · " + classLabel(element.compatibilityClass) + (marksOf(element).includes("unverified") ? " · unverified" : "")
    : "Hover an element to see its event.";
}

function updateSceneNote() {
  const info = scene.summary();
  const parts = ["Showing " + info.drawn + " of " + info.visible + " events at this position in 3D."];
  const hidden = hiddenCount();
  if (hidden) parts.push(hidden + " events from unchecked sources are hidden here and in the table. They are not absent.");
  const untimed = info.seqs.filter((seq) => { const element = elementOf(seq); return element && element.timeKnown === false; }).length;
  if (untimed) parts.push(untimed + " of them state no time: the scene places them after their predecessor and invents no time.");
  if (info.omitted.length) {
    parts.push("Only in the table: " + info.omitted.map((item) => item.count + " (" + item.reason + ")").join("; ") + ".");
  }
  $("scene-note").textContent = parts.join(" ");
}

// Keeps the scene on the model, playback position and selection of the table. Cheap when nothing changed.
function syncScene() {
  if (!scene) return;
  try {
    applyScene();
  } catch (error) {
    console.error(error);
    sceneUnavailable("it could not draw this model.");
  }
}

function applyScene() {
  const modelChanged = sceneModel !== state.model;
  if (modelChanged) {
    sceneModel = state.model;
    scene.setModel(state.model);
  }
  const hidden = [...state.hiddenSources].sort().join("|");
  if (modelChanged || sceneCursor !== state.cursor || sceneHidden !== hidden) {
    sceneCursor = state.cursor;
    sceneHidden = hidden;
    // The scene shows only checked sources; the playback frontier still follows the position, not the filter.
    const position = rowsInOrder().slice(0, state.cursor);
    scene.setVisible(
      position.filter(({ element }) => isSourceShown(element, state.hiddenSources)).map(({ row }) => row.seq),
      position.map(({ row }) => row.seq));
    updateSceneNote();
  }
  if (modelChanged || sceneSelected !== state.selected) {
    sceneSelected = state.selected;
    scene.setSelected(state.selected);
  }
}

function sceneUnavailable(reason) {
  if (scene) {
    try {
      scene.dispose();
    } catch (error) {
      console.error(error);
    }
    scene = null;
  }
  $("scene-section").hidden = false;
  $("scene-box").hidden = true;
  $("scene-hover").hidden = true;
  $("scene-reset").hidden = true;
  $("legend-scene-block").hidden = true;
  $("scene-note").textContent = "The 3D scene is not available: " + reason + " The table below shows the same events, counters and evidence.";
}

async function startScene() {
  if (typeof WebGL2RenderingContext !== "function") {
    sceneUnavailable("this browser has no WebGL2.");
    return;
  }
  let module_;
  try {
    module_ = await import("/web/braid-scene.js");
  } catch (error) {
    console.error(error);
    sceneUnavailable("its code could not be loaded or was refused.");
    return;
  }
  $("scene-section").hidden = false; // the canvas needs a laid-out box to size itself
  try {
    scene = module_.createBraidScene($("scene-box"), { onSelect: select, onHover: showHover, onUnavailable: sceneUnavailable });
  } catch (error) {
    console.error(error);
    sceneUnavailable("WebGL2 could not be started.");
    return;
  }
  $("legend-scene-block").hidden = false;
  syncScene();
}

// ---------------------------------------------------------------- start

function renderAll() {
  renderSources();
  renderKindFilter();
  renderCounters();
  renderLanes();
  renderDropped();
  renderTable();
  renderEvidence();
  renderPlayback();
}

renderLegend();
bindControls();
renderAll();
loadSnapshot();
followEvents();
startScene();
