# SPDX-License-Identifier: AGPL-3.0-only
import hashlib
import io
import json
from pathlib import Path
import tarfile
import tempfile
import unittest
from agent_braid.plugin_package import inventory, verify_package
from scripts.build_native_plugin import DISTRIBUTION_ATTRIBUTES, ROOT, assemble, extract_runtime


class PluginPackageTests(unittest.TestCase):
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
