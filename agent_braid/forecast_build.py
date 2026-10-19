# SPDX-License-Identifier: AGPL-3.0-only
"""Data-only build lock and output comparison; never installs or executes.

Completeness and matching bytes do not prove publisher authority, an isolated
build, bootability or admission. Those require independent retained evidence.
"""
from .forecast_data import digest, integer, pin, require
from copy import deepcopy
import hashlib
import re

ROLES = ('base-image', 'systemd-source', 'kernel', 'python', 'git', 'loader',
         'meson', 'ninja', 'cc', 'clang-bpf', 'binutils', 'libbpf', 'libseccomp',
         'libcap', 'gperf', 'cryptsetup', 'util-linux', 'e2fsprogs', 'gdisk',
         'dracut', 'bpftool', 'manager-bridge-source', 'census-source',
         'operator-source', 'input-repository')
SYSTEMD_COMMIT = '3255daee1572366b74fe92f002a3d60ecbb27103'

# Source archives, not emitted Linux objects or publisher-authenticity approvals.
_DEPENDENCIES = {
    'cryptsetup': {
        'version': '2.8.8', 'commit': 'f1dbcce190719c9e177e8fbaf3df0b908f87d920',
        'sourceArchiveSha256': '569481f396d228fc7e02ce9565799340b326210f420b8945f3e4fc795acda669',
        'sourceArchiveBytes': 12171571,
        'configure': ['--with-crypto_backend=kernel', '--disable-udev',
                      '--disable-external-tokens', '--disable-ssh-token',
                      '--disable-internal-argon2', '--disable-libargon2'],
        'macros': {'USE_UDEV': None, 'USE_EXTERNAL_TOKENS': None,
                   'ENABLE_AF_ALG': '1', 'USE_INTERNAL_ARGON2': '0',
                   'HAVE_ARGON2_H': None}},
    'libdevmapper': {
        'sourceVersion': 'lvm2-2.03.31', 'libraryVersion': '1.02.205',
        'commit': '3a6e221c569eb253fa38a772b15e53b5de65b5d1',
        'sourceArchiveSha256': 'b6034560504ae26aeb5d0d5cb148fb2714cbfb4d6a193aa9bb9ce623c754d63c',
        'sourceArchiveBytes': 2877517,
        'configure': ['--disable-dmfilemapd', '--disable-udev_sync',
                      '--disable-udev_rules', '--without-udev'],
        'macros': {'DMFILEMAPD': None, 'UDEV_SYNC_SUPPORT': None}},
}


def dependency_build_policy():
    """Frozen private build constraints; never substitute source hashes for ELFs."""
    return {'version': 'fc1-dependency-build-policy-v1',
            'components': deepcopy(_DEPENDENCIES),
            'cryptoBackendSource': 'lib/crypto_backend/crypto_kernel.c',
            'kernel': {'version': '6.12.113',
                'commit': '7fdb7c1824a1f9979d648d7ae28ac446bcee9c6e',
                'config': {'CONFIG_MODULES':'n', 'CONFIG_UEVENT_HELPER':'n',
                    'CONFIG_STATIC_USERMODEHELPER':'y', 'CONFIG_STATIC_USERMODEHELPER_PATH':'""',
                    'CONFIG_DEVTMPFS':'y', 'CONFIG_DEVTMPFS_MOUNT':'y',
                    'CONFIG_BLK_DEV_LOOP':'y', 'CONFIG_BLK_DEV_DM':'y', 'CONFIG_DM_VERITY':'y',
                    'CONFIG_EXT4_FS':'y', 'CONFIG_CRYPTO_SHA256':'y', 'CONFIG_CRYPTO_USER_API_HASH':'y'}},
            'dmsetupUse': 'root broker only: table --target verity /dev/block/<bound-device>; no --exec',
            'hostRequirements': ['required dm-verity/loop/ext4/SHA256/AF_ALG features built in',
                'no kernel modules and immutable empty static usermode-helper path',
                'immutable host excludes udev daemon, activatable units and executable rules; '
                'udevadm ELF and every systemd-udevd alias/copy excluded by independent filesystem census',
                'kernel/host/readback identities verified by independent retained bootstrap'],
            'sourceBuildCorrespondenceVerified': False, 'dependencyClosureAccepted': False,
            'hostActivationClosed': False, 'buildExecutionAuthorized': False,
            'nativeQualification': False, 'executionAuthorization': False}


def inspect_kernel_helper_config(raw):
    """Literal .config check; does not attest the emitted or booted kernel."""
    require(type(raw) is bytes and 0 < len(raw) <= 256*1024 and b'\0' not in raw
            and b'\\' not in raw, 'kernel-helper-config-input')
    expected = dependency_build_policy()['kernel']['config']; seen = {}
    for line in raw.decode('ascii').splitlines():
        disabled = re.fullmatch(r'# (CONFIG_[A-Za-z_0-9]+) is not set', line)
        enabled = re.fullmatch(r'(CONFIG_[A-Za-z_0-9]+)=(.*)', line)
        if not disabled and not enabled: continue
        name, value = (disabled[1], 'n') if disabled else enabled.groups()
        if name not in expected: continue
        require(name not in seen and value == expected[name], 'kernel-helper-config-unsafe:'+name)
        seen[name] = value
    require(set(seen) == set(expected), 'kernel-helper-config-incomplete')
    return {'configSha256': hashlib.sha256(raw).hexdigest(), 'literalConstraintsSatisfied': True,
            'emittedKernelCorrespondenceVerified': False, 'bootedKernelVerified': False,
            'udevAbsenceVerified': False, 'nativeQualification': False,
            'executionAuthorization': False}


def inspect_dependency_config(component, raw):
    """Inspect literal generated-header constraints without a C preprocessor.

    Relevant conditional, duplicate, indirect and function-like definitions fail.
    This is a header check, not evidence that a compiler used that header or the
    kernel crypto source. Emitted objects and link inputs remain separate gates.
    """
    require(component in _DEPENDENCIES and type(raw) is bytes and
            0 < len(raw) <= 65536 and b'\0' not in raw, 'dependency-config-input')
    # C splices lines before tokenizing comments. Check original bytes first.
    require(b'\\\n' not in raw and b'\\\r\n' not in raw, 'dependency-config-indirection')
    text = raw.decode('ascii'); expected = _DEPENDENCIES[component]['macros']
    # Autoconf's literal undef comments are records; other comments carry no directives.
    text = re.sub(r'/\*\s*#undef\s+([A-Za-z_][A-Za-z_0-9]*)\s*\*/', r'#undef \1', text)
    text = re.sub(r'/\*.*?\*/|//[^\n]*', '', text, flags=re.S)
    require(not re.search(r'\\\r?\n|^\s*#\s*(include|include_next)\b', text, re.M),
            'dependency-config-indirection')
    seen = {}; depth = 0
    for line in text.splitlines():
        if re.match(r'^\s*#\s*(if|ifdef|ifndef)\b', line): depth += 1
        elif re.match(r'^\s*#\s*endif\b', line):
            require(depth > 0, 'dependency-config-conditional'); depth -= 1
        match = re.match(r'^\s*#\s*(define|undef)\s+([A-Za-z_][A-Za-z_0-9]*)(.*)$', line)
        if not match or match[2] not in expected: continue
        directive, name, value = match.groups()
        require(depth == 0 and name not in seen and not value.rstrip().endswith('\\'),
                'dependency-config-ambiguous')
        value = value.strip()
        require((directive == 'undef' and not value and expected[name] is None) or
                (directive == 'define' and value == expected[name]), 'dependency-config-unsafe:'+name)
        seen[name] = expected[name]
    require(depth == 0 and set(seen) == set(expected), 'dependency-config-incomplete')
    return {'component': component, 'headerSha256': hashlib.sha256(raw).hexdigest(),
            'literalConstraintsSatisfied': True, 'compiledHeaderUseVerified': False,
            'cryptoBackendSourceVerified': False, 'dependencyClosureAccepted': False,
            'executionAuthorization': False}


def build_recipe(artifacts, *, source_digest, dependency_manifest_sha256):
    """Require a closed operator-selected inventory, not URLs or mutable tags.

    The dependency manifest names every transitive build/runtime file and its
    resolution; this function only binds its bytes, not its correctness.
    """
    pin(source_digest);pin(dependency_manifest_sha256)
    require(type(artifacts) is dict and set(artifacts)==set(ROLES), 'build-role-roster')
    rows={}
    for role in ROLES:
        row=artifacts[role]
        require(type(row) is dict and set(row)=={'sha256','bytes','provenanceSha256'},
                'build-artifact-fields')
        pin(row['sha256']);pin(row['provenanceSha256']);integer(row['bytes'],1,4*1024**3)
        rows[role]=dict(row)
    require(sum(row['bytes'] for row in rows.values())<=8*1024**3,'build-input-storage')
    return {'version':'fc1-linux-build-recipe-v1','architecture':'aarch64',
            'sourceDigest':source_digest,'systemdCommit':SYSTEMD_COMMIT,
            'dependencyManifestSha256':dependency_manifest_sha256,'artifacts':rows,
            'builds':2,'secondsPerBuild':7200,'inspectionSeconds':3600,
            'totalSeconds':18000,'cpu':1,'memoryBytes':4*1024**3,'diskBytes':20*1024**3,
            'networkDuringBuild':False,'reuseBuildDirectory':False,
            'sourceAuthenticityAccepted':False,'dependencyClosureAccepted':False,
            'buildExecutionAuthorized':False,'nativeQualification':False}


def build_recipe_v2(artifacts, *, source_digest, dependency_manifest_sha256):
    """Bind exact dependency source inputs to the existing two-build envelope.

    v1 remains reconstructible history. v2's extra source is inside the same
    aggregate storage/time limits. No build command is dispatched by this API.
    """
    require(type(artifacts) is dict and set(artifacts) == set(ROLES)|{'libdevmapper-source'},
            'build-v2-role-roster')
    for role, component in (('cryptsetup','cryptsetup'),('libdevmapper-source','libdevmapper')):
        row = artifacts[role]; bound = _DEPENDENCIES[component]
        require(type(row) is dict and set(row) == {'sha256','bytes','provenanceSha256'},
                'build-v2-dependency-fields')
        integer(row['bytes'], 1, 4*1024**3)
        require(row['sha256'] == bound['sourceArchiveSha256'] and
                row['bytes'] == bound['sourceArchiveBytes'], 'build-v2-dependency-source')
        pin(row['provenanceSha256'])
    recipe = build_recipe({r: artifacts[r] for r in ROLES}, source_digest=source_digest,
                          dependency_manifest_sha256=dependency_manifest_sha256)
    recipe['version'] = 'fc1-linux-build-recipe-v2'
    recipe['artifacts']['libdevmapper-source'] = dict(artifacts['libdevmapper-source'])
    require(sum(r['bytes'] for r in recipe['artifacts'].values()) <= 8*1024**3,
            'build-input-storage')
    recipe['dependencyPolicy'] = dependency_build_policy()
    recipe['dependencyPolicyDigest'] = digest(recipe['dependencyPolicy'])
    recipe['dependencySourceRoles'] = {'cryptsetup': 'cryptsetup',
                                       'libdevmapper': 'libdevmapper-source'}
    return recipe


def compare_outputs(recipe, first, second):
    """Compare complete producer inventories; independent filesystem census pending.

    No attempt at a third build or normalization after observing differences.
    Equal output declarations alone are deliberately not reproducibility evidence.
    """
    version = recipe.get('version')
    require(version in ('fc1-linux-build-recipe-v1','fc1-linux-build-recipe-v2'),'build-recipe-version')
    builder = build_recipe if version.endswith('-v1') else build_recipe_v2
    require(recipe==builder(recipe['artifacts'],source_digest=recipe['sourceDigest'],
                dependency_manifest_sha256=recipe['dependencyManifestSha256']),'build-recipe-drift')
    expected=digest(recipe);seen=set();inventories=[]
    for report in (first,second):
        require(type(report) is dict and set(report)=={'recipeDigest','buildId','files'},
                'build-report-fields')
        require(report['recipeDigest']==expected,'build-recipe-drift')
        identifier=pin(report['buildId']);require(identifier not in seen,'build-same-attempt')
        seen.add(identifier);files=report['files']
        require(type(files) is dict and 0<len(files)<=20000,'build-output-roster')
        total=0
        for name,row in files.items():
            require(type(name) is str and 0<len(name)<=1024 and not name.startswith('/')
                    and all(p not in ('','.','..') for p in name.split('/')),'build-output-path')
            require(type(row) is dict and set(row)=={'sha256','bytes'},'build-output-fields')
            pin(row['sha256']);integer(row['bytes'],1,4*1024**3);total+=row['bytes']
        require(total<=8*1024**3,'build-output-storage');inventories.append(files)
    differences=sorted(name for name in set(inventories[0])|set(inventories[1])
                       if inventories[0].get(name)!=inventories[1].get(name))
    return {'recipeDigest':expected,'declaredOutputsMatch':not differences,
            'differences':differences,'independentInventoryVerified':False,
            'cleanBuildsVerified':False,'reproducibilityAccepted':False,
            'nativeQualification':False,'executionAuthorization':False}
