# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit owner-supplied numeric hooks; no process, prompt or repository reads."""
from copy import deepcopy
from time import monotonic_ns
from .forecast_data import require,identifier,finite,integer,digest,reconcile_phases

class TelemetryRecorder:
    def __init__(self, episode_id, counters, *, clock=monotonic_ns):
        identifier(episode_id);require(type(counters) is dict and len(counters)<=16,'invalid-counter-allowlist')
        for name,unit in counters.items():identifier(name);identifier(unit)
        self.episode=episode_id;self.allowlist=deepcopy(counters);self.clock=clock
        self.origin=integer(clock());self.last=self.origin;self.active={};self.phases=[];self.counters=[];self.seen=set();self.closed=False

    def _tick(self):
        require(not self.closed,'telemetry-closed');now=integer(self.clock());require(now>=self.last,'clock-regressed')
        self.last=now;return now-self.origin

    def start_phase(self,name):
        identifier(name);require(name not in self.active and len(self.phases)+len(self.active)<1024,'invalid-phase')
        self.active[name]=self._tick()

    def end_phase(self,name):
        require(name in self.active,'unknown-phase');end=self._tick()
        self.phases.append({'name':name,'startedNs':self.active.pop(name),'finishedNs':end})

    def sample(self,name,value,*,reason=None):
        require(name in self.allowlist and len(self.counters)<4096,'counter-not-allowlisted');timestamp=self._tick()
        key=(name,timestamp);require(key not in self.seen,'duplicate-counter-receipt')
        if value is None:identifier(reason)
        else:finite(value);require(reason is None,'inconsistent-counter')
        self.seen.add(key);self.counters.append({'name':name,'unit':self.allowlist[name],'value':value,'reason':reason,'observedNs':timestamp})

    def finish(self):
        wall=self._tick();self.closed=True
        result={'version':'agent-braid-forecast-telemetry-v1','episodeId':self.episode,
                'sourceKind':'authentic-on-synthetic','status':'incomplete-phase' if self.active else 'completed',
                'incompletePhases':sorted(self.active),'phaseIntervals':deepcopy(self.phases),
                'counters':deepcopy(self.counters),**reconcile_phases(self.phases,wall)}
        result['receiptDigest']=digest(result);return result
