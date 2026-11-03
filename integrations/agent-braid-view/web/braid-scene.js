// SPDX-License-Identifier: AGPL-3.0-only
// Agent Braid activity viewer: first-party Three.js scene of the Loom model (SPEC-061 T025).
//
// Read-only and bound to the same model as the table view: every drawn object belongs to exactly one
// model element (its `seq`), clicking one asks the page to select that event (the evidence panel
// is the table view's), and playback shows the same prefix of events by hiding later objects and
// clipping the strands at the playback frontier. Three.js comes from web/vendor through the inline
// import map of index.html; nothing here loads or sends anything.
//
// Visual grammar (specs/061-activity-viewer/research.md):
//   strand tube               strand per agent or unit (colour is the host)
//   two tubes exchanging lanes  independent-candidate pair (the only pair drawn as a swap; layout only)
//   arc over lanes            a classified pair between non-adjacent lanes (bridge, no crossing); coloured and
//                             styled by its classification, so an unknown pair is a dashed pulsing arc
//   arrow                     ordered pair, no swap
//   red knot between stubs    conflicting pair, no swap, recoil
//   dashed pulsing link       unknown pair, no swap, never coloured as independent
//   polygon badge             compatibility class: the number of sides is the class (3 + class). A class is
//                             a categorical label, not a guarantee and not a safety ordering, so every badge
//                             has the same colour and opacity
//   translucent slabs         planned waves (advisory plan, not a runtime measurement)
//   framed slabs              runtime wave markers
//   rings                     grants (thin) and workflow gates (thick); sides and colour by state or result
//   cone                      hazard, anchored at every unit strand it names; sparks when observed, dashed
//                             pulsing wire when not observed (absence of observation is not evidence)
//   grey dashed stub          observation gap: the strand is broken and the absence is visible
//   amber octahedron          unverified: not checked by this viewer
// Effort and tokens are not drawn in this release.
//
// Opacity never carries a class or any ordering: it is used only for the translucent wave slabs, the
// selection frame and the pulse of the dashed, not-observed and gap shapes.

import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";

const TIME_LENGTH = 24;
const LANE_GAP = 1.6;
const TUBE_RADIUS = 0.07;
const CLIP_EPSILON = 0.12;
const MAX_DRAWN_ELEMENTS = 2000;
const LABEL_LIMIT = 40;
const BADGE_RADIUS = 0.17;
const VERTICAL_FOV = 40;

const DRAWN_ELEMENTS = new Set(["strand", "strand-state", "strand-end", "crossing", "hazard-cone", "gap",
  "wave-plane", "wave-marker", "gate-ring"]);
const NOT_DRAWN_REASON = {
  "session": "session origin: shown in the table",
  "report": "analysis report: shown in the table and the evidence panel",
  "runtime-phase": "runtime phase: shown in the table",
  "effort": "effort and tokens are not drawn in this release: shown in the table",
};

const COLORS = {
  independent: 0x2a9d8f,
  ordered: 0x5f7fb0,
  conflict: 0xd1495b,
  unknown: 0xe0a100,
  hazard: 0xe4572e,
  spark: 0xffb703,
  badge: 0x7f8fa9,
  wave: 0x4c78a8,
  runtimeWave: 0x8e5ea2,
  unverified: 0xf2a900,
  grey: 0x8a8d96,
  selection: 0x1b8cff,
};
const HOST_COLORS = { braid: 0x5b7db1, claude: 0xb0794f, codex: 0x7a8f5a };
// [sides, colour]: the shape differs as well as the colour, and the label names the state or result.
const GATE_RESULTS = {
  "refused": [3, 0xd1495b], "busy": [4, 0x8a8d96], "inconclusive": [5, 0xe0a100],
  "hazards-found": [6, 0xe4572e], "ok-analyzed": [8, 0x2a9d8f], "ok-certified": [32, 0x3a86ff],
};
const GRANT_STATES = {
  "issued": [32, 0x3a86ff], "consumed": [32, 0x8a8d96], "expired": [12, 0x9d8189], "refused": [4, 0xd1495b],
};

const V = (x, y, z) => new THREE.Vector3(x, y, z);

function shorten(value) {
  const text = String(value === null || value === undefined ? "" : value);
  return text.length > LABEL_LIMIT ? text.slice(0, LABEL_LIMIT - 1) + "…" : text;
}

function runsOf(indexes) {
  const sorted = [...new Set(indexes)].sort((a, b) => a - b);
  const runs = [];
  for (const index of sorted) {
    const last = runs[runs.length - 1];
    if (last && index === last[1] + 1) last[1] = index;
    else runs.push([index, index]);
  }
  return runs;
}

// ---------------------------------------------------------------- building the objects of a model

export function buildBraid(model, options = {}) {
  const labelsOn = options.labels !== false && typeof document !== "undefined";
  const textStyle = { color: options.textColor || "#444444", halo: options.haloColor || "#ffffff" };
  const group = new THREE.Group();
  const built = {
    group, bySeq: new Map(), xOf: new Map(), notDrawn: new Map(), animated: new Set(), animatedSeqs: new Set(),
    minX: 0, maxX: 0,
    dispose() {
      group.traverse((object) => {
        if (object.geometry) object.geometry.dispose();
        const list = Array.isArray(object.material) ? object.material : object.material ? [object.material] : [];
        for (const item of list) {
          if (item.map) item.map.dispose();
          item.dispose();
        }
      });
      group.clear();
    },
  };
  if (!model || !Array.isArray(model.elements) || !Array.isArray(model.lanes)) return built;

  const elements = model.elements;
  const lanes = model.lanes;
  const laneById = new Map(lanes.map((lane) => [lane.strandId, lane.laneIndex]));
  const laneCount = lanes.reduce((count, lane) => Math.max(count, lane.laneIndex + 1), 0);
  const rawMax = elements.reduce((most, element) => Math.max(most, Number(element.x) || 0), 1);
  const scale = TIME_LENGTH / rawMax;
  const xOf = (element) => (Number(element.x) || 0) * scale;
  const zOf = (index) => (index - (laneCount - 1) / 2) * LANE_GAP;
  const spanZ = Math.max(0, laneCount - 1) * LANE_GAP;
  built.maxX = TIME_LENGTH;
  for (const element of elements) built.xOf.set(element.seq, xOf(element));

  const materials = new Map();
  function material(kind, color, settings = {}) {
    const key = kind + ":" + color + ":" + JSON.stringify(settings);
    const known = materials.get(key);
    if (known) return known;
    const common = { color };
    if (settings.pulse || (settings.opacity !== undefined && settings.opacity < 1)) {
      common.transparent = true;
      common.opacity = settings.opacity === undefined ? 1 : settings.opacity;
    }
    if (settings.depthWrite === false) common.depthWrite = false;
    if (settings.wireframe) common.wireframe = true;
    let created;
    if (kind === "solid") created = new THREE.MeshStandardMaterial({ ...common, roughness: 0.55, metalness: 0.05 });
    else if (kind === "points") created = new THREE.PointsMaterial({ ...common, size: 0.1 });
    else if (kind === "line") created = new THREE.LineBasicMaterial(common);
    else created = new THREE.MeshBasicMaterial(common);
    created.userData.base = common.opacity === undefined ? 1 : common.opacity;
    if (settings.pulse) {
      created.userData.pulse = true;
      built.animated.add(created);
    }
    materials.set(key, created);
    return created;
  }

  let drawnCount = 0;

  // `owner` is the seq whose visibility governs the object; `selectable` makes a click select that seq.
  function put(owner, object, part, selectable = true) {
    object.userData.part = part;
    if (selectable) object.userData.seq = owner;
    group.add(object);
    if (!built.bySeq.has(owner)) built.bySeq.set(owner, []);
    built.bySeq.get(owner).push(object);
    if (object.material && object.material.userData && object.material.userData.pulse) built.animatedSeqs.add(owner);
    return object;
  }

  function tube(owner, part, curve, radius, mat, segments = 16) {
    return put(owner, new THREE.Mesh(new THREE.TubeGeometry(curve, segments, radius, 8, false), mat), part);
  }

  function line3(a, b) {
    return new THREE.LineCurve3(a, b);
  }

  // A dashed run built from short tubes so that it is visible at any line width.
  function dashes(owner, part, from, to, radius, mat, dash = 0.16, gap = 0.12) {
    const length = from.distanceTo(to);
    if (length <= 0) return;
    const direction = to.clone().sub(from).normalize();
    for (let at = 0; at < length; at += dash + gap) {
      const end = Math.min(at + dash, length);
      tube(owner, part, line3(from.clone().addScaledVector(direction, at), from.clone().addScaledVector(direction, end)),
        radius, mat, 1);
    }
  }

  function label(owner, text, position, settings = {}) {
    if (!labelsOn) return;
    const sprite = makeLabel(text, textStyle, settings);
    if (!sprite) return;
    sprite.position.copy(position);
    put(owner, sprite, "label", settings.selectable === true);
  }

  function unverifiedMarker(element, x, y, z) {
    const mesh = new THREE.Mesh(new THREE.OctahedronGeometry(0.13),
      material("basic", COLORS.unverified, { wireframe: true }));
    mesh.position.set(x, y, z);
    put(element.seq, mesh, "unverified-marker");
  }

  // ---- strands: one tube per lane, broken at observation gaps, ending at the close event when there is one
  const byId = new Map(elements.map((element) => [element.seq, element]));
  const closeAt = new Map();
  const gapsAt = new Map();
  for (const element of elements) {
    if (element.element === "strand-end" && !closeAt.has(element.strandId)) closeAt.set(element.strandId, xOf(element));
    if (element.element === "gap" && element.strandId !== null && element.strandId !== undefined) {
      if (!gapsAt.has(element.strandId)) gapsAt.set(element.strandId, []);
      gapsAt.get(element.strandId).push(xOf(element));
    }
  }
  for (const lane of lanes) {
    const opener = byId.get(lane.seq);
    const x0 = opener ? xOf(opener) : 0;
    const x1 = Math.max(closeAt.has(lane.strandId) ? closeAt.get(lane.strandId) : TIME_LENGTH, x0 + 0.05);
    const z = zOf(lane.laneIndex);
    const mat = material("solid", HOST_COLORS[lane.host] || COLORS.grey);
    const radius = lane.declared ? TUBE_RADIUS : TUBE_RADIUS * 0.6;
    let start = x0;
    for (const gapX of (gapsAt.get(lane.strandId) || []).sort((a, b) => a - b)) {
      if (gapX <= start || gapX >= x1) continue;
      if (gapX - 0.25 > start) tube(lane.seq, "strand", line3(V(start, 0, z), V(gapX - 0.25, 0, z)), radius, mat, 1);
      start = gapX + 0.25;
    }
    if (x1 > start) tube(lane.seq, "strand", line3(V(start, 0, z), V(x1, 0, z)), radius, mat, 1);
    label(lane.seq, shorten(lane.label), V(x0 - 0.3, 0.3, z), { align: "right", selectable: lane.declared });
    if (lane.declared && opener && opener.unverified) unverifiedMarker(opener, x0, 0.5, z);
    // tubes of a lane that only a crossing names are not selectable: they are not an event of their own
    for (const object of built.bySeq.get(lane.seq) || []) {
      if (!lane.declared && object.userData.part === "strand") delete object.userData.seq;
    }
  }

  // ---- per element
  for (const element of elements) {
    if (!DRAWN_ELEMENTS.has(element.element)) {
      built.notDrawn.set(element.seq, NOT_DRAWN_REASON[element.element] || "kind not drawn: shown in the table");
      continue;
    }
    if (element.element === "strand") {
      if (!built.bySeq.has(element.seq)) built.notDrawn.set(element.seq, "strand without a lane");
      continue; // the lane loop above drew it
    }
    if (drawnCount >= MAX_DRAWN_ELEMENTS) {
      built.notDrawn.set(element.seq, "draw cap of " + MAX_DRAWN_ELEMENTS + " elements: shown in the table");
      continue;
    }
    const before = built.bySeq.has(element.seq) ? built.bySeq.get(element.seq).length : 0;
    const x = xOf(element);
    const drawer = DRAWERS[element.element];
    drawer({ element, x, zOf, spanZ, laneById, put, tube, line3, dashes, label, material, unverifiedMarker, built });
    const after = built.bySeq.has(element.seq) ? built.bySeq.get(element.seq).length : 0;
    if (after === before && !built.notDrawn.has(element.seq)) built.notDrawn.set(element.seq, "nothing to place in the lanes: shown in the table");
    if (after > before) drawnCount += 1;
  }
  built.materials = materials;
  return built;
}

// ---------------------------------------------------------------- one drawer per element kind

function classBadge(c, class_, x, y, z) {
  if (!Number.isInteger(class_) || class_ < 0 || class_ > 5) return;
  const sides = 3 + class_;
  const mesh = new THREE.Mesh(new THREE.CylinderGeometry(BADGE_RADIUS, BADGE_RADIUS, 0.05, sides),
    c.material("solid", COLORS.badge));
  mesh.position.set(x, y, z);
  mesh.userData.sides = sides;
  c.put(c.element.seq, mesh, "badge");
  c.label(c.element.seq, "class " + class_, V(x, y + 0.3, z), { size: 0.26, selectable: true });
}

function drawCrossing(c) {
  const { element, x, zOf, put, tube, line3, dashes, material } = c;
  const segments = Array.isArray(element.segments) ? element.segments : [];
  if (segments.length === 0) {
    c.built.notDrawn.set(element.seq, "pair without a placed lane: shown in the table");
    return;
  }
  const za = zOf(segments[0].fromLane);
  const zb = zOf(segments[segments.length - 1].toLane);
  const mid = (za + zb) / 2;
  const direction = Math.sign(zb - za) || 1;
  const seq = element.seq;
  let badgeY = 0.62;
  let markerY = 0.95;
  switch (element.drawAs) {
    case "swap": {
      const half = 0.7;
      const over = new THREE.CubicBezierCurve3(V(x - half, 0.1, za), V(x, 0.1, za), V(x, 0.1, zb), V(x + half, 0.1, zb));
      const under = new THREE.CubicBezierCurve3(V(x - half, -0.1, zb), V(x, -0.1, zb), V(x, -0.1, za), V(x + half, -0.1, za));
      const mat = material("solid", COLORS.independent);
      tube(seq, "swap", over, TUBE_RADIUS * 1.15, mat, 20);
      tube(seq, "swap", under, TUBE_RADIUS * 1.15, mat, 20);
      break;
    }
    case "ordered-link": {
      const mat = material("solid", COLORS.ordered);
      tube(seq, "ordered-link", line3(V(x, 0, za), V(x, 0, zb - direction * 0.28)), 0.035, mat, 1);
      const head = new THREE.Mesh(new THREE.ConeGeometry(0.12, 0.32, 16), mat);
      head.rotation.x = direction > 0 ? Math.PI / 2 : -Math.PI / 2;
      head.position.set(x, 0, zb - direction * 0.16);
      put(seq, head, "ordered-head");
      break;
    }
    case "conflict-knot": {
      const mat = material("solid", COLORS.conflict);
      const knot = new THREE.Mesh(new THREE.TorusKnotGeometry(0.2, 0.055, 64, 8), mat);
      knot.position.set(x, 0.2, mid);
      put(seq, knot, "conflict-knot");
      tube(seq, "conflict-stub", line3(V(x, 0, za), V(x, 0, mid - direction * 0.32)), 0.045, mat, 1);
      tube(seq, "conflict-stub", line3(V(x, 0, zb), V(x, 0, mid + direction * 0.32)), 0.045, mat, 1);
      badgeY = 0.8;
      break;
    }
    case "unknown-link": {
      dashes(seq, "unknown-link", V(x, 0, za), V(x, 0, zb), 0.05,
        material("basic", COLORS.unknown, { pulse: true, opacity: 1 }));
      break;
    }
    case "bridge": {
      // A bridge is only the route over lanes that are not crossed; the colour and style follow the classification.
      const rise = 1.2 + 0.3 * (Array.isArray(element.passesOverLanes) ? element.passesOverLanes.length : 0);
      const arc = new THREE.QuadraticBezierCurve3(V(x, 0, za), V(x, rise, mid), V(x, 0, zb));
      if (element.classification === "unknown") {
        const pulse = material("basic", COLORS.unknown, { pulse: true, opacity: 1 });
        const points = arc.getPoints(24);
        for (let index = 0; index + 1 < points.length; index += 2) {
          tube(seq, "bridge-unknown", line3(points[index], points[index + 1]), 0.05, pulse, 1);
        }
      } else {
        const known = { "independent-candidate": ["bridge", COLORS.independent], "ordered": ["bridge-ordered", COLORS.ordered],
          "conflicting": ["bridge-conflicting", COLORS.conflict] }[element.classification];
        const [part, colour] = known || ["bridge-unrecognized", COLORS.grey];
        tube(seq, part, arc, 0.05, material("solid", colour), 28);
      }
      badgeY = rise / 2 + 0.3;
      markerY = badgeY + 0.5;
      break;
    }
    default:
      c.built.notDrawn.set(seq, "pair without a placed lane: shown in the table");
      return;
  }
  if (element.incompleteCoverage && element.classification !== "unknown") {
    // Partial coverage: what the crossing does not list is not shown to be absent.
    const halo = new THREE.Mesh(new THREE.TorusGeometry(0.5, 0.02, 6, 28),
      material("basic", COLORS.unknown, { pulse: true, opacity: 0.9 }));
    halo.rotation.x = Math.PI / 2;
    halo.position.set(x, 0.12, mid);
    put(seq, halo, "partial-halo");
  }
  classBadge(c, element.compatibilityClass, x, badgeY, mid);
  if (element.unverified) c.unverifiedMarker(element, x, markerY, mid);
}

function drawHazard(c) {
  const { element, x, zOf, laneById, put, material } = c;
  const units = Array.isArray(element.units) ? element.units : [];
  const absent = element.absence === true;
  let index = 0;
  for (const unit of units) {
    if (!laneById.has(unit)) continue;
    const z = zOf(laneById.get(unit));
    const cone = new THREE.Mesh(new THREE.ConeGeometry(0.22, 0.5, 16),
      absent ? material("basic", COLORS.unknown, { wireframe: true, pulse: true, opacity: 1 })
        : material("solid", COLORS.hazard));
    cone.rotation.z = Math.PI; // apex down onto the strand it names
    cone.position.set(x, 0.4, z);
    put(element.seq, cone, absent ? "hazard-cone-unobserved" : "hazard-cone");
    if (!absent) {
      const positions = [];
      for (let spark = 0; spark < 7; spark += 1) {
        const phase = (element.seq * 13 + index * 7 + spark * 5) % 37;
        const angle = (phase / 37) * Math.PI * 2 + spark;
        positions.push(x + Math.cos(angle) * 0.34, 0.75 + (spark % 3) * 0.12, z + Math.sin(angle) * 0.34);
      }
      const geometry = new THREE.BufferGeometry();
      geometry.setAttribute("position", new THREE.Float32BufferAttribute(positions, 3));
      put(element.seq, new THREE.Points(geometry, material("points", COLORS.spark)), "hazard-spark");
    }
    if (element.unverified) c.unverifiedMarker(element, x, 1.15, z);
    index += 1;
  }
  if (index === 0) c.built.notDrawn.set(element.seq, "no unit strand of this hazard is in the lanes: shown in the table");
}

function drawGap(c) {
  const { element, x, zOf, laneById, put, dashes, material } = c;
  if (!laneById.has(element.strandId)) {
    c.built.notDrawn.set(element.seq, "gap not tied to a lane: shown in the table");
    return;
  }
  const z = zOf(laneById.get(element.strandId));
  dashes(element.seq, "gap-stub", V(x - 0.25, 0, z), V(x + 0.25, 0, z), 0.05,
    material("basic", COLORS.grey, { pulse: true, opacity: 1 }), 0.1, 0.07);
  for (const side of [-0.28, 0.28]) {
    const bar = new THREE.Mesh(new THREE.BoxGeometry(0.04, 0.32, 0.04), material("basic", COLORS.grey));
    bar.position.set(x + side, 0, z);
    bar.rotation.z = side < 0 ? 0.35 : -0.35;
    put(element.seq, bar, "gap-break");
  }
  if (element.unverified) c.unverifiedMarker(element, x, 0.6, z);
}

function slabsFor(c, indexes, x, color, filled, part) {
  const { element, zOf, put, material } = c;
  for (const [low, high] of runsOf(indexes)) {
    const depth = (high - low) * LANE_GAP + 1.1;
    const geometry = new THREE.BoxGeometry(0.06, 1.5, depth);
    const centre = (zOf(low) + zOf(high)) / 2;
    if (filled) {
      const slab = new THREE.Mesh(geometry, material("basic", color, { opacity: 0.16, depthWrite: false }));
      slab.position.set(x, 0, centre);
      put(element.seq, slab, part);
    }
    const edges = new THREE.LineSegments(new THREE.EdgesGeometry(geometry), material("line", color));
    edges.position.set(x, 0, centre);
    put(element.seq, edges, part + "-edges");
  }
}

function drawWavePlane(c) {
  const { element, x, zOf, label } = c;
  const waves = Array.isArray(element.waves) ? element.waves : [];
  let top = null;
  waves.forEach((wave, index) => {
    const indexes = Array.isArray(wave.lanes) ? wave.lanes : [];
    if (indexes.length === 0) return;
    slabsFor(c, indexes, x + index * 0.55, COLORS.wave, true, "wave-slab");
    const z = zOf(Math.min(...indexes));
    if (top === null || z < top) top = z;
  });
  if (top === null) {
    c.built.notDrawn.set(element.seq, "plan without placed lanes: shown in the table");
    return;
  }
  label(element.seq, "advisory plan, not a runtime measurement", V(x, 1.15, top), { selectable: true });
  if (element.unverified) c.unverifiedMarker(element, x, 1.5, top);
}

function drawWaveMarker(c) {
  const { element, x, zOf, label } = c;
  const indexes = Array.isArray(element.lanes) ? element.lanes : [];
  if (indexes.length === 0) {
    c.built.notDrawn.set(element.seq, "wave without placed lanes: shown in the table");
    return;
  }
  slabsFor(c, indexes, x, COLORS.runtimeWave, element.phase === "finished", "wave-frame");
  label(element.seq, "wave " + element.wave + " " + element.phase, V(x, 1.0, zOf(Math.min(...indexes))), { selectable: true });
  if (element.unverified) c.unverifiedMarker(element, x, 1.4, zOf(Math.min(...indexes)));
}

function drawGateRing(c) {
  const { element, x, spanZ, put, material, label } = c;
  const grant = element.ringKind === "grant";
  const table = grant ? GRANT_STATES : GATE_RESULTS;
  const name = grant ? element.state : element.gateStatus;
  const [sides, color] = table[name] || [3, COLORS.grey];
  const radius = Math.max(grant ? 0.95 : 1.25, spanZ / 2 + (grant ? 0.65 : 1.0));
  let ring;
  if (element.ringKind === "workflow-phase") {
    const points = [];
    for (let step = 0; step < 48; step += 1) {
      const angle = (step / 48) * Math.PI * 2;
      if (step % 3 !== 2) points.push(V(0, Math.sin(angle) * radius, Math.cos(angle) * radius));
    }
    const dashed = [];
    for (let step = 0; step + 1 < points.length; step += 2) dashed.push(points[step], points[step + 1]);
    ring = new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(dashed), material("line", color));
  } else {
    ring = new THREE.Mesh(new THREE.TorusGeometry(radius, grant ? 0.035 : 0.075, 8, sides), material("solid", color));
    ring.rotation.y = Math.PI / 2;
  }
  ring.position.set(x, 0, 0);
  put(element.seq, ring, grant ? "grant-ring" : element.ringKind === "workflow-phase" ? "gate-phase-ring" : "gate-result-ring");
  label(element.seq, (grant ? "grant " : "gate ") + String(name), V(x, radius + 0.3, 0), { selectable: true });
  if (element.unverified) c.unverifiedMarker(element, x, radius + 0.75, 0);
}

function drawBead(c) {
  const { element, x, zOf, put, material } = c;
  const lane = Array.isArray(element.lanes) ? element.lanes[0] : undefined;
  if (lane === undefined) {
    c.built.notDrawn.set(element.seq, "no lane: shown in the table");
    return;
  }
  const mesh = new THREE.Mesh(new THREE.SphereGeometry(0.11, 12, 8), material("solid", COLORS.grey));
  mesh.position.set(x, 0, zOf(lane));
  put(element.seq, mesh, "strand-state");
  if (element.unverified) c.unverifiedMarker(element, x, 0.5, zOf(lane));
}

function drawStrandEnd(c) {
  const { element, x, zOf, put, material } = c;
  const lane = Array.isArray(element.lanes) ? element.lanes[0] : undefined;
  if (lane === undefined) {
    c.built.notDrawn.set(element.seq, "no lane: shown in the table");
    return;
  }
  const cap = new THREE.Mesh(new THREE.TorusGeometry(0.16, 0.035, 8, 20), material("solid", COLORS.grey));
  cap.rotation.y = Math.PI / 2;
  cap.position.set(x, 0, zOf(lane));
  put(element.seq, cap, "strand-end");
  if (element.unverified) c.unverifiedMarker(element, x, 0.5, zOf(lane));
}

const DRAWERS = {
  "crossing": drawCrossing,
  "hazard-cone": drawHazard,
  "gap": drawGap,
  "wave-plane": drawWavePlane,
  "wave-marker": drawWaveMarker,
  "gate-ring": drawGateRing,
  "strand-state": drawBead,
  "strand-end": drawStrandEnd,
};

// ---------------------------------------------------------------- text sprites (drawn on a 2D canvas)

function makeLabel(text, style, settings) {
  let canvas;
  let context;
  try {
    canvas = document.createElement("canvas");
    context = canvas.getContext("2d");
  } catch (error) {
    return null;
  }
  if (!context) return null;
  const pixels = 2 * (settings.size ? settings.size / 0.34 * 28 : 28);
  const font = "600 " + Math.round(pixels) + "px system-ui, sans-serif";
  context.font = font;
  const width = Math.ceil(context.measureText(text).width) + 16;
  const height = Math.ceil(pixels * 1.5);
  canvas.width = Math.min(width, 2048);
  canvas.height = height;
  context.font = font;
  context.textBaseline = "middle";
  context.textAlign = "center";
  context.lineJoin = "round";
  context.lineWidth = 6;
  context.strokeStyle = style.halo;
  context.fillStyle = style.color;
  context.strokeText(text, canvas.width / 2, height / 2, canvas.width - 8);
  context.fillText(text, canvas.width / 2, height / 2, canvas.width - 8);
  const texture = new THREE.CanvasTexture(canvas);
  texture.colorSpace = THREE.SRGBColorSpace;
  texture.minFilter = THREE.LinearFilter;
  texture.generateMipmaps = false;
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: texture, depthTest: false, transparent: true }));
  const unit = 1 / (pixels / (settings.size || 0.34));
  sprite.scale.set(canvas.width * unit, canvas.height * unit, 1);
  sprite.center.set(settings.align === "right" ? 1 : 0.5, 0.5);
  sprite.renderOrder = 10;
  return sprite;
}

// ---------------------------------------------------------------- inspection helpers (also used by tests)

// The x of the playback frontier: the position of the last visible event, or -Infinity when nothing is visible.
export function frontierX(built, visibleSeqs) {
  let frontier = -Infinity;
  for (const seq of visibleSeqs) {
    const x = built.xOf.get(seq);
    if (x !== undefined && x > frontier) frontier = x;
  }
  return frontier;
}

// Plain description of what was built: parts per owning seq, and why an element was left out.
export function describeBraid(built) {
  const parts = {};
  for (const [seq, objects] of built.bySeq) parts[seq] = [...new Set(objects.map((object) => object.userData.part))].sort();
  const notDrawn = {};
  for (const [seq, reason] of built.notDrawn) notDrawn[seq] = reason;
  return { parts, notDrawn };
}

// ---------------------------------------------------------------- the interactive scene

function readColors(container) {
  const style = getComputedStyle(container);
  const pick = (name, fallback) => {
    const value = style.getPropertyValue(name).trim();
    return value || fallback;
  };
  return { text: style.color || "#444444", halo: pick("--panel", "#ffffff"), accent: pick("--accent", "#1b5fa6") };
}

export function createBraidScene(container, hooks = {}) {
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "low-power" });
  const canvas = renderer.domElement;
  canvas.setAttribute("role", "img");
  canvas.setAttribute("aria-label",
    "3D view of strands, crossings, waves, gates and hazards. The events table presents the same facts as text.");
  canvas.classList.add("scene-canvas");
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(VERTICAL_FOV, 1, 0.1, 400);
  const controls = new OrbitControls(camera, canvas);
  controls.screenSpacePanning = true;
  const clip = new THREE.Plane(V(-1, 0, 0), -1000);
  renderer.clippingPlanes = [clip];
  scene.add(new THREE.AmbientLight(0xffffff, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 2.2);
  sun.position.set(6, 12, 8);
  scene.add(sun);
  container.append(canvas);

  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");
  const raycaster = new THREE.Raycaster();
  raycaster.params.Line = { threshold: 0.15 };
  raycaster.params.Points = { threshold: 0.12 };
  const pointer = new THREE.Vector2();

  let model = null;
  let built = buildBraid(null);
  let visible = new Set();
  let selected = null;
  let frontier = -Infinity;
  let selection = null;
  let hovered = null;
  let fitted = false;
  let userMoved = false;
  let frame = 0;
  let disposed = false;
  let colors = readColors(container);

  function size() {
    const width = Math.max(container.clientWidth, 1);
    const height = Math.max(container.clientHeight, 1);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.updateProjectionMatrix();
    requestRender();
  }

  function pulsing() {
    if (reducedMotion.matches || document.visibilityState !== "visible" || built.animated.size === 0) return false;
    for (const seq of built.animatedSeqs) if (visible.has(seq)) return true;
    return false;
  }

  function render(time) {
    frame = 0;
    if (disposed) return;
    const wave = reducedMotion.matches ? 0.85 : 0.5 + 0.5 * Math.sin((time || 0) / 260);
    for (const item of built.animated) item.opacity = item.userData.base * (0.35 + 0.65 * wave);
    renderer.render(scene, camera);
    if (pulsing()) requestRender();
  }

  function requestRender() {
    if (!frame && !disposed) frame = requestAnimationFrame(render);
  }

  // Sample points of everything that was built (all of it, not only what is visible now).
  function samplePoints() {
    const points = [];
    built.group.updateMatrixWorld(true);
    built.group.traverse((object) => {
      if (object.isSprite) {
        for (const side of [-0.5, 0.5]) points.push(V(side - (object.center.x - 0.5), 0, 0).applyMatrix4(object.matrixWorld));
        return;
      }
      const attribute = object.geometry && object.geometry.attributes && object.geometry.attributes.position;
      if (!attribute) return;
      const stride = Math.max(1, Math.floor(attribute.count / 12));
      for (let index = 0; index < attribute.count; index += stride) {
        points.push(V(0, 0, 0).fromBufferAttribute(attribute, index).applyMatrix4(object.matrixWorld));
      }
    });
    const keep = Math.max(1, Math.ceil(points.length / 6000));
    return keep === 1 ? points : points.filter((_, index) => index % keep === 0);
  }

  function fit() {
    const points = samplePoints();
    if (points.length === 0) return;
    const centre = new THREE.Box3().setFromPoints(points).getCenter(new THREE.Vector3());
    const direction = V(-0.15, 0.55, 0.85).normalize();
    // Back the camera off along a fixed direction until every sampled point is inside the view.
    let distance = 1;
    for (let step = 0; step < 120; step += 1) {
      camera.position.copy(centre).addScaledVector(direction, distance);
      camera.lookAt(centre);
      camera.updateMatrixWorld();
      const projected = V(0, 0, 0);
      const inside = points.every((point) => {
        projected.copy(point).project(camera);
        return Math.abs(projected.x) <= 0.92 && Math.abs(projected.y) <= 0.9 && projected.z < 1;
      });
      if (inside) break;
      distance *= 1.05;
    }
    controls.target.copy(centre);
    camera.far = Math.max(400, distance * 4);
    camera.updateProjectionMatrix();
    controls.update();
    fitted = true;
  }

  function updateSelection() {
    if (selection) {
      scene.remove(selection);
      selection.traverse((object) => {
        if (object.geometry) object.geometry.dispose();
        if (object.material) object.material.dispose();
      });
      selection = null;
    }
    const objects = selected === null ? undefined : built.bySeq.get(selected);
    if (!objects || !visible.has(selected)) return;
    const box = new THREE.Box3();
    for (const object of objects) if (object.userData.part !== "label") box.expandByObject(object);
    if (box.isEmpty()) return;
    box.expandByScalar(0.18);
    const colour = new THREE.Color();
    try {
      colour.set(colors.accent);
    } catch (error) {
      colour.set(COLORS.selection);
    }
    const centre = box.getCenter(new THREE.Vector3());
    const extent = box.getSize(new THREE.Vector3());
    selection = new THREE.Group();
    const fill = new THREE.Mesh(new THREE.BoxGeometry(extent.x, extent.y, extent.z),
      new THREE.MeshBasicMaterial({ color: colour, transparent: true, opacity: 0.14, depthWrite: false }));
    fill.position.copy(centre);
    selection.add(fill);
    selection.add(new THREE.Box3Helper(box, colour));
    scene.add(selection);
  }

  function applyVisibility() {
    for (const [seq, objects] of built.bySeq) {
      const shown = visible.has(seq);
      for (const object of objects) object.visible = shown;
    }
    frontier = frontierX(built, visible);
    clip.constant = Number.isFinite(frontier) ? frontier + CLIP_EPSILON : -1000;
    updateSelection();
    requestRender();
  }

  function rebuild() {
    colors = readColors(container);
    scene.remove(built.group);
    built.dispose();
    built = buildBraid(model, { textColor: colors.text, haloColor: colors.halo });
    scene.add(built.group);
    if (!fitted && model && model.elements.length > 0) {
      size();
      fit();
    }
    applyVisibility();
  }

  function pick(event) {
    const rect = canvas.getBoundingClientRect();
    if (rect.width === 0 || rect.height === 0) return null;
    pointer.set(((event.clientX - rect.left) / rect.width) * 2 - 1, -((event.clientY - rect.top) / rect.height) * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    for (const hit of raycaster.intersectObjects(built.group.children, false)) {
      const seq = hit.object.userData.seq;
      if (seq === undefined || !visible.has(seq) || hit.point.x > frontier + CLIP_EPSILON) continue;
      return seq;
    }
    return null;
  }

  let down = null;
  let hoverFrame = 0;
  function onPointerDown(event) {
    down = { x: event.clientX, y: event.clientY };
  }
  function onPointerUp(event) {
    const start = down;
    down = null;
    if (!start || Math.hypot(event.clientX - start.x, event.clientY - start.y) > 4) return;
    const seq = pick(event);
    if (seq !== null && hooks.onSelect) hooks.onSelect(seq);
  }
  function onPointerMove(event) {
    if (event.buttons !== 0 || hoverFrame) return;
    hoverFrame = requestAnimationFrame(() => {
      hoverFrame = 0;
      const seq = pick(event);
      canvas.classList.toggle("over-element", seq !== null);
      if (seq !== hovered) {
        hovered = seq;
        if (hooks.onHover) hooks.onHover(seq);
      }
    });
  }
  function onPointerLeave() {
    if (hovered !== null) {
      hovered = null;
      canvas.classList.remove("over-element");
      if (hooks.onHover) hooks.onHover(null);
    }
  }
  function onContextLost(event) {
    event.preventDefault();
    if (hooks.onUnavailable) hooks.onUnavailable("The WebGL context was lost.");
  }

  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointerup", onPointerUp);
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerleave", onPointerLeave);
  canvas.addEventListener("webglcontextlost", onContextLost);
  controls.addEventListener("change", requestRender);
  controls.addEventListener("start", () => { userMoved = true; });
  const observer = typeof ResizeObserver === "function" ? new ResizeObserver(() => {
    size();
    if (!userMoved && fitted) fit(); // until the user moves the camera, keep the whole scene framed
  }) : null;
  if (observer) observer.observe(container);
  const onVisibility = () => requestRender();
  const onTheme = () => rebuild();
  document.addEventListener("visibilitychange", onVisibility);
  darkQuery.addEventListener("change", onTheme);
  reducedMotion.addEventListener("change", onVisibility);
  size();

  return {
    setModel(next) {
      model = next;
      rebuild();
    },
    setVisible(seqs) {
      visible = new Set(seqs);
      applyVisibility();
    },
    setSelected(seq) {
      selected = seq === undefined ? null : seq;
      updateSelection();
      requestRender();
    },
    resetView() {
      userMoved = false;
      fit();
      requestRender();
    },
    // What the scene shows right now, for the note under it.
    summary() {
      let drawn = 0;
      for (const seq of visible) if (built.bySeq.has(seq)) drawn += 1;
      const omitted = new Map();
      for (const [seq, reason] of built.notDrawn) if (visible.has(seq)) omitted.set(reason, (omitted.get(reason) || 0) + 1);
      return { visible: visible.size, drawn, omitted: [...omitted].map(([reason, count]) => ({ reason, count })) };
    },
    dispose() {
      disposed = true;
      if (frame) cancelAnimationFrame(frame);
      if (hoverFrame) cancelAnimationFrame(hoverFrame);
      if (observer) observer.disconnect();
      document.removeEventListener("visibilitychange", onVisibility);
      darkQuery.removeEventListener("change", onTheme);
      reducedMotion.removeEventListener("change", onVisibility);
      controls.dispose();
      built.dispose();
      renderer.dispose();
      canvas.remove();
    },
  };
}
