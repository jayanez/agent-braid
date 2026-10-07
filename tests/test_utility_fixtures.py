# SPDX-License-Identifier: AGPL-3.0-only
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from agent_braid.utility_fixtures import (
    InvalidUtilityFixture, PREPARED_MANIFEST_SHA256, build_fixture,
    validate_prepared_manifest,
)

MANIFEST = Path(__file__).resolve().parents[1] / 'specs/022-m4-utility-followup/evidence/prepared-fixture-manifest.json'


class UtilityFixtureTests(unittest.TestCase):
    def setUp(self):
        self.raw = MANIFEST.read_bytes()
        self.manifest = validate_prepared_manifest(self.raw)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def test_archived_manifest_has_exact_fixed_inventory_and_exclusions(self):
        self.assertEqual(hashlib.sha256(self.raw).hexdigest(), PREPARED_MANIFEST_SHA256)
        self.assertEqual([b['blockId'] for b in self.manifest['blocks']], [
            'independent-2-1024', 'independent-2-65536', 'independent-2-1048576',
            'independent-4-1024', 'independent-4-65536', 'independent-4-1048576',
            'dependency-chain-4-1024', 'dependency-chain-4-65536', 'dependency-chain-4-1048576'])
        self.assertEqual([b['blockId'] for b in self.manifest['blocks'] if b['directNumericExclusions']], [
            'independent-2-1048576', 'independent-4-65536', 'independent-4-1048576',
            'dependency-chain-4-65536', 'dependency-chain-4-1048576'])

    def test_manifest_drift_inventory_order_and_exclusions_fail(self):
        mutations = []
        order = deepcopy(self.manifest)
        order['blocks'][0], order['blocks'][1] = order['blocks'][1], order['blocks'][0]
        mutations.append(order)
        omission = deepcopy(self.manifest)
        omission['blocks'].pop()
        mutations.append(omission)
        exclusion = deepcopy(self.manifest)
        exclusion['blocks'][2]['directNumericExclusions'] = []
        mutations.append(exclusion)
        for mutation in mutations:
            with self.subTest(mutation=mutation['blocks'][0]['blockId']):
                with self.assertRaisesRegex(InvalidUtilityFixture, 'manifest hash mismatch'):
                    validate_prepared_manifest(json.dumps(mutation).encode())
        with self.assertRaises(InvalidUtilityFixture):
            validate_prepared_manifest(self.raw.decode())

    def _reconstruct(self, index):
        block = self.manifest['blocks'][index]
        result = build_fixture(block, self.root / block['blockId'])
        self.assertEqual(result['identities'], block['operationIdentities'])
        self.assertEqual(result['expectedFinalTree'], block['expectedFinalTree'])
        self.assertEqual(result['runtimeRequest']['baseRevision'], block['baseCommit'])
        self.assertEqual(result['runtimeRequest']['order'], block['plannedOrder'])
        for identity in result['identities']:
            patch = (self.root / block['blockId'] / identity['patchFile']).read_bytes()
            self.assertEqual('sha256:' + hashlib.sha256(patch).hexdigest(), identity['patchSha256'])
            self.assertEqual(len(patch), identity['patchBytes'])
        for label in ['runtimeRequest', 'replayRequest']:
            raw = Path(result[label + 'Path']).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), result[label + 'Sha256'])
            self.assertEqual(json.loads(raw), result[label])
        # Independent Git observation, without any runtime/replay/admission call.
        process = subprocess.run(['git', '-C', result['repository'], 'rev-parse',
                                  result['expectedFinalTree'] + '^{tree}'],
                                 capture_output=True, timeout=30, check=True)
        self.assertEqual(process.stdout.decode().strip(), block['expectedFinalTree'])
        repository = Path(result['repository'])
        self.assertTrue((repository / '.git').is_dir())
        observed_head = subprocess.run(['git', '-C', str(repository), 'rev-parse', 'HEAD'],
                                       capture_output=True, timeout=30, check=True)
        self.assertEqual(observed_head.stdout.decode().strip(), block['baseCommit'])
        observed_bare = subprocess.run(['git', '-C', str(repository), 'rev-parse',
                                       '--is-bare-repository'], capture_output=True,
                                      timeout=30, check=True)
        self.assertEqual(observed_bare.stdout, b'false\n')
        self.assertEqual(sorted(p.name for p in repository.glob('*.txt')),
                         [i + '.txt' for i in block['plannedOrder']])
        for identifier in block['plannedOrder']:
            self.assertEqual((repository / (identifier + '.txt')).read_bytes(), b'base\n')
        return result

    def test_independent_two_fixture_reconstructs_exact_objects_and_patches(self):
        result = self._reconstruct(0)
        self.assertEqual([o['dependencies'] for o in result['runtimeRequest']['operations']], [[], []])
        self.assertEqual(result['directNumericExclusions'], [])

    def test_chain_fixture_reconstructs_exact_order_control(self):
        result = self._reconstruct(6)
        self.assertEqual([o['dependencies'] for o in result['runtimeRequest']['operations']],
                         [[], ['a'], ['b'], ['c']])
        self.assertEqual({i['parentCommit'] for i in result['identities']},
                         {result['runtimeRequest']['baseRevision']})
        self.assertTrue(all('declaredWrites' not in o for o in result['replayRequest']['operations']))

    def test_block_identity_and_scalar_tamper_fail_before_destination_creation(self):
        for field, value in [('payloadBytesPerOperation', True), ('operationCount', 2.0),
                             ('aggregatePatchBytes', '2284'), ('baseCommit', '0' * 40)]:
            block = deepcopy(self.manifest['blocks'][0])
            block[field] = value
            dest = self.root / field
            with self.subTest(field=field), self.assertRaisesRegex(InvalidUtilityFixture, 'identity hash mismatch'):
                build_fixture(block, dest)
            self.assertFalse(dest.exists())

    def test_existing_destination_and_symlink_are_never_overwritten(self):
        destination = self.root / 'existing'
        destination.mkdir()
        sentinel = destination / 'owned.txt'
        sentinel.write_bytes(b'preserve')
        with self.assertRaisesRegex(InvalidUtilityFixture, 'already exists'):
            build_fixture(self.manifest['blocks'][0], destination)
        self.assertEqual(list(destination.iterdir()), [sentinel])
        self.assertEqual(sentinel.read_bytes(), b'preserve')
        link = self.root / 'link'
        link.symlink_to(self.root / 'absent')
        with self.assertRaisesRegex(InvalidUtilityFixture, 'already exists'):
            build_fixture(self.manifest['blocks'][0], link)
        self.assertTrue(link.is_symlink())
        self.assertFalse((self.root / 'absent').exists())

    def test_source_checkout_and_bare_ancestor_reject_without_mutation(self):
        source = self.root / 'source'
        source.mkdir()
        (source / '.git').write_text('gitdir: private')
        with self.assertRaisesRegex(InvalidUtilityFixture, 'source Git storage'):
            build_fixture(self.manifest['blocks'][0], source / 'new')
        self.assertEqual((source / '.git').read_text(), 'gitdir: private')
        self.assertFalse((source / 'new').exists())
        bare = self.root / 'bare'
        bare.mkdir()
        (bare / 'HEAD').write_text('ref: refs/heads/base\n')
        (bare / 'objects').mkdir()
        (bare / 'refs').mkdir()
        with self.assertRaisesRegex(InvalidUtilityFixture, 'source Git storage'):
            build_fixture(self.manifest['blocks'][0], bare / 'new')
        self.assertFalse((bare / 'new').exists())


if __name__ == '__main__':
    unittest.main()
