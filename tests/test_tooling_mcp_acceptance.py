# SPDX-License-Identifier: AGPL-3.0-only
"""Paired local acceptance controls for SPEC-040.

These tests exercise the installed optional SDK and synthetic service boundaries.
They do not observe Codex/Claude hosts or establish human acceptance.
"""
from __future__ import annotations

import asyncio
import base64
from copy import deepcopy
import hashlib
import importlib.metadata
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch
from typing import Any

from agent_braid import analysis, mcp_runtime, runtime_policy
from agent_braid.tooling_mcp import (
    CHUNK_BYTES, INLINE_RESULT_BYTES, ToolingConfig, ToolingError, ToolingService,
    _tool_definitions,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / "examples/analysis/file-edits.json").read_text(encoding="utf-8"))


def _fixture_config(base: Path, *, runtime: bool = False, source: Path | None = None):
    source = source or base / "source"
    source.mkdir(parents=True, exist_ok=True)
    results = base / "results"
    results.mkdir(parents=True, exist_ok=True)
    grants = base / "grants"
    return ToolingConfig(source, results, grants if runtime else None, runtime)


def _reconstruct(service: ToolingService, reference: dict) -> bytes:
    """Consumer-side manifest/chunk verifier; parse only after whole-file checks."""
    mime, text = service.read_resource(reference["uri"])
    manifest = json.loads(text)
    assert mime == "application/json"
    assert manifest["artifactId"] == reference["artifactId"]
    assert manifest["sha256"] == reference["sha256"]
    assert manifest["sizeBytes"] == reference["sizeBytes"]
    assert manifest["chunkSizeBytes"] == CHUNK_BYTES
    result = bytearray()
    uri = manifest["firstChunkUri"]
    expected_offset = 0
    visited = set()
    while uri is not None:
        if uri in visited:
            raise AssertionError("duplicate chunk URI")
        visited.add(uri)
        _, chunk_text = service.read_resource(uri)
        chunk = json.loads(chunk_text)
        raw = base64.b64decode(chunk["data"], validate=True)
        assert chunk["artifactId"] == manifest["artifactId"]
        assert chunk["artifactSha256"] == manifest["sha256"]
        assert chunk["offset"] == expected_offset
        assert chunk["length"] == len(raw)
        assert chunk["totalBytes"] == manifest["sizeBytes"]
        assert chunk["chunkSha256"] == hashlib.sha256(raw).hexdigest()
        assert 0 < len(raw) <= CHUNK_BYTES
        expected_offset += len(raw)
        result.extend(raw)
        uri = chunk["nextChunkUri"]
    assert expected_offset == manifest["sizeBytes"]
    assert hashlib.sha256(result).hexdigest() == manifest["sha256"]
    # Decode only after the complete byte chain and digest have been checked.
    bytes(result).decode("utf-8")
    return bytes(result)


class MpcAcceptance(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.config = _fixture_config(self.base)
        self.service = ToolingService(self.config)

    def test_sc001_optional_sdk_pin_core_import_and_missing_dependency_refusal(self):
        self.assertEqual(importlib.metadata.version("mcp"), "2.3.0")
        self.assertIsNotNone(importlib.util.find_spec("mcp"))
        self.assertEqual(mcp_runtime.TOOLS,
                         ("analyze", "prepare", "status", "execute", "recover", "verify"))
        # The core import surface does not eagerly import the optional SDK.
        original_import = __import__

        def no_sdk(name, *args, **kwargs):
            if name == "mcp" or name.startswith("mcp."):
                raise ImportError("not installed")
            return original_import(name, *args, **kwargs)

        from agent_braid import tooling_mcp
        with patch("builtins.__import__", side_effect=no_sdk):
            with self.assertRaisesRegex(RuntimeError, "optional 'tooling' extra"):
                tooling_mcp.create_server(self.config)

    def test_sc002_protocol_modes_and_legacy_endpoint_paired_controls(self):
        # The actual SDK peer negotiation matrix is exercised in the companion
        # integration test file; here assert both declared schema sets and legacy
        # dispatch semantics against the same immutable request.
        from mcp import types
        definitions = _tool_definitions(self.service, types)
        self.assertEqual({item.name for item in definitions}, set(self.service.tools))
        for definition in definitions:
            self.assertIsInstance(definition.input_schema, dict)
            self.assertIsInstance(definition.output_schema, dict)
        from tests.test_git_runtime import GitRuntimeTests
        fixture = GitRuntimeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        config = ToolingConfig(fixture.repo, self.config.result_parent)
        service = ToolingService(config)
        args = {"request": fixture.request}
        legacy = mcp_runtime.RuntimeTools(config.source_root,
                                          config.result_parent,
                                          config.result_parent / ".disabled-grants")
        legacy_result = legacy.invoke("analyze", args, threading.Event())
        tooling_result = service.invoke("analyze", args, threading.Event())
        self.assertEqual(tooling_result["status"], "ok")
        self.assertEqual(tooling_result["result"], legacy_result)
        refused = self.service.invoke("unsupported-mode", {}, threading.Event())
        self.assertEqual(refused["status"], "refused")
        self.assertNotIn("unsupported-mode", self.service.tools)

    def test_sc003_aim_git_worktree_parity_and_large_unicode_chain_refusals(self):
        # AIM: compare the complete MCP core report to the real CLI output.
        aim_path = self.base / "aim.json"
        aim_path.write_text(json.dumps(SAMPLE), encoding="utf-8")
        cli = subprocess.run([sys.executable, "-m", "agent_braid.cli", "analyze", str(aim_path)],
                             cwd=ROOT, capture_output=True, text=True, check=True)
        aim_result = self.service.invoke("analyze-work", {"kind": "aim", "request": SAMPLE}, threading.Event())
        self.assertEqual(aim_result["status"], "ok")
        self.assertEqual(aim_result["result"]["report"], json.loads(cli.stdout))
        self.assertFalse(aim_result["result"]["provenance"]["executionAuthorization"])

        # Scale a valid AIM input to an actual multi-megabyte analyzer report;
        # compare the complete SDK-shaped result to the CLI on identical bytes.
        large_aim = deepcopy(SAMPLE)
        template = large_aim["operations"][0]
        shared_resources = [f"repo://acceptance/λ/{index:02d}/{'r' * 361}" for index in range(12)]
        large_aim["operations"] = []
        for index in range(32):
            operation = deepcopy(template)
            operation["instanceId"] = f"acceptance-{index:02d}"
            operation["attemptId"] = f"acceptance-{index:02d}-attempt"
            operation["effects"]["declared"] = [
                {"kind": "write", "resource": resource} for resource in shared_resources]
            large_aim["operations"].append(operation)
        large_aim_path = self.base / "large-aim.json"
        large_aim_path.write_text(json.dumps(large_aim), encoding="utf-8")
        self.assertLess(large_aim_path.stat().st_size, 1024 * 1024)
        large_cli = subprocess.run([sys.executable, "-m", "agent_braid.cli", "analyze",
                                    str(large_aim_path)], cwd=ROOT, capture_output=True,
                                   text=True, check=True)
        large_envelope = self.service.invoke("analyze-work",
            {"kind": "aim", "request": large_aim}, threading.Event())
        self.assertEqual(large_envelope["status"], "ok", large_envelope["summary"])
        self.assertEqual(large_envelope["result"]["type"], "evidence-artifact-reference")
        self.assertGreater(large_envelope["result"]["sizeBytes"], INLINE_RESULT_BYTES)
        large_bytes = _reconstruct(self.service, large_envelope["result"])
        large_result = json.loads(large_bytes)
        self.assertEqual(large_result["report"], json.loads(large_cli.stdout))
        self.assertFalse(large_result["provenance"]["executionAuthorization"])
        # The analyzer's JSON serializer escapes non-ASCII report text. The
        # direct UTF-8 boundary condition is tested below with a raw Unicode
        # artifact whose code point is deliberately split across chunk 1.

        # Git/worktree: use a real temporary repository with two committed edits,
        # then compare the tagged adapter result to the existing CLI analyzer.
        from tests.test_git_adapter import GitAdapterTests
        fixture = GitAdapterTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        request = fixture.request(left={"kind": "worktree", "path": str(fixture.repo)})
        config = ToolingConfig(fixture.repo, self.config.result_parent,
                               worktree_roots=(fixture.repo,))
        service = ToolingService(config)
        git_input = self.base / "git.json"
        git_input.write_text(json.dumps(request), encoding="utf-8")
        provenance = self.base / "git-provenance.json"
        git_cli = subprocess.run([sys.executable, "-m", "agent_braid.cli", "analyze-git",
                                  str(git_input), "--provenance-output", str(provenance)],
                                 cwd=ROOT, capture_output=True, text=True, check=True)
        git_result = service.invoke("analyze-work", {"kind": "git", "request": request}, threading.Event())
        self.assertEqual(git_result["status"], "ok", git_result["summary"])
        self.assertEqual(git_result["result"]["report"], json.loads(git_cli.stdout))

        # A >256 KiB exact UTF-8 artifact whose first code point straddles the
        # first 128 KiB boundary verifies byte-oriented reconstruction.
        prefix = b'{"payload":"'
        pad = CHUNK_BYTES - len(prefix) - 1
        value = {"payload": "x" * pad + "界" * 100_000}
        envelope = self.service._envelope("analyze-work", "ok", value,
                                           input_value={"fixture": "large-unicode"})
        self.assertGreater(envelope["result"]["sizeBytes"], INLINE_RESULT_BYTES)
        raw = _reconstruct(self.service, envelope["result"])
        self.assertEqual(json.loads(raw), value)
        self.assertEqual(raw[CHUNK_BYTES - 1:CHUNK_BYTES + 2], "界".encode("utf-8"))
        uri = envelope["result"]["uri"]
        manifest = json.loads(self.service.read_resource(uri)[1])
        first = json.loads(self.service.read_resource(manifest["firstChunkUri"])[1])
        with self.assertRaises(ToolingError):
            self.service.read_resource(manifest["firstChunkUri"].replace(
                f"/{first['offset']}/{first['length']}", f"/{first['totalBytes']}/1"))
        with self.assertRaises(ToolingError):
            self.service.read_resource(manifest["firstChunkUri"].replace(first["artifactSha256"], "0" * 64))
        resource_read = self.service.read_resource

        def rewrite_chunk(transform):
            def read(selector, cancelled=None):
                mime, text = resource_read(selector, cancelled)
                if "/chunks/" not in selector:
                    return mime, text
                chunk = json.loads(text)
                return mime, json.dumps(transform(chunk, selector), separators=(",", ":"))
            return read

        with patch.object(self.service, "read_resource", side_effect=rewrite_chunk(
                lambda chunk, selector: {**chunk, "nextChunkUri": selector})):
            with self.assertRaisesRegex(AssertionError, "duplicate chunk URI"):
                _reconstruct(self.service, envelope["result"])
        with patch.object(self.service, "read_resource", side_effect=rewrite_chunk(
                lambda chunk, _selector: {**chunk, "offset": chunk["offset"] + 1})):
            with self.assertRaises(AssertionError):
                _reconstruct(self.service, envelope["result"])
        with patch.object(self.service, "read_resource", side_effect=rewrite_chunk(
                lambda chunk, _selector: {**chunk, "nextChunkUri": None})):
            with self.assertRaises(AssertionError):
                _reconstruct(self.service, envelope["result"])
        with patch.object(self.service, "read_resource", side_effect=rewrite_chunk(
                lambda chunk, _selector: {**chunk, "data": base64.b64encode(b"z" * chunk["length"]).decode("ascii")})):
            with self.assertRaises(AssertionError):
                _reconstruct(self.service, envelope["result"])

        unknown = self.service.invoke("analyze-work", {"kind": "unregistered", "request": SAMPLE}, threading.Event())
        self.assertEqual(unknown["status"], "refused")
        self.assertFalse(unknown["result"])

    def test_sc004_schema_depth_summary_and_envelope_refusal_controls(self):
        good = self.service.invoke("analyze-work", {"kind": "aim", "request": SAMPLE}, threading.Event())
        self.assertEqual(set(good), {"schemaVersion", "operation", "status", "summary", "result",
                                     "evidenceRefs", "limits", "provenance"})
        self.assertIn("valid core result", good["summary"])
        malformed = self.service.invoke("analyze-work", {"kind": "aim"}, threading.Event())
        self.assertEqual(malformed["status"], "refused")
        deep = cursor = {}
        for _ in range(34):
            cursor["x"] = {}
            cursor = cursor["x"]
        nested = self.service.invoke("analyze-work", {"kind": "aim", "request": deep}, threading.Event())
        self.assertEqual(nested["status"], "refused")
        oversized_input = {"kind": "aim", "request": {"padding": "x" * (1024 * 1024)}}
        large = self.service.invoke("analyze-work", oversized_input, threading.Event())
        self.assertEqual(large["status"], "refused")
        self.assertIsNone(large["result"])
        oversized_output = self.service._envelope("analyze-work", "ok",
            {"payload": "x" * (8 * 1024 * 1024 + 1)}, input_value={"synthetic": True})
        self.assertEqual(oversized_output["status"], "refused")
        self.assertIsNone(oversized_output["result"])

    def test_sc005_canonical_roots_symlinks_unknown_inventory_and_analysis_only(self):
        self.assertEqual(self.service.tools, ("analyze-work", "analyze", "prepare"))
        self.assertEqual(self.service.capabilities()["mode"], "analysis-only")
        self.assertEqual(self.service.invoke("execute", {}, threading.Event())["status"], "refused")
        with self.assertRaises(ToolingError):
            self.service.read_resource("agent-braid://runs/unknown/status")
        alias = self.base / "source-alias"
        alias.symlink_to(self.config.source_root, target_is_directory=True)
        aliased = ToolingConfig(alias, self.config.result_parent)
        self.assertEqual(aliased.source_root, self.config.source_root.resolve())
        result_alias = self.base / "results-alias"
        result_alias.symlink_to(self.config.result_parent, target_is_directory=True)
        self.assertEqual(ToolingConfig(self.config.source_root, result_alias).result_parent,
                         self.config.result_parent.resolve())
        outside = self.config.source_root / "nested-result"
        outside.mkdir()
        escape = self.base / "escape"
        escape.symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ToolingError):
            ToolingConfig(self.config.source_root, escape)

    def test_sc006_exact_grant_authority_positive_absent_wrong_scope_expired_reused(self):
        from tests.test_git_runtime import GitRuntimeTests
        fixture = GitRuntimeTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        grants = self.base / "grant-store"
        config = ToolingConfig(fixture.repo, self.config.result_parent, grants, True)
        service = ToolingService(config)
        run = self.config.result_parent / "acceptance-grant-run"
        args = {"request": fixture.request, "runDirectory": str(run), "mode": "serial"}
        plan = service.invoke("prepare", args, threading.Event())["result"]
        absent = service.invoke("execute", {"plan": plan, "grantId": "00000000-0000-0000-0000-000000000001"}, threading.Event())
        self.assertIn(absent["status"], {"refused", "unknown"})
        wrong_scope = runtime_policy.issue_operator_grant(plan, grants,
            acknowledge=plan["planDigest"], action="abort")
        mismatch = service.invoke("execute", {"plan": plan, "grantId": wrong_scope["grantId"]}, threading.Event())
        self.assertIn(mismatch["status"], {"refused", "unknown"})
        expired = runtime_policy.issue_operator_grant(plan, grants,
            acknowledge=plan["planDigest"], ttl_seconds=1)
        # Expiration is deterministic without sleeping by changing the stored
        # time to an already-expired value; state/digest still match the grant.
        grant_path = grants / (expired["grantId"] + ".json")
        record = json.loads(grant_path.read_text())
        record["expiresAt"] = 1
        payload = {key: value for key, value in record.items() if key not in {"state", "grantDigest"}}
        from agent_braid import runtime_policy as policy
        record["grantDigest"] = policy._digest(payload)
        grant_path.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")
        expired_result = service.invoke("execute", {"plan": plan, "grantId": expired["grantId"]}, threading.Event())
        self.assertIn(expired_result["status"], {"refused", "unknown"})
        revoked = runtime_policy.issue_operator_grant(plan, grants, acknowledge=plan["planDigest"])
        revoked_path = grants / (revoked["grantId"] + ".json")
        revoked_record = json.loads(revoked_path.read_text())
        revoked_record["state"] = "revoked"
        revoked_path.write_text(json.dumps(revoked_record, sort_keys=True, separators=(",", ":")) + "\n")
        revoked_result = service.invoke("execute", {"plan": plan, "grantId": revoked["grantId"]}, threading.Event())
        self.assertIn(revoked_result["status"], {"refused", "unknown"})
        grant = runtime_policy.issue_operator_grant(plan, grants, acknowledge=plan["planDigest"])
        completed = service.invoke("execute", {"plan": plan, "grantId": grant["grantId"]}, threading.Event())
        self.assertEqual(completed["status"], "ok", completed["summary"])
        replay = service.invoke("execute", {"plan": plan, "grantId": grant["grantId"]}, threading.Event())
        self.assertEqual(replay["result"]["dispatch"], "not-repeated")
        self.assertEqual(fixture.snapshot(fixture.repo), fixture.before)

    def test_sc007_cancellation_stale_base_concurrency_and_recovery_observability(self):
        cancelled = threading.Event()
        cancelled.set()
        refused = self.service.invoke("analyze-work", {"kind": "aim", "request": SAMPLE}, cancelled)
        self.assertEqual(refused["status"], "refused")
        self.assertIsNone(refused["result"])
        started = [threading.Event() for _ in range(4)]
        release = threading.Event()
        counter = iter(started)
        original = self.service._analyze_work

        def hold(args):
            next(counter).set()
            release.wait(2)
            return original(args)

        with patch.object(self.service, "_analyze_work", side_effect=hold):
            workers = [threading.Thread(target=self.service.invoke,
                args=("analyze-work", {"kind": "aim", "request": SAMPLE}, threading.Event()))
                for _ in range(4)]
            for worker in workers:
                worker.start()
            self.assertTrue(all(event.wait(1) for event in started))
            second = self.service.invoke("analyze-work", {"kind": "aim", "request": SAMPLE}, threading.Event())
            self.assertEqual(second["status"], "refused")
            self.assertIn("concurrency limit", second["summary"])
            release.set()
            for worker in workers:
                worker.join(3)
                self.assertFalse(worker.is_alive())
        # Existing adapter/runtime tests cover dispatched cancellation settling,
        # stale plans, status, verify, and private-run recovery. Assert inventory
        # status remains unknown rather than presenting a prepared plan as a run.
        plan = {"planDigest": "a" * 64, "runtimeManifest": {"runDirectory": str(self.config.result_parent / "planned")}}
        run_id = self.service._register_plan(plan)
        status = json.loads(self.service.read_resource(f"agent-braid://runs/{run_id}/status")[1])["status"]
        self.assertEqual(status["status"], "unknown")
        self.assertFalse(status["runObserved"])

    def test_sc008_owned_empty_and_multi_chunk_resources_prompts_and_refusals(self):
        from agent_braid.tooling_mcp import _Artifact
        empty_id, empty_run = "ev-empty", "run-empty"
        empty_digest = hashlib.sha256(b"").hexdigest()
        self.service.artifacts[empty_id] = _Artifact(empty_id, empty_run, b"",
            "application/json", empty_digest, 0)
        empty_uri = self.service._base_uri(empty_run, empty_id)
        manifest = json.loads(self.service.read_resource(empty_uri)[1])
        self.assertIsNone(manifest["firstChunkUri"])
        self.assertEqual(manifest["sizeBytes"], 0)
        value = {"payload": "z" * (INLINE_RESULT_BYTES + 1024)}
        large = self.service._envelope("analyze-work", "ok", value, input_value={"fixture": "artifact"})
        exact = _reconstruct(self.service, large["result"])
        self.assertEqual(json.loads(exact), value)
        uri = large["result"]["uri"]
        forged_owner = uri.replace("/runs/", "/runs/not-owned/", 1)
        with self.assertRaises(ToolingError):
            self.service.read_resource(forged_owner)
        with self.assertRaises(ToolingError):
            self.service.read_resource("agent-braid://runs/nope/evidence/nope")
        from agent_braid.tooling_mcp import _PROMPT_TEXT
        self.assertEqual(set(_PROMPT_TEXT), {"agent-braid-analyze", "agent-braid-plan", "agent-braid-evidence"})
        self.assertIn("do not infer execution authority", _PROMPT_TEXT["agent-braid-analyze"].lower())
        self.assertIn("never request or create a grant", _PROMPT_TEXT["agent-braid-plan"].lower())
        self.assertFalse(any(name in self.service.tools for name in ("grant", "read-file", "execute", "recover")))


class MpcSdkTransportAcceptance(unittest.IsolatedAsyncioTestCase):
    """Exercise large evidence and Git analysis through real local SDK stdio clients."""

    SERVER_BOOTSTRAP = (
        "import asyncio,sys; from pathlib import Path; "
        "from agent_braid.tooling_mcp import ToolingConfig,serve_stdio; "
        "source=Path(sys.argv[1]); results=Path(sys.argv[2]); "
        "roots=tuple(Path(p) for p in sys.argv[3:]); "
        "asyncio.run(serve_stdio(ToolingConfig(source,results,worktree_roots=roots)))"
    )

    async def asyncSetUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addAsyncCleanup(asyncio.to_thread, self.temp.cleanup)
        self.base = Path(self.temp.name)

    def _trace(self, name: str, content: bytes) -> str | None:
        trace_root = os.environ.get("M45_CONTROL_TRACE_DIR")
        if not trace_root:
            return None
        target = Path(trace_root) / name
        if target.parent != Path(trace_root) or target.exists():
            raise AssertionError("trace path is unsafe or already exists")
        target.write_bytes(content)
        os.chmod(target, 0o600)
        return target.name

    def _trace_json(self, name: str, value: Any) -> str | None:
        return self._trace(name, (json.dumps(value, ensure_ascii=False,
                                             sort_keys=True, indent=2) + "\n").encode("utf-8"))

    async def _client(self, mode: str, source: Path, *, roots: tuple[Path, ...] = ()):
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters
        results = self.base / f"results-{mode}-{len(list(self.base.iterdir()))}"
        results.mkdir()
        params = StdioServerParameters(command=sys.executable,
            args=["-c", self.SERVER_BOOTSTRAP, str(source), str(results),
                  *(str(root) for root in roots)], cwd=str(ROOT))
        return Client(params, mode=mode)

    async def _reconstruct(self, client, reference: dict, *, trace_prefix: str | None = None) -> bytes:
        result = bytearray()
        first = await client.read_resource(reference["uri"])
        self.assertEqual(len(first.contents), 1)
        manifest = json.loads(first.contents[0].text)
        chain_trace = {"manifestUri": reference["uri"], "manifestSha256": hashlib.sha256(
            first.contents[0].text.encode("utf-8")).hexdigest(), "chunks": []}
        if trace_prefix:
            self._trace(f"{trace_prefix}-manifest.json", first.contents[0].text.encode("utf-8"))
        self.assertEqual(manifest["artifactId"], reference["artifactId"])
        self.assertEqual(manifest["sha256"], reference["sha256"])
        self.assertEqual(manifest["sizeBytes"], reference["sizeBytes"])
        self.assertEqual(manifest["chunkSizeBytes"], CHUNK_BYTES)
        uri = manifest["firstChunkUri"]
        offset = 0
        seen = set()
        while uri is not None:
            self.assertNotIn(uri, seen, "chunk chain must not repeat a resource URI")
            seen.add(uri)
            read = await client.read_resource(uri)
            chunk = json.loads(read.contents[0].text)
            raw = base64.b64decode(chunk["data"], validate=True)
            self.assertEqual(chunk["artifactId"], manifest["artifactId"])
            self.assertEqual(chunk["artifactSha256"], manifest["sha256"])
            self.assertEqual(chunk["offset"], offset)
            self.assertEqual(chunk["length"], len(raw))
            self.assertEqual(chunk["totalBytes"], manifest["sizeBytes"])
            self.assertEqual(chunk["chunkSha256"], hashlib.sha256(raw).hexdigest())
            self.assertGreater(len(raw), 0)
            self.assertLessEqual(len(raw), CHUNK_BYTES)
            response_bytes = read.contents[0].text.encode("utf-8")
            response_name = (self._trace(f"{trace_prefix}-chunk-{len(chain_trace['chunks']):03d}.json",
                                          response_bytes) if trace_prefix else None)
            chain_trace["chunks"].append({"uri": uri, "offset": offset, "length": len(raw),
                "chunkSha256": chunk["chunkSha256"], "responseSha256": hashlib.sha256(response_bytes).hexdigest(),
                "responseFile": response_name})
            result.extend(raw)
            offset += len(raw)
            uri = chunk["nextChunkUri"]
        self.assertEqual(offset, manifest["sizeBytes"])
        self.assertEqual(hashlib.sha256(result).hexdigest(), manifest["sha256"])
        bytes(result).decode("utf-8")
        chain_trace["reconstructedSha256"] = hashlib.sha256(result).hexdigest()
        chain_trace["reconstructedSizeBytes"] = len(result)
        if trace_prefix:
            self._trace(f"{trace_prefix}-reconstructed.bin", bytes(result))
            self._trace_json(f"{trace_prefix}-chain.json", chain_trace)
        return bytes(result)

    async def _reconstruct_uri(self, client, uri: str, *, artifact_id: str,
                               digest: str, size: int, trace_prefix: str | None = None) -> bytes:
        return await self._reconstruct(client, {"uri": uri, "artifactId": artifact_id,
                                                "sha256": digest, "sizeBytes": size},
                                       trace_prefix=trace_prefix)

    def _large_aim(self) -> dict:
        large = deepcopy(SAMPLE)
        template = large["operations"][0]
        resources = [f"repo://acceptance/λ/{i:02d}/{'r' * 361}" for i in range(12)]
        large["operations"] = []
        for index in range(32):
            operation = deepcopy(template)
            operation["instanceId"] = f"stdio-{index:02d}"
            operation["attemptId"] = f"stdio-{index:02d}-attempt"
            operation["effects"]["declared"] = [
                {"kind": "write", "resource": resource} for resource in resources]
            large["operations"].append(operation)
        return large

    async def test_sc003_sdk_stdio_large_aim_chunk_chain_and_cli_parity_auto_legacy(self):
        large = self._large_aim()
        source = self.base / "source"
        source.mkdir()
        request_path = self.base / "large-aim.json"
        request_path.write_text(json.dumps(large), encoding="utf-8")
        self._trace("sc003-large-aim-input.json", request_path.read_bytes())
        self.assertLess(request_path.stat().st_size, 1024 * 1024)
        cli = subprocess.run([sys.executable, "-m", "agent_braid.cli", "analyze",
                              str(request_path)], cwd=ROOT, capture_output=True,
                             text=True, check=True)
        expected_report = json.loads(cli.stdout)
        self._trace("sc003-large-aim-cli-report.json", cli.stdout.encode("utf-8"))
        saw_multi_chunk_result = False
        for mode, protocol in (("auto", "2026-07-28"), ("legacy", "2025-11-25")):
            async with await self._client(mode, source) as client:
                self.assertEqual(client.protocol_version, protocol)
                response = await client.call_tool("analyze-work", {"kind": "aim", "request": large})
                envelope = response.structured_content
                self._trace(f"sc003-large-aim-{mode}-tool-envelope.json",
                            response.content[0].text.encode("utf-8"))
                self.assertEqual(envelope["status"], "ok", envelope["summary"])
                self.assertEqual(json.loads(response.content[0].text), envelope)
                reference = envelope["result"]
                self.assertEqual(reference["type"], "evidence-artifact-reference")
                self.assertGreater(reference["sizeBytes"], INLINE_RESULT_BYTES)
                complete = await self._reconstruct(client, reference,
                                                   trace_prefix=f"sc003-large-aim-{mode}")
                self.assertGreater(len(complete), CHUNK_BYTES * 2)
                value = json.loads(complete)
                self.assertEqual(value["report"], expected_report)
                self.assertFalse(value["provenance"]["executionAuthorization"])
                saw_multi_chunk_result = True
        self.assertTrue(saw_multi_chunk_result)

    async def test_sc003_sdk_stdio_git_worktree_success_and_unsupported_refusal(self):
        from tests.test_git_adapter import GitAdapterTests
        fixture = GitAdapterTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        source = fixture.repo
        request = fixture.request(left={"kind": "worktree", "path": str(fixture.repo)})
        input_path = self.base / "git-request.json"
        input_path.write_text(json.dumps(request), encoding="utf-8")
        self._trace("sc003-git-worktree-input.json", input_path.read_bytes())
        provenance = self.base / "git-provenance.json"
        cli = subprocess.run([sys.executable, "-m", "agent_braid.cli", "analyze-git",
                              str(input_path), "--provenance-output", str(provenance)],
                             cwd=ROOT, capture_output=True, text=True, check=True)
        expected_report = json.loads(cli.stdout)
        expected_provenance = json.loads(provenance.read_text(encoding="utf-8"))
        commits = {}
        for name in ("HEAD", request.get("baseRevision")):
            if name:
                result = subprocess.run(["git", "rev-parse", str(name)], cwd=source,
                                        capture_output=True, text=True, check=True)
                commits[str(name)] = result.stdout.strip()
        self._trace_json("sc003-git-worktree-input-commits.json", commits)
        self._trace("sc003-git-cli-report.json", cli.stdout.encode("utf-8"))
        self._trace_json("sc003-git-cli-provenance.json", expected_provenance)
        outside = deepcopy(request)
        outside["repository"] = str(self.base)
        for mode, protocol in (("auto", "2026-07-28"), ("legacy", "2025-11-25")):
            async with await self._client(mode, source, roots=(fixture.repo,)) as client:
                self.assertEqual(client.protocol_version, protocol)
                good = await client.call_tool("analyze-work", {"kind": "git", "request": request})
                self._trace(f"sc003-git-{mode}-valid-envelope.json",
                            good.content[0].text.encode("utf-8"))
                self.assertEqual(good.structured_content["status"], "ok",
                                 good.structured_content["summary"])
                self.assertEqual(good.structured_content["result"]["report"], expected_report)
                self.assertEqual(good.structured_content["result"]["provenance"], expected_provenance)
                invalid_kind = await client.call_tool("analyze-work", {
                    "kind": "unsupported", "request": request})
                self._trace(f"sc003-git-{mode}-unknown-envelope.json",
                            invalid_kind.content[0].text.encode("utf-8"))
                self.assertEqual(invalid_kind.structured_content["status"], "refused")
                outside_result = await client.call_tool("analyze-work", {
                    "kind": "git", "request": outside})
                self._trace(f"sc003-git-{mode}-out-of-root-envelope.json",
                            outside_result.content[0].text.encode("utf-8"))
                self.assertEqual(outside_result.structured_content["status"], "refused")
                self.assertFalse(outside_result.structured_content["result"])

    async def test_sc008_sdk_stdio_owned_empty_and_raw_unicode_manifest_chain(self):
        # This purpose-built local fixture seeds only artifacts in the
        # ToolingService-owned inventory, then serves them with the pinned SDK
        # over stdio. It is an artifact/resource transport control, not a claim
        # that an installed native host creates zero-byte artifacts.
        script = r'''import asyncio, hashlib, sys
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
from agent_braid.tooling_mcp import ToolingConfig, ToolingService, _Artifact, _read_resource_bounded

source, results = Path(sys.argv[1]), Path(sys.argv[2])
service = ToolingService(ToolingConfig(source, results))
run_id = "run-stdio-owned-fixture"
raw = b'{"payload":"' + b'x' * (128 * 1024 - len(b'{"payload":"') - 1) + "界".encode() + "界".encode() * 100_000 + b'"}'
artifacts = {"ev-empty-fixture": b"", "ev-unicode-fixture": raw}
for artifact_id, content in artifacts.items():
    digest = hashlib.sha256(content).hexdigest()
    service.artifacts[artifact_id] = _Artifact(artifact_id, run_id, content, "application/json", digest, len(content))
async def list_resources(_ctx, _params):
    return types.ListResourcesResult(resources=[types.Resource(name=aid, uri=service._base_uri(run_id, aid), mimeType="application/json") for aid in artifacts])
async def read_resource(_ctx, params):
    mime, text = await _read_resource_bounded(service, str(params.uri))
    return types.ReadResourceResult(contents=[types.TextResourceContents(uri=str(params.uri), mimeType=mime, text=text)])
server = Server("mcp-owned-artifact-fixture", version="1", on_list_resources=list_resources, on_read_resource=read_resource)
async def main():
    async with stdio_server() as (reader, writer):
        await server.run(reader, writer, server.create_initialization_options())
asyncio.run(main())
'''
        source = self.base / "artifact-source"
        results = self.base / "artifact-results"
        source.mkdir()
        results.mkdir()
        # StdioServerParameters cannot pass source/results to the common
        # bootstrap while using this custom inventory server, so use a small
        # custom parameter construction with deterministic local fixture paths.
        from mcp import Client
        from mcp.client.stdio import StdioServerParameters
        for mode, protocol in (("auto", "2026-07-28"), ("legacy", "2025-11-25")):
            params = StdioServerParameters(command=sys.executable,
                args=["-c", script, str(source), str(results)], cwd=str(ROOT))
            async with Client(params, mode=mode) as client:
                self.assertEqual(client.protocol_version, protocol)
                listed = await client.list_resources()
                resources = {item.name: item.uri for item in listed.resources}
                empty_uri = resources["ev-empty-fixture"]
                empty_read = await client.read_resource(empty_uri)
                self._trace(f"sc008-empty-{mode}-manifest.json",
                            empty_read.contents[0].text.encode("utf-8"))
                empty_manifest = json.loads(empty_read.contents[0].text)
                self.assertEqual(empty_manifest["sizeBytes"], 0)
                self.assertEqual(empty_manifest["sha256"], hashlib.sha256(b"").hexdigest())
                self.assertIsNone(empty_manifest["firstChunkUri"])
                unicode_uri = resources["ev-unicode-fixture"]
                first = await client.read_resource(unicode_uri)
                manifest = json.loads(first.contents[0].text)
                reconstructed = await self._reconstruct_uri(client, unicode_uri,
                    artifact_id=manifest["artifactId"], digest=manifest["sha256"],
                    size=manifest["sizeBytes"], trace_prefix=f"sc008-unicode-{mode}")
                self.assertEqual(hashlib.sha256(reconstructed).hexdigest(), manifest["sha256"])
                self.assertGreater(len(reconstructed), CHUNK_BYTES)
                self.assertEqual(reconstructed[CHUNK_BYTES - 1:CHUNK_BYTES + 2], "界".encode())
                json.loads(reconstructed.decode("utf-8"))


if __name__ == "__main__":
    unittest.main()
