# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 VIS.1c (T054, T058): the shared state and derived model (state.js), the string module (strings.js),
the language detection and the server language hint. state.js and strings.js run under Node without a DOM."""
import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from html.parser import HTMLParser
from pathlib import Path

from agent_braid.view_loom import parse_stream
from agent_braid.view_model import build_model
from agent_braid.view_serve import language_hint_from_environ
from tests.test_view_web_bundle import EXAMPLE, WEB, read, strings_table

RICH = Path(__file__).resolve().parents[1] / "specs/061-activity-viewer/vis1c/audit/fixture/rich.jsonl"
NODE = unittest.skipIf(not shutil.which("node") and not os.environ.get("CI"), "node is needed to run the modules")

PROGRAM = """
import { readFileSync } from "node:fs";
import * as state from "./state.js";
import * as strings from "./strings.js";
const { model, call } = JSON.parse(readFileSync(process.argv[2], "utf8"));
const derived = model ? state.derive(model) : null;
const strip = (value) => JSON.parse(JSON.stringify(value, (key, item) => (typeof item === "function" || item instanceof Map || item instanceof Set ? undefined : item)));
const calls = {
  sequence: () => ({ sequence: derived.axis.sequence, untimed: derived.axis.untimed, total: derived.axis.total,
    spanX: derived.axis.spanX, ticks: derived.axis.ticks(), same: derived.placedModel === model,
    placed: derived.placedModel.elements.map((element) => ({ seq: element.seq, x: element.x, timeKnown: element.timeKnown, relMs: element.relMs })),
    lanes: derived.lanes, crossings: derived.crossings, concurrency: derived.concurrency, overlaps: derived.overlaps,
    waiting: derived.lanes.map(state.waitingTime) }),
  derive: () => ({ lanes: derived.lanes, rows: derived.rows, crossings: derived.crossings, conflicts: derived.conflicts,
    concurrency: derived.concurrency, overlaps: derived.overlaps, breaks: derived.axis.breaks, ticks: derived.axis.ticks(),
    summary: state.summarize(model, derived) }),
  filters: () => {
    const result = {};
    for (const [name, filters] of Object.entries(call.sets)) {
      const f = { agents: new Set(filters.agents || []), status: new Set(filters.status || []), kinds: new Set(filters.kinds || []), onlyProblems: Boolean(filters.onlyProblems) };
      result[name] = model.elements.filter((element) => state.passesFilters(element, derived, f)).map((element) => element.seq);
    }
    return result;
  },
  hash: () => {
    const s = state.createState();
    Object.assign(s, call.state);
    s.hiddenSources = new Set(call.state.hiddenSources || []);
    s.filters = { agents: new Set(call.state.agents || []), status: new Set(call.state.status || []), onlyProblems: Boolean(call.state.onlyProblems) };
    const text = state.encodeHash(s);
    return { text, decoded: state.decodeHash(text), hostile: state.decodeHash(call.hostile) };
  },
  time: () => ({ clock: call.values.map(state.formatClock), duration: call.values.map(state.formatDuration) }),
  language: () => call.cases.map((c) => strings.chooseLanguage(c)),
  tags: () => call.tags.map(strings.normalizeTag),
  translate: () => call.cases.map(([lang, key, params]) => strings.translate(lang, key, params)),
  sources: () => model.elements.map((element) => state.sourceOf(element)),
  markerkinds: () => Object.fromEntries(model.elements.map((element) => [element.seq, state.markerKind(element)])),
  hashkinds: () => {
    const s = state.createState();
    s.filters.kinds = new Set(["conflict", "gap", "bogus"]);
    const text = state.encodeHash(s);
    return { text, decoded: state.decodeHash(text), hasFilters: state.hasFilters(s) };
  },
};
console.log(JSON.stringify(strip(calls[call.name]())));
"""


class ModuleCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        (cls.root / "package.json").write_text('{"type": "module"}')
        for name in ("state.js", "strings.js"):
            shutil.copyfile(WEB / name, cls.root / name)
        (cls.root / "driver.mjs").write_text(PROGRAM)
        cls.rich = json.loads(json.dumps(build_model(parse_stream(RICH.read_bytes()))))
        cls.example = json.loads(json.dumps(build_model(parse_stream(EXAMPLE.read_bytes()))))

    def run_js(self, name, model=None, **call):
        path = self.root / "input.json"
        path.write_text(json.dumps({"model": model, "call": {"name": name, **call}}))
        done = subprocess.run(["node", "driver.mjs", str(path)], cwd=self.root, capture_output=True, text=True, timeout=60)
        if done.returncode != 0:
            raise AssertionError(done.stderr)
        return json.loads(done.stdout)


@NODE
class DerivedModelTests(ModuleCase):
    """REQ-016 / SC-016: the derived opening, closing and duration of every lane equal the model's relMs values."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.derived = cls.run_js(cls, "derive", cls.rich)

    def by_seq(self, model):
        return {e["seq"]: e for e in model["elements"]}

    def test_every_lane_opens_and_closes_at_the_relms_of_its_open_and_close_events(self):
        elements = self.by_seq(self.rich)
        closes = {e["strandId"]: e for e in self.rich["elements"] if e["element"] == "strand-end"}
        self.assertEqual(len(self.derived["lanes"]), len(self.rich["lanes"]))
        for lane in self.derived["lanes"]:
            with self.subTest(lane=lane["strandId"]):
                self.assertEqual(lane["openMs"], elements[lane["openSeq"]]["relMs"])
                close = closes.get(lane["strandId"])
                if close:
                    self.assertEqual((lane["closeMs"], lane["state"]), (close["relMs"], "finished"))
                    self.assertEqual(lane["durationMs"], close["relMs"] - lane["openMs"])
                    self.assertEqual(lane["outcome"], close["outcome"])
                else:
                    self.assertEqual((lane["closeMs"], lane["durationMs"], lane["outcome"]), (None, None, None))

    def test_a_lane_without_a_close_is_never_finished_and_never_has_an_outcome(self):
        open_lanes = [lane for lane in self.derived["lanes"] if lane["closeSeq"] is None]
        self.assertTrue(open_lanes)
        self.assertTrue(all(lane["state"] != "finished" and lane["outcome"] is None for lane in open_lanes))

    def test_children_follow_their_parent_and_a_parent_that_is_not_a_lane_is_not_guessed(self):
        rows = [row["laneIndex"] for row in self.derived["rows"]]
        self.assertEqual(sorted(rows), sorted(lane["laneIndex"] for lane in self.rich["lanes"]))
        lanes = {lane["laneIndex"]: lane for lane in self.derived["lanes"]}
        for lane in lanes.values():
            if lane["parentLane"] is not None:
                self.assertLess(rows.index(lane["parentLane"]), rows.index(lane["laneIndex"]))
                self.assertEqual(lane["depth"], lanes[lane["parentLane"]]["depth"] + 1)
        orphan = json.loads(json.dumps(self.rich))
        orphan["lanes"][1]["parentStrandId"] = "nobody"
        result = self.run_js("derive", orphan)
        child = result["lanes"][1]
        self.assertEqual((child["parentLane"], child["orphan"]), (None, True))

    def test_lanes_with_the_same_label_get_an_ordinal_by_opening_time_and_others_do_not(self):
        twin = json.loads(json.dumps(self.rich))
        twin["lanes"][2]["label"] = twin["lanes"][1]["label"]
        result = self.run_js("derive", twin)
        first, second = result["lanes"][1], result["lanes"][2]
        self.assertEqual((first["ordinal"], second["ordinal"]), (1, 2))
        self.assertTrue(second["displayLabel"].endswith("#2"))
        self.assertTrue(all(lane["ordinal"] is None for lane in self.derived["lanes"]))

    def test_the_predicted_conflict_is_the_conflicting_crossing_and_no_observed_collision_exists(self):
        conflicting = {e["seq"] for e in self.rich["elements"] if e["element"] == "crossing" and e["classification"] == "conflicting"}
        self.assertEqual({c["seq"] for c in self.derived["conflicts"]}, conflicting)
        self.assertTrue(all(c["kind"] == "predicted" for c in self.derived["conflicts"]))
        self.assertEqual({c["kind"] for c in self.derived["crossings"]}, {None, "predicted"})
        self.assertEqual(self.derived["summary"]["predictedConflicts"], len(conflicting))

    def test_overlap_is_the_time_both_lanes_were_open_and_unknown_without_comparable_times(self):
        lanes = {lane["laneIndex"]: lane for lane in self.derived["lanes"]}
        for crossing in self.derived["crossings"]:
            a, b = (lanes[i] for i in crossing["lanes"])
            expected = max(0, min(a["endMs"], b["endMs"]) - max(a["openMs"], b["openMs"]))
            self.assertEqual(crossing["overlap"]["ms"], expected)
        mixed = json.loads(json.dumps(self.rich))
        mixed["axis"]["basis"] = "mixed"
        self.assertTrue(all(c["overlap"] is None for c in self.run_js("derive", mixed)["crossings"]))

    def test_concurrency_counts_open_lanes_and_its_peak_is_the_maximum_step(self):
        steps = self.derived["concurrency"]["steps"]
        known = [lane for lane in self.derived["lanes"] if lane["state"] != "unknown"]
        peak = max(sum(1 for lane in known if lane["openMs"] <= at < lane["endMs"]) for at in (lane["openMs"] for lane in known))
        self.assertEqual(self.derived["concurrency"]["peak"], peak)
        self.assertEqual(self.derived["concurrency"]["peak"], max(step["open"] for step in steps))
        self.assertEqual(steps[-1]["open"], 0)
        self.assertTrue(all(left["ms"] < right["ms"] for left, right in zip(steps, steps[1:])))

    def test_every_compression_of_the_model_is_a_labelled_break_with_its_omitted_time(self):
        breaks = self.derived["breaks"]
        self.assertEqual([b["spanMs"] for b in breaks], [c["spanMs"] for c in self.rich["axis"]["compressions"]])
        self.assertTrue(all(b["x2"] > b["x1"] for b in breaks))

    def test_no_tick_falls_inside_a_compressed_span(self):
        ticks = self.derived["ticks"]
        self.assertTrue(ticks)
        for tick in ticks:
            self.assertFalse(any(b["x1"] < tick["x"] < b["x2"] for b in self.derived["breaks"]), tick)

    def test_a_close_that_states_no_time_gives_no_end_time_and_no_waiting_span(self):
        model = json.loads(json.dumps(self.rich))
        close = next(e for e in model["elements"] if e["element"] == "strand-end" and e["strandId"] == "explore")
        close["timeKnown"] = False
        lane = next(l for l in self.run_js("derive", model)["lanes"] if l["strandId"] == "explore")
        self.assertEqual((lane["closeMs"], lane["durationMs"], lane["state"]), (None, None, "finished"))

    def test_waiting_spans_run_between_stated_updates_and_an_open_one_has_no_end(self):
        model = json.loads(json.dumps(self.rich))
        updates = [e for e in model["elements"] if e["element"] == "strand-state" and e["strandId"] == "explore"]
        updates[0]["state"] = "waiting"
        lane = next(l for l in self.run_js("derive", model)["lanes"] if l["strandId"] == "explore")
        self.assertEqual(lane["waitSpans"][0]["fromMs"], updates[0]["relMs"])
        self.assertEqual(lane["waitSpans"][0]["toMs"], updates[1]["relMs"])
        self.assertFalse(lane["waitSpans"][0]["open"])

    def test_a_model_without_lanes_derives_nothing_and_does_not_fail(self):
        empty = {"lanes": [], "elements": [], "table": [], "axis": {}, "counters": {"gaps": {"total": 0}}}
        result = self.run_js("derive", empty)
        self.assertEqual((result["lanes"], result["crossings"], result["concurrency"]["peak"]), ([], [], 0))

    def test_the_existing_example_model_derives_too(self):
        result = self.run_js("derive", self.example)
        self.assertEqual(len(result["lanes"]), len(self.example["lanes"]))


@NODE
class FilterTests(ModuleCase):
    def test_agent_status_and_problem_filters_act_on_elements_and_keep_untied_ones(self):
        agent = self.rich["lanes"][1]["strandId"]
        sets = {"none": {}, "agent": {"agents": [agent]}, "finished": {"status": ["finished"]}, "problems": {"onlyProblems": True}}
        result = self.run_js("filters", self.rich, sets=sets)
        everything = [e["seq"] for e in self.rich["elements"]]
        self.assertEqual(result["none"], everything)
        tied = {e["seq"] for e in self.rich["elements"] if e.get("lanes")}
        self.assertTrue(set(result["agent"]) >= set(everything) - tied)  # untied elements stay
        lane = self.rich["lanes"][1]["laneIndex"]
        self.assertTrue(all(lane in e["lanes"] for e in self.rich["elements"] if e["seq"] in result["agent"] and e.get("lanes")))
        self.assertLess(len(result["agent"]), len(everything))
        self.assertLessEqual(len(result["finished"]), len(everything))
        problems = [e for e in self.rich["elements"] if e["seq"] in result["problems"]]
        self.assertTrue(problems)
        self.assertTrue(any(e["element"] == "gap" for e in problems))
        self.assertTrue(any(e.get("classification") == "conflicting" for e in problems))
        self.assertFalse(any(e["element"] == "strand" for e in problems), "plain unverified is not a problem")


@NODE
class KindFilterTests(ModuleCase):
    """REQ-019 / SC-019: a legend entry filters markers alike in every view; agents and their states are never hidden by it."""

    def test_a_marker_kind_keeps_its_markers_and_hides_other_markers_but_never_agents(self):
        result = self.run_js("filters", self.rich, sets={"conflict": {"kinds": ["conflict"]}, "gap": {"kinds": ["gap", "hazard"]}})
        by_seq = {e["seq"]: e for e in self.rich["elements"]}
        markers = {"crossing", "hazard-cone", "gap", "gate-ring"}
        for name, kept in (("conflict", lambda e: e["element"] == "crossing" and e["classification"] == "conflicting"),
                           ("gap", lambda e: e["element"] in ("gap", "hazard-cone"))):
            shown = [by_seq[seq] for seq in result[name]]
            with self.subTest(kind=name):
                self.assertTrue(all(kept(e) for e in shown if e["element"] in markers))
                self.assertTrue(any(kept(e) for e in shown))
                self.assertEqual(sum(1 for e in shown if e["element"] == "strand"), len(self.rich["lanes"]))

    def test_every_element_has_the_marker_kind_the_legend_names(self):
        kinds = self.run_js("markerkinds", self.rich)
        expected = {"crossing": {"conflicting": "conflict", "independent-candidate": "independent", "ordered": "ordered", "unknown": "unknown"}}
        for element in self.rich["elements"]:
            kind = kinds[str(element["seq"])]
            if element["element"] == "crossing":
                self.assertEqual(kind, expected["crossing"][element["classification"]])
            elif element["element"] == "hazard-cone":
                self.assertEqual(kind, "hazard")
            elif element["element"] == "gap":
                self.assertEqual(kind, "gap")
            elif element["element"] == "gate-ring":
                self.assertEqual(kind, "grant" if element["ringKind"] == "grant" else "gate")
            else:
                self.assertIsNone(kind, element["element"])

    def test_kinds_are_written_to_the_hash_and_count_as_a_filter(self):
        result = self.run_js("hashkinds", None)
        self.assertEqual(result["text"], "#v=timeline&kd=conflict,gap")
        self.assertEqual(result["decoded"]["kinds"], ["conflict", "gap"])
        self.assertTrue(result["hasFilters"])

    def test_the_kinds_survive_the_hash_and_unknown_ones_are_dropped(self):
        state = {"view": "timeline", "selected": None, "kinds": []}
        decoded = self.run_js("hash", None, state=state, hostile="#kd=conflict,evil,gap")["hostile"]
        self.assertEqual(decoded["kinds"], ["conflict", "gap"])


@NODE
class HashTests(ModuleCase):
    def test_the_hash_carries_ids_only_and_round_trips(self):
        state = {"view": "map3d", "selected": 12, "hiddenSources": ["hook"], "agents": ["explore"], "status": ["waiting"],
                 "onlyProblems": True, "viewport": {"x0": 1000, "x1": 9000}}
        result = self.run_js("hash", None, state=state, hostile="")
        self.assertEqual(result["decoded"], {"view": "map3d", "selected": 12, "hide": ["hook"], "agents": ["explore"],
                                             "status": ["waiting"], "kinds": [], "onlyProblems": True, "viewport": {"x0": 1000, "x1": 9000}})
        self.assertRegex(result["text"], r"^#[A-Za-z0-9=&,._:%#-]+$")

    def test_hostile_input_is_dropped_not_interpreted(self):
        hostile = "#v=<script>&sel=1;DROP&hide=ok,%01,%E0%A4%A&st=running,evil&x=9-1&ag=" + "a" * 200
        decoded = self.run_js("hash", None, state={}, hostile=hostile)["hostile"]
        self.assertEqual((decoded["view"], decoded["selected"], decoded["viewport"]), (None, None, None))
        self.assertEqual((decoded["hide"], decoded["status"], decoded["agents"]), (["ok"], ["running"], []))

    def test_an_unsafe_id_is_never_written_to_the_hash(self):
        state = {"view": "timeline", "selected": None, "hiddenSources": ["fine", "bad\u0001", "x" * 65]}
        self.assertEqual(self.run_js("hash", None, state=state, hostile="")["text"], "#v=timeline&hide=fine")

    def test_a_watched_root_source_survives_the_round_trip(self):
        state = {"view": "map3d", "selected": None, "hiddenSources": ["watched:root 1"]}
        result = self.run_js("hash", None, state=state, hostile="")
        self.assertEqual(result["decoded"]["hide"], ["watched:root 1"])


@NODE
class SourceAndTimeTests(ModuleCase):
    def test_every_event_of_the_example_has_one_known_source(self):
        sources = set(self.run_js("sources", self.example))
        self.assertTrue(sources <= {"watched", "replay", "hook", "viewer"} or all(s.startswith("watched:root ") for s in sources - {"watched", "replay", "hook", "viewer"}))

    def test_clock_and_duration_text(self):
        result = self.run_js("time", None, values=[0, 52000, 3725000, -1, None])
        self.assertEqual(result["clock"], ["0:00", "0:52", "1:02:05", "–", "–"])
        self.assertEqual(result["duration"], ["0 ms", "52 s", "1 h 02 min", "–", "–"])
        more = self.run_js("time", None, values=[850, 86000, 120000])["duration"]
        self.assertEqual(more, ["850 ms", "1 min 26 s", "2 min"])


@NODE
class LanguageTests(ModuleCase):
    """OD-V1 as accepted: manual choice, then the browser or desktop-app locale, then the server hint, then English."""

    def test_detection_order(self):
        cases = [
            {"choice": "es", "languages": ["en-US"], "hint": "en"},   # a manual choice wins
            {"choice": "auto", "languages": ["fr-FR", "es-MX", "en"], "hint": "en"},  # first supported browser entry
            {"choice": "auto", "languages": ["fr-FR"], "hint": "es"},  # nothing supported in the browser: the terminal hint
            {"choice": "auto", "languages": [], "hint": "es"},
            {"choice": "auto", "languages": ["de"], "hint": None},     # nothing supported: English
            {"choice": "auto", "languages": ["en-GB"], "hint": "es"},  # a supported browser locale beats the hint
            {"choice": "bogus", "languages": None, "hint": "klingon"},
        ]
        self.assertEqual(self.run_js("language", None, cases=cases), ["es", "es", "es", "es", "en", "en", "en"])

    def test_tags_are_normalised_and_unsupported_ones_are_refused(self):
        tags = ["es", "ES", "es-MX", "es_ES.UTF-8", "en_US", "C", "POSIX", "", None, "fr", "esperanto", 7]
        self.assertEqual(self.run_js("tags", None, tags=tags), ["es", "es", "es", "es", "en", None, None, None, None, None, None, None])

    def test_translation_falls_back_to_english_then_to_the_key_and_fills_placeholders(self):
        cases = [["es", "boundary", None], ["fr", "boundary", None], ["es", "no.such.key", None],
                 ["en", "playback.count", {"cursor": 3, "total": 9}], ["en", "playback.count", {"cursor": 3}]]
        result = self.run_js("translate", None, cases=cases)
        self.assertEqual(result[0], "Solo lectura · no autoriza ejecución")
        self.assertEqual(result[1], "Read-only · does not authorize execution")
        self.assertEqual(result[2], "no.such.key")
        self.assertEqual(result[3], "3 of 9")
        self.assertEqual(result[4], "3 of {total}")


@NODE
class StringTableTests(unittest.TestCase):
    """REQ-020 / SC-020: identical keys in both languages; every key used by the page exists."""

    @classmethod
    def setUpClass(cls):
        cls.table = strings_table()

    def test_the_spanish_and_english_tables_have_identical_keys(self):
        self.assertEqual(set(self.table["en"]) ^ set(self.table["es"]), set())

    def test_every_value_is_non_empty_and_placeholders_match_between_languages(self):
        placeholder = re.compile(r"\{([A-Za-z]+)\}")
        for key, english in self.table["en"].items():
            spanish = self.table["es"][key]
            with self.subTest(key=key):
                self.assertTrue(english.strip() and spanish.strip())
                self.assertEqual(set(placeholder.findall(english)), set(placeholder.findall(spanish)))

    def test_count_forms_come_in_pairs(self):
        keys = set(self.table["en"])
        for key in keys:
            if key.endswith(".one"):
                self.assertIn(key[:-4] + ".other", keys)
            if key.endswith(".other"):
                self.assertIn(key[:-6] + ".one", keys)

    def test_every_key_the_scripts_ask_for_exists(self):
        keys = set(self.table["en"])
        asked = set()
        for name in ("loom.js",):
            text = read(name)
            asked |= set(re.findall(r'\bt\(\s*"([A-Za-z0-9_.]+)"', text))
            asked |= {k + suffix for k in re.findall(r'\btn\(\s*"([A-Za-z0-9_.]+)"', text) for suffix in (".one", ".other")}
            asked |= set(re.findall(r'"((?:shape|scene\.reason|sceneLegend|mark|verification|state|outcome|connection|source)\.[A-Za-z0-9_.]+)"', text))
        self.assertTrue(asked)
        prefixes = {key for key in asked if key.endswith(".")}  # built at run time: "state." + name
        self.assertEqual(sorted(key for key in prefixes if not any(known.startswith(key) for known in keys)), [])
        self.assertEqual(sorted((asked - prefixes) - keys), [])

    def test_every_key_built_from_a_list_or_a_prefix_exists(self):
        keys = set(self.table["en"])
        text = read("loom.js")
        lists = {"sceneLegend.": r"SCENE_LEGEND_KEYS = \[([^\]]*)\]", "mark.": r"MARK_KEYS = \[([^\]]*)\]"}
        for prefix, pattern in lists.items():
            names = re.findall(r'"([A-Za-z]+)"', re.search(pattern, text).group(1))
            self.assertTrue(names)
            for name in names:
                self.assertIn(prefix + name, keys)
                if prefix == "mark.":
                    self.assertIn(prefix + name + ".meaning", keys)
        for name in ("rehashed", "derived", "unverified"):
            self.assertIn(f"verification.{name}.meaning", keys)
        for name in ("watched", "replay", "hook", "viewer"):
            self.assertIn(f"source.{name}.meaning", keys)
        for name in ("running", "waiting", "finished", "unknown"):
            self.assertIn(f"state.{name}", keys)
        for name in ("live", "reconnecting", "notOpen", "connecting"):
            self.assertIn(f"connection.{name}", keys)
        for value in re.findall(r'"(scene\.reason\.[A-Za-z0-9]+)"', text):
            self.assertIn(value, keys)

    def test_the_scene_reason_texts_the_page_translates_are_the_ones_the_scene_emits(self):
        scene = read("braid-scene.js")
        for english in re.findall(r'^\s*"([^"]+)": "scene\.reason\.', read("loom.js"), re.M):
            self.assertIn(english, scene)

    def test_no_user_facing_literal_is_assigned_in_the_page_script(self):
        text = read("loom.js")
        self.assertEqual(re.findall(r'textContent\s*=\s*"[^"]*[a-z] [a-z][^"]*"', text), [])
        self.assertEqual(re.findall(r'\bh\("[a-z0-9]+",[^)]*?\},\s*"[A-Za-z][^"]* [^"]*"\)', text), [])


class PageTextScan(HTMLParser):
    def __init__(self):
        super().__init__()
        self.stack, self.found = [], []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        self.stack.append((tag, attributes.get("data-i18n"), attributes.get("data-i18n-title"), attributes.get("title"), []))

    def handle_data(self, data):
        if self.stack:
            self.stack[-1][4].append(data)

    def handle_endtag(self, tag):
        while self.stack:
            name, key, title_key, title, data = self.stack.pop()
            if key:
                self.found.append((key, "".join(data).strip(), title_key, title))
            if name == tag:
                break


@NODE
class StaticPageTextTests(unittest.TestCase):
    """The English default in index.html equals the English table, so the page reads the same without scripts."""

    def test_every_data_i18n_key_exists_and_its_default_text_is_the_english_text(self):
        scan = PageTextScan()
        scan.feed(read("index.html"))
        table = strings_table()
        self.assertGreater(len(scan.found), 30)
        for key, text, title_key, title in scan.found:
            with self.subTest(key=key):
                self.assertIn(key, table["en"])
                self.assertEqual(" ".join(text.split()), table["en"][key])
                if title_key:
                    self.assertEqual(title, table["en"][title_key])

    def test_the_language_is_declared_and_the_boundary_strip_is_in_the_page(self):
        html = read("index.html")
        self.assertIn('<html lang="en">', html)
        self.assertIn('data-i18n="boundary"', html)


class LanguageHintTests(unittest.TestCase):
    """The server sends a bare language tag, never the locale string or the environment."""

    def test_precedence_and_supported_set(self):
        cases = [
            ({"LANG": "es_ES.UTF-8"}, "es"), ({"LANG": "en_US.UTF-8"}, "en"), ({"LC_ALL": "es_MX.UTF-8", "LANG": "en_US"}, "es"),
            ({"LC_MESSAGES": "en_GB", "LANG": "es_ES"}, "en"), ({"LC_ALL": "", "LANG": "es_ES"}, "es"),
            ({"LANG": "fr_FR.UTF-8"}, None), ({"LANG": "C"}, None), ({"LANG": "POSIX"}, None), ({}, None),
            ({"LC_ALL": "C", "LANG": "es_ES"}, None), ({"LANG": "es"}, "es"), ({"LANG": "../../etc"}, None),
        ]
        for environ, expected in cases:
            with self.subTest(environ=environ):
                self.assertEqual(language_hint_from_environ(environ), expected)

    def test_the_hint_leaves_only_as_a_two_letter_tag(self):
        self.assertEqual(language_hint_from_environ({"LANG": "es_ES.UTF-8@euro"}), "es")
        self.assertEqual(language_hint_from_environ({"LANG": "EN_us"}), "en")
        self.assertEqual(language_hint_from_environ({"LC_ALL": "en", "LANG": "es_ES.UTF-8"}), "en")


if __name__ == "__main__":
    unittest.main()


def _flip_untimed(model_events, every):
    """A copy of loom events where every `every`-th one states no time (shape of a mixed real stream)."""
    out = json.loads(json.dumps(model_events))
    for index, event in enumerate(out):
        if index % every == 1:
            event["at"] = {"relMs": 0, "basis": "sequence-only"}
    return out


@NODE
class SequenceAxisTests(ModuleCase):
    """Real-use bug 2026-11-04: a model with events that state no time is drawn on a sequence axis, honestly."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        from tests.test_view_web_behaviour import MIXED_REPORT, UNTIMED_REPORT, untimed_model
        cls.untimed = untimed_model(UNTIMED_REPORT, MIXED_REPORT)
        cls.mixed = json.loads(json.dumps(build_model(_flip_untimed(parse_stream(RICH.read_bytes()), 3))))

    def test_an_untimed_model_gets_one_slot_per_event_in_model_order_and_sequence_ticks(self):
        result = self.run_js("sequence", self.untimed)
        self.assertTrue(result["sequence"])
        self.assertEqual((result["untimed"], result["total"]), (len(self.untimed["elements"]),) * 2)
        order = {e["seq"]: e["order"] for e in self.untimed["elements"]}
        xs = {item["seq"]: item["x"] for item in result["placed"]}
        self.assertEqual(len(set(xs.values())), len(xs))
        self.assertEqual(sorted(xs, key=xs.get), sorted(order, key=order.get))
        self.assertEqual(result["spanX"], 1000 * len(xs))
        self.assertTrue(result["ticks"] and all(re.fullmatch(r"#\d+", tick["label"]) for tick in result["ticks"]))
        self.assertLessEqual(len(result["ticks"]), 10)
        self.assertTrue(all(c["positioned"] and not c["timeKnown"] for c in result["crossings"]))

    def test_no_duration_overlap_or_concurrency_is_derived_from_sequence_slots(self):
        result = self.run_js("sequence", self.untimed)
        for lane in result["lanes"]:
            self.assertEqual((lane["durationMs"], lane["observedMs"], lane["openKnown"]), (None, None, False))
            self.assertLess(lane["openX"], lane["endX"] + 1)
        self.assertEqual(result["concurrency"], {"steps": [], "peak": 0, "peakMs": None})
        self.assertEqual(result["overlaps"], [])
        self.assertTrue(all(c["overlap"] is None for c in result["crossings"]))

    def test_a_mixed_model_states_durations_only_where_both_ends_state_a_time(self):
        result = self.run_js("sequence", self.mixed)
        self.assertTrue(result["sequence"])
        self.assertGreater(result["untimed"], 0)
        self.assertLess(result["untimed"], result["total"])
        placed = {item["seq"]: item for item in result["placed"]}
        stated = {e["seq"]: e for e in self.mixed["elements"]}
        for item in result["placed"]:  # time stays the event's own; only the position is the slot
            self.assertEqual((item["timeKnown"], item["relMs"]), (stated[item["seq"]]["timeKnown"], stated[item["seq"]]["relMs"]))
        some = False
        for lane in result["lanes"]:
            opener = placed[lane["openSeq"]]
            close = placed.get(lane["closeSeq"])
            if lane["durationMs"] is not None:
                some = True
                self.assertTrue(opener["timeKnown"] and close["timeKnown"])
                self.assertEqual(lane["durationMs"], close["relMs"] - opener["relMs"])
            elif close is not None:
                self.assertFalse(opener["timeKnown"] and close["timeKnown"])
        self.assertTrue(some, "the mixed fixture keeps at least one fully timed lane")
        for lane, waiting in zip(result["lanes"], result["waiting"]):
            for span in lane["waitSpans"]:
                if span["fromMs"] is None or span["toMs"] is None:
                    self.assertFalse(waiting["complete"])
        self.assertEqual(result["concurrency"]["peak"], 0)

    def test_a_fully_timed_model_is_left_on_its_time_axis(self):
        result = self.run_js("sequence", self.rich)
        self.assertEqual((result["sequence"], result["same"], result["untimed"]), (False, True, 0))
