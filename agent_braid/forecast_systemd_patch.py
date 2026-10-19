# SPDX-License-Identifier: AGPL-3.0-only
"""Exact-source FC.1 patch generation only; never compiles or executes systemd.

This is a review candidate, not a qualified binary or an activation interface.
The input roster and hashes are fixed; there is no fuzzy patch application.
"""
import difflib
import hashlib
from pathlib import Path

from .forecast_data import digest, require

COMMIT = '3255daee1572366b74fe92f002a3d60ecbb27103'
BASE = {
    'src/basic/meson.build': 'ec8df3258c144e32adab9cdc979236552379dace5d5968ea4a552beec1169bdc',
    'src/basic/process-util.c': 'ce30b7b922c74ac2b9d6c8ca63c822ce6fe654e1971dd18dd754788deb13f597',
    'src/basic/process-util.h': '0cab330ec8538b5723aadf4ce368509cea75c42ca3055ba5dc68e358b17156c6',
    'src/core/execute.c': 'd6dc8db645c35d2bf088a121b4729e6aa326d9801a1297036ba13701fd210a57',
    'src/core/exec-invoke.c': '031e849a5a477fb523c913be6fb6e484029bc3667868cf358efaf53b924b8e91',
    'src/core/namespace.c': '3757a1b53c246f51a8d9e1b6e281402abcf3576c209239deb38ff13ed4e4acee',
    'src/core/namespace.h': 'c38d27b73ccfb14b44b9b91da5e5b9c5de38d89672daa8e8e211e9093c7d2e73',
}
ADDITIONS = {
    'src/basic/fc1-systemd-gate.c': 'research/native/fc1_systemd_gate.c',
    'src/basic/fc1-systemd-gate.h': 'research/native/fc1_systemd_gate.h',
    'src/core/fc1-systemd-policy.h': 'research/native/fc1_systemd_policy.h',
}


def _replace(text, old, new):
    require(text.count(old) == 1, 'systemd-patch-anchor-drift')
    return text.replace(old, new, 1)


def _include(text, header):
    return _replace(text, '/* SPDX-License-Identifier: LGPL-2.1-or-later */\n',
                    '/* SPDX-License-Identifier: LGPL-2.1-or-later */\n\n#include "'+header+'"\n')


def patch_sources(sources, additions):
    """Return transformed bytes and a provenance manifest; no filesystem writes."""
    require(type(sources) is dict and set(sources) == set(BASE), 'systemd-patch-roster')
    require(type(additions) is dict and set(additions) == set(ADDITIONS), 'systemd-patch-additions')
    for name, raw in sources.items():
        require(type(raw) is bytes and hashlib.sha256(raw).hexdigest() == BASE[name],
                'systemd-patch-source-drift:'+name)
    for raw in additions.values():
        require(type(raw) is bytes and 0 < len(raw) <= 65536 and b'\0' not in raw,
                'systemd-patch-added-source')
    out = {n: raw.decode('utf-8') for n, raw in sources.items()}
    n = 'src/basic/meson.build'
    out[n] = _replace(out[n], "basic_sources = files(\n", "basic_sources = files(\n        'fc1-systemd-gate.c',\n")
    n = 'src/basic/process-util.c'
    out[n] = _include(out[n], 'fc1-systemd-gate.h')
    signature = '''int posix_spawn_wrapper(
                const char *path,
                char * const *argv,
                char * const *envp,
                const char *cgroup,
                PidRef *ret_pidref)'''
    out[n] = _replace(out[n], signature+' {', signature.replace('int posix_spawn_wrapper(', 'static int posix_spawn_wrapper_internal(').replace(
        'PidRef *ret_pidref)', 'PidRef *ret_pidref, int gate_fd, const char *unit, const char *invocation)')+' {')
    out[n] = _replace(out[n], '        short flags = POSIX_SPAWN_SETSIGMASK;', '''        bool strict = gate_fd >= 0;
        /* No ungated wrapper may enter this private subtree. */
        if (!strict && cgroup && startswith(cgroup, "/fc1")) return -EPERM;
        if (strict) {
                int role = fc1_unit_role(unit);
                char expected[256];
                if (role < 0 || !cgroup) return -EPERM;
                xsprintf(expected, "/%.67s.slice/%.67s%s/%s", unit, unit,
                         role < 3 ? "-root.slice" : "-workers.slice", unit);
                if (!streq(cgroup, expected)) return -EPERM;
        }
        short flags = POSIX_SPAWN_SETSIGMASK;''')
    out[n] = _replace(out[n], '        if (cgroup && have_clone_into_cgroup) {',
        '        if (strict && !have_clone_into_cgroup) return -EOPNOTSUPP;\n\n        if (cgroup && have_clone_into_cgroup) {')
    out[n] = _replace(out[n], '                else if (r != ENOSYS)\n', '                else if (strict || r != ENOSYS)\n')
    first = '        r = pidfd_spawn(&pidfd, path, NULL, &attr, argv, envp);'
    require(out[n].count(first) == 2, 'systemd-patch-spawn-count')
    out[n] = out[n].replace(first, '''        if (strict) {
                if (!FLAGS_SET(flags, POSIX_SPAWN_SETCGROUP)) return -EPERM;
                r = fc1_gate_authorize(gate_fd, 0, unit, invocation);
                if (r < 0) return r;
        }
'''+first+'''
        /* An admitted attempt may never retry without CLONE_INTO_CGROUP. */
        if (strict && r != 0) return -r;''', 1)
    wrappers = '''int posix_spawn_wrapper(const char *path, char *const *argv, char *const *envp,
                        const char *cgroup, PidRef *ret_pidref) {
        return posix_spawn_wrapper_internal(path, argv, envp, cgroup, ret_pidref, -EBADF, NULL, NULL);
}

int posix_spawn_wrapper_fc1(const char *path, char *const *argv, char *const *envp,
                            const char *cgroup, PidRef *ret_pidref, int gate_fd,
                            const char *unit, const char *invocation) {
        if (fc1_unit_role(unit)>=0 && gate_fd<0) return -EPERM;
        return posix_spawn_wrapper_internal(path, argv, envp, cgroup, ret_pidref, gate_fd, unit, invocation);
}

'''
    out[n] = _replace(out[n], 'int proc_dir_open(DIR **ret) {', wrappers+'int proc_dir_open(DIR **ret) {')
    n = 'src/basic/process-util.h'
    out[n] = _replace(out[n], 'int proc_dir_open(DIR **ret);', '''int posix_spawn_wrapper_fc1(const char *path, char *const *argv, char *const *envp,
                            const char *cgroup, PidRef *ret_pidref, int gate_fd,
                            const char *unit, const char *invocation);

int proc_dir_open(DIR **ret);''')
    n = 'src/core/execute.c'
    out[n] = _include(out[n], 'fc1-systemd-policy.h')
    out[n] = _replace(out[n], '        LOG_CONTEXT_PUSH_UNIT(unit);\n\n        r = exec_context_load_environment', '''        r = fc1_context_check(context, params, command);
        if (r < 0) return r;

        LOG_CONTEXT_PUSH_UNIT(unit);

        r = exec_context_load_environment''')
    out[n] = _replace(out[n], '        /* Restore the original ambient capability set', '''        _cleanup_close_ int fc1_gate_fd = -EBADF;
        if (fc1_unit_role(params->unit_id)>=0) {
                fc1_gate_fd = fc1_gate_open(params->unit_id);
                if (fc1_gate_fd < 0) return fc1_gate_fd;
        }

        /* Restore the original ambient capability set''')
    out[n] = _replace(out[n], '        r = posix_spawn_wrapper(\n', '        r = posix_spawn_wrapper_fc1(\n')
    out[n] = _replace(out[n], '                        &pidref);\n\n        /* Drop the ambient set',
        '                        &pidref, fc1_gate_fd, params->unit_id, params->invocation_id_string);\n\n        /* Drop the ambient set')
    n = 'src/core/exec-invoke.c'
    out[n] = _include(out[n], 'fc1-systemd-policy.h')
    out[n] = _replace(out[n], '        LOG_CONTEXT_PUSH_EXEC(context, params);\n', '''        bool fc1_scope = fc1_unit_role(params->unit_id)>=0;
        _cleanup_close_ int fc1_gate_fd = -EBADF;
        r = fc1_context_check(context, params, command);
        if (r < 0) { *exit_status=EXIT_EXEC; return r; }
        if (fc1_scope) {
                fc1_gate_fd = fc1_gate_open(params->unit_id);
                if (fc1_gate_fd < 0) { *exit_status=EXIT_EXEC; return fc1_gate_fd; }
        }

        LOG_CONTEXT_PUSH_EXEC(context, params);
''')
    out[n] = _replace(out[n], '        r = add_shifted_fd(&keep_fds, &n_keep_fds, &params->exec_fd);', '''        /* Private CLOEXEC channel, deliberately outside params->fds/flag_fds. */
        r = add_shifted_fd(&keep_fds, &n_keep_fds, &fc1_gate_fd);
        if (r < 0) { *exit_status=EXIT_FDS; return r; }

        r = add_shifted_fd(&keep_fds, &n_keep_fds, &params->exec_fd);''')
    out[n] = _replace(out[n], '                .runtime_scope = params->runtime_scope,\n',
        '                .runtime_scope = params->runtime_scope,\n                .fc1_scope = fc1_unit_role(params->unit_id)>=0,\n')
    out[n] = _replace(out[n], '''        if (exec_context_get_effective_private_users(context, params) == PRIVATE_USERS_MANAGED)
                log_debug("Running with a managed user namespace, not initializing UIDs/GIDs.");''',
        '''        if (fc1_scope) {
                /* Validated canonical decimal IDs; no NSS/user/group database. */
                uid = (uid_t) strtoul(context->user, NULL, 10);
                gid = (gid_t) strtoul(context->group, NULL, 10);
                username = context->user;
                /* ngids=0 alone does not clear the inherited group list. */
                if (setgroups(0, NULL) < 0) { *exit_status=EXIT_GROUP; return -errno; }
        } else if (exec_context_get_effective_private_users(context, params) == PRIVATE_USERS_MANAGED)
                log_debug("Running with a managed user namespace, not initializing UIDs/GIDs.");''')
    out[n] = _replace(out[n],
        '                ngids = get_supplementary_groups(context, username, gid, &gids);',
        '                ngids = fc1_scope ? 0 : get_supplementary_groups(context, username, gid, &gids);')
    out[n] = _replace(out[n], '        r = fexecve_or_execve(executable_fd, executable, final_argv, accum_env);', '''        if (fc1_scope) {
                r = fc1_gate_authorize(fc1_gate_fd, 1, params->unit_id, params->invocation_id_string);
                if (r >= 0) {
                        /* Exactly one exec syscall, no path/script/ENOSYS fallback. */
                        (void) execveat(executable_fd, "", final_argv, accum_env, AT_EMPTY_PATH);
                        r = -errno;
                }
        } else
                r = fexecve_or_execve(executable_fd, executable, final_argv, accum_env);''')
    n = 'src/core/namespace.h'
    out[n] = _replace(out[n], 'typedef struct NamespaceParameters {\n        RuntimeScope runtime_scope;',
        'typedef struct NamespaceParameters {\n        RuntimeScope runtime_scope;\n        bool fc1_scope;')
    n = 'src/core/namespace.c'
    out[n] = _replace(out[n], '        bool ro = namespace_read_only(p);\n', '''        bool ro = namespace_read_only(p);
        if (p->fc1_scope) {
                if (!ro || p->private_users != PRIVATE_USERS_NO || p->private_bpf != PRIVATE_BPF_NO)
                        return -EPERM;
                /* No fsck/growfs/udev-partition or userspace verity helper jobs. */
                dissect_image_flags &= ~(DISSECT_IMAGE_FSCK | DISSECT_IMAGE_GROWFS |
                        DISSECT_IMAGE_ADD_PARTITION_DEVICES | DISSECT_IMAGE_PIN_PARTITION_DEVICES |
                        DISSECT_IMAGE_ALLOW_USERSPACE_VERITY | DISSECT_IMAGE_VERITY_SHARE);
        }
''')
    result = {n: text.encode('utf-8') for n, text in out.items()}
    result.update(additions)
    manifest = {'version': 'fc1-systemd-source-patch-v1', 'systemdCommit': COMMIT,
                'baseSha256': dict(BASE),
                'outputSha256': {n: hashlib.sha256(raw).hexdigest() for n, raw in result.items()},
                'sourceReviewAccepted': False, 'buildExecutionAuthorized': False,
                'nativeQualification': False, 'executionAuthorization': False}
    manifest['outputDigest'] = digest(manifest['outputSha256'])
    return result, manifest


def unified_patch(sources, outputs):
    """Render the exact result as reviewable text; no shell or patch subprocess."""
    return ''.join(''.join(difflib.unified_diff(
        sources.get(n, b'').decode('utf-8').splitlines(keepends=True),
        outputs[n].decode('utf-8').splitlines(keepends=True),
        fromfile='a/'+n if n in sources else '/dev/null', tofile='b/'+n))
        for n in sorted(outputs))


def local_additions(repository):
    """Read only the three named project sources, never an image or workload."""
    return {target: (Path(repository)/source).read_bytes() for target, source in ADDITIONS.items()}
