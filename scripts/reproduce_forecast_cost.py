#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
"""Capture owned synthetic host costs; no model loading, daemon or network work."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import platform
import signal
import sys
import sysconfig


def _write(directory, name, value):
    from agent_braid.forecast_data import canonical
    from agent_braid.forecast_store import open_directory
    parent = open_directory(directory, private=True)
    try:
        fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                     0o600, dir_fd=parent)
        with os.fdopen(fd, 'wb') as stream:
            stream.write(canonical(value) + b'\n'); stream.flush(); os.fsync(stream.fileno())
        os.fsync(parent)
    finally:
        os.close(parent)
    # Partial output is retained; never retry/overwrite it.


def package_digest():
    """Bind measured installed Python bytes, separately from any wheel/model."""
    import hashlib
    import agent_braid
    from agent_braid.forecast_data import digest, require
    origin = Path(agent_braid.__file__).resolve(strict=True)
    purelib = Path(sysconfig.get_path('purelib')).resolve(strict=True)
    require(origin == purelib / 'agent_braid' / '__init__.py', 'installed-package-origin-required')
    root = origin.parent
    return digest({str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest()
                   for p in sorted(root.rglob('*.py'))})


def reproduce(directory, artifact_digest=None, *, paired_git=False, termination_code=None):
    """Observe this process only; unavailable deployment counters stay unknown."""
    from agent_braid.forecast_cost import CostRecorder, summarize_cost_ledger
    from agent_braid.forecast_data import digest, require
    from agent_braid.forecast_lab import signal_episode, git_fixture
    from agent_braid.forecast_advice import ForecastSession
    from agent_braid.forecast_experiment import paired_synthetic_episode, summarize_pairs
    def pending():
        code = 0 if termination_code is None else termination_code()
        require(type(code) is int and code in (0, 130, 143), 'invalid-termination-code')
        return code
    def guard():
        if pending(): raise SystemExit(pending())
    recorder = CostRecorder('owned-synthetic-cost', digest({'seed': 20261014, 'pairedGit': paired_git}), None)
    session = None; predictions = []; pairs = []; error = None; cleanup = True; exit_code = 0
    import resource
    child_start = resource.getrusage(resource.RUSAGE_CHILDREN)
    child_started_ns = recorder.clock() - recorder.started
    try:
        with recorder.phase('package-identity', 'verification'):
            guard()
            observed_package_digest = package_digest()
            recorder.record['artifactDigest'] = observed_package_digest
            recorder.record['artifactReason'] = None
            require(artifact_digest is None or artifact_digest == observed_package_digest, 'cost-package-binding-drift')
        with recorder.phase('signals', 'data-preparation'):
            guard()
            signal = signal_episode('constant', seed=20261014)
        recorder.unavailable('prior-artifacts', 'artifact-provisioning', 'prior-setup-unallocated',
                             accounting='reused', source_digest=observed_package_digest)
        for stage in ('engine-startup', 'model-startup', 'residency'):
            recorder.unavailable(stage, stage, 'no-model-or-engine-in-this-procedure',
                                 accounting='not-applicable')
        with recorder.phase('session', 'isolated-preparation'):
            guard()
            session = ForecastSession()
        request = dict(version='agent-braid-forecast-request-v1', backend='persistence',
                       window=signal['window'], horizon=1, alpha=.3)
        with recorder.phase('baseline', 'forecast'):
            guard()
            predictions.append(session.predict(request))
            guard()
        with recorder.phase('cache-hit', 'cache'):
            guard()
            predictions.append(session.predict(request))
            require(session.last_cache_receipt['cacheHit'] is True, 'expected-cache-hit')
        with recorder.phase('missing-artifact-refusal', 'failure-controls'):
            guard()
            predictions.append(session.predict({**request, 'backend': 'chronos2'}))
            require(predictions[-1]['status'] == 'unavailable', 'expected-model-unavailable')
        if paired_git:
            from agent_braid.runtime_policy import issue_operator_grant
            def operator(plan, root):
                return issue_operator_grant(plan, root, acknowledge=plan['planDigest'])
            for chain in (False, True):
                guard()
                with recorder.phase('fixture-' + str(chain), 'isolated-preparation'):
                    fixture_scope = git_fixture(seed=20261014 + int(chain), dependency_chain=chain)
                    fixture = fixture_scope.__enter__()
                try:
                    pairs.append(paired_synthetic_episode(fixture, signal, operator=operator,
                                                         cost_recorder=recorder))
                finally:
                    try:
                        with recorder.phase('fixture-cleanup-' + str(chain), 'cleanup'):
                            fixture_scope.__exit__(None, None, None)
                    except BaseException:
                        cleanup = False
                        raise
        else:
            for stage in ('grants', 'replay', 'isolated-execution', 'advice'):
                recorder.unavailable(stage, stage, 'no-policy-arms-selected', accounting='not-applicable')
        recorder.unavailable('waiting', 'waiting-deferred', 'serial-no-deferred-policy',
                             accounting='not-applicable')
        with recorder.phase('verify', 'verification'):
            guard()
            require(all(p['executionAuthorization'] is False for p in predictions), 'forecast-cannot-authorize')
            require(not any(name.split('.')[0] in ('torch', 'chronos', 'transformers')
                            for name in sys.modules), 'unexpected-ml-import')
            paired_summary = summarize_pairs(pairs) if pairs else None
        with recorder.phase('payload-export', 'export'):
            _write(directory, 'payload.json', dict(
                version='agent-braid-synthetic-cost-payload-v1', python=platform.python_version(),
                packageOrigin=str(Path(__import__('agent_braid').__file__).resolve(strict=True)),
                forecasts=predictions, pairedEpisodes=pairs, pairedSummary=paired_summary,
                modelLoaded=False, realWorkloadEvidence=False, utilityAccepted=False))
    except BaseException as exc:
        interrupted = isinstance(exc, (KeyboardInterrupt, SystemExit))
        error = 'synthetic-cost-procedure-interrupted' if interrupted else 'synthetic-cost-procedure-failed'
        exit_code = 130 if isinstance(exc, KeyboardInterrupt) else exc.code if isinstance(exc, SystemExit) and exc.code in (130, 143) else 2
    finally:
        try:
            with recorder.phase('session-cleanup', 'cleanup'):
                if session is not None: session.close()
        except BaseException:
            cleanup = False; error = 'synthetic-cleanup-unconfirmed'; exit_code = 2
    if pending():
        error = 'synthetic-cost-procedure-interrupted'; exit_code = pending()
    child_end = resource.getrusage(resource.RUSAGE_CHILDREN)
    child_finished_ns = recorder.clock() - recorder.started
    host_usage = resource.getrusage(resource.RUSAGE_SELF)
    memory_observed_ns = recorder.clock() - recorder.started
    ledger = recorder.seal(cleanup_confirmed=cleanup)
    children = next(row for row in ledger['cpu'] if row['domain'] == 'client-children')
    children.update(meterId='owned-waited-children', startedNs=child_started_ns,
                    finishedNs=child_finished_ns,
                    beforeNs=round((child_start.ru_utime + child_start.ru_stime) * 1e9),
                    afterNs=round((child_end.ru_utime + child_end.ru_stime) * 1e9), reason=None)
    ledger['memory'] = [dict(meterId='coordinator-process', scope='process-lifetime-peak',
                            observedAtNs=memory_observed_ns,
                            bytes=int(host_usage.ru_maxrss) * (1 if sys.platform == 'darwin' else 1024),
                            reason=None, sourceDigest=None, samplePeriodNs=None,
                            limitBytes=None, limitReason='host-counter-not-enforced-cap')]
    ledger['receiptDigest'] = digest({k: v for k, v in ledger.items() if k != 'receiptDigest'})
    _write(directory, 'ledger.json', ledger)
    if pending():
        error = 'synthetic-cost-procedure-interrupted'; exit_code = pending()
    summary = summarize_cost_ledger(ledger)
    _write(directory, 'summary.json', dict(summary=summary, error=error,
                                          modelLoaded=False, executionAuthorization=False))
    return pending() or exit_code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-directory', type=Path, required=True,
                        help='New private directory; existing paths are refused before work')
    parser.add_argument('--artifact-digest',
                        help='Optional expected digest of installed Python file hashes; checked before work')
    parser.add_argument('--paired-git', action='store_true')
    args = parser.parse_args()
    directory = args.output_directory
    queued = {'code': 0}
    def terminate(signum, frame):
        # Cooperative at phase boundaries; never interrupt durable finalization.
        if not queued['code']: queued['code'] = 130 if signum == signal.SIGINT else 143
    previous = {kind: signal.signal(kind, terminate) for kind in (signal.SIGINT, signal.SIGTERM)}
    try:
        from agent_braid.forecast_data import pin
        if args.artifact_digest is not None: pin(args.artifact_digest)
        directory.mkdir(mode=0o700, exist_ok=False)
        return reproduce(directory.resolve(strict=True), args.artifact_digest,
                         paired_git=args.paired_git, termination_code=lambda: queued['code'])
    finally:
        for kind, handler in previous.items(): signal.signal(kind, handler)


if __name__ == '__main__':
    raise SystemExit(main())
