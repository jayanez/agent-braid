# SPDX-License-Identifier: AGPL-3.0-only
"""Small independently authored software fixtures, never research evaluation data."""
from copy import deepcopy
from hashlib import sha1
import json
from pathlib import Path
import unittest

from agent_braid.system_one import canonical, freeze, thaw
from agent_braid.system_one_verified_ir import interpret, render, validate_program, verify_program

FIXTURE = Path(__file__).parent / 'fixtures' / 'system_one_verified_ir.json'


def blob(lines):
    if lines is None:
        return '0' * 40
    raw = ''.join(lines).encode()
    return sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()


def hunk(base, begin, end, new, patch=None):
    old = None if base is None else base[begin:end]
    return {'begin': begin, 'end': end, 'old': old, 'new': new,
            'atStart': begin == 0, 'atEnd': base is None or end == len(base),
            'patchLines': patch if patch is not None else
            ([] if old is None else ['-' + line for line in old]) + ['+' + line for line in new]}


def change(path, base, hunks):
    if base is None:
        final = hunks[0]['new']
    else:
        final, cursor = [], 0
        for fragment in hunks:
            final += base[cursor:fragment['begin']] + fragment['new']
            cursor = fragment['end']
        final += base[cursor:]
    return {'path': path, 'old': blob(base), 'new': blob(final), 'hunks': hunks}


def program(files, changes, goal):
    return {'files': files, 'goal': {path: blob(lines) for path, lines in goal.items()},
            'ops': {name: {'dependencies': [], 'changes': value} for name, value in changes.items()},
            'plans': {'k0': list(reversed(changes)), 'k1': [], 'k2': list(changes), 'wait': None}}


def checkpoint(_stage, _units):
    return None


class VerifiedIRTests(unittest.TestCase):
    def setUp(self):
        self.fixture_bytes = FIXTURE.read_bytes()
        self.value = json.loads(self.fixture_bytes)['program']

    def verify(self, value=None, order=None, maximum=128, check=checkpoint):
        value = self.value if value is None else value
        return verify_program(value, tuple(value['plans']) if order is None else order,
                              max_hunks=maximum, checkpoint=check)

    def test_completed_exact_shape_lexical_ties_and_every_plan(self):
        result = self.verify(order=('k2', 'wait', 'k1', 'k0'))
        self.assertEqual(set(result), {'status', 'eligible', 'choice', 'plans', 'executionAuthorization'})
        self.assertEqual(result['status'], 'answered')
        self.assertEqual(result['eligible'], ('k0', 'k2'))
        self.assertEqual(result['choice'], 'k0')
        self.assertEqual(tuple(result['plans']), ('k2', 'k1', 'k0'))
        self.assertFalse(result['plans']['k1']['valid'])
        self.assertEqual(result['plans']['k1']['failure'], {'step': 0, 'reason': 'final-goal'})
        self.assertFalse(result['executionAuthorization'])
        self.assertEqual(result['plans']['k0']['finalBlobs'], self.value['goal'])

    def test_frozen_inputs_outputs_and_caller_data_unchanged(self):
        before = canonical(self.value)
        validated = validate_program(freeze(self.value), checkpoint=checkpoint)
        result = self.verify(validated)
        with self.assertRaises(TypeError):
            validated['files']['sample.txt'][0] = 'changed\n'
        with self.assertRaises(TypeError):
            result['choice'] = 'k2'
        self.assertEqual(canonical(self.value), before)
        self.assertEqual(FIXTURE.read_bytes(), self.fixture_bytes)

    def test_exact_en_es_symbolic_controlled_roundtrips(self):
        # Deliberately preserve an unsorted offered-plan insertion order.
        self.value['plans'] = {key: self.value['plans'][key] for key in ('wait', 'k2', 'k0', 'k1')}
        for language in ('en', 'es'):
            for representation in ('symbolic', 'controlled'):
                with self.subTest(language=language, representation=representation):
                    payload = render(freeze(self.value), language, representation, checkpoint=checkpoint)
                    restored = interpret(payload, checkpoint=checkpoint)
                    self.assertEqual(restored, freeze(self.value))
                    self.assertEqual(tuple(restored['plans']), ('wait', 'k2', 'k0', 'k1'))
                    self.assertEqual(render(restored, language, representation, checkpoint=checkpoint), payload)
                    self.assertFalse(payload['executionAuthorization'])

    def test_rendered_grammar_matches_independently_stored_text(self):
        expected = json.loads(self.fixture_bytes)['controlledEn']
        self.assertEqual(render(self.value, 'en', 'controlled', checkpoint=checkpoint)['text'], expected)

    def test_k0_invalid_does_not_hide_valid_other_option(self):
        self.value['plans']['k0'] = ['a', 'a', 'b']
        result = self.verify()
        self.assertEqual(result['eligible'], ('k2',))
        self.assertEqual(result['choice'], 'k2')
        self.assertEqual(result['plans']['k0']['failure'], {'step': 1, 'reason': 'operation-precondition'})
        self.assertEqual(result['plans']['k0']['cost'], 3)

    def test_dependency_failure_and_cycle_are_different(self):
        self.value['ops']['b']['dependencies'] = ['a']
        result = self.verify()
        self.assertEqual(result['eligible'], ('k2',))
        self.assertEqual(result['plans']['k0']['failure']['reason'], 'operation-precondition')
        self.value['ops']['a']['dependencies'] = ['b']
        with self.assertRaisesRegex(ValueError, '^invalid-ir$'):
            self.verify()

    def test_wrong_goal_is_completed_semantic_defer(self):
        self.value['goal']['sample.txt'] = '1' * 40
        result = self.verify()
        self.assertEqual(result['status'], 'semantic-defer')
        self.assertEqual(result['eligible'], ('wait',))
        self.assertEqual(result['choice'], 'wait')
        self.assertTrue(result['plans']['k0']['complete'])
        self.assertFalse(result['plans']['k0']['goalAchieved'])
        self.assertEqual(result['plans']['k0']['failure']['reason'], 'final-goal')

    def test_eof_with_retained_tail_context_allows_reorder(self):
        base = ['head\n', 'body\n', 'tail\n']
        a = change('x.txt', base, [hunk(base, 1, 3, ['BODY\n', 'tail\n'],
                                         ['-body\n', '+BODY\n', ' tail\n'])])
        b = change('x.txt', base, [hunk(base, 2, 3, ['tail\n', 'extra\n'], [' tail\n', '+extra\n'])])
        value = program({'x.txt': base}, {'a': [a], 'b': [b]},
                        {'x.txt': ['head\n', 'BODY\n', 'tail\n', 'extra\n']})
        result = self.verify(value)
        self.assertEqual(result['eligible'], ('k0', 'k2'))
        self.assertEqual(result['plans']['k0']['trace'][1]['fragments'][0]['position'], 1)

    def test_terminal_edit_without_retained_context_stays_at_eof(self):
        base = ['head\n', 'tail\n']
        a = change('x.txt', base, [hunk(base, 1, 2, ['TAIL\n'])])
        b = change('x.txt', base, [hunk(base, 1, 2, ['tail\n', 'extra\n'], [' tail\n', '+extra\n'])])
        value = program({'x.txt': base}, {'a': [a], 'b': [b]}, {'x.txt': ['head\n', 'TAIL\n', 'extra\n']})
        result = self.verify(value)
        self.assertEqual(result['status'], 'semantic-defer')
        self.assertEqual(result['plans']['k0']['failure'], {'step': 1, 'reason': 'missing-context'})

    def test_bof_remains_strict_even_with_context(self):
        base = ['head\n', 'tail\n']
        a = change('x.txt', base, [hunk(base, 0, 2, ['HEAD\n', 'tail\n'],
                                         ['-head\n', '+HEAD\n', ' tail\n'])])
        b = change('x.txt', base, [hunk(base, 0, 1, ['intro\n', 'head\n'], ['+intro\n', ' head\n'])])
        value = program({'x.txt': base}, {'a': [a], 'b': [b]}, {'x.txt': ['intro\n', 'HEAD\n', 'tail\n']})
        self.assertEqual(self.verify(value)['plans']['k0']['failure'],
                         {'step': 1, 'reason': 'missing-context'})

    def test_four_operations_two_hunks_and_multiple_files(self):
        x, y = ['a\n', 'b\n', 'c\n', 'd\n', 'e\n'], ['u\n', 'v\n', 'w\n']
        changes = {
            'a': [change('x.txt', x, [hunk(x, 0, 1, ['A\n']), hunk(x, 2, 3, ['C\n'])])],
            'b': [change('x.txt', x, [hunk(x, 4, 5, ['E\n'])])],
            'c': [change('y.txt', y, [hunk(y, 0, 1, ['U\n'])])],
            'd': [change('y.txt', y, [hunk(y, 2, 3, ['W\n'])])],
        }
        value = program({'x.txt': x, 'y.txt': y}, changes,
                        {'x.txt': ['A\n', 'b\n', 'C\n', 'd\n', 'E\n'], 'y.txt': ['U\n', 'v\n', 'W\n']})
        result = self.verify(value)
        self.assertEqual(result['eligible'], ('k0', 'k2'))
        self.assertEqual(len(result['plans']['k2']['trace'][0]['fragments']), 2)
        self.assertEqual(result['plans']['k2']['finalBlobs'], value['goal'])

    def test_failed_multifile_step_does_not_commit_earlier_file(self):
        left, right = ['left\n'], ['right\n']
        changes = {'a': [change('left.txt', left, [hunk(left, 0, 1, ['LEFT\n'])]),
                         change('right.txt', right, [hunk(right, 0, 1, ['AR\n'])])],
                   'b': [change('right.txt', right, [hunk(right, 0, 1, ['BR\n'])])]}
        value = program({'left.txt': left, 'right.txt': right}, changes,
                        {'left.txt': ['LEFT\n'], 'right.txt': ['BR\n']})
        failed = self.verify(value)['plans']['k0']['trace'][1]
        self.assertFalse(failed['committed'])
        self.assertEqual(failed['blobsAfter'], {'left.txt': blob(left), 'right.txt': blob(['BR\n'])})
        self.assertEqual(len(failed['fragments']), 1)

    def test_absent_file_is_explicit_absence_and_addition_not_unknown(self):
        base = ['base\n']
        changes = {'a': [change('new.txt', None, [hunk(None, 0, 0, ['new\n'])])],
                   'b': [change('old.txt', base, [hunk(base, 0, 1, ['OLD\n'])])]}
        value = program({'new.txt': None, 'old.txt': base}, changes,
                        {'new.txt': ['new\n'], 'old.txt': ['OLD\n']})
        self.assertEqual(self.verify(value)['status'], 'answered')
        value['files']['new.txt'] = 'unknown'
        with self.assertRaisesRegex(ValueError, '^invalid-ir$'):
            self.verify(value)

    def test_ambiguous_runtime_anchor_refuses_instead_of_false_candidate(self):
        base = ['p\n', 'q\n', 'z\n']
        value = program({'x.txt': base}, {
            'a': [change('x.txt', base, [hunk(base, 1, 2, ['Q\n'])])],
            'b': [change('x.txt', base, [hunk(base, 2, 3, ['q\n'])])],
        }, {'x.txt': ['p\n', 'Q\n', 'q\n']})
        with self.assertRaisesRegex(ValueError, '^ambiguous-anchor$'):
            self.verify(value)

    def test_malformed_programs_raise_fixed_codes_and_no_partial_result(self):
        mutations = [lambda p: p.update(extra=True),
                     lambda p: p['ops']['a'].update(dependencies=['unknown']),
                     lambda p: p['ops']['a']['changes'][0]['hunks'][0].update(begin=True),
                     lambda p: p['ops']['a']['changes'][0]['hunks'][0]['patchLines'].__setitem__(0, '+alpha\n'),
                     lambda p: p['plans'].update(k2=['unknown']),
                     lambda p: p['plans'].update(k2=None),
                     lambda p: p['files'].update({'../escape.txt': ['bad\n']}),
                     lambda p: p['files']['sample.txt'].__setitem__(0, 'alpha\r\n')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                value = deepcopy(self.value)
                mutate(value)
                with self.assertRaisesRegex(ValueError, '^(invalid-ir|ambiguous-anchor)$'):
                    self.verify(value)

    def test_text_duplicates_omissions_reorder_negation_and_authority_rejected(self):
        payload = thaw(render(self.value, 'es', 'controlled', checkpoint=checkpoint))
        lines = payload['text'].splitlines(keepends=True)
        texts = [payload['text'] + lines[1], ''.join(lines[:-1]),
                 ''.join([lines[0], lines[2], lines[1]] + lines[3:]),
                 payload['text'].replace('Archivo inicial: ', 'No Archivo inicial: ', 1),
                 payload['text'].rstrip('\n'), payload['text'] + 'Unsupported prose.\n']
        for text in texts:
            with self.subTest(text=text[:80]):
                bad = dict(payload, text=text)
                with self.assertRaises(ValueError):
                    interpret(bad, checkpoint=checkpoint)
        for key, value in [('executionAuthorization', True), ('confidence', 1), ('language', 'fr')]:
            bad = dict(payload)
            bad[key] = value
            with self.assertRaisesRegex(ValueError, '^text-mismatch$'):
                interpret(bad, checkpoint=checkpoint)

    def test_inner_json_duplicate_nonfinite_numbers_surrogates_and_depth_rejected(self):
        payload = thaw(render(self.value, 'en', 'symbolic', checkpoint=checkpoint))
        # Each is placed in one literal record: root-envelope parsing cannot hide inner admission.
        bad_literals = ['["k1",{"x":1,"x":2}]', '["k1",[NaN]]', '["k1",[Infinity]]',
                        '["k1",[9223372036854775808]]', '["k1",[1000000000000000000000]]',
                        '["k1",["\\ud800"]]', '["k1",' + '[' * 17 + '0' + ']' * 17 + ']']
        for literal in bad_literals:
            with self.subTest(literal=literal):
                bad = dict(payload, text=payload['text'].replace('PLAN ["k1",[]].', 'PLAN ' + literal + '.'))
                with self.assertRaisesRegex(ValueError, '^text-mismatch$'):
                    interpret(bad, checkpoint=checkpoint)

    def test_source_and_all_candidate_hunks_charge_same_checkpoint(self):
        calls = []
        self.verify(check=lambda stage, units: calls.append((stage, units)))
        self.assertEqual(sum(units for _, units in calls), 6)  # 2 source + 2 per complete candidate
        self.assertTrue(all(stage == 'verification' for stage, _ in calls))
        with self.assertRaisesRegex(ValueError, '^work-budget-exceeded$'):
            self.verify(maximum=5)
        with self.assertRaisesRegex(ValueError, '^work-budget-exceeded$'):
            self.verify(maximum=0)

    def test_outer_hunk_counter_survives_multiple_verifications(self):
        used = 0
        def shared(stage, units):
            nonlocal used
            self.assertEqual(stage, 'verification')
            if used + units > 8:
                raise ValueError('work-budget-exceeded')
            used += units
        self.verify(check=shared)
        self.assertEqual(used, 6)
        with self.assertRaisesRegex(ValueError, '^work-budget-exceeded$'):
            self.verify(check=shared)
        self.assertEqual(used, 8)

    def test_nested_interpret_render_and_validation_charge_source_hunks(self):
        calls = []
        check = lambda stage, units: calls.append((stage, units))
        payload = render(self.value, 'en', 'controlled', checkpoint=check)
        interpret(payload, checkpoint=check)
        validate_program(self.value, checkpoint=check)
        self.assertEqual(sum(units for _, units in calls), 6)
        self.assertTrue(all(stage == 'verification' for stage, units in calls if units))
        self.assertIn(('interpretation', 0), calls)

    def test_trusted_cancellation_and_deadline_propagate_by_identity(self):
        for reason in ('cancelled', 'deadline-exceeded', 'work-budget-exceeded'):
            for entry in ('validate', 'render', 'interpret', 'verify'):
                with self.subTest(reason=reason, entry=entry):
                    marker = ValueError(reason)
                    calls = 0
                    def stop(_stage, _units):
                        nonlocal calls
                        calls += 1
                        if calls == 3:
                            raise marker
                    with self.assertRaises(ValueError) as caught:
                        if entry == 'validate':
                            validate_program(self.value, checkpoint=stop)
                        elif entry == 'render':
                            render(self.value, 'en', 'controlled', checkpoint=stop)
                        elif entry == 'interpret':
                            interpret(render(self.value, 'en', 'controlled', checkpoint=checkpoint), checkpoint=stop)
                        else:
                            self.verify(check=stop)
                    self.assertIs(caught.exception, marker)
                    self.assertEqual(calls, 3)

    def test_cancellation_before_publish_suppresses_completed_answer(self):
        calls = []
        self.verify(check=lambda stage, units: calls.append((stage, units)))
        stop_at = len(calls)
        seen = 0
        def stop(_stage, _units):
            nonlocal seen
            seen += 1
            if seen == stop_at:
                raise ValueError('cancelled')
        with self.assertRaisesRegex(ValueError, '^cancelled$'):
            self.verify(check=stop)
        self.assertEqual(seen, stop_at)

    def test_exact_domain_limits_and_resource_arguments(self):
        for maximum in (-1, 129, True, None):
            with self.subTest(maximum=maximum):
                with self.assertRaisesRegex(ValueError, '^invalid-budget$'):
                    self.verify(maximum=maximum)
        for order in (('k0',) * 4, ('k0', 'k1', 'k2', 'missing'), ['k0', 'k1', 'k2', 'wait']):
            with self.assertRaisesRegex(ValueError, '^invalid-ir$'):
                self.verify(order=order)
        for lines in ([str(i) + '\n' for i in range(65)], ['x' * 4096 + '\n'], [' \n'], ['nul\0\n']):
            value = deepcopy(self.value)
            value['files']['sample.txt'] = lines
            with self.assertRaisesRegex(ValueError, '^invalid-ir$'):
                self.verify(value)

    def test_order_and_option_name_invariance_causal_sensitivity(self):
        baseline = self.verify()
        renamed = deepcopy(self.value)
        renamed['plans'] = {'z2': renamed['plans']['k2'], 'z0': renamed['plans']['k0'],
                            'z1': renamed['plans']['k1'], 'defer': None}
        result = self.verify(renamed)
        self.assertEqual(result['eligible'], ('z0', 'z2'))
        self.assertEqual(result['plans']['z0']['finalBlobs'], baseline['plans']['k0']['finalBlobs'])
        renamed['ops']['b']['dependencies'] = ['a']
        result = self.verify(renamed)
        self.assertEqual(result['eligible'], ('z2',))
        self.assertFalse(result['plans']['z0']['valid'])

    def test_pure_import_boundary(self):
        import agent_braid.system_one_verified_ir as module
        source = Path(module.__file__).read_text()
        self.assertNotIn('research.system_one', source)
        self.assertNotIn('subprocess', source)
        self.assertNotIn('system_one_verified_acquisition', source)


if __name__ == '__main__':
    unittest.main()
