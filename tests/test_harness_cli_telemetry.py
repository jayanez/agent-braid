# SPDX-License-Identifier: AGPL-3.0-only
"""HAR wave 1: opt-in local telemetry for `agent-braid harness` calls (batch v4)."""
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest
import uuid
from unittest.mock import patch

from agent_braid import harness_cli
from agent_braid import tooling_telemetry as telemetry
from agent_braid.cli import main


class HarnessCliTelemetryTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name).resolve()
        self.directory = self.root / 'metrics'
        lookup = patch.object(telemetry, 'default_directory', return_value=self.directory)
        lookup.start()
        self.addCleanup(lookup.stop)

    def harness(self, *argv):
        out = io.StringIO()
        with redirect_stdout(out), redirect_stderr(io.StringIO()):
            code = main(['harness', *argv])
        return code, out.getvalue()

    def cells(self):
        return {(r['operation'], r['outcome'], r['metric']): r['count'] for r in telemetry.Store().report()['rows']}

    def test_consent_off_by_default_and_explicit_off_leave_no_store(self):
        missing = str(self.root / 'absent.json')
        for argv in (('capabilities',), ('capabilities', '--telemetry', 'off'),
                     ('--telemetry', 'off', 'inspect', missing), ('inspect', missing)):
            with self.subTest(argv=argv):
                self.harness(*argv)
        self.assertFalse(self.directory.exists())

    def test_ok_and_refused_calls_count_per_subcommand_with_unchanged_output(self):
        off = self.harness('capabilities')
        on = self.harness('capabilities', '--telemetry', 'local')
        self.assertEqual(on, off)
        self.assertEqual(on[0], 0)
        secret = self.root / 'private-record-name.json'
        refused = self.harness('--telemetry', 'local', 'inspect', str(secret))
        self.assertEqual(refused[0], 2)
        self.assertEqual(json.loads(refused[1])['status'], 'refused')
        cells = self.cells()
        self.assertEqual(cells[('harness-capabilities', 'ok', 'calls')], 1)
        self.assertEqual(cells[('harness-inspect', 'refused', 'calls')], 1)
        self.assertEqual({metric for _, _, metric in cells}, {'calls', 'duration'})
        stored = b''.join(p.read_bytes() for p in self.directory.iterdir() if p.is_file())
        self.assertNotIn(b'private-record-name', stored)
        self.assertNotIn(str(self.root).encode(), stored)

    def test_uncaught_failure_counts_as_error_and_still_raises(self):
        with patch.object(harness_cli, '_dispatch', side_effect=RuntimeError('boom')):
            with self.assertRaises(RuntimeError):
                self.harness('capabilities', '--telemetry', 'local')
        self.assertEqual(self.cells(), {('harness-capabilities', 'error', 'calls'): 1,
                                        ('harness-capabilities', 'error', 'duration'): 1})

    def test_every_subcommand_has_a_closed_operation_name(self):
        self.assertEqual(telemetry.HARNESS_OPERATIONS, tuple(f'harness-{name}' for name in harness_cli.COMMANDS))
        self.assertTrue(set(telemetry.HARNESS_OPERATIONS) <= set(telemetry.OPERATIONS['cli']))

    def test_harness_cells_export_as_v4_and_older_batches_cannot_carry_them(self):
        self.harness('capabilities', '--telemetry', 'local')
        out = self.root / 'out.json'
        self.assertEqual(telemetry.Store().export(out)['status'], 'exported')
        batch = json.loads(out.read_text())
        self.assertEqual(batch['schema'], 'agent-braid-local-telemetry-batch/v4')
        self.assertEqual(telemetry.Store(self.root / 'other').merge(out)['status'], 'merged')
        for schema in (telemetry.SCHEMA_V1, telemetry.SCHEMA_V2, telemetry.SCHEMA_V3):
            with self.subTest(schema=schema):
                old = self.root / 'old.json'
                old.write_text(json.dumps(dict(batch, schema=schema, batchId=str(uuid.uuid4()))))
                with self.assertRaises(ValueError):
                    telemetry.Store(self.root / 'refuse').merge(old)
        self.assertFalse((self.root / 'refuse').exists())

    def test_status_limits_name_the_harness_coverage(self):
        code, text = main_json(['telemetry', 'status', '--format', 'json'])
        self.assertEqual(code, 0)
        limits = ' '.join(json.loads(text)['limits'])
        self.assertIn('analyze/analyze-git/system-one/harness', limits)
        self.assertIn('Batch schema v4', limits)
        self.assertIn('cannot export a store that holds harness cells', limits)


def main_json(argv):
    out = io.StringIO()
    with redirect_stdout(out):
        code = main(argv)
    return code, out.getvalue()


if __name__ == '__main__':
    unittest.main()
