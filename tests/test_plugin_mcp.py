# SPDX-License-Identifier: AGPL-3.0-only
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import re
import stat
import threading
import unittest
from unittest import mock
import importlib.util
from tests import test_plugin_registry as registry_tests
from agent_braid import plugin_mcp
from agent_braid.plugin_mcp import PluginRouter
from agent_braid.plugin_registry import RegistryStale, load, plan_setup, apply
from tests.spec060_golden import golden, normalize


class PluginRouterTests(unittest.TestCase):
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install

    def test_two_workspaces_keep_core_results_and_resource_ownership(self):
        self.install()
        other = self.base / 'another'
        other.mkdir()
        import subprocess
        subprocess.run(['git', 'init', '-q', str(other)], check=True)
        self.install([other])
        router = PluginRouter(self.home)
        ids = [x['workspaceId'] for x in load(self.home)['workspaces']]
        sample = json.loads((Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json').read_text())
        result = router.invoke('analyze-work', {'workspaceId': ids[0], 'kind': 'aim', 'request': sample}, threading.Event())
        self.assertEqual(result['status'], 'ok')
        self.assertEqual(result['result']['report']['interactions'][0]['classification'], 'independent-candidate')
        uri = result['evidenceRefs'][0]['uri']
        self.assertTrue(uri.startswith('agent-braid-plugin://' + ids[0] + '/'))
        manifest = json.loads(router.read_resource(uri)[1])
        chunk = json.loads(router.read_resource(manifest['firstChunkUri'])[1])
        self.assertEqual(chunk['artifactSha256'], manifest['sha256'])
        with self.assertRaises(ValueError):
            router.read_resource(uri.replace(ids[0], ids[1]))
        self.assertEqual(router.invoke('execute', {'workspaceId': ids[0]}, threading.Event())['status'], 'refused')
        self.assertEqual(router.invoke('analyze-work', {'workspaceId': 'not-registered'}, threading.Event())['status'], 'refused')

    def test_registry_change_requires_reconnect_and_no_root_override(self):
        self.install()
        router = PluginRouter(self.home)
        identifier = load(self.home)['workspaces'][0]['workspaceId']
        result = router.invoke('analyze-work', {'workspaceId': identifier, 'sourceRoot': str(self.repo)}, threading.Event())
        self.assertEqual(result['status'], 'refused')
        preview = plan_setup(self.home, [], remove=[identifier])
        apply(self.home, preview, preview['previewDigest'])
        self.assertTrue(router.status()['reconnectRequired'])
        self.assertEqual(router.invoke('analyze-work', {'workspaceId': identifier}, threading.Event())['status'], 'refused')

    def rewrite(self, transform):
        path = self.home / 'registry.json'
        value = transform(json.loads(path.read_text()))
        path.write_text(json.dumps(value, separators=(',', ':')))

    def make_repo(self, name):
        import subprocess
        path = self.base / name
        path.mkdir()
        subprocess.run(['git', 'init', '-q', str(path)], check=True)
        return path

    def two_workspaces(self):
        second = self.make_repo('another')
        self.install([self.repo, second])
        return [x['workspaceId'] for x in load(self.home)['workspaces']]

    def assert_not_reconnect_refusal(self, result):
        self.assertNotIn('reconnect', result['summary'])
        self.assertNotEqual(result['result'], {'code': RegistryStale.code})

    def test_noop_and_reordered_rewrites_do_not_require_reconnect(self):
        ids = self.two_workspaces()
        router = PluginRouter(self.home)
        baseline = router.status()['baselineDigest']
        self.rewrite(lambda v: v)
        self.rewrite(lambda v: dict(v, workspaces=list(reversed(v['workspaces']))))
        status = router.status()
        self.assertFalse(status['reconnectRequired'])
        self.assertEqual((status['baselineDigest'], status['currentDigest']), (baseline, baseline))
        sample = json.loads((Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json').read_text())
        result = router.invoke('analyze-work', {'workspaceId': ids[0], 'kind': 'aim', 'request': sample}, threading.Event())
        self.assertEqual(result['status'], 'ok')
        self.assert_not_reconnect_refusal(result)

    def test_raw_byte_differences_alone_do_not_require_reconnect(self):
        self.two_workspaces()
        router = PluginRouter(self.home)
        path = self.home / 'registry.json'
        before = path.read_bytes()
        value = json.loads(before)
        path.write_text(json.dumps(dict(reversed(list(value.items()))), indent=4, sort_keys=False) + '\n\n')
        self.assertNotEqual(path.read_bytes(), before)
        status = router.status()
        self.assertFalse(status['reconnectRequired'])
        self.assertEqual(status['baselineDigest'], status['currentDigest'])

    def test_idempotent_setup_apply_does_not_require_reconnect(self):
        self.install()
        router = PluginRouter(self.home)
        self.install()
        self.assertFalse(router.status()['reconnectRequired'])

    def test_each_effective_change_requires_reconnect_and_changes_the_digest(self):
        extra = self.make_repo('third')
        second = self.make_repo('another')
        worktree = self.make_repo('worktree')
        grants = self.base / 'grants'
        grants.mkdir()
        first = lambda v, **change: dict(v, workspaces=[dict(v['workspaces'][0], **change)] + v['workspaces'][1:])
        changes = {
            'removed': lambda v: dict(v, workspaces=v['workspaces'][:1]),
            'consent': lambda v: dict(v, telemetry='local'),
            'worktree-root': lambda v: first(v, worktreeRoots=[str(worktree)]),
            'grant': lambda v: first(v, runtimeEnabled=True, grantStore=str(grants)),
        }
        for name, change in changes.items():
            with self.subTest(name):
                self.home = self.base / f'state-{name}'
                self.install([self.repo, second])
                router = PluginRouter(self.home)
                self.rewrite(change)
                status = router.status()
                self.assertTrue(status['reconnectRequired'])
                self.assertNotEqual(status['baselineDigest'], status['currentDigest'])
        with self.subTest('added'):
            self.home = self.base / 'state-added'
            self.install([self.repo])
            router = PluginRouter(self.home)
            self.install([extra])
            status = router.status()
            self.assertTrue(status['reconnectRequired'])
            self.assertNotEqual(status['baselineDigest'], status['currentDigest'])

    def test_digests_are_path_free(self):
        self.install()
        router = PluginRouter(self.home)
        status = router.status()
        for key in ('baselineDigest', 'currentDigest'):
            self.assertRegex(status[key], r'^[0-9a-f]{64}$')
        self.assertNotIn(str(self.base), json.dumps({k: status[k] for k in ('baselineDigest', 'currentDigest')}))

    def test_stale_refusal_names_reconnect_and_keeps_registered_workspace_id(self):
        self.install()
        router = PluginRouter(self.home)
        identifier = load(self.home)['workspaces'][0]['workspaceId']
        self.rewrite(lambda v: dict(v, telemetry='local'))
        result = router.invoke('analyze-work', {'workspaceId': identifier}, threading.Event())
        self.assertEqual(result['status'], 'refused')
        self.assertEqual(result['workspaceId'], identifier)
        self.assertEqual(result['result'], {'code': RegistryStale.code})
        self.assertIn('reconnect', result['summary'])
        self.assertIn('plugin-status', result['summary'])
        self.assertNotIn('check workspace, arguments', result['summary'])
        self.assertFalse(result['provenance']['executionAuthorization'])

    def test_stale_refusal_for_unregistered_workspace_does_not_echo_it(self):
        self.install()
        router = PluginRouter(self.home)
        self.rewrite(lambda v: dict(v, telemetry='local'))
        result = router.invoke('analyze-work', {'workspaceId': 'not-registered'}, threading.Event())
        self.assertEqual(result['status'], 'refused')
        self.assertIsNone(result['workspaceId'])

    def test_stale_read_resource_raises_registry_stale(self):
        self.install()
        router = PluginRouter(self.home)
        identifier = load(self.home)['workspaces'][0]['workspaceId']
        self.rewrite(lambda v: dict(v, telemetry='local'))
        with self.assertRaises(RegistryStale) as caught:
            router.read_resource(f'agent-braid-plugin://{identifier}/capabilities')
        self.assertIn('plugin-status', str(caught.exception))

    def test_bootstrap_tools_still_answer_when_stale(self):
        self.install()
        router = PluginRouter(self.home)
        self.rewrite(lambda v: dict(v, telemetry='local'))
        for name in ('plugin-status', 'workspaces'):
            result = router.invoke(name, {}, threading.Event())
            self.assertEqual(result['status'], 'ok')
            self.assertTrue(result['result']['reconnectRequired'])

    def test_stale_connection_keeps_its_snapshotted_roots_and_grants(self):
        self.install()
        router = PluginRouter(self.home)
        before = router.status()['workspaces']
        self.rewrite(lambda v: dict(v, workspaces=[]))
        self.assertEqual(router.status()['workspaces'], before)
        self.assertEqual(len(router.services), 1)

    def test_status_separates_package_version_from_plugin_version(self):
        from agent_braid import __version__
        self.install()
        status = PluginRouter(self.home).status()
        self.assertEqual(status['version'], __version__)
        self.assertIsNone(status['pluginVersion'])  # no packaged plugin root, e.g. a source checkout
        package = self.base / 'package'
        package.mkdir()
        (package / 'plugin.json').write_text(json.dumps({'name': 'agent-braid', 'version': '0.1.0-alpha.7'}))
        status = PluginRouter(self.home, package).status()
        self.assertEqual((status['version'], status['pluginVersion']), (__version__, '0.1.0-alpha.7'))

    def test_plugin_version_is_null_for_a_missing_or_malformed_manifest(self):
        self.install()
        package = self.base / 'package'
        package.mkdir()
        self.assertIsNone(PluginRouter(self.home, package).status()['pluginVersion'])
        for text in ('not json', '[]', json.dumps({'version': 6})):
            (package / 'plugin.json').write_text(text)
            self.assertIsNone(PluginRouter(self.home, package).status()['pluginVersion'], text)

    def test_snapshotted_telemetry_consent_reaches_every_workspace_and_requires_reconnect(self):
        self.install()
        router = PluginRouter(self.home)
        self.assertEqual({s.config.telemetry for s in router.services.values()}, {'off'})
        self.assertEqual(router.status()['telemetry'], {'configuredMode': 'off', 'activeMode': 'off',
            'retentionDays': 30, 'automaticUpload': False})
        preview = plan_setup(self.home, [], telemetry='local')
        apply(self.home, preview, preview['previewDigest'])
        status = router.status()
        self.assertTrue(status['reconnectRequired'])
        self.assertEqual((status['telemetry']['configuredMode'], status['telemetry']['activeMode']), ('local', 'off'))
        identifier = load(self.home)['workspaces'][0]['workspaceId']
        self.assertEqual(router.invoke('analyze-work', {'workspaceId': identifier}, threading.Event())['status'], 'refused')
        reconnected = PluginRouter(self.home)
        self.assertEqual({s.config.telemetry for s in reconnected.services.values()}, {'local'})
        self.assertEqual(reconnected.status()['telemetry']['activeMode'], 'local')

    def test_local_consent_records_plugin_calls_as_mcp_surface(self):
        from unittest.mock import patch
        from agent_braid import tooling_telemetry as telemetry
        self.install()
        preview = plan_setup(self.home, [], telemetry='local')
        apply(self.home, preview, preview['previewDigest'])
        store = self.base / 'telemetry'
        with patch.object(telemetry, 'default_directory', return_value=store):
            router = PluginRouter(self.home)
            identifier = load(self.home)['workspaces'][0]['workspaceId']
            sample = json.loads((Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json').read_text())
            result = router.invoke('analyze-work', {'workspaceId': identifier, 'kind': 'aim', 'request': sample}, threading.Event())
            self.assertEqual(result['status'], 'ok')
            report = telemetry.Store().report()
        self.assertIn('mcp', json.dumps(report))
        self.assertIn('analyze-work', json.dumps(report))

    def router_refusals(self, router, identifier):
        """Every router-level refusal path."""
        from unittest.mock import patch
        from agent_braid import tooling_mcp as core
        sample = {'workspaceId': identifier, 'kind': 'aim', 'request': {}}
        out = {'unknown-workspace': router.invoke('analyze-work', dict(sample, workspaceId='not-registered'), threading.Event()),
               'malformed-arguments': router.invoke('analyze-work', ['not', 'an', 'object'], threading.Event()),
               'bootstrap-arguments': router.invoke('workspaces', {'x': 1}, threading.Event())}
        with router.admission:
            out['busy-admission'] = router.invoke('analyze-work', sample, threading.Event())
        with patch.object(core, 'MAX_INVENTORY_ARTIFACTS', 0):
            out['full-inventory'] = router.invoke('analyze-work', sample, threading.Event())
        return out

    def assert_router_refusals_write_no_telemetry(self, consent, stale):
        # Consent off only: with consent local the refusals are counted (tests/test_plugin_mcp_telemetry.py).
        from unittest.mock import patch
        from agent_braid import tooling_telemetry as telemetry
        self.install()
        if consent == 'local':
            preview = plan_setup(self.home, [], telemetry='local')
            apply(self.home, preview, preview['previewDigest'])
        store = self.base / 'telemetry'
        with patch.object(telemetry, 'default_directory', return_value=store):
            router = PluginRouter(self.home)
            self.assertEqual(router.status()['telemetry']['activeMode'], consent)
            identifier = load(self.home)['workspaces'][0]['workspaceId']
            refusals = self.router_refusals(router, identifier)
            if stale:
                self.rewrite(lambda v: dict(v, workspaces=[]))
                refusals['reconnect-required'] = router.invoke('analyze-work', {'workspaceId': identifier}, threading.Event())
                self.assertEqual(refusals['reconnect-required']['result'], {'code': RegistryStale.code})
            for cause, result in refusals.items():
                self.assertEqual(result['status'], 'refused', cause)
            self.assertFalse(store.exists(), 'a refusal created the telemetry store')
            self.assertEqual(telemetry.Store().report()['rows'], [])

    def test_router_refusals_write_no_telemetry_with_consent_off(self):
        self.assert_router_refusals_write_no_telemetry('off', stale=True)

    def test_service_refusal_with_consent_local_is_counted_once(self):
        from unittest.mock import patch
        from agent_braid import tooling_telemetry as telemetry
        self.install()
        preview = plan_setup(self.home, [], telemetry='local')
        apply(self.home, preview, preview['previewDigest'])
        with patch.object(telemetry, 'default_directory', return_value=self.base / 'telemetry'):
            router = PluginRouter(self.home)
            identifier = load(self.home)['workspaces'][0]['workspaceId']
            # A refusal that reaches the service is counted exactly once, by the router that owns the measurement.
            result = router.invoke('analyze-work', {'workspaceId': identifier}, threading.Event())
            self.assertEqual(result['status'], 'refused')
            rows = telemetry.Store().report()['rows']
        self.assertIn(('mcp', 'analyze-work', 'refused', 'calls', 1),
                      [(r['surface'], r['operation'], r['outcome'], r['metric'], r['count']) for r in rows])

    def test_v01_registry_serves_migration_status_without_workspaces(self):
        registry_tests.PluginRegistryTests.legacy_registry(self)
        router = PluginRouter(self.home)
        status = router.status()
        self.assertEqual(status['status'], 'migration-required')
        self.assertEqual(status['workspaces'], [])
        self.assertEqual(router.services, {})
        self.assertEqual(status['telemetry']['activeMode'], 'off')


class PluginReportCopyTests(unittest.TestCase):
    """SPEC-061 T040 / REQ-006: a private local copy of each analyze-work report in the result root."""
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install
    NAME = re.compile(r'^analysis-\d{8}T\d{12}Z-[0-9a-f]{16}$')

    def sample(self):
        return json.loads((Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json').read_text())

    def start(self):
        self.install()
        self.router = PluginRouter(self.home)
        row = load(self.home)['workspaces'][0]
        self.identifier = row['workspaceId']
        self.root = Path(row['resultRoot'])
        self.service = self.router.services[self.identifier]

    def analyze(self, name='analyze-work', **extra):
        args = {'workspaceId': self.identifier, 'kind': 'aim', 'request': self.sample()}
        args.update(extra)
        return self.router.invoke(name, args, threading.Event())

    def copies(self):
        return sorted(p.name for p in self.root.iterdir() if self.NAME.match(p.name))

    def make_copy(self, when, size=10, *, extra=None):
        """A pre-existing copy named for `when` (datetime): a sparse analysis.json of `size` bytes."""
        directory = self.root / ('analysis-' + when.strftime('%Y%m%dT%H%M%S') + f'{when.microsecond:06d}Z-' + os.urandom(8).hex())
        directory.mkdir(mode=0o700)
        with open(directory / 'analysis.json', 'wb') as stream:
            stream.truncate(size)
        for name in extra or ():
            (directory / name).write_bytes(b'x')
        return directory

    def write(self, root, body=b'{}', registered=None, **kwargs):
        return plugin_mcp.write_report_copy(root, registered if registered is not None else root, body, **kwargs)

    def test_copy_has_the_report_body_private_modes_and_one_directory_per_report(self):
        self.start()
        envelope = self.analyze()
        self.assertEqual(envelope['status'], 'ok')
        first = self.copies()
        self.assertEqual(len(first), 1)
        directory = self.root / first[0]
        self.assertEqual(sorted(p.name for p in directory.iterdir()), ['analysis.json'])
        self.assertEqual(stat.S_IMODE(directory.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE((directory / 'analysis.json').stat().st_mode), 0o600)
        data = (directory / 'analysis.json').read_bytes()
        self.assertEqual(json.loads(data), envelope['result']['report'])  # the report body, not the MCP envelope
        self.assertEqual(self.analyze()['status'], 'ok')
        second = self.copies()
        self.assertEqual(len(second), 2)
        self.assertTrue(set(first) <= set(second))
        self.assertEqual(stat.S_IMODE(self.root.stat().st_mode), 0o700)

    def test_stored_bytes_round_trip_through_the_viewer_adapter_and_the_watcher(self):
        from agent_braid.view_adapters import events_from_analysis
        from agent_braid.view_store import LoomStore
        from agent_braid.view_tail import KNOWN_ARTIFACTS, ArtifactTail
        self.start()
        self.assertIn('analysis.json', KNOWN_ARTIFACTS)
        self.analyze()
        name = self.copies()[0]
        data = (self.root / name / 'analysis.json').read_bytes()
        events = events_from_analysis(data, path=f'{name}/analysis.json')
        self.assertEqual(events[0]['kind'], 'analysis.report')
        self.assertNotIn('source-unsupported', json.dumps(events))
        self.assertEqual({e['source']['verification'] for e in events}, {'rehashed'})
        store = LoomStore()
        self.assertGreater(ArtifactTail(store, [self.root]).poll_once(), 0)  # walks the subdirectory
        self.assertEqual(store.replay()[0]['kind'], 'analysis.report')

    def test_a_report_held_as_an_evidence_artifact_is_copied_as_the_same_report_body(self):
        from agent_braid import tooling_mcp as core
        self.start()
        with mock.patch.object(core, 'INLINE_RESULT_BYTES', 1):
            envelope = self.analyze()
        self.assertEqual(envelope['result']['type'], 'evidence-artifact-reference')
        held = json.loads(self.service.artifacts[envelope['evidenceRefs'][0]['artifactId']].data)
        name = self.copies()[0]
        self.assertEqual(json.loads((self.root / name / 'analysis.json').read_bytes()), held['report'])

    def test_only_a_successful_analyze_work_writes_a_copy(self):
        self.start()
        ok = {'status': 'ok', 'result': {'report': {'a': 1}}}  # an ok `analyze` envelope: only the name gates a copy
        with mock.patch.object(plugin_mcp.core.ToolingService, 'invoke', return_value=ok):
            self.assertEqual(self.service.invoke('analyze', {}, threading.Event()), ok)
        self.assertEqual(list(self.root.iterdir()), [])
        for result in (self.analyze(kind='unsupported'), self.analyze(request={}),
                       self.router.invoke('analyze-work', {'workspaceId': 'not-registered'}, threading.Event())):
            self.assertEqual(result['status'], 'refused')
        self.assertEqual(list(self.root.iterdir()), [])

    def test_a_copy_failure_neither_fails_nor_changes_the_response(self):
        self.start()
        baseline = self.analyze()

        def comparable(envelope):
            value = json.loads(json.dumps(envelope))
            value['evidenceRefs'] = [{k: v for k, v in ref.items() if k not in {'artifactId', 'uri'}}
                                     for ref in value['evidenceRefs']]
            return value

        for error in (OSError('/secret/path'), RuntimeError('/secret/path')):
            with self.subTest(type(error).__name__), mock.patch.object(plugin_mcp, 'write_report_copy', side_effect=error):
                failed = self.analyze()
            self.assertNotIn('secret', json.dumps(failed))
            self.assertEqual(comparable(failed), comparable(baseline))
        self.assertEqual(len(self.copies()), 1)  # only the baseline call wrote one

    @unittest.skipIf(hasattr(os, 'geteuid') and os.geteuid() == 0, 'root ignores directory permissions')
    def test_an_unwritable_result_root_does_not_fail_the_call(self):
        self.start()
        self.root.chmod(0o500)
        self.addCleanup(self.root.chmod, 0o700)
        self.assertEqual(self.analyze()['status'], 'ok')
        self.assertEqual(self.copies(), [])

    def test_refuses_a_root_that_is_a_link_not_private_or_not_the_registered_one(self):
        self.start()
        elsewhere = self.base / 'elsewhere'
        elsewhere.mkdir(mode=0o700)
        link = self.base / 'link'
        link.symlink_to(elsewhere)
        loose = self.base / 'loose'
        loose.mkdir()
        loose.chmod(0o755)
        missing = self.base / 'nope'
        for label, root, registered in (('link', link, link), ('loose', loose, loose),
                                        ('unregistered', elsewhere, self.root), ('missing', missing, missing)):
            with self.subTest(label), self.assertRaises((OSError, ValueError)):
                self.write(root, registered=registered)
        self.assertEqual(list(elsewhere.iterdir()), [])
        self.assertEqual(list(loose.iterdir()), [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_refuses_a_link_inside_the_path_of_the_root(self):
        self.start()
        real = self.base / 'real'
        (real / 'results').mkdir(parents=True, mode=0o700)
        real.chmod(0o700)
        alias = self.base / 'alias'
        alias.symlink_to(real)
        with self.assertRaises((OSError, ValueError)):
            self.write(alias / 'results')
        self.assertEqual(list((real / 'results').iterdir()), [])

    def test_the_name_is_unique_and_sortable_by_time(self):
        self.start()
        early = datetime(2026, 11, 3, 10, 0, 0, 5, tzinfo=timezone.utc)
        late = datetime(2026, 11, 3, 10, 0, 0, 6, tzinfo=timezone.utc)
        self.write(self.root, now=early)
        self.write(self.root, now=late)
        self.write(self.root, now=late)
        names = self.copies()
        self.assertEqual(len(names), 3)
        self.assertEqual(names, sorted(names))
        self.assertTrue(names[0].startswith('analysis-20261103T100000000005Z-'))

    def test_a_failed_publish_leaves_no_visible_artifact(self):
        self.start()
        with mock.patch.object(plugin_mcp.os, 'rename', side_effect=OSError):
            with self.assertRaises(OSError):
                self.write(self.root)
        self.assertEqual([p.name for p in self.root.rglob('analysis.json')], [])
        self.assertEqual(list(self.root.iterdir()), [])

    def test_retention_removes_copies_older_than_thirty_days_and_nothing_else(self):
        self.start()
        now = datetime(2026, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
        old = self.make_copy(now - timedelta(days=30, seconds=1))
        edge = self.make_copy(now - timedelta(days=30) + timedelta(seconds=1))
        recent = self.make_copy(now - timedelta(days=1))
        foreign = self.make_copy(now - timedelta(days=90), extra=['notes.txt'])  # holds a file that is not ours: kept
        (self.root / 'notes.txt').write_text('keep')
        (self.root / 'run-aaaa').mkdir()
        (self.root / 'run-aaaa' / 'state.json').write_text('{}')
        (self.root / 'analysis-old-but-not-a-copy').mkdir()
        outside = self.base / 'outside'
        outside.mkdir()
        (outside / 'analysis.json').write_text('keep')
        os.symlink(outside, self.root / ('analysis-20200101T000000000000Z-' + '0' * 16))
        os.utime(self.root / 'notes.txt', (0, 0))
        self.write(self.root, now=now)
        self.assertFalse(old.exists())
        self.assertTrue(edge.exists() and recent.exists() and foreign.exists())
        self.assertEqual(sorted(p.name for p in self.root.iterdir() if not self.NAME.match(p.name)),
                         ['analysis-old-but-not-a-copy', 'notes.txt', 'run-aaaa'])
        self.assertEqual((outside / 'analysis.json').read_text(), 'keep')
        self.assertEqual((self.root / 'run-aaaa' / 'state.json').read_text(), '{}')

    def test_retention_caps_the_total_at_64_mib_removing_the_oldest_first(self):
        self.assertEqual(plugin_mcp.REPORT_COPY_MAX_BYTES, 64 * 1024 * 1024)
        self.assertEqual(plugin_mcp.REPORT_COPY_DAYS, 30)
        self.start()
        now = datetime(2026, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
        mib = 1024 * 1024
        made = [self.make_copy(now - timedelta(hours=10 - n), 10 * mib) for n in range(7)]  # 70 MiB in total
        with open(self.root / 'big-unrelated.bin', 'wb') as stream:
            stream.truncate(200 * mib)  # other files never count and are never touched
        self.write(self.root, b'{}', now=now)
        self.assertEqual([p.exists() for p in made], [False] + [True] * 6)
        self.write(self.root, b'x' * (5 * mib), now=now)  # 60 MiB + 5 MiB + 2 bytes: the next oldest goes
        self.assertEqual([p.exists() for p in made], [False, False] + [True] * 5)
        self.assertTrue((self.root / 'big-unrelated.bin').exists())
        total = sum((self.root / name / 'analysis.json').stat().st_size for name in self.copies())
        self.assertLessEqual(total, 64 * mib)

    def test_a_retention_failure_keeps_the_new_copy_and_the_response(self):
        self.start()
        with mock.patch.object(plugin_mcp, '_prune_report_copies', side_effect=OSError):
            self.assertEqual(self.analyze()['status'], 'ok')
        self.assertEqual(len(self.copies()), 1)

    def test_retention_caps_the_number_of_copies_and_never_removes_the_new_one(self):
        self.assertEqual(plugin_mcp.REPORT_COPY_MAX_COUNT, 1500)
        self.start()
        now = datetime(2026, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
        made = [self.make_copy(now - timedelta(hours=10 - n)) for n in range(5)]
        self.write(self.root, now=now, max_count=3)
        self.assertEqual([p.exists() for p in made], [False] * 3 + [True] * 2)
        self.assertEqual(len(self.copies()), 3)  # the new copy is one of them

    def test_an_oversized_new_copy_is_kept_when_it_alone_exceeds_the_cap(self):
        self.start()
        now = datetime(2026, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
        old = self.make_copy(now - timedelta(hours=1))
        self.write(self.root, b'x' * 100, now=now, max_bytes=10)
        self.assertFalse(old.exists())
        names = self.copies()
        self.assertEqual(len(names), 1)
        self.assertEqual((self.root / names[0] / 'analysis.json').read_bytes(), b'x' * 100)

    def test_an_abandoned_temporary_only_directory_is_pruned_once_old(self):
        self.start()
        now = datetime(2026, 11, 3, 12, 0, 0, tzinfo=timezone.utc)
        stale = self.make_copy(now - timedelta(days=31))
        (stale / 'analysis.json').rename(stale / '.analysis.tmp')
        self.write(self.root, now=now)
        self.assertFalse(stale.exists())

    def test_concurrent_writes_each_leave_a_whole_copy(self):
        self.start()
        bodies = [json.dumps({'n': n}).encode() for n in range(8)]
        threads = [threading.Thread(target=self.write, args=(self.root, body)) for body in bodies]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()
        stored = sorted((self.root / name / 'analysis.json').read_bytes() for name in self.copies())
        self.assertEqual(stored, sorted(bodies))

    def test_the_shadow_and_telemetry_paths_are_not_overridden(self):
        for name in ('_shadow', '_invoke_measured', '_invoke'):
            self.assertNotIn(name, plugin_mcp.WorkspaceService.__dict__)


@unittest.skipUnless(importlib.util.find_spec("mcp"), "optional mcp==2.3.0 SDK is unavailable")
class PluginSdkTests(unittest.IsolatedAsyncioTestCase):
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install

    async def test_actual_sdk_connection_preserves_both_protocols_and_workspace_resources(self):
        import sys
        from mcp import Client
        from mcp.shared.exceptions import MCPError
        from mcp.client.stdio import StdioServerParameters
        self.install()
        identifier = load(self.home)['workspaces'][0]['workspaceId']
        root = Path(__file__).resolve().parents[1]
        sample = json.loads((root / 'examples/analysis/file-edits.json').read_text())
        for mode in ('auto', 'legacy'):
            params = StdioServerParameters(command=sys.executable,
                args=['-m', 'agent_braid', 'plugin', 'serve', '--home', str(self.home)], cwd=str(root))
            async with Client(params, mode=mode) as client:
                definitions = {tool.name: tool for tool in (await client.list_tools()).tools}
                names = set(definitions)
                self.assertEqual(names, {'plugin-status', 'workspaces', 'analyze-work', 'analyze', 'prepare'})
                response = await client.call_tool('analyze-work', {'workspaceId': identifier, 'kind': 'aim', 'request': sample})
                value = response.structured_content
                self.assertEqual(value['status'], 'ok')
                self.assertEqual(json.loads(response.content[0].text), value)
                import jsonschema
                jsonschema.validate(value, definitions['analyze-work'].output_schema)
                refused = await client.call_tool('analyze-work', {'workspaceId': 'unknown'})
                self.assertEqual(refused.structured_content['status'], 'refused')
                jsonschema.validate(refused.structured_content, definitions['analyze-work'].output_schema)
                uri = value['evidenceRefs'][0]['uri']
                data = await client.read_resource(uri)
                self.assertTrue(json.loads(data.contents[0].text)['firstChunkUri'].startswith('agent-braid-plugin://'))
                self.assertEqual((await client.list_resource_templates()).resource_templates, [])
                self.assertEqual(value['schemaVersion'], 'agent-braid-plugin/v0.2')
                self.assertEqual(refused.structured_content['schemaVersion'], 'agent-braid-plugin/v0.2')
                self.assertEqual(definitions['analyze-work'].output_schema['properties']['schemaVersion'], {'const': 'agent-braid-plugin/v0.2'})
                self.assertIsNone(client.server_capabilities.prompts)
                with self.assertRaisesRegex(MCPError, 'Method not found'):
                    await client.list_prompts()
                before = sorted(str(r.uri) for r in (await client.list_resources()).resources)
                for prompt_name in ('agent-braid-analyze', 'analyze'):
                    with self.assertRaisesRegex(MCPError, 'Method not found'):
                        await client.get_prompt(prompt_name)
                after = sorted(str(r.uri) for r in (await client.list_resources()).resources)
                self.assertEqual(before, after)
                raw = (await client.read_resource(f'agent-braid-plugin://{identifier}/capabilities')).contents[0].text
                capabilities = json.loads(raw)
                for key in ('prompts', 'deprecatedPrompts', 'envelopeSchemaVersion'):
                    self.assertNotIn(key, capabilities)
                self.assertTrue(capabilities['resources'])
                self.assertEqual(capabilities['schemaVersion'], 'agent-braid-tooling/v0.1')
                self.assertEqual(raw.replace(identifier, 'wsgolden').encode('utf-8'), golden('plugin-capabilities.json'))


class PluginAlpha4GoldenTests(unittest.TestCase):
    """SPEC-060 REQ-004: the plugin surface is byte-identical to alpha.4 (goldens captured before the change)."""
    NEW_KEYS = ('prompts', 'deprecatedPrompts', 'envelopeSchemaVersion')

    def setUp(self):
        import tempfile
        from agent_braid import tooling_mcp as core
        from agent_braid.plugin_mcp import WorkspaceService
        self.temp = tempfile.TemporaryDirectory()
        base = Path(self.temp.name)
        (base / 's').mkdir()
        (base / 'r').mkdir()
        self.core = core
        self.service = WorkspaceService('wsgolden', core.ToolingConfig(base / 's', base / 'r'))

    def tearDown(self):
        self.temp.cleanup()

    def test_capabilities_resource_bytes_equal_the_alpha4_golden(self):
        produced = self.core._json_bytes(self.service.capabilities())
        self.assertEqual(produced, golden('plugin-capabilities.json'))
        value = json.loads(produced)
        self.assertEqual(value['schemaVersion'], 'agent-braid-tooling/v0.1')
        for key in self.NEW_KEYS:
            self.assertNotIn(key, value)

    def test_tool_envelope_equals_the_alpha4_golden(self):
        from agent_braid.plugin_mcp import SCHEMA
        sample = json.loads((Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json').read_text())
        envelope = self.service.invoke('analyze-work', {'kind': 'aim', 'request': sample}, threading.Event())
        envelope = dict(envelope, schemaVersion=SCHEMA, workspaceId='wsgolden')
        produced = normalize(self.core._json_bytes(envelope).decode('utf-8')).encode('utf-8')
        self.assertEqual(produced, golden('plugin-analyze-work-envelope.json'))
        self.assertEqual(envelope['schemaVersion'], 'agent-braid-plugin/v0.2')
        self.assertEqual(envelope['provenance']['schemaVersion'], 'agent-braid-tooling/v0.1')

    def test_negative_control_unstripped_core_capabilities_differ_from_the_golden(self):
        shared = self.core.ToolingService.capabilities(self.service)
        self.assertEqual(shared['schemaVersion'], 'agent-braid-tooling/v0.2')
        for key in self.NEW_KEYS:
            self.assertIn(key, shared)
        shared['resources'] = [self.service.external(uri) for uri in shared['resources']]
        self.assertNotEqual(self.core._json_bytes(shared), golden('plugin-capabilities.json'))

    def test_negative_control_each_leaked_key_breaks_the_golden(self):
        for key in self.NEW_KEYS:
            leaked = dict(self.service.capabilities(), **{key: 'x'})
            self.assertNotEqual(self.core._json_bytes(leaked), golden('plugin-capabilities.json'), key)


class PluginPromptNegativeControlTests(unittest.TestCase):
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install

    def test_negative_control_shared_core_still_advertises_prompts_but_plugin_drops_them(self):
        from agent_braid import tooling_mcp as core
        self.install()
        service = next(iter(PluginRouter(self.home).services.values()))
        shared = core.ToolingService.capabilities(service)
        self.assertEqual(len(shared['prompts']), 3)  # the old v0.1 plugin behaviour: would fail the new assertion
        self.assertNotIn('prompts', service.capabilities())
        self.assertEqual(len(core._PROMPTS), 6)  # portable server keeps its prompts (3 canonical + 3 aliases)


class PluginOpenCodeSessionIdentifierTests(unittest.IsolatedAsyncioTestCase):
    """SPEC-068 REQ-009 / REQ-010: an OpenCode request `_meta` session identifier changes nothing and is stored nowhere."""
    setUp = registry_tests.PluginRegistryTests.setUp
    install = registry_tests.PluginRegistryTests.install
    SESSION = 'ses_OpenCodeSentinel0123456789'
    META = {'ai.opencode/sessionID': SESSION}
    SAMPLE = json.loads((Path(__file__).resolve().parents[1] / 'examples/analysis/file-edits.json').read_text())

    def consent(self):
        preview = plan_setup(self.home, [], telemetry='local', system_one='shadow')
        apply(self.home, preview, preview['previewDigest'])

    async def drive(self, label, meta):
        """One OpenCode-like session over the real SDK (in memory): every plugin tool plus a resource read."""
        from mcp import Client, types
        from agent_braid import system_one_shadow as shadow, tooling_telemetry as telemetry
        store, episodes = self.base / label / 'telemetry', self.base / label / 'system-one'
        kwargs = {'meta': meta} if meta else {}
        outputs = {}
        with mock.patch.object(telemetry, 'default_directory', return_value=store), \
                mock.patch.object(shadow, 'default_directory', return_value=episodes):
            router = PluginRouter(self.home)
            router.record_start()
            identifier = load(self.home)['workspaces'][0]['workspaceId']
            with mock.patch.object(router, 'invoke', wraps=router.invoke) as spy:
                client_info = types.Implementation(name='opencode', version='2.1.4')
                async with Client(plugin_mcp.create_server(router), mode='legacy', client_info=client_info) as client:
                    calls = [('plugin-status', {}), ('workspaces', {}),
                             ('analyze-work', {'workspaceId': identifier, 'kind': 'aim', 'request': self.SAMPLE}),
                             ('analyze-work', {'workspaceId': 'not-registered'}),
                             ('execute', {'workspaceId': identifier, 'plan': {}, 'grantId': 'x'})]
                    for index, (name, arguments) in enumerate(calls):
                        response = await client.call_tool(name, arguments, **kwargs)
                        outputs[f'{index}-{name}'] = response.structured_content
                    uri = outputs['2-analyze-work']['evidenceRefs'][0]['uri']
                    outputs['resource'] = (await client.read_resource(uri, **kwargs)).contents[0].text
            self.assertNotIn(self.SESSION, repr(spy.call_args_list), 'the router received request metadata')
            self.assertTrue(shadow.flush(), 'shadow worker did not finish')
            (self.base / label / 'export').mkdir(mode=0o700)
            exported = self.base / label / 'export' / 'batch.json'
            telemetry.Store().export(exported)
        return normalize(json.dumps(outputs, sort_keys=True).replace(f'/{label}/', '/RUN/')), store, episodes, exported

    def leaks(self):
        """Every file or directory under the test root whose name or bytes carry the session identifier."""
        found = []
        for directory, names, files in os.walk(self.base):
            for name in names + files:
                path = Path(directory, name)
                if self.SESSION in name or (path.is_file() and not path.is_symlink()
                                            and self.SESSION.encode() in path.read_bytes()):
                    found.append(str(path))
        return found

    @unittest.skipUnless(importlib.util.find_spec('mcp'), 'optional mcp==2.3.0 SDK is unavailable')
    async def test_envelopes_telemetry_and_stores_are_identical_with_and_without_the_session_identifier(self):
        from agent_braid import tooling_telemetry as telemetry
        self.install()
        self.consent()
        plain, plain_store, plain_episodes, plain_batch = await self.drive('plain', None)
        tagged, tagged_store, tagged_episodes, tagged_batch = await self.drive('tagged', self.META)
        self.assertEqual(tagged, plain)  # envelopes and the evidence manifest, byte for byte
        self.assertNotIn(self.SESSION, tagged)
        self.assertEqual(self.leaks(), [])
        # SPEC-047: same cells (durations may land in a neighbouring bucket), same closed fields, schema v2.
        def cells(directory):
            with mock.patch.object(telemetry, 'default_directory', return_value=directory):
                rows = telemetry.Store().report()['rows']
            return sorted((r['surface'], r['operation'], r['outcome'], r['metric'],
                           'any' if r['metric'] == 'duration' else r['bucket'], r['count']) for r in rows)
        self.assertEqual(cells(tagged_store), cells(plain_store))
        batches = [json.loads(path.read_text()) for path in (plain_batch, tagged_batch)]
        for batch in batches:
            self.assertEqual(batch['schema'], telemetry.SCHEMA)
            self.assertEqual({tuple(sorted(row)) for row in batch['rows']},
                             {('bucket', 'count', 'day', 'metric', 'operation', 'outcome', 'surface')})
        self.assertEqual([(r['surface'], r['operation'], r['outcome'], r['metric']) for r in batches[0]['rows']],
                         [(r['surface'], r['operation'], r['outcome'], r['metric']) for r in batches[1]['rows']])
        # SPEC-066: the shadow store gains the same structural episodes, with the same fields.
        def episodes(directory):
            lines = [json.loads(line) for path in sorted(directory.glob('episodes-*.jsonl'))
                     for line in path.read_text().splitlines()]
            return [sorted(line) for line in lines]
        self.assertTrue(episodes(plain_episodes))
        self.assertEqual(episodes(tagged_episodes), episodes(plain_episodes))

    def test_negative_control_the_scan_finds_a_stored_identifier(self):
        self.install()
        self.assertEqual(self.leaks(), [])
        (self.base / 'leak.txt').write_text('{"session": "' + self.SESSION + '"}')
        (self.base / f'{self.SESSION}.json').write_text('{}')
        self.assertEqual(len(self.leaks()), 2)

    def test_telemetry_vocabularies_and_the_log_audit_classes_are_unchanged(self):
        from agent_braid import telemetry_audit as audit, tooling_telemetry as telemetry
        self.assertEqual(telemetry.SCHEMA, 'agent-braid-local-telemetry-batch/v2')
        self.assertEqual(telemetry.OUTCOMES, ('ok', 'refused', 'error', 'cancelled', 'unknown'))
        self.assertEqual(telemetry.REASON_SURFACES, ('mcp', 'lifecycle'))
        self.assertEqual(set(telemetry.BUCKETS), {'calls', 'duration', 'classification', 'missing-summary', 'refusal-reason'})
        self.assertEqual(telemetry.BUCKETS['refusal-reason'], telemetry.REFUSAL_REASONS)
        self.assertEqual(len(telemetry.REFUSAL_REASONS), 11)
        self.assertEqual(audit.SCHEMA, 'agent-braid-telemetry-log-audit/v1')
        self.assertEqual(audit.CALL_CLASSES, ('router-refused', 'reconnect-required', 'worktree-allowlist', 'request-shape',
                                              'arguments-invalid', 'operation-refused', 'other'))
        self.assertEqual(audit.STARTUP_CLASSES, telemetry.REFUSAL_REASONS)
