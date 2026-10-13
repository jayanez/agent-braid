# SPDX-License-Identifier: AGPL-3.0-only
import unittest,time,threading
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
