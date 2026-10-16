# SPDX-License-Identifier: AGPL-3.0-only
"""Owned numeric fixtures, never real-source or capacity attestations."""
def window():
    return {'version': 'agent-braid-telemetry-window-v1', 'sourceKind': 'synthetic',
            'episodeGroup': 'episode-1', 'resourceReceiptDigest': 'a' * 64,
            'gridStartNs': 0, 'stepNs': 100000000, 'cutoffNs': 300000000,
            'targetIds': ['load'], 'units': ['count'], 'values': [[1, 2, 3, 4]],
            'observedMask': [[True] * 4], 'availableAtNs': [[0, 100000000, 200000000, 300000000]],
            'missingReasons': [[None] * 4], 'pastCovariates': {}, 'knownFutureCovariates': {},
            'partitionDigest': 'b' * 64, 'transformDigest': 'c' * 64}
