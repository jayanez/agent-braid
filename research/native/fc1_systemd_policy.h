// SPDX-License-Identifier: AGPL-3.0-only
/* Private FC.1 policy. Not a generic systemd admission interface. */
#pragma once
#include "execute.h"
#include "fc1-systemd-gate.h"
#include <errno.h>
#include <stdlib.h>
#include <string.h>

static inline bool fc1_numeric_identity(const char *s) {
        if (!s || !*s) return false;
        for (const char *p=s; *p; p++) if (*p<'0' || *p>'9') return false;
        if (strlen(s)>5 || (s[0]=='0' && s[1])) return false;
        unsigned long n=strtoul(s,NULL,10);
        return n==0 || (n>=61000 && n<=64999);
}
static inline int fc1_context_check(const ExecContext *c, const ExecParameters *p,
                                    const ExecCommand *command) {
        if (fc1_unit_role(p->unit_id)<0) return 0;
        /* FC.1 resolves numeric credentials directly in exec_invoke, clears
         * inherited groups, and never requests a login/home database record. */
        if (p->runtime_scope!=RUNTIME_SCOPE_SYSTEM ||
            !fc1_numeric_identity(c->user) || !fc1_numeric_identity(c->group) ||
            c->supplementary_groups || c->pam_name || c->dynamic_user ||
            c->private_bpf!=PRIVATE_BPF_NO || c->private_users!=PRIVATE_USERS_NO ||
            c->user_namespace_path || c->network_namespace_path || c->ipc_namespace_path ||
            c->private_pids!=PRIVATE_PIDS_NO || c->syscall_filter || c->syscall_archs ||
            c->address_families || c->restrict_filesystems || c->log_namespace ||
            c->working_directory_home || c->set_login_environment != 0 ||
            p->shall_confirm_spawn || (p->flags & EXEC_IS_CONTROL) || command->flags)
                return -EPERM;
        int role = fc1_unit_role(p->unit_id);
        if (strcmp(c->user, c->group) ||
            ((role < 3) != !strcmp(c->user, "0"))) return -EPERM;
        return 0;
}
