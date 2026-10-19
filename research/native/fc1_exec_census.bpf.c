// SPDX-License-Identifier: AGPL-3.0-only
/* Source only: never built, loaded or attached by importing any Python module.
 * Uses non-GPL-only helpers available in Linux 6.12, with no task-memory/BTF
 * reads. A fork event identifies the current (parent) task, NOT the child.
 * Exact compiler/header/object/translated-program identities require review.
 */
#include <linux/bpf.h>
#include <bpf/bpf_helpers.h>
struct configuration { __u64 cgroup, epoch; __u32 level, reserved; __u64 enabled; };
struct counters { __u64 allocated, written, lost, reserved; };
struct event {
    __u64 sequence, ns, flow_cgroup, task_cgroup;
    __u32 pid, tgid, kind, reserved;
};
_Static_assert(sizeof(struct event)==48,"census event ABI");
struct { __uint(type,BPF_MAP_TYPE_ARRAY); __uint(max_entries,1);
    __type(key,__u32); __type(value,struct configuration); } fc1_cfg SEC(".maps");
struct { __uint(type,BPF_MAP_TYPE_ARRAY); __uint(max_entries,1);
    __type(key,__u32); __type(value,struct counters); } fc1_state SEC(".maps");
struct { __uint(type,BPF_MAP_TYPE_ARRAY); __uint(max_entries,65536);
    __type(key,__u32); __type(value,struct event); } fc1_evts SEC(".maps");
static __always_inline int emit(__u32 kind) {
    __u32 zero=0;
    struct configuration *cfg=bpf_map_lookup_elem(&fc1_cfg,&zero);
    struct counters *state=bpf_map_lookup_elem(&fc1_state,&zero);
    if (!cfg || !state || cfg->enabled!=1 || cfg->level!=1 || cfg->reserved ||
        bpf_get_current_ancestor_cgroup_id(1)!=cfg->cgroup) return 0;
    __u64 slot=__sync_fetch_and_add(&state->allocated,1);
    if (slot>=65536) { __sync_fetch_and_add(&state->lost,1); return 0; }
    __u64 identity=bpf_get_current_pid_tgid();
    struct event event={};
    event.sequence=slot+1; event.ns=bpf_ktime_get_ns();
    event.flow_cgroup=cfg->cgroup;event.task_cgroup=bpf_get_current_cgroup_id();
    event.pid=(__u32)identity;event.tgid=identity>>32;event.kind=kind;
    __u32 key=(__u32)slot;
    if (bpf_map_update_elem(&fc1_evts,&key,&event,BPF_ANY))
        __sync_fetch_and_add(&state->lost,1);
    else __sync_fetch_and_add(&state->written,1);
    return 0;
}
SEC("raw_tp/sched_process_fork")
int fc1_fork(struct bpf_raw_tracepoint_args *ctx) { (void)ctx; return emit(1); }
SEC("raw_tp/sched_process_exec")
int fc1_exec(struct bpf_raw_tracepoint_args *ctx) { (void)ctx; return emit(2); }
SEC("raw_tp/sched_process_exit")
int fc1_exit(struct bpf_raw_tracepoint_args *ctx) { (void)ctx; return emit(3); }
char LICENSE[] SEC("license")="AGPL-3.0-only";
