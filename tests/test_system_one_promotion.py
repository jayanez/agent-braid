# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-066 REQ-401 / T401 plumbing: the immutable System One promotion registry.

`advise` is effective for a decision point only on a valid, digest-pinned owner go; the empty registry
(the shipped state) changes nothing. Rollback to `off` is atomic under interruption, and a tampered or
unknown record is refused.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
import unittest
from unittest import mock

from agent_braid import system_one_promotion as promotion
from agent_braid.plugin_mcp import PluginRouter
from agent_braid.plugin_registry import apply, load, plan_setup

PIN = 'a' * 64
EVIDENCE = 'b' * 64


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.home = self.base / 'state'
        self.home.mkdir(mode=0o700)
        self.path = self.home / promotion.FILENAME

    def go(self, point='DP-1', manifest=PIN):
        return promotion.record_go(self.home, point, evidence_digest=EVIDENCE, manifest_digest=manifest,
                                   decided_on='2026-11-14')

    def rewrite(self, change):
        value = json.loads(self.path.read_text())
        change(value)
        self.path.write_text(json.dumps(value))
        os.chmod(self.path, 0o600)


class EmptyRegistryTests(Base):
    def test_absent_registry_holds_no_records(self):
        self.assertEqual(promotion.load(self.home), ())
        self.assertFalse(self.path.exists())

    def test_empty_registry_never_resolves_advise(self):
        for configured, expected in (('advise', 'shadow'), ('shadow', 'shadow'), ('off', 'off')):
            with self.subTest(configured=configured):
                resolved = promotion.resolve(configured, promotion.load(self.home), PIN)
                self.assertEqual(resolved['activeMode'], expected)
                self.assertEqual(resolved['decisionPoints']['DP-1']['activeMode'], expected)
                self.assertIn(resolved['reason'], promotion.REASONS)
        self.assertEqual(promotion.resolve('advise', (), PIN)['reason'], 'no-owner-go')
        self.assertEqual(promotion.resolve('shadow', (), PIN)['reason'], 'configured')

    def test_unknown_configured_mode_is_refused(self):
        with self.assertRaises(promotion.PromotionError):
            promotion.resolve('assist', (), PIN)


class GoAndRollbackTests(Base):
    def test_valid_go_enables_advise_only_for_its_decision_point(self):
        record = self.go()
        self.assertEqual(record['decision'], 'go')
        records = promotion.load(self.home)
        self.assertEqual(len(records), 1)
        resolved = promotion.resolve('advise', records, PIN)
        self.assertEqual((resolved['activeMode'], resolved['reason']), ('advise', 'owner-go'))
        # A go never lifts the consent: shadow and off stay as configured.
        self.assertEqual(promotion.resolve('shadow', records, PIN)['activeMode'], 'shadow')
        self.assertEqual(promotion.resolve('off', records, PIN)['activeMode'], 'off')

    def test_go_pinned_to_another_backend_identity_does_not_promote(self):
        self.go(manifest='c' * 64)
        resolved = promotion.resolve('advise', promotion.load(self.home), PIN)
        self.assertEqual((resolved['activeMode'], resolved['reason']), ('shadow', 'identity-mismatch'))

    def test_rollback_demotes_the_decision_point_to_off(self):
        self.go()
        promotion.rollback(self.home, 'DP-1', decided_on='2026-11-15')
        records = promotion.load(self.home)
        self.assertEqual([r['decision'] for r in records], ['go', 'rollback'])
        for configured in ('advise', 'shadow'):
            resolved = promotion.resolve(configured, records, PIN)
            self.assertEqual((resolved['activeMode'], resolved['reason']), ('off', 'rolled-back'))
        self.go()  # a new owner go after a rollback promotes again
        self.assertEqual(promotion.resolve('advise', promotion.load(self.home), PIN)['activeMode'], 'advise')

    def test_records_are_immutable_and_chained(self):
        self.go()
        promotion.rollback(self.home, 'DP-1', decided_on='2026-11-15')
        first, second = promotion.load(self.home)
        with self.assertRaises(TypeError):
            first['decision'] = 'rollback'
        self.assertEqual(second['previousDigest'], first['recordDigest'])
        self.assertEqual((first['sequence'], second['sequence']), (0, 1))

    def test_unknown_decision_point_and_malformed_inputs_are_refused_without_writing(self):
        for call in (lambda: self.go(point='DP-9'),
                     lambda: self.go(manifest='sha256:' + PIN),
                     lambda: promotion.record_go(self.home, 'DP-1', evidence_digest='E' * 64,
                                                 manifest_digest=PIN, decided_on='2026-11-14'),
                     lambda: promotion.record_go(self.home, 'DP-1', evidence_digest=EVIDENCE,
                                                 manifest_digest=PIN, decided_on='yesterday'),
                     lambda: promotion.rollback(self.home, 'DP-2', decided_on='2026-11-14')):
            with self.subTest(call=call), self.assertRaises(promotion.PromotionError):
                call()
        self.assertFalse(self.path.exists())

    def test_impossible_calendar_date_is_refused(self):
        with self.assertRaises(promotion.PromotionError):
            promotion.record_go(self.home, 'DP-1', evidence_digest=EVIDENCE, manifest_digest=PIN,
                                decided_on='2026-02-30')
        self.assertFalse(self.path.exists())

    def test_full_registry_refuses_a_go_but_never_a_rollback(self):
        self.go()
        with mock.patch.object(promotion, 'MAX_RECORDS', 1):
            with self.assertRaises(promotion.PromotionError):
                self.go()
            promotion.rollback(self.home, 'DP-1', decided_on='2026-11-15')
            # The oversized registry now fails verification and promotes nothing.
            status = promotion.status(self.home, 'advise', PIN)
            self.assertEqual((status['valid'], status['decisionPoints']['DP-1']['activeMode']), (False, 'shadow'))
        self.assertEqual([r['decision'] for r in promotion.load(self.home)], ['go', 'rollback'])

    def test_busy_registry_lock_has_its_own_code(self):
        import fcntl
        fd = os.open(self.home / 'registry.lock', os.O_CREAT | os.O_RDWR, 0o600)
        self.addCleanup(os.close, fd)
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with self.assertRaises(promotion.PromotionError) as caught:
            self.go()
        self.assertEqual(caught.exception.code, 'promotion-busy')

    def test_unreadable_registry_is_reported_invalid(self):
        self.go()
        with mock.patch.object(promotion, '_raw', side_effect=OSError('EIO')):
            status = promotion.status(self.home, 'advise', PIN)
        self.assertFalse(status['valid'])

    def test_registry_file_is_private_and_regular(self):
        self.go()
        info = self.path.stat()
        self.assertTrue(stat.S_ISREG(info.st_mode))
        self.assertEqual(stat.S_IMODE(info.st_mode), 0o600)
        self.assertEqual(sorted(p.name for p in self.home.iterdir() if p.name.startswith('.')), [])


class TamperTests(Base):
    def setUp(self):
        super().setUp()
        self.go()

    def assert_refused(self, code='promotion-tampered'):
        with self.assertRaises(promotion.PromotionError) as caught:
            promotion.load(self.home)
        self.assertEqual(caught.exception.code, code)
        status = promotion.status(self.home, 'advise', PIN)
        self.assertFalse(status['valid'])
        self.assertEqual(status['decisionPoints']['DP-1'], {'activeMode': 'shadow', 'reason': 'promotion-registry-invalid'})
        with self.assertRaises(promotion.PromotionError):
            self.go()  # never append onto a registry that fails verification

    def test_edited_record_is_refused(self):
        self.rewrite(lambda v: v['records'][0].update(manifestDigest='d' * 64))
        self.assert_refused()

    def test_forged_record_digest_is_refused(self):
        self.rewrite(lambda v: v['records'][0].update(recordDigest='e' * 64))
        self.assert_refused()

    def test_removed_or_reordered_chain_is_refused(self):
        promotion.rollback(self.home, 'DP-1', decided_on='2026-11-15')
        self.rewrite(lambda v: v['records'].pop(0))  # dropping the go leaves a dangling chain
        self.assert_refused()

    def test_unknown_fields_schema_and_values_are_refused(self):
        changes = (lambda v: v['records'][0].update(extra=True),
                   lambda v: v.update(schema='agent-braid-s1-promotion/v9'),
                   lambda v: v['records'][0].update(decisionPoint='DP-7'),
                   lambda v: v['records'][0].update(decision='advise'),
                   lambda v: v.update(records={}))
        original = self.path.read_bytes()
        for change in changes:
            with self.subTest(change=change):
                self.path.write_bytes(original)
                self.rewrite(change)
                self.assert_refused('promotion-shape')

    def test_duplicate_members_and_nonfinite_values_are_refused(self):
        raw = self.path.read_text()
        self.path.write_text(raw.replace('"schema"', '"schema": "x", "schema"', 1))
        self.assert_refused('promotion-shape')
        self.path.write_text('{"schema": NaN, "records": []}')
        self.assert_refused('promotion-shape')

    def test_oversized_registry_is_refused(self):
        self.path.write_bytes(b' ' * (promotion.MAX_BYTES + 1))
        self.assert_refused('promotion-shape')

    def test_symlinked_or_shared_registry_is_refused(self):
        target = self.base / 'elsewhere.json'
        target.write_bytes(self.path.read_bytes())
        os.chmod(target, 0o600)
        self.path.unlink()
        self.path.symlink_to(target)
        self.assert_refused('promotion-unsafe-path')
        self.path.unlink()
        target.rename(self.path)
        os.chmod(self.path, 0o644)
        self.assert_refused('promotion-unsafe-path')


class AtomicRollbackTests(Base):
    def test_interrupted_rollback_leaves_the_previous_registry_intact(self):
        self.go()
        before = self.path.read_bytes()
        with mock.patch.object(promotion.os, 'replace', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                promotion.rollback(self.home, 'DP-1', decided_on='2026-11-15')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual([p.name for p in self.home.iterdir() if p.name.startswith('.')], [])
        self.assertEqual([r['decision'] for r in promotion.load(self.home)], ['go'])

    def test_interrupted_write_before_rename_never_exposes_a_partial_file(self):
        self.go()
        before = self.path.read_bytes()
        real_fsync = os.fsync

        def crash(fd):
            real_fsync(fd)
            raise OSError('simulated power loss')
        with mock.patch.object(promotion.os, 'fsync', side_effect=crash):
            with self.assertRaises(OSError):
                promotion.rollback(self.home, 'DP-1', decided_on='2026-11-15')
        self.assertEqual(self.path.read_bytes(), before)
        self.assertEqual([p.name for p in self.home.iterdir() if p.name.startswith('.')], [])

    def test_completed_rollback_is_visible_in_one_step(self):
        self.go()
        promotion.rollback(self.home, 'DP-1', decided_on='2026-11-15')
        status = promotion.status(self.home, 'advise', PIN)
        self.assertEqual(status['decisionPoints']['DP-1'], {'activeMode': 'off', 'reason': 'rolled-back'})
        self.assertEqual(status['records'], 2)


class StatusReportingTests(Base):
    def test_status_of_the_empty_registry(self):
        status = promotion.status(self.home, 'advise', PIN)
        self.assertEqual(status, {'present': False, 'valid': True, 'records': 0,
                                  'decisionPoints': {'DP-1': {'activeMode': 'shadow', 'reason': 'no-owner-go'}},
                                  'executionAuthorization': False})


class PluginWiringTests(Base):
    def setUp(self):
        super().setUp()
        self.repo = self.base / 'project'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)

    def configure(self, mode):
        preview = plan_setup(self.home, [self.repo], system_one=mode)
        apply(self.home, preview, preview['previewDigest'])
        return preview

    def test_advise_consent_is_accepted_and_previewed(self):
        preview = self.configure('advise')
        self.assertEqual(load(self.home)['systemOne'], 'advise')
        self.assertTrue(any('advise' in e and 'owner go' in e for e in preview['effects']))
        self.assertTrue(any('Earlier plugin versions refuse' in e for e in preview['effects']))

    def test_advise_without_go_serves_shadow_and_reports_the_reason(self):
        self.configure('advise')
        router = PluginRouter(self.home)
        self.assertEqual({s.config.system_one for s in router.services.values()}, {'shadow'})
        status = router.status()
        block = status['systemOne']
        self.assertEqual((block['configuredMode'], block['activeMode'], block['reason']),
                         ('advise', 'shadow', 'no-owner-go'))
        self.assertEqual(block['promotion']['decisionPoints']['DP-1'],
                         {'activeMode': 'shadow', 'reason': 'no-owner-go'})
        self.assertIs(block['executionAuthorization'], False)
        self.assertIs(status['executionAuthorization'], False)

    def test_advise_with_valid_go_reports_advise_without_authority(self):
        from agent_braid import system_one_shadow as shadow
        self.configure('advise')
        promotion.record_go(self.home, 'DP-1', evidence_digest=EVIDENCE,
                            manifest_digest=shadow.EXPECTED_MANIFEST_DIGEST, decided_on='2026-11-14')
        router = PluginRouter(self.home)
        block = router.status()['systemOne']
        self.assertEqual((block['activeMode'], block['reason']), ('advise', 'owner-go'))
        self.assertIs(block['executionAuthorization'], False)
        # Effective advise serves the DP-1 rule advice and keeps recording shadow episodes.
        self.assertEqual({s.config.system_one for s in router.services.values()}, {'advise'})

    def test_rollback_after_connect_requires_a_reconnect(self):
        from agent_braid import system_one_shadow as shadow
        self.configure('advise')
        promotion.record_go(self.home, 'DP-1', evidence_digest=EVIDENCE,
                            manifest_digest=shadow.EXPECTED_MANIFEST_DIGEST, decided_on='2026-11-14')
        router = PluginRouter(self.home)
        self.assertFalse(router.status()['reconnectRequired'])
        promotion.rollback(self.home, 'DP-1', decided_on='2026-11-15')
        status = router.status()
        self.assertTrue(status['reconnectRequired'])
        self.assertEqual(status['systemOne']['activeMode'], 'advise')
        reconnected = PluginRouter(self.home)
        self.assertEqual((reconnected.status()['systemOne']['activeMode'], reconnected.status()['reconnectRequired']),
                         ('off', False))
        self.assertEqual({s.config.system_one for s in reconnected.services.values()}, {'off'})

    def test_off_and_shadow_status_report_configured_reason(self):
        router = PluginRouter(self.home)
        block = router.status()['systemOne']
        self.assertEqual((block['activeMode'], block['reason']), ('off', 'configured'))
        self.assertIs(block['executionAuthorization'], False)

    def test_invalid_promotion_registry_never_stops_serving(self):
        self.configure('advise')
        self.path.write_text('{}')
        os.chmod(self.path, 0o600)
        router = PluginRouter(self.home)
        self.assertTrue(router.services)
        block = router.status()['systemOne']
        self.assertEqual((block['activeMode'], block['reason']), ('shadow', 'promotion-registry-invalid'))
        self.assertFalse(block['promotion']['valid'])


if __name__ == '__main__':
    unittest.main()
