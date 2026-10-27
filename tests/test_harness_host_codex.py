# SPDX-License-Identifier: AGPL-3.0-only
"""Offline Codex host adapter controls; deterministic doubles, no native dispatch."""
from dataclasses import FrozenInstanceError, replace
from hashlib import sha256
import json
import unittest

from agent_braid import harness_host_codex as codex
from agent_braid import harness_lab as lab
from agent_braid import harness_manifest as manifests
from agent_braid import harness_observation as obs
from agent_braid.system_one import canonical
from tests.test_harness_manifest import make_manifest

NOW = 1_800_000_000
SECRET = "sk-test-SECRET-0123456789"
GOOD = {"build": "codex-cli 0.46.0", "model": "gpt-test", "route": "subscription",
        "auth": "existing-login", "provider": "openai"}


def line(**event) -> bytes:
    return (json.dumps(event) + "\n").encode()


def stream(*extra, terminal=True) -> tuple:
    chunks = [line(type="thread.started", thread_id="t1"), line(type="turn.started"),
              line(type="item.completed", item={"id": "i1", "type": "agent_message", "text": "hi"}),
              *extra]
    if terminal:
        chunks.append(line(type="turn.completed", usage={"input_tokens": 5, "output_tokens": 7}))
    return tuple(chunks)


def make_manifest_obj(verifier_sha=None) -> manifests.HarnessManifest:
    wire = make_manifest()
    if verifier_sha:
        wire["verifier"]["sha256"] = verifier_sha
    return manifests.parse_manifest(canonical(wire))


def make_inventory() -> obs.ExportInventory:
    wire = {"format": obs.INVENTORY_FORMAT,
            "allowedEventFields": ["text", "state", "effect", "path", "tool", "exitCode", "textBytes"],
            "secrets": [SECRET], "maxRetentionSeconds": 3600}
    return obs.verify_inventory(canonical(wire), expected_sha256=sha256(canonical(wire)).hexdigest())


def launch(manifest=None, **over) -> codex.CodexLaunch:
    args = dict(manifest_sha256=(manifest or make_manifest_obj()).sha256,
                executable="/opt/codex/bin/codex", executable_sha256="a" * 64,
                build=GOOD["build"], model=GOOD["model"], effort="medium", prompt_sha256="b" * 64)
    args.update(over)
    return codex.CodexLaunch(**args)


def host(chunks=None, **over) -> codex.ScriptedCodexHost:
    over.setdefault("discovery", GOOD)
    return codex.ScriptedCodexHost(codex.Script(chunks=stream() if chunks is None else chunks, **over))


def run(h=None, manifest=None, spec=None, **over) -> codex.CodexRunResult:
    manifest = manifest or make_manifest_obj()
    args = dict(manifest=manifest, attempt_id="attempt-1", inventory=make_inventory(), now=NOW,
                retention_seconds=60, limits=codex.HostLimits(wall_seconds=5))
    args.update(over)
    return codex.run_codex(spec or launch(manifest), h or host(), **args)


def terminal(result) -> str:
    return result.observation.to_dict()["terminal"]


def refusal(test, call, reason):
    with test.assertRaises(codex.CodexHostError) as ctx:
        call()
    test.assertEqual(ctx.exception.reason, reason)


class Verifier(codex.OutcomeVerifier):
    def __init__(self, verdict="pass", sha=None, boom=False):
        self.verdict, self.boom, self.requests = verdict, boom, []
        self.sha256 = sha or make_manifest()["verifier"]["sha256"]

    def verify(self, request):
        self.requests.append(request)
        if self.boom:
            raise RuntimeError("verifier crashed")
        return self.verdict


class LaunchTests(unittest.TestCase):
    def test_typed_launch_is_frozen_and_hash_bound(self):
        spec = launch()
        self.assertEqual(spec.sha256, launch().sha256)
        self.assertNotEqual(spec.sha256, launch(effort="high").sha256)
        with self.assertRaises(FrozenInstanceError):
            spec.model = "other"
        data = spec.to_dict()
        self.assertEqual((data["route"], data["auth"], data["executionAuthorization"]),
                         ("subscription", "existing-login", False))
        self.assertEqual(spec.argv[-1], "-")  # prompt via stdin, never argv
        self.assertNotIn("b" * 64, " ".join(spec.argv))

    def test_malformed_fields_refuse(self):
        for over in ({"manifest_sha256": "x"}, {"executable": "codex"}, {"executable": "/a\x00b"},
                     {"build": "codex 1"}, {"model": "bad model"}, {"effort": "extreme"},
                     {"sandbox": "danger-full-access"}, {"prompt_sha256": "B" * 64},
                     {"executable_sha256": None}):
            with self.subTest(over=over):
                refusal(self, lambda: launch(**over), "invalid-launch")

    def test_paid_capable_environment_is_refused(self):
        for name in ("OPENAI_API_KEY", "CODEX_API_KEY", "OPENAI_BASE_URL", "ANTHROPIC_API_KEY",
                     "GITHUB_TOKEN", "AZURE_OPENAI_ENDPOINT", "OPENAI_ORG_ID"):
            with self.subTest(name=name):
                refusal(self, lambda: launch(env=((name, "x"),)), "paid-fallback-refused")

    def test_unlisted_and_duplicate_environment_is_refused(self):
        refusal(self, lambda: launch(env=(("EDITOR", "vi"),)), "env-not-allowed")
        refusal(self, lambda: launch(env=(("HOME", "/h"), ("HOME", "/i"))), "invalid-launch")
        self.assertEqual(launch(env=(("HOME", "/h"), ("CODEX_HOME", "/c"))).to_dict()["env"],
                         ["CODEX_HOME", "HOME"])


class DiscoveryTests(unittest.TestCase):
    def test_fresh_matching_discovery_passes(self):
        d = codex.parse_discovery(dict(GOOD), now=NOW)
        codex.verify_discovery(launch(), d, now=NOW + 300)

    def test_stale_or_future_discovery_refuses(self):
        d = codex.parse_discovery(dict(GOOD), now=NOW)
        refusal(self, lambda: codex.verify_discovery(launch(), d, now=NOW + 301), "discovery-stale")
        refusal(self, lambda: codex.verify_discovery(launch(), d, now=NOW - 1), "discovery-stale")

    def test_paid_route_or_api_key_auth_refuses(self):
        for over in ({"route": "api"}, {"auth": "api-key"}):
            d = codex.parse_discovery({**GOOD, **over}, now=NOW)
            refusal(self, lambda: codex.verify_discovery(launch(), d, now=NOW), "paid-fallback-refused")

    def test_unobserved_route_or_auth_refuses(self):
        for over in ({"route": None}, {"auth": None}):
            d = codex.parse_discovery({**GOOD, **over}, now=NOW)
            refusal(self, lambda: codex.verify_discovery(launch(), d, now=NOW), "route-unobserved")

    def test_build_and_model_drift_refuse(self):
        for over in ({"build": "codex-cli 0.47.0"}, {"model": "other"}, {"model": None}, {"build": None}):
            d = codex.parse_discovery({**GOOD, **over}, now=NOW)
            refusal(self, lambda: codex.verify_discovery(launch(), d, now=NOW), "discovery-drift")

    def test_provider_outside_allow_list_refuses(self):
        for over in ({"provider": "other"}, {"provider": None}):
            d = codex.parse_discovery({**GOOD, **over}, now=NOW)
            refusal(self, lambda: codex.verify_discovery(launch(), d, now=NOW), "provider-not-allowed")

    def test_host_reported_observation_time_makes_run_staleness_real(self):
        stale = {**GOOD, "observedAt": NOW - 301}
        refusal(self, lambda: run(host(discovery=stale)), "discovery-stale")
        self.assertEqual(terminal(run(host(discovery={**GOOD, "observedAt": NOW - 300}))), "completed")
        refusal(self, lambda: codex.parse_discovery({**GOOD, "observedAt": "x"}, now=NOW),
                "invalid-discovery")

    def test_provider_drift_after_run_forbids_completion(self):
        result = run(host(post_discovery={**GOOD, "provider": "other"}))
        self.assertIn("route-drift", result.observation.to_dict()["loss"]["transportErrors"])

    def test_non_string_item_and_change_kinds_do_not_crash(self):
        result = run(host(stream(line(type="item.completed", item={"type": []}),
                                 line(type="item.completed", item={"type": "file_change", "changes": [
                                     {"path": "a.txt", "kind": []}, {"path": "b.txt", "kind": {}}]}),
                                 line(type="item.completed", item={"type": {}}))))
        self.assertNotEqual(terminal(result), "completed")

    def test_raising_elapsed_is_a_fixed_transport_error(self):
        class Bad(codex._ScriptedSession):
            def elapsed(self):
                raise RuntimeError("secret detail")
        h = host()
        h.open = lambda spec, inputs: Bad(h._script)
        result = run(h)
        self.assertIn("transport-error", result.observation.to_dict()["loss"]["transportErrors"])
        self.assertNotEqual(terminal(result), "completed")

    def test_unimplemented_post_discover_is_not_silently_native(self):
        refusal(self, lambda: codex.NativeCodexHost().post_discover(), "native-dispatch-unqualified")

    def test_malformed_discovery_refuses(self):
        for raw in (None, [], {**GOOD, "extra": 1}, {k: v for k, v in GOOD.items() if k != "model"},
                    {**GOOD, "build": "v1"}, {**GOOD, "route": "free"}, {**GOOD, "auth": "oauth"},
                    {**GOOD, "model": 3}):
            with self.subTest(raw=raw):
                refusal(self, lambda: codex.parse_discovery(raw, now=NOW), "invalid-discovery")


class NativeRefusalTests(unittest.TestCase):
    def test_constant_is_false(self):
        self.assertIs(codex.NATIVE_DISPATCH_QUALIFIED, False)

    def test_native_host_refuses_everywhere(self):
        refusal(self, lambda: run(codex.NativeCodexHost()), "native-dispatch-unqualified")
        refusal(self, codex.NativeCodexHost().discover, "native-dispatch-unqualified")
        refusal(self, lambda: codex.NativeCodexHost().open(launch(), {}), "native-dispatch-unqualified")

    def test_forged_kind_and_subclass_cannot_ride_the_double_path(self):
        class Forged(codex.ScriptedCodexHost):
            kind = "double"
        forged = Forged(codex.Script(discovery=GOOD, chunks=stream()))
        refusal(self, lambda: run(forged), "native-dispatch-unqualified")
        self.assertEqual(forged.opened, 0)

        class Fake(codex.CodexHost):
            kind = "double"
            opened = 0

            def discover(self):
                return dict(GOOD)

            def open(self, spec, inputs):
                self.opened += 1
                raise AssertionError("must not launch")
        fake = Fake()
        refusal(self, lambda: run(fake), "native-dispatch-unqualified")
        self.assertEqual(fake.opened, 0)

    def test_lab_containment_qualification_does_not_unlock_native(self):
        wire = {"format": lab.QUALIFICATION_FORMAT, "backend": "native-x", "kind": "native",
                "environmentSha256": make_manifest()["environment"]["sha256"],
                "enforced": list(lab.ENFORCED_EFFECTS), "expiresAt": NOW + 100,
                "evidenceSha256": "e" * 64}
        qualification = lab.verify_qualification(canonical(wire),
                                                 expected_sha256=sha256(canonical(wire)).hexdigest())
        native = codex.NativeCodexHost()
        native.qualification = qualification
        refusal(self, lambda: run(native), "native-dispatch-unqualified")

    def test_double_result_is_labelled_fixture_never_host(self):
        result = run()
        self.assertEqual(result.host, "double")
        self.assertEqual(result.observation.to_dict()["source"], "fixture")
        self.assertFalse(result.executionAuthorization)
        self.assertIs(result.to_dict()["executionAuthorization"], False)
        self.assertIsNone(result.to_dict()["cashMicros"])


class StreamNormalizationTests(unittest.TestCase):
    def test_complete_stream_normalizes(self):
        result = run()
        data = result.observation.to_dict()
        self.assertEqual(terminal(result), "completed")
        self.assertEqual([e["kind"] for e in data["events"]], ["start", "message", "terminal"])
        self.assertEqual(data["events"][1]["text"], "hi")
        self.assertEqual(dict(result.usage), {"input_tokens": 5, "output_tokens": 7})
        self.assertEqual(result.ignored_events, 1)
        self.assertEqual(result.exit_code, 0)
        self.assertTrue(result.settled and result.cleaned)
        self.assertEqual(data["loss"]["transportErrors"], [])

    def test_tool_effect_and_file_events(self):
        extra = (
            line(type="item.completed", item={"type": "command_execution", "command": SECRET,
                                              "exit_code": 0}),
            line(type="item.completed", item={"type": "file_change", "changes": [
                {"path": "out.txt", "kind": "add"}, {"path": "a/b.txt", "kind": "update"},
                {"path": "old.txt", "kind": "delete"}]}),
            line(type="item.completed", item={"type": "web_search", "query": "q"}),
            line(type="item.completed", item={"type": "mcp_tool_call", "server": "s", "tool": "t"}),
            line(type="item.completed", item={"type": "reasoning", "text": "thinking"}))
        result = run(host(stream(*extra)))
        data = result.observation.to_dict()
        self.assertEqual(terminal(result), "completed")
        kinds = [(e["kind"], e.get("effect") or e.get("tool")) for e in data["events"]]
        self.assertIn(("effect", "process"), kinds)
        self.assertIn(("effect", "network"), kinds)
        self.assertIn(("tool", "mcp:s.t"), kinds)
        paths = {(f["effect"], f["path"]) for f in data["events"] if f["kind"] == "effect" and "path" in f}
        self.assertEqual(paths, {("create", "out.txt"), ("write", "a/b.txt"), ("delete", "old.txt")})
        self.assertTrue(all(e["evidence"] == "inferred" for e in data["effects"]))
        self.assertEqual(result.ignored_events, 2)  # turn.started + reasoning
        raw = result.observation.canonical_bytes
        self.assertNotIn(b"thinking", raw)
        self.assertNotIn(SECRET.encode(), raw)  # command text never exported

    def test_secret_in_message_is_redacted(self):
        result = run(host(stream(line(type="item.completed",
                                      item={"type": "agent_message", "text": "key " + SECRET}))))
        self.assertNotIn(SECRET.encode(), result.observation.canonical_bytes)
        self.assertEqual(result.observation.to_dict()["redaction"]["replacements"], 1)

    def test_artifact_diff_is_observed_not_inferred(self):
        result = run(host(files={"out.txt": b"done"}), inputs={})
        data = result.observation.to_dict()
        self.assertTrue(data["artifactsObserved"])
        self.assertEqual([a["path"] for a in data["artifacts"]], ["out.txt"])
        self.assertEqual(data["effects"][0]["evidence"], "observed")

    def test_unknown_event_types_forbid_completion(self):
        for bad in (line(type="brand.new"), line(type="item.completed", item={"type": "hologram"}),
                    line(type="item.completed", item=None), line(foo=1), b"[1]\n",
                    line(type="item.completed", item={"type": "file_change", "changes": [
                        {"path": "/etc/passwd", "kind": "add"}]}),
                    line(type="item.completed", item={"type": "file_change", "changes": [
                        {"path": "../x", "kind": "add"}]}),
                    line(type="item.completed", item={"type": "file_change", "changes": [
                        {"path": "x", "kind": "rename"}]})):
            with self.subTest(bad=bad):
                result = run(host(stream(bad)))
                self.assertEqual(terminal(result), "unobserved")

    def test_malformed_json_line_is_loss(self):
        result = run(host(stream(b"{not json\n")))
        self.assertEqual(terminal(result), "unobserved")
        self.assertIn("malformed-line", result.observation.to_dict()["loss"]["transportErrors"])

    def test_missing_terminal_with_clean_exit_is_unobserved(self):
        result = run(host(stream(terminal=False)))
        self.assertEqual(terminal(result), "unobserved")
        self.assertEqual(result.outcome, "unverified")

    def test_duplicate_terminal_is_unobserved(self):
        done = line(type="turn.completed", usage={})
        self.assertEqual(terminal(run(host(stream(done)))), "unobserved")

    def test_turn_failed_maps_to_failed_terminal(self):
        result = run(host(stream(line(type="turn.failed", error={"message": "boom"}),
                                 terminal=False), exit_code=1))
        data = result.observation.to_dict()
        self.assertEqual(terminal(result), "failed")
        self.assertEqual([e["kind"] for e in data["events"]][-2:], ["error", "terminal"])

    def test_nonzero_exit_without_terminal_is_supervisor_failed(self):
        result = run(host(stream(terminal=False), exit_code=3))
        self.assertEqual(terminal(result), "failed")

    def test_completed_claim_with_nonzero_exit_is_not_trusted(self):
        result = run(host(exit_code=2))
        self.assertEqual(terminal(result), "unobserved")
        self.assertIn("exit-contradicts-completion", result.observation.to_dict()["loss"]["transportErrors"])
        self.assertEqual(result.outcome, "unverified")

    def test_partial_final_line_is_loss(self):
        chunks = stream(terminal=False) + (b'{"type":"turn.compl',)
        result = run(host(chunks))
        self.assertIn("truncated-final-line", result.observation.to_dict()["loss"]["transportErrors"])
        self.assertEqual(terminal(result), "unobserved")

    def test_lines_split_across_chunks_reassemble(self):
        whole = b"".join(stream())
        chunks = tuple(whole[i:i + 7] for i in range(0, len(whole), 7))
        self.assertEqual(terminal(run(host(chunks))), "completed")

    def test_long_text_is_clipped_with_size_kept(self):
        result = run(host(stream(line(type="item.completed",
                                      item={"type": "agent_message", "text": "é" * 5000}))))
        message = result.observation.to_dict()["events"][2]
        self.assertLessEqual(len(message["text"].encode()), codex.MAX_TEXT_BYTES)
        self.assertEqual(message["textBytes"], 10_000)

    def test_event_overflow_cancels_and_forbids_completion(self):
        many = tuple(line(type="item.completed", item={"type": "web_search"})
                     for _ in range(obs.MAX_EVENTS + 5))
        result = run(host(stream(*many)), limits=codex.HostLimits(wall_seconds=5,
                                                                  max_output_bytes=65_536))
        self.assertIn("event-overflow", result.observation.to_dict()["loss"]["transportErrors"])
        self.assertEqual(terminal(result), "unobserved")

    def test_oversized_line_is_loss(self):
        result = run(host(stream(b"x" * (codex.MAX_LINE_BYTES + 10) + b"\n")))
        self.assertIn("line-overflow", result.observation.to_dict()["loss"]["transportErrors"])
        self.assertEqual(terminal(result), "unobserved")

    def test_output_cap_truncates_and_interrupts(self):
        result = run(host(stream()), limits=codex.HostLimits(wall_seconds=5, max_output_bytes=60))
        errors = result.observation.to_dict()["loss"]["transportErrors"]
        self.assertIn("output-truncated", errors)
        self.assertEqual(terminal(result), "unobserved")

    def test_transport_exception_is_loss(self):
        result = run(host(read_error_at=2))
        self.assertIn("transport-error", result.observation.to_dict()["loss"]["transportErrors"])
        self.assertEqual(terminal(result), "unobserved")


class CancelTimeoutTests(unittest.TestCase):
    def test_timeout_interrupts_and_settles(self):
        result = run(host(stream(terminal=False) + ("hang",), children=2, exit_code=0, tick=1.0),
                     limits=codex.HostLimits(wall_seconds=6))
        self.assertTrue(result.timed_out)
        self.assertEqual(result.exit_code, -15)
        self.assertTrue(result.settled and result.cleaned)
        self.assertEqual(terminal(result), "interrupted")
        self.assertEqual(result.outcome, "unverified")

    def test_timeout_boundary_uses_virtual_clock(self):
        slow = host(stream(terminal=False), tick=2.0)  # 4 reads == 8s elapsed
        self.assertTrue(run(slow, limits=codex.HostLimits(wall_seconds=5)).timed_out)
        fast = host(stream(), tick=0.1)
        self.assertFalse(run(fast, limits=codex.HostLimits(wall_seconds=5)).timed_out)

    def test_cancel_mid_stream_interrupts(self):
        token = codex.CancelToken()
        script = codex.Script(discovery=GOOD, chunks=stream(), on_read=lambda i: token.set() if i == 1 else None,
                              children=1)
        result = run(codex.ScriptedCodexHost(script), cancel=token)
        self.assertTrue(result.cancelled)
        self.assertEqual(terminal(result), "interrupted")
        self.assertTrue(result.settled)

    def test_cancel_before_first_read(self):
        token = codex.CancelToken()
        token.set()
        h = host()
        result = run(h, cancel=token)
        self.assertTrue(result.cancelled)
        self.assertEqual(result.observation.to_dict()["events"][0]["kind"], "terminal")

    def test_completion_racing_cancel_is_not_trusted(self):
        token = codex.CancelToken()
        script = codex.Script(discovery=GOOD, chunks=stream() + (b"",),
                              on_read=lambda i: token.set() if i == len(stream()) else None)
        result = run(codex.ScriptedCodexHost(script), cancel=token)
        self.assertTrue(result.cancelled)
        self.assertIn("completion-contradicts-supervisor",
                      result.observation.to_dict()["loss"]["transportErrors"])
        self.assertEqual(terminal(result), "unobserved")

    def test_unkillable_child_is_unsettled_and_blocks_completion(self):
        result = run(host(children=1, unkillable=True))
        self.assertFalse(result.settled)
        self.assertIn("unsettled-child", result.observation.to_dict()["loss"]["transportErrors"])
        self.assertEqual(terminal(result), "unobserved")
        self.assertEqual(result.outcome, "unverified")

    def test_lingering_child_after_clean_exit_is_killed(self):
        result = run(host(children=3))
        self.assertTrue(result.settled)
        self.assertEqual(terminal(result), "completed")

    def test_infinite_silence_is_bounded(self):
        result = run(host(("hang",)))  # clock never advances: read budget ends it
        self.assertTrue(result.timed_out)
        self.assertEqual(terminal(result), "interrupted")

    def test_route_drift_after_run_forbids_completion(self):
        result = run(host(post_discovery={**GOOD, "route": "api"}))
        self.assertIn("route-drift", result.observation.to_dict()["loss"]["transportErrors"])
        self.assertEqual(terminal(result), "unobserved")

    def test_close_failure_is_reported_as_not_cleaned(self):
        class Bad(codex._ScriptedSession):
            def close(self):
                return False
        h = host()
        h.open = lambda spec, inputs: Bad(h._script)
        self.assertFalse(run(h).cleaned)


class PreLaunchRefusalTests(unittest.TestCase):
    def test_manifest_drift(self):
        other = make_manifest()
        other["task"]["id"] = "other-task"
        spec = launch(manifests.parse_manifest(canonical(other)))
        h = host()
        refusal(self, lambda: run(h, spec=spec), "manifest-drift")
        self.assertEqual(h.opened, 0)

    def test_paid_and_drifted_discovery_never_launch(self):
        for over, reason in (({"auth": "api-key"}, "paid-fallback-refused"),
                             ({"route": "api"}, "paid-fallback-refused"),
                             ({"model": "other"}, "discovery-drift"),
                             ({"route": None}, "route-unobserved")):
            h = host(discovery={**GOOD, **over})
            refusal(self, lambda: run(h), reason)
            self.assertEqual(h.opened, 0)

    def test_malformed_discovery_never_launches(self):
        h = host(discovery={"build": 1})
        refusal(self, lambda: run(h), "invalid-discovery")
        self.assertEqual(h.opened, 0)

    def test_discovery_failure_is_sanitized(self):
        class Broken(codex.ScriptedCodexHost):
            pass
        h = codex.ScriptedCodexHost(codex.Script(discovery=GOOD))
        h.discover = lambda: (_ for _ in ()).throw(RuntimeError("secret " + SECRET))
        with self.assertRaises(codex.CodexHostError) as ctx:
            run(h)
        self.assertEqual(ctx.exception.reason, "discovery-failed")
        self.assertNotIn(SECRET, str(ctx.exception))

    def test_launch_failure_is_sanitized(self):
        refusal(self, lambda: run(host(open_error=True)), "launch-failed")

    def test_stale_discovery_is_not_reusable(self):
        d = codex.parse_discovery(dict(GOOD), now=NOW)
        refusal(self, lambda: codex.verify_discovery(launch(), d, now=NOW + 10_000), "discovery-stale")

    def test_invalid_arguments(self):
        refusal(self, lambda: run(attempt_id="bad id"), "invalid-attempt")
        refusal(self, lambda: run(attempt_id=SECRET), "secret-in-identity")
        refusal(self, lambda: run(retention_seconds=0), "invalid-retention")
        refusal(self, lambda: run(limits=codex.HostLimits(max_output_bytes=10_000_000)), "invalid-limits")
        refusal(self, lambda: run(inputs={"../x": b"a"}), "invalid-inputs")
        refusal(self, lambda: run(inputs={"a": "text"}), "invalid-inputs")
        refusal(self, lambda: codex.HostLimits(wall_seconds=0), "invalid-limits")
        refusal(self, lambda: codex.HostLimits(wall_seconds=lab.MAX_WALL_SECONDS + 1), "invalid-limits")
        refusal(self, lambda: codex.run_codex("spec", host(), manifest=make_manifest_obj(),
                                              attempt_id="a", inventory=make_inventory(), now=NOW,
                                              retention_seconds=1), "invalid-codex-request")

    def test_limits_cannot_exceed_manifest_stage_output(self):
        cap = make_manifest()["limits"]["maxStageOutputBytes"]
        refusal(self, lambda: run(limits=codex.HostLimits(max_output_bytes=cap + 1)), "invalid-limits")


class VerifierHandoffTests(unittest.TestCase):
    def test_pass_yields_verified_and_request_has_no_host_claim(self):
        verifier = Verifier("pass")
        result = run(host(files={"out.txt": b"done"}), verifier=verifier)
        self.assertEqual(result.outcome, "verified")
        request = verifier.requests[0]
        self.assertEqual(request.observation_sha256, result.observation.sha256)
        self.assertEqual(dict(request.artifacts), {"out.txt": b"done"})
        self.assertFalse(hasattr(request, "terminal") or hasattr(request, "events"))

    def test_fail_inconclusive_garbage_and_crash(self):
        for verifier, expected in ((Verifier("fail"), "rejected"), (Verifier("inconclusive"), "inconclusive"),
                                   (Verifier("maybe"), "inconclusive"), (Verifier(boom=True), "inconclusive")):
            self.assertEqual(run(verifier=verifier).outcome, expected)

    def test_no_verifier_never_means_verified(self):
        self.assertEqual(run().outcome, "unverified-no-verifier")

    def test_verifier_not_called_for_non_completed_attempts(self):
        verifier = Verifier("pass")
        for h in (host(stream(terminal=False) + ("hang",), tick=1.0), host(exit_code=2),
                  host(children=1, unkillable=True)):
            self.assertEqual(run(h, verifier=verifier, limits=codex.HostLimits(wall_seconds=3)).outcome,
                             "unverified")
        self.assertEqual(verifier.requests, [])

    def test_verifier_must_match_manifest_hash(self):
        h = host()
        refusal(self, lambda: run(h, verifier=Verifier(sha="9" * 64)), "verifier-drift")
        self.assertEqual(h.opened, 0)

    def test_verifier_cannot_be_the_host(self):
        class SelfVerifying(codex.ScriptedCodexHost, codex.OutcomeVerifier):
            sha256 = make_manifest()["verifier"]["sha256"]
        v = SelfVerifying(codex.Script(discovery=GOOD))
        refusal(self, lambda: run(verifier=v), "verifier-not-independent")

    def test_unobservable_artifacts_block_handoff(self):
        verifier = Verifier("pass")
        result = run(host(files={"../escape": b"x"}), verifier=verifier)
        self.assertIn("artifact-unobservable", result.observation.to_dict()["loss"]["transportErrors"])
        self.assertEqual(result.outcome, "unverified")
        self.assertEqual(verifier.requests, [])


if __name__ == "__main__":
    unittest.main()
