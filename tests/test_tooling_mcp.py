# SPDX-License-Identifier: AGPL-3.0-only

from __future__ import annotations

import asyncio
import base64
import builtins
from copy import deepcopy
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

from agent_braid import mcp_runtime
from agent_braid import runtime_policy
from agent_braid.tooling_mcp import (
    CHUNK_BYTES,
    INLINE_RESULT_BYTES,
    MAX_ARTIFACT_BYTES,
    MAX_FRAME_BYTES,
    ToolingConfig,
    ToolingError,
    ToolingService,
    _BoundedInput,
    _read_resource_bounded,
    _settle_cancelled_worker,
    _validate_call_shape,
)


ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / "examples/analysis/file-edits.json").read_text())


class ToolingServiceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        self.source = base / "source"
        self.results = base / "results"
        self.source.mkdir()
        self.results.mkdir()
        self.config = ToolingConfig(self.source, self.results)
        self.service = ToolingService(self.config)

    def tearDown(self):
        self.temp.cleanup()

    def test_analyze_work_preserves_core_result_and_advisory_boundary(self):
        result = self.service.invoke(
            "analyze-work", {"kind": "aim", "request": SAMPLE}, threading.Event())
        self.assertEqual(result["schemaVersion"], "agent-braid-tooling/v0.1")
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["result"]["report"]["interactions"][0]["classification"],
                         "independent-candidate")
        self.assertFalse(result["result"]["report"]["executionAuthorization"])
        self.assertTrue(result["provenance"]["inputDigest"])

    def test_runtime_mutations_are_not_advertised_or_dispatchable_by_default(self):
        self.assertEqual(self.service.tools, ("analyze-work", "analyze", "prepare"))
        result = self.service.invoke("execute", {}, threading.Event())
        self.assertEqual(result["status"], "refused")
        self.assertFalse(any("grant" in name.lower() for name in self.service.tools))

    def test_worktree_paths_must_be_in_operator_allowlist(self):
        request = {"gitAnalysisRequestVersion": "0.1.0-alpha",
                   "repository": str(self.source), "baseRevision": "HEAD",
                   "operations": [{"instanceId": "a", "attemptId": "a1",
                       "source": {"kind": "worktree", "path": str(self.source.parent)},
                       "dependencies": [], "uncertainPaths": []},
                       {"instanceId": "b", "attemptId": "b1",
                       "source": {"kind": "commit", "revision": "HEAD"},
                       "dependencies": [], "uncertainPaths": []}]}
        result = self.service.invoke("analyze-work", {"kind": "git", "request": request}, threading.Event())
        self.assertEqual(result["status"], "refused")
        self.assertIn("allowlist", result["summary"])
        self.assertNotIn(self.temp.name, result["summary"])

    def test_depth_and_operation_bounds_are_checked_before_core(self):
        deeply_nested = {}
        cursor = deeply_nested
        for _ in range(34):
            cursor["x"] = {}
            cursor = cursor["x"]
        result = self.service.invoke("analyze-work", {"kind": "aim", "request": deeply_nested},
                                     threading.Event())
        self.assertEqual(result["status"], "refused")
        excessive = {"analysisInputVersion": "0.1.0-alpha", "source": {
            "kind": "test", "description": "bounded"}, "operations": [{}] * 33}
        result = self.service.invoke("analyze-work", {"kind": "aim", "request": excessive},
                                     threading.Event())
        self.assertEqual(result["status"], "refused")
        self.assertIn("32-operation", result["summary"])

    def test_chunk_manifest_and_exact_reconstruction(self):
        value = {"payload": "λ" * (INLINE_RESULT_BYTES // 2 + 100)}
        envelope = self.service._envelope("analyze-work", "ok", value, input_value={"kind": "fixture"})
        self.assertEqual(envelope["result"]["type"], "evidence-artifact-reference")
        ref = envelope["result"]
        mime, manifest_text = self.service.read_resource(ref["uri"])
        manifest = json.loads(manifest_text)
        self.assertEqual(mime, "application/json")
        chunks = bytearray()
        uri = manifest["firstChunkUri"]
        while uri:
            _, chunk_text = self.service.read_resource(uri)
            chunk = json.loads(chunk_text)
            data = base64.b64decode(chunk["data"], validate=True)
            self.assertEqual(len(data), chunk["length"])
            self.assertLessEqual(len(data), CHUNK_BYTES)
            chunks.extend(data)
            uri = chunk["nextChunkUri"]
        self.assertEqual(len(chunks), manifest["sizeBytes"])
        self.assertEqual(__import__("hashlib").sha256(chunks).hexdigest(), manifest["sha256"])
        self.assertEqual(json.loads(chunks), value)

    def test_resource_rejects_wrong_owner_hash_and_range(self):
        envelope = self.service._envelope("analyze-work", "ok", {"payload": "x" * (INLINE_RESULT_BYTES + 1)},
                                          input_value={"kind": "fixture"})
        uri = envelope["result"]["uri"]
        with self.assertRaises(ToolingError):
            self.service.read_resource(uri.replace("/runs/", "/runs/forged", 1))
        with self.assertRaises(ToolingError):
            self.service.read_resource(uri + "/chunks/" + "0" * 64 + "/0/1")
        with self.assertRaises(ToolingError):
            self.service.read_resource(uri + "/chunks/" + envelope["result"]["sha256"] + "/0/999999")
        with self.assertRaisesRegex(ToolingError, "artifact bounds"):
            self.service.read_resource(uri + "/chunks/" + envelope["result"]["sha256"] + "/" + "9" * 100 + "/1")
        with self.assertRaisesRegex(ToolingError, "URI limit"):
            self.service.read_resource(uri + "/" + "x" * 2000)

    def test_malformed_bracketed_resource_authority_is_a_bounded_refusal(self):
        with self.assertRaisesRegex(ToolingError, "Malformed resource URI"):
            self.service.read_resource("agent-braid://runs[bad/status")

    def test_oversized_core_result_never_claims_success_or_complete_evidence(self):
        oversized = {"payload": "x" * (MAX_ARTIFACT_BYTES + 1)}
        plan = {"planDigest": "a" * 64, "runtimeManifest": {
            "runDirectory": str(self.results / "oversized-run")}}
        refused = self.service._envelope("prepare", "ok", oversized,
            input_value={"request": {}}, plan_override=plan)
        self.assertEqual("refused", refused["status"])
        self.assertIsNone(refused["result"])
        self.assertFalse(refused["evidenceRefs"])
        self.assertNotIn("completed", refused["summary"])

        uncertain = self.service._envelope("execute", "ok", oversized,
            input_value={"plan": plan}, plan_override=plan)
        self.assertEqual("unknown", uncertain["status"])
        self.assertTrue(uncertain["result"]["resultUnavailable"])
        self.assertEqual("Do not replay; inspect the existing run",
                         uncertain["result"]["retryGuidance"])
        self.assertFalse(uncertain["evidenceRefs"])
        self.assertNotIn("completed", uncertain["summary"])

    def test_artifact_corruption_is_rejected_in_manifest_and_chunk_reads(self):
        envelope = self.service._envelope("analyze-work", "ok",
            {"payload": "x" * (INLINE_RESULT_BYTES + 1)}, input_value={"kind": "fixture"})
        artifact = next(iter(self.service.artifacts.values()))
        object.__setattr__(artifact, "data", b"z" * artifact.expected_size)
        with self.assertRaisesRegex(ToolingError, "corrupt or stale"):
            self.service.read_resource(envelope["result"]["uri"])
        uri = envelope["result"]["uri"] + "/chunks/" + artifact.expected_digest + "/0/1"
        with self.assertRaisesRegex(ToolingError, "corrupt or stale"):
            self.service.read_resource(uri)

    def test_service_validates_call_shape_and_operation_bounds_itself(self):
        malformed = self.service.invoke("analyze-work", {"kind": "aim"}, threading.Event())
        self.assertEqual(malformed["status"], "refused")
        self.assertIn("input schema", malformed["summary"])
        request = {"analysisInputVersion": "0.1.0-alpha", "source": {
            "kind": "test", "description": "bounded"}, "operations": [{}] * 33}
        malformed = self.service.invoke("analyze", {"request": request}, threading.Event())
        self.assertEqual(malformed["status"], "refused")
        self.assertIn("32-operation", malformed["summary"])

    def test_internal_core_type_error_is_error_and_diagnostic_is_fixed(self):
        with patch("agent_braid.tooling_mcp.analysis.analyze", side_effect=TypeError("/secret/path")):
            result = self.service.invoke("analyze-work", {"kind": "aim", "request": SAMPLE}, threading.Event())
        self.assertEqual(result["status"], "error")
        self.assertNotIn("/secret/path", result["summary"])
        self.assertIn("Internal adapter failure", result["summary"])

    def test_active_call_limit_is_enforced(self):
        self.service.active_calls = 4
        result = self.service.invoke("analyze-work", {"kind": "aim", "request": SAMPLE}, threading.Event())
        self.assertEqual(result["status"], "refused")
        self.assertIn("concurrency limit", result["summary"])
        self.service.active_calls = 0

    def test_analysis_only_status_does_not_claim_runtime_observation(self):
        run_dir = self.results / "planned-run"
        plan = {"planDigest": "a" * 64, "runtimeManifest": {"runDirectory": str(run_dir)}}
        run_id = self.service._register_plan(plan)
        _, text = self.service.read_resource(f"agent-braid://runs/{run_id}/status")
        status = json.loads(text)["status"]
        self.assertEqual(status["status"], "unknown")
        self.assertTrue(status["planPrepared"])
        self.assertFalse(status["runObserved"])
        self.assertFalse(status["executionAuthorization"])

    def test_cancelled_request_never_dispatches(self):
        cancelled = threading.Event()
        cancelled.set()
        result = self.service.invoke("analyze-work", {"kind": "aim", "request": SAMPLE}, cancelled)
        self.assertEqual(result["status"], "refused")
        self.assertEqual(result["result"], None)

    def test_malformed_tool_shape_is_rejected_at_protocol_boundary(self):
        with self.assertRaises(ToolingError):
            _validate_call_shape("analyze-work", {"kind": "aim", "request": SAMPLE,
                                                   "extra": True})

    def test_runtime_requires_disjoint_operator_grant_store(self):
        with self.assertRaisesRegex(ToolingError, "outside source and result"):
            ToolingConfig(self.source, self.results, self.results / "grants", True)
        grants = self.source.parent / "grants"
        enabled = ToolingConfig(self.source, self.results, grants, True)
        self.assertIn("execute", ToolingService(enabled).tools)

    def test_results_and_grants_are_disjoint_from_every_allowlisted_worktree(self):
        base = Path(self.temp.name)
        worktree_parent = base / "readable-worktrees"
        worktree = worktree_parent / "checkout"
        worktree.mkdir(parents=True)
        nested_results = worktree / "results"
        nested_results.mkdir()
        grants_under = worktree / "grants"
        grants_under.mkdir()
        alias = base / "worktree-alias"
        alias.symlink_to(worktree, target_is_directory=True)
        aliased_grants = alias / "grant-store"

        for result_root in (nested_results, worktree_parent):
            result_root.mkdir(exist_ok=True)
            with self.subTest(result_root=result_root), self.assertRaisesRegex(
                    ToolingError, "result root must be disjoint"):
                ToolingConfig(self.source, result_root, worktree_roots=(worktree,))

        for grant in (grants_under, worktree_parent, aliased_grants):
            with self.subTest(grant=grant), self.assertRaisesRegex(
                    ToolingError, "outside source and result"):
                # Grant isolation applies in analysis-only mode too.
                ToolingConfig(self.source, self.results, grant, runtime_enabled=False,
                              worktree_roots=(worktree,))

    def test_source_and_worktree_read_roots_may_be_nested(self):
        nested = self.source / "nested-checkout"
        nested.mkdir()
        config = ToolingConfig(self.source, self.results, worktree_roots=(nested,))
        self.assertIn(self.source.resolve(), config.worktree_roots)
        self.assertIn(nested.resolve(), config.worktree_roots)

    def test_sdk_import_is_lazy_and_core_missing_extra_message_is_actionable(self):
        from agent_braid import tooling_mcp
        original_import = builtins.__import__

        def without_mcp(name, *args, **kwargs):
            if name == "mcp" or name.startswith("mcp."):
                raise ImportError("not installed")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=without_mcp):
            with self.assertRaisesRegex(RuntimeError, "optional 'tooling' extra"):
                tooling_mcp.create_server(self.config)
        self.assertEqual(mcp_runtime.TOOLS, ("analyze", "prepare", "status", "execute", "recover", "verify"))

    def test_server_requires_exact_pinned_sdk_distribution_before_construction(self):
        from agent_braid.tooling_mcp import create_server
        with patch("importlib.metadata.version", return_value="2.3.0"):
            if importlib.util.find_spec("mcp"):
                self.assertIsNotNone(create_server(self.config))
            else:
                with self.assertRaisesRegex(RuntimeError, "optional 'tooling' extra"):
                    create_server(self.config)
        with patch("importlib.metadata.version", return_value="1.0.0"):
            with self.assertRaisesRegex(RuntimeError, "Unsupported MCP SDK version"):
                create_server(self.config)
        from importlib.metadata import PackageNotFoundError
        with patch("importlib.metadata.version", side_effect=PackageNotFoundError("mcp")):
            with self.assertRaisesRegex(RuntimeError, "optional 'tooling' extra"):
                create_server(self.config)


class SyntheticRuntimeSequenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_git_runtime import GitRuntimeTests
        cls.fixture = GitRuntimeTests()
        cls.fixture.setUp()

    @classmethod
    def tearDownClass(cls):
        cls.fixture.doCleanups()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.results = self.root / "results"
        self.results.mkdir()
        self.grants = self.root / "grants"
        self.config = ToolingConfig(self.fixture.repo, self.results, self.grants, True)
        self.results = self.config.result_parent
        self.service = ToolingService(self.config)
        self.run_directory = self.results / "synthetic-run"
        self.request_args = {"request": self.fixture.request,
                             "runDirectory": str(self.run_directory), "mode": "serial"}

    def test_existing_runtime_prepare_grant_execute_status_verify_and_refusal_guards(self):
        outside = self.root / "outside" / "run"
        rejected = self.service.invoke("prepare", {**self.request_args,
            "runDirectory": str(outside)}, threading.Event())
        self.assertEqual("refused", rejected["status"])
        self.assertFalse(outside.parent.exists())

        core_plan = self.service.runtime.invoke("prepare", self.request_args, threading.Event())
        prepared = self.service.invoke("prepare", self.request_args, threading.Event())
        self.assertEqual("ok", prepared["status"])
        self.assertEqual(core_plan, prepared["result"], "adapter must preserve the complete RuntimeTools plan")
        self.assertFalse(self.run_directory.exists(), "prepare must remain a nonpersistent rehearsal")
        plan = prepared["result"]

        before = self.service.invoke("status", {"plan": plan}, threading.Event())
        self.assertEqual("no-private-run", before["result"]["status"])
        stale = deepcopy(plan)
        stale["planDigest"] = "0" * 64
        stale_result = self.service.invoke("status", {"plan": stale}, threading.Event())
        self.assertIn(stale_result["status"], {"refused", "unknown"})
        self.assertFalse(self.run_directory.exists())

        wrong = self.service.invoke("execute", {"plan": plan,
            "grantId": "00000000-0000-0000-0000-000000000001"}, threading.Event())
        self.assertIn(wrong["status"], {"refused", "unknown"})
        self.assertFalse(self.run_directory.exists())

        expired = runtime_policy.issue_operator_grant(plan, self.grants,
            acknowledge=plan["planDigest"], ttl_seconds=1)
        time.sleep(1.1)
        expired_result = self.service.invoke("execute", {"plan": plan,
            "grantId": expired["grantId"]}, threading.Event())
        self.assertIn(expired_result["status"], {"refused", "unknown"})
        self.assertFalse(self.run_directory.exists())

        grant = runtime_policy.issue_operator_grant(plan, self.grants,
            acknowledge=plan["planDigest"])
        completed = self.service.invoke("execute", {"plan": plan,
            "grantId": grant["grantId"]}, threading.Event())
        self.assertEqual("ok", completed["status"], completed["summary"])
        self.assertEqual("completed", completed["result"]["runtime"]["status"])
        inspected = self.service.invoke("status", {"plan": plan}, threading.Event())
        verified = self.service.invoke("verify", {"plan": plan}, threading.Event())
        self.assertEqual("ok", inspected["status"])
        self.assertEqual("verified-completed", inspected["result"]["runtime"]["status"])
        self.assertEqual("ok", verified["status"])
        self.assertEqual("verified-completed", verified["result"]["runtime"]["status"])
        reused = self.service.invoke("execute", {"plan": plan,
            "grantId": grant["grantId"]}, threading.Event())
        self.assertEqual("not-repeated", reused["result"]["dispatch"])
        self.assertEqual(self.fixture.before, self.fixture.snapshot(self.fixture.repo))

    def test_runtime_status_resource_caps_output_and_waits_on_cancellation(self):
        plan = {"planDigest": "a" * 64, "runtimeManifest": {
            "runDirectory": str(self.run_directory)}}
        run_id = self.service._register_plan(plan)
        uri = f"agent-braid://runs/{run_id}/status"

        class LargeStatus:
            def invoke(self, _name, _args, _cancelled):
                return {"status": "unknown", "detail": "x" * (256 * 1024)}

        self.service.runtime = LargeStatus()
        with self.assertRaisesRegex(ToolingError, "256 KiB"):
            self.service.read_resource(uri)

        started, completed = threading.Event(), threading.Event()

        class CancellableStatus:
            def invoke(self, _name, _args, cancelled):
                started.set()
                cancelled.wait(timeout=2)
                completed.set()
                return {"status": "unknown"}

        self.service.runtime = CancellableStatus()

        async def cancel_read():
            task = asyncio.create_task(_read_resource_bounded(self.service, uri))
            await asyncio.to_thread(started.wait, 1)
            task.cancel()
            with self.assertRaises(asyncio.CancelledError):
                await task

        asyncio.run(cancel_read())
        self.assertTrue(completed.is_set(), "resource cancellation must wait for the status worker")


class BoundedInputTests(unittest.IsolatedAsyncioTestCase):
    async def test_stream_rejects_duplicate_nonfinite_deep_and_invalid_utf8_before_sdk(self):
        for raw in (b'{"a":1,"a":2}\n', b'{"n":NaN}\n',
                    (b"{" * 50) + (b"}" * 50) + b"\n", b"\xff\n"):
            line = await _BoundedInput(io.BytesIO(raw)).__anext__()
            self.assertEqual(line, "{\n")
        self.assertEqual("{\n", await _BoundedInput(io.StringIO("\ud800\n")).__anext__())

    async def test_stream_caps_and_closes_on_oversized_line(self):
        class CountingStream:
            def __init__(self):
                self.remaining = MAX_FRAME_BYTES + 50_000
                self.calls = 0
            def readline(self, size=-1):
                self.calls += 1
                if self.remaining <= 0:
                    return b"\n"
                count = min(size, self.remaining)
                self.remaining -= count
                return b"x" * count
        stream = CountingStream()
        line = await _BoundedInput(stream).__anext__()
        self.assertEqual(line, "{\n")
        self.assertLess(stream.calls, 200)
        self.assertGreater(stream.remaining, 0, "oversized input should close without unbounded draining")


class WorkerCancellationTests(unittest.IsolatedAsyncioTestCase):
    async def test_cancellation_waits_for_dispatched_worker_checkpoint(self):
        started = threading.Event()
        cancel_event = threading.Event()
        completed = threading.Event()

        def worker_body():
            started.set()
            cancel_event.wait(timeout=2)
            completed.set()

        worker = asyncio.create_task(asyncio.to_thread(worker_body))

        async def caller():
            try:
                await asyncio.shield(worker)
            except asyncio.CancelledError:
                await _settle_cancelled_worker(worker, cancel_event)
                raise

        task = asyncio.create_task(caller())
        self.assertTrue(await asyncio.to_thread(started.wait, 1), "worker must dispatch before caller cancellation")
        task.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await task
        self.assertTrue(completed.is_set(), "handler must wait until the dispatched worker reaches its checkpoint")


@unittest.skipUnless(importlib.util.find_spec("mcp"), "optional tooling extra (mcp==2.3.0) is not installed")
class SdkClientIntegrationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.source = self.base / "source"
        self.results = self.base / "results"
        self.source.mkdir()
        self.results.mkdir()

    async def asyncTearDown(self):
        self.temp.cleanup()

    async def _client(self, mode: str):
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters
        params = StdioServerParameters(command=sys.executable,
            args=["-m", "agent_braid.tooling_mcp", "--source-root", str(self.source),
                  "--result-parent", str(self.results)], cwd=str(ROOT))
        return Client(params, mode=mode)

    async def test_sdk_auto_and_legacy_negotiation_tools_resource_prompt_and_call(self):
        for mode in ("auto", "legacy"):
            async with await self._client(mode) as client:
                expected_protocol = "2025-11-25" if mode == "legacy" else "2026-07-28"
                self.assertEqual(client.protocol_version, expected_protocol)
                listed = await client.list_tools()
                names = {tool.name for tool in listed.tools}
                self.assertEqual(names, {"analyze-work", "analyze", "prepare"})
                response = await client.call_tool("analyze-work", {"kind": "aim", "request": SAMPLE})
                envelope = response.structured_content
                self.assertEqual(envelope["status"], "ok")
                self.assertIn("report", envelope["result"])
                self.assertEqual(json.loads(response.content[0].text), envelope)
                if mode == "auto":
                    array_response = await client.call_tool("analyze-work", {
                        "kind": "aim", "request": SAMPLE["operations"]})
                    self.assertEqual("ok", array_response.structured_content["status"])
                    self.assertEqual(2, array_response.structured_content["result"]["report"]["summary"]["operationCount"])
                resources = await client.list_resources()
                self.assertIn("agent-braid://capabilities", {r.uri for r in resources.resources})
                resource = await client.read_resource("agent-braid://capabilities")
                self.assertIn("analysis-only", resource.contents[0].text)
                prompts = await client.list_prompts()
                self.assertEqual({p.name for p in prompts.prompts},
                                 {"agent-braid-analyze", "agent-braid-plan", "agent-braid-evidence"})
                prompt = await client.get_prompt("agent-braid-evidence")
                self.assertIn("SHA-256", prompt.messages[0].content.text)

if __name__ == "__main__":
    unittest.main()
