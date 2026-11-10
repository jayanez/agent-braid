# SPDX-License-Identifier: AGPL-3.0-only
"""Offline controls for the SPEC-050/T006 bounded roles and orchestration policy."""
import ast
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import unittest

from agent_braid import harness_components as hc
from agent_braid import harness_orchestration as ho
from agent_braid import harness_tools as ht
from agent_braid.system_one import canonical, freeze
from tests.test_harness_components import file_row, make_inventory
from tests.test_harness_tools import compile_spec, make_spec

MODULE = Path(ho.__file__)
ROLE_FILES = {f"roles/{n}.md": f"Role {n} guidance.\n".encode()
              for n in ("planner", "builder", "reviewer", "docs")}


def compile_profile():
    rows = [file_row(p, b) for p, b in sorted(ROLE_FILES.items())]
    value = make_inventory(rows, componentClass="C8")
    return hc.compile_inventory(json.dumps(value).encode(),
                                expected_input_sha256=sha256(canonical(value)).hexdigest())


PROFILE = compile_profile()


def ctx_rows(*names):
    return [{"path": f"roles/{n}.md", "sha256": sha256(ROLE_FILES[f"roles/{n}.md"]).hexdigest(),
             "sizeBytes": len(ROLE_FILES[f"roles/{n}.md"])} for n in names]


TOOL_TEXT = ROLE_FILES["roles/docs.md"]
TOOL_READ = {"path": "roles/docs.md", "sha256": sha256(TOOL_TEXT).hexdigest(),
             "sizeBytes": len(TOOL_TEXT)}


def tool_helper(ctx, data):
    words = len(ctx.read("roles/docs.md").split())
    ctx.write("out/report.txt", f"{data['label']}:{words}".encode())
    return {"count": words, "ok": True}


def tool_checker(data, output, artifacts):
    return output["count"] == 3 and artifacts["out/report.txt"] == b"x:3"


def role(rid, ctx, *, own=(), reads=(), deps=(), effect="E2", tools=(), output=None):
    return {"roleId": rid, "context": ctx_rows(ctx), "ownership": list(own),
            "reads": list(reads), "dependencies": list(deps), "effectClass": effect,
            "tools": list(tools),
            "output": output or [{"name": "n", "type": "integer", "max": 100}]}


def make_spec_plan(**over):
    value = {"format": ho.SPEC_FORMAT, "planId": "plan-1", "profileSha256": PROFILE.sha256,
             "roles": [
                 role("builder", "builder", own=["out/build.txt"], reads=["out/plan.json"],
                      deps=["planner"]),
                 role("docs", "docs", own=["out/docs.md"]),
                 role("planner", "planner", own=["out/plan.json"]),
                 role("reviewer", "reviewer", reads=["out/build.txt"], deps=["builder"],
                      effect="E1")],
             "executionAuthorization": False}
    value.update(over)
    return value


def compile_plan(value, **kw):
    return ho.compile_plan(json.dumps(value).encode(),
                           expected_input_sha256=sha256(canonical(value)).hexdigest(),
                           profile=kw.pop("profile", PROFILE), **kw)


def handlers(n=1, plan_n=None):
    def planner(ctx, inputs):
        ctx.write("out/plan.json", b"plan")
        return {"n": plan_n if plan_n is not None else n}

    def builder(ctx, inputs):
        ctx.write("out/build.txt", b"built:" + ctx.read("out/plan.json"))
        return {"n": inputs["planner"]["n"] + 1}

    def docs(ctx, inputs):
        ctx.write("out/docs.md", b"docs")
        return {"n": 0}

    def reviewer(ctx, inputs):
        return {"n": len(ctx.read("out/build.txt"))}
    return {"planner": planner, "builder": builder, "docs": docs, "reviewer": reviewer}


def reference(outputs, artifacts):
    return (outputs["reviewer"]["n"] == len("built:plan") and
            outputs["builder"]["n"] == outputs["planner"]["n"] + 1)


class OrchestrationTests(unittest.TestCase):
    def refuses(self, reason, fn, *args, **kwargs):
        with self.assertRaises(hc.ProfileError) as caught:
            fn(*args, **kwargs)
        self.assertEqual(caught.exception.reason, reason)

    def refuses_spec(self, reason, mutate=None, **kw):
        value = make_spec_plan()
        if mutate:
            mutate(value)
        self.refuses(reason, compile_plan, value, **kw)

    def run_plan(self, plan=None, hs=None, **kw):
        return ho.run_plan(plan or compile_plan(make_spec_plan()), hs or handlers(),
                           kw.pop("checker", reference), files=kw.pop("files", ROLE_FILES),
                           **kw)

    # --- positive controls -------------------------------------------------
    def test_compiles_blocked_plan_with_serial_order(self):
        plan = compile_plan(make_spec_plan())
        data = plan.to_dict()
        self.assertEqual(plan.order, ("docs", "planner", "builder", "reviewer"))
        self.assertEqual(data["admission"], {"state": "blocked",
                                             "blocker": "no-containment-qualification"})
        self.assertEqual(data["delegation"], "none")
        self.assertIs(data["executionAuthorization"], False)
        self.assertEqual(data["parallelism"], {"width": 1, "allowed": False,
                                               "advisoryCandidates": [
                                                   ["builder", "docs"], ["docs", "planner"],
                                                   ["docs", "reviewer"]]})
        self.assertEqual(plan.sha256, compile_plan(make_spec_plan()).sha256)

    def test_analysis_reuses_existing_analyzer_classifications(self):
        rows = {(r["left"], r["right"]): r["classification"]
                for r in compile_plan(make_spec_plan()).data["analysis"]["interactions"]}
        self.assertEqual(rows[("builder", "planner")], "ordered")
        self.assertEqual(rows[("docs", "planner")], "independent-candidate")

    def test_verify_plan_roundtrip_and_drift(self):
        plan = compile_plan(make_spec_plan())
        self.assertEqual(ho.verify_plan(plan.canonical_bytes, expected_sha256=plan.sha256,
                                        profile=PROFILE).sha256, plan.sha256)
        self.refuses("plan-drift", ho.verify_plan, plan.canonical_bytes,
                     expected_sha256="0" * 64, profile=PROFILE)
        forged = plan.to_dict()
        forged["admission"] = {"state": "enabled", "blocker": None}
        raw = canonical(forged)
        self.refuses("plan-drift", ho.verify_plan, raw,
                     expected_sha256=sha256(raw).hexdigest(), profile=PROFILE)
        forged = plan.to_dict()
        forged["parallelism"]["allowed"] = True
        raw = canonical(forged)
        self.refuses("plan-drift", ho.verify_plan, raw,
                     expected_sha256=sha256(raw).hexdigest(), profile=PROFILE)

    def test_run_matches_serial_reference_and_is_simulated(self):
        result = self.run_plan()
        self.assertEqual((result.status, result.reason), ("completed", None))
        self.assertEqual(result.completed, ("docs", "planner", "builder", "reviewer"))
        self.assertTrue(result.simulated)
        self.assertEqual((result.delegation, result.execution_authorization), ("none", False))
        plan = compile_plan(make_spec_plan())
        for rid, raw in result.handoffs.items():
            ho.verify_handoff(plan, rid, raw, expected_sha256=result.handoff_sha256[rid])
        self.assertEqual(result.artifacts["out/build.txt"], b"built:plan")

    def test_independent_roles_stay_serial(self):
        order = []
        hs = {rid: (lambda inner, rid: lambda c, i: (order.append(rid), inner(c, i))[1])(fn, rid)
              for rid, fn in handlers().items()}
        self.run_plan(hs=hs)
        self.assertEqual(order, list(compile_plan(make_spec_plan()).order))

    # --- role scope escalation --------------------------------------------
    def test_write_outside_ownership_refused(self):
        hs = handlers()

        def bad(ctx, inputs):
            ctx.write("out/build.txt", b"x")
            return {"n": 1}
        hs["planner"] = bad
        self.refuses("write-outside-ownership", self.run_plan, hs=hs)

    def test_swallowed_violation_still_fails(self):
        hs = handlers()

        def sneaky(ctx, inputs):
            try:
                ctx.write("out/build.txt", b"x")
            except hc.ProfileError:
                pass
            ctx.write("out/plan.json", b"plan")
            return {"n": 1}
        hs["planner"] = sneaky
        self.refuses("write-outside-ownership", self.run_plan, hs=hs)

    def test_read_outside_scope_refused(self):
        hs = handlers()
        hs["docs"] = lambda ctx, i: ctx.read("roles/planner.md") and {"n": 0}
        self.refuses("read-outside-scope", self.run_plan, hs=hs)

    def test_context_bytes_drift_refused(self):
        files = dict(ROLE_FILES, **{"roles/builder.md": b"tampered\n"})
        hs = handlers()
        hs["docs"] = lambda ctx, i: (ctx.write("out/docs.md", b"d"), {"n": 0})[1]
        hs["builder"] = lambda ctx, i: (ctx.read("roles/builder.md"), {"n": 0})[1]
        self.refuses("context-drift", self.run_plan, hs=hs, files=files)

    def test_closed_context_unusable_after_teardown(self):
        leaked = []
        hs = handlers()
        inner = hs["planner"]
        hs["planner"] = lambda c, i: (leaked.append(c), inner(c, i))[1]
        self.run_plan(hs=hs)
        self.refuses("context-closed", leaked[0].write, "out/plan.json", b"x")

    def test_role_effect_escalation_refused(self):
        self.refuses_spec("effect-blocked", lambda v: v["roles"][0].update(effectClass="E3"))
        self.refuses_spec("effect-blocked", lambda v: v["roles"][0].update(effectClass="E4"))
        self.refuses_spec("excluded-effect", lambda v: v["roles"][0].update(effectClass="E5"))

    def test_effect_outside_declared_class_refused(self):
        # E1 role may not own write destinations; E2 role must own one; E0 holds nothing.
        self.refuses_spec("undeclared-effect",
                          lambda v: v["roles"][3].update(ownership=["out/r.md"]))
        self.refuses_spec("undeclared-effect", lambda v: v["roles"][1].update(ownership=[]))
        self.refuses_spec("undeclared-effect", lambda v: v["roles"][3].update(effectClass="E0"))

    def test_ownership_must_stay_in_private_out_root(self):
        self.refuses_spec("path-outside-surface",
                          lambda v: v["roles"][1].update(ownership=["src/x.md"]))
        self.refuses_spec("path-outside-surface",
                          lambda v: v["roles"][1].update(ownership=["out/x.py"]))
        self.refuses_spec("protected-component",
                          lambda v: v["roles"][1].update(ownership=["out/.git/x.md"]))

    def test_context_must_come_from_bound_profile(self):
        def alien(v):
            v["roles"][1]["context"] = [{"path": "roles/docs.md", "sha256": "1" * 64,
                                          "sizeBytes": 3}]
        self.refuses_spec("context-outside-profile", alien)
        self.refuses_spec("context-outside-profile", lambda v: v["roles"][1].update(
            context=[{"path": "roles/other.md", "sha256": "1" * 64, "sizeBytes": 3}]))

    def test_profile_binding(self):
        self.refuses_spec("profile-drift", lambda v: v.update(profileSha256="2" * 64))
        raw, kw = _c1()
        other = hc.compile_inventory(raw, **kw)
        self.refuses("profile-mismatch", compile_plan, make_spec_plan(), profile=other)
        self.refuses("profile-mismatch", compile_plan, make_spec_plan(), profile=None)

    # --- ownership, dependencies ------------------------------------------
    def test_ownership_overlap_refused(self):
        self.refuses_spec("ownership-overlap",
                          lambda v: v["roles"][1].update(ownership=["out/build.txt"]))
        self.refuses_spec("ownership-overlap",
                          lambda v: v["roles"][1].update(ownership=["out/BUILD.txt"]))

    def test_dependency_cycle_self_and_unknown_refused(self):
        self.refuses_spec("dependency-cycle", lambda v: v["roles"][2].update(
            dependencies=["reviewer"]))
        self.refuses_spec("dependency-cycle",
                          lambda v: v["roles"][1].update(dependencies=["docs"]))
        self.refuses_spec("unknown-dependency",
                          lambda v: v["roles"][1].update(dependencies=["ghost"]))

    def test_unordered_conflict_refused(self):
        # reviewer reads builder's output but declares no dependency edge.
        self.refuses_spec("unordered-conflict",
                          lambda v: v["roles"][3].update(dependencies=[]))
        # a read justified only by a transitive dependency compiles
        def transitive(v):
            v["roles"][3].update(reads=["out/build.txt", "out/plan.json"])
        compile_plan(self.mutated(transitive))
        # an edge pointing the wrong way (reader runs before the writer) refuses
        def backwards(v):
            v["roles"][3].update(dependencies=[])
            v["roles"][0].update(dependencies=["planner", "reviewer"])
        self.refuses_spec("read-before-write", backwards)

    def mutated(self, mutate):
        value = make_spec_plan()
        mutate(value)
        return value

    def test_case_alias_paths_refused(self):
        self.refuses_spec("path-alias", lambda v: v["roles"][3].update(reads=["out/BUILD.txt"]))
        self.refuses_spec("path-alias", lambda v: v["roles"][3].update(
            reads=["out/build.txt"], context=ctx_rows("reviewer")) or v["roles"][1].update(
            reads=["roles/REVIEWER.md"], context=ctx_rows("docs"), effectClass="E2"))

    def test_read_of_unowned_unknown_path_refused(self):
        self.refuses_spec("read-outside-scope",
                          lambda v: v["roles"][3].update(reads=["out/nobody.txt"]))

    def test_structure_and_budget_refusals(self):
        self.refuses_spec("invalid-role", lambda v: v["roles"].append(deepcopy(v["roles"][0])
                                                                      ) or v["roles"].extend(
            [deepcopy(v["roles"][1]) for _ in range(8)]))
        self.refuses_spec("duplicate-or-unordered-inventory",
                          lambda v: v["roles"].reverse())
        self.refuses_spec("inventory-budget-exceeded", lambda v: v["roles"][1].update(
            ownership=[f"out/f{i:02d}.md" for i in range(33)]))
        self.refuses_spec("unsupported-version", lambda v: v.update(format="x"))
        self.refuses_spec("unsupported-profile", lambda v: v.update(executionAuthorization=True))
        self.refuses_spec("invalid-profile", lambda v: v.update(extra=1))
        self.refuses_spec("invalid-schema", lambda v: v["roles"][1].update(output=[]))
        self.refuses_spec("invalid-role-id", lambda v: v["roles"][1].update(roleId="a b"))
        value = make_spec_plan()
        self.refuses("input-drift", ho.compile_plan, json.dumps(value).encode(),
                     expected_input_sha256="3" * 64, profile=PROFILE)

    # --- handoff schema forgery -------------------------------------------
    def handoff(self):
        result = self.run_plan()
        plan = compile_plan(make_spec_plan())
        return plan, json.loads(result.handoffs["builder"])

    def forge(self, mutate, reason, role_id="builder"):
        plan, record = self.handoff()
        mutate(record)
        raw = canonical(record)
        self.refuses(reason, ho.verify_handoff, plan, role_id, raw,
                     expected_sha256=sha256(raw).hexdigest())

    def test_handoff_forgery_refused(self):
        self.forge(lambda r: r.update(extra=1), "invalid-handoff")
        self.forge(lambda r: r.update(executionAuthorization=True), "invalid-handoff")
        self.forge(lambda r: r.update(format="braid-harness-handoff/v0.2"), "invalid-handoff")
        self.forge(lambda r: r.update(planSha256="4" * 64), "handoff-plan-mismatch")
        self.forge(lambda r: r.update(roleId="planner"), "handoff-role-mismatch")
        self.forge(lambda r: r["outputs"].update(n="7"), "invalid-output")
        self.forge(lambda r: r["outputs"].update(n=10 ** 6), "output-budget-exceeded")
        self.forge(lambda r: r["outputs"].update(smuggled=1), "invalid-output")
        self.forge(lambda r: r.update(outputSha256="5" * 64), "handoff-output-mismatch")
        self.forge(lambda r: r["dependencies"].update(docs="6" * 64), "handoff-dependencies")
        self.forge(lambda r: r["dependencies"].clear(), "handoff-dependencies")
        self.forge(lambda r: r["artifacts"].update({"out/other.txt": "7" * 64}),
                   "handoff-artifacts")
        self.forge(lambda r: r["artifacts"].clear(), "handoff-artifacts")

    def test_handoff_trusted_hash_and_role_checked(self):
        plan, record = self.handoff()
        raw = canonical(record)
        self.refuses("handoff-drift", ho.verify_handoff, plan, "builder", raw,
                     expected_sha256="8" * 64)
        self.refuses("unknown-role", ho.verify_handoff, plan, "ghost", raw,
                     expected_sha256=sha256(raw).hexdigest())
        self.refuses("invalid-expected-hash", ho.verify_handoff, plan, "builder", raw,
                     expected_sha256="short")

    def test_handoff_for_another_plan_refused(self):
        other = make_spec_plan(planId="plan-2")
        other_plan = compile_plan(other)
        result = self.run_plan(other_plan)
        plan = compile_plan(make_spec_plan())
        self.refuses("handoff-plan-mismatch", ho.verify_handoff, plan, "builder",
                     result.handoffs["builder"],
                     expected_sha256=result.handoff_sha256["builder"])

    # --- failure, cancellation, resume, stale -----------------------------
    def test_integration_failure_stops_dependents(self):
        hs = handlers()

        def boom(ctx, inputs):
            raise RuntimeError("secret path /etc")
        hs["builder"] = boom
        result = self.run_plan(hs=hs)
        self.assertEqual((result.status, result.reason, result.failed_role),
                         ("failed", "role-failed", "builder"))
        self.assertEqual(result.completed, ("docs", "planner"))
        self.assertEqual(result.skipped, ("builder", "reviewer"))
        self.assertNotIn("reviewer", result.handoffs)

    def test_invalid_output_and_missing_artifact_fail_run(self):
        hs = handlers()
        hs["planner"] = lambda c, i: (c.write("out/plan.json", b"p"), {"n": "x"})[1]
        self.assertEqual(self.run_plan(hs=hs).reason, "invalid-output")
        hs["planner"] = lambda c, i: {"n": 1}
        self.assertEqual(self.run_plan(hs=hs).reason, "artifact-missing")

    def test_reference_mismatch_and_checker_controls(self):
        result = self.run_plan(checker=lambda o, a: False)
        self.assertEqual((result.status, result.reason), ("failed", "reference-mismatch"))
        self.assertEqual(self.run_plan(checker=lambda o, a: 1).reason, "reference-mismatch")
        self.assertEqual(self.run_plan(checker=lambda o, a: 1 / 0).reason, "checker-raised")
        hs = handlers()
        self.refuses("checker-not-independent", self.run_plan, hs=hs,
                     checker=hs["planner"])
        self.refuses("helper-missing", self.run_plan, hs={"planner": hs["planner"]})
        self.refuses("helper-missing", self.run_plan,
                     hs=dict(handlers(), ghost=lambda c, i: {}))

    def test_cancellation_then_resumed_handoffs_match_uninterrupted_run(self):
        full = self.run_plan()
        calls = []

        def cancel():
            calls.append(1)
            return len(calls) > 2
        part = self.run_plan(cancel=cancel)
        self.assertEqual((part.status, part.reason), ("cancelled", "cancelled"))
        self.assertEqual(part.completed, ("docs", "planner"))
        self.assertEqual(part.skipped, ("builder", "reviewer"))
        resume = {r: (part.handoffs[r], part.handoff_sha256[r]) for r in part.completed}
        done = self.run_plan(resume_handoffs=resume, resume_artifacts=dict(part.artifacts))
        self.assertEqual(done.status, "completed")
        self.assertEqual(dict(done.handoff_sha256), dict(full.handoff_sha256))
        self.assertEqual(dict(done.artifacts), dict(full.artifacts))

    def test_resumed_roles_do_not_rerun(self):
        part = self.run_plan(cancel=lambda: True)
        self.assertEqual(part.completed, ())
        full = self.run_plan()
        ran = []
        hs = handlers()
        hs["planner"] = lambda c, i: ran.append("planner") or {"n": 1}
        resume = {r: (full.handoffs[r], full.handoff_sha256[r]) for r in ("docs", "planner")}
        result = self.run_plan(hs=hs, resume_handoffs=resume,
                               resume_artifacts={p: full.artifacts[p]
                                                 for p in ("out/plan.json", "out/docs.md")})
        self.assertEqual(ran, [])
        self.assertEqual(result.status, "completed")

    def test_stale_dependency_on_resume_refused(self):
        old = self.run_plan()
        newer = self.run_plan(hs=handlers(plan_n=5),
                              checker=lambda o, a: True)
        # builder handoff from the old run, planner handoff from the changed run.
        resume = {"planner": (newer.handoffs["planner"], newer.handoff_sha256["planner"]),
                  "builder": (old.handoffs["builder"], old.handoff_sha256["builder"])}
        arts = {"out/plan.json": newer.artifacts["out/plan.json"],
                "out/build.txt": old.artifacts["out/build.txt"]}
        self.refuses("stale-handoff", self.run_plan, resume_handoffs=resume,
                     resume_artifacts=arts)

    def test_resume_without_dependency_or_with_foreign_artifacts_refused(self):
        full = self.run_plan()
        resume = {"builder": (full.handoffs["builder"], full.handoff_sha256["builder"])}
        self.refuses("stale-handoff", self.run_plan, hs=handlers(plan_n=5),
                     resume_handoffs=resume,
                     resume_artifacts={"out/build.txt": full.artifacts["out/build.txt"]})
        resume = {"docs": (full.handoffs["docs"], full.handoff_sha256["docs"])}
        self.refuses("stale-handoff", self.run_plan, resume_handoffs=resume,
                     resume_artifacts={"out/docs.md": full.artifacts["out/docs.md"],
                                       "out/plan.json": b"poison"})
        self.refuses("stale-handoff", self.run_plan, resume_handoffs=resume,
                     resume_artifacts={"out/docs.md": b"altered"})
        self.refuses("unknown-role", self.run_plan,
                     resume_handoffs={"ghost": (b"{}", "9" * 64)})

    def test_forged_resume_handoff_refused(self):
        full = self.run_plan()
        record = json.loads(full.handoffs["docs"])
        record["outputs"]["n"] = 99
        raw = canonical(record)
        self.refuses("handoff-output-mismatch", self.run_plan,
                     resume_handoffs={"docs": (raw, sha256(raw).hexdigest())},
                     resume_artifacts={"out/docs.md": full.artifacts["out/docs.md"]})

    # --- tool scope --------------------------------------------------------
    def tool_plan(self, mutate=None, tool_spec=None):
        spec = tool_spec or make_spec(writes=["out/report.txt"], reads=[TOOL_READ])
        allowlist = ht.compile_allowlist([compile_spec(spec)])
        value = make_spec_plan()
        value["roles"][1] = role("docs", "docs", own=["out/docs.md", "out/report.txt"],
                                 tools=["count-words"])
        if mutate:
            mutate(value)
        return value, allowlist

    def test_tool_scope_runs_inside_role_and_binds_allowlist(self):
        value, allowlist = self.tool_plan()
        plan = compile_plan(value, allowlist=allowlist)
        self.assertEqual(plan.data["allowlistSha256"], allowlist.sha256)
        hs = handlers()

        def docs(ctx, inputs):
            result = ctx.tool("count-words", {"label": "x"})
            ctx.write("out/docs.md", b"d")
            ctx.write("out/report.txt", b"x:3")
            return {"n": result.output["count"]}
        hs["docs"] = docs
        files = dict(ROLE_FILES)
        result = ho.run_plan(plan, hs, reference, files=files, allowlist=allowlist,
                             helpers={"count-words": tool_helper},
                             checkers={"count-words": tool_checker})
        self.assertEqual(result.status, "completed")
        self.assertEqual(json.loads(result.handoffs["docs"])["outputs"], {"n": 3})
        self.refuses("invalid-allowlist", ho.run_plan, plan, hs, reference, files=files)

    def test_tool_outside_role_scope_refused(self):
        value, allowlist = self.tool_plan()
        plan = compile_plan(value, allowlist=allowlist)
        hs = handlers()
        hs["docs"] = lambda ctx, i: (ctx.write("out/docs.md", b"d"),
                                     ctx.write("out/report.txt", b"r"), {"n": 0})[2]
        hs["planner"] = lambda ctx, i: ctx.tool("count-words", {"label": "x"})
        files = dict(ROLE_FILES)
        self.refuses("tool-outside-role-scope", ho.run_plan, plan, hs, reference,
                     files=files, allowlist=allowlist)

    def test_tool_scope_escalation_refused(self):
        # tool writes a path the role does not own
        value, allowlist = self.tool_plan(lambda v: v["roles"][1].update(
            ownership=["out/docs.md"]))
        self.refuses("tool-scope-escalation", compile_plan, value, allowlist=allowlist)
        # tool reads a path the role cannot read
        value, allowlist = self.tool_plan(
            lambda v: v["roles"][1].update(context=ctx_rows("planner")))
        self.refuses("tool-scope-escalation", compile_plan, value, allowlist=allowlist)
        # tool effect class above the role ceiling (E1 role, E2 tool)
        value, allowlist = self.tool_plan()
        value["roles"][1].update(effectClass="E1", ownership=[])
        self.refuses("tool-scope-escalation", compile_plan, value, allowlist=allowlist)

    def test_tool_not_allowlisted_or_blocked_refused(self):
        value, allowlist = self.tool_plan()
        self.refuses("tool-not-allowlisted", compile_plan, value)
        value["roles"][1]["tools"] = ["ghost"]
        self.refuses("tool-not-allowlisted", compile_plan, value, allowlist=allowlist)
        spec = make_spec(effectClass="E3", writes=["out/report.txt"], reads=[TOOL_READ])
        value, allowlist = self.tool_plan(tool_spec=spec)
        self.refuses("effect-blocked", compile_plan, value, allowlist=allowlist)

    # --- hardening ---------------------------------------------------------
    def test_hand_built_or_forged_plan_never_runs(self):
        data = compile_plan(make_spec_plan()).to_dict()
        data["admission"] = {"state": "implemented", "blocker": None}
        data["executionAuthorization"] = True
        self.refuses("plan-not-compiled", ho.OrchestrationPlan, freeze(data), canonical(data))
        self.refuses("plan-not-compiled", ho.OrchestrationPlan, freeze(data), canonical(data),
                     object())
        self.refuses("unknown-role", compile_plan(make_spec_plan()).role, "ghost")

    def test_budget_refusals(self):
        big = [{"path": "roles/builder.md", "sha256": "1" * 64, "sizeBytes": 1}]
        self.refuses_spec("context-outside-profile",
                          lambda v: v["roles"][0].update(context=big))
        self.refuses_spec("context-outside-profile", lambda v: v["roles"][0].update(
            context=[{"path": ["x"], "sha256": "1" * 64, "sizeBytes": 1}]))
        hs = handlers()
        hs["planner"] = lambda c, i: (c.write("out/plan.json", b"x" * 40000), {"n": 1})[1]
        self.refuses("write-budget-exceeded", self.run_plan, hs=hs)

    def test_e1_role_must_read_something(self):
        self.refuses_spec("undeclared-effect", lambda v: v["roles"][3].update(
            context=[], reads=[], dependencies=[]))

    def test_cancel_and_resume_inputs_are_typed_refusals(self):
        self.refuses("cancel-raised", self.run_plan, cancel=lambda: 1 / 0)
        self.assertEqual(self.run_plan(cancel=lambda: 1).status, "cancelled")
        full = self.run_plan()
        self.refuses("invalid-input", self.run_plan, resume_handoffs={"docs": b"x"})
        self.refuses("invalid-input", self.run_plan, resume_handoffs={
            "docs": (full.handoffs["docs"], full.handoff_sha256["docs"])},
            resume_artifacts={"out/docs.md": "docs"})
        self.refuses("write-budget-exceeded", self.run_plan, resume_handoffs={
            "docs": (full.handoffs["docs"], full.handoff_sha256["docs"])},
            resume_artifacts={"out/docs.md": b"x" * 40000})

    def test_tool_refusal_is_latched_and_artifact_bound(self):
        value, allowlist = self.tool_plan()
        plan = compile_plan(value, allowlist=allowlist)
        files = dict(ROLE_FILES)
        kw = dict(files=files, allowlist=allowlist, helpers={"count-words": tool_helper},
                  checkers={"count-words": tool_checker})

        def docs_with(body):
            hs = handlers()

            def docs(ctx, inputs):
                body(ctx)
                return {"n": 0}
            hs["docs"] = docs
            return hs

        def swallow(ctx):
            try:
                ctx.tool("count-words", {"label": "y"})   # checker rejects this label
            except hc.ProfileError:
                pass
            ctx.write("out/docs.md", b"d")
            ctx.write("out/report.txt", b"r")
        self.refuses("check-failed", ho.run_plan, plan, docs_with(swallow), reference, **kw)

        def forge(ctx):
            ctx.tool("count-words", {"label": "x"})
            ctx.write("out/report.txt", b"forged")
        self.refuses("tool-artifact-mismatch", ho.run_plan, plan, docs_with(forge),
                     reference, **kw)

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

    def test_admission_cannot_be_raised_by_input(self):
        plan = compile_plan(make_spec_plan())
        self.assertEqual(plan.data["admission"]["state"], "blocked")
        for key in ("admission", "delegation", "parallelism", "order"):
            self.refuses("invalid-profile", compile_plan, dict(make_spec_plan(), **{key: {}}))


def _c1():
    value = make_inventory()
    return json.dumps(value).encode(), {"expected_input_sha256": sha256(
        canonical(value)).hexdigest()}


if __name__ == "__main__":
    unittest.main()
