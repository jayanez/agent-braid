# SPDX-License-Identifier: AGPL-3.0-only
"""Frozen synthetic shadow diagnostics and conservative rollback rehearsal."""
from copy import deepcopy
from .forecast_data import keys,require,integer,finite,digest,pin
from .forecast_store import verify_receipt

class SyntheticAdviceMonitor:
    """Observe later synthetic labels; never confer real source or traffic authority."""
    def __init__(self,policy):
        keys(policy,('version','partition','maximumFailures','maximumAbsoluteError'))
        require(policy['version']==1 and policy['partition']=='development','unfrozen-monitor')
        integer(policy['maximumFailures'],1,128);finite(policy['maximumAbsoluteError'])
        require(policy['maximumAbsoluteError']>=0,'invalid-drift-threshold')
        self.policy=deepcopy(policy);self.failures=0;self.rolled_back=False;self.records=[]

    def observe(self,advice,forecast,outcome):
        require(len(self.records)<4096,'trace-budget-exceeded')
        advice=verify_receipt(advice);forecast=verify_receipt(forecast)
        require(advice['sourceKind']==forecast['sourceKind']=='synthetic','monitor-source-not-admitted')
        require(advice['forecastDigest']==forecast['packetDigest'],'trace-forecast-drift')
        keys(outcome,('version','sourceKind','forecastDigest','eventNs','availableAtNs','actual','targetId','unit'))
        require(outcome['version']=='agent-braid-synthetic-outcome-v1' and outcome['sourceKind']=='synthetic','monitor-source-not-admitted')
        require(pin(outcome['forecastDigest'])==forecast['packetDigest'],'outcome-forecast-drift')
        integer(outcome['eventNs']);integer(outcome['availableAtNs'])
        require(outcome['eventNs'] in forecast['futureTimesNs'] and outcome['availableAtNs']>=outcome['eventNs'],'outcome-not-later-observation')
        require(outcome['targetId'] in forecast['targetIds'],'outcome-target-drift')
        target=forecast['targetIds'].index(outcome['targetId']);require(outcome['unit']==forecast['units'][target],'outcome-unit-drift')
        actual=finite(outcome['actual']);error=None
        failed=forecast['status']!='forecast'
        if not failed:
            index=forecast['futureTimesNs'].index(outcome['eventNs'])
            error=abs(actual-forecast['median'][target][index]);failed=error>self.policy['maximumAbsoluteError']
        if failed:self.failures+=1
        self.rolled_back=self.rolled_back or self.failures>=self.policy['maximumFailures']
        trace={'version':'agent-braid-synthetic-shadow-trace-v1','provenance':'synthetic-simulation',
               'adviceDigest':advice['packetDigest'],'forecastDigest':forecast['packetDigest'],'outcomeDigest':digest(outcome),
               'monitorPolicyDigest':digest(self.policy),'absoluteError':error,'failures':self.failures,
               'referenceAction':advice['referenceAction'],'proposedAction':advice['proposedAction'],
               'shadowAction':advice['referenceAction'],'rollbackMode':'off' if self.rolled_back else 'shadow',
               'reason':'synthetic-drift-rollback' if self.rolled_back else 'synthetic-shadow-observation',
               'executionAuthorization':False}
        trace['receiptDigest']=digest(trace);self.records.append(trace);return deepcopy(trace)
