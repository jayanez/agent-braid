# SPDX-License-Identifier: AGPL-3.0-only
"""Direct cache conformance with synthetic windows and a numerical stub only."""
import threading
import unittest
from copy import deepcopy
from unittest.mock import patch

from agent_braid.forecast_advice import ForecastSession
from agent_braid.forecast_baselines import predict_baseline
from agent_braid.forecast_cache import ForecastCache
from agent_braid.forecast_data import ForecastError, digest
from agent_braid.forecast_outputs import envelope, validate_forecast
from tests.forecast_helpers import window
from tests.forecast_resource_helpers import catalogue, rebind
from tests.test_forecast_worker import manifest, TestControlVerifier


class CacheConformanceTests(unittest.TestCase):
    def session(self):
        session = ForecastSession(manifest(), artifact_verifier=TestControlVerifier())
        self.addCleanup(session.close)
        class SyntheticWorker:
            loaded = True
            def __init__(self):
                self.calls = 0
                self.after_result = lambda: None
            def forecast(self, w, h, **kwargs):
                self.calls += 1
                quantiles = predict_baseline(w, h)['quantiles']
                result = envelope(w, h, model_digest=digest(session.adapter.manifest),
                                  quantiles=quantiles)
                self.after_result()
                return result
            def close(self):
                self.loaded = False
        worker = SyntheticWorker(); session.adapter.worker = worker
        request = dict(version='agent-braid-forecast-request-v1', backend='chronos2',
                       window=window(), horizon=1, alpha=.3)
        request['window']['resourceReceiptDigest'] = digest(catalogue()['profiles'][0]['resource'])
        return session, worker, request

    def test_each_causal_identity_misses_and_cached_uncached_numerics_match(self):
        def mask(r):
            w = r['window']; w['values'][0][0] = None; w['observedMask'][0][0] = False
            w['availableAtNs'][0][0] = None; w['missingReasons'][0][0] = 'synthetic-missing'
        def resource_revision(r):
            profile = catalogue()['profiles'][0]
            profile['metadata']['inventoryRevision'] = '9' * 64; rebind(profile)
            r['window']['resourceReceiptDigest'] = digest(profile['resource'])
        def capability_revision(r):
            profile = catalogue()['profiles'][0]
            profile['metadata']['isolation']['revision'] = '8' * 64
            profile['metadata']['runtimeRevision'] = '7' * 64
            rebind(profile)
            r['window']['resourceReceiptDigest'] = digest(profile['resource'])
        changes = {
            'cutoff': lambda r: r['window'].update(cutoffNs=400000000),
            'mask': mask,
            'resource-inventory': resource_revision,
            'resource-capability-runtime-isolation': capability_revision,
            'preprocessing': lambda r: r['window'].update(transformDigest='d' * 64),
            'partition': lambda r: r['window'].update(partitionDigest='e' * 64),
            'horizon': lambda r: r.update(horizon=5),
            'values': lambda r: r['window']['values'][0].__setitem__(-1, 8),
            'alpha': lambda r: r.update(alpha=.5),
        }
        for name, change in changes.items():
            with self.subTest(identity=name):
                session, worker, request = self.session()
                first = session.predict(request); first_key = session.last_cache_receipt['key']
                changed = deepcopy(request); change(changed)
                uncached = session.predict(changed)
                self.assertEqual(2, worker.calls)
                self.assertFalse(session.last_cache_receipt['cacheHit'])
                self.assertNotEqual(first_key, session.last_cache_receipt['key'])
                cached = session.predict(changed)
                self.assertEqual(2, worker.calls)
                self.assertTrue(session.last_cache_receipt['cacheHit'])
                self.assertEqual(uncached['packetDigest'], session.last_cache_receipt['originalForecastDigest'])
                validate_forecast(cached, changed['window'], changed['horizon'])
                for field in ('quantiles', 'median', 'modelDigest', 'inputDigest', 'futureTimesNs'):
                    self.assertEqual(uncached[field], cached[field])
                self.assertFalse(cached['executionAuthorization'])
                self.assertEqual('forecast', first['status'])

    def test_changed_artifact_or_backend_cannot_reuse_another_prediction(self):
        session, worker, request = self.session()
        original = session.predict(request); key = session.last_cache_receipt['key']
        session.adapter.manifest['imageId'] = 'sha256:' + 'f' * 64
        changed = session.predict(request)
        self.assertEqual(2, worker.calls)
        self.assertFalse(session.last_cache_receipt['cacheHit'])
        self.assertNotEqual(key, session.last_cache_receipt['key'])
        self.assertNotEqual(original['modelDigest'], changed['modelDigest'])
        session.predict(request); self.assertTrue(session.last_cache_receipt['cacheHit'])
        request['backend'] = 'persistence'
        session.predict(request); self.assertFalse(session.last_cache_receipt['cacheHit'])
        self.assertEqual(2, worker.calls)

    def test_hit_emits_current_cost_rather_than_original_inference_cost(self):
        session, worker, request = self.session()
        first = session.predict(request)
        with patch('agent_braid.forecast_advice.time.monotonic_ns', side_effect=[100, 500]), \
             patch('agent_braid.forecast_advice.time.monotonic', return_value=0), \
             patch('agent_braid.forecast_outputs.monotonic_ns', return_value=350):
            cached = session.predict(request)
        self.assertEqual(1, worker.calls)
        self.assertEqual(250, cached['costs']['wallNs'])
        self.assertEqual(400, session.last_cache_receipt['wallNs'])
        self.assertEqual(first['packetDigest'], session.last_cache_receipt['originalForecastDigest'])
        self.assertEqual(cached['packetDigest'], session.last_cache_receipt['currentForecastDigest'])
        self.assertIsNone(cached['costs']['modelCpuNs'])
        self.assertEqual('not-observed', cached['costs']['modelCpuReason'])

    def test_cancellation_during_cache_read_never_delivers_the_hit(self):
        session, worker, request = self.session(); session.predict(request); session.predict(request)
        self.assertTrue(session.last_cache_receipt['cacheHit'])
        cancellation = threading.Event(); get = session.cache.get
        def cancel_read(key):
            value = get(key); cancellation.set(); return value
        with patch.object(session.cache, 'get', side_effect=cancel_read):
            result = session.predict(request, cancellation=cancellation)
        self.assertEqual('cancelled', result['status'])
        self.assertIsNone(result['quantiles'])
        self.assertIsNone(session.last_cache_receipt)
        self.assertEqual(1, worker.calls)

    def test_cancellation_during_cache_read_precedes_consuming_its_payload(self):
        session, worker, request = self.session(); session.predict(request)
        cancellation = threading.Event()
        def cancelled_payload(key):
            cancellation.set()
            return {'status': 'must-not-consume-cancelled-payload'}
        with patch.object(session.cache, 'get', side_effect=cancelled_payload):
            result = session.predict(request, cancellation=cancellation)
        self.assertEqual('cancelled', result['status'])
        self.assertIsNone(session.last_cache_receipt)
        self.assertEqual(1, worker.calls)

    def test_cancellation_after_backend_does_not_commit_an_incomplete_result(self):
        session, worker, request = self.session(); cancellation = threading.Event()
        worker.after_result = cancellation.set
        with patch.object(session.cache, 'put', wraps=session.cache.put) as put:
            result = session.predict(request, cancellation=cancellation)
        put.assert_not_called()
        self.assertEqual('cancelled', result['status'])
        self.assertFalse(session.cache.records)
        self.assertIsNone(session.last_cache_receipt)
        cancellation.clear(); worker.after_result = lambda: None
        self.assertEqual('forecast', session.predict(request, cancellation=cancellation)['status'])
        self.assertEqual(2, worker.calls)

    def test_cancel_or_deadline_during_a_miss_never_invokes_the_backend(self):
        for status in ('cancelled', 'timed-out'):
            with self.subTest(status=status):
                session, worker, request = self.session(); cancellation = threading.Event()
                clock = [100.0]
                def interrupted_lookup(key):
                    if status == 'cancelled': cancellation.set()
                    else: clock[0] = 102.0
                    return None
                with patch.object(session.cache, 'get', side_effect=interrupted_lookup), \
                     patch('agent_braid.forecast_advice.time.monotonic_ns', return_value=100000000000), \
                     patch('agent_braid.forecast_advice.time.monotonic', side_effect=lambda: clock[0]):
                    result = session.predict(request, cancellation=cancellation)
                self.assertEqual(status, result['status'])
                self.assertEqual(0, worker.calls)
                self.assertFalse(session.cache.records)
                self.assertIsNone(session.last_cache_receipt)

    def test_already_cancelled_or_expired_hit_never_even_reads_cache(self):
        for status in ('cancelled', 'timed-out'):
            with self.subTest(status=status):
                session, worker, request = self.session(); session.predict(request)
                cancellation = threading.Event()
                if status == 'cancelled': cancellation.set()
                with patch.object(session.cache, 'get') as get, \
                     patch('agent_braid.forecast_advice.time.monotonic_ns', return_value=100000000000), \
                     patch('agent_braid.forecast_advice.time.monotonic', return_value=100.0):
                    result = session.predict(request, cancellation=cancellation,
                                             deadline=99.0 if status == 'timed-out' else None)
                self.assertEqual(status, result['status']); get.assert_not_called()
                self.assertEqual(1, worker.calls)
                self.assertIsNone(session.last_cache_receipt)

    def test_terminal_backend_results_never_populate_the_cache(self):
        for status in ('unavailable', 'refused', 'timed-out', 'cancelled'):
            with self.subTest(status=status):
                session, worker, request = self.session()
                terminal = envelope(request['window'], 1, model_digest=digest(session.adapter.manifest),
                                    status=status, reasons=('synthetic-control',))
                with patch.object(worker, 'forecast', return_value=terminal) as call:
                    self.assertEqual(status, session.predict(request)['status'])
                    self.assertEqual(status, session.predict(request)['status'])
                self.assertEqual(2, call.call_count)
                self.assertFalse(session.cache.records)
                self.assertFalse(session.last_cache_receipt['cacheHit'])

    def test_cache_storage_and_sessions_do_not_share_mutable_results(self):
        cache = ForecastCache(capacity=2); source = {'values': [1]}
        cache.put('first', source); source['values'][0] = 9
        read = cache.get('first'); read['values'][0] = 8
        self.assertEqual([1], cache.get('first')['values'])
        cache.put('second', source); cache.get('first'); cache.put('third', source)
        self.assertIsNone(cache.get('second'))
        first, worker1, request = self.session(); second, worker2, _ = self.session()
        output = first.predict(request); output['quantiles'][0][0][1] = 999
        self.assertNotEqual(999, first.predict(request)['median'][0][0])
        self.assertEqual('forecast', second.predict(request)['status'])
        self.assertEqual((1, 1), (worker1.calls, worker2.calls))

    def test_cancel_or_deadline_during_cache_commit_removes_only_its_entry(self):
        for terminal in ('cancelled', 'timed-out'):
            with self.subTest(terminal=terminal):
                session, worker, request = self.session(); cancellation = threading.Event()
                original = session.predict(request); original_key = session.last_cache_receipt['key']
                changed = deepcopy(request); changed['horizon'] = 5
                put = session.cache.put; clock = [100.0]
                def interrupted_put(key, result):
                    put(key, result)
                    if terminal == 'cancelled': cancellation.set()
                    else: clock[0] = 102.0
                with patch.object(session.cache, 'put', side_effect=interrupted_put), \
                     patch('agent_braid.forecast_advice.time.monotonic_ns', return_value=100000000000), \
                     patch('agent_braid.forecast_advice.time.monotonic', side_effect=lambda: clock[0]):
                    result = session.predict(changed, cancellation=cancellation)
                self.assertEqual(terminal, result['status'])
                self.assertIsNone(session.last_cache_receipt)
                self.assertEqual([original_key], list(session.cache.records))
                self.assertEqual(original, session.cache.get(original_key))
                self.assertEqual(2, worker.calls)

    def test_a_misbound_cache_packet_refuses_instead_of_relabelling_its_values(self):
        session, worker, request = self.session(); output = session.predict(request)
        key = session.last_cache_receipt['key']
        output['inputDigest'] = 'e' * 64
        output['packetDigest'] = digest({k: v for k, v in output.items() if k != 'packetDigest'})
        session.cache.put(key, output)
        with self.assertRaisesRegex(ForecastError, 'forecast-input-drift'):
            session.predict(request)
        self.assertIsNone(session.last_cache_receipt)
        self.assertEqual(1, worker.calls)

    def test_a_cached_model_identity_cannot_be_relabelled_as_the_current_artifact(self):
        session, worker, request = self.session(); output = session.predict(request)
        key = session.last_cache_receipt['key']; output['modelDigest'] = 'a' * 64
        output['packetDigest'] = digest({k: v for k, v in output.items() if k != 'packetDigest'})
        session.cache.put(key, output)
        with self.assertRaisesRegex(ForecastError, 'cached-artifact-drift'):
            session.predict(request)
        self.assertEqual(1, worker.calls)
        self.assertIsNone(session.last_cache_receipt)
