# SPDX-License-Identifier: AGPL-3.0-only
"""Pure patch-input checks. No compiler, binary, native control or workload."""
import unittest
from agent_braid.forecast_data import ForecastError
from agent_braid.forecast_systemd_patch import BASE,ADDITIONS,patch_sources,unified_patch


class SourcePatchTests(unittest.TestCase):
    def test_missing_or_extra_source_refuses(self):
        for sources in ({}, {**{n:b'' for n in BASE}, 'unexpected':b''}):
            with self.assertRaisesRegex(ForecastError,'patch-roster'):
                patch_sources(sources,{n:b'x' for n in ADDITIONS})

    def test_mutable_source_or_declared_commit_cannot_replace_bytes(self):
        with self.assertRaisesRegex(ForecastError,'source-drift'):
            patch_sources({n:b'changed upstream bytes' for n in BASE},
                          {n:b'x' for n in ADDITIONS})

    def test_added_roster_is_closed_before_transform(self):
        with self.assertRaisesRegex(ForecastError,'patch-additions'):
            patch_sources({n:b'' for n in BASE},{})

    def test_text_export_deterministic_with_new_file_marker(self):
        source={'a':b'before\n'};output={'b':b'new\n','a':b'after\n'}
        raw=unified_patch(source,output)
        self.assertEqual(raw,unified_patch(source,dict(reversed(list(output.items())))))
        self.assertIn('--- /dev/null\n+++ b/b\n',raw)
        self.assertIn('-before\n+after\n',raw)
