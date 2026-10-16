# SPDX-License-Identifier: AGPL-3.0-only
"""Prospective metadata-only feasibility; calibration/holdout outcomes stay sealed."""
from collections import Counter
from .forecast_data import require,keys,identifier,integer,finite,pin,digest,canonical,parse_record

def readiness_packet(raw,*,source_verifier=None):
    registration=parse_record(canonical(raw));keys(registration,('version','sourceKind','sourceRegisterDigest','primaryGroups','episodes'))
    require(registration['version']=='agent-braid-forecast-readiness-v1','unsupported-readiness-version')
    require(registration['sourceKind'] in ('synthetic','permissioned'),'unsupported-readiness-source')
    pin(registration['sourceRegisterDigest'])
    primary=registration['primaryGroups'];require(type(primary) is list and 1<=len(primary)<=8
            and len(set(map(identifier,primary)))==len(primary),'invalid-primary-groups')
    if registration['sourceKind']=='permissioned':require(source_verifier is not None and source_verifier(registration) is True,'source-not-admitted')
    episodes=registration['episodes'];require(type(episodes) is list and len(episodes)<=4096,'readiness-roster-budget')
    seen=set();counts=Counter();groups=Counter();exclusions=Counter()
    for episode in episodes:
        keys(episode,('episodeId','partition','resourceGroup','observedHistoryBins','missingTargetFraction','status','exclusionReason'))
        identity=identifier(episode['episodeId']);require(identity not in seen,'duplicate-readiness-episode');seen.add(identity)
        require(episode['partition'] in ('development','calibration','holdout'),'unsupported-partition')
        identifier(episode['resourceGroup']);require(episode['resourceGroup'] in primary,'unregistered-primary-group')
        integer(episode['observedHistoryBins'],0,128)
        finite(episode['missingTargetFraction']);require(0<=episode['missingTargetFraction']<=1,'invalid-missingness')
        require(episode['status'] in ('admitted','excluded'),'invalid-readiness-status')
        eligible=episode['status']=='admitted' and episode['observedHistoryBins']>=64 and episode['missingTargetFraction']<=.2
        if episode['status']=='excluded':identifier(episode['exclusionReason']);exclusions[episode['exclusionReason']]+=1
        else:
            require(episode['exclusionReason'] is None,'inconsistent-readiness-exclusion')
            if not eligible:exclusions['insufficient-history-or-missingness']+=1
        counts[episode['partition']]+=1
        if eligible and episode['partition']=='holdout':groups[episode['resourceGroup']]+=1
    for group in primary:groups.setdefault(group,0)
    ready=all(count>=30 for count in groups.values())
    result={'version':'agent-braid-forecast-readiness-packet-v1','sourceKind':registration['sourceKind'],
            'sourceRegisterDigest':registration['sourceRegisterDigest'],'intendedEpisodes':len(episodes),'partitionCounts':dict(counts),
            'eligibleHoldoutGroups':dict(groups),'exclusionCounts':dict(exclusions),
            'status':'synthetic-rehearsal' if registration['sourceKind']=='synthetic' else 'ready' if ready else 'infeasible',
            'outcomeValuesInspected':False,'realLaunchAuthorized':False,'utilityAccepted':False}
    result['packetDigest']=digest(result);return result
