# SPDX-License-Identifier: AGPL-3.0-only
"""Closed second-layer history reconciliation, using disposable Git fixtures."""
from copy import deepcopy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from scripts import history_equivalence as history


class RewrittenHistoryContractTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='braid-history-correction-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.git('init', '-b', 'main')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.root/'value').write_text('base\n')
        self.git('add', 'value'); self.git('commit', '-m', 'root')
        self.base = self.git('rev-parse', 'HEAD')
        self.git('switch', '-c', 'candidate')
        (self.root/'value').write_text('candidate\n')
        self.git('commit', '-am', 'candidate')
        self.candidate = self.git('rev-parse', 'HEAD')
        self.tree = self.git('rev-parse', 'HEAD^{tree}')
        self.git('tag', '-a', 'reviewed', '-m', 'Exact retained object')
        self.oid = self.git('rev-parse', 'refs/tags/reviewed')
        self.git('switch', 'main')
        self.git('branch', '-D', 'candidate')
        self.original, self.intermediate = '1'*40, '2'*40
        self.old_oid = '4'*40
        legacy_tag = dict(oldName='original', newName='reviewed', oldCommit=self.original,
                          newCommit=self.intermediate, oldTagObject='3'*40,
                          newTagObject=self.old_oid, tree=self.tree)
        corrected_tag = dict(oldName='reviewed', newName='reviewed', oldCommit=self.intermediate,
                             newCommit=self.candidate, oldTagObject=self.old_oid,
                             newTagObject=self.oid, tree=self.tree)
        self.legacy = dict(recordVersion='0.1.0', adr='docs/adr/0022-attribution-correction-history-equivalence.md',
                           reason='fixture original mapping', limits=['No new approval'],
                           entries=[dict(old=self.original, new=self.intermediate, tree=self.tree)], tags=[legacy_tag])
        self.correction = dict(recordVersion='0.1.0', adr='docs/adr/0023-second-history-correction-equivalence.md',
                               reason='fixture second mapping', limits=['No new approval'],
                               entries=[dict(old=self.intermediate, new=self.candidate, tree=self.tree)], tags=[corrected_tag])

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args],
                                        text=True, stderr=subprocess.PIPE).strip()

    def publish(self):
        for relative, data in ((history.EQUIVALENCE, self.legacy), (history.CORRECTION, self.correction)):
            path = self.root/relative; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(history._canonical(data))
        self.git('add', 'docs'); self.git('commit', '-m', 'Introduce exact fixture mappings')

    def test_composes_both_layers_without_original_objects_or_approval_changes(self):
        self.publish()
        before = (self.root/history.EQUIVALENCE).read_bytes()
        self.assertEqual(self.candidate, history.resolve_public_commit(self.root, self.original, self.tree))
        self.assertEqual(self.candidate, history.resolve_public_commit(self.root, self.intermediate))
        self.assertEqual((self.candidate, self.oid), history.retained_tag_binding(
            self.root, 'refs/tags/reviewed', self.intermediate, self.old_oid))
        self.assertEqual('f'*40, history.recorded_equivalent(self.root, 'f'*40))
        self.assertEqual(before, (self.root/history.EQUIVALENCE).read_bytes())

    def test_deleted_or_modified_second_record_fails_after_introduction(self):
        self.publish(); path = self.root/history.CORRECTION; original = path.read_bytes()
        path.unlink()
        with self.assertRaisesRegex(ValueError, 'missing after introduction'):
            history.load_equivalence(self.root)
        for payload in (original+b'\n', history._canonical({**self.correction, 'reason': 'changed'})):
            path.write_bytes(payload)
            with self.subTest(payload=payload[-25:]), self.assertRaises(ValueError):
                history.load_equivalence(self.root)

    def test_duplicate_old_tag_name_is_rejected_even_in_first_published_record(self):
        self.correction['tags'].append({**self.correction['tags'][0], 'newName': 'zz-review'})
        self.publish()
        with self.assertRaisesRegex(ValueError, 'unique and sorted'):
            history.load_equivalence(self.root)

    def test_cross_layer_cycle_is_rejected(self):
        self.correction['entries'][0]['new'] = self.original
        self.correction['tags'][0]['newCommit'] = self.original
        self.publish()
        with self.assertRaisesRegex(ValueError, 'cross-layer cycle'):
            history.load_equivalence(self.root)

    def test_cross_layer_tag_name_collision_is_rejected(self):
        self.correction['tags'][0]['oldName'] = 'other'
        self.publish()
        with self.assertRaisesRegex(ValueError, 'collides'):
            history.load_equivalence(self.root)

    def test_exact_old_candidate_and_object_are_required_without_changing_refs(self):
        self.publish(); before = self.git('show-ref')
        for candidate, oid in ((self.base, self.old_oid), (self.intermediate, '0'*40)):
            with self.subTest(candidate=candidate, oid=oid), self.assertRaisesRegex(ValueError, 'retained tag pin'):
                history.retained_tag_binding(self.root, 'refs/tags/reviewed', candidate, oid)
        self.assertEqual(before, self.git('show-ref'))

    def test_missing_lightweight_or_recreated_tag_cannot_resolve_tag_only_target(self):
        self.publish()
        for variant in ('missing', 'lightweight', 'recreated'):
            self.git('update-ref', '-d', 'refs/tags/reviewed')
            if variant == 'lightweight': self.git('update-ref', 'refs/tags/reviewed', self.candidate)
            elif variant == 'recreated': self.git('tag', '-a', 'reviewed', self.candidate, '-m', 'Counterfeit')
            with self.subTest(variant=variant), self.assertRaisesRegex(ValueError, 'not in public ancestry'):
                history.resolve_public_commit(self.root, self.original)
            self.git('update-ref', 'refs/tags/reviewed', self.oid)

    def test_tree_disagreement_and_replacements_fail_closed(self):
        self.publish()
        with self.assertRaisesRegex(ValueError, 'tree does not match'):
            history.resolve_public_commit(self.root, self.original, '0'*40)
        data = history.load_equivalence(self.root)
        altered = deepcopy(data); altered['entries'][self.original]['tree'] = '0'*40
        with patch.object(history, 'load_equivalence', return_value=altered):
            with self.assertRaisesRegex(ValueError, 'tree does not match'):
                history.resolve_public_commit(self.root, self.original)
        self.git('replace', self.candidate, self.base)
        self.assertEqual(self.candidate, history.resolve_public_commit(self.root, self.original, self.tree))

    def test_composition_cannot_change_an_original_recorded_tree(self):
        self.correction['entries'][0]['tree'] = '0'*40
        self.correction['tags'][0]['tree'] = '0'*40
        self.publish()
        with self.assertRaisesRegex(ValueError, 'changed a recorded tree'):
            history.load_equivalence(self.root)

    def test_composition_cannot_replace_original_mapping_key(self):
        self.correction['entries'][0]['old'] = self.original
        self.correction['tags'][0]['oldCommit'] = self.original
        self.publish()
        with self.assertRaisesRegex(ValueError, 'replace original mapping keys'):
            history.load_equivalence(self.root)

    def test_unknown_intermediate_target_remains_unavailable(self):
        self.legacy['entries'].append(dict(old='5'*40, new='6'*40, tree=self.tree))
        self.publish()
        self.assertEqual('6'*40, history.recorded_equivalent(self.root, '5'*40))
        with self.assertRaisesRegex(ValueError, 'tree does not match'):
            history.resolve_public_commit(self.root, '5'*40)
