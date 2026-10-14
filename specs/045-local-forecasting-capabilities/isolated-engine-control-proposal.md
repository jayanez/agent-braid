# Owned isolated Docker daemon fault control

Status: prepared procedure; execution blocked by missing isolated environment.
No execution, provisioning or artifact approval is requested by this document.
This extends SPEC-035 SC-005 and SPEC-045 SC-002/006 evidence without changing
worker limits. Existing one-run v1–v5 approvals are consumed.

## Isolation and prerequisites

Run only inside a disposable, exclusively owned Linux ARM64 VM. Do not use the
shared Docker Desktop daemon, a privileged nested container, or host-wide process
matching. The current macOS host has Docker CLI but no `dockerd`, Colima, Lima or
QEMU executable. The VM runtime, Linux kernel/root filesystem, Docker CLI/daemon,
container runtime and immutable configuration require exact versions/hashes and
rights review before an execution request can be frozen. Neither this proposal
nor synthetic tests establish availability of that environment.

Docker documents multiple daemons as experimental. Its
[daemon reference](https://docs.docker.com/reference/cli/dockerd/#run-multiple-daemons)
requires separate sockets, data roots, execution roots, PID files and configuration.
Use these independently owned paths within the VM; disable bridge, forwarding,
IP masquerading and iptables/ip6tables management. Do not use default daemon paths
or containerd namespaces. Bind the VM identity, boot identity, daemon PID and birth,
engine ID, Unix socket inode, containerd namespace and configuration digest in the
supervisor receipt. Independently prove that these differ from any shared engine.
The supervisor obtains ownership from its launched child handle and environment
receipt, never from a caller-supplied PID or JSON approval boolean.

The control needs no external network after preparation. Reuse only retained,
verified checkpoint files and image bytes after their exact admission. Transferring
or rebuilding an image into the VM does not establish an identical image ID or
manifest: verify both. A new socket and filesystem path change manifest identity
and require a new exact owner decision. Host/image wheel parity must be verified
for the selected candidate. Model worker remains CPU1/thread1, 2 GiB/zero swap,
64 PIDs, 64 MiB scratch, one active/zero queue, offline/read-only/nonroot,
30 seconds through first prediction and one second resident; no automatic increase.
VM capacity/boot/storage budgets are separate proposed limits, to be pinned and
reviewed with the actual VM artifact, not inferred from the worker approval.

## Registered sequence

1. Preflight every immutable identity, one-run claim, exact owner/pin binding,
   budget and supervisor cleanup ability before starting the VM or model.
   Refuse unsupported cgroups, uncertain ownership, shared endpoints or missing
   independent VM destruction proof. Retain every attempted stage.
2. Start the owned VM and daemon. Capture startup/provisioning counters and verify
   effective engine/worker settings. Register exactly one synthetic cold H1
   prediction; require valid bound output before inducing a resident fault.
3. Capture final available worker/daemon CPU, cgroup peak/current memory and RSS
   observations before fault. Verify exact child identity/birth immediately before
   signaling only that owned daemon. Use a bounded crash signal, not a graceful
   restart and not an attach-client interruption. Record applied live-restore
   configuration: [live restore](https://docs.docker.com/engine/daemon/live-restore/)
   can keep containers alive while the daemon is unavailable.
4. Attempt one registered resident H5 call. Retain refusal/timeout and diagnostics.
   No hidden warmup, retry or subsequent forecast. Success requires no dispatch,
   invalidated readiness/reuse, an unconfirmed-cleanup marker and denial of the
   next lease. Do not infer container removal from an unreachable daemon.
5. Stop/destroy only the owned VM through its supervisor handle, including its
   worker/containerd children and storage. Prove VM/process absence outside the
   failed daemon. Preserve any unobserved counters. If destruction is unconfirmed,
   retain the blocking marker and stop. A later Docker worker close alone cannot
   clear an already released persistent marker; reconciliation is a separately
   reviewed operator procedure binding the exact owner/manifest and absence proof.
6. Export every outcome and whole-procedure wall/counter record, including VM boot,
   resident holding, fault, failed removal, destruction, serialization/export and
   supervisor publication residual. Remove the one-run pin in the supervisor's
   finally block. Never delete the persistent consumed claim or previous receipts.

## Synthetic preparation and outstanding execution packet

`ForecastWorkerTests.test_simulated_daemon_loss_preserves_container_identity_and_blocks_new_lease`
rehearses refusal, identity preservation, persistent denial and absence of Docker
commands. It does not crash a real daemon or demonstrate physical cleanup.

The eventual packet must contain exact executable/VM/kernel/rootfs/daemon hashes,
image/wheel/manifest/checkpoint bindings, dependency rights, command procedure hash,
reviewed independent tests, complete cost collector hashes, one procedure/two
forecast attempts, zero retries, exact stage/total/destruction budgets, additional
spend EUR0, retained prior outcomes and explicit exclusions. No runnable packet
with missing pins or inferred approval is created. Whole-daemon evidence remains
pending until those prerequisites exist and the owner approves that exact packet.
