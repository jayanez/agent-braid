# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-075 T012 (REQ-012 / SC-012): spec, tasks, validation plan, assurance, evidence and documentation agree."""
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / 'specs/075-lightning-dataset-export'
DOC = ROOT / 'docs/tooling/LIGHTNING.md'
STALE = (r'lands with T0\d\d', r'waits for T0\d\d', r'until T0\d\d', r'\(T0\d\d\) are not exercised',
         r'is T0\d\d\b(?!:)', r'no SPEC-074 file change', r'same cutoff')


def text(name):
    return (SPEC / name).read_text()


class ConvergeTests(unittest.TestCase):
    def setUp(self):
        self.assurance = json.loads(text('assurance.json'))

    def test_every_requirement_has_one_scenario_procedure_task_and_evidence(self):
        spec, tasks, plan = text('spec.md'), text('tasks.md'), text('validation-plan.md')
        for requirement in self.assurance['requirements']:
            number = requirement['id'][4:]
            (scenario,) = requirement['scenarios']
            with self.subTest(requirement=requirement['id']):
                self.assertEqual(scenario['id'], f'SC-{number}')
                self.assertIn(f"### {requirement['id']}", spec)
                self.assertIn(f"procedure_{number}", plan)
                self.assertRegex(tasks, rf"- \[x\] T\d\d\d \([^)]*REQ-{number}\b")
                if requirement['id'] == 'REQ-012':
                    continue  # this module is procedure_012's own run; its record is written after it passes
                self.assertTrue(scenario['obtained_evidence'], 'no obtained evidence')
                for item in scenario['obtained_evidence']:
                    self.assertTrue((ROOT / item['path']).exists(), item['path'])
                    # test procedures pass; procedure_001 is the owner review record
                    self.assertTrue(item['outcome'].startswith('passed') or requirement['id'] == 'REQ-001',
                                    item['outcome'][:40])

    def test_every_task_is_done_and_every_procedure_has_a_record(self):
        tasks = text('tasks.md')
        self.assertNotIn('- [ ]', tasks)
        for number in (*range(2, 12), 13):  # procedure_012 is this module's own record, written after it passes
            with self.subTest(procedure=number):
                self.assertTrue((SPEC / f'evidence/procedure_{number:03d}.json').exists())

    def test_no_stale_forward_reference_or_false_claim(self):
        script = (ROOT / 'scripts/spec075_capture_evidence.py').read_text()
        for name, body in [(p.name, p.read_text()) for p in SPEC.rglob('*.md')] + [('capture script', script)]:
            for pattern in STALE:
                with self.subTest(file=name, pattern=pattern):
                    self.assertIsNone(re.search(pattern, body), name)

    def test_owner_decisions_and_residual_risks_are_stated(self):
        spec = text('spec.md')
        for phrase in ('OD-1 — Host usage-terms review (open, deferred', 'OD-2 — Balance default (decided',
                       'OD-3 — Canaries', 'OD-4 — Additive `lightning purge` output', 'catches known shapes only',
                       'nothing here shows that any dataset or its\nbalance improves a model'):
            self.assertIn(phrase, spec)
        for row in range(1, 11):
            self.assertRegex(spec, rf'\n\| A{row} \|')
        self.assertIn('SPEC-074 behaviour is assumed', self.assurance['scientific_limits'])

    def test_user_documentation_says_what_the_export_does_not_do(self):
        doc = ' '.join(DOC.read_text().split())
        for phrase in ('Off by default', 'export-disabled', "No provider's terms of use have been reviewed",
                       'terms-gate-missing', 'only fixture runs', 'ships no terms decision record',
                       'catches known shapes only', 'canary-detected', 'Outside purge', 'delete them yourself',
                       'retention-expired', 'no claim that a dataset or its balance helps any model'):
            self.assertIn(phrase, doc)
        for link in re.findall(r'\]\((\.\./[^)#]+)', DOC.read_text()):
            self.assertTrue((DOC.parent / link).resolve().exists(), link)

    def test_the_help_text_matches_the_documentation(self):
        from agent_braid import lightning_cli
        helptext = ' '.join(lightning_cli.EXPORT_HELP.split())
        for phrase in ('OFF by default', 'export-disabled', "No provider's terms have been reviewed",
                       'catches known shapes only', 'outside lightning purge', 'retention-expired'):
            self.assertIn(phrase, helptext)

    def test_no_terms_decision_record_ships(self):
        found = [p for p in ROOT.rglob('*.json') if not any(part.startswith('.') for part in p.relative_to(ROOT).parts)
                 and b'braid-lightning-terms-decision/v0.1' in p.read_bytes()]
        self.assertEqual(found, [])

    def test_coordinator_owned_files_are_not_cited_as_changed(self):
        for name in ('ROADMAP.md', 'docs/development/SPEC_MILESTONE_INDEX.md', 'docs/development/github-tracking.json'):
            self.assertNotIn(name, self.assurance['references'])


if __name__ == '__main__':
    unittest.main()
