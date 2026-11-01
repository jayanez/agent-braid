# SPDX-License-Identifier: AGPL-3.0-only
"""Offline opt-in CLI publication and local-file admission controls."""
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import system_one_shadow, tooling_telemetry
from agent_braid.cli import main
from agent_braid.system_one import STRICT_POLICY, canonical
from tests.test_system_one_core import fixture


class SystemOneCliTests(unittest.TestCase):
    def invoke(self, *args):
        stream = StringIO()
        with redirect_stdout(stream):
            status = main(list(args))
        return status, json.loads(stream.getvalue())

    def test_explicit_synthetic_answer_strict_abstention_and_parser_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "input.json"
            source.write_bytes(canonical(fixture()))
            status, response = self.invoke("system-one", "decide", str(source))
            self.assertEqual(status, 0)
            self.assertEqual(response["status"], "answered")
            self.assertFalse(response["executionAuthorization"])
            source.write_bytes(canonical(fixture(policy=STRICT_POLICY)))
            status, response = self.invoke("system-one", "decide", str(source))
            self.assertEqual((status, response["status"], response["answers"]), (1, "abstain", []))
            source.write_bytes(b'{"sourceKind":"SECRET_SENTINEL","sourceKind":0}')
            status, response = self.invoke("system-one", "decide", str(source))
            self.assertEqual((status, response["status"]), (2, "refused"))
            self.assertNotIn("SECRET_SENTINEL", json.dumps(response))

    def test_capabilities_never_allocates_runtime_or_calls_provider(self):
        with patch("agent_braid.system_one_backends.DecisionRuntime", side_effect=AssertionError("runtime instantiated")):
            status, manifest = self.invoke("system-one", "capabilities")
        self.assertEqual(status, 0)
        self.assertEqual(manifest["maxActive"], 1)
        self.assertFalse(manifest["executionAuthorization"])

    def test_local_admission_refuses_symlink_fifo_directory_missing_and_large(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source"
            source.write_bytes(canonical(fixture()))
            link = root / "link"
            link.symlink_to(source)
            fifo = root / "fifo"
            os.mkfifo(fifo)
            large = root / "large"
            large.write_bytes(b" " * 1_048_577)
            for path in (link, fifo, root, root / "missing", large):
                with self.subTest(path=path.name):
                    status, response = self.invoke("system-one", "decide", str(path))
                    self.assertEqual(status, 2)
                    self.assertEqual(set(response), {"error"})

    def test_every_subcommand_accepts_telemetry_and_records_only_the_system_one_cell(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / "input.json"
            source.write_bytes(canonical(fixture()))
            metrics = root / "metrics"
            with patch.object(tooling_telemetry, "default_directory", return_value=metrics), \
                    patch.object(system_one_shadow, "default_directory", return_value=root / "store"):
                for command in (("capabilities",), ("decide", str(source)), ("report", "--format", "json"),
                                ("purge", "--yes")):
                    for position in ("group", "subcommand"):
                        arguments = ("system-one", "--telemetry", "local", *command) if position == "group" \
                            else ("system-one", *command, "--telemetry", "local")
                        with self.subTest(arguments=arguments):
                            stream = StringIO()
                            with redirect_stdout(stream):
                                self.assertIn(main(list(arguments)), (0, 1))
            rows = tooling_telemetry.Store(metrics).report()["rows"]
        self.assertTrue(rows)
        self.assertEqual({(row["surface"], row["operation"]) for row in rows}, {("cli", "system-one")})
        self.assertEqual({row["metric"] for row in rows} - {"calls", "duration"}, set())
        self.assertEqual(sum(row["count"] for row in rows if row["metric"] == "calls"), 8)

    def test_system_one_without_telemetry_creates_no_metrics(self):
        with tempfile.TemporaryDirectory() as directory:
            metrics = Path(directory) / "metrics"
            with patch.object(tooling_telemetry, "default_directory", return_value=metrics):
                self.invoke("system-one", "capabilities")
            self.assertFalse(metrics.exists())

    def test_legacy_help_does_not_load_decision_command(self):
        with patch("agent_braid.system_one_cli.run", side_effect=AssertionError("decision dispatched")):
            with redirect_stdout(StringIO()), self.assertRaises(SystemExit) as exit_context:
                main(["analyze", "--help"])
        self.assertEqual(exit_context.exception.code, 0)
