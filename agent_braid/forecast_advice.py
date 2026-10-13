# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit local session facade; forecasts and advice never dispatch work."""
from copy import deepcopy
import threading
import time
from .forecast_data import canonical,parse_record,keys,require,digest,finite,validate_window
from .forecast_baselines import predict_baseline
from .forecast_cache import ForecastCache
from .forecast_chronos import ChronosAdapter
from .forecast_outputs import envelope
from .forecast_policy import advise

def capabilities():
    return {'version':'agent-braid-forecast-capabilities-v1','defaultMode':'off',
            'backends':{'persistence':'available','ewma':'available','chronos2':'requires-approved-local-artifacts'},
            'horizons':[1,5,10],'quantiles':[.1,.5,.9],'activeRequests':1,'queuedRequests':0,
            'systemOneBridge':'deferred-pending-accepted-consumer-contract','transport':'local-stdio',
            'evidenceClass':'heuristic','executionAuthorization':False}

class ForecastSession:
    def __init__(self,manifest=None,*,artifact_verifier=None):
        self.adapter=ChronosAdapter(deepcopy(manifest),artifact_verifier=artifact_verifier)
        self.cache=ForecastCache();self.lock=threading.Lock();self.closed=False;self.last_cache_receipt=None

    def capabilities(self):
        result=capabilities();result['model']=self.adapter.capabilities();return result

    def predict(self,raw,*,deadline=None,cancellation=None):
        started=time.monotonic_ns();request=parse_record(canonical(raw))
        keys(request,('version','backend','window','horizon','alpha'))
        require(request['version']=='agent-braid-forecast-request-v1','unsupported-request-version')
        require(request['backend'] in ('persistence','ewma','chronos2'),'unsupported-backend')
        window=validate_window(request['window']);require(type(request['horizon']) is int and request['horizon'] in (1,5,10),'unsupported-horizon')
        finite(request['alpha']);require(0<request['alpha']<=1,'invalid-ewma-alpha')
        require(self.lock.acquire(blocking=False),'session-busy')
        try:
            require(not self.closed,'session-closed')
            model_digest=digest(self.adapter.manifest) if self.adapter.manifest is not None else digest({'artifact':None})
            if request['backend']=='chronos2' and not self.adapter.capabilities()['available']:
                self.cache.clear();self.adapter.close();self.adapter.worker=None
                return envelope(window,request['horizon'],model_digest=model_digest,status='unavailable',reasons=('artifact-not-approved',),started_ns=started)
            if cancellation is not None and cancellation.is_set():
                return envelope(window,request['horizon'],model_digest=model_digest,status='cancelled',reasons=('cancelled',),started_ns=started)
            if deadline is not None and time.monotonic()>=deadline:
                return envelope(window,request['horizon'],model_digest=model_digest,status='timed-out',reasons=('deadline-exceeded',),started_ns=started)
            key=self.cache.key(request,model_digest);cached=self.cache.get(key)
            if cached is not None:
                result=envelope(window,request['horizon'],model_digest=cached['modelDigest'],quantiles=cached['quantiles'],started_ns=started)
                self.last_cache_receipt={'cacheHit':True,'key':key,'originalForecastDigest':cached['packetDigest'],
                                         'currentForecastDigest':result['packetDigest'],'wallNs':time.monotonic_ns()-started}
                return result
            if request['backend']=='chronos2':result=self.adapter.forecast(window,request['horizon'],deadline=deadline,cancellation=cancellation)
            else:result=predict_baseline(window,request['horizon'],method=request['backend'],alpha=request['alpha'])
            if result['status']=='forecast':self.cache.put(key,result)
            self.last_cache_receipt={'cacheHit':False,'key':key,'originalForecastDigest':None,
                                     'currentForecastDigest':result['packetDigest'],'wallNs':time.monotonic_ns()-started}
            return deepcopy(result)
        finally:self.lock.release()

    def advice(self,request):
        require(not self.closed,'session-closed');return advise(request)

    def close(self):
        require(self.lock.acquire(blocking=False),'session-busy')
        try:self.adapter.close();self.cache.clear();self.closed=True
        finally:self.lock.release()
