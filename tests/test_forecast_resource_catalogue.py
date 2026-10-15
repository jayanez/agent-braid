# SPDX-License-Identifier: AGPL-3.0-only
import unittest
from copy import deepcopy

from agent_braid.forecast_data import ForecastError, digest
from agent_braid.forecast_resources import ResourceCatalogue, validate_resource
from tests.forecast_resource_helpers import catalogue, rebind


class ResourceCatalogueTests(unittest.TestCase):
    def registry(self, raw=None, **overrides):
        raw = catalogue() if raw is None else raw
        config = dict(expected_digest=digest(raw), host_id='synthetic-local', clock_id='synthetic-clock-epoch',
                      runtime_revision='1' * 64, inventory_revision='2' * 64,
                      isolation_revision='3' * 64)
        config.update(overrides)
        return ResourceCatalogue(raw, **config)

    def resolve(self, registry, **overrides):
        request = dict(now_ns=150, mode='parallel', workers=2, operations=2,
                       patch_bytes=1024, scratch_bytes=4096)
        request.update(overrides)
        return registry.resolve('synthetic-preparation', **request)

    def test_registered_synthetic_profile_is_bound_copied_and_never_authority(self):
        raw = catalogue(); registry = self.registry(raw)
        receipt = self.resolve(registry)
        self.assertEqual('synthetic', receipt['sourceKind'])
        self.assertEqual(digest(raw), receipt['catalogueDigest'])
        self.assertEqual(digest(raw['profiles'][0]), receipt['profileDigest'])
        self.assertEqual(digest(raw['profiles'][0]['resource']), receipt['resourceDigest'])
        self.assertFalse(receipt['executionAuthorization'])
        self.assertFalse(receipt['metadata']['isolation']['hardMemoryLimitSupported'])
        raw['profiles'][0]['resource']['caps']['operations'] = 2
        receipt['resource']['caps']['operations'] = 2
        self.assertEqual(4, self.resolve(registry)['resource']['caps']['operations'])

    def test_unknown_stale_future_modes_and_each_budget_refuse(self):
        registry = self.registry()
        with self.assertRaisesRegex(ForecastError, 'unknown-resource'):
            registry.resolve('unknown', now_ns=150, mode='serial', workers=1,
                             operations=2, patch_bytes=1, scratch_bytes=1)
        for change in (dict(now_ns=99), dict(now_ns=200), dict(mode='remote'),
                       dict(workers=5), dict(workers=True), dict(workers=3, operations=2),
                       dict(operations=5), dict(patch_bytes=262145),
                       dict(scratch_bytes=67108865), dict(mode='serial', workers=2)):
            with self.subTest(change=change), self.assertRaises(ForecastError):
                self.resolve(registry, **change)
        self.assertEqual('serial', self.resolve(registry, mode='serial', workers=1)['mode'])

    def test_configured_pin_host_and_all_revisions_cannot_be_self_asserted(self):
        raw = catalogue()
        changed = deepcopy(raw); changed['profiles'][0]['resource']['caps']['patchBytes'] = 100
        rebind(changed['profiles'][0])
        with self.assertRaisesRegex(ForecastError, 'catalogue-not-allowlisted'):
            self.registry(changed, expected_digest=digest(raw))
        for config in (dict(host_id='another-local'), dict(clock_id='another-clock-epoch'), dict(runtime_revision='5' * 64),
                       dict(isolation_revision='6' * 64), dict(inventory_revision='7' * 64)):
            with self.subTest(config=config), self.assertRaises(ForecastError):
                self.resolve(self.registry(**config))

    def test_missing_isolation_receipt_and_forged_metadata_are_rejected(self):
        for mutate in (lambda m: m['isolation'].pop('receiptDigest'),
                       lambda m: m['isolation'].pop('hardCpuLimitSupported'),
                       lambda m: m['isolation'].update(ownedScratch=False),
                       lambda m: m['isolation'].update(independentGrants=False),
                       lambda m: m['platform'].update(memoryBytes=True)):
            raw = catalogue(); mutate(raw['profiles'][0]['metadata'])
            rebind(raw['profiles'][0])
            with self.subTest(raw=raw), self.assertRaises(ForecastError):
                self.resolve(self.registry(raw))
        raw = catalogue(); raw['profiles'][0]['metadata']['runtimeRevision'] = '5' * 64
        with self.assertRaisesRegex(ForecastError, 'resource-metadata-drift'):
            self.registry(raw)

    def test_availability_receipt_cannot_change_identity_clock_or_observations(self):
        for key, value in [('hostId', 'other-local'), ('profileId', 'other-profile'),
                           ('sourceKind', 'permissioned'), ('expiresNs', 201),
                           ('observedNs', True), ('clockId', True), ('timeUnit', 'seconds'),
                           ('inventoryRevision', '8' * 64),
                           ('observationsDigest', '9' * 64)]:
            raw = catalogue(); profile = raw['profiles'][0]
            profile['metadata']['availabilityReceipt'][key] = value
            profile['resource']['profileRevision'] = digest(profile['metadata'])
            with self.subTest(field=key), self.assertRaises(ForecastError):
                self.registry(raw)

    def test_new_reviewed_inventory_is_a_new_resource_receipt_and_old_context_refuses(self):
        raw = catalogue(); old = self.resolve(self.registry(raw))
        raw['profiles'][0]['metadata']['inventoryRevision'] = '5' * 64
        rebind(raw['profiles'][0])
        with self.assertRaisesRegex(ForecastError, 'resource-inventory-drift'):
            self.resolve(self.registry(raw))
        new = self.resolve(self.registry(raw, inventory_revision='5' * 64))
        self.assertNotEqual(old['resourceDigest'], new['resourceDigest'])
        self.assertNotEqual(old['profileDigest'], new['profileDigest'])

    def test_unsupported_configured_enforcement_refuses_without_invented_caps(self):
        registry = self.registry(required_controls=('hardMemoryLimitSupported',))
        with self.assertRaisesRegex(ForecastError, 'resource-enforcement-unavailable'):
            self.resolve(registry)

    def test_empty_actual_catalogue_does_not_admit_any_host(self):
        raw = catalogue(); raw.update(sourceKind='permissioned', profiles=[])
        registry = self.registry(raw, authority_verifier=lambda p: True)
        with self.assertRaisesRegex(ForecastError, 'unknown-resource'):
            self.resolve(registry)

    def test_catalogue_shape_and_contract_do_not_widen_the_existing_runtime(self):
        changes = [lambda c: c.update(version='latest'),
                   lambda c: c.update(executionAuthorization=True),
                   lambda c: c.update(sourceKind='remote'),
                   lambda c: c['profiles'].append(deepcopy(c['profiles'][0])),
                   lambda c: c['profiles'][0]['resource'].update(executionContract='remote-dispatch-v1'),
                   lambda c: c['profiles'][0]['metadata']['isolation'].update(scope='distributed'),
                   lambda c: c['profiles'][0]['resource'].update(allowedModes=[{}])]
        for mutate in changes:
            raw = catalogue(); mutate(raw)
            for profile in raw['profiles']: rebind(profile)
            with self.subTest(raw=raw), self.assertRaises(ForecastError):
                self.registry(raw)

    def test_permissioned_requires_external_review_on_every_use_and_passes_a_copy(self):
        # Injected test verifier proves the protocol, not real-resource admission.
        raw = catalogue(); raw['sourceKind'] = 'permissioned'
        raw['profiles'][0]['resource']['sourceKind'] = 'permissioned'
        raw['profiles'][0]['resource']['allowedModes'] = ['serial']
        raw['profiles'][0]['resource']['maxWorkers'] = 1
        rebind(raw['profiles'][0]); calls = []; allowed = [True]
        def verifier(profile):
            calls.append(deepcopy(profile)); profile['resource']['caps']['operations'] = 99
            return allowed[0]
        with self.assertRaisesRegex(ForecastError, 'resource-not-admitted'):
            self.resolve(self.registry(raw), mode='serial', workers=1)
        registry = self.registry(raw, authority_verifier=verifier)
        self.assertEqual(4, self.resolve(registry, mode='serial', workers=1)['resource']['caps']['operations'])
        self.assertEqual(4, self.resolve(registry, mode='serial', workers=1)['resource']['caps']['operations'])
        allowed[0] = False
        with self.assertRaisesRegex(ForecastError, 'resource-not-admitted'):
            self.resolve(registry, mode='serial', workers=1)
        self.assertEqual(3, len(calls))
        self.assertTrue(all(p == raw['profiles'][0] for p in calls))

    def test_legacy_permissioned_record_cannot_bypass_missing_metadata(self):
        from tests.test_forecast_resources import resource
        raw = resource(); raw['sourceKind'] = 'permissioned'
        with self.assertRaisesRegex(ForecastError, 'resource-profile-metadata-required'):
            validate_resource(raw, expected_digest=digest(raw), now_ns=150,
                              authority_verifier=lambda p: True)

    def test_v2_permissioned_callback_cannot_substitute_for_pinned_full_profile(self):
        raw = catalogue()['profiles'][0]['resource']; raw['sourceKind'] = 'permissioned'
        raw['profileRevision'] = '9' * 64
        with self.assertRaisesRegex(ForecastError, 'resource-not-admitted'):
            validate_resource(raw, expected_digest=digest(raw), now_ns=150,
                              authority_verifier=lambda p: True)
        class FakeCatalogue(ResourceCatalogue):
            def __init__(self): pass
            def _admit(self, resource): pass
        with self.assertRaisesRegex(ForecastError, 'resource-not-admitted'):
            validate_resource(raw, expected_digest=digest(raw), now_ns=150,
                              authority_verifier=FakeCatalogue())

    def test_permissioned_parallel_cannot_remove_minimum_enforcement(self):
        raw = catalogue(); raw['sourceKind'] = 'permissioned'
        raw['profiles'][0]['resource']['sourceKind'] = 'permissioned'; rebind(raw['profiles'][0])
        calls = []
        registry = self.registry(raw, required_controls=(), authority_verifier=lambda p: calls.append(p) or True)
        for mode, workers in [('parallel', 2), ('serial', 1)]:
            with self.subTest(mode=mode), self.assertRaisesRegex(ForecastError, 'resource-enforcement-unavailable'):
                self.resolve(registry, mode=mode, workers=workers)
        self.assertFalse(calls)

    def test_permissioned_public_validation_uses_exact_catalogue_and_sanitizes_errors(self):
        raw = catalogue(); raw['sourceKind'] = 'permissioned'
        r = raw['profiles'][0]['resource']; r.update(sourceKind='permissioned', allowedModes=['serial'], maxWorkers=1)
        rebind(raw['profiles'][0]); calls = []
        registry = self.registry(raw, authority_verifier=lambda p: calls.append(p) or True)
        validated = validate_resource(r, expected_digest=digest(r), now_ns=150, authority_verifier=registry)
        self.assertEqual(r, validated); self.assertEqual([raw['profiles'][0]], calls)
        changed = deepcopy(r); changed['caps']['operations'] = 3
        with self.assertRaisesRegex(ForecastError, 'resource-not-allowlisted'):
            validate_resource(changed, expected_digest=digest(changed), now_ns=150, authority_verifier=registry)
        self.assertEqual(1, len(calls))
        def failed(profile): raise RuntimeError('private-control-error')
        registry = self.registry(raw, authority_verifier=failed)
        with self.assertRaisesRegex(ForecastError, '^resource-not-admitted$'):
            validate_resource(r, expected_digest=digest(r), now_ns=150, authority_verifier=registry)

    def test_synthetic_profile_flows_to_forecast_advice_and_cannot_dispatch(self):
        from agent_braid.forecast_advice import ForecastSession
        from agent_braid.forecast_policy import advise, verify_consumption
        from tests.test_forecast_policy import request
        receipt = self.resolve(self.registry()); policy = request()
        policy['resource'] = receipt['resource']; policy['resourceDigest'] = receipt['resourceDigest']
        policy['window']['resourceReceiptDigest'] = receipt['resourceDigest']
        with_session = dict(version='agent-braid-forecast-request-v1', backend='persistence',
                            window=policy['window'], horizon=1, alpha=.3)
        session = ForecastSession(); self.addCleanup(session.close)
        policy['forecast'] = session.predict(with_session)
        cached = session.predict(with_session)
        self.assertTrue(session.last_cache_receipt['cacheHit'])
        self.assertEqual(receipt['resourceDigest'], cached['resourceReceiptDigest'])
        advice = advise(policy)
        self.assertEqual('serial', advice['selectedAction'])
        self.assertFalse(advice['executionAuthorization'])
        with self.assertRaisesRegex(ForecastError, 'synthetic-advice-cannot-dispatch'):
            verify_consumption(advice, policy, plan_digest='d' * 64, now_ns=150)
