# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T030 preparation: the real-use receipt script, on a temporary HOME only.

Every test points HOME at a temporary directory and checks that it did, so the
owner's real stores are never read or modified here. Fixture episodes and telemetry
cells are produced by the shipped code paths (ToolingService in shadow mode with
local telemetry), not by hand-written lines.
"""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from datetime import date
from io import StringIO
import hashlib
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from agent_braid import plugin_registry, system_one_shadow as shadow, tooling_telemetry as telemetry
from agent_braid.tooling_mcp import ToolingConfig, ToolingService
from scripts import spec066_t030_receipt as receipt
from tests.test_system_one_shadow import SAMPLE, SENTINEL, sentinel_request, unknown_request


class Base(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name).resolve()
        self.home = self.base / 'home'
        self.home.mkdir(mode=0o700)
        self.out = self.base / 'evidence'
        environment = {key: value for key, value in os.environ.items()
                       if key not in {'AGENT_BRAID_HOME', 'XDG_DATA_HOME'}}
        environment['HOME'] = str(self.home)
        patcher = patch.dict(os.environ, environment, clear=True)
        patcher.start()
        self.addCleanup(patcher.stop)
        # Guard: every store the script reads must live under the temporary HOME.
        for path in (shadow.default_directory(), telemetry.default_directory(), plugin_registry.home_path(),
                     Path.home()):
            self.assertTrue(path.is_relative_to(self.home), 'test would touch a real store')
        self.addCleanup(shadow.flush)

    def call(self, request, day, *, kind='aim'):
        """One analyze-work call on `day` with shadow mode and local telemetry, as the plugin makes it."""
        source, results = self.base / 'source', self.base / 'results'
        source.mkdir(exist_ok=True)
        results.mkdir(exist_ok=True)
        service = ToolingService(ToolingConfig(source, results, telemetry='local', system_one='shadow'))
        with patch.object(shadow, 'today', return_value=day), patch.object(telemetry, 'today', return_value=day):
            envelope = service.invoke('analyze-work', {'kind': kind, 'request': request}, threading.Event())
            self.assertTrue(shadow.flush())
        return envelope

    def run_main(self, current, *args):
        stdout, stderr = StringIO(), StringIO()
        with patch.object(receipt, 'today', return_value=current), \
                patch.object(shadow, 'today', return_value=current), \
                redirect_stdout(stdout), redirect_stderr(stderr):
            code = receipt.main(list(args), output_dir=self.out)
        return code, stdout.getvalue(), stderr.getvalue()

    def tree(self):
        return {str(path.relative_to(self.home)): (path.stat().st_mtime_ns, hashlib.sha256(path.read_bytes()).hexdigest())
                for path in sorted(self.home.rglob('*')) if path.is_file()}


class GateTests(Base):
    def test_dry_run_prints_the_receipt_and_writes_nothing_before_the_due_date(self):
        code, stdout, _ = self.run_main(date(2026, 11, 7), '--dry-run')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout)['receiptDate'], '2026-11-07')
        self.assertFalse(self.out.exists())

    def test_write_is_refused_before_the_due_date(self):
        code, stdout, stderr = self.run_main(date(2026, 11, 8))
        self.assertEqual((code, stdout), (2, ''))
        self.assertIn('2026-11-09', stderr)
        self.assertFalse(self.out.exists())

    def test_writes_on_the_due_date_reruns_identically_and_refuses_different_content(self):
        code, _, _ = self.run_main(date(2026, 11, 9))
        self.assertEqual(code, 0)
        target = self.out / 'real-use-shadow-2026-11-09.json'
        first = target.read_bytes()
        self.assertEqual(self.run_main(date(2026, 11, 9))[0], 0)
        self.assertEqual(target.read_bytes(), first)
        target.write_text('{}\n')
        code, _, stderr = self.run_main(date(2026, 11, 9))
        self.assertEqual(code, 2)
        self.assertIn('different content', stderr)
        self.assertEqual(target.read_text(), '{}\n')


class CountTests(Base):
    def setUp(self):
        super().setUp()
        self.assertEqual(self.call(SAMPLE, date(2026, 11, 1))['status'], 'ok')       # before day 1
        self.assertEqual(self.call(SAMPLE, date(2026, 11, 3))['status'], 'ok')
        self.assertEqual(self.call(unknown_request(), date(2026, 11, 5))['status'], 'ok')
        self.assertEqual(self.call({'not': 'a request'}, date(2026, 11, 5))['status'], 'refused')
        self.assertEqual(self.call(SAMPLE, date(2026, 11, 10))['status'], 'ok')      # after the receipt date

    def test_counts_cover_only_the_window_dates(self):
        value = receipt.build(date(2026, 11, 9))
        episodes = value['systemOneShadow']
        self.assertEqual(value['outcome'], 'observations')
        self.assertEqual((episodes['episodes'], episodes['datesWithEpisodes']), (2, 2))
        self.assertEqual(episodes['operations'], {'analyze-work': 2})
        self.assertEqual(episodes['systemOneStatus'], {'abstained': 2})
        self.assertEqual(episodes['pairsAnalysed'], 2)
        self.assertEqual(episodes['unknownPairs'], 1)
        self.assertEqual(episodes['dp1OpportunityShare'], 0.5)
        calls = value['telemetry']['operations']['mcp:analyze-work']
        self.assertEqual(calls['calls'], {'ok': 2, 'refused': 1})
        self.assertEqual(calls['datesWithCalls'], 2)
        self.assertEqual(sum(calls['pairClassifications'].values()), 2)
        self.assertEqual(value['telemetry']['operations']['cli:system-one']['calls'], {})

    def test_shadow_counts_match_the_system_one_report_on_the_same_dates(self):
        with patch.object(shadow, 'today', return_value=date(2026, 11, 9)):
            report = shadow.report()
        in_window = [day for day in report['days'] if '2026-11-02' <= day['day'] <= '2026-11-09']
        counted = receipt.build(date(2026, 11, 9))['systemOneShadow']
        self.assertEqual(counted['episodes'], sum(day['episodes'] for day in in_window))
        self.assertGreater(report['totals']['episodes'], counted['episodes'])  # the controls outside are present

    def test_read_only_telemetry_rows_equal_the_telemetry_report(self):
        rows = [dict(zip(('day', 'surface', 'operation', 'outcome', 'metric', 'bucket', 'count'), row))
                for row in receipt._telemetry_rows()]
        with patch.object(telemetry, 'today', return_value=date(2026, 11, 10)):
            self.assertEqual(rows, telemetry.Store().report()['rows'])

    def test_reading_changes_no_byte_and_no_timestamp_under_home(self):
        # A cell older than the store's 30 retained dates: report() would delete it on access, the receipt must not.
        with patch.object(telemetry, 'today', return_value=date(2026, 9, 1)):
            telemetry.Store().record('mcp', 'analyze-work', 'ok', 1)
        before = self.tree()
        with redirect_stdout(StringIO()):
            self.assertEqual(self.run_main(date(2026, 11, 9), '--dry-run')[0], 0)
        self.assertEqual(self.tree(), before)

    def test_no_request_value_or_local_path_reaches_the_receipt(self):
        self.call(sentinel_request(), date(2026, 11, 6))
        code, stdout, _ = self.run_main(date(2026, 11, 9), '--dry-run')
        self.assertEqual(code, 0)
        for secret in (SENTINEL, str(self.home), str(self.base), 'secret/path'):
            self.assertNotIn(secret, stdout)

    def test_a_value_outside_the_closed_vocabulary_stops_the_receipt(self):
        """Negative control: the closed-vocabulary check is what keeps arbitrary strings out."""
        real = shadow.report

        def foreign():
            value = real()
            for day in value['days']:
                day['operations'][SENTINEL] = 1
            return value

        with patch.object(receipt.shadow, 'report', foreign):
            code, stdout, stderr = self.run_main(date(2026, 11, 9), '--dry-run')
        self.assertEqual((code, stdout), (2, ''))
        self.assertIn('closed vocabulary', stderr)

    def test_a_local_path_in_any_field_stops_the_receipt(self):
        """Negative control for the path guard in render()."""
        with patch.object(receipt, 'consent', return_value={'status': 'observed', 'leak': str(self.home / 'x')}):
            code, stdout, stderr = self.run_main(date(2026, 11, 9), '--dry-run')
        self.assertEqual((code, stdout), (2, ''))
        self.assertIn('local path', stderr)


class SourceTests(Base):
    def test_an_empty_home_is_a_valid_no_observations_receipt_and_creates_nothing(self):
        code, stdout, _ = self.run_main(date(2026, 11, 9), '--dry-run')
        self.assertEqual(code, 0)
        value = json.loads(stdout)
        self.assertEqual(value['outcome'], 'no observations')
        for name in ('systemOneShadow', 'consent', 'telemetry'):
            self.assertEqual(value[name]['status'], 'no observations')
        self.assertEqual(len(value['sourcesChecked']), 9)
        self.assertTrue(all(item['result'] for item in value['sourcesChecked']))
        self.assertFalse(value['executionAuthorization'])
        self.assertEqual(list(self.home.rglob('*')), [])

    def test_consent_is_read_from_the_registry_without_changing_it(self):
        preview = plugin_registry.plan_setup(None, [], system_one='shadow', telemetry='local')
        plugin_registry.apply(None, preview, preview['previewDigest'])
        before = self.tree()
        self.assertEqual(receipt.consent(), {'status': 'observed', 'systemOneConfiguredMode': 'shadow',
                                             'telemetryConfiguredMode': 'local',
                                             'systemOneActiveMode': 'not-readable-offline'})
        self.assertEqual(self.tree(), before)

    def test_plugin_versions_come_from_host_caches_and_ignore_other_names(self):
        for host, version in (('.claude', '0.1.0-alpha.6'), ('.codex', '0.1.0-alpha.7')):
            (self.home / host / 'plugins/cache/agent-braid/agent-braid' / version).mkdir(parents=True)
        (self.home / '.codex/plugins/cache/agent-braid/agent-braid' / SENTINEL).mkdir()
        (self.home / '.claude/plugins/installed_plugins.json').write_text(json.dumps(
            {'version': 2, 'plugins': {'agent-braid@agent-braid': [{'version': '0.1.0-alpha.6', 'installPath': '/x'}],
                                       'other@market': [{'version': '9.9.9'}]}}))
        versions = receipt.plugin_versions()
        self.assertEqual(versions['claudeCode'], {'installed': ['0.1.0-alpha.6'], 'cached': ['0.1.0-alpha.6']})
        self.assertEqual(versions['codex'], {'cached': ['0.1.0-alpha.7']})
        self.assertNotIn(SENTINEL, json.dumps(versions))


if __name__ == '__main__':
    unittest.main()
