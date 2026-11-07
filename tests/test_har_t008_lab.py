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
        # an abort at an input() prompt prints the report on the prompt line
        text = 'Type the attempt name: {\n  "verdict": "cohort-aborted",\n  "units": 0\n}\n'
        self.assertEqual(lab.extract_report(text)["verdict"], "cohort-aborted")
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
        good = '{"verdict":"cohort-finished","attempt":"t008-x","executionAuthorization":False}'
        code, _ = self.capture(f"import json;print(json.dumps({good},indent=2))")
        self.assertEqual(code, 0)
        for bad in ('{"verdict":"cohort-finished","attempt":"other","executionAuthorization":False}',
                    '{"verdict":"cohort-finished","attempt":"t008-x","executionAuthorization":True}',
                    '{"verdict":"cohort-finished","attempt":"t008-x","executionAuthorization":False,"stopped":"x"}'):
            code, _ = self.capture(f"import json;print(json.dumps({bad},indent=2))")
            self.assertEqual(code, 1)
        code, files = self.capture("import sys;print('boom');sys.exit(3)")
        self.assertEqual(code, 3)
        self.assertIn("t008-cohort-t008-x.txt", files)
        self.assertNotIn("t008-cohort-t008-x.json", files)

    def test_ctrl_c_keeps_draining_so_the_aborted_report_is_saved(self):
        class Out:
            def __init__(self):
                self.items = [KeyboardInterrupt, b"{\n  \"verdict\": \"cohort-aborted\"\n}\n", b""]

            def read1(self, n):
                item = self.items.pop(0)
                if item is KeyboardInterrupt:
                    raise KeyboardInterrupt
                return item

        class Proc:
            stdout = Out()
            terminated = False

            def terminate(self):
                self.terminated = True

        chunks = []
        import codecs
        proc = Proc()
        with contextlib.redirect_stdout(io.StringIO()):
            interrupted = lab.drain(proc, codecs.getincrementaldecoder("utf-8")(), chunks)
        self.assertTrue(interrupted)
        self.assertFalse(proc.terminated)  # one Ctrl-C only drains; a second terminates
        self.assertEqual(lab.extract_report("".join(chunks))["verdict"], "cohort-aborted")

    def test_a_failure_while_relaying_still_saves_the_transcript_and_kills_the_child(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(lab, "drain", side_effect=KeyboardInterrupt), \
                    contextlib.redirect_stdout(io.StringIO()), \
                    contextlib.redirect_stderr(io.StringIO()):
                code = lab.run_cohort_capture([sys.executable, "-c", "import time;time.sleep(60)"], {}, tmp,
                                              "t008-x", Path(tmp), lambda text: None)
            self.assertNotEqual(code, 0)
            self.assertTrue((Path(tmp) / "t008-cohort-t008-x.txt").exists())

    def test_save_output_refuses_symlinks_and_writes_private_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            lab.save_output("a.json", "{}", folder)
            self.assertEqual((folder / "a.json").stat().st_mode & 0o777, 0o600)
            (folder / "b.json").symlink_to(folder / "a.json")
            with self.assertRaises(t9lab.Stop):
                lab.save_output("b.json", "{}", folder)
            lab.save_output("a.json", '{"x": 1}', folder)  # a differing rerun keeps the old evidence
            self.assertTrue((folder / "a.json.1").exists())

    def test_env_check_looks_at_names_only(self):
        self.assertIsNone(lab.ENV_NAME.search("PATH"))
        self.assertIsNotNone(lab.ENV_NAME.search("CLAUDE_CODE_OAUTH_TOKEN"))

    def test_unit_cap_matches_the_driver(self):
        import har_t008_unit as driver
        self.assertEqual(lab.MAX_UNITS, driver.MAX_UNITS)


class RunPastValidationTests(unittest.TestCase):
    def setUp(self):
        import hashlib
        import json
        from unittest import mock
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.home = root / "home"
        braid = root / "braid"
        scripts = braid / f"repo-{COMMIT[:7]}" / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "har_t008_unit.py").write_text("# fake")
        files = {}
        for name in ("claude", "python", "sandbox"):
            path = root / name
            path.write_text(name)
            files[name] = (str(path), hashlib.sha256(name.encode()).hexdigest())
        self.handoff = root / "handoff"
        (self.handoff / "to-lab").mkdir(parents=True)
        (self.handoff / "from-lab").mkdir()
        self.pins = {"claudeSha256": files["claude"][1], "interpreterSha256": files["python"][1],
                     "sandboxExecSha256": files["sandbox"][1]}
        (self.handoff / "to-lab" / "setup-summary.json").write_text(json.dumps(
            {"summaryVersion": t9lab.SUMMARY_VERSION, "commit": COMMIT, "pins": self.pins}))
        self.patches = [
            mock.patch.dict("os.environ", {"HOME": str(self.home)}),
            mock.patch.object(t9lab, "BRAID", str(braid)),
            mock.patch.object(t9lab, "CLAUDE", files["claude"][0]),
            mock.patch.object(t9lab, "PYTHON", files["python"][0]),
            mock.patch.object(t9lab, "SANDBOX_EXEC", files["sandbox"][0]),
            mock.patch.object(lab, "TRUSTED_UID", __import__("os").getuid()),
        ]
        for patch in self.patches:
            patch.start()
            self.addCleanup(patch.stop)

    def go(self, *extra, env=None):
        return lab.run(args("--handoff", str(self.handoff), *extra), env or {}, say=lambda text: None)

    def test_a_hash_mismatch_stops_before_any_driver_runs(self):
        (Path(t9lab.CLAUDE)).write_text("tampered")
        with self.assertRaises(t9lab.Stop) as cm:
            self.go()
        self.assertIn("pinned hash", str(cm.exception))

    def test_an_untrusted_code_copy_stops(self):
        from unittest import mock
        with mock.patch.object(lab, "TRUSTED_UID", 0 if __import__("os").getuid() else 1):
            with self.assertRaises(t9lab.Stop) as cm:
                self.go()
        self.assertIn("not trusted", str(cm.exception))

    def test_a_missing_code_copy_or_from_lab_stops(self):
        (Path(t9lab.BRAID) / f"repo-{COMMIT[:7]}" / "scripts" / "har_t008_unit.py").unlink()
        with self.assertRaises(t9lab.Stop):
            self.go()

    def test_the_cohort_runs_after_the_dry_run_and_the_output_directory_is_copied(self):
        from unittest import mock
        out_dir = self.home / "t008" / "out" / "t008-20261109a"
        out_dir.mkdir(parents=True)
        (out_dir / ".sessions.json").write_text("{}")
        calls = []
        with mock.patch.object(lab, "run_driver_capture", lambda *a: calls.append("dry") or "d"), \
                mock.patch.object(lab, "run_cohort_capture", lambda *a: calls.append("cohort") or 2):
            self.assertEqual(self.go(), 2)
        self.assertEqual(calls, ["dry", "cohort"])
        self.assertTrue((self.handoff / "from-lab" / "bundle-t008-20261109a" / ".sessions.json").exists())

    def test_the_bundle_is_copied_even_when_the_cohort_raises(self):
        from unittest import mock
        out_dir = self.home / "t008" / "out" / "t008-20261109a"
        out_dir.mkdir(parents=True)
        (out_dir / "x").write_text("1")
        with mock.patch.object(lab, "run_driver_capture", lambda *a: "d"), \
                mock.patch.object(lab, "run_cohort_capture", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.go()
        self.assertTrue((self.handoff / "from-lab" / "bundle-t008-20261109a" / "x").exists())


if __name__ == "__main__":
    unittest.main()
