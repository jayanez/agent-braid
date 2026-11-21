# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-078 T011 (REQ-006 / SC-006): the runner keeps one redacted transcript record per rollout, only under SPEC-074
consent `redacted` for the `rollout` source, so a 0/3 prompt can be reviewed at Gate 1.

Fake hosts only; no model is contacted.
"""
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import lightning_runner as runner
from agent_braid import lightning_store as store
from agent_braid.cli import main
from agent_braid.lightning_hosts import Secrets, ToolCall, Transcript

from tests import test_spec078_heldout_v2 as base

SECRET = 'sk-ant-oat01-' + 'x' * 40


def consent(home: Path, level: str, sources: str = 'rollout') -> None:
    flags = ['lightning', 'init', '--home', str(home), '--non-interactive', '--trace-consent', level,
             '--trace-sources', sources]
    out = StringIO()
    with redirect_stdout(out), patch('sys.stderr', StringIO()):
        assert main(flags) == 0
    with redirect_stdout(StringIO()), patch('sys.stderr', StringIO()):
        assert main([*flags, '--apply', '--preview-digest', json.loads(out.getvalue())['previewDigest']]) == 0


class RunnerTraceTests(base.TempRoot):
    run_fake = base.RunnerTests.run_fake

    def setUp(self):
        super().setUp()
        self.home = Path(self.tmp.name).resolve() / 'home'

    def traces(self, status):
        return store.RunStore(self.home, status['runId']).read_content()

    def test_without_consent_no_content_is_stored(self):
        self.freeze()
        status = self.run_fake('v2-feedback')
        self.assertEqual(status['traces'], {'content': False, 'stored': 0, 'notStored': {}})
        self.assertFalse((store.RunStore(self.home, status['runId']).root / store.CONTENT_FILE).exists())

    def test_consent_without_the_rollout_source_stores_nothing(self):
        self.freeze()
        consent(self.home, 'redacted', 'loom')
        status = self.run_fake('v2-feedback')
        self.assertFalse(status['traces']['content'])
        self.assertEqual(self.traces(status), [])

    def test_consent_redacted_stores_one_record_per_rollout(self):
        self.freeze()
        consent(self.home, 'redacted')
        status = self.run_fake('v2-feedback')
        run = store.RunStore(self.home, status['runId'])
        results = {r.value['rolloutId']: r.value for r in run.read('result')}
        lines = run.read_content()
        self.assertEqual(status['traces'], {'content': True, 'stored': len(results), 'notStored': {}})
        records = {line['record']['rolloutId']: line['record'] for line in lines}
        self.assertEqual(len(lines), len(records))
        self.assertEqual(set(records), set(results))  # one per rollout, none refused
        prompts = {c['id']: c['prompt'] for c in base.cases('v2-feedback')}
        for rollout_id, record in records.items():
            self.assertEqual(record['schema'], runner.TRACE_SCHEMA)
            self.assertEqual(record['attemptId'], results[rollout_id]['attemptId'])
            self.assertEqual(record['transcriptSha256'], results[rollout_id]['transcriptSha256'])
            self.assertEqual(record['prompt'], prompts[rollout_id.split('.')[1]])
            self.assertTrue(any(c['tool'].endswith('analyze-work') for c in record['toolCalls']))
        raw = (run.root / store.CONTENT_FILE).read_text()
        self.assertNotIn('sk-ant-PLANTED-', raw)  # the fake host's planted credential never reaches the file


    def test_a_leaking_rollout_stores_no_trace(self):
        self.freeze()
        consent(self.home, 'redacted')
        status = self.run_fake('v2-feedback', fake_variant='leak-secret')
        self.assertEqual(status['refusal'], 'credential-leak')
        self.assertEqual(status['traces']['stored'], 0)
        self.assertEqual(self.traces(status), [])

    def test_a_broken_content_file_never_changes_results_or_stops_the_run(self):
        self.freeze()
        consent(self.home, 'redacted')
        first = self.run_fake('v2-feedback', max_rollouts=2)
        run = store.RunStore(self.home, first['runId'])
        with open(run.root / store.CONTENT_FILE, 'ab') as stream:
            stream.write(b'{"createdAt": 1')  # a torn line, as after a crash or a full disk
        resumed = self.run_fake('v2-feedback', max_rollouts=4, run_id=first['runId'], resume=True)
        self.assertIsNone(resumed['refusal'])
        self.assertEqual(resumed['completed'], 4)
        self.assertEqual(resumed['traces'], {'content': True, 'stored': 0, 'notStored': {'trace-error': 2}})


class TraceRecordTests(unittest.TestCase):
    def transcript(self, text='done', calls=1, output='ok'):
        return Transcript(tool_calls=[ToolCall('mcp__agent-braid__analyze-work', {'kind': 'aim'}, output, False)
                                      for _ in range(calls)], text=text)

    def test_fields_are_bounded_and_marked_truncated(self):
        record = runner.trace_record('claude-code.V2F-001.r1', 'a1', 'v2-feedback', 'prompt',
                                     self.transcript('y ' * 10000, calls=12, output='z ' * 2500), '0' * 64)
        self.assertTrue(record['truncated'])
        self.assertEqual(len(record['response']), runner.TRACE_LIMITS[0][0])
        self.assertEqual(len(record['toolCalls']), runner.TRACE_LIMITS[0][1])
        self.assertEqual(len(record['toolCalls'][0]['output']), runner.TRACE_LIMITS[0][2])
        small = runner.trace_record('r', 'a1', 'v2-feedback', 'prompt', self.transcript(), '0' * 64)
        self.assertFalse(small['truncated'])

    def test_redaction_runs_before_the_cut_and_the_cut_drops_the_split_word(self):
        token = 'ghp_' + 'A' * 36
        text = 'x ' * 5990 + token  # the token starts at 11980, across the 12000 limit
        plain = runner.trace_record('r', 'a1', 'v2-test', 'p', self.transcript(text), '0' * 64)
        self.assertNotIn('ghp_', plain['response'])  # the split word is dropped
        secrets = Secrets()
        redacted = runner.trace_record('r', 'a1', 'v2-test', 'p', self.transcript('see ' + token + ' end'), '0' * 64,
                                       redact=secrets.redact)
        self.assertNotIn('ghp_', redacted['response'])

    def run_store(self, tmp):
        home = Path(tmp).resolve() / 'home'
        consent(home, 'redacted')
        run = store.RunStore(home, 'r1')
        run.create(config_digest='b' * 64)
        return run

    def test_a_secret_in_the_transcript_is_redacted_before_it_is_stored(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.run_store(tmp)
            secrets = Secrets([SECRET])
            outcome = runner.store_trace(run, secrets, lambda limits: runner.trace_record(
                'r', 'a1', 'v2-test', 'prompt', self.transcript(f'key {SECRET} mail ana@example.org'), '0' * 64,
                limits))
            self.assertEqual(outcome, 'stored')
            raw = (run.root / store.CONTENT_FILE).read_text()
            self.assertNotIn(SECRET, raw)
            self.assertNotIn('ana@example.org', raw)

    def test_a_record_too_large_is_retried_smaller_then_given_up(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = self.run_store(tmp)
            secrets = Secrets()
            big = self.transcript('é ' * 10000, calls=8, output='\x01 ' * 2500)  # six bytes per escaped char
            self.assertEqual(runner.store_trace(run, secrets, lambda limits: runner.trace_record(
                'r', 'a1', 'v2-test', 'prompt', big, '0' * 64, limits)), 'stored')
            self.assertEqual(len(run.read_content()[0]['record']['response']), runner.TRACE_LIMITS[1][0])
            self.assertEqual(runner.store_trace(run, secrets, lambda limits: {'blob': 'p' * 70000}), 'too-large')
            self.assertEqual(len(run.read_content()), 1)  # nothing half-written

if __name__ == '__main__':
    unittest.main()
