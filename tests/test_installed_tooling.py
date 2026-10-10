# SPDX-License-Identifier: AGPL-3.0-only
"""Safety checks for the opt-in installed-package verifier."""
from __future__ import annotations

import contextlib
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import sys
import stat
import tempfile
import types
import unittest
from unittest.mock import patch
import zipfile


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "verify_installed_tooling.py"
SPEC = importlib.util.spec_from_file_location("verify_installed_tooling", SCRIPT)
verifier = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(verifier)


def write_wheel(directory: Path, name: str, version: str, requires: tuple[str, ...] = ()) -> tuple[str, str]:
    filename = f"{name.replace('-', '_')}-{version}-py3-none-any.whl"
    metadata = "\n".join([
        "Metadata-Version: 2.4", f"Name: {name}", f"Version: {version}", "License: MIT",
        *[f"Requires-Dist: {item}" for item in requires], "", "",
    ])
    with zipfile.ZipFile(directory / filename, "w") as archive:
        archive.writestr(f"{name.replace('-', '_')}-{version}.dist-info/METADATA", metadata)
    digest = hashlib.sha256((directory / filename).read_bytes()).hexdigest()
    return filename, digest


def closure_fixture(root: Path, *, omit_extra_evaluation: bool = False) -> tuple[Path, Path]:
    wheelhouse = root / "wheelhouse"
    wheelhouse.mkdir()
    requirements = {
        "mcp": ("2.3.0", ("pyjwt[crypto]>=2.0; python_version >= '3.8'",)),
        "pyjwt": ("2.15.1", ("cryptography>=3.4; extra == 'crypto'",)),
        "cryptography": ("50.0.2", ()),
    }
    package_rows = []
    filenames = {}
    for name, (version, reqs) in requirements.items():
        display = "PyJWT" if name == "pyjwt" else name
        filename, digest = write_wheel(wheelhouse, display, version, reqs)
        filenames[name] = filename
        package_rows.append({
            "name": display, "canonicalName": name, "version": version,
            "wheel": filename, "wheelSha256": digest, "licenseExpression": None,
            "licenseMetadata": "MIT", "requiresDist": list(reqs),
            "requestedExtras": ["crypto"] if name == "pyjwt" else [],
        })
    lock_path = root / "closure.lock.txt"
    lock_path.write_text("mcp==2.3.0 --hash=sha256:" + "a" * 64 + "\n")
    lock_digest = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    marker_req = requirements["mcp"][1][0]
    extra_req = requirements["pyjwt"][1][0]
    evaluations = {
        "mcp|": [{
            "requirement": marker_req, "markerContext": None, "markerMatched": True,
            "selectedPackage": "pyjwt", "requestedExtras": ["crypto"],
        }],
        "pyjwt|": [{
            "requirement": extra_req, "markerContext": None, "markerMatched": False,
            "selectedPackage": None, "requestedExtras": [],
        }],
        "pyjwt|crypto": [{
            "requirement": extra_req, "markerContext": "crypto", "markerMatched": True,
            "selectedPackage": "cryptography", "requestedExtras": [],
        }],
        "cryptography|": [],
    }
    if omit_extra_evaluation:
        del evaluations["pyjwt|crypto"]
    manifest = {
        "schema": "agent-braid-mcp-closure/v1",
        "target": {"name": "linux-amd64", "python": "3.13.11", "implementation": "CPython"},
        "directRequirements": ["mcp==2.3.0"],
        "markerEnvironment": {"python_full_version": "3.13.11"},
        "lockFile": {"path": lock_path.name, "sha256": lock_digest},
        "packages": package_rows,
        "dependencyEdges": [
            {"from": "mcp", "fromExtra": None, "to": "pyjwt", "requirement": marker_req,
             "requestedExtras": ["crypto"]},
            {"from": "pyjwt", "fromExtra": "crypto", "to": "cryptography", "requirement": extra_req,
             "requestedExtras": []},
        ],
        "requirementEvaluations": evaluations,
    }
    manifest_path = root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, sort_keys=True))
    return manifest_path, wheelhouse


class InstalledVerifierSafetyTests(unittest.TestCase):
    def test_generated_child_sources_compile_and_sdk_success_records_both_modes(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            config = root / "relay-config.json"
            config.write_text(json.dumps({"status": "unset", "traces": {}}))
            request = {"analysisInputVersion": "fixture", "operations": []}
            code = verifier._sdk_probe_code(root / "relay.py", config, root, root,
                root, {"PATH": "/bin"}, request)
            compile(verifier._relay_source(), "relay.py", "exec")
            compile(verifier._installed_audit_code({}), "audit.py", "exec")
            compile(code, "sdk-probe.py", "exec")

            report = {"status": "synthetic-ok", "count": 2}
            envelope = {"status": "ok", "result": {"report": report,
                "provenance": {"executionAuthorization": False}}}

            class FakeClient:
                def __init__(self, params, mode):
                    self.params = params
                    self.mode = mode
                    self.protocol_version = "2026-07-28" if mode == "auto" else "2025-11-25"

                async def __aenter__(self):
                    return self

                async def __aexit__(self, *_args):
                    config_data = json.loads(Path(self.params.args[2]).read_text())
                    status_path = Path(config_data["status"])
                    status_path.write_text(json.dumps({"returnCode": 0, "interrupted": False,
                        "forcedTermination": None, "reaped": True, "trace": {}}))

                async def list_tools(self):
                    return types.SimpleNamespace(tools=[types.SimpleNamespace(name=name)
                        for name in ("analyze", "analyze-work", "prepare")])

                async def call_tool(self, _name, arguments):
                    if arguments["request"] == {}:
                        return types.SimpleNamespace(structured_content={"status": "refused"}, isError=True)
                    return types.SimpleNamespace(structured_content=envelope,
                        content=[types.SimpleNamespace(text=json.dumps(envelope))], isError=False)

                async def list_resources(self):
                    return types.SimpleNamespace(resources=[types.SimpleNamespace(uri="agent-braid://capabilities")])

                async def read_resource(self, _uri):
                    return types.SimpleNamespace(contents=[types.SimpleNamespace(text="analysis-only")])

                async def list_prompts(self):
                    return types.SimpleNamespace(prompts=[types.SimpleNamespace(name=name) for name in
                        ("agent-braid-analyze", "agent-braid-evidence", "agent-braid-plan")])

                async def get_prompt(self, _name):
                    return types.SimpleNamespace(messages=[types.SimpleNamespace(content=
                        types.SimpleNamespace(text="SHA-256"))])

            class FakeParameters:
                def __init__(self, **kwargs):
                    self.__dict__.update(kwargs)

            mcp = types.ModuleType("mcp")
            mcp.Client = FakeClient
            client_pkg = types.ModuleType("mcp.client")
            stdio = types.ModuleType("mcp.client.stdio")
            stdio.StdioServerParameters = FakeParameters
            output = io.StringIO()
            with patch.dict(sys.modules, {"mcp": mcp, "mcp.client": client_pkg,
                                          "mcp.client.stdio": stdio}), contextlib.redirect_stdout(output):
                exec(compile(code, "sdk-probe.py", "exec"), {"__name__": "sdk_probe_test"})
            result = json.loads(output.getvalue())
            sessions = result["sessions"]
            self.assertEqual(["auto", "legacy"], [row["mode"] for row in sessions])
            expected = verifier.canonical_json_sha256(report)
            self.assertEqual([expected, expected], [row["aimReportSha256"] for row in sessions])

    def test_cli_report_digest_is_canonical_across_json_key_order(self):
        left = {"report": {"status": "ok", "count": 2}}
        right = {"report": {"count": 2, "status": "ok"}}
        self.assertEqual(verifier.canonical_json_sha256(left),
                         verifier.canonical_json_sha256(right))
        self.assertNotEqual(verifier.canonical_json_sha256(left),
                            verifier.canonical_json_sha256({"report": {"status": "ok", "count": 3}}))

    def test_command_raw_streams_and_blocked_partial_receipt_are_durable(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary)
            receipt = {"commands": [], "status": "running"}
            result = verifier.CommandResult(7, False, False, b"private synthetic stdout", b"synthetic stderr")
            verifier.record_command(receipt, work, "aim-analysis-cli-core", result)
            row = receipt["commands"][0]
            stdout_path = work / row["rawStdoutPath"]
            stderr_path = work / row["rawStderrPath"]
            self.assertEqual(b"private synthetic stdout", stdout_path.read_bytes())
            self.assertEqual(b"synthetic stderr", stderr_path.read_bytes())
            self.assertEqual(0o600, stat.S_IMODE(stdout_path.stat().st_mode))
            verifier.mark_blocked_receipt(work, "synthetic failure")
            persisted = json.loads((work / "receipt.json").read_text())
            self.assertEqual("blocked", persisted["status"])
            self.assertEqual("synthetic failure", persisted["blockedReason"])
            self.assertEqual(row, persisted["commands"][0])

    def test_actual_nonzero_child_exit_and_output_digest_are_recorded(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = {"PATH": str(Path(sys.executable).parent), "HOME": temporary}
            result = verifier.run_bounded(
                [sys.executable, "-I", "-c", "print('safe'); raise SystemExit(7)"],
                cwd=Path(temporary), env=env, timeout=5)
        self.assertEqual(7, result.returncode)
        self.assertFalse(result.timed_out)
        self.assertEqual(b"safe\n", result.stdout)
        self.assertEqual(hashlib.sha256(result.stdout).hexdigest(),
                         result.receipt()["stdoutSha256"])
        self.assertEqual([sys.executable, "-I", "-c", "print('safe'); raise SystemExit(7)"],
                         result.receipt()["argv"])
        self.assertLessEqual(result.receipt()["elapsedSeconds"], result.receipt()["timeoutSeconds"] + 2)
        self.assertEqual(verifier.MAX_OUTPUT_BYTES, result.receipt()["maxOutputBytes"])

    def test_timeout_reaps_the_owned_process_group(self):
        with tempfile.TemporaryDirectory() as temporary:
            env = {"PATH": str(Path(sys.executable).parent), "HOME": temporary}
            result = verifier.run_bounded(
                [sys.executable, "-I", "-c", "import time; time.sleep(30)"],
                cwd=Path(temporary), env=env, timeout=0.2)
        self.assertTrue(result.timed_out)
        self.assertIsNotNone(result.returncode)
        self.assertNotEqual(0, result.returncode)

    def test_output_limit_is_explicit_and_does_not_retain_unbounded_data(self):
        with tempfile.TemporaryDirectory() as temporary, patch.object(verifier, "MAX_OUTPUT_BYTES", 64):
            env = {"PATH": str(Path(sys.executable).parent), "HOME": temporary}
            result = verifier.run_bounded(
                [sys.executable, "-I", "-c", "import sys; sys.stdout.write('x'*100000)"],
                cwd=Path(temporary), env=env, timeout=5)
        self.assertTrue(result.output_limited)
        self.assertIsNotNone(result.returncode)
        self.assertEqual(64, len(result.stdout))
        self.assertGreater(result.receipt()["stdoutObservedBytes"], 64)
        self.assertFalse(result.receipt()["outputCaptureComplete"])

    def test_target_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest, wheelhouse = closure_fixture(Path(temporary))
            with self.assertRaisesRegex(verifier.ProbeError, "target mismatch"):
                verifier.verify_lock_and_wheelhouse(manifest, wheelhouse, "macos-arm64")

    def test_wheel_digest_mismatch_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest, wheelhouse = closure_fixture(Path(temporary))
            verifier.verify_lock_and_wheelhouse(manifest, wheelhouse, "linux-amd64")
            victim = next(wheelhouse.glob("*.whl"))
            victim.write_bytes(victim.read_bytes() + b"x")
            with self.assertRaisesRegex(verifier.ProbeError, "wheelhouse digest"):
                verifier.verify_lock_and_wheelhouse(manifest, wheelhouse, "linux-amd64")

    def test_nested_requested_extra_must_have_all_marker_contexts_resolved(self):
        with tempfile.TemporaryDirectory() as temporary:
            manifest, wheelhouse = closure_fixture(Path(temporary), omit_extra_evaluation=True)
            with self.assertRaisesRegex(verifier.ProbeError, "conditional requirement evaluations"):
                verifier.verify_lock_and_wheelhouse(manifest, wheelhouse, "linux-amd64")

    def test_preflight_mode_never_creates_a_workdir_or_installs(self):
        with tempfile.TemporaryDirectory() as temporary:
            work = Path(temporary) / "must-not-exist"
            output = io.StringIO()
            args = [
                "--target", "linux-amd64", "--manifest", "missing.json",
                "--wheelhouse", "missing-wheelhouse", "--candidate-wheel", "missing.whl",
                "--candidate-sha256", "0" * 64, "--work-dir", str(work),
            ]
            with contextlib.redirect_stdout(output):
                exit_code = verifier.main(args)
            self.assertEqual(2, exit_code)
            self.assertFalse(work.exists())
            self.assertIn("refusing install", output.getvalue())


if __name__ == "__main__":
    unittest.main()

