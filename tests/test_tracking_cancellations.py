# SPDX-License-Identifier: AGPL-3.0-only
"""Cancellation is a bound owner disposition, never a completed criterion."""
from copy import deepcopy
import hashlib
import io
import json
from pathlib import Path
from contextlib import redirect_stdout
import tempfile
import unittest
from unittest.mock import patch

from scripts.sync_github_tracking import source_inventory, build_plan, apply_plan, milestone_plan


class CancellationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.folder = self.root / 'specs/001-example'
        self.folder.mkdir(parents=True)
        (self.folder / 'spec.md').write_text('# Example\n')
        (self.folder / 'assurance.json').write_text('{"requirements": []}')
        self.line = '- [ ] T001: Original complete-cost criterion.'
        (self.folder / 'tasks.md').write_text(self.line + '\n')
        self.decision = dict(version='agent-braid-task-cancellation-v1', taskId='SPEC-001/T001',
                             decision='adopted', disposition='cancelled-partial-infeasible',
                             stateReason='not_planned', criterionCompleted=False,
                             taskLineSha256=hashlib.sha256(self.line.encode()).hexdigest(),
                             sourceReference='Direct owner instruction', reason='Irrecoverable history')
        self.config = dict(repository='owner/repo', project_url='example', milestones={'M': 'bounded'},
                           specs={'001-example': {'milestone': 'M', 'state': 'open'}},
                           closed_milestones=[], task_state_overrides={}, project_review_pending=[])
        self.config_path = self.root / 'config.json'
        self.save()

    def save(self):
        raw = (json.dumps(self.decision) + '\n').encode()
        (self.folder / 'decision.json').write_bytes(raw)
        self.config['task_cancellations'] = {'SPEC-001/T001': {
            'decision': 'specs/001-example/decision.json', 'sha256': hashlib.sha256(raw).hexdigest()}}
        self.config_path.write_text(json.dumps(self.config))

    def inventory(self):
        return source_inventory(self.root, self.config_path)

    def fixtures(self):
        config, desired = self.inventory()
        milestones = {'M': {'number': 1, 'state': 'open'}}
        issues = {item['key']: dict(number=i + 1, id=i + 1, title=item['title'], body=item['body'],
                                   state='open', milestone={'title': 'M', 'number': 1})
                  for i, item in enumerate(desired)}
        return config, desired, milestones, issues, {'children': {'SPEC-001': {2}}, 'unmarked_titles': set()}

    def test_adopted_disposition_closes_without_checking_original_criterion(self):
        _, desired = self.inventory()
        item = desired[1]
        self.assertEqual(('closed', 'not_planned'), (item['state'], item['state_reason']))
        self.assertIn('cancelled', item['body'].lower())
        self.assertIn('not completed', item['body'])
        self.assertEqual(self.line + '\n', (self.folder / 'tasks.md').read_text())

    def test_no_cancellation_preserves_unchecked_open_task(self):
        self.config.pop('task_cancellations')
        self.config_path.write_text(json.dumps(self.config))
        self.assertEqual('open', self.inventory()[1][1]['state'])

    def test_absent_altered_or_escaping_decision_refuses(self):
        for name in ('missing', 'hash', 'escape', 'symlink'):
            with self.subTest(name=name):
                self.save()
                if name == 'missing': (self.folder / 'decision.json').unlink()
                elif name == 'hash': (self.folder / 'decision.json').write_text('{}')
                elif name == 'escape':
                    self.config['task_cancellations']['SPEC-001/T001']['decision'] = '../decision.json'
                    self.config_path.write_text(json.dumps(self.config))
                else:
                    (self.folder / 'decision.json').rename(self.folder / 'target.json')
                    (self.folder / 'decision.json').symlink_to(self.folder / 'target.json')
                with self.assertRaises((ValueError, OSError)): self.inventory()
                if name == 'symlink': (self.folder / 'decision.json').unlink()

    def test_decision_scope_authority_and_noncompletion_are_required(self):
        for key, value in [('decision', 'proposed'), ('taskId', 'SPEC-001/T002'),
                           ('stateReason', 'completed'), ('criterionCompleted', True),
                           ('version', 'other'), ('sourceReference', ''), ('reason', '')]:
            with self.subTest(key=key):
                old = deepcopy(self.decision)
                self.decision[key] = value; self.save()
                with self.assertRaises(ValueError): self.inventory()
                self.decision = old

    def test_symlinked_directory_and_malformed_binding_refuse(self):
        (self.root / 'alias').symlink_to(self.folder, target_is_directory=True)
        for binding in ({'decision': None, 'sha256': 'a' * 64},
                        {'decision': 'alias/decision.json', 'sha256': 'a' * 64},
                        {'decision': 'specs/001-example/decision.json', 'sha256': None}):
            with self.subTest(binding=binding):
                self.config['task_cancellations'] = {'SPEC-001/T001': binding}
                self.config_path.write_text(json.dumps(self.config))
                with self.assertRaises(ValueError): self.inventory()

    def test_registered_fc2_cancellation_is_distinct_from_seven_completions(self):
        _, desired = source_inventory()
        tasks = [x for x in desired if x['parent'] == 'SPEC-045']
        cancelled = [x for x in tasks if x.get('state_reason') == 'not_planned']
        self.assertEqual(['SPEC-045/T007'], [x['key'] for x in cancelled])
        self.assertEqual(7, sum(x['state'] == 'closed' and x not in cancelled for x in tasks))
        from scripts.sync_github_tracking import ROOT
        self.assertRegex((ROOT / 'specs/045-local-forecasting-capabilities/tasks.md').read_text(),
                         r'(?m)^- \[ \] T007 .*Capture approved actual Chronos CPU conformance and complete costs\.')

    def test_changed_or_checked_criterion_and_completed_override_refuse(self):
        for change in ('changed', 'checked', 'override', 'unknown'):
            with self.subTest(change=change):
                self.save()
                (self.folder / 'tasks.md').write_text(self.line + '\n')
                if change == 'changed': (self.folder / 'tasks.md').write_text(self.line + ' Changed.\n')
                elif change == 'checked': (self.folder / 'tasks.md').write_text(self.line.replace('[ ]', '[x]') + '\n')
                elif change == 'override': self.config['task_state_overrides'] = {'SPEC-001/T001': 'completed'}
                else: self.config['task_cancellations']['SPEC-001/T002'] = self.config['task_cancellations']['SPEC-001/T001']
                self.config_path.write_text(json.dumps(self.config))
                with self.assertRaises(ValueError): self.inventory()
                self.config['task_state_overrides'] = {}

    def test_planned_and_applied_reason_is_not_planned(self):
        config, desired, milestones, issues, extra = self.fixtures()
        operations = build_plan(config, desired, milestones, issues, extra)
        self.assertEqual([{'action': 'set_state', 'key': 'SPEC-001/T001', 'from': 'open',
                           'to': 'closed', 'state_reason': 'not_planned'}], operations)
        with patch('scripts.sync_github_tracking.gh_api', return_value={}) as api, redirect_stdout(io.StringIO()):
            apply_plan('owner/repo', config, desired, milestones, issues, operations)
        self.assertEqual({'state': 'closed', 'state_reason': 'not_planned'}, api.call_args.kwargs['body'])

    def test_already_closed_completed_reason_is_repaired_then_idempotent(self):
        args = self.fixtures()
        args[3]['SPEC-001/T001'].update(state='closed', state_reason='completed')
        operations = build_plan(*args)
        self.assertEqual('not_planned', operations[0]['state_reason'])
        args[3]['SPEC-001/T001']['state_reason'] = 'not_planned'
        self.assertEqual([], build_plan(*args))

    def test_reviewed_reason_drift_refuses_before_remote_writes(self):
        config, desired, milestones, issues, extra = self.fixtures()
        ops = build_plan(config, desired, milestones, issues, extra)
        ops[0]['state_reason'] = 'completed'
        with patch('scripts.sync_github_tracking.gh_api') as api, self.assertRaises(ValueError):
            apply_plan('owner/repo', config, desired, milestones, issues, ops)
        api.assert_not_called()

    def test_state_basis_update_preserves_task_and_additional_sections(self):
        args = self.fixtures()
        item = args[3]['SPEC-001/T001']
        item['body'] = item['body'].replace(next(x for x in item['body'].splitlines() if x.startswith('- State basis:')),
                                          '- State basis: Source checkbox in tasks.md.') + '\n## Retained note\nKeep me.\n'
        before = item['body']; ops = build_plan(*args)
        self.assertEqual(['set_state', 'update_state_basis'], [op['action'] for op in ops])
        with patch('scripts.sync_github_tracking.gh_api', side_effect=lambda *a, **kw: {**item, **kw['body']}) as api, redirect_stdout(io.StringIO()):
            apply_plan('owner/repo', args[0], args[1], args[2], args[3], ops)
        after = api.call_args.kwargs['body']['body']
        self.assertEqual(before.split('- State basis:')[0], after.split('- State basis:')[0])
        self.assertTrue(after.endswith('\n## Retained note\nKeep me.\n'))

    def test_milestone_scope_does_not_close_unrelated_items(self):
        config, desired, milestones, issues, extra = self.fixtures()
        config.update(milestone_numbers={'M': 1, 'Other': 2})
        config['milestones']['Other'] = 'other'
        other = dict(key='SPEC-999', kind='spec', title='Unrelated', state='closed', parent=None, milestone='Other')
        desired.append(other); milestones['Other'] = {'number': 2, 'state': 'open'}
        issues['SPEC-999'] = dict(number=9, id=9, title='Unrelated', state='open', milestone={'number': 2})
        plan = milestone_plan(config, desired, milestones, issues, extra, 1)[-1]
        self.assertEqual({'SPEC-001/T001'}, {op['key'] for op in plan})
