# SPDX-License-Identifier: AGPL-3.0-only
"""Independent transition and refusal controls for the closed workload model."""
from copy import deepcopy
import hashlib
import unittest

from research.workload_lab.model import (
    INPUT_BYTES, LIMIT, MODEL, InvalidWorkload, canonical, declared_effects,
    digest, footprint, initial_config, loads, resolve, step, validate,
)


def operation(identifier='a', kind='snapshot-read', resource='x', **fields):
    return {'id': identifier, 'kind': kind, 'resource': resource,
            'dependencies': [], 'outcomes': ['success'], **fields}


def request(operations=None):
    return {'model': MODEL, 'initial': {'state': {'x': 10, 'y': 4},
            'versions': {'x': 0, 'y': 2}, 'aliases': {'alias': 'x', 'chain': 'alias'}},
            'operations': [operation()] if operations is None else operations,
            'observation': {'mode': 'exact'},
            'caps': {'paths': 20000, 'steps': 120000, 'events': 240000}}


def add(left, right):
    return {'op': 'add', 'left': left, 'right': right}


class WorkloadModelTests(unittest.TestCase):
    def test_private_state_alias_results_versions(self):
        r = request([operation(resource='chain'), operation('b', 'literal-write', value=17)])
        original = deepcopy(r)
        validated = validate(r)
        self.assertEqual(validated, original)
        validated['initial']['state']['x'] = 99
        self.assertEqual(r, original)
        c = initial_config(r)
        self.assertEqual(c, {'state': {'x': 10, 'y': 4}, 'versions': {'x': 0, 'y': 2},
                         'aliases': {'alias': 'x', 'chain': 'alias'}, 'results': {},
                         'events': [], 'idempotencyLedger': [], 'pending': ['a', 'b'],
                         'outcome': 'success', 'reason': None})
        self.assertEqual(resolve(r['initial'], 'chain'), 'x')
        after = step(r, c, 'a', 'success')
        self.assertEqual(after['results'], {'a': 10})
        self.assertEqual(after['pending'], ['b'])
        written = step(r, after, 'b', 'success')
        self.assertEqual(written['state'], {'x': 17, 'y': 4})
        self.assertEqual(written['versions'], {'x': 1, 'y': 2})
        self.assertEqual(written['results'], {'a': 10, 'b': 17})
        written['aliases']['alias'] = 'y'
        written['events'].append({})
        self.assertEqual(c, initial_config(r))
        self.assertEqual(r, original)

    def test_all_writes_and_read_kinds_and_transitive_capture(self):
        operations = [operation('a', 'config-read'),
            operation('b', 'literal-write', value=12, dependencies=['a']),
            operation('c', 'derived-write', expression=add({'result': 'a'}, {'int': 1}), dependencies=['b']),
            operation('d', 'guarded-write', expression={'op': 'multiply', 'left': {'result': 'a'}, 'right': {'int': -2}},
                      guard={'op': 'le', 'left': {'result': 'a'}, 'right': {'int': 10}}, dependencies=['c']),
            operation('e', 'add-constant', amount=-3, dependencies=['d'])]
        r = validate(request(operations)); c = initial_config(r)
        for identifier in 'abcde':
            c = step(r, c, identifier, 'success')
        # c deliberately uses captured 10, losing the earlier update to 12.
        self.assertEqual(c['results'], {'a': 10, 'b': 12, 'c': 11, 'd': -20, 'e': -23})
        self.assertEqual(c['state'], {'x': -23, 'y': 4})
        self.assertEqual(c['versions'], {'x': 4, 'y': 2})
        self.assertEqual(c['pending'], [])

    def test_error_and_send_then_error_preserve_prior_effects(self):
        ops = [operation('a', 'literal-write', value=21),
               operation('b', 'external-action', resource='alias', event='send',
                         idempotencyKey='one', outcomes=['success', 'send-then-error']), operation('c')]
        r = validate(request(ops)); c = step(r, initial_config(r), 'a', 'success')
        failed = step(r, c, 'b', 'send-then-error')
        self.assertEqual(failed['events'], [{'operationId': 'b', 'resource': 'x', 'name': 'send', 'value': 21, 'idempotencyKey': 'one'}])
        self.assertEqual(failed['results'], {'a': 21, 'b': 1})
        self.assertEqual(failed['pending'], ['c'])
        self.assertEqual((failed['outcome'], failed['reason']), ('error', 'send-then-error'))
        self.assertEqual(failed['idempotencyLedger'], ['one'])
        self.assertEqual(failed['versions'], {'x': 1, 'y': 2})
        self.assertEqual(c['events'], [])
        r['operations'][1]['outcomes'] = ['error']
        generic = step(r, c, 'b', 'error')
        self.assertEqual(generic['events'], [])
        self.assertEqual(generic['results'], {'a': 21})
        self.assertEqual(generic['pending'], ['c'])
        self.assertEqual(generic['state'], {'x': 21, 'y': 4})
        with self.assertRaises(InvalidWorkload):
            step(r, generic, 'c', 'success')

    def test_idempotency_is_local_and_events_are_not_resource_writes(self):
        ops = [operation('a', 'external-action', event='send', idempotencyKey='key'),
               operation('b', 'external-action', resource='alias', event='different', idempotencyKey='key'),
               operation('c', 'external-action', event='send')]
        r = validate(request(ops)); c = initial_config(r)
        for identifier in 'abc':
            c = step(r, c, identifier, 'success')
        self.assertEqual(c['results'], {'a': 1, 'b': 0, 'c': 1})
        self.assertEqual(c['events'], [
            {'operationId': 'a', 'resource': 'x', 'name': 'send', 'value': 10, 'idempotencyKey': 'key'},
            {'operationId': 'c', 'resource': 'x', 'name': 'send', 'value': 10, 'idempotencyKey': None}])
        self.assertEqual(c['versions'], {'x': 0, 'y': 2})
        self.assertEqual(step(r, initial_config(r), 'a', 'success')['results'], {'a': 1})

    def test_blocking_guard_version_dependencies_and_missing_capture(self):
        variants = [operation(requiredVersion=1),
            operation(kind='guarded-write', expression={'int': 8},
                      guard={'op': 'lt', 'left': {'int': 2}, 'right': {'int': 1}})]
        for op, reason in zip(variants, ['stale-version', 'false-guard']):
            r = validate(request([op])); c = initial_config(r)
            blocked = step(r, c, 'a', 'success')
            self.assertEqual(blocked, {**c, 'outcome': 'blocked', 'reason': reason})
        r = validate(request([operation(), operation('b', dependencies=['a'])]))
        c = initial_config(r); c['pending'] = ['b', 'a']
        self.assertEqual(step(r, c, 'b', 'success')['reason'], 'unmet-dependency')
        r['operations'][1] = operation('b', 'derived-write', expression={'result': 'a'}, dependencies=['a'])
        c['results']['a'] = 10
        c['pending'] = ['b']
        del c['results']['a']
        self.assertEqual(step(r, c, 'b', 'success'), {**c, 'outcome': 'blocked', 'reason': 'missing-capture'})
        with self.assertRaises(InvalidWorkload):
            step(r, initial_config(r), 'b', 'success')
        with self.assertRaises(InvalidWorkload):
            step(r, initial_config(r), 'a', 'send-then-error')

    def test_arithmetic_and_version_overflow_are_atomic(self):
        expressions = [add({'int': LIMIT}, {'int': 1}),
                       {'op': 'subtract', 'left': {'int': -LIMIT}, 'right': {'int': 1}},
                       {'op': 'multiply', 'left': {'int': LIMIT}, 'right': {'int': 2}},
                       add(add({'int': LIMIT}, {'int': 1}), {'int': -1})]
        ops = [operation(kind='derived-write', expression=e) for e in expressions]
        ops += [operation(kind='add-constant', amount=LIMIT), operation(kind='literal-write', value=0)]
        for i, op in enumerate(ops):
            r = request([op, operation('b')])
            if i == len(ops) - 1:
                r['initial']['versions']['x'] = LIMIT
            r = validate(r); before = initial_config(r)
            after = step(r, before, 'a', 'success')
            self.assertEqual(after['state'], before['state'])
            self.assertEqual(after['versions'], before['versions'])
            self.assertEqual(after['results'], {})
            self.assertEqual(after['pending'], ['b'])
            self.assertEqual(after['outcome'], 'error')
            self.assertEqual(after['reason'], 'version-overflow' if i == len(ops) - 1 else 'arithmetic-overflow')
        for bound in [-LIMIT, 0, LIMIT]:
            r = request([operation(kind='literal-write', value=bound)])
            self.assertEqual(step(r, initial_config(r), 'a', 'success')['state']['x'], bound)

    def test_footprints_include_alias_versions_and_captured_resources(self):
        read = operation(resource='chain')
        write = operation('b', 'guarded-write', resource='y', dependencies=['a'],
                          expression={'result': 'a'}, guard={'op': 'eq', 'left': {'result': 'a'}, 'right': {'int': 10}},
                          requiredVersion=2,
                          effects={'complete': True, 'reads': ['alias', 'y'], 'writes': ['y'], 'emits': []})
        r = validate(request([read, write]))
        self.assertEqual(footprint(r, write), {'reads': {'x', 'y'}, 'writes': {'y'}, 'emits': set()})
        self.assertEqual(declared_effects(r, write), {'known': True, 'reads': ['x', 'y'], 'writes': ['y'], 'emits': [], 'reasons': []})
        self.assertFalse(declared_effects(r, read)['known'])
        write['effects']['reads'] = ['y']
        self.assertEqual(declared_effects(r, write)['reasons'], ['missing-reads'])
        write['effects']['complete'] = False
        self.assertIn('incomplete-declaration', declared_effects(r, write)['reasons'])
        external = operation(kind='external-action', event='send', effects={'complete': True, 'reads': [], 'writes': [], 'emits': ['alias']})
        r = validate(request([external]))
        self.assertEqual(footprint(r, external), {'reads': {'x'}, 'writes': set(), 'emits': {'x'}})
        self.assertFalse(declared_effects(r, external)['known'])
        literal = operation(kind='literal-write', value=1, requiredVersion=0)
        self.assertEqual(footprint(request([literal]), literal)['reads'], {'x'})

    def test_declarations_extra_resources_conservative_and_cannot_change_effects(self):
        op = operation(kind='literal-write', value=7,
                       effects={'complete': True, 'reads': ['x', 'y'], 'writes': ['x', 'y'], 'emits': ['y']})
        r = validate(request([op]))
        self.assertTrue(declared_effects(r, op)['known'])
        c = step(r, initial_config(r), 'a', 'success')
        self.assertEqual(c['state'], {'x': 7, 'y': 4})
        self.assertEqual(c['events'], [])
        op['effects']['writes'] = []
        self.assertFalse(declared_effects(r, op)['known'])
        self.assertEqual(step(r, initial_config(r), 'a', 'success'), c)

    def test_guard_operators_and_stale_external_block_before_effect(self):
        for operator, left, right in [('eq', 1, 1), ('lt', -1, 0), ('le', 0, 0)]:
            op = operation(kind='guarded-write', expression={'op': 'subtract', 'left': {'int': 5}, 'right': {'int': 2}},
                           guard={'op': operator, 'left': {'int': left}, 'right': {'int': right}})
            r = validate(request([op]))
            self.assertEqual(step(r, initial_config(r), 'a', 'success')['results'], {'a': 3})
        r = validate(request([operation(kind='external-action', event='send', requiredVersion=1, outcomes=['send-then-error'])]))
        c = initial_config(r)
        self.assertEqual(step(r, c, 'a', 'send-then-error'), {**c, 'outcome': 'blocked', 'reason': 'stale-version'})

    def test_reject_unsafe_and_malformed_requests(self):
        def mutation(path, value):
            r = request(); target = r
            for key in path[:-1]: target = target[key]
            target[path[-1]] = value
            return r
        cases = [mutation(['extra'], 'https://example.invalid'), mutation(['operations', 0, 'kind'], 'eval'),
            mutation(['operations', 0, 'resource'], 'missing'), mutation(['operations', 0, 'dependencies'], ['a']),
            mutation(['operations', 0, 'dependencies'], ['missing']), mutation(['operations', 0, 'outcomes'], []),
            mutation(['operations', 0, 'outcomes'], ['success', 'success']), mutation(['operations', 0, 'outcomes'], ['send-then-error']),
            mutation(['operations', 0, 'requiredVersion'], True), mutation(['initial', 'versions'], {'x': 0}),
            mutation(['initial', 'aliases'], {'a': 'b', 'b': 'a'}), mutation(['initial', 'aliases'], {'a': 'b', 'b': []}),
            mutation(['initial', 'aliases'], {'x': 'y'}), mutation(['initial', 'aliases'], {'alias': 'missing'}),
            mutation(['initial', 'state', 'x'], False), mutation(['initial', 'versions', 'x'], -1),
            mutation(['operations'], [operation(), operation()]), mutation(['operations'], []),
            mutation(['operations'], [operation(str(i)) for i in range(7)]),
            mutation(['operations', 0, 'value'], 1), mutation(['operations', 0, 'id'], '\ud800'),
            mutation(['initial', 'aliases'], {'alias': '\udfff'}), mutation(['caps', 'paths'], 20001),
            mutation(['caps', 'steps'], 120001), mutation(['caps', 'events'], 240001),
            mutation(['caps', 'paths'], -1), mutation(['caps', 'paths'], False),
            mutation(['observation'], {'mode': 'selected-values', 'resources': ['x', 'alias']})]
        for r in cases:
            with self.subTest(request=r), self.assertRaises(InvalidWorkload): validate(r)
        for source in ['b', 'a', 'missing']:
            r = request([operation(), operation('b', 'derived-write', expression={'result': source}, dependencies=['a'])])
            with self.subTest(source=source):
                if source == 'a': validate(r)
                else:
                    with self.assertRaises(InvalidWorkload): validate(r)
        r = request([operation('a', 'literal-write', value=1), operation('b', 'derived-write', expression={'result': 'a'}, dependencies=['a'])])
        with self.assertRaises(InvalidWorkload): validate(r)
        r = request([operation('a', dependencies=['b']), operation('b', dependencies=['a'])])
        with self.assertRaises(InvalidWorkload): validate(r)
        for expression in [{'int': 1, 'result': 'a'}, {'op': 'eval', 'left': {'int': 1}, 'right': {'int': 2}}, {'result': 'a', 'code': 'print(1)'}]:
            r = request([operation(kind='derived-write', expression=expression)])
            with self.assertRaises(InvalidWorkload): validate(r)

    def test_exact_numeric_name_counts_depth_and_zero_boundaries(self):
        r = request(); r['caps'] = {'paths': 0, 'steps': 0, 'events': 0}
        r['initial']['state']['x'] = -LIMIT; r['initial']['versions']['x'] = LIMIT
        r['operations'][0]['id'] = '😀' * 256
        validate(r)
        r = request([operation(str(i)) for i in range(6)])
        r['initial']['aliases'] = {}
        validate(r)
        r['initial']['aliases'] = {f'a{i}': 'x' for i in range(65)}
        with self.assertRaises(InvalidWorkload): validate(r)
        for count in [1, 64]:
            r = request(); r['initial'] = {'state': {str(i): 0 for i in range(count)}, 'versions': {str(i): 0 for i in range(count)}, 'aliases': {f'a{i}': '0' for i in range(64)}}; r['operations'][0]['resource'] = '0'; validate(r)
        for count in [0, 65]:
            r = request(); r['initial']['state'] = {str(i): 0 for i in range(count)}
            with self.assertRaises(InvalidWorkload): validate(r)
        for value in [-LIMIT - 1, LIMIT + 1, 0.0, True]:
            r = request([operation(kind='literal-write', value=value)])
            with self.assertRaises(InvalidWorkload): validate(r)
        for length in [0, 257]:
            r = request(); r['operations'][0]['id'] = 'a' * length
            with self.assertRaises(InvalidWorkload): validate(r)
        expression = {'int': 0}
        for _ in range(12): expression = add(expression, {'int': 0})
        validate(request([operation(kind='derived-write', expression=expression)]))
        with self.assertRaises(InvalidWorkload):
            validate(request([operation(kind='derived-write', expression=add(expression, {'int': 0}))]))

    def test_strict_json_canonical_and_digest_boundaries(self):
        value = {'z': 'España 😀', 'a': True}
        self.assertEqual(canonical(value), b'{"a":true,"z":"Espa\\u00f1a \\ud83d\\ude00"}')
        self.assertEqual(digest(value), hashlib.sha256(canonical(value)).hexdigest())
        self.assertEqual(loads(canonical(value)), value)
        invalid = ['{"x":1,"x":2}', '{"a":{"x":1,"x":2}}', '1.0', 'NaN', 'Infinity', '"\\ud800"', '{"\\udfff":1}', '1e0', '[' * 66 + '0' + ']' * 66]
        for text in invalid:
            with self.subTest(text=text), self.assertRaises(InvalidWorkload): loads(text)
        for value in [float('nan'), float('inf'), 1.0, {'\ud800': 1}, '\udfff', {1: 'x'}, (1,), LIMIT + 1]:
            with self.subTest(value=value), self.assertRaises(InvalidWorkload): canonical(value)
        nested = 0
        for _ in range(64): nested = [nested]
        canonical(nested)
        with self.assertRaises(InvalidWorkload): canonical([nested])
        self.assertEqual(loads(' ' * (INPUT_BYTES - 1) + '0'), 0)
        with self.assertRaises(InvalidWorkload): loads(' ' * INPUT_BYTES + '0')
        with self.assertRaises(InvalidWorkload): loads(b'\xff')

    def test_explicit_transport_limit_preserves_request_default(self):
        larger_report = ' ' * INPUT_BYTES + '0'
        with self.assertRaises(InvalidWorkload): loads(larger_report)
        self.assertEqual(loads(larger_report, limit=INPUT_BYTES + 1), 0)
        self.assertEqual(loads('0', limit=1), 0)
        self.assertEqual(loads(b'0', limit=1), 0)
        for text, limit in [('0', 0), (' 0', 1), ('"é"', 3)]:
            with self.subTest(text=text, limit=limit), self.assertRaises(InvalidWorkload):
                loads(text, limit=limit)
        self.assertEqual(loads('"é"', limit=4), 'é')
        for limit in [-1, True, False, 1.0, None, '1']:
            with self.subTest(limit=limit), self.assertRaises(InvalidWorkload):
                loads('0', limit=limit)
        # A larger transport allowance never relaxes strict JSON content rules.
        with self.assertRaises(InvalidWorkload): loads('1.0', limit=512 * 1024 * 1024)
