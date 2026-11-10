# SPDX-License-Identifier: AGPL-3.0-only
"""Offline controls for the SPEC-050/T005 hook and plugin adapters (doubles only)."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import unittest

from agent_braid import harness_hooks as hh
from agent_braid.system_one import canonical

MODULE = Path(hh.__file__)


def original():
    return {"origin": "original", "file": None, "revision": None, "sha256": None,
            "terms": None, "noticesRetained": None, "modificationNotice": None}


def entry(hook_id, events=("PreToolUse",), priority=10, on_failure="ignore"):
    return {"id": hook_id, "events": list(events), "priority": priority,
            "onFailure": on_failure}


def make_spec(**over):
    value = {
        "format": hh.SPEC_FORMAT, "hooksetId": "demo-hooks", "version": 1,
        "componentClass": "C6", "host": "claude", "effectClass": "E0",
        "entries": [entry("a-first", priority=1), entry("b-second", priority=2)],
        "limits": {"maxEvents": 8, "maxDispatches": 16, "maxDepth": 2, "timeoutMs": 100,
                   "maxPayloadBytes": 256},
        "provenance": original(), "executionAuthorization": False}
    value.update(over)
    return value


def compile_spec(value):
    return hh.compile_hookset(json.dumps(value).encode(),
                              expected_input_sha256=sha256(canonical(value)).hexdigest())


def ev(event_id, seq, event="PreToolUse", payload=None):
    return {"eventId": event_id, "seq": seq, "event": event,
            "payload": payload if payload is not None else {"tool": "read"}}


def allow(_ctx, _event):
    return {"decision": "allow", "note": ""}


def deny(_ctx, _event):
    return {"decision": "deny", "note": "no"}


class FakeClock:
    def __init__(self, step=0):
        self.now, self.step = 0, step

    def __call__(self):
        self.now += self.step
        return self.now


def run(hookset, events, handlers, ledger=None, **kw):
    return hh.run_events(hookset, events, handlers=handlers,
                         ledger=hh.ReplayLedger() if ledger is None else ledger, **kw)


class Base(unittest.TestCase):
    def refuses(self, reason, fn, *args, **kwargs):
        with self.assertRaises(hh.ProfileError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)

    def refuses_spec(self, reason, **over):
        self.refuses(reason, compile_spec, make_spec(**over))

    def hookset(self, **over):
        return compile_spec(make_spec(**over))

    def statuses(self, result, index=0):
        return {h["hookId"]: (h["status"], h["reason"]) for h in
                result.events[index]["hooks"]}


class MatrixTests(Base):
    def test_matrices_are_independent_per_host(self):
        claude, codex = hh.matrix_record("claude"), hh.matrix_record("codex")
        self.assertEqual(claude["modeled"], ["PostToolUse", "PreToolUse", "SessionStart", "Stop"])
        self.assertEqual(codex["modeled"], [])
        self.assertIsNone(codex["observedBuild"])
        for record in (claude, codex):
            self.assertEqual(record["qualification"], "unqualified")
            self.assertEqual(record["observation"], "modeled-not-observed")
            self.assertIs(record["executionAuthorization"], False)
        self.assertEqual(hh.event_status("claude", "PreCompact"), "unavailable")
        self.assertEqual(hh.event_status("codex", "PreToolUse"), "unavailable")
        self.assertEqual(hh.event_status("claude", "Nope"), "unknown")

    def test_verify_matrix_roundtrip_and_forgeries(self):
        raw = canonical(hh.matrix_record("claude"))
        self.assertEqual(hh.verify_matrix(raw, expected_sha256=hh.matrix_sha256("claude"))
                         ["host"], "claude")
        for mutate in (
                lambda m: m["modeled"].append("PreCompact"),
                lambda m: m.update(qualification="qualified"),
                lambda m: m.update(observation="observed"),
                lambda m: m.update(executionAuthorization=True),
                lambda m: m.update(host="codex"),
                lambda m: m.update(extra=1)):
            forged = hh.matrix_record("claude")
            mutate(forged)
            forged_raw = canonical(forged)
            self.refuses("matrix-forged", hh.verify_matrix, forged_raw,
                         expected_sha256=sha256(forged_raw).hexdigest())
        self.refuses("matrix-drift", hh.verify_matrix, raw, expected_sha256="0" * 64)
        self.refuses("invalid-expected-hash", hh.verify_matrix, raw, expected_sha256="x")

    def test_matrices_stay_independent(self):
        for event in hh.EVENT_VOCAB:
            self.assertEqual(hh.event_status("codex", event), "unavailable")
        self.assertNotEqual(hh.matrix_sha256("claude"), hh.matrix_sha256("codex"))

    def test_codex_matrix_cannot_borrow_claude_events(self):
        forged = hh.matrix_record("codex")
        forged["modeled"] = list(hh.matrix_record("claude")["modeled"])
        raw = canonical(forged)
        self.refuses("matrix-forged", hh.verify_matrix, raw,
                     expected_sha256=sha256(raw).hexdigest())


class CompileTests(Base):
    def test_compiles_blocked_unauthorized_contract(self):
        hs = self.hookset()
        data = hs.to_dict()
        self.assertEqual(data["admission"], {"state": "blocked",
                                             "blocker": "no-containment-qualification"})
        self.assertIs(data["executionAuthorization"], False)
        self.assertEqual(data["matrixSha256"], hh.matrix_sha256("claude"))
        self.assertEqual(data["hostSupport"]["codex"]["qualification"], "unqualified")
        self.assertEqual(hh.verify_hookset(hs.canonical_bytes, expected_sha256=hs.sha256)
                         .sha256, hs.sha256)

    def test_plugin_class_is_also_blocked(self):
        hs = self.hookset(componentClass="C7", entries=[
            entry("p-one", ("PostToolUse", "PreToolUse"))])
        self.assertEqual(hs.data["admission"]["state"], "blocked")

    def test_codex_refused_not_installed(self):
        self.refuses_spec("host-refused", host="codex")

    def test_unavailable_and_unknown_events_cannot_be_declared(self):
        self.refuses_spec("event-unavailable", entries=[entry("a", ("PreCompact",))])
        self.refuses_spec("event-unavailable", entries=[entry("a", ("PermissionRequest",))])
        self.refuses_spec("event-unknown", entries=[entry("a", ("Bogus",))])

    def test_hook_class_takes_exactly_one_event(self):
        self.refuses_spec("invalid-entry",
                          entries=[entry("a", ("PostToolUse", "PreToolUse"))])

    def test_negative_spec_controls(self):
        self.refuses_spec("excluded-effect", effectClass="E5")
        self.refuses_spec("invalid-effect", effectClass="E9")
        self.refuses_spec("unknown-class", componentClass="C5")
        self.refuses_spec("unsupported-profile", executionAuthorization=True)
        self.refuses_spec("unsupported-version", format="braid-harness-hooks-spec/v0.2")
        self.refuses_spec("invalid-version", version=2)
        self.refuses_spec("invalid-entry", entries=[])
        self.refuses_spec("invalid-entry", entries=[entry("a", priority=-1)])
        self.refuses_spec("invalid-entry", entries=[entry("a", on_failure="allow")])
        self.refuses_spec("invalid-entry", entries=[entry("bad id")])
        self.refuses_spec("invalid-entry", entries=[
            {**entry("a"), "command": "rm -rf /"}])
        self.refuses_spec("duplicate-or-unordered-inventory",
                          entries=[entry("b"), entry("a")])
        self.refuses_spec("duplicate-or-unordered-inventory",
                          entries=[entry("a"), entry("a")])
        self.refuses_spec("path-alias", entries=[entry("A"), entry("a")])
        self.refuses_spec("inventory-budget-exceeded",
                          entries=[entry(f"h{i:02d}") for i in range(17)])
        self.refuses_spec("limits-exceed-ceiling", limits={**make_spec()["limits"],
                                                           "maxDepth": 3})
        self.refuses_spec("limits-exceed-ceiling", limits={**make_spec()["limits"],
                                                           "timeoutMs": 5000})
        self.refuses_spec("invalid-limits", limits={"maxEvents": 1})
        self.refuses_spec("invalid-provenance", provenance={"origin": "adapted"})

    def test_extra_spec_key_for_tool_loop_changes_refused(self):
        self.refuses("invalid-profile", compile_spec, {**make_spec(), "toolLoop": []})

    def test_input_drift_and_parse_controls(self):
        raw = json.dumps(make_spec()).encode()
        self.refuses("input-drift", hh.compile_hookset, raw, expected_input_sha256="0" * 64)
        self.refuses("invalid-expected-hash", hh.compile_hookset, raw,
                     expected_input_sha256="abc")
        self.refuses("invalid-json", hh.compile_hookset, b"{",
                     expected_input_sha256="0" * 64)

    def test_parse_rejects_tampered_contract(self):
        def tampered(mutate):
            data = self.hookset().to_dict()
            mutate(data)
            return json.dumps(data).encode()
        for reason, mutate in (
                ("admission-mismatch", lambda d: d["admission"].update(state="enabled")),
                ("admission-mismatch", lambda d: d["admission"].update(state="implemented",
                                                                       blocker=None)),
                ("unsupported-profile", lambda d: d.update(executionAuthorization=True)),
                ("matrix-forged", lambda d: d.update(matrixSha256="1" * 64)),
                ("host-build-drift", lambda d: d["hostSupport"]["codex"].update(
                    qualification="qualified")),
                ("unsupported-profile", lambda d: d["policies"].update(event="x")),
                ("unsupported-version", lambda d: d.update(format="braid-harness-hooks/v0.9"))):
            self.refuses(reason, hh.parse_hookset, tampered(mutate))

    def test_verify_hookset_drift(self):
        hs = self.hookset()
        self.refuses("hookset-drift", hh.verify_hookset, hs.canonical_bytes,
                     expected_sha256="2" * 64)

    def test_contract_is_immutable(self):
        hs = self.hookset()
        with self.assertRaises(TypeError):
            hs.data["entries"][0]["id"] = "x"  # type: ignore[index]
        hs.to_dict()["entries"].clear()
        self.assertEqual(len(hs.data["entries"]), 2)


class DispatchTests(Base):
    def test_ordering_by_priority_then_id_and_event_order(self):
        calls = []

        def rec(name):
            def handler(_ctx, event):
                calls.append((name, event["eventId"]))
                return {"decision": "allow", "note": ""}
            return handler
        hs = self.hookset(entries=[entry("a-late", priority=5), entry("b-early", priority=1),
                                   entry("c-tie", priority=5)])
        result = run(hs, [ev("e1", 0), ev("e2", 1)],
                     {n: rec(n) for n in ("a-late", "b-early", "c-tie")})
        self.assertEqual(calls, [(n, e) for e in ("e1", "e2")
                                 for n in ("b-early", "a-late", "c-tie")])
        self.assertEqual([e["decision"] for e in result.events], ["allow", "allow"])
        self.assertIs(result.execution_authorization, False)
        self.assertEqual(result.admission["state"], "blocked")
        self.assertIs(result.native_execution, False)

    def test_deny_wins_and_hooks_all_run(self):
        result = run(self.hookset(), [ev("e1", 0)], {"a-first": deny, "b-second": allow})
        self.assertEqual(result.events[0]["decision"], "deny")
        self.assertEqual(self.statuses(result)["b-second"], ("ok", None))

    def test_only_subscribed_hooks_run(self):
        hs = self.hookset(entries=[entry("a-pre"), entry("b-post", ("PostToolUse",))])
        result = run(hs, [ev("e1", 0)], {"a-pre": allow, "b-post": deny})
        self.assertEqual(list(self.statuses(result)), ["a-pre"])
        self.assertEqual(result.events[0]["decision"], "allow")

    def test_unknown_unavailable_and_undeclared_events_rejected(self):
        hs = self.hookset()
        result = run(hs, [ev("e1", 0, "Bogus"), ev("e2", 0, "PreCompact"),
                          ev("e3", 0, "Stop"), ev("e4", 1)], {"a-first": allow})
        self.assertEqual([(e["status"], e["reason"]) for e in result.events], [
            ("rejected", "event-unknown"), ("rejected", "event-unavailable"),
            ("accepted", None), ("accepted", None)])
        self.assertEqual(list(result.events[2]["hooks"]), [])

    def test_event_order_enforced(self):
        ledger = hh.ReplayLedger()
        result = run(self.hookset(), [ev("e1", 1), ev("e2", 0), ev("e3", 0)],
                     {"a-first": allow}, ledger)
        self.assertEqual([(e["status"], e["reason"]) for e in result.events], [
            ("rejected", "event-order"), ("accepted", None), ("rejected", "event-order")])

    def test_replay_is_deduplicated_and_conflict_refused(self):
        ledger = hh.ReplayLedger()
        calls = []

        def handler(_ctx, event):
            calls.append(event["eventId"])
            return {"decision": "allow", "note": ""}
        hs = self.hookset()
        first = run(hs, [ev("e1", 0)], {"a-first": handler}, ledger)
        self.assertEqual(first.events[0]["status"], "accepted")
        again = run(hs, [ev("e1", 0), ev("e1", 1, payload={"tool": "write"}),
                         ev("e2", 1)], {"a-first": handler}, ledger)
        self.assertEqual([(e["status"], e["reason"]) for e in again.events], [
            ("duplicate", None), ("rejected", "replay-conflict"), ("accepted", None)])
        self.assertEqual(calls, ["e1", "e2"])
        self.assertNotEqual(first.ledger_sha256, again.ledger_sha256)

    def test_rejected_events_are_not_remembered(self):
        ledger = hh.ReplayLedger()
        run(self.hookset(), [ev("e1", 0, "Bogus")], {"a-first": allow}, ledger)
        self.assertEqual(ledger.size, 0)

    def test_ledger_bounded(self):
        ledger = hh.ReplayLedger()
        hs = self.hookset(limits={**make_spec()["limits"], "maxEvents": 8})
        for i in range(hh.MAX_LEDGER):
            ledger._remember(f"x{i}", "0" * 64)
        self.refuses("ledger-full", run, hs, [ev("e1", ledger.next_seq)],
                     {"a-first": allow}, ledger)

    def test_payload_and_event_shape_controls(self):
        hs = self.hookset()
        big = run(hs, [ev("e1", 0, payload={"k": "x" * 300})], {"a-first": allow})
        self.assertEqual(big.events[0]["reason"], "payload-budget-exceeded")
        for bad in (ev("e1", 0, payload={"bad key": 1}), ev("e1", 0, payload={"k": 1.5}),
                    ev("e1", 0, payload={"k": "\ud800"}), {**ev("e1", 0), "x": 1},
                    ev("bad id", 0), ev("e1", -1), ev("e1", True), "event"):
            self.refuses("invalid-event", run, hs, [bad], {"a-first": allow})
        self.refuses("event-budget-exceeded", run, hs,
                     [ev(f"e{i}", i) for i in range(9)], {"a-first": allow})
        self.refuses("invalid-event", run, hs, "nope", {"a-first": allow})

    def test_handler_set_controls(self):
        hs = self.hookset()
        self.refuses("handler-not-declared", run, hs, [ev("e1", 0)], {"zzz": allow})
        self.refuses("invalid-input", run, hs, [ev("e1", 0)], [allow])
        missing = run(hs, [ev("e1", 0)], {"a-first": allow})
        self.assertEqual(self.statuses(missing)["b-second"], ("failed", "handler-missing"))
        self.refuses("invalid-input", hh.run_events, hs, [ev("e1", 0)],
                     handlers={}, ledger=object())
        self.refuses("invalid-hookset", hh.run_events, object(), [], handlers={},
                     ledger=hh.ReplayLedger())

    def test_tampered_hookset_object_is_refused_at_dispatch(self):
        hs = self.hookset()
        data = hs.to_dict()
        data["effectClass"] = "E0"
        data["limits"]["maxDispatches"] = 10_000
        forged = hh.HookSet(hs.data, canonical(data))
        self.refuses("contract-drift", run, forged, [ev("e1", 0)], {"a-first": allow})
        data = hs.to_dict()
        data["limits"]["maxDispatches"] = 10_000
        forged = hh.HookSet(hh.freeze(data), canonical(data))
        self.refuses("limits-exceed-ceiling", run, forged, [ev("e1", 0)], {"a-first": allow})

    def test_result_with_extra_key_is_an_escalation_attempt(self):
        result = run(self.hookset(), [ev("e1", 0)],
                     {"a-first": lambda c, e: {"decision": "allow", "note": "", "x": 1}})
        self.assertEqual(self.statuses(result)["a-first"], ("failed", "escalation-attempt"))

    def test_context_cancelled_after_close_refused(self):
        captured = []

        def grab(ctx, _event):
            captured.append(ctx)
            return {"decision": "allow", "note": ""}
        run(self.hookset(), [ev("e1", 0)], {"a-first": grab})
        self.refuses("context-closed", captured[0].cancelled)

    def test_unsorted_event_lists_refused(self):
        self.refuses_spec("invalid-entry", componentClass="C7",
                          entries=[entry("a", ("PreToolUse", "PostToolUse"))])

    def test_non_e0_hookset_does_not_dispatch(self):
        hs = self.hookset(effectClass="E3")
        self.assertEqual(hs.data["admission"]["state"], "blocked")
        self.refuses("effect-blocked", run, hs, [ev("e1", 0)], {"a-first": allow})

    def test_receipt_hashes_bind_inputs(self):
        hs = self.hookset()
        one = run(hs, [ev("e1", 0)], {"a-first": allow, "b-second": allow})
        two = run(hs, [ev("e1", 0)], {"a-first": allow, "b-second": deny})
        self.assertEqual(one.hookset_sha256, hs.sha256)
        self.assertEqual(one.matrix_sha256, hh.matrix_sha256("claude"))
        self.assertNotEqual(one.events_sha256, two.events_sha256)
        data = one.to_dict()
        self.assertIs(data["executionAuthorization"], False)
        self.assertIs(data["nativeExecution"], False)
        json.dumps(data)
        with self.assertRaises(Exception):
            one.events[0]["decision"] = "x"  # type: ignore[index]


class IsolationTests(Base):
    def test_failure_does_not_cascade_to_other_hooks(self):
        def boom(_ctx, _event):
            raise RuntimeError("secret detail /etc/passwd")
        result = run(self.hookset(), [ev("e1", 0), ev("e2", 1)],
                     {"a-first": boom, "b-second": deny})
        for index in (0, 1):
            self.assertEqual(self.statuses(result, index), {
                "a-first": ("failed", "hook-failed"), "b-second": ("ok", None)})
        self.assertNotIn("passwd", json.dumps(result.to_dict()))
        self.assertEqual(result.events[0]["decision"], "deny")

    def test_failure_policy_ignore_vs_deny(self):
        def boom(_ctx, _event):
            raise ValueError
        ignore = run(self.hookset(), [ev("e1", 0)], {"a-first": boom, "b-second": allow})
        self.assertEqual(ignore.events[0]["decision"], "allow")
        closed = self.hookset(entries=[entry("a-first", on_failure="deny", priority=1),
                                       entry("b-second", priority=2)])
        denied = run(closed, [ev("e1", 0)], {"a-first": boom, "b-second": allow})
        self.assertEqual(denied.events[0]["decision"], "deny")

    def test_escalation_attempts_are_failures_not_applied(self):
        grants = [
            {"decision": "allow", "note": "", "grant": "all"},
            {"decision": "approve", "note": ""},
            {"decision": "permit", "note": ""},
            {"decision": "allow"},
            "allow",
        ]
        for result_value in grants:
            result = run(self.hookset(), [ev("e1", 0)],
                         {"a-first": lambda c, e, v=result_value: v, "b-second": allow})
            status = self.statuses(result)["a-first"]
            self.assertEqual(status[0], "failed", result_value)
            self.assertIn(status[1], ("escalation-attempt", "invalid-result"))
            self.assertNotIn("grant", json.dumps(result.to_dict()))

    def test_note_is_bounded_and_stored_as_hash(self):
        result = run(self.hookset(), [ev("e1", 0)],
                     {"a-first": lambda c, e: {"decision": "allow", "note": "x" * 300},
                      "b-second": lambda c, e: {"decision": "allow", "note": "hi"}})
        self.assertEqual(self.statuses(result)["a-first"], ("failed", "invalid-result"))
        row = result.events[0]["hooks"][1]
        self.assertEqual(row["noteSha256"], sha256(b"hi").hexdigest())
        self.assertNotIn("note", row)

    def test_hook_cannot_mutate_event_or_shared_state(self):
        shared = {"decision": "allow"}

        def mutate(_ctx, event):
            event["payload"]["tool"] = "write"
            return shared
        result = run(self.hookset(), [ev("e1", 0)], {"a-first": mutate, "b-second": allow})
        self.assertEqual(self.statuses(result)["a-first"], ("failed", "hook-failed"))

        seen = []

        def spy(_ctx, event):
            seen.append(event["payload"]["tool"])
            return {"decision": "allow", "note": ""}
        run(self.hookset(), [ev("e2", 0)], {"a-first": allow, "b-second": spy})
        self.assertEqual(seen, ["read"])

    def test_context_has_no_authority_surface(self):
        captured = []

        def grab(ctx, _event):
            captured.append(ctx)
            for name in ("exec", "fetch", "write", "read", "grant", "settings"):
                if hasattr(ctx, name):
                    raise AssertionError(name)
            return {"decision": "allow", "note": ""}
        result = run(self.hookset(), [ev("e1", 0)], {"a-first": grab, "b-second": allow})
        self.assertEqual(self.statuses(result)["a-first"], ("ok", None))
        self.refuses("context-closed", captured[0].emit, "Stop", {})
        self.assertEqual(result.teardown, {"closed": True, "contextsClosed": 2})

    def test_swallowed_context_refusal_still_fails(self):
        def swallow(ctx, _event):
            try:
                ctx.emit("PreCompact", {})
            except hh.ProfileError:
                pass
            return {"decision": "allow", "note": ""}
        result = run(self.hookset(), [ev("e1", 0)], {"a-first": swallow, "b-second": allow})
        self.assertEqual(self.statuses(result)["a-first"], ("failed", "event-unavailable"))

    def test_timeout_is_a_failure_and_isolated(self):
        clock = FakeClock(step=120_000_000)  # 120 ms per clock read, budget 100 ms
        result = run(self.hookset(), [ev("e1", 0)], {"a-first": allow, "b-second": allow},
                     clock=clock)
        self.assertTrue(all(s == ("failed", "timeout")
                            for s in self.statuses(result).values()))

    def test_dispatch_budget(self):
        hs = self.hookset(limits={**make_spec()["limits"], "maxDispatches": 3})
        result = run(hs, [ev("e1", 0), ev("e2", 1)], {"a-first": allow, "b-second": allow})
        self.assertEqual(self.statuses(result, 1), {
            "a-first": ("ok", None), "b-second": ("skipped", "dispatch-budget-exceeded")})
        self.assertEqual(result.dispatches, 3)

    def test_base_exception_propagates_after_teardown(self):
        def interrupt(_ctx, _event):
            raise KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            run(self.hookset(), [ev("e1", 0)], {"a-first": interrupt})


class EmitAndRecursionTests(Base):
    def chain(self, **over):
        return self.hookset(entries=[
            entry("a-pre", ("PreToolUse",), 1), entry("b-post", ("PostToolUse",), 1),
            entry("c-stop", ("Stop",), 1)], **over)

    def test_emitted_events_dispatch_depth_first(self):
        order = []

        def pre(ctx, _event):
            order.append("pre")
            ctx.emit("PostToolUse", {"tool": "read"})
            return {"decision": "allow", "note": ""}

        def post(_ctx, _event):
            order.append("post")
            return {"decision": "allow", "note": ""}
        result = run(self.chain(), [ev("e1", 0)], {"a-pre": pre, "b-post": post})
        self.assertEqual(order, ["pre", "post"])
        emitted = result.events[0]["emitted"]
        self.assertEqual([(e["event"], e["status"], e["depth"]) for e in emitted],
                         [("PostToolUse", "accepted", 1)])

    def test_recursion_loop_detected_and_isolated(self):
        calls = []

        def pre(ctx, _event):
            calls.append("pre")
            ctx.emit("PostToolUse", {})
            return {"decision": "allow", "note": ""}

        def post(ctx, _event):
            calls.append("post")
            ctx.emit("PreToolUse", {})
            return {"decision": "allow", "note": ""}
        result = run(self.chain(), [ev("e1", 0)], {"a-pre": pre, "b-post": post})
        self.assertEqual(calls, ["pre", "post"])
        inner = result.events[0]["emitted"][0]["emitted"][0]
        self.assertEqual(inner["hooks"][0]["status"], "failed")
        self.assertEqual(inner["hooks"][0]["reason"], "recursion-loop")

    def test_self_emit_loop(self):
        def pre(ctx, _event):
            ctx.emit("PreToolUse", {})
            return {"decision": "allow", "note": ""}
        result = run(self.chain(), [ev("e1", 0)], {"a-pre": pre})
        inner = result.events[0]["emitted"][0]
        self.assertEqual(inner["hooks"][0]["reason"], "recursion-loop")

    def test_depth_bound(self):
        hs = self.chain(limits={**make_spec()["limits"], "maxDepth": 1})

        def pre(ctx, _event):
            ctx.emit("PostToolUse", {})
            return {"decision": "allow", "note": ""}

        def post(ctx, _event):
            ctx.emit("Stop", {})
            return {"decision": "allow", "note": ""}
        result = run(hs, [ev("e1", 0)], {"a-pre": pre, "b-post": post})
        deepest = result.events[0]["emitted"][0]["emitted"][0]
        self.assertEqual((deepest["status"], deepest["reason"]),
                         ("rejected", "recursion-depth"))
        self.assertEqual(list(deepest["hooks"]), [])

    def test_emit_budget_and_validation(self):
        def spam(ctx, _event):
            for _ in range(hh.MAX_EMITS + 1):
                ctx.emit("Stop", {})
            return {"decision": "allow", "note": ""}
        result = run(self.chain(), [ev("e1", 0)], {"a-pre": spam})
        self.assertEqual(self.statuses(result)["a-pre"], ("failed", "emit-budget-exceeded"))

        def bad_payload(ctx, _event):
            ctx.emit("Stop", {"k": 1.5})
            return {"decision": "allow", "note": ""}
        result = run(self.chain(), [ev("e2", 0)], {"a-pre": bad_payload})
        self.assertEqual(self.statuses(result)["a-pre"], ("failed", "invalid-event"))

    def test_child_deny_and_cancel_propagate_to_the_parent(self):
        def pre(ctx, _event):
            ctx.emit("PostToolUse", {})
            return {"decision": "allow", "note": ""}
        result = run(self.chain(), [ev("e1", 0)], {"a-pre": pre, "b-post": deny})
        self.assertEqual(result.events[0]["decision"], "deny")
        state = {"flag": False}

        def post(_ctx, _event):
            state["flag"] = True
            return {"decision": "allow", "note": ""}
        result = run(self.chain(), [ev("e2", 0)], {"a-pre": pre, "b-post": post},
                     cancel=lambda: state["flag"])
        self.assertEqual(result.events[0]["emitted"][0]["decision"], "allow")
        self.assertFalse(result.events[0]["decision"] == "deny")

    def test_emits_of_a_refused_result_are_discarded(self):
        def pre(ctx, _event):
            ctx.emit("PostToolUse", {})
            return {"decision": "approve", "note": ""}
        result = run(self.chain(), [ev("e1", 0)], {"a-pre": pre, "b-post": deny})
        self.assertEqual(self.statuses(result)["a-pre"], ("failed", "escalation-attempt"))
        self.assertEqual(list(result.events[0]["emitted"]), [])
        self.assertEqual(result.events[0]["decision"], "allow")

    def test_emit_payload_budget(self):
        def pre(ctx, _event):
            ctx.emit("Stop", {"k": "x" * 300})
            return {"decision": "allow", "note": ""}
        result = run(self.chain(), [ev("e1", 0)], {"a-pre": pre})
        self.assertEqual(self.statuses(result)["a-pre"], ("failed", "payload-budget-exceeded"))

    def test_failed_hook_emits_are_discarded(self):
        def pre(ctx, _event):
            ctx.emit("PostToolUse", {})
            raise RuntimeError
        result = run(self.chain(), [ev("e1", 0)], {"a-pre": pre})
        self.assertEqual(list(result.events[0]["emitted"]), [])

    def test_emitted_events_unavailable_for_codex_matrix_style_names(self):
        def pre(ctx, _event):
            ctx.emit("Bogus", {})
            return {"decision": "allow", "note": ""}
        result = run(self.chain(), [ev("e1", 0)], {"a-pre": pre})
        self.assertEqual(self.statuses(result)["a-pre"], ("failed", "event-unknown"))


class CancellationTests(Base):
    def test_cancel_before_start_runs_nothing(self):
        called = []
        result = run(self.hookset(), [ev("e1", 0), ev("e2", 1)],
                     {"a-first": lambda c, e: called.append(1)}, cancel=lambda: True)
        self.assertEqual(called, [])
        self.assertEqual([e["status"] for e in result.events], ["cancelled", "cancelled"])
        self.assertTrue(result.cancelled)
        self.assertEqual(result.teardown["contextsClosed"], 0)

    def test_cancel_mid_event_skips_remaining_hooks_and_events(self):
        state = {"flag": False}

        def first(_ctx, _event):
            state["flag"] = True
            return {"decision": "allow", "note": ""}
        result = run(self.hookset(), [ev("e1", 0), ev("e2", 1)],
                     {"a-first": first, "b-second": allow}, cancel=lambda: state["flag"])
        self.assertEqual(self.statuses(result), {"a-first": ("ok", None),
                                                 "b-second": ("cancelled", None)})
        self.assertEqual(result.events[0]["decision"], "cancelled")
        self.assertEqual(result.events[1]["status"], "cancelled")
        self.assertEqual(result.teardown, {"closed": True, "contextsClosed": 1})

    def test_hook_observes_cancellation_through_context(self):
        state = {"flag": False, "seen": None}

        def watcher(ctx, _event):
            state["flag"] = True
            state["seen"] = ctx.cancelled()
            return {"decision": "allow", "note": ""}
        run(self.hookset(), [ev("e1", 0)], {"a-first": watcher},
            cancel=lambda: state["flag"])
        self.assertIs(state["seen"], True)

    def test_raising_cancel_probe_fails_closed(self):
        def probe():
            raise RuntimeError
        result = run(self.hookset(), [ev("e1", 0)], {"a-first": allow}, cancel=probe)
        self.assertTrue(result.cancelled)
        self.assertEqual(result.events[0]["status"], "cancelled")

    def test_deny_fails_closed_when_budget_skips_a_deny_on_failure_hook(self):
        hs = self.hookset(entries=[entry("a-burn", priority=1),
                                   entry("z-guard", priority=2, on_failure="deny")],
                          limits={**make_spec()["limits"], "maxDispatches": 1})
        result = run(hs, [ev("e1", 0)], {"a-burn": allow, "z-guard": deny})
        self.assertEqual(self.statuses(result)["z-guard"],
                         ("skipped", "dispatch-budget-exceeded"))
        self.assertEqual(result.events[0]["decision"], "deny")

    def test_deny_outranks_cancellation(self):
        state = {"flag": False}

        def deny_and_cancel(_ctx, _event):
            state["flag"] = True
            return {"decision": "deny", "note": ""}
        result = run(self.hookset(), [ev("e1", 0)],
                     {"a-first": deny_and_cancel, "b-second": allow},
                     cancel=lambda: state["flag"])
        self.assertEqual(result.events[0]["decision"], "deny")

    def test_cancelled_midway_event_can_be_retried(self):
        state = {"flag": False}
        ledger = hh.ReplayLedger()

        def first(_ctx, _event):
            state["flag"] = True
            return {"decision": "allow", "note": ""}
        run(self.hookset(), [ev("e1", 0)], {"a-first": first, "b-second": allow}, ledger,
            cancel=lambda: state["flag"])
        self.assertEqual(ledger.size, 0)
        again = run(self.hookset(), [ev("e1", 0)], {"a-first": allow, "b-second": allow},
                    ledger)
        self.assertEqual(again.events[0]["status"], "accepted")
        self.assertEqual(ledger.size, 1)

    def test_clock_error_mid_run_leaves_ledger_unchanged(self):
        ledger = hh.ReplayLedger()

        def bad_clock():
            raise RuntimeError
        with self.assertRaises(RuntimeError):
            run(self.hookset(), [ev("e1", 0)], {"a-first": allow}, ledger, clock=bad_clock)
        self.assertEqual((ledger.size, ledger.next_seq), (0, 0))
        run(self.hookset(), [ev("e1", 0)], {"a-first": allow}, ledger)
        self.assertEqual(ledger.size, 1)

    def test_reentrant_use_of_a_ledger_is_refused(self):
        ledger = hh.ReplayLedger()
        hs = self.hookset()
        inner = []

        def reenter(_ctx, _event):
            try:
                run(hs, [ev("e9", 0)], {"a-first": allow}, ledger)
            except hh.ProfileError as exc:
                inner.append(exc.reason)
            return {"decision": "allow", "note": ""}
        run(hs, [ev("e1", 0)], {"a-first": reenter}, ledger)
        self.assertEqual(inner, ["ledger-busy"])

    def test_handler_cannot_choose_its_failure_reason(self):
        def spoof(_ctx, _event):
            raise hh.ProfileError("matrix-forged")
        result = run(self.hookset(), [ev("e1", 0)], {"a-first": spoof, "b-second": allow})
        self.assertEqual(self.statuses(result)["a-first"], ("failed", "hook-failed"))

    def test_failed_hook_event_is_a_duplicate_on_retry(self):
        ledger = hh.ReplayLedger()

        def boom(_ctx, _event):
            raise RuntimeError
        hs = self.hookset()
        run(hs, [ev("e1", 0)], {"a-first": boom}, ledger)
        again = run(hs, [ev("e1", 0)], {"a-first": allow}, ledger)
        self.assertEqual(again.events[0]["status"], "duplicate")

    def test_cancelled_event_not_remembered(self):
        ledger = hh.ReplayLedger()
        run(self.hookset(), [ev("e1", 0)], {"a-first": allow}, ledger, cancel=lambda: True)
        self.assertEqual(ledger.size, 0)

    def test_non_callable_cancel_refused(self):
        self.refuses("invalid-input", run, self.hookset(), [ev("e1", 0)],
                     {"a-first": allow}, cancel=True)


class StructureTests(Base):
    def test_module_never_starts_processes_or_opens_resources(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                    for a in n.names}
        imported |= {n.module.split(".")[0] for n in ast.walk(tree)
                     if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
        self.assertFalse(imported & {"os", "subprocess", "socket", "urllib", "http", "shutil",
                                     "pathlib", "ctypes", "multiprocessing", "threading",
                                     "asyncio", "importlib", "pickle", "signal", "sys"})
        calls = {n.func.id for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertFalse(calls & {"open", "exec", "eval", "compile", "__import__"})

    def test_no_global_registry_exists(self):
        for name in vars(hh):
            self.assertFalse(name.upper() in {"REGISTRY", "HANDLERS", "HOOKS"} or
                             name.lower().startswith("register"), name)

    def test_nothing_in_the_module_can_be_enabled(self):
        for name in vars(hh):
            self.assertFalse(name.lower().startswith(("enable", "install", "activate")), name)


if __name__ == "__main__":
    unittest.main()
