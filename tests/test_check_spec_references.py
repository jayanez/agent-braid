# SPDX-License-Identifier: AGPL-3.0-only
"""The mechanical cross-reference check finds broken citations, gaps and cycles; no model is used."""
import json
import tempfile
import unittest
from pathlib import Path

from scripts import check_spec_references as refs

SPEC = """# Feature

#### REQ-001 — First
- **SC-001** Given a, when b, then c.

#### REQ-002 — Second
- **SC-002** Given a, when b, then c.

- **OD-1 — A decision.** Used by REQ-001; see OD-2.
- **OD-2 — Another.** Used by REQ-002 and OD-1.
"""
TASKS = """# Tasks

- [ ] T001 (OD-1..OD-2): Owner review.
- [ ] T002 (REQ-001 / SC-001): Build. Files: `tests/test_a.py`. Dependencies: T001. Verification: tests.
- [ ] T003 (REQ-002 / SC-002): Build more. Files: `tests/test_b.py`. Dependencies: T002. Verification: tests.
"""
PLAN = """| REQ | SC | Planned test file | Planned test | Planned evidence |
|---|---|---|---|---|
| REQ-001 | SC-001 | `tests/test_a.py` | `A.test_a` | Output of T002. |
| REQ-002 | SC-002 | `tests/test_b.py` | `B.test_b` | Output of T003. |
"""


def assurance(*pairs):
    return json.dumps({'requirements': [{'id': r, 'scenarios': [{'id': s} for s in scenarios]}
                                        for r, scenarios in pairs]})


class ReferenceCheckTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.specs = Path(tmp.name).resolve() / 'specs'

    def feature(self, name, *, spec=SPEC, tasks=TASKS, plan=PLAN, record=None):
        folder = self.specs / name
        folder.mkdir(parents=True)
        (folder / 'spec.md').write_text(spec)
        (folder / 'tasks.md').write_text(tasks)
        (folder / 'validation-plan.md').write_text(plan)
        (folder / 'assurance.json').write_text(
            record or assurance(('REQ-001', ['SC-001']), ('REQ-002', ['SC-002'])))
        return folder

    def test_a_consistent_feature_passes(self):
        self.assertEqual(refs.check([self.feature('001-clean')]), ([], []))

    def test_an_undefined_citation_is_an_error(self):
        errors, _ = refs.check([self.feature('001-a', spec=SPEC + '\nSee REQ-009 and OD-7.\n')])
        self.assertEqual(len(errors), 2)
        self.assertIn('001-a/spec.md:12: REQ-009 is cited but not defined', errors)

    def test_a_range_is_expanded(self):
        errors, _ = refs.check([self.feature('001-a', spec=SPEC + '\nCovers SC-001 to SC-003.\n')])
        self.assertEqual(errors, ['001-a/spec.md:12: SC-003 is cited but not defined'])

    def test_a_requirement_without_scenario_or_task_is_an_error(self):
        record = assurance(('REQ-001', ['SC-001']), ('REQ-002', ['SC-002']), ('REQ-003', []))
        errors, _ = refs.check([self.feature('001-a', spec=SPEC + '\n#### REQ-003 — Third\n', record=record)])
        self.assertIn('001-a: REQ-003 has no acceptance scenario', errors)
        self.assertIn('001-a: REQ-003 is not traced by any task', errors)

    def test_a_stale_owner_review_range_is_an_error(self):
        spec = SPEC + '- **OD-3 — Late decision.** Used by REQ-001 and OD-3.\n'
        errors, _ = refs.check([self.feature('001-a', spec=spec)])
        self.assertEqual(errors, ['001-a/tasks.md: T001 covers OD-1..OD-2 but the highest decision is OD-3'])

    def test_a_plan_file_outside_the_owning_task_is_an_error(self):
        errors, _ = refs.check([self.feature('001-a', plan=PLAN.replace('test_b.py', 'test_c.py'))])
        self.assertEqual(errors, ['001-a/validation-plan.md:4: tests/test_c.py (SC-002) is not in the files of T003'])

    def test_a_cycle_across_two_features_is_an_error(self):
        one = self.feature('001-a', tasks=TASKS.replace('Dependencies: T001.', 'Dependencies: T001, SPEC-002 T003.'))
        two = self.feature('002-b', tasks=TASKS.replace('Dependencies: T002.', 'Dependencies: T002, SPEC-001 T002.'))
        errors, _ = refs.check([one, two])
        self.assertEqual(len(errors), 1)
        self.assertTrue(errors[0].startswith('dependency cycle: '))

    def test_a_citation_into_another_feature_is_resolved_there(self):
        self.feature('002-b')
        good = self.feature('001-a', spec=SPEC + '\nUses SPEC-002 OD-1, OD-2 and SPEC-002 T003.\n')
        self.assertEqual(refs.check([good])[0], [])
        bad = self.feature('003-c', spec=SPEC + '\nUses SPEC-002 OD-9 and SPEC-077 T001.\n')
        self.assertEqual(refs.check([bad])[0], ['003-c/spec.md:12: SPEC-002 OD-9 is cited but not defined',
                                                '003-c/spec.md:12: SPEC-077 does not exist'])

    def test_warnings_do_not_fail_and_a_retired_task_id_is_known(self):
        tasks = TASKS + '- [ ] T005: Housekeeping. Dependencies: T003.\n\nTask ID T004 is retired: never assigned.\n'
        spec = SPEC + '- **OD-3 — Unused.**\n'
        errors, warnings = refs.check([self.feature('001-a', spec=spec, tasks=tasks.replace('OD-2)', 'OD-3)'))])
        self.assertEqual(errors, [])
        self.assertEqual(warnings, ['001-a/tasks.md: T005 names no requirement', '001-a: OD-3 is defined and never cited'])

    def test_the_command_fails_on_errors_and_refuses_a_non_feature(self):
        self.assertEqual(refs.main([str(self.feature('001-a'))]), 0)
        self.assertEqual(refs.main([str(self.feature('002-b', spec=SPEC + '\nSee T099.\n'))]), 1)
        self.assertEqual(refs.main([str(self.specs)]), 2)


if __name__ == '__main__':
    unittest.main()
