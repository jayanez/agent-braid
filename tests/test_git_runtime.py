# SPDX-License-Identifier: AGPL-3.0-only
"""Real Git and process interruption controls for the first private runtime."""
from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

from agent_braid import git_runtime as runtime
from jsonschema import Draft202012Validator

from agent_braid.git_process import GitExecutionCancelled, GitCommandLimitExceeded

ROOT = Path(__file__).resolve().parents[1]


class GitRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.repo = self.root / 'source'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.name', 'Runtime tests')
        self.git('config', 'user.email', 'tests@example.invalid')
        for path in ['a.txt', 'b.txt']:
            (self.repo / path).write_text('base\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        self.base_tree = self.git('rev-parse', 'HEAD^{tree}')
        commits = []
        for identifier, filename in [('a', 'a.txt'), ('b', 'b.txt')]:
            self.git('checkout', '-q', '-b', identifier, self.base)
            (self.repo / filename).write_text(identifier + '\n')
            self.git('add', filename)
            self.git('commit', '-qm', identifier)
            commits.append(self.git('rev-parse', 'HEAD'))
        self.git('checkout', '-q', 'main')
        for identifier in ['a', 'b']:
            (self.repo / (identifier + '.txt')).write_text(identifier + '\n')
        self.git('add', '.')
        expected = self.git('write-tree')
        self.git('reset', '--hard', '-q', self.base)
        self.request = {'gitRuntimeRequestVersion': runtime.VERSION,
                        'repository': str(self.repo), 'baseRevision': self.base,
                        'expectedFinalTree': expected, 'order': ['a', 'b'],
                        'operations': [
                            {'instanceId': i, 'attemptId': i + '-attempt',
                             'source': {'kind': 'commit', 'revision': c},
                             'dependencies': [], 'uncertainPaths': [],
                             'declaredWrites': [i + '.txt']}
                            for i, c in zip(['a', 'b'], commits)]}
        self.dest = self.root / 'run'
        self.before = self.snapshot(self.repo)

    def git(self, *args, repo=None):
        env = os.environ.copy()
        env['GIT_CONFIG_NOSYSTEM'] = '1'
        env['GIT_CONFIG_GLOBAL'] = os.devnull
        p = subprocess.run(['git', '-C', str(repo or self.repo), *args],
                           env=env, capture_output=True, check=True)
        return p.stdout.decode().strip()

    def snapshot(self, directory):
        return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in directory.rglob('*') if p.is_file() and not p.is_symlink()}

    def execute(self):
        manifest = runtime.prepare_run(self.request, self.dest)
        report = runtime.execute_run(self.request, self.dest, manifest['manifestDigest'])
        return manifest, report

    def test_prepare_is_read_only(self):
        manifest = runtime.prepare_run(self.request, self.dest)
        self.assertEqual(manifest, runtime.prepare_run(self.request, self.dest))
        self.assertFalse(self.dest.exists())
        self.assertEqual(self.snapshot(self.repo), self.before)
        self.assertEqual([s['operationId'] for s in manifest['steps']], ['a', 'b'])
        self.assertEqual(manifest['steps'][-1]['outputTree'], self.request['expectedFinalTree'])
        self.assertEqual(manifest['steps'][1]['parentCommit'], manifest['steps'][0]['commit'])
        self.assertFalse(manifest['sourcePromotion'])

    def test_invalid_inputs(self):
        variants = []
        for mutate in [
            lambda r: r.update(baseRevision='main'),
            lambda r: r.update(expectedFinalTree=self.base_tree),
            lambda r: r.update(order=['b', 'a', 'a']),
            lambda r: r['operations'][0].update(uncertainPaths=['a.txt']),
            lambda r: r['operations'][0].update(declaredWrites=['b.txt']),
            lambda r: r['operations'][0].update(declaredWrites=['../escape']),
            lambda r: r['operations'][0].update(dependencies=['absent']),
            lambda r: r['operations'][0]['source'].update(revision='a'),
            lambda r: r['operations'][0].update(dependencies=['a']),
            lambda r: r['operations'][0].update(extra=True),
        ]:
            req = deepcopy(self.request)
            mutate(req)
            variants.append(req)
        for req in variants:
            with self.subTest(req=req), self.assertRaises(ValueError):
                runtime.prepare_run(req, self.dest)
            self.assertFalse(self.dest.exists())
        for kind in ['binary', 'symlink', 'delete', 'conflict']:
            self.git('checkout', '-q', '-B', 'unsupported', self.base)
            path = self.repo / 'a.txt'
            if kind == 'binary':
                path.write_bytes(b'\0binary')
            elif kind == 'symlink':
                path.unlink()
                path.symlink_to('/tmp/no-runtime-target')
            elif kind == 'delete':
                path.unlink()
            else:
                path.write_text('conflicting\n')
            self.git('add', '-A')
            self.git('commit', '-qm', kind)
            req = deepcopy(self.request)
            commit = self.git('rev-parse', 'HEAD')
            if kind == 'conflict':
                req['operations'][1].update(source={'kind': 'commit', 'revision': commit},
                                            declaredWrites=['a.txt'])
            else:
                req['operations'][0]['source']['revision'] = commit
            with self.subTest(kind=kind), self.assertRaises(ValueError):
                runtime.prepare_run(req, self.dest)
        self.assertFalse(self.dest.exists())

    def test_authorization_and_destination(self):
        manifest = runtime.prepare_run(self.request, self.dest)
        for digest in ['', 'sha256:' + '0' * 64]:
            with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'authorization'):
                runtime.execute_run(self.request, self.dest, digest)
            self.assertFalse(self.dest.exists())
        other = self.root / 'other-run'
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'authorization'):
            runtime.execute_run(self.request, other, manifest['manifestDigest'])
        for dest in [self.repo / 'new-run', self.repo / '.git' / 'new-run']:
            with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'inside source'):
                runtime.prepare_run(self.request, dest)
        req = deepcopy(self.request)
        req['operations'][1]['dependencies'] = ['a']
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'authorization'):
            runtime.execute_run(req, self.dest, manifest['manifestDigest'])
        req['order'] = ['b', 'a']
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'order'):
            runtime.prepare_run(req, self.dest)
        self.dest.symlink_to(self.repo, target_is_directory=True)
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'destination'):
            runtime.execute_run(self.request, self.dest, manifest['manifestDigest'])
        self.dest.unlink()
        self.dest.mkdir()
        (self.dest / 'keep').write_text('owned by somebody else')
        with self.assertRaises(FileExistsError):
            runtime.execute_run(self.request, self.dest, manifest['manifestDigest'])
        self.assertEqual((self.dest / 'keep').read_text(), 'owned by somebody else')

    def test_execute_and_verify(self):
        marker = self.root / 'hook-fired'
        for name in ['post-commit', 'pre-commit', 'post-checkout', 'reference-transaction']:
            hook = self.repo / '.git/hooks' / name
            hook.write_text('#!/bin/sh\ntouch ' + str(marker) + '\n')
            hook.chmod(0o755)
        self.git('config', 'diff.external', 'touch ' + str(marker))
        self.before = self.snapshot(self.repo)
        manifest, report = self.execute()
        self.assertEqual(report['status'], 'completed')
        self.assertEqual(report['completedOperations'], ['a', 'b'])
        self.assertEqual(self.git('rev-parse', runtime.RESULT_REF + '^{tree}', repo=self.dest / 'result.git'),
                         self.request['expectedFinalTree'])
        self.assertEqual(self.git('show', runtime.RESULT_REF + ':a.txt', repo=self.dest / 'result.git'), 'a')
        self.assertEqual(self.git('show', runtime.RESULT_REF + ':b.txt', repo=self.dest / 'result.git'), 'b')
        self.assertFalse(marker.exists())
        self.assertEqual(self.snapshot(self.repo), self.before)
        before = self.snapshot(self.dest)
        verified = runtime.verify_run(self.request, self.dest)
        self.assertEqual(verified['status'], 'verified-completed')
        self.assertEqual(self.snapshot(self.dest), before)
        self.assertEqual(runtime.recover_run(self.request, self.dest, manifest['manifestDigest'])['resultCommit'],
                         report['resultCommit'])
        aborted = runtime.recover_run(self.request, self.dest, manifest['manifestDigest'], 'abort')
        self.assertEqual(aborted['resultCommit'], self.base)
        self.assertEqual(aborted['completedOperations'], [])
        self.assertEqual(runtime.verify_run(self.request, self.dest)['status'], 'verified-aborted')
        self.assertEqual(runtime.recover_run(self.request, self.dest, manifest['manifestDigest'], 'abort')['status'],
                         'aborted')
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'cannot resume'):
            runtime.recover_run(self.request, self.dest, manifest['manifestDigest'])

    def crash(self, boundary, action='execute'):
        request_file = self.root / 'request.json'
        request_file.write_text(json.dumps(self.request))
        manifest = runtime.prepare_run(self.request, self.dest)
        script = '''import json,os,sys
from pathlib import Path
from agent_braid import git_runtime as r
req=json.loads(Path(sys.argv[1]).read_text())
original=r._atomic_json
original_git=r._git
original_publish=r._publish_directory
boundary=sys.argv[4]
def atomic(root,name,value):
    original(root,name,value)
    if boundary=="intent" and value.get("phase")=="applying": os._exit(77)
    if boundary=="initializing" and value.get("phase")=="initializing": os._exit(77)
    if boundary=="abort-intent" and value.get("phase")=="aborting": os._exit(77)
def git(repo,env,budget,*args,**kwargs):
    result=original_git(repo,env,budget,*args,**kwargs)
    if boundary=="cas" and args[0]=="update-ref" and len(args)==4: os._exit(77)
    if boundary=="initialization-copy" and args[0]=="fetch" and repo.name=="initializing.git": os._exit(77)
    if boundary=="last-cas" and args[0]=="update-ref" and len(args)==4 and args[2]==json.loads((repo.parent/"manifest.json").read_text())["steps"][-1]["commit"]: os._exit(77)
    if boundary=="abort-cas" and args[0]=="update-ref" and len(args)==4: os._exit(77)
    return result
def publish(stage,dest):
    if boundary=="before-publication": os._exit(77)
    original_publish(stage,dest)
    if boundary=="publication": os._exit(77)
r._publish_directory=publish
r._atomic_json=atomic
r._git=git
if sys.argv[5]=="execute": r.execute_run(req,sys.argv[2],sys.argv[3])
else: r.recover_run(req,sys.argv[2],sys.argv[3],"abort")
'''
        process = subprocess.run([sys.executable, '-c', script, str(request_file), str(self.dest),
                                  manifest['manifestDigest'], boundary, action], cwd=ROOT, capture_output=True)
        self.assertEqual(process.returncode, 77, process.stderr.decode())
        return manifest

    def test_process_crash_recovery(self):
        for boundary in ['publication', 'initialization-copy', 'intent', 'cas', 'last-cas']:
            with self.subTest(boundary=boundary):
                self.dest = self.root / boundary
                manifest = self.crash(boundary)
                prefix = runtime.verify_run(self.request, self.dest)
                self.assertEqual(prefix['status'], 'verified-prefix')
                self.assertEqual(prefix['completedOperations'], ['a', 'b'] if boundary == 'last-cas' else ['a'] if boundary == 'cas' else [])
                completed = runtime.recover_run(self.request, self.dest, manifest['manifestDigest'])
                self.assertEqual(completed['completedOperations'], ['a', 'b'])
                self.assertEqual(completed['resultCommit'], manifest['steps'][-1]['commit'])
        for boundary in ['abort-intent', 'abort-cas']:
            with self.subTest(boundary=boundary):
                self.dest = self.root / boundary
                manifest, _ = self.execute()
                self.crash(boundary, 'abort')
                with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'cannot resume'):
                    runtime.recover_run(self.request, self.dest, manifest['manifestDigest'])
                report = runtime.recover_run(self.request, self.dest, manifest['manifestDigest'], 'abort')
                self.assertEqual(report['status'], 'aborted')
                self.assertEqual(report['resultCommit'], self.base)
        self.assertEqual(self.snapshot(self.repo), self.before)

    def test_tamper_and_lock(self):
        manifest, report = self.execute()
        state_path = self.dest / 'state.json'
        original = state_path.read_bytes()
        value = json.loads(original)
        value['nextIndex'] = 0
        state_path.write_text(json.dumps(value))
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'completion'):
            runtime.verify_run(self.request, self.dest)
        state_path.write_bytes(original)
        with runtime._lock(self.dest):
            with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'another coordinator'):
                runtime.recover_run(self.request, self.dest, manifest['manifestDigest'])
        self.git('update-ref', runtime.RESULT_REF, self.base, repo=self.dest / 'result.git')
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'checkpoint'):
            runtime.recover_run(self.request, self.dest, manifest['manifestDigest'])
        self.git('update-ref', runtime.RESULT_REF, report['resultCommit'], repo=self.dest / 'result.git')
        value = json.loads((self.dest / 'manifest.json').read_text())
        value['sourcePromotion'] = True
        (self.dest / 'manifest.json').write_text(json.dumps(value))
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'stored manifest'):
            runtime.verify_run(self.request, self.dest)
        (self.dest / 'manifest.json').write_text(json.dumps(manifest))
        sentinel = self.root / 'sentinel'
        sentinel.write_text('untouched')
        state_path.unlink()
        state_path.symlink_to(sentinel)
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'symlink'):
            runtime.recover_run(self.request, self.dest, manifest['manifestDigest'])
        self.assertEqual(sentinel.read_text(), 'untouched')

    def test_cli_and_forged_terminal(self):
        request_file = self.root / 'request.json'
        request_file.write_text(json.dumps(self.request))
        def cli(command, *options):
            process = subprocess.run([sys.executable, '-m', 'agent_braid', command, str(request_file),
                                      '--run-directory', str(self.dest), *options], cwd=ROOT, capture_output=True)
            return process.returncode, json.loads(process.stdout)
        code, manifest = cli('prepare-git-run')
        self.assertEqual(code, 0)
        code, result = cli('execute-git-run', '--authorize', 'wrong')
        self.assertEqual((code, result['status']), (2, 'rejected'))
        self.assertFalse(self.dest.exists())
        code, result = cli('execute-git-run', '--authorize', manifest['manifestDigest'])
        self.assertEqual((code, result['status']), (0, 'completed'))
        self.assertEqual(cli('verify-git-run')[1]['status'], 'verified-completed')
        code, result = cli('recover-git-run', '--authorize', manifest['manifestDigest'], '--action', 'abort')
        self.assertEqual((code, result['status']), (0, 'aborted'))
        value = json.loads((self.dest / 'state.json').read_text())
        value.update(phase='completed', nextIndex=2)
        (self.dest / 'state.json').write_text(json.dumps(value))
        self.assertEqual(cli('verify-git-run')[0], 2)

    def test_cancellation_and_bounded_failure(self):
        cancellation = threading.Event()
        cancellation.set()
        with self.assertRaises(GitExecutionCancelled):
            runtime.prepare_run(self.request, self.dest, cancel_event=cancellation)
        self.assertFalse(self.dest.exists())
        manifest = runtime.prepare_run(self.request, self.dest)
        original = runtime._git
        def fail_apply(repo, env, budget, *args, **kwargs):
            if args[0] == 'apply' and repo == self.dest / 'result.git':
                raise GitCommandLimitExceeded('injected exhausted command budget')
            return original(repo, env, budget, *args, **kwargs)
        with patch.object(runtime, '_git', side_effect=fail_apply):
            with self.assertRaises(GitCommandLimitExceeded):
                runtime.execute_run(self.request, self.dest, manifest['manifestDigest'])
        self.assertEqual(runtime.verify_run(self.request, self.dest)['status'], 'verified-prefix')
        self.assertEqual(runtime.recover_run(self.request, self.dest, manifest['manifestDigest'])['status'], 'completed')
        self.assertEqual(self.snapshot(self.repo), self.before)

    def test_schemas_and_supported_dependencies(self):
        self.request['operations'][1]['dependencies'] = ['a']
        manifest, report = self.execute()
        for name, value in [('request', self.request), ('manifest', manifest),
                            ('report', report), ('state', json.loads((self.dest / 'state.json').read_text()))]:
            schema = json.loads((ROOT / ('schemas/0.1.0-alpha/git-runtime-' + name + '.schema.json')).read_text())
            Draft202012Validator(schema).validate(value)
        self.assertEqual(report['completedOperations'], ['a', 'b'])

    def test_corrupt_objects_and_configuration_are_rejected(self):
        manifest, report = self.execute()
        repo = self.dest / 'result.git'
        config = repo / 'config'
        original = config.read_bytes()
        config.write_bytes(original + b'\n[core]\n bare = false\n')
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'configuration'):
            runtime.verify_run(self.request, self.dest)
        config.write_bytes(original)
        blob = manifest['steps'][0]['effects'][0]['afterBlob']
        import zlib
        path = repo / 'objects' / blob[:2] / blob[2:]
        # It may have arrived packed, so publish a corrupt loose shadow object.
        path.parent.mkdir(exist_ok=True)
        if path.exists():
            path.chmod(0o600)
        path.write_bytes(zlib.compress(b'blob 6\0forged'))
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'fsck'):
            runtime.verify_run(self.request, self.dest)

    def test_abandoned_index_lock_is_recovered_under_ownership(self):
        manifest = self.crash('intent')
        lock = self.dest / 'result.git/index.lock'
        lock.write_bytes(b'partial owned index')
        self.assertEqual(runtime.recover_run(self.request, self.dest, manifest['manifestDigest'])['status'],
                         'completed')
        self.assertFalse(lock.exists())
        self.assertEqual(runtime.verify_run(self.request, self.dest)['status'], 'verified-completed')

    def test_killed_ref_transaction_is_recovered(self):
        for action in ['resume', 'abort']:
            with self.subTest(action=action):
                self.dest = self.root / ('ref-lock-' + action)
                manifest = self.crash('intent')
                repo = self.dest / 'result.git'
                with runtime._lock(self.dest):
                    process = subprocess.Popen(
                        ['git', '-C', str(repo), 'update-ref', '--stdin'],
                        env=runtime._environment(self.root / 'transaction-home'),
                        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                        pass_fds=(runtime._OWNERSHIP_FD.get(),))
                    try:
                        process.stdin.write(('start\nupdate ' + runtime.RESULT_REF + ' ' +
                                             self.base + ' ' + self.base + '\nprepare\n').encode())
                        process.stdin.flush()
                        self.assertEqual(process.stdout.readline(), b'start: ok\n')
                        self.assertEqual(process.stdout.readline(), b'prepare: ok\n')
                        process.kill()
                        process.wait(timeout=5)
                    finally:
                        if process.poll() is None:
                            process.kill()
                            process.wait(timeout=5)
                        for stream in (process.stdin, process.stdout, process.stderr):
                            stream.close()
                abandoned = repo / (runtime.RESULT_REF + '.lock')
                self.assertTrue(abandoned.exists())
                # Verification remains read-only, even with a stranded ref lock.
                before = self.snapshot(self.dest)
                with self.assertRaises(runtime.InvalidGitRuntime):
                    runtime.verify_run(self.request, self.dest)
                self.assertEqual(self.snapshot(self.dest), before)
                report = runtime.recover_run(self.request, self.dest, manifest['manifestDigest'], action)
                self.assertEqual(report['status'], 'completed' if action == 'resume' else 'aborted')
                self.assertFalse(abandoned.exists())
                self.assertEqual(runtime.verify_run(self.request, self.dest)['status'],
                                 'verified-completed' if action == 'resume' else 'verified-aborted')

    def test_invalid_state_does_not_remove_ref_lock(self):
        manifest = self.crash('intent')
        lock = self.dest / 'result.git' / (runtime.RESULT_REF + '.lock')
        lock.write_bytes(b'preserve rejected state')
        state = json.loads((self.dest / 'state.json').read_text())
        state['nextIndex'] = 99
        (self.dest / 'state.json').write_text(json.dumps(state))
        with self.assertRaises(runtime.InvalidGitRuntime):
            runtime.recover_run(self.request, self.dest, manifest['manifestDigest'])
        self.assertEqual(lock.read_bytes(), b'preserve rejected state')

    def test_invocation_budget_is_cumulative(self):
        from agent_braid.git_process import GitExecutionTimeout
        manifest, _ = self.execute()
        new_dest = self.root / 'budget-run'
        other = runtime.prepare_run(self.request, new_dest)
        prepared = runtime._prepare
        inspected = runtime._inspect
        driven = runtime._drive
        # Model 31 seconds in each phase without slow wall-clock sleeps. Each
        # phase fits 60 seconds on its own; together they must time out.
        def preparation(*args, **kwargs):
            result = prepared(*args, **kwargs)
            kwargs['budget'].started_at -= 31
            return result
        def inspection(root, manifest, env, budget, **kwargs):
            budget.started_at -= 31
            return inspected(root, manifest, env, budget, **kwargs)
        def execution(root, manifest, patches, env, budget, action):
            budget.started_at -= 31
            return driven(root, manifest, patches, env, budget, action)
        for operation in ['execute', 'recover', 'verify']:
            with self.subTest(operation=operation), patch.object(runtime, '_prepare', side_effect=preparation):
                if operation == 'verify':
                    with patch.object(runtime, '_inspect', side_effect=inspection):
                        with self.assertRaises(GitExecutionTimeout):
                            runtime.verify_run(self.request, self.dest)
                else:
                    with patch.object(runtime, '_drive', side_effect=execution):
                        with self.assertRaises(GitExecutionTimeout):
                            if operation == 'execute':
                                runtime.execute_run(self.request, new_dest, other['manifestDigest'])
                            else:
                                runtime.recover_run(self.request, self.dest, manifest['manifestDigest'])
        self.assertEqual(runtime.verify_run(self.request, self.dest)['status'], 'verified-completed')

    def test_command_and_output_budgets_are_cumulative(self):
        from agent_braid.git_process import GitCommandLimitExceeded, GitOutputLimitExceeded
        prepared = runtime._prepare
        for resource, error in [('commands', GitCommandLimitExceeded), ('output_bytes', GitOutputLimitExceeded)]:
            with self.subTest(resource=resource):
                dest = self.root / resource
                manifest = runtime.prepare_run(self.request, dest)
                def exhaustion(*args, **kwargs):
                    result = prepared(*args, **kwargs)
                    budget = kwargs['budget']
                    setattr(budget, resource, budget.max_commands if resource == 'commands'
                            else budget.max_output_bytes)
                    return result
                with patch.object(runtime, '_prepare', side_effect=exhaustion):
                    with self.assertRaises(error):
                        runtime.execute_run(self.request, dest, manifest['manifestDigest'])
                self.assertEqual(runtime.verify_run(self.request, dest)['status'], 'verified-prefix')
                self.assertEqual(runtime.recover_run(self.request, dest, manifest['manifestDigest'])['status'],
                                 'completed')

    def test_exclusive_sealed_directory_publication(self):
        manifest = self.crash('before-publication')
        self.assertFalse(self.dest.exists())
        report = runtime.execute_run(self.request, self.dest, manifest['manifestDigest'])
        self.assertEqual(report['status'], 'completed')
        foreign = self.root / 'foreign'
        foreign.mkdir()
        stage = self.root / 'stage'
        stage.mkdir()
        (stage / 'marker').write_text('ours')
        with self.assertRaises(FileExistsError):
            runtime._publish_directory(stage, foreign)
        self.assertTrue(stage.exists())
        self.assertEqual(list(foreign.iterdir()), [])

    def test_four_operation_boundary_and_resource_limits(self):
        for identifier in ['c', 'd']:
            self.git('checkout', '-q', '-B', identifier, self.base)
            (self.repo / (identifier + '.txt')).write_text(identifier + '\n')
            self.git('add', identifier + '.txt')
            self.git('commit', '-qm', identifier)
            self.request['operations'].append({'instanceId': identifier, 'attemptId': identifier,
                'source': {'kind': 'commit', 'revision': self.git('rev-parse', 'HEAD')},
                'dependencies': [], 'uncertainPaths': [], 'declaredWrites': [identifier + '.txt']})
        self.git('checkout', '-q', 'main')
        for identifier in ['a', 'b', 'c', 'd']:
            (self.repo / (identifier + '.txt')).write_text(identifier + '\n')
        self.git('add', '.')
        self.request['expectedFinalTree'] = self.git('write-tree')
        self.git('reset', '--hard', '-q', self.base)
        self.request['order'] = ['a', 'b', 'c', 'd']
        self.request['operations'][3]['dependencies'] = ['b', 'c']
        self.before = self.snapshot(self.repo)
        manifest, report = self.execute()
        self.assertEqual(report['completedOperations'], ['a', 'b', 'c', 'd'])
        self.assertEqual(runtime.verify_run(self.request, self.dest)['status'], 'verified-completed')
        self.assertEqual(self.snapshot(self.repo), self.before)
        req = deepcopy(self.request)
        req['operations'].append(deepcopy(req['operations'][0]))
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, '2-4'):
            runtime.prepare_run(req, self.root / 'too-many')
        self.git('checkout', '-q', '-B', 'large', self.base)
        (self.repo / 'a.txt').write_text('line-' + 'x' * (runtime.LIMITS['patchBytes'] + 1) + '\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'large')
        req = deepcopy(self.request)
        req['operations'][0]['source']['revision'] = self.git('rev-parse', 'HEAD')
        with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'patch limit'):
            runtime.prepare_run(req, self.root / 'too-large')

    def test_orphan_git_child_retains_coordinator_lock(self):
        import signal
        import time
        owned = self.root / 'owned'
        owned.mkdir()
        marker = self.root / 'child.json'
        binary = self.root / 'bin'
        binary.mkdir()
        fake = binary / 'git'
        fake.write_text('#!' + sys.executable + '\n' +
                        'import os,time,json\nfrom pathlib import Path\n' +
                        'Path(' + repr(str(marker)) + ').write_text(json.dumps({"pid":os.getpid()}))\n' +
                        'time.sleep(30)\n')
        fake.chmod(0o755)
        script = '''from pathlib import Path
import sys
from agent_braid import git_runtime as r
from agent_braid.git_process import run_git
root=Path(sys.argv[1])
with r._lock(root):
    env=r._environment(root/"home")
    env["PATH"]=sys.argv[2]
    r.run_owned_git(root,("fixture",),env=env,budget=r._budget(root), ownership_fd=r._OWNERSHIP_FD.get())
'''
        parent = subprocess.Popen([sys.executable, '-c', script, str(owned), str(binary)],
                                  cwd=ROOT, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE)
        child_pid = None
        try:
            deadline = time.monotonic() + 10
            while not marker.exists() and time.monotonic() < deadline:
                if parent.poll() is not None:
                    self.fail(parent.stderr.read().decode())
                time.sleep(0.01)
            self.assertTrue(marker.exists())
            child_pid = json.loads(marker.read_text())['pid']
            parent.kill()
            parent.wait(timeout=5)
            with self.assertRaisesRegex(runtime.InvalidGitRuntime, 'another coordinator'):
                with runtime._lock(owned):
                    pass
            os.kill(child_pid, signal.SIGKILL)
            deadline = time.monotonic() + 5
            while time.monotonic() < deadline:
                try:
                    with runtime._lock(owned):
                        break
                except runtime.InvalidGitRuntime:
                    time.sleep(0.01)
            else:
                self.fail('orphan child did not release owned lock')
        finally:
            if parent.poll() is None:
                parent.kill()
                parent.wait(timeout=5)
            parent.stderr.close()
            if child_pid is not None:
                try:
                    os.kill(child_pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass

    def test_recovery_does_not_adopt_unsealed_foreign_directory(self):
        manifest = runtime.prepare_run(self.request, self.dest)
        self.dest.mkdir()
        before = self.snapshot(self.dest)
        with self.assertRaises(FileNotFoundError):
            runtime.recover_run(self.request, self.dest, manifest['manifestDigest'])
        self.assertEqual(self.snapshot(self.dest), before)
        self.assertEqual(list(self.dest.iterdir()), [])
