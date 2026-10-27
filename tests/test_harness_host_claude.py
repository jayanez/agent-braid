# SPDX-License-Identifier: AGPL-3.0-only
"""Claude host adapter controls with deterministic doubles; no native dispatch or qualification."""
from dataclasses import FrozenInstanceError
from hashlib import sha256
import threading
import unittest

from agent_braid import harness_context as ctx
from agent_braid import harness_host_claude as hc
from agent_braid import harness_observation as obs
from agent_braid.harness_manifest import parse_manifest
from agent_braid.system_one import canonical
from tests.test_harness_manifest import make_manifest

NOW = 1_800_000_000
SECRET = "sk-test-SECRET-0123456789"
SESSION = "123e4567-e89b-42d3-a456-426614174000"
VERSION = "2.1.0 (Claude Code)"
WINDOW = hc.CompatibilityWindow((2, 0, 0), (3, 0, 0))
NOTE = b"owned note\n"


def make_manifest_and_context(note=NOTE):
    value = make_manifest()
    value["context"] = [{"id": "note", "path": "a/note.txt", "sha256": sha256(note).hexdigest(),
                         "sizeBytes": len(note), "trust": "untrusted-evidence", "selected": True}]
    value["effects"]["read"] = ["base/guidance/main.md", "candidate/guidance/main.md",
                                "context/a/note.txt", "source/task.txt"]
    manifest = parse_manifest(canonical(value))
    budget = ctx.ContextBudget(max_entries=4, max_entry_bytes=1024, max_total_bytes=2048,
                               excerpt_bytes=128)
    return manifest, ctx.assemble_context(manifest, {"a/note.txt": note}, budget=budget)


def make_inventory():
    wire = {"format": obs.INVENTORY_FORMAT, "allowedEventFields": ["text", "state"],
            "secrets": [SECRET], "maxRetentionSeconds": 3600}
    return obs.verify_inventory(canonical(wire), expected_sha256=sha256(canonical(wire)).hexdigest())


def init(**over):
    return {"type": "system", "subtype": "init", "session_id": SESSION, "model": "claude-test",
            "claude_code_version": VERSION, "apiKeySource": "none", **over}


def assistant(*blocks):
    return {"type": "assistant", "message": {"content": list(blocks)}}


def result(**over):
    return {"type": "result", "subtype": "success", "is_error": False, "session_id": SESSION,
            "permission_denials": [], **over}


GOOD = (init(), assistant({"type": "text", "text": "reading"}, {"type": "tool_use", "name": "Read"}),
        {"type": "user", "message": {"content": [{"type": "tool_result", "content": "secret body"}]}},
        result())


def run(lines=GOOD, *, double=None, **over):
    manifest, context = make_manifest_and_context()
    args = dict(transport=double or hc.ClaudeHostDouble(lines), request=hc.ClaudeRequest(SESSION),
                compatibility=WINDOW, attempt_id="attempt-1", inventory=make_inventory(), now=NOW,
                retention_seconds=60)
    args.update(over)
    return hc.run_claude(manifest, context, **args)


class NativeStub(hc.ClaudeTransport):
    """A would-be real launcher; any call is a test failure."""

    def version(self):
        raise AssertionError("native version probe must not run")

    def run(self, plan, prompt, limits, cancel):
        raise AssertionError("native dispatch must not run")


def qualification_wire(**over):
    manifest, _ = make_manifest_and_context()
    wire = {"format": hc.QUALIFICATION_FORMAT, "host": "claude",
            "environmentSha256": manifest.data["environment"]["sha256"],
            "enforced": ["credential", "filesystem", "network", "process"],
            "expiresAt": NOW + 100, "evidenceSha256": "a" * 64}
    wire.update(over)
    return wire


def qualify(wire):
    raw = canonical(wire)
    return hc.verify_host_qualification(raw, expected_sha256=sha256(raw).hexdigest())


class ClaudeHostTests(unittest.TestCase):
    def refuses(self, reason, **kw):
        with self.assertRaises(hc.ClaudeHostError) as cm:
            run(**kw)
        self.assertEqual(cm.exception.reason, reason)

    def state(self, result_):
        return result_.observation.to_dict()["terminal"]

    # --- positive controls ---

    def test_complete_stream_normalizes_to_a_hash_bound_completed_observation(self):
        double = hc.ClaudeHostDouble(GOOD)
        outcome = run(double=double)
        data = outcome.observation.to_dict()
        self.assertEqual(self.state(outcome), "completed")
        self.assertEqual(outcome.transport, "double")
        self.assertEqual(data["source"], "fixture")
        self.assertEqual([e["kind"] for e in data["events"]], ["start", "message", "tool", "terminal"])
        self.assertEqual((outcome.host_version, outcome.host_model), (VERSION, "claude-test"))
        self.assertFalse(outcome.executionAuthorization)
        self.assertFalse(outcome.to_dict()["executionAuthorization"])
        self.assertNotIn("secret body", repr(data))  # tool results never exported
        with self.assertRaises(FrozenInstanceError):
            outcome.transport = "native"

    def test_launch_plan_is_claude_specific_fresh_session_and_read_only(self):
        double = hc.ClaudeHostDouble(GOOD)
        run(double=double, request=hc.ClaudeRequest(SESSION, model="claude-test", allowed_tools=("Grep", "Read")))
        (plan, prompt), = double.launches
        argv = plan.argv
        self.assertEqual(argv[:4], ("claude", "-p", "--output-format", "stream-json"))
        self.assertEqual(argv[argv.index("--session-id") + 1], SESSION)
        self.assertEqual(argv[argv.index("--permission-mode") + 1], "plan")
        self.assertEqual(argv[argv.index("--allowedTools") + 1], "Grep,Read")
        self.assertEqual(argv[argv.index("--model") + 1], "claude-test")
        for forbidden in ("--resume", "--continue", "--dangerously-skip-permissions", "bypassPermissions"):
            self.assertNotIn(forbidden, argv)
        self.assertEqual(plan.prompt_sha256, sha256(prompt).hexdigest())
        self.assertIn(b"owned note", prompt)

    def test_environment_policy_keeps_existing_auth_and_denies_paid_routes(self):
        double = hc.ClaudeHostDouble(GOOD)
        run(double=double)
        plan = double.launches[0][0]
        self.assertEqual(plan.env_allow, ("HOME", "PATH"))
        self.assertIn("ANTHROPIC_API_KEY", plan.env_deny)
        self.assertFalse(set(plan.env_allow) & set(plan.env_deny))

    def test_secret_in_output_is_redacted_from_the_observation(self):
        lines = (init(), assistant({"type": "text", "text": f"key {SECRET}"}), result())
        outcome = run(lines)
        self.assertNotIn(SECRET, repr(outcome.observation.to_dict()))
        self.assertNotIn(SECRET.encode(), outcome.observation.canonical_bytes)

    # --- permissions, session and request ---

    def test_unsafe_permission_modes_and_tools_are_refused(self):
        for mode in ("bypassPermissions", "acceptEdits", "dontAsk", "", None):
            with self.assertRaises(hc.ClaudeHostError) as cm:
                hc.ClaudeRequest(SESSION, permission_mode=mode)
            self.assertEqual(cm.exception.reason, "permission-refused")
        for tools in (("Bash",), ("Write",), ("*",), ("Read", "Read"), ["Read"], ("Read", "Bash(*)")):
            with self.assertRaises(hc.ClaudeHostError):
                hc.ClaudeRequest(SESSION, allowed_tools=tools)

    def test_session_model_and_turn_limits_are_strict(self):
        for session in ("", "not-a-uuid", SESSION.upper(), SESSION + "0", None, 7):
            with self.assertRaises(hc.ClaudeHostError):
                hc.ClaudeRequest(session)
        for model in ("", "-x", "a b", "x" * 65, 5):
            with self.assertRaises(hc.ClaudeHostError):
                hc.ClaudeRequest(SESSION, model=model)
        for turns in (0, 9, True, "3"):
            with self.assertRaises(hc.ClaudeHostError):
                hc.ClaudeRequest(SESSION, max_turns=turns)

    def test_request_inputs_are_typed_and_refused_without_launch(self):
        double = hc.ClaudeHostDouble(GOOD)
        manifest, context = make_manifest_and_context()
        base = dict(transport=double, request=hc.ClaudeRequest(SESSION), compatibility=WINDOW,
                    attempt_id="attempt-1", inventory=make_inventory(), now=NOW, retention_seconds=60)
        with self.assertRaises(hc.ClaudeHostError):
            hc.run_claude(manifest, "not a package", **base)
        with self.assertRaises(hc.ClaudeHostError):
            hc.run_claude(manifest, context, **{**base, "request": {"session_id": SESSION}})
        with self.assertRaises(hc.ClaudeHostError):
            hc.run_claude(manifest, context, **{**base, "limits": 3})
        with self.assertRaises(hc.ClaudeHostError) as cm:
            hc.run_claude(manifest, context, **{**base, "attempt_id": SECRET})
        self.assertEqual(cm.exception.reason, "secret-in-identity")
        with self.assertRaises(hc.ClaudeHostError):
            hc.HostLimits(wall_seconds=0)
        self.assertEqual(double.launches, [])

    def test_empty_context_is_refused_without_launch(self):
        manifest, _ = make_manifest_and_context()
        empty = ctx.assemble_context(manifest, {}, budget=ctx.ContextBudget(4, 1024, 2048, 128))
        double = hc.ClaudeHostDouble(GOOD)
        with self.assertRaises(hc.ClaudeHostError) as cm:
            hc.run_claude(manifest, empty, transport=double, request=hc.ClaudeRequest(SESSION),
                          compatibility=WINDOW, attempt_id="attempt-1", inventory=make_inventory(),
                          now=NOW, retention_seconds=60)
        self.assertEqual(cm.exception.reason, "invalid-context")
        self.assertEqual(double.launches, [])

    # --- native refusal and host separation ---

    def test_native_transport_is_refused_and_never_called(self):
        self.refuses("native-host-unqualified", transport=NativeStub())

    def test_double_subclass_cannot_claim_the_double_label(self):
        class Spoof(hc.ClaudeHostDouble):
            pass

        self.refuses("invalid-transport", transport=Spoof(GOOD))

    def test_non_transport_is_refused(self):
        self.refuses("invalid-transport", transport=object())

    def test_valid_claude_qualification_still_refuses_an_offline_manifest(self):
        stub = NativeStub()
        self.refuses("native-host-unqualified", transport=stub, qualification=qualify(qualification_wire()))

    def test_other_host_qualification_cannot_qualify_claude(self):
        with self.assertRaises(hc.ClaudeHostError) as cm:
            qualify(qualification_wire(host="codex"))
        self.assertEqual(cm.exception.reason, "host-mismatch")

    def test_qualification_is_strict_and_hash_bound(self):
        good = canonical(qualification_wire())
        digest = sha256(good).hexdigest()
        for bad in (b"{", b"[]", canonical(qualification_wire(extra=1)),
                    canonical(qualification_wire(format="x")),
                    canonical(qualification_wire(enforced=["network"])),
                    canonical(qualification_wire(expiresAt=-1)),
                    canonical(qualification_wire(evidenceSha256="short")),
                    canonical({k: v for k, v in qualification_wire().items() if k != "host"})):
            with self.assertRaises(hc.ClaudeHostError):
                hc.verify_host_qualification(bad, expected_sha256=sha256(bad).hexdigest())
        with self.assertRaises(hc.ClaudeHostError) as cm:
            hc.verify_host_qualification(good, expected_sha256="0" * 64)
        self.assertEqual(cm.exception.reason, "qualification-drift")
        with self.assertRaises(hc.ClaudeHostError):
            hc.verify_host_qualification(good, expected_sha256="nothex")
        self.assertEqual(hc.verify_host_qualification(good, expected_sha256=digest).sha256, digest)

    def test_stale_or_foreign_qualification_is_not_enough(self):
        self.refuses("native-host-unqualified", transport=NativeStub(),
                     qualification=qualify(qualification_wire(expiresAt=NOW)))
        self.refuses("native-host-unqualified", transport=NativeStub(),
                     qualification=qualify(qualification_wire(environmentSha256="b" * 64)))
        self.refuses("native-host-unqualified", transport=NativeStub(), qualification=object())

    def test_codex_shaped_output_is_not_understood_as_claude_completion(self):
        lines = ({"type": "thread.started", "thread_id": "t"},
                 {"type": "item.completed", "item": {"type": "agent_message", "text": "done"}},
                 {"type": "turn.completed"})
        outcome = run(lines)
        self.assertNotEqual(self.state(outcome), "completed")
        self.assertIn("unknown-event-type", outcome.observation.to_dict()["loss"]["transportErrors"])

    # --- version handling ---

    def test_version_parsing_and_window(self):
        self.assertEqual(hc.parse_version("2.1.0 (Claude Code)"), (2, 1, 0))
        self.assertEqual(hc.parse_version("2.1.0"), (2, 1, 0))
        for bad in ("", "2.1", "v2.1.0", "2.1.0-beta", "2.1.0 (Other)", "2.1.0\n", None, 2):
            with self.assertRaises(hc.ClaudeHostError):
                hc.parse_version(bad)
        self.assertTrue(WINDOW.admits((2, 9, 9)))
        self.assertFalse(WINDOW.admits((3, 0, 0)))
        self.assertFalse(WINDOW.admits((1, 9, 9)))
        for args in (((2, 0), (3, 0, 0)), ((3, 0, 0), (2, 0, 0)), ((2, 0, 0), (2, 0, 0)), ([2, 0, 0], (3, 0, 0))):
            with self.assertRaises(hc.ClaudeHostError):
                hc.CompatibilityWindow(*args)

    def test_unsupported_or_malformed_version_refuses_before_launch(self):
        for text in ("3.0.0 (Claude Code)", "1.0.0", "garbage"):
            double = hc.ClaudeHostDouble(GOOD, version=text)
            with self.assertRaises(hc.ClaudeHostError):
                run(double=double)
            self.assertEqual(double.launches, [])

    def test_version_reported_in_init_must_match_discovery(self):
        outcome = run((init(claude_code_version="2.9.9 (Claude Code)"), result()))
        self.assertEqual(self.state(outcome), "failed")
        outcome = run((result(),))
        self.assertNotEqual(self.state(outcome), "completed")

    # --- terminals ---

    def test_error_results_and_denials(self):
        for subtype in ("error_max_turns", "error_during_execution"):
            self.assertEqual(self.state(run((init(), result(subtype=subtype, is_error=True)))), "failed")
        self.assertEqual(self.state(run((init(), result(is_error=True)))), "failed")
        denied = run((init(), result(permission_denials=[{"tool_name": "Bash"}])))
        self.assertEqual(self.state(denied), "refused")

    def test_unverified_or_paid_route_is_refused_not_completed(self):
        for source in ("ANTHROPIC_API_KEY", "user", None, ""):
            outcome = run((init(apiKeySource=source), result()))
            self.assertEqual(self.state(outcome), "refused", source)
        self.assertEqual(self.state(run((init(apiKeySource="oauth"), result()))), "completed")

    def test_session_mismatch_blocks_completion(self):
        other = "223e4567-e89b-42d3-a456-426614174000"
        self.assertEqual(self.state(run((init(session_id=other), result()))), "failed")
        self.assertEqual(self.state(run((init(), result(session_id=other)))), "failed")
        self.assertEqual(self.state(run((init(session_id=None), result(session_id=None)))), "failed")

    def test_exit_code_and_missing_result_never_fabricate_completion(self):
        self.assertEqual(self.state(run(double=hc.ClaudeHostDouble(GOOD, exit_code=1))), "failed")
        no_result = run((init(), assistant({"type": "text", "text": "x"})))
        self.assertEqual(self.state(no_result), "unobserved")
        self.assertIn("missing-result", no_result.observation.to_dict()["loss"]["transportErrors"])
        crashed = run(double=hc.ClaudeHostDouble((init(),), exit_code=137))
        self.assertEqual(crashed.observation.to_dict()["events"][-1]["state"], "failed")

    def test_duplicate_init_result_and_malformed_lines_block_completion(self):
        for lines, code in (((init(), init(), result()), "duplicate-init"),
                            ((init(), result(), result()), "duplicate-result"),
                            ((init(), b"{not json", result()), "malformed-line"),
                            ((init(), assistant({"type": "bogus"}), result()), "malformed-line"),
                            ((init(), {"type": "assistant", "message": []}, result()), "malformed-line"),
                            ((init(), {"type": "bogus"}, result()), "unknown-event-type")):
            outcome = run(lines)
            self.assertEqual(self.state(outcome), "unobserved", code)
            self.assertIn(code, outcome.observation.to_dict()["loss"]["transportErrors"])

    # --- cancellation, timeout, settlement, bounds ---

    def test_cancel_before_launch_never_starts_the_host(self):
        double, cancel = hc.ClaudeHostDouble(GOOD), threading.Event()
        cancel.set()
        self.refuses("cancelled-before-launch", double=double, cancel=cancel)
        self.assertEqual(double.launches, [])

    def test_cancel_during_run_is_interrupted_even_with_a_success_result(self):
        outcome = run(double=hc.ClaudeHostDouble(GOOD, cancel_mid_run=True))
        self.assertTrue(outcome.cancelled)
        self.assertEqual(self.state(outcome), "interrupted")
        late = threading.Event()
        double = hc.ClaudeHostDouble(GOOD)
        original = double.run

        def set_then_run(plan, prompt, limits, cancel):
            cancel.set()
            return original(plan, prompt, limits, cancel)

        double.run = set_then_run
        self.assertEqual(self.state(run(double=double, cancel=late)), "interrupted")

    def test_timeout_is_interrupted_never_completed(self):
        outcome = run(double=hc.ClaudeHostDouble(GOOD, exit_code=None, timed_out=True))
        self.assertTrue(outcome.timed_out)
        self.assertEqual(self.state(outcome), "interrupted")

    def test_unsettled_child_and_truncated_output_block_a_stated_outcome(self):
        unsettled = run(double=hc.ClaudeHostDouble(GOOD, settled=False))
        self.assertFalse(unsettled.settled)
        self.assertEqual(self.state(unsettled), "unobserved")
        self.assertIn("unsettled-child", unsettled.observation.to_dict()["loss"]["transportErrors"])
        truncated = run(double=hc.ClaudeHostDouble(GOOD, output_truncated=True))
        self.assertEqual(self.state(truncated), "unobserved")
        small = run(limits=hc.HostLimits(wall_seconds=1, max_output_bytes=40))
        self.assertEqual(self.state(small), "unobserved")

    def test_event_flood_and_oversize_fields_are_counted_not_trusted(self):
        flood = (init(), *[assistant({"type": "text", "text": "x"})] * 400, result())
        outcome = run(flood, limits=hc.HostLimits(max_output_bytes=1_048_576))
        self.assertIn("event-overflow", outcome.observation.to_dict()["loss"]["transportErrors"])
        self.assertNotEqual(self.state(outcome), "completed")
        big = run((init(), assistant({"type": "text", "text": "y" * 9000}), result()))
        self.assertIn("field-truncated", big.observation.to_dict()["loss"]["transportErrors"])
        self.assertNotEqual(self.state(big), "completed")

    def test_transport_failures_are_sanitized(self):
        double = hc.ClaudeHostDouble(GOOD)
        double.run = lambda *a: (_ for _ in ()).throw(RuntimeError(SECRET))
        with self.assertRaises(hc.ClaudeHostError) as cm:
            run(double=double)
        self.assertEqual(cm.exception.reason, "transport-failed")
        self.assertNotIn(SECRET, str(cm.exception))
        double = hc.ClaudeHostDouble(GOOD)
        double.run = lambda *a: "not a run"
        with self.assertRaises(hc.ClaudeHostError) as cm:
            run(double=double)
        self.assertEqual(cm.exception.reason, "invalid-transport-result")


if __name__ == "__main__":
    unittest.main()
