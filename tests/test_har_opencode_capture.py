# SPDX-License-Identifier: AGPL-3.0-only
"""Pure helpers of the SPEC-080 T007/T008 OpenCode capture script (no binary is run)."""
import json
from pathlib import Path
import unittest

from scripts import har_opencode_capture as capture


class CaptureHelperTests(unittest.TestCase):
    def test_sandbox_denies_the_real_home_and_outbound_ip_except_the_service_port(self):
        profile = capture.sandbox_profile(Path("/Users/someone"), Path("/Users/someone/.opencode/bin/opencode"),
                                          Path("/var/tmp/braid-x"), 41234)
        for rule in ('(deny network-outbound (remote ip))', '(allow network-outbound (remote ip "localhost:41234"))',
                     '(deny file-read* (subpath "/Users/someone"))', '(deny file-write* (subpath "/Users/someone"))',
                     '(allow file-read* (subpath "/Users/someone/.opencode/bin"))',
                     '(allow file-read* file-write* (subpath "/var/tmp/braid-x"))'):
            self.assertIn(rule, profile)
        self.assertLess(profile.index('(deny file-read* (subpath "/Users/someone"))'),
                        profile.index('(allow file-read* (subpath "/Users/someone/.opencode/bin"))'))
        with self.assertRaises(capture.Stop):
            capture.sandbox_profile(Path('/Users/a"b'), Path("/x/opencode"), Path("/t"), 1)

    def test_listed_reads_status_lines_only(self):
        self.assertTrue(capture.listed("○ agent-braid  pending\n", "agent-braid"))
        self.assertTrue(capture.listed("✗ probe   failed: x\n✗ probe2  failed: y\n", "probe2"))
        self.assertFalse(capture.listed("✗ probe2  failed: y\n", "probe"))
        self.assertFalse(capture.listed(capture.NO_SERVERS + "\n", "probe"))

    def test_config_document_selects_the_file_and_reports_absence(self):
        sources = [{"type": "document", "path": "/t/opencode.json", "info": {"mcp": {}}},
                   {"type": "directory", "path": "/t"}]
        self.assertEqual(capture.config_document(json.dumps(sources), "/t/opencode.json"), ("parsed", {"mcp": {}}))
        self.assertEqual(capture.config_document(json.dumps(sources[1:]), "/t/opencode.json"), ("absent", None))
        self.assertEqual(capture.config_document("not json", "/t/opencode.json"), ("unparsed", None))

    def test_winner_names_the_kept_shape_by_command(self):
        def case(command):
            return {"debugConfig": {"info": {"mcp": {"servers": {"probe": {"command": command}}}}}}
        self.assertEqual(capture.winner(case(["/usr/bin/true"])), "plural")
        self.assertEqual(capture.winner(case(["/usr/bin/false"])), "singular")
        self.assertEqual(capture.winner({"debugConfig": {"info": None}}), "not observed")

    def test_cases_cover_both_shapes_of_every_family_and_a_negative_control(self):
        shapes = {(case.family, case.shape) for case in capture.CASES}
        for family in ("mcp", "plugins", "permissions"):
            self.assertIn((family, "singular"), shapes)
            self.assertIn((family, "plural"), shapes)
        self.assertIn(("control", "unknown-key"), shapes)
        self.assertEqual(len({case.name for case in capture.CASES}), len(capture.CASES))


if __name__ == "__main__":
    unittest.main()
