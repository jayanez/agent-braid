# SPDX-License-Identifier: AGPL-3.0-only
"""Source-bound admission accounting, without a native execution entrypoint.

The ledger reserves requests for a future isolated launcher. Caller-reported
lifecycle events do not prove that every native launch was intercepted. Neither
the source envelope nor a healthy ledger admits a profile or authorizes work.
"""
from copy import deepcopy
import hashlib
from pathlib import Path
import re
from threading import Lock

from .forecast_data import digest, integer, pin, require

PHASES = ('prepare', 'grant', 'dispatch', 'verify')
SOURCE_FILES = (
    'agent_braid/forecast_admission.py', 'agent_braid/forecast_data.py',
    'agent_braid/forecast_git_launch.py',
    'agent_braid/forecast_linux_profile.py', 'agent_braid/forecast_operator_bridge.py',
    'agent_braid/forecast_native.py', 'agent_braid/forecast_recipe.py',
    'agent_braid/forecast_exec_census.py', 'agent_braid/forecast_exec_gate.py',
    'agent_braid/forecast_launcher.py', 'agent_braid/forecast_bootstrap.py',
    'agent_braid/forecast_manager.py', 'agent_braid/forecast_supervisor.py',
    'agent_braid/forecast_build.py', 'research/native/fc1_manager_bridge.c',
    'agent_braid/forecast_bundle_auth.py', 'agent_braid/forecast_linux_artifacts.py',
    'agent_braid/forecast_admission_worker.py', 'scripts/fc1_admission_worker.py',
    'agent_braid/runtime_policy.py', 'agent_braid/git_runtime.py',
    'agent_braid/runtime_scheduler.py', 'agent_braid/git_replay.py',
    'agent_braid/git_adapter.py', 'agent_braid/git_process.py',
    'agent_braid/git_runtime_process.py', 'agent_braid/git_exec.py',
    'agent_braid/git_partial_order.py', 'agent_braid/git_integration_prototype.py',
    'agent_braid/utility_budget_observer.py', 'agent_braid/analysis.py',
    'research/lab/model.py', 'research/native/fc1_exec_census.bpf.c',
    'agent_braid/forecast_exec_budget.py', 'agent_braid/forecast_mounts.py',
    'agent_braid/forecast_systemd_patch.py', 'research/native/fc1_systemd_gate.c',
    'research/native/fc1_systemd_gate.h', 'research/native/fc1_systemd_policy.h',
    'research/native/fc1-systemd-2613.patch',
    'agent_braid/forecast_host_census.py', 'agent_braid/forecast_manager_escrow.py',
    'agent_braid/forecast_v9_driver.py', 'agent_braid/forecast_v9_renderer.py',
)
# Fixed reviewed-source model: changing source requires a fresh accounting review,
# not regenerating an arbitrary hash and treating it as accepted coverage.
_MODELED_SOURCE = 'b2251aa6d1be57eef361d25121eac726ed4be23364588158897691318a1a71d0'


def source_digest(root, *, reader=None):
    """Hash only named repository sources; never inspect workload or host state."""
    root = Path(root)
    hashes = {}
    for name in SOURCE_FILES:
        raw = (root / name).read_bytes() if reader is None else reader(root / name)
        if name == 'agent_braid/forecast_admission.py':
            # Normalize only the one model-pin assignment to break its hash cycle.
            # The ledger, inventory and normalization algorithm remain hashed.
            raw, count = re.subn(rb"(?m)^_MODELED_SOURCE = '[0-9a-f]{64}'$",
                                b"_MODELED_SOURCE = '<normalized-model-pin>'", raw)
            require(count == 1, 'admission-model-pin-format')
        hashes[name] = hashlib.sha256(raw).hexdigest()
    return digest(hashes)


def source_envelope(root, *, mode, final_verifier, expected_source_digest=None):
    """Return cap sums for the exact API route, not a measured minimum/deadline.

    Rows count replay budgets (512 requests/120s), runtime budgets (256/60s),
    and exact single-command common-directory probes (1 request/30s process
    timeout). Python work, teardown and storage outside those roots are unbounded
    by these sums. No runtime module is imported or invoked here.
    """
    require(mode in ('serial', 'parallel'), 'unsupported-admission-mode')
    require(final_verifier in ('runtime', 'policy'), 'unsupported-final-verifier')
    actual = source_digest(root)
    require(actual == _MODELED_SOURCE, 'admission-source-drift')
    if expected_source_digest is not None:
        require(actual == pin(expected_source_digest), 'admission-source-drift')
    # Tuples: replay budgets, runtime budgets, exact single-command probes.
    rows = ([(3, 1, 1), (1, 1, 1), (1, 2, 1)] if mode == 'serial'
            else [(3, 2, 1), (1, 2, 1), (1, 6, 2)])
    final = ((0, 1, 0) if final_verifier == 'runtime'
             else (1, 2, 1) if mode == 'serial' else (1, 4, 2))
    phases = []
    for name, (replay, runtime, probes) in zip(PHASES, [*rows, final], strict=True):
        phases.append({'phase': name, 'replayBudgets': replay,
                       'runtimeBudgets': runtime, 'singleCommandProbes': probes,
                       'gitRequests': 512 * replay + 256 * runtime + probes,
                       'internalCapSumSeconds': 120 * replay + 60 * runtime + 30 * probes})
    return {'version': 'agent-braid-admission-source-envelope-v1',
            'sourceDigest': actual, 'mode': mode, 'finalVerifier': final_verifier,
            'phases': phases, 'gitRequests': sum(r['gitRequests'] for r in phases),
            'internalCapSumSeconds': sum(r['internalCapSumSeconds'] for r in phases),
            'minimumMeasuredGitRequests': None, 'wholeFlowWallUpperBoundNs': None,
            'blockers': ['input-specific-bounds-not-established',
                         'native-launch-coverage-not-established',
                         'non-git-deadline-and-terminal-reserve-not-established',
                         'aggregate-retained-storage-bound-not-established'],
            'executionAuthorization': False, 'actualProfileAdmitted': False,
            'limits': ['Source-cap arithmetic, not actual native counts or cost.',
                       'Per-budget scratch is sampled, not a hard whole-flow disk quota.',
                       'CPU/RSS observations are not host enforcement.',
                       'The existing budget observer swallows callback exceptions.']}


class PhaseLedger:
    """Thread-safe request reservations; no subprocesses, hooks, grants or retries.

    A trusted launcher would reserve before Popen, then acknowledge started,
    failed-start and finished states. The future supervisor must establish native
    coverage independently; this class never claims it. Reservations already
    consume concurrency, preventing two workers racing past the same limit.
    """
    def __init__(self, *, bounds, total, max_active):
        require(type(bounds) is dict and set(bounds) == set(PHASES), 'phase-bounds-required')
        checked = {p: integer(bounds[p], 1) for p in PHASES}
        integer(total, 1)
        integer(max_active, 1, 2)
        require(sum(checked.values()) <= total, 'whole-flow-budget-insufficient')
        self._bounds = checked
        self._total = total
        self._max_active = max_active
        self._lock = Lock()
        self._phase_index = -1
        self._tickets = {}
        self._outstanding = 0
        self._peak = 0
        self._healthy = True
        self._counts = {p: dict(attempted=0, accepted=0, launched=0,
                               finished=0, startFailed=0, denied=0) for p in PHASES}

    def enter(self, phase):
        with self._lock:
            require(self._outstanding == 0, 'outstanding-reservations')
            if not self._healthy:
                # Failure can skip remaining work to inspect retained state only.
                # The future driver must bind this phase to its trusted verifier.
                require(phase == 'verify' and self._phase_index < 3, 'admission-stopped')
                self._phase_index = 3
            else:
                require(self._phase_index + 1 < len(PHASES)
                        and phase == PHASES[self._phase_index + 1], 'invalid-phase-order')
                self._phase_index += 1

    def reserve(self):
        with self._lock:
            require(self._phase_index >= 0, 'phase-required')
            phase = PHASES[self._phase_index]
            counts = self._counts[phase]
            counts['attempted'] += 1
            reason = None
            if (not self._healthy and phase != 'verify'
                    or phase == 'verify' and (counts['denied'] or counts['startFailed'])):
                reason = 'admission-stopped'
            elif counts['accepted'] >= self._bounds[phase]:
                reason = 'phase-budget-exhausted'
            elif self._outstanding >= self._max_active:
                reason = 'concurrent-request-limit'
            if reason is not None:
                counts['denied'] += 1
                self._healthy = False
                require(False, reason)
            counts['accepted'] += 1
            self._outstanding += 1
            self._peak = max(self._peak, self._outstanding)
            token = len(self._tickets) + 1
            self._tickets[token] = (phase, 'reserved')
            return token

    def _transition(self, token, before, after, counter, *, release):
        integer(token, 1)
        with self._lock:
            require(token in self._tickets and self._tickets[token][1] == before,
                    'invalid-request-lifecycle')
            phase, _ = self._tickets[token]
            self._tickets[token] = (phase, after)
            self._counts[phase][counter] += 1
            if release:
                self._outstanding -= 1
            if after == 'start-failed':
                self._healthy = False

    def launched(self, token):
        self._transition(token, 'reserved', 'launched', 'launched', release=False)

    def start_failed(self, token):
        self._transition(token, 'reserved', 'start-failed', 'startFailed', release=True)

    def finished(self, token):
        self._transition(token, 'launched', 'finished', 'finished', release=True)

    def receipt(self):
        with self._lock:
            return {'version': 'agent-braid-admission-request-ledger-v1',
                    'phaseBounds': dict(self._bounds), 'totalLimit': self._total,
                    'maxOutstandingReservations': self._max_active,
                    'phases': deepcopy(self._counts),
                    'outstandingReservations': self._outstanding,
                    'peakOutstandingReservations': self._peak,
                    'accountingHealthy': self._healthy,
                    'nativeObservation': False, 'cleanupConfirmed': False,
                    'executionAuthorization': False}
