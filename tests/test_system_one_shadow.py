# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 S1.5a: shadow episodes are derived, private, bounded and never change output."""
from __future__ import annotations

from contextlib import redirect_stdout
from copy import deepcopy
from io import StringIO
import fcntl
import itertools
import json
import os
from pathlib import Path
import subprocess
import tempfile
import threading
import types
import unittest
from unittest.mock import patch

from agent_braid import system_one_shadow as shadow
from agent_braid import tooling_mcp, tooling_telemetry
from agent_braid.cli import main
from agent_braid.plugin_mcp import PluginRouter
from agent_braid.plugin_registry import apply, configuration_digest, load, plan_setup
from agent_braid.tooling_mcp import ToolingConfig, ToolingError, ToolingService

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = json.loads((ROOT / 'examples/analysis/file-edits.json').read_text())
SENTINEL = 'SENTINEL-7f3a91c2'


def sentinel_request() -> dict:
    """Two AIM operations with unique sentinel strings in every free-text position."""
    value = deepcopy(SAMPLE)
    value['source']['description'] = SENTINEL + '-description'
    for index, operation in enumerate(value['operations']):
        operation['instanceId'] = f'{SENTINEL}-instance-{index}'
        operation['attemptId'] = f'{SENTINEL}-attempt-{index}'
        operation['effects']['coverage']['domain'] = SENTINEL + '-domain'
        for effect in operation['effects']['declared']:
            effect['resource'] = f'repo://{SENTINEL}/secret/path-{index}.txt'
    return value


def unknown_request() -> dict:
    """One partial-coverage operation makes the pair `unknown` (the DP-1 opportunity)."""
    value = sentinel_request()
    value['operations'][1]['effects']['coverage']['status'] = 'partial'
    return value


def counter_uuid():
    counter = itertools.count(1)
    return types.SimpleNamespace(uuid4=lambda: types.SimpleNamespace(hex=f'{next(counter):032x}'),
                                 UUID=__import__('uuid').UUID)


class Base(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.source = self.base / 'source'
        self.results = self.base / 'results'
        self.store = self.base / 'store'
        self.source.mkdir()
        self.results.mkdir()
        patcher = patch.object(shadow, 'default_directory', return_value=self.store)
        patcher.start()
        self.addCleanup(patcher.stop)
        with shadow._refusal_lock:
            shadow._refusals.clear()
        self.addCleanup(shadow.flush)  # no worker job outlives the store it writes to

    def service(self, mode='shadow', **kwargs):
        return ToolingService(ToolingConfig(self.source, self.results, system_one=mode, **kwargs))

    def episodes(self):
        lines = []
        for path in sorted(self.store.glob('episodes-*.jsonl')):
            lines.extend(json.loads(line) for line in path.read_bytes().splitlines())
        return lines

    def invoke(self, service, request, kind='aim'):
        envelope = service.invoke('analyze-work', {'kind': kind, 'request': request}, threading.Event())
        self.assertTrue(shadow.flush(), 'shadow worker did not finish')
        return envelope


class ConfigTests(Base):
    def test_system_one_mode_is_closed(self):
        for bad in ('on', 'advise', '', None):
            with self.assertRaises(ToolingError):
                ToolingConfig(self.source, self.results, system_one=bad)
        self.assertEqual(ToolingConfig(self.source, self.results).system_one, 'off')


class ParityTests(Base):
    """SC-001: envelopes in shadow mode are byte-identical to off mode."""

    def envelope_bytes(self, mode, call):
        with patch.object(tooling_mcp, 'uuid', counter_uuid()):
            service = self.service(mode)
            value = json.dumps(call(service), sort_keys=True).encode()
            self.assertTrue(shadow.flush())
            return value

    def test_analyze_work_aim_is_byte_identical_and_records_one_episode(self):
        call = lambda s: self.invoke(s, SAMPLE)
        off = self.envelope_bytes('off', call)
        self.assertEqual(self.episodes(), [])
        on = self.envelope_bytes('shadow', call)
        self.assertEqual(off, on)
        episodes = self.episodes()
        self.assertEqual(len(episodes), 1)
        shadow.validate_episode(episodes[0])
        self.assertEqual((episodes[0]['operation'], episodes[0]['analysisKind']), ('analyze-work', 'aim'))

    def test_refused_and_unsupported_calls_record_nothing(self):
        service = self.service()
        refused = service.invoke('analyze-work', {'kind': 'aim', 'request': {'operations': [{}] * 33}}, threading.Event())
        self.assertEqual(refused['status'], 'refused')
        self.assertEqual(service.invoke('execute', {}, threading.Event())['status'], 'refused')
        self.assertFalse(self.store.exists())

    def git_fixture(self):
        env = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull}
        def git(*args):
            return subprocess.run(['git', '-C', str(self.source), *args], env=env, check=True,
                                  capture_output=True).stdout.decode().strip()
        git('init', '-q', '-b', 'main')
        git('config', 'user.name', 'Shadow tests')
        git('config', 'user.email', 'tests@example.invalid')
        for name in ('a.txt', 'b.txt'):
            (self.source / name).write_text('base\n')
        git('add', '.')
        git('commit', '-qm', 'base')
        base = git('rev-parse', 'HEAD')
        commits = []
        for name in ('a', 'b'):
            git('checkout', '-q', '-b', name, base)
            (self.source / f'{name}.txt').write_text(name + '\n')
            git('add', '.')
            git('commit', '-qm', name)
            commits.append(git('rev-parse', 'HEAD'))
        git('checkout', '-q', 'main')
        return {'gitAnalysisRequestVersion': '0.1.0-alpha', 'repository': str(self.source),
                'baseRevision': base,
                'operations': [{'instanceId': name, 'attemptId': name + '-1',
                                'source': {'kind': 'commit', 'revision': commit},
                                'dependencies': [], 'uncertainPaths': []}
                               for name, commit in zip(('a', 'b'), commits)]}

    def test_git_analyze_work_prepare_and_analyze_are_byte_identical(self):
        request = self.git_fixture()
        git_call = lambda s: self.invoke(s, request, 'git')
        off = self.envelope_bytes('off', git_call)
        on = self.envelope_bytes('shadow', git_call)
        self.assertEqual(off, on)
        episode, = self.episodes()
        self.assertEqual(episode['analysisKind'], 'git')
        self.assertEqual(episode['operation'], 'analyze-work')
        shadow.validate_episode(episode)
        before = len(self.episodes())
        runtime_request = {'gitRuntimeRequestVersion': __import__('agent_braid.git_runtime', fromlist=['VERSION']).VERSION,
                           'repository': str(self.source), 'baseRevision': request['baseRevision'],
                           'expectedFinalTree': self.expected_tree(request), 'order': ['a', 'b'],
                           'operations': [dict(op, declaredWrites=[op['instanceId'] + '.txt'])
                                          for op in request['operations']]}
        for name, args in (('analyze', {'request': runtime_request}),
                           ('prepare', {'request': runtime_request,
                                        'runDirectory': str(self.results / 'run'), 'mode': 'serial'})):
            call = lambda s, name=name, args=args: s.invoke(name, args, threading.Event())
            first = self.envelope_bytes('off', call)
            second = self.envelope_bytes('shadow', call)
            self.assertEqual(json.loads(first)['status'], 'ok', first[:300])
            self.assertEqual(first, second, name)
        # The Git replay `analyze` result carries no System 2 interaction report: no episode.
        self.assertEqual(len(self.episodes()), before)

    def expected_tree(self, request):
        env = {**os.environ, 'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': os.devnull}
        def git(*args):
            return subprocess.run(['git', '-C', str(self.source), *args], env=env, check=True,
                                  capture_output=True).stdout.decode().strip()
        git('checkout', '-q', '--detach', request['baseRevision'])
        for name in ('a', 'b'):
            (self.source / f'{name}.txt').write_text(name + '\n')
        git('add', '.')
        tree = git('write-tree')
        git('reset', '--hard', '-q', request['baseRevision'])
        git('checkout', '-q', 'main')
        return tree

    def test_oversized_report_is_read_from_the_owned_artifact_without_changing_the_envelope(self):
        with patch.object(tooling_mcp, 'INLINE_RESULT_BYTES', 100):
            envelope = self.invoke(self.service(), sentinel_request())
        self.assertEqual(envelope['result']['type'], 'evidence-artifact-reference')
        self.assertEqual(len(self.episodes()), 1)

    def test_shadow_failure_never_raises_or_alters_the_envelope(self):
        expected = self.envelope_bytes('off', lambda s: self.invoke(s, SAMPLE))
        with patch.object(shadow, 'build_episode', side_effect=RuntimeError('boom')):
            actual = self.envelope_bytes('shadow', lambda s: self.invoke(s, SAMPLE))
        self.assertEqual(expected, actual)
        self.assertEqual(shadow.refusal_counts().get('internal-error'), 1)
        with patch.object(shadow, 'submit', side_effect=RuntimeError('boom')):
            self.assertEqual(self.envelope_bytes('shadow', lambda s: self.invoke(s, SAMPLE)), expected)

    def test_interrupts_are_not_swallowed_by_the_shadow_guard(self):
        with patch.object(shadow, 'submit', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.invoke(self.service(), SAMPLE)
        self.assertEqual(self.invoke(self.service('off'), SAMPLE)['status'], 'ok')


class EpisodeTests(Base):
    def test_episode_conforms_and_holds_no_input_string(self):
        service = self.service()
        self.invoke(service, sentinel_request())
        self.invoke(service, unknown_request())
        stored = b''.join(p.read_bytes() for p in self.store.glob('episodes-*.jsonl'))
        self.assertNotIn(SENTINEL.encode(), stored)
        for forbidden in (b'repo://', b'secret', b'attempt', b'instance', b'sha256:'):
            self.assertNotIn(forbidden, stored)
        first, second = self.episodes()
        for episode in (first, second):
            shadow.validate_episode(episode)
            self.assertIs(episode['executionAuthorization'], False)
            self.assertEqual(episode['systemOne']['status'], 'abstained')
            self.assertEqual(episode['systemOne']['reason'], 'calibration-absent')
            self.assertEqual(episode['systemOne']['backendId'], 'stdlib-rule-fixture-v1')
            self.assertEqual(episode['systemOne']['manifestDigest'], shadow.EXPECTED_MANIFEST_DIGEST)
            self.assertIsNone(episode['systemOne']['answers'])
            self.assertEqual(episode['analyzer'], {'version': '0.1.0-alpha', 'ruleSet': 'exact-resource-footprints-v1'})
        self.assertNotEqual(first['episodeId'], second['episodeId'])
        pair = first['pairs'][0]
        self.assertEqual((pair['system2'], pair['system2Determinate']), ('independent-candidate', True))
        self.assertEqual(pair['reasonCodes'], ['disjoint'])
        self.assertIsNone(pair['effectKinds'])
        pair = second['pairs'][0]
        self.assertEqual((pair['system2'], pair['system2Determinate']), ('unknown', False))
        self.assertEqual(pair['reasonCodes'], ['partial-coverage'])
        self.assertIn('partial', pair['coverage'])
        self.assertIsNone(pair['observedOutcome'])

    def report_with(self, reasons, constraints=('requires-execution-contract-before-parallelism',), count=1):
        report = {'analyzer': {'name': 'agent-braid', 'version': '0.1.0-alpha', 'ruleSet': 'exact-resource-footprints-v1'},
                  'summary': {'operationCount': 2, 'pairCount': count,
                              'classifications': {'independent-candidate': count, 'ordered': 0,
                                                  'conflicting': 0, 'unknown': 0}},
                  'interactions': [{'left': 'a', 'right': 'b', 'classification': 'independent-candidate',
                                    'sharedResources': ['r'], 'reasons': list(reasons),
                                    'constraints': list(constraints),
                                    'evidence': {'coverage': ['complete']}}] * count}
        return report

    def test_unmapped_reason_is_skipped_with_no_pairs(self):
        episode = shadow.build_episode(self.report_with(['Some new free text sentence']), 'analyze-work', 'aim')
        shadow.validate_episode(episode)
        self.assertEqual((episode['systemOne']['status'], episode['systemOne']['reason']), ('skipped', 'unmapped-reason'))
        self.assertEqual((episode['pairs'], episode['pairsRecorded'], episode['pairCount']), ([], 0, 1))
        self.assertNotIn('free text', json.dumps(episode))
        unknown_constraint = shadow.build_episode(
            self.report_with(['Complete exact-resource footprints are disjoint.'], ['made-up']), 'analyze-work', 'aim')
        self.assertEqual(unknown_constraint['systemOne']['reason'], 'unmapped-reason')

    def test_every_reason_sentence_the_analyzer_emits_is_mapped(self):
        from agent_braid import analysis

        def operation(name, effects, coverage='complete', reads=None):
            return {'instanceId': name, 'readVersions': reads or {},
                    'effects': {'declared': [{'kind': k, 'resource': r} for k, r in effects],
                                'inferred': [], 'observed': [], 'coverage': {'status': coverage}}}

        def interaction(left, right, ordered=False):
            ancestors = {left['instanceId']: set(), right['instanceId']: set()}
            if ordered:
                ancestors[right['instanceId']].add(left['instanceId'])
            return analysis._interaction(left, right, ancestors)

        cases = {
            'dependency-order': interaction(operation('a', [('read', 'r')]), operation('b', [('read', 'r')]), True),
            'shared-write': interaction(operation('a', [('write', 'r')]), operation('b', [('read', 'r')])),
            'partial-coverage': interaction(operation('a', [('read', 'x')], 'partial'), operation('b', [('read', 'y')])),
            'external-effect': interaction(operation('a', [('call', 'x')]), operation('b', [('read', 'y')])),
            'disjoint': interaction(operation('a', [('read', 'x')]), operation('b', [('read', 'y')])),
            'shared-read-only': interaction(operation('a', [('read', 'r')]), operation('b', [('read', 'r')])),
            'read-version': interaction(operation('a', [('read', 'x')], reads={'x': 'v1'}), operation('b', [('read', 'y')])),
        }
        emitted = set()
        for expected, item in cases.items():
            pair = shadow._pair(item)
            self.assertIsNotNone(pair, expected)
            self.assertIn(expected, pair['reasonCodes'])
            emitted.update(item['reasons'])
        self.assertEqual(emitted, set(shadow.REASON_TABLE))
        self.assertEqual(set(cases), set(shadow.REASON_CODES))

    def test_pairs_are_capped_deterministically_in_report_order(self):
        episode = shadow.build_episode(self.report_with(['Complete exact-resource footprints are disjoint.'], count=100),
                                       'analyze-work', 'aim')
        shadow.validate_episode(episode)
        self.assertEqual((episode['pairCount'], episode['pairsRecorded'], len(episode['pairs'])), (100, 64, 64))
        self.assertEqual(episode['classificationCounts']['independent-candidate'], 100)

    def test_classification_counts_must_sum_to_pair_count(self):
        report = self.report_with(['Complete exact-resource footprints are disjoint.'])
        report['summary']['classifications']['unknown'] = 1
        with self.assertRaises(ValueError):
            shadow.build_episode(report, 'analyze-work', 'aim')

    def test_identity_mismatch_is_refused_and_still_valid(self):
        with patch.object(shadow, 'EXPECTED_MANIFEST_DIGEST', '0' * 64):
            self.invoke(self.service(), SAMPLE)
        episode, = self.episodes()
        shadow.validate_episode(episode)
        self.assertEqual((episode['systemOne']['status'], episode['systemOne']['reason']), ('refused', 'identity-mismatch'))
        self.assertEqual(episode['systemOne']['manifestDigest'], '49f9022082fd12eda9ae1e0cd86ff827ca0c41dded4a52c618357cc9e525a3ca')
        with patch.object(shadow, 'EXPECTED_BACKEND_ID', 'other-backend'):
            self.assertEqual(shadow.build_episode(self.report_with(['Complete exact-resource footprints are disjoint.']),
                                                  'analyze-work', 'aim')['systemOne']['reason'], 'identity-mismatch')

    def test_budget_exceeded_is_skipped_and_elapsed_is_bounded(self):
        ticks = itertools.count(0, 60_000_000)
        episode = shadow.build_episode(self.report_with(['Complete exact-resource footprints are disjoint.']),
                                       'analyze-work', 'aim', clock=lambda: next(ticks))
        shadow.validate_episode(episode)
        self.assertEqual((episode['systemOne']['status'], episode['systemOne']['reason']), ('skipped', 'budget-exceeded'))
        self.assertLessEqual(episode['systemOne']['elapsedMicros'], 50_000)
        ticks = itertools.count(0, 1_000)
        fast = shadow.build_episode(self.report_with(['Complete exact-resource footprints are disjoint.']),
                                    'analyze-work', 'aim', clock=lambda: next(ticks))
        self.assertEqual(fast['systemOne']['status'], 'abstained')

    def test_validator_rejects_strings_outside_the_closed_vocabularies(self):
        good = shadow.build_episode(self.report_with(['Complete exact-resource footprints are disjoint.']), 'analyze-work', 'aim')
        shadow.validate_episode(good)
        def mutated(change):
            value = deepcopy(good)
            change(value)
            return value
        cases = [
            lambda v: v.update(extra='x'),
            lambda v: v.update(episodeId=v['episodeId'].upper()),
            lambda v: v.update(operation='prepare'),
            lambda v: v['pairs'][0]['reasonCodes'].append('write /etc/passwd'),
            lambda v: v['pairs'][0]['constraints'].append('free text'),
            lambda v: v['pairs'][0].update(resource='repo://x'),
            lambda v: v['pairs'][0].update(effectKinds={'left': ['write'], 'right': ['/path']}),
            lambda v: v['pairs'][0].update(observedOutcome='conflict'),
            lambda v: v['systemOne'].update(reason='because'),
            lambda v: v['systemOne'].update(manifestDigest='ABC'),
            lambda v: v['systemOne'].update(answers=[]),
            lambda v: v['analyzer'].update(ruleSet='has space and /path'),
            lambda v: v.update(executionAuthorization=True),
            lambda v: v.update(pairsRecorded=0),
            lambda v: v.update(operationCount=True),
        ]
        for index, change in enumerate(cases):
            with self.assertRaises(ValueError, msg=index):
                shadow.validate_episode(mutated(change))
        ok = mutated(lambda v: v['pairs'][0].update(effectKinds={'left': ['read'], 'right': ['delete', 'write']}))
        shadow.validate_episode(ok)


class StoreTests(Base):
    """SC-003: refusals leave the caller's result and budget untouched."""

    def assert_refused_without_effect(self, reason):
        counts = shadow.refusal_counts().get(reason, 0)
        with patch.object(tooling_mcp, 'uuid', counter_uuid()):
            on = json.dumps(self.invoke(self.service(), SAMPLE), sort_keys=True)
        with patch.object(tooling_mcp, 'uuid', counter_uuid()):
            off = json.dumps(self.invoke(self.service('off'), SAMPLE), sort_keys=True)
        self.assertEqual(on, off)
        self.assertEqual(json.loads(off)['status'], 'ok')
        self.assertEqual(shadow.refusal_counts().get(reason, 0), counts + 1)

    def test_symlinked_store_directory_is_refused(self):
        target = self.base / 'elsewhere'
        target.mkdir(mode=0o700)
        self.store.symlink_to(target)
        self.assert_refused_without_effect('unavailable')
        self.assertEqual(list(target.iterdir()), [])

    def test_store_inside_a_repository_is_refused(self):
        (self.base / '.git').mkdir()
        self.assert_refused_without_effect('unavailable')

    def test_group_readable_store_is_refused(self):
        self.store.mkdir(mode=0o750)
        self.store.chmod(0o750)
        self.assert_refused_without_effect('unavailable')

    def test_oversize_day_file_refuses_without_growing(self):
        self.store.mkdir(mode=0o700)
        target = self.store / f'episodes-{shadow.today().isoformat()}.jsonl'
        fd = os.open(target, os.O_WRONLY | os.O_CREAT, 0o600)
        os.ftruncate(fd, shadow.MAX_FILE_BYTES - 10)
        os.close(fd)
        self.assert_refused_without_effect('oversize')
        self.assertEqual(target.stat().st_size, shadow.MAX_FILE_BYTES - 10)

    def test_busy_lock_refuses_without_waiting(self):
        self.store.mkdir(mode=0o700)
        descriptor = os.open(self.store / 'store.lock', os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, descriptor)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assert_refused_without_effect('busy')
        self.assertEqual(self.episodes(), [])

    def test_unrelated_files_do_not_disable_the_store(self):
        self.store.mkdir(mode=0o700)
        (self.store / '.DS_Store').write_bytes(b'x')
        self.invoke(self.service(), SAMPLE)
        self.assertEqual(len(self.episodes()), 1)
        self.assertEqual(shadow.report()['totals']['episodes'], 1)
        self.assertTrue(shadow.store_present())
        self.assertEqual(shadow.refusal_counts(), {})
        result = shadow.purge()
        self.assertEqual((result['status'], result['leftover']), ('purged', ['.DS_Store']))
        self.assertEqual([p.name for p in self.store.iterdir()], ['.DS_Store'])

    def test_future_dated_day_files_are_kept(self):
        self.store.mkdir(mode=0o700)
        future = self.store / 'episodes-2999-01-01.jsonl'
        future.write_bytes(b'')
        future.chmod(0o600)
        self.assertTrue(shadow._retained(future.name, shadow.today()))
        self.assertFalse(shadow._retained('episodes-2020-01-01.jsonl', shadow.today()))
        self.invoke(self.service(), SAMPLE)
        self.assertTrue(future.exists())

    def test_purge_refuses_cleanly_while_the_store_is_locked(self):
        self.invoke(self.service(), SAMPLE)
        descriptor = os.open(self.store / 'store.lock', os.O_RDWR)
        self.addCleanup(os.close, descriptor)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with self.assertRaises(shadow.StoreRefused) as caught:
            shadow.purge()
        self.assertEqual(str(caught.exception), 'busy')
        stderr = StringIO()
        with redirect_stdout(StringIO()), patch('sys.stderr', stderr):
            code = main(['system-one', 'purge', '--yes'])
        self.assertEqual(code, 2)
        self.assertIn('retry', stderr.getvalue())
        self.assertNotIn(str(self.store), stderr.getvalue())
        self.assertEqual(len(self.episodes()), 1)
        fcntl.flock(descriptor, fcntl.LOCK_UN)
        self.assertEqual(shadow.purge()['status'], 'purged')
        self.assertFalse(self.store.exists())

    def test_cli_wording_names_the_system_one_store_not_telemetry(self):
        self.store.mkdir(mode=0o750)
        self.store.chmod(0o750)
        stderr = StringIO()
        with redirect_stdout(StringIO()), patch('sys.stderr', stderr):
            code = main(['system-one', 'report'])
        self.assertEqual(code, 2)
        self.assertIn('System One store', stderr.getvalue())
        self.assertNotIn('telemetry', stderr.getvalue())

    def test_files_are_private_and_old_dates_are_not_retained(self):
        self.invoke(self.service(), SAMPLE)
        self.assertEqual(self.store.stat().st_mode & 0o777, 0o700)
        for path in self.store.iterdir():
            self.assertEqual(path.stat().st_mode & 0o777, 0o600, path.name)
        old = self.store / 'episodes-2020-01-01.jsonl'
        old.write_bytes(b'')
        old.chmod(0o600)
        self.invoke(self.service(), SAMPLE)
        self.assertFalse(old.exists())
        self.assertEqual(len(self.episodes()), 2)

    def test_default_store_location_is_fixed_under_home(self):
        patch.stopall()
        self.assertEqual(shadow.default_directory(), Path.home() / '.local/share/agent-braid/system-one')
        self.assertEqual(shadow.display_location(), '~/.local/share/agent-braid/system-one')


class WorkerTests(Base):
    """C1: the work leaves the request path, never holds the router lock, and is bounded."""

    def gated(self):
        entered, release = threading.Event(), threading.Event()
        real = shadow.build_episode
        threads = []
        def build(*args, **kwargs):
            threads.append(threading.current_thread())
            entered.set()
            self.assertTrue(release.wait(5))
            return real(*args, **kwargs)
        self.addCleanup(release.set)
        return entered, release, threads, patch.object(shadow, 'build_episode', build)

    def test_router_returns_before_the_episode_is_built_and_releases_admission(self):
        home = self.base / 'home'
        repo = self.base / 'repo'
        repo.mkdir()
        subprocess.run(['git', '-C', str(repo), 'init', '-q'], check=True)
        preview = plan_setup(home, [repo], system_one='shadow')
        apply(home, preview, preview['previewDigest'])
        router = PluginRouter(home)
        identifier = next(iter(router.services))
        entered, release, threads, gate = self.gated()
        with gate:
            envelope = router.invoke('analyze-work', {'workspaceId': identifier, 'kind': 'aim',
                                                      'request': SAMPLE}, threading.Event())
            self.assertEqual(envelope['status'], 'ok')
            self.assertTrue(entered.wait(5))
            self.assertFalse(router.admission.locked())
            self.assertEqual(self.episodes(), [])
            release.set()
            self.assertTrue(shadow.flush())
        self.assertNotIn(threading.current_thread(), threads)
        self.assertEqual(len(self.episodes()), 1)

    def test_busy_worker_drops_new_reports_without_changing_envelopes(self):
        entered, release, _, gate = self.gated()
        service = self.service()
        with gate:
            first = service.invoke('analyze-work', {'kind': 'aim', 'request': SAMPLE}, threading.Event())
            self.assertTrue(entered.wait(5))
            for _ in range(3):  # one waits in the single slot, the rest are dropped
                again = service.invoke('analyze-work', {'kind': 'aim', 'request': SAMPLE}, threading.Event())
                self.assertEqual(again['status'], 'ok')
            self.assertEqual(shadow.refusal_counts().get('busy'), 2)
            release.set()
            self.assertTrue(shadow.flush())
        self.assertEqual(first['status'], 'ok')
        self.assertEqual(len(self.episodes()), 2)

    def test_oversize_artifact_backed_report_is_counted_and_not_decoded(self):
        with patch.object(tooling_mcp, 'INLINE_RESULT_BYTES', 100), \
                patch.object(shadow, 'MAX_REPORT_BYTES', 10), \
                patch.object(shadow.json, 'loads', side_effect=AssertionError('decoded')):
            envelope = self.invoke(self.service(), sentinel_request())
        self.assertEqual(envelope['result']['type'], 'evidence-artifact-reference')
        self.assertEqual(shadow.refusal_counts(), {'oversize-report': 1})
        self.assertEqual(self.episodes(), [])

    def test_decode_time_counts_against_the_budget(self):
        ticks = itertools.count(0, 30_000_000)
        with patch.object(shadow.time, 'monotonic_ns', lambda: next(ticks)):
            shadow.observe('analyze-work', 'aim', json.dumps({'report': EpisodeTests.report_with(
                None, ['Complete exact-resource footprints are disjoint.'])}).encode())
        episode, = self.episodes()
        self.assertEqual((episode['systemOne']['status'], episode['systemOne']['reason']),
                         ('skipped', 'budget-exceeded'))


class ReportTests(Base):
    """SC-004: report counts match seeded episodes and print no bodies."""

    def seed(self):
        service = self.service()
        for request in (SAMPLE, sentinel_request(), unknown_request(), unknown_request()):
            self.invoke(service, request)

    def test_report_counts_match_seeded_episodes(self):
        self.seed()
        value = shadow.report()
        self.assertEqual(value['schema'], 'agent-braid-s1-report/v0.1')
        self.assertEqual(value['totals']['episodes'], 4)
        self.assertEqual(value['totals']['operations'], {'analyze-work': 4})
        self.assertEqual(value['totals']['system2'], {'independent-candidate': 2, 'unknown': 2})
        self.assertEqual(value['totals']['systemOne'], {'abstained': 4})
        self.assertEqual((value['pairsRecorded'], value['pairsAnalysed'], value['unknownPairs'],
                          value['unknownShare']), (4, 4, 2, 0.5))
        day, = value['days']
        self.assertEqual(day['episodes'], 4)
        self.assertNotIn(SENTINEL, json.dumps(value))
        text = shadow.render_report(value)
        self.assertIn('50.0%', text)
        self.assertNotIn('episodeId', text)

    def test_cli_report_json_text_and_absent_store(self):
        def run(*args):
            stream = StringIO()
            with redirect_stdout(stream):
                code = main(['system-one', *args])
            return code, stream.getvalue()
        code, out = run('report', '--format', 'json')
        self.assertEqual((code, json.loads(out)['totals']['episodes']), (0, 0))
        self.assertFalse(self.store.exists(), 'report must not create the store')
        self.seed()
        code, out = run('report', '--format', 'json')
        self.assertEqual(json.loads(out)['totals']['episodes'], 4)
        code, out = run('report')
        self.assertIn('Episodes: 4', out)
        self.assertNotIn('episodeId', out)

    def test_invalid_lines_are_counted_not_printed(self):
        self.seed()
        target = next(self.store.glob('episodes-*.jsonl'))
        with open(target, 'ab') as stream:
            stream.write(b'{"schemaVersion":"' + SENTINEL.encode() + b'"}\nnot json\n')
        value = shadow.report()
        self.assertEqual((value['totals']['episodes'], value['invalidLines']), (4, 2))
        self.assertNotIn(SENTINEL, json.dumps(value))

    def test_purge_requires_confirmation_unless_yes(self):
        self.seed()
        def run(*args, answer=None):
            stream = StringIO()
            with redirect_stdout(stream), patch('builtins.input', return_value=answer) as prompt:
                code = main(['system-one', 'purge', *args])
            return code, stream.getvalue(), prompt.call_count
        code, _, asked = run(answer='n')
        self.assertEqual((code, asked, self.store.exists()), (1, 1, True))
        code, out, asked = run(answer='y')
        self.assertEqual((code, asked, self.store.exists()), (0, 1, False))
        self.assertEqual(json.loads(out)['status'], 'purged')
        self.seed()
        code, _, asked = run('--yes')
        self.assertEqual((code, asked, self.store.exists()), (0, 0, False))
        self.assertEqual(shadow.purge(), {'status': 'empty', 'externalCopies': 'not-removed'})

    def test_command_telemetry_is_opt_in_and_aggregate_only(self):
        telemetry_store = self.base / 'telemetry'
        with patch.object(tooling_telemetry, 'default_directory', return_value=telemetry_store):
            with redirect_stdout(StringIO()):
                main(['system-one', 'report'])
            self.assertFalse(telemetry_store.exists())
            with redirect_stdout(StringIO()):
                main(['system-one', '--telemetry', 'local', 'report'])
            rows = tooling_telemetry.Store().report()['rows']
        self.assertEqual({(r['surface'], r['operation'], r['outcome']) for r in rows}, {('cli', 'system-one', 'ok')})
        self.assertIn('system-one', tooling_telemetry.OPERATIONS['cli'])

    def test_command_telemetry_outcome_mapping(self):
        from argparse import Namespace
        from agent_braid.cli import _outcome
        system_one = lambda command: Namespace(command='system-one', decision_command=command)
        table = [(system_one('report'), 0, 'ok'), (system_one('decide'), 0, 'ok'),
                 (system_one('decide'), 1, 'ok'),  # abstain or defer is a valid answer
                 (system_one('decide'), 2, 'refused'), (system_one('purge'), 1, 'refused'),
                 (system_one('purge'), 2, 'refused'), (system_one('report'), 3, 'error'),
                 (Namespace(command='analyze'), 1, 'error'), (Namespace(command='analyze'), 2, 'refused')]
        for args, code, outcome in table:
            self.assertEqual(_outcome(args, code), outcome, (args, code))
        telemetry_store = self.base / 'telemetry'
        self.seed()
        with patch.object(tooling_telemetry, 'default_directory', return_value=telemetry_store), \
                redirect_stdout(StringIO()), patch('builtins.input', return_value='n'):
            self.assertEqual(main(['system-one', '--telemetry', 'local', 'purge']), 1)
            rows = tooling_telemetry.Store().report()['rows']
        self.assertEqual({r['outcome'] for r in rows}, {'refused'})


class RegistryTests(Base):
    def setUp(self):
        super().setUp()
        self.home = self.base / 'home'
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', '-C', str(self.repo), 'init', '-q'], check=True)

    def set_mode(self, mode):
        preview = plan_setup(self.home, [], system_one=mode)
        return preview, apply(self.home, preview, preview['previewDigest'])

    def test_absent_and_off_keep_registry_bytes_and_digest(self):
        legacy_style = {'schema': 'agent-braid-plugin-registry/v0.2', 'telemetry': 'off', 'workspaces': []}
        base_digest = configuration_digest(legacy_style)
        self.assertEqual(configuration_digest(dict(legacy_style, systemOne='off')), base_digest)
        preview, _ = self.set_mode(None)
        before = (self.home / 'registry.json').read_bytes()
        self.assertNotIn(b'systemOne', before)
        self.assertEqual(configuration_digest(load(self.home)), base_digest)
        self.set_mode('shadow')
        shadowed = (self.home / 'registry.json').read_bytes()
        self.assertIn(b'"systemOne": "shadow"', shadowed)
        self.assertNotEqual(configuration_digest(load(self.home)), base_digest)
        preview, _ = self.set_mode('off')
        self.assertEqual((self.home / 'registry.json').read_bytes(), before)
        self.assertEqual(configuration_digest(load(self.home)), base_digest)
        self.assertTrue(any('System One mode: off' in effect for effect in preview['effects']))

    def test_shadow_consent_warns_that_earlier_plugin_versions_refuse_the_registry(self):
        preview, _ = self.set_mode('shadow')
        self.assertTrue(any('Earlier plugin versions refuse' in effect for effect in preview['effects']))
        preview, _ = self.set_mode('off')
        self.assertFalse(any('Earlier plugin versions refuse' in effect for effect in preview['effects']))

    def test_unknown_consent_is_refused(self):
        from agent_braid.plugin_registry import RegistryError
        with self.assertRaises(RegistryError):
            plan_setup(self.home, [], system_one='advise')
        self.set_mode('shadow')
        path = self.home / 'registry.json'
        value = json.loads(path.read_text())
        value['systemOne'] = 'advise'
        path.write_text(json.dumps(value))
        with self.assertRaises(RegistryError):
            load(self.home)

    def test_setup_cli_previews_and_applies_system_one_consent_alone(self):
        def run(*args):
            out, err = StringIO(), StringIO()
            with redirect_stdout(out), patch('sys.stderr', err):
                code = main(['plugin', 'setup', '--home', str(self.home), *args])
            return code, out.getvalue(), err.getvalue()
        code, out, _ = run('--system-one', 'shadow')
        self.assertEqual(code, 0)
        preview = json.loads(out)
        self.assertEqual(preview['registry']['systemOne'], 'shadow')
        self.assertTrue(any('System One' in effect and 'reconnect' in effect for effect in preview['effects']))
        self.assertFalse((self.home / 'registry.json').exists())
        code, _, _ = run('--system-one', 'shadow', '--apply', '--preview-digest', preview['previewDigest'])
        self.assertEqual((code, load(self.home)['systemOne']), (0, 'shadow'))

    def test_plugin_status_reports_configured_and_active_mode_after_reconnect(self):
        self.set_mode(None)
        router = PluginRouter(self.home)
        status = router.status()['systemOne']
        self.assertEqual((status['configuredMode'], status['activeMode'], status['episodeRetentionDays']), ('off', 'off', 30))
        self.assertEqual(set(status), {'configuredMode', 'activeMode', 'store', 'episodeRetentionDays'})
        self.assertEqual(status['store']['present'], False)
        self.set_mode('shadow')
        status = router.status()
        self.assertEqual((status['systemOne']['configuredMode'], status['systemOne']['activeMode']), ('shadow', 'off'))
        self.assertTrue(status['reconnectRequired'])
        reconnected = PluginRouter(self.home)
        self.assertEqual(reconnected.status()['systemOne']['activeMode'], 'shadow')
        self.assertFalse(reconnected.status()['reconnectRequired'])
        self.assertEqual({s.config.system_one for s in reconnected.services.values()} or {'shadow'}, {'shadow'})

    def test_registered_workspace_receives_shadow_mode(self):
        preview = plan_setup(self.home, [self.repo], system_one='shadow')
        apply(self.home, preview, preview['previewDigest'])
        router = PluginRouter(self.home)
        self.assertEqual({s.config.system_one for s in router.services.values()}, {'shadow'})
        self.assertEqual(PluginRouter(self.home).status()['executionAuthorization'], False)


if __name__ == '__main__':
    unittest.main()
