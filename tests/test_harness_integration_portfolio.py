# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-050/T012 combined offline controls over the whole Braid Harness portfolio.

The SPEC-050/T002-T011 modules run together with the SPEC-049/T013 profile registry, on
synthetic doubles in temporary directories: components -> skills/tools/hooks -> orchestration
-> search -> curation -> automatic-promotion shadow/canary -> lifecycle (install, migrate,
canary, incident stop, revoke, rollback, uninstall, recover) -> read-only advisory views. No
host, model, network or paid route is used, hooks run on a fake clock and nothing native runs,
so these controls are deterministic engineering evidence only: not qualification, activation,
utility or product acceptance.
"""
import builtins
from contextlib import contextmanager
from dataclasses import replace
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from agent_braid import harness_auto_promotion as ap
from agent_braid import harness_components as hc
from agent_braid import harness_costs as hcost
from agent_braid import harness_curation as cur
from agent_braid import harness_hooks as hh
from agent_braid import harness_lifecycle as hl
from agent_braid import harness_orchestration as ho
from agent_braid import harness_promotion as pr
from agent_braid import harness_search as hs
from agent_braid import harness_skills as hsk
from agent_braid import harness_tools as ht
from agent_braid.system_one import canonical

from tests import test_harness_hooks as hooks_t
from tests import test_harness_orchestration as orch_t
from tests import test_harness_search as search_t
from tests import test_harness_skills as skills_t
from tests import test_harness_tools as tools_t
from tests.test_harness_advisory import run as advisory
from tests.test_harness_auto_promotion import CLEAR, CONTROL, PROPOSER, World
from tests.test_harness_components import _compile, make_inventory
from tests.test_harness_curation import APP, TRUST, library
from tests.test_harness_lifecycle import BLOCKED, ROBOT, V1, V2, V3
from tests.test_harness_promotion import HUMAN, IDENTITY, SCOPE, decide, h
from tests.test_harness_refinement import make_policy

# A private payload that must never appear in any status, receipt, advisory view or record.
MARKER = "PRIVATE-T012-MARKER"
SECRET = f"{MARKER} do not export".encode()
LESSON = h("ev-e1")  # cited by curation entry e1 and by the registry decision below
AUTHORITY_KEYS = ("executionAuthorization", "nativeExecution")
_WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


def authority_values(value):
    """Every ``executionAuthorization``/``nativeExecution`` value nested anywhere in ``value``."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key in AUTHORITY_KEYS:
                yield item
            yield from authority_values(item)
    elif isinstance(value, (list, tuple)):
        for item in value:
            yield from authority_values(item)


@contextmanager
def write_guard(allowed: Path):
    """Record every mutating filesystem call, resolved when it happens; on exit, refuse any
    path outside ``allowed``. Python-level calls only; native code is not observed."""
    seen = []

    def wrap(fn, mutating, paths=1):
        def inner(*args, **kwargs):
            if mutating(*args, **kwargs):
                seen.extend(os.path.realpath(a) for a in args[:paths]
                            if isinstance(a, (str, os.PathLike)))
            return fn(*args, **kwargs)
        return inner

    def opened(path, mode="r", *_, **kw):
        return any(c in str(kw.get("mode", mode)) for c in "wax+")

    def flagged(path, flags, *_, **__):
        return bool(flags & _WRITE_FLAGS)

    def always(*_, **__):
        return True

    patches = [mock.patch.object(builtins, "open", wrap(builtins.open, opened)),
               mock.patch.object(io, "open", wrap(io.open, opened)),
               mock.patch.object(os, "open", wrap(os.open, flagged))]
    for name in ("mkdir", "rmdir", "replace", "rename", "unlink", "remove", "symlink", "link",
                 "truncate", "chmod", "utime"):
        patches.append(mock.patch.object(os, name, wrap(getattr(os, name), always, 2)))
    # harness_lifecycle binds these at import time, so patching ``os`` does not reach them.
    for name in ("_replace", "_rename", "_unlink"):
        patches.append(mock.patch.object(hl, name, wrap(getattr(hl, name), always, 2)))
    for p in patches:
        p.start()
    try:
        yield seen
    finally:
        for p in reversed(patches):
            p.stop()
    real = os.path.realpath(allowed) + os.sep
    outside = [p for p in seen if not p.startswith(real)]
    if outside:
        raise AssertionError(f"write outside the temporary root: {outside}")


def canary_inputs(world, **over):
    return {"registration": world.registration, "evaluation": world.report,
            "base_files": world.base, "candidate_files": world.candidate, "proposer": PROPOSER,
            "acceptance": world.accept(), "identity": IDENTITY, "evaluated_at": 10} | CLEAR | over


class Portfolio(unittest.TestCase):
    """Shared temporary root with a sentinel outside the workspace."""

    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.outer = Path(tmp.name)
        self.root = self.outer / "ws"
        self.root.mkdir()
        (self.outer / "sentinel.txt").write_bytes(b"outside\n")
        self.records = []  # every record produced, checked for authority and leakage

    def tearDown(self):
        self.assertEqual(sorted(os.listdir(self.outer)), ["sentinel.txt", "ws"])
        self.assertEqual((self.outer / "sentinel.txt").read_bytes(), b"outside\n")

    def keep(self, value):
        """Keep one record; each must carry an authority flag (key or attribute)."""
        if isinstance(value, dict):
            self.assertTrue(any(k in value for k in AUTHORITY_KEYS), value)
            self.records.append(value)
        else:
            self.assertIs(value.executionAuthorization, False, value)
            self.records.append(value.to_dict() if hasattr(value, "to_dict") else
                                {"executionAuthorization": value.executionAuthorization})
        return value

    def refuses(self, error, expected, fn, /, *args, **kwargs):
        with self.assertRaises(error) as ctx:
            fn(*args, **kwargs)
        self.assertEqual(ctx.exception.reason, expected)

    def install(self, at=1, **over):
        return hl.install(self.root, **({"opt_in": True, "operator": HUMAN, "scope": SCOPE,
                                         "host": "claude", "identity": IDENTITY, "at": at} | over))

    def migrate(self, profile, at, expected=None, operator=HUMAN):
        return hl.migrate(self.root, profile.canonical_bytes,
                          expected_sha256=expected or profile.sha256, expires_at=1000,
                          operator=operator, at=at)

    def blob(self, profile):
        return self.root / hl.OWNED / hl.PROFILES / f"{profile.sha256}.json"

    def corrupt_state(self, old: bytes, new: bytes):
        state = self.root / hl.OWNED / hl.STATE
        state.write_bytes(state.read_bytes().replace(old, new))


class EndToEndTests(Portfolio):
    def component_layer(self):
        """T002-T006: compile, load, run and coordinate components on doubles."""
        for profile in (V1, V2):
            self.assertEqual(self.keep(profile.to_dict())["admission"]["state"], "implemented")
        catalog, _, _, contents = skills_t.compiled()
        session = hsk.SkillSession(catalog, constraints=skills_t.CONSTRAINTS)
        session.load("report", contents)  # pulls its dependency lazily
        self.assertEqual(session.loaded, ("triage", "report"))
        self.assertIn(hsk.TRUST, session.render())
        tool = ht.run_tool(tools_t.allowlist_for(tools_t.make_spec()), "count-words",
                           {"label": "n"}, helpers={"count-words": tools_t.helper},
                           checkers={"count-words": tools_t.checker},
                           files={tools_t.NOTES_PATH: tools_t.NOTES})
        self.assertEqual(self.keep(tool.to_dict())["output"], {"count": 3, "ok": True})
        hooks = hh.run_events(hooks_t.compile_spec(hooks_t.make_spec()),
                              [hooks_t.ev("e1", 1), hooks_t.ev("e2", 2, "Stop")],
                              handlers={"a-first": hooks_t.allow, "b-second": hooks_t.deny},
                              ledger=hh.ReplayLedger(), clock=hooks_t.FakeClock())
        self.assertEqual(self.keep(hooks.to_dict())["admission"]["state"], "blocked")
        plan = orch_t.compile_plan(orch_t.make_spec_plan())
        self.assertEqual(self.keep(plan.to_dict())["delegation"], "none")
        result = ho.run_plan(plan, orch_t.handlers(), orch_t.reference, files=orch_t.ROLE_FILES)
        self.assertEqual((result.status, result.simulated, result.delegation),
                         ("completed", True, "none"))
        self.assertIs(result.execution_authorization, False)

    def search_layer(self):
        """T007: synthetic equal-budget accounting is deterministic and does not reward volume."""
        manifest, policy = make_policy()

        def compare():
            props = {(1, 1, 1): search_t.proposal(manifest, "general", {search_t.G: b"g\n"}),
                     (1, 2, 1): search_t.proposal(manifest, "task", {search_t.T: b"t\n"})}
            lab = search_t.Lab(manifest, props, search_t.Flat())
            return lab, hs.compare_arms(manifest, policy, probe_budget=3, prober_id="prober-1",
                                        propose=lab.propose, probe=lab.probe)

        lab, record = compare()
        wire = self.keep(record.to_dict())
        self.assertEqual(record.sha256, compare()[1].sha256)
        executed = sum(a["executedProbes"] for a in wire["arms"])
        self.assertEqual(executed, sum(1 for r in lab.requests if r.scope != "base"))
        self.assertTrue(all(a["executedProbes"] <= 3 and not a["overspent"]
                            for a in wire["arms"]))
        self.assertFalse(wire["volumeScored"] or wire["utilityClaim"])
        self.assertEqual(wire["evidence"], "synthetic-offline-doubles")
        self.assertEqual(hcost.CASH_CAP_EUR_CENTS, 0)  # a configured cap, not a measured cost

    def assert_not_active(self):
        status = hl.status(self.root)
        self.assertEqual((status["activation"], status["ordinaryUse"], status["export"]),
                         (hl.ACTIVATION, "unavailable", "disabled"))

    def test_the_portfolio_runs_end_to_end_offline_and_grants_nothing(self):
        world = World(evidence=[LESSON])
        store = library("e1", "e2")
        context = {"taskStartedAt": 1000, **APP}
        with write_guard(self.root) as writes:
            self.component_layer()
            self.search_layer()
            # T008: curated retrieval serves both lessons before revocation.
            served = self.keep(cur.retrieve(store, context, max_entries=4, max_bytes=4096, **TRUST))
            self.assertEqual([r["id"] for r in served.served], ["e1", "e2"])
            # T009: the production policy abstains on the current pending endpoints.
            production = ap.assess(ap.build_policy(CONTROL | {"tolerablePendingEndpoints": []}),
                                   world.record, registry=world.registry, **canary_inputs(world))
            self.assertEqual(self.keep(production).to_dict()["reason"], "pending-endpoints")
            self.assertEqual((production.outcome, production.rule), ("abstain", 12))
            # T011: install, migrate twice, store a private record and a registry.
            self.keep(self.install())
            self.keep(self.migrate(V1, at=2))
            self.keep(self.migrate(V2, at=3))
            private = hl.retain(self.root, SECRET, kind="trace", retain_until=500, at=4)
            first = self.keep(decide(at=5, evidence=[LESSON]))
            second = self.keep(decide(at=6, rollback=first.to_dict()["profileSha256"]))
            registry = (pr.ProfileRegistry.empty(SCOPE).begin(first, current=IDENTITY, at=20)
                        .commit(current=IDENTITY, at=20).begin(second, current=IDENTITY, at=20)
                        .commit(current=IDENTITY, at=20))
            self.keep(hl.save_registry(self.root, registry, at=20))
            # Shadow -> canary through the persisted registry; a canary never activates.
            shadow = self.keep(ap.PolicyRun(ap.build_policy(CONTROL)).enable(HUMAN, at=21))
            run = self.keep(hl.begin_canary(self.root, shadow, world.record, at=22,
                                            **canary_inputs(world)))
            step = self.keep(hl.observe_canary(self.root, run, "ok", current=IDENTITY, at=23))
            self.assert_not_active()
            # Incident stop halts and rolls the registry back to the prior profile; the canary
            # run observed on the halted installation stops too, and only a human clears it.
            stop = self.keep(hl.incident_stop(self.root, at=24))
            self.assertIsNone(stop.registryFailure)
            self.assertEqual(hl.load_registry(self.root).active, first.sha256)
            halted = self.keep(hl.observe_canary(self.root, step.run, "ok", current=IDENTITY,
                                                 at=24))
            self.assertEqual(halted.run.journal[-1]["reason"], "incident-stop")
            states = [shadow.state, run.state, step.run.state, halted.run.state]
            self.refuses(hl.LifecycleError, "incident-stop", self.migrate, V3, at=25)
            self.keep(hl.clear_incident(self.root, operator=HUMAN, evidence=h("pm"), at=25))
            # One revocation reaches the persisted T013 registry and the T008 store together.
            revoked_registry, curated = hl.revoke(self.root, LESSON, at=200,
                                                  reason="lesson-revoked", store=store)
            self.keep(curated)
            persisted = hl.load_registry(self.root)
            self.assertEqual(persisted.sha256, revoked_registry.sha256)
            self.assertIsNone(persisted.active)
            self.assertIn(LESSON, persisted.revoked)
            self.assertIs(hl.status(self.root)["registryConsistent"], True)
            self.assertEqual(curated.revoked, ("e1",))
            after = self.keep(cur.retrieve(curated.store, context, max_entries=4,
                                           max_bytes=4096, **TRUST))
            self.assertEqual([r["id"] for r in after.served], ["e2"])
            # Human rollback keeps the prior profile byte for byte.
            status = self.keep(hl.rollback(self.root, operator=HUMAN, at=201, reason="downgrade"))
            self.assertEqual(status["current"]["sha256"], V1.sha256)
            self.assertEqual(hl.read_profile(self.root, V1.sha256), V1.canonical_bytes)
            self.assert_not_active()
            # T010 read-only advisory views over what the lifecycle stored.
            views = [advisory("capabilities", "--workspace", self.root),
                     advisory("profile-inventory", "--workspace", self.root,
                              "--profile", self.blob(V1), "--sha256", V1.sha256),
                     advisory("profile-diff", "--workspace", self.root,
                              "--base", self.blob(V1), "--candidate", self.blob(V2)),
                     advisory("status", "--workspace", self.root, "--registry",
                              self.root / hl.OWNED / hl.REGISTRY)]
            for code, view in views:
                self.assertEqual((code, view["status"]), (0, "ok"), view)
                self.keep(view)
            self.assertEqual(views[1][1]["result"]["authenticity"], "hash-matched")
            self.keep(hl.status(self.root, now=600))
            # The marker is only in its private blob, never in any other owned file.
            owned = self.root / hl.OWNED
            for path in owned.rglob("*"):
                if path.is_file() and path != owned / hl.PRIVATE / private:
                    self.assertNotIn(MARKER.encode(), path.read_bytes(), path)
            receipt = self.keep(hl.uninstall(self.root, operator=HUMAN, at=202))
            self.keep(hl.recover(self.root))
        # The guard observed the lifecycle's own writes, all inside the workspace.
        self.assertIn(os.path.realpath(owned / hl.STATE), writes)
        # Nothing reached ``active`` at any stage, and activation always refuses.
        self.assertNotIn("active", states)
        self.assertEqual(states[-1], "stopped")
        self.refuses(hl.LifecycleError, "activation-requires-adoption", hl.activate, self.root)
        # Every record carries executionAuthorization (and nativeExecution) false.
        flags = list(authority_values(self.records))
        self.assertTrue(flags and all(f is False for f in flags))
        # The private payload never leaves its blob: only its hash is reported.
        text = json.dumps(self.records, sort_keys=True, default=str)
        self.assertNotIn(MARKER, text)
        self.assertIn(private, text)
        # Uninstall removed everything it owned and recover left no residue.
        self.assertIn(f"{hl.PRIVATE}/{private}", [r["path"] for r in receipt["removed"]])
        self.assertEqual((os.listdir(self.root), hl.residue(self.root)), ([], []))

    def test_every_component_class_stays_below_qualified(self):
        for cls in hc.CLASSES:
            for effect in hc.EFFECTS:
                if effect == "E5":
                    self.refuses(hc.ProfileError, "excluded-effect", hc.derive_admission,
                                 cls, effect)
                    continue
                state, _ = hc.derive_admission(cls, effect)
                self.assertIn(state, ("implemented", "blocked"), (cls, effect))
        self.assertEqual(BLOCKED.to_dict()["admission"]["state"], "blocked")
        self.assertIs(pr.AUTOMATIC_PROMOTION, False)


class AdversarialControlTests(Portfolio):
    """Tampered, stale, drifted and forged inputs each refuse across module boundaries."""

    def setUp(self):
        super().setUp()
        self.install()
        self.migrate(V1, at=2)

    def test_tampered_profiles_refuse_everywhere(self):
        tampered = V2.canonical_bytes.replace(b'"version":2', b'"version":3')
        self.refuses(hc.ProfileError, "profile-drift", hc.verify_profile, tampered,
                     expected_sha256=V2.sha256)
        self.refuses(hl.LifecycleError, "profile-drift", hl.migrate, self.root, tampered,
                     expected_sha256=V2.sha256, expires_at=100, operator=HUMAN, at=3)
        self.migrate(V2, at=3)
        self.blob(V1).write_bytes(V2.canonical_bytes)  # a valid profile under the wrong name
        self.refuses(hl.LifecycleError, "prior-profile-unavailable", hl.rollback, self.root,
                     operator=HUMAN, at=4, reason="downgrade")
        self.assertEqual(hl.status(self.root)["current"]["sha256"], V2.sha256)
        self.refuses(hl.LifecycleError, "profile-unavailable", hl.read_profile, self.root,
                     V1.sha256)
        self.assertTrue(self.blob(V1).exists())  # refused by the hash check, not absence
        code, view = advisory("profile-inventory", "--workspace", self.root,
                              "--profile", self.blob(V1), "--sha256", V1.sha256)
        self.assertEqual((code, view["status"], view["reason"], view["executionAuthorization"]),
                         (2, "refused", "profile-drift", False))

    def test_stale_or_skipped_versions_refuse(self):
        self.refuses(hl.LifecycleError, "migration-not-linked", self.migrate, V3, at=3)
        self.refuses(hl.LifecycleError, "migration-not-linked", self.migrate, V1, at=3)
        self.refuses(hc.ProfileError, "stale-parent", _compile,
                     make_inventory(version=2, parentSha256=V2.sha256),
                     parent_raw=V1.canonical_bytes, expected_parent_sha256=V1.sha256)
        self.corrupt_state(hl.FORMAT.encode(), b"braid-harness-lifecycle/v0.2")
        self.refuses(hl.LifecycleError, "unsupported-version", hl.status, self.root)

    def test_identity_drift_blocks_canary_promotion_and_registry_service(self):
        world = World()
        drifted = IDENTITY | {"model": "model-b:2"}
        shadow = ap.PolicyRun(ap.build_policy(CONTROL)).enable(HUMAN, at=3)
        # A canary asserted under another identity refuses before any drift is recorded.
        self.refuses(hl.LifecycleError, "identity-drift", hl.begin_canary, self.root, shadow,
                     world.record, at=3, **canary_inputs(world, identity=drifted))
        self.assertEqual(hl.check_drift(self.root, drifted, at=4), ["stale-model"])
        self.refuses(hl.LifecycleError, "requalification-required", hl.begin_canary, self.root,
                     shadow, world.record, at=5, **canary_inputs(world))
        self.refuses(hl.LifecycleError, "requalification-required", self.migrate, V2, at=5)
        registry = pr.ProfileRegistry.empty(SCOPE).begin(decide(at=5), current=IDENTITY, at=6)
        registry = registry.commit(current=IDENTITY, at=6)
        self.assertEqual(registry.resolve(drifted, cohort="synthetic").reason, "stale-model")

    def test_forged_records_refuse(self):
        legit = orch_t.compile_plan(orch_t.make_spec_plan())
        self.refuses(hc.ProfileError, "plan-drift", ho.verify_plan, legit.canonical_bytes,
                     expected_sha256=sha256(b"other").hexdigest(), profile=orch_t.PROFILE)
        plan = legit.to_dict()
        plan["admission"] = {"state": "enabled", "blocker": None}
        raw = canonical(plan)
        self.refuses(hc.ProfileError, "plan-drift", ho.verify_plan, raw,
                     expected_sha256=sha256(raw).hexdigest(), profile=orch_t.PROFILE)
        for spec in (tools_t, hooks_t):
            with self.subTest(module=spec.__name__):
                self.refuses(hc.ProfileError, "unsupported-profile", spec.compile_spec,
                             spec.make_spec(executionAuthorization=True))
        for over in ({"adoption": "adopted"}, {"executionAuthorization": True}):
            with self.subTest(over=over):
                self.refuses(ap.AutoPromotionError, "invalid-policy", ap.build_policy,
                             CONTROL | over)
        self.refuses(ap.AutoPromotionError, "invalid-state", ap.PolicyRun,
                     ap.build_policy(CONTROL), "active")
        run = ap.PolicyRun(ap.build_policy(CONTROL))
        self.refuses(ap.AutoPromotionError, "activation-requires-adoption", run.activate)
        self.refuses(ap.AutoPromotionError, "invalid-state", replace, run, state="active")
        self.corrupt_state(b'"executionAuthorization":false', b'"executionAuthorization":true')
        self.refuses(hl.LifecycleError, "invalid-state", hl.status, self.root)

    def test_automatic_operators_and_blocked_profiles_cannot_change_anything(self):
        self.refuses(hl.LifecycleError, "automatic-promotion-disabled", self.migrate, V2, at=3,
                     operator=ROBOT)
        self.refuses(hl.LifecycleError, "automatic-promotion-disabled", hl.uninstall, self.root,
                     operator=ROBOT, at=3)
        self.refuses(ap.AutoPromotionError, "automatic-promotion-disabled",
                     ap.PolicyRun(ap.build_policy(CONTROL)).enable, ROBOT, at=3)
        self.refuses(hl.LifecycleError, "profile-blocked", self.migrate, BLOCKED, at=3)
        self.assertEqual(hl.status(self.root)["current"]["sha256"], V1.sha256)


class CrossHostAndRecoveryTests(Portfolio):
    def test_only_the_observed_host_is_supported_and_codex_refuses_everywhere(self):
        self.assertEqual(hl.SUPPORTED_HOSTS, ("claude",))
        self.refuses(hl.LifecycleError, "unsupported-host", self.install, host="codex")
        self.refuses(hc.ProfileError, "host-refused", _compile, make_inventory(host="codex"))
        forged = canonical(V1.to_dict() | {"host": "codex"})  # a stored record relabelled
        self.refuses(hc.ProfileError, "host-refused", hc.verify_profile, forged,
                     expected_sha256=sha256(forged).hexdigest())
        self.assertEqual(hh.matrix_record("codex")["modeled"], [])
        self.assertEqual(hh.event_status("codex", "PreToolUse"), "unavailable")
        self.assertEqual(hh.matrix_record("claude")["observation"], "modeled-not-observed")
        code, view = advisory("capabilities", "--workspace", self.root)
        hosts = view["result"]["hosts"]
        self.assertEqual((code, hosts["claude"]["qualification"]), (0, "unqualified"))
        self.assertIsNone(hosts["codex"]["observedBuild"])
        self.assertEqual(os.listdir(self.root), [])

    def test_interrupted_install_and_uninstall_recover_without_residue(self):
        with mock.patch.object(hl, "_rename", side_effect=OSError("crash")):
            self.refuses(hl.LifecycleError, "write-failed", self.install)
        self.assertEqual(hl.status(self.root)["state"], "not-installed")
        self.install()
        self.migrate(V1, at=2)
        hl.retain(self.root, SECRET, kind="trace", retain_until=10, at=3)
        with mock.patch.object(hl, "_unlink", side_effect=OSError("crash")):
            self.refuses(hl.LifecycleError, "cleanup-incomplete", hl.uninstall, self.root,
                         operator=HUMAN, at=4)
        self.assertEqual(hl.status(self.root)["state"], "not-installed")
        self.assertEqual(len(hl.residue(self.root)), 1)
        hl.recover(self.root)
        self.assertEqual((os.listdir(self.root), hl.residue(self.root)), ([], []))


class WriteGuardTests(unittest.TestCase):
    def test_the_guard_detects_writes_outside_its_root(self):
        writes = {
            "open": lambda d: Path(d, "x").write_bytes(b"x"),
            "os.open": lambda d: os.close(os.open(Path(d, "x"), os.O_WRONLY | os.O_CREAT)),
            "mkdir": lambda d: os.mkdir(Path(d, "x")),
            "rename": lambda d: (Path(d, "a").write_bytes(b""),
                                 os.rename(Path(d, "a"), Path(d, "b"))),
            "symlink-escape": lambda d: Path(d, "link").write_bytes(b"x"),
        }
        for name, write in writes.items():
            with self.subTest(name), tempfile.TemporaryDirectory() as allowed, \
                    tempfile.TemporaryDirectory() as other:
                target = other
                if name == "symlink-escape":  # a link inside the root that points outside
                    os.symlink(Path(other, "real"), Path(allowed, "link"))
                    target = allowed
                with self.assertRaises(AssertionError):
                    with write_guard(Path(allowed)):
                        write(target)
                        if name == "symlink-escape":
                            os.unlink(Path(allowed, "link"))  # deleted before exit
        with tempfile.TemporaryDirectory() as allowed, write_guard(Path(allowed)):
            Path(allowed, "y").write_bytes(b"y")


if __name__ == "__main__":
    unittest.main()
