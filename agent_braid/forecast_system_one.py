# SPDX-License-Identifier: AGPL-3.0-only
"""Explicit optional bridge boundary; current System 1 contracts are not widened."""
def bridge_capabilities():
    return {'version':'agent-braid-forecast-system-one-v1','status':'deferred',
            'reasonCodes':['forecast-context-consumer-not-accepted'],'evidenceClass':'heuristic','executionAuthorization':False}
