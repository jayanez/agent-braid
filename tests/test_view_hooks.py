# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-061 T019: observational Claude Code hook ingest (procedure_005, hook part)."""
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from agent_braid import view_hooks, view_serve
from agent_braid.view_hooks import HookIngest
from agent_braid.view_serve import IngestRefusal, ViewServer
from agent_braid.view_store import LoomStore

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests/fixtures/view/hooks"
RECEIPT = ROOT / "specs/061-activity-viewer/evidence/hv-t030-20261101.json"
CONTRACT = ROOT / "specs/061-activity-viewer/contracts/ui-security-privacy.md"
SENTINEL = "SENTINEL"
JSON = {"Content-Type": "application/json"}


def fixture(name):
    return json.loads((FIXTURES / f"{name}.json").read_text())


def kinds(events):
    return [event["kind"] for event in events]


class IngestCase(unittest.TestCase):
    def setUp(self):
        self.store = LoomStore()
        self.hooks = HookIngest(self.store)

    def events(self):
        return self.store.replay()

    def data(self, kind):
        return [event["data"] for event in self.events() if event["kind"] == kind]


class MappingTests(IngestCase):
    def test_first_event_opens_the_session_strand_without_session_start(self):
        self.hooks.handle(fixture("post-tool-use-main"))
        events = self.events()
        self.assertEqual(kinds(events), ["strand.open", "strand.update"])
        opened = events[0]["data"]
        self.assertEqual((opened["role"], opened["host"], opened["parentStrandId"]), ("agent", "claude", None))
        self.assertEqual(events[1]["data"]["strandId"], opened["strandId"])
        self.assertEqual((events[1]["data"]["state"], events[1]["data"]["toolName"]), ("running", "Bash"))

    def test_session_start_is_accepted_when_delivered_and_opens_once(self):
        self.hooks.handle(fixture("session-start"))
        self.hooks.handle(fixture("session-start"))
        self.hooks.handle(fixture("post-tool-use-main"))
        self.assertEqual(kinds(self.events()).count("strand.open"), 1)

    def test_subagent_strand_comes_from_agent_id_and_hangs_under_the_session(self):
        self.hooks.handle(fixture("subagent-start"))
        opens = self.data("strand.open")
        self.assertEqual([item["role"] for item in opens], ["agent", "subagent"])
        self.assertEqual(opens[1]["parentStrandId"], opens[0]["strandId"])
        self.assertEqual(opens[1]["label"], "general-purpose")

    def test_tool_event_inside_a_subagent_updates_the_subagent_strand(self):
        self.hooks.handle(fixture("subagent-start"))
        self.hooks.handle(fixture("post-tool-use-subagent"))
        sub = self.data("strand.open")[1]["strandId"]
        update = self.data("strand.update")[0]
        self.assertEqual((update["strandId"], update["toolName"]), (sub, "Bash"))

    def test_post_tool_use_inside_an_unannounced_subagent_still_opens_it(self):
        self.hooks.handle(fixture("post-tool-use-subagent"))
        self.assertEqual([item["role"] for item in self.data("strand.open")], ["agent", "subagent"])
        self.hooks.handle(fixture("subagent-start"))
        self.assertEqual(kinds(self.events()).count("strand.open"), 2)

    def test_subagent_stop_closes_the_strand_with_unknown_outcome(self):
        self.hooks.handle(fixture("subagent-start"))
        self.hooks.handle(fixture("subagent-stop"))
        closes = self.data("strand.close")
        self.assertEqual(closes, [{"strandId": self.data("strand.open")[1]["strandId"], "outcome": "unknown"}])

    def test_a_lone_surrogate_is_absent_not_an_error(self):
        for field in ("session_id", "agent_id", "tool_name", "agent_type"):
            with self.subTest(field):
                payload = {**fixture("post-tool-use-subagent"), field: "\ud800"}
                self.hooks.handle(payload)  # no exception: the server would otherwise answer 500
        self.assertTrue(all(event["executionAuthorization"] is False for event in self.events()))

    def test_events_for_a_closed_strand_are_not_stored(self):
        self.hooks.handle(fixture("subagent-start"))
        self.hooks.handle(fixture("subagent-stop"))
        count = len(self.events())
        self.hooks.handle(fixture("post-tool-use-subagent"))
        self.hooks.handle(fixture("subagent-stop"))
        self.assertEqual(len(self.events()), count)

    def test_session_end_closes_open_subagents_then_the_session(self):
        self.hooks.handle(fixture("subagent-start"))
        self.hooks.handle(fixture("session-end"))
        opens, closes = self.data("strand.open"), self.data("strand.close")
        self.assertEqual([item["strandId"] for item in closes], [opens[1]["strandId"], opens[0]["strandId"]])
        self.assertEqual({item["outcome"] for item in closes}, {"unknown"})

    def test_session_end_as_first_event_opens_and_closes_the_session(self):
        self.hooks.handle(fixture("session-end"))
        self.assertEqual(kinds(self.events()), ["strand.open", "strand.close"])

    def test_events_are_unverified_claude_hook_events_without_authority(self):
        for name in ("subagent-start", "post-tool-use-subagent", "subagent-stop", "session-end"):
            self.hooks.handle(fixture(name))
        for event in self.events():
            self.assertEqual(event["source"], {"adapter": "claude-hook", "evidenceRef": None,
                                               "host": "claude", "verification": "unverified"})
            self.assertIs(event["executionAuthorization"], False)
            self.assertEqual(event["at"]["basis"], "viewer-monotonic")

    def test_time_comes_from_the_injected_monotonic_clock(self):
        ticks = iter([0, 5_000_000, 9_000_000, 9_000_000])
        hooks = HookIngest(self.store, clock=lambda: next(ticks))
        hooks.handle(fixture("post-tool-use-main"))
        self.assertEqual([event["at"]["relMs"] for event in self.events()], [5, 9])

    def test_unsafe_tool_name_is_stored_as_null(self):
        payload = fixture("post-tool-use-main")
        payload["tool_name"] = "bad‮tool"
        self.hooks.handle(payload)
        self.assertIsNone(self.data("strand.update")[0]["toolName"])
        for bad in ("x" * (view_hooks.TEXT_MAX_LENGTH + 1), "Bash\n"):
            payload = fixture("post-tool-use-main")
            payload["tool_name"] = bad
            self.hooks.handle(payload)
        self.assertEqual([item["toolName"] for item in self.data("strand.update")], [None] * 3)
        payload = fixture("subagent-start")
        payload["agent_type"] = "general\n"
        self.hooks.handle(payload)  # must not raise: a trailing newline is not free text
        self.assertEqual(self.data("strand.open")[-1]["label"], "Claude subagent")

    def test_non_string_optional_fields_are_ignored(self):
        payload = fixture("subagent-start")
        payload["agent_type"] = {"nested": "value"}
        self.hooks.handle(payload)
        self.assertEqual(self.data("strand.open")[1]["label"], "Claude subagent")


class PrivacyTests(IngestCase):
    ALL = ("session-start", "subagent-start", "post-tool-use-main", "post-tool-use-subagent",
           "subagent-stop", "session-end", "unknown-attribute")

    def feed_all(self):
        for name in self.ALL:
            self.hooks.handle(fixture(name))

    def test_no_dropped_value_or_raw_identifier_reaches_the_store_or_the_inventory(self):
        self.feed_all()
        blob = json.dumps(self.events()) + json.dumps(self.hooks.dropped_names())
        for forbidden in (SENTINEL, "session-fixture-1", "agent-fixture-1", "toolu-fixture", "prompt-1",
                          "model-fixture", "transcript.jsonl"):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, blob)

    def test_identifiers_are_salted_hex_that_differs_across_sessions(self):
        self.hooks.handle(fixture("subagent-start"))
        other = HookIngest(LoomStore())
        other.handle(fixture("subagent-start"))
        mine = [item["strandId"] for item in self.data("strand.open")]
        theirs = [event["data"]["strandId"] for event in other.store.replay() if event["kind"] == "strand.open"]
        self.assertTrue(all(len(value) == 16 and set(value) <= set("0123456789abcdef") for value in mine))
        self.assertTrue(set(mine).isdisjoint(theirs))

    def test_same_salt_gives_the_same_identifiers(self):
        first, second = HookIngest(LoomStore(), salt=b"s" * 16), HookIngest(LoomStore(), salt=b"s" * 16)
        for hooks in (first, second):
            hooks.handle(fixture("subagent-start"))
        ids = [[e["data"]["strandId"] for e in h.store.replay() if e["kind"] == "strand.open"] for h in (first, second)]
        self.assertEqual(ids[0], ids[1])

    def test_dropped_names_cover_every_receipt_name_outside_the_allowlist(self):
        self.feed_all()
        receipt = json.loads(RECEIPT.read_text())["observed"]["hooks"]["payloadFieldNames"]
        observed = {name for event in ("PostToolUse", "SessionEnd", "SubagentStart", "SubagentStop")
                    for name in receipt[event]}
        expected = observed - set(view_hooks.ALLOWED_FIELDS)
        names = set(self.hooks.dropped_names())
        self.assertLessEqual(expected, names)
        self.assertTrue(names.isdisjoint(view_hooks.ALLOWED_FIELDS))

    def test_unknown_attribute_name_is_inventoried_and_its_value_is_not_kept(self):
        self.hooks.handle(fixture("unknown-attribute"))
        names = self.hooks.dropped_names()
        self.assertIn("brand_new_attribute", names)
        self.assertIn("brand_new_object.inner_name", names)
        self.assertNotIn(SENTINEL, json.dumps(self.events()))

    def test_inventory_is_bounded(self):
        payload = fixture("subagent-start")
        for index in range(400):
            payload[f"extra_{index}"] = 1
        self.hooks.handle(payload)
        self.assertEqual(len(self.hooks.dropped_names()), view_serve.MAX_INVENTORY_NAMES)

    def test_inventory_skips_long_unprintable_and_data_like_names(self):
        payload = fixture("post-tool-use-main")
        payload["x" * (view_serve.MAX_INVENTORY_NAME_LENGTH + 1)] = 1
        payload["bad\u202ename"] = 1
        payload["tool_response"] = {"/Users/someone/secret.txt": 1, "ENV-NAME=value": 2, "fine_name": 3}
        self.hooks.handle(payload)
        names = self.hooks.dropped_names()
        self.assertIn("tool_response.fine_name", names)
        self.assertIn("tool_response", names)
        self.assertEqual([name for name in names if "secret" in name or "ENV" in name or "bad" in name], [])
        self.assertTrue(all(len(name) <= view_serve.MAX_INVENTORY_NAME_LENGTH for name in names))

    def test_deeply_nested_and_wide_values_do_not_recurse_or_blow_up(self):
        payload = fixture("post-tool-use-main")
        nested = value = {}
        for _ in range(60):
            value["n"] = {}
            value = value["n"]
        payload["deep"] = nested
        payload["wide"] = [{"item": index} for index in range(5000)]
        self.hooks.handle(payload)
        self.assertIn("wide[].item", self.hooks.dropped_names())


class RefusalTests(IngestCase):
    def test_decision_events_and_unlisted_events_are_refused_with_403(self):
        for name in ("decision-pre-tool-use", "decision-permission-request", "decision-user-prompt-submit",
                     "decision-stop"):
            with self.subTest(name=name), self.assertRaises(IngestRefusal) as caught:
                self.hooks.handle(fixture(name))
            self.assertEqual(caught.exception.status, 403)
        payload = fixture("session-end")
        payload["hook_event_name"] = "SomeFutureEvent"
        with self.assertRaises(IngestRefusal) as caught:
            self.hooks.handle(payload)
        self.assertEqual(caught.exception.status, 403)
        self.assertEqual(self.events(), [])
        self.assertEqual(self.hooks.dropped_names(), [])

    def test_non_object_and_nameless_payloads_are_schema_violations(self):
        for payload in ([], "x", 3, None, {}, {"hook_event_name": 7}, {"hook_event_name": ["PostToolUse"]}):
            with self.subTest(payload=payload), self.assertRaises(IngestRefusal) as caught:
                self.hooks.handle(payload)
            self.assertEqual(caught.exception.status, 400)
        self.assertEqual(self.events(), [])

    def test_unrecognised_shapes_yield_one_shape_unpinned_gap_per_event_name(self):
        for _ in range(3):
            self.hooks.handle(fixture("subagent-start-without-agent-id"))
        gaps = self.data("observation.gap")
        self.assertEqual([gap["reason"] for gap in gaps], ["shape-unpinned"])
        self.assertEqual(kinds(self.events()), ["observation.gap"])
        broken = fixture("post-tool-use-main")
        broken["session_id"] = ""
        self.hooks.handle(broken)
        self.assertEqual(len(self.data("observation.gap")), 2)
        self.assertEqual(kinds(self.events()).count("strand.open"), 0)

    def test_a_refused_strand_open_by_the_store_cap_stores_nothing_for_that_strand(self):
        store = LoomStore(caps={"strands": 1})
        hooks = HookIngest(store)
        hooks.handle(fixture("subagent-start"))  # session takes the one slot; the subagent is refused
        kinds_seen = [event["kind"] for event in store.replay()]
        self.assertEqual(kinds_seen, ["strand.open", "observation.gap"])
        hooks.handle(fixture("post-tool-use-subagent"))
        hooks.handle(fixture("subagent-stop"))
        self.assertEqual([event["kind"] for event in store.replay()], kinds_seen)


class ServerCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.store = LoomStore()
        self.hooks = HookIngest(self.store)
        self.server = ViewServer(
            self.store, Path(self.tmp.name) / "run",
            ingest_handlers={view_serve.HOOK_PATH: self.hooks.handle}, names_inventory=self.hooks.dropped_names)
        thread = threading.Thread(target=self.server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.addCleanup(self.stop, thread)
        self.token = self.server.token_path.read_text()

    def stop(self, thread):
        self.server.shutdown()
        self.server.server_close()
        thread.join(5)

    def request(self, method, path, headers=None, body=None):
        headers = {"Host": f"127.0.0.1:{self.server.port}", **(headers or {})}
        connection = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=5)
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            return response.status, response.read()
        finally:
            connection.close()

    def post(self, payload):
        body = payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        return self.request("POST", view_serve.HOOK_PATH, {**JSON, "Authorization": f"Bearer {self.token}"}, body)


class HttpTests(ServerCase):
    def cookie(self):
        connection = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=5)
        try:
            connection.request("GET", self.server.open_url.split(str(self.server.port), 1)[1],
                               headers={"Host": f"127.0.0.1:{self.server.port}"})
            response = connection.getresponse()
            response.read()
            return response.getheader("Set-Cookie").split(";")[0]
        finally:
            connection.close()

    def stream(self, cookie):
        """The first retained events of `/events` as text (one `data:` line per stored event)."""
        wanted = self.store.stats()["count"]
        connection = http.client.HTTPConnection("127.0.0.1", self.server.port, timeout=5)
        try:
            connection.request("GET", "/events", headers={"Host": f"127.0.0.1:{self.server.port}",
                                                           "Last-Event-ID": "0", **cookie})
            response = connection.getresponse()
            lines = []
            while sum(line.startswith(b"data:") for line in lines) < wanted:
                lines.append(response.fp.readline())
            return b"".join(lines)
        finally:
            connection.close()

    def test_every_hook_response_body_is_empty_including_refusals(self):
        results = [self.post(fixture(name)) for name in (
            "session-start", "subagent-start", "post-tool-use-main", "subagent-stop", "session-end",
            "decision-pre-tool-use", "decision-user-prompt-submit", "decision-stop", "decision-permission-request",
            "unknown-attribute", "subagent-start-without-agent-id")]
        results += [self.post(b"not json"), self.post(b"[]"), self.post({})]
        self.assertEqual([body for _, body in results], [b""] * len(results))
        self.assertEqual([status for status, _ in results],
                         [200] * 5 + [403] * 4 + [200, 200] + [400] * 3)

    def test_no_sentinel_in_snapshot_events_or_any_response(self):
        bodies = []
        for name in ("subagent-start", "post-tool-use-subagent", "unknown-attribute", "subagent-stop",
                     "session-end", "decision-user-prompt-submit"):
            bodies.append(self.post(fixture(name))[1])
        cookie = {"Cookie": self.cookie()}
        bodies.append(self.request("GET", "/snapshot", cookie)[1])
        bodies.append(self.stream(cookie))
        blob = b"".join(bodies).decode("utf-8", "replace")
        self.assertNotIn(SENTINEL, blob)
        self.assertNotIn("agent-fixture-1", blob)
        snapshot = json.loads(self.request("GET", "/snapshot", cookie)[1])
        self.assertIn("brand_new_attribute", snapshot["droppedAttributeNames"])
        self.assertIn("tool_input.command", snapshot["droppedAttributeNames"])

    def test_missing_or_wrong_token_is_404_without_state_change(self):
        body = json.dumps(fixture("subagent-start")).encode()
        self.assertEqual(self.request("POST", view_serve.HOOK_PATH, JSON, body)[0], 404)
        self.assertEqual(self.request("POST", view_serve.HOOK_PATH, {**JSON, "Authorization": "Bearer wrong"}, body)[0], 404)
        self.assertEqual(self.store.stats()["headSeq"], 0)


class ContractTests(unittest.TestCase):
    """The pinned allowlist in the contract agrees with the receipt and with the code."""

    def hook_line(self):
        text = CONTRACT.read_text()
        start = text.index("- Claude Code hooks:")
        return text[start:text.index("\n- ", start + 3)]

    def otel_line(self):
        text = CONTRACT.read_text()
        start = text.index("- Claude Code OpenTelemetry:")
        return text[start:text.index("\n- ", start + 3)]

    def test_hook_allowlist_in_the_contract_is_the_code_allowlist(self):
        line = self.hook_line()
        for name in view_hooks.ALLOWED_FIELDS:
            self.assertIn(f"`{name}`", line)
        for event in view_hooks.OBSERVATIONAL_EVENTS:
            self.assertIn(f"`{event}`", line)

    def test_every_allowed_field_was_observed_in_the_receipt(self):
        receipt = json.loads(RECEIPT.read_text())["observed"]["hooks"]["payloadFieldNames"]
        observed = {name for names in receipt.values() for name in names}
        self.assertLessEqual(set(view_hooks.ALLOWED_FIELDS), observed)

    def test_opentelemetry_list_names_no_agent_or_parent_agent_id(self):
        allowlist = self.otel_line().partition("Host verification")[0]
        self.assertIn("`session.id`", allowlist)
        self.assertNotIn("agent_id", allowlist)
        self.assertNotIn("parent_agent_id", allowlist)

    def test_session_start_is_not_relied_upon(self):
        self.assertIn("not delivered", self.hook_line())


if __name__ == "__main__":
    unittest.main()
