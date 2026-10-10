# SPDX-License-Identifier: AGPL-3.0-only
"""Static fail-closed tests for the prepared Linux installed-package recipe."""
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "docs/tooling/linux-reproduction/run.py"
SPEC = importlib.util.spec_from_file_location("linux_reproduction_recipe", SCRIPT)
recipe = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
sys.modules[SPEC.name] = recipe
SPEC.loader.exec_module(recipe)


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class LinuxToolingRecipeTests(unittest.TestCase):
    def _bundle(self, directory: Path):
        root = directory / "input"
        repro = root / "reproducibility"
        wheels = root / "wheelhouse"
        repro.mkdir(parents=True)
        wheels.mkdir()
        candidate = b"frozen-candidate"
        probe = b"frozen-probe"
        package = b"locked-mcp-wheel"
        lock = b"mcp==2.3.0 --hash=sha256:locked\n"
        (root / recipe.CANDIDATE_FILENAME).write_bytes(candidate)
        (root / "verify_installed_tooling.py").write_bytes(probe)
        (repro / "mcp-2.3.0-cp313-linux-amd64.lock.txt").write_bytes(lock)
        (wheels / "mcp-2.3.0-py3-none-any.whl").write_bytes(package)
        manifest = {
            "schema": "agent-braid-mcp-closure/v1",
            "target": {"name": "linux-amd64", "platformSystem": "Linux",
                       "platformMachine": "x86_64", "python": "3.13.11",
                       "implementation": "CPython"},
            "directRequirements": ["mcp==2.3.0"],
            "lockFile": {"path": "mcp-2.3.0-cp313-linux-amd64.lock.txt",
                         "sha256": digest(lock)},
            "packages": [{"wheel": "mcp-2.3.0-py3-none-any.whl",
                          "wheelSha256": digest(package)}],
        }
        raw_manifest = json.dumps(manifest, sort_keys=True).encode()
        manifest_path = repro / "mcp-2.3.0-cp313-linux-amd64.manifest.json"
        manifest_path.write_bytes(raw_manifest)
        wheelhouse_hash = hashlib.sha256(
            f"mcp-2.3.0-py3-none-any.whl:{digest(package)}".encode("ascii")
        ).hexdigest()
        expected = {
            "manifest_sha256": digest(raw_manifest),
            "candidate_sha256": digest(candidate),
            "probe_sha256": digest(probe),
            "wheelhouse_sha256": wheelhouse_hash,
        }
        return root, wheels, expected

    def test_bundle_validator_accepts_exact_target_and_rejects_artifact_drift(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, _wheels, expected = self._bundle(Path(temporary))
            checked = recipe.validate_manifest_bundle(root, **expected)
            self.assertEqual(recipe.IMAGE, checked["image"])
            (root / recipe.CANDIDATE_FILENAME).write_bytes(b"changed")
            with self.assertRaisesRegex(recipe.Refused, "candidate wheel digest mismatch"):
                recipe.validate_manifest_bundle(root, **expected)

    def test_bundle_validator_rejects_wrong_target_and_wheelhouse_roster(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, wheelhouse, expected = self._bundle(Path(temporary))
            manifest_path = root / "reproducibility/mcp-2.3.0-cp313-linux-amd64.manifest.json"
            manifest = json.loads(manifest_path.read_text())
            manifest["target"]["platformMachine"] = "arm64"
            manifest_path.write_text(json.dumps(manifest, sort_keys=True))
            expected["manifest_sha256"] = digest(manifest_path.read_bytes())
            with self.assertRaisesRegex(recipe.Refused, "dependency manifest target mismatch"):
                recipe.validate_manifest_bundle(root, **expected)

            root, wheelhouse, expected = self._bundle(Path(temporary) / "second")
            (wheelhouse / "unlocked.whl").write_bytes(b"unexpected")
            with self.assertRaisesRegex(recipe.Refused, "wheelhouse roster mismatch"):
                recipe.validate_manifest_bundle(root, **expected)

    def test_native_host_guard_rejects_emulation_and_wrong_os(self):
        for system, machine in (("Darwin", "arm64"), ("Linux", "aarch64"), ("Windows", "AMD64")):
            with self.subTest(system=system, machine=machine):
                with self.assertRaisesRegex(recipe.Refused, "Linux x86_64"):
                    recipe.require_native_target(system, machine)
        recipe.require_native_target("Linux", "x86_64")

    def test_arm64_launch_requires_explicit_emulation_and_retains_target_identity(self):
        for system, machine in (("Darwin", "arm64"), ("Linux", "aarch64")):
            with self.subTest(system=system):
                with self.assertRaises(recipe.Refused):
                    recipe.launch_host_identity(system, machine, False)
                identity = recipe.launch_host_identity(system, machine, True)
                self.assertEqual("arm64-launch-host-amd64-container", identity["mode"])
                self.assertEqual(machine, identity["machine"])
        for system, machine in (("Windows", "ARM64"), ("Linux", "riscv64")):
            with self.assertRaises(recipe.Refused):
                recipe.launch_host_identity(system, machine, True)
        self.assertEqual("native-launch-host", recipe.launch_host_identity("Linux", "x86_64", False)["mode"])

    def test_daemon_identity_refuses_unknown_platform_and_excludes_private_fields(self):
        data = {"OSType": "linux", "Architecture": "aarch64", "ServerVersion": "fixture", "Name": "private-host"}
        with patch.dict(recipe.os.environ, {"DOCKER_HOST": "unix:///fixture", "DOCKER_CONTEXT": ""}), patch.object(recipe.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout=json.dumps(data))):
            actual = recipe.inspect_daemon_identity("docker")
            self.assertNotIn("Name", actual)
            self.assertEqual("unix", actual["endpointScheme"])
            self.assertEqual("amd64-on-arm64-daemon-emulation", actual["containerExecutionMode"])
            self.assertEqual("aarch64", actual["Architecture"])
        with patch.dict(recipe.os.environ, {"DOCKER_HOST": "tcp://remote-fixture:2376", "DOCKER_CONTEXT": ""}), patch.object(recipe.subprocess, "run") as forbidden:
            with self.assertRaisesRegex(recipe.Refused, "local Unix"):
                recipe.inspect_daemon_identity("docker")
            forbidden.assert_not_called()
        for bad in ({"OSType": "windows", "Architecture": "amd64"}, {"OSType": "linux", "Architecture": "unknown"}, []):
            with patch.dict(recipe.os.environ, {"DOCKER_HOST": "unix:///fixture", "DOCKER_CONTEXT": ""}), patch.object(recipe.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout=json.dumps(bad))):
                with self.assertRaises(recipe.Refused):
                    recipe.inspect_daemon_identity("docker")

    def test_main_remote_endpoint_refuses_before_any_docker_invocation(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, _wheels, expected = self._bundle(Path(temporary))
            args = ["--input-dir", str(root), "--output-dir", str(Path(temporary)/"output"),
                    "--candidate-sha256", expected["candidate_sha256"],
                    "--probe-sha256", expected["probe_sha256"],
                    "--manifest-sha256", expected["manifest_sha256"],
                    "--wheelhouse-sha256", expected["wheelhouse_sha256"],
                    "--launcher-sha256", recipe.sha256_file(SCRIPT), "--execute"]
            with patch.dict(recipe.os.environ, {"DOCKER_HOST": "tcp://remote-fixture:2376", "DOCKER_CONTEXT": ""}), \
                 patch.object(recipe.platform, "system", return_value="Linux"), \
                 patch.object(recipe.platform, "machine", return_value="x86_64"), \
                 patch.object(recipe.shutil, "which", return_value="/usr/bin/docker"), \
                 patch.object(recipe.subprocess, "run") as forbidden, redirect_stdout(io.StringIO()):
                self.assertEqual(2, recipe.main(args))
            forbidden.assert_not_called()

    def test_context_override_cannot_hide_remote_endpoint_behind_unix_host_env(self):
        with patch.dict(recipe.os.environ, {"DOCKER_HOST": "unix:///fixture", "DOCKER_CONTEXT": "remote-fixture"}), \
             patch.object(recipe.subprocess, "run", return_value=subprocess.CompletedProcess([], 0, stdout='"ssh://remote-fixture"')) as calls:
            with self.assertRaisesRegex(recipe.Refused, "local Unix"):
                recipe.inspect_daemon_identity("docker")
            calls.assert_called_once_with(["docker", "context", "inspect", "remote-fixture", "--format", "{{json .Endpoints.docker.Host}}"], check=False, capture_output=True, text=True, timeout=15)

    def test_local_image_guard_requires_exact_amd64_digest(self):
        good = [{"Os": "linux", "Architecture": "amd64",
                 "RepoDigests": ["python@" + recipe.IMAGE_DIGEST]}]
        recipe.validate_image_metadata(json.dumps(good))
        for bad in (
            [{"Os": "linux", "Architecture": "arm64",
              "RepoDigests": ["python@" + recipe.IMAGE_DIGEST]}],
            [{"Os": "linux", "Architecture": "amd64",
              "RepoDigests": ["python@sha256:" + "0" * 64]}],
        ):
            with self.subTest(bad=bad):
                with self.assertRaises(recipe.Refused):
                    recipe.validate_image_metadata(json.dumps(bad))

    def test_local_image_inspect_json_array_is_passed_to_real_digest_validator(self):
        inspected = [{"Os": "linux", "Architecture": "amd64",
                      "RepoDigests": ["docker.io/library/python@" + recipe.IMAGE_DIGEST]}]
        result = subprocess.CompletedProcess([], 0, stdout=json.dumps(inspected), stderr="")
        with patch.object(recipe.subprocess, "run", return_value=result) as runner:
            recipe._inspect_local_image("/usr/bin/docker")
        command = runner.call_args.args[0]
        self.assertEqual(["/usr/bin/docker", "image", "inspect", recipe.IMAGE], command)
        self.assertNotIn("--format", command)

        wrong = subprocess.CompletedProcess([], 0, stdout=json.dumps([{
            "Os": "linux", "Architecture": "amd64",
            "RepoDigests": ["python@sha256:" + "0" * 64],
        }]), stderr="")
        with patch.object(recipe.subprocess, "run", return_value=wrong):
            with self.assertRaisesRegex(recipe.Refused, "local image digest mismatch"):
                recipe._inspect_local_image("/usr/bin/docker")

    def test_container_command_is_offline_pinned_and_read_only_for_inputs(self):
        argv = recipe.docker_argv("/usr/bin/docker", recipe.IMAGE, Path("/frozen"),
                                  Path("/evidence"), "a" * 64, "owned-probe")
        self.assertIn("--pull=never", argv)
        self.assertIn("--platform=linux/amd64", argv)
        self.assertIn("--network=none", argv)
        self.assertIn("--read-only", argv)
        self.assertIn("--execute-installed", argv)
        self.assertEqual("/inputs/" + recipe.CANDIDATE_FILENAME,
                         argv[argv.index("--candidate-wheel") + 1])
        self.assertEqual("agent_braid-0.1.0a1-py3-none-any.whl", recipe.CANDIDATE_FILENAME)
        self.assertIn("type=bind,src=/frozen,dst=/inputs,readonly", argv)
        self.assertIn("type=bind,src=/evidence,dst=/evidence", argv)
        self.assertIn(recipe.IMAGE, argv)
        self.assertFalse(any(value == "build" or value == "pull" for value in argv))

    def test_zero_exit_invalid_json_keeps_private_launcher_trace_and_diagnosis(self):
        with tempfile.TemporaryDirectory() as temporary:
            root, _wheelhouse, expected = self._bundle(Path(temporary))
            output_dir = Path(temporary) / "evidence"
            raw_stdout = b"not valid JSON\n"
            raw_stderr = b"bounded stderr\n"
            result = recipe.BoundedCommandResult(
                returncode=0, timed_out=False, output_limited=False,
                stdout=raw_stdout, stderr=raw_stderr,
                stdout_bytes_observed=len(raw_stdout), stderr_bytes_observed=len(raw_stderr),
                stdout_sha256=digest(raw_stdout), stderr_sha256=digest(raw_stderr),
                started_at="2026-10-10T00:00:00.000Z", finished_at="2026-10-10T00:00:01.000Z",
                duration_ms=1000,
            )
            args = [
                "--input-dir", str(root), "--output-dir", str(output_dir),
                "--candidate-sha256", expected["candidate_sha256"],
                "--probe-sha256", expected["probe_sha256"],
                "--manifest-sha256", expected["manifest_sha256"],
                "--wheelhouse-sha256", expected["wheelhouse_sha256"],
                "--launcher-sha256", recipe.sha256_file(SCRIPT), "--execute",
            ]
            stdout = io.StringIO()
            with patch.object(recipe.platform, "system", return_value="Linux"), \
                 patch.object(recipe.platform, "machine", return_value="x86_64"), \
                 patch.object(recipe.shutil, "which", return_value="/usr/bin/docker"), \
                 patch.object(recipe, "_inspect_local_image"), \
                 patch.object(recipe, "inspect_daemon_identity", return_value={"Architecture": "amd64"}), \
                 patch.object(recipe, "run_docker_bounded", return_value=result) as run_child, \
                 redirect_stdout(stdout):
                status = recipe.main(args)

            self.assertEqual(2, status)
            run_child.assert_called_once()
            summary = json.loads(stdout.getvalue())
            self.assertEqual("failed", summary["status"])
            self.assertEqual("probe returned invalid result JSON", summary["reason"])
            receipt_path = Path(summary["launcherReceipt"])
            receipt = json.loads(receipt_path.read_text())
            self.assertEqual("completed", receipt["status"])
            self.assertEqual(0, receipt["returnCode"])
            self.assertEqual(720, receipt["timeoutSeconds"])
            self.assertGreaterEqual(receipt["durationMs"], 0)
            self.assertEqual(run_child.call_args.args[0], receipt["argv"])
            self.assertEqual(digest(raw_stdout), receipt["stdout"]["sha256Observed"])
            self.assertEqual(digest(raw_stderr), receipt["stderr"]["sha256Observed"])
            self.assertEqual(raw_stdout, (output_dir / receipt["stdout"]["path"]).read_bytes())
            self.assertEqual(raw_stderr, (output_dir / receipt["stderr"]["path"]).read_bytes())
            self.assertEqual(0o700, output_dir.stat().st_mode & 0o777)
            for name in ("launcher-receipt.json", "launcher.stdout.bin", "launcher.stderr.bin"):
                self.assertEqual(0o600, (output_dir / name).stat().st_mode & 0o777)

    def test_every_post_launch_outcome_keeps_bounded_private_trace(self):
        cases = (
            ("child failure", 17, False, False, b"partial result\n", b"probe error\n", 17, "failed", "failed"),
            ("timeout", -15, True, False, b"partial result\n", b"still running\n", 124, "timed_out", "timed_out"),
            ("output limit", -15, False, True, b"partial result\n", b"too much output\n", 2, "output_limited", "output_limited"),
            ("bad status", 0, False, False, b'{"status":"blocked"}\n', b"diagnostic\n", 2, "failed", "completed"),
        )
        for label, returncode, timed_out, output_limited, raw_stdout, raw_stderr, expected_exit, expected_status, receipt_status in cases:
            with self.subTest(outcome=label), tempfile.TemporaryDirectory() as temporary:
                root, _wheelhouse, expected = self._bundle(Path(temporary))
                output_dir = Path(temporary) / "evidence"
                result = recipe.BoundedCommandResult(
                    returncode=returncode, timed_out=timed_out, output_limited=output_limited,
                    stdout=raw_stdout, stderr=raw_stderr,
                    stdout_bytes_observed=len(raw_stdout), stderr_bytes_observed=len(raw_stderr),
                    stdout_sha256=digest(raw_stdout), stderr_sha256=digest(raw_stderr),
                    started_at="2026-10-10T00:00:00.000Z", finished_at="2026-10-10T00:00:01.000Z",
                    duration_ms=1000,
                )
                args = [
                    "--input-dir", str(root), "--output-dir", str(output_dir),
                    "--candidate-sha256", expected["candidate_sha256"],
                    "--probe-sha256", expected["probe_sha256"],
                    "--manifest-sha256", expected["manifest_sha256"],
                    "--wheelhouse-sha256", expected["wheelhouse_sha256"],
                    "--launcher-sha256", recipe.sha256_file(SCRIPT), "--execute",
                ]
                output = io.StringIO()
                cleanup = subprocess.CompletedProcess([], 0, stdout=b"", stderr=b"")
                with patch.object(recipe.platform, "system", return_value="Linux"), \
                     patch.object(recipe.platform, "machine", return_value="x86_64"), \
                     patch.object(recipe.shutil, "which", return_value="/usr/bin/docker"), \
                     patch.object(recipe, "_inspect_local_image"), \
                 patch.object(recipe, "inspect_daemon_identity", return_value={"Architecture": "amd64"}), \
                     patch.object(recipe, "run_docker_bounded", return_value=result), \
                     patch.object(recipe.subprocess, "run", return_value=cleanup) as cleanup_runner, \
                     redirect_stdout(output):
                    status = recipe.main(args)

                self.assertEqual(expected_exit, status)
                if timed_out or output_limited:
                    cleanup_runner.assert_called_once_with(
                        ["/usr/bin/docker", "rm", "--force", unittest.mock.ANY],
                        check=False, capture_output=True, timeout=15,
                    )
                else:
                    cleanup_runner.assert_not_called()
                summary = json.loads(output.getvalue())
                self.assertEqual(expected_status, summary["status"])
                receipt_path = Path(summary["launcherReceipt"])
                receipt = json.loads(receipt_path.read_text())
                self.assertEqual(receipt_status, receipt["status"])
                self.assertEqual(returncode, receipt["returnCode"])
                self.assertEqual(timed_out, receipt["timedOut"])
                self.assertEqual(output_limited, receipt["outputLimited"])
                self.assertEqual(digest(raw_stdout), receipt["stdout"]["sha256Observed"])
                self.assertEqual(digest(raw_stderr), receipt["stderr"]["sha256Observed"])
                self.assertEqual(raw_stdout, (output_dir / receipt["stdout"]["path"]).read_bytes())
                self.assertEqual(raw_stderr, (output_dir / receipt["stderr"]["path"]).read_bytes())
                for name in ("launcher-receipt.json", "launcher.stdout.bin", "launcher.stderr.bin"):
                    self.assertEqual(0o600, (output_dir / name).stat().st_mode & 0o777)


if __name__ == "__main__":
    unittest.main()
