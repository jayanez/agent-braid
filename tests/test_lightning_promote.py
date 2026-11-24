# SPDX-License-Identifier: AGPL-3.0-only
"""SPEC-073: Lightning promotion through the HAR profile registry (procedures 001-008)."""
import ast
from contextlib import redirect_stdout
from io import StringIO
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from agent_braid.cli import main
from agent_braid import lightning_promote as lp
from agent_braid import lightning_store as st
from agent_braid import harness_promotion as hp
from agent_braid.harness_evaluation import EvaluationRecord, Registration, _record
from agent_braid.lightning_evaluation import spec049_pair
from agent_braid.lightning_resources import sha256_text

ROOT = Path(__file__).resolve().parents[1]
SCOPE = 'lightning.skill.analyze'
BASE_TEXT = '# analyze\n\nbaseline guidance\n'
TEXT = '# analyze\n\nimproved guidance\nnew line\n'
IDENTITY = {'sourceSha256': 'd' * 64, 'host': 'claude-code', 'model': 'claude-sonnet-5-5',
            'toolSetSha256': 'e' * 64, 'policySha256': 'f' * 64}


def summary(verdict):
    return {'hosts': {'claude-code': {'verdict': verdict, 'trials': 30, 'prompts': 10,
                                      'firstAttemptPrompts': 8, 'withinRetryPrompts': 10}}}


def low_reason():
    """An override reason whose digest sorts before the baseline's among the cited evidence."""
    base = sha256_text(BASE_TEXT)
    return next(r for r in (f'drill {i}' for i in range(1000)) if sha256_text(r) < base)


def pair(candidate, base_verdict='misses', primary_verdict='meets', base=None):
    base = base or sha256_text(BASE_TEXT)
    return spec049_pair(
        baseline={'arm': 'A0', 'candidateSha256': base, 'canaryHits': 0, 'summary': summary(base_verdict)},
        primary={'arm': 'A2', 'candidateSha256': candidate, 'canaryHits': 0,
                 'summary': summary(primary_verdict)},
        heldout_sha256='b' * 64, protocol_sha256='c' * 64,
        costs={'A': {'rollouts': 30}, 'C': {'rollouts': 30}})


SAFE = {'unsafeAdmissions': 0, 'authorityViolations': 0, 'effectViolations': 0}
HUMAN = {'kind': 'human', 'id': 'owner'}


def noninferior(evaluation):
    """Synthetic fixture (OD-4): the same report with every C-vs-A stratum assessed noninferior."""
    data = evaluation.to_dict()
    for stratum in data['strata'].values():
        stratum['comparisons']['C-vs-A']['noninferiority'] = {
            'status': 'assessed', 'verdict': 'noninferior', 'reasons': []}
    return _record(EvaluationRecord, data)


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name).resolve() / 'home'
        self.run = st.RunStore(self.home, 'run-1')
        self.run.create(config_digest='c' * 64, now=1000.0)
        self.sha = sha256_text(TEXT)
        self.run.write_candidate_text(self.sha, TEXT)
        self.registration, self.evaluation = pair(self.sha)
        self.root = Path(self.tmp.name).resolve() / 'root'
        self.target = self.root / lp.SCOPES[SCOPE].target
        self.target.parent.mkdir(parents=True)
        self.target.write_text(BASE_TEXT)

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, sha=None, scope=SCOPE, **overrides):
        kwargs = {'registration': self.registration, 'evaluation': self.evaluation, 'identity': IDENTITY,
                  **overrides}
        return lp.build_record(self.run, sha or self.sha, scope, **kwargs)

    def refused(self, reason, call):
        with self.assertRaises(lp.PromoteError) as caught:
            call()
        self.assertEqual(caught.exception.reason, reason)


class ScopeMapTests(unittest.TestCase):
    def test_closed_map_has_only_analyze_and_its_path_exists(self):
        self.assertEqual(set(lp.SCOPES), {SCOPE})
        entry = lp.SCOPES[SCOPE]
        self.assertEqual(entry.limit, 32 * 1024)
        self.assertTrue((ROOT / entry.target).is_file())

    def test_unknown_scope_is_refused(self):
        for scope in ('lightning.skill.plan', '', None, 'lightning.skill.analyze '):
            with self.assertRaises(lp.PromoteError) as caught:
                lp.scope_entry(scope)
            self.assertEqual(caught.exception.reason, 'unknown-scope')


class BuildRecordTests(Base):
    """procedure_001 / SC-001."""

    def test_valid_native_record_with_supported_h1(self):
        record = self.build()
        self.assertEqual((record.scope, record.candidateSha256, record.text), (SCOPE, self.sha, TEXT))
        self.assertEqual(record.target, lp.SCOPES[SCOPE].target)
        self.assertEqual(record.heldOutSupport, 'supported')
        self.assertEqual(record.profile['cohort'], 'native')
        self.assertEqual(record.profile['effects'], ['skill-text'])
        self.assertEqual(record.evidence, sorted([self.registration.sha256, self.evaluation.sha256]))
        self.assertFalse(record.executionAuthorization)

    def test_h1_not_supported_is_reported_not_raised(self):
        registration, evaluation = pair(self.sha, base_verdict='meets')
        record = self.build(registration=registration, evaluation=evaluation)
        self.assertEqual(record.heldOutSupport, 'no-held-out-support')
        registration, evaluation = pair(self.sha, primary_verdict='misses')
        self.assertEqual(self.build(registration=registration, evaluation=evaluation).heldOutSupport,
                         'no-held-out-support')

    def test_unknown_scope_refused(self):
        self.refused('unknown-scope', lambda: self.build(scope='lightning.skill.plan'))

    def test_candidate_not_stored(self):
        other = sha256_text('other text\n')
        registration, evaluation = pair(other)
        self.refused('candidate-not-stored',
                     lambda: self.build(sha=other, registration=registration, evaluation=evaluation))

    def test_tampered_stored_text_is_a_digest_mismatch(self):
        path = self.run.root / 'candidates' / f'{self.sha}.md'
        path.write_text(TEXT + 'injected\n')
        self.refused('digest-mismatch', self.build)

    def test_oversize_text_refused(self):
        big = '# analyze\n' + 'x' * (32 * 1024)
        sha = sha256_text(big)
        self.run.write_candidate_text(sha, big)
        registration, evaluation = pair(sha)
        self.refused('text-too-large', lambda: self.build(sha=sha, registration=registration,
                                                          evaluation=evaluation))

    def test_pair_not_naming_the_candidate_refused(self):
        registration, evaluation = pair(sha256_text('other text\n'))
        self.refused('candidate-mismatch', lambda: self.build(registration=registration,
                                                              evaluation=evaluation))

    def test_mismatched_pair_refused(self):
        registration, _ = pair(self.sha, base='9' * 64)
        self.refused('registration-mismatch', lambda: self.build(registration=registration))

    def test_arm_c_equal_to_base_refused(self):
        registration, evaluation = pair(self.sha, base=self.sha)
        self.refused('no-candidate', lambda: self.build(registration=registration, evaluation=evaluation))

    def test_bad_identity_refused(self):
        self.refused('invalid-profile', lambda: self.build(identity={**IDENTITY, 'host': ''}))

    def test_committed_spec072_pair_loads_and_its_winner_is_not_supported(self):
        evidence = ROOT / 'specs/072-lightning-prompt-optimization/evidence'
        registration = lp.load_record(Registration, (evidence / 'heldout-registration.json').read_bytes())
        evaluation = lp.load_record(EvaluationRecord,
                                    (evidence / 'heldout-evaluation-record.json').read_bytes())
        self.assertEqual(evaluation.to_dict()['registrationSha256'], registration.sha256)
        # BL.2 promoted nothing: the committed winner has no held-out support.
        self.assertNotEqual(evaluation.to_dict()['h1']['outcome'], 'supported')

    def test_non_canonical_record_bytes_refused(self):
        raw = self.registration.canonical_bytes
        self.refused('invalid-evaluation', lambda: lp.load_record(Registration, raw + b' '))
        self.refused('invalid-evaluation', lambda: lp.load_record(Registration, b'{'))


def snapshot(*roots):
    """Every file under ``roots`` with its bytes (no write may happen during a preview)."""
    return {str(p): p.read_bytes() for r in roots if r.exists() for p in sorted(r.rglob('*')) if p.is_file()}


class PreviewTests(Base):
    """procedure_003 / SC-003 (preview half; apply is T005)."""

    def preview(self, **kwargs):
        return lp.preview_promote(self.build(), home=self.home, root=self.root, **kwargs)

    def test_preview_fields_and_no_writes(self):
        before = snapshot(self.home, self.root)
        doc = self.preview()
        self.assertEqual(snapshot(self.home, self.root), before)
        self.assertFalse(lp.registry_path(self.home, SCOPE).exists())
        self.assertEqual(doc['schema'], 'braid-lightning-promotion-preview/v0.1')
        self.assertEqual((doc['action'], doc['scope'], doc['targetPath']), ('promote', SCOPE, lp.SCOPES[SCOPE].target))
        self.assertIsNone(doc['currentSha256'])
        self.assertEqual(doc['candidateSha256'], self.sha)
        self.assertEqual(doc['fileSha256Before'], sha256_text(BASE_TEXT))
        self.assertEqual(doc['registrySha256Before'], sha256_text(''))
        self.assertEqual(doc['diffSummary'], {'added': 2, 'removed': 1})
        # The scope's first decision also cites the baseline file it replaces.
        self.assertEqual(doc['evidence'], sorted([self.registration.sha256, self.evaluation.sha256,
                                                  sha256_text(BASE_TEXT)]))
        self.assertEqual((doc['cohort'], doc['requiredDecision'], doc['heldOutSupport']),
                         ('native', 'approved', 'supported'))
        self.assertIs(doc['executionAuthorization'], False)
        self.assertNotIn(TEXT, json.dumps(doc))
        # A SPEC-072 pair is descriptive-only: the preview shows the apply would refuse (OD-4).
        self.assertEqual(doc['blockers'], ['regression-not-covered'])

    def test_digest_is_deterministic_and_bound_to_file_and_registry(self):
        first = self.preview()
        self.assertEqual(self.preview()['previewDigest'], first['previewDigest'])
        body = {k: v for k, v in first.items() if k not in ('previewDigest', 'executionAuthorization')}
        self.assertEqual(lp.seal(body)['previewDigest'], first['previewDigest'])
        self.target.write_text(BASE_TEXT + 'edit\n')
        self.assertNotEqual(self.preview()['previewDigest'], first['previewDigest'])

    def test_override_reason_is_cited_by_digest_and_validated(self):
        registration, evaluation = pair(self.sha, base_verdict='meets')
        record = self.build(registration=registration, evaluation=evaluation)
        plain = lp.preview_promote(record, home=self.home, root=self.root)
        self.assertIn('no-held-out-support', plain['blockers'])
        doc = lp.preview_promote(record, home=self.home, root=self.root, override_reason='drill only')
        self.assertNotIn('no-held-out-support', doc['blockers'])
        self.assertEqual(doc['overrideReason'], 'drill only')
        self.assertIn(sha256_text('drill only'), doc['evidence'])
        for bad in ('', '   ', 'a\nb', 'x' * 513, 3):
            self.refused('invalid-override-reason', lambda bad=bad: lp.preview_promote(
                record, home=self.home, root=self.root, override_reason=bad))

    def test_unavailable_target_refused(self):
        self.target.unlink()
        self.refused('target-unavailable', self.preview)
        os.symlink(self.root / 'elsewhere', self.target)
        (self.root / 'elsewhere').write_text(BASE_TEXT)
        self.refused('target-unavailable', self.preview)


class CliPreviewTests(Base):
    def files(self):
        paths = {}
        for name, raw in (('registration', self.registration.canonical_bytes),
                          ('evaluation', self.evaluation.canonical_bytes),
                          ('identity', json.dumps(IDENTITY).encode())):
            paths[name] = Path(self.tmp.name) / f'{name}.json'
            paths[name].write_bytes(raw)
        return paths

    def cli(self, *extra, candidate=None):
        f = self.files()
        argv = ['lightning', 'promote', '--home', str(self.home), '--root', str(self.root),
                '--candidate', candidate or self.sha, '--run-id', 'run-1',
                '--registration', str(f['registration']), '--evaluation', str(f['evaluation']),
                '--identity', str(f['identity']), *extra]
        out, err = StringIO(), StringIO()
        with redirect_stdout(out), patch('sys.stderr', err):
            code = main(argv)
        return code, out.getvalue(), err.getvalue()

    def test_cli_prints_the_preview_and_writes_nothing(self):
        before = snapshot(self.home, self.root)
        code, out, err = self.cli()
        self.assertEqual((code, err), (0, ''))
        doc = json.loads(out)
        self.assertEqual(doc, lp.preview_promote(self.build(), home=self.home, root=self.root))
        self.assertEqual(snapshot(self.home, self.root), before)

    def test_cli_refusal_is_one_fixed_line(self):
        code, out, err = self.cli('--scope', 'lightning.skill.plan')
        self.assertEqual((code, out, err), (2, '', 'lightning promote refused (unknown-scope)\n'))
        code, _, err = self.cli(candidate='0' * 64)
        self.assertEqual((code, err), (2, 'lightning promote refused (candidate-not-stored)\n'))


class ApplyTests(Base):
    """procedure_002 / SC-002 and the apply half of procedure_003."""

    def setUp(self):
        super().setUp()
        self.evaluation = noninferior(self.evaluation)

    def apply(self, record=None, digest=None, **kwargs):
        record = record or self.build()
        doc = lp.preview_promote(record, home=self.home, root=self.root,
                                 override_reason=kwargs.get('override_reason'))
        args = {'actor': HUMAN, 'safety': SAFE, 'at': 10, **kwargs}
        return lp.apply_promote(record, home=self.home, root=self.root,
                                preview_digest=digest or doc['previewDigest'], **args)

    def registry(self):
        return hp.load(lp.registry_path(self.home, SCOPE))

    def test_human_decide_begin_commit_writes_registry_and_file(self):
        doc = lp.preview_promote(self.build(), home=self.home, root=self.root)
        self.assertEqual(doc['blockers'], [])
        result = self.apply()
        self.assertEqual(result['status'], 'committed')
        self.assertIs(result['executionAuthorization'], False)
        self.assertEqual(self.target.read_text(), TEXT)
        self.assertEqual(result['fileSha256After'], self.sha)
        value = self.registry()
        self.assertEqual(lp.active_candidate(value), self.sha)
        self.assertEqual([e['event'] for e in value.journal], ['recorded', 'begun', 'committed'])
        decision = value.decisions[value.active]
        self.assertEqual((decision['actor'], decision['decision'], decision['cohort']),
                         (HUMAN, 'approved', 'native'))
        self.assertEqual(result['registrySha256After'], value.sha256)

    def test_bounded_write_set(self):
        before = snapshot(self.home, self.root)
        self.apply()
        after = snapshot(self.home, self.root)
        changed = {p for p in after if before.get(p) != after[p]} | (set(before) - set(after))
        registry = str(lp.registry_path(self.home, SCOPE))
        baseline = str(self.run.root / 'candidates' / f'{sha256_text(BASE_TEXT)}.md')
        self.assertEqual(changed, {registry, registry + '.lock', str(self.target), baseline})
        # The baseline text is kept content-addressed in the run store and cited by the decision.
        self.assertEqual(self.run.candidate_text(sha256_text(BASE_TEXT)), BASE_TEXT)
        self.assertEqual(lp.baseline_digest(self.registry()), sha256_text(BASE_TEXT))
        decision = self.registry().decisions[self.registry().active]
        self.assertEqual(list(decision['limits']), [lp.baseline_limit(sha256_text(BASE_TEXT))])

    def test_file_mode_is_kept(self):
        os.chmod(self.target, 0o640)
        self.apply()
        self.assertEqual(os.stat(self.target).st_mode & 0o777, 0o640)

    def test_change_between_preview_check_and_write_is_stale(self):
        real = lp.read_target
        calls = []

        def drifting(root, scope):
            calls.append(1)
            # Calls 1-2 are the human's preview and apply's recomputed one (equal digests);
            # call 3 is the re-read right before writing, which alone must catch the drift.
            return real(root, scope) + (b'drift\n' if len(calls) > 2 else b'')
        with patch.object(lp, 'read_target', drifting):
            self.refused('preview-stale', self.apply)
        self.assertEqual(len(calls), 3)
        self.assertFalse(lp.registry_path(self.home, SCOPE).exists())
        self.assertEqual(self.target.read_text(), BASE_TEXT)

    def test_automatic_actor_refused_and_nothing_written(self):
        before = snapshot(self.home, self.root)
        self.refused('automatic-promotion-disabled',
                     lambda: self.apply(actor={'kind': 'automatic-policy', 'id': 'policy'}))
        self.assertEqual(snapshot(self.home, self.root), before)

    def test_synthetic_cohort_refused(self):
        data = self.evaluation.to_dict()
        data['cohort'] = 'synthetic'
        self.refused('cohort-mismatch', lambda: self.build(evaluation=_record(EvaluationRecord, data)))

    def test_stale_identity_refused(self):
        before = snapshot(self.home, self.root)
        self.refused('stale-model', lambda: self.apply(current={**IDENTITY, 'model': 'other-model'}))
        self.assertEqual(snapshot(self.home, self.root), before)

    def test_unsafe_or_unknown_safety_refused(self):
        self.refused('unsafe-admission', lambda: self.apply(safety={**SAFE, 'unsafeAdmissions': 1}))
        self.refused('safety-unknown', lambda: self.apply(safety={**SAFE, 'effectViolations': None}))

    def test_descriptive_only_pair_refused_regression_not_covered(self):
        registration, evaluation = pair(self.sha)
        record = self.build(registration=registration, evaluation=evaluation)
        self.refused('regression-not-covered', lambda: self.apply(record))
        self.assertEqual(self.target.read_text(), BASE_TEXT)

    def test_stale_preview_refused_after_file_or_registry_change(self):
        doc = lp.preview_promote(self.build(), home=self.home, root=self.root)
        self.target.write_text(BASE_TEXT + 'edit\n')
        self.refused('preview-stale', lambda: self.apply(digest=doc['previewDigest']))
        self.target.write_text(BASE_TEXT)
        lp.registry_path(self.home, SCOPE).parent.mkdir(parents=True)
        hp.save(lp.registry_path(self.home, SCOPE), hp.ProfileRegistry.empty(SCOPE))
        self.refused('preview-stale', lambda: self.apply(digest=doc['previewDigest']))
        self.refused('preview-stale', lambda: self.apply(digest='0' * 64))

    def test_no_held_out_support_needs_override_reason_recorded_in_decision(self):
        registration, evaluation = pair(self.sha, base_verdict='meets')
        record = self.build(registration=registration, evaluation=noninferior(evaluation))
        self.refused('no-held-out-support', lambda: self.apply(record))
        self.apply(record, override_reason='drill only')
        decision = self.registry().decisions[self.registry().active]
        self.assertEqual(list(decision['limits']), [lp.baseline_limit(sha256_text(BASE_TEXT)),
                                                    'owner-override-no-held-out-support'])
        self.assertIn(sha256_text('drill only'), decision['evidenceSha256s'])
        self.assertNotIn(b'drill only', lp.registry_path(self.home, SCOPE).read_bytes())
        # OD-5: the reason text is kept in the run store beside its cited digest.
        self.assertEqual(self.run.candidate_text(sha256_text('drill only')), 'drill only')

    def test_failed_file_write_aborts_and_restores(self):
        real = os.replace

        def failing(src, dst):
            if str(dst) == str(self.target):
                raise OSError('disk full')
            return real(src, dst)
        with patch.object(os, 'replace', failing):
            self.refused('apply-failed', self.apply)
        self.assertEqual(self.target.read_text(), BASE_TEXT)
        value = self.registry()
        self.assertIsNone(value.active)
        self.assertIsNone(value.pending)
        self.assertEqual([e['event'] for e in value.journal], ['recorded', 'begun', 'aborted'])
        self.assertEqual(list(self.target.parent.glob('.SKILL.md.tmp-*')), [])

    def test_failed_commit_aborts_and_restores_file(self):
        with patch.object(hp.ProfileRegistry, 'commit', side_effect=hp.PromotionError('stale-host')):
            self.refused('apply-failed', self.apply)
        self.assertEqual(self.target.read_text(), BASE_TEXT)
        self.assertEqual(self.registry().journal[-1]['event'], 'aborted')

    def test_failed_restore_still_records_the_abort_and_reports_abort_failed(self):
        real = lp.write_target

        def failing(root, scope, raw):
            if raw != TEXT.encode():
                raise lp.PromoteError('target-write-failed')
            return real(root, scope, raw)
        with patch.object(hp.ProfileRegistry, 'commit', side_effect=hp.PromotionError('stale-host')), \
                patch.object(lp, 'write_target', failing):
            self.refused('abort-failed', self.apply)
        self.assertEqual(self.registry().journal[-1]['event'], 'aborted')
        self.assertEqual(self.target.read_text(), TEXT)  # left for the build check to flag

    def interrupted(self):
        """A promotion interrupted after begin was saved: pending entry, candidate text on disk."""
        with patch.object(hp.ProfileRegistry, 'commit', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.apply()
        self.assertIsNotNone(self.registry().pending)
        self.assertEqual(self.target.read_text(), TEXT)

    def test_interrupted_promotion_is_recovered_by_abort(self):
        self.interrupted()
        self.refused('transaction-in-progress', lambda: self.apply(at=11))
        before = snapshot(self.home, self.root)
        doc = lp.preview_abort(SCOPE, home=self.home, root=self.root, run=self.run, at=12)
        self.assertEqual(snapshot(self.home, self.root), before)
        self.assertEqual((doc['action'], doc['pendingSha256'], doc['candidateSha256']),
                         ('abort', self.sha, sha256_text(BASE_TEXT)))
        result = lp.apply_abort(SCOPE, home=self.home, root=self.root, run=self.run,
                                preview_digest=doc['previewDigest'], at=12)
        self.assertEqual(result['status'], 'aborted')
        self.assertEqual(self.target.read_text(), BASE_TEXT)
        value = self.registry()
        self.assertIsNone(value.pending)
        self.assertEqual(value.journal[-1]['event'], 'aborted')
        self.apply(at=13)  # a new promotion can start again
        self.assertEqual(self.target.read_text(), TEXT)

    def test_abort_needs_a_pending_entry_and_a_fresh_preview(self):
        self.refused('no-transaction', lambda: lp.preview_abort(SCOPE, home=self.home, root=self.root,
                                                                run=self.run, at=1))
        self.interrupted()
        doc = lp.preview_abort(SCOPE, home=self.home, root=self.root, run=self.run, at=12)
        self.target.write_text('edit\n')
        self.refused('preview-stale', lambda: lp.apply_abort(
            SCOPE, home=self.home, root=self.root, run=self.run, preview_digest=doc['previewDigest'], at=12))
        other = lp.preview_abort(SCOPE, home=self.home, root=self.root, run=self.run, reason='other', at=12)
        self.assertNotEqual(other['previewDigest'], lp.preview_abort(
            SCOPE, home=self.home, root=self.root, run=self.run, at=12)['previewDigest'])

    def test_abort_after_override_restores_the_baseline_not_the_reason(self):
        reason = low_reason()
        registration, evaluation = pair(self.sha, base_verdict='meets')
        record = self.build(registration=registration, evaluation=noninferior(evaluation))
        with patch.object(hp.ProfileRegistry, 'commit', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.apply(record, override_reason=reason)
        first = self.registry().decisions[self.registry().pending]
        self.assertEqual(sorted(first['evidenceSha256s'])[0], sha256_text(reason))
        doc = lp.preview_abort(SCOPE, home=self.home, root=self.root, run=self.run, at=12)
        self.assertEqual(doc['candidateSha256'], sha256_text(BASE_TEXT))
        lp.apply_abort(SCOPE, home=self.home, root=self.root, run=self.run,
                       preview_digest=doc['previewDigest'], at=12)
        self.assertEqual(self.target.read_text(), BASE_TEXT)

    def test_reapply_of_the_active_candidate_refused(self):
        self.apply()
        self.refused('already-active', lambda: self.apply(at=11))

    def test_cli_apply_with_digest_then_stale(self):
        cli = CliPreviewTests('test_cli_refusal_is_one_fixed_line')
        cli.tmp, cli.home, cli.root, cli.sha = self.tmp, self.home, self.root, self.sha
        cli.registration, cli.evaluation = self.registration, self.evaluation
        safety = Path(self.tmp.name) / 'safety.json'
        safety.write_text(json.dumps(SAFE))
        code, out, _ = cli.cli()
        digest = json.loads(out)['previewDigest']
        code, out, err = cli.cli('--apply', '--preview-digest', digest, '--actor', 'owner',
                                 '--safety', str(safety))
        self.assertEqual((code, err), (0, ''), err)
        self.assertEqual(json.loads(out)['status'], 'committed')
        self.assertEqual(self.target.read_text(), TEXT)
        code, _, err = cli.cli('--apply', '--preview-digest', digest, '--actor', 'owner',
                               '--safety', str(safety))
        self.assertEqual((code, err), (2, 'lightning promote refused (preview-stale)\n'))
        code, _, err = cli.cli('--apply', '--preview-digest', digest)
        self.assertEqual((code, err), (2, 'lightning promote refused (apply-needs-digest-actor-safety)\n'))

    def test_cli_os_error_is_one_fixed_line(self):
        cli = CliPreviewTests('test_cli_refusal_is_one_fixed_line')
        cli.tmp, cli.home, cli.root, cli.sha = self.tmp, self.home, self.root, self.sha
        cli.registration, cli.evaluation = self.registration, self.evaluation
        with patch.object(lp, 'preview_promote', side_effect=PermissionError('denied')):
            code, out, err = cli.cli()
        self.assertEqual((code, out, err), (2, '', 'lightning promote refused (io-error)\n'))


MODULE = ROOT / 'agent_braid' / 'lightning_promote.py'
FORBIDDEN_STDLIB = {'socket', 'subprocess', 'multiprocessing', 'asyncio', 'http', 'urllib', 'ssl',
                    'ftplib', 'smtplib', 'importlib', 'ctypes', 'shutil'}
FORBIDDEN_NAMES = {'system', 'popen', 'spawn', 'execv', 'execve', 'fork', '__import__', 'activate',
                   'import_module', 'execute', 'recover'}


def violations(source):
    """Boundary violations of a module's source: non-stdlib or forbidden imports and calls."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Import):
            roots = [a.name.split('.')[0] for a in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            roots = [node.module.split('.')[0]]
        else:
            roots = []
        for root in roots:
            if root not in sys.stdlib_module_names or root in FORBIDDEN_STDLIB:
                found.append(('import', root))
        if isinstance(node, ast.ImportFrom) and node.level == 1 and node.module is None:
            found += [('local', a.name) for a in node.names if 'mcp' in a.name]
        name = node.attr if isinstance(node, ast.Attribute) else node.id if isinstance(node, ast.Name) else None
        if name in FORBIDDEN_NAMES:
            found.append(('name', name))
    return found


class BoundaryTests(Base):
    """procedure_008 / SC-008: no socket, no process, standard library only, bounded writes.

    The AST check is module-local: it covers ``lightning_promote.py`` itself. Importing it
    still loads Agent Braid modules (for example ``harness_promotion`` -> ``harness_lab``)
    that import ``subprocess``; the runtime test shows the promotion paths never call it.
    """

    def test_module_source_has_no_forbidden_import_or_call(self):
        self.assertEqual(violations(MODULE.read_text()), [])

    def test_negative_control_detects_a_patched_module(self):
        source = MODULE.read_text()
        for patch_line, kind in (('import socket\n', 'socket'), ('import requests\n', 'requests'),
                                 ('from subprocess import run\n', 'subprocess')):
            self.assertIn(('import', kind), violations(patch_line + source))
        self.assertIn(('name', 'system'), violations(source + '\nos.system("x")\n'))
        self.assertIn(('name', 'activate'), violations(source + '\nstore.activate(1)\n'))

    def test_no_mcp_tool_exposes_promotion(self):
        for path in (ROOT / 'agent_braid').glob('*mcp*.py'):
            self.assertNotIn('lightning_promote', path.read_text(), path.name)
        self.assertNotIn('promote', (ROOT / 'agent_braid' / 'plugin_mcp.py').read_text())

    def test_automatic_promotion_stays_disabled(self):
        from agent_braid import harness_promotion
        self.assertIs(harness_promotion.AUTOMATIC_PROMOTION, False)

    def test_preview_opens_no_socket_or_process_and_writes_nothing(self):
        def refuse(*args, **kwargs):
            raise AssertionError('boundary crossed')
        before = snapshot(self.home, self.root)
        writes = []
        real_open = os.open

        def watch(path, flags, *args, **kwargs):
            if flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT):
                writes.append(str(path))
            return real_open(path, flags, *args, **kwargs)
        with patch.object(socket, 'socket', refuse), patch.object(subprocess, 'Popen', refuse), \
                patch.object(os, 'system', refuse), patch.object(os, 'open', watch):
            lp.preview_promote(self.build(), home=self.home, root=self.root)
        self.assertEqual(writes, [])
        self.assertEqual(snapshot(self.home, self.root), before)


if __name__ == '__main__':
    unittest.main()
