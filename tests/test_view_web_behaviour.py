# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T047 (finding 9): behaviour tests of the activity viewer page for playback, SSE resume, the evidence
panel and the scene-failure fallback.

The real `loom.js` runs under Node with the minimal DOM of `test_view_web_bundle`, a scripted `fetch`
(`/snapshot` and `/events`) and a recording scene stub. Timers over 20 ms are shortened so reconnects and
playback steps finish quickly. Nothing here reads the script as text.
"""
import json
import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from agent_braid.view_loom import parse_stream
from agent_braid.view_model import build_model
from tests.test_view_web_bundle import DOM_STUB, EXAMPLE, MODULES, WEB

SCENE_STUB = """
globalThis.sceneCalls = [];
globalThis.sceneSelected = [];
globalThis.sceneHandlers = null;
export function createBraidScene(container, handlers) {
  globalThis.sceneHandlers = handlers;
  return {
    setModel() {},
    setVisible(seqs) { sceneCalls.push([...seqs]); },
    setSelected(seq) { sceneSelected.push(seq); },
    resetView() {},
    summary() { return { visible: 0, drawn: 0, seqs: [], omitted: [] }; },
    dispose() {},
  };
}
"""
SCENE_THROWS = """
export function createBraidScene() { throw new Error("no webgl context"); }
"""
SCENE_HOOKS = """
export async function resolve(specifier, context, next) {
  if (specifier === "/web/braid-scene.js") {
    return { url: new URL("./" + (process.env.SCENE_VARIANT || "scene-stub.mjs"), import.meta.url).href, shortCircuit: true };
  }
  return next(specifier, context);
}
"""
DRIVER = """
import { readFileSync } from "node:fs";
import { register } from "node:module";
import { find } from "./dom-stub.mjs";

const { model, config, steps } = JSON.parse(readFileSync(process.argv[2], "utf8"));
const realSetTimeout = globalThis.setTimeout;
globalThis.setTimeout = (fn, ms, ...rest) => realSetTimeout(fn, Math.min(ms, 20), ...rest);
const sleep = (ms) => new Promise((resolve) => realSetTimeout(resolve, ms));
if (config.noWebgl) delete globalThis.WebGL2RenderingContext;
register("./scene-hooks.mjs", import.meta.url);

const requests = [];
const queue = [...config.events];
const encoder = new TextEncoder();
globalThis.fetch = async (url, options = {}) => {
  requests.push({ url, headers: options.headers || {} });
  if (url === "/snapshot") return { ok: true, status: 200, json: async () => ({ model, droppedAttributeNames: [], uiLanguageHint: config.hint }) };
  const plan = queue.shift();
  if (!plan) return new Promise(() => {});
  if (plan.status !== 200) return { ok: false, status: plan.status, body: null };
  let index = 0;
  return { ok: true, status: 200, body: { getReader: () => ({
    read: async () => {
      if (index < plan.chunks.length) return { done: false, value: encoder.encode(plan.chunks[index++]) };
      return plan.hang ? new Promise(() => {}) : { done: true };
    },
  }) } };
};

await import("./loom.js");
await sleep(60);

const text = (id) => find(id).textContent;
const observe = () => ({
  count: text("pb-count"), playing: find("pb-play").attrs["data-playing"],
  rows: find("events-body").children.map((row) => Number(row.descendants().find((node) => node.attrs["data-seq"]).attrs["data-seq"])),
  backDisabled: find("pb-back").disabled, forwardDisabled: find("pb-forward").disabled,
  evidence: text("evidence"), authorization: [text("authorization"), find("authorization").className], connection: text("connection"), notice: text("notice"),
  snapshots: requests.filter((request) => request.url === "/snapshot").length,
  events: requests.filter((request) => request.url === "/events").map((request) => request.headers),
  scene: { section: find("scene-section").hidden, box: find("scene-box").hidden, note: text("scene-note"),
           legend: find("legend-scene-block").hidden, calls: [...(globalThis.sceneCalls || [])], selected: [...(globalThis.sceneSelected || [])] },
});
const results = [observe()];
for (const step of steps) {
  if (step.click) find(step.click).listeners.click[0]();
  else if (step.range !== undefined) {
    find("pb-range").value = String(step.range);
    find("pb-range").listeners.input[0]({ target: find("pb-range") });
  } else if (step.speed) find("pb-speed").value = String(step.speed);
  else if (step.select !== undefined) {
    find("events-body").descendants().find((node) => node.attrs["data-seq"] === String(step.select)).listeners.click[0]();
  } else if (step.unavailable) globalThis.sceneHandlers.onUnavailable(step.unavailable);
  await sleep(step.wait || 60);
  results.push(observe());
}
console.log(JSON.stringify(results));
process.exit(0);
"""


def block(identifier, data="changed"):
    return f"id: {identifier}\ndata: {data}\n\n"


HANG = {"status": 200, "chunks": [], "hang": True}


@unittest.skipIf(not shutil.which("node") and not os.environ.get("CI"), "node is needed to drive the page without a browser")
class PageBehaviourCase(unittest.TestCase):
    """Runs the real loom.js under Node; `drive` returns one observation before the steps and one after each."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name)
        (cls.root / "package.json").write_text('{"type": "module"}')
        for name in MODULES:
            shutil.copyfile(WEB / name, cls.root / name)
        for name, body in (("dom-stub.mjs", DOM_STUB), ("scene-stub.mjs", SCENE_STUB), ("scene-throws.mjs", SCENE_THROWS),
                           ("scene-hooks.mjs", SCENE_HOOKS), ("driver.mjs", DRIVER)):
            (cls.root / name).write_text(body)
        cls.model = json.loads(json.dumps(build_model(parse_stream(EXAMPLE.read_bytes()))))
        cls.total = len(cls.model["elements"])
        cls.seqs = [row["seq"] for row in cls.model["table"]]

    def drive(self, steps=(), events=(), variant=None, languages=None, **config):
        path = self.root / "input.json"
        path.write_text(json.dumps({"model": self.model, "config": {"events": list(events), **config}, "steps": list(steps)}))
        environment = {**os.environ, "SCENE_VARIANT": variant or "scene-stub.mjs"}
        if languages is not None:
            environment["NAV_LANGUAGES"] = json.dumps(languages)
        done = subprocess.run(["node", "driver.mjs", str(path)], cwd=self.root, capture_output=True, text=True,
                              timeout=60, env=environment)
        if done.returncode != 0:
            raise AssertionError(done.stderr)
        return json.loads(done.stdout)


class PlaybackTests(PageBehaviourCase):
    FAST = {"speed": 1000}

    def test_the_page_opens_at_the_end_with_every_event_in_the_table(self):
        first = self.drive()[0]
        self.assertEqual(first["count"], f"{self.total} of {self.total}")
        self.assertEqual(first["rows"], self.seqs)

    def test_play_steps_one_event_at_a_time_to_the_end_and_then_stops(self):
        results = self.drive([self.FAST, {"click": "pb-start"}, {"click": "pb-play", "wait": 400}])
        self.assertEqual(results[2]["count"], f"0 of {self.total}")
        self.assertEqual(results[2]["rows"], [])
        self.assertEqual(results[3]["count"], f"{self.total} of {self.total}")
        self.assertEqual(results[3]["rows"], self.seqs)
        self.assertEqual(results[3]["playing"], "false")

    def test_play_at_the_end_restarts_from_the_beginning(self):
        results = self.drive([{"click": "pb-play", "wait": 1}])
        self.assertEqual(results[1]["playing"], "true")
        self.assertLess(len(results[1]["rows"]), self.total)

    def test_pause_keeps_the_position_and_it_does_not_move_afterwards(self):
        results = self.drive([{"click": "pb-start"}, {"click": "pb-play", "wait": 100}, {"click": "pb-play", "wait": 1},
                              {"wait": 150}])
        playing, paused, later = results[2], results[3], results[4]
        self.assertEqual(playing["playing"], "true")
        self.assertEqual(paused["playing"], "false")
        self.assertEqual((paused["count"], paused["rows"]), (later["count"], later["rows"]))
        self.assertEqual(paused["rows"], self.seqs[:len(paused["rows"])])

    def test_every_manual_control_stops_playback_and_moves_by_its_own_amount(self):
        results = self.drive([{"click": "pb-start"}, {"click": "pb-forward"}, {"click": "pb-forward"}, {"click": "pb-back"},
                              {"click": "pb-play", "wait": 1}, {"range": 3}, {"click": "pb-play", "wait": 1}, {"click": "pb-end"}])
        counts = [result["count"] for result in results[1:]]
        self.assertEqual(counts[:4], [f"0 of {self.total}", f"1 of {self.total}", f"2 of {self.total}", f"1 of {self.total}"])
        self.assertEqual(results[5]["playing"], "true")
        self.assertEqual((results[6]["count"], results[6]["playing"], results[6]["rows"]), (f"3 of {self.total}", "false", self.seqs[:3]))
        self.assertEqual(results[7]["playing"], "true")
        self.assertEqual((results[8]["count"], results[8]["playing"]), (f"{self.total} of {self.total}", "false"))

    def test_the_buttons_are_disabled_at_the_ends(self):
        results = self.drive([{"click": "pb-start"}, {"click": "pb-end"}])
        self.assertEqual((results[1]["backDisabled"], results[1]["forwardDisabled"]), (True, False))
        self.assertEqual((results[2]["backDisabled"], results[2]["forwardDisabled"]), (False, True))

    def test_the_scene_is_shown_exactly_the_events_up_to_the_playback_position(self):
        results = self.drive([{"click": "pb-start"}, {"range": 4}])
        self.assertEqual(results[1]["scene"]["calls"][-1], [])
        self.assertEqual(results[2]["scene"]["calls"][-1], self.seqs[:4])


class LanguageTests(PageBehaviourCase):
    """OD-V1: the page language follows the browser or desktop-app locale, then the server hint, then English."""

    def test_english_is_the_fallback_when_nothing_is_supported(self):
        final = self.drive(languages=["de-DE"])[0]
        self.assertEqual(final["count"], f"{self.total} of {self.total}")

    def test_a_spanish_browser_gets_spanish(self):
        final = self.drive(languages=["es-ES", "en"])[0]
        self.assertEqual(final["count"], f"{self.total} de {self.total}")
        self.assertIn("Selecciona un evento", final["evidence"])

    def test_the_server_hint_is_used_when_the_browser_offers_no_supported_language(self):
        self.assertEqual(self.drive(languages=["fr"], hint="es")[0]["count"], f"{self.total} de {self.total}")

    def test_the_boundary_badge_follows_the_model_and_a_true_value_is_marked(self):
        first = self.drive()[0]
        self.assertEqual(first["authorization"], ["executionAuthorization: false", "badge"])
        self.model = {**self.model, "executionAuthorization": True}
        try:
            self.assertEqual(self.drive()[0]["authorization"], ["executionAuthorization: true", "badge mark unverified"])
        finally:
            self.model = {**self.model, "executionAuthorization": False}


class SseResumeTests(PageBehaviourCase):
    def test_a_reconnect_sends_the_last_event_id_and_data_blocks_refresh_the_snapshot(self):
        final = self.drive([{"wait": 150}], [{"status": 200, "chunks": [block(5), block(7)]}, HANG])[-1]
        self.assertEqual(final["events"][0], {"Accept": "text/event-stream"})
        self.assertEqual(final["events"][1], {"Accept": "text/event-stream", "Last-Event-ID": "7"})
        self.assertEqual(final["connection"], "live")
        self.assertGreaterEqual(final["snapshots"], 2)

    def test_a_block_split_across_chunks_with_crlf_line_ends_is_read_whole(self):
        final = self.drive([{"wait": 150}], [{"status": 200, "chunks": ["id: 1", "2\r\ndata: changed\r", "\n\r\n"]}, HANG])[-1]
        self.assertEqual(final["events"][1]["Last-Event-ID"], "12")

    def test_a_crlf_pair_split_between_chunks_is_read_as_one_line_end(self):
        final = self.drive([{"wait": 150}], [{"status": 200, "chunks": ["id: 9\r\n\r", "\ndata: changed\r\n\r\n"]}, HANG])[-1]
        self.assertEqual(final["events"][1]["Last-Event-ID"], "9")

    def test_a_non_numeric_negative_or_oversized_id_never_replaces_the_resume_point(self):
        chunks = [block(3), block("abc"), block("12345678901234567"), block("-4")]
        final = self.drive([{"wait": 150}], [{"status": 200, "chunks": chunks}, HANG])[-1]
        self.assertEqual(final["events"][1]["Last-Event-ID"], "3")

    def test_a_comment_block_adds_no_refresh_and_no_resume_point(self):
        final = self.drive([{"wait": 100}], [{"status": 200, "chunks": [": keep-alive\n\n"], "hang": True}])[-1]
        self.assertEqual(final["snapshots"], 2)  # the first load and the one on connecting
        self.assertEqual(final["events"], [{"Accept": "text/event-stream"}])

    def test_a_failed_stream_is_retried_and_without_an_id_sends_no_resume_point(self):
        final = self.drive([{"wait": 150}], [{"status": 500}, HANG])[-1]
        self.assertEqual(final["events"], [{"Accept": "text/event-stream"}] * 2)
        self.assertEqual(final["connection"], "live")

    def test_a_closed_session_stops_following_and_is_not_retried(self):
        final = self.drive([{"wait": 150}], [{"status": 404}])[-1]
        self.assertEqual(final["connection"], "not open")
        self.assertEqual(len(final["events"]), 1)


class EvidencePanelTests(PageBehaviourCase):
    def pick(self, with_reference):
        elements = [e for e in self.model["elements"] if bool(e.get("evidenceRef")) is with_reference]
        self.assertTrue(elements)
        return elements[0]

    def test_with_nothing_selected_the_panel_asks_for_a_selection(self):
        self.assertIn("Select an event", self.drive()[0]["evidence"])

    def test_a_selected_event_shows_its_kind_class_verification_and_evidence_path_and_hash(self):
        element = self.pick(True)
        panel = self.drive([{"select": element["seq"]}])[1]["evidence"]
        self.assertIn(f"Event {element['seq']} · {element['kind']}", panel)
        self.assertIn(element["evidenceRef"]["path"], panel)
        self.assertIn(element["evidenceRef"]["sha256"], panel)
        self.assertIn("not a guarantee and not a safety ordering", panel)
        self.assertIn(element["verification"], panel)

    def test_an_event_without_an_artifact_says_there_is_none(self):
        element = self.pick(False)
        panel = self.drive([{"select": element["seq"]}])[1]["evidence"]
        self.assertIn("None: the event is host-reported or derived by the viewer", panel)

    def test_selecting_another_event_replaces_the_panel_and_tells_the_scene(self):
        first, second = self.seqs[0], self.seqs[1]
        results = self.drive([{"select": first}, {"select": second}])
        self.assertIn(f"Event {first} ", results[1]["evidence"])
        self.assertIn(f"Event {second} ", results[2]["evidence"])
        self.assertNotIn(f"Event {first} ", results[2]["evidence"])
        self.assertEqual(results[2]["scene"]["selected"][-1], second)


class SceneFallbackTests(PageBehaviourCase):
    def test_a_working_scene_is_shown_without_a_failure_note(self):
        final = self.drive()[-1]
        self.assertFalse(final["scene"]["section"])
        self.assertFalse(final["scene"]["legend"])
        self.assertNotIn("not available", final["scene"]["note"])

    def test_a_browser_without_webgl2_keeps_the_table_and_says_why(self):
        final = self.drive(noWebgl=True)[-1]
        self.assertIn("The 3D scene is not available: this browser has no WebGL2.", final["scene"]["note"])
        self.assertIn("The table below shows the same events", final["scene"]["note"])
        self.assertTrue(final["scene"]["box"])
        self.assertTrue(final["scene"]["legend"])
        self.assertEqual(final["rows"], self.seqs)

    def test_scene_code_that_cannot_be_loaded_keeps_the_table_and_says_why(self):
        final = self.drive(variant="missing-scene.mjs")[-1]
        self.assertIn("its code could not be loaded or was refused", final["scene"]["note"])
        self.assertTrue(final["scene"]["box"])
        self.assertEqual(final["rows"], self.seqs)

    def test_a_scene_that_throws_on_start_keeps_the_table_and_says_why(self):
        final = self.drive(variant="scene-throws.mjs")[-1]
        self.assertIn("WebGL2 could not be started", final["scene"]["note"])
        self.assertEqual(final["rows"], self.seqs)

    def test_a_scene_that_reports_itself_unavailable_later_falls_back_and_playback_still_works(self):
        results = self.drive([{"unavailable": "the GPU context was lost."}, {"click": "pb-start"}, {"click": "pb-forward"}])
        self.assertIn("The 3D scene is not available: the GPU context was lost.", results[1]["scene"]["note"])
        self.assertTrue(results[1]["scene"]["box"])
        self.assertEqual(results[3]["rows"], self.seqs[:1])


if __name__ == "__main__":
    unittest.main()
