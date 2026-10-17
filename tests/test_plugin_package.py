# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from agent_braid.plugin_package import inventory, verify_package
from scripts.build_native_plugin import DISTRIBUTION_ATTRIBUTES, ROOT, assemble, extract_runtime, prepare_bytecode, materialize_runtime_links


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
