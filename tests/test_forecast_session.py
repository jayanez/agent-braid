# SPDX-License-Identifier: AGPL-3.0-only
import unittest,time,threading
from unittest.mock import patch
from agent_braid.forecast_data import ForecastError,digest
from agent_braid.forecast_advice import ForecastSession,capabilities
from tests.forecast_helpers import window

def request():return {'version':'agent-braid-forecast-request-v1','backend':'persistence','window':window(),'horizon':1,'alpha':.3}

class ForecastSessionTests(unittest.TestCase):
    def test_revoked_approval_unloads_owned_worker_and_clears_cache(self):
        from tests.test_forecast_worker import manifest,TestControlVerifier
        from agent_braid.forecast_outputs import envelope
        class Worker:
            loaded=True;closed=False
            def forecast(self,w,h,**kwargs):return envelope(w,h,model_digest=digest(manifest()),quantiles=[[[4,4,4]]])
            def close(self):self.closed=True;self.loaded=False
        worker=Worker();session=ForecastSession(manifest(),artifact_verifier=TestControlVerifier());session.adapter.worker=worker
        r=request();r['backend']='chronos2';self.assertEqual('forecast',session.predict(r)['status'])
        session.adapter.artifact_verifier=None
        self.assertEqual('unavailable',session.predict(r)['status']);self.assertTrue(worker.closed)
        self.assertFalse(session.cache.records);self.assertIsNone(session.adapter.worker);session.close()

    def test_cache_reemits_current_cost_and_changed_inputs_miss(self):
        session=ForecastSession();r=request();first=session.predict(r);second=session.predict(r)
        self.assertEqual(first['quantiles'],second['quantiles']);self.assertTrue(session.last_cache_receipt['cacheHit'])
        self.assertEqual(first['packetDigest'],session.last_cache_receipt['originalForecastDigest'])
        r['window']['values'][0][-1]=8;self.assertEqual([[8]],session.predict(r)['median'])
        self.assertFalse(session.last_cache_receipt['cacheHit']);session.close()

    def test_closed_busy_cancelled_and_timeout_are_explicit(self):
        s=ForecastSession();s.lock.acquire()
        with self.assertRaises(ForecastError):s.predict(request())
        s.lock.release();cancel=threading.Event();cancel.set()
        self.assertEqual('cancelled',s.predict(request(),cancellation=cancel)['status'])
        self.assertEqual('timed-out',s.predict(request(),deadline=time.monotonic()-1)['status'])
        s.close()
        with self.assertRaises(ForecastError):s.predict(request())

    def test_default_and_absent_chronos_do_not_load_model(self):
        self.assertEqual('off',capabilities()['defaultMode'])
        s=ForecastSession();r=request();r['backend']='chronos2'
        self.assertEqual(['artifact-not-approved'],s.predict(r)['reasonCodes']);s.close()

    def controlled_chronos(self,loaded):
        from tests.test_forecast_worker import manifest,TestControlVerifier
        from agent_braid.forecast_outputs import envelope
        class Worker:
            def __init__(self):self.loaded=loaded;self.calls=[]
            def forecast(self,w,h,**kwargs):
                self.calls.append(kwargs);self.loaded=True
                return envelope(w,h,model_digest=digest(manifest()),quantiles=[[[4,4,4]]])
            def close(self):self.loaded=False
        session=ForecastSession(manifest(),artifact_verifier=TestControlVerifier());worker=Worker();session.adapter.worker=worker
        r=request();r['backend']='chronos2';return session,worker,r

    def test_chronos_entry_budget_includes_validation_and_translation(self):
        from agent_braid.forecast_data import validate_window
        from agent_braid.forecast_chronos_inputs import translate_inputs
        for loaded,caller,expected in [(False,None,130),(True,None,101),(False,100.9,100.9)]:
            with self.subTest(loaded=loaded,caller=caller):
                session,worker,r=self.controlled_chronos(loaded);clock=[100]
                def validate(w):clock[0]=100.4;return validate_window(w)
                def translate(w,h):clock[0]=100.8;return translate_inputs(w,h)
                with patch('agent_braid.forecast_advice.time.monotonic_ns',return_value=100000000000), \
                     patch('agent_braid.forecast_advice.time.monotonic',side_effect=lambda:clock[0]), \
                     patch('agent_braid.forecast_advice.validate_window',side_effect=validate), \
                     patch('agent_braid.forecast_chronos.translate_inputs',side_effect=translate):
                    self.assertEqual('forecast',session.predict(r,deadline=caller)['status'])
                self.assertEqual(expected,worker.calls[0]['deadline']);session.close()

    def test_validation_expiry_prevents_worker_and_cache_expiry_prevents_cached_result(self):
        from agent_braid.forecast_data import validate_window
        session,worker,r=self.controlled_chronos(True);clock=[100]
        def validate(w):clock[0]=102;return validate_window(w)
        with patch('agent_braid.forecast_advice.time.monotonic_ns',return_value=100000000000), \
             patch('agent_braid.forecast_advice.time.monotonic',side_effect=lambda:clock[0]), \
             patch('agent_braid.forecast_advice.validate_window',side_effect=validate):
            self.assertEqual('timed-out',session.predict(r)['status'])
        self.assertFalse(worker.calls)
        first=session.predict(r);worker.calls.clear();clock[0]=100
        def cache_get(key):clock[0]=102;return first
        with patch('agent_braid.forecast_advice.time.monotonic_ns',return_value=100000000000), \
             patch('agent_braid.forecast_advice.time.monotonic',side_effect=lambda:clock[0]), \
             patch.object(session.cache,'get',side_effect=cache_get):
            self.assertEqual('timed-out',session.predict(r)['status'])
        self.assertFalse(worker.calls);session.close()
