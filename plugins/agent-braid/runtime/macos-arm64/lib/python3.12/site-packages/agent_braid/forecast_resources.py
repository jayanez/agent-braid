# SPDX-License-Identifier: AGPL-3.0-only
"""Pinned local resource metadata; synthetic fixtures never attest to capacity.

Catalogue pins, expected host/revisions and authority verifiers are trusted caller
configuration, not fields to accept from a forecast/advice request. Construction
checks integrity only. Every permissioned resolve requires external admission.
"""
from copy import deepcopy

from .forecast_data import canonical, parse_record, keys, require, integer, identifier, pin, digest


_RESOURCE_FIELDS = ('version', 'sourceKind', 'profileId', 'hostId', 'executionContract',
                    'allowedModes', 'maxWorkers', 'observedNs', 'expiresNs', 'caps')
_CONTROLS = ('ownedScratch', 'independentGrants', 'verifierRequired',
             'hardCpuLimitSupported', 'hardMemoryLimitSupported')


def _resource(raw):
    profile = parse_record(canonical(raw))
    version = profile.get('version')
    require(version in ('agent-braid-forecast-resource-v1', 'agent-braid-forecast-resource-v2'),
            'unsupported-resource-version')
    keys(profile, _RESOURCE_FIELDS + ('profileRevision',) if version.endswith('v2') else _RESOURCE_FIELDS)
    if version.endswith('v2'):
        pin(profile['profileRevision'])
    require(profile['sourceKind'] in ('synthetic', 'permissioned'), 'unsupported-resource-source')
    for field in ('profileId', 'hostId', 'executionContract'):
        identifier(profile[field])
    require(profile['executionContract'] == 'authorized-serial-index-patch-v1', 'unsupported-execution-contract')
    integer(profile['observedNs']); integer(profile['expiresNs'])
    require(profile['observedNs'] < profile['expiresNs'], 'invalid-resource-interval')
    modes = profile['allowedModes']
    require(type(modes) is list and 1 <= len(modes) <= 2 and
            all(type(mode) is str and mode in ('serial', 'parallel') for mode in modes),
            'unsupported-resource-mode')
    require(len(set(modes)) == len(modes), 'invalid-resource-modes')
    integer(profile['maxWorkers'], 1, 4)
    require('parallel' not in modes or profile['maxWorkers'] >= 2, 'invalid-resource-workers')
    keys(profile['caps'], ('operations', 'patchBytes', 'scratchBytes'))
    integer(profile['caps']['operations'], 2, 4)
    integer(profile['caps']['patchBytes'], 1, 262144)
    integer(profile['caps']['scratchBytes'], 1, 67108864)
    return profile


def validate_resource(raw, *, expected_digest, now_ns, authority_verifier=None):
    profile = _resource(raw)
    pin(expected_digest)
    require(digest(profile) == expected_digest, 'resource-not-allowlisted')
    integer(now_ns)
    require(profile['observedNs'] <= now_ns < profile['expiresNs'], 'stale-resource')
    if profile['sourceKind'] == 'permissioned':
        require(profile['version'] == 'agent-braid-forecast-resource-v2', 'resource-profile-metadata-required')
        require(type(authority_verifier) is ResourceCatalogue, 'resource-not-admitted')
        authority_verifier._admit(profile)
    return deepcopy(profile)


def _registered_profile(raw):
    keys(raw, ('resource', 'metadata'))
    resource = _resource(raw['resource']); metadata = raw['metadata']
    require(resource['version'] == 'agent-braid-forecast-resource-v2', 'resource-profile-metadata-required')
    require(resource['profileRevision'] == digest(metadata), 'resource-metadata-drift')
    keys(metadata, ('runtimeRevision', 'inventoryRevision', 'platform', 'isolation', 'availabilityReceipt'))
    for name in ('runtimeRevision', 'inventoryRevision'):
        pin(metadata[name])
    platform = metadata['platform']
    keys(platform, ('system', 'architecture', 'logicalCpuCount', 'memoryBytes'))
    identifier(platform['system']); identifier(platform['architecture'])
    integer(platform['logicalCpuCount'], 1); integer(platform['memoryBytes'], 1)
    isolation = metadata['isolation']
    keys(isolation, ('revision', 'receiptDigest', 'scope') + _CONTROLS)
    pin(isolation['revision']); pin(isolation['receiptDigest'])
    require(isolation['scope'] == 'owned-git-index-scratch-v1', 'unsupported-resource-isolation')
    for name in _CONTROLS:
        require(type(isolation[name]) is bool, 'invalid-enforcement-metadata')
    require(all(isolation[name] for name in _CONTROLS[:3]), 'resource-isolation-incomplete')
    receipt = metadata['availabilityReceipt']
    keys(receipt, ('version', 'sourceKind', 'profileId', 'hostId', 'inventoryRevision',
                   'clockId', 'timeUnit', 'observedNs', 'expiresNs', 'observationsDigest'))
    require(receipt['version'] == 'agent-braid-resource-availability-v1', 'unsupported-availability-version')
    identifier(receipt['clockId'])
    require(receipt['timeUnit'] == 'monotonic-ns', 'unsupported-availability-clock')
    for name in ('sourceKind', 'profileId', 'hostId', 'observedNs', 'expiresNs'):
        require(type(receipt[name]) is type(resource[name]) and receipt[name] == resource[name],
                'resource-availability-drift')
    require(receipt['inventoryRevision'] == metadata['inventoryRevision'], 'resource-availability-drift')
    observations = {name: resource[name] for name in ('caps', 'allowedModes', 'maxWorkers')}
    observations.update(platform=platform, isolation=isolation)
    require(receipt['observationsDigest'] == digest(observations), 'resource-observations-drift')
    return deepcopy(raw)


class ResourceCatalogue:
    """One configured local profile, or an empty unadmitted real catalogue.

    This class reads no host data and creates no workers or grants. False hard
    limit support never claims an enforced cap. A consumer requiring a control
    must name it in trusted ``required_controls``; unsupported controls refuse.
    Permissioned profiles declaring parallel require CPU/memory enforcement
    support; this minimum cannot be removed by required_controls. The external
    verifier reviews the entire profile/availability receipt and its admitted
    modes on every use, using a copy. Flags are not proof without that review.
    """

    def __init__(self, raw, *, expected_digest, host_id, clock_id, runtime_revision,
                 isolation_revision, inventory_revision, authority_verifier=None,
                 required_controls=()):
        catalogue = parse_record(canonical(raw))
        keys(catalogue, ('version', 'sourceKind', 'profiles', 'executionAuthorization'))
        require(catalogue['version'] == 'agent-braid-resource-catalogue-v1', 'unsupported-catalogue-version')
        pin(expected_digest)
        require(digest(catalogue) == expected_digest, 'catalogue-not-allowlisted')
        require(catalogue['executionAuthorization'] is False, 'resource-cannot-authorize')
        require(catalogue['sourceKind'] in ('synthetic', 'permissioned'), 'unsupported-resource-source')
        profiles = catalogue['profiles']
        require(type(profiles) is list and len(profiles) <= 1, 'resource-catalogue-cardinality')
        self._profiles = {}
        for raw_profile in profiles:
            profile = _registered_profile(raw_profile)
            require(profile['resource']['sourceKind'] == catalogue['sourceKind'], 'resource-provenance-drift')
            self._profiles[profile['resource']['profileId']] = profile
        self._host_id = identifier(host_id)
        self._clock_id = identifier(clock_id)
        self._runtime = pin(runtime_revision)
        self._isolation = pin(isolation_revision)
        self._inventory = pin(inventory_revision)
        require(type(required_controls) in (list, tuple) and
                all(type(name) is str and name in _CONTROLS for name in required_controls),
                'invalid-required-enforcement')
        self._required_controls = tuple(required_controls)
        require(authority_verifier is None or callable(authority_verifier), 'invalid-resource-verifier')
        self._verifier = authority_verifier
        self._digest = expected_digest

    def _profile(self, profile_id):
        identifier(profile_id)
        require(profile_id in self._profiles, 'unknown-resource')
        profile = self._profiles[profile_id]
        resource, metadata = profile['resource'], profile['metadata']
        require(resource['hostId'] == self._host_id, 'resource-host-drift')
        require(metadata['availabilityReceipt']['clockId'] == self._clock_id, 'resource-clock-drift')
        require(metadata['runtimeRevision'] == self._runtime, 'resource-runtime-drift')
        require(metadata['isolation']['revision'] == self._isolation, 'resource-isolation-drift')
        require(metadata['inventoryRevision'] == self._inventory, 'resource-inventory-drift')
        require(all(metadata['isolation'][name] for name in self._required_controls),
                'resource-enforcement-unavailable')
        return profile

    def _admit(self, resource):
        profile = self._profile(resource['profileId'])
        require(canonical(profile['resource']) == canonical(resource), 'resource-not-allowlisted')
        if 'parallel' in resource['allowedModes']:
            require(all(profile['metadata']['isolation'][name] for name in _CONTROLS[3:]),
                    'resource-enforcement-unavailable')
        require(self._verifier is not None, 'resource-not-admitted')
        try:
            admitted = self._verifier(deepcopy(profile)) is True
        except Exception:
            admitted = False
        require(admitted, 'resource-not-admitted')

    def resolve(self, profile_id, *, now_ns, mode, workers, operations, patch_bytes, scratch_bytes):
        profile = self._profile(profile_id)
        resource, metadata = profile['resource'], profile['metadata']
        resource = validate_resource(resource, expected_digest=digest(resource), now_ns=now_ns,
                                     authority_verifier=self)
        require(type(mode) is str and mode in resource['allowedModes'], 'resource-mode-not-admitted')
        integer(workers, 1, resource['maxWorkers'])
        integer(operations, 2, resource['caps']['operations'])
        integer(patch_bytes, 1, resource['caps']['patchBytes'])
        integer(scratch_bytes, 1, resource['caps']['scratchBytes'])
        require(workers <= operations and (workers == 1 if mode == 'serial' else workers >= 2),
                'resource-worker-budget')
        return {'version': 'agent-braid-resource-eligibility-v1', 'sourceKind': resource['sourceKind'],
                'catalogueDigest': self._digest, 'profileDigest': digest(profile),
                'resourceDigest': digest(resource), 'resource': resource, 'metadata': deepcopy(metadata),
                'checkedNs': now_ns, 'mode': mode, 'workers': workers,
                'requested': {'operations': operations, 'patchBytes': patch_bytes, 'scratchBytes': scratch_bytes},
                'executionAuthorization': False}
