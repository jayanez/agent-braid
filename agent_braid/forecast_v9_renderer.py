# SPDX-License-Identifier: AGPL-3.0-only
"""Private v9 unit TEXT renderer. No installation, manager or native admission.

V8 execution bodies retain their isolation settings. V9 owns the exact roster,
explicit ordering, credentials and root-owned mount lifecycle. Implicit path and
slice dependencies remain unverified; this text is not a closed native graph.
"""
import hashlib
from pathlib import Path

from .forecast_data import digest, require
from .forecast_exec_budget import ROLES, ROLE_PHASE, ExecAllocation, module_dependency_budget


def render_offline_v9(profile):
    """Render a detached nine-unit draft over the existing immutable profile pins.

    The existing profile identity remains the gate's unit/cgroup namespace. This
    artifact gets its own renderer identity; it never renames a v8 manifest to v9.
    Timeout directives are relative proposals, never the absolute outer watchdog.
    """
    from .forecast_linux_profile import LinuxAdmissionProfile
    require(type(profile) is LinuxAdmissionProfile, 'v9-renderer-profile-type')
    whole = sum(p.wall_seconds for p in profile.limits)
    require(all(p.wall_seconds >= 4 for p in profile.limits),
            'v9-renderer-start-stop-reserve')
    original = profile.units(remaining_seconds=whole)
    stem = 'fc1'+profile.identity
    role_units = {role: stem+('.service' if role == 'anchor' else '-'+role+'.service')
                  for role in ROLES}
    slices = (stem+'.slice', stem+'-root.slice', stem+'-workers.slice')
    units = {}
    parent = {slices[0]: '-.slice', slices[1]: slices[0], slices[2]: slices[0]}
    for name in slices:
        require(name in original and original[name].count('[Slice]\n') == 1,
                'v9-renderer-v8-slice-shape')
        body = original[name].split('[Slice]\n', 1)[1]
        units[name] = ('[Unit]\nDefaultDependencies=no\nAfter='+parent[name]+
                       '\nRequires='+parent[name]+'\n[Slice]\n'+body)
    for index, role in enumerate(ROLES):
        name = role_units[role]
        require(name in original and original[name].count('[Service]\n') == 1,
                'v9-renderer-v8-service-shape')
        lines = original[name].split('[Service]\n', 1)[1].splitlines()
        # Drop only the explicitly replaced credential/time settings. No blanket
        # removal of hardening, paths, quotas or worker bindings is allowed.
        replaced = {'User','Group','SetLoginEnvironment','TimeoutStartSec',
                    'TimeoutStopSec','RuntimeMaxSec','StandardInput','StandardOutput','StandardError'}
        lines = [line for line in lines if line.partition('=')[0] not in replaced]
        require(sum(line.startswith('ExecStart=') for line in lines) == 1 and
                not any(line.startswith(('ExecStartPre=','ExecStartPost=','ExecCondition=',
                                         'ExecStop=','ExecStopPost=','ExecReload=')) for line in lines),
                'v9-renderer-extra-command')
        uid = '0' if index < 3 else str(profile.uid)
        # prepare is one worker spanning prepare/grant/dispatch, not three starts.
        duration = (whole if index < 3 else sum(p.wall_seconds for p in profile.limits[:3])
                    if role == 'prepare' else profile.limits[ROLE_PHASE[index]].wall_seconds)
        service_slice = slices[1] if index < 3 else slices[2]
        after = ([role_units[ROLES[index-1]]] if index else []) + [service_slice]
        header = ('[Unit]\nDefaultDependencies=no\nAfter='+' '.join(after)+
                  '\nRequires='+service_slice+'\n')
        units[name] = (header+'[Service]\n'+'\n'.join(lines)+'\nUser='+uid+
                       '\nGroup='+uid+'\nSetLoginEnvironment=no\nTimeoutStartSec=2\n'
                       'TimeoutStopSec=1\nRuntimeMaxSec='+str(duration-3)+
                       '\nStandardInput=null\nStandardOutput=null\nStandardError=null\n')
    dependencies = offline_dependency_inventory(profile, units)
    hashes = {name: hashlib.sha256(text.encode()).hexdigest() for name,text in units.items()}
    return {'version': 'fc1-offline-unit-renderer-v9',
            'profileIdentity': profile.identity, 'profileBindingVersion': profile.manifest()['version'],
            'sourceDigest': profile.source_digest,
            'rendererSha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'units': units, 'unitSha256': hashes, 'unitSetDigest': digest(hashes),
            'roles': role_units, 'sliceParents': parent,
            'mountLifecycleOwner': 'root-syscall-owner', 'managerMountJobs': [],
            'explicitServiceActivationEdges': [],
            'dependencyInventory': dependencies,
            'dependencyInventoryDigest': digest(dependencies),
            'unresolvedDependencies': [
                'RootImage/WorkingDirectory path-to-mount manager dependencies',
                'RootImage ordering on systemd-udevd despite excluded udev payloads',
                'slice parent and root slice activation/readback',
                'unit_patch_contexts conditional module-service Wants/After jobs',
                'booted-manager units, aliases, generators and drop-ins not observed'],
            'nativeGraphClosed': False, 'profileV9Emitted': False,
            'operationalBudgetClosed': False, 'nativeQualification': False,
            'executionAuthorization': False}


# This allowlist bounds THIS renderer's syntax audit, not systemd's whole grammar.
_SERVICE_KEYS = frozenset((
    'Type Slice ExecStart ProtectSystem NoNewPrivileges CPUAccounting CPUQuota '
    'MemoryAccounting MemoryMax MemorySwapMax TasksAccounting TasksMax KillMode '
    'SendSIGKILL Restart OOMPolicy User Group SetLoginEnvironment TimeoutStartSec '
    'TimeoutStopSec RuntimeMaxSec StandardInput StandardOutput StandardError '
    'RootImage RootHash RootImageOptions MountAPIVFS ProtectHome PrivateNetwork '
    'PrivateDevices ProtectControlGroups ProtectKernelTunables ProtectKernelModules '
    'ProtectKernelLogs ProtectClock CapabilityBoundingSet AmbientCapabilities '
    'RestrictNamespaces RestrictSUIDSGID RestrictRealtime LockPersonality Delegate '
    'InaccessiblePaths ProtectProc ProcSubset BindPaths BindReadOnlyPaths '
    'WorkingDirectory UMask Environment').split())
_SLICE_KEYS = frozenset(('CPUAccounting CPUQuota MemoryAccounting MemoryMax '
                         'MemorySwapMax TasksAccounting TasksMax').split())


def offline_dependency_inventory(profile, units):
    """Audit exact local edges; retain unknown path and loaded-manager obligations.

    This intentionally limited parser is NOT systemd-analyze, a unit loader or a
    graph resolver. Unknown directives/sections/continuations fail, rather than
    silently widening the reviewed syntax. No topology or manager facts are read.
    """
    from .forecast_linux_profile import LinuxAdmissionProfile
    require(type(profile) is LinuxAdmissionProfile, 'v9-dependency-profile-type')
    stem = 'fc1'+profile.identity
    services = {stem+('.service' if r=='anchor' else '-'+r+'.service'):i
                for i,r in enumerate(ROLES)}
    slices = {stem+'.slice':'-.slice', stem+'-root.slice':stem+'.slice',
              stem+'-workers.slice':stem+'.slice'}
    require(type(units) is dict and set(units)==set(services)|set(slices),
            'v9-dependency-roster')
    edges=[]; paths=[]; image_ordering=[]; hashes={}
    mount_requests=[]; bindings=[]; slice_obligations=[]; context_jobs=[]
    for name,text in units.items():
        require(type(text) is str and len(text.encode())<=65536,
                'v9-dependency-unit-size')
        hashes[name]=hashlib.sha256(text.encode()).hexdigest()
        kind='Service' if name in services else 'Slice'
        parsed={}; section=None
        for line in text.splitlines():
            require(line and line==line.strip() and not line.endswith('\\'),
                    'v9-dependency-unsupported-syntax')
            if line.startswith('['):
                require(line in ('[Unit]','['+kind+']') and line not in parsed,
                        'v9-dependency-section')
                section=line;parsed[section]={};continue
            key,sep,value=line.partition('=')
            require(section is not None and sep and key in (
                {'DefaultDependencies','After','Requires'} if section=='[Unit]' else
                _SERVICE_KEYS if kind=='Service' else _SLICE_KEYS),
                'v9-dependency-unreviewed-directive')
            parsed[section].setdefault(key,[]).append(value)
        require(set(parsed)=={'[Unit]','['+kind+']'}, 'v9-dependency-sections')
        unit=parsed['[Unit]']; body=parsed['['+kind+']']
        require(unit.get('DefaultDependencies')==['no'], 'v9-dependency-defaults')
        require(all(len(v)==1 for k,v in body.items() if k not in
                    ('BindReadOnlyPaths','Environment')), 'v9-dependency-duplicate')
        if kind=='Service':
            index=services[name]; target=stem+('-root.slice' if index<3 else '-workers.slice')
            prior=[] if index==0 else [stem+('.service' if ROLES[index-1]=='anchor'
                                            else '-'+ROLES[index-1]+'.service')]
            require(body.get('Slice')==[target] and body.get('Type')==['exec'] and
                    all(body.get(k)==['null'] for k in
                        ('StandardInput','StandardOutput','StandardError')),
                    'v9-dependency-service-trigger')
            expected_after=prior+[target]
            slice_obligations.append({'unit':name,'declaredSlice':target,
                'resolvedSliceObserved':False,
                'parserReturnZeroSufficient':False,
                'requiredResolvedRelation':'UNIT_IN_SLICE / UNIT_ATOM_IN_SLICE',
                'assignmentAndLoadStateVerified':False,
                'mergedIdentityAndEffectiveContextVerified':False,
                'defaultSelectionSkippedIfSliceResolved':True,
                'sourceFunctions':['config_parse_unit_slice','manager_load_unit','unit_set_slice',
                                   'UNIT_GET_SLICE','unit_set_default_slice','unit_add_slice_dependencies'],
                'fallbackSelection':'unverified; depends on effective unit and manager context'})
            for directive in ('RootImage','WorkingDirectory','BindPaths','BindReadOnlyPaths'):
                for value in body.get(directive,[]):
                    paths.append({'unit':name,'directive':directive,'value':value,
                                  'resolution':'unverified; no host mount target inferred'})
                    if directive in ('RootImage','WorkingDirectory'):
                        missing_ok = directive=='WorkingDirectory' and value.startswith('-')
                        path = value[1:] if missing_ok else value
                        require(path.startswith('/') and not any(c in path for c in ('%', '\\', '"')),
                                'v9-dependency-unreviewed-path-syntax')
                        mount_requests.append({'unit':name,'directive':directive,'path':path,
                            'mountRequestKind':'Wants' if directive=='RootImage' or missing_ok else 'Requires',
                            'missingOk':missing_ok, 'mountUnitTargets':None,
                            'sourceFunction':'unit_add_exec_dependencies'})
                    else:
                        bindings.append({'unit':name,'directive':directive,'value':value,
                            'scope':'namespace/topology obligation; no direct branch in unit_add_exec_dependencies'})
            if 'RootImage' in body:
                context_jobs.append({'unit':name,'sourceFunction':'unit_patch_contexts',
                    'condition':'effective exec+cgroup contexts, active device policy and root_image/mount_images/root_mstack',
                    'declaredRootImage':body['RootImage'][0],
                    'declaredPrivateDevices':body.get('PrivateDevices',[None])[0],
                    'devicePolicyNote':'PrivateDevices can promote AUTO to CLOSED; no does not establish inactive policy',
                    'edges':[{'kind':kind,'to':target} for target in
                             ('modprobe@loop.service','modprobe@dm_mod.service','modprobe@dm_verity.service')
                             for kind in ('After','Wants')],
                    'activationPossible':True,'activationObserved':False,'effectiveContextVerified':False})
                image_ordering.append({'from':name,'kind':'After','to':'systemd-udevd.service',
                                       'activationByThisEdge':False})
        else:
            target=slices[name];expected_after=[target]
        require(unit.get('After')==[' '.join(expected_after)] and
                unit.get('Requires')==[target], 'v9-dependency-edge-drift')
        for edge_kind,targets in (('After',expected_after),('Requires',[target])):
            for target_name in targets:
                edges.append({'from':name,'kind':edge_kind,'to':target_name,
                              'local':target_name in units})
    return {'version':'fc1-offline-dependency-inventory-v4',
            'scope':'exact renderer syntax and declared edges only',
            'unitSetDigest':digest(hashes),'explicitEdges':edges,
            'serviceSliceEdgesPromoted':2*len(services),
            'externalSliceObligations':['-.slice'],
            'pathResolutionObligations':paths,'rootImageOrderingObligations':image_ordering,
            'mountRequests':mount_requests,'namespaceBindingObligations':bindings,
            'sliceSelectionObligations':slice_obligations,
            'contextGeneratedJobObligations':context_jobs,
            'moduleBudgetObligations':module_dependency_budget(ExecAllocation.from_profile(profile), context_jobs),
            'managerContextVerified':False,
            'sourceReview':{'commit':'3255daee1572366b74fe92f002a3d60ecbb27103',
                'unitCsha256':'dbff1f6b10c7ff433bfb5ddbe919b2fc8e450a87105b451cd0370851da355907',
                'functionsInspected':['unit_add_exec_dependencies','unit_set_default_slice',
                    'unit_add_slice_dependencies','unit_add_mount_dependencies','unit_add_mounts_for','unit_set_slice',
                    'config_parse_unit_slice','manager_load_unit_prepare','manager_load_unit',
                    'manager_dispatch_load_queue','UNIT_GET_SLICE','unit_has_dependency',
                    'unit_patch_contexts','unit_get_private_tmp','unit_get_private_var_tmp'],
                'sliceMappingSourceSha256':{
                    'src/core/load-fragment.c':'217f7961d85fb2e4b1464822ae2b25e89d69d06c1428eb0eafa5d7b530b32695',
                    'src/core/load-fragment-gperf.gperf.in':'8e85fca1c1d179a930140300e80315679c7db3cab06df5f367f39fe68cd675ab',
                    'src/core/unit.h':'563a8180f79038ddc28d267cd971c902bd6c1df438ac92cee6e0a6612b8e1eca',
                    'src/core/manager.c':'4f4abbd08cd64d295eb239233503e23a038a63db7dec2e16bc61253846b6f56f',
                    'src/core/unit-dependency-atom.c':'ac00161e86f4522648d3986496b80d726836de41972456209c52ad2a171bf0f5'},
                'scope':'read-only source inspection; no emitted object or effective context acceptance',
                'effectiveContextVerified':False},
            'blockers':['context-generated modprobe Wants/After jobs are not qualified or budgeted',
                        'path-to-mount resolution has no retained topology witness',
                        'configuration-to-effective-context mapping and deferred mount loading not qualified',
                        'root slice and loaded manager aliases/generators/drop-ins unobserved'],
            'offlineClosure':False,'nativeGraphClosed':False,
            'operationalBudgetClosed':False,'executionAuthorization':False}
