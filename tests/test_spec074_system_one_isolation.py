# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-074 REQ-007 / SC-007 (T009): the adapter reads System One episodes and never writes back.

The shadow store is a real one (written by `system_one_shadow.append`) in a temporary directory.
Reading it through the adapter must leave every byte, mtime, mode and name unchanged, open every
file read-only, and produce records that no System One input path accepts (ADR 0034).
"""
import ast
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from agent_braid import analysis
from agent_braid import lightning_adapter as adapter
from agent_braid import system_one_shadow as shadow
from tests.test_lightning_adapter import SALT, SAMPLE, cli

ROOT = Path(__file__).resolve().parents[1]
WRITE_FLAGS = os.O_WRONLY | os.O_RDWR | os.O_CREAT | os.O_APPEND | os.O_TRUNC


def snapshot(root: Path) -> dict:
    """Name, mode, size, mtime and bytes of every entry under `root`, links not followed."""
    state = {}
    for path in sorted(root.rglob('*')):
        info = path.lstat()
        state[str(path.relative_to(root))] = (info.st_mode, info.st_size, info.st_mtime_ns,
                                              None if path.is_dir() or path.is_symlink() else path.read_bytes())
    info = root.lstat()
    return {'.': (info.st_mode, info.st_mtime_ns), **state}


class IsolationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        base = Path(self.tmp.name).resolve()
        self.home, self.store = base / 'home', base / 'shadow'
        mover = patch.object(shadow, 'default_directory', lambda: self.store)
        mover.start()
        self.addCleanup(mover.stop)
        for _ in range(2):
            shadow.append(shadow.build_episode(analysis.analyze(SAMPLE), 'analyze-work', 'aim', request=SAMPLE))
        [self.day] = shadow._entries(self.store)

    def tearDown(self):
        self.tmp.cleanup()

    def consent(self, sources):
        flags = ['lightning', 'init', '--home', str(self.home), '--non-interactive', '--trace-consent', 'redacted',
                 '--trace-sources', sources]
        _, out, _ = cli(*flags)
        self.assertEqual(cli(*flags, '--apply', '--preview-digest', json.loads(out)['previewDigest'])[0], 0)

    def read_all(self):
        return adapter.system_one_triplets(self.home, self.day, SALT), \
            adapter.system_one_messages(self.home, self.day, SALT)

    def test_reading_leaves_the_shadow_directory_unchanged(self):
        before = snapshot(self.store)
        self.assertEqual(len(before), 3)  # the directory, the day file and the store lock
        for sources in (None, 'rollout', 'rollout,system-one'):  # consent none, unlisted, listed
            if sources:
                self.consent(sources)
            triplets, _ = self.read_all()
            self.assertEqual(len(triplets), 2)
            self.assertEqual(snapshot(self.store), before, sources)
        self.assertIsNotNone(triplets[0]['prompt'])  # the listed pass read content

    def test_a_write_under_the_shadow_directory_is_detected(self):
        """Negative control: an adapter that touches the store fails the snapshot comparison."""
        self.consent('rollout,system-one')
        before = snapshot(self.store)
        real = shadow.read_day

        def writing(path):
            with open(Path(path).parent / 'lightning-cache.json', 'w') as stream:
                stream.write('{}')
            return real(path)
        with patch.object(shadow, 'read_day', writing):
            self.read_all()
        self.assertNotEqual(snapshot(self.store), before)

    def test_every_open_under_the_store_is_read_only(self):
        self.consent('rollout,system-one')
        opened, real_open = [], os.open

        def recording(path, flags, *args, **kwargs):
            if Path(path).resolve().is_relative_to(self.store):
                opened.append(flags)
            return real_open(path, flags, *args, **kwargs)
        with patch('os.open', recording), patch('builtins.open', side_effect=AssertionError('builtins.open used')):
            self.read_all()
        self.assertEqual(len(opened), 2)  # one per reader call
        self.assertTrue(all(flags & WRITE_FLAGS == 0 and flags & os.O_NOFOLLOW for flags in opened), opened)

    def test_no_system_one_input_accepts_an_adapter_record(self):
        self.consent('rollout,system-one')
        triplets, messages = self.read_all()
        before = snapshot(self.store)
        for record in (triplets[0], messages):
            with self.assertRaises(ValueError):
                shadow.validate_episode(record)
            with self.assertRaises(shadow.StoreRefused):
                shadow.append(record)
            with self.assertRaises((ValueError, KeyError, TypeError)):
                shadow.build_episode(record, 'analyze-work', 'aim')
        self.assertEqual(snapshot(self.store), before)

    def test_lightning_code_names_no_system_one_input(self):
        """Static half: Lightning code reaches System One only through read_day, and System One imports no Lightning."""
        for path in (ROOT / 'agent_braid').glob('lightning_*.py'):
            for node in ast.walk(ast.parse(path.read_text())):
                if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                        and node.value.id == 'system_one_shadow':
                    self.assertEqual(node.attr, 'read_day', path.name)
                self.assertFalse(isinstance(node, ast.ImportFrom) and node.module == 'system_one_shadow',
                                 path.name)  # no `from .system_one_shadow import ...`
        for path in (ROOT / 'agent_braid').glob('system_one*.py'):
            self.assertNotIn('lightning', path.read_text(), path.name)


if __name__ == '__main__':
    unittest.main()
