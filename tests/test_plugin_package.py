# SPDX-License-Identifier: AGPL-3.0-only
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import tarfile
import tempfile
import unittest
from unittest import mock
from agent_braid.plugin_package import inventory, verify_package
from scripts import build_native_plugin
from scripts.build_native_plugin import DISTRIBUTION_ATTRIBUTES, ROOT, VERSION, assemble, extract_runtime, prepare_bytecode, materialize_runtime_links


class PluginPackageTests(unittest.TestCase):
    def test_runtime_aliases_survive_native_managers_that_omit_symlinks(self):
        import shutil
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / 'runtime'; runtime.mkdir()
            binary = runtime / 'python3.12'; binary.write_bytes(b'executable fixture'); binary.chmod(0o755)
            (runtime / 'python').symlink_to('python3.12')
            aliases = materialize_runtime_links(runtime)
            self.assertEqual(aliases, [{'path': 'python', 'target': 'python3.12'}])
            self.assertFalse((runtime / 'python').is_symlink())
            self.assertEqual((runtime / 'python').read_bytes(), binary.read_bytes())
            self.assertTrue((runtime / 'python').stat().st_mode & 0o111)
            # Reproduce the native copier's regular-file-only behavior.
            installed = root / 'installed'; installed.mkdir()
            for path in runtime.iterdir():
                if not path.is_symlink(): shutil.copy2(path, installed / path.name)
            self.assertEqual(inventory(runtime), inventory(installed))
            (runtime / 'escape').symlink_to(root / 'installed/python')
            with self.assertRaisesRegex(ValueError, 'contained regular file'):
                materialize_runtime_links(runtime)
            self.assertTrue((runtime / 'escape').is_symlink())

    def test_inventory_rejects_content_drift_and_tracks_directory_symlinks(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'assets').mkdir()
            (root / 'assets/data').write_text('original')
            (root / 'alias').symlink_to('assets', target_is_directory=True)
            files = inventory(root)
            self.assertEqual(files['alias'], {'link': 'assets'})
            (root / 'package-inventory.json').write_text(json.dumps({'schema': 'agent-braid-plugin-package/v1', 'version': 'test', 'files': files}))
            self.assertEqual(verify_package(root)['status'], 'verified')
            (root / 'assets/data').write_text('changed')
            with self.assertRaises(ValueError):
                verify_package(root)

    def _package_with_markers(self, directory):
        root = Path(directory)
        (root / 'assets').mkdir()
        (root / 'assets/data').write_text('original')
        (root / 'package-inventory.json').write_text(json.dumps({
            'schema': 'agent-braid-plugin-package/v1', 'version': 'test', 'files': inventory(root)}))
        markers = root / '.in_use'
        markers.mkdir()
        return root, markers

    def test_host_in_use_markers_are_tolerated(self):
        with tempfile.TemporaryDirectory() as directory:
            root, markers = self._package_with_markers(directory)
            (markers / '10785').write_text('{"pid":10785,"procStart":"Fri Oct 23 07:34:53 2026"}')
            (markers / '4096').write_bytes(b'x' * 4096)
            self.assertEqual(verify_package(root)['status'], 'verified')

    def test_unsupported_host_marker_entries_are_refused(self):
        cases = {
            'non-numeric name': lambda m: (m / 'not-a-pid').write_text('{}'),
            'non-ascii digits': lambda m: (m / '\u0661\u0662\u0663').write_text('{}'),
            'oversized marker': lambda m: (m / '123').write_bytes(b'x' * 4097),
            'symlinked marker': lambda m: (m / '124').symlink_to(m.parent / 'assets/data'),
            'directory marker': lambda m: (m / '125').mkdir(),
            'fifo marker': lambda m: __import__('os').mkfifo(m / '126'),
            'nested entry': lambda m: ((m / '127').mkdir(), (m / '127/nested').write_text('{}')),
        }
        for label, make in cases.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
                root, markers = self._package_with_markers(directory)
                make(markers)
                with self.assertRaisesRegex(ValueError, 'host marker'):
                    verify_package(root)

    def test_marker_directory_must_be_a_real_root_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root, markers = self._package_with_markers(directory)
            markers.rmdir()
            markers.write_text('{}')
            with self.assertRaisesRegex(ValueError, 'host marker'):
                verify_package(root)
        with tempfile.TemporaryDirectory() as directory:
            root, markers = self._package_with_markers(directory)
            markers.rmdir()
            markers.symlink_to(root / 'assets', target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'host marker'):
                verify_package(root)
        with tempfile.TemporaryDirectory() as directory:
            root, markers = self._package_with_markers(directory)
            nested = root / 'assets/.in_use'
            nested.mkdir()
            (nested / '1').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'inventory changed'):
                verify_package(root)

    def test_marker_removed_by_host_during_the_walk_is_skipped(self):
        from unittest import mock
        with tempfile.TemporaryDirectory() as directory:
            root, markers = self._package_with_markers(directory)
            marker = markers / '10785'
            marker.write_text('{}')
            real_rglob = Path.rglob

            def rglob_then_host_exits(self, pattern):
                for path in real_rglob(self, pattern):
                    if path.name == marker.name and marker.exists():
                        marker.unlink()
                    yield path
            with mock.patch.object(Path, 'rglob', rglob_then_host_exits):
                self.assertEqual(verify_package(root)['status'], 'verified')

    def test_build_inventory_does_not_hide_marker_shaped_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root, markers = self._package_with_markers(directory)
            (markers / '1').write_text('{}')
            self.assertIn('.in_use/1', inventory(root))
            self.assertNotIn('.in_use/1', inventory(root, allow_host_markers=True))

    def test_extract_rejects_hash_and_traversal_but_omits_unused_cyclic_terminfo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            path = root / 'runtime.tar.gz'
            with tarfile.open(path, 'w:gz') as stream:
                member = tarfile.TarInfo('python/bin/python3.12'); member.size = 3
                stream.addfile(member, io.BytesIO(b'app'))
                member = tarfile.TarInfo('python/share/terminfo/c/cycle'); member.type = tarfile.SYMTYPE; member.linkname = 'cycle'
                stream.addfile(member)
            expected = hashlib.sha256(path.read_bytes()).hexdigest()
            with self.assertRaises(ValueError):
                extract_runtime(path, root / 'bad', '0' * 64)
            result = extract_runtime(path, root / 'good', expected)
            self.assertEqual((result / 'bin/python3.12').read_bytes(), b'app')
            self.assertFalse((result / 'share/terminfo').exists())
            with tarfile.open(path, 'w:gz') as stream:
                member = tarfile.TarInfo('python/../../escape'); member.size = 3
                stream.addfile(member, io.BytesIO(b'bad'))
            with self.assertRaises((ValueError, tarfile.FilterError)):
                extract_runtime(path, root / 'unsafe', hashlib.sha256(path.read_bytes()).hexdigest())
            self.assertFalse((root / 'escape').exists())

    def test_build_rejects_output_through_a_symlink_into_checkout(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'alias').symlink_to(ROOT, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, 'outside the source checkout'):
                assemble(root / 'alias/should-never-exist', root / 'cache')
            self.assertFalse((ROOT / 'should-never-exist').exists())

    def test_fifo_inventory_is_refused_before_open(self):
        import os
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            os.mkfifo(root / 'package-inventory.json', 0o600)
            with self.assertRaisesRegex(ValueError, 'Invalid package inventory'):
                verify_package(root)

    def test_missing_or_malformed_version_is_a_bounded_refusal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for version in (None, 42, ''):
                (root / 'package-inventory.json').write_text(json.dumps({
                    'schema': 'agent-braid-plugin-package/v1', 'files': {}, 'version': version}))
                with self.assertRaisesRegex(ValueError, 'version'):
                    verify_package(root)

    def test_distribution_git_checkout_preserves_runtime_crlf_bytes(self):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'; clone = root / 'clone'
            subprocess.run(['git', 'init', '-q', str(source)], check=True)
            subprocess.run(['git', '-C', str(source), 'config', 'core.autocrlf', 'true'], check=True)
            (source / '.gitattributes').write_text(DISTRIBUTION_ATTRIBUTES)
            original = b'wheel,RECORD,bytes\r\nexact,checksum,data\r\n'
            (source / 'RECORD').write_bytes(original)
            subprocess.run(['git', '-C', str(source), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(source), '-c', 'user.name=Fixture', '-c',
                            'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], check=True)
            subprocess.run(['git', 'clone', '-q', '--no-local', str(source), str(clone)], check=True)
            subprocess.run(['git', '-C', str(clone), 'config', 'core.autocrlf', 'true'], check=True)
            subprocess.run(['git', '-C', str(clone), 'checkout-index', '--all', '--force'], check=True)
            self.assertEqual((clone / 'RECORD').read_bytes(), original)

    @unittest.skipUnless(__import__('sys').version_info[:2] == (3, 12), 'native build requires Python 3.12')
    def test_hash_bytecode_remains_unchanged_after_source_timestamp_changes(self):
        import os
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / 'lib/python3.12'; library.mkdir(parents=True)
            source = library / 'canary.py'; source.write_text('VALUE = 42\n')
            prepare_bytecode(root, 'fixture')
            cache = library / '__pycache__/canary.cpython-312.pyc'
            before = cache.read_bytes()
            self.assertEqual(int.from_bytes(before[4:8], 'little'), 3)
            os.utime(source, (1, 1))
            code = f'import sys; sys.path.insert(0, {str(library)!r}); import canary; assert canary.VALUE == 42'
            subprocess.run([sys.executable, '-I', '-c', code], check=True)
            self.assertEqual(cache.read_bytes(), before)


WORKFLOW_FIXTURE = {'braid-gate.js': b"export const meta = { name: 'braid-gate' }\n",
                    'lib/helper.js': b'export const helper = 1\n'}


_REAL_RUN = subprocess.run


def _fake_run(command, **options):
    """Stand in for the wheel build and pip installs; Git calls stay real. No network is used."""
    command = [str(x) for x in command]
    if command[0] == 'git':
        return _REAL_RUN(command, **options)
    if '--wheel' in command:
        outdir = Path(command[command.index('--outdir') + 1])
        outdir.mkdir(parents=True, exist_ok=True)
        (outdir / 'agent_braid-0-py3-none-any.whl').write_bytes(b'fixture wheel')


def _fake_extract(archive, destination, expected):
    runtime = Path(destination) / 'python'
    (runtime / 'lib/python3.12/site-packages').mkdir(parents=True)
    return runtime


class WorkflowPackagingTests(unittest.TestCase):
    """Opt-in packaging of the Claude-only workflow component (SPEC-052 REQ-011)."""

    @classmethod
    def setUpClass(cls):
        cls.scratch = tempfile.TemporaryDirectory()
        base = Path(cls.scratch.name)
        cls.fixture = base / 'workflows'
        for name, data in WORKFLOW_FIXTURE.items():
            (cls.fixture / name).parent.mkdir(parents=True, exist_ok=True)
            (cls.fixture / name).write_bytes(data)
        subprocess.run(['git', 'init', '-q', str(base)], check=True)
        (cls.fixture / 'ignored.local').write_text('secret\n')
        (cls.fixture / 'untracked.js').write_text('export {}\n')
        (cls.fixture / 'link.js').symlink_to(base / 'outside')
        (base / '.gitignore').write_text('ignored.local\n__pycache__/\n')
        subprocess.run(['git', '-C', str(base), 'add', '-f', '--'] +
                       ['workflows/' + x for x in WORKFLOW_FIXTURE], check=True)
        cls.default = cls._build(base / 'default')
        cls.opt_in = cls._build(base / 'opt-in', include_workflows=True)
        cls.opt_in_again = cls._build(base / 'opt-in-again', include_workflows=True)

    @classmethod
    def tearDownClass(cls):
        cls.scratch.cleanup()

    @classmethod
    def _build(cls, output, **options):
        base = Path(cls.scratch.name)
        with mock.patch.object(build_native_plugin, 'WORKFLOWS_SOURCE', cls.fixture), \
                mock.patch.object(build_native_plugin.subprocess, 'run', _fake_run), \
                mock.patch.object(build_native_plugin, '_download'), \
                mock.patch.object(build_native_plugin, 'extract_runtime', _fake_extract), \
                mock.patch.object(build_native_plugin, 'prepare_bytecode', return_value={'mode': 'fixture'}):
            result = assemble(output, base / 'cache', platforms=['macos-arm64'], allow_dirty=True, **options)
        return Path(result['plugin'])

    def test_default_build_excludes_workflows_and_verifies(self):
        self.assertFalse((self.default / 'workflows').exists())
        self.assertFalse((self.default / 'ENGINEERING-ONLY.json').exists())
        self.assertFalse([x for x in inventory(self.default) if x.startswith('workflows/')])
        self.assertEqual(verify_package(self.default)['status'], 'verified')
        provenance = json.loads((self.default / 'provenance.json').read_text())
        self.assertNotIn('engineeringOnly', provenance)

    def test_opt_in_ships_only_tracked_regular_files(self):
        shipped = sorted(x for x in inventory(self.opt_in) if x.startswith('workflows/'))
        self.assertEqual(shipped, sorted('workflows/' + x for x in WORKFLOW_FIXTURE))
        for name in ('ignored.local', 'untracked.js', 'link.js'):
            self.assertFalse((self.opt_in / 'workflows' / name).exists(), name)

    def test_tracked_symlink_in_workflow_source_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / 'w').mkdir()
            (root / 'w/a.js').write_text('export {}\n')
            (root / 'w/link.js').symlink_to(root / 'w/a.js')
            subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)
            with self.assertRaisesRegex(ValueError, 'tracked regular file'):
                build_native_plugin.copy_tracked_workflows(root / 'w', root / 'out')

    def test_tracked_file_below_a_directory_replaced_by_a_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / 'w/sub').mkdir(parents=True)
            (root / 'w/sub/a.js').write_text('export {}\n')
            subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)
            (root / 'outside').mkdir()
            (root / 'outside/a.js').write_text('export const outside = 1\n')
            shutil.rmtree(root / 'w/sub')
            (root / 'w/sub').symlink_to(root / 'outside')
            with self.assertRaisesRegex(ValueError, 'tracked regular file'):
                build_native_plugin.copy_tracked_workflows(root / 'w', root / 'out')
            self.assertFalse((root / 'out').exists())

    def test_workflow_source_without_tracked_files_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / 'w').mkdir()
            (root / 'w/untracked.js').write_text('export {}\n')
            with self.assertRaisesRegex(ValueError, 'no tracked files'):
                build_native_plugin.copy_tracked_workflows(root / 'w', root / 'out')

    def test_copy_preserves_the_executable_bit(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / 'w').mkdir()
            (root / 'w/run.js').write_text('export {}\n')
            (root / 'w/run.js').chmod(0o755)
            (root / 'w/plain.js').write_text('export {}\n')
            (root / 'w/plain.js').chmod(0o644)
            subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)
            build_native_plugin.copy_tracked_workflows(root / 'w', root / 'out')
            self.assertEqual((root / 'out/run.js').stat().st_mode & 0o777, 0o755)
            self.assertEqual((root / 'out/plain.js').stat().st_mode & 0o777, 0o644)

    def test_tracked_but_deleted_workflow_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            (root / 'w').mkdir()
            (root / 'w/a.js').write_text('export {}\n')
            subprocess.run(['git', '-C', str(root), 'add', '-A'], check=True)
            (root / 'w/a.js').unlink()
            with self.assertRaisesRegex(ValueError, 'tracked regular file'):
                build_native_plugin.copy_tracked_workflows(root / 'w', root / 'out')

    def test_default_source_archive_holds_only_tracked_files(self):
        tracked = set(subprocess.check_output(['git', 'ls-files', '--cached', '-z'], cwd=ROOT,
                                              text=True).split('\0'))
        archive = next((self.default.parent.parent / 'sources').glob('*-source.tar.gz'))
        with tarfile.open(archive) as stream:
            names = set(stream.getnames())
        self.assertFalse(names - tracked)
        self.assertFalse((self.default / 'workflows').exists())

    def test_opt_in_copies_the_workflow_tree_with_stable_inventory_entries(self):
        files = inventory(self.opt_in)
        for name, data in WORKFLOW_FIXTURE.items():
            self.assertEqual((self.opt_in / 'workflows' / name).read_bytes(), data)
            self.assertEqual(files['workflows/' + name]['sha256'], hashlib.sha256(data).hexdigest())
        self.assertEqual(sorted(x for x in files if x.startswith('workflows/')),
                         sorted('workflows/' + x for x in WORKFLOW_FIXTURE))
        self.assertEqual(verify_package(self.opt_in)['status'], 'verified')

    def test_two_opt_in_builds_have_identical_inventories(self):
        first, second = inventory(self.opt_in), inventory(self.opt_in_again)
        # provenance.json embeds the source archive hash, whose gzip header carries a timestamp.
        first.pop('provenance.json'); second.pop('provenance.json')
        self.assertEqual(first, second)

    def test_opt_in_is_marked_engineering_only_and_keeps_the_version(self):
        marker = json.loads((self.opt_in / 'ENGINEERING-ONLY.json').read_text())
        self.assertEqual(marker['component'], 'workflows')
        self.assertIs(marker['releasable'], False)
        provenance = json.loads((self.opt_in / 'provenance.json').read_text())
        self.assertEqual(provenance['engineeringOnly']['component'], 'workflows')
        for plugin in (self.default, self.opt_in):
            self.assertEqual(provenance['version'], VERSION)
            self.assertEqual(json.loads((plugin / '.claude-plugin/plugin.json').read_text())['version'], VERSION)
            self.assertEqual(json.loads((plugin / 'plugin.json').read_text())['version'], VERSION)
            self.assertEqual(json.loads((plugin / 'package-inventory.json').read_text())['version'], VERSION)
        self.assertEqual(VERSION, '0.1.0-alpha.3')

    def test_opt_in_leaves_manifests_mcp_and_skills_byte_identical(self):
        names = ['plugin.json', '.claude-plugin/plugin.json', 'mcp.json', '.mcp.json', 'launch']
        names += [x for x in inventory(self.default) if x.startswith('skills/')]
        # Five product skills plus the setup skill, all present in both builds.
        self.assertEqual(len([x for x in names if x.endswith('/SKILL.md')]), 6)
        for name in names:
            self.assertEqual((self.opt_in / name).read_bytes(), (self.default / name).read_bytes(), name)
        before, after = inventory(self.default), inventory(self.opt_in)
        extra = set(after) - set(before)
        self.assertEqual(extra, {'ENGINEERING-ONLY.json'} | {'workflows/' + x for x in WORKFLOW_FIXTURE})
        self.assertEqual(set(before) - set(after), set())
        for name in set(before) - {'provenance.json'}:
            self.assertEqual(before[name], after[name], name)

    def test_claude_manifest_declares_no_workflows_override_and_no_other_components(self):
        for plugin in (self.default, self.opt_in):
            manifest = json.loads((plugin / '.claude-plugin/plugin.json').read_text())
            portable = json.loads((plugin / 'plugin.json').read_text())
            for key in ('workflows', 'hooks', 'mods', 'agents', 'monitors'):
                self.assertNotIn(key, manifest)
                self.assertNotIn(key, portable)
            self.assertEqual(sorted(x for x in inventory(plugin)
                                    if x.split('/')[0] in ('hooks', 'mods', 'agents', 'monitors')), [])
        self.assertIn('mcpServers', json.loads((self.opt_in / '.mcp.json').read_text()))

    def test_verification_rejects_missing_altered_and_extra_workflow_files(self):
        def missing(root): (root / 'workflows/braid-gate.js').unlink()
        def altered(root): (root / 'workflows/braid-gate.js').write_bytes(b'export const meta = {}\n')
        def extra(root): (root / 'workflows/extra.js').write_text('export {}\n')
        def missing_directory(root): shutil.rmtree(root / 'workflows/lib')
        for label, change in (('missing', missing), ('altered', altered), ('extra', extra),
                              ('missing directory', missing_directory)):
            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
                copy = Path(directory) / 'plugin'
                shutil.copytree(self.opt_in, copy)
                self.assertEqual(verify_package(copy)['status'], 'verified')
                change(copy)
                with self.assertRaisesRegex(ValueError, 'inventory changed'):
                    verify_package(copy)

    def test_engineering_marker_and_workflow_directory_must_agree(self):
        build_native_plugin.verify_engineering_marker(self.default)
        build_native_plugin.verify_engineering_marker(self.opt_in)
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / 'plugin'
            shutil.copytree(self.opt_in, copy)
            (copy / 'ENGINEERING-ONLY.json').unlink()
            with self.assertRaisesRegex(ValueError, 'engineering-only'):
                build_native_plugin.verify_engineering_marker(copy)
        with tempfile.TemporaryDirectory() as directory:
            copy = Path(directory) / 'plugin'
            shutil.copytree(self.default, copy)
            (copy / 'ENGINEERING-ONLY.json').write_text('{}')
            with self.assertRaisesRegex(ValueError, 'engineering-only'):
                build_native_plugin.verify_engineering_marker(copy)

    def test_engineering_marker_content_must_match(self):
        for label, change in (('releasable', {'releasable': True}), ('reason', {'reason': 'altered'})):
            with self.subTest(label), tempfile.TemporaryDirectory() as directory:
                copy = Path(directory) / 'plugin'
                shutil.copytree(self.opt_in, copy)
                marker = copy / 'ENGINEERING-ONLY.json'
                marker.write_text(json.dumps({**json.loads(marker.read_text()), **change}))
                with self.assertRaisesRegex(ValueError, 'engineering-only'):
                    build_native_plugin.verify_engineering_marker(copy)

    def test_assemble_verifies_the_engineering_marker(self):
        with mock.patch.object(build_native_plugin, 'verify_engineering_marker',
                               side_effect=ValueError('marker check ran')) as check:
            with self.assertRaisesRegex(ValueError, 'marker check ran'):
                self._build(Path(self.scratch.name) / 'marker-wiring', include_workflows=True)
        check.assert_called_once()

    def test_opt_in_requires_an_existing_workflow_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            missing = Path(directory) / 'absent'
            with mock.patch.object(build_native_plugin, 'WORKFLOWS_SOURCE', missing):
                with self.assertRaisesRegex(ValueError, 'workflow'):
                    assemble(Path(directory) / 'out', Path(directory) / 'cache', allow_dirty=True,
                             include_workflows=True)
            self.assertFalse((Path(directory) / 'out').exists())

    def test_command_line_flag_is_explicit_and_off_by_default(self):
        with mock.patch.object(build_native_plugin, 'assemble', return_value={}) as built, \
                mock.patch.object(build_native_plugin.sys, 'argv', ['build', '--output', 'o', '--cache', 'c']):
            with contextlib.redirect_stdout(io.StringIO()):
                build_native_plugin.main()
        self.assertFalse(built.call_args.kwargs['include_workflows'])
        with mock.patch.object(build_native_plugin, 'assemble', return_value={}) as built, \
                mock.patch.object(build_native_plugin.sys, 'argv',
                                  ['build', '--output', 'o', '--cache', 'c', '--include-workflows']):
            with contextlib.redirect_stdout(io.StringIO()):
                build_native_plugin.main()
        self.assertTrue(built.call_args.kwargs['include_workflows'])
