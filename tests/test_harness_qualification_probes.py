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
import socket
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace
import unittest
from unittest import mock

from agent_braid import harness_containment_macos as mac
from agent_braid import harness_host_claude as hc
from agent_braid import harness_lab as lab
from agent_braid import harness_qualification_probes as q
from agent_braid.system_one import canonical

CLOCK = 1_800_000_000.0
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


def reading(offset, five_hour):
    """An NC-6 usage-card reading ``offset`` seconds before the fixed test clock."""
    stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(CLOCK - offset))
    return {"source": "claude-desktop-usage-card", "observedAt": stamp, "fiveHourPercent": five_hour,
            "weeklyPercent": 5, "extraUsageEnabled": False}


def lines(mapping):
    return b"".join(canonical({"attempt": n, "outcome": o, "errno": "NONE", "info": False}) + b"\n"
                    for n, o in mapping.items())


class FakeArena:
    """Arena double: no filesystem tree, listener or process; independent observations scripted."""

    def __init__(self, world, parent, *, public, proxy, proxy_enforcing, spawn_sibling, **kwargs):
        self.world = world
        self.nonce, self.marker = "abcdef012345", "braid-dummy-fake-marker"
        self.work = Path(parent)
        self.kwargs = kwargs
        self.relay = None
        self.document = {"proxy": proxy, "proxy_enforcing": proxy_enforcing,
                         "mach_names": list(kwargs.get("mach_names", ())),
                         "adjacent": {"run_dir": "/x"} if kwargs.get("layout") else {}}
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
        self.launch = {}  # the same for the launch-probe profile
        self.limit_exceeded = {"PROC-03": "memory"}  # probe id -> backend stop reason
        self.proxy = {}  # attempt -> outcome overrides for the NET-05 parsing block
        self.trips = {}  # (mode, probe id) -> {tripwire: outcome} appended to the scripted output
        self.changed, self.hits = {}, {}
        self.contained_survivors = 0
        self.unsettled = set()
        self.raises = {}  # (mode, probe id) -> exception
        self.killed, self.arenas, self.executed = [], [], []
        self.sessions = {"CRED-05": OAUTH_STREAM, "HOST-01": OAUTH_STREAM, "NET-05-CLI": OAUTH_STREAM}
        self.post = {"CRED-05": 11, "HOST-01": 11, "NET-05-CLI": 11}  # 5-hour percent after each session
        self.egress = {"connections": 2, "allowed": 2, "allowed:api.anthropic.com:443": 2}
        self.cancel = {"survivors": 0, "settled": True, "cancelled": True, "escaped": 0}
        self.accounting = {}  # (mode, probe id) -> (escaped, surviving) reported by the backend double
        self.cancel_calls = []
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
        def execute(source, workdir, wall, arena, *, cancel=None):
            probe = self.probe_of(source)
            self.mode, self.current = mode, probe.id
            if cancel is None:
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
                outcomes.update((self.launch if mode == "contained-launch" else self.contained).get(probe.id, {}))
            outcomes.pop("cancel-settlement", None)
            for name in q.PROXY_ATTEMPTS:
                outcomes.pop(name, None)
            if cancel is not None:  # the PROC-08 cancellation half: only the begin event, then a cancel
                self.cancel_calls.append((mode, probe.id, cancel))
                state = self.cancel
                return q.ExecResult(canonical({"begin": "outlive-timeout"}) + b"\n", None,
                                    settled=state["settled"], cancelled=state["cancelled"],
                                    limit_exceeded=None, escaped_processes=state["escaped"],
                                    surviving_processes=state["survivors"])
            escaped, surviving = self.accounting.get((mode, probe.id), (0, 0))
            trips = b"".join(canonical({"attempt": n, "outcome": o, "errno": "NONE", "info": True, "trip": True})
                             + b"\n" for n, o in self.trips.get((mode, probe.id), {}).items())
            control = mode == "uncontained-control"
            return q.ExecResult(lines(outcomes) + trips, 0, settled=probe.id not in self.unsettled or control,
                                limit_exceeded=self.limit_exceeded.get(probe.id),
                                escaped_processes=None if control else escaped,
                                surviving_processes=None if control else surviving)
        execute.accepts_cancel = True
        return execute

    def proxy_block(self, *, control, relay, proxy_factory):
        return {n: self.proxy.get(n, "allowed" if control else "denied") for n in q.PROXY_ATTEMPTS}

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
                               quota={"pre": reading(60, 10), "post": reading(10, self.post[probe_id])})

    def runner(self, **over):
        args = dict(control=self.run("uncontained-control"), contained=self.run("contained"),
                    launch_contained=self.run("contained-launch"),
                    arena_parent=self.tmp, proxy_address="127.0.0.1:45000", sessions=self.driver,
                    process_scan=self.scan, process_table=lambda: set(), process_kill=self.kill,
                    arena_factory=self.arena,
                    clock=lambda: CLOCK, real_home="/home/world", mach_names=lambda: ["com.apple.fake.service"],
                    allowed_ip="192.0.2.1", lan_ip="", proxy_block=self.proxy_block)
        args.update(over)
        return q.QualificationProbeRunner(**args)


def row(probe_id, control, contained, **extra):
    probe = q.BY_ID[probe_id]
    c = {n: control for n in probe.counted} if isinstance(control, str) else dict(control)
    k = {n: contained for n in probe.counted} if isinstance(contained, str) else dict(contained)
    base = {"settled": True, "escalated": False}
    pair = (dict(base, probe=probe_id, mode="uncontained-control", attempts=c),
            dict(base, probe=probe_id, mode="contained", attempts=k, **extra))
    if probe.runner == "helper":
        pair += (dict(pair[1], mode="contained-launch"),)
    return pair


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

    def test_the_memory_attempts_exceed_the_limit_by_a_gigabyte_and_hold_it_for_the_watchdog(self):
        # T009 attempt 3: 256 MiB over the limit, released at once, peaked at 99 % of the limit in the watchdog
        body = q.BY_ID["PROC-03"].source_template.split("def memory():")[1].split("\ndef ")[0]
        self.assertIn('incompressible(A["limits"]["memoryBytes"] + (1 << 30))', body)
        self.assertIn("time.sleep(2)", body)
        self.assertLess(body.index("time.sleep(2)"), body.index("return True"))

    def test_the_memory_attempt_runs_last_because_its_kill_stops_the_helper(self):
        # T009 attempt 4, launch-probe row: the kill of "memory" left "memory-burst" never begun, so inconclusive
        probe = q.BY_ID["PROC-03"]
        self.assertEqual(probe.counted[-1], "memory")
        self.assertEqual([name for name, _ in probe.attempts][-1], "memory")
        self.assertEqual(set(q.LIMIT_ATTRIBUTION), {"memory"})

    def test_the_memory_residual_names_the_footprint_limit_and_the_founders_acceptance(self):
        residual = q.BY_ID["PROC-03"].residual
        self.assertIn("physical footprint of the child's tree at most memoryBytes", residual)
        self.assertIn("compressed size, so a process whose pages compress well can hold more memory than the limit", residual)
        self.assertIn("founder-decisions-20261106.json", residual)
        self.assertTrue((Path(__file__).resolve().parents[1] / "specs/065-native-claude-containment/evidence/founder-decisions-20261106.json")
                        .is_file())

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
        control, contained, launch = row("PROC-01", "allowed", "denied")
        for rows in ([contained, launch], [control], [control, contained], [control, launch]):
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
        control, contained, launch = row("PROC-02", "allowed", "denied")
        contained["settled"] = False
        summary = q.summarize(passing_rows(override={"PROC-02": (control, contained, launch)}))
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
            "attempt('i-fork', lambda: (_ for _ in ()).throw(BlockingIOError(errno.EAGAIN, 'x')), FORK_DENY)\n"
            "attempt('j-dns', lookup, dns=True)\ntripwire('k-trip', lambda: True)\n"
            "tripwire('l-trip-denied', deny)\n")
        source = "A = {}\n" + q.PRELUDE + body
        out = subprocess.run([sys.executable, "-I", "-S", "-c", source], capture_output=True, timeout=20)
        self.assertEqual(out.returncode, 0, out.stderr)
        got = {}
        for text in out.stdout.splitlines():
            event = json.loads(text)
            got[event["attempt"]] = (event["outcome"], event["errno"], event["info"])
        self.assertEqual(got, {
            "a-denied": ("denied", "EPERM", False), "b-missing": ("inconclusive", "ENOENT", False),
            "c-boom": ("inconclusive", "OTHER", False), "d-lookup": ("inconclusive", "RESOLUTION", False),
            "e-true": ("allowed", "NONE", False), "f-false": ("denied", "NONE", False),
            "g-none": ("inconclusive", "NONE", False), "h-note": ("allowed", "NONE", True),
            "i-fork": ("denied", "EAGAIN", False), "j-dns": ("denied", "RESOLUTION", False),
            "k-trip": ("allowed", "NONE", True), "l-trip-denied": ("denied", "EPERM", True)})

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
        self.assertEqual(len(rows), sum(len(q.QualificationProbeRunner.modes(p)) for p in q.CATALOG))
        self.assertEqual({r["mode"] for r in rows}, set(q.MODES))
        self.assertEqual({r["mode"] for r in rows if r["probe"] == "HOST-01"},
                         {"uncontained-control", "contained"})
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
                                 ["uncontained-control", "contained", "contained-launch"], probe.id)
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
        world.control["NET-01"] = {"tcp-public-literal": "denied"}
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

    def test_executor_that_cannot_cancel_blocks_proc_08(self):
        world = World(self)
        plain = world.run("contained")
        del plain.accepts_cancel
        _, summary = self.run_all_with(world, contained=plain)
        self.assertEqual(summary["probes"]["PROC-08"]["status"], "inconclusive")
        self.assertEqual(summary["effects"]["process"]["status"], "inconclusive")

    def test_cancel_half_is_driven_through_the_contained_executor_with_an_event(self):
        world = World(self)
        _, summary = self.run_all(world)
        self.assertTrue(summary["passRuleSatisfied"])
        self.assertEqual([(m, p) for m, p, _ in world.cancel_calls], [("contained", "PROC-08"), ("contained-launch", "PROC-08")])
        self.assertIsInstance(world.cancel_calls[0][2], threading.Event)
        self.assertTrue(world.cancel_calls[0][2].is_set())  # the watcher cancelled it
        row = next(r for r in self.rows(world) if r["probe"] == "PROC-08" and r["mode"] == "contained")
        self.assertEqual(row["attempts"]["cancel-settlement"], "denied")
        self.assertEqual(row["independent"]["cancel"]["cancelled"], True)

    def rows(self, world):
        return [json.loads(t) for t in (world.tmp / "bundle" / "results.jsonl").read_text().splitlines()]

    def test_cancel_survivor_or_unsettled_cancel_is_an_escape(self):
        for outcome in ({"survivors": 1, "settled": True, "cancelled": True, "escaped": 1},
                        {"survivors": 0, "settled": False, "cancelled": True, "escaped": 0}):
            world = World(self)
            world.cancel = outcome
            _, summary = self.run_all_with(world)
            self.assertEqual(summary["effects"]["process"]["status"], "not-enforced", outcome)
        for outcome in ({"survivors": 0, "settled": True, "cancelled": False, "escaped": 0},):
            world = World(self)
            world.cancel = outcome
            _, summary = self.run_all_with(world)
            self.assertEqual(summary["effects"]["process"]["status"], "inconclusive", outcome)

    def test_a_swept_leaver_in_the_cancel_half_is_not_an_escape_but_a_survivor_scan_hit_is(self):
        world = World(self)
        world.cancel = {"survivors": 0, "settled": False, "cancelled": True, "escaped": 2}
        _, summary = self.run_all_with(world)
        self.assertTrue(summary["passRuleSatisfied"])
        world = World(self)
        world.contained_survivors = 1  # the independent scan still sees a nonce process
        _, summary = self.run_all_with(world)
        self.assertEqual(summary["probes"]["PROC-08"]["status"], "allowed")

    def test_cancel_half_needs_the_helper_to_have_begun_and_an_available_process_table(self):
        world = World(self)
        base = world.run("contained")

        def quiet(source, workdir, wall, arena, *, cancel=None):
            result = base(source, workdir, wall, arena, cancel=cancel)
            return result if cancel is None else q.ExecResult(b"", None, cancelled=True, surviving_processes=0)
        quiet.accepts_cancel = True
        _, summary = self.run_all_with(world, contained=quiet)
        self.assertEqual(summary["probes"]["PROC-08"]["status"], "inconclusive")
        world = World(self)
        _, summary = self.run_all_with(world, process_table=lambda: (_ for _ in ()).throw(OSError("ps")))
        self.assertEqual(summary["probes"]["PROC-08"]["status"], "inconclusive")

    def test_cancel_half_refusal_is_recorded_and_inconclusive(self):
        world = World(self)
        base = world.run("contained")

        def refusing(source, workdir, wall, arena, *, cancel=None):
            if cancel is not None:
                raise lab.LabError("dedicated-user-busy")
            return base(source, workdir, wall, arena)
        refusing.accepts_cancel = True
        out, summary = self.run_all_with(world, contained=refusing)
        self.assertEqual(summary["probes"]["PROC-08"]["status"], "inconclusive")
        row = next(r for r in self.rows(world) if r["probe"] == "PROC-08" and r["mode"] == "contained")
        self.assertEqual(row["independent"]["cancel"]["refused"], "dedicated-user-busy")

    def test_swept_group_leaver_is_not_an_escape_but_a_survivor_is(self):
        """RV-01: PROC-04 and PROC-08 judge the backend's surviving count, not the strict settled flag."""
        for pid in ("PROC-04", "PROC-08"):
            world = World(self)
            world.unsettled.add(pid)  # the strict flag is false whenever a leaver was seen
            world.accounting[("contained", pid)] = (2, 0)
            world.accounting[("contained-launch", pid)] = (1, 0)
            out, summary = self.run_all(world)
            self.assertEqual(summary["probes"][pid]["status"], "denied", pid)
            self.assertTrue(summary["probes"][pid]["pass"], pid)
            rows = [json.loads(t) for t in (out / "results.jsonl").read_text().splitlines()]
            row = next(r for r in rows if r["probe"] == pid and r["mode"] == "contained")
            self.assertEqual((row["independent"]["escapedProcesses"], row["independent"]["survivingProcesses"]),
                             (2, 0))
            self.assertTrue(row["settled"])
            world = World(self)
            world.unsettled.add(pid)
            world.accounting[("contained-launch", pid)] = (2, 1)  # the sweep could not kill one
            _, summary = self.run_all(world)
            self.assertEqual(summary["probes"][pid]["status"], "allowed", pid)
            self.assertEqual(summary["effects"]["process"]["status"], "not-enforced")

    def test_unsettled_group_without_a_swept_leaver_is_still_an_escape(self):
        world = World(self)
        world.unsettled.add("PROC-04")
        _, summary = self.run_all(world)  # the double reports (0 escaped, 0 surviving) yet unsettled
        self.assertEqual(summary["probes"]["PROC-04"]["status"], "allowed")
        self.assertFalse(q.swept_settled(q.ExecResult(b"", 0, settled=False)))  # no accounting: strict
        self.assertTrue(q.swept_settled(q.ExecResult(b"", 0, settled=False, escaped_processes=1,
                                                       surviving_processes=0)))
        self.assertFalse(q.swept_settled(q.ExecResult(b"", 0, settled=False, escaped_processes=0,
                                                        surviving_processes=0)))
        self.assertFalse(q.swept_settled(q.ExecResult(b"", 0, settled=False, escaped_processes=3,
                                                        surviving_processes=1)))

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
            world.runner().run(out, environment=environment(backend="leaks DUMMYSECRET here"),
                               secrets=["DUMMYSECRET"])
        self.assertEqual(raised.exception.reason, "secret-in-artifact")
        self.assertNotIn("DUMMYSECRET", str(raised.exception))
        self.assertFalse([name for name in q.BUNDLE_FILES if (out / name).exists()])

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
        self.assertEqual(len(rows), sum(len(q.QualificationProbeRunner.modes(p)) for p in q.CATALOG))
        self.assertIn("arena-path-too-long", [r.get("refused") for r in rows])
        self.assertFalse(summary["passRuleSatisfied"])

    def test_escape_observed_without_a_control_row_is_not_hidden(self):
        _, contained, *_ = row("FS-01", "allowed", {"outside-dir": "allowed", "tmp-path": "denied",
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

    def test_net_05_cli_is_judged_on_the_proxy_counters(self):
        base = self.session("oauth")
        target = "api.anthropic.com:443"

        def verdict(egress):
            return q.classify_session("NET-05-CLI", replace(base, egress=egress))

        clean = {"connections": 2, "allowed": 2, f"allowed:{target}": 2}
        self.assertEqual(verdict(clean), "denied")
        self.assertEqual(verdict(clean | {"denied": 1, "denied:target-not-allowed": 1}), "denied")
        self.assertEqual(q.classify_session("NET-05-CLI", base), "inconclusive")  # no tap
        self.assertEqual(verdict(clean | {"unexpectedDirect": 1}), "allowed")
        self.assertEqual(verdict({"unexpectedDirect": 2}), "allowed")
        self.assertEqual(verdict({"allowed": 1, "allowed:evil.example:443": 1}), "allowed")
        # no tunnel at all, refusals alone, or counters that disagree prove nothing
        self.assertEqual(verdict({}), "inconclusive")
        self.assertEqual(verdict({"denied": 1, "denied:sni-mismatch": 1}), "inconclusive")
        self.assertEqual(verdict({"allowed": 2, f"allowed:{target}": 1}), "inconclusive")
        self.assertEqual(verdict({"allowed": 1}), "inconclusive")
        # malformed counters
        for bad in ({"allowed": -1}, {"allowed": True}, {"allowed": "1"}, {1: 1}, ["allowed"], "x"):
            self.assertEqual(verdict(bad), "inconclusive", bad)
        no_init = replace(self.session("oauth"), stdout=b"", egress=clean)
        self.assertEqual(q.classify_session("NET-05-CLI", no_init), "inconclusive")

    def test_net_05_cli_judges_tunnels_against_the_policy_endpoints(self):
        # F4: a refresh host the policy lists (NC-1 evidence) is a designed tunnel, not an escape
        refresh = "console.anthropic.com:443"
        counters = {"connections": 2, "allowed": 2, "allowed:api.anthropic.com:443": 1, f"allowed:{refresh}": 1}
        session = replace(self.session("oauth"), egress=counters)
        self.assertEqual(q.classify_session("NET-05-CLI", session), "allowed")  # default: the static endpoint
        self.assertEqual(q.classify_session("NET-05-CLI", session, endpoints=(*mac.ALLOWED_ENDPOINTS, refresh)),
                         "denied")
        other = replace(session, egress={"allowed": 1, "allowed:evil.example:443": 1})
        self.assertEqual(q.classify_session("NET-05-CLI", other, endpoints=(*mac.ALLOWED_ENDPOINTS, refresh)),
                         "allowed")

    def test_runner_judges_sessions_against_its_endpoints(self):
        refresh = "console.anthropic.com:443"
        world = World(self)
        world.egress = {"connections": 2, "allowed": 2, "allowed:api.anthropic.com:443": 1, f"allowed:{refresh}": 1}
        probe = q.BY_ID["NET-05-CLI"]
        self.assertEqual(world.runner().run_mode(probe, "contained")["attempts"]["session"], "allowed")
        listed = world.runner(endpoints=(*mac.ALLOWED_ENDPOINTS, refresh))
        self.assertEqual(listed.run_mode(probe, "contained")["attempts"]["session"], "denied")

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

    def __init__(self, stdout=OAUTH_STREAM, error=None, evidence=True, egress=None):
        self.stdout, self.error, self.calls, self.egress = stdout, error, [], egress
        self.run_evidence = ([{"quota": {"fiveHourPercent": 12}, "executionAuthorization": False}]
                             if evidence else [])

    def version(self):
        self.calls.append("version")
        return "2.1.292 (Claude Code)"

    def run(self, plan, prompt, limits, cancel):
        self.calls.append(("run", plan.argv, prompt, limits))
        if self.error:
            raise hc.ClaudeHostError(self.error)
        if self.egress is None:  # a run that carries no accounting (e.g. the route-unverified kill path)
            return hc.HostRun(self.stdout, 0)
        return mac.ContainedHostRun(self.stdout, 0, egress=self.egress)


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

    def test_driver_reports_the_run_own_egress_delta_not_the_backend_totals(self):
        own = {"connections": 2, "allowed": 2, "allowed:api.anthropic.com:443": 2, "bytesUp": 9}
        result = q.native_session_driver(lambda: FakeNativeTransport(egress=own))("NET-05-CLI")
        self.assertEqual(result.egress, own)
        self.assertEqual(q.classify_session("NET-05-CLI", result), "denied")

    def test_pre_session_tunnels_of_the_backend_do_not_count_as_cli_traffic(self):
        # DRV-01: the NC-11 subset opens NET-06 tunnels to the allowed host before the CLI starts. The
        # backend takes the run's delta after them, so a CLI that sent nothing has an empty delta.
        silent = q.native_session_driver(lambda: FakeNativeTransport(egress={}))("NET-05-CLI")
        self.assertEqual(silent.egress, {})
        self.assertEqual(q.classify_session("NET-05-CLI", silent), "inconclusive")
        unobserved = q.native_session_driver(FakeNativeTransport)("NET-05-CLI")  # no accounting at all
        self.assertIsNone(unobserved.egress)
        self.assertEqual(q.classify_session("NET-05-CLI", unobserved), "inconclusive")

    def test_a_malformed_run_delta_is_not_an_observation(self):
        for bad in ({"allowed": True}, {"allowed": -1}, {1: 1}, "allowed"):
            with self.subTest(egress=bad):
                self.assertIsNone(q.native_session_driver(lambda: FakeNativeTransport(egress=bad))("X").egress)

    def test_driver_lists_config_dir_before_and_after_the_session(self):
        listings = iter([{"entries": {"a.json": "1" * 64}, "truncated": False},
                         {"entries": {"a.json": "2" * 64, "projects": "dir"}, "truncated": False}])
        result = q.native_session_driver(FakeNativeTransport, read_config=lambda: next(listings))("HOST-01")
        self.assertEqual((result.config["before"], result.config["after"]), (1, 2))
        self.assertEqual((result.config["added"], result.config["removed"], result.config["modified"]),
                         (["projects"], [], ["a.json"]))
        self.assertEqual(result.config["digests"], {"a.json": "2" * 64, "projects": "dir"})  # changed ones only

    def test_an_unreadable_config_dir_is_unavailable_not_empty(self):
        def broken():
            raise OSError("gone")

        for reader in (None, broken, lambda: None):
            self.assertIsNone(q.native_session_driver(FakeNativeTransport, read_config=reader)("HOST-01").config)

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
        with mock.patch.object(q.subprocess, "run", return_value=SimpleNamespace(stdout=listing, stderr="", returncode=0)):
            self.assertEqual(q.scan_processes("nonce123"), [101, 303])

    def test_kill_processes_ignores_missing_pids(self):
        with mock.patch.object(q.os, "kill", side_effect=[None, ProcessLookupError()]) as kill:
            q.kill_processes([1, 2])
        self.assertEqual([c.args[0] for c in kill.call_args_list], [1, 2])


class F4RunnerTests(unittest.TestCase):
    def make(self, outcome_for):
        world = World(self)
        calls = []

        class Policy(SimpleNamespace):
            def render(self, entry):
                body = b'(allow process-exec (literal "/c/claude"))\n'
                if entry == q.LAUNCH_PROBE_ENTRY:
                    body = b'(allow process-exec (literal "/c/claude") (literal "/c/python"))\n'
                return body

        class Backend:
            policy = Policy(proxy_port=45123, probe_catalog_sha256=q.CATALOG_SHA256, interpreter="/c/python",
                            run_root="/r", config_dir="/c/cfg", interpreter_root="/c")

            def run_probe(self, source, workdir, limits):
                probe = world.probe_of(source)
                calls.append((probe.id, workdir, limits))
                outcome = outcome_for(probe)
                return lab.ChildResult(lines({n: outcome for n in probe.counted}), 0, False, False, True)

            def run_launch_probe(self, source, workdir, limits):
                calls.append(("launch-probe", world.probe_of(source).id, workdir, limits))
                return self.run_probe(source, workdir, limits)

        runner = q.make_f4_probe_runner(arena_parent=world.tmp, workdir_factory=lambda: world.tmp,
                                        arena_factory=world.arena)
        return runner, Backend(), calls, world

    def test_runs_only_the_contained_probe_and_maps_the_outcome(self):
        runner, backend, calls, world = self.make(lambda p: "allowed" if p.functional else "denied")
        with mock.patch.object(q, "uncontained_executor", side_effect=AssertionError("uncontained")):
            self.assertEqual(runner("FS-01", backend), "denied")
            self.assertEqual(runner("NET-06", backend), "allowed")
        self.assertEqual([c[0] for c in calls], ["FS-01", "launch-probe", "FS-01", "NET-06", "launch-probe", "NET-06"])
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
            arena_parent=tmp, proxy_address="127.0.0.1:1", spawn_sibling=False, lan_ip="", real_home=None)
        for pid in ("FS-01", "FS-02", "FS-03", "FS-04", "FS-05", "FS-06", "CRED-01", "CRED-03", "CRED-04",
                    "PROC-01"):
            with self.subTest(probe=pid):
                row = runner.run_mode(q.BY_ID[pid], "uncontained-control")
                self.assertEqual(set(row["attempts"].values()), {"allowed"}, row)


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


class ReviewCatalogTests(unittest.TestCase):
    """T008 review fixes at catalog level (RV-05 to RV-14, RV-27)."""

    def test_network_probes_are_connect_level_and_name_resolution_is_informational(self):
        net01 = q.BY_ID["NET-01"]
        self.assertEqual(net01.counted, ("tcp-loopback-listener", "tcp-public-literal"))
        self.assertEqual(net01.tripwires, ("tcp-by-name",))
        self.assertIn("tcp4", net01.watch)
        self.assertIn("direct-allowed-host", q.BY_ID["NET-05"].counted)
        self.assertIn("allowed_ip", q.BY_ID["NET-05"].body)
        self.assertEqual(set(q.PROXY_ATTEMPTS), set(q.BY_ID["NET-05"].extra))
        self.assertIn("tcp-lan-listener", q.BY_ID["NET-04"].counted)
        self.assertIn("tcp-lan", q.BY_ID["NET-04"].watch)

    def test_review_classes_have_attempts(self):
        wanted = {
            "FS-01": {"adjacent-candidate-prefix", "adjacent-run-root", "adjacent-config-parent",
                      "adjacent-interpreter-root", "chmod-outside", "chflags-outside", "xattr-outside"},
            "FS-02": {"hardlink-own-tree"}, "FS-03": {"alias-data-volume", "alias-private-var",
                                                       "alias-private-tmp"},
            "FS-05": {"rename-out", "link-out", "copy-in", "clone-in"},
            "FS-06": {"inherited-descriptor", "fifo", "device-node", "dev-ptmx", "dev-fd"},
            "FS-07": {"mach-mds", "mach-mdwrite", "mach-spotlight"},
            "PROC-01": {"exec-written-script"}, "PROC-05": {"real-launch-agent"},
            "PROC-03": {"memory"},
            "PROC-06": {"mach-sweep", "mach-tccd", "iokit-service"},
            "PROC-07": {"signal-supervisor", "ptrace-sibling", "sysctl-proc-all", "sysctl-hw", "list-pids",
                        "shm-posix", "sem-posix", "shm-sysv"}}
        for pid, names in wanted.items():
            self.assertLessEqual(names, set(q.BY_ID[pid].counted), pid)

    def test_informational_attempts_are_tripwires_or_notes_never_counted(self):
        self.assertEqual(q.BY_ID["NET-07"].tripwires, ("raw-socket",))
        self.assertNotIn("raw-socket", q.BY_ID["NET-07"].counted)
        self.assertIn("task-for-pid", q.BY_ID["PROC-07"].tripwires)
        self.assertNotIn("mdfind", q.BY_ID["FS-07"].counted)
        entry = next(e for e in q.catalog_document()["probes"] if e["id"] == "NET-02")
        self.assertIn("tcp-link-local-metadata", entry["tripwires"])
        self.assertEqual(entry["profiles"], ["fixture", q.LAUNCH_PROBE_ENTRY])

    def test_catalog_hash_binds_the_runner_judge_and_arena_source(self):
        self.assertEqual(q.catalog_document()["runnerSha256"],
                         hashlib.sha256(Path(q.__file__).read_bytes()).hexdigest())
        with mock.patch.object(q.Path, "read_bytes", return_value=b"edited runner"):
            self.assertNotEqual(q.catalog_sha256(), q.CATALOG_SHA256)

    def test_an_attempt_the_line_start_scan_would_miss_is_refused(self):
        wrapped = replace(q.BY_ID["PROC-04"], body='def wrapped():\n    attempt("hidden", lambda: True)\n'
                          'attempt("double-fork", lambda: True)\n')
        with self.assertRaises(q.ProbeError) as raised:
            q._validate_catalog([wrapped])
        self.assertEqual(raised.exception.reason, "invalid-catalog")
        q._validate_catalog([replace(wrapped, body='attempt("double-fork", lambda: True)\n')])

    def test_every_call_site_in_the_shipped_catalog_is_declared(self):
        for probe in q.CATALOG:
            if probe.runner == "helper":
                self.assertEqual(len(q._CALL_SITE.findall(probe.body)), len(q._ATTEMPT_CALL.findall(probe.body)),
                                 probe.id)


class PreludeHelperTests(unittest.TestCase):
    """The prelude functions that need no host: executed in-process, defining only."""

    def namespace(self, **document):
        ns = {"A": document}
        exec(q.PRELUDE, ns)
        return ns

    def test_proxy_replies_need_an_explicit_200_or_403(self):
        verdict = self.namespace()["_verdict"]
        self.assertIs(verdict(b"HTTP/1.1 200 Connection Established"), True)
        self.assertIs(verdict(b"HTTP/1.1 403 Forbidden"), False)
        for other in (b"", b"HTTP/1.1 502 Bad Gateway", b"HTTP/1.1 400", b"garbage"):
            self.assertIsNone(verdict(other), other)

    def test_tunnel_is_inconclusive_when_the_proxy_just_closes(self):
        ns = self.namespace()
        server = socket.socket()
        server.bind(("127.0.0.1", 0))
        server.listen(1)
        self.addCleanup(server.close)

        def close_at_once():
            client, _ = server.accept()
            client.recv(1024)
            client.close()

        thread = threading.Thread(target=close_at_once, daemon=True)
        thread.start()
        self.assertIsNone(ns["tunnel"]("127.0.0.1:%d" % server.getsockname()[1], "example.com", 443))
        thread.join(2)

    def test_mach_sweep_needs_one_explicit_refusal_to_be_a_denial(self):
        ns = self.namespace(mach_names=["a.b.c", "d.e.f", "g.h.i"])
        for table, expected in (({"a.b.c": None, "d.e.f": True, "g.h.i": False}, True),
                                ({"a.b.c": None, "d.e.f": False, "g.h.i": None}, False),
                                ({"a.b.c": None, "d.e.f": None, "g.h.i": None}, None)):
            ns["mach"] = table.get
            self.assertIs(ns["mach_sweep"](), expected, table)
        self.assertIsNone(self.namespace(mach_names=[])["mach_sweep"]())

    def test_descriptor_inventory_sees_only_what_is_open(self):
        ns = self.namespace()
        with open(os.devnull) as handle:
            descriptor = handle.fileno()
            self.assertIn(descriptor, ns["open_descriptors"]())
        self.assertNotIn(descriptor, ns["open_descriptors"]())

    def test_gaierror_is_a_denial_only_for_the_explicit_dns_attempt(self):
        ns = self.namespace()

        def lookup():
            raise socket.gaierror(8, "x")

        self.assertEqual(ns["_classify"](lookup, ns["DENY"], False)[0], "inconclusive")
        self.assertEqual(ns["_classify"](lookup, ns["DENY"], True)[0], "denied")


class JudgeProfileTests(unittest.TestCase):
    """RV-04: helper probes must hold under the fixture and the launch-probe profile."""

    def three(self, pid, control, contained, launch):
        probe = q.BY_ID[pid]
        names = probe.counted
        base = {"settled": True, "escalated": False}
        return (dict(base, probe=pid, mode="uncontained-control", attempts={n: control for n in names}),
                dict(base, probe=pid, mode="contained", attempts={n: contained for n in names}),
                dict(base, probe=pid, mode="contained-launch", attempts={n: launch for n in names}))

    def test_an_escape_only_under_the_launch_profile_is_not_enforced(self):
        rows = self.three("FS-01", "allowed", "denied", "allowed")
        verdict = q.judge_probe(q.BY_ID["FS-01"], *rows)
        self.assertEqual((verdict["status"], verdict["pass"], verdict["reason"]), ("allowed", False, "escape-allowed"))
        self.assertEqual(verdict["profiles"][q.LAUNCH_PROBE_ENTRY]["status"], "allowed")
        summary = q.summarize(passing_rows(override={"FS-01": rows}))
        self.assertEqual(summary["effects"]["filesystem"]["status"], "not-enforced")

    def test_missing_launch_row_blocks_the_pass_but_is_not_an_escape(self):
        control, contained, _ = self.three("FS-01", "allowed", "denied", "denied")
        verdict = q.judge_probe(q.BY_ID["FS-01"], control, contained)
        self.assertEqual((verdict["status"], verdict["pass"]), ("inconclusive", False))
        self.assertEqual(verdict["profiles"][q.LAUNCH_PROBE_ENTRY]["reason"], "mode-missing")

    def test_both_profiles_passing_passes_and_reports_both(self):
        verdict = q.judge_probe(q.BY_ID["FS-01"], *self.three("FS-01", "allowed", "denied", "denied"))
        self.assertTrue(verdict["pass"])
        self.assertEqual({k: v["status"] for k, v in verdict["profiles"].items()},
                         {"fixture": "denied", q.LAUNCH_PROBE_ENTRY: "denied"})

    def test_functional_probe_must_work_under_both_profiles(self):
        ok = self.three("NET-06", "allowed", "allowed", "allowed")
        self.assertTrue(q.judge_probe(q.BY_ID["NET-06"], *ok)["pass"])
        broken = self.three("NET-06", "allowed", "allowed", "denied")
        verdict = q.judge_probe(q.BY_ID["NET-06"], *broken)
        self.assertEqual((verdict["status"], verdict["pass"]), ("denied", False))

    def test_session_probes_have_no_launch_profile_row(self):
        control, contained = row("HOST-01", "allowed", "allowed")
        self.assertTrue(q.judge_probe(q.BY_ID["HOST-01"], control, contained)["pass"])
        with self.assertRaises(q.ProbeError):
            World(self).runner().run_mode(q.BY_ID["HOST-01"], "contained-launch")


class LaunchProbeExecutorTests(unittest.TestCase):
    LAUNCH = (b'(allow process-exec (literal "/c/claude"))\n'
              b'(allow file-read* file-map-executable (literal "/") (literal "/c/claude"))\n'
              b'(allow file-write* (subpath "/w"))\n')
    PROBE = (b'(allow process-exec (literal "/c/claude") (literal "/c/python"))\n'
             b'(allow file-read* file-map-executable (literal "/") (literal "/c/claude") (literal "/c/python"))\n'
             b'(allow file-write* (subpath "/w"))\n')

    def test_delta_must_be_exactly_the_interpreter_literal(self):
        delta = q.launch_probe_delta_is_interpreter_only
        self.assertTrue(delta(self.LAUNCH, self.PROBE, "/c/python"))
        self.assertFalse(delta(self.LAUNCH, self.LAUNCH, "/c/python"))  # nothing added
        self.assertFalse(delta(self.LAUNCH, self.PROBE + b"(allow network*)\n", "/c/python"))
        self.assertFalse(delta(self.LAUNCH, self.PROBE.replace(b"(literal \"/\")", b"(subpath \"/\")"), "/c/python"))
        self.assertFalse(delta(self.PROBE, self.PROBE, "/c/python"))  # the launch profile already allows it
        widened = self.PROBE.replace(b'(subpath "/w"))', b'(subpath "/w") (literal "/c/python"))')
        self.assertFalse(delta(self.LAUNCH, widened, "/c/python"))  # a write rule gained the literal

    def backend(self, launch=LAUNCH, probe=PROBE, hook=True):
        calls = []

        class Policy:
            interpreter = "/c/python"
            interpreter_root = "/c"

            def render(self, entry):
                return launch if entry == "launch" else probe

        class Backend:
            policy = Policy()

            def run_probe(self, *a):
                raise AssertionError("fixture entry used for the launch profile")

        if hook:
            def run_launch_probe(source, workdir, limits):
                calls.append((source, workdir, limits))
                return lab.ChildResult(b"out", 0, False, False, True)
            Backend.run_launch_probe = staticmethod(run_launch_probe)
        return Backend(), calls

    def test_launch_profile_uses_the_hook_with_the_factory_workdir(self):
        backend, calls = self.backend()
        work = Path("/w/candidate")
        executor = q.ContainedExecutor(backend, lambda: work, q.LAUNCH_PROBE_ENTRY)
        self.assertEqual(executor.workdir(), work)
        result = executor(b"x", Path("ignored"), 5, None)
        self.assertEqual(calls, [(b"x", work, lab.FixtureLimits(wall_seconds=5))])
        self.assertEqual(result.limit_exceeded, "unavailable")

    def test_backend_without_the_hook_or_the_profile_is_unsupported_not_a_pass(self):
        for backend in (self.backend(hook=False)[0], SimpleNamespace(run_probe=lambda *a: None)):
            with self.assertRaises(lab.LabError) as raised:
                q.ContainedExecutor(backend, lambda: Path("/w"), q.LAUNCH_PROBE_ENTRY)(b"", Path("/w"), 1, None)
            self.assertEqual(raised.exception.reason, "launch-probe-unsupported")

    def test_a_profile_that_drifted_from_launch_is_refused(self):
        backend, calls = self.backend(probe=self.PROBE + b"(allow file-write* (subpath \"/\"))\n")
        with self.assertRaises(lab.LabError) as raised:
            q.ContainedExecutor(backend, lambda: Path("/w"), q.LAUNCH_PROBE_ENTRY)(b"", Path("/w"), 1, None)
        self.assertEqual(raised.exception.reason, "launch-probe-profile-drift")
        self.assertEqual(calls, [])

    def test_unknown_profile_is_refused(self):
        with self.assertRaises(q.ProbeError):
            q.ContainedExecutor(object(), lambda: Path("/w"), "other")

    def test_backend_stop_reason_is_carried_when_reported(self):
        class Backend:
            def run_probe(self, *a):
                return SimpleNamespace(stdout=b"", exit_code=None, timed_out=False, output_truncated=False,
                                       settled=True, limit_exceeded="memory")

        result = q.ContainedExecutor(Backend(), lambda: Path("/w"))(b"", Path("/w"), 1, None)
        self.assertEqual(result.limit_exceeded, "memory")

    def test_layout_comes_from_the_policy(self):
        policy = SimpleNamespace(run_root="/r", config_dir="/c", interpreter_root="/i")
        self.assertEqual(q.layout_from_policy(policy, "/r/w"),
                         {"candidate": "/r/w", "run_root": "/r", "config_dir": "/c", "interpreter_root": "/i"})
        self.assertEqual(q.layout_from_policy(policy, None), {})


class ReviewRunnerTests(unittest.TestCase):
    """Runner behaviour added by the T008 fixes."""

    def run_all(self, world, **over):
        out = world.tmp / "bundle"
        return out, world.runner(**over).run(out, environment=environment())

    def rows(self, out):
        return [json.loads(t) for t in (out / "results.jsonl").read_text().splitlines()]

    def test_escape_only_in_the_launch_profile_row_is_not_enforced(self):
        world = World(self)
        world.launch["FS-03"] = {"case-alias": "allowed"}
        out, summary = self.run_all(world)
        self.assertEqual(summary["effects"]["filesystem"]["status"], "not-enforced")
        self.assertEqual(summary["probes"]["FS-03"]["profiles"][q.LAUNCH_PROBE_ENTRY]["status"], "allowed")
        launch = next(r for r in self.rows(out) if r["probe"] == "FS-03" and r["mode"] == "contained-launch")
        self.assertEqual(launch["profile"], q.LAUNCH_PROBE_ENTRY)

    def test_unconfigured_or_refused_launch_profile_blocks_the_pass(self):
        world = World(self)
        out, summary = self.run_all(world, launch_contained=None)
        refused = next(r for r in self.rows(out) if r["probe"] == "FS-01" and r["mode"] == "contained-launch")
        self.assertEqual(refused["refused"], "launch-probe-not-configured")
        self.assertFalse(summary["passRuleSatisfied"])
        self.assertEqual(summary["effects"]["filesystem"]["status"], "inconclusive")
        world = World(self)
        world.raises[("contained-launch", "PROC-01")] = lab.LabError("launch-probe-unsupported")
        out, summary = self.run_all(world)
        self.assertEqual(summary["probes"]["PROC-01"]["status"], "inconclusive")
        self.assertEqual(summary["effects"]["process"]["status"], "inconclusive")

    def test_tripwire_success_in_the_contained_run_escalates_but_not_in_the_control(self):
        world = World(self)
        world.trips[("uncontained-control", "NET-07")] = {"raw-socket": "allowed"}
        _, summary = self.run_all(world)
        self.assertTrue(summary["passRuleSatisfied"])
        world = World(self)
        world.trips[("contained", "NET-07")] = {"raw-socket": "allowed"}
        out, summary = self.run_all(world)
        self.assertEqual(summary["effects"]["network"]["status"], "not-enforced")
        contained = next(r for r in self.rows(out) if r["probe"] == "NET-07" and r["mode"] == "contained")
        self.assertEqual(contained["independent"]["tripwires"], ["raw-socket"])
        world = World(self)
        world.trips[("contained-launch", "NET-07")] = {"raw-socket": "allowed"}
        self.assertEqual(self.run_all(world)[1]["effects"]["network"]["status"], "not-enforced")

    def test_a_denied_tripwire_changes_nothing(self):
        world = World(self)
        world.trips[("contained", "NET-07")] = {"raw-socket": "denied"}
        self.assertTrue(self.run_all(world)[1]["passRuleSatisfied"])

    def test_memory_denial_needs_the_backends_memory_stop_reason(self):
        for reason in (None, "unavailable", "cpu"):
            world = World(self)
            world.limit_exceeded["PROC-03"] = reason
            _, summary = self.run_all(world)
            self.assertEqual(summary["probes"]["PROC-03"]["status"], "inconclusive", reason)
            self.assertEqual(summary["effects"]["process"]["status"], "inconclusive")
        world = World(self)
        out, summary = self.run_all(world)
        self.assertEqual(summary["probes"]["PROC-03"]["status"], "denied")
        row_ = next(r for r in self.rows(out) if r["probe"] == "PROC-03" and r["mode"] == "contained")
        self.assertEqual(row_["limitExceeded"], "memory")
        self.assertIn("outputTruncated", row_)

    def test_process_table_diff_finds_a_survivor_the_nonce_scan_cannot_see(self):
        world = World(self)
        state = {"calls": 0}

        def table():
            state["calls"] += 1
            return {(1, "t0")} if state["calls"] % 2 else {(1, "t0"), (9, "t1")}

        out, summary = self.run_all(world, process_table=table)
        self.assertNotIn(9, world.killed)  # unattributed processes are reported, never killed, by default
        killing = World(self)
        state["calls"] = 0
        self.run_all(killing, process_table=table, kill_table_diff=True)
        self.assertIn(9, killing.killed)
        self.assertEqual(summary["effects"]["process"]["status"], "not-enforced")
        proc02 = next(r for r in self.rows(out) if r["probe"] == "PROC-02" and r["mode"] == "contained")
        self.assertEqual(proc02["independent"]["survivors"], 1)
        self.assertEqual(proc02["independent"]["processTable"], "ok")

    def table_diff_world(self, names, *, child_names=frozenset({"python3.12"}), listing=None):
        """A table that gains pids 9 and 10 during each run; ``names`` is what ``ps -p`` says about them."""
        world, state = World(self), {"calls": 0}

        def table():
            state["calls"] += 1
            return {(1, "t0")} if state["calls"] % 2 else {(1, "t0"), (9, "t1"), (10, "t1")}

        def process_names(pids):
            if isinstance(names, Exception):
                raise names
            return {pid: names[pid] for pid in pids if pid in names}

        out, summary = self.run_all(world, process_table=table, child_names=child_names,
                                    process_names=listing or process_names)
        return world, out, summary

    def contained_row(self, out, probe_id):
        return next(r for r in self.rows(out) if r["probe"] == probe_id and r["mode"] == "contained")

    def test_new_processes_that_no_contained_run_can_start_are_noted_not_counted_as_survivors(self):
        # T009 attempt 3: two to eight new processes of the dedicated user, with the backend reporting nothing
        # surviving, turned PROC-08 allowed; launchd agents are not descendants of a profile that execs only
        # the interpreter, claude and sandbox-exec
        world, out, summary = self.table_diff_world({9: "mdworker_shared", 10: "cfprefsd"})
        proc08 = self.contained_row(out, "PROC-08")
        self.assertEqual(proc08["independent"]["survivors"], 0)
        self.assertEqual(proc08["independent"]["strayProcesses"], {"count": 2, "names": ["cfprefsd", "mdworker_shared"]})
        self.assertEqual(proc08["independent"]["cancel"]["survivors"], 0)
        self.assertEqual(proc08["independent"]["cancel"]["strayProcesses"]["count"], 2)
        self.assertEqual(summary["probes"]["PROC-08"]["status"], "denied")
        self.assertEqual(world.killed.count(9), 0)

    def test_a_new_process_with_an_allowed_executable_name_is_still_a_survivor(self):
        _, out, summary = self.table_diff_world({9: "mdworker_shared", 10: "python3.12"})
        proc08 = self.contained_row(out, "PROC-08")
        self.assertEqual(proc08["independent"]["survivors"], 1)
        self.assertEqual(proc08["independent"]["strayProcesses"]["count"], 1)
        self.assertEqual(summary["probes"]["PROC-08"]["status"], "allowed")
        self.assertEqual(summary["probes"]["PROC-04"]["status"], "allowed")

    def test_a_failing_ps_counts_every_new_process_and_without_names_nothing_is_filtered(self):
        _, out, summary = self.table_diff_world(OSError("ps"))
        self.assertEqual(self.contained_row(out, "PROC-08")["independent"]["survivors"], 2)
        self.assertNotIn("strayProcesses", self.contained_row(out, "PROC-08")["independent"])
        _, out, _ = self.table_diff_world({9: "mdworker_shared"}, child_names=None)
        self.assertEqual(self.contained_row(out, "PROC-08")["independent"]["survivors"], 2)

    def test_a_process_that_ps_no_longer_lists_is_gone_and_survives_nothing(self):
        _, out, _ = self.table_diff_world({})
        self.assertEqual(self.contained_row(out, "PROC-08")["independent"]["survivors"], 0)

    def test_live_process_names_skips_zombies_and_takes_the_executable_basename(self):
        listing = "  9 Ss   /usr/libexec/cfprefsd\n 10 Z    (python3.12)\n 11 R+ /opt/py/bin/python3.12\n bad\n"
        with mock.patch.object(q.subprocess, "run", return_value=SimpleNamespace(stdout=listing, stderr="", returncode=0)) as run:
            self.assertEqual(q.live_process_names([9, 10, 11]), {9: "cfprefsd", 11: "python3.12"})
        self.assertEqual(run.call_args.args[0], ["/bin/ps", "-o", "pid=,stat=,comm=", "-p", "9,10,11"])
        self.assertEqual(q.live_process_names([]), {})
        for done in (SimpleNamespace(stdout="", stderr="usage", returncode=2),
                     SimpleNamespace(stdout="", stderr="ps: denied", returncode=1)):
            with mock.patch.object(q.subprocess, "run", return_value=done), self.assertRaises(OSError):
                q.live_process_names([9])
        with mock.patch.object(q.subprocess, "run", return_value=SimpleNamespace(stdout="", stderr="", returncode=1)):
            self.assertEqual(q.live_process_names([9]), {})  # no pid matched: they are gone

    def test_descendant_names_come_from_the_exec_allow_list_and_this_interpreter(self):
        policy = SimpleNamespace(claude="/x/bin/claude-2.1.292", interpreter="/x/py/bin/python3.12",
                                 helpers=(("/x/bin/helper", "h"),))
        names = q.descendant_names(policy)
        self.assertTrue({"claude-2.1.292", "python3.12", "helper", "sandbox-exec", "Python"} <= names)
        self.assertNotIn("mdworker_shared", names)

    def test_a_member_the_sweep_killed_while_it_was_exiting_does_not_unsettle_a_limit_kill(self):
        # T009 attempt 3, launch-probe PROC-03: the watchdog fired, the group was swept, one dying member was
        # seen on the way out (escaped 1, surviving 0), and the row read unsettled, hence allowed
        world = World(self)
        world.unsettled.add("PROC-03")
        world.accounting[("contained", "PROC-03")] = (1, 0)
        world.accounting[("contained-launch", "PROC-03")] = (1, 0)
        _, summary = self.run_all(world)
        self.assertEqual(summary["probes"]["PROC-03"]["status"], "denied")
        still = World(self)
        still.unsettled.add("PROC-03")
        still.accounting[("contained", "PROC-03")] = (1, 1)  # something outlived the sweep
        self.assertEqual(self.run_all(still)[1]["probes"]["PROC-03"]["status"], "allowed")

    def test_survival_needs_the_helper_to_have_actually_tried(self):
        world = World(self)
        world.contained["PROC-04"] = {"double-fork": "inconclusive"}
        _, summary = self.run_all(world)
        self.assertEqual(summary["probes"]["PROC-04"]["status"], "inconclusive")

    def test_unavailable_process_table_cannot_pass_a_survivor_probe(self):
        world = World(self)

        def broken():
            raise OSError("ps")

        out, summary = self.run_all(world, process_table=broken)
        proc02 = next(r for r in self.rows(out) if r["probe"] == "PROC-02" and r["mode"] == "contained")
        self.assertEqual(proc02["independent"]["processTable"], "unavailable")
        self.assertFalse(summary["passRuleSatisfied"])
        self.assertEqual(summary["effects"]["process"]["status"], "inconclusive")

    def test_the_supervisor_environment_carries_a_dummy_only_while_the_contained_helper_runs(self):
        world = World(self)
        seen = {}
        base = world.run("contained")

        def spying(source, workdir, wall, arena):
            seen[world.probe_of(source).id] = os.environ.get("BRAID_DUMMY_abcdef012345")
            return base(source, workdir, wall, arena)

        control_seen = []
        control = world.run("uncontained-control")

        def control_spy(source, workdir, wall, arena):
            control_seen.append(os.environ.get("BRAID_DUMMY_abcdef012345"))
            return control(source, workdir, wall, arena)

        self.run_all(world, contained=spying, control=control_spy)
        self.assertEqual(set(seen.values()), {"braid-dummy-fake-marker"})
        self.assertEqual(set(control_seen), {None})
        self.assertNotIn("BRAID_DUMMY_abcdef012345", os.environ)

    def test_arena_receives_resolved_addresses_layout_and_mach_names_only_where_needed(self):
        world = World(self)
        resolved = []
        self.run_all(world, allowed_ip=None, resolver=lambda host: resolved.append(host) or "192.0.2.9",
                     layout=lambda workdir: {"candidate": "/x"})
        self.assertEqual(resolved, ["api.anthropic.com"])
        by_probe = {}
        for arena in world.arenas:
            by_probe.setdefault(arena.kwargs["allowed_ip"], 0)
            by_probe[arena.kwargs["allowed_ip"]] += 1
        self.assertEqual(by_probe["192.0.2.9"], 3)  # NET-05 in the three helper modes
        names = [a.kwargs["mach_names"] for a in world.arenas if a.kwargs["mach_names"]]
        self.assertEqual(len(names), 3)
        self.assertEqual(names[0], ["com.apple.fake.service"])
        layouts = [a.kwargs["layout"] for a in world.arenas]
        self.assertIn(None, layouts)  # the control builds its own analogue
        self.assertIn({"candidate": "/x"}, layouts)

    def test_mach_names_are_recorded_in_the_bundle_and_filtered(self):
        world = World(self)
        out, _ = self.run_all(world, mach_names=lambda: ["com.apple.ok.name", "bad name", "../x", "a.b"])
        rows = [r for r in self.rows(out) if r["probe"] == "PROC-06" and r["mode"] != "uncontained-control"]
        self.assertTrue(rows and all(r["machNames"] == ["com.apple.ok.name"] for r in rows))

    def test_proxy_parsing_results_are_judged_with_the_probe(self):
        world = World(self)
        world.proxy["proxy-userinfo"] = "allowed"
        out, summary = self.run_all(world)
        self.assertEqual(summary["effects"]["network"]["status"], "not-enforced")
        contained = next(r for r in self.rows(out) if r["probe"] == "NET-05" and r["mode"] == "contained")
        self.assertEqual(contained["attempts"]["proxy-userinfo"], "allowed")
        world = World(self)
        world.proxy["proxy-sni-mismatch"] = "inconclusive"
        self.assertEqual(self.run_all(world)[1]["probes"]["NET-05"]["status"], "inconclusive")


class SessionStopRuleTests(unittest.TestCase):
    """RV-15: NC-10 2 % stop rule with pre/post readings, and a persisted session count."""

    def run_all(self, world, out=None, **over):
        out = out or world.tmp / "bundle"
        return out, world.runner(**over).run(out, environment=environment())

    def rows(self, out):
        return {(r["probe"], r["mode"]): r for r in map(json.loads, (out / "results.jsonl").read_text().splitlines())}

    def test_within_two_percent_runs_all_three_sessions_and_records_decisions(self):
        world = World(self)
        out, summary = self.run_all(world)
        self.assertEqual(len(world.session_calls), 3)
        quota = json.loads((out / "quota.json").read_text())
        self.assertEqual(quota["sessionsStarted"], 3)
        decision = quota["sessions"][0]["decision"]
        self.assertTrue(decision["proceed"])
        self.assertEqual(decision["evidence"]["fiveHourDelta"], 1)
        self.assertEqual(quota["sessions"][0]["quota"]["pre"]["fiveHourPercent"], 10)

    def test_a_session_above_two_percent_stops_the_attempt(self):
        world = World(self)
        order = [p.id for p in q.CATALOG if p.runner == "session"]
        world.post[order[0]] = 13
        out, _ = self.run_all(world)
        self.assertEqual(world.session_calls, [order[0]])
        rows = self.rows(out)
        self.assertEqual(rows[(order[0], "contained")]["quotaStop"], "probe-above-five-hour-cap")
        self.assertEqual(rows[(order[1], "contained")]["refused"], "quota-stop")
        quota = json.loads((out / "quota.json").read_text())
        self.assertFalse(quota["sessions"][0]["decision"]["proceed"])
        self.assertEqual(quota["sessionsStarted"], 1)

    def test_missing_stale_or_malformed_readings_stop_like_an_overrun(self):
        for quota, reason in (({}, "missing-pre-reading"), ({"pre": reading(60, 10)}, "missing-post-reading"),
                              ({"pre": reading(900, 10), "post": reading(800, 10)}, "stale-post-reading"),
                              ({"pre": reading(60, 10), "post": {"fiveHourPercent": 10}}, "unparseable-reading")):
            world = World(self)
            world.driver = lambda probe_id, quota=quota: (world.session_calls.append(probe_id) or
                                                          q.SessionResult(OAUTH_STREAM, 0, quota=quota))
            out, _ = self.run_all(world)
            self.assertEqual(len(world.session_calls), 1, reason)
            first = next(iter(json.loads((out / "quota.json").read_text())["sessions"]))
            self.assertEqual(first["decision"]["reason"], reason)

    def test_a_refused_session_stops_further_sessions(self):
        world = World(self)
        world.driver = lambda probe_id: world.session_calls.append(probe_id) or q.SessionResult(refused="quota-stop")
        self.run_all(world)
        self.assertEqual(len(world.session_calls), 1)

    def test_the_count_survives_a_failed_run_so_a_retry_cannot_exceed_three(self):
        class Crash(BaseException):
            pass

        world = World(self)
        out = world.tmp / "bundle"
        calls = []

        def driver(probe_id):
            calls.append(probe_id)
            if len(calls) == 2:
                raise Crash
            return world.driver(probe_id)

        with self.assertRaises(Crash):
            world.runner(sessions=driver).run(out, environment=environment())
        counter = json.loads((out / q.SESSION_COUNT_FILE).read_text())
        self.assertEqual(counter, {"sessionsStarted": 2, "quotaStop": None})
        self.assertEqual(oct((out / q.SESSION_COUNT_FILE).stat().st_mode & 0o777), "0o600")
        retry = World(self)
        summary = retry.runner().run(out, environment=environment())
        self.assertEqual(len(retry.session_calls), 1)  # only the one session left
        self.assertEqual(json.loads((out / "quota.json").read_text())["sessionsStarted"], 3)
        self.assertEqual(sorted(p.name for p in out.iterdir()), sorted(q.BUNDLE_FILES))
        self.assertFalse(summary["passRuleSatisfied"])
        self.assertEqual(q.verify_bundle(out), summary["bundleSha256"])

    def test_a_directory_with_anything_but_the_counter_is_still_refused(self):
        world = World(self)
        out = world.tmp / "bundle"
        out.mkdir()
        (out / q.SESSION_COUNT_FILE).write_text(json.dumps({"sessionsStarted": 3}))
        (out / "stray").write_text("x")
        with self.assertRaises(q.ProbeError) as raised:
            world.runner().run(out, environment=environment())
        self.assertEqual(raised.exception.reason, "bundle-exists")

    def test_a_corrupt_counter_or_a_stored_stop_cannot_reopen_the_budget(self):
        for content in ("not json", json.dumps({"sessionsStarted": "x"}), json.dumps([1]),
                        json.dumps({"sessionsStarted": 1, "quotaStop": "probe-above-five-hour-cap"})):
            world = World(self)
            out = world.tmp / "bundle"
            out.mkdir()
            (out / q.SESSION_COUNT_FILE).write_text(content)
            self.run_all(world, out=out)
            self.assertEqual(world.session_calls, [], content)

    def test_a_stored_count_of_three_refuses_every_session(self):
        world = World(self)
        out = world.tmp / "bundle"
        out.mkdir()
        (out / q.SESSION_COUNT_FILE).write_text(json.dumps({"sessionsStarted": 3}))
        self.run_all(world, out=out)
        self.assertEqual(world.session_calls, [])

    def test_native_driver_takes_the_pre_and_post_readings_around_the_session(self):
        readings = iter([reading(60, 10), reading(10, 11)])
        made = []
        driver = q.native_session_driver(lambda: made.append(FakeNativeTransport()) or made[-1],
                                         read_quota=lambda: next(readings))
        result = driver("HOST-01")
        self.assertEqual(result.quota["pre"]["fiveHourPercent"], 10)
        self.assertEqual(result.quota["post"]["fiveHourPercent"], 11)
        self.assertEqual(result.quota["admission"], {"fiveHourPercent": 12})
        self.assertIsNone(q.native_session_driver(lambda: FakeNativeTransport(evidence=False))("HOST-01").quota)


class QualRound3Tests(unittest.TestCase):
    """Round 3 (2026-11-04): not-applicable rules, the repaired controls, the token in the scan list,
    session exit reasons and the PROC-03/04 evidence. No judge is weakened."""

    def rows(self, pid, control, contained, errors):
        probe = q.BY_ID[pid]
        base = {"settled": True, "escalated": False, "probe": pid}
        c = dict(base, mode="uncontained-control", attempts=dict(control), errors=dict(errors))
        k = dict(base, mode="contained", attempts=dict(contained))
        return c, k, dict(k, mode="contained-launch")

    def judge(self, pid, control, contained, errors):
        return q.judge_probe(q.BY_ID[pid], *self.rows(pid, control, contained, errors))

    def all_with(self, pid, value, **over):
        return {n: value for n in q.BY_ID[pid].counted} | over

    # not-applicable rules ----------------------------------------------------------------------------

    def test_an_ipv6_attempt_without_a_route_is_not_applicable_and_the_ipv4_attempt_still_decides(self):
        for code in ("EHOSTUNREACH", "ENETUNREACH", "EADDRNOTAVAIL"):
            with self.subTest(code):
                verdict = self.judge("NET-02", {"tcp-ipv4-literal": "allowed", "tcp-ipv6-literal": "inconclusive"},
                                     self.all_with("NET-02", "denied"), {"tcp-ipv6-literal": code})
                self.assertEqual((verdict["status"], verdict["pass"], verdict["notApplicable"]),
                                 ("denied", True, ["tcp-ipv6-literal"]))

    def test_a_contained_escape_at_a_not_applicable_attempt_is_still_an_escape(self):
        verdict = self.judge("NET-02", {"tcp-ipv4-literal": "allowed", "tcp-ipv6-literal": "inconclusive"},
                             {"tcp-ipv4-literal": "denied", "tcp-ipv6-literal": "allowed"},
                             {"tcp-ipv6-literal": "EHOSTUNREACH"})
        self.assertEqual((verdict["status"], verdict["pass"], verdict["reason"]),
                         ("allowed", False, "escape-allowed"))
        self.assertEqual(q.summarize(passing_rows(override={"NET-02": self.rows(
            "NET-02", {"tcp-ipv4-literal": "allowed", "tcp-ipv6-literal": "inconclusive"},
            {"tcp-ipv4-literal": "denied", "tcp-ipv6-literal": "allowed"},
            {"tcp-ipv6-literal": "EHOSTUNREACH"})}))["effects"]["network"]["status"], "not-enforced")

    def test_only_the_listed_attempts_and_codes_are_excluded(self):
        # an unlisted code for a listed attempt, a listed code for an unlisted attempt, a missing errors map
        cases = (("NET-02", {"tcp-ipv4-literal": "allowed", "tcp-ipv6-literal": "inconclusive"},
                  {"tcp-ipv6-literal": "OTHER"}),
                 ("NET-02", {"tcp-ipv4-literal": "inconclusive", "tcp-ipv6-literal": "allowed"},
                  {"tcp-ipv4-literal": "EHOSTUNREACH"}),
                 ("NET-02", {"tcp-ipv4-literal": "allowed", "tcp-ipv6-literal": "inconclusive"}, {}),
                 ("FS-01", {"outside-dir": "inconclusive"}, {"outside-dir": "ABSENT"}),
                 ("CRED-02", {"keychain-file": "inconclusive"}, {"keychain-file": "ABSENT"}),
                 ("PROC-07", {"signal-sibling": "denied"}, {"signal-sibling": "EPERM"}))
        for pid, control, errors in cases:
            with self.subTest(pid=pid, errors=errors):
                full = {n: "allowed" for n in q.BY_ID[pid].counted} | control
                verdict = self.judge(pid, full, self.all_with(pid, "denied"), errors)
                self.assertEqual((verdict["pass"], verdict["reason"], verdict["notApplicable"]),
                                 (False, "positive-control-failed", []))

    def test_an_attempt_that_succeeded_uncontained_is_never_excluded(self):
        verdict = self.judge("NET-02", self.all_with("NET-02", "allowed"), self.all_with("NET-02", "denied"),
                             {"tcp-ipv6-literal": "EHOSTUNREACH"})
        self.assertEqual((verdict["pass"], verdict["notApplicable"]), (True, []))

    def test_each_listed_rule_excludes_exactly_its_attempt(self):
        expected = {("CRED-02", "mach-secd", "ABSENT"), ("FS-07", "mach-spotlight", "ABSENT"),
                    ("PROC-07", "ptrace-sibling", "EPERM"), ("NET-02", "tcp-ipv6-literal", "EHOSTUNREACH")}
        self.assertEqual({(pid, name, codes[0]) for (pid, name), codes in q.NOT_APPLICABLE.items()}, expected)
        for pid, name, code in sorted(expected):
            with self.subTest(pid=pid, attempt=name):
                control = self.all_with(pid, "allowed", **{name: "denied" if code == "EPERM" else "inconclusive"})
                verdict = self.judge(pid, control, self.all_with(pid, "denied"), {name: code})
                self.assertEqual((verdict["pass"], verdict["notApplicable"]), (True, [name]))

    def test_at_least_one_counted_attempt_always_stays_required(self):
        probe = q.BY_ID["NET-01"]
        rules = {("NET-01", name): ("EHOSTUNREACH",) for name in probe.counted}
        control = {"attempts": {n: "inconclusive" for n in probe.counted},
                   "errors": {n: "EHOSTUNREACH" for n in probe.counted}}
        with mock.patch.object(q, "NOT_APPLICABLE", rules):
            self.assertEqual(q.not_applicable(probe, control), frozenset())
        self.assertEqual(q.not_applicable(q.BY_ID["NET-06"], control), frozenset())  # functional: never
        self.assertEqual(q.not_applicable(probe, None), frozenset())

    def test_the_summary_still_requires_every_mandatory_attempt_and_names_the_exclusions(self):
        rows = self.rows("NET-02", {"tcp-ipv4-literal": "allowed", "tcp-ipv6-literal": "inconclusive"},
                         self.all_with("NET-02", "denied"), {"tcp-ipv6-literal": "EHOSTUNREACH"})
        summary = q.summarize(passing_rows(override={"NET-02": rows}))
        self.assertTrue(summary["passRuleSatisfied"])
        self.assertEqual(summary["effects"]["network"]["notApplicable"], {"NET-02": ["tcp-ipv6-literal"]})
        self.assertEqual(summary["probes"]["NET-02"]["notApplicable"], ["tcp-ipv6-literal"])
        # the mandatory IPv4 attempt inconclusive in the contained run still blocks the effect
        weak = self.rows("NET-02", {"tcp-ipv4-literal": "allowed", "tcp-ipv6-literal": "inconclusive"},
                         {"tcp-ipv4-literal": "inconclusive", "tcp-ipv6-literal": "denied"},
                         {"tcp-ipv6-literal": "EHOSTUNREACH"})
        blocked = q.summarize(passing_rows(override={"NET-02": weak}))
        self.assertFalse(blocked["passRuleSatisfied"])
        self.assertEqual(blocked["effects"]["network"]["status"], "inconclusive")
        # a bundle written from such rows verifies: the exclusions are re-derived from the rows
        rows_all = passing_rows(override={"NET-02": rows})
        out = Path(tempfile.mkdtemp(prefix="braid-t007-nab-")) / "bundle"
        self.addCleanup(shutil.rmtree, out.parent, ignore_errors=True)
        written = q.write_bundle(out, environment=environment(), rows=rows_all, quota=[],
                                 summary=q.summarize(rows_all))
        self.assertEqual(q.verify_bundle(out), written["bundleSha256"])
        self.assertEqual(written["effects"]["network"]["notApplicable"], {"NET-02": ["tcp-ipv6-literal"]})

    # prelude ------------------------------------------------------------------------------------------

    def test_an_unregistered_mach_service_reads_as_absent_in_the_helper(self):
        ns = {"A": {}}
        exec(q.PRELUDE, ns)

        def absent():
            raise ns["Absent"]()

        self.assertEqual(ns["_classify"](absent, ns["DENY"], False), ("inconclusive", "ABSENT"))
        for pid, name in (("CRED-02", "mach-secd"), ("FS-07", "mach-spotlight")):
            self.assertRegex(q.BY_ID[pid].body, rf'attempt\("{name}", lambda: mach\("[\w.]+", True\)\)')

    # repaired probes ------------------------------------------------------------------------------------

    def helper(self, limits, *names):
        body = q.BY_ID["PROC-03"].body
        code = "import json\nA = {'limits': %r}\n" % limits + q.PRELUDE
        for name in names:
            start = body.index(f"def {name}(")
            end = body.index("\ndef ", start + 1) if "\ndef " in body[start + 1:] else body.index("\ncpu", start)
            code += body[start:end] + "\n"
        return code

    def run_python(self, code, prelude=""):
        return subprocess.run([sys.executable, "-I", "-S", "-c", prelude + code], capture_output=True,
                              text=True, timeout=60)

    def test_the_open_files_control_has_headroom_and_the_contained_limit_still_stops_it(self):
        code = self.helper({"openFiles": 32}, "open_files")
        free = self.run_python(code + "print(open_files())\n")
        self.assertEqual((free.returncode, free.stdout.strip()), (0, "True"), free.stderr)  # the control opens all
        capped = self.run_python("import resource\nresource.setrlimit(resource.RLIMIT_NOFILE, (32, 32))\n"
                                 + code + "open_files()\n")
        self.assertNotEqual(capped.returncode, 0)
        self.assertIn("OSError", capped.stderr)  # EMFILE under the enforced hard limit

    def test_the_memory_attempt_fills_every_page_with_distinct_incompressible_data(self):
        # T009 attempt 4: one byte per page compressed to almost nothing and the footprint read ~0.7 GiB under an
        # allocation 1 GiB over the limit held 2 s. Founder decision PROC-03 (2026-11-06): incompressible data.
        code = self.helper({}, "incompressible")
        script = (code + "import mmap, zlib\n"
                  "size = 96 << 20\n"  # not a multiple of the 64 MiB tile: the last tile is partial
                  "block = incompressible(size)\n"
                  "assert len(block) == size\n"
                  "pages = range(0, size, mmap.PAGESIZE)\n"
                  "ratios = [len(zlib.compress(block[o:o + mmap.PAGESIZE], 9)) / mmap.PAGESIZE for o in pages]\n"
                  "distinct = len({block[o:o + mmap.PAGESIZE] for o in pages})\n"
                  "print(min(ratios), distinct, len(pages))\n")
        result = self.run_python(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        smallest, distinct, pages = result.stdout.split()
        self.assertGreater(float(smallest), 0.99)  # no page compresses (the partial last tile included)
        self.assertEqual(distinct, pages)  # no two pages are equal, so nothing can share a page

    def test_the_memory_attempt_touches_every_page(self):
        code = self.helper({"memoryBytes": 0}, "incompressible", "memory")  # 1 GiB mapping
        script = ("import resource, sys\n" + code + "memory()\n"
                  "peak = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss\n"
                  "print(peak if sys.platform == 'darwin' else peak * 1024)\n")
        result = self.run_python(script)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertGreater(int(result.stdout), 200 << 20)  # a 1 byte per MiB loop would stay near 30 MiB

    def test_the_var_alias_names_a_runner_owned_file_under_private_var_on_every_layout(self):
        tmp = Path(tempfile.mkdtemp(prefix="bt-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        arena = q.Arena(tmp, public=q.DEFAULT_PUBLIC, proxy="127.0.0.1:9", proxy_enforcing=True,
                        spawn_sibling=False)
        self.addCleanup(arena.close)
        alias = arena.document["var_alias"]
        self.assertTrue(alias.startswith("/var/tmp/braid-probe-var-"), alias)
        self.assertIn("/private" + alias, arena.extra_outside)  # watched as changed and removed on close
        self.assertEqual(arena.document["nonce"], alias.rsplit("-", 1)[1])
        self.assertIn('writes(A["var_alias"]) if A["var_alias"] else None', q.BY_ID["FS-03"].body)

    # PROC-03 / PROC-04 ----------------------------------------------------------------------------------

    def test_the_proc_03_row_reports_what_the_memory_watchdog_measured(self):
        world = World(self)
        base = world.run("contained")

        def contained(source, workdir, wall, arena, *, cancel=None):
            return replace(base(source, workdir, wall, arena, cancel=cancel), peak_memory_bytes=7, memory_samples=3)

        contained.accepts_cancel = True
        result = world.runner(contained=contained).run_mode(q.BY_ID["PROC-03"], "contained")
        self.assertEqual(result["independent"]["memoryWatchdog"], {"peakBytes": 7, "samples": 3})
        control = world.runner().run_mode(q.BY_ID["PROC-03"], "uncontained-control")
        self.assertNotIn("memoryWatchdog", control["independent"])

    def test_the_contained_executor_passes_the_watchdog_measurements_through(self):
        backend = SimpleNamespace(run_probe=lambda *a, **k: mac.ProbeResult(
            b"", 0, False, False, True, peak_memory_bytes=11, memory_samples=2))
        result = q.ContainedExecutor(backend, lambda: Path(tempfile.gettempdir()))(
            b"x", Path("."), 5, SimpleNamespace())
        self.assertEqual((result.peak_memory_bytes, result.memory_samples), (11, 2))

    def test_the_catalog_in_the_bundle_states_the_proc_esc_1_residual(self):
        entries = {e["id"]: e for e in q.catalog_document()["probes"]}
        self.assertIn("PROC-ESC-1", entries["PROC-04"]["residual"])
        self.assertIn("scrubs its environment", entries["PROC-04"]["residual"])
        self.assertEqual(entries["FS-01"]["residual"], "")

    # token in the scan list ------------------------------------------------------------------------------

    def test_a_token_with_slash_or_tilde_is_still_a_scan_literal(self):
        config = Path(tempfile.mkdtemp(prefix="braid-t007-tok-"))
        self.addCleanup(shutil.rmtree, config, ignore_errors=True)
        token = "sk-ant-oat01-ab/cd~ef" + "Gh4" * 8
        (config / mac.TOKEN_FILE).write_text(token)
        self.assertEqual(q.credential_values(config), [token])

    def test_the_token_file_is_a_secret_literal_that_can_never_reach_a_bundle(self):
        world = World(self)
        config = world.tmp / "config"
        config.mkdir()
        token = "sk-ant-oat01-" + "Ab1Cd2Ef3Gh4" * 5
        (config / mac.TOKEN_FILE).write_text(token + "\n")
        os.chmod(config / mac.TOKEN_FILE, 0o640)  # the scan reads it whatever its mode
        self.assertEqual(q.credential_values(config), [token])
        inventory = q.credential_inventory(config)
        self.assertEqual(inventory[0][1], {"file": mac.TOKEN_FILE, "path": "$"})
        with self.assertRaises(q.ProbeError) as raised:
            world.runner(read_credentials=lambda: q.credential_values(config)).run(
                world.tmp / "b", environment=environment(backend=token))
        self.assertEqual(raised.exception.reason, "secret-in-artifact")
        self.assertNotIn(token, str(raised.exception))
        self.assertNotIn(token, json.dumps(raised.exception.detail))

    # sessions --------------------------------------------------------------------------------------------

    def test_session_exit_reasons_come_from_the_exit_code_the_init_event_and_the_token_mark(self):
        init = OAUTH_STREAM
        cases = (
            (q.SessionResult(init, 0), "ok"),
            (q.SessionResult(b"", 0), "no-init"),
            (q.SessionResult(init, 1), "cli-exit-nonzero"),
            (q.SessionResult(b"", 1, auth_token="absent"), "auth-missing"),
            (q.SessionResult(b"", 1, auth_token="present"), "exit-before-init"),
            (q.SessionResult(b"", 1), "exit-before-init"),
            (q.SessionResult(b"", None, timed_out=True), "timed-out"),
            (q.SessionResult(b"", None, cancelled=True), "cancelled"),
            (q.SessionResult(refused="quota-stop"), "refused"),
        )
        for session, reason in cases:
            with self.subTest(reason=reason):
                self.assertEqual(q.session_exit_reason(session), reason)
                self.assertIn(reason, q.EXIT_REASONS)
        # never from text: the same exit with any output text gives the same reason
        self.assertEqual(q.session_exit_reason(q.SessionResult(b"Not logged in. Please run /login", 1,
                                                               auth_token="present")), "exit-before-init")

    def test_session_rows_carry_the_exit_reason_and_the_token_mark(self):
        world = World(self)
        runner = world.runner(sessions=lambda pid: q.SessionResult(
            b"", 1, auth_token="absent", quota={"pre": reading(60, 10), "post": reading(10, 10)}))
        result = runner.run_mode(q.BY_ID["CRED-05"], "contained")
        self.assertEqual((result["exitReason"], result["authToken"], result["exitCode"]), ("auth-missing", "absent", 1))
        ok = world.runner().run_mode(q.BY_ID["HOST-01"], "contained")
        self.assertEqual((ok["exitReason"], ok["authToken"]), ("ok", None))

    def test_the_driver_reads_the_token_mark_from_the_backends_launch_record(self):
        class Backend:
            run_evidence = [{"entry": "launch", "authToken": "present"}, {"entry": "fixture"},
                            {"entry": "launch", "authToken": "absent"}]

        for error, expect in ((None, "absent"), ("quota-stop", "absent")):
            transport = FakeNativeTransport(error=error)
            transport.backend = Backend()
            result = q.native_session_driver(lambda t=transport: t)("HOST-01")
            self.assertEqual(result.auth_token, expect)
        bare = q.native_session_driver(FakeNativeTransport)("HOST-01")
        self.assertIsNone(bare.auth_token)  # a transport without a backend record says nothing


class BundleHardeningTests(unittest.TestCase):
    """RV-24: allow-listed environment document, token-shaped strings and credential values."""

    def test_environment_is_an_allow_list_of_facts_and_hashes(self):
        world = World(self)
        good = environment(osBuild="27A5001", claudeVersion="2.1.292", arch="arm64", profileSha256="a" * 64)
        world.runner().run(world.tmp / "ok", environment=good)
        for bad in (environment(account="dedicated"), environment(backend="/Users/me/x"),
                    environment(backend="x" * 200), environment(osBuild=["a"]), environment(osBuild=-1)):
            with self.assertRaises(q.ProbeError) as raised:
                world.runner().run(world.tmp / "no", environment=bad)
            self.assertEqual(raised.exception.reason, "invalid-environment")
            self.assertFalse((world.tmp / "no").exists())

    def test_token_shapes_and_long_opaque_runs_are_refused_but_digests_pass(self):
        for text in ("key sk-ant-api03-abcdef", "jwt eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.sig",
                     "-----BEGIN PRIVATE KEY-----", "ghp_" + "a" * 30, "AKIA" + "A" * 16,
                     "blob " + "QUJD" * 12, "hex " + "ab" * 30):
            with self.assertRaises(q.ProbeError, msg=text) as raised:
                q.scan_for_secrets({"f": text}, [])
            self.assertEqual(raised.exception.reason, "secret-in-artifact")
        q.scan_for_secrets({"f": json.dumps({"sha": "0123456789abcdef" * 4, "id": "FS-01", "p": "outside-abc/x.txt"})}, [])

    def test_credential_values_come_from_the_config_dir_and_stay_out_of_the_bundle(self):
        world = World(self)
        config = world.tmp / "config"
        config.mkdir()
        (config / ".credentials.json").write_text(json.dumps(
            {"claudeAiOauth": {"accessToken": "tok-1234567890abcdef", "scopes": ["a", "user:inference"],
                               "n": 5}}))
        (config / ".claude.json").write_text("not json")
        values = q.credential_values(config)
        self.assertEqual(values, ["tok-1234567890abcdef"])
        self.assertEqual(q.credential_values(world.tmp / "missing"), [])
        with self.assertRaises(q.ProbeError) as raised:
            world.runner(read_credentials=lambda: values).run(
                world.tmp / "b", environment=environment(backend="tok-1234567890abcdef"))
        self.assertEqual(raised.exception.reason, "secret-in-artifact")
        self.assertNotIn("tok-1234567890abcdef", str(raised.exception))

    def test_an_unreadable_credential_scan_aborts_instead_of_skipping(self):
        world = World(self)

        def broken():
            raise OSError("denied")

        with self.assertRaises(q.ProbeError) as raised:
            world.runner(read_credentials=broken).run(world.tmp / "b", environment=environment())
        self.assertEqual(raised.exception.reason, "credential-scan-unavailable")
        self.assertFalse((world.tmp / "b" / "summary.json").exists())


class ProxyParsingTests(unittest.TestCase):
    """RV-10: parsing attacks against a live EgressProxy whose upstream is a recorder."""

    def test_enforcing_proxy_refuses_every_case_and_reaches_the_recorder_only_when_legitimate(self):
        self.assertEqual(q.run_proxy_parsing(control=False, relay=None, timeout=2),
                         {name: "denied" for name in q.PROXY_ATTEMPTS})

    def test_permissive_relay_lets_every_case_through_which_is_the_control(self):
        tmp = Path(tempfile.mkdtemp(prefix="bt-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        arena = q.Arena(tmp, public=q.DEFAULT_PUBLIC, proxy=None, proxy_enforcing=False, spawn_sibling=False)
        self.addCleanup(arena.close)
        self.assertEqual(q.run_proxy_parsing(control=True, relay=arena.relay, timeout=2),
                         {name: "allowed" for name in q.PROXY_ATTEMPTS})

    def test_a_proxy_that_never_reaches_the_recorder_proves_nothing(self):
        class DeafProxy:
            port = 1

            def __init__(self, *a, **k):
                pass

            def start(self):
                pass

            def close(self):
                pass

        self.assertEqual(q.run_proxy_parsing(control=False, relay=None, proxy_factory=DeafProxy, timeout=0.2),
                         {name: "inconclusive" for name in q.PROXY_ATTEMPTS})

    def test_unstartable_proxy_and_missing_relay_are_inconclusive(self):
        def broken(*a, **k):
            raise lab.LabError("proxy-unavailable")

        unknown = {name: "inconclusive" for name in q.PROXY_ATTEMPTS}
        self.assertEqual(q.run_proxy_parsing(control=False, relay=None, proxy_factory=broken), unknown)
        self.assertEqual(q.run_proxy_parsing(control=True, relay=None), unknown)

    def test_classification_needs_an_explicit_403_or_a_close(self):
        c = q.classify_proxy_case
        self.assertEqual(c("refuse", b"HTTP/1.1 403 Forbidden", True, 0), "denied")
        self.assertEqual(c("refuse", b"", True, 0), "denied")
        self.assertEqual(c("refuse", None, False, 0), "inconclusive")  # a timeout
        self.assertEqual(c("refuse", b"HTTP/1.1 400 Bad", True, 0), "inconclusive")
        self.assertEqual(c("refuse", b"HTTP/1.1 403", True, 1), "allowed")  # the upstream was contacted
        self.assertEqual(c("refuse", b"HTTP/1.1 200 ok", False, 0), "allowed")
        self.assertEqual(c("sni", b"HTTP/1.1 200 ok", True, 0), "denied")
        self.assertEqual(c("sni", b"HTTP/1.1 200 ok", True, 1), "allowed")
        self.assertEqual(c("sni", b"HTTP/1.1 403", True, 0), "inconclusive")
        self.assertEqual(c("sni", b"HTTP/1.1 200 ok", False, None), "allowed")  # control

    def test_client_hello_names_the_requested_server(self):
        self.assertEqual(mac.client_hello_sni(q.client_hello("Example.COM")), "example.com")


class DiscoveryHelperTests(unittest.TestCase):
    def test_launchd_listing_yields_service_names_not_files(self):
        text = ("services = {\n   0  - com.apple.mdworker.shared\n  100 0 application.com.vendor.app.123\n}\n"
                "endpoints = {\n\t\"com.apple.metadata.mds\" = {\n}\n"
                "path = /System/Library/LaunchDaemons/com.apple.foo.plist\nname = a.b\n"
                "bundle = com.apple.Safari.app\n")
        names = q.parse_launchd_names(text)
        self.assertEqual(names, ["application.com.vendor.app.123", "com.apple.mdworker.shared",
                                 "com.apple.metadata.mds"])

    def test_enumeration_reads_both_domains_and_survives_a_failing_one(self):
        calls = []

        def run(argv, **kw):
            calls.append(argv)
            if argv[-1] == "system":
                raise OSError("launchctl")
            return SimpleNamespace(stdout="com.apple.user.service.a\n")

        self.assertEqual(q.enumerate_mach_services(501, run=run), ["com.apple.user.service.a"])
        self.assertEqual([c[-1] for c in calls], ["system", "user/501"])
        self.assertEqual(q.enumerate_mach_services(501, run=lambda *a, **k: (_ for _ in ()).throw(OSError())), [])

    def test_process_table_parses_ps_and_skips_ps_and_this_process(self):
        listing = (f"  11 Sat Nov  1 12:00:00 2026 /usr/bin/python3\n  12 Sat Nov  1 12:00:01 2026 /bin/ps\n"
                   f"  {os.getpid()} Sat Nov  1 12:00:02 2026 /usr/bin/python3\nbroken line\n")
        with mock.patch.object(q.subprocess, "run", return_value=SimpleNamespace(stdout=listing, stderr="", returncode=0)) as run:
            self.assertEqual(q.own_process_table(), {(11, "Sat Nov 1 12:00:00 2026")})
        self.assertIn("-U", run.call_args.args[0])

    def test_lan_and_ip_discovery_degrade_to_none(self):
        with mock.patch.object(q.socket, "socket", side_effect=OSError("no route")):
            self.assertIsNone(q.discover_lan_address())
        with mock.patch.object(q.socket, "getaddrinfo", side_effect=OSError("offline")):
            self.assertIsNone(q.resolve_ipv4("example.invalid"))
        with mock.patch.object(q.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("192.0.2.5", 443))]):
            self.assertEqual(q.resolve_ipv4("example.invalid"), "192.0.2.5")


class ReviewArenaTests(unittest.TestCase):
    """Adjacent decoys, own-tree files and the LAN listener (RV-09, RV-10)."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="bt-"))
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)

    def arena(self, **kw):
        arena = q.Arena(self.tmp, public=q.DEFAULT_PUBLIC, proxy="127.0.0.1:9", proxy_enforcing=True,
                        spawn_sibling=False, **kw)
        self.addCleanup(arena.close)
        return arena

    def real_layout(self):
        base = self.tmp / "real"
        layout = {"candidate": str(base / "run" / "cand"), "run_root": str(base / "run"),
                  "config_dir": str(base / "home" / "cfg"), "interpreter_root": str(base / "interp")}
        for path in (base / "run" / "cand", base / "home", base / "interp"):
            path.mkdir(parents=True)
        return layout, base

    def test_control_arena_builds_the_same_shapes_inside_itself(self):
        arena = self.arena()
        adjacent = arena.document["adjacent"]
        self.assertEqual(set(adjacent), {"candidate_prefix", "run_dir", "run_root", "config_parent",
                                         "config_sibling", "interpreter_root"})
        for path in adjacent.values():
            self.assertTrue(path.startswith(str(arena.root)), path)

    def test_real_layout_gets_decoys_next_to_the_allowed_paths_and_leaves_nothing_behind(self):
        layout, base = self.real_layout()
        before = sorted(str(p) for p in base.rglob("*"))
        arena = self.arena(layout=layout, real_home=str(base / "home"))
        adjacent = arena.document["adjacent"]
        self.assertTrue(adjacent["candidate_prefix"].startswith(layout["candidate"] + "-braid-adj-"))
        self.assertEqual(os.path.dirname(adjacent["run_dir"]), str(base / "run"))
        self.assertEqual(os.path.dirname(adjacent["config_parent"]), str(base / "home"))
        self.assertTrue(arena.document["own_file"].startswith(str(base / "home") + "/.braid-own-"))
        self.assertTrue(arena.document["real_launch_agents"].endswith("/home/Library/LaunchAgents"))
        before_run = arena.snapshot()
        Path(adjacent["run_root"]).write_text("escape")  # an escape the child could have made
        self.assertIn(adjacent["run_root"], arena.changed(before_run))
        arena.close()
        self.assertEqual(sorted(str(p) for p in base.rglob("*")), before)

    def test_incomplete_or_relative_layout_plants_nothing(self):
        for layout in ({}, {"candidate": "relative"}, {"candidate": "/nonexistent-dir/x", "run_root": "/",
                                                        "config_dir": "/", "interpreter_root": "/"}):
            arena = self.arena(layout=layout)
            self.assertEqual(arena.document["adjacent"], {})

    def test_own_tree_file_is_watched_for_modification(self):
        arena = self.arena()
        before = arena.snapshot()
        Path(arena.document["own_file"]).write_text("changed through a hard link")
        self.assertTrue(arena.changed(before))

    def test_aliases_and_extra_paths_are_distinct_and_cleaned(self):
        arena = self.arena()
        document = arena.document
        self.assertNotEqual(document["tmp_alias"], document["tmp_target"])
        self.assertIn(document["tmp_alias"], arena.extra_outside)
        self.assertEqual(document["nonce"], arena.nonce)

    def test_lan_listener_counts_connections_and_is_absent_without_an_address(self):
        arena = self.arena(lan_ip="127.0.0.1")
        document = arena.document
        self.assertEqual((document["lan_ip"], document["tcp_lan_port"] > 0), ("127.0.0.1", True))
        socket.create_connection(("127.0.0.1", document["tcp_lan_port"]), timeout=2).close()
        for _ in range(100):
            if arena.hit_counts().get("tcp-lan"):
                break
            threading.Event().wait(0.05)
        self.assertEqual(arena.hit_counts().get("tcp-lan"), 1)
        none = self.arena()
        self.assertEqual((none.document["lan_ip"], none.document["tcp_lan_port"]), ("", 0))

    def test_resolved_literals_and_mach_names_reach_the_document(self):
        arena = self.arena(allowed_ip="192.0.2.7", mach_names=("a.b.c",))
        self.assertEqual((arena.document["allowed_ip"], arena.document["mach_names"]), ("192.0.2.7", ["a.b.c"]))
        self.assertEqual(self.arena().document["allowed_ip"], "")

    def test_permissive_relay_passes_any_request_line(self):
        arena = q.Arena(self.tmp, public=q.DEFAULT_PUBLIC, proxy=None, proxy_enforcing=False, spawn_sibling=False)
        self.addCleanup(arena.close)
        host, _, port = arena.relay.rpartition(":")
        with socket.create_connection((host, int(port)), timeout=2) as sock:
            sock.sendall(b"GET http://example.com/ HTTP/1.1\r\n\r\n")
            self.assertTrue(sock.recv(64).startswith(b"HTTP/1.1 200"))


class ReviewF4Tests(unittest.TestCase):
    """RV-04 and RV-14 on the NC-11 subset, over the doubles of F4RunnerTests."""

    make = F4RunnerTests.make

    def test_both_profiles_must_agree(self):
        runner, backend, calls, world = self.make(lambda p: "allowed" if p.functional else "denied")
        original = backend.run_launch_probe

        def disagreeing(source, workdir, limits):
            probe = world.probe_of(source)
            return lab.ChildResult(lines({n: "denied" if probe.functional else "allowed" for n in probe.counted}),
                                   0, False, False, True)

        backend.run_launch_probe = disagreeing
        self.assertEqual(runner("NET-06", backend), "error")  # functional control broke under launch-probe
        self.assertEqual(runner("FS-01", backend), "allowed")  # an escape in either profile refuses
        backend.run_launch_probe = original

    def test_backend_without_the_launch_hook_cannot_pass_the_check(self):
        runner, backend, *_ = self.make(lambda p: "allowed" if p.functional else "denied")
        del type(backend).run_launch_probe
        self.assertEqual(runner("FS-01", backend), "error")

    def test_launch_profile_can_be_switched_off_explicitly(self):
        runner, backend, calls, world = self.make(lambda p: "denied")
        fixture_only = q.make_f4_probe_runner(arena_parent=world.tmp, workdir_factory=lambda: world.tmp,
                                              arena_factory=world.arena, launch_profile=False)
        del type(backend).run_launch_probe
        self.assertEqual(fixture_only("FS-01", backend), "denied")

    def test_a_policy_that_does_not_bind_this_catalog_is_an_error(self):
        runner, backend, calls, _ = self.make(lambda p: "denied")
        backend.policy.probe_catalog_sha256 = "0" * 64
        self.assertEqual(runner("FS-01", backend), "error")
        self.assertEqual(calls, [])
        backend.policy = SimpleNamespace(proxy_port=1)
        self.assertEqual(runner("FS-01", backend), "error")

    def test_layout_is_taken_from_the_policy_and_the_check_is_offline(self):
        runner, backend, calls, world = self.make(lambda p: "denied")
        seen = []
        factory = world.arena

        def spy(parent, **kwargs):
            seen.append(kwargs["layout"])
            return factory(parent, **kwargs)

        runner = q.make_f4_probe_runner(arena_parent=world.tmp, workdir_factory=lambda: world.tmp,
                                        arena_factory=spy)
        self.assertEqual(runner("FS-01", backend), "denied")
        self.assertEqual(seen[0]["config_dir"], "/c/cfg")
        self.assertEqual(seen[0]["candidate"], str(world.tmp))


class BackendIntegrationTests(unittest.TestCase):
    """The T005 backend delta consumed for real: its policy, result types and public hooks, with the
    child execution replaced by doubles (no helper, sandbox or claude runs)."""

    def machine(self):
        from tests.test_harness_containment_macos import Machine, make_backend
        machine = Machine(self)
        backend = make_backend(machine)
        self.addCleanup(backend.close)
        return machine, backend

    def test_the_real_policy_renders_a_launch_probe_profile_the_runner_accepts(self):
        policy = self.machine()[0].policy
        launch, probe = policy.render("launch"), policy.render(q.LAUNCH_PROBE_ENTRY)
        delta = q.launch_probe_delta_is_interpreter_only
        self.assertTrue(delta(launch, probe, policy.interpreter, policy.interpreter_root))
        self.assertFalse(delta(launch, probe, policy.interpreter))  # the prefix read needs the root to be named
        self.assertFalse(delta(launch, policy.render("fixture"), policy.interpreter, policy.interpreter_root))
        widened = probe.decode().replace(f'(subpath "{policy.interpreter_root}")', '(subpath "/usr")')
        self.assertFalse(delta(launch, widened.encode(), policy.interpreter, policy.interpreter_root))
        self.assertEqual(q.LAUNCH_PROBE_ENTRY, mac.LAUNCH_PROBE)
        self.assertTrue(q.policy_binds_catalog(policy))

    def test_delta_checker_allows_only_interpreter_items_per_rule(self):
        delta = q.launch_probe_delta_is_interpreter_only
        launch = (b'(allow process-exec (literal "/c/claude"))\n'
                  b'(allow file-read* file-map-executable (literal "/") (subpath "/s") (literal "/c/claude"))\n'
                  b'(allow file-read-metadata (literal "/c") (literal "/"))\n')
        probe = (b'(allow process-exec (literal "/c/claude") (literal "/i/bin/python"))\n'
                 b'(allow file-read* file-map-executable (literal "/") (subpath "/s") (subpath "/i") '
                 b'(literal "/c/claude") (literal "/i/bin/python"))\n'
                 b'(allow file-read-metadata (literal "/c") (literal "/") (literal "/i") (literal "/i/bin"))\n')
        self.assertTrue(delta(launch, probe, "/i/bin/python", "/i"))
        # a metadata literal that is not an ancestor of the interpreter, a removed item, a doubled item
        for bad in (probe.replace(b'(literal "/i/bin"))', b'(literal "/i/bin") (literal "/etc"))'),
                    probe.replace(b'(literal "/c") (literal "/")', b'(literal "/")'),
                    probe.replace(b'(literal "/i/bin/python"))\n(allow file-read*',
                                  b'(literal "/i/bin/python") (literal "/i/bin/python"))\n(allow file-read*'),
                    probe.replace(b'(allow process-exec (literal "/c/claude") (literal "/i/bin/python"))',
                                  b'(allow process-exec (literal "/c/claude") (subpath "/i"))')):
            self.assertFalse(delta(launch, bad, "/i/bin/python", "/i"))

    def test_contained_executor_carries_backend_accounting_limit_and_cancel(self):
        calls = []

        class Backend:
            def run_probe(self, source, workdir, limits, **kwargs):
                calls.append(kwargs)
                return mac.ProbeResult(b"out", None, False, False, False, cancelled=True, escaped_processes=2,
                                       surviving_processes=1, limit_exceeded="memory")

        executor = q.ContainedExecutor(Backend(), lambda: Path("/w"))
        plain = executor(b"", Path("/w"), 1, None)
        self.assertEqual((plain.limit_exceeded, plain.escaped_processes, plain.surviving_processes,
                          plain.cancelled, plain.settled), ("memory", 2, 1, True, False))
        event = threading.Event()
        executor(b"", Path("/w"), 1, None, cancel=event)
        self.assertEqual(calls, [{}, {"cancel": event}])
        self.assertTrue(executor.accepts_cancel)

    def test_a_backend_that_reports_nothing_leaves_accounting_unavailable(self):
        backend = SimpleNamespace(run_probe=lambda *a, **k: lab.ChildResult(b"", 0, False, False, True))
        result = q.ContainedExecutor(backend, lambda: Path("/w"))(b"", Path("/w"), 1, None)
        self.assertEqual((result.limit_exceeded, result.escaped_processes, result.surviving_processes),
                         ("unavailable", None, None))

    def test_memory_denial_needs_the_backend_stop_reason(self):
        """RV-13 end to end: a kill is a memory denial only when ProbeResult.limit_exceeded says memory."""
        world = World(self)
        world.limit_exceeded["PROC-03"] = None  # killed, but not by the memory watchdog
        _, summary = self.run_world(world)
        self.assertEqual(summary["probes"]["PROC-03"]["status"], "inconclusive")
        world = World(self)
        world.limit_exceeded["PROC-03"] = "memory"
        _, summary = self.run_world(world)
        self.assertEqual(summary["probes"]["PROC-03"]["status"], "denied")

    def run_world(self, world):
        out = world.tmp / "bundle"
        return out, world.runner().run(out, environment=environment())

    def test_f4_runner_works_against_the_real_backend_and_policy(self):
        """The check no longer errors merely for a missing hook: every NC-11 probe runs on both profiles."""
        machine, backend = self.machine()
        world = World(self)
        seen = []

        def contained(entry):
            def run(source, workdir, limits, **kwargs):
                probe = world.probe_of(source)
                seen.append((entry, probe.id))
                outcome = "allowed" if probe.functional else "denied"
                return mac.ProbeResult(lines({n: outcome for n in probe.counted}), 0, False, False, True)
            return run

        runner = q.make_f4_probe_runner(arena_parent=world.tmp, workdir_factory=lambda: world.tmp,
                                        arena_factory=world.arena)
        with mock.patch.object(backend, "run_probe", contained("fixture")), \
                mock.patch.object(backend, "run_launch_probe", contained(q.LAUNCH_PROBE_ENTRY)):
            observed = {probe: runner(probe, backend) for probe, _ in mac.F4_PROBES}
        self.assertEqual(observed, dict(mac.F4_PROBES))
        self.assertEqual(len(seen), 2 * len(mac.F4_PROBES))

    def test_factory_wires_the_orchestrator_inputs_and_defaults_fail_closed(self):
        machine, backend = self.machine()
        world = World(self)
        credentials, names = lambda: ["sk-dummy"], lambda: ["com.apple.fake.service"]
        runner = q.make_qualification_runner(
            backend, arena_parent=world.tmp, workdir_factory=lambda: world.tmp,
            transport_factory=FakeNativeTransport, read_quota=lambda: reading(10, 10),
            read_credentials=credentials, real_home="/home/dedicated", lan_ip="192.0.2.7",
            allowed_ip="192.0.2.9", mach_names=names, arena_factory=world.arena)
        self.assertEqual((runner.real_home, runner.lan_ip, runner.allowed_ip, runner.mach_names,
                          runner.read_credentials), ("/home/dedicated", "192.0.2.7", "192.0.2.9", names,
                                                     credentials))
        self.assertEqual(runner.proxy_address, f"127.0.0.1:{machine.policy.proxy_port}")
        self.assertIs(runner.control, q.uncontained_executor)
        self.assertEqual((runner.contained.profile, runner.launch_contained.profile),
                         ("fixture", q.LAUNCH_PROBE_ENTRY))
        self.assertEqual(runner.layout(Path("/w"))["config_dir"], machine.policy.config_dir)
        self.assertEqual(runner.sessions("CRED-05").refused, None)  # the driver reaches the transport
        bare = q.make_qualification_runner(backend, arena_parent=world.tmp, workdir_factory=lambda: world.tmp,
                                           lan_ip="")
        self.assertIsNone(bare.sessions)
        self.assertEqual(bare.real_home, q.home_directory())  # DRV-02: the runner is the dedicated account
        self.assertEqual(bare.read_credentials(), [])  # DRV-03: wired to config_dir, here empty
        self.assertIsNone(bare.lan_ip)  # "" disables the LAN attempts
        self.assertEqual(bare.run_mode(q.BY_ID["HOST-01"], "contained")["refused"], "session-driver-missing")

    def test_factory_session_egress_is_the_run_delta_not_the_backend_total(self):
        machine, backend = self.machine()
        world = World(self)
        # the backend proxy already carries the pre-session NET-06 tunnels; the CLI sent nothing
        pre_session = {"connections": 4, "allowed": 4, "allowed:api.anthropic.com:443": 4}
        with mock.patch.object(backend._proxy, "counters", lambda: pre_session):
            runner = q.make_qualification_runner(
                backend, arena_parent=world.tmp, workdir_factory=lambda: world.tmp,
                transport_factory=lambda: FakeNativeTransport(egress={}), lan_ip="", arena_factory=world.arena)
            result = runner.sessions("NET-05-CLI")
        self.assertEqual(q.classify_session("NET-05-CLI", result), "inconclusive")

    def test_factory_needs_a_real_home(self):
        machine, backend = self.machine()
        world = World(self)
        kwargs = dict(arena_parent=world.tmp, workdir_factory=lambda: world.tmp, lan_ip="")
        with mock.patch.object(q, "home_directory", lambda: None):
            with self.assertRaises(q.ProbeError) as raised:
                q.make_qualification_runner(backend, **kwargs)
        self.assertEqual(raised.exception.reason, "real-home-unavailable")
        for bad in ("", "relative/home"):
            with self.assertRaises(q.ProbeError):
                q.make_qualification_runner(backend, real_home=bad, **kwargs)
        self.assertEqual(q.make_qualification_runner(backend, real_home="/home/x", **kwargs).real_home, "/home/x")

    def test_factory_scans_the_config_dir_credentials_by_default(self):
        machine, backend = self.machine()
        world = World(self)
        Path(machine.policy.config_dir, ".credentials.json").write_text('{"token": "dummy-secret-value-123456"}')
        runner = q.make_qualification_runner(backend, arena_parent=world.tmp, workdir_factory=lambda: world.tmp,
                                             lan_ip="")
        self.assertEqual(runner.read_credentials(), ["dummy-secret-value-123456"])

    def test_factory_lists_the_config_dir_around_each_session_by_default(self):
        machine, backend = self.machine()
        world = World(self)
        config = Path(machine.policy.config_dir)

        class Writing(FakeNativeTransport):
            def run(self, *args):
                (config / "session-state.json").write_text("{}")
                return super().run(*args)

        runner = q.make_qualification_runner(
            backend, arena_parent=world.tmp, workdir_factory=lambda: world.tmp, transport_factory=Writing,
            lan_ip="", arena_factory=world.arena)
        result = runner.sessions("HOST-01")
        self.assertEqual((result.config["added"], result.config["removed"], result.config["modified"]),
                         (["session-state.json"], [], []))

    def test_factory_refuses_a_policy_that_does_not_bind_this_catalog(self):
        world = World(self)
        for backend in (SimpleNamespace(policy=SimpleNamespace(probe_catalog_sha256="0" * 64, proxy_port=1)),
                        SimpleNamespace()):
            with self.assertRaises(q.ProbeError) as raised:
                q.make_qualification_runner(backend, arena_parent=world.tmp, workdir_factory=lambda: world.tmp)
            self.assertEqual(raised.exception.reason, "catalog-not-bound")


class PreT009FixTests(unittest.TestCase):
    """The pre-T009 fixes of the delta security review: DRV-02, DRV-14, DRV-16."""

    def init_stream(self, source):
        return canonical({"type": "system", "subtype": "init", "apiKeySource": source}) + b"\n"

    def test_the_real_api_key_source_label_stays_in_the_evidence(self):
        # DRV-14: T009 exists to observe the real values; a label is not a secret
        for reported, recorded in (("oauth", "oauth"), ("none", "none"), ("ANTHROPIC_API_KEY", "ANTHROPIC_API_KEY"),
                                   ("claude.ai-subscription_2", "claude.ai-subscription_2"),
                                   ("has space", "other"), ("a/b", "other"), ("x" * 33, "other"), ("", None)):
            with self.subTest(reported=reported):
                world = World(self)
                world.sessions["CRED-05"] = self.init_stream(reported)
                row = world.runner().run_mode(q.BY_ID["CRED-05"], "contained")
                self.assertEqual(row["independent"]["apiKeySource"], recorded)

    def test_a_label_in_the_bundle_cannot_trip_the_secret_scan(self):
        world = World(self)
        world.sessions["CRED-05"] = self.init_stream("x" * 33)
        world.runner().run(world.tmp / "b", environment=environment())  # does not raise
        self.assertTrue((world.tmp / "b" / "summary.json").exists())

    def test_the_session_row_carries_the_config_dir_comparison(self):
        world = World(self)
        comparison = {"before": 1, "after": 2, "added": ["projects"], "removed": [], "modified": [],
                      "digests": {"a.json": "2" * 64, "projects": "dir"}, "truncated": False}

        def driver(probe_id):
            return q.SessionResult(OAUTH_STREAM, 0, config=comparison,
                                   quota={"pre": reading(60, 10), "post": reading(10, 11)})
        row = world.runner(sessions=driver).run_mode(q.BY_ID["HOST-01"], "contained")
        self.assertEqual(row["independent"]["configDir"], comparison)
        world.runner(sessions=driver).run(world.tmp / "b", environment=environment())  # passes the scan
        none = world.runner(sessions=lambda pid: q.SessionResult(OAUTH_STREAM, 0)).run_mode(
            q.BY_ID["HOST-01"], "contained")
        self.assertIsNone(none["independent"]["configDir"])

    def test_config_dir_listing_has_names_and_digests_only(self):
        tmp = Path(tempfile.mkdtemp(prefix="braid-cfg-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / "projects").mkdir()
        (tmp / "projects" / "s.jsonl").write_text("secret-contents-must-not-appear")
        (tmp / ".credentials.json").write_text("tok")
        (tmp / "link").symlink_to("/etc/hosts")
        (tmp / ("n" * 60 + ".json")).write_text("x")
        listing = q.config_dir_listing(tmp)
        entries = listing["entries"]
        self.assertFalse(listing["truncated"])
        self.assertEqual(entries[".credentials.json"], hashlib.sha256(b"tok").hexdigest())
        self.assertEqual(entries["projects"], "dir")
        self.assertTrue(entries["link"].startswith("link:"))
        self.assertIn("#" + hashlib.sha256(("n" * 60 + ".json").encode()).hexdigest(), entries)
        self.assertNotIn("secret-contents-must-not-appear", json.dumps(listing))
        self.assertNotIn(str(tmp), json.dumps(listing))
        q.scan_for_secrets({"listing": json.dumps(listing)}, [])  # the long name was replaced by a digest

    def test_config_dir_listing_is_bounded_and_unavailable_when_unreadable(self):
        tmp = Path(tempfile.mkdtemp(prefix="braid-cfg-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        for index in range(5):
            (tmp / f"f{index}").write_text("x")
        limited = q.config_dir_listing(tmp, limit=3)
        self.assertEqual((len(limited["entries"]), limited["truncated"]), (3, True))
        self.assertIsNone(q.config_dir_listing(tmp / "missing"))
        self.assertIsNone(q.config_dir_changes(None, limited))
        self.assertIsNone(q.config_dir_changes({"entries": []}, limited))

    def test_config_dir_changes_tells_added_removed_and_modified_apart(self):
        before = {"entries": {"keep": "1" * 64, "gone": "2" * 64, "edit": "3" * 64}, "truncated": False}
        after = {"entries": {"keep": "1" * 64, "new": "4" * 64, "edit": "5" * 64}, "truncated": True}
        changes = q.config_dir_changes(before, after)
        self.assertEqual((changes["added"], changes["removed"], changes["modified"], changes["truncated"]),
                         ([], [], [], True))  # a cut listing gives counts only
        after["truncated"] = False
        changes = q.config_dir_changes(before, after)
        self.assertEqual((changes["added"], changes["removed"], changes["modified"], changes["digests"]),
                         (["new"], ["gone"], ["edit"], {"edit": "5" * 64, "new": "4" * 64}))

    def test_special_files_and_links_in_config_dir_never_block_or_leak(self):
        tmp = Path(tempfile.mkdtemp(prefix="braid-cfg-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        os.mkfifo(tmp / "pipe")
        (tmp / "unreadable").write_text("x")
        os.chmod(tmp / "unreadable", 0)
        entries = q.config_dir_listing(tmp)["entries"]
        self.assertEqual(entries["pipe"], "special")
        if os.geteuid() != 0:
            self.assertEqual(entries["unreadable"], "unreadable")

    def test_a_secret_shaped_key_source_is_recorded_as_other(self):
        self.assertEqual(q._key_source_label("sk-ant-api03-abcdef"), "other")

    def test_credential_scan_values_skip_paths_urls_and_host_names(self):
        tmp = Path(tempfile.mkdtemp(prefix="braid-cfg-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / ".claude.json").write_text(json.dumps({
            "path": "/Users/dedicated/project-dir", "url": "https://api.anthropic.com/v1",
            "host": "api.anthropic.com", "mail": "someone@example.com", "text": "two words here ok",
            "token": "tok-1234567890abcdef"}))
        self.assertEqual(q.credential_values(tmp), ["tok-1234567890abcdef"])

    def test_real_path_attempts_cannot_pass_without_a_real_home(self):
        # DRV-02: inside the arena the contained attempt is denied only because the arena is outside the write set
        for real_home, status in (("/home/world", "denied"), (None, "inconclusive")):
            with self.subTest(real_home=real_home):
                world = World(self)
                for probe, attempt in (("PROC-05", "real-launch-agent"), ("FS-02", "hardlink-own-tree")):
                    row = world.runner(real_home=real_home).run_mode(q.BY_ID[probe], "contained")
                    self.assertEqual(row["attempts"][attempt], status)
                    self.assertEqual(row["independent"]["realHome"], real_home is not None)
                    other = [v for k, v in row["attempts"].items() if k != attempt]
                    self.assertIn("denied", other)  # only the real-path attempts are demoted

    def test_the_control_row_is_never_real_home_evidence(self):
        world = World(self)
        row = world.runner().run_mode(q.BY_ID["FS-02"], "uncontained-control")
        self.assertFalse(row["independent"]["realHome"])
        self.assertEqual(row["attempts"]["hardlink-own-tree"], "allowed")


# --- T009 attempt 1 (2026-11-03): refused self-check, bundle blocked by the secret scan --------------

# What Claude Code 2.1.x keeps in the dedicated account's .claude.json after a login, with invented values.
CLAUDE_JSON_2_1 = {
    "numStartups": 3, "installMethod": "native", "autoUpdates": False,
    "firstStartTime": "2026-11-03T21:11:12.345Z", "userID": "9f2c" * 16,
    "oauthAccount": {"accountUuid": "3f1c2a52-7b1e-4f6a-9d0e-5a2f8c1d9b77", "emailAddress": "lab@example.com",
                     "organizationUuid": "c1d2e3f4-0a1b-4c2d-8e3f-a4b5c6d7e8f9", "organizationName": "Lab Org",
                     "displayName": "Lab", "billingType": "stripe_subscription", "organizationRole": "admin"},
    "lastReleaseNotesSeen": "2.1.292", "lastOnboardingVersion": "2.1.292",
    "projects": {"/Users/lab/run/work-abcd1234": {
        "lastSessionId": "7b9d3c1e-0f2a-4b6c-8d4e-1a2b3c4d5e6f",
        "lastModelUsage": {"claude-haiku-4-5-20251001": {"inputTokens": 3}}}},
    "cachedGrowthBookFeatures": {"model": "claude-haiku-4-5-20251001", "env": ["ANTHROPIC_API_KEY"]},
    "cachedStatsigGates": {"gate": True}}
# Real Mach service names of macOS 27 (from the MachServices of the system LaunchDaemons on the founder's
# machine); the first two hold a 48-character underscore-joined run, the third a 40-character CamelCase one.
APPLE_LONG_NAMES = [
    "com.apple.proactive.SuggestionRequest.ps_unstructured_reminder_interaction_suggestions",
    "com.apple.proactive.SuggestionRequest.ps_unstructured_calendar_interaction_suggestions",
    "com.apple.SoftwareUpdateNotificationManagerService"]


class AttemptOneReproductionTests(unittest.TestCase):
    """The path of the founder's first real run, with doubles: session 1 refused by the backend's
    pre-session check, the other modes stopped, the bundle written."""

    def attempt_one(self, world, *, refused="self-check-failed", mach=("com.apple.fake.service",), config=None):
        credentials = []
        if config is not None:
            directory = world.tmp / "config"
            directory.mkdir(exist_ok=True)
            (directory / ".claude.json").write_text(json.dumps(config))
            credentials = q.credential_values(directory)
        out = world.tmp / "bundle"
        runner = world.runner(sessions=lambda probe_id: q.SessionResult(refused=refused),
                              read_credentials=lambda: credentials, mach_names=lambda: list(mach))
        return out, runner.run(out, environment=environment()), credentials

    def test_a_refused_first_session_still_writes_a_bundle_with_realistic_credentials(self):
        world = World(self)
        out, summary, credentials = self.attempt_one(world, config=CLAUDE_JSON_2_1)
        self.assertGreaterEqual(len(credentials), 5)
        rows = {(r["probe"], r["mode"]): r for r in map(json.loads, (out / "results.jsonl").read_text().splitlines())}
        self.assertEqual(rows[("CRED-05", "contained")]["refused"], "self-check-failed")
        self.assertEqual({rows[(p, "contained")]["refused"] for p in ("HOST-01", "NET-05-CLI")}, {"quota-stop"})
        self.assertEqual(rows[("CRED-05", "uncontained-control")]["control"], "detector-self-test")
        quota = json.loads((out / "quota.json").read_text())
        self.assertEqual(quota["sessionsStarted"], 1)
        self.assertEqual(quota["sessions"][0]["decision"]["reason"], "session-refused-self-check-failed")
        self.assertEqual(q.verify_bundle(out), summary["bundleSha256"])
        # no literal taken from the account's files is part of the bundle's closed vocabulary
        texts = "".join((out / name).read_text() for name in q.BUNDLE_FILES)
        self.assertEqual([c for c in credentials if c in texts], [])

    def test_launchd_names_with_a_long_identifier_no_longer_refuse_the_bundle(self):
        # before the fix: ProbeError secret-in-artifact (long-run) from PROC-06's machNames
        for name in APPLE_LONG_NAMES:
            self.assertTrue(q._looks_secret(name), name)
        world = World(self)
        out, _, _ = self.attempt_one(world, mach=[*APPLE_LONG_NAMES, "com.apple.ok.name"])
        rows = [json.loads(t) for t in (out / "results.jsonl").read_text().splitlines()]
        recorded = [r["machNames"] for r in rows if r["probe"] == "PROC-06"]
        self.assertEqual(len(recorded), 3)
        for names in recorded:
            self.assertEqual(sorted(names), sorted([
                *("#" + hashlib.sha256(n.encode()).hexdigest() for n in APPLE_LONG_NAMES), "com.apple.ok.name"]))
        # the helper is still handed the real names: the sweep tests what launchd really lists
        swept = [a.kwargs["mach_names"] for a in world.arenas if a.kwargs["mach_names"]]
        self.assertTrue(swept and all(set(APPLE_LONG_NAMES) <= set(names) for names in swept))
        self.assertNotIn("ps_unstructured", "".join((out / name).read_text() for name in q.BUNDLE_FILES))

    def test_a_long_reason_code_composed_by_the_runner_does_not_refuse_the_bundle(self):
        # session-refused- (16 characters) plus a 24+ character backend reason is a 40+ character run
        for reason in ("operator-account-unresolved", "dedicated-user-own-login", "process-accounting-failed",
                       "workdir-outside-run-root", "qualification-environment-mismatch"):
            with self.subTest(reason=reason):
                world = World(self)
                out, _, _ = self.attempt_one(world, refused=reason)
                quota = json.loads((out / "quota.json").read_text())
                self.assertEqual(quota["sessions"][0]["decision"]["reason"], f"session-refused-{reason}")

    def test_the_stop_reason_allowance_is_narrow(self):
        for text in ("a" * 45, "A" * 45, "ab" * 25, "x" * 20 + "-" + "y" * 20,  # not a stop reason at all
                     "operator-account-unresolved-and-more-words-here",  # hyphenated words without the prefix
                     "Session-Refused-Operator-Account-Unresolved", "session_refused_operator_account_unresolved",
                     "session-refused-operator-account-unresolved-1", "session-refused-op3rator-account-unresolved",
                     "session-refused-" + "ab" * 25, "session-refused-" + "-".join(["abcdefgh"] * 7)):  # over 64
            with self.subTest(text=text):
                with self.assertRaises(q.ProbeError):
                    q.scan_for_secrets({"f": json.dumps({"k": text})}, [])
        for code in ("qualification-environment-mismatch", "operator-account-unresolved", "post-reading-not-after-pre-reading"):
            q.scan_for_secrets({"f": json.dumps({"k": f"session-refused-{code}"})}, [])

    def test_changed_paths_the_bundle_records_are_safe_to_record(self):
        world = World(self)
        long_name = "outside-0123456789ab/" + "n" * 50
        world.changed = {"FS-01": [long_name, "outside-0123456789ab/new.txt"]}
        row = world.runner().run_mode(q.BY_ID["FS-01"], "uncontained-control")
        self.assertEqual(row["independent"]["changedOutside"],
                         ["#" + hashlib.sha256(long_name.encode()).hexdigest(),
                          "outside-0123456789ab/new.txt"])
        world.runner().run(world.tmp / "b", environment=environment())  # the bundle passes the scan

    def test_bundle_safe_name_keeps_clean_names_and_hashes_the_rest(self):
        self.assertEqual(q.bundle_safe_name("com.apple.fake.service"), "com.apple.fake.service")
        self.assertEqual(q.bundle_safe_name("com.x.sk-ant-api03-abcdef"),
                         "#" + hashlib.sha256(b"com.x.sk-ant-api03-abcdef").hexdigest())


class RedactedScanReportTests(unittest.TestCase):
    """A refused bundle says where and by which rule, never what."""

    SECRET = "QXz9_Wv7=Kp3+Lm5-Rt8"

    def refusal(self, texts, secrets=(), **kw):
        with self.assertRaises(q.ProbeError) as raised:
            q.scan_for_secrets(texts, list(secrets), **kw)
        return raised.exception

    def assertRedacted(self, error, secret=None, extra=()):
        self.assertEqual((error.reason, str(error)), ("secret-in-artifact", "secret-in-artifact"))
        rendered = json.dumps(error.detail)
        for value in (secret or self.SECRET, *extra):
            for size in (3, 4):
                for start in range(len(value) - size + 1):
                    self.assertNotIn(value[start:start + size], rendered, value[start:start + size])
            self.assertNotIn(value, repr(error))

    def test_a_listed_literal_is_reported_with_file_line_path_rule_length_and_origin(self):
        rows = [json.dumps({"probe": "FS-01", "independent": {"changedOutside": ["a", f"x/{self.SECRET}/y"]}}),
                json.dumps({"probe": "FS-02"})]
        error = self.refusal({"results.jsonl": "\n".join(rows[::-1]) + "\n", "quota.json": "{}\n"},
                             [self.SECRET], origins=["credential#0"])
        self.assertEqual(error.detail, {"total": 1, "findings": [
            {"file": "results.jsonl", "line": 2, "path": "$.independent.changedOutside[1]",
             "rule": "listed-literal", "length": len(self.SECRET), "origin": "credential#0"}]})
        self.assertRedacted(error)

    def test_each_token_shape_and_the_long_run_are_named(self):
        cases = {"anthropic-api-key": "sk-ant-api03-abcdef", "jwt": "eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.s",
                 "pem-header": "-----BEGIN PRIVATE KEY-----", "github-token": "ghp_" + "a" * 30,
                 "aws-access-key-id": "AKIA" + "A" * 16, "long-run": "QUJD" * 12}
        for rule, value in cases.items():
            with self.subTest(rule=rule):
                error = self.refusal({"environment.json": json.dumps({"backend": value}) + "\n"})
                finding = error.detail["findings"][0]
                self.assertEqual((finding["file"], finding["line"], finding["path"], finding["rule"]),
                                 ("environment.json", 1, "$.backend", rule))
                self.assertGreaterEqual(finding["length"], 10)
                self.assertNotIn(value, json.dumps(error.detail))

    def test_a_key_is_never_named_in_the_path_when_it_is_the_value_or_not_a_plain_field_name(self):
        document = {"names": {self.SECRET: 1, "/Users/lab/some dir": {"inner": "sk-ant-api03-abcdef"}, "ok_key": 2}}
        error = self.refusal({"f.json": json.dumps(document)}, [self.SECRET])
        self.assertEqual(sorted((f["path"], f["rule"]) for f in error.detail["findings"]),
                         [("$.names.<key>", "listed-literal"), ("$.names.<key>.inner", "anthropic-api-key")])
        self.assertRedacted(error, extra=["/Users/lab/some dir"])

    def test_text_that_is_not_json_is_placed_by_line_and_a_multi_line_literal_by_file(self):
        error = self.refusal({"notes.txt": f"first\nsecond {self.SECRET}\n"}, [self.SECRET])
        self.assertEqual(error.detail["findings"], [{"file": "notes.txt", "line": 2, "path": None,
                                                     "rule": "listed-literal", "length": len(self.SECRET),
                                                     "origin": "listed"}])
        spanning = "ab\ncd"
        error = self.refusal({"notes.txt": "x ab\ncd y\n"}, [spanning])
        self.assertEqual(error.detail["findings"], [{"file": "notes.txt", "line": None, "path": None,
                                                     "rule": "listed-literal", "length": 5, "origin": "listed"}])

    def test_findings_are_capped_but_counted(self):
        text = "".join(json.dumps({"n": i, "v": f"ghp_{'a' * 30}"}) + "\n" for i in range(30))
        error = self.refusal({"results.jsonl": text})
        self.assertEqual((len(error.detail["findings"]), error.detail["total"]), (q.MAX_FINDINGS, 30))

    def test_an_unlabelled_literal_is_listed_and_a_clean_scan_raises_nothing(self):
        error = self.refusal({"f": f"a {self.SECRET}"}, [self.SECRET, ""])
        self.assertEqual(error.detail["findings"][0]["origin"], "listed")
        q.scan_for_secrets({"f": json.dumps({"id": "FS-01", "sha": "ab" * 32})}, [self.SECRET, ""])

    def test_the_runner_labels_extras_and_credentials(self):
        world = World(self)
        credentials = ["Hj3Vb7Nm5Rt8Zq4Xw9Kp2", "Zq4Xw9Kp2Vb7Nm5Rt8Hj3"]
        for name, secret, extra, expected in (("caller", "Gy6Tf1Ds0Ra8Eq2Wc4Ux", ["Gy6Tf1Ds0Ra8Eq2Wc4Ux"], "caller"),
                                               ("credential", credentials[1], [], "credential#1")):
            with self.subTest(name=name):
                runner = world.runner(read_credentials=lambda: credentials)
                with self.assertRaises(q.ProbeError) as raised:
                    runner.run(world.tmp / f"b-{name}", environment=environment(backend=secret), secrets=extra)
                finding = raised.exception.detail["findings"][0]
                self.assertEqual((finding["file"], finding["path"], finding["origin"]),
                                 ("environment.json", "$.backend", expected))
                self.assertRedacted(raised.exception, secret)
                self.assertFalse((world.tmp / f"b-{name}" / "summary.json").exists())  # nothing but the counter

    def test_the_arena_marker_is_labelled_a_marker(self):
        world = World(self)
        runner = world.runner(mach_names=lambda: ["com.apple.fake.service"])
        runner.markers.append("braid-dummy-fake-marker")
        with self.assertRaises(q.ProbeError) as raised:
            q.write_bundle(world.tmp / "m", environment=environment(), rows=[{"probe": "x", "note": "has braid-dummy-fake-marker"}],
                           quota=[], summary={}, secrets=runner.markers, origins=["marker"])
        self.assertEqual(raised.exception.detail["findings"][0]["origin"], "marker")
        self.assertEqual(raised.exception.detail["findings"][0]["file"], "results.jsonl")

    def test_a_second_scan_of_the_summary_reports_its_own_file(self):
        world = World(self)
        with self.assertRaises(q.ProbeError) as raised:
            q.write_bundle(world.tmp / "m", environment=environment(), rows=[], quota=[],
                           summary={"leak": self.SECRET}, secrets=[self.SECRET])
        self.assertEqual(raised.exception.detail["findings"][0]["file"], "summary.json")
        self.assertFalse((world.tmp / "m").exists())

    def test_credential_origins_follow_credential_values_and_name_fields_only(self):
        tmp = Path(tempfile.mkdtemp(prefix="braid-cfg-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        (tmp / ".credentials.json").write_text(json.dumps({"claudeAiOauth": {"accessToken": "tok-1234567890abcdef"}}))
        (tmp / ".claude.json").write_text(json.dumps({
            "oauthAccount": {"billingType": "stripe_subscription"}, "ids": ["aaaaaaaa-1111-2222-3333-444444444444"],
            "projects": {"/Users/lab/dir": {"lastSessionId": "7b9d3c1e-0f2a-4b6c-8d4e-1a2b3c4d5e6f"}},
            "dup": "tok-1234567890abcdef"}))
        inventory = q.credential_inventory(tmp)
        values, origins = [v for v, _ in inventory], [o for _, o in inventory]
        self.assertEqual(values, q.credential_values(tmp))
        by_value = dict(zip(values, origins))
        self.assertEqual(by_value["tok-1234567890abcdef"], {"file": ".credentials.json", "path": "$.claudeAiOauth.accessToken"})
        self.assertEqual(by_value["stripe_subscription"], {"file": ".claude.json", "path": "$.oauthAccount.billingType"})
        self.assertEqual(by_value["aaaaaaaa-1111-2222-3333-444444444444"], {"file": ".claude.json", "path": "$.ids[0]"})
        self.assertEqual(by_value["7b9d3c1e-0f2a-4b6c-8d4e-1a2b3c4d5e6f"],
                         {"file": ".claude.json", "path": "$.projects.<key>.lastSessionId"})
        self.assertNotIn("/Users/lab", json.dumps(origins))
        self.assertEqual(q.credential_inventory(tmp / "missing"), [])

    def test_a_credential_valued_key_is_never_printed_in_an_origin_path(self):
        tmp = Path(tempfile.mkdtemp(prefix="braid-cfg-"))
        self.addCleanup(shutil.rmtree, tmp, ignore_errors=True)
        key = "Zq8Xk2Lm9Pq4Rt7Vw1Yz3Ab5Cd6Ef8Gh"  # 32 characters, a plain-looking name that is also a value
        (tmp / ".claude.json").write_text(json.dumps({"cache": {key: key}, "plain": {"hasLongName": "x1" * 10}}))
        inventory = q.credential_inventory(tmp)
        self.assertIn(key, [v for v, _ in inventory])
        self.assertNotIn(key, json.dumps([o for _, o in inventory]))
        self.assertEqual(dict(inventory)[key]["path"], "$.cache.<key>")
        self.assertEqual(dict(inventory)["x1" * 10]["path"], "$.plain.hasLongName")

if __name__ == "__main__":
    unittest.main()
