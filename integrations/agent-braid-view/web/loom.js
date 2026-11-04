// SPDX-License-Identifier: AGPL-3.0-only
// Agent Braid activity viewer: first-party shell of the Loom model (SPEC-061 VIS.1a, redesigned in VIS.1c).
//
// This file fetches the model, follows the server, keeps the one shared state (state.js) and renders the page
// around it: header, toolbar, the main view, the detail panel, playback and the tabs (events table, summary,
// legend, help). The optional 3D scene (braid-scene.js) is loaded afterwards with a dynamic import and only when
// WebGL2 exists; if it is missing, refused or fails, the page says so and keeps the table. Views are bound to
// this state: they only call `select` and read the model, the playback position and the filters.
//
// Read-only. It fetches /snapshot (the model built by the server) and follows /events (Server-Sent Events,
// resumed with Last-Event-ID) only to learn that the model changed. Every value from an event reaches the page as a
// text node: elements are built with createElement and textContent, never from markup strings, which the Trusted
// Types directive of the content security policy would refuse anyway. All user-facing wording lives in strings.js.
// Nothing here sends data anywhere except same-origin GET requests, and nothing is an authorization.

import {
  createState, derive, summarize, formatClock, formatDuration, marksOf, sourceOf, sourceKeys, ROOT_PREFIX, orderedRows,
  passesFilters, hasFilters, encodeHash, decodeHash, readPreference, writePreference, waitingTime, LANE_STATES,
  MARKER_KINDS, markerKind,
} from "./state.js";
import { createTimeline, iconNode } from "./timeline.js";
import { translate, chooseLanguage, normalizeTag, LANGUAGES } from "./strings.js";

const CLASS_NAMES = ["heuristic", "syntactic", "semantic", "transactional", "confluence", "Yang–Baxter"];

// [glyph, key]: the key is the verification value, its label is `verification.<key>` and its meaning `verification.<key>.meaning`.
const VERIFICATION = { rehashed: "✓", derived: "≈", unverified: "⚠" };

// [glyph, string key of the label]
const CROSSING_SHAPES = {
  "swap": ["⇄", "shape.swap"],
  "ordered-link": ["→", "shape.orderedLink"],
  "conflict-knot": ["✕", "shape.conflictKnot"],
  "unknown-link": ["?", "shape.unknownLink"],
  "bridge": ["⌒", "shape.bridge"],
  "unplaced": ["·", "shape.unplaced"],
};

const ELEMENT_SHAPES = {
  "strand": ["│", "shape.strand"],
  "strand-state": ["│", "shape.strandState"],
  "strand-end": ["└", "shape.strandEnd"],
  "effort": ["Σ", "shape.effort"],
  "wave-plane": ["▭", "shape.wavePlane"],
  "wave-marker": ["▣", "shape.waveMarker"],
  "hazard-cone": ["△", "shape.hazardCone"],
  "gap": ["▯", "shape.gap"],
  "runtime-phase": ["○", "shape.runtimePhase"],
  "session": ["□", "shape.session"],
  "report": ["¶", "shape.report"],
};

const RING_SHAPES = {
  "grant": ["◯", "shape.grant"],
  "workflow-phase": ["◎", "shape.gatePhase"],
  "workflow-result": ["◉", "shape.gateResult"],
};

const MARK_KEYS = ["unverified", "uncertain", "partial", "absence", "gap", "notime"];
const SCENE_LEGEND_KEYS = ["tube", "swap", "bridge", "ordered", "unknown", "badge", "slabs", "rings", "hazard", "gap", "grey", "unverified", "effort"];

// The scene reports why an event is not drawn in English; the page shows it in the viewer's language.
const SCENE_REASON_KEYS = {
  "session origin: shown in the table": "scene.reason.session",
  "analysis report: shown in the table and the evidence panel": "scene.reason.report",
  "runtime phase: shown in the table": "scene.reason.runtimePhase",
  "effort and tokens are not drawn in this release: shown in the table": "scene.reason.effort",
};

const ATTRS = /^(type|title|value|data-[a-z-]+|aria-[a-z-]+)$/;
const STEP_MS = 700;
const REAL_TIME_MIN_MS = 120;
const REAL_TIME_MAX_MS = 1500;
const TABS = ["events", "summary", "legend", "help"];

const state = createState();

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

// ---------------------------------------------------------------- language

function t(key, params) {
  return translate(state.lang, key, params);
}

// The count form of a message: `key.one` for exactly one, `key.other` otherwise; the count is available as {n}.
function tn(key, count, params) {
  return translate(state.lang, key + (count === 1 ? ".one" : ".other"), { n: count, ...params });
}

function browserLanguages() {
  try {
    if (typeof navigator === "undefined") return [];
    if (Array.isArray(navigator.languages) && navigator.languages.length) return [...navigator.languages];
    return navigator.language ? [navigator.language] : [];
  } catch (error) {
    return [];
  }
}

function detectLanguage() {
  return chooseLanguage({
    choice: state.langChoice, languages: browserLanguages(), hint: state.languageHint,
  });
}

// Static text carries its English default in the page and a key; this swaps in the chosen language.
function applyStaticText() {
  if (document.documentElement) document.documentElement.lang = state.lang;
  document.title = t("page.documentTitle");
  if (typeof document.querySelectorAll !== "function") return;
  for (const node of document.querySelectorAll("[data-i18n]")) node.textContent = t(node.dataset.i18n);
  for (const node of document.querySelectorAll("[data-i18n-title]")) node.title = t(node.dataset.i18nTitle);
  for (const node of document.querySelectorAll("[data-i18n-label]")) node.setAttribute("aria-label", t(node.dataset.i18nLabel));
}

let languageApplied = false;

function applyLanguage() {
  const next = detectLanguage();
  const changed = next !== state.lang;
  state.lang = next;
  if (changed || !languageApplied) {
    languageApplied = true;
    applyStaticText();
    for (const id of ["source-list", "agent-list", "status-list"]) $(id).dataset.keys = ""; // rebuilt in the new language
    const select = $("lang-select");
    if (select) select.value = state.langChoice;
    if (noticeKey) setNotice(noticeKey.key, noticeKey.params);
    if (state.model) renderAll();
    else renderChrome();
    if (scene) { labelCanvas(); syncScene(true); }
    else if (sceneFailure) $("scene-note").textContent = t("scene.unavailable", { reason: t(sceneFailure) });
  }
}

function setLanguageChoice(choice) {
  state.langChoice = choice === "es" || choice === "en" ? choice : "auto";
  writePreference("lang", state.langChoice === "auto" ? null : state.langChoice);
  applyLanguage();
}

// ---------------------------------------------------------------- labels

function classLabel(value) {
  if (value === null || value === undefined) return t("class.none");
  const name = CLASS_NAMES[value];
  return name === undefined ? t("class.unrecognized", { value: String(value) }) : t("class.named", { value, name });
}

function shapeOf(element) {
  if (element.element === "crossing") {
    const [glyph, key] = CROSSING_SHAPES[element.drawAs] || ["?", "shape.crossing"];
    const label = t(key);
    return [glyph, element.incompleteCoverage && element.isSwap ? t("shape.partialSuffix", { label }) : label];
  }
  if (element.element === "gate-ring") {
    const [glyph, key] = RING_SHAPES[element.ringKind] || ["◯", "shape.gate"];
    return [glyph, t(key)];
  }
  const entry = ELEMENT_SHAPES[element.element];
  return entry ? [entry[0], t(entry[1])] : ["·", String(element.element)];
}

function markNode(key) {
  return h("span", { class: "mark " + key, title: t("mark." + key + ".meaning") }, t("mark." + key));
}

function verificationNode(value) {
  if (!VERIFICATION[value]) return h("span", { class: "mark uncertain" }, t("verification.unrecognized", { value: String(value) }));
  return h("span", { class: "mark " + (value === "unverified" ? "unverified" : ""), title: t("verification." + value + ".meaning") },
    VERIFICATION[value] + " " + t("verification." + value));
}

function timeText(element) {
  if (!element.timeKnown) return t("time.sequenceOnly");
  return formatClock(element.relMs - axisMin());
}

function axisMin() {
  return state.model && state.model.axis && typeof state.model.axis.minMs === "number" ? state.model.axis.minMs : 0;
}

function textOf(value) {
  return String(value === null || value === undefined ? "" : value);
}

// ---------------------------------------------------------------- event sources

function sourceText(key) {
  if (!key.startsWith(ROOT_PREFIX)) return [t("source." + key), t("source." + key + ".meaning")];
  const label = key.slice(ROOT_PREFIX.length);
  return [label, t("source.root.meaning", { label })];
}

function isSourceShown(element) {
  return !state.hiddenSources.has(sourceOf(element));
}

function hiddenText(hidden, total) {
  return hidden === 0 ? t("sources.allShown") : t("sources.someHidden", { hidden, total });
}

// ---------------------------------------------------------------- data

let rowsCache = null;
let elementsCache = null;
let derivedCache = null;

// The model's elements by seq, built once per model.
function elementOf(seq) {
  if (!state.model) return undefined;
  if (!elementsCache || elementsCache.model !== state.model) {
    elementsCache = { model: state.model, bySeq: new Map(state.model.elements.map((element) => [element.seq, element])) };
  }
  return elementsCache.bySeq.get(seq);
}

// The derived model (agents, crossings, axis, overlaps) of the current model, computed once per model.
function derived() {
  if (!derivedCache || derivedCache.model !== state.model) derivedCache = { model: state.model, value: derive(state.model) };
  return derivedCache.value;
}

let countsCache = null;

// Events per source of the current model, counted once per model.
function sourceCounts() {
  if (!state.model) return {};
  if (!countsCache || countsCache.model !== state.model) {
    const counts = {};
    for (const element of state.model.elements) counts[sourceOf(element)] = (counts[sourceOf(element)] || 0) + 1;
    countsCache = { model: state.model, counts };
  }
  return countsCache.counts;
}

function hiddenCount() {
  const counts = sourceCounts();
  let total = 0;
  for (const key of state.hiddenSources) total += counts[key] || 0;
  return total;
}

function rowsInOrder() {
  if (!state.model) return [];
  if (rowsCache && rowsCache.model === state.model) return rowsCache.rows;
  const rows = orderedRows(state.model);
  rowsCache = { model: state.model, rows };
  return rows;
}

// Events that the agent, status and problems filters leave out, over every retained event.
function filteredOutCount() {
  if (!state.model) return 0;
  const info = derived();
  return state.model.elements.filter((element) => !passesFilters(element, info, state.filters)).length;
}

function shownInViews(element) {
  return isSourceShown(element) && passesFilters(element, derived(), state.filters);
}

let noticeKey = null;

function setNotice(key, params) {
  noticeKey = key ? { key, params } : null;
  const box = $("notice");
  box.textContent = key ? t(key, params) : "";
  box.hidden = !key;
}

let snapshotRequest = 0;

async function loadSnapshot() {
  const request = ++snapshotRequest;
  let response;
  try {
    response = await fetch("/snapshot", { cache: "no-store", credentials: "same-origin" });
  } catch (error) {
    setNotice("notice.unreachable");
    return;
  }
  if (response.status === 404) {
    setNotice("notice.notOpen");
    return;
  }
  if (!response.ok) {
    setNotice("notice.snapshotFailed", { status: response.status });
    return;
  }
  let document_;
  try {
    document_ = await response.json();
    if (!document_ || typeof document_.model !== "object" || document_.model === null) throw new Error("no model");
  } catch (error) {
    setNotice("notice.invalidJson");
    return;
  }
  if (request !== snapshotRequest) return; // a newer request supersedes this response
  setNotice(null);
  const firstModel = state.model === null;
  const atEnd = state.cursor >= totalCount();
  state.model = document_.model;
  state.languageHint = normalizeTag(document_.uiLanguageHint);
  state.dropped = Array.isArray(document_.droppedAttributeNames) ? document_.droppedAttributeNames : [];
  state.cursor = atEnd ? totalCount() : Math.min(state.cursor, totalCount());
  if (firstModel) restoreFromHash();
  if (state.selected !== null && !state.model.elements.some((element) => element.seq === state.selected)) {
    state.selected = null;
  }
  try {
    applyLanguage(); // the hint may change the language
    renderAll();
  } catch (error) {
    console.error(error);
    setNotice("notice.renderFailed");
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

let connectionKey = "connecting";

function setConnection(key) {
  connectionKey = key;
  $("connection").textContent = t("connection." + key);
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
        setConnection("notOpen");
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
        buffer = (buffer + decoder.decode(value, { stream: true })).replace(/\r\n/g, "\n"); // a CR at the end of a chunk waits for its LF
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

// ---------------------------------------------------------------- header and chrome

function renderSummary() {
  const box = $("summary");
  if (!state.model || totalCount() === 0) {
    box.textContent = t("summary.empty");
    return;
  }
  const s = summarize(state.model, derived());
  const parts = [tn("summary.agents", s.agents)];
  if (s.durationMs > 0) parts.push(formatDuration(s.durationMs));
  if (s.peak > 1) parts.push(tn("summary.peak", s.peak));
  if (s.predictedConflicts > 0) parts.push(tn("summary.conflicts", s.predictedConflicts));
  if (s.gaps > 0) parts.push(tn("summary.gaps", s.gaps));
  box.textContent = parts.join(" · ");
}

// Static parts that depend on the language or the number of views and not on the model.
function renderAuthorization() {
  const value = state.model ? state.model.executionAuthorization : false;
  const badge = $("authorization");
  badge.textContent = "executionAuthorization: " + String(value);
  badge.className = value === false ? "badge" : "badge mark unverified";
}

function renderChrome() {
  renderAuthorization();
  setConnection(connectionKey);
  renderViewSwitch();
  renderTabs();
  renderSummary();
}

// ---------------------------------------------------------------- legend (static tables above)

function renderLegend() {
  fill("legend-classes", CLASS_NAMES.map((name, index) => h("li", null, t("class.named", { value: index, name }))),
    h("li", null, t("class.legendNone")));
  fill("legend-shapes",
    Object.values(CROSSING_SHAPES).map(([glyph, key]) => h("li", null, h("span", { class: "glyph" }, glyph), t(key))),
    Object.values(ELEMENT_SHAPES).map(([glyph, key]) => h("li", null, h("span", { class: "glyph" }, glyph), t(key))),
    Object.values(RING_SHAPES).map(([glyph, key]) => h("li", null, h("span", { class: "glyph" }, glyph), t(key))));
  fill("legend-verification", Object.keys(VERIFICATION).map((key) =>
    h("li", null, h("span", { class: "glyph" }, VERIFICATION[key]), t("verification." + key) + ": " + t("verification." + key + ".meaning"))));
  fill("legend-marks", MARK_KEYS.map((key) => h("li", null, markNode(key), " " + t("mark." + key + ".meaning"))));
  fill("legend-scene", SCENE_LEGEND_KEYS.map((key) => h("li", null, t("sceneLegend." + key))));
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
  $("counters-scope").textContent = t("counters.scope", { count: model.eventCount });
  const out = [];
  kv(out, t("counters.conflicts"), c.conflictsFlagged);
  kv(out, t("counters.ordered"), c.orderedPairs);
  kv(out, t("counters.independent"), c.independentCandidates);
  kv(out, t("counters.unknown"), c.unknownPairs);
  kv(out, t("counters.swaps"), c.swaps);
  kv(out, t("counters.bridges"), c.bridges);
  kv(out, t("counters.waveWidth"), c.plannedWaveWidth.maxWidth === null ? t("counters.nonePlanned") : c.plannedWaveWidth.maxWidth);
  out.push(h("dd", { class: "full" }, t("counters.waveLabel") + " (" + tn("counters.plans", c.plannedWaveWidth.plans) + ")"));
  kv(out, t("counters.hazards"), c.hazards.total);
  for (const [name, count] of Object.entries(c.hazards.byKind)) kv(out, name, count, true);
  kv(out, t("counters.gaps"), c.gaps.total);
  for (const [name, count] of Object.entries(c.gaps.byReason)) if (count) kv(out, name, count, true);
  kv(out, t("counters.gatePhases"), c.gates.phases);
  kv(out, t("counters.gateResults"), c.gates.results);
  kv(out, t("counters.grants"), c.grants.total);
  for (const name of ["issued", "consumed", "expired", "refused"]) kv(out, name, c.grants[name], true);
  kv(out, t("counters.unverified"), c.unverifiedElements);
  fill("counters", out);

  const a = c.absence;
  const gone = [];
  kv(gone, t("absence.unknownPairs"), a.unknownPairs);
  kv(gone, t("absence.partial"), a.independentWithIncompleteCoverage);
  kv(gone, t("absence.hazards"), a.hazardsNotObserved);
  kv(gone, t("absence.gaps"), a.gaps);
  kv(gone, t("absence.truncated"), a.truncated);
  for (const cut of model.truncated) kv(gone, t("absence.cap", { what: cut.what, limit: cut.limit }), t("absence.dropped", { count: cut.dropped }), true);
  fill("absence", gone);
}

function laneKind(lane) {
  if (lane.parentLane !== null) return t("agent.kind.subagent");
  if (lane.orphan) return t("agent.kind.orphan");
  return lane.role === "agent" ? t("agent.kind.main") : t("agent.kind.unit");
}

const OUTCOMES = new Set(["ok", "error", "unknown", "cancelled"]);

function outcomeText(outcome) {
  return OUTCOMES.has(outcome) ? t("outcome." + outcome) : textOf(outcome);
}

function stateText(lane) {
  const base = t("state." + lane.state);
  return lane.inferred ? base + " " + t("state.inferred") : base;
}

function renderLanes() {
  const info = derived();
  fill("lanes", info.rows.map(({ laneIndex }) => {
    const lane = info.byIndex.get(laneIndex);
    return h("li", { class: lane.depth ? "child" : "" },
      lane.displayLabel + " ",
      h("span", { class: "hint" }, "(" + (lane.declared ? lane.host + " " + lane.role : t("lanes.undeclared")) + ", " + stateText(lane) + ") "),
      lane.unverified ? markNode("unverified") : null);
  }));
}

function renderDropped() {
  fill("dropped-list", state.dropped.length ? state.dropped.map((name) => h("li", null, name)) : [h("li", null, t("dropped.none"))]);
}

// ---------------------------------------------------------------- filters (sources, agents, status, problems)

const sourceNodes = new Map();
const agentNodes = new Map();
const statusNodes = new Map();

function renderSources() {
  const counts = sourceCounts();
  const keys = sourceKeys(counts);
  // A source that no longer has events has no checkbox, so it cannot stay hidden with no way to show it again.
  for (const key of [...state.hiddenSources]) if (!counts[key]) state.hiddenSources.delete(key);
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
      const [name, title] = sourceText(key);
      return h("label", { class: "source", title }, input, " ", name, " ", count);
    }));
  }
  for (const key of keys) {
    const node = sourceNodes.get(key);
    node.input.checked = !state.hiddenSources.has(key);
    node.count.textContent = "(" + tn("sources.events", counts[key]) + ")";
  }
  $("source-status").textContent = hiddenText(hiddenCount(), totalCount());
}

function checkboxList(listId, nodes, entries, onToggle) {
  const signature = entries.map((entry) => entry.key).join("|");
  const list = $(listId);
  if (list.dataset.keys !== signature) {
    list.dataset.keys = signature;
    nodes.clear();
    fill(listId, entries.map((entry) => {
      const input = h("input", { type: "checkbox", "data-filter": entry.key,
        on: { change: (event) => onToggle(entry.key, event.target.checked) } });
      const count = h("span", { class: "source-count" });
      nodes.set(entry.key, { input, count });
      return h("label", { class: "source", title: entry.title || null }, input, " ", entry.label, " ", count);
    }));
  }
  for (const entry of entries) {
    const node = nodes.get(entry.key);
    node.input.checked = entry.checked;
    node.count.textContent = "(" + entry.count + ")";
  }
}

function renderAgentFilters() {
  const info = derived();
  const entries = info.rows.map(({ laneIndex }) => {
    const lane = info.byIndex.get(laneIndex);
    return { key: lane.strandId, label: lane.displayLabel, count: lane.seqs.length, checked: state.filters.agents.has(lane.strandId), title: laneKind(lane) };
  });
  for (const id of [...state.filters.agents]) if (!info.byStrand.has(id)) state.filters.agents.delete(id);
  $("agent-menu").hidden = entries.length === 0;
  checkboxList("agent-list", agentNodes, entries, (key, on) => {
    if (on) state.filters.agents.add(key);
    else state.filters.agents.delete(key);
    filtersChanged();
  });
  $("agent-hint").textContent = state.filters.agents.size ? t("filters.agents.some", { n: state.filters.agents.size }) : t("filters.agents.all");
}

function renderStatusFilters() {
  const info = derived();
  const entries = LANE_STATES.map((name) => ({
    key: name, label: t("state." + name), count: info.lanes.filter((lane) => lane.state === name).length,
    checked: state.filters.status.has(name),
  }));
  $("status-menu").hidden = info.lanes.length === 0;
  checkboxList("status-list", statusNodes, entries, (key, on) => {
    if (on) state.filters.status.add(key);
    else state.filters.status.delete(key);
    filtersChanged();
  });
  $("status-hint").textContent = t("filters.status.note");
}

function renderFilterStatus() {
  const out = $("filter-status");
  const hidden = hiddenCount();
  const left = state.model ? filteredOutCount() : 0;
  const parts = [];
  if (hidden) parts.push(tn("filters.hiddenSources", hidden));
  if (left) parts.push(tn("filters.leftOut", left));
  out.textContent = parts.join(" · ");
  out.hidden = parts.length === 0;
  $("filter-clear").disabled = !hasFilters(state);
  $("filter-problems").checked = state.filters.onlyProblems;
}

function toggleSource(key, shown) {
  if (shown) state.hiddenSources.delete(key);
  else state.hiddenSources.add(key);
  const selected = state.selected === null ? undefined : elementOf(state.selected);
  if (selected && !isSourceShown(selected)) state.selected = null;
  filtersChanged();
}

function filtersChanged() {
  const selected = state.selected === null ? undefined : elementOf(state.selected);
  if (selected && !shownInViews(selected)) state.selected = null;
  renderSources();
  renderAgentFilters();
  renderStatusFilters();
  renderFilterStatus();
  renderPlayback();
  renderTable();
  renderEvidence();
  syncHash();
}

function clearFilters() {
  state.hiddenSources.clear();
  state.filters.agents.clear();
  state.filters.status.clear();
  state.filters.kinds.clear();
  state.filters.onlyProblems = false;
  filtersChanged();
}

// ---------------------------------------------------------------- table

function visibleRows() {
  return rowsInOrder().slice(0, state.cursor).filter(({ element }) => {
    if (!shownInViews(element)) return false;
    if (state.filterKind && element.element !== state.filterKind) return false;
    return true;
  });
}

function renderKindFilter() {
  const select = $("filter-kind");
  const kinds = [...new Set((state.model ? state.model.elements : []).map((element) => element.element))].sort();
  if (state.filterKind && !kinds.includes(state.filterKind)) state.filterKind = "";
  const key = kinds.join("|") + "|" + state.lang;
  if (select.dataset.kinds === key) return;
  select.dataset.kinds = key;
  select.replaceChildren(h("option", { value: "" }, t("table.kindAll")),
    ...kinds.map((kind) => h("option", { value: kind }, kind)));
  select.value = state.filterKind;
}

function renderTable() {
  const rows = visibleRows();
  const last = state.cursor > 0 ? rowsInOrder()[state.cursor - 1] : null;
  const active = document.activeElement;
  const focusedSeq = active && active.dataset && active.dataset.seq !== undefined ? active.dataset.seq : null;
  const cell = (key, ...children) => h("td", { "data-label": t("table.col." + key) }, ...children);
  fill("events-body", rows.map(({ row, element }) => {
    const [glyph, label] = shapeOf(element);
    const selected = state.selected === row.seq;
    return h("tr", { class: (selected ? "selected " : "") + (last && last.row.seq === row.seq ? "current" : "") },
    cell("seq", h("button", {
      type: "button", class: "row-button", "aria-label": t("table.select", { seq: row.seq }),
      "aria-pressed": selected ? "true" : "false", "data-seq": row.seq,
      on: { click: () => select(row.seq) },
    }, (selected ? "▶ " : "") + row.seq)),
    cell("time", h("span", { title: element.timeKnown ? element.relMs + " ms" : null }, timeText(element))),
    cell("shape", h("span", { class: "glyph", "aria-hidden": "true" }, glyph), label),
    cell("subject", textOf(row.subject)),
    cell("status", row.status === null || row.status === undefined ? "—" : String(row.status)),
    cell("class", classLabel(row.compatibilityClass)),
    cell("verification", verificationNode(element.verification)),
    cell("marks", marksOf(element).map(markNode)));
  }));
  if (focusedSeq !== null) {
    const again = $("events-body").querySelector('[data-seq="' + CSS.escape(focusedSeq) + '"]');
    if (again) again.focus({ preventScroll: true });
  }
  $("table-empty").hidden = rows.length > 0;
  const hidden = hiddenCount();
  $("table-empty").textContent = (state.model && totalCount() > 0 && rows.length === 0
    ? t("table.emptyPosition") : t("table.empty")) + (hidden ? " " + hiddenText(hidden, totalCount()) : "");
  syncViews();
}

function select(seq) {
  state.selected = seq;
  renderTable();
  renderEvidence();
  syncHash();
}

function deselect() {
  if (state.selected !== null) select(null);
}

// ---------------------------------------------------------------- detail panel

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

function noneRecorded() {
  return t("detail.noneRecorded");
}

function detailPairs(element) {
  switch (element.element) {
    case "crossing": {
      const evidence = element.evidence || {};
      const coverage = Array.isArray(evidence.coverage) ? evidence.coverage : [];
      const report = element.report;
      return [
        [t("detail.classification"), element.classification],
        [t("detail.drawnAs"), shapeOf(element)[1]],
        [t("detail.leftAgent"), element.left],
        [t("detail.rightAgent"), element.right],
        [t("detail.sharedResources"), listOrNone(element.sharedResources, noneRecorded())],
        [t("detail.evidenceMethod"), String(evidence.method)],
        [t("detail.ruleSet"), String(evidence.ruleSet)],
        [t("detail.coverage"), coverage.join(", ") + (element.incompleteCoverage ? " " + t("detail.coverage.incomplete") : "")],
        [t("detail.reasons"), listOrNone(element.reasons, noneRecorded())],
        [t("detail.constraints"), listOrNone(element.constraints, noneRecorded())],
        [t("detail.passedOver"), element.passesOverLanes.length ? element.passesOverLanes.join(", ") : t("detail.none")],
        [t("detail.reportUncertainty"), report ? listOrNone(report.uncertainty, noneRecorded()) : t("detail.noReport")],
        [t("detail.reportLimits"), report ? listOrNone(report.limits, noneRecorded()) : t("detail.noReport")],
      ];
    }
    case "hazard-cone":
      return [[t("detail.hazard"), element.hazardKind], [t("detail.stage"), element.stage], [t("detail.units"), listOrNone(element.units, t("detail.none"))],
        [t("detail.notObserved"), element.absence ? t("detail.notObserved.yes") : t("detail.no")]];
    case "gap":
      return [[t("detail.reason"), element.reason], [t("detail.agent"), element.strandId === null ? t("detail.none") : element.strandId],
        [t("detail.fromSeq"), element.fromSeq === null ? t("detail.unknown") : element.fromSeq],
        [t("detail.toSeq"), element.toSeq === null ? t("detail.unknown") : element.toSeq]];
    case "wave-plane":
      return [[t("detail.plan"), element.planId], [t("detail.mode"), element.mode], [t("detail.label"), element.label],
        [t("detail.waves"), listOrNone(element.waves.map((wave) => t("detail.waveLine", { width: wave.width, agents: wave.strands.join(", ") })), t("detail.none"))]];
    case "wave-marker":
      return [[t("detail.schedule"), element.scheduleId], [t("detail.wave"), element.wave], [t("detail.phase"), element.phase],
        [t("detail.agents"), listOrNone(element.strands, t("detail.none"))]];
    case "gate-ring":
      return element.ringKind === "grant"
        ? [[t("detail.grant"), element.grantId], [t("detail.action"), element.action], [t("detail.state"), element.state],
          [t("detail.derived"), element.derived ? t("detail.yes") : t("detail.no")]]
        : [[t("detail.gate"), element.gateId], [t("detail.gateStatus"), element.gateStatus],
          element.ringKind === "workflow-phase" ? [t("detail.phase"), element.phase] : [t("detail.operationCount"), element.operationCount]];
    case "effort":
      return [[t("detail.effortBasis"), element.effortBasis], [t("detail.knownTokens"), element.knownTokens === null ? t("detail.unknown") : element.knownTokens]];
    default:
      return [];
  }
}

// What the event says about its agent: state, start and end, duration, waiting time and the time it overlapped
// with other agents (F1, F2). Only what the events state; an end that was not observed is said so.
function agentSection(element) {
  const info = derived();
  const lane = element.strandId !== undefined && element.strandId !== null ? info.byStrand.get(element.strandId) : null;
  if (!lane) return null;
  const waiting = waitingTime(lane);
  const overlaps = info.overlaps.filter((item) => item.lanes.includes(lane.laneIndex));
  const rows = [
    [t("agent.name"), lane.displayLabel],
    [t("agent.kind"), laneKind(lane)],
    [t("agent.state"), stateText(lane)],
    [t("agent.start"), lane.openKnown ? formatClock(lane.openMs - axisMin()) : t("time.sequenceOnly")],
    [t("agent.end"), lane.closeSeq !== null ? formatClock(lane.closeMs - axisMin()) + " · " + outcomeText(lane.outcome) : t("agent.endNotObserved")],
    [t("agent.duration"), lane.durationMs !== null ? formatDuration(lane.durationMs)
      : lane.observedMs !== null ? t("agent.durationAtLeast", { text: formatDuration(lane.observedMs) }) : t("detail.unknown")],
  ];
  if (lane.toolMarks.length) rows.push([t("agent.tools"), String(lane.toolMarks.length)]);
  if (waiting.totalMs > 0 || waiting.open) {
    rows.push([t("agent.waiting"), formatDuration(waiting.totalMs) + (waiting.open ? " " + t("agent.waitingOpen") : "")]);
  }
  if (overlaps.length) {
    rows.push([t("agent.overlaps"), h("ul", null, overlaps.slice(0, 5).map((item) => {
      const other = info.byIndex.get(item.lanes[0] === lane.laneIndex ? item.lanes[1] : item.lanes[0]);
      return h("li", null, other.displayLabel + ": " + formatDuration(item.ms));
    }))]);
  }
  return section(t("detail.agentSection"), definitions(rows), h("p", { class: "hint" }, t("agent.note")));
}

// For a crossing: whether the two agents were open at the same time. Descriptive; it does not say the analysis was right.
function overlapRow(element) {
  if (element.element !== "crossing") return null;
  const info = derived();
  const crossing = info.crossings.find((item) => item.seq === element.seq);
  if (!crossing) return null;
  const overlap = crossing.overlap;
  const text = overlap === null ? t("crossing.overlap.unknown")
    : overlap.ms > 0 ? t("crossing.overlap.yes", { text: formatDuration(overlap.ms) }) + (overlap.inferred ? " " + t("state.inferred") : "")
      : t("crossing.overlap.no");
  return section(t("crossing.overlapTitle"), h("p", null, text), h("p", { class: "hint" }, t("crossing.overlapNote")));
}

function renderEvidence() {
  const element = state.selected === null ? undefined : elementOf(state.selected);
  $("detail-close").hidden = !element;
  $("detail").classList.toggle("open", Boolean(element));
  if (!element) {
    fill("evidence", h("p", { class: "hint" }, t("evidence.empty")));
    return;
  }
  const ref = element.evidenceRef;
  const marks = marksOf(element);
  fill("evidence",
    h("p", null, h("strong", null, t("evidence.title", { seq: element.seq, kind: element.kind })), " ", marks.map(markNode)),
    agentSection(element),
    overlapRow(element),
    section(t("detail.eventSection"), definitions([
      [t("detail.element"), element.element],
      [t("detail.subject"), textOf(element.subject)],
      [t("detail.status"), element.status === null || element.status === undefined ? "—" : String(element.status)],
      [t("detail.host"), element.host],
      [t("detail.time"), timeText(element) + " (" + (element.timeKnown ? element.relMs + " ms, " : "") + element.basis + ")"],
    ])),
    section(t("detail.classSection"), h("p", null, classLabel(element.compatibilityClass)),
      h("p", { class: "hint" }, t("detail.classNote"))),
    section(t("detail.verificationSection"), h("p", null, verificationNode(element.verification)),
      h("p", { class: "hint" }, VERIFICATION[element.verification] ? t("verification." + element.verification + ".meaning") : "")),
    section(t("detail.evidenceSection"), ref
      ? definitions([[t("detail.path"), ref.path], ["sha256", ref.sha256]])
      : h("p", null, t("detail.noArtifact"))),
    detailPairs(element).length ? section(t("detail.detailsSection"), definitions(detailPairs(element))) : null,
    h("details", null, h("summary", null, t("detail.allFields")), h("pre", null, JSON.stringify(element, null, 2))));
}

// ---------------------------------------------------------------- playback

function renderPlayback() {
  const total = totalCount();
  const range = $("pb-range");
  range.max = String(total);
  range.value = String(state.cursor);
  // Stepping moves over every retained event; with a source unchecked, say how many of those up to here are drawn.
  const shown = state.hiddenSources.size
    ? " " + t("playback.shown", { n: rowsInOrder().slice(0, state.cursor).filter(({ element }) => isSourceShown(element)).length }) : "";
  $("pb-count").textContent = t("playback.count", { cursor: state.cursor, total }) + shown;
  range.setAttribute("aria-valuetext", t("playback.valueText", { cursor: state.cursor, total }) + shown);
  $("pb-back").disabled = state.cursor <= 0;
  $("pb-start").disabled = state.cursor <= 0;
  $("pb-forward").disabled = state.cursor >= total;
  $("pb-play").setAttribute("data-playing", state.playing ? "true" : "false");
  $("pb-play").textContent = t(state.playing ? "playback.pause" : "playback.play");
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

// "By events" steps at a fixed pace. "Real time" waits as long as the compressed axis between two events,
// within bounds, so a long omitted gap never stalls playback.
function stepDelay() {
  const speed = Number($("pb-speed").value) || 1;
  if ($("pb-mode").value !== "real") return STEP_MS / speed;
  const rows = rowsInOrder();
  const here = rows[state.cursor - 1];
  const next = rows[state.cursor];
  if (!here || !next) return STEP_MS / speed;
  return Math.min(REAL_TIME_MAX_MS, Math.max(REAL_TIME_MIN_MS, (next.element.x - here.element.x) / speed));
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
  state.timer = setTimeout(tick, stepDelay());
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

// ---------------------------------------------------------------- tabs and help

let currentTab = "events";

function renderTabs() {
  for (const name of TABS) {
    const tab = $("tab-" + name);
    const on = name === currentTab;
    tab.setAttribute("aria-selected", on ? "true" : "false");
    tab.tabIndex = on ? 0 : -1;
    $("panel-" + name).hidden = !on;
  }
}

function showTab(name, focus) {
  if (!TABS.includes(name)) return;
  currentTab = name;
  renderTabs();
  if (focus) $("tab-" + name).focus();
}

function onTabKey(event) {
  const at = TABS.indexOf(currentTab);
  let next = at;
  if (event.key === "ArrowRight") next = (at + 1) % TABS.length;
  else if (event.key === "ArrowLeft") next = (at + TABS.length - 1) % TABS.length;
  else if (event.key === "Home") next = 0;
  else if (event.key === "End") next = TABS.length - 1;
  else return;
  event.preventDefault();
  showTab(TABS[next], true);
}

function openHelp() {
  showTab("help", false);
  const heading = $("help-title");
  if (heading.scrollIntoView) heading.scrollIntoView({ block: "start" });
  heading.focus();
}

function openSceneHelp() {
  const dialog = $("scene-help");
  if (dialog.open) return;
  if (typeof dialog.showModal === "function") dialog.showModal();
  else dialog.setAttribute("open", "");
}

function isTyping(event) {
  const target = event.target;
  const tag = target && target.tagName ? String(target.tagName).toLowerCase() : "";
  return tag === "input" || tag === "select" || tag === "textarea" || Boolean(target && target.isContentEditable);
}

function onKey(event) {
  if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey) return;
  if (event.target && event.target.closest && event.target.closest("dialog")) return; // the dialog handles its own keys
  if (event.key === "Escape") {
    if (!isTyping(event)) deselect();
  } else if (event.key === "?" && !isTyping(event)) {
    event.preventDefault();
    if (state.view === "map3d") openSceneHelp();
    else openHelp();
  }
}

function bindControls() {
  $("pb-start").addEventListener("click", () => { stopPlayback(); setCursor(0); });
  $("pb-back").addEventListener("click", () => { stopPlayback(); setCursor(state.cursor - 1); });
  $("pb-forward").addEventListener("click", () => { stopPlayback(); setCursor(state.cursor + 1); });
  $("pb-end").addEventListener("click", () => { stopPlayback(); setCursor(totalCount()); });
  $("pb-play").addEventListener("click", togglePlay);
  $("pb-range").addEventListener("input", (event) => { stopPlayback(); setCursor(Number(event.target.value)); });
  $("filter-kind").addEventListener("change", (event) => { state.filterKind = event.target.value; renderTable(); });
  $("filter-problems").addEventListener("change", (event) => { state.filters.onlyProblems = event.target.checked; filtersChanged(); });
  $("filter-clear").addEventListener("click", clearFilters);
  $("scene-reset").addEventListener("click", () => { if (scene) scene.resetView(); });
  $("scene-frame").addEventListener("click", () => { if (scene) scene.resetView(); });
  for (const id of ["scene-view-lateral", "scene-view-top", "scene-view-iso"]) {
    $(id).addEventListener("click", (event) => { if (scene) scene.setPreset(event.currentTarget.dataset.preset); });
  }
  $("scene-lock").addEventListener("click", () => {
    const on = $("scene-lock").getAttribute("aria-pressed") !== "true";
    $("scene-lock").setAttribute("aria-pressed", on ? "true" : "false");
    if (scene) scene.setLocked(on);
  });
  $("scene-help-open").addEventListener("click", openSceneHelp);
  $("tl-zoom-in").addEventListener("click", () => { if (timeline) timeline.zoomIn(); });
  $("tl-zoom-out").addEventListener("click", () => { if (timeline) timeline.zoomOut(); });
  $("tl-frame").addEventListener("click", () => { if (timeline) timeline.frame(); });
  $("view-timeline").addEventListener("change", () => setView("timeline", true));
  $("view-map3d").addEventListener("change", () => setView("map3d", true));
  $("lang-select").addEventListener("change", (event) => setLanguageChoice(event.target.value));
  $("detail-close").addEventListener("click", deselect);
  $("about-open").addEventListener("click", openHelp);
  $("tablist").addEventListener("keydown", onTabKey);
  for (const name of TABS) $("tab-" + name).addEventListener("click", () => showTab(name, false));
  document.addEventListener("keydown", onKey);
}

// ---------------------------------------------------------------- views and the URL hash

// The views this build offers. The first is the default; a deep link or a stored choice may pick another.
const views = [{ id: "timeline" }, { id: "map3d" }];

function availableView(id) {
  return views.some((view) => view.id === id) ? id : views[0].id;
}

function renderViewSwitch() {
  $("view-switch").hidden = views.length < 2;
  $("view-timeline").checked = state.view === "timeline";
  $("view-map3d").checked = state.view === "map3d";
  $("timeline-section").hidden = state.view !== "timeline";
  $("scene-section").hidden = state.view !== "map3d";
}

function setView(id, byUser) {
  const next = availableView(id);
  if (next === state.view && viewApplied) return;
  state.view = next;
  viewApplied = true;
  if (byUser) writePreference("view", next); // a default is never stored as if it were a choice
  renderViewSwitch();
  if (next === "map3d" && !sceneRequested) startScene();
  else if (next === "map3d" && scene && scene.refreshLabels) scene.refreshLabels(); // sizes cannot be measured while hidden
  syncViews();
  syncHash();
}

let viewApplied = false;

// ---------------------------------------------------------------- 2D timeline

let timeline = null;

function laneInfo(lane) {
  const range = lane.openKnown
    ? formatClock(lane.openMs - axisMin()) + " – " + (lane.closeKnown && lane.closeMs !== null ? formatClock(lane.closeMs - axisMin()) : t("agent.endNotObserved"))
    : t("time.sequenceOnly");
  const duration = lane.durationMs !== null ? formatDuration(lane.durationMs)
    : lane.state !== "unknown" && lane.observedMs !== null ? "≥ " + formatDuration(lane.observedMs) : "–";
  const outcome = lane.closeSeq !== null ? ", " + outcomeText(lane.outcome) : "";
  const waiting = waitingTime(lane);
  const parts = [lane.displayLabel, laneKind(lane), stateText(lane) + outcome, range, duration];
  if (lane.toolMarks.length) parts.push(tn("tl.tools", lane.toolMarks.length));
  if (waiting.totalMs > 0) parts.push(t("tl.waited", { text: formatDuration(waiting.totalMs) }));
  const mark = lane.state === "finished" ? { ok: "✓", error: "✕", cancelled: "⊘" }[lane.outcome] || "?" : lane.state === "running" ? "▶" : lane.state === "waiting" ? "⏸" : "?";
  return { aria: parts.join(", "), tip: parts.join(" · "), mark, duration };
}

function crossingTip(crossing) {
  const names = crossing.lanes.map((index) => { const lane = derived().byIndex.get(index); return lane ? lane.displayLabel : String(index); }).join(" / ");
  const resources = crossing.resources.length ? crossing.resources.join(", ") : t("detail.none");
  let text;
  if (crossing.kind === "predicted") text = t("tl.tip.conflict", { names, resources });
  else if (crossing.classification === "independent-candidate") text = t("tl.tip.independent", { names });
  else if (crossing.classification === "ordered") text = t("tl.tip.ordered", { names });
  else text = t("tl.tip.unknown", { names });
  const overlap = crossing.overlap;
  if (overlap === null) return text;
  return text + " " + (overlap.ms > 0 ? t("tl.tip.overlapYes", { text: formatDuration(overlap.ms) }) : t("tl.tip.overlapNo"));
}

function syncTimeline() {
  if (state.view !== "timeline" || !state.model) return;
  if (!timeline) {
    timeline = createTimeline($("timeline-box"), {
      t, onSelect: select, describe: laneInfo, crossingTip,
      onViewport: (viewport) => { state.viewport = viewport; syncViews(); syncHash(); },
    });
  }
  const position = rowsInOrder().slice(0, state.cursor);
  const shown = new Set(position.filter(({ element }) => shownInViews(element)).map(({ row }) => row.seq));
  const last = position.length ? position[position.length - 1].element : null;
  timeline.render({
    model: state.model, derived: derived(), shown, selected: state.selected, viewport: state.viewport,
    cursorX: last && last.timeKnown !== false ? last.x : null,
  });
  const info = derived();
  $("timeline-note").textContent = t("tl.note", { shown: shown.size, total: totalCount() }) +
    (info.axis.breaks.length ? " " + tn("tl.breaks", info.axis.breaks.length) : "");
}

function syncViews() {
  if (state.view === "timeline") syncTimeline();
  else syncScene();
  renderLegendLine();
}

// ---------------------------------------------------------------- legend line (a filter shared by every view)

function kindCounts() {
  const counts = Object.fromEntries(MARKER_KINDS.map((kind) => [kind, 0]));
  if (state.model) for (const element of state.model.elements) { const kind = markerKind(element); if (kind) counts[kind] += 1; }
  return counts;
}

const KIND_GLYPH = {
  conflict: "g-conflict-predicted", independent: "g-independent", ordered: "g-ordered", unknown: "g-unknown",
  hazard: "g-hazard-observed", gap: "g-gap", gate: "g-gate", grant: "g-grant",
};

function renderLegendLine() {
  const counts = kindCounts();
  const list = $("legend-line");
  const present = MARKER_KINDS.filter((kind) => counts[kind] > 0);
  const signature = present.map((kind) => kind + counts[kind]).join("|") + "|" + state.lang;
  list.hidden = present.length === 0;
  if (list.dataset.keys !== signature) {
    list.dataset.keys = signature;
    list.replaceChildren(...present.map((kind) => {
      const button = h("button", { type: "button", class: "legend-chip", "data-kind": kind, title: t("legend.line." + kind + ".title"),
        on: { click: () => toggleKind(kind) } }, iconNode(KIND_GLYPH[kind]), " ", t("legend.line." + kind), " ", h("span", { class: "source-count" }, String(counts[kind])));
      return button;
    }));
  }
  for (const node of list.children) node.setAttribute("aria-pressed", state.filters.kinds.has(node.dataset.kind) ? "true" : "false");
}

function toggleKind(kind) {
  if (state.filters.kinds.has(kind)) state.filters.kinds.delete(kind);
  else state.filters.kinds.add(kind);
  filtersChanged();
}

function syncHash() {
  if (typeof history === "undefined" || typeof location === "undefined" || typeof history.replaceState !== "function") return;
  try {
    const next = encodeHash(state);
    if (next !== location.hash) history.replaceState(null, "", location.pathname + location.search + next);
  } catch (error) {
    // the hash is a convenience; a browser that refuses it keeps the page working
  }
}

// The view is chosen before the first model arrives, so only the chosen view is ever built.
function restoreView() {
  const wanted = typeof location === "undefined" ? { view: null } : decodeHash(location.hash);
  state.view = availableView(wanted.view || readPreference("view") || state.view);
}

function restoreFromHash() {
  if (typeof location === "undefined") return;
  const wanted = decodeHash(location.hash);
  for (const key of wanted.hide) state.hiddenSources.add(key);
  for (const id of wanted.agents) state.filters.agents.add(id);
  for (const name of wanted.status) state.filters.status.add(name);
  for (const kind of wanted.kinds) state.filters.kinds.add(kind);
  state.filters.onlyProblems = wanted.onlyProblems;
  if (wanted.selected !== null && elementOf(wanted.selected)) state.selected = wanted.selected;
  if (wanted.viewport) state.viewport = wanted.viewport;
  const chosen = state.selected === null ? undefined : elementOf(state.selected);
  if (chosen && !shownInViews(chosen)) state.selected = null; // a restored filter may hide the restored selection
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
    ? t("scene.hover", { seq: element.seq, kind: element.kind, subject: textOf(element.subject), cls: classLabel(element.compatibilityClass) }) +
      (marksOf(element).includes("unverified") ? " · " + t("mark.unverified") : "")
    : t("scene.hoverHint");
}

function updateSceneNote() {
  const info = scene.summary();
  const parts = [t("scene.showing", { drawn: info.drawn, visible: info.visible })];
  const hidden = hiddenCount();
  if (hidden) parts.push(t("scene.hiddenSources", { n: hidden }));
  const left = filteredOutCount();
  if (left) parts.push(t("scene.leftOut", { n: left }));
  const untimed = info.seqs.filter((seq) => { const element = elementOf(seq); return element && element.timeKnown === false; }).length;
  if (untimed) parts.push(t("scene.untimed", { n: untimed }));
  if (info.omitted.length) {
    parts.push(t("scene.onlyInTable", {
      items: info.omitted.map((item) => item.count + " (" + (SCENE_REASON_KEYS[item.reason] ? t(SCENE_REASON_KEYS[item.reason]) : item.reason) + ")").join("; "),
    }));
  }
  $("scene-note").textContent = parts.join(" ");
}

// Keeps the scene on the model, playback position, filters and selection of the table. Cheap when nothing changed.
function syncScene(force) {
  if (!scene) return;
  try {
    applyScene(force);
  } catch (error) {
    console.error(error);
    sceneUnavailable("scene.reason.draw");
  }
}

function applyScene(force) {
  const modelChanged = sceneModel !== state.model;
  if (modelChanged) {
    sceneModel = state.model;
    scene.setModel(state.model);
  }
  const hidden = [...state.hiddenSources].sort().join("|") + "#" + [...state.filters.agents].sort().join("|") + "#" +
    [...state.filters.status].sort().join("|") + "#" + [...state.filters.kinds].sort().join("|") + "#" + state.filters.onlyProblems;
  if (modelChanged || force || sceneCursor !== state.cursor || sceneHidden !== hidden) {
    sceneCursor = state.cursor;
    sceneHidden = hidden;
    // The scene shows only what passes the filters; the playback frontier still follows the position, not the filter.
    const position = rowsInOrder().slice(0, state.cursor);
    scene.setVisible(
      position.filter(({ element }) => shownInViews(element)).map(({ row }) => row.seq),
      position.map(({ row }) => row.seq));
    updateSceneNote();
    showHover(null);
  }
  if (modelChanged || sceneSelected !== state.selected) {
    sceneSelected = state.selected;
    scene.setSelected(state.selected);
  }
}

// `reason` is a string key of the page or, from the scene itself, a sentence it wrote.
let sceneFailure = null;

function sceneUnavailable(reason) {
  sceneFailure = reason;
  if (scene) {
    try {
      scene.dispose();
    } catch (error) {
      console.error(error);
    }
    scene = null;
  }
  $("scene-box").hidden = true;
  $("scene-hover").hidden = true;
  $("scene-reset").hidden = true;
  $("legend-scene-block").hidden = true;
  $("scene-note").textContent = t("scene.unavailable", { reason: t(reason) });
}

let sceneRequested = false;

async function startScene() {
  sceneRequested = true;
  if (typeof WebGL2RenderingContext !== "function") {
    sceneUnavailable("scene.reason.noWebgl2");
    return;
  }
  let module_;
  try {
    module_ = await import("/web/braid-scene.js");
  } catch (error) {
    console.error(error);
    sceneUnavailable("scene.reason.load");
    return;
  }
  try {
    scene = module_.createBraidScene($("scene-box"), { onSelect: select, onHover: showHover, onUnavailable: sceneUnavailable, t });
  } catch (error) {
    console.error(error);
    sceneUnavailable("scene.reason.start");
    return;
  }
  $("legend-scene-block").hidden = false;
  labelCanvas();
  syncScene();
}

function labelCanvas() {
  if (!scene || !scene.canvas) return;
  scene.canvas.setAttribute("aria-label", t("scene.canvas.aria"));
  if (scene.refreshLabels && state.view === "map3d") scene.refreshLabels();
}

// ---------------------------------------------------------------- start

function renderAll() {
  renderChrome();
  renderSources();
  renderAgentFilters();
  renderStatusFilters();
  renderFilterStatus();
  renderKindFilter();
  renderCounters();
  renderLanes();
  renderDropped();
  renderTable();
  renderEvidence();
  renderPlayback();
  renderLegend();
  showHover(null);
}

state.langChoice = (() => {
  const stored = readPreference("lang");
  return LANGUAGES.includes(stored) ? stored : "auto";
})();
bindControls();
applyLanguage();
renderAll();
restoreView();
setView(state.view);
loadSnapshot();
followEvents();
