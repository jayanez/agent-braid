# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 T013: the System One store negative-control matrix and telemetry path parity.

Every hostile layout must be refused without raising out of the observer, must leave
the caller's envelope byte-identical to `off`, and must increment the matching
in-memory refusal counter. The same layouts are then run against the telemetry path
checker to show that both refuse them.
"""
from __future__ import annotations

import errno
import fcntl
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

from agent_braid import system_one_shadow as shadow
from agent_braid import tooling_mcp, tooling_telemetry
from tests.test_system_one_shadow import SAMPLE, Base, counter_uuid


class Matrix(Base):
    def assert_refused(self, reason='unavailable', store=None):
        """Shadow and off envelopes are identical and `reason` was counted exactly once."""
        counts = shadow.refusal_counts().get(reason, 0)
        with patch.object(shadow, 'default_directory', return_value=store or self.store), \
                patch.object(tooling_mcp, 'uuid', counter_uuid()):
            on = json.dumps(self.invoke(self.service(), SAMPLE), sort_keys=True)
        with patch.object(tooling_mcp, 'uuid', counter_uuid()):
            off = json.dumps(self.invoke(self.service('off'), SAMPLE), sort_keys=True)
        self.assertEqual(on, off)
        self.assertEqual(json.loads(off)['status'], 'ok')
        self.assertEqual(shadow.refusal_counts().get(reason, 0), counts + 1)

    def private_store(self):
        self.store.mkdir(mode=0o700)
        self.store.chmod(0o700)

    def day_file(self, mode=0o600, size=0):
        path = self.store / f'episodes-{shadow.today().isoformat()}.jsonl'
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT, 0o600)
        os.ftruncate(descriptor, size)
        os.close(descriptor)
        path.chmod(mode)
        return path

    def nested_store(self, level):
        """A store whose path has a symlink at `level` of ('a', 'b', 'store')."""
        parts = ['a', 'b', 'store']
        root = self.base / f'root{level}'
        target = self.base / f'target{level}'
        current = root
        for name in parts[:level]:
            current = current / name
            current.mkdir(parents=True, mode=0o700)
        current.mkdir(parents=True, mode=0o700, exist_ok=True)
        target.mkdir(mode=0o700)
        beneath = target
        for name in parts[level + 1:]:
            beneath = beneath / name
            beneath.mkdir(mode=0o700)
        (current / parts[level]).symlink_to(target)
        return root.joinpath(*parts), target

    def assert_untouched(self, target):
        self.assertEqual([p for p in target.rglob('*') if not p.is_dir()], [])


class NegativeControlTests(Matrix):
    def test_symlink_at_each_level_of_the_store_path_is_refused(self):
        for level, name in enumerate(('first ancestor', 'second ancestor', 'store directory')):
            with self.subTest(level=name):
                store, target = self.nested_store(level)
                self.assert_refused(store=store)
                self.assert_untouched(target)

    def test_symlinked_day_file_is_refused_and_its_target_untouched(self):
        self.private_store()
        target = self.base / 'victim'
        target.write_bytes(b'keep')
        (self.store / f'episodes-{shadow.today().isoformat()}.jsonl').symlink_to(target)
        self.assert_refused()
        self.assertEqual(target.read_bytes(), b'keep')

    def test_symlinked_lock_file_is_refused_and_its_target_untouched(self):
        self.private_store()
        target = self.base / 'victim'
        target.write_bytes(b'keep')
        (self.store / 'store.lock').symlink_to(target)
        self.assert_refused()
        self.assertEqual(target.read_bytes(), b'keep')
        self.assertEqual(self.episodes(), [])

    def test_store_inside_a_repository_ancestor_is_refused(self):
        layouts = {
            'git directory': lambda root: (root / '.git').mkdir(),
            'git file': lambda root: (root / '.git').write_text('gitdir: elsewhere\n'),
            'bare repository': lambda root: [(root / 'HEAD').write_text('ref: refs/heads/main\n'),
                                             (root / 'objects').mkdir(), (root / 'refs').mkdir()],
        }
        for name, make in layouts.items():
            with self.subTest(layout=name):
                root = self.base / name.replace(' ', '-')
                root.mkdir()
                make(root)
                store = root / 'nested' / 'store'
                self.assert_refused(store=store)
                self.assertFalse(store.exists())

    def test_group_readable_day_file_is_refused_without_growing(self):
        self.private_store()
        path = self.day_file(mode=0o640)
        self.assert_refused()
        self.assertEqual(path.stat().st_size, 0)

    def test_world_readable_store_directory_is_refused(self):
        self.private_store()
        self.store.chmod(0o705)
        self.assert_refused()
        self.assertEqual(list(self.store.iterdir()), [])

    def test_extra_hard_link_to_the_day_file_is_refused_without_growing(self):
        self.private_store()
        path = self.day_file()
        os.link(path, self.base / 'alias')
        self.assert_refused()
        self.assertEqual((path.stat().st_size, path.stat().st_nlink), (0, 2))

    def test_foreign_owner_is_refused_without_changing_ownership(self):
        self.private_store()
        path = self.day_file()
        # Simulated: this process claims another user id; nothing is chowned.
        with patch.object(os, 'getuid', return_value=os.getuid() + 1):
            self.assert_refused()
        self.assertEqual(path.stat().st_size, 0)

    def test_open_descriptor_checks_hold_when_the_path_check_is_bypassed(self):
        # A file swapped in after the path check is still caught on the open descriptor.
        real = shadow._safe

        def lenient(path, *, directory=False):
            return Path(path) if Path(path).name.startswith('episodes-') else real(path, directory=directory)

        self.private_store()
        path = self.day_file(mode=0o640)
        with patch.object(shadow, '_safe', lenient):
            self.assert_refused()
        path.chmod(0o600)
        os.link(path, self.base / 'alias')
        with patch.object(shadow, '_safe', lenient):
            self.assert_refused()
        self.assertEqual(path.stat().st_size, 0)
        self.assertEqual(self.episodes(), [])

    def test_oversize_day_file_is_refused_without_growing(self):
        self.private_store()
        path = self.day_file(size=shadow.MAX_FILE_BYTES - 10)
        self.assert_refused('oversize')
        self.assertEqual(path.stat().st_size, shadow.MAX_FILE_BYTES - 10)

    def test_day_file_with_room_still_takes_the_episode(self):
        self.private_store()
        path = self.day_file(size=shadow.MAX_FILE_BYTES - 4096)
        self.invoke(self.service(), SAMPLE)
        self.assertEqual(shadow.refusal_counts().get('oversize', 0), 0)
        self.assertGreater(path.stat().st_size, shadow.MAX_FILE_BYTES - 4096)
        self.assertLessEqual(path.stat().st_size, shadow.MAX_FILE_BYTES)

    def test_busy_lock_is_refused(self):
        self.private_store()
        descriptor = os.open(self.store / 'store.lock', os.O_RDWR | os.O_CREAT, 0o600)
        self.addCleanup(os.close, descriptor)
        fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
        self.assert_refused('busy')
        self.assertEqual(self.episodes(), [])

    def test_unknown_file_is_neither_read_nor_touched_and_does_not_disable_the_store(self):
        # Implemented policy (see test_system_one_shadow): unrelated names are ignored by
        # append and retention, and are left in place with a message by purge.
        self.private_store()
        stray = self.store / 'notes.txt'
        stray.write_bytes(b'user data')
        stray.chmod(0o640)
        self.invoke(self.service(), SAMPLE)
        self.assertEqual(len(self.episodes()), 1)
        self.assertEqual(shadow.refusal_counts(), {})
        self.assertEqual((stray.read_bytes(), stray.stat().st_mode & 0o777), (b'user data', 0o640))
        result = shadow.purge()
        self.assertEqual(result['leftover'], ['notes.txt'])
        self.assertEqual(stray.read_bytes(), b'user data')

    def test_unsafe_entry_named_like_a_day_file_is_refused(self):
        self.private_store()
        (self.store / f'episodes-{shadow.today().isoformat()}.jsonl').mkdir(mode=0o700)
        self.assert_refused()

    def test_full_disk_is_refused_and_leaves_no_partial_line(self):
        self.private_store()
        self.assertIsNotNone(shadow._secret())  # salt exists, so only the episode write fails
        disk_full = OSError(errno.ENOSPC, 'No space left on device')
        with patch.object(shadow.os, 'write', side_effect=disk_full):
            self.assert_refused()
        self.assertEqual(self.stored_bytes(), b'')
        self.invoke(self.service(), SAMPLE)  # the store recovers once the disk has room
        self.assertEqual(len(self.episodes()), 1)

    def test_read_only_store_directory_is_refused(self):
        if os.geteuid() == 0:
            self.skipTest('root bypasses directory permissions')
        self.private_store()
        self.store.chmod(0o500)
        self.addCleanup(self.store.chmod, 0o700)
        self.assert_refused()
        self.assertEqual(list(self.store.iterdir()), [])

    def test_observe_itself_swallows_a_refusal(self):
        self.private_store()
        self.store.chmod(0o750)
        with patch.object(shadow, 'build_episode', return_value={'not': 'valid'}):
            self.assertIsNone(shadow.observe('analyze-work', 'aim', {}))
        self.assertEqual(shadow.refusal_counts().get('unavailable'), 1)


class TelemetryParityTests(Matrix):
    """The System One store reuses the telemetry checker; both must refuse the same layouts."""

    def both_refuse(self, path, *, directory=False):
        for name, checker in (('telemetry', tooling_telemetry._path), ('system one', shadow._safe)):
            with self.subTest(checker=name, path=path.name), self.assertRaises(ValueError):
                checker(path, directory=directory)

    def test_the_store_delegates_to_the_telemetry_checker(self):
        self.assertIs(shadow._path, tooling_telemetry._path)
        self.assertIs(shadow._canonical, tooling_telemetry._canonical)
        self.assertIs(shadow.today, tooling_telemetry.today)

    def test_safe_layouts_are_accepted_by_both(self):
        self.private_store()
        path = self.day_file()
        for checker in (tooling_telemetry._path, shadow._safe):
            self.assertEqual(checker(self.store, directory=True), self.store)
            self.assertEqual(checker(path), path)
            self.assertEqual(checker(self.store / 'absent'), self.store / 'absent')

    def test_symlinks_at_every_level_are_refused_by_both(self):
        for level in range(3):
            store, _ = self.nested_store(level)
            self.both_refuse(store, directory=True)
            self.both_refuse(store / f'episodes-{shadow.today().isoformat()}.jsonl')

    def test_symlinked_file_is_refused_by_both(self):
        self.private_store()
        victim = self.base / 'victim'
        victim.write_bytes(b'')
        victim.chmod(0o600)
        link = self.store / f'episodes-{shadow.today().isoformat()}.jsonl'
        link.symlink_to(victim)
        self.both_refuse(link)

    def test_repository_ancestors_are_refused_by_both(self):
        for name, make in {'dot-git': lambda r: (r / '.git').mkdir(),
                           'dot-git-file': lambda r: (r / '.git').write_text('gitdir: x\n'),
                           'bare': lambda r: [(r / 'HEAD').write_text('x\n'), (r / 'objects').mkdir(),
                                              (r / 'refs').mkdir()]}.items():
            root = self.base / name
            root.mkdir()
            make(root)
            self.both_refuse(root / 'store', directory=True)

    def test_group_readable_paths_are_refused_by_both(self):
        self.private_store()
        self.store.chmod(0o750)
        self.both_refuse(self.store, directory=True)
        self.store.chmod(0o700)
        self.both_refuse(self.day_file(mode=0o640))

    def test_extra_hard_link_is_refused_by_both(self):
        self.private_store()
        path = self.day_file()
        os.link(path, self.base / 'alias')
        self.both_refuse(path)

    def test_foreign_owner_is_refused_by_both(self):
        self.private_store()
        path = self.day_file()
        with patch.object(os, 'getuid', return_value=os.getuid() + 1):
            self.both_refuse(self.store, directory=True)
            self.both_refuse(path)

    def test_wrong_file_type_and_non_canonical_paths_are_refused_by_both(self):
        self.private_store()
        self.both_refuse(self.store)  # a directory where a file is required
        path = self.day_file()
        self.both_refuse(path, directory=True)  # a file where a directory is required
        self.both_refuse(self.store / '..' / self.store.name / path.name)

    def test_only_the_wording_differs(self):
        self.private_store()
        self.store.chmod(0o750)
        with self.assertRaises(ValueError) as telemetry:
            tooling_telemetry._path(self.store, directory=True)
        with self.assertRaises(ValueError) as system_one:
            shadow._safe(self.store, directory=True)
        self.assertIn('telemetry', str(telemetry.exception))
        self.assertEqual(str(system_one.exception), str(telemetry.exception).replace('telemetry', 'System One store'))


class UnlinkOwnTests(Base):
    """Purge removes planted links at the salt paths without following them."""

    def test_purge_removes_a_dangling_link_planted_at_the_salt(self):
        shadow._secret()
        path = shadow.default_directory() / shadow.SALT_FILE
        path.unlink()
        path.symlink_to(path.parent / 'missing-target')
        result = shadow.purge()
        self.assertFalse(path.is_symlink())
        self.assertNotIn(shadow.SALT_FILE, result.get('leftover', []))

    def test_purge_removes_a_link_without_touching_its_target(self):
        shadow._secret()
        path = shadow.default_directory() / shadow.SALT_FILE
        target = self.base / 'target'
        target.write_bytes(b'kept')
        path.unlink()
        path.symlink_to(target)
        shadow.purge()
        self.assertFalse(path.is_symlink())
        self.assertEqual(target.read_bytes(), b'kept')


if __name__ == '__main__':
    unittest.main()
