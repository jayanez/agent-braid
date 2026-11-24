# SPDX-License-Identifier: AGPL-3.0-only
"""Offline controls for the SPEC-050/T004 allowlisted tool contracts and helpers."""
import ast
import inspect
import sys
import types
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
from pathlib import Path
import unittest

from agent_braid import harness_components as hc
from agent_braid import harness_tools as ht
from agent_braid.system_one import canonical, digest, freeze, thaw

MODULE = Path(ht.__file__)
NOTES = b"alpha beta gamma\n"
NOTES_PATH = "data/notes.txt"


def original():
    return {"origin": "original", "file": None, "revision": None, "sha256": None,
            "terms": None, "noticesRetained": None, "modificationNotice": None}


def make_spec(**over):
    value = {
        "format": ht.SPEC_FORMAT, "toolId": "count-words", "version": 1, "effectClass": "E2",
        "guidance": "Counts words in one inventoried note and writes a report.",
        "input": [{"name": "label", "type": "string", "max": 32}],
        "output": [{"name": "count", "type": "integer", "max": 1000},
                   {"name": "ok", "type": "boolean", "max": None}],
        "reads": [{"path": NOTES_PATH, "sha256": sha256(NOTES).hexdigest(),
                   "sizeBytes": len(NOTES)}],
        "writes": ["out/report.txt"],
        "limits": {"maxInputBytes": 512, "maxOutputBytes": 256, "maxOps": 4,
                   "maxWriteBytes": 64, "timeoutMs": 1000},
        "provenance": original(), "executionAuthorization": False}
    value.update(over)
    return value


def compile_spec(value):
    return ht.compile_contract(json.dumps(value).encode(),
                               expected_input_sha256=sha256(canonical(value)).hexdigest())


def helper(ctx, data):
    words = len(ctx.read(NOTES_PATH).split())
    ctx.write("out/report.txt", f"{data['label']}:{words}".encode())
    return {"count": words, "ok": True}


def checker(data, output, artifacts):
    return (output["count"] == 3 and output["ok"] is True and
            artifacts["out/report.txt"] == f"{data['label']}:3".encode())


class FakeClock:
    def __init__(self, step=0):
        self.now, self.step = 0, step

    def __call__(self):
        self.now += self.step
        return self.now


def allowlist_for(*specs):
    return ht.compile_allowlist([compile_spec(s) for s in specs])


class ToolContractTests(unittest.TestCase):
    def refuses(self, reason, fn, *args, **kwargs):
        with self.assertRaises(ht.ProfileError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)

    def refuses_spec(self, reason, **over):
        self.refuses(reason, compile_spec, make_spec(**over))

    def refuses_contract(self, reason, mutate):
        data = compile_spec(make_spec()).to_dict()
        mutate(data)
        self.refuses(reason, ht.parse_contract, canonical(data))

    def run_tool(self, allowlist=None, *, tool="count-words", data=None, helpers=None,
                 checkers=None, files=None, clock=None):
        return ht.run_tool(
            allowlist or allowlist_for(make_spec()), tool,
            data if data is not None else {"label": "n"},
            helpers=helpers if helpers is not None else {"count-words": helper},
            checkers=checkers if checkers is not None else {"count-words": checker},
            files=files if files is not None else {NOTES_PATH: NOTES},
            clock=clock or FakeClock())

    # --- positive controls -------------------------------------------------
    def test_compiles_immutable_implemented_contract_without_authority(self):
        contract = compile_spec(make_spec())
        data = contract.to_dict()
        self.assertEqual(data["format"], "braid-harness-tool/v0.1")
        self.assertEqual(data["componentClass"], "C5")
        self.assertEqual(data["admission"], {"state": "implemented", "blocker": None})
        self.assertIs(data["executionAuthorization"], False)
        self.assertEqual(data["hostSupport"]["claude"]["qualification"], "unqualified")
        with self.assertRaises(FrozenInstanceError):
            contract.data = {}
        with self.assertRaises(TypeError):
            contract.data["admission"]["state"] = "enabled"
        data["admission"]["state"] = "enabled"
        self.assertEqual(contract.data["admission"]["state"], "implemented")
        again = compile_spec(make_spec())
        self.assertEqual(again.canonical_bytes, contract.canonical_bytes)
        self.assertEqual(ht.parse_contract(contract.canonical_bytes).sha256, contract.sha256)
        self.assertEqual(ht.verify_contract(contract.canonical_bytes,
                                            expected_sha256=contract.sha256).sha256,
                         contract.sha256)

    def test_runs_helper_with_independent_check_and_teardown(self):
        allow = allowlist_for(make_spec())
        result = self.run_tool(allow)
        self.assertEqual(result.output, {"count": 3, "ok": True})
        self.assertEqual(result.artifacts, {"out/report.txt": sha256(b"n:3").hexdigest()})
        self.assertEqual(result.ops, 2)
        self.assertEqual(result.teardown, {"closed": True, "artifactsRemoved": 1})
        self.assertIs(result.execution_authorization, False)
        self.assertEqual(result.input_sha256, digest({"label": "n"}))
        self.assertEqual(result.output_sha256, digest({"count": 3, "ok": True}))
        self.assertEqual(result.contract_sha256, allow.contracts["count-words"].sha256)
        self.assertEqual(result.allowlist_sha256, allow.sha256)
        self.assertIs(result.to_dict()["executionAuthorization"], False)
        with self.assertRaises(FrozenInstanceError):
            result.ops = 0
        self.assertEqual(self.run_tool(allow).output_sha256, result.output_sha256)

    def test_e0_and_e1_effect_classes_run_within_their_declaration(self):
        e0 = make_spec(toolId="pure", effectClass="E0", reads=[], writes=[],
                       limits={**make_spec()["limits"], "maxWriteBytes": 0})
        allow = allowlist_for(e0)
        result = self.run_tool(allow, tool="pure", data={"label": "x"},
                               helpers={"pure": lambda ctx, d: {"count": len(d["label"]),
                                                                 "ok": True}},
                               checkers={"pure": lambda d, o, a: o["count"] == 1})
        self.assertEqual(result.output["count"], 1)
        e1 = make_spec(toolId="reader", effectClass="E1", writes=[],
                       limits={**make_spec()["limits"], "maxWriteBytes": 0})
        result = self.run_tool(
            allowlist_for(e1), tool="reader",
            helpers={"reader": lambda ctx, d: {"count": len(ctx.read(NOTES_PATH).split()),
                                                "ok": True}},
            checkers={"reader": lambda d, o, a: o["count"] == 3 and a == {}})
        self.assertEqual(result.artifacts, {})

    def test_allowlist_round_trip_names_exact_contracts(self):
        specs = [make_spec(), make_spec(toolId="alpha-tool")]
        contracts = [compile_spec(s) for s in specs]
        allow = ht.compile_allowlist(contracts)
        self.assertEqual([r["toolId"] for r in allow.data["tools"]],
                         ["alpha-tool", "count-words"])
        again = ht.verify_allowlist(allow.canonical_bytes, expected_sha256=allow.sha256,
                                    contract_raws=[c.canonical_bytes for c in contracts])
        self.assertEqual(again.sha256, allow.sha256)
        self.assertIs(allow.data["executionAuthorization"], False)

    # --- negative controls: allowlist and registration ---------------------
    def test_tool_not_in_allowlist_is_refused(self):
        self.refuses("tool-not-allowlisted", self.run_tool, tool="other")
        # An allowlisted contract does not make an arbitrary name runnable.
        self.refuses("tool-not-allowlisted", self.run_tool, tool="Count-Words")

    def test_unlisted_helper_is_refused_not_auto_registered(self):
        self.refuses("helper-not-allowlisted", self.run_tool,
                     helpers={"count-words": helper, "new-exe": helper})

    def test_missing_helper_or_checker_is_refused(self):
        self.refuses("helper-missing", self.run_tool, helpers={})
        self.refuses("checker-missing", self.run_tool, checkers={})
        self.refuses("helper-missing", self.run_tool, helpers={"count-words": "ls"})

    def test_checker_must_be_independent_and_exactly_true(self):
        self.refuses("checker-not-independent", self.run_tool,
                     checkers={"count-words": helper})
        for verdict in (False, None, 1, "yes"):
            self.refuses("check-failed", self.run_tool,
                         checkers={"count-words": lambda d, o, a, v=verdict: v})

        def raising(data, output, artifacts):
            raise RuntimeError("boom /secret/path")
        self.refuses("checker-raised", self.run_tool, checkers={"count-words": raising})

    def test_wrong_output_fails_the_independent_check(self):
        def liar(ctx, data):
            ctx.write("out/report.txt", b"n:3")
            return {"count": 99, "ok": True}
        self.refuses("check-failed", self.run_tool, helpers={"count-words": liar})

    # --- negative controls: effects and paths ------------------------------
    def test_undeclared_effects_are_refused_at_run_time(self):
        e0 = make_spec(toolId="pure", effectClass="E0", reads=[], writes=[],
                       limits={**make_spec()["limits"], "maxWriteBytes": 0})
        allow = allowlist_for(e0)
        for attempt in (lambda c: c.read(NOTES_PATH), lambda c: c.write("out/a.txt", b"x")):
            self.refuses("undeclared-effect", self.run_tool, allow, tool="pure",
                         helpers={"pure": lambda c, d, a=attempt: a(c)},
                         checkers={"pure": checker})
        # Child process and network handles are never reachable, even for E2.
        for name in ("exec", "fetch"):
            self.refuses("undeclared-effect", self.run_tool,
                         helpers={"count-words": lambda c, d, n=name: getattr(c, n)("x")})
        e1 = make_spec(toolId="reader", effectClass="E1", writes=[],
                       limits={**make_spec()["limits"], "maxWriteBytes": 0})
        self.refuses("undeclared-effect", self.run_tool, allowlist_for(e1), tool="reader",
                     helpers={"reader": lambda c, d: c.write("out/report.txt", b"x")},
                     checkers={"reader": checker})

    def test_contract_declarations_may_not_exceed_the_effect_class(self):
        self.refuses_spec("undeclared-effect", effectClass="E0")
        self.refuses_spec("undeclared-effect", effectClass="E1")
        self.refuses_spec("undeclared-effect", effectClass="E2", writes=[],
                          limits={**make_spec()["limits"], "maxWriteBytes": 0})

    def test_e5_is_refused_and_e3_e4_stay_blocked(self):
        self.refuses_spec("excluded-effect", effectClass="E5")
        self.refuses_spec("invalid-effect", effectClass="E9")
        for effect in ("E3", "E4"):
            allow = allowlist_for(make_spec(effectClass=effect))
            contract = allow.contracts["count-words"]
            self.assertEqual(contract.data["admission"],
                             {"state": "blocked", "blocker": "effects-not-adopted"})
            called = []
            self.refuses("effect-blocked", self.run_tool, allow,
                         helpers={"count-words": lambda c, d: called.append(1)})
            self.assertEqual(called, [])

    def test_path_escape_and_uninventoried_paths_are_refused(self):
        for bad in ("../etc/passwd", "/etc/passwd", "data/../notes.txt", "data//notes.txt",
                    "data\\notes.txt", "data/notes.txt\x00"):
            self.refuses("invalid-path", self.run_tool, helpers={
                "count-words": lambda c, d, b=bad: c.read(b)})
        # In the files double but not in the positive inventory.
        files = {NOTES_PATH: NOTES, "data/other.txt": b"secret"}
        self.refuses("path-outside-inventory", self.run_tool, files=files, helpers={
            "count-words": lambda c, d: c.read("data/other.txt")})
        self.refuses("path-outside-inventory", self.run_tool, helpers={
            "count-words": lambda c, d: c.write("out/elsewhere.txt", b"x")})
        self.refuses("invalid-path", self.run_tool, helpers={
            "count-words": lambda c, d: c.write("out/../escape.txt", b"x")})

    def test_contract_paths_must_be_safe_and_positive(self):
        for bad, reason in (("../x.txt", "invalid-path"), ("/abs.txt", "invalid-path"),
                            ("tests/x.txt", "protected-component"),
                            ("tools/x.txt", "protected-component"),
                            (".hidden/x.txt", "protected-component"),
                            ("hooks/x.txt", "protected-component"),
                            ("out/in.txt", "path-outside-surface"),
                            ("OUT/in.txt", "path-outside-surface")):
            with self.subTest(read=bad):
                reads = [{"path": bad, "sha256": "1" * 64, "sizeBytes": 1}]
                self.refuses_spec(reason, reads=reads)
        for bad, reason in (("data/x.txt", "path-outside-surface"),
                            ("out/x.py", "path-outside-surface"),
                            ("out", "path-outside-surface"),
                            ("out/Tools/../x.txt", "invalid-path")):
            with self.subTest(write=bad):
                self.refuses_spec(reason, writes=[bad])
        self.refuses_spec("protected-component", writes=["out/hooks/x.txt"])
        self.refuses_spec("path-alias", writes=["out/Report.txt", "out/report.txt"])
        self.refuses_spec("duplicate-or-unordered-inventory",
                          writes=["out/b.txt", "out/a.txt"])

    def test_resource_drift_and_missing_files_are_refused(self):
        self.refuses("resource-drift", self.run_tool, files={NOTES_PATH: NOTES + b"x"})
        self.refuses("resource-missing", self.run_tool, files={})
        self.refuses("resource-missing", self.run_tool, files={NOTES_PATH: "text"})

    # --- negative controls: artifacts, bounds, teardown --------------------
    def test_unexpected_missing_and_duplicate_artifacts_are_refused(self):
        def forgets(ctx, data):
            ctx.read(NOTES_PATH)
            return {"count": 3, "ok": True}
        self.refuses("artifact-missing", self.run_tool, helpers={"count-words": forgets})

        def twice(ctx, data):
            ctx.write("out/report.txt", b"a")
            ctx.write("out/report.txt", b"b")
        self.refuses("artifact-exists", self.run_tool, helpers={"count-words": twice})
        self.refuses("invalid-artifact", self.run_tool, helpers={
            "count-words": lambda c, d: c.write("out/report.txt", "text")})

    def test_write_and_ops_budgets_are_enforced(self):
        self.refuses("write-budget-exceeded", self.run_tool, helpers={
            "count-words": lambda c, d: c.write("out/report.txt", b"x" * 65)})
        spec = make_spec(limits={**make_spec()["limits"], "maxOps": 1})
        self.refuses("ops-budget-exceeded", self.run_tool, allowlist_for(spec))

    def test_output_over_bound_or_malformed_is_refused(self):
        spec = make_spec(
            output=[{"name": "text", "type": "string", "max": 4000}],
            limits={**make_spec()["limits"], "maxOutputBytes": 64})
        allow = allowlist_for(spec)

        def run(out):
            return self.run_tool(
                allow, helpers={"count-words": lambda c, d: (
                    c.read(NOTES_PATH), c.write("out/report.txt", b"x"), out)[-1]},
                checkers={"count-words": lambda d, o, a: True})
        self.assertEqual(run({"text": "ok"}).output["text"], "ok")
        self.refuses("output-budget-exceeded", run, {"text": "x" * 100})
        self.refuses("output-budget-exceeded", self.run_tool, helpers={
            "count-words": lambda c, d: (c.write("out/report.txt", b"x"),
                                         {"count": 10 ** 6, "ok": True})[1]})
        for bad in ({"count": 3}, {"count": 3, "ok": True, "extra": 1},
                    {"count": True, "ok": True}, {"count": "3", "ok": True},
                    {"count": 3, "ok": 1}, [1], None, "text"):
            self.refuses("invalid-output", self.run_tool, helpers={
                "count-words": lambda c, d, b=bad: (c.write("out/report.txt", b"x"), b)[1]})

    def test_input_is_typed_and_bounded(self):
        for bad in ({}, {"label": 1}, {"label": "n", "extra": 1}, {"label": None}):
            self.refuses("invalid-input", self.run_tool, data=bad)
        self.refuses("invalid-input", self.run_tool, data=["label"])
        self.refuses("input-budget-exceeded", self.run_tool, data={"label": "x" * 33})
        self.refuses("input-budget-exceeded", self.run_tool, data={"label": "x" * 600})

    def test_deadline_is_enforced_on_the_injected_clock(self):
        # 1000 ms budget; each clock read advances 400 ms.
        step = 400_000_000
        self.refuses("timeout", self.run_tool, clock=FakeClock(step))
        slow = make_spec(limits={**make_spec()["limits"], "timeoutMs": 5000})
        self.assertEqual(self.run_tool(allowlist_for(slow), clock=FakeClock(step)).ops, 2)

    def test_helper_exceptions_are_sanitized_and_teardown_still_runs(self):
        leaked = []

        def boom(ctx, data):
            leaked.append(ctx)
            ctx.write("out/report.txt", b"partial")
            raise RuntimeError("secret /Users/someone/key")
        with self.assertRaises(ht.ProfileError) as caught:
            self.run_tool(helpers={"count-words": boom})
        self.assertEqual(caught.exception.reason, "helper-failed")
        self.assertNotIn("secret", str(caught.exception))
        self.assertIsNone(caught.exception.__cause__)
        ctx = leaked[0]
        self.assertEqual(ctx.artifact_count, 0)
        self.refuses("context-closed", ctx.read, NOTES_PATH)
        self.refuses("context-closed", ctx.write, "out/report.txt", b"x")

    def test_teardown_runs_after_refusals_and_a_kept_context_is_dead(self):
        kept = []

        def keeps(ctx, data):
            kept.append(ctx)
            ctx.write("out/report.txt", b"n:3")
            return {"count": 3, "ok": True}
        self.run_tool(helpers={"count-words": keeps})
        self.assertEqual(kept[0].artifact_count, 0)
        self.refuses("context-closed", kept[0].read, NOTES_PATH)
        # Independent-check failure also tears down.
        self.refuses("check-failed", self.run_tool, helpers={"count-words": keeps},
                     checkers={"count-words": lambda d, o, a: False})
        self.assertEqual(kept[1].artifact_count, 0)

    def test_checker_receives_immutable_views(self):
        seen = {}

        def probe(data, output, artifacts):
            seen.update(data=data, output=output)
            with self.assertRaises(TypeError):
                output["count"] = 0
            with self.assertRaises(TypeError):
                data["label"] = "z"
            return True
        result = self.run_tool(checkers={"count-words": probe})
        self.assertEqual(result.output["count"], 3)
        self.assertEqual(seen["output"]["count"], 3)

    def test_helper_cannot_mutate_the_input_record(self):
        def mutator(ctx, data):
            data["label"] = "evil"
        self.refuses("helper-failed", self.run_tool, helpers={"count-words": mutator})

    def test_helper_cannot_swallow_a_context_refusal(self):
        attempts = {
            "path-outside-inventory": lambda c: c.read("data/other.txt"),
            "invalid-path": lambda c: c.read("../etc/passwd"),
            "undeclared-effect": lambda c: c.exec("rm -rf /"),
            "undeclared-effect2": lambda c: c.fetch("http://x"),
            "path-outside-inventory2": lambda c: c.write("out/other.txt", b"x"),
        }
        for name, attempt in attempts.items():
            def sneaky(ctx, data, attempt=attempt):
                try:
                    attempt(ctx)
                except ht.ProfileError:
                    pass
                return helper(ctx, data)
            with self.subTest(name=name):
                with self.assertRaises(ht.ProfileError) as caught:
                    self.run_tool(helpers={"count-words": sneaky},
                                  files={NOTES_PATH: NOTES, "data/other.txt": b"s"})
                self.assertEqual(caught.exception.reason, name.rstrip("2"))
        spec = make_spec(limits={**make_spec()["limits"], "maxOps": 2})

        def over_budget(ctx, data):
            try:
                ctx.read(NOTES_PATH), ctx.read(NOTES_PATH), ctx.read(NOTES_PATH)
            except ht.ProfileError:
                pass
            return helper(ctx, data)
        self.refuses("ops-budget-exceeded", self.run_tool, allowlist_for(spec),
                     helpers={"count-words": over_budget})

    def test_helper_raised_profile_error_is_sanitized(self):
        def forger(ctx, data):
            raise ht.ProfileError("secret /Users/x/key")
        self.refuses("helper-failed", self.run_tool, helpers={"count-words": forger})

        def fake_refusal(ctx, data):
            raise ht.ProfileError("resource-drift")
        self.refuses("helper-failed", self.run_tool, helpers={"count-words": fake_refusal})

    def test_unlisted_checker_and_bad_arguments_are_refused(self):
        self.refuses("helper-not-allowlisted", self.run_tool,
                     checkers={"count-words": checker, "new-exe": checker})
        self.refuses("invalid-input", ht.run_tool, allowlist_for(make_spec()), "count-words",
                     {"label": "n"}, helpers=None, checkers={}, files={})
        self.refuses("tool-not-allowlisted", self.run_tool, tool=["count-words"])

    def test_output_with_str_subclass_key_is_refused(self):
        class Key(str):
            pass
        self.refuses("invalid-output", self.run_tool, helpers={
            "count-words": lambda c, d: (c.write("out/report.txt", b"x"),
                                         {Key("count"): 3, "ok": True})[1]})

    def test_deeply_nested_input_is_refused_not_crashed(self):
        deep = cur = {}
        for _ in range(100_000):
            cur["a"] = {}
            cur = cur["a"]
        self.refuses("invalid-input", self.run_tool, data=deep)

    def test_context_disagreeing_with_its_bytes_is_refused(self):
        allow = allowlist_for(make_spec())
        good = allow.contracts["count-words"]
        forged = good.to_dict()
        forged["writes"] = ["out/evil.txt", "out/report.txt"]
        forged["limits"]["maxOps"] = 64
        bad = ht.ToolContract(freeze(forged), good.canonical_bytes)
        fal = ht.ToolAllowlist(allow.data, allow.canonical_bytes, {"count-words": bad})
        self.refuses("contract-drift", self.run_tool, fal)
        # Forged admission on an E3 contract cannot reach execution either.
        e3 = allowlist_for(make_spec(effectClass="E3")).contracts["count-words"].to_dict()
        e3["admission"] = {"state": "implemented", "blocker": None}
        liar = ht.ToolContract(freeze(e3), canonical(e3))
        e3_allow = allowlist_for(make_spec(effectClass="E3"))
        fal = ht.ToolAllowlist(e3_allow.data, e3_allow.canonical_bytes, {"count-words": liar})
        self.refuses_any(fal)
        # Allowlist data that disagrees with its bytes, and a contract missing from its list.
        tampered = ht.ToolAllowlist(freeze({**thaw(allow.data), "tools": []}),
                                    allow.canonical_bytes, allow.contracts)
        self.refuses("contract-drift", self.run_tool, tampered)
        stray = ht.ToolAllowlist(allow.data, allow.canonical_bytes, {"other": good})
        self.refuses("helper-not-allowlisted", self.run_tool, stray)

    def refuses_any(self, allowlist):
        with self.assertRaises(ht.ProfileError):
            self.run_tool(allowlist)

    # --- negative controls: forged identity --------------------------------
    def test_forged_contract_hash_is_refused(self):
        contract = compile_spec(make_spec())
        self.refuses("contract-drift", ht.verify_contract, contract.canonical_bytes,
                     expected_sha256="0" * 64)
        self.refuses("invalid-expected-hash", ht.verify_contract, contract.canonical_bytes,
                     expected_sha256="abc")
        self.refuses("input-drift", ht.compile_contract, json.dumps(make_spec()).encode(),
                     expected_input_sha256="0" * 64)
        forged = contract.to_dict()
        forged["limits"]["timeoutMs"] = 10_000
        self.refuses("contract-drift", ht.verify_contract, canonical(forged),
                     expected_sha256=contract.sha256)

    def test_forged_allowlist_and_contract_set_are_refused(self):
        contracts = [compile_spec(make_spec())]
        allow = ht.compile_allowlist(contracts)
        raws = [c.canonical_bytes for c in contracts]
        self.refuses("allowlist-drift", ht.verify_allowlist, allow.canonical_bytes,
                     expected_sha256="0" * 64, contract_raws=raws)
        looser = compile_spec(make_spec(
            limits={**make_spec()["limits"], "timeoutMs": 2000}))
        self.refuses("contract-set-mismatch", ht.verify_allowlist, allow.canonical_bytes,
                     expected_sha256=allow.sha256, contract_raws=[looser.canonical_bytes])
        self.refuses("contract-set-mismatch", ht.verify_allowlist, allow.canonical_bytes,
                     expected_sha256=allow.sha256, contract_raws=[])
        extra = compile_spec(make_spec(toolId="extra-tool"))
        self.refuses("contract-set-mismatch", ht.verify_allowlist, allow.canonical_bytes,
                     expected_sha256=allow.sha256,
                     contract_raws=raws + [extra.canonical_bytes])
        self.refuses("duplicate-tool", ht.compile_allowlist, contracts + contracts)
        value = allow.data
        forged = {**thaw(value), "executionAuthorization": True}
        self.refuses("unsupported-profile", ht.verify_allowlist, canonical(forged),
                     expected_sha256=sha256(canonical(forged)).hexdigest(), contract_raws=raws)

    def test_run_rechecks_contract_identity_inside_the_allowlist(self):
        allow = allowlist_for(make_spec())
        looser = compile_spec(make_spec(limits={**make_spec()["limits"], "timeoutMs": 2000}))
        forged = ht.ToolAllowlist(allow.data, allow.canonical_bytes,
                                  {"count-words": looser})
        self.refuses("contract-drift", self.run_tool, forged)
        self.refuses("invalid-allowlist", self.run_tool, {"tools": []})

    def test_parse_refuses_forged_or_escalated_contracts(self):
        def put(path, value):
            def mutate(data):
                target = data
                for key in path[:-1]:
                    target = target[key]
                target[path[-1]] = value
            return mutate
        cases = [
            ("unsupported-profile", put(["executionAuthorization"], True)),
            ("unsupported-version", put(["format"], "braid-harness-tool/v0.2")),
            ("admission-mismatch", put(["admission", "state"], "enabled")),
            ("admission-mismatch", put(["admission", "state"], "qualified")),
            ("admission-mismatch", put(["effectClass"], "E3")),
            ("unknown-class", put(["componentClass"], "C1")),
            ("host-refused", put(["host"], "codex")),
            ("host-build-drift", put(["hostSupport", "claude", "qualification"], "qualified")),
            ("unsupported-profile", put(["policies", "path"], "anything")),
            ("limits-exceed-ceiling", put(["limits", "timeoutMs"], 10 ** 9)),
            ("limits-exceed-ceiling", put(["limits", "maxOutputBytes"], 10 ** 9)),
            ("limits-exceed-ceiling", put(["limits", "maxOps"], 0)),
            ("invalid-limits", put(["limits", "extra"], 1)),
            ("invalid-tool-id", put(["toolId"], "Bad Id")),
            ("invalid-version", put(["version"], 0)),
            ("invalid-version", put(["version"], 2)),
            ("invalid-schema", put(["input"], [{"name": "a", "type": "float", "max": 1}])),
            ("invalid-guidance", put(["guidance"], "x" * 2000)),
            ("invalid-guidance", put(["guidance"], "bad\x00text")),
            ("invalid-provenance", put(["provenance", "origin"], "adapted")),
        ]
        for reason, mutate in cases:
            with self.subTest(reason=reason):
                self.refuses_contract(reason, mutate)
        data = compile_spec(make_spec()).to_dict()
        data["extra"] = 1
        self.refuses("invalid-profile", ht.parse_contract, canonical(data))
        self.refuses("invalid-json", ht.parse_contract, b"{")

    def test_spec_schemas_and_inventories_are_bounded(self):
        field = lambda n: {"name": n, "type": "boolean", "max": None}
        self.refuses_spec("invalid-schema", input=[field(f"f{i:02d}") for i in range(17)])
        self.refuses_spec("invalid-schema", input=[field("b"), field("a")])
        self.refuses_spec("invalid-schema", input=[{"name": "a", "type": "string", "max": 0}])
        self.refuses_spec("invalid-schema", input=[{"name": "a", "type": "string",
                                                    "max": 10 ** 6}])
        self.refuses_spec("invalid-schema", input=[{"name": "a", "type": "boolean", "max": 1}])
        row = lambda i, size: {"path": f"data/f{i:02d}.txt", "sha256": "1" * 64,
                               "sizeBytes": size}
        self.refuses_spec("inventory-budget-exceeded",
                          reads=[row(i, 1) for i in range(17)])
        self.refuses_spec("inventory-budget-exceeded", reads=[row(0, 40000)])
        self.refuses_spec("inventory-budget-exceeded",
                          reads=[row(i, 32768) for i in range(5)])
        self.refuses_spec("inventory-budget-exceeded",
                          writes=[f"out/w{i:02d}.txt" for i in range(33)])
        self.refuses_spec("unsupported-version", format="braid-harness-tool-spec/v0.2")
        self.refuses_spec("unsupported-profile", executionAuthorization=True)

    # --- structure ---------------------------------------------------------
    def test_module_never_starts_processes_or_opens_resources(self):
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        imported = {a.name.split(".")[0] for n in ast.walk(tree) if isinstance(n, ast.Import)
                    for a in n.names}
        imported |= {n.module.split(".")[0] for n in ast.walk(tree)
                     if isinstance(n, ast.ImportFrom) and n.module and n.level == 0}
        self.assertFalse(imported & {"os", "subprocess", "socket", "urllib", "http", "shutil",
                                     "pathlib", "ctypes", "multiprocessing", "threading",
                                     "asyncio", "importlib", "pickle"})
        calls = {n.func.id for n in ast.walk(tree)
                 if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
        self.assertFalse(calls & {"open", "exec", "eval", "compile", "__import__"})

    def test_no_global_registry_exists(self):
        for name in vars(ht):
            self.assertFalse(name.upper() in {"REGISTRY", "HELPERS", "TOOLS"} or
                             name.lower().startswith("register"), name)


# --- E3 subprocess adapter (contract section 13, drafted), deterministic doubles only ------

HELPER_BYTES = b"#!pinned helper bytes, never executed\n"
HELPER_PATH = ht.HELPER_ROOT + "count-words-e3"
REPORT = "out/report.txt"


def make_e3_spec(**over):
    return make_spec(**{"toolId": "count-words-e3", "effectClass": "E3", **over})


def make_exec_spec(contract, **over):
    value = {
        "format": ht.EXEC_SPEC_FORMAT, "toolId": contract.tool_id,
        "contractSha256": contract.sha256,
        "helper": {"path": HELPER_PATH, "sha256": sha256(HELPER_BYTES).hexdigest(),
                   "sizeBytes": len(HELPER_BYTES)},
        "argv": [HELPER_PATH, "--label", "{label}", NOTES_PATH],
        "env": [{"name": "LANG", "value": "C"}, {"name": "LC_ALL", "value": "C"}],
        "limits": {"timeoutMs": 1000, "maxStdoutBytes": 256, "maxStderrBytes": 64},
        "network": "none", "contractState": "drafted", "executionAuthorization": False}
    value.update(over)
    return value


class DoubleExecutor:
    """Deterministic stand-in for a contained child: computes, never spawns."""

    def __init__(self, m, **behaviour):
        self.m, self.b = m, behaviour
        self.requests, self.teardowns = [], 0

    def run(self, request):
        self.requests.append(request)
        if "raise" in self.b:
            raise self.b["raise"]
        label = request.argv[2]
        words = len(request.inputs[NOTES_PATH].split())
        artifacts = {REPORT: f"{label}:{words}".encode()}
        artifacts.update(self.b.get("extra", {}))
        for path in self.b.get("drop", ()):
            artifacts.pop(path)
        stdout = self.b.get("stdout", json.dumps({"count": words, "ok": True}).encode())
        return self.m.ExecOutcome(
            exit_code=self.b.get("exit_code", 0), stdout=stdout,
            stderr=self.b.get("stderr", b""), artifacts=artifacts,
            timed_out=self.b.get("timed_out", False),
            network_attempts=self.b.get("network", 0))

    def teardown(self, request):
        self.teardowns += 1
        if "teardown_raise" in self.b:
            raise RuntimeError("teardown failed")
        return {"processesRemaining": self.b.get("left", 0), "artifactsRemoved": 1}


def e3_checker(data, output, artifacts):
    return (output == {"count": 3, "ok": True} and
            artifacts[REPORT] == f"{data['label']}:3".encode())


def mutant(old, new):
    """Load a separate copy of harness_tools with one guard textually disabled."""
    source = MODULE.read_text(encoding="utf-8")
    assert source.count(old) == 1, old
    name = "agent_braid._harness_tools_mutant"
    module = types.ModuleType(name)
    module.__package__ = "agent_braid"
    sys.modules[name] = module
    try:
        exec(compile(source.replace(old, new), str(MODULE), "exec"), module.__dict__)
    finally:
        del sys.modules[name]
    return module


class Scenario:
    """One E3 run built entirely from the records of module ``m``."""

    def __init__(self, m=ht, spec=None, exec_over=None, clock=None, **behaviour):
        spec = spec or make_e3_spec()
        self.m = m
        self.contract = m.compile_contract(
            json.dumps(spec).encode(),
            expected_input_sha256=sha256(canonical(spec)).hexdigest())
        self.allow = m.compile_allowlist([self.contract])
        value = make_exec_spec(self.contract, **(exec_over or {}))
        self.record = m.compile_exec(json.dumps(value).encode(), contract=self.contract,
                                     expected_input_sha256=sha256(canonical(value)).hexdigest())
        self.executor = DoubleExecutor(m, **behaviour)
        self.clock = clock or FakeClock(step=1)

    def _kwargs(self, over):
        kwargs = {"exec_record": self.record, "executor": self.executor,
                  "checker": e3_checker, "files": {NOTES_PATH: NOTES}, "clock": self.clock}
        kwargs.update(over)
        return kwargs

    def run(self, label="notes", **over):
        """The test-only double entry: the same adapter checks, any injected executor."""
        return self.m._run_helper_double(self.allow, self.contract.tool_id, {"label": label},
                                         **self._kwargs(over))

    def run_public(self, label="notes", **over):
        """The public entry: only ``ContainedExecutor`` itself reaches ``run()``."""
        return self.m.run_helper(self.allow, self.contract.tool_id, {"label": label},
                                 **self._kwargs(over))


class SubprocessAdapterTests(unittest.TestCase):
    def refuses(self, reason, fn, *args, **kwargs):
        with self.assertRaises(ht.ProfileError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)

    def mutation_accepts(self, old, new, build, reason):
        """Mutation control: with the guard removed, the same attack is no longer refused for it.

        ``build(module)`` returns the attack as a zero-argument callable. The control shows
        that the matching negative test can fail, so it does not pass by construction.
        """
        attack = build(mutant(old, new))
        try:
            attack()
        except ht.ProfileError as exc:
            self.assertNotEqual(exc.reason, reason)

    # --- positive ----------------------------------------------------------
    def test_pinned_helper_runs_against_a_double_with_check_and_teardown(self):
        s = Scenario()
        result = s.run()
        self.assertEqual(thaw(result.output), {"count": 3, "ok": True})
        self.assertEqual(result.exec_sha256, s.record.sha256)
        self.assertEqual(result.artifacts[REPORT], sha256(b"notes:3").hexdigest())
        self.assertEqual(thaw(result.teardown),
                         {"closed": True, "artifactsRemoved": 1, "processesRemaining": 0})
        self.assertIs(result.to_dict()["executionAuthorization"], False)
        self.assertEqual(result.to_dict()["execSha256"], s.record.sha256)
        (request,) = s.executor.requests
        self.assertEqual(request.argv, (HELPER_PATH, "--label", "notes", NOTES_PATH))
        self.assertEqual(request.env, (("LANG", "C"), ("LC_ALL", "C")))
        self.assertEqual(dict(request.inputs), {NOTES_PATH: NOTES})
        self.assertEqual(request.writes, (REPORT,))
        self.assertEqual((request.network, request.timeout_ms), (False, 1000))
        self.assertEqual(request.helper_sha256, sha256(HELPER_BYTES).hexdigest())
        self.assertEqual(s.executor.teardowns, 1)

    def test_integer_fields_substitute_as_whole_arguments(self):
        spec = make_e3_spec(input=[{"name": "label", "type": "string", "max": 32},
                                   {"name": "n", "type": "integer", "max": 100}])
        s = Scenario(spec=spec, exec_over={"argv": [HELPER_PATH, "{label}", "{n}"]})

        class Two(DoubleExecutor):
            def run(self, request):
                self.requests.append(request)
                return self.m.ExecOutcome(0, b'{"count": 3, "ok": true}',
                                          artifacts={REPORT: b"notes:3"})
        s.executor = Two(ht)
        result = ht._run_helper_double(
            s.allow, s.contract.tool_id, {"label": "notes", "n": 7}, exec_record=s.record,
            executor=s.executor, checker=e3_checker, files={NOTES_PATH: NOTES},
            clock=FakeClock(1))
        self.assertEqual(s.executor.requests[0].argv, (HELPER_PATH, "notes", "7"))
        self.assertEqual(thaw(result.output)["count"], 3)
        self.refuses("argument-injection", ht._run_helper_double, s.allow,
                     s.contract.tool_id, {"label": "notes", "n": -7}, exec_record=s.record,
                     executor=s.executor, checker=e3_checker, files={NOTES_PATH: NOTES})

    def test_exec_record_is_drafted_bound_and_grants_nothing(self):
        s = Scenario()
        data = thaw(s.record.data)
        self.assertEqual((data["format"], data["contractState"], data["network"]),
                         (ht.EXEC_FORMAT, "drafted", "none"))
        self.assertIs(data["executionAuthorization"], False)
        raw = canonical(data)
        self.assertEqual(ht.verify_exec(raw, expected_sha256=s.record.sha256,
                                        contract=s.contract).sha256, s.record.sha256)
        self.refuses("exec-drift", ht.verify_exec, raw, expected_sha256="0" * 64,
                     contract=s.contract)
        self.refuses("input-drift", ht.compile_exec, raw, expected_input_sha256="0" * 64,
                     contract=s.contract)
        with self.assertRaises(FrozenInstanceError):
            s.record.data = {}  # type: ignore[misc]

    def test_c5_admission_agrees_with_the_component_registry(self):
        for effect in ("E0", "E1", "E2", "E3", "E4"):
            state, blocker = hc.derive_admission("C5", effect)
            self.assertEqual(ht._admission(effect), {"state": state, "blocker": blocker})
        self.assertEqual(hc.derive_admission("C5", "E2"), ("implemented", None))
        self.assertEqual(hc.derive_admission("C5", "E3"), ("blocked", "effects-not-adopted"))
        self.assertEqual(Scenario().contract.data["admission"]["state"], "blocked")

    # --- the real executor refuses before anything starts ------------------
    def test_contained_executor_refuses_every_unqualified_helper(self):
        self.assertEqual(ht.QUALIFIED_HELPERS, frozenset())
        self.assertIsInstance(ht.QUALIFIED_HELPERS, frozenset)
        for fn in (ht.run_helper, ht.ContainedExecutor.run, ht.ContainedExecutor):
            params = set(inspect.signature(fn).parameters)
            self.assertFalse(params & {"qualified", "pins", "qualified_helpers", "allow"}, fn)
        s = Scenario()
        self.refuses("helper-not-qualified", s.run_public, executor=ht.ContainedExecutor())

    def test_mutation_control_pinned_helper_reaches_only_the_containment_refusal(self):
        pin = repr({(HELPER_PATH, sha256(HELPER_BYTES).hexdigest())})
        m = mutant("QUALIFIED_HELPERS: frozenset[tuple[str, str]] = frozenset()",
                   f"QUALIFIED_HELPERS: frozenset[tuple[str, str]] = frozenset({pin})")
        self.refuses("containment-not-wired", Scenario(m).run_public,
                     executor=m.ContainedExecutor())

    # --- only the contained executor reaches run() (GPT-6 D5 review, F-001) ----
    def test_public_run_helper_refuses_a_non_contained_executor_before_run(self):
        class Spawner(ht.ContainedExecutor):
            """A subclass that would launch a child; it must never be called."""

            def __init__(self):
                self.calls = []

            def run(self, request):
                self.calls.append("run")
                raise AssertionError("run() reached")

            def teardown(self, request):
                self.calls.append("teardown")
                return {"processesRemaining": 0, "artifactsRemoved": 0}

        s = Scenario()
        spawner = Spawner()
        for executor in (s.executor, spawner):
            with self.subTest(executor=type(executor).__name__):
                self.refuses("executor-not-contained", s.run_public, executor=executor)
        self.assertEqual((s.executor.requests, s.executor.teardowns), ([], 0))
        self.assertEqual(spawner.calls, [])

    def test_contained_executor_methods_cannot_be_replaced_per_instance(self):
        executor = ht.ContainedExecutor()
        with self.assertRaises(AttributeError):
            executor.run = lambda request: None  # type: ignore[method-assign]
        with self.assertRaises(AttributeError):
            executor.teardown = lambda request: None  # type: ignore[method-assign]

    def test_double_entry_is_test_only(self):
        """No shipped module may reach the double entry; only tests call it."""
        package = MODULE.parent
        users = sorted(p.name for p in package.rglob("*.py")
                       if "_run_helper_double" in p.read_text(encoding="utf-8"))
        self.assertEqual(users, ["harness_tools.py"])
        tree = ast.parse(MODULE.read_text(encoding="utf-8"))
        calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and
                 getattr(n.func, "id", None) == "_run_helper_double"]
        self.assertEqual(len(calls), 1)  # only from run_helper, after the gate
        self.assertNotIn("_run_helper_double", getattr(ht, "__all__", ()))

    def test_mutation_control_contained_executor_gate(self):
        self.mutation_accepts(
            '_require(type(executor) is ContainedExecutor, "executor-not-contained")', "pass",
            lambda m: lambda: Scenario(m).run_public(), "executor-not-contained")

    def test_double_cannot_spoof_a_containment_refusal(self):
        self.refuses("helper-failed",
                     Scenario(**{"raise": ht.ProfileError("helper-not-qualified")}).run)
        s = Scenario(**{"raise": OSError("boom")})
        self.refuses("helper-failed", s.run)
        self.assertEqual(s.executor.teardowns, 1)

    # --- injection and launch inputs ----------------------------------------
    def test_argument_injection_is_refused_before_the_executor(self):
        for label in ("-rf", "--output=/etc/x", "", "a/../b", "a\x00b", "a\nb", "a‮b"):
            with self.subTest(label=label):
                s = Scenario()
                self.refuses("argument-injection", s.run, label=label)
                self.assertEqual((s.executor.requests, s.executor.teardowns), ([], 0))

    def test_mutation_control_argument_injection(self):
        self.mutation_accepts(
            '_require(type(text) is str and text != "" and not text.startswith("-") and\n'
            '             ".." not in text and _printable(text), "argument-injection")', "pass",
            lambda m: lambda: Scenario(m).run(label="-rf"), "argument-injection")

    def test_environment_is_literal_and_denies_loader_and_secret_names(self):
        for name in ("DYLD_INSERT_LIBRARIES", "LD_PRELOAD", "PYTHONPATH", "NODE_OPTIONS",
                     "HTTPS_PROXY", "API_KEY", "GH_TOKEN", "AWS_SECRET", "OAUTH_X"):
            with self.subTest(name=name):
                self.refuses("env-denied", Scenario,
                             exec_over={"env": [{"name": name, "value": "x"}]})
        for env in ([{"name": "lang", "value": "C"}], [{"name": "A", "value": "\x1b"}],
                    [{"name": "A", "value": "é"}],
                    [{"name": "B", "value": "1"}, {"name": "A", "value": "1"}],
                    [{"name": f"V{i}", "value": "1"} for i in range(9)],
                    [{"name": "A", "value": "x" * 1100}], [{"name": "A"}]):
            with self.subTest(env=env[:1]):
                self.refuses("invalid-env", Scenario, exec_over={"env": env})

    def test_mutation_control_env_deny(self):
        self.mutation_accepts(
            "not name.startswith(_ENV_DENY_PREFIX) and\n"
            "                 not any(part in name for part in _ENV_DENY_PART)", "True",
            lambda m: lambda: Scenario(m, exec_over={"env": [
                {"name": "DYLD_INSERT_LIBRARIES", "value": "x"}]}), "env-denied")

    def test_argv_template_and_helper_pin_are_strict(self):
        for argv in ([HELPER_PATH, "{missing}"], ["/bin/sh", "-c", "x"], [HELPER_PATH, "a{b"],
                     [HELPER_PATH, "{label}x"], [], [HELPER_PATH] + ["a"] * 32,
                     [HELPER_PATH, ""], [HELPER_PATH, "a\x00"]):
            with self.subTest(argv=argv[:3]):
                self.refuses("invalid-argv", Scenario, exec_over={"argv": argv})
        for path in ("/usr/bin/false", ht.HELPER_ROOT + "../x", ht.HELPER_ROOT + "A",
                     ht.HELPER_ROOT + "sub/x", "helpers/x"):
            with self.subTest(path=path):
                helper = {"path": path, "sha256": sha256(HELPER_BYTES).hexdigest(),
                          "sizeBytes": 1}
                self.refuses("invalid-helper", Scenario,
                             exec_over={"helper": helper, "argv": [path]})
        self.refuses("invalid-helper", Scenario, exec_over={"helper": {
            "path": HELPER_PATH, "sha256": "x" * 64, "sizeBytes": 1}})
        self.refuses("invalid-helper", Scenario, exec_over={"helper": {
            "path": HELPER_PATH, "sha256": sha256(HELPER_BYTES).hexdigest(), "sizeBytes": 0}})

    def test_argv_byte_budget_is_enforced_after_substitution(self):
        spec = make_e3_spec(input=[{"name": "label", "type": "string", "max": 4096}],
                            limits={"maxInputBytes": 8192, "maxOutputBytes": 256, "maxOps": 4,
                                    "maxWriteBytes": 64, "timeoutMs": 1000})
        s = Scenario(spec=spec, exec_over={"argv": [HELPER_PATH] + ["{label}"] * 2})
        self.refuses("argv-budget-exceeded", s.run, label="a" * 2100)
        self.assertEqual(s.executor.requests, [])

    def test_exec_limits_and_flags_are_bounded(self):
        for limits in ({"timeoutMs": 2000, "maxStdoutBytes": 256, "maxStderrBytes": 64},
                       {"timeoutMs": 1000, "maxStdoutBytes": 512, "maxStderrBytes": 64},
                       {"timeoutMs": 1000, "maxStdoutBytes": 256, "maxStderrBytes": 20000},
                       {"timeoutMs": 0, "maxStdoutBytes": 256, "maxStderrBytes": 64}):
            with self.subTest(limits=limits):
                self.refuses("limits-exceed-ceiling", Scenario, exec_over={"limits": limits})
        self.refuses("invalid-limits", Scenario, exec_over={"limits": {"timeoutMs": 1}})
        self.refuses("unsupported-profile", Scenario, exec_over={"contractState": "adopted"})
        self.refuses("unsupported-profile", Scenario, exec_over={"executionAuthorization": True})
        self.refuses("network-not-allowed", Scenario, exec_over={"network": "loopback"})
        self.refuses("unsupported-version", Scenario,
                     exec_over={"format": "braid-harness-exec-spec/v0.2"})

    def test_mutation_control_network_declaration(self):
        self.mutation_accepts('_require(value["network"] == "none", "network-not-allowed")',
                              "pass", lambda m: lambda: Scenario(m, exec_over={
                                  "network": "loopback"}), "network-not-allowed")

    def test_exec_record_must_bind_its_own_e3_contract(self):
        s = Scenario()
        self.refuses("undeclared-effect", ht.parse_exec, s.record.canonical_bytes,
                     contract=compile_spec(make_spec()))
        data = thaw(s.record.data)
        data["contractSha256"] = "0" * 64
        self.refuses("contract-set-mismatch", ht.parse_exec, canonical(data),
                     contract=s.contract)
        for spec, tool in ((make_spec(), "count-words"),
                           (make_e3_spec(effectClass="E4"), "count-words-e3")):
            with self.subTest(effect=spec["effectClass"]):
                self.refuses("effect-blocked", ht._run_helper_double, allowlist_for(spec),
                             tool, {"label": "x"}, exec_record=s.record, executor=s.executor,
                             checker=e3_checker, files={NOTES_PATH: NOTES})
                self.refuses("effect-blocked", ht.run_helper, allowlist_for(spec), tool,
                             {"label": "x"}, exec_record=s.record,
                             executor=ht.ContainedExecutor(), checker=e3_checker,
                             files={NOTES_PATH: NOTES})
        self.refuses("tool-not-allowlisted", ht._run_helper_double, s.allow, "other",
                     {"label": "x"}, exec_record=s.record, executor=s.executor,
                     checker=e3_checker, files={NOTES_PATH: NOTES})
        self.assertEqual(s.executor.requests, [])

    def test_e3_contract_still_never_runs_in_process(self):
        s = Scenario()
        self.refuses("effect-blocked", ht.run_tool, s.allow, s.contract.tool_id,
                     {"label": "x"}, helpers={s.contract.tool_id: helper},
                     checkers={s.contract.tool_id: checker}, files={NOTES_PATH: NOTES})

    def test_forged_exec_view_is_refused(self):
        s = Scenario()
        forged = ht.HelperExec(freeze({**thaw(s.record.data), "env": []}),
                               s.record.canonical_bytes)
        self.refuses("exec-drift", s.run, exec_record=forged)
        self.refuses("invalid-exec", s.run, exec_record=thaw(s.record.data))
        self.assertEqual(s.executor.requests, [])

    def test_mutation_control_exec_view_drift(self):
        def build(m):
            s = Scenario(m)
            forged = m.HelperExec(freeze({**thaw(s.record.data), "env": []}),
                                  s.record.canonical_bytes)
            return lambda: s.run(exec_record=forged)
        self.mutation_accepts(
            '_require(canonical(exec_record.data) == record.canonical_bytes, "exec-drift")',
            "pass", build, "exec-drift")

    def test_input_resources_must_match_the_inventory(self):
        s = Scenario()
        self.refuses("resource-drift", s.run, files={NOTES_PATH: b"x" * len(NOTES)})
        self.refuses("resource-missing", s.run, files={})
        self.assertEqual(s.executor.requests, [])

    def test_mutation_control_resource_drift(self):
        def build(m):
            s = Scenario(m)
            return lambda: s.run(files={NOTES_PATH: b"x" * len(NOTES)},
                                 checker=lambda *_: True)
        self.mutation_accepts(
            '_require(len(item) == row["sizeBytes"] and sha256(item).hexdigest() == '
            'row["sha256"],\n                 "resource-drift")', "pass", build,
            "resource-drift")

    # --- outcome guards ----------------------------------------------------
    def test_network_attempt_is_refused_and_torn_down(self):
        s = Scenario(network=1)
        self.refuses("network-attempted", s.run)
        self.assertEqual(s.executor.teardowns, 1)

    def test_mutation_control_network_attempt(self):
        self.mutation_accepts('_require(outcome.network_attempts == 0, "network-attempted")',
                              "pass", lambda m: Scenario(m, network=1).run,
                              "network-attempted")

    def test_timeout_reported_or_measured_is_refused(self):
        s = Scenario(timed_out=True)
        self.refuses("timeout", s.run)
        self.assertEqual(s.executor.teardowns, 1)
        slow = Scenario(clock=FakeClock(step=2_000_000_000))
        self.refuses("timeout", slow.run)
        self.assertEqual(slow.executor.teardowns, 1)

    def test_mutation_control_timeout(self):
        self.mutation_accepts(
            '_require(not outcome.timed_out and elapsed_ns <= request.timeout_ms * 1_000_000, '
            '"timeout")', "pass",
            lambda m: Scenario(m, clock=FakeClock(step=2_000_000_000)).run, "timeout")

    def test_killed_or_failing_child_is_refused(self):
        self.refuses("helper-killed", Scenario(exit_code=None).run)
        s = Scenario(exit_code=3)
        self.refuses("helper-failed", s.run)
        self.assertEqual(s.executor.teardowns, 1)

    def test_mutation_control_exit_code(self):
        self.mutation_accepts('_require(outcome.exit_code == 0, "helper-failed")', "pass",
                              lambda m: Scenario(m, exit_code=3).run, "helper-failed")

    def test_unexpected_artifact_is_refused(self):
        for extra in ({"out/other.txt": b"x"}, {"../escape.txt": b"x"},
                      {"/tmp/x": b"x"}, {NOTES_PATH: b"x"}, {"OUT/report.txt": b"x"}):
            with self.subTest(extra=extra):
                s = Scenario(extra=extra)
                self.refuses("unexpected-artifact", s.run)
                self.assertEqual(s.executor.teardowns, 1)
        self.refuses("invalid-artifact", Scenario(extra={REPORT: "text"}).run)

    def test_mutation_control_unexpected_artifact(self):
        self.mutation_accepts(
            '_require(type(path) is str and path in request.writes, "unexpected-artifact")',
            "pass", lambda m: Scenario(m, extra={"out/other.txt": b"x"}).run,
            "unexpected-artifact")

    def test_missing_artifact_is_refused(self):
        self.refuses("artifact-missing", Scenario(drop=(REPORT,)).run)

    def test_mutation_control_missing_artifact(self):
        def build(m):
            s = Scenario(m, drop=(REPORT,))
            return lambda: s.run(checker=lambda *_: True)
        self.mutation_accepts(
            '_require(set(artifacts) == set(request.writes), "artifact-missing")', "pass",
            build, "artifact-missing")

    def test_write_budget_applies_to_reported_artifacts(self):
        self.refuses("write-budget-exceeded", Scenario(extra={REPORT: b"x" * 65}).run)

    def test_output_and_stderr_are_bounded_and_typed(self):
        self.refuses("output-budget-exceeded", Scenario(stdout=b" " * 257).run)
        self.refuses("stderr-budget-exceeded", Scenario(stderr=b"e" * 65).run)
        for stdout in (b"not json", b'{"count": 3}', b'{"count": "3", "ok": true}',
                       b'{"count": 3, "ok": true, "extra": 1}', b"[]"):
            with self.subTest(stdout=stdout):
                self.refuses("invalid-output", Scenario(stdout=stdout).run)
        self.refuses("output-budget-exceeded",
                     Scenario(stdout=b'{"count": 1001, "ok": true}').run)

    def test_mutation_control_stdout_budget(self):
        big = json.dumps({"count": 3, "ok": True}).encode() + b" " * 300
        self.mutation_accepts(
            '_require(len(outcome.stdout) <= request.max_stdout_bytes, '
            '"output-budget-exceeded")', "pass", lambda m: Scenario(m, stdout=big).run,
            "output-budget-exceeded")

    def test_mutation_control_stderr_budget(self):
        self.mutation_accepts(
            '_require(len(outcome.stderr) <= request.max_stderr_bytes, '
            '"stderr-budget-exceeded")', "pass", lambda m: Scenario(m, stderr=b"e" * 65).run,
            "stderr-budget-exceeded")

    def test_malformed_outcome_is_refused(self):
        class Raw(DoubleExecutor):
            def run(self, request):
                return {"exit_code": 0}
        s = Scenario()
        s.executor = Raw(ht)
        self.refuses("invalid-outcome", s.run)
        self.assertEqual(s.executor.teardowns, 1)
        self.refuses("invalid-outcome", Scenario(network=True).run)

    # --- checker and teardown ----------------------------------------------
    def test_checker_is_mandatory_distinct_and_exactly_true(self):
        s = Scenario()
        self.refuses("checker-not-independent", s.run, checker=s.executor.run)
        self.refuses("checker-missing", s.run, checker=None)
        self.refuses("check-failed", s.run, checker=lambda *_: 1)
        self.refuses("check-failed", s.run, checker=lambda *_: False)
        self.refuses("checker-raised", s.run, checker=lambda *_: 1 / 0)
        self.refuses("executor-missing", s.run, executor=object())
        self.assertEqual(s.executor.teardowns, 3)

    def test_mutation_control_checker_independence(self):
        def build(m):
            s = Scenario(m)
            return lambda: s.run(checker=s.executor.run)
        self.mutation_accepts(
            '_require(checker is not executor and checker != executor.run, '
            '"checker-not-independent")', "pass", build, "checker-not-independent")

    def test_teardown_leftovers_or_failures_are_refused(self):
        self.refuses("teardown-incomplete", Scenario(left=1).run)
        self.refuses("teardown-incomplete", Scenario(teardown_raise=True).run)
        self.refuses("teardown-incomplete", Scenario(left=True).run)
        # A failed run still tears down, and a leftover process outranks the run failure.
        s = Scenario(exit_code=3, left=2)
        self.refuses("teardown-incomplete", s.run)
        self.assertEqual(s.executor.teardowns, 1)

    def test_mutation_control_teardown(self):
        self.mutation_accepts('receipt["processesRemaining"] == 0 and ', "",
                              lambda m: Scenario(m, left=1).run, "teardown-incomplete")

    def test_mutation_control_helper_root(self):
        path = "/usr/bin/false"
        helper = {"path": path, "sha256": sha256(HELPER_BYTES).hexdigest(), "sizeBytes": 1}
        self.mutation_accepts(
            "path.startswith(HELPER_ROOT) and\n"
            "             _HELPER_NAME.fullmatch(path[len(HELPER_ROOT):]) is not None", "True",
            lambda m: lambda: Scenario(m, exec_over={"helper": helper, "argv": [path]}),
            "invalid-helper")

    def test_mutation_control_argv_budget(self):
        spec = make_e3_spec(input=[{"name": "label", "type": "string", "max": 4096}],
                            limits={"maxInputBytes": 8192, "maxOutputBytes": 256, "maxOps": 4,
                                    "maxWriteBytes": 64, "timeoutMs": 1000})

        def build(m):
            s = Scenario(m, spec=spec, exec_over={"argv": [HELPER_PATH] + ["{label}"] * 2})
            return lambda: s.run(label="a" * 2100, checker=lambda *_: True)
        self.mutation_accepts(
            '<= EXEC_CEILINGS["maxArgBytes"],\n             "argv-budget-exceeded")',
            '<= 10 ** 9, "argv-budget-exceeded")', build, "argv-budget-exceeded")

    def test_mutation_control_write_budget(self):
        def build(m):
            s = Scenario(m, extra={REPORT: b"x" * 65})
            return lambda: s.run(checker=lambda *_: True)
        self.mutation_accepts(
            '_require(len(item) <= MAX_WRITE_FILE and total <= '
            'contract.data["limits"]["maxWriteBytes"],\n                 '
            '"write-budget-exceeded")', "pass", build, "write-budget-exceeded")

    def test_mutation_control_e3_only(self):
        def build(m):
            s = Scenario(m)
            allow = m.compile_allowlist([m.compile_contract(
                json.dumps(make_spec()).encode(),
                expected_input_sha256=sha256(canonical(make_spec())).hexdigest())])
            return lambda: m._run_helper_double(allow, "count-words", {"label": "x"},
                                                exec_record=s.record, executor=s.executor,
                                                checker=e3_checker, files={NOTES_PATH: NOTES})
        self.mutation_accepts(
            '_require(contract.data["effectClass"] == "E3", "effect-blocked")', "pass", build,
            "effect-blocked")

    def test_mutation_control_checker_verdict(self):
        self.mutation_accepts('_require(verdict is True, "check-failed")\n        input_sha, '
                              'output_sha = digest(input_value), digest(output)\n        '
                              'artifact_hashes = {p: sha256(b).hexdigest() for p, b in '
                              'artifacts.items()}\n    finally:\n        removed = _teardown',
                              'input_sha, output_sha = digest(input_value), digest(output)\n'
                              '        artifact_hashes = {p: sha256(b).hexdigest() for p, b in '
                              'artifacts.items()}\n    finally:\n        removed = _teardown',
                              lambda m: lambda: Scenario(m).run(checker=lambda *_: 1),
                              "check-failed")

    def test_mutation_control_killed_child(self):
        self.mutation_accepts('_require(outcome.exit_code is not None, "helper-killed")',
                              "pass", lambda m: Scenario(m, exit_code=None).run,
                              "helper-killed")

    def test_mutants_are_isolated_from_the_real_module(self):
        mutant('_require(outcome.network_attempts == 0, "network-attempted")', "pass")
        self.refuses("network-attempted", Scenario(network=1).run)
        self.assertNotIn("agent_braid._harness_tools_mutant", sys.modules)


if __name__ == "__main__":
    unittest.main()
