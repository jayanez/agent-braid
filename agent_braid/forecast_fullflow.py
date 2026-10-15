# SPDX-License-Identifier: AGPL-3.0-only
"""One selected synthetic flow; metrology scope never authorizes execution.

A trusted collector performs the separately admitted worker lifecycle inside
this operation. Its fresh batch is consumed, not relabelled as new inference.
The final metrology attestation is outside the measured product boundary.
"""
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import secrets

from .forecast_cost import CostRecorder, summarize_cost_ledger
from .forecast_data import canonical, digest, integer, keys, parse_record, pin, require
from .forecast_outputs import validate_forecast
from .forecast_store import open_directory

VERSION = 'agent-braid-selected-flow-cost-v2'


def _write(directory, name, value):
    raw = canonical(value) + b'\n'
    parent = open_directory(directory, private=True)
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.fsync(parent)
        fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent)
        with os.fdopen(fd, 'rb') as stream:
            require(stream.read(len(raw) + 1) == raw, 'payload-readback-drift')
    finally:
        os.close(parent)
    return hashlib.sha256(raw).hexdigest()


def validate_model_batch(raw, window, nonce, source_kind):
    """Validate a fresh batch's bindings, not its source authenticity."""
    batch = parse_record(canonical(raw))
    keys(batch, ('version', 'runNonce', 'sourceKind', 'manifestDigest', 'inputDigest',
                 'rows', 'backendCalls', 'cacheHit', 'cleanupConfirmed',
                 'collectorDigest', 'counterReceiptDigest', 'receiptDigest'))
    require(batch['version'] == 'agent-braid-selected-model-batch-v1'
            and batch['runNonce'] == nonce and batch['sourceKind'] == source_kind
            and source_kind in ('synthetic-simulation', 'authentic-on-synthetic'),
            'model-batch-scope-drift')
    require(batch['inputDigest'] == digest(window), 'model-batch-input-drift')
    for field in ('manifestDigest', 'collectorDigest', 'counterReceiptDigest'):
        pin(batch[field])
    require(type(batch['backendCalls']) is int and batch['backendCalls'] == 2
            and batch['cacheHit'] is True and batch['cleanupConfirmed'] is True,
            'model-batch-lifecycle-incomplete')
    rows = batch['rows']
    require(type(rows) is list and len(rows) == 3, 'session-call-count-drift')
    for index, horizon in enumerate((1, 5, 1)):
        row = rows[index]
        keys(row, ('horizon', 'wallNs', 'forecast'))
        require(type(row['horizon']) is int and row['horizon'] == horizon,
                'session-horizon-drift')
        integer(row['wallNs'])
        require(row['wallNs'] <= (30000000000 if index == 0 else 1000000000),
                'session-call-budget-exceeded')
        packet = validate_forecast(row['forecast'], window, horizon)
        require(packet['status'] == 'forecast'
                and packet['modelDigest'] == batch['manifestDigest'], 'model-batch-forecast-drift')
    require(rows[0]['forecast']['quantiles'] == rows[2]['forecast']['quantiles'],
            'cached-forecast-drift')
    require(batch['receiptDigest'] == digest({k:v for k,v in batch.items()
                                              if k != 'receiptDigest'}), 'model-batch-digest-drift')
    return batch


def _waited_children_cpu():
    try:
        import resource
    except ImportError:
        return None
    usage = resource.getrusage(resource.RUSAGE_CHILDREN)
    return round((usage.ru_utime + usage.ru_stime) * 1e9)


class _BatchConsumer:
    def __init__(self, batch, window):
        self.batch, self.window = batch, window

    def predict(self, request):
        require(request['backend'] == 'chronos2' and request['horizon'] == 1
                and request['window'] == self.window, 'batch-consumption-request-drift')
        return deepcopy(self.batch['rows'][0]['forecast'])


def run_selected_flow(directory, *, collector, operator, artifact_digest,
                      source_kind='authentic-on-synthetic'):
    """Collect once, consume fresh forecasts and retain every fixed fixture arm.

    The callable collector owns admission, lifetime counters and bounded cleanup;
    generic validation cannot certify it. No external commands are selected by
    input records. The caller supplies an independent operator, never a forecaster.
    Existing output is refused before work. Terminal receipt storage failure
    propagates; partial durable files stay available for the outside observer.
    """
    from .forecast_lab import signal_episode, git_fixture
    from .forecast_experiment import paired_synthetic_episode
    pin(artifact_digest)
    require(callable(collector) and callable(operator), 'independent-boundaries-required')
    require(source_kind in ('synthetic-simulation', 'authentic-on-synthetic'), 'unsupported-flow-source')
    output = Path(directory).absolute()
    nonce = secrets.token_hex(16)
    children_before = _waited_children_cpu()
    recorder = CostRecorder('selected-' + nonce, digest({'seed':20261015}), artifact_digest,
                            source_kind='authentic-on-synthetic')
    with recorder.phase('output-allocation', 'isolated-preparation'):
        parent = open_directory(output.parent, private=False)
        try:
            os.mkdir(output.name, mode=0o700, dir_fd=parent)
        finally:
            os.close(parent)
    batch = None; episodes = []; progress = {}; completed_fixtures = set()
    error = None; code = 0; published = False
    cleanup = False; payload_sha = None
    try:
        with recorder.phase('register-operation', 'verification'):
            _write(output, 'start.json', {'version':VERSION,'runNonce':nonce,
                'sourceKind':source_kind,'artifactDigest':artifact_digest,
                'intendedFixtures':['independent','dependency-chain'],
                'intendedArms':['serial-reference','non-model-reference','forecast-choice'],
                'executionAuthorization':False})
        with recorder.phase('signals', 'data-preparation'):
            signal = signal_episode('constant', seed=20261015)
        with recorder.phase('fresh-model-lifecycle', 'forecast'):
            raw_batch = collector(deepcopy(signal['window']), nonce)
            # Cleanup is known only after the collector validates and returns.
            batch = validate_model_batch(raw_batch, signal['window'], nonce, source_kind)
            cleanup = True
        consumer = _BatchConsumer(batch, signal['window'])
        for chain in (False, True):
            with recorder.phase('fixture-' + str(chain), 'isolated-preparation'):
                scope = git_fixture(seed=20261015 + int(chain), dependency_chain=chain)
                fixture = scope.__enter__()
            def observe(value):
                progress[chain] = value
                active = value['activeArm']
                ordinal = len(value['arms']) + (1 if active is not None else 0)
                event = 'start' if active is not None else 'end'
                with recorder.phase('progress-'+str(chain)+'-'+str(ordinal)+'-'+event, 'export'):
                    _write(output, 'arm-progress-'+str(int(chain))+'-'+str(ordinal)+'-'+event+'.json', value)
            try:
                episodes.append(paired_synthetic_episode(
                    fixture, signal, operator=operator, session=consumer,
                    order_seed=20261015 + int(chain), cost_recorder=recorder,
                    progress=observe))
                completed_fixtures.add(chain)
            finally:
                try:
                    with recorder.phase('fixture-close-' + str(chain), 'cleanup'):
                        scope.__exit__(None, None, None)
                except BaseException:
                    cleanup = False
                    raise
        if any(a['status'] != 'completed' for e in episodes for a in e['arms']):
            error = 'incomplete-selected-flow'; code = 2
    except BaseException as exc:
        error = type(exc).__name__
        if batch is not None: cleanup = False
        code = 130 if isinstance(exc, KeyboardInterrupt) else 2
    try:
        with recorder.phase('product-payload-publication', 'export'):
            payload_sha = _write(output, 'payload.json', {
                'version': 'agent-braid-selected-flow-payload-v1', 'runNonce':nonce,
                'sourceKind':'authentic-on-synthetic', 'modelSourceKind':source_kind, 'modelBatch':batch, 'pairedEpisodes':episodes,
                'partialEpisodes':[v for k,v in progress.items() if k not in completed_fixtures],
                'intendedRoster':{'fixtures':['independent','dependency-chain'],
                    'arms':['serial-reference','non-model-reference','forecast-choice']},
                'modelAcquisitionScope':'shared-once-per-batch-outside-policy-arm-times',
                'forecastArmPhase':'consumption-of-current-batch-not-new-inference',
                'utilityAccepted':False, 'executionAuthorization':False})
            published = True
    except (OSError, ValueError) as exc:
        error = type(exc).__name__; code = 2
    # No synthetic or reused stage is invented to claim broad cost completeness.
    for stage in ('artifact-provisioning', 'engine-startup', 'model-startup', 'residency',
                  'failure-controls', 'waiting-deferred'):
        recorder.unavailable(stage, stage, 'collector-lifecycle-separate-scope' if batch else 'collector-incomplete')
    children_after = _waited_children_cpu()
    children_cpu = None if children_before is None or children_after is None else children_after - children_before
    if children_cpu is not None: integer(children_cpu)
    ledger = recorder.seal(cleanup_confirmed=cleanup)
    result = dict(version=VERSION, runNonce=nonce, sourceKind='authentic-on-synthetic',
                  modelSourceKind=source_kind,
                  ledger=ledger, costSummary=summarize_cost_ledger(ledger),
                  hostWaitedChildrenCpuNs=children_cpu,
                  hostWaitedChildrenScope='waited-native-helper-and-git-excludes-guest-and-host-XPC',
                  hostWaitedChildrenReason='platform-counter-unavailable' if children_cpu is None else None,
                  backendCalls=0 if batch is None else batch['backendCalls'],
                  collectorReceiptDigest=None if batch is None else batch['counterReceiptDigest'],
                  payloadSha256=payload_sha, payloadPublicationIncluded=published,
                  stopEvent='owned-cleanup-and-product-payload-readback',
                  attestationPublicationIncluded=False,
                  attestationReason='metrology-attestation-outside-selected-operation',
                  cleanupConfirmed=cleanup, error=error, exit=code,
                  fullDeploymentCostAccepted=False, economicCostAccepted=False,
                  utilityAccepted=False, executionAuthorization=False)
    result['receiptDigest'] = digest(result)
    _write(output, 'operation.json', result)
    return code
