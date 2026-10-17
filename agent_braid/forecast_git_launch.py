# SPDX-License-Identifier: AGPL-3.0-only
"""Opt-in Git launch boundary for an externally contained admission worker.

This module does not create containment, quota or watchdog authority. The trusted
operator supplies a live verifier, outside request/model data. Without its exact
binding no scoped launch is possible. Historical runners remain unchanged.
"""
from contextlib import contextmanager
from copy import deepcopy
import hashlib
import os
from pathlib import Path
import selectors
import secrets
import subprocess
import sys
import threading
import time

from .forecast_admission import PHASES, PhaseLedger
from .forecast_data import digest, integer, pin, require
from .git_process import (
    GitCommandFailure, GitCommandResult,
    run_git as legacy_run_git,
)
from .git_runtime_process import run_owned_git as legacy_run_owned_git

_active = None
_retired = False
_activation = threading.Lock()
INPUT_COMMITS = ('203c74029b594055549b4d97c182829b793502f6',
                 '086901fed1a957271727a4bb4dc1b23790499829')
INPUT_PATCHES = ('453877ff3d7779d64729566ad7e79dd121bc85704c3ae882e6fb32dba3fdbb62',
                 '705a65e1047fd03753c7e44d2fb69fc6d0542bc7e65c5d45bdcead8e77c87fab')


class GitLaunchScope:
    """One isolated worker, shared across its threads, with no public activation.

    Phase time/storage caps are explicit abort limits, not cost estimates. Each
    phase has a separate allocation. A trusted external supervisor must stop and
    confirm work termination before a separately contained final verifier starts.
    The verifier callback must itself have an external deadline; Python checks
    here cannot interrupt a blocked callback or arbitrary non-Git Python work.
    """
    def __init__(self, *, root, source_root, source_digest, git_executable, git_sha256,
                 mode, final_verifier, phase_requests,
                 phase_ns, phase_bytes, terminal_ns, terminal_bytes,
                 max_active, boundary_verifier,
                 verification_of=None, verification_deadline_ns=None,
                 verification_work_root=None,
                 clock=time.monotonic_ns):
        self.root = Path(root).resolve(strict=True)
        self.source_root = Path(source_root).resolve(strict=True)
        self.git_executable = Path(git_executable).resolve(strict=True)
        self.git_sha256 = pin(git_sha256)
        require(self.root.is_dir() and self.source_root.is_dir(), 'admission-roots-required')
        require(mode in ('serial', 'parallel') and final_verifier in ('runtime', 'policy'),
                'admission-route-required')
        require(mode != 'serial' or max_active == 1, 'serial-admission-concurrency')
        require(not self.root.is_relative_to(self.source_root)
                and not self.source_root.is_relative_to(self.root), 'overlapping-admission-roots')
        require(callable(boundary_verifier), 'operator-boundary-verifier-required')
        require(os.name == 'posix' and os.getpid() == os.getpgrp(),
                'admission-isolated-worker-required')
        require(type(phase_ns) is dict and set(phase_ns) == set(PHASES), 'phase-time-reserves-required')
        require(type(phase_bytes) is dict and set(phase_bytes) == set(PHASES), 'phase-storage-reserves-required')
        self.times = {p: integer(phase_ns[p], 1) for p in PHASES}
        self.space = {p: integer(phase_bytes[p], 1) for p in PHASES}
        self.terminal_ns = integer(terminal_ns, 1)
        self.terminal_bytes = integer(terminal_bytes, 1)
        self.verification_of = None if verification_of is None else pin(verification_of)
        self.verification_work_root = (None if verification_work_root is None
                                       else Path(verification_work_root).resolve(strict=True))
        if self.verification_work_root is not None:
            require(self.verification_of is not None and self.verification_work_root.is_dir()
                    and not self.verification_work_root.is_relative_to(self.root)
                    and not self.root.is_relative_to(self.verification_work_root)
                    and not self.verification_work_root.is_relative_to(self.source_root)
                    and not self.source_root.is_relative_to(self.verification_work_root),
                    'verification-work-root-binding')
        self._clock = clock
        self._origin = clock()
        if self.verification_of:
            self._global_deadline = integer(verification_deadline_ns, 1)
            require(self._origin + self.times['verify'] + self.terminal_ns <= self._global_deadline,
                    'terminal-time-reserve-insufficient')
        else:
            require(verification_deadline_ns is None, 'unexpected-verification-deadline')
            self._global_deadline = self._origin + sum(self.times.values()) + self.terminal_ns
        self.ledger = PhaseLedger(bounds=phase_requests, total=sum(phase_requests.values()),
                                  max_active=max_active)
        self.binding = {'version': 'agent-braid-git-admission-boundary-v2',
                        'workerPid': os.getpid(), 'workerPgid': os.getpgrp(),
                        'scopeNonce': secrets.token_hex(16),
                        'root': str(self.root), 'sourceRoot': str(self.source_root),
                        'sourceDigest': pin(source_digest), 'inputCommits': list(INPUT_COMMITS),
                        'gitExecutable': str(self.git_executable), 'gitSha256': self.git_sha256,
                        'inputPatchSha256': list(INPUT_PATCHES),
                        'baseCommit': '48f4226db1e1b0565b1f8faf0eca81c150a65d30',
                        'mode': mode, 'finalVerifier': final_verifier,
                        'phaseRequests': dict(phase_requests), 'phaseNs': dict(self.times),
                        'phaseBytes': dict(self.space), 'terminalNs': self.terminal_ns,
                        'terminalBytes': self.terminal_bytes, 'maxActive': max_active}
        self.binding['verificationOf'] = self.verification_of
        self.binding['verificationWorkRoot'] = (None if self.verification_work_root is None
                                                 else str(self.verification_work_root))
        self.binding['wholeFlowDeadlineNs'] = self._global_deadline
        self.binding_digest = digest(self.binding)
        self._verify = boundary_verifier
        self._deadline = self._origin
        self._phase = None
        self._stopped = False
        self._processes = {}
        self._records = []
        self._lock = threading.RLock()

    def enter(self, phase):
        with self._lock:
            try:
                require(not self._processes, 'unreaped-admission-children')
                require(not self._stopped, 'admission-worker-stopped')
                if self.verification_of is not None:
                    require(self._phase is None and phase == 'verify', 'verification-worker-only')
                    # Empty local counters describe this verifier worker, not the
                    # previous work. No preparation or grant API is invoked.
                    for skipped in PHASES[:3]:
                        self.ledger.enter(skipped)
                else:
                    require(phase != 'verify', 'independent-verifier-required')
                self.ledger.enter(phase)
                self._phase = phase
                future = sum(self.times[p] for p in PHASES[PHASES.index(phase) + 1:]) + self.terminal_ns
                require(self._clock() < self._global_deadline - future,
                        'terminal-time-reserve-insufficient')
                self._deadline = min(self._clock() + self.times[phase], self._global_deadline - future)
                self.check()
            except BaseException:
                self.stop()
                raise

    def check(self, invocation=None):
        """Reject stale/missing containment/quota before effects and after reads."""
        with self._lock:
            try:
                self._check(invocation)
            except BaseException:
                self.stop()
                raise

    def _check(self, invocation):
        require(self._phase is not None and not self._stopped, 'admission-worker-stopped')
        require(os.getpid() == self.binding['workerPid']
                and os.getpgrp() == self.binding['workerPgid'], 'admission-worker-identity-drift')
        require(self._clock() < self._deadline, 'admission-phase-deadline')
        observed = self._verify(deepcopy(self.binding), self._phase, self._deadline,
                                deepcopy(invocation))
        require(type(observed) is dict and observed.get('bindingDigest') == self.binding_digest,
                'admission-boundary-binding')
        require(all(observed.get(key) is True for key in
                    ('containedProcessTree', 'hardQuota', 'externalWatchdog',
                     'allWriteRootsCovered', 'sourceInputsVerified', 'immutableExecutable')),
                'admission-boundary-unverified')
        require(type(observed.get('watchdogDeadlineNs')) is int
                and observed['watchdogDeadlineNs'] <= self._deadline,
                'admission-external-deadline-unverified')
        require(type(observed.get('phaseQuotaBytes')) is int
                and 0 < observed['phaseQuotaBytes'] <= self.space[self._phase],
                'admission-phase-quota-unverified')
        require(type(observed.get('availableBytes')) is int
                and observed['availableBytes'] >= sum(self.space[p] for p in
                    PHASES[PHASES.index(self._phase):]) + self.terminal_bytes,
                'terminal-storage-reserve-insufficient')
        require(type(observed.get('expiresNs')) is int and
                self._clock() < min(self._deadline, observed['expiresNs'], observed['watchdogDeadlineNs']),
                'admission-boundary-expired')
        require(not self._stopped, 'admission-worker-stopped')
        if self.verification_of is not None:
            require(observed.get('terminatedWorkBindingDigest') == self.verification_of
                    and observed.get('terminatedWorkDeadlineNs') == self._global_deadline
                    and observed.get('priorWorkTerminated') is True,
                    'prior-work-termination-unverified')
        if invocation is not None:
            require(observed.get('launchAllowed') is True
                    and observed.get('launchDigest') == digest(invocation),
                    'admission-invocation-unverified')
            if self.verification_of is not None:
                require(observed.get('readOnlyVerification') is True,
                        'terminal-verifier-effects-unverified')

    def start(self, command, *, input_sha256, **kwargs):
        with self._lock:
            try:
                # Freeze exactly the invocation that the trusted authority sees.
                command = list(command)
                kwargs['env'] = dict(kwargs['env'])
                invocation = {'argv': command, 'env': kwargs['env'], 'cwd': kwargs.get('cwd'),
                              'inputSha256': input_sha256, 'inheritedFds': list(kwargs['pass_fds'])}
                self.check(invocation)
                token = self.ledger.reserve()
            except BaseException:
                self._stopped = True
                raise
            try:
                # Do not create detached Git groups. The independently verified
                # containment must also prevent descendants from escaping it.
                process = subprocess.Popen(command, start_new_session=False, **kwargs)
            except BaseException:
                self.ledger.start_failed(token)
                self._stopped = True
                raise
            self.ledger.launched(token)
            self._processes[token] = process
            self._records.append({'ticket': token, 'phase': self._phase,
                                  'pid': process.pid, 'reaped': False,
                                  'launchDigest': digest(invocation)})
            return token, process

    def reaped(self, token, returncode):
        with self._lock:
            require(token in self._processes and type(returncode) is int, 'unknown-admission-child')
            self.ledger.finished(token)
            del self._processes[token]
            next(r for r in self._records if r['ticket'] == token).update(
                reaped=True, returncode=returncode)

    def stop(self):
        with self._lock:
            self._stopped = True
            # Direct-child cancellation only. External containment owns complete
            # descendant termination; this code never signals child_pid as PGID.
            for process in self._processes.values():
                try:
                    process.kill()
                except OSError:
                    pass

    def receipt(self):
        with self._lock:
            return {'version': 'agent-braid-git-launch-scope-receipt-v1',
                    'bindingDigest': self.binding_digest,
                    'requests': self.ledger.receipt(), 'children': deepcopy(self._records),
                    'stopped': self._stopped, 'unreaped': len(self._processes),
                    'externalCleanupVerified': False, 'actualProfileAdmitted': False,
                    'executionAuthorization': False}


@contextmanager
def admission_launches(scope):
    """Internal trusted-worker activation, never reachable from CLI/MCP payloads."""
    global _active, _retired
    require(type(scope) is GitLaunchScope, 'typed-admission-scope-required')
    require(_activation.acquire(blocking=False), 'admission-already-active')
    try:
        require(not _retired and _active is None, 'admission-worker-retired')
        # Once opted in, this isolated worker can never return to legacy launches.
        _retired = True
        require(threading.active_count() == 1, 'admission-activation-requires-single-thread')
        historical = 'agent_braid.git_integration_prototype'
        require(sys.modules.get(historical) is None
                and getattr(sys.modules['agent_braid'], 'git_integration_prototype', None) is None,
                'historical-prototype-outside-admission')
        # The frozen M2 path is not part of this worker. Block future imports for
        # its lifetime instead of modifying bytes bound by historical approval.
        sys.modules[historical] = None
        scope.check()
        _active = scope
        try:
            yield scope
            scope.check()
        except BaseException:
            scope.stop()
            raise
        finally:
            if scope._processes:
                scope.stop()
            _active = None
    finally:
        _activation.release()


def require_scoped_budget(budget):
    require(not _retired or _active is not None, 'admission-worker-retired')
    if _active is not None:
        require(budget is not None, 'unbudgeted-admission-git')


def run_git(cwd, args, *, env, budget, input_bytes=None, allow_failure=False,
            command_timeout=30.0, poll_interval=0.01):
    if _active is None:
        require(not _retired, 'admission-worker-retired')
        return legacy_run_git(cwd, args, env=env, budget=budget, input_bytes=input_bytes,
                              allow_failure=allow_failure, command_timeout=command_timeout,
                              poll_interval=poll_interval)
    return _run(_active, cwd, args, env, budget, input_bytes, allow_failure,
                command_timeout, poll_interval, ())


def run_owned_git(cwd, args, *, env, budget, input_bytes=None, allow_failure=False,
                  command_timeout=30.0, poll_interval=0.01, ownership_fd=None):
    if _active is None:
        require(not _retired, 'admission-worker-retired')
        return legacy_run_owned_git(cwd, args, env=env, budget=budget, input_bytes=input_bytes,
                                    allow_failure=allow_failure, command_timeout=command_timeout,
                                    poll_interval=poll_interval, ownership_fd=ownership_fd)
    return _run(_active, cwd, args, env, budget, input_bytes, allow_failure,
                command_timeout, poll_interval,
                (ownership_fd,) if ownership_fd is not None else ())


def _run(scope, cwd, args, env, budget, payload, allow_failure, timeout, interval, fds):
    """Versioned POSIX selector runner: bounded I/O and bounded reaping."""
    token = process = None
    selector = selectors.DefaultSelector()
    outputs = {'stdout': bytearray(), 'stderr': bytearray()}
    try:
        require(os.name == 'posix', 'admission-posix-required')
        cwd = Path(cwd).resolve(strict=True)
        require(cwd == scope.source_root or cwd.is_relative_to(scope.root)
                or scope.verification_work_root is not None
                and cwd.is_relative_to(scope.verification_work_root),
                'admission-cwd-outside-binding')
        root = Path(budget.temp_root).resolve(strict=True)
        require(root.is_relative_to(scope.root), 'admission-scratch-outside-quota')
        require(type(env) is dict and not set(env).intersection({
            'GIT_DIR', 'GIT_WORK_TREE', 'GIT_COMMON_DIR', 'GIT_OBJECT_DIRECTORY',
            'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_CONFIG_PARAMETERS', 'GIT_EXEC_PATH'}),
            'admission-environment-redirect')
        require(env.get('GIT_CONFIG_GLOBAL') == os.devnull and env.get('GIT_CONFIG_NOSYSTEM') == '1'
                and env.get('GIT_ALLOW_PROTOCOL') == 'file'
                and env.get('GIT_TERMINAL_PROMPT') == '0'
                and env.get('GIT_CONFIG_COUNT', '0') == '0', 'admission-unsanitized-environment')
        for key in ('HOME', 'TMPDIR', 'GIT_INDEX_FILE'):
            if key != 'GIT_INDEX_FILE' or key in env:
                require(type(env.get(key)) is str and Path(env[key]).is_absolute()
                        and Path(env[key]).resolve().is_relative_to(scope.root),
                        'admission-environment-outside-quota')
        require(scope.git_executable.is_file() and scope.git_executable.stat().st_size <= 32*1024*1024,
                'admission-git-pin-required')
        require(hashlib.sha256(scope.git_executable.read_bytes()).hexdigest() == scope.git_sha256,
                'admission-git-pin-drift')
        require(budget.max_process_address_space_bytes is None,
                'admission-address-space-wrapper-not-supported')
        timeout = budget.begin_command(timeout)
        deadline = min(scope._clock() + int(timeout * 10**9), scope._deadline)
        token, process = scope.start([str(scope.git_executable), '-C', str(cwd), *args],
            input_sha256=hashlib.sha256(payload).hexdigest() if payload is not None else None,
            cwd=None, env=env,
            stdin=subprocess.PIPE if payload is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, pass_fds=fds)
        for name, stream in [('stdout', process.stdout), ('stderr', process.stderr)]:
            os.set_blocking(stream.fileno(), False)
            selector.register(stream, selectors.EVENT_READ, name)
        written = 0
        if process.stdin is not None:
            os.set_blocking(process.stdin.fileno(), False)
            if payload:
                selector.register(process.stdin, selectors.EVENT_WRITE, 'stdin')
            else:
                process.stdin.close()
        while selector.get_map() or process.poll() is None:
            scope.check()
            require(scope._clock() < deadline, 'admission-command-deadline')
            require(not (budget.cancel_event and budget.cancel_event.is_set()), 'admission-cancelled')
            require(not budget.scratch_exceeds_limit(), 'admission-stage-scratch-limit')
            for key, _ in selector.select(min(interval, 0.05)):
                stream, name = key.fileobj, key.data
                try:
                    if name == 'stdin':
                        written += os.write(stream.fileno(), payload[written:written + 65536])
                        if written == len(payload):
                            selector.unregister(stream)
                            stream.close()
                        continue
                    data = os.read(stream.fileno(), 65536)
                except BlockingIOError:
                    continue
                except BrokenPipeError:
                    selector.unregister(stream)
                    stream.close()
                    continue
                if not data:
                    selector.unregister(stream)
                    stream.close()
                    continue
                require(sum(map(len, outputs.values())) + len(data) <= budget.max_command_output_bytes
                        and budget.record_output(len(data)), 'admission-output-limit')
                outputs[name].extend(data)
        result = process.wait(timeout=0.2)
        scope.reaped(token, result)
        token = None
        scope.check()
        budget._sample_child_usage()
        if result and not allow_failure:
            raise GitCommandFailure(args[0] if args else 'unknown Git command')
        return GitCommandResult(bytes(outputs['stdout']), bytes(outputs['stderr']), result)
    except BaseException:
        scope.stop()
        raise
    finally:
        selector.close()
        if process is not None:
            if token is not None:
                try:
                    result = process.wait(timeout=0.2)
                    scope.reaped(token, result)
                except subprocess.TimeoutExpired:
                    pass  # Explicitly retained as unreaped; outer supervisor owns it.
            for stream in (process.stdin, process.stdout, process.stderr):
                if stream is not None:
                    stream.close()
