# SPDX-License-Identifier: AGPL-3.0-only
"""Private fixed-image worker entrypoint; never registered in public CLI or MCP.

Requires an operator-provided immutable image recipe and a live root channel.
Importing this module starts nothing. Native readiness is not inferred from it.
"""
from dataclasses import fields
import json
import os
from pathlib import Path
import socket
import stat
import sys

from .forecast_data import digest, pin, require
from .forecast_git_launch import GitLaunchScope, INPUT_COMMITS, admission_launches
from .forecast_linux_profile import BASE, LinuxAdmissionProfile, PhaseLimit
from .forecast_operator_bridge import WorkerBridge, peer, receive, send

IMAGE_ROOT = Path('/opt/agent-braid')
MAX_RECORD = 1024 * 1024


def read_record(path):
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(fd, 'rb') as stream:
        info = os.fstat(stream.fileno())
        require(stat.S_ISREG(info.st_mode) and info.st_size <= MAX_RECORD, 'worker-record-bound')
        raw = stream.read(MAX_RECORD+1)
    require(len(raw) <= MAX_RECORD, 'worker-record-bound')
    from research.lab.model import loads
    return loads(raw.decode())


def write_record(path, value):
    raw = json.dumps(value, sort_keys=True, allow_nan=False).encode()
    require(len(raw) <= MAX_RECORD, 'worker-output-bound')
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'wb') as stream:
        stream.write(raw + b'\n')
        stream.flush()
        os.fsync(stream.fileno())


def recipe_profile(recipe, identity):
    """Static shape/input validation; does not inspect or execute input sources."""
    require(type(recipe) is dict and set(recipe) == {'version','profile','request','gitSha256'},
            'worker-recipe-fields')
    require(recipe['version'] == 'agent-braid-admission-worker-v1', 'worker-recipe-version')
    config = dict(recipe['profile'])
    config['limits'] = tuple(PhaseLimit(**p) for p in config['limits'])
    require(set(config) == {f.name for f in fields(LinuxAdmissionProfile) if f.init},
            'worker-profile-fields')
    profile = LinuxAdmissionProfile(**config)
    require(profile.identity == pin(identity), 'worker-profile-identity')
    pin(recipe['gitSha256'])
    request = recipe['request']
    require(type(request) is dict and request.get('repository') == str(IMAGE_ROOT/'inputs/repository')
            and request.get('baseRevision') == BASE, 'worker-fixed-source')
    require(bootstrap_free_request(request), 'worker-request-shape')
    operations = request.get('operations')
    require(type(operations) is list and len(operations) == 2
            and tuple(op.get('source', {}).get('revision') for op in operations) == INPUT_COMMITS,
            'worker-fixed-inputs')
    return profile


def bootstrap_free_request(request):
    from .git_replay import _validate_request
    from .git_runtime import OID
    try:
        require(set(request) == {'gitRuntimeRequestVersion','repository','baseRevision',
                               'operations','order','expectedFinalTree'}, 'worker-request-fields')
        require(request['gitRuntimeRequestVersion'] == '0.1.0-alpha'
                and type(request['expectedFinalTree']) is str
                and OID.fullmatch(request['expectedFinalTree']), 'worker-expected-tree-required')
        ops = request['operations']
        require(type(ops) is list and len(ops) == 2, 'worker-operation-count')
        for op in ops:
            require(set(op) == {'instanceId','attemptId','source','dependencies','uncertainPaths','declaredWrites'}
                    and op['uncertainPaths'] == [] and type(op['declaredWrites']) is list
                    and all(type(p) is str for p in op['declaredWrites']), 'worker-operation-fields')
        _validate_request({'gitAnalysisRequestVersion':'0.1.0-alpha',
            'repository':request['repository'], 'baseRevision':request['baseRevision'],
            'operations':[{k:v for k,v in op.items() if k != 'declaredWrites'} for op in ops]})
        require(request['order'] == [op['instanceId'] for op in ops], 'worker-fixed-order')
        return True
    except (KeyError, TypeError, ValueError):
        return False


def work(scope, channel, request, mode):
    """Only the registered runtime route; no dynamic module, callback or command."""
    from . import git_replay, git_runtime, runtime_policy
    scope.enter('prepare')
    with admission_launches(scope):
        evidence, advisory = git_replay.produce(git_runtime._analysis_request(request))
        plan = runtime_policy.prepare_policy_run(request, '/work/run',
            replay_evidence=evidence, advisory_plan=advisory, mode=mode)
        write_record('/work/plan.json', plan)
        channel.call('transition', phase='grant')
        scope.enter('grant')
        grant = runtime_policy.issue_operator_grant(plan, '/work/grants',
            acknowledge=plan['planDigest'], ttl_seconds=900)
        channel.call('transition', phase='dispatch')
        scope.enter('dispatch')
        result = runtime_policy.execute_policy_run(plan, '/work/grants', grant['grantId'])
        write_record('/work/dispatch.json', result)
    write_record('/work/launches.json', scope.receipt())


def verify(scope, request, mode):
    from . import git_runtime, runtime_policy
    scope.enter('verify')
    with admission_launches(scope):
        if mode == 'serial':
            result = git_runtime.verify_run(request, '/work/run')
        else:
            plan = read_record('/work/plan.json')
            require(plan['runtimeManifest']['request'] == request, 'worker-plan-request')
            result = runtime_policy.inspect_policy_run(plan, '/work/grants')
        runtime = result if mode == 'serial' else result.get('runtime', {})
        require(runtime.get('status') == 'verified-completed'
                and runtime.get('resultTree') == request['expectedFinalTree'], 'worker-result-not-complete')
        if mode == 'parallel':
            require(result.get('preparationVerification', {}).get('status')
                    == 'verified-worker-trees-and-effects', 'worker-parallel-not-verified')
        write_record('/scratch/verification.json', result)
    write_record('/scratch/launches.json', scope.receipt())


def main(argv=None):
    """Image launcher target. Missing recipe/channel/qualification always refuses."""
    argv = sys.argv[1:] if argv is None else argv
    require(sys.platform == 'linux' and len(argv) == 2, 'worker-linux-arguments-required')
    identity, phase = argv
    pin(identity)
    require(phase in ('prepare','verify','terminal'), 'worker-unit-phase')
    recipe = read_record(IMAGE_ROOT/'fc1'/(identity+'.json'))
    profile = recipe_profile(recipe, identity)
    require(os.getuid() == profile.uid and os.getpid() == os.getpgrp(), 'worker-process-identity')
    profile.validate_source(IMAGE_ROOT/'source')
    scratch = Path('/work' if phase == 'prepare' else '/scratch')
    for name in ('home','tmp'):
        (scratch/name).mkdir(mode=0o700, exist_ok=True)
    os.environ['HOME'], os.environ['TMPDIR'] = str(scratch/'home'), str(scratch/'tmp')
    import tempfile
    tempfile.tempdir = str(scratch/'tmp')
    with socket.socket(socket.AF_UNIX, socket.SOCK_SEQPACKET) as sock:
        sock.settimeout(1)
        sock.set_inheritable(False)
        sock.connect('/operator.sock')
        peer(sock, uid=0)
        bootstrap = receive(sock)
        require(set(bootstrap) == {'profileIdentity','phase','originNs','verificationOf','deadlineNs'}
                and bootstrap['profileIdentity'] == identity and bootstrap['phase'] == phase,
                'worker-bootstrap-binding')
        # Terminal performs no Git/grant work. Operator must still close its own
        # ledger and confirm this cgroup empty; this file is not an acceptance.
        if phase == 'terminal':
            require(bootstrap['verificationOf'] is not None, 'worker-terminal-prior-binding')
            send(sock, {'terminalIdentity':identity})
            require(receive(sock) == {'terminalAccepted':identity}, 'worker-terminal-refused')
            write_record('/scratch/terminal.json', {'profileIdentity':identity,
                'verificationDigest':digest(read_record('/prior/verify/verification.json')),
                'actualProfileAdmitted':False, 'executionAuthorization':False})
            return 0
        limits = {p.phase:p for p in profile.limits}
        holder = {}
        scope = GitLaunchScope(root=scratch, source_root=IMAGE_ROOT/'inputs/repository',
            source_digest=profile.source_digest, git_executable=IMAGE_ROOT/'bin/git',
            git_sha256=recipe['gitSha256'], mode=profile.mode,
            final_verifier='runtime' if profile.mode == 'serial' else 'policy',
            phase_requests={p:limits[p].requests for p in ('prepare','grant','dispatch','verify')},
            phase_ns={p:limits[p].wall_seconds*10**9 for p in ('prepare','grant','dispatch','verify')},
            phase_bytes={p:limits[p].storage_bytes for p in ('prepare','grant','dispatch','verify')},
            terminal_ns=limits['terminal'].wall_seconds*10**9, terminal_bytes=limits['terminal'].storage_bytes,
            max_active=1 if profile.mode == 'serial' else 2,
            boundary_verifier=lambda *a: holder['channel'].verify(*a),
            launch_observer=lambda *a, **kw: holder['channel'].lifecycle(*a, **kw),
            flow_origin_ns=bootstrap['originNs'],
            verification_of=bootstrap['verificationOf'],
            verification_deadline_ns=bootstrap['deadlineNs'] if phase == 'verify' else None,
            verification_work_root='/work' if phase == 'verify' else None)
        require(scope.binding['wholeFlowDeadlineNs'] == bootstrap['deadlineNs'], 'worker-original-deadline')
        send(sock, {'binding':scope.binding})
        require(receive(sock) == {'bindingDigest':scope.binding_digest}, 'worker-handshake-refused')
        holder['channel'] = WorkerBridge(sock, scope.binding)
        (work(scope, holder['channel'], recipe['request'], profile.mode) if phase == 'prepare'
         else verify(scope, recipe['request'], profile.mode))
        holder['channel'].call('complete', phase='dispatch' if phase == 'prepare' else 'verify')
    return 0
