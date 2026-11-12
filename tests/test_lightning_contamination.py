# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-072 REQ-006 / SC-006: contamination scan and the sandboxed optimizer host (fake hosts; no model contacted)."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

from agent_braid import lightning_runner as runner
from agent_braid.harness_host_claude import ENV_DENY

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts import spec072_holdout_fingerprints as fingerprints  # noqa: E402

CLEAN_ENV = {k: v for k, v in os.environ.items() if not k.endswith('_API_KEY') and k not in ENV_DENY}
HELD = json.loads((ROOT / runner.PROMPT_FILES['held-out']).read_text())['cases']
DEV = json.loads((ROOT / runner.PROMPT_FILES['development']).read_text())['cases']
SKILL = (ROOT / 'integrations/agent-braid/skills/agent-braid-analyze/SKILL.md').read_text()
DARWIN = sys.platform == 'darwin'


class ScanTests(unittest.TestCase):
    def setUp(self):
        self.prints = runner.load_fingerprints(ROOT)

    def passed(self, text):
        return runner.contamination_passed(text, self.prints)

    def test_committed_fingerprints_are_current_and_reproducible(self):
        self.assertEqual(fingerprints.build(), json.loads((ROOT / runner.FINGERPRINTS).read_text()))

    def test_clean_development_inputs_pass(self):
        self.assertTrue(self.passed(SKILL))
        for case in DEV:
            self.assertTrue(self.passed(f"- {case['id']}: {case['prompt']}"), case['id'])

    def test_held_out_material_is_refused(self):
        words = runner.normalize_words(HELD[3]['prompt'])
        start = next(i for i in range(len(words) - 7)
                     if runner.window_sha256(words[i:i + 8]) in set(self.prints['windowSha256']))
        excerpt = 'Earlier advice:  ' + ' '.join(words[start:start + 8]).upper() + ' and more.'
        for text in (excerpt, 'see HELD-07', 'note ' + runner.HOLDOUT_CANARY, 'note ' + runner.LIGHTNING_CANARY):
            with self.subTest(text=text[:20]):
                self.assertFalse(self.passed(text))

    def test_held_out_id_is_refused_by_hash_without_the_pattern(self):
        prints = dict(self.prints, idSha256=self.prints['idSha256'] + [runner.hashlib.sha256(b'case-x').hexdigest()])
        self.assertFalse(runner.contamination_passed('about case-x', prints))

    def test_stale_fingerprints_are_refused(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for rel in (runner.FINGERPRINTS, 'specs/069-aim-request-authoring/prompts/FREEZE.json'):
                (root / rel).parent.mkdir(parents=True, exist_ok=True)
                (root / rel).write_bytes((ROOT / rel).read_bytes())
            value = json.loads((root / runner.FINGERPRINTS).read_text())
            value['heldOutSha256'] = '0' * 64
            (root / runner.FINGERPRINTS).write_text(json.dumps(value))
            with self.assertRaises(runner.RunnerError) as caught:
                runner.load_fingerprints(root)
            self.assertEqual(caught.exception.code, 'holdout-fingerprint-stale')

    def test_held_out_workspaces_carry_the_held_out_canary(self):
        self.assertIn(runner.HOLDOUT_CANARY, runner.canary_note('held-out'))
        self.assertNotIn(runner.HOLDOUT_CANARY, runner.canary_note('development'))

    def test_channel_checks_before_every_call(self):
        seen = []
        channel = runner.OptimizerChannel('claude-code', transport=seen.append, fake=True)
        channel.call('clean input')
        with self.assertRaises(runner.RunnerError):
            channel.call(HELD[0]['prompt'])
        self.assertEqual(seen, ['clean input'])
        self.assertEqual(len(channel.calls), 1)


class SandboxedHostTests(unittest.TestCase):
    def make(self, **kwargs):
        kwargs.setdefault('environ', CLEAN_ENV)
        return runner.OptimizerChannel('claude-code', fake_hosts=True, **kwargs)

    def test_fake_host_call_runs_without_tools_in_the_disposable_profile(self):
        channel = self.make()
        try:
            call_id, text, check = channel.call('Improve this guidance.')
            self.assertEqual((call_id, text.strip(), check['passed']), ('opt-0001', 'OK', True))
            host = channel._transport
            self.assertNotIn('ANTHROPIC_API_KEY', host.env)
            self.assertTrue(str(host.cwd).startswith(str(host.profile.root)))
            denied = {str(ROOT / p) for p in runner.OPTIMIZER_DENIED}
            self.assertTrue(denied <= {str(p) for p in host.protected})
            if DARWIN:
                self.assertTrue(host.probe['enforced'])
                read = runner.run_process(['/bin/cat', str(ROOT / runner.PROMPT_FILES['held-out'])], host.env, host.cwd,
                                          host.profile, [], host.sandbox, 30, 'probe')
                self.assertNotEqual(read.returncode, 0)
                self.assertNotIn(HELD[0]['prompt'][:20], read.stdout)
        finally:
            self.assertTrue(channel.close()['clean'])

    def test_unverified_key_source_is_refused(self):
        channel = self.make(fake_key_source='apiKey')
        try:
            with self.assertRaises(runner.RunnerError) as caught:
                channel.call('Improve this guidance.')
            self.assertEqual(caught.exception.code, 'route-unverified')
        finally:
            channel.close()

    def test_paid_key_and_unsupported_host_are_refused_before_any_process(self):
        with self.assertRaises(runner.RunnerError) as caught:
            self.make(environ={**CLEAN_ENV, 'ANTHROPIC_API_KEY': 'sk-ant-test'})
        self.assertEqual(caught.exception.code, 'paid-route-refused')
        with self.assertRaises(runner.RunnerError) as caught:
            runner.OptimizerChannel('opencode', fake_hosts=True, environ=CLEAN_ENV)
        self.assertEqual(caught.exception.code, 'route-unverified')
        with self.assertRaises(runner.RunnerError) as caught:
            runner.OptimizerChannel('claude-code', transport=str)
        self.assertEqual(caught.exception.code, 'isolation-failed')


if __name__ == '__main__':
    unittest.main()
