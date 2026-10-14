# SPDX-License-Identifier: AGPL-3.0-only
"""Allowlisted local resource identities; synthetic profiles are never actual caps."""
from copy import deepcopy
from .forecast_data import canonical,parse_record,keys,require,integer,identifier,pin,digest

def validate_resource(raw, *, expected_digest, now_ns, authority_verifier=None):
    profile=parse_record(canonical(raw)); keys(profile,('version','sourceKind','profileId','hostId','executionContract',
                       'allowedModes','maxWorkers','observedNs','expiresNs','caps'))
    require(profile['version']=='agent-braid-forecast-resource-v1','unsupported-resource-version')
    require(profile['sourceKind'] in ('synthetic','permissioned'),'unsupported-resource-source')
    pin(expected_digest);require(digest(profile)==expected_digest,'resource-not-allowlisted')
    for field in ('profileId','hostId','executionContract'):identifier(profile[field])
    require(profile['executionContract']=='authorized-serial-index-patch-v1','unsupported-execution-contract')
    integer(now_ns);integer(profile['observedNs']);integer(profile['expiresNs'])
    require(profile['observedNs']<=now_ns<profile['expiresNs'],'stale-resource')
    modes=profile['allowedModes'];require(type(modes) is list and modes and len(modes)<=2,'invalid-resource-modes')
    require(len(set(modes))==len(modes) and set(modes)<={'serial','parallel'},'unsupported-resource-mode')
    integer(profile['maxWorkers'],1,4);keys(profile['caps'],('operations','patchBytes','scratchBytes'))
    integer(profile['caps']['operations'],2,4);integer(profile['caps']['patchBytes'],1,262144)
    integer(profile['caps']['scratchBytes'],1,67108864)
    if profile['sourceKind']=='permissioned':
        require(authority_verifier is not None and authority_verifier(deepcopy(profile)) is True,'resource-not-admitted')
    return deepcopy(profile)
