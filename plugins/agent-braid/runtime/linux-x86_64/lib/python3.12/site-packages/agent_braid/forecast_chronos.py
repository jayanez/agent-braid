# SPDX-License-Identifier: AGPL-3.0-only
"""Lazy local Chronos contract; no torch import or model load in host discovery."""
from time import monotonic_ns
from .forecast_data import require,finite,digest
from .forecast_outputs import envelope
from .forecast_chronos_inputs import translate_inputs
from .forecast_authority import require_artifact_approval
from .forecast_data import ForecastError

def normalize_output(window,horizon,quantiles,points,*,model_digest,started_ns=None):
    require(type(quantiles) is list and len(quantiles)==1 and type(points) is list and len(points)==1,'invalid-item-axis')
    normalized=envelope(window,horizon,model_digest=model_digest,quantiles=quantiles[0],started_ns=started_ns)
    require(type(points[0]) is list and len(points[0])==len(normalized['median']),'invalid-point-axis')
    for actual,expected in zip(points[0],normalized['median']):
        require(type(actual) is list and len(actual)==horizon,'invalid-point-axis')
        for a,b in zip(actual,expected):
            finite(a);require(abs(a-b)<=1e-6*max(1,abs(b)),'upstream-point-not-median')
    return normalized

class ChronosAdapter:
    def __init__(self,manifest=None,*,artifact_verifier=None,worker=None):
        self.manifest=manifest;self.artifact_verifier=artifact_verifier;self.worker=worker

    def capabilities(self):
        approved=False
        if self.manifest is not None:
            try:require_artifact_approval(self.manifest,self.artifact_verifier);approved=True
            except ForecastError:pass
        return {'backend':'chronos2-local-cpu','available':approved,'requiresExternalArtifactApproval':True,
                'modelLoaded':bool(self.worker is not None and getattr(self.worker,'loaded',False)),
                'evidenceClass':'heuristic','executionAuthorization':False}

    def forecast(self,window,horizon,*,deadline=None,cancellation=None):
        started=monotonic_ns();model=digest(self.manifest) if self.manifest is not None else digest({'backend':'unavailable'})
        translate_inputs(window,horizon)
        if not self.capabilities()['available']:
            return envelope(window,horizon,model_digest=model,status='unavailable',reasons=('artifact-not-approved',),started_ns=started)
        if self.worker is None:
            from .forecast_worker import DockerCPUWorker
            self.worker=DockerCPUWorker(self.manifest,artifact_verifier=self.artifact_verifier)
        return self.worker.forecast(window,horizon,deadline=deadline,cancellation=cancellation)

    def close(self):
        if self.worker is not None:self.worker.close()
