# SPDX-License-Identifier: AGPL-3.0-only
"""Test-only catalogue. Its numbers never attest to a real host or slot."""
import json
from pathlib import Path

from agent_braid.forecast_data import digest


def catalogue():
    path = (Path(__file__).resolve().parents[1] / 'specs' /
            '034-workload-forecast-data/fixtures/synthetic-resource-catalogue.json')
    return json.loads(path.read_text())


def rebind(profile):
    """Simulate a separately configured revision, never an admission decision."""
    resource, metadata = profile['resource'], profile['metadata']
    observation = {k: resource[k] for k in ('caps', 'allowedModes', 'maxWorkers')}
    observation.update(platform=metadata['platform'], isolation=metadata['isolation'])
    receipt = metadata['availabilityReceipt']
    for key in ('sourceKind', 'profileId', 'hostId', 'observedNs', 'expiresNs'):
        receipt[key] = resource[key]
    receipt['inventoryRevision'] = metadata['inventoryRevision']
    receipt['observationsDigest'] = digest(observation)
    resource['profileRevision'] = digest(metadata)
    return profile
