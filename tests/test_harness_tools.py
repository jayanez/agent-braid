# SPDX-License-Identifier: AGPL-3.0-only
"""Offline controls for the SPEC-050/T004 allowlisted tool contracts and helpers."""
import ast
from dataclasses import FrozenInstanceError
from hashlib import sha256
import json
from pathlib import Path
import unittest

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


if __name__ == "__main__":
    unittest.main()
