# SPDX-License-Identifier: AGPL-3.0-only
"""Causal regularization and episode-level chronological partition controls."""
from copy import deepcopy
from .forecast_data import WINDOW_VERSION, require, integer, keys, identifier, finite, validate_window

def compile_window(events, *, target_ids, units, grid_start_ns, step_ns, bins, cutoff_ns,
                   episode_group, resource_digest, partition_digest, transform_digest):
    integer(bins,1,128); integer(step_ns,1); integer(grid_start_ns); integer(cutoff_ns)
    require(type(events) is list and len(events)<=4096,'event-budget-exceeded')
    require(type(target_ids) is list and type(units) is list and len(target_ids)==len(units),'invalid-targets')
    require(1<=len(target_ids)<=8 and len(set(map(identifier,target_ids)))==len(target_ids),'invalid-targets')
    values=[[None]*bins for _ in target_ids]; masks=[[False]*bins for _ in target_ids]
    available=[[None]*bins for _ in target_ids]; reasons=[['not-observed']*bins for _ in target_ids]
    seen=set()
    for event in events:
        keys(event,('targetId','eventNs','availableAtNs','unit','value'))
        require(event['targetId'] in target_ids,'unknown-target'); target=target_ids.index(event['targetId'])
        require(event['unit']==units[target],'mixed-units'); finite(event['value'])
        timestamp=integer(event['eventNs']); arrival=integer(event['availableAtNs'])
        require(arrival>=timestamp,'arrival-precedes-event')
        if timestamp<grid_start_ns or timestamp>=grid_start_ns+bins*step_ns: continue
        require((timestamp-grid_start_ns)%step_ns==0,'off-grid-event')
        index=(timestamp-grid_start_ns)//step_ns; key=(target,index)
        require(key not in seen,'duplicate-grid-value'); seen.add(key)
        if arrival>cutoff_ns: reasons[target][index]='late-arrival'; continue
        values[target][index]=event['value']; masks[target][index]=True
        available[target][index]=arrival; reasons[target][index]=None
    return validate_window({'version':WINDOW_VERSION,'sourceKind':'synthetic','episodeGroup':episode_group,
        'resourceReceiptDigest':resource_digest,'gridStartNs':grid_start_ns,'stepNs':step_ns,'cutoffNs':cutoff_ns,
        'targetIds':target_ids,'units':units,'values':values,'observedMask':masks,'availableAtNs':available,
        'missingReasons':reasons,'pastCovariates':{},'knownFutureCovariates':{},
        'partitionDigest':partition_digest,'transformDigest':transform_digest})

def validate_partitions(rows):
    require(type(rows) is list and len(rows)<=4096,'partition-budget-exceeded')
    groups={}; intervals=[]; ranks={'development':0,'calibration':1,'holdout':2}
    for row in rows:
        keys(row,('episodeGroup','partition','startNs','endNs')); group=identifier(row['episodeGroup'])
        partition=row['partition']; require(partition in ranks,'unknown-partition')
        require(group not in groups or groups[group]==partition,'episode-crosses-partitions'); groups[group]=partition
        start=integer(row['startNs']); end=integer(row['endNs']); require(start<=end,'invalid-partition-interval')
        intervals.append((start,end,partition))
    for i,(start,end,partition) in enumerate(intervals):
        for other_start,other_end,other_partition in intervals[i+1:]:
            if partition==other_partition: continue
            earlier,later=((start,end,partition),(other_start,other_end,other_partition)) if start<=other_start else ((other_start,other_end,other_partition),(start,end,partition))
            require(earlier[1]<later[0] and ranks[earlier[2]]<ranks[later[2]],'unpurged-or-nonchronological-partition')
    return deepcopy(rows)
