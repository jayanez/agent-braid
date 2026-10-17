# SPDX-License-Identifier: AGPL-3.0-only
"""Launch-boundary control tests; fake processes only, no admission execution."""
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import hashlib
import sys
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import MagicMock, patch
import agent_braid

from agent_braid import forecast_git_launch as launch
from agent_braid.forecast_data import ForecastError, digest


class FakeSelector:
    def __init__(self):
        self.streams = {}
    def register(self, stream, _event, name):
        self.streams[stream] = name
    def unregister(self, stream):
        del self.streams[stream]
    def get_map(self):
        return self.streams
    def select(self, _timeout):
        return [(SimpleNamespace(fileobj=s, data=n), 1) for s, n in list(self.streams.items())]
    def close(self):
        self.streams.clear()


class GitLaunchBoundaryTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name)
        self.work = self.root / 'work'
        self.source = self.root / 'source'
        self.work.mkdir(); self.source.mkdir()
        self.git_executable = self.root / 'git'
        self.git_executable.write_bytes(b'owned executable pin, never executed')
        self.now = 0
        self.observation = {}
        self.addCleanup(patch.stopall)
        patch.object(launch, '_active', None).start()
        patch.object(launch, '_retired', False).start()
        patch.dict(sys.modules, {'agent_braid.git_integration_prototype': None}).start()
        patch.object(agent_braid, 'git_integration_prototype', None, create=True).start()
        patch.object(launch.os, 'getpid', return_value=100).start()
        patch.object(launch.os, 'getpgrp', return_value=100).start()
        patch.object(launch.threading, 'active_count', return_value=1).start()
        self.spawn = patch.object(launch.subprocess, 'Popen').start()
        self.process = MagicMock(pid=123)
        self.process.stdin = None
        self.process.poll.return_value = 0
        self.process.wait.return_value = 0
        self.spawn.return_value = self.process
        patch.object(launch.selectors, 'DefaultSelector', FakeSelector).start()
        patch.object(launch.os, 'set_blocking').start()
        self.read = patch.object(launch.os, 'read', return_value=b'').start()
        self.legacy = patch.object(launch, 'legacy_run_git', side_effect=AssertionError('legacy bypass')).start()
        self.owned = patch.object(launch, 'legacy_run_owned_git', side_effect=AssertionError('legacy bypass')).start()

    def verifier(self, binding, phase, deadline, invocation=None):
        value = dict(bindingDigest=digest(binding), containedProcessTree=True,
                    hardQuota=True, externalWatchdog=True, allWriteRootsCovered=True,
                    sourceInputsVerified=True,
                    immutableExecutable=True,
                    availableBytes=1000, phaseQuotaBytes=binding['phaseBytes'][phase],
                    watchdogDeadlineNs=deadline, expiresNs=10**12, **self.observation)
        if invocation is not None:
            value.update(launchAllowed=True, launchDigest=digest(invocation))
        return value

    def scope(self, **changes):
        config = dict(root=self.work, source_root=self.source, source_digest='a'*64,
                      git_executable=self.git_executable,
                      git_sha256=hashlib.sha256(self.git_executable.read_bytes()).hexdigest(),
                      mode='parallel', final_verifier='policy',
                      phase_requests={p:2 for p in launch.PHASES},
                      phase_ns={p:100 for p in launch.PHASES},
                      phase_bytes={p:10 for p in launch.PHASES},
                      terminal_ns=20, terminal_bytes=4,
                      max_active=2, boundary_verifier=self.verifier, clock=lambda:self.now)
        config.update(changes)
        return launch.GitLaunchScope(**config)

    def budget(self):
        budget = MagicMock(temp_root=self.work, max_process_address_space_bytes=None,
                           cancel_event=None, max_command_output_bytes=8)
        budget.begin_command.return_value = 30
        budget.scratch_exceeds_limit.return_value = False
        budget.record_output.return_value = True
        return budget

    def git(self, owned=False, budget=None):
        from agent_braid.git_replay import _sanitized_environment
        fn = launch.run_owned_git if owned else launch.run_git
        return fn(self.source, ('status',), env=_sanitized_environment(self.work/'home'),
                  budget=budget or self.budget())

    def test_both_routes_reserve_before_spawn_and_inherit_containment(self):
        scope = self.scope(); scope.enter('prepare')
        def spawning(*args, **kwargs):
            counts = scope.receipt()['requests']['phases']['prepare']
            self.assertGreater(counts['accepted'], counts['launched'])
            self.assertIs(kwargs['start_new_session'], False)
            return self.process
        self.spawn.side_effect = spawning
        with launch.admission_launches(scope):
            self.git(); self.git(owned=True)
        counts = scope.receipt()['requests']['phases']['prepare']
        self.assertEqual((2,2,2,2), tuple(counts[k] for k in ('attempted','accepted','launched','finished')))
        self.assertFalse(scope.receipt()['externalCleanupVerified'])
        self.legacy.assert_not_called(); self.owned.assert_not_called()

    def test_no_post_scope_fallback_or_reactivation(self):
        scope = self.scope(); scope.enter('prepare')
        with launch.admission_launches(scope):
            self.git()
        with self.assertRaisesRegex(ForecastError, 'retired'):
            self.git()
        with self.assertRaisesRegex(ForecastError, 'retired'):
            with launch.admission_launches(scope):
                pass
        self.assertEqual(1, self.spawn.call_count)

    def test_adapter_rejects_unbudgeted_route_before_subprocess_run(self):
        from agent_braid import git_adapter
        scope = self.scope(); scope.enter('prepare')
        with patch.object(git_adapter.subprocess, 'run', side_effect=AssertionError('unbudgeted Git')):
            with self.assertRaisesRegex(ForecastError, 'unbudgeted'):
                with launch.admission_launches(scope):
                    git_adapter._git_result(self.source, 'status')
        self.spawn.assert_not_called()

    def test_three_consumers_use_the_same_launch_boundary(self):
        from agent_braid import git_adapter, git_replay, git_runtime
        self.assertIs(git_adapter.run_git, launch.run_git)
        self.assertIs(git_replay.run_git, launch.run_git)
        self.assertIs(git_runtime.run_owned_git, launch.run_owned_git)

    def test_missing_or_expired_capabilities_refuse_before_spawn(self):
        for field, bad in [('hardQuota',False),('containedProcessTree',False),
                           ('externalWatchdog',False),('allWriteRootsCovered',False),
                           ('sourceInputsVerified',False),
                           ('immutableExecutable',False),
                           ('bindingDigest','0'*64),('expiresNs',0),
                           ('watchdogDeadlineNs',101),('availableBytes',43),
                           ('watchdogDeadlineNs',0),('phaseQuotaBytes',11),
                           ('phaseQuotaBytes',0)]:
            with self.subTest(field=field):
                scope = self.scope()
                old = self.verifier
                def verify(binding, phase, deadline, invocation=None):
                    value=old(binding,phase,deadline,invocation); value[field]=bad; return value
                scope._verify=verify
                with self.assertRaises(ForecastError):
                    scope.enter('prepare')
        self.spawn.assert_not_called()

    def test_phase_and_terminal_reserves_cannot_be_borrowed(self):
        scope = self.scope(); scope.enter('prepare')
        self.now = 100
        with self.assertRaisesRegex(ForecastError,'deadline'):
            scope.check()
        self.now = 0
        scope = self.scope(); scope.enter('prepare')
        self.now = 321
        with self.assertRaisesRegex(ForecastError,'terminal-time'):
            scope.enter('grant')
        self.spawn.assert_not_called()

    def test_spawn_failure_is_not_a_launch_and_stops_worker(self):
        scope = self.scope(); scope.enter('prepare')
        self.spawn.side_effect = OSError('spawn denied')
        with self.assertRaises(OSError):
            with launch.admission_launches(scope):
                self.git()
        counts=scope.receipt()['requests']['phases']['prepare']
        self.assertEqual((1,0,1), tuple(counts[k] for k in ('accepted','launched','startFailed')))
        self.assertTrue(scope.receipt()['stopped'])

    def test_output_failure_kills_direct_child_and_never_killpg_child_pid(self):
        scope = self.scope(); scope.enter('prepare')
        self.read.return_value = b'x'*9
        with patch.object(launch.os, 'killpg', side_effect=AssertionError('wrong PGID')):
            with self.assertRaisesRegex(ForecastError,'output-limit'):
                with launch.admission_launches(scope):
                    self.git()
        self.process.kill.assert_called()
        self.assertEqual(0,scope.receipt()['unreaped'])
        self.assertFalse(scope.receipt()['externalCleanupVerified'])

    def test_unreapable_child_remains_unknown_in_receipt(self):
        scope = self.scope(); scope.enter('prepare')
        self.read.return_value = b'x'*9
        self.process.wait.side_effect = launch.subprocess.TimeoutExpired('git',0.2)
        with self.assertRaisesRegex(ForecastError,'output-limit'):
            with launch.admission_launches(scope):
                self.git()
        self.assertEqual(1,scope.receipt()['unreaped'])
        self.assertFalse(scope.receipt()['children'][0]['reaped'])

    def test_worker_threads_share_scope_and_request_reservations(self):
        scope = self.scope(); scope.enter('prepare')
        with launch.admission_launches(scope):
            with ThreadPoolExecutor(max_workers=2) as pool:
                list(pool.map(lambda _: self.git(), range(2)))
        self.assertEqual(2,self.spawn.call_count)
        self.assertEqual(2,scope.receipt()['requests']['phases']['prepare']['finished'])

    def test_quota_root_violation_and_limit_exhaustion_cannot_spawn(self):
        scope = self.scope(); scope.enter('prepare')
        budget=self.budget(); budget.temp_root=self.source
        with self.assertRaisesRegex(ForecastError,'outside-quota'):
            with launch.admission_launches(scope):
                self.git(budget=budget)
        self.spawn.assert_not_called()

    def test_unscoped_routes_preserve_legacy_arguments(self):
        self.legacy.side_effect=None; self.owned.side_effect=None
        self.git(); self.git(owned=True)
        self.legacy.assert_called_once(); self.owned.assert_called_once()
        self.spawn.assert_not_called()

    def test_serial_cannot_claim_two_active_git_children(self):
        with self.assertRaisesRegex(ForecastError,'serial-admission-concurrency'):
            self.scope(mode='serial')

    def test_historical_prototype_cannot_enter_or_be_imported_by_worker(self):
        scope=self.scope(); scope.enter('prepare')
        with patch.dict(sys.modules, {'agent_braid.git_integration_prototype': object()}):
            with self.assertRaisesRegex(ForecastError,'historical-prototype-outside'):
                with launch.admission_launches(scope):
                    pass
        self.spawn.assert_not_called()
        launch._retired=False
        scope=self.scope(); scope.enter('prepare')
        with launch.admission_launches(scope):
            with self.assertRaises(ModuleNotFoundError):
                __import__('agent_braid.git_integration_prototype')

    def test_activation_rejects_concurrent_importer_threads(self):
        scope=self.scope(); scope.enter('prepare')
        with patch.object(launch.threading,'active_count',return_value=2):
            with self.assertRaisesRegex(ForecastError,'requires-single-thread'):
                with launch.admission_launches(scope):
                    pass
        self.spawn.assert_not_called()

    def test_concrete_invocation_requires_operator_approval(self):
        scope = self.scope(); scope.enter('prepare')
        original = self.verifier
        def verify(binding, phase, deadline, invocation=None):
            value = original(binding, phase, deadline, invocation)
            if invocation is not None:
                self.assertEqual(str(self.git_executable.resolve()), invocation['argv'][0])
                self.assertEqual(str(self.source.resolve()), invocation['argv'][2])
                value['launchDigest'] = 'b'*64
            return value
        scope._verify = verify
        with self.assertRaisesRegex(ForecastError,'invocation-unverified'):
            with launch.admission_launches(scope):
                self.git()
        self.spawn.assert_not_called()

    def test_binary_drift_refuses_before_spawn(self):
        scope = self.scope(); scope.enter('prepare')
        self.git_executable.write_bytes(b'changed')
        with self.assertRaisesRegex(ForecastError,'pin-drift'):
            with launch.admission_launches(scope):
                self.git()
        self.spawn.assert_not_called()

    def test_environment_redirect_outside_quota_refuses_before_spawn(self):
        from agent_braid.git_replay import _sanitized_environment
        scope = self.scope(); scope.enter('prepare')
        env = _sanitized_environment(self.work/'home')
        env['GIT_INDEX_FILE'] = str(self.source/'index')
        with self.assertRaisesRegex(ForecastError,'environment-outside-quota'):
            with launch.admission_launches(scope):
                launch.run_git(self.source, ('status',), env=env, budget=self.budget())
        self.spawn.assert_not_called()

    def test_exhaustion_never_launches_an_extra_child(self):
        scope = self.scope(phase_requests={p:1 for p in launch.PHASES}); scope.enter('prepare')
        with self.assertRaisesRegex(ForecastError,'phase-budget-exhausted'):
            with launch.admission_launches(scope):
                self.git(); self.git()
        self.assertEqual(1,self.spawn.call_count)
        counts=scope.receipt()['requests']['phases']['prepare']
        self.assertEqual((2,1,1),tuple(counts[k] for k in ('attempted','launched','denied')))

    def test_independent_verifier_requires_terminated_work_and_readonly_launch(self):
        scope = self.scope(verification_of='c'*64, verification_deadline_ns=420)
        with self.assertRaisesRegex(ForecastError,'prior-work-termination'):
            scope.enter('verify')
        scope = self.scope(verification_of='c'*64, verification_deadline_ns=420)
        original = self.verifier
        def verify(binding,phase,deadline,invocation=None):
            value=original(binding,phase,deadline,invocation)
            value.update(priorWorkTerminated=True,terminatedWorkBindingDigest='c'*64,
                         terminatedWorkDeadlineNs=420)
            return value
        scope._verify=verify; scope.enter('verify')
        with self.assertRaisesRegex(ForecastError,'verifier-effects'):
            with launch.admission_launches(scope):
                self.git()
        self.spawn.assert_not_called()

    def test_verifier_cannot_extend_original_whole_flow_deadline(self):
        self.now=301
        with self.assertRaisesRegex(ForecastError,'terminal-time-reserve'):
            self.scope(verification_of='c'*64,verification_deadline_ns=420)
        self.now=0
        scope=self.scope(); scope.enter('prepare'); scope.enter('grant'); scope.enter('dispatch')
        with self.assertRaisesRegex(ForecastError,'independent-verifier-required'):
            scope.enter('verify')

    def test_separate_verifier_retains_original_readonly_run_path(self):
        retained=self.root/'retained'
        retained.mkdir()
        self.observation.update(priorWorkTerminated=True,
            terminatedWorkBindingDigest='c'*64,terminatedWorkDeadlineNs=420,
            readOnlyVerification=True)
        scope=self.scope(verification_of='c'*64,verification_deadline_ns=420,
                         verification_work_root=retained)
        scope.enter('verify')
        from agent_braid.git_replay import _sanitized_environment
        with launch.admission_launches(scope):
            launch.run_git(retained,('status',),env=_sanitized_environment(self.work/'home'),
                           budget=self.budget())
        self.assertEqual(scope.binding['verificationWorkRoot'],str(retained.resolve()))
        self.assertEqual(scope.binding['version'],'agent-braid-git-admission-boundary-v2')
        self.spawn.assert_called_once()

    def test_work_worker_cannot_add_a_verification_root(self):
        retained=self.root/'retained'
        retained.mkdir()
        with self.assertRaisesRegex(ForecastError,'verification-work-root-binding'):
            self.scope(verification_work_root=retained)
        self.spawn.assert_not_called()
