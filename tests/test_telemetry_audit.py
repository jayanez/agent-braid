# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-047 T012: read-only host-log audit; synthetic fixtures only, never the real logs or store."""
from contextlib import redirect_stderr, redirect_stdout
import datetime
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import telemetry_audit as audit
from agent_braid import tooling_telemetry_cli

TODAY = datetime.date(2026, 11, 3)
SALT = b'fixed-salt'
FAIL_TAIL = ('{"evidenceRefs":[],"limits":["x"],"operation":"%s","provenance":{"executionAuthorization":[REDACTED]},'
             '"result":null,"schemaVersion":"agent-braid-plugin/v0.2","status":"%s","summary":"%s","workspaceId":null}')
GENERIC = 'Plugin request refused: check workspace, arguments, registry and reconnect state'


def line(kind, text, stamp='2026-11-02T10:00:00.000Z', session='session-a', cwd='/Users/secret/other-repo'):
    return json.dumps({kind: text, 'timestamp': stamp, 'sessionId': session, 'cwd': cwd})


def failure(tool, summary, status='refused', **kwargs):
    return line('debug', f"Tool '{tool}' failed after 0s: " + FAIL_TAIL % (tool, status, summary), **kwargs)


def report_rows(*rows):
    keys = ('day', 'surface', 'operation', 'outcome', 'metric', 'bucket', 'count')
    return {'rows': [dict(zip(keys, row)) for row in rows]}


class Fixture(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache = Path(self._tmp.name) / 'claude-cli-nodejs'

    def write(self, project, lines, name='2026-11-02T10-00-00-000Z.jsonl', directory=audit.LOG_DIR_NAME):
        path = self.cache / project / directory / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('\n'.join(lines) + '\n')
        return path

    def read(self, since='2026-11-01'):
        return audit.read_logs(self.cache, since, SALT)


class ReadLogsTests(Fixture):
    def test_calls_outcomes_and_failure_classes_per_day(self):
        self.write('-p1', [
            line('debug', 'Calling MCP tool: analyze-work'), line('debug', "Tool 'analyze-work' completed successfully in 5ms"),
            line('debug', 'Calling MCP tool: analyze-work'), failure('analyze-work', GENERIC),
            line('debug', 'Calling MCP tool: analyze-work'), failure('analyze-work', 'analyze-work refused: Git analysis request shape is invalid'),
            line('debug', 'Calling MCP tool: analyze-work'),
            line('debug', 'Calling MCP tool: never-heard-of-it'), failure('never-heard-of-it', 'boom', status='error'),
            line('error', FAIL_TAIL % ('analyze-work', 'refused', GENERIC)),  # duplicate error line is not counted
        ])
        day = self.read()['days']['2026-11-02']
        self.assertEqual(day['calls']['analyze-work'], {'calls': 4, 'ok': 1, 'refused': 2, 'error': 0, 'unfinished': 1})
        self.assertEqual(day['calls']['other'], {'calls': 1, 'ok': 0, 'refused': 0, 'error': 1, 'unfinished': 0})
        self.assertEqual(day['callFailureClasses'], {'router-refused': 1, 'request-shape': 1, 'other': 1})

    def test_startup_refusals_are_deduplicated_per_session_and_hash_session_ids(self):
        message = 'plugin refused: Unsafe worktree root\n'
        self.write('-p1', [
            line('debug', 'stderr of the stdio server before restarting it: ' + message),
            line('error', 'Server stderr: ' + message),
            line('debug', 'Connection failed after 2495ms, 2495ms of it awake (CONNECTION_CLOSED): Connection closed'),
            line('error', 'Connection failed (CONNECTION_CLOSED): Connection closed'),
            line('error', 'Server stderr: ' + message, session='session-b'),
        ])
        result = self.read()
        day = result['days']['2026-11-02']
        self.assertEqual(day['startupRefusals'], {'registry-unsafe-path': 2})
        self.assertEqual(day['connectionFailures'], 1)
        self.assertEqual(day['startupRefusalSessionCount'], 2)
        hashes = day['startupRefusalSessions']
        self.assertEqual(len(hashes), 2)
        text = json.dumps(result)
        for secret in ('session-a', 'session-b', '/Users/secret', 'Unsafe worktree', 'other-repo', '-p1'):
            self.assertNotIn(secret, text)
        self.assertEqual(self.read()['days']['2026-11-02']['startupRefusalSessions'], hashes)  # same salt: stable

    def test_only_the_plugin_log_directory_is_read(self):
        decoy = [line('debug', 'Calling MCP tool: analyze-work')]
        self.write('-p1', decoy, directory='mcp-logs-other-server')
        self.write('-p1', decoy, name='notes.txt')
        self.assertEqual(self.read()['days'], {})
        self.assertEqual(self.read()['filesRead'], 0)

    def test_symlinks_malformed_and_oversize_input_are_skipped_not_followed(self):
        real = self.write('-p1', [line('debug', 'Calling MCP tool: analyze-work')])
        outside = Path(self._tmp.name) / 'outside.jsonl'
        outside.write_text(line('debug', 'Calling MCP tool: workspaces') + '\n')
        (real.parent / 'link.jsonl').symlink_to(outside)
        (self.cache / '-linked').symlink_to(self.cache / '-p1')
        self.write('-p2', ['not json', '[1]', json.dumps({'debug': 5, 'timestamp': 'x', 'sessionId': 's'}),
                           line('debug', 'Calling MCP tool: status', stamp='garbage')], name='bad.jsonl')
        big = self.write('-p3', [line('debug', 'Calling MCP tool: verify')], name='big.jsonl')
        big.write_bytes(b'x' * (audit.MAX_FILE_BYTES + 10))
        result = self.read()
        self.assertEqual(list(result['days']['2026-11-02']['calls']), ['analyze-work'])
        self.assertEqual(result['linesSkipped'], 4)
        self.assertEqual(result['filesSkipped'], 1)
        self.assertTrue(result['truncated'])

    def test_since_filters_days_and_missing_root_is_empty(self):
        self.write('-p1', [line('debug', 'Calling MCP tool: workspaces', stamp='2026-10-01T00:00:00.000Z'),
                           line('debug', 'Calling MCP tool: workspaces', stamp='2026-11-02T00:00:00.000Z')])
        self.assertEqual(list(self.read('2026-11-01')['days']), ['2026-11-02'])
        self.assertEqual(audit.read_logs(self.cache / 'missing', '2026-01-01', SALT)['days'], {})

    def test_failure_and_startup_classification_use_fixed_phrases(self):
        self.assertEqual(audit.classify_call_failure('Registry changed: reconnect the MCP'), 'reconnect-required')
        self.assertEqual(audit.classify_call_failure('Worktree is outside the operator-configured allowlist'), 'worktree-allowlist')
        self.assertEqual(audit.classify_call_failure('analyze-work refused: Tool arguments do not match the declared input schema'), 'arguments-invalid')
        self.assertEqual(audit.classify_call_failure('anything else'), 'other')
        self.assertIn(audit.classify_call_failure(GENERIC), audit.CALL_CLASSES)
        for message, expected in (('Unsafe worktree root', 'registry-unsafe-path'), ('Malformed workspace registry', 'registry-shape'),
                                  ('registry must migrate', 'migration-required'), ('Runtime requires a grant store', 'grant-missing'),
                                  ('zzz', 'other')):
            self.assertEqual(audit.classify_startup(message), expected)
        self.assertTrue(set(audit.classify_startup(m) for m in ('Unsafe', 'q')) <= set(audit.STARTUP_CLASSES))


class ReconcileTests(Fixture):
    def days(self, calls, failed=0):
        self.write('-p1', [x for _ in range(calls) for x in (line('debug', 'Calling MCP tool: analyze-work'),)]
                   + [failure('analyze-work', GENERIC) for _ in range(failed)])
        return self.read()['days']

    def test_gap_between_log_and_store_is_flagged(self):
        result = audit.reconcile(self.days(12, failed=5), report_rows(
            ('2026-11-02', 'mcp', 'analyze-work', 'ok', 'calls', 'all', 8), ('2026-11-02', 'mcp', 'analyze-work', 'refused', 'calls', 'all', 1)), TODAY)
        row = result['rows'][0]
        self.assertEqual((row['logCalls'], row['storeCalls'], row['callGap'], row['failedGap'], row['flagged']), (12, 9, 3, 4, True))
        self.assertEqual(result['flagged'], 1)
        self.assertEqual(result['status'], 'compared')

    def test_matching_counts_are_not_flagged_and_unavailable_store_is_never_success(self):
        days = self.days(2)
        match = audit.reconcile(days, report_rows(('2026-11-02', 'mcp', 'analyze-work', 'ok', 'calls', 'all', 2)), TODAY)
        self.assertEqual(match['flagged'], 0)
        self.assertEqual(audit.reconcile(days, None, TODAY), {'status': 'unavailable', 'rows': [], 'flagged': 0})
        empty = audit.reconcile(days, report_rows(), TODAY)
        self.assertEqual((empty['status'], empty['flagged']), ('store-empty', 1))

    def test_days_beyond_store_retention_are_not_flagged(self):
        self.write('-p1', [line('debug', 'Calling MCP tool: workspaces', stamp='2026-09-01T00:00:00.000Z')])
        row = audit.reconcile(self.read('2026-08-01')['days'], report_rows(('2026-11-02', 'mcp', 'workspaces', 'ok', 'calls', 'all', 1)), TODAY)['rows'][0]
        self.assertFalse(row['inStoreRetention'])
        self.assertFalse(row['flagged'])

    def test_store_only_day_is_flagged_and_sessions_beyond_cap_are_counted(self):
        self.write('-p1', [line('error', 'Server stderr: plugin refused: Unsafe worktree root\n', session=f's{i}')
                           for i in range(audit.MAX_SESSION_HASHES + 5)])
        days = self.read()['days']
        self.assertEqual(days['2026-11-02']['startupRefusalSessionCount'], audit.MAX_SESSION_HASHES + 5)
        self.assertEqual(len(days['2026-11-02']['startupRefusalSessions']), audit.MAX_SESSION_HASHES)
        result = audit.reconcile(days, report_rows(('2026-11-01', 'mcp', 'workspaces', 'ok', 'calls', 'all', 3)), TODAY, '2026-11-01')
        self.assertEqual([(r['day'], r['callGap'], r['flagged']) for r in result['rows']], [('2026-11-01', -3, True)])

    def test_byte_budget_skips_files_before_reading(self):
        self.write('-p1', [line('debug', 'Calling MCP tool: status')])
        with patch.object(audit, 'MAX_TOTAL_BYTES', 10):
            result = self.read()
        self.assertEqual((result['filesRead'], result['filesSkipped'], result['truncated']), (0, 1, True))
        self.assertEqual(result['days'], {})

    def test_serve_start_refusals_are_compared_with_startup_refusal_sessions(self):
        self.write('-p1', [line('error', 'Server stderr: plugin refused: Unsafe worktree root\n')])
        result = audit.reconcile(self.read()['days'], report_rows(
            ('2026-11-02', 'lifecycle', 'serve-start', 'refused', 'calls', 'all', 1)), TODAY)
        self.assertEqual(result['startup'], [{'day': '2026-11-02', 'logStartupRefusalSessions': 1, 'storeServeStartRefused': 1}])


class AuditAndCliTests(Fixture):
    def test_alerts_summary_and_text_render(self):
        self.write('-p1', [line('error', 'Server stderr: plugin refused: Unsafe worktree root\n'),
                           line('debug', 'Calling MCP tool: analyze-work'), failure('analyze-work', GENERIC)])
        result = audit.audit(self.cache, report_rows(), today=TODAY, since='2026-11-01', salt=SALT)
        self.assertEqual(result['alerts'], ['startup-refusals', 'reconciliation-gap', 'store-empty'])
        self.assertEqual(result['summary']['startupRefusals'], 1)
        self.assertEqual(result['cannotSee'], list(audit.CANNOT_SEE))
        text = audit.render_text(result)
        self.assertIn('GAP 2026-11-02 analyze-work: log 1 vs store 0', text)
        self.assertIn('Telemetry cannot see:', text)
        self.assertNotIn('/Users/secret', text)

    def test_no_cache_root_reports_logs_unavailable(self):
        result = audit.audit(None, None, today=TODAY)
        self.assertFalse(result['logsAvailable'])
        self.assertEqual(result['reconciliation']['status'], 'unavailable')
        self.assertEqual(result['since'], '2026-10-28')

    def run_cli(self, *argv):
        parser = __import__('argparse').ArgumentParser()
        tooling_telemetry_cli.add_parser(parser.add_subparsers(dest='command', required=True))
        args = parser.parse_args(['telemetry', 'audit-logs', *argv])
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = tooling_telemetry_cli.run(args)
        return code, out.getvalue(), err.getvalue()

    def test_cli_json_uses_store_report_and_never_writes(self):
        self.write('-p1', [line('debug', 'Calling MCP tool: workspaces')])
        before = sorted(p.name for p in Path(self._tmp.name).rglob('*'))
        with patch('agent_braid.tooling_telemetry.Store') as store:
            store.return_value.report.return_value = report_rows()
            code, out, _ = self.run_cli('--cache-root', str(self.cache), '--since', '2026-11-01', '--format', 'json')
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(out)['schema'], audit.SCHEMA)
        self.assertEqual(sorted(p.name for p in Path(self._tmp.name).rglob('*')), before)

    def test_cli_degrades_when_store_is_unusable_and_refuses_bad_date(self):
        self.write('-p1', [line('debug', 'Calling MCP tool: workspaces')])
        with patch('agent_braid.tooling_telemetry.Store', side_effect=__import__('sqlite3').DatabaseError('private path')):
            code, out, _ = self.run_cli('--cache-root', str(self.cache), '--since', '2026-11-01', '--format', 'json')
        self.assertEqual(json.loads(out)['reconciliation']['status'], 'unavailable')
        code, out, err = self.run_cli('--since', 'yesterday')
        self.assertEqual((code, out), (2, ''))
        self.assertNotIn('yesterday', err)


if __name__ == '__main__':
    unittest.main()
