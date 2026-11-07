# SPDX-License-Identifier: AGPL-3.0-only
"""T008 one-command lab wrapper controls: validation, plan, command shape, report extraction; nothing native runs."""
import contextlib
import io
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import har_t008_lab as lab  # noqa: E402
import har_t009_lab as t9lab  # noqa: E402

COMMIT = "a" * 40
PINS = {"claudeSha256": "1" * 64, "interpreterSha256": "2" * 64, "sandboxExecSha256": "3" * 64}


def args(*extra, attempt="t008-20261109a", commit=COMMIT):
    return lab.parser().parse_args(["--commit", commit, "--operator-account", "founder",
                                    "--attempt", attempt, *extra])


class WrapperTests(unittest.TestCase):
    def test_labels_and_hashes_are_validated_before_anything_runs(self):
        with self.assertRaises(t9lab.Stop):
            lab.run(args(attempt="t009-20261109"), {})
        with self.assertRaises(t9lab.Stop):
            lab.run(args(commit="abc"), {})

    def test_units_are_capped_at_the_founders_four(self):
        self.assertEqual(args().units, 4)
        for units in ("5", "0"):
            with self.assertRaises(t9lab.Stop):
                lab.run(args("--units", units), {})

    def test_the_command_runs_the_t008_driver_from_the_pinned_code_copy_unbuffered(self):
        cmd = lab.driver_command(args(), PINS, "/Users/lab", "--founder-go")
        self.assertEqual(cmd[:4], [t9lab.PYTHON, "-B", "-I", "-u"])
        self.assertEqual(cmd[4], f"{t9lab.BRAID}/repo-{COMMIT[:7]}/scripts/har_t008_unit.py")
        self.assertIn("--founder-go", cmd)
        self.assertEqual(cmd[cmd.index("--units") + 1], "4")
        self.assertEqual(cmd[cmd.index("--config-dir") + 1], "/Users/lab/t009/config")  # the T009 login is reused
        self.assertEqual(cmd[cmd.index("--out-dir") + 1], "/Users/lab/t008/out/t008-20261109a")

    def test_plan_prints_stages_and_runs_nothing(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            self.assertEqual(lab.run(args("--plan"), {}), 0)
        text = out.getvalue()
        for needle in ("--dry-run", "--founder-go", "window", "no sudo", "verdict is the founder's"):
            self.assertIn(needle, text)

    def test_credential_environment_variables_stop_the_run(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(t9lab.Stop) as cm:
                lab.run(args("--handoff", tmp), {"ANTHROPIC_API_KEY": "secret-value"})
        self.assertIn("ANTHROPIC_API_KEY", str(cm.exception))
        self.assertNotIn("secret-value", str(cm.exception))

    def test_the_final_report_is_taken_from_the_end_of_the_transcript(self):
        text = 'T008 cohort\nprompt: {not json\n{\n  "verdict": "cohort-finished",\n  "units": 4\n}\n'
        self.assertEqual(lab.extract_report(text)["verdict"], "cohort-finished")
        with self.assertRaises(t9lab.Stop):
            lab.extract_report("no report here\n")
        with self.assertRaises(t9lab.Stop):
            lab.extract_report("x\n{\n  broken\n}\n")

    def test_a_trailing_traceback_does_not_hide_the_report(self):
        text = 'x\n{\n  "verdict": "cohort-aborted"\n}\nTraceback (most recent call last):\n  KeyboardInterrupt\n'
        self.assertEqual(lab.extract_report(text)["verdict"], "cohort-aborted")

    def capture(self, script):
        with tempfile.TemporaryDirectory() as tmp:
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = lab.run_cohort_capture([sys.executable, "-c", script], {}, tmp, "t008-x", Path(tmp),
                                              lambda text: None)
            return code, sorted(p.name for p in Path(tmp).iterdir())

    def test_exit_zero_without_a_finished_verdict_is_not_success(self):
        code, files = self.capture('import json;print(json.dumps({"verdict":"cohort-stopped"},indent=2))')
        self.assertEqual(code, 1)
        self.assertIn("t008-cohort-t008-x.json", files)

    def test_a_finished_cohort_succeeds_and_a_crash_keeps_the_transcript(self):
        code, _ = self.capture('import json;print(json.dumps({"verdict":"cohort-finished"},indent=2))')
        self.assertEqual(code, 0)
        code, files = self.capture("import sys;print('boom');sys.exit(3)")
        self.assertEqual(code, 3)
        self.assertIn("t008-cohort-t008-x.txt", files)
        self.assertNotIn("t008-cohort-t008-x.json", files)


if __name__ == "__main__":
    unittest.main()
