# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-065 T007 probe catalog and evidence runner (procedure_009: shape, pass rule, no record).

Unit level only. No catalog helper is executed against the host here: the executors, the process
scan, the session driver and the backend are deterministic doubles, and nothing launches
``claude``, ``sandbox-exec`` or an external network connection. Real but harmless local pieces:
the helper prelude run on its own scripted errors, the arena on loopback and a temporary
directory, and ``uncontained_executor`` over trivial sources. Live controls are skipped unless
``BRAID_T007_LIVE_CONTROLS=1`` (CI never sets it).
"""
from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import threading
from types import SimpleNamespace
import unittest
from unittest import mock

from agent_braid import harness_containment_macos as mac
from agent_braid import harness_host_claude as hc
from agent_braid import harness_lab as lab
from agent_braid import harness_qualification_probes as q
from agent_braid.system_one import canonical

ENV_HASH = "7" * 64
OAUTH_STREAM = (canonical({"type": "system", "subtype": "init", "apiKeySource": "oauth"}) + b"\n"
                + canonical({"type": "result", "subtype": "success", "is_error": False}) + b"\n")
CONTRACT_IDS = (
    [f"FS-0{i}" for i in range(1, 8)] + [f"NET-0{i}" for i in range(1, 9)]
    + [f"CRED-0{i}" for i in range(1, 8)] + [f"PROC-0{i}" for i in range(1, 9)] + ["HOST-01"])


def environment(**over):
    value = {"environmentSha256": ENV_HASH, "probeCatalogSha256": q.CATALOG_SHA256, "backend": "double"}
    value.update(over)
    return value


def lines(mapping):
    return b"".join(canonical({"attempt": n, "outcome": o, "errno": "NONE", "info": False}) + b"\n"
                    for n, o in mapping.items())


class FakeArena:
    """Arena double: no filesystem tree, listener or process; independent observations scripted."""

    def __init__(self, world, parent, *, public, proxy, proxy_enforcing, spawn_sibling):
        self.world = world
        self.nonce, self.marker = "abcdef012345", "braid-dummy-fake-marker"
        self.work = Path(parent)
        self.document = {"proxy": proxy, "proxy_enforcing": proxy_enforcing}
        self.closed = False

    def snapshot(self):
        return {}

    def changed(self, before):
        return list(self.world.changed.get(self.world.current, []))

    def hit_counts(self):
        return dict(self.world.hits.get(self.world.current, {}))

    def close(self):
        self.closed = True


class World:
    """Scripts both executors, the process scan, the cancel check and the session driver."""

    def __init__(self, test):
        self.tmp = Path(tempfile.mkdtemp(prefix="braid-t007-"))
        test.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        self.mode = None
        self.current = None
        self.control = {}  # probe id -> {attempt: outcome} overrides for the control
        self.contained = {}  # probe id -> {attempt: outcome} overrides for the contained run
        self.changed, self.hits = {}, {}
        self.contained_survivors = 0
        self.unsettled = set()
        self.raises = {}  # (mode, probe id) -> exception
        self.killed, self.arenas, self.executed = [], [], []
        self.sessions = {"CRED-05": OAUTH_STREAM, "HOST-01": OAUTH_STREAM, "NET-05-CLI": OAUTH_STREAM}
        self.egress = {"admitted": ["api.anthropic.com:443"], "unexpectedDirect": 0}
        self.cancel = {"survivors": 0, "settled": True, "cancelled": True}
        self.session_calls = []

    def probe_of(self, source: bytes):
        text = source.decode()
        found = [p for p in q.CATALOG if p.runner == "helper" and p.source_template in text]
        assert len(found) == 1
        return found[0]

    def arena(self, parent, **kwargs):
        arena = FakeArena(self, self.tmp, **kwargs)
        self.arenas.append(arena)
        return arena

    def run(self, mode):
        def execute(source, workdir, wall, arena):
            probe = self.probe_of(source)
            self.mode, self.current = mode, probe.id
            self.executed.append((mode, probe.id, wall))
            error = self.raises.get((mode, probe.id))
            if error is not None:
                raise error
            if mode == "uncontained-control":
                outcomes = {n: "allowed" for n in probe.counted}
                outcomes.update(self.control.get(probe.id, {}))
            else:
                base = "allowed" if probe.functional else "denied"
                outcomes = {n: base for n in probe.counted}
                outcomes.update(self.contained.get(probe.id, {}))
            outcomes.pop("cancel-settlement", None)
            return q.ExecResult(lines(outcomes), 0, settled=probe.id not in self.unsettled
                                or mode == "uncontained-control")
        return execute

    def scan(self, nonce):
        if self.mode == "uncontained-control":
            return [4242]
        return [4343] * self.contained_survivors

    def kill(self, pids):
        self.killed.extend(pids)

    def driver(self, probe_id):
        self.session_calls.append(probe_id)
        egress = self.egress if probe_id == "NET-05-CLI" else None
        return q.SessionResult(self.sessions[probe_id], 0, egress=egress,
                               quota={"pre": {"fiveHourPercent": 10}})

    def runner(self, **over):
        args = dict(control=self.run("uncontained-control"), contained=self.run("contained"),
                    arena_parent=self.tmp, proxy_address="127.0.0.1:45000", sessions=self.driver,
                    process_scan=self.scan, process_kill=self.kill, cancel_check=lambda: dict(self.cancel),
                    arena_factory=self.arena, clock=lambda: 1_800_000_000.0)
        args.update(over)
        return q.QualificationProbeRunner(**args)


def row(probe_id, control, contained, **extra):
    probe = q.BY_ID[probe_id]
    c = {n: control for n in probe.counted} if isinstance(control, str) else dict(control)
    k = {n: contained for n in probe.counted} if isinstance(contained, str) else dict(contained)
    base = {"settled": True, "escalated": False}
    return (dict(base, probe=probe_id, mode="uncontained-control", attempts=c),
            dict(base, probe=probe_id, mode="contained", attempts=k, **extra))


def passing_rows(skip=(), override=None):
    rows = []
    for probe in q.CATALOG:
        if probe.id in skip:
            continue
        control, contained = ("allowed", "allowed" if probe.functional else "denied")
        pair = (override or {}).get(probe.id) or row(probe.id, control, contained)
        rows.extend(pair)
    return rows


class CatalogShapeTests(unittest.TestCase):
    def test_ids_match_the_contract_plus_the_cli_variant(self):
        ids = [p.id for p in q.CATALOG]
        self.assertEqual(sorted(ids), sorted(CONTRACT_IDS + ["NET-05-CLI"]))
        self.assertEqual(len(ids), len(set(ids)))

    def test_every_effect_has_probes_and_host_is_functional(self):
        for effect in lab.ENFORCED_EFFECTS:
            self.assertTrue([p for p in q.CATALOG if p.effect == effect], effect)
        self.assertEqual({p.id for p in q.CATALOG if p.effect == "host"}, {"HOST-01"})
        self.assertEqual({p.id for p in q.CATALOG if p.functional}, {"NET-06", "HOST-01"})

    def test_session_probes_are_exactly_the_three_native_ones_within_the_cap(self):
        sessions = {p.id for p in q.CATALOG if p.runner == "session"}
        self.assertEqual(sessions, {"HOST-01", "CRED-05", "NET-05-CLI"})
        self.assertEqual(sum(p.sessions for p in q.CATALOG), q.MAX_PROBE_SESSIONS)
        with self.assertRaises(q.ProbeError):
            q._validate_catalog(q.CATALOG + (replace(q.BY_ID["HOST-01"], id="HOST-02"),))

    def test_every_helper_compiles_and_declares_named_attempts(self):
        for probe in q.CATALOG:
            if probe.runner != "helper":
                continue
            compile(q.render_source(probe, SimpleNamespace(document={"x": 1})).decode(), probe.id, "exec")
            self.assertTrue(probe.counted, probe.id)
            for name, _ in probe.attempts:
                self.assertRegex(name, r"\A[a-z0-9][a-z0-9-]*\Z")

    def test_every_escape_probe_has_a_positive_control_description(self):
        for entry in q.catalog_document()["probes"]:
            self.assertIn("uncontained" if entry["sessions"] == 0 else "self-test",
                          entry["positiveControl"])
            self.assertIn(entry["direction"], ("escape", "functional-control"))
            self.assertIn(entry["expected"], ("denied", "allowed"))

    def test_helpers_carry_no_operator_paths_or_real_secrets(self):
        for probe in q.CATALOG:
            text = probe.source_template
            self.assertNotIn("/Users/", text)
            self.assertNotIn("sk-ant", text)

    def test_catalog_hash_is_stable_and_binds_the_sources(self):
        self.assertEqual(q.CATALOG_SHA256, q.catalog_sha256())
        changed = list(q.CATALOG)
        changed[0] = replace(changed[0], body=changed[0].body + "\n# edited\n")
        self.assertNotEqual(q.catalog_sha256(changed), q.CATALOG_SHA256)
        weaker = list(q.CATALOG)
        weaker[1] = replace(weaker[1], expected="allowed")
        self.assertNotEqual(q.catalog_sha256(weaker), q.CATALOG_SHA256)

    def test_policy_binding_checks_the_hash(self):
        self.assertTrue(q.policy_binds_catalog(SimpleNamespace(probe_catalog_sha256=q.CATALOG_SHA256)))
        self.assertFalse(q.policy_binds_catalog(SimpleNamespace(probe_catalog_sha256="0" * 64)))

    def test_pre_session_subset_matches_catalog_expectations(self):
        for probe_id, expected in mac.F4_PROBES:
            self.assertEqual(q.BY_ID[probe_id].expected, expected)
        self.assertEqual(q.F4_IDS, tuple(p for p, _ in mac.F4_PROBES))


class PassRuleTests(unittest.TestCase):
    def test_all_denied_with_passing_controls_is_enforced_and_satisfies_the_rule(self):
        summary = q.summarize(passing_rows())
        self.assertTrue(all(e["status"] == "enforced" for e in summary["effects"].values()))
        self.assertTrue(summary["hostFunctional"])
        self.assertTrue(summary["passRuleSatisfied"])
        self.assertEqual(summary["missingProbes"], [])
        self.assertFalse(summary["qualificationRecordWritten"])
        self.assertFalse(summary["executionAuthorization"])

    def test_one_allowed_escape_makes_the_effect_not_enforced(self):
        for probe in q.CATALOG:
            if probe.functional or probe.runner == "session" and probe.id != "CRED-05":
                continue
            with self.subTest(probe=probe.id):
                names = probe.counted
                contained = {n: "denied" for n in names} | {names[0]: "allowed"}
                summary = q.summarize(passing_rows(override={probe.id: row(probe.id, "allowed", contained)}))
                self.assertEqual(summary["effects"][probe.effect]["status"], "not-enforced")
                self.assertEqual(summary["notEnforced"], [probe.effect])
                self.assertFalse(summary["passRuleSatisfied"])

    def test_failing_positive_control_is_inconclusive_and_blocks(self):
        override = {"FS-01": row("FS-01", {"outside-dir": "denied", "tmp-path": "allowed",
                                            "decoy-home": "allowed", "decoy-repo": "allowed"}, "denied")}
        summary = q.summarize(passing_rows(override=override))
        self.assertEqual(summary["probes"]["FS-01"]["status"], "inconclusive")
        self.assertEqual(summary["probes"]["FS-01"]["reason"], "positive-control-failed")
        self.assertEqual(summary["effects"]["filesystem"]["status"], "inconclusive")
        self.assertEqual(summary["effects"]["filesystem"]["failing"], ["FS-01"])
        self.assertFalse(summary["passRuleSatisfied"])

    def test_control_failure_does_not_hide_an_escape_that_was_observed(self):
        override = {"FS-01": row("FS-01", "denied", {"outside-dir": "allowed", "tmp-path": "denied",
                                                      "decoy-home": "denied", "decoy-repo": "denied"})}
        summary = q.summarize(passing_rows(override=override))
        self.assertEqual(summary["effects"]["filesystem"]["status"], "not-enforced")

    def test_missing_probe_leaves_the_profile_not_qualified(self):
        summary = q.summarize(passing_rows(skip=("NET-03",)))
        self.assertEqual(summary["missingProbes"], ["NET-03"])
        self.assertEqual(summary["effects"]["network"]["status"], "inconclusive")
        self.assertEqual(summary["effects"]["network"]["missing"], ["NET-03"])
        self.assertFalse(summary["passRuleSatisfied"])

    def test_missing_control_or_contained_mode_is_inconclusive(self):
        control, contained = row("PROC-01", "allowed", "denied")
        for rows in ([contained], [control]):
            summary = q.summarize([r for r in passing_rows(skip=("PROC-01",))] + rows)
            self.assertEqual(summary["probes"]["PROC-01"]["status"], "inconclusive")
            self.assertEqual(summary["effects"]["process"]["status"], "inconclusive")

    def test_missing_host_probe_blocks_even_with_four_enforced_effects(self):
        summary = q.summarize(passing_rows(skip=("HOST-01",)))
        self.assertTrue(all(e["status"] == "enforced" for e in summary["effects"].values()))
        self.assertFalse(summary["hostFunctional"])
        self.assertFalse(summary["passRuleSatisfied"])

    def test_failed_host_session_blocks(self):
        override = {"HOST-01": row("HOST-01", "allowed", "denied")}
        summary = q.summarize(passing_rows(override=override))
        self.assertFalse(summary["hostFunctional"])
        self.assertFalse(summary["passRuleSatisfied"])

    def test_functional_failure_is_inconclusive_not_an_escape(self):
        override = {"NET-06": row("NET-06", "allowed", "denied")}
        summary = q.summarize(passing_rows(override=override))
        self.assertEqual(summary["effects"]["network"]["status"], "inconclusive")
        self.assertEqual(summary["notEnforced"], [])

    def test_independent_observation_escalates_only_toward_allowed(self):
        escalated = {"FS-01": row("FS-01", "allowed", "denied", escalated=True)}
        summary = q.summarize(passing_rows(override=escalated))
        self.assertEqual(summary["effects"]["filesystem"]["status"], "not-enforced")
        # a contained row whose attempts say allowed stays allowed whatever else was observed
        stays = {"FS-01": row("FS-01", "allowed", "allowed", escalated=False)}
        self.assertEqual(q.summarize(passing_rows(override=stays))["probes"]["FS-01"]["status"], "allowed")

    def test_unsettled_contained_child_counts_as_an_escape(self):
        control, contained = row("PROC-02", "allowed", "denied")
        contained["settled"] = False
        summary = q.summarize(passing_rows(override={"PROC-02": (control, contained)}))
        self.assertEqual(summary["effects"]["process"]["status"], "not-enforced")

    def test_inconclusive_contained_attempt_never_counts_as_denied(self):
        contained = {"outside-dir": "denied", "tmp-path": "inconclusive", "decoy-home": "denied",
                     "decoy-repo": "denied"}
        summary = q.summarize(passing_rows(override={"FS-01": row("FS-01", "allowed", contained)}))
        self.assertEqual(summary["probes"]["FS-01"]["status"], "inconclusive")
        self.assertFalse(summary["probes"]["FS-01"]["pass"])

    def test_row_outcome_semantics(self):
        probe, functional = q.BY_ID["FS-01"], q.BY_ID["NET-06"]
        self.assertEqual(q.row_outcome(probe, {n: "denied" for n in probe.counted}), "denied")
        self.assertEqual(q.row_outcome(probe, {}), "inconclusive")
        self.assertEqual(q.row_outcome(probe, {"outside-dir": "allowed"}), "allowed")
        self.assertEqual(q.row_outcome(functional, {"allowed-endpoint": "allowed"}), "allowed")
        self.assertEqual(q.row_outcome(functional, {"allowed-endpoint": "denied"}), "denied")
        self.assertEqual(q.row_outcome(functional, {"allowed-endpoint": "inconclusive"}), "inconclusive")


class HelperProtocolTests(unittest.TestCase):
    PROBE = q.BY_ID["PROC-03"]

    def test_prelude_classifies_errors_in_a_real_child_that_never_touches_the_host(self):
        body = (
            "def deny():\n    raise PermissionError(errno.EPERM, 'x')\n"
            "def missing():\n    raise FileNotFoundError(errno.ENOENT, 'x')\n"
            "def boom():\n    raise ValueError('x')\n"
            "def lookup():\n    raise socket.gaierror(8, 'x')\n"
            "attempt('a-denied', deny)\nattempt('b-missing', missing)\nattempt('c-boom', boom)\n"
            "attempt('d-lookup', lookup)\nattempt('e-true', lambda: True)\nattempt('f-false', lambda: False)\n"
            "attempt('g-none', lambda: None)\nnote('h-note', lambda: True)\n"
            "attempt('i-fork', lambda: (_ for _ in ()).throw(BlockingIOError(errno.EAGAIN, 'x')), FORK_DENY)\n")
        source = "A = {}\n" + q.PRELUDE + body
        out = subprocess.run([sys.executable, "-I", "-S", "-c", source], capture_output=True, timeout=20)
        self.assertEqual(out.returncode, 0, out.stderr)
        got = {}
        for text in out.stdout.splitlines():
            event = json.loads(text)
            got[event["attempt"]] = (event["outcome"], event["errno"], event["info"])
        self.assertEqual(got, {
            "a-denied": ("denied", "EPERM", False), "b-missing": ("inconclusive", "ENOENT", False),
            "c-boom": ("inconclusive", "OTHER", False), "d-lookup": ("denied", "RESOLUTION", False),
            "e-true": ("allowed", "NONE", False), "f-false": ("denied", "NONE", False),
            "g-none": ("inconclusive", "NONE", False), "h-note": ("allowed", "NONE", True),
            "i-fork": ("denied", "EAGAIN", False)})

    def test_limit_children_report_signal_and_refusal_without_running_a_limit(self):
        body = (
            "import os, signal\n"
            "limit('s-signal', lambda: os.kill(os.getpid(), signal.SIGKILL))\n"
            "limit('r-refused', lambda: (_ for _ in ()).throw(OSError(errno.EMFILE, 'x')))\n"
            "limit('p-passed', lambda: True)\nlimit_note('n-note', lambda: True)\n")
        out = subprocess.run([sys.executable, "-I", "-S", "-c", "A = {}\n" + q.PRELUDE + body],
                             capture_output=True, timeout=20)
        events = [json.loads(t) for t in out.stdout.splitlines()]
        got = {e["attempt"]: (e["outcome"], e["info"]) for e in events if "attempt" in e}
        self.assertEqual(got, {"s-signal": ("denied", False), "r-refused": ("denied", False),
                               "p-passed": ("allowed", False), "n-note": ("allowed", True)})
        self.assertEqual([e["begin"] for e in events if "begin" in e],
                         ["s-signal", "r-refused", "p-passed", "n-note"])

    def parse(self, data, **over):
        return q.parse_helper_output(self.PROBE, q.ExecResult(data, **({"exit_code": 0} | over)))

    def test_parser_drops_unknown_malformed_and_duplicate_lines(self):
        data = (b'{"attempt":"file-size","outcome":"denied"}\n{"attempt":"file-size","outcome":"allowed"}\n'
                b'{"attempt":"invented","outcome":"denied"}\nnot json\n[1]\n'
                b'{"attempt":"memory","outcome":"maybe"}\n{"attempt":"open-files","outcome":"allowed"}\n')
        outcomes, _ = self.parse(data)
        self.assertEqual(outcomes, {"file-size": "denied", "open-files": "allowed"})

    def test_terminal_attempt_killed_before_reporting_is_a_limit_denial_only_when_settled(self):
        data = b'{"begin":"memory"}\n'
        self.assertEqual(self.parse(data, exit_code=None)[0], {"memory": "denied"})
        # a wall-clock kill proves nothing about the limit
        self.assertEqual(self.parse(data, exit_code=0, timed_out=True)[0], {})
        self.assertEqual(self.parse(data, exit_code=None, settled=False)[0], {})
        self.assertEqual(self.parse(data, exit_code=0)[0], {})
        self.assertEqual(self.parse(b'{"begin":"cpu"}\n{"begin":"nope"}\n', exit_code=None)[1], {"cpu"})

    def test_non_terminal_attempt_without_result_is_never_denied_by_a_kill(self):
        probe = q.BY_ID["FS-01"]
        outcomes, begun = q.parse_helper_output(
            probe, q.ExecResult(b'{"begin":"outside-dir"}\n', None))
        self.assertEqual((outcomes, begun), ({}, {"outside-dir"}))


class RunnerTests(unittest.TestCase):
    def run_all(self, world, **kw):
        out = world.tmp / "bundle"
        summary = world.runner().run(out, environment=environment(), **kw)
        return out, summary

    def test_good_world_writes_the_bundle_and_satisfies_the_pass_rule(self):
        world = World(self)
        out, summary = self.run_all(world)
        self.assertTrue(summary["passRuleSatisfied"], summary["probes"])
        self.assertEqual(sorted(p.name for p in out.iterdir()), sorted(q.BUNDLE_FILES))
        rows = [json.loads(t) for t in (out / "results.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 2 * len(q.CATALOG))
        self.assertEqual({r["mode"] for r in rows}, set(q.MODES))
        catalog = json.loads((out / "catalog.json").read_text())
        self.assertEqual(catalog["probes"][0]["id"], "FS-01")
        self.assertEqual(summary["catalogSha256"], q.CATALOG_SHA256)
        self.assertEqual(q.verify_bundle(out), summary["bundleSha256"])
        self.assertEqual(summary["environmentSha256"], ENV_HASH)

    def test_every_helper_probe_ran_uncontained_control_first_then_contained(self):
        world = World(self)
        self.run_all(world)
        order = [(m, p) for m, p, _ in world.executed]
        for probe in q.CATALOG:
            if probe.runner == "helper":
                self.assertEqual([m for m, p in order if p == probe.id],
                                 ["uncontained-control", "contained"], probe.id)
                self.assertLess(order.index(("uncontained-control", probe.id)),
                                order.index(("contained", probe.id)))

    def test_sessions_use_the_driver_only_contained_and_the_control_is_a_detector_self_test(self):
        world = World(self)
        out, summary = self.run_all(world)
        self.assertEqual(sorted(world.session_calls), ["CRED-05", "HOST-01", "NET-05-CLI"])
        rows = {(r["probe"], r["mode"]): r for r in map(json.loads, (out / "results.jsonl").read_text().splitlines())}
        for pid in ("CRED-05", "HOST-01", "NET-05-CLI"):
            self.assertEqual(rows[(pid, "uncontained-control")]["control"], "detector-self-test")
            self.assertEqual(rows[(pid, "uncontained-control")]["attempts"], {"session": "allowed"})
        quota = json.loads((out / "quota.json").read_text())
        self.assertEqual(sorted(s["probe"] for s in quota["sessions"]), ["CRED-05", "HOST-01", "NET-05-CLI"])

    def test_survivors_are_killed_after_each_scan_and_reported(self):
        world = World(self)
        out, _ = self.run_all(world)
        self.assertTrue(world.killed and set(world.killed) == {4242})
        rows = [json.loads(t) for t in (out / "results.jsonl").read_text().splitlines()]
        control = next(r for r in rows if r["probe"] == "PROC-04" and r["mode"] == "uncontained-control")
        self.assertEqual(control["independent"]["survivors"], 1)

    def test_all_arenas_are_closed_even_when_an_executor_fails(self):
        world = World(self)
        world.raises[("contained", "FS-01")] = RuntimeError("boom")
        _, summary = self.run_all(world)
        self.assertTrue(all(a.closed for a in world.arenas))
        self.assertEqual(summary["probes"]["FS-01"]["status"], "inconclusive")

    def test_escape_in_the_contained_run_is_not_enforced(self):
        world = World(self)
        world.contained["FS-03"] = {"case-alias": "allowed"}
        _, summary = self.run_all(world)
        self.assertEqual(summary["effects"]["filesystem"]["status"], "not-enforced")
        self.assertEqual(summary["notEnforced"], ["filesystem"])
        self.assertFalse(summary["passRuleSatisfied"])

    def test_failing_positive_control_makes_the_probe_inconclusive(self):
        world = World(self)
        world.control["NET-01"] = {"tcp-by-name": "denied"}
        _, summary = self.run_all(world)
        self.assertEqual(summary["probes"]["NET-01"]["status"], "inconclusive")
        self.assertEqual(summary["effects"]["network"]["status"], "inconclusive")
        self.assertFalse(summary["passRuleSatisfied"])

    def test_independent_snapshot_difference_overrides_a_denied_report(self):
        world = World(self)
        world.changed["FS-05"] = ["outside/victim-0.txt"]
        out, summary = self.run_all(world)
        # the control also changes the arena (expected); only the contained change escalates
        world.changed = {"FS-05": []}
        self.assertEqual(summary["effects"]["filesystem"]["status"], "not-enforced")
        rows = [json.loads(t) for t in (out / "results.jsonl").read_text().splitlines()]
        contained = next(r for r in rows if r["probe"] == "FS-05" and r["mode"] == "contained")
        self.assertTrue(contained["escalated"])
        self.assertEqual(contained["independent"]["changedOutside"], ["outside/victim-0.txt"])

    def test_listener_hit_escalates_a_denied_network_report(self):
        world = World(self)
        world.hits["NET-04"] = {"tcp4": 1}
        _, summary = self.run_all(world)
        self.assertEqual(summary["effects"]["network"]["status"], "not-enforced")

    def test_listener_hit_on_an_unwatched_counter_does_not_escalate(self):
        world = World(self)
        world.hits["NET-04"] = {"udp": 3}
        _, summary = self.run_all(world)
        self.assertTrue(summary["passRuleSatisfied"])

    def test_surviving_process_after_the_contained_run_is_an_escape(self):
        world = World(self)
        world.contained_survivors = 1
        _, summary = self.run_all(world)
        self.assertEqual(summary["effects"]["process"]["status"], "not-enforced")
        self.assertIn(4343, world.killed)

    def test_unsettled_contained_child_is_an_escape(self):
        world = World(self)
        world.unsettled.add("PROC-01")
        _, summary = self.run_all(world)
        self.assertEqual(summary["effects"]["process"]["status"], "not-enforced")

    def test_backend_refusal_is_recorded_as_a_fixed_reason_and_is_inconclusive(self):
        world = World(self)
        world.raises[("contained", "PROC-01")] = lab.LabError("self-check-allowed")
        out, summary = self.run_all(world)
        rows = [json.loads(t) for t in (out / "results.jsonl").read_text().splitlines()]
        refused = next(r for r in rows if r["probe"] == "PROC-01" and r["mode"] == "contained")
        self.assertEqual(refused["refused"], "self-check-allowed")
        self.assertEqual(summary["probes"]["PROC-01"]["status"], "inconclusive")

    def test_subset_selection_leaves_the_other_probes_missing(self):
        world = World(self)
        out, summary = self.run_all(world, probes=["FS-01", "NET-06"])
        self.assertEqual(len(summary["missingProbes"]), len(q.CATALOG) - 2)
        self.assertFalse(summary["passRuleSatisfied"])
        self.assertEqual({e for _, e, _ in world.executed}, {"FS-01", "NET-06"})

    def test_unknown_or_repeated_selection_is_refused_before_anything_runs(self):
        world = World(self)
        for bad in (["FS-99"], ["FS-01", "FS-01"]):
            with self.assertRaises(q.ProbeError) as raised:
                world.runner().run(world.tmp / "x", environment=environment(), probes=bad)
            self.assertEqual(raised.exception.reason, "unknown-probe")
        self.assertEqual(world.executed, [])
        self.assertFalse((world.tmp / "x").exists())

    def test_session_probes_without_a_driver_are_inconclusive_with_a_reason(self):
        world = World(self)
        out, summary = self.run_all_with(world, sessions=None)
        self.assertEqual(summary["probes"]["HOST-01"]["status"], "inconclusive")
        self.assertFalse(summary["hostFunctional"])
        rows = [json.loads(t) for t in (out / "results.jsonl").read_text().splitlines()]
        self.assertEqual(next(r for r in rows if r["probe"] == "HOST-01" and r["mode"] == "contained")["refused"],
                         "session-driver-missing")

    def run_all_with(self, world, **over):
        out = world.tmp / "bundle"
        return out, world.runner(**over).run(out, environment=environment())

    def test_session_cap_stops_a_fourth_session(self):
        world = World(self)
        runner = world.runner()
        runner._session_count = q.MAX_PROBE_SESSIONS
        row = runner.run_mode(q.BY_ID["HOST-01"], "contained")
        self.assertEqual(row["refused"], "session-cap")
        self.assertEqual(world.session_calls, [])

    def test_driver_exception_is_inconclusive_not_an_error(self):
        world = World(self)
        def broken(probe_id):
            raise RuntimeError("secret detail")
        row = world.runner(sessions=broken).run_mode(q.BY_ID["CRED-05"], "contained")
        self.assertEqual(row["attempts"], {"session": "inconclusive"})
        self.assertEqual(row["refused"], "driver-failed")
        self.assertNotIn("secret", json.dumps(row))

    def test_missing_cancel_check_blocks_proc_08(self):
        world = World(self)
        _, summary = self.run_all_with(world, cancel_check=None)
        self.assertEqual(summary["probes"]["PROC-08"]["status"], "inconclusive")
        self.assertEqual(summary["effects"]["process"]["status"], "inconclusive")

    def test_cancel_survivor_or_unsettled_cancel_is_an_escape(self):
        for outcome in ({"survivors": 1, "settled": True, "cancelled": True},
                        {"survivors": 0, "settled": False, "cancelled": True}):
            world = World(self)
            world.cancel = outcome
            _, summary = self.run_all_with(world)
            self.assertEqual(summary["effects"]["process"]["status"], "not-enforced", outcome)
        for outcome in ({"survivors": 0, "settled": True, "cancelled": False}, {"settled": True}):
            world = World(self)
            world.cancel = outcome
            _, summary = self.run_all_with(world)
            self.assertEqual(summary["effects"]["process"]["status"], "inconclusive", outcome)

    def test_survival_probe_where_the_helper_never_ran_is_inconclusive_not_denied(self):
        world = World(self)
        base = world.run("contained")
        def silent(source, workdir, wall, arena):
            result = base(source, workdir, wall, arena)
            if world.current == "PROC-04":
                return q.ExecResult(b"", 1)
            return result
        _, summary = self.run_all_with(world, contained=silent)
        self.assertEqual(summary["probes"]["PROC-04"]["status"], "inconclusive")

    def test_session_escape_is_flagged_and_unverified_route_is_an_escape(self):
        world = World(self)
        world.sessions["CRED-05"] = (canonical({"type": "system", "subtype": "init",
                                                 "apiKeySource": "ANTHROPIC_API_KEY"}) + b"\n")
        _, summary = self.run_all(world)
        self.assertEqual(summary["effects"]["credential"]["status"], "not-enforced")

    def test_no_session_is_ever_started_in_control_mode(self):
        world = World(self)
        for pid in ("CRED-05", "HOST-01", "NET-05-CLI"):
            world.runner().run_mode(q.BY_ID[pid], "uncontained-control")
        self.assertEqual(world.session_calls, [])

    def test_environment_must_bind_this_catalog_and_carry_a_hash(self):
        world = World(self)
        for bad, reason in ((environment(probeCatalogSha256="0" * 64), "catalog-hash-mismatch"),
                            (environment(environmentSha256="xyz"), "invalid-environment"),
                            ({"probeCatalogSha256": q.CATALOG_SHA256}, "invalid-environment")):
            with self.assertRaises(q.ProbeError) as raised:
                world.runner().run(world.tmp / "b", environment=bad)
            self.assertEqual(raised.exception.reason, reason)
        self.assertFalse((world.tmp / "b").exists())
        self.assertEqual(world.executed, [])

    def test_existing_bundle_directory_is_never_overwritten(self):
        world = World(self)
        out = world.tmp / "bundle"
        out.mkdir()
        (out / "keep").write_text("evidence")
        with self.assertRaises(q.ProbeError) as raised:
            world.runner().run(out, environment=environment())
        self.assertEqual(raised.exception.reason, "bundle-exists")
        self.assertEqual((out / "keep").read_text(), "evidence")

    def test_secret_in_an_artifact_aborts_before_any_file_is_written(self):
        world = World(self)
        out = world.tmp / "bundle"
        with self.assertRaises(q.ProbeError) as raised:
            world.runner().run(out, environment=environment(note="leaks DUMMYSECRET here"),
                               secrets=["DUMMYSECRET"])
        self.assertEqual(raised.exception.reason, "secret-in-artifact")
        self.assertNotIn("DUMMYSECRET", str(raised.exception))
        self.assertFalse(out.exists())

    def test_arena_markers_are_always_in_the_secret_scan(self):
        world = World(self)
        runner = world.runner()
        runner.run_mode(q.BY_ID["FS-01"], "contained")
        self.assertEqual(runner.markers, ["braid-dummy-fake-marker"])
        with self.assertRaises(q.ProbeError):
            q.scan_for_secrets({"f": "has braid-dummy-fake-marker"}, runner.markers)
        with self.assertRaises(q.ProbeError):
            q.write_bundle(world.tmp / "m", environment=environment(), rows=[], quota=[],
                           summary={"effects": {}}, secrets=runner.markers + ["bundle"])
        self.assertFalse((world.tmp / "m").exists())

    def test_bundle_verification_detects_edits(self):
        world = World(self)
        out, _ = self.run_all(world)
        results = out / "results.jsonl"
        results.write_text(results.read_text().replace("denied", "allowed", 1))
        with self.assertRaises(q.ProbeError) as raised:
            q.verify_bundle(out)
        self.assertEqual(raised.exception.reason, "bundle-drift")

    def test_edited_summary_verdict_is_detected(self):
        world = World(self)
        out, _ = self.run_all(world)
        path = out / "summary.json"
        document = json.loads(path.read_text())
        document["passRuleSatisfied"] = not document["passRuleSatisfied"]
        path.write_text(json.dumps(document))
        with self.assertRaises(q.ProbeError) as raised:
            q.verify_bundle(out)
        self.assertEqual(raised.exception.reason, "bundle-drift")

    def test_arena_failure_keeps_the_bundle_with_an_inconclusive_row(self):
        world = World(self)
        factory = world.arena

        def failing(parent, **kwargs):
            if len(world.arenas) == 4:
                raise q.ProbeError("arena-path-too-long")
            return factory(parent, **kwargs)

        out, summary = self.run_all_with(world, arena_factory=failing)
        rows = [json.loads(t) for t in (out / "results.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 2 * len(q.CATALOG))
        self.assertIn("arena-path-too-long", [r.get("refused") for r in rows])
        self.assertFalse(summary["passRuleSatisfied"])

    def test_escape_observed_without_a_control_row_is_not_hidden(self):
        _, contained = row("FS-01", "allowed", {"outside-dir": "allowed", "tmp-path": "denied",
                                                 "decoy-home": "denied", "decoy-repo": "denied"})
        contained["outcome"] = "allowed"
        summary = q.summarize([contained] + passing_rows(skip=("FS-01",)))
        self.assertEqual(summary["effects"]["filesystem"]["status"], "not-enforced")

    def test_bundle_files_are_private_and_marked_non_authorizing(self):
        world = World(self)
        out, summary = self.run_all(world)
        self.assertEqual(oct(out.stat().st_mode & 0o777), "0o700")
        for name in q.BUNDLE_FILES:
            self.assertEqual(oct((out / name).stat().st_mode & 0o777), "0o600", name)
        self.assertIs(summary["executionAuthorization"], False)
        stored = json.loads((out / "summary.json").read_text())
        self.assertIs(stored["executionAuthorization"], False)
        self.assertIs(stored["qualificationRecordWritten"], False)


class NoQualificationRecordTests(unittest.TestCase):
    def test_module_has_no_record_format_field_verifier_or_signing_name(self):
        text = Path(q.__file__).read_text()
        for needle in ("QUALIFICATION_FORMAT", "braid-harness-containment-qualification",
                       "braid-harness-host-qualification", "expiresAt", "evidenceSha256",
                       "verify_qualification", "verify_host_qualification", "Qualification("):
            self.assertNotIn(needle, text, needle)
        names = [n for n in dir(q) if not n.startswith("_")]
        self.assertEqual([n for n in names if re.search(r"issue|sign(?!al)|grant|authori[sz]e|record", n, re.I)], [])

    def test_bundle_contains_no_record_shaped_file_or_field(self):
        world = World(self)
        out = world.tmp / "bundle"
        world.runner().run(out, environment=environment())
        for path in out.iterdir():
            text = path.read_text()
            self.assertNotIn("braid-harness-", text)
            self.assertNotIn("expiresAt", text)
            self.assertNotIn("evidenceSha256", text)
        self.assertEqual(sorted(p.name for p in out.iterdir()), sorted(q.BUNDLE_FILES))

    def test_summary_cannot_be_fed_to_the_runtime_verifiers(self):
        world = World(self)
        out = world.tmp / "bundle"
        world.runner().run(out, environment=environment())
        raw = (out / "summary.json").read_bytes()
        digest = hashlib.sha256(raw).hexdigest()
        with self.assertRaises(lab.LabError) as lab_error:
            lab.verify_qualification(raw, expected_sha256=digest)
        self.assertEqual(lab_error.exception.reason, "invalid-qualification")
        with self.assertRaises(hc.ClaudeHostError) as host_error:
            hc.verify_host_qualification(raw, expected_sha256=digest)
        self.assertEqual(host_error.exception.reason, "invalid-qualification")


class SessionTests(unittest.TestCase):
    def session(self, key=None, result=True, **kw):
        events = []
        if key is not None:
            events.append({"type": "system", "subtype": "init", "apiKeySource": key})
        if result:
            events.append({"type": "result", "subtype": "success", "is_error": False})
        return q.SessionResult(b"\n".join(canonical(e) for e in events), kw.pop("exit_code", 0), **kw)

    def test_cred_05(self):
        self.assertEqual(q.classify_session("CRED-05", self.session("oauth")), "denied")
        self.assertEqual(q.classify_session("CRED-05", self.session("none")), "denied")
        self.assertEqual(q.classify_session("CRED-05", self.session("ANTHROPIC_API_KEY")), "allowed")
        self.assertEqual(q.classify_session("CRED-05", self.session(None)), "inconclusive")
        self.assertEqual(q.classify_session("CRED-05", q.SessionResult(refused="quota-stop")), "inconclusive")

    def test_host_01_requires_a_complete_subscription_session(self):
        self.assertEqual(q.classify_session("HOST-01", self.session("oauth")), "allowed")
        self.assertEqual(q.classify_session("HOST-01", self.session("oauth", exit_code=1)), "denied")
        self.assertEqual(q.classify_session("HOST-01", self.session("oauth", timed_out=True)), "denied")
        self.assertEqual(q.classify_session("HOST-01", self.session("oauth", settled=False)), "denied")
        self.assertEqual(q.classify_session("HOST-01", self.session("paid")), "denied")
        self.assertEqual(q.classify_session("HOST-01", self.session("oauth", result=False)), "inconclusive")
        failed = q.SessionResult(canonical({"type": "system", "subtype": "init", "apiKeySource": "oauth"})
                                 + b"\n" + canonical({"type": "result", "subtype": "error", "is_error": True}), 0)
        self.assertEqual(q.classify_session("HOST-01", failed), "denied")

    def test_net_05_cli_needs_an_egress_observation(self):
        base = self.session("oauth")
        clean = replace(base, egress={"admitted": ["api.anthropic.com:443"], "unexpectedDirect": 0})
        self.assertEqual(q.classify_session("NET-05-CLI", clean), "denied")
        self.assertEqual(q.classify_session("NET-05-CLI", base), "inconclusive")
        direct = replace(base, egress={"admitted": [], "unexpectedDirect": 2})
        self.assertEqual(q.classify_session("NET-05-CLI", direct), "allowed")
        other = replace(base, egress={"admitted": ["evil.example:443"], "unexpectedDirect": 0})
        self.assertEqual(q.classify_session("NET-05-CLI", other), "allowed")
        self.assertEqual(q.classify_session("NET-05-CLI", replace(base, egress={"admitted": []})), "inconclusive")
        text = replace(base, egress={"admitted": "api.anthropic.com:443", "unexpectedDirect": 0})
        self.assertEqual(q.classify_session("NET-05-CLI", text), "inconclusive")

    def test_detector_self_test_is_allowed_for_every_session_probe(self):
        for pid in ("CRED-05", "HOST-01", "NET-05-CLI"):
            self.assertEqual(q.detector_self_test(pid), "allowed", pid)
        with self.assertRaises(q.ProbeError):
            q.detector_self_test("FS-01")
        with self.assertRaises(q.ProbeError):
            q.classify_session("FS-01", q.SessionResult())

    def test_detector_self_test_fails_when_the_classifier_is_blind(self):
        with mock.patch.object(q, "classify_session", return_value="denied"):
            for pid in ("CRED-05", "HOST-01", "NET-05-CLI"):
                self.assertNotEqual(q.detector_self_test(pid), "allowed", pid)

    def test_malformed_stream_lines_are_ignored(self):
        junk = q.SessionResult(b"garbage\n[1]\n" + OAUTH_STREAM, 0)
        self.assertEqual(q.classify_session("HOST-01", junk), "allowed")


class FakeNativeTransport(hc.ClaudeTransport):
    kind = "native"

    def __init__(self, stdout=OAUTH_STREAM, error=None):
        self.stdout, self.error, self.calls = stdout, error, []
        self.run_evidence = [{"quota": {"fiveHourPercent": 12}, "executionAuthorization": False}]

    def version(self):
        self.calls.append("version")
        return "2.1.292 (Claude Code)"

    def run(self, plan, prompt, limits, cancel):
        self.calls.append(("run", plan.argv, prompt, limits))
        if self.error:
            raise hc.ClaudeHostError(self.error)
        return hc.HostRun(self.stdout, 0)


class NativeSessionDriverTests(unittest.TestCase):
    def test_driver_goes_through_the_transport_with_a_minimal_read_only_plan(self):
        transports = []

        def factory():
            transports.append(FakeNativeTransport())
            return transports[-1]

        result = q.native_session_driver(factory, model="haiku")("HOST-01")
        self.assertEqual(len(transports), 1)
        calls = transports[0].calls
        self.assertEqual(calls[0], "version")
        _, argv, prompt, limits = calls[1]
        self.assertEqual(argv[0], "claude")
        self.assertIn("plan", argv)
        self.assertEqual(argv[argv.index("--max-turns") + 1], "1")
        self.assertEqual(argv[argv.index("--model") + 1], "haiku")
        self.assertEqual(argv[argv.index("--tools") + 1], "Read")
        self.assertEqual(prompt, q.PROBE_PROMPT)
        self.assertEqual(result.stdout, OAUTH_STREAM)
        self.assertEqual(result.quota, {"admission": {"fiveHourPercent": 12}})
        self.assertIsNone(result.egress)

    def test_every_session_gets_a_fresh_single_attempt_transport(self):
        made = []
        driver = q.native_session_driver(lambda: made.append(FakeNativeTransport()) or made[-1])
        driver("CRED-05")
        driver("HOST-01")
        self.assertEqual(len(made), 2)

    def test_transport_refusal_becomes_a_fixed_reason_not_an_exception(self):
        result = q.native_session_driver(lambda: FakeNativeTransport(error="quota-stop"))("HOST-01")
        self.assertEqual(result.refused, "quota-stop")
        self.assertEqual(q.classify_session("HOST-01", result), "inconclusive")


class ExecutorTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="braid-t007-exec-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def arena(self):
        target = self.tmp / "target.txt"
        target.write_text("dummy")
        return SimpleNamespace(
            inherit_fd=lambda: os.open(target, os.O_RDONLY),
            control_env=lambda: {"HOME": str(self.tmp), "PATH": "/usr/bin:/bin"})

    def test_contained_executor_uses_run_probe_with_a_factory_workdir_and_wall(self):
        calls = []

        class Backend:
            def run_probe(self, source, workdir, limits):
                calls.append((source, workdir, limits))
                return lab.ChildResult(b"out", 0, False, False, True)

        work = self.tmp / "candidate"
        result = q.ContainedExecutor(Backend(), lambda: work)(b"print(1)", Path("ignored"), 7, None)
        self.assertEqual(calls, [(b"print(1)", work, lab.FixtureLimits(wall_seconds=7))])
        self.assertEqual(result, q.ExecResult(b"out", 0, False, False, True))

    def test_contained_executor_lets_a_backend_refusal_through(self):
        class Backend:
            def run_probe(self, *a):
                raise lab.LabError("profile-compile-failed")

        with self.assertRaises(lab.LabError):
            q.ContainedExecutor(Backend(), lambda: self.tmp)(b"", self.tmp, 1, None)

    def test_uncontained_executor_runs_a_harmless_source_in_a_minimal_environment(self):
        source = b"import os, sys\nprint(sorted(os.environ))\nprint(len(sys.argv))\n"
        result = q.uncontained_executor(source, self.tmp, 20, self.arena())
        self.assertEqual((result.exit_code, result.timed_out, result.settled), (0, False, True))
        self.assertIn(b"'HOME'", result.stdout)
        self.assertNotIn(b"ANTHROPIC", result.stdout)

    def test_uncontained_executor_kills_and_settles_on_timeout(self):
        result = q.uncontained_executor(b"import time\ntime.sleep(30)\n", self.tmp, 1, self.arena())
        self.assertTrue(result.timed_out)
        self.assertTrue(result.settled)

    def test_scan_processes_matches_the_nonce_and_skips_this_process(self):
        listing = (f"  101 python -c A nonce123 x\n  {os.getpid()} python nonce123\n"
                   "  202 other\n  303 python nonce123\n")
        with mock.patch.object(q.subprocess, "run", return_value=SimpleNamespace(stdout=listing)):
            self.assertEqual(q.scan_processes("nonce123"), [101, 303])

    def test_kill_processes_ignores_missing_pids(self):
        with mock.patch.object(q.os, "kill", side_effect=[None, ProcessLookupError()]) as kill:
            q.kill_processes([1, 2])
        self.assertEqual([c.args[0] for c in kill.call_args_list], [1, 2])


class F4RunnerTests(unittest.TestCase):
    def make(self, outcome_for):
        world = World(self)
        calls = []

        class Backend:
            policy = SimpleNamespace(proxy_port=45123)

            def run_probe(self, source, workdir, limits):
                probe = world.probe_of(source)
                calls.append((probe.id, workdir, limits))
                outcome = outcome_for(probe)
                return lab.ChildResult(lines({n: outcome for n in probe.counted}), 0, False, False, True)

        runner = q.make_f4_probe_runner(arena_parent=world.tmp, workdir_factory=lambda: world.tmp,
                                        arena_factory=world.arena)
        return runner, Backend(), calls, world

    def test_runs_only_the_contained_probe_and_maps_the_outcome(self):
        runner, backend, calls, world = self.make(lambda p: "allowed" if p.functional else "denied")
        with mock.patch.object(q, "uncontained_executor", side_effect=AssertionError("uncontained")):
            self.assertEqual(runner("FS-01", backend), "denied")
            self.assertEqual(runner("NET-06", backend), "allowed")
        self.assertEqual([c[0] for c in calls], ["FS-01", "NET-06"])
        self.assertEqual(calls[0][2], lab.FixtureLimits(wall_seconds=q.BY_ID["FS-01"].wall_seconds))
        self.assertEqual(world.session_calls, [])

    def test_an_allowed_escape_is_reported_as_allowed_so_the_backend_refuses(self):
        runner, backend, *_ = self.make(lambda p: "allowed")
        self.assertEqual(runner("PROC-01", backend), "allowed")

    def test_unknown_or_non_f4_probe_and_inconclusive_results_are_errors(self):
        runner, backend, *_ = self.make(lambda p: "inconclusive")
        self.assertEqual(runner("FS-99", backend), "error")
        self.assertEqual(runner("FS-02", backend), "error")
        self.assertEqual(runner("FS-01", backend), "error")


@unittest.skipUnless(os.environ.get("BRAID_T007_LIVE_CONTROLS") == "1" and sys.platform == "darwin",
                     "live positive controls run only with BRAID_T007_LIVE_CONTROLS=1 on macOS")
class LiveControlTests(unittest.TestCase):
    """Local-only positive controls (disposable arena, no network, no claude, no sandbox)."""

    def test_filesystem_and_credential_controls_succeed_uncontained(self):
        tmp = Path(tempfile.mkdtemp(prefix="braid-t007-live-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        runner = q.QualificationProbeRunner(
            control=q.uncontained_executor, contained=lambda *a: q.ExecResult(b"", 1),
            arena_parent=tmp, proxy_address="127.0.0.1:1", spawn_sibling=False)
        for pid in ("FS-01", "FS-02", "FS-03", "FS-04", "FS-05", "CRED-01", "CRED-03", "CRED-04"):
            with self.subTest(probe=pid):
                row = runner.run_mode(q.BY_ID[pid], "uncontained-control")
                self.assertEqual(row["outcome"], "allowed", row)


class ArenaTests(unittest.TestCase):
    """The real arena, on loopback and a temporary directory only."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="bt-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def test_tree_holds_dummy_secrets_only_and_cleans_up(self):
        arena = q.Arena(self.tmp, public=q.DEFAULT_PUBLIC, proxy=None, proxy_enforcing=False,
                        spawn_sibling=False)
        root = arena.root
        document = arena.document
        self.assertTrue(str(root).startswith(os.path.realpath(self.tmp)))
        for path in document["secret_files"] + [document["target"], document["keychain"]]:
            self.assertEqual(Path(path).read_text(), arena.marker)
        self.assertEqual(document["sibling_pid"], 0)
        self.assertTrue(document["proxy"].startswith("127.0.0.1:"))
        self.assertIn("ANTHROPIC_API_KEY", document["env_names"])
        self.assertEqual(arena.control_env()["ANTHROPIC_API_KEY"], arena.marker)
        self.assertNotIn(os.path.expanduser("~"), json.dumps(document))
        arena.close()
        self.assertFalse(root.exists())

    def test_snapshot_detects_changes_and_extra_outside_paths(self):
        arena = q.Arena(self.tmp, public=q.DEFAULT_PUBLIC, proxy="127.0.0.1:9", proxy_enforcing=True,
                        spawn_sibling=False)
        self.addCleanup(arena.close)
        before = arena.snapshot()
        self.assertEqual(arena.changed(before), [])
        Path(arena.document["victims"][0]).unlink()
        Path(arena.document["home"], "added.txt").write_text("x")
        os.symlink("/", Path(arena.document["repo"], "link"))
        Path(arena.extra_outside[0]).write_text("x")
        changed = arena.changed(before)
        self.assertEqual(len(changed), 4)
        self.assertEqual(arena.document["proxy"], "127.0.0.1:9")

    def test_listeners_count_connections_and_close_cleanly(self):
        import socket as sk
        arena = q.Arena(self.tmp, public=q.DEFAULT_PUBLIC, proxy=None, proxy_enforcing=False,
                        spawn_sibling=False)
        document = arena.document
        sk.create_connection(("127.0.0.1", document["tcp_port"]), timeout=2).close()
        with sk.socket(sk.AF_UNIX, sk.SOCK_STREAM) as sock:
            sock.connect(document["ssh_agent"])
        with sk.socket(sk.AF_INET, sk.SOCK_DGRAM) as sock:
            sock.sendto(b"x", ("127.0.0.1", document["udp_port"]))
        host, _, port = document["proxy"].rpartition(":")
        with sk.create_connection((host, int(port)), timeout=2) as sock:
            sock.sendall(b"CONNECT example.com:443 HTTP/1.1\r\n\r\n")
            self.assertTrue(sock.recv(64).startswith(b"HTTP/1.1 200"))
        hits = {}
        for _ in range(100):
            hits = arena.hit_counts()
            if hits.get("tcp4") and hits.get("ssh-agent") and hits.get("udp") and hits.get("relay"):
                break
            threading.Event().wait(0.05)
        self.assertEqual({k: hits.get(k) for k in ("tcp4", "ssh-agent", "udp", "relay")},
                         {"tcp4": 1, "ssh-agent": 1, "udp": 1, "relay": 1})
        arena.close()

    def test_sibling_process_carries_the_dummy_marker_and_is_killed_on_close(self):
        arena = q.Arena(self.tmp, public=q.DEFAULT_PUBLIC, proxy="127.0.0.1:9", proxy_enforcing=True,
                        spawn_sibling=True)
        pid = arena.document["sibling_pid"]
        self.assertGreater(pid, 0)
        os.kill(pid, 0)
        arena.close()
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_overlong_socket_path_is_refused(self):
        deep = self.tmp / ("d" * 60) / ("e" * 60)
        deep.mkdir(parents=True)
        with self.assertRaises(q.ProbeError) as raised:
            q.Arena(deep, public=q.DEFAULT_PUBLIC, proxy="127.0.0.1:9", proxy_enforcing=True,
                    spawn_sibling=False)
        self.assertEqual(raised.exception.reason, "arena-path-too-long")
        self.assertEqual(list(deep.iterdir()), [])

    def test_parent_must_exist(self):
        with self.assertRaises(q.ProbeError):
            q.Arena(self.tmp / "missing", public=q.DEFAULT_PUBLIC, proxy=None, proxy_enforcing=False)


if __name__ == "__main__":
    unittest.main()
