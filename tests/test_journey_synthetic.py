# SPDX-License-Identifier: AGPL-3.0-only
"""One-command owned synthetic journey (SPEC-043 T001); no host, network or model."""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import unittest.mock

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "examples/journey/run_journey.py"
STEPS = ["install", "discovery", "analysis", "plan", "grant-refusal", "execute-interrupted",
         "recover", "verify", "export", "uninstall"]


def _load():
    spec = importlib.util.spec_from_file_location("run_journey", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SyntheticJourneyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.receipt = _load().run_journey()

    def test_every_step_passes_in_order_with_explicit_domain(self):
        receipt = self.receipt
        self.assertEqual("passed", receipt["status"])
        self.assertEqual(STEPS, [step["step"] for step in receipt["steps"]])
        self.assertEqual("synthetic-local", receipt["domain"])
        for flag in ("hostConnection", "networkUsed", "modelSpend", "executionAuthorization"):
            self.assertIs(False, receipt[flag])
        self.assertIn("not actual-host", receipt["limits"][0])

    def test_refusal_and_negative_controls_are_recorded(self):
        steps = {step["step"]: step for step in self.receipt["steps"]}
        self.assertEqual("refused", steps["grant-refusal"]["toolStatus"])
        self.assertFalse(steps["grant-refusal"]["runCreated"])
        self.assertFalse(steps["grant-refusal"]["grantsIssued"])
        self.assertEqual("verified-completed", steps["verify"]["runtimeStatus"])
        self.assertTrue(steps["verify"]["resultTreeMatchesExpected"])
        self.assertTrue(self.receipt["sourceUnchanged"])
        controls = {control["name"]: control for control in self.receipt["negativeControls"]}
        self.assertEqual({"unissued-grant-refused", "mismatched-acknowledgement-refused",
                          "no-grant-tool-exposed"}, set(controls))
        self.assertTrue(all(control["held"] for control in controls.values()))

    def test_export_is_deterministic_and_hashed(self):
        export = {step["step"]: step for step in self.receipt["steps"]}["export"]
        self.assertTrue(export["deterministic"])
        self.assertEqual(64, len(export["files"]["evidence.json"]))

    def test_receipt_has_no_local_paths(self):
        text = json.dumps(self.receipt)
        for path in (tempfile.gettempdir(), Path(tempfile.gettempdir()).resolve(), ROOT):
            self.assertNotIn(str(path), text)
        self.assertNotIn("/private/var", text)

    def test_failure_is_loud_and_removes_stale_receipt(self):
        module = _load()
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "receipt.json"
            out.write_text("stale", encoding="utf-8")
            with unittest.mock.patch.object(module, "_run_journey", side_effect=KeyError("boom")):
                self.assertEqual(1, module.main(["--output", str(out)]))
            self.assertFalse(out.exists())

    def test_network_access_is_blocked_during_the_run(self):
        import socket
        module = _load()
        def reach_out():
            socket.socket()
        with unittest.mock.patch.object(module, "_run_journey", side_effect=reach_out):
            with self.assertRaises(module.JourneyError):
                module.run_journey()

    def test_single_command_writes_receipt_and_exits_zero(self):
        with tempfile.TemporaryDirectory() as temporary:
            out = Path(temporary) / "receipt.json"
            run = subprocess.run([sys.executable, str(SCRIPT), "--output", str(out)],
                                 cwd=ROOT, capture_output=True, text=True, timeout=300)
            self.assertEqual(0, run.returncode, run.stderr)
            self.assertEqual("passed", json.loads(out.read_text(encoding="utf-8"))["status"])


if __name__ == "__main__":
    unittest.main()
