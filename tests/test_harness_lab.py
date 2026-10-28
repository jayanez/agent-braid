# SPDX-License-Identifier: AGPL-3.0-only
"""Offline laboratory runner controls; no host, native or containment acceptance."""
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
import glob
import os
import tempfile
import threading
import time
import unittest

from agent_braid import harness_lab as lab
from agent_braid import harness_manifest as manifests
from agent_braid import harness_observation as obs
from agent_braid.system_one import canonical
from tests.test_harness_manifest import make_manifest

NOW = 1_800_000_000
SECRET = "sk-test-SECRET-0123456789"
WORKDIR_GLOB = os.path.join(tempfile.gettempdir(), "braid-lab-*")

COMPLETE = b'''
import json
open("out.txt", "w").write("done")
for e in ({"seq": 0, "kind": "start"}, {"seq": 1, "kind": "message", "text": "hi"},
          {"seq": 2, "kind": "terminal", "state": "completed"}):
    print(json.dumps(e))
'''


def manifest_for(fixture: bytes) -> manifests.HarnessManifest:
    wire = make_manifest()
    wire["task"]["fixtureSha256"] = sha256(fixture).hexdigest()
    return manifests.parse_manifest(canonical(wire))


def make_inventory() -> obs.ExportInventory:
    wire = {"format": obs.INVENTORY_FORMAT, "allowedEventFields": ["text", "state", "effect", "path"],
            "secrets": [SECRET], "maxRetentionSeconds": 3600}
    return obs.verify_inventory(canonical(wire), expected_sha256=sha256(canonical(wire)).hexdigest())


def run(fixture: bytes = COMPLETE, manifest=None, **over) -> lab.LabResult:
    args = dict(backend=lab.SimulatedContainment(), attempt_id="attempt-1",
                inventory=make_inventory(), now=NOW, retention_seconds=60,
                limits=lab.FixtureLimits(wall_seconds=3))
    args.update(over)
    return lab.run_fixture(manifest or manifest_for(fixture), fixture, **args)


def native_manifest(host: str = "native-x", sessions: object = 1, fixture: bytes = COMPLETE):
    """A hand-built manifest declaring a native host; ``parse_manifest`` never yields one."""
    manifest = manifest_for(fixture)
    data = manifest.to_dict()
    data["host"]["kind"] = host
    if sessions is None:
        del data["limits"]["maxNativeSessions"]
    else:
        data["limits"]["maxNativeSessions"] = sessions
    return replace(manifest, data=data)


def terminal(result: lab.LabResult) -> str:
    return result.observation.to_dict()["terminal"]


def qualification(**over) -> lab.Qualification:
    wire = {"format": lab.QUALIFICATION_FORMAT, "backend": "native-x", "kind": "native",
            "environmentSha256": make_manifest()["environment"]["sha256"],
            "enforced": list(lab.ENFORCED_EFFECTS), "expiresAt": NOW + 100,
            "evidenceSha256": "e" * 64}
    wire.update(over)
    return lab.verify_qualification(canonical(wire), expected_sha256=sha256(canonical(wire)).hexdigest())


class FakeNative(lab.ContainmentBackend):
    def __init__(self, qual=None, result=None):
        self.qualification, self.result, self.calls = qual, result, 0

    def run(self, source, workdir, limits):
        self.calls += 1
        if isinstance(self.result, Exception):
            raise self.result
        return self.result or lab.ChildResult(
            b'{"seq":0,"kind":"start"}\n{"seq":1,"kind":"terminal","state":"completed"}\n',
            0, False, False, True)


class RunnerTests(unittest.TestCase):
    def test_owned_fixture_runs_and_is_observed_as_simulated(self):
        before = set(glob.glob(WORKDIR_GLOB))
        result = run()
        d = result.observation.to_dict()
        self.assertEqual(d["terminal"], "completed")
        self.assertEqual(d["source"], "fixture")
        self.assertEqual([a["path"] for a in d["artifacts"]], ["out.txt"])
        self.assertEqual(result.containment, "simulated")
        self.assertTrue(result.settled and result.cleaned)
        self.assertFalse(result.executionAuthorization or result.to_dict()["executionAuthorization"])
        self.assertEqual(set(glob.glob(WORKDIR_GLOB)), before)
        with self.assertRaises(FrozenInstanceError):
            result.containment = "native"

    def test_run_is_deterministic(self):
        a, b = run().observation, run().observation
        self.assertEqual(a.sha256, b.sha256)

    def test_fixture_hash_drift_refuses_before_any_child_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "ran")
            fixture = f'open({marker!r}, "w").close()'.encode()
            manifest = manifest_for(fixture)
            for tampered in (fixture + b"\n", b"", b"x" * 40_000):
                with self.subTest(size=len(tampered)), self.assertRaises(lab.LabError):
                    lab.run_fixture(manifest, tampered, backend=lab.SimulatedContainment(),
                                    attempt_id="a1", inventory=make_inventory(), now=NOW,
                                    retention_seconds=60)
            self.assertFalse(os.path.exists(marker))

    def test_bad_arguments_refuse_before_any_child_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "ran")
            fixture = f'open({marker!r}, "w").close()'.encode()
            for over in ({"attempt_id": "bad id!"}, {"retention_seconds": 0}, {"now": -1},
                         {"inventory": object()}, {"inputs": {"../x": b""}},
                         {"inputs": {"A": b"", "a": b""}}, {"inputs": {"a": "text"}},
                         {"limits": lab.FixtureLimits(max_output_bytes=10**6)}):
                with self.subTest(over=sorted(over)), self.assertRaises(lab.LabError):
                    run(fixture, **over)
            with self.assertRaises(lab.LabError):
                lab.FixtureLimits(wall_seconds=lab.MAX_WALL_SECONDS + 1)
            self.assertFalse(os.path.exists(marker))

    def test_attempt_id_containing_a_secret_is_refused_as_domain_error(self):
        with self.assertRaises(lab.LabError):
            run(attempt_id=SECRET)

    def test_empty_environment_and_private_workdir(self):
        fixture = b'''
import json, os
print(json.dumps({"seq": 0, "kind": "start"}))
print(json.dumps({"seq": 1, "kind": "message", "text": ",".join(sorted(os.environ))}))
print(json.dumps({"seq": 2, "kind": "terminal", "state": "completed"}))
'''
        os.environ["BRAID_LAB_CANARY"] = "leak"
        self.addCleanup(os.environ.pop, "BRAID_LAB_CANARY", None)
        d = run(fixture).observation.to_dict()
        names = d["events"][1]["text"].split(",")
        self.assertIn("PYTHONHASHSEED", names)
        self.assertNotIn("BRAID_LAB_CANARY", names)
        self.assertNotIn("PATH", names)

    def test_inputs_before_state_makes_modification_observable(self):
        fixture = b'''
import json
open("a.txt", "w").write("new")
for e in ({"seq": 0, "kind": "start"}, {"seq": 1, "kind": "terminal", "state": "completed"}):
    print(json.dumps(e))
'''
        d = run(fixture, inputs={"a.txt": b"old", "keep.txt": b"same"}).observation.to_dict()
        self.assertEqual([(a["path"], a["change"]) for a in d["artifacts"]], [("a.txt", "modified")])


class ChildFailureTests(unittest.TestCase):
    def test_timeout_is_interrupted_and_group_is_settled(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = os.path.join(tmp, "grandchild")
            fixture = f'''
import subprocess, sys, time
subprocess.Popen([sys.executable, "-c", "import time; time.sleep(2); open({marker!r}, 'w').close()"])
print('{{"seq":0,"kind":"start"}}', flush=True)
time.sleep(60)
'''.encode()
            started = time.monotonic()
            result = run(fixture, limits=lab.FixtureLimits(wall_seconds=1))
            self.assertLess(time.monotonic() - started, 10)
            self.assertTrue(result.timed_out and result.settled and result.cleaned)
            self.assertEqual(terminal(result), "interrupted")
            time.sleep(2.5)
            self.assertFalse(os.path.exists(marker), "grandchild survived settlement")

    def test_nonzero_exit_without_terminal_is_failed(self):
        d = run(b'import sys; print(\'{"seq":0,"kind":"start"}\'); sys.exit(3)')
        self.assertEqual((terminal(d), d.exit_code), ("failed", 3))

    def test_clean_exit_without_terminal_is_never_completed(self):
        result = run(b'print(\'{"seq":0,"kind":"start"}\')')
        self.assertEqual(result.exit_code, 0)
        self.assertEqual(terminal(result), "unobserved")

    def test_output_flood_is_truncated_and_cannot_complete(self):
        fixture = b'''
import sys
sys.stdout.write('{"seq":0,"kind":"start"}\\n')
while True:
    sys.stdout.write("x" * 4096 + "\\n")
'''
        result = run(fixture, limits=lab.FixtureLimits(wall_seconds=5, max_output_bytes=4096))
        self.assertTrue(result.output_truncated)
        self.assertEqual(terminal(result), "unobserved")
        self.assertIn("output-truncated", result.observation.to_dict()["loss"]["transportErrors"])

    def test_malformed_and_excess_events_are_loss_not_repair(self):
        fixture = b'''
import json
print("not json")
print(json.dumps({"seq": 0, "kind": "start"}))
print(json.dumps({"seq": 1, "kind": "terminal", "state": "completed"}))
'''
        result = run(fixture)
        self.assertEqual(terminal(result), "unobserved")
        self.assertEqual(result.observation.to_dict()["loss"]["transportErrors"], ["malformed-line"])
        many = b'import json\nfor i in range(300): print(json.dumps({"seq": i, "kind": "message"}))'
        result = run(many)
        self.assertIn("event-overflow", result.observation.to_dict()["loss"]["transportErrors"])
        self.assertEqual(terminal(result), "unobserved")

    def test_symlink_or_unreadable_artifact_marks_loss(self):
        fixture = b'''
import json, os
os.symlink("/etc/hosts", "link")
for e in ({"seq": 0, "kind": "start"}, {"seq": 1, "kind": "terminal", "state": "completed"}):
    print(json.dumps(e))
'''
        result = run(fixture)
        self.assertEqual(terminal(result), "unobserved")
        self.assertIn("artifact-unobservable", result.observation.to_dict()["loss"]["transportErrors"])
        self.assertTrue(result.cleaned)

    def test_non_utf8_fixture_is_a_domain_refusal(self):
        with self.assertRaises(lab.LabError):
            run(b"\xff\xfe")


class ContainmentTests(unittest.TestCase):
    def test_native_backend_without_qualification_refuses_without_running(self):
        backend = FakeNative()
        with self.assertRaisesRegex(lab.LabError, "^containment-unqualified$"):
            run(backend=backend)
        self.assertEqual(backend.calls, 0)

    def test_fixture_support_is_not_inherited_by_native_backends(self):
        class Lookalike(lab.SimulatedContainment):
            pass
        for backend in (Lookalike(), FakeNative(), object(), None):
            with self.subTest(backend=type(backend).__name__), self.assertRaises(lab.LabError):
                run(backend=backend)

    def test_qualification_must_match_environment_and_not_be_expired(self):
        for qual in (qualification(environmentSha256="0" * 64), qualification(expiresAt=NOW),
                     qualification(expiresAt=NOW - 1)):
            backend = FakeNative(qual)
            with self.subTest(qual=qual.expires_at), self.assertRaisesRegex(
                    lab.LabError, "^containment-unqualified$"):
                run(backend=backend)
            self.assertEqual(backend.calls, 0)

    def test_caller_constructed_qualification_object_of_wrong_type_refuses(self):
        backend = FakeNative({"environmentSha256": make_manifest()["environment"]["sha256"]})
        with self.assertRaisesRegex(lab.LabError, "^containment-unqualified$"):
            run(backend=backend)

    def test_qualified_native_backend_refuses_an_offline_manifest(self):
        # Parsed-manifest path (F1); the next test isolates each clause.
        backend = FakeNative(qualification())
        with self.assertRaisesRegex(lab.LabError, "^containment-unqualified$"):
            run(backend=backend)
        self.assertEqual(backend.calls, 0)

    def test_native_backend_requires_matching_host_kind_and_native_sessions(self):
        for manifest in (native_manifest(host="offline"), native_manifest(sessions=0), native_manifest(sessions=None),
                         native_manifest(sessions=True), native_manifest(sessions="1")):
            backend = FakeNative(qualification())
            with self.subTest(host=manifest.data["host"]["kind"],
                              sessions=manifest.data["limits"].get("maxNativeSessions")), \
                    self.assertRaisesRegex(lab.LabError, "^containment-unqualified$"):
                run(backend=backend, manifest=manifest)
            self.assertEqual(backend.calls, 0)

    def test_qualified_native_backend_is_labelled_native_and_host_sourced(self):
        backend = FakeNative(qualification())
        result = run(backend=backend, manifest=native_manifest())
        self.assertEqual((backend.calls, result.containment), (1, "native"))
        self.assertEqual(result.observation.to_dict()["source"], "host")
        self.assertFalse(result.executionAuthorization)

    def test_backend_failures_are_domain_errors_and_clean_up(self):
        before = set(glob.glob(WORKDIR_GLOB))
        for failure in (RuntimeError("boom"), OSError("disk"), "not a ChildResult"):
            with self.subTest(failure=repr(failure)), self.assertRaises(lab.LabError):
                run(backend=FakeNative(qualification(), failure), manifest=native_manifest())
        self.assertEqual(set(glob.glob(WORKDIR_GLOB)), before)

    def test_qualification_verification_is_strict_and_hash_bound(self):
        wire = {"format": lab.QUALIFICATION_FORMAT, "backend": "native-x", "kind": "native",
                "environmentSha256": "a" * 64, "enforced": list(lab.ENFORCED_EFFECTS),
                "expiresAt": NOW, "evidenceSha256": "e" * 64}
        raw = canonical(wire)
        good = sha256(raw).hexdigest()
        self.assertEqual(lab.verify_qualification(raw, expected_sha256=good).sha256, good)
        with self.assertRaisesRegex(lab.LabError, "^qualification-drift$"):
            lab.verify_qualification(raw, expected_sha256="0" * 64)
        bad = [dict(wire, kind="simulated"), dict(wire, enforced=["filesystem"]),
               dict(wire, enforced=[*lab.ENFORCED_EFFECTS, "x"]), dict(wire, extra=1),
               dict(wire, expiresAt=True), dict(wire, format="future/v9"),
               dict(wire, backend="bad id")]
        for value in bad:
            with self.subTest(value=value), self.assertRaises(lab.LabError):
                lab.verify_qualification(canonical(value), expected_sha256=sha256(canonical(value)).hexdigest())
        for raw_bad in (b"[]", b"\xff", b"{}", None, "x"):
            with self.subTest(raw=raw_bad), self.assertRaises(lab.LabError):
                lab.verify_qualification(raw_bad, expected_sha256=good)
        with self.assertRaises(lab.LabError):
            lab.verify_qualification(raw, expected_sha256="short")

class ReviewFollowupTests(unittest.TestCase):
    def test_non_object_qualification_json_is_a_domain_refusal(self):
        for raw in (b"[]", b"[1]", b"1", b'"x"', b"null", b"true"):
            with self.subTest(raw=raw), self.assertRaisesRegex(lab.LabError, "^invalid-qualification$"):
                lab.verify_qualification(raw, expected_sha256="0" * 64)

    def test_authorization_is_not_a_constructible_field(self):
        result = run()
        with self.assertRaises(TypeError):
            lab.LabResult(result.observation, "simulated", 0, False, False, True, True,
                          executionAuthorization=True)
        self.assertIs(result.executionAuthorization, False)
        with self.assertRaises(FrozenInstanceError):
            result.executionAuthorization = True

    def test_entry_scan_is_capped_and_lossy(self):
        fixture = f'''
import json, os
for i in range({lab.MAX_SCAN_ENTRIES + 50}):
    os.mkdir("d%d" % i)
for e in ({{"seq": 0, "kind": "start"}}, {{"seq": 1, "kind": "terminal", "state": "completed"}}):
    print(json.dumps(e))
'''.encode()
        result = run(fixture, limits=lab.FixtureLimits(wall_seconds=10))
        self.assertEqual(terminal(result), "unobserved")
        self.assertIn("artifact-unobservable", result.observation.to_dict()["loss"]["transportErrors"])
        self.assertTrue(result.cleaned)

    def test_runs_from_a_non_main_thread(self):
        box = []
        thread = threading.Thread(target=lambda: box.append(run()))
        thread.start()
        thread.join(30)
        self.assertEqual(terminal(box[0]), "completed")

    def test_child_cannot_exceed_rlimits(self):
        fixture = b'''
import json, resource
print(json.dumps({"seq": 0, "kind": "start"}))
print(json.dumps({"seq": 1, "kind": "message", "text": str(resource.getrlimit(resource.RLIMIT_NOFILE)[0])}))
print(json.dumps({"seq": 2, "kind": "terminal", "state": "completed"}))
'''
        self.assertEqual(run(fixture).observation.to_dict()["events"][1]["text"], "64")


if __name__ == "__main__":
    unittest.main()
