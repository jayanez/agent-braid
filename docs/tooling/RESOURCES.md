<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Local resource observations

`agent_braid.tooling_resources.LocalResourceCollector` is a read-only source
for elapsed local activity time, a kernel-bound RSS sample of the supervisor-owned
root process, and logical bytes
retained under one caller-bound private cohort results directory. It accepts the exact
`ProcessIdentity` value produced by `tooling_supervisor`; a missing identity
returns RSS unknown, never a fabricated zero. Construct the collector at the
start of the registered activity and call `sample(identity)` at bounded
observation points. The constructor's monotonic clock reading defines the local
wall interval, which includes gaps and collector work through each sample.

The caller supplies the fixed results root for the registered activity. The
collector binds that exact path to the registration and activity references; it
does not invent a host directory layout or create the directory. It requires
the root and its immediate parent directories to be user-owned and inaccessible
to group/other users. The caller also supplies existing source and grant roots;
the collector rejects overlap with either set. The retained-disk scan uses descriptor-relative
no-follow traversal, rejects symlinks and special files, checks owner and
private mode bits, and bounds file count, directory count, depth, and path
component length. It reports logical file lengths and a manifest digest, not
allocated blocks. It rechecks file and directory metadata after traversal;
these checks narrow races but do not create an atomic filesystem snapshot.

The supervisor captures a kernel birth binding immediately after `Popen`,
before polling or waiting can reap the owned child. On macOS, the source is
Apple libproc `proc_pid_rusage` with `RUSAGE_INFO_V0`, comparing the kernel
`ri_uuid` and `ri_proc_start_abstime` fields at capture and each sample. This
compares the values reported by that source; it does not claim global token
uniqueness. On Linux, the source holds an open `/proc/<pid>` directory
descriptor and uses a pidfd when available. If `pidfd_open` reports `ENOSYS`,
it reads `stat` relative to the already-open proc directory; it never reopens
a numeric PID path while sampling. Both paths compare boot ID and `stat` start
ticks while reading RSS pages. The procfs fallback relies on the kernel's
documented descriptor-relative behavior: operations through the pinned proc
directory do not retarget a later process that reuses the PID, and reads can
fail after the original process exits. This is weaker liveness signaling than
polling a pidfd, so a failed or stale procfd read becomes unknown or partial.
Missing permissions, malformed metadata, or a changed birth token likewise
leave RSS unknown or partial. The launch-time kernel
resident size is included as the first sample, and later reads are compared
against that birth binding. The source does not infer identity from `ps`
timestamps.

Linux documents `/proc/<pid>/stat` RSS accounting as asynchronous and not
precise. A newly started, already-owned process can therefore have a sample
whose reported resident-page count is zero. The collector preserves that value
as the selected kernel observation; it does not impose a positive floor or
interpolate. A missing pre-start process identity remains unknown rather than
zero, and a zero root-process sample says nothing about child or process-tree
RSS.

RSS scope is only the exact supervisor-owned root process. It does not sum
children or descendants, even when they remain in the same process group; this
is not a complete process-tree maximum and cannot clear a tree-wide cap by
itself. Values are monotonic maxima of successful samples, not continuous
peaks. macOS reads `ri_resident_size` from `RUSAGE_INFO_V0`; XNU populates that
field from the task physical-memory ledger. Linux converts the proc stat
resident-page count using the reported system page size. Both are local kernel
observations and do not authenticate a provider or operation. Native kernel
calls and filesystem metadata operations are synchronous; the kernel provides
no hard I/O timing guarantee. Any integration with the supervisor's one-second
observer callback must use a separately bounded asynchronous or cached source
and preserve the original observation timestamps rather than relabeling a stale
sample as fresh.

Source references: [Apple `ri_proc_start_abstime`](https://developer.apple.com/documentation/kernel/rusage_info_v0/1577540-ri_proc_start_abstime), [Apple `ri_resident_size`](https://developer.apple.com/documentation/kernel/rusage_info_v0/1577575-ri_resident_size), [XNU `rusage_info_v0` declaration](https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/resource.h), [XNU population of `ri_resident_size`](https://github.com/apple-oss-distributions/xnu/blob/main/osfmk/kern/bsd_kern.c), [Linux `pidfd_open(2)`](https://man7.org/linux/man-pages/man2/pidfd_open.2.html), [Linux procfs descriptor semantics](https://www.kernel.org/doc/html/latest/filesystems/proc.html#overview), and [Linux `/proc/pid/stat(5)`](https://man7.org/linux/man-pages/man5/proc_pid_stat.5.html) (RSS accounting caveat).

The immutable snapshot records source names, activity and registration
references, UTC observation bounds, monotonic elapsed time, metric scope,
sample coverage, selected-source hashes, and an overall SHA-256 receipt. The
hash detects accidental receipt changes; it does not authenticate the caller,
the OS, the process, or the measurement. `authenticity_verified` and
`complete_telemetry_snapshot` remain false, and each metric has
`usable_for_caps=false`.

RSS remains a sampled observation, not a continuous peak. A process may
allocate between samples, and child processes are outside this exact-root
scope. Local disk covers only the caller-bound cohort results root at the scan instant.
Synchronous filesystem metadata operations and kernel I/O have no hard
preemption guarantee. Local wall time is not provider runtime or human time.
No metric here reports token usage, retries, provider spend, billing state,
authorization, or a complete capture. These values cannot by themselves clear
registered cost caps or external measurement and acceptance gates.

Tests use bounded synthetic process identities, temporary private roots, and
one short-lived test-owned isolated subprocess. They make no host, provider,
grant, or network calls; the collector itself never signals the observed
process.
