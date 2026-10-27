# FC.1 real utility resumption — 2026-10-17

## Owner decision and current boundary

The owner explicitly resumed SPEC-034/T005 and approved implementing the FC.1
real-utility plan on 2026-10-17. This supersedes the instruction to keep preparing
SPEC-036 indefinitely deferred, for the software/admission work described here.
It does not erase the [cancelled partial attempt](t005-disposition.md), consume a
new native grant, or accept its original unchecked criterion. Historical decisions,
assurance and receipts retain their exact domains. SPEC-045/T007 remains not_planned.

The first implementation (commit `203c740`) was the source-bound request envelope and concurrent
phase ledger in `agent_braid/forecast_admission.py`. It contains no native launcher,
runtime invocation, model, host inspection, source collection, CLI or MCP endpoint.
Public contracts and mandatory runtime verifiers are unchanged. The opt-in launch
implementation below now routes the relevant internal Git calls through a new boundary.

**Status: blocked before an executable admission candidate.** No real inputs have
been captured or admitted. The whole-flow watchdog, terminal publication/cleanup
bound, retained-storage bound and interception of every native launch are not
established. A healthy accounting ledger is not evidence of those properties.
Do not package an execution request from this increment or proceed to the pilot.

## Corrected source accounting

Each replay budget allows 512 requests/120 seconds; each runtime budget allows
256/60 seconds. A source-pinned common-directory probe makes exactly one Git call,
with a 30-second command timeout. `produce` performs two replays. Preparation,
grant issuance and dispatch each reconstruct and verify the policy. Parallel
schedule reconstruction uses two separate runtime budgets, not one.

| Phase | Serial, final runtime verifier | Parallel, final runtime verifier | Parallel, final policy inspection |
|---|---:|---:|---:|
| Evidence production + initial policy preparation | 1,793 | 2,049 | 2,049 |
| Grant reconstruction | 769 | 1,025 | 1,025 |
| Dispatch and included report | 1,025 | 2,050 | 2,050 |
| Final independent verification | 256 | 256 | 1,538 |
| **Git request cap sum** | **3,843** | **5,380** | **6,662** |

The original plan's 6,918 included one extra runtime budget in final inspection.
Policy inspection verifies the parallel journal and worker claims as well as the
final tree; the current synthetic harness ends with a direct runtime verifier.
These are distinct routes and may not share a mislabeled accounting record.

The source envelope explicitly records every budget instance and exact probe.
The resulting internal time-cap sums (including probe process timeouts) are
990, 1,380 and 1,740 seconds respectively. **None is a whole-flow wall deadline.**
Python processing, grant fsync, filesystem walks, teardown and terminal publication
are outside those Git time bounds. The proposed extra 30 seconds is unverified,
not a measured reserve. The earlier 18.5/33.5-minute and 4h33 pilot statements must
not be used as executable wall budgets. Minimum actual native requests/costs remain
unknown. Preserve measured historical costs without adding nested intervals.

The envelope refuses source drift against the fixed modeled source digest. This
is a freshness check for the enumerated route, not proof of transitive coverage,
reviewer identity, actual native costs, input-specific adequacy or execution rights.
Changing source requires review, not merely regenerating a trusted hash.

## Fail-closed accounting without invented native coverage

The ledger requires all four reservations before use: prepare, grant, dispatch,
verify. Their sum must fit the total. The limits and receipts are copied. A phase
cannot borrow the verifier's reservation. Requests are reserved atomically before
a future launcher starts work; at most two reservations can be outstanding.
Serial procedures must configure one. Accepted-but-unstarted requests consume
concurrency so two workers cannot race past the cap.

Attempted, accepted, launched, start-failed and finished requests are separate.
Invalid transitions and phase replay refuse; outstanding requests prevent phase
advancement. A denied request or failed start remains recorded as unhealthy and
stops further preparation/grant/dispatch. Only the reserved final verification
may follow a failed phase; its own denial/start failure is terminal too. This
never resets health. The future driver must bind that exception exclusively to
its trusted verifier, not permit a caller-selected operation under that name.
Launch/finish acknowledgments are caller reports, not kernel observations. Even
an empty or healthy ledger always reports nativeObservation=false,
cleanupConfirmed=false and executionAuthorization=false.

Do not repurpose `utility_budget_observer`: it intentionally swallows exceptions
and cannot enforce admission. No instrumentation exception is silently upgraded
to a safety guarantee. The existing frozen process runners have not been patched.

## Ordered continuation and stop rule

1. Bind two eligible real operations, source rights and exact input/candidate
   identities before capture or native work. Derive input-specific limits and
   establish native-launch coverage, a separately enforced whole-flow watchdog,
   terminal reserve and aggregate retained-storage limit. Seek one Luna review
   of that concrete candidate; do not replace missing bounds with another packet.
2. Present at most one serial and one parallel admission control with closed
   budgets. Each still needs explicit owner execution authority. No old grant,
   profile activation, automatic retry or unreviewed cleanup/recovery is reused.
3. Only after admission and separate source/compute permission, run the agreed
   three development episodes, one cycle of three policies: at most nine arms
   and three cold forecasts. One profile, two operations, two workers maximum,
   Agent Braid only, zero additional euros/downloads. No AI-host launch is needed
   for these arms. All attempts, fallback and missing values remain visible.
4. Connect permissioned source verification through windows, forecasts, economic
   candidates and actual receipts before claiming the chain accepts real inputs.
   Existing session/mapper/harness restrictions are not bypassed; synthetic
   labels and the #554 assumed-tick report remain synthetic. Measure the entire
   prospective deployment boundary; retain historical missing CPU/cost as unknown.
5. Register any later holdout only after a reviewed feasibility decision. Keep
   separate development/calibration/holdout, a single primary group and the
   proposed 30 independent holdout episodes, 2 warmup + 5 measured cycles and
   three arms (630 arm executions), subject to statistical feasibility review.
   Freeze seeds/thresholds/budgets and cold behavior before outcomes. No positive
   result is required; a 1.10 median ratio and 95% lower bound above 1.00 remain
   review candidates, not an obtained acceptance. T008/T009 and founder promotion
   stay independent. Never automatically enlarge the experiment after failure.

The proposed 100 ms grid and one-bin horizon also retain a point-of-use
freshness gate. The historical 4.133591752 s cold availability/first-prediction
observation finished about 41 such bins after cutoff; it is a warning, not a
universal latency lower bound. A future decision must use its actual monotonic
time, reject advice at or after the target interval end (cutoff + step * horizon)
or expiry, and validate causal availability. A 5 s resource freshness allowance
does not renew an expired forecast. Do not change the horizon or add scenarios
to obtain feasibility; record failure if the registered scope cannot work.

Stop this increment at its recorded blockers. This is the original experiment's
dependency order, not another synthetic scenario, execution package or recurring
assessment. No native/model/source acceptance follows from these unit regressions.

## Selected real maintenance inputs — static registration only

The owner approved the proposed pair on 2026-10-17 ("OK, pues adelante"),
solely to register existing input identities and static limits. The two lots
share base `48f4226db1e1b0565b1f8faf0eca81c150a65d30`:

| Operation | Frozen source commit | Patch bytes | Changed paths |
|---|---|---:|---:|
| FC.1 accounting maintenance | `203c74029b594055549b4d97c182829b793502f6` | 42,227 | 6 |
| Plugin documentation maintenance | `086901fed1a957271727a4bb4dc1b23790499829` | 29,204 | 5 |
| **Aggregate** | **Two existing operations** | **71,431** | **11** |

Static Git metadata/diff inspection found only ordinary A/M file changes and no
shared changed paths. The aggregate fits the existing 256 KiB patch and 16-path
runtime limits. Exact patch digests, trees and file modes are in the existing
[accounting receipt](evidence/t005-resumption-accounting.json). Raw patches were
not exported, replayed or applied. No expected final merged tree is claimed.
Disjoint paths do not establish semantic equivalence, runtime admissibility or
independent episodes; the selected lots count as zero observed episodes.

This registration is not experimental telemetry/source permission, a grant,
resource-profile activation, cleanup authority or permission to launch. Existing
branches and their approvals remain independent; this does not merge #557 or
import the uncommitted telemetry branch.

The two source trees contain respectively 32,932,089 and 32,921,249 logical blob
bytes. These are static inventory sizes, not concurrent scratch or retained
storage limits: Git objects, pack/index/refs, temporary copies, publication,
grants, evidence and filesystem overhead still need a complete bound. Do not
sum tree inventory sizes into a fabricated disk quota.

The source-level request cap sums remain 3,843 for serial/direct verification
and 6,662 for parallel/full policy inspection (10,505 across both controls).
They are not narrowed input-specific operational budgets or measured minima.
No executable admission budget is accepted by this registration.

### Remaining technical stop, confirmed by independent static review

Both `git_process.run_git` and `git_runtime_process.run_owned_git` launch with
`start_new_session=True`. Their Git groups therefore need explicit ownership and
termination verification; killing an outer coordinator group alone is not enough.
A reliable launch boundary must reserve before each Popen, distinguish start
failure from launch, retain process identities through reaping, and cover both
runners. The whole-flow watchdog must also cover Python reconstruction and
terminal publication/cleanup, with separately preserved verifier resources.
Every temporary and retained root needs coverage; sampled per-stage scratch is
not a hard aggregate quota. The historical runners, M2 prototype and supervisor are unchanged.

Until that concrete coverage, storage bound and input-specific request budget
are justified, stop before an executable candidate. Do not create another generic
watchdog, fixture, approval package or retry around unproved limits. The plugin
NO-GO applies to the plugin value scenario; it does not by itself prohibit these
separate fixed-runtime admission controls.

## Opt-in launch and terminal supervision implementation

`agent_braid/forecast_git_launch.py` adds a versioned internal route for a dedicated,
externally contained POSIX worker. Adapter, replay and runtime calls share that route. The frozen `git_process.py`, `git_runtime_process.py`,
`git_integration_prototype.py` and `tooling_supervisor.py` bytes remain unchanged. Outside the opt-in route, existing
behavior delegates to the historical runners. Once opted in, the worker cannot
return to a legacy route or reactivate another scope; it must terminate.

Each scoped Popen reserves a phase request first, distinguishes failed start from
launch, records the actual PID and reaping status, and inherits the worker group
instead of creating a detached session. Cancellation kills tracked direct children;
full descendant termination remains the external containment's responsibility.
An unreaped child or unverified external cleanup never becomes a successful close.
Selector-based I/O and bounded waits avoid an unbounded process.wait or pipe-reader
join inside this route. Existing per-stage command/output/scratch limits remain.
An address-space wrapper is unsupported in this route and refuses before launch.
The historical M2 integration prototype is explicitly outside the admission worker:
activation rejects it if already loaded, blocks later imports for the worker's
lifetime, and requires a single Python thread at activation so an import cannot
race that exclusion. The fixed adapter/replay/runtime route does not import it.
Worker threads may start only after activation; no legacy fallback follows exit.

The binding fixes the selected commits and patch hashes, base, mode, final-verifier
route, source digest, executable path/hash, roots, PID/PGID, nonce and absolute
whole-flow deadline. Every launch additionally submits its exact argv, environment,
input hash and inherited descriptors to the trusted operator verifier. A mismatch
refuses before spawn. Source/scratch cwd are constrained; Git environment redirects
are rejected; HOME/TMPDIR/index must stay inside the quota root. No raw environment
or patch contents are exported in the receipt.

The authority is constructor-supplied by trusted operator code, never selected by
a client/model payload. It must verify actual process-tree containment (including
prevention of escape), coverage of every write root, hard phase quotas with protected
future capacity, the matching external watchdog deadline, source inputs and an
immutable Git executable. A hash check alone cannot eliminate path/exec TOCTOU.
The verifier itself and non-Git Python work must be bounded by that external
watchdog. Neither a boolean copied from a request nor a sampled disk scanner
establishes these capabilities. There is no default authority, profile provisioning,
CLI/MCP activation or native admission entrypoint in this increment.

Requests, time and storage have separate explicit allocations for each phase,
plus a terminal time/storage reserve. There are no default numeric time or disk
budgets. The current operational values remain **unset**, because the selected
inputs' inventory sizes and internal Git cap sums do not justify those whole-flow
allocations. Missing, stale, mismatched or insufficient authority/capacity fails
closed. This is implemented budget enforcement, not a measured budget estimate.

The work worker cannot perform final verification. A new `verification_of` worker
requires the previous work binding, confirmed termination, the original absolute
deadline, sufficient remaining verify/terminal reserves and operator-approved
read-only verification effects. Starting another worker never resets that deadline
or authorizes recovery, grant reuse, publication or cleanup. Its empty work-phase
counters describe only that independent verifier, not completion of the producer.

The expanded source digest covers the dispatcher, ledger and validation helpers.
Only the model-pin assignment is normalized to avoid a hash cycle; the inventory,
ledger body and normalization algorithm are hashed. The source caps remain
conditional cap arithmetic, with a new identity; old receipts keep their historical
commit binding. No mutable source pin is treated as operator approval.

**Current stop:** the software route is implemented and tested with fake processes;
no operator-backed containment/quota/immutable-executable lease or closed numerical
whole-flow budget has been obtained for the actual profile. Therefore it still
cannot be presented as an executable admission candidate. Native qualification,
source/rights acceptance, final-tree equivalence, T001/T005/T008/T009 and utility
acceptance remain pending. No real inputs were replayed or captured.

## Existing profile capability resolution (static only)

The bounded review of `scripts/docker/t013/run-validation.sh` and
`verify-resource-profile.py` does not supply an admitted FC.1 profile. Their
read-only root/repository mounts, disabled network, dropped capabilities,
CPU/memory/task declarations and bounded `/tmp` are reusable configuration ideas,
not observations about the selected host. The Linux address-space check concerns
one child, not aggregate memory or storage accounting.

The concrete gaps are:

| Guarantee | Missing from the existing configuration |
| --- | --- |
| Containment and closure | Operator binding and independently confirmed termination of the work tree before a separate verifier. |
| Hard storage and reserves | `/artifacts` is a writable host bind without a hard quota; phase and terminal capacity are not protected across every write root. |
| Immutable profile | The image is a mutable tag with an environment override; its identity is not bound to the source, executable and two selected commits. |
| Whole-flow time | No external watchdog spans work, independent verification, publication and cleanup under the original deadline. |
| Concrete allocation | The inputs do not establish non-Git time or aggregate storage ceilings. T013's historical numbers are not FC.1 budgets. |

**Decision:** retain the implemented refusal boundary and stop numerical budget
closure here. The next technical prerequisite is a concrete operator-owned profile
covering these gaps, with immutable identity and all write roots enumerated. This
is not a request to run T013, provision a container/VM, weaken the verifier or issue
another package. No native qualification is authorized by this record. Until that
prerequisite exists, time/storage allocations remain unset for both selected
inputs; the Git cap sums remain conditional static bounds. T001, T005, T008 and
T009 retain their pending acceptance gates.

## Linux operator profile implementation — not native admission

`agent_braid/forecast_linux_profile.py` implements a private, non-activating
profile compiler and operator-side protocol. It produces unit text in memory;
it does not install services, mount storage, build an image or start a worker.
It exposes no CLI/MCP capability. The actual resource catalogue remains empty.

The proposed profile uses one CPU in aggregate, 2 GiB aggregate memory, no swap,
64 tasks and at most two Git workers (one for serial). A systemd slice contains
all workers. A root-image content digest, explicit dm-verity root hash, runtime
source digest, compiler digest, manager digest, selected commits/patches and all
allocations bind its identity. Values must be supplied by the operator; no
placeholder image or manager identity is registered. The image contract requires
one verity-protected root containing code, Git, inputs and trusted entrypoints;
separate unverified partitions are prohibited. RootHash/read-only configuration
is not evidence that a qualifying image already exists.

Preparation, grant and dispatch retain one worker and the original run/grant
paths. Root-only cgroup freeze plus kernel process membership excludes live Git
children during a handoff. The operator remounts the same tmpfs with a new hard
byte/inode cap equal to actual retained usage plus the next phase allocation,
then verifies the kernel mount readback. No grant store is copied or reset.
Verifier and terminal tmpfs mounts are separate; the work worker cannot address
them. Prior work is exposed read-only to the separate final workers. Future
capacity is excluded from the current write quota; this does not promise physical
RAM availability or completion under the aggregate memory limit.

The external watchdog process binds the frozen worker through kernel cgroup
membership and a pidfd before arming. EOF, worker exit, expiry, invalid rearm or
initialization failure triggers cgroup-wide kill. Phase transitions preserve the
original monotonic deadline. A manager-level runtime/BindsTo bound complements
that process; it does not replace independent kernel termination readback. The
operator-side ledger survives worker changes. Empty cgroup confirmation precedes
verification/terminal attachment; failures stop without retry or admission claims.
No host artifact bind or unbounded stdout/journal export is introduced. Native
acceptance must independently cover every writable mount, directive enforcement,
watchdog death, reaping, publication and cleanup.

### Concrete proposed refusal ceilings for the selected pair

| Mode / final verifier | Git request cap | Whole-flow wall cap | Aggregate phase storage cap |
| --- | ---: | ---: | ---: |
| Serial / runtime | 3,843 | 1,140 s (19 min) | 713,326,592 bytes |
| Parallel / policy | 6,662 | 1,890 s (31.5 min) | 1,384,415,232 bytes |

These are **proposals of abort ceilings**, not narrowed measured minima, predicted
cost, owner-approved spend or proof that either input will fit. Requests retain
the source cap sums. Time adds an explicit policy allowance of 30 s for non-Git
work per phase and a separate 30 s terminal reserve. Storage adds one existing
64 MiB internal scratch envelope per Git budget, the registered 71,431 patch
bytes and an explicit 8 MiB output allowance per phase, rounded upward to a
4 KiB page, plus 8 MiB terminal storage. Output allowances and 65,536 inodes per
work/verify phase (4,096 terminal) are proposed refusal policies, not empirical
requirements. Instrumentation, mount transitions and verification pay their
phase's allowance. Overflow/OOM/timeout is a retained failure, never an automatic
increase. No two controls run concurrently. The full per-phase table is retained
in the existing accounting record.

**Remaining binding gate:** no matching root image/entrypoints, actual manager
identity, launch IPC bridge or independent native readback has been supplied or
qualified. The library cannot turn these missing bindings into a live verifier
lease. Consequently, the operative budget remains unaccepted and the candidate
remains non-activable. This increment implements the compiler and operator phase primitives; it does
not close native profile acceptance, input eligibility or utility. Do not
build/provision an image, create a replacement execution package or launch a
control automatically. T001, T005, T008 and T009 remain pending.

### Read-only runtime integration follow-up

The final verifier preserves the original `/work` run/grant paths and uses its
own `/scratch` for HOME, TMPDIR, indexes and output. `verify_run` opens the existing
coordinator lock with `O_RDONLY` while preserving exclusive `flock`; it cannot
create a lock or change the retained run. This profile is local/tmpfs, not NFS.
The private launch binding advances to v2 and explicitly binds the read-only work
root only for the separate verifier. Writable scratch/environment constraints and
operator approval of each invocation remain mandatory. Work mode cannot add this
read-only root as another writable destination.

These changes add no Git commands and leave the numeric cap rows unchanged.
The prior proposal retains its historical source digest in the accounting record;
the follow-up records the current digest and code hashes separately. Neither
source identity is an execution approval or a native acceptance receipt.

Technical references: the versioned [systemd execution contract](https://github.com/systemd/systemd/blob/v261.3/man/systemd.exec.xml),
[service deadlines](https://github.com/systemd/systemd/blob/v261.3/man/systemd.service.xml)
and [unit lifecycle dependencies](https://github.com/systemd/systemd/blob/v261.3/man/systemd.unit.xml).
These describe the selected implementation mechanism; no installed version is
inferred from them.

## Plugin and telemetry coordination

One candidate value scenario: real Agent Braid maintenance through the installed
Claude/Codex plugin, with forecasting as the economic question. Hosts are blocks;
the same task in both is one episode. Reuse obtained installation/update journeys.
Do not add an onboarding A/B, combine this with the nine fixed-runtime arms or
reuse M4.5's historical 108 slots as utility observations.

The plugin's analysis-only contract has no forecast/grant binding. That missing
economic decision is a gate, not permission to add MCP actions. Product telemetry
v1 stores daily aggregates/coarse histograms without exact timing or event order;
it cannot supply causal windows or paired costs. Preserve that privacy contract.
Experimental capture needs separate private consent/retention and opaque episode
bindings; exclude prompts, thinking and credentials. No host is launched here.

Plugins and telemetry both used SPEC-046 / ADR 0024 in separate histories. Their
owners must resolve identity alignment before integrating the later branch;
this FC.1 increment edits neither branch nor its historical approvals.

## Validation and evidence

`tests.test_forecast_admission` checks the actual source envelope, drift refusal,
reserved final verification, failed-start accounting, ticket/phase replay and
atomic concurrency. It creates no Git workload, model, VM or approval package.
The [accounting receipt](evidence/t005-resumption-accounting.json) records obtained
software checks and the continuing blockers. Original T005, SPEC-036/T001/T008/T009
and dependent acceptance criteria remain unchecked; no milestone closes.

### Private operator bridge and fixed worker continuation

The next authorized software increment adds `forecast_operator_bridge.py`,
`forecast_admission_worker.py` and the private image launcher source
`scripts/fc1_admission_worker.py`. It adds no public CLI/MCP command and neither
builds an image nor starts a manager, worker, native control or model.

The root operator accepts a connected Linux Unix `SOCK_SEQPACKET` channel only
with kernel-observed worker PID/UID. The worker requires a root peer. Messages
have a 64 KiB ceiling, strict field sets, unique JSON keys, a monotonic sequence
and an exact worker-binding digest. Socket descriptors are non-inheritable;
requests have bounded I/O and the operator monitors disconnects against the
original phase deadline. A read-only bind exposes only the operator socket file
inside each worker; socket ownership/mode and its actual mount remain native
readback requirements. No listener is automatically created.

Each scoped Git launch reserves the external operator ledger before `Popen`.
Its exact argv, environment, input digest and inherited descriptors accompany the
reservation. The operator-supplied child observer must independently bind the
PID/kernel identity, executable, invocation and containment, retain that identity,
and independently confirm termination and return code before releasing the
reservation. There is no default native observer. An already vanished command,
producer-only `startFailed`, unknown exit, EOF, replay or identity ambiguity keeps
uncertainty visible and aborts without refund or retry. A producer's completion
message explicitly does **not** establish kernel closure. The original cgroup
must independently be empty before another worker attaches.

The fixed worker reads a bounded recipe from the immutable image, verifies its
profile identity and requires the two selected input identities on their common
base. It does not invent `expectedFinalTree`. It runs evidence/preparation,
operator grant and dispatch in the same original work process and paths. The
independent verifier uses the original read-only `/work` and its own scratch;
acceptance requires `verified-completed`, the registered expected tree, and,
for parallel mode, independent worker-tree/effect verification. The terminal
worker writes a bounded digest record; it cannot admit the profile or establish
operator/kernel cleanup. The operator still owns final ledger reconciliation
and closure.

Private launch bindings are now v3, with an explicit original flow origin and
external-ledger flag. Startup/IPC consumes the current phase's allocation. A
phase may shorten to preserve all later reserves and the original total deadline;
it cannot reset that clock or borrow the verifier/terminal reserve. The named
source inventory now includes the bridge, worker, Linux compiler and launcher.
This adds no Git invocation to the modeled runtime routes. The unchanged 3,843 /
6,662 request ceilings and 19 / 31.5 minute, 680.28125 / 1320.28125 MiB proposals
remain abort policies, **not** measured minima, accepted budgets or authority.

**Concrete remaining blocker:** no qualified Linux image/root hash, manager
identity, immutable real recipe/expected tree or native boundary/child/binding
observer is supplied. The prescribed local image directories are absent on the
current macOS preparation host; this says nothing about uninspected other hosts.
The callbacks intentionally have no permissive default. Consequently the
software protocol can be checked offline but there is still no executable,
admitted two-input candidate. No image construction, activation, source replay
or replacement attempt follows automatically. The next decision needs that
concrete artifact/provider binding, before any launch approval can be requested.

The existing evidence record retains the previous source pins, diagnostics,
reviews and limits. T001/T005/T008/T009 and all source, native, model, experiment,
interpretation and adoption gates remain pending. Plugins #557 remains frozen
and analysis-only; telemetry remains separate, unintegrated and unsuitable as
causal FC.1 history. Neither track acquires execution or capture authority here.

### Immutable recipe and native verifier continuation — 2026-10-18

This continuation supersedes the preceding missing-provider statement only for
implemented software. It does not qualify a host or accept T005. The private
worker recipe is v2; the external Linux profile is v3 and launch binding is v4.
The recipe contains only version, source digest, Linux Git SHA and the request.
Its SHA is bound by the external profile after image construction, avoiding an
image/profile self-hash cycle. Bounded reads of the three fixed commits' tree
metadata (664,952 bytes, no blobs or replay) established the expected final tree
`a9fba0b46b332981f1097035ee0b71c21ad100be`. The retained metadata record names
all inputs and permits independent reconstruction of the pure tree arithmetic.

The root verifier now checks the manager, image SHA/verity root, worker identity,
mount isolation, source inventory, exact recipe, closed loose object inventory,
watchdog and phase quotas. Source/admin path components must stay regular and on
the read-only image device. Root CLI tools execute sealed copies of the exact
pinned bytes. Git children require live identity observation and independent
zombie exit-status observation before reap; unobservable fast exits fail closed.
The future native object-closure verifier reads blobs and charges that work; it
was not executed against the real inputs here. Its compressed and decompressed
closure limits are each 128 MiB per qualification; all instrumented reads share a
2 GiB phase cap, with at most five qualifications and fifteen bounded root tools.
These costs consume existing phase deadlines rather than receive free time.

Profile v3 renders a shared aggregate slice (one CPU, 3 GiB, 96 tasks), a worker
subslice (2 GiB, 64 tasks), and an operator service (512 MiB, 16 tasks), all with
zero swap. Native readback requires actual operator placement and executable pin
and all three quotas. Rendering does not install/start units. The operator's
immutable launcher/orchestrator artifact is still absent. Peak RSS, unreaped-child
CPU, external OS/anchor work and whole-flow cleanup remain native accounting
gates; installed VM RAM is not treated as an execution quota.

The single image definition is `linux-image-contract.json`: local aarch64 Linux,
kernel >=6.12, systemd 261.3, Python 3.13.11, one vCPU, 4 GiB RAM, 20 GiB VM
scratch, a raw GPT image capped at 512 MiB with one verity-protected ext4 root.
Actual audited Linux Git/Python/manager/operator/dependency artifacts and their
hashes are absent. Therefore recipe bytes, recipe SHA, image SHA and verity root
remain unset. There is no fabricated executable candidate, image build or fallback
download. The 512 MiB image ceiling itself must be shown feasible by those artifacts.

**Stop blocker:** an independent bounded census/cap of Git-internal helper execs
has not been established. Python-issued Git request ceilings are not a descendant
exec budget. Source-only tracer exploration was not built, loaded, attached or
integrated. Before accepting any operational budget, a reviewed native mechanism
must reconcile helper execs and reject missing/overflow/ambiguous events. Until
then the unchanged serial 3,843 / parallel 6,662 Git-request, 1,140 / 1,890 second
and 713,326,592 / 1,384,415,232 byte ceilings remain proposed abort limits, not
minimum costs, completion guarantees or accepted execution allocations.

Luna's focused static review found no actionable residual in the image-path,
sealed-tool or aggregate quota changes. All 84 offline targeted tests passed; their
result is software evidence only. The full PR profile was interrupted (130) when
a repeated operator-executable hashing cost was corrected. It is not a passing
result; a complete stable PR profile remains pending. The corrected provider
hashes the operator once and checks inode/device identity on each later readback. Plugins and telemetry received the material
state and remain frozen. T001, T005, T008, T009 and all source, model, native,
pilot/holdout, publication, interpretation and founder-adoption gates stay pending.

### Git auxiliary census and Linux provenance — 2026-10-18

The private profile is now **v4**, binding an external census-manifest SHA. The
new read-only kernel adapter accepts only BPF object-open, object-info and map
lookup operations; it cannot load, attach or mutate programs/maps. Three retained
raw-tracepoint links must refer to independently pinned fork/exec/exit programs
sharing the exact cfg/state/event maps. The fixed numeric ABI has 48-byte records,
65,536 slots (3 MiB event payload), and no argv, paths, environment or prompt data.
Configuration, program identity, recursion misses, loss, in-flight records and
snapshot stability are checked. These are software checks, not observed native
coverage: the probe source/object/loader and actual translated-program hashes are
still missing. Root-supplied hashes require independent source/build review;
reading a program hash from the kernel cannot approve that same program.

Each phase reconciles only its new events and newly known Git/tool/worker execs.
A later known PID cannot relabel a closed phase. Repeated execs by one PID count
again; residual events remain auxiliary-or-unclassified, without pretending that
all are Git helpers. Each phase receives an explicit proposed auxiliary abort
allowance equal to its Git-request cap: 3,843 serial / 6,662 parallel in aggregate.
With fifteen root-tool and three worker entries, the corresponding total exec
abort policies are 7,704 / 13,342. The event journal has its own independent cap;
thread/fork/exit traffic can exhaust it earlier. These are conservative **risk
choices**, not measured helper requirements or guaranteed sufficient capacity.
No later phase's reserve or prior unused helper allowance may be borrowed.

**The essential distinction:** a post-exec journal can detect an exceeded policy
but cannot prevent that exec. Therefore v4 declares `execAdmissionEnforced=false`,
and `NativeBoundary.qualify()` refuses before kernel reads or tool launches. This
candidate cannot release workers. Closing the launch budget needs a separately
reviewed pre-exec barrier, such as root-owned seccomp notification for both exec
syscalls, inherited non-relaxable filters, independent filter/listener identity,
per-phase admission accounting, and fail-closed supervisor/listener death. That
mechanism is not implemented, deployed or accepted here. There is no permissive
fallback from a missing hard limit to an observational counter.

For Linux artifacts, `sourceAcquisition` in the existing image contract now fixes
source candidates rather than prescribing an unversioned download:

| Component | Fixed source identity | Actual Linux binary identity |
|---|---|---|
| Kernel | 6.12.113; archive SHA256 `e09b6727e5c521253f0d41694900b9c38fb7604db7d35238a8197aa9f7de2428` advertised in upstream checksum metadata | Missing |
| systemd | v261.3; commit `3255daee1572366b74fe92f002a3d60ecbb27103` | Missing |
| Git | v2.56.0; commit `a018953688f1b10bddf91bff8747068f5f4746a4` | Missing |
| Python | 3.13.11; archive SHA256 `16ede7bb7cdbfa895d11b0642fa0e523f291e6487194d53cf6d3b338c3a17ea2` advertised in upstream Sigstore metadata | Missing |

Only small public release/checksum/signature metadata was read. No source archive,
ELF binary, dependency, image or model was downloaded or executed. GitHub reports
valid signatures on the selected Git/systemd tags; no local signature verification
or key-policy acceptance is claimed. Advertised source digests are neither
verified archive bytes nor ELF hashes. The canonical systemd repository resolved
v261.3; the stable-mirror 404 is a diagnostic, not a reason to change the pin.

The concrete acquisition route is one operator-selected **existing audited local
Linux aarch64 bundle**, independently pinned by manifest and provenance SHA256.
The explicit inspector `forecast_linux_artifacts.inspect_bundle` reads only named
regular files through no-follow directory FDs, enforces fixed byte/count bounds,
checks hashes and stable inode/size/timestamps, and parses ELF architecture without
running binaries, importing packages or invoking ldd. Its receipts deliberately
leave source authenticity, dependency closure and native qualification false.
It was tested with tiny parser fixtures only, never against a Linux bundle.

Required bindings are kernel, manager, systemctl, dmsetup, Git, Python, operator
interpreter, immutable operator launcher/orchestrator, and census object. Exact
loader/libraries, Python runtime files, Git helper closure and probe/filter build
identity need independent review and a complete manifest. dmsetup/libc and the
build toolchain remain unselected: this is **not** a build-ready dependency lock.
If no approved bundle exists, acquiring/exporting/building one needs separate
specific authority; that initial inventory performed no network artifact acquisition, Linux build,
image construction, VM launch or automatic fallback. The subsequently authorized
static-only package acquisitions are recorded in the continuations below. Actual file
sizes must fit the existing root/image caps including filesystem/verity overhead.
The inspector file-byte sum does not prove that image fit.

All instrumentation, kernel allocations, readback, inspection and closure must
consume the previously registered CPU/memory/time/storage scopes. Three MiB of
journal payload is not peak RSS or total kernel memory. No phase wall, Git scratch,
VM scratch or worker limit was increased. The operational budget remains blocked
by pre-exec mediation, reviewed artifacts and native qualification; it is not
closed by source metadata, parser tests, administrative tracking or this review.

### Pre-exec quota core and partial binary audit — 2026-10-18

Profile **v5** binds the exact filter bytes and records the implemented quota core,
but keeps `execAdmissionEnforced=false`; the native qualifier still refuses.
`forecast_exec_gate.py` adds an explicit future single-thread installer, a root
listener driver and write-ahead phase ledger. Nothing installs or starts on import.
Both aarch64 exec syscalls notify the root broker, foreign ABI kills, and later
seccomp/prctl calls are denied to prevent a newer filter shadowing this listener.
The broker reserves before CONTINUE, keeps failed/ambiguous attempts consumed,
never refunds/retries, and closes all owned listeners on failure. CONTINUE is a
numeric allowance, not semantic authority or proof that the exec succeeded. No
security decision reads mutable argv/path/payload memory from the tracee.

Luna found and the implementation corrected a phase-transition race and exposed
FD ownership. The broker now retains a CLOEXEC duplicate behind an opaque token;
root verifier callbacks receive only their intended verification input, while
caller-facing handles/receipts do not disclose the retained FD. A shared lock
covers receive/reserve/continue. The root-controlled transition requires verified
quiescence and no pending notifications, preserves listener epochs, rejects public
ledger advancement, and cannot extend original/per-phase deadlines. Frozen prior
phase helpers cannot spend the next phase's allowance. These are source/API
properties, not hostile-root isolation or an installed native security boundary.

The missing integration is explicit: a dedicated immutable launcher must install
before creating any threads/children, hand the listener exclusively to a separately
supervised root broker, and cover root tools/Git descendants as well as registered
manager startup allowances. Counting current threads alone does not prove race-free
installation. Actual filter/listener/task/cgroup identity and cleanup must be
verified independently. Until that exists, the implemented core cannot be claimed
to prevent every launch in the candidate runtime. It does not enable this profile.
The new numeric BPF census source is present, with the 48-byte ABI and parent PID
semantics on fork; it was not compiled, loaded or attached. Its actual object,
compiler/header lock and translated-program hashes remain missing.

Following the owner's specifically relayed static-audit acquisition authority,
four Debian arm64 candidate packages were obtained, without installation, builds,
maintainer-script execution, ELF execution or ldd: Python minimal 3.13.11-1,
libpython minimal 3.13.11-1, dmsetup 2:1.02.205-2 and libdevmapper 2:1.02.205-2.
Their archives total **3,117,352 bytes**. Static inspection identified five actual
ELFs, totaling **7,846,160 bytes**, with exact SHA256 and dynamic dependencies in
`partialLinuxBundleAudit` of the existing image contract. The Python interpreter
SHA256 is `6d0e9a0717a0c2a15d6fb281cb2e5cecc7a824462fa5e4987995c35cb534f5d1`;
dmsetup is `554e3526e1683a710be0c8aa89ea52be72e2cc5a96c7029d07a80de7827554f2`.
These identify inspected candidate bytes; they are not installed or accepted pins.

The archive parser read only the data member; symlinks were recorded but not
followed/extracted, and only selected regular ELF files were saved in the owned
static-audit directory. The source inspector now reads ELF program/dynamic headers
to report interpreter, DT_NEEDED and search paths as data. It never invokes the
loader and still leaves dependency resolution/authenticity false. Matching a
Snapshot SHA1 locator and computing an actual SHA256 do not authenticate package
signatures or approve provenance.

**Concrete bundle disposition:** partial/unaccepted. The inspected files require
unprovided libc/loader, libm/z/expat, crypto/ssl, selinux and matching libudev,
plus the complete Python runtime (including ctypes/libffi). Fixed Git2.56.0 and
systemd261.3 had no exact match in the queried Snapshot route; no replacement was
selected. That narrow observation is not a claim that no binaries exist elsewhere.
Kernel, operator launcher/broker integration, compiled probe and dependency/build
lock are absent. Plugins confirmed that its existing Linux x86_64/Python3.12.15
package and emulated controls do not supply this aarch64 bundle. A build/export or
another explicitly scoped acquisition is a separate action, never an automatic
consequence of this audit. The full `inspect_bundle` acceptance path was not run
against this incomplete inventory.

Existing serial/parallel request, wall, VM/Git scratch and aggregate/operator caps
were not enlarged. Static-audit host storage is separate from execution tmpfs and
VM scratch; compressed archive bytes, ELF file bytes and installed memory are not
summed as one quota. Neither the partial file sum nor parser tests demonstrate
image fit, runtime cost or a minimum viable operational budget. T001/T005/T008/T009,
native admission, source/model permissions, experiment, publication and adoption
remain pending. The single retained work record is extended; no new launch packet
or experimental scenario is created.

### Launcher/root actor and historical package authentication — 2026-10-18

This continuation supersedes the previous lot's *missing software handoff* status;
it does not supersede its native or scientific gates. Profile **v6** additionally
pins the worker interpreter and the separate operator entry file. Worker units
start the pinned Python interpreter directly with `-I -S` and the fixed source
script; a separate executable worker wrapper is no longer required. The source
script explicitly selects the immutable source directory, without site hooks.

`forecast_launcher.py` now connects the private launcher, root broker and operator
client in source. A root-owned verifier checks peer credentials, exact command,
entry/interpreter/source pins, read-only mounts, cgroup and process start identity.
A bounded nonce-bound SCM_RIGHTS handoff closes the original listener before ACK;
the root verifies release independently. After fork, the controller closes its
copy of the accepting socket; the child retains an explicit FD allowlist. Malformed
or truncated ancillary data, accounting failure and transfer failure close owned
FDs. These source properties do not establish actual kernel filter bytecode,
inheritance, source immutability or exclusive custody on a running host.

The root actor owns phase transitions and consumed permits. Worker entry is reserved
before the supervisor receives a fixed unit-start intent; no manager is invoked.
Separate verify/terminal workers require the same ordering. Frozen/empty task checks,
phase deadlines and the observed exec census must agree with distinct prior root
permissions. Observed execs cannot manufacture permissions, refund unsuccessful
attempts or silently borrow another phase. Terminal completion now stops and reaps
the root actor before accepting the timeline finish and closes census/child handles.
Its wall, process CPU and reaped-child CPU have separate receipts. An unconfirmed
reap or nonzero actor exit fails closure; cleanup cannot extend the current phase.

Luna identified and the delta corrected incomplete post-SIGKILL reaping, the child
cleanup gap on pidfd acquisition failure, and the controller's retained accepting
socket (including failure of the first socket close). Mocked controls exercise these
failure paths. They do not execute a fork, filter installer, broker or native unit.
The external immutable `admission.py`, actual manager bootstrap/entry receipt and
activation backend are still absent. In particular, an outer operator bootstrap
cannot be self-authorized retrospectively by the actor it creates. Its authority
and cost remain a blocker inside the registered boundary; no extra exec allowance
or free residency is assumed. `execAdmissionEnforced=false` and `qualify()` refusal
remain unchanged.

The existing **2 GiB per-phase instrumented-read abort policy** is partitioned into
1 GiB for the operator provider and 1 GiB for the root actor; bootstrap actor reads
remain charged to prepare. This is cumulative instrumented I/O, not an allocation
or memory quota. Readback and socket transfers consume their owner's partition;
operator/actor CPU scopes remain explicit. Actor process CPU snapshots are cumulative;
the terminal reaped-child CPU includes that same actor. These are overlapping
views and must not be added together or summed across snapshots. Readback/closure
wall intervals are contained in their phase wall intervals, not extra durations.
No Git, wall, aggregate/operator memory,
VM/Git scratch, output or retained-storage ceiling is enlarged. End-to-end cost and
whole-flow closure still need independent native evidence.

The same owned static-audit directory now contains **23 Debian arm64 packages**
(**12,672,180 compressed bytes**) and **104 selected regular ELF files**
(**32,485,088 bytes**). No ELF, maintainer script, build tool or installer was run.
The two historical InRelease signatures were mathematically verified with an
already installed cryptographic provider, using pinned official key-file hashes
and full signing fingerprints. SHA256 and size bind each Packages index to its
signed Release and each of these 23 archives to the exact package/version/arm64
stanza. The new bounded verifier supports only RSA v4 canonical-text signatures
with SHA256/384/512; it is not a general OpenPGP policy validator. It leaves key
certification, revocation/expiry, publisher trust policy and current freshness
unaccepted. Both retained Release Valid-Until dates are historical (May/December
2025); no freshness exception or key approval is inferred from the valid signature.

The updated SONAME inventory removes false missing-library reports caused by
versioned filenames. Among these inspected ELFs, `libudev.so.1` still has no
provider. Finding a SONAME provider is only a structural observation: loader paths,
symbol versions, non-ELF runtime/package dependencies, Python runtime files and the
complete fixed-version bundle remain unaccepted. Exact Git2.56.0, systemd261.3 and
systemctl, matching libudev, kernel image, immutable operator entry, compiled probe,
source/build lock and image/verity identities are still missing. Another version,
architecture or the plugins' x86_64 bundle is not substituted. No unbounded recursive
acquisition or build follows automatically.

The contract and existing T005 work/evidence record retain hashes of the static
receipts and package identities. Downloaded archive bytes, selected ELF bytes,
filesystem image fit and peak RAM remain distinct. These partial hashes do not
serialize an executable recipe or close the operational budget. T001/T005/T008/T009
and all native/source/model/experiment/publication/adoption gates remain pending;
#557 and input B remain frozen, with no telemetry capture or public MCP expansion.

### External bootstrap and exact-version artifact continuation — 2026-10-18

This is the current continuation of the same work record. Earlier package and
missing-artifact observations remain historical. The current 29-file source digest
is `3a4ae051c1ddb2b0d395d56369f85c3538a9fd9a84a412ee38f273af08b8b207`.

`forecast_bootstrap.py` connects a source-only external escrow and root authority
to launcher adoption. Anchor and operator starts consume write-ahead permissions
before a manager intent; independent unit/manager identities and the original
absolute watchdog must already be bound. Adoption checks the issuer's retained
history over a private root peer channel, its pinned ELF/start identity, and the
operator PID/start identity. A producer receipt or caller-selected verification
callback cannot authorize adoption. Both starts debit existing ordinary prepare
exec slots: **two consumed slots, zero extra allowance**. Adoption resets neither
phase origin/deadline nor instrumented-read accounting. The actual immutable
`admission.py`, qualified issuer/manager backend and native watchdog accreditation
remain absent. No bootstrap, root actor or manager was started.

Static acquisition now includes an exact **6.12.113-1 arm64 cloud kernel** and
**Git 2.56.0-1.fc45 aarch64**, without changing the fixed core versions. Candidate
kernel image SHA256 is
`922795269a84ddb746fa7943c490c20a21903d976ac8d33a46f1c16ea142b92b`;
candidate Git ELF SHA256 is
`1182d6374f4657c910811458aaf32e1183e845143fddcbb13e70f85d47ee678c`.
They are candidate data hashes, not accepted profile pins. The kernel package's
signed Debian-security metadata chain was checked mathematically. Its config has
seccomp, cgroups and BPF/BTF enabled, but device mapper, verity and loop are modules;
matching module files are hashed, not loaded. Bootability and initramfs/kmod
closure remain unaccepted.

Git requires `PCRE2_10.47`; an exact aarch64 PCRE2 provider from its recorded
buildroot was acquired as a proposed provider. RSA signature mathematics checks
both immutable RPM headers against a pinned official Fedora key file/full signer
fingerprint. SHA256 bindings from those signed headers check **11 selected ELF
files**. This does not verify the whole RPM payload or accept publisher trust,
key certification/revocation/expiry or freshness. No downloaded ELF, script,
installer or maintainer hook was executed; no build or installation occurred.

The retained inventory now has **115 inspected ELF files**. A proposed resolution
table selects **114 files / 45,798,872 bytes**, retaining the prior PCRE2 bytes as
history. The version-table parser checks required/provided ELF version names
without invoking a loader. Still missing are `libudev.so.1` / `LIBUDEV_183`,
`libcrypto.so.4` and `libssl.so.4` / `OPENSSL_4.0.0`, `libcurl.so.4`, and an expat
provider exporting `LIBEXPAT_1.0.0`. Exact systemd261.3 manager/systemctl and matching
libudev were not located in the bounded Debian/Fedora queries; this is not a claim
of global absence. Full helper/non-ELF runtime, loader and source/build closure,
probe/compiler/object identities and image/verity/fit evidence remain pending.
No recursive acquisition or version substitution follows automatically.

Luna reviewed the corrected bootstrap authority, ELF version parser and RPM header
authentication deltas without residual actionable findings in that bounded scope.
**110 targeted software tests passed** for this current source. The preserved
sensitive validation passed **2,057 tests with 19 skips**, but belongs to the prior
28-file source digest `4f38e90d04c2733b5d3ded3c23078a8407becd0fd84d1a77c7a8d1c26c09c74c`;
it is not attributed to the later delta. No routine full-profile repetition was
performed. A stable PR profile remains a separate future integration requirement.

The existing evidence JSON and image contract retain receipt hashes and exact
observation scopes. The serial/parallel abort policies remain 3,843/6,662 Git
requests and 1,140/1,890 seconds; they are not measured minima, completion promises
or accepted operational budgets. `execAdmissionEnforced=false` remains fixed.
T001/T005/T008/T009 and all native, source, model, pilot, holdout, publication,
interpretation and adoption gates remain pending. Plugins #557/input B and telemetry
remain frozen; no profile, source capture, model or native admission control ran.

### Dependency closure and absolute bootstrap gate — 2026-10-18

The current continuation is `dependencyAndAbsoluteBootstrapContinuation` in the
same T005 evidence record. Source digest:
`af9299430b9bd2704d18df14b44373d381643f2776d4a8e2833547c226bef89d`
(**29 files**, private profile **v7**, bootstrap contract **v2**). Earlier candidate
results retain their own source identities; this continuation creates no launch
packet and accepts no original task criterion.

A finite acquisition of **24 additional aarch64 RPM packages** from Git's already
identified buildroot adds **9,216,448 archive bytes**. The 24 immutable-header RSA
signatures and SHA256 bindings for **71 selected regular ELF files** were checked.
This closes the previously missing OpenSSL4, curl, expat and their selected ELF
providers, including `libcrypt.so.2`. SSH requires `GLIBC_2.43`; proposed glibc2.44
and its matching loader replace providers only in the proposed resolution table.
All previous bytes remain retained. No installed profile, accepted dependency lock,
fixed Git/Python/systemd/kernel version or architecture was changed.

The retained inventory has **186 inspected ELF files**; the proposed table selects
**168 / 66,121,512 bytes** with no ambiguous SONAME provider. Its only missing
DT_NEEDED name is **`libudev.so.1`**, with `LIBUDEV_183` required by device mapper
and libfido2. This is selected-file, symbol-name closure, not loader acceptance:
`GLIBC_PRIVATE` ABI, actual paths, NSS/SASL/OpenSSL dynamically loaded modules,
non-ELF runtime files and the host-versus-worker-image inventory remain unaccepted.
There are now **52 retained package archives / 50 distinct packages /
62,625,382 bytes**. These host static-audit sizes are not VM scratch, filesystem fit,
peak memory or measured economic costs. The glibc inspection initially stopped at
a hardlinked non-ELF utility; the same pinned archive was reused for its selected
regular library/loader files. That stopped inspection is retained in the record;
no utility, downloaded program, installer or maintainer script was executed.

The exact upstream systemd261.3 release has no attached assets in the bounded
[release inspection](https://github.com/systemd/systemd/releases/tag/v261.3).
The Git buildroot contains systemd262, which was not acquired or substituted.
This is not a global absence claim. Exact systemd261.3 manager/systemctl and an
appropriate libudev provider still need an audited binary supply or a separately
authorized build route. No build follows automatically from missing artifacts.
Signature mathematics and selected-file hashes still do not accept publisher/key
certification, revocation/expiry, freshness, complete RPM payload or source/build
provenance.

Luna's bounded deadline review identified that `RuntimeMaxSec` starts from service
activation, rather than the original whole-flow origin. Context7's requested
v261.3 query returned main-branch source links; the relevant implementation and
unit semantics were therefore checked separately at the exact
[v261.3 service source](https://github.com/systemd/systemd/blob/v261.3/src/core/service.c)
and [v261.3 unit manual](https://github.com/systemd/systemd/blob/v261.3/man/systemd.unit.xml),
with hashes retained. BindsTo/After and Slice are lifecycle/placement controls;
they do not implement the missing independent absolute watchdog.

The source now requires **both** immutable `execAdmissionEnforced` and
`bootstrapSupervisionAccepted` gates before any bootstrap provider, authority IPC
or start; both remain **false** in the real profile. The watchdog contract binds
the original origin, scope, cancel and close deadlines, plan digest and a single
arming time no later than the first reservation. Root-provider readback is checked
before and after each start. Anchor joins the existing aggregate slice, and the
operator declares BindsTo/After anchor. No start or task allowance is added.

A failure after any admitted start, including a second-reservation failure, requests
one whole-scope cancellation. Its retained request binds nonce, plan, scope and
request time; cleanup must independently echo those bindings, observe the empty
scope after the request, and close before the original deadline. Unknown or late
readback remains unconfirmed, with no refund or automatic retry. Luna found and
the delta corrected acceptance of a replayed pre-cancellation empty readback.
The final bounded review has no residual actionable finding.

These software contracts **do not accredit** the actual watchdog/issuer/manager.
A blocked manager call must not block cancellation; issuer exit must revoke work.
The actual independent implementation, immutable entry, pre-held cgroup kill
capability, empty readback, and issuer/watchdog lifecycle costs remain missing.
They cannot be supplied by a client-selected callback, a unit hash or a reported
boolean. The outer supervisor's residency is not free or outside the accounting
boundary.

| Proposed abort policy | Serial | Parallel |
|---|---:|---:|
| Git requests | 3,843 | 6,662 |
| Original total wall seconds | 1,140 | 1,890 |
| Cancel no later than origin + seconds | 1,139 | 1,889 |
| Close by origin + seconds | 1,140 | 1,890 |
| Retained phase storage bytes | 713,326,592 | 1,384,415,232 |

The one-second whole-flow cleanup reserve is **inside** the existing total/terminal
allocation. Two bootstrap entries still debit ordinary prepare exec slots; total
exec policies remain 7,704/13,342. VM/worker/operator/aggregate memory, tasks, read,
output and scratch ceilings do not increase. These are abort policies, not measured
minima, completion promises or an accepted operational budget. The budget remains
blocked on the exact artifacts, authority/supervisor implementation and complete
cost/closure bindings above, plus probe/compiler/image/verity/fit evidence.

**115 targeted software/parser/mocked-control tests passed** on the current source.
The full sensitive profile remains obtained only for source4f38; the prior110
checks remain obtained only for source3a4a. Neither is relabelled as a full check of
this delta. Current planner output still selects sensitive validation; it was
inspected without repeating the broad suite. Stable PR validation remains pending
before integration. T001/T005/T008/T009 and all source/model/native/pilot/holdout,
publication, interpretation and adoption gates remain pending. #557/input B and
telemetry stay frozen; no capture, build, VM, profile activation or native control
was performed.


### Ephemeral supervisor and build implementation continuation (2026-10-18)

This continuation supersedes the current-state claims of the preceding section;
its source pins and test results remain historical. The v8 profile and v3 bootstrap
reserve **three** startup entries (supervisor, anchor, operator) from existing
prepare exec slots. They add no exec allowance. Root processes share a hard
512 MiB/16-task root slice; workers retain 2 GiB/64 tasks inside the original
3 GiB/96-task aggregate. Acceptance state no longer changes the reviewed unit
identity. The runtime still refuses unaccepted profiles before native effects.

`forecast_supervisor.py` retains no-follow cgroup kill/event descriptors for the
operator and workers, binds the original plan/origin/nonce and deadlines, and
attempts both revocations even if one fails. The anchor observes issuer exit,
malformed authority traffic and expiry independently of manager RPC. A late
watchdog still attempts cancellation but cannot accept late closure. The receipt
explicitly separates empty execution targets from the **unverified** exit of the
supervisor/watchdog and whole-flow cleanup. The external final observer remains
required. These are implementation paths checked with mocks, not native evidence.

`forecast_manager.py` and the source-only `fc1_manager_bridge.c` bind the root
private PID1 socket, a fixed six-unit roster, typed read-only properties and one
outstanding request. Starts consume their reservation before IPC and cannot retry
an ambiguous result. The bridge has not been compiled or loaded. The operator
entry named by the unit files remains missing: the modules are not an activatable
end-to-end native driver. An external owner guard must protect supervisor/anchor
startup, including the interval before the watchdog can be accredited.

`forecast_build.py` implements a data-only 25-role build lock and complete output
inventory comparison. It refuses missing roles, mutable/unpinned inputs, changed
recipes, repeated build identities and escaping output paths. Two declared equal
outputs do not accept clean builds, independent inventory or reproducibility.
The fixed proposed build envelope is **two 2-hour builds plus 1 hour inspection**,
1 CPU, 4 GiB memory and a 20 GiB VM disk, with no network during the actual builds
and no reused build directory. This is an abort ceiling requiring authorization,
not a measured minimum or a construction already performed. Lima/VZ installation,
VM creation and both builds remain behind their separate execution gate.

The bounded toolchain lookup keeps Koji buildroot71634011, repo6697092 and
event180107141. `clang` is supplied by llvm23.1.2-2.fc45; `sgdisk` comes from
gdisk1.0.10-6.fc45. Empty initial package-name queries remain in the diagnostic
record. Meson1.12.1, Ninja1.13.2 and the remaining selections are metadata candidates,
not authenticated artifact pins. There is no accepted 25-role lock yet. Kernel
headers7.2.4 in that buildroot do not replace the selected6.12.113 kernel UAPI.

The fixed completion sequence is:

1. Close the authenticated build/runtime file inventory, loader and dynamic-module
   resolution; obtain the exact systemd261.3/libudev build and source/object pins.
2. Complete the immutable native entry, external startup guard and final observer;
   bound PID1's systemd-executor/mount helpers before each start. A unit start is
   not evidence of only one native exec. If the bound cannot be established,
   retain a concrete blocker rather than expand the allowance.
3. Review the complete candidate and lock. Only then seek the separate VM/build
   authorization, perform the two builds and independent inventory comparison.
4. Seek the separate mechanism-accreditation authorization. Acceptance of its
   evidence does not authorize either fixed-input admission control.
5. Present the exact serial/parallel candidate hashes and phase budgets for the
   separate control authorization. Do not activate anything automatically.

The admission abort ceilings remain serial3,843 Git /7,704 exec /1,140 seconds /
713,326,592 retained bytes and parallel6,662 Git /13,342 exec /1,890 seconds /
1,384,415,232 retained bytes. No cost minimum or accepted operational budget can
be claimed while the lock, helper census and complete lifecycle binding are open.
No model, VM, native control, real-source capture, installation or build was run.
T001/T005/T008/T009, pilot/holdout and human interpretation/adoption remain pending.
The plugins and telemetry threads received this same boundary; #557/input B,
analysis-only MCP and aggregated telemetry stay frozen.

Validation is recorded in the matching machine-readable continuation. The broad
quick profile was stopped after detecting source-pin drift during the unclosed
candidate; it is failed/interrupted, not a pass. Previous full-profile evidence
remains bound to its old source. PR validation of the complete stable candidate
remains pending. This continuation creates no new experimental scenario or packet.


The preceding increment's source identity was `bf760ded9e0b32b0a2e30f518f30a87a4dcbc0d27e176ed3cb936133bb2b658c` (33 named sources).
Luna's focused read-only review reports no remaining actionable finding in this
delta; its native and scientific exclusions above remain open. Refreshing this
source pin only binds the static derivation, as separately checked by Luna; it
creates no image, artifact, grant or accepted-profile pin. **162 targeted checks
passed** for this source after updating the mock root-slice topology. The initial
targeted run caught that outdated mock and was corrected; no runtime control was
used to resolve it. The final log and static metadata receipts are hash-bound in
`ephemeralSupervisorAndBuildContinuation` in the existing accounting record.

The final Spec Kit structural gates and whitespace check passed. Semantic/human
review remains separate; the interrupted broad profile is not relabelled.


#### Current blocking disposition: manager jobs and terminal exec quota

The current v8 unit template is **rejected before native launch**. This is a
static admission-preparation finding, not a failed real control, experiment result
or utility verdict. The resumed T005 obligation and all other real gates stay open.

The bounded source census at exact systemd commit
`3255daee1572366b74fe92f002a3d60ecbb27103` established:

- [process-util.c:2015-2127](https://github.com/systemd/systemd/blob/3255daee1572366b74fe92f002a3d60ecbb27103/src/basic/process-util.c#L2015)
  permits libc/kernel fallbacks without CLONE_INTO_CGROUP. Attaching later cannot
  retroactively contain the executor's first exec.
- [execute.c:528-608](https://github.com/systemd/systemd/blob/3255daee1572366b74fe92f002a3d60ecbb27103/src/core/execute.c#L528)
  spawns systemd-executor; [exec-invoke.c:6693-6716](https://github.com/systemd/systemd/blob/3255daee1572366b74fe92f002a3d60ecbb27103/src/core/exec-invoke.c#L6693)
  performs the separate target exec. Both precede the worker's Python filter
  installation. Reserving just one event per unit does not cover them.
- The three mount units are separate manager jobs. [mount.c:1003-1053](https://github.com/systemd/systemd/blob/3255daee1572366b74fe92f002a3d60ecbb27103/src/core/mount.c#L1003)
  and [1597-1609](https://github.com/systemd/systemd/blob/3255daee1572366b74fe92f002a3d60ecbb27103/src/core/mount.c#L1597)
  allow an initial unmount attempt plus32 retries: **33 attempts**, each with
  executor and umount. One such campaign for each of three mounts accounts for
  up to198 execs. That subtotal is not a whole-flow upper bound: repeated jobs,
  failed exec attempts, RootImage and other helpers remain unclosed.

For **both fixed-input serial and parallel profiles**, terminal has zero Git
requests, hence its existing exec ledger permits `2*0 + 3 + 1 = 4` attempts.
Even a successful closure without retries has this known floor:

| Terminal work in the current route | Exec floor |
|---|---:|
| Terminal executor and worker | 2 |
| Terminal volume executor and mount | 2 |
| One executor and umount for each of three retained volumes | 6 |
| **Known floor, excluding other terminal work/helpers** | **10** |
| **Existing phase cap, with no lending** | **4** |

These are source-template/budget facts. No unavailable image or actual profile
identity has been replaced with a test placeholder. Increasing the aggregate Git
allowance cannot repair a phase-specific missing reserve or a pre-exec gap.

`RootManager.open()` and `request_start()` now independently reject the rendered
mount graph, implicit manager dependencies, additional control commands and the
known terminal shortfall **before** native reads, library loading or StartUnit.
Commented/duplicate DefaultDependencies declarations and indented control commands
cannot bypass this necessary check. Passing a future graph check alone would still
not establish native pre-exec enforcement; immutable readiness gates remain in force.

Luna confirmed the source findings, the 4-versus10 contradiction and the stop gate.
The plan's stop rule applies: **no build/install/VM request, partial manager patch,
new driver candidate, quota increase or automatic alternate attempt** is prepared
on this route. The build lock and immutable driver remain incomplete. Technical
resumption requires a concrete replacement of the uncovered launch/mount path with
independently reviewed pre-exec and lifecycle coverage within the retained limits;
this record does not authorize or prepare that replacement. Forecasting utility
has not been evaluated or rejected by this infrastructure finding.

The same existing machine-readable continuation contains the source inventory,
individual hashes, lookup failures, review and final targeted-test receipt. No new
scenario or evidence package was created. Broad sensitive/PR validation remains
pending; the previous interrupted run is not promoted to a pass.

Final source identity for this stop gate: `b30e1279b6bc11c658754a3cc432c21f970cea9757d5b0a7eced650dc515ad8e` (33 sources).
**166 targeted software/parser/mocked-control checks passed**. Repository, contract,
release-record and Constitution-replica checks passed; Spec Kit preflight passed.
No full-profile pass or native acceptance is claimed. Plugins and telemetry were
synchronized with this stop disposition; their frozen boundaries remain in place.

#### Authorized v9 redesign: source implementation stopped on dependency closure

The owner subsequently authorized the bounded replacement described in the plan:
root-owned syscall mounts instead of mount jobs, a minimal patch to exact systemd
261.3 commit `3255daee1572366b74fe92f002a3d60ecbb27103`, and prospective
redistribution between disjoint escrow and broker quotas without increasing the
aggregate. That authorization supersedes the previous paragraph's statement that
no replacement was authorized. It does not accept or activate a profile.

The private source implementation now contains:

- `forecast_exec_budget.py`: escrow phases `[9,0,0,2,2]`, broker `2*Git+1`,
  write-ahead consumption, original-flow time reserves and no quota lending.
- `forecast_mounts.py`: a root-owner component that verifies PID1's mount
  namespace, reads back exact tmpfs quotas and identities, and attempts each
  unmount once without lazy detach. It retains uncertain syscall outcomes.
- `forecast_systemd_patch.py` and `research/native/fc1-systemd-2613.patch`: a
  deterministic, exact-input transformation of seven pinned upstream files plus
  three private source additions. PID1 and the executor have separate CLOEXEC
  channels. The patch retains the executor channel outside `params->fds`, requires
  CLONE_INTO_CGROUP, refuses its fallbacks, and uses one final `execveat` attempt.

The patch applies to the retained exact upstream sources. No C source was compiled,
loaded or executed. Those properties are source intentions reviewed by Luna, not
native enforcement or proof of a bootable candidate.

The source inventory now binds all 40 named files at
`800d39c8ec63ad0555467734402bf1e5a94ad73eee10e8306ab64b03c8d3aadf`.
The old b30e stop-gate receipt remains historical evidence. Refreshing the source
pin does not accept coverage or change the Git caps.

| Prospective allocation | Serial phases | Parallel phases |
|---|---|---|
| Exec attempts | 3596 / 1539 / 2051 / 515 / 3 | 4108 / 2051 / 4101 / 3079 / 3 |
| Total | 7704 | 13342 |
| Retained flow wall limit | 1140 seconds | 1890 seconds |
| Retained storage limit | 713326592 bytes | 1384415232 bytes |

These allocations are not executable budgets. The new ledger and mount owner are
not yet integrated into a v9 driver/profile. The current renderer remains v8 and
its independent pre-launch refusal is preserved.

**Current disposition: stop under the approved unknown-helper/cost rule.** Luna's
bounded source review found no concrete FD-shifting defect or obvious incompatibility
with the retained headers. It could not close two dependencies:

1. `namespace.c:2670-2723` still reaches `dissected_image_decrypt`. The verity
   path in `dissect-image.c:3380-3431` loads libcryptsetup and calls crypt_init,
   crypt_load and activation. The exact libcryptsetup/libdevmapper transitive
   chain is not fixed and reviewed. This is an unknown helper/cost boundary,
   **not evidence that an extra exec occurred**.
2. Restricting User/Group to numeric IDs does not itself prove that the retained
   `get_user_creds`/`get_group_creds` path avoids NSS. The patch comment now makes
   that limitation explicit.

The root escrow server must additionally bind any reply deadline to the original
retained flow deadline. The client's current-clock comparison alone cannot prove
that binding. The server, immutable owner/start guard/final observer, typed manager
replacement, v9 unit graph/v4 bootstrap, v2 launcher integration, dependency/build
lock and whole-flow lifecycle budget remain incomplete. No ready admission
candidate, v9 profile identity, build request or alternate runtime is emitted.

179 targeted software/parser/mocked-control checks passed. The first targeted run
exposed a stale timestamp-based Python bytecode cache after the equal-length pin
edit; removing that single local cache resolved both drift errors without changing
source or weakening the drift gate. The repository quick profile escalated to
sensitive. Its full-test discovery had already imported the stale bytecode before
that cache was removed, retaining the same two drift errors in the running
interpreter. The exact owned test process was interrupted after cwd verification;
there is no broad-profile pass and no broad rerun. Repository, contract, release,
portable publication, research-radar, adoption-track, market-model and CLI checks
completed before interruption. Final changed-record repository/contract/release,
Spec Kit structural and whitespace checks passed. A stable PR profile remains
pending because the admission candidate is not ready.

The plugin track completed read-only support at `086901fed1a957271727a4bb4dc1b23790499829`.
Its existing explicit runtime mode/grants do not authorize FC.1, and its alpha.2
bundle does not provide the required Linux aarch64 environment. The telemetry
track completed read-only support at `b2cf477fe9f9d586d6431ae9ed9a14abb3266706`:
daily aggregates cannot substitute for private causal windows or lifecycle receipts;
no concrete new receipt schema was accepted. Both products remain frozen.

T001, resumed T005, T008, T009, source consent, native admission, model, pilot,
holdout, human interpretation and founder promotion remain pending. There were
no builds, VM launches, profile activations, native controls, model invocations,
real-workload executions or telemetry captures. No new scenario or equivalent
approval package was created. This implementation stops here; the next technical
work must dispose of the two named dependency boundaries before driver integration
or a concrete build/execution proposal can proceed.

#### Dependency continuation: credential bypass and constrained library/kernel sources

The owner expressly resumed the two dependency findings. The implementation now
closes the reviewed credential route in source and fixes the library build
conditions. It does **not** declare an emitted, booted or admitted v9 profile.
The preceding stop record and its interrupted validation remain historical.

The exact systemd `user-util.c` confirms that non-root numeric `get_user_creds`
still invokes `getpwuid`; `get_supplementary_groups` can invoke `initgroups`.
The FC.1 patch now assigns validated decimal UID/GID directly, keeps a numeric
username, clears inherited supplementary groups with checked `setgroups(0,NULL)`,
and bypasses all three credential/group lookups. It requires explicit equal
User/Group compatible with the root/worker role and `SetLoginEnvironment=no`.
PAM, dynamic identity, supplementary groups, shell/control flags and
`WorkingDirectory=~` are refused. Non-FC.1 credential lookup remains unchanged.
Luna found no residual NSS path in this reviewed route, conditional on the
validated context reaching the executor. The C code has not been compiled.

The private build policy fixes these source identities and constraints:

| Component | Exact source | Required exclusions |
|---|---|---|
| cryptsetup 2.8.8 | `f1dbcce190719c9e177e8fbaf3df0b908f87d920` | udev, external tokens, SSH token and Argon2 disabled; kernel crypto backend |
| libdevmapper 1.02.205, LVM2 2.03.31 | `3a6e221c569eb253fa38a772b15e53b5de65b5d1` | dmfilemapd, udev synchronization/rules and libudev disabled |
| Linux 6.12.113 | `7fdb7c1824a1f9979d648d7ae28ac446bcee9c6e` | no modules, no uevent helper, static usermode-helper path empty; required storage/crypto features built in |

The known direct libdm fork/exec path is behind `DMFILEMAPD`. The external token
loader in cryptsetup is excluded by `USE_EXTERNAL_TOKENS`. The CLI's `dmsetup
--exec` path remains outside the sole root-broker `table --target verity` command;
dmsetup is not a systemd/worker-image helper. These are bounded source findings,
not a universal proof that arbitrary library entrypoints cannot launch processes.

The kernel choice removes a runtime modprobe dependency: with
`CONFIG_STATIC_USERMODEHELPER=y` and `CONFIG_STATIC_USERMODEHELPER_PATH=""`, the
pinned `kernel/umh.c:368-422` replaces the helper path and returns before queuing
helper execution. `CONFIG_MODULES=n` and `CONFIG_UEVENT_HELPER=n` supplement that
boundary. Literal .config checks also require loop, dm-verity, ext4, devtmpfs,
SHA256 and AF_ALG hash support built in. This is a configuration requirement for
future artifact verification; no running kernel was read or changed.

Userspace udev needs a separate immutable-host condition. Exact systemd source
installs `systemd-udevd` as an alias of **udevadm**, so excluding only the daemon
pathname would be insufficient. The independent host census must exclude that
executable identity, all aliases/copies, activatable units and executable rules.
Build flags alone do not establish that absence. No host-image census or bootstrap
acceptance is claimed.

`build_recipe_v2` binds the two actual source-archive hashes and lengths and adds
the libdevmapper source role. Its 26-role inventory retains the two builds, 18000
seconds, 4 GiB RAM, 20 GiB disk and 8 GiB aggregate input cap. v1 remains
reconstructible. Literal dependency-header checks reject enabled, missing,
duplicate, conditional and indirect macro settings, including C line splicing
before comment removal. The inspectors deliberately keep header use, crypto
backend object selection, emitted/booted kernel and native acceptance unverified.

The actual source archives were inspected as data only. Their hashes identify
source bytes; they are not Linux ELF hashes, publisher-authenticity approval or
evidence of source-to-object correspondence. No downloaded candidate library was loaded,
and no candidate C/BPF source or image was executed. The software-validation
scope deviation below must not be hidden by that narrower statement.

Luna reviewed the source closure, actual credential patch, inspectors and recipe
integration. The review's line-splicing finding was fixed and covered by a targeted
regression. No residual finding remained in those deltas. The accounting entry
`v9Redesign.dependencyClosureContinuation` retains the source inventory, precise
review scope and validation disposition without replacing earlier evidence.

Current source identity: `98a80a135564d049947695fa3fbabf6280cdae9b104b17eaf1b61c964c4984c5`
(40 files). Git and prospective exec allocations, 1140/1890-second admission flow
limits and 713326592/1384415232-byte retained storage caps are unchanged. No
allocation is promoted to execution authority or a measured minimum.

The remaining technical boundary is now explicit: emitted dependency/link and
provenance locks, source/config-to-object correspondence, kernel/host readback,
the immutable owner/escrow/watchdog/final observer, typed manager integration and
whole-flow accounting. Those are still required before emitting an artifact-bound
v9 profile or presenting native controls. No ready native candidate, profile
activation, grant, source capture, model, pilot, holdout or acceptance is implied.
T001, T005, T008, T009 and the human/founder gates stay pending. Plugins and product
telemetry remain frozen and receive only this bounded coordination disposition.

Validation of this continuation: **189 targeted tests passed**. The general quick
profile escalated to sensitive and was interrupted after it reached existing
native-predictor unit tests that call synthetic fixture `fit`/`score`. Invoking
those tests exceeded the owner's no-model boundary; this was acknowledged and
the exact owned test process was stopped after cwd verification. The synthetic
call count was not individually metered. No Chronos/optional model artifact was
loaded, no real forecasting/source run or native admission control occurred, and
those unit results are not admission or utility evidence. There is **no complete
sensitive/PR pass**. Repository, contracts, release, portable publication,
research-radar, adoption-track, market-model and CLI checks completed before the
interruption. Future validation under this authorization must exclude full
discovery and any profile that invokes model-fitting/scoring tests; the full gate
stays pending. It must not be silently downgraded or rerun unchanged.

Final model-free repository, contract, release-record, Constitution-replica,
Spec Kit structural and whitespace checks passed. These do not replace the
interrupted full profile or accept semantic, human or native gates.

### Bounded staged-host and driver continuation

The current continuation adds three private modules to the same source inventory:
`forecast_host_census`, `forecast_manager_escrow` and `forecast_v9_driver`. It does
not create a new forecasting scenario, execution package, public envelope or MCP
capability. Earlier source identities and the validation-scope incident above
remain history; this lot does not reuse the interrupted general run as acceptance.

The offline census requires an externally pinned manifest and walks **all**
entries of an explicitly selected staging tree using retained directory FDs. It
rejects undeclared/hidden files, missing entries, links, special files, foreign
ownership and writable modes. It hashes every file, including non-executable
copies of forbidden ELF identities, and checks architecture and the recorded
kernel/dependency configuration requirements. Nonblocking, no-controlling-terminal
opens prevent a raced FIFO from blocking before fstat. Limits are 4,096 files,
4,096 directories, 8,192 entries, depth 16, 128 MiB per file and 480 MiB aggregate;
none expands the retained operational quotas. Aliases must be flattened within
those caps. Publisher authenticity, complete dependency resolution, source/object
correspondence, future immutability and running-host state remain unverified.
No real Linux staging tree or live host was inspected in this continuation.

The private escrow decodes the actual 152-byte C request and 32-byte response ABI.
It validates per-message SCM_CREDENTIALS rather than creator credentials, disposes
of all unexpected SCM_RIGHTS descriptors, and binds PID/start, executable, UID/GID,
cgroup, role and invocation. It reserves before replying from the existing escrow
partition `[9,0,0,2,2]`; it cannot spend the broker partition. Unknown or late replies
remain consumed and poison the session. The full request and listener close share
a lock. Closing revokes the state before withdrawing the listener and preserves
cleanup uncertainty; it does not certify whole-flow cleanup. Neither completed
permit pairs nor an external-owner accounting entry prove successful target exec
or a pre-exec owner guard.

The driver freezes staging/source/inventory/provenance identities, executor pin,
UID, nonce, allocation and phase seconds. Its broker and escrow advance together
against the original monotonic deadline. Expired phases, outstanding attempts,
quota failure, drift and unknown outcomes stop the session without refund or
restart. Finishing accounting is separate from native acceptance. Its native
entry always refuses, even if the existing bootstrap readiness check is changed;
there is no caller-selected authority or boolean override. This is preparation
and accounting code, **not the qualified native driver**. The existing v8 unsafe
job-graph refusal remains intact; no v9 profile identity has been emitted.

Luna reviewed only this new delta and the focused corrections: nonblocking census
reads, phase expiry, transaction serialization, late replies and close ordering.
The new identity regression also exposed omitted phase durations; those are now
part of the frozen identity. In total 21 distinct new model-free software cases
passed across the focused slices and affected-case fixes. The prior 189 cases and
five initial census cases were not rerun unchanged; there was no general suite,
profile activation, native admission control, model, workload source or forecasting
experiment. These cases use owned temporary data and fake transport/process facts;
they do not substitute for Linux qualification.

The existing admission ceilings remain 7,704/13,342 exec attempts,
1,140/1,890 seconds and 713,326,592/1,384,415,232 retained bytes for serial/parallel.
They remain provisional allocations, not measured minima or authorization. The
next technical dependency is actual emitted Linux artifacts with complete
link/dependency/provenance locks and independently checked source/config-to-object
correspondence. Qualified immutable owner entry, absolute watchdog, final observer
and v9 manager/broker-launcher integration still follow before a concrete native
candidate and operational budget can be accepted. This authorization performs
none of those native actions. T001, T005, T008, T009 and all source, execution,
human and founder gates remain pending. Plugin and telemetry product bytes remain
frozen; both tracks receive this disposition without new tasks or approval loops.

Current source identity for this continuation: `6ef1abb0e14daecb23afe9d39ddf630a3f6b40fdb0d6a9ddc1d45c2972d399da`
(43 named source files). AST, JSON, exact source pin, pending-gate, Constitution
replica and whitespace checks passed. The successful Spec Kit preflight from this
lot is reused; general/PR validation remains pending under the owner boundary.
The final disposition was delivered to both coordinated conversations.

### Offline v9 graph, bootstrap v4 and broker v2 composition — 2026-10-18

The owner authorized continuation in the preserved checkout, limited to offline
software. `offline_v9_plan` composes a prospective six-role graph with the frozen
driver preparation and disjoint allocation. `offline_bootstrap_v4` binds that graph,
nonce and original deadlines. Its bootstrap scope ends at the operator: one owner
entry plus three pairs consumes seven escrow attempts; the later prepare pair
consumes two more, exactly the existing phase-zero allocation of nine. Bootstrap
charges no broker startup slot. Mount lifecycle is assigned prospectively to the
root syscall owner; no mount jobs, unit text or Linux v9 profile are emitted.

`OfflineV9Integration` shares one driver with one `OfflineBrokerV2` adapter. The
adapter keeps the driver's lock and broker partition, requires preceding escrow
pairs, binds role/PID/start facts, rejects duplicate adapters and cross-phase
notification replay, and retains consumed unknown outcomes. These are explicit
invented/recorded facts in an offline accounting API, not authenticated launcher
identities or an implementation of native listener transport. The v8 renderer and
its independent unsafe-graph rejection remain intact, as does the unconditional
native-entry refusal even when bootstrap readiness is mocked.

Ten distinct new model-free cases passed in bounded slices: plan/budget/clock
binding, mixed profile refusal, prerequisite/replay failure, disjoint startup
charges and detached receipts, cross-phase notification replay, process/deadline/
unknown outcome failure, preserved native and v8 gates, worker phase isolation,
single adapter ownership, and five-phase accounting. The plan case was rerun after
clarifying bootstrap scope. A targeted mutation disabling notification replay was
detected by its regression case and the source was restored. No prior suite was
rerun. Spec Kit structural preflight passed before edits. General quick/PR/sensitive
profiles remain pending under the owner restriction, not waived.

Luna (`gpt-6-luna`) reviewed only the new offline delta by inspection. Its bootstrap
scope ambiguity was clarified with the explicit 7+2=9 breakdown; follow-up review
confirmed closure with no residual finding in that correction. Review does not
accept native enforcement, host provenance or economic utility. Logs and exact
scope are recorded in `v9Redesign.offlineGraphIntegrationContinuation` in the same
accounting record; earlier continuations and the historical model incident remain.

Current normalized source identity is
`029ea0218dd67e287e75c24b07fcecaaf2a702e425110e825c80d844302c7bab` (43 files).
The refreshed pin identifies bytes only. Executable v9 rendering, native transport
and typed manager integration, emitted objects and independent correspondence,
booted-host immutability, owner guard/watchdog/final observer and complete lifecycle
budget remain pending. No builds, models, real workload sources, native controls
or live-host census occurred in this lot. No task/milestone or acceptance gate is
closed, and the plugin/telemetry products remain frozen.

### Offline v9 unit-text renderer integration — 2026-10-18

The owner authorized the renderer continuation without builds, models, real
workload sources or native controls. `forecast_v9_renderer` returns a detached
draft of six service units and three slices. It reuses the existing v8 service
bodies and slice quotas, replaces the explicit unit ordering, drops mount jobs,
and retains a root-syscall-owner mount assignment. It sets numeric User/Group,
SetLoginEnvironment=no, DefaultDependencies=no, one ExecStart, no restart/control
commands and null stdio. Relative runtime/start/stop directives fit the retained
windows; they do not implement an absolute outer watchdog. No unit is installed,
loaded, parsed by systemd or activated. This draft is not a new admission profile:
the v8 manifest, namespace identity and independent unsafe-graph refusal remain.

Each unit's exact text hash, the unit-set digest and renderer source hash enter
the graph. Bootstrap v4 requires the exact six-service/three-slice hash roster and
binds the graph digest; broker-launcher v2 retains the same integration identity.
Receipts expose unit-set/bootstrap digests and poison the driver on replaced plan
bytes or a diverging broker identity before returning hashes. The native entry
still refuses unconditionally after its existing bootstrap gate.

**The manager graph remains blocked.** DefaultDependencies=no does not remove all
implicit dependencies. RootImage/WorkingDirectory can still add path-to-mount
requirements, RootImage adds ordering on udev, and slices retain parent activation.
Booted-manager aliases, generators and drop-ins are unobserved. The renderer lists
these unknowns and leaves nativeGraphClosed=false. The earlier graph's prospective
implicitDependencies=false field is replaced with implicitDependenciesClosed=false;
absence of explicit mount jobs is not a claim of resolved native dependencies.
See the official [systemd execution documentation for the 261 series](https://www.freedesktop.org/software/systemd/man/261/systemd.exec.html)
and [slice dependency documentation](https://www.freedesktop.org/software/systemd/man/latest/systemd.slice.html).
Context7's resolver returned a monthly-quota error. The fallback execution page
identifies 261.2 and the slice page 262; neither qualifies exact 261.3 emitted
objects, dependency closure or loaded behavior.

Eighteen distinct targeted software cases passed across bounded slices: eight new
renderer cases and ten materially affected offline integration cases. The initial
17-case run had 16 passes and one incorrect test expectation locating MemoryMax
on each worker service; the configured budget lives on the workers slice. The
corrected test checks the slice and preserved isolation bindings and passed alone.
The new receipt-drift case and three affected healthy receipt cases passed after
the guard was added. A tight-window regression detected temporary weakening of
the start/stop reserve; the exact source was restored. Logs and all attempts are
recorded in `v9Redesign.offlineRendererContinuation`. No full-suite pass is claimed.

Spec Kit structural preflight passed before edits. Luna (`gpt-6-luna`) inspected
only this delta and the receipt-drift correction, finding no concrete residual
issue in that scope. Structural checks and review do not accept native enforcement
or economic utility. General quick/PR/sensitive profiles remain pending under the
owner restriction; previous suites and unchanged scenarios were not repeated.

Current normalized source identity is
`ff952e45495d8bd343b1b7cfcc4590a138dd6aebcef67977f70a823aeeaf489a`
(44 files, adding the private renderer). The pin identifies current bytes only.
Actual Linux objects and independent source/config-to-object correspondence,
immutable booted host, qualified native transport/manager/owner guard, original
watchdog and final observer, and complete CPU/memory/time/storage/lifecycle budget
remain pending. All admission, utility, workload-evidence and execution gates remain
false. Earlier records and the historical model-scope incident are preserved;
plugin and telemetry products remain frozen.

### Bounded offline dependency continuation — 2026-10-19

The owner requested offline closure of implicit renderer dependencies while keeping
the checkout and all gates. The renderer now explicitly orders and requires each
service's existing slice. This promotes 12 expected service-to-slice relations;
it does not pull another service into the declared activation graph. The three
slice-parent relationships were already explicit. A bounded syntax inventory
checks the nine-unit roster and enumerates 23 declared After/Requires edges. The
only external target in that **declared local roster** is `-.slice`; this does
not mean it is the only dependency the native manager could add.

`offline_dependency_inventory` rejects unreviewed directives/sections, duplicate
singleton directives, continuations, changed defaults/type/stdio and drifting
After/Requires/Slice relations. Its allowlist deliberately covers only the current
renderer grammar, not the systemd language. Exact unit hashes bind the inventory;
its digest enters the renderer, graph, bootstrap and broker integration identity,
and is exposed by the guarded receipt. Neither the parser nor its digest supplies
host facts, a native unit loader or semantic dependency resolution.

Selected retained source observations were read without new downloads. The stored
API content and Git blob hashes match `systemd2613-service.c` and
`systemd2613-unit.xml`; their SHA256 identities and evidence limits are recorded in
`v9Redesign.offlineDependencyContinuation`. `service_add_extras` calls
`unit_add_exec_dependencies` and `unit_set_default_slice` separately from
`service_add_default_dependencies`. The retained unit documentation distinguishes
disableable default dependencies from implicit dependencies that remain in force.
This is source/document inspection only, not emitted-object or publisher acceptance.

**Stop: complete offline closure is not established.** The full owning
implementations of those two dependency functions are absent from the selected
retained audit. No mount-topology witness resolves RootImage, WorkingDirectory or
bind paths to actual loaded mount units. RootImage ordering on udev is retained
as an ordering obligation, not a claim that this After edge activates udev.
Root-slice state, manager aliases, generators and drop-ins remain unobserved.
The inventory therefore keeps offlineClosure=false and nativeGraphClosed=false.
No isolation directive was removed, no source patch or recipe was expanded, and
no host/topology receipt was invented to evade these unknowns.

Six new dependency cases, eight affected renderer cases and two affected
integration cases passed in bounded slices (16 distinct software cases).
A regression detected temporarily disabling the Requires-target check, and the
exact source was restored. Logs are recorded in the same accounting child. Spec
Kit structural preflight passed before edits. Luna (`gpt-6-luna`) reviewed only
this delta by inspection and found no concrete defects in the local edges or
digest binding, explicitly preserving the parser's limited scope. No general/full
suite was executed; quick/PR/sensitive profiles remain pending under the owner
restriction, not waived.

Current normalized source identity is
`0799361a051555a0701f3d26d2264265f38859bcb2370ce38a0da30e8c9c4f53`
(44 files). The pin identifies bytes, not accepted closure. All profile, native,
budget, workload-evidence, utility and execution gates remain false/pending.
There were no builds, models, real workload sources, native controls, live-host
census or source downloads in this lot. Earlier continuations and the historical
model-scope incident remain intact; plugin/telemetry products remain frozen.

### systemd 261.3 dependency-function source review — 2026-10-19

The owner authorized offline review of the two named functions and useful synthetic
fixtures while retaining every execution gate. The missing technical source file
was retrieved as text from the already fixed systemd commit, without workload
access or compilation:
[src/core/unit.c](https://raw.githubusercontent.com/systemd/systemd/3255daee1572366b74fe92f002a3d60ecbb27103/src/core/unit.c),
260,528 bytes, SHA256
`dbff1f6b10c7ff433bfb5ddbe919b2fc8e450a87105b451cd0370851da355907`.
The retained copy and per-function ranges/hashes are recorded in
`v9Redesign.unitDependencySourceReviewContinuation`. Both requested bodies and four
adjacent slice/mount helpers were inspected. No upstream C patch was changed.

The source distinguishes WorkingDirectory mount requests (Requires, or Wants for
missing_ok) from RootImage (Wants). BindPaths/BindReadOnlyPaths have no direct branch
in that function and remain separate namespace/topology obligations. An already
resolved slice skips default selection; declared Slice text does not establish
that resolution. Path-prefix registration and deferred mount loading still depend
on manager state. The inventory now records these distinctions, unobserved resolved
slices and null mount targets, with literal-only path projection. It retains the
fixed source identity and effectiveContextVerified=false.

The earlier missing-function-source stop is now historical, not a current blocker.
Current blockers are effective-context/configuration binding, deferred mount
resolution, topology, loaded manager aliases/generators/drop-ins, immutable host,
objects/source correspondence and complete lifecycle budget. Reading function bodies
does not close those obligations or authorize a native control. Inventory v2 is a
bounded projection of the current renderer subset, not a C execution/emulation or
complete systemd graph resolver. All admission and acceptance gates remain false.

Four new software cases and eight affected cases passed in bounded slices (12
distinct cases). A synthetic -/work variant distinguishes missing_ok from the
ordinary WorkingDirectory request; it supplies no mount observation. Two separate
mutants, RootImage incorrectly classified as Requires and missing_ok ignored, were
detected by their named regressions; exact source was restored. Existing graph,
bootstrap and broker hash bindings still passed. Logs retain every attempt in the
same accounting child. No full-suite/general discovery or forecasting scenario was
run; quick/PR/sensitive profiles remain pending under the owner restriction.

Spec Kit structural preflight passed before edits. Luna (`gpt-6-luna`) independently
inspected the source and then the inventory/test delta. It confirmed the new
classifications; a range-coverage precision was closed by reading the remaining
unit_add_mounts_for lines through 5197. The parent verified the source hash; the
reviewer did not rehash or execute anything. This review accepts no native behavior,
scientific result, publisher authority or operational budget.

Current normalized source identity is
`6dfe0fe321e8b3f59622d8ef6d50b1ed8617d3774b0f7777f424732ff3f966f4`
(44 files). The checkout and previous continuations are preserved. This lot ran no
builds, models, real workload sources, native controls or live-host census; one
upstream technical source file was retrieved for text inspection. The historical
model-scope incident remains recorded, and plugin/telemetry products remain frozen.

### Slice assignment and manager-context source review — 2026-10-19

The owner authorized the offline review and useful synthetic fixtures while
preserving the checkout and all gates. Five technical source files were retrieved
as text from the same fixed systemd commit: load-fragment.c, its gperf input,
unit.h, manager.c and unit-dependency-atom.c. Existing unit.c/execute.c were reused.
Hashes and bounded review ranges are recorded in the same accounting child,
`v9Redesign.sliceManagerContextReviewContinuation`, with a retained audit copy at
`/private/tmp/fc1-linux-bundle-audit-20261018/slice-manager-context-review-20261019.json`.
Partial initialization excerpts are explicitly distinguished from complete function
inspection. No C source patch or emitted object was changed or run.

The Slice directive maps to config_parse_unit_slice, which expands the name, loads
configuration and attempts unit_set_slice. Failures can be warned and ignored with
return0. unit_set_slice records UNIT_IN_SLICE, whose atom is UNIT_ATOM_IN_SLICE;
UNIT_GET_SLICE queries that relation. Declared After/Requires is not this placement
proof. Loading also involves caches, queues, merges and a recursion guard; successful
return alone does not prove effective configuration or startability. Inventory v3
therefore requires distinct assignment/load/merge/context observations and keeps
all of them unverified.

**Additional source-level blocker discovered:** unit_patch_contexts can add
After+Wants dependencies for modprobe@loop.service, modprobe@dm_mod.service and
modprobe@dm_verity.service when exec/cgroup contexts, active device policy and
image setup are present. PrivateDevices can promote AUTO to CLOSED. For the three
currently declared worker RootImages, the inventory now retains 18 conditional
arcs (nine Wants, nine After), without claiming any manager activation. Built-in
kernel components do not delete these source-level job requests. These jobs are
not accepted as covered by the existing role/exec budget. Isolation directives
were not removed to suppress the finding.

The graph field now states automaticServiceStartsClosed=false, replacing the
broader automaticServiceStarts=false assertion; explicit unit-text service
activation edges are still separately represented. This distinction prevents the
absence of declared service pull-ins from hiding context-generated jobs. Effective
context, alias/drop-in provenance, placement, topology, helper closure and full
lifecycle cost remain blockers. No ready candidate or closure is inferred.

Three new fixture cases and 12 affected cases passed in bounded slices (15 distinct
software cases). The synthetic PrivateDevices=no case retains the device-policy
uncertainty, while removing a declared RootImage changes only the text projection;
that counterfactual is not an admitted or startable replacement profile. A mutation
that wrongly suppresses the module family for PrivateDevices=no was detected by
its named regression and the exact source was restored. Graph/bootstrap/broker
binding cases passed. Logs retain each attempt in the accounting record.

Spec Kit structural preflight passed before edits. Luna (`gpt-6-luna`) independently
found the missing conditional family, then confirmed its correction in inventory
v3 with no concrete residual finding in that delta. It ran no tests or validations.
No general/full-suite validation was run; quick/PR/sensitive remain pending under
the owner's restriction, not waived. Source inspection and synthetic fixtures are
not loaded-manager observations or native qualification.

Current normalized source identity is
`6ad18b9838e1d98aef73a32ed0ad5df94e9c5045b70267aeef493954fec28d16`
(44 files). All native/profile/budget/workload/utility/execution gates remain false.
There were no builds, models, real workload sources, native controls or live-host
census in this lot. Previous continuations and the historical model-scope incident
are preserved; plugin and telemetry products remain frozen.

### modprobe dependency and budget source review — 2026-10-19

The owner authorized offline review and useful synthetic fixtures without changing
execution authority. The retained audit adds three technical text sources from the
same fixed systemd commit: units/modprobe@.service, units/meson.build and
src/shared/condition.c. An initial .service.in probe returned404; the actual
upstream template is .service. Exact paths/hashes and review limits are recorded in
`v9Redesign.modprobeBudgetReviewContinuation`, with the retained audit at
`/private/tmp/fc1-linux-bundle-audit-20261018/modprobe-budget-source-review-20261019.json`.
No source was compiled or loaded and no modprobe command was run.

The template is included without a HAVE_KMOD guard on its Meson entry. Its oneshot
command is failure-ignoring, uses a bare executable name, has no RemainAfterExit,
and disables start rate limiting. Capability and negated module-loaded conditions
can skip a start. The capability predicate uses the manager's bounding set; an
empty worker CapabilityBoundingSet does not supply that observation. The module
predicate reads sysfs/initstate; a built-in source configuration is not that runtime
observation. Even a skipped command does not prove zero full-flow cost.

Nine conditional Wants references are not nine observed starts. They target three
instances which may coalesce, skip or reactivate. They also do not match any of
the six FC1 gate roles. Their placement, binary search path, exact modprobe binary,
transitive behavior and helper/command-hook costs are unqualified. Existing escrow
or spare broker allowance cannot be treated as coverage for those external jobs.
Ignoring an exit failure does not erase an attempted exec or prove cost-free work.

`module_dependency_budget`, integrated into inventory v4, now records that gap.
Under an explicitly hypothetical two-exec-per-start assumption, one start of each
of three distinct targets gives a subtotal of six attempts. Starting all three
once at each worker site gives 18 and phase extras [6,0,0,6,6]. **Neither illustration
is an upper bound, measured minimum, accepted operational budget or authorization.**
Actual activations and complete cost/attempt upper bounds remain null. All existing
allocations are unchanged: 7,704/13,342 prospective serial/parallel attempts,
escrow [9,0,0,2,2], fixed overhead [10,1,1,3,3]. No added allowance or broker loan
is issued. The Cpatch, build recipe and role roster remain intact.

Five new budget cases, thirteen affected dependency cases and two affected binding
cases passed in bounded slices (20 distinct software cases). Synthetic projections
of one site, three sites and no sites check reference/target accounting without
inventing manager observations. Malformed/replayed projections and claimed native
facts are rejected. A mutation confusing repeated references with distinct targets
was detected by the counterfactual fixture and exact source was restored. All
attempt logs are retained in the same accounting child; no forecasting scenario
or general/full-suite test was executed.

Spec Kit structural preflight passed before edits. Luna (`gpt-6-luna`) independently
reviewed the source and advisory delta without executions. It confirmed the limits
and found no concrete defect in the delta. quick/PR/sensitive profiles remain
pending under the owner restriction, not waived. Unknown activation, transitive
helper cost and pre-exec coverage remain stop conditions before any native candidate.

Current normalized source identity is
`a410879956b69a7b33107d346ca448b3ac94dfff81ad31bee8fbe7d1d4bf548b`
(44 files). All profile/native/budget/workload/utility/execution gates remain false.
The checkout, prior continuations and historical model-scope incident are preserved;
plugin/telemetry products remain frozen. This lot ran no builds, models, real
workload sources, native controls or live-host census.

### modprobe pre-exec coverage source review — 2026-10-19

The owner authorized offline review without quota expansion. The existing source
paths were inspected without additional source downloads. Exact hashes of the
Cgate/policy, source transformer, receiver, launcher and broker are retained in
`v9Redesign.modprobePreExecReviewContinuation`. No C source patch, protocol,
receiver, launcher, broker, role roster or native-entry mechanism was changed.

The sender paths request the two manager-gate permits only for recognized FC1 unit
names. modprobe@ targets are outside that roster. Unrecognized units retain the
generic spawn/target-exec route in the inspected source. An ungated spawn with a
/fc1-prefixed cgroup is refused by the source fence, but actual external placement
is unknown; that fence does not establish global interception of PID1's jobs.

**A rejected foreign frame is not a pre-exec barrier for a request never sent.**
The receiver would refuse modprobe names, but the unrecognized sender does not
reach that protocol route. The worker/operator listener also does not by itself
cover PID1 sibling services. A recognized label is not proof of the target binary,
cgroup or loaded-unit identity. These are source-scope conclusions, not observed
native behavior or proof of a working interception mechanism.

The advisory module-budget reportv2 now makes these distinctions explicit in
preExecCoverage, binds the reviewed source hashes and keeps observed rejection,
qualification and authorization false. It grants no role or exec allowance. The
existing six-role escrow and broker partitions remain unchanged; no quota lending,
refund, new native profile or ready candidate follows from the report.

Three new pre-exec fixture cases and seven affected cases passed in bounded slices
(10 distinct software cases). Synthetic ABI frames exercise both sites, foreign
names, lookalikes and another profile identity; all six legitimate names provide
positive decoding controls. A fake valid prepare label with a system.slice executor
cgroup is refused, preserving eight prior consumed records. This is pure escrow
state, not a real modprobe interception. An in-memory role-name substitution was
detected by the ABI fixture; repository source was not mutated. Logs retain every
attempt in the same accounting child.

Spec Kit structural preflight passed before edits. Luna (`gpt-6-luna`) independently
reviewed source and delta without executions and found no interpretation defect.
No full/general discovery was run; quick/PR/sensitive profiles remain pending under
the owner restriction, not waived. A qualified pre-effect mechanism for the
external manager jobs, exact causal identity/accounting binding, emitted objects,
immutable host and full lifecycle budget remain stop conditions. This review does
not implement or accept that missing barrier.

Current normalized source identity is
`1856d90528c49fd8acd88911144b4bec0f6bbcef4ffc81d66693bb7c054e4b8a`
(44 files). Every profile/native/budget/workload/utility/execution gate remains
false/pending. The checkout, previous continuations and historical model-scope
incident are preserved; plugin/telemetry products remain frozen. This lot ran no
builds, models, real workload sources, native controls or live-host census.

### Proposed zero-allowance modprobe barrier design — 2026-10-19

**Status: independently reviewed design proposal only; unimplemented, unqualified
and not adopted.** The owner authorized offline design, not implementation or
native execution. The existing plan was located with setup_plan (no template copy
or plan overwrite). This design stays in the single resumption/accounting record;
no new feature package, scenario, public interface, ADR adoption or authority
snapshot is created. Runtime sources and their 44-file pin remain unchanged.

The proposed policy refuses uncovered module-service work. If the current FC1
image/device-policy path needs modprobe jobs, its parent load/start fails and the
candidate remains NO-GO. Required Wants must not be silently suppressed while
continuing image work. Built-in source configuration, a skipped condition, receiver
refusal or an empty worker capability set cannot substitute for the barrier.

The policy is restricted to a future independently qualified, dedicated immutable
FC1 VM/host. It is not a proposed installation on the owner's workstation or a
shared host. Selective attribution by FC1 cgroup alone is insufficient when PID1
can merge, cache or directly activate external jobs. Unknown shared/cached work or
unclosed unit/alias provenance rejects admission. No live policy change, artifact
build or test invocation follows from this document.

| Point | Proposed source position and action | Limit |
|---|---|---|
| MPB-G1 | In unit_patch_contexts, after the effective predicates are known but before module-dependency registration, refuse the FC1 parent requiring the uncovered helper family. Propagate refusal to the original owner. | Does not cancel existing cached/shared/queued work. |
| MPB-G2 | Mandatory manager denial before exec_context_load_environment and the first executor spawn, including non-FC1 module-service identities under the dedicated-host policy. | Requires canonical identity, immutable policy/universe and boot/epoch qualification; the current patch does not implement it. |
| MPB-G3 | Independent executor denial before every final target exec dispatch, including the generic path and fallbacks. | Defense in depth only: an executor already created is a prior effect; stop and preserve consumption/uncertainty. |

The qualified policy would be immutable and bound to manager/executor objects,
source/config-to-object provenance, boot identity, original invocation/nonce,
canonical unit/alias/drop-in and exec-FD provenance, original origin/close-by and
retained counters. No client envelope, callback, environment flag or caller-supplied
approval bit may select or disable it. Missing/stale/drifting bindings reject the
candidate. A name-only service guard does not establish exclusion of arbitrary
module-loader execution from other already running processes; separate transitive
helper/host closure remains required.

The intended guard adds no role, permit, process, helper or service activation.
Denial receipts use bounded existing accounting capacity; they must not activate a
new logging/helper service. Guard/receipt CPU, wall time, memory, I/O and retained
storage are not presumed free. Their costs must fit the original lifecycle caps,
without extending deadlines or resetting origin. Unknown overhead is a stop. The
prospective totals remain 7,704/13,342 exec attempts, escrow [9,0,0,2,2] and fixed
[10,1,1,3,3]; none is an accepted minimum or execution grant. Prior reserved or
uncertain attempts are never refunded to make a late denial look cost-free.

Requirements MPB-D01–MPB-D08 in the accounting child trace policy provenance,
parent refusal, pre-spawn interception, target defense, quota conservation,
dedicated-host scope, overhead and evidence boundaries. They refine the bounded
engineering proposal under Constitution Articles 5/6/7/12/13/14/19/20, GOVERNANCE,
existing operational semantics and SPEC-034. No normative authority is amended;
architectural adoption and any necessary ADR remain pending.

Thirteen documentary synthetic traces MPB-F01–MPB-F13 expose boundary cases:
current parent helper demand; direct service activation; canonical/unknown aliases;
cached epoch and coalesced ownership; late target denial after executor spawn;
condition skip; source/deadline drift; ordinary six-role work; unknown host scope;
and receiver-only rejection. Every trace keeps nativeAcceptance=false. In
particular, MPB-F07 is a **violation**, not successful zero-exec denial. Ordinary
work without module demand still requires all existing gates and receives no new
authority. Fixture consistency is a design check, not an implemented barrier test
or a native observation.

Rejected shortcuts include extra modprobe escrow roles, broker loans, relying only
on masking/absent templates or condition skips, dropping required dependency edges,
target-only denial after the first effect, and a global policy on a shared host.
The current candidate is not ready: source implementation, architectural adoption,
immutable policy/host/loaded-job binding, complete overhead and
helper bounds, object correspondence and separately authorized native-negative
checks remain future gates. Existing owner/watchdog/final-observer obligations and
all original scientific/human/founder gates remain pending.

Spec Kit structural preflight passed before edits. This turn implements no source
hook, native validator or executable request. Previous Luna source reviews are not
review/approval of this new design. General
quick/PR/sensitive validation remains pending under the owner restriction. The
checkout and history remain intact, with no builds, models, real workload sources,
native controls, live-host census or additional technical-source downloads.

Independent read-only review by **gpt-6-luna** completed on 2026-10-19 for
this section and its accounting child. Luna found no ordering contradiction in
G1/G2/G3 as proposed and raised one P3 terminology finding: MPB-F01 now uses
`module_dependency_demand_detected`, distinguishing detected demand from actual
dependency registration or queueing. This documentary correction was applied
after review; no second review or implemented-barrier result is claimed.

Luna retained the already declared blocker: neither G2/G3 nor these traces
demonstrate exclusion of direct `init_module`/`finit_module` calls or loaders in
already running processes. Future qualified host closure must resolve those
mechanisms. Review is advisory, not design adoption, implementation authority or
native qualification. Quotas, source pin, checkout and every existing gate remain
unchanged. No build, runtime model, real source or native control was executed.

### Direct module calls and active-loader closure proposal — 2026-10-19

**Status: independently reviewed offline proposal; no implementation, adoption
or native qualification.** This extends MPB-G1/G2/G3 without changing their
meaning. It specifies proof obligations, not verified Linux enforcement behavior.
No new upstream sources, live census or technical-source downloads were used.

The proposed admission conjunction is: all existing gates AND a qualified global
module-load prohibition AND a closed initial process/kernel state AND bounded
loader execution/accounting. None of these predicates is presently established.
A module insertion denied after a loader starts does not demonstrate zero exec
attempts. An already loaded module or an earlier syscall is an initial effect,
not something this proposal can undo. Unknown history refuses the candidate.

| Requirement | Proposed condition before admission | Failure disposition |
|---|---|---|
| DMC-D01 | A dedicated immutable FC1 host has an independently qualified kernel-wide prohibition at every effective init_module/finit_module entry, before insertion effects, for every task and supported ABI. Prove coverage of equivalent/compatibility paths or exclude them in the qualified image. | Missing path/object/ABI correspondence refuses admission. No syscall numbers or hook behavior are assumed here. |
| DMC-D02 | Protection is established in the trusted boot sequence before any untrusted userspace, remains non-disableable throughout the original lifecycle, and is bound to kernel/config/object, boot epoch and policy identities. | Late enablement, policy drift or any unprotected interval refuses admission; no retroactive clean claim. |
| DMC-D03 | Initial kernel state and every extant task/thread, manager, helper and descendant have bounded provenance from that boot epoch. Account for in-flight module requests and execs, kernel-originated helper requests and queues, pending jobs, inherited executable FDs and privilege-changing paths. Prevent an admission race by a qualified continuous invariant, not a census followed by an unprotected gap. | An unknown or preexisting loader/request refuses the candidate; do not kill/restart it and call the state clean. |
| DMC-D04 | Preserve G1/G2/G3. Separately close loader exec routes from active processes and kernel-originated module/helper requests, including renamed, FD-backed or generic fallback dispatch. Require qualified boot-policy denial before helper creation; unknown reachability refuses admission. A syscall denial alone does not intercept that exec. | Uncovered loader exec or unbounded retries refuses admission even if module insertion would fail. Known prior spawn retains consumption and stops. |
| DMC-D05 | No owner/client/namespace/credential transition or service activation can widen the protection domain; privilege-bearing components belong to the same immutable trust boundary. | Unknown escape or mutability refuses admission; worker-local filters/capabilities alone are insufficient. |
| DMC-D06 | Denial, audit/receipt, kernel helper requests/queues/retries, existing-task activity and boot-policy preparation have explicit accounting boundaries and bounded complete costs inside the original applicable lifecycle caps. | Unknown or excessive cost stops; no new role/helper/permit, refunds, broker loan, deadline reset or quota expansion. |
| DMC-D07 | Future source-to-object correspondence and separately authorized negative native checks must establish each condition, including active-process races and alternate exec routes. | Documentary traces and absent observations never qualify a host. |

The preferred design direction is global prohibition from qualified boot, combined
with the existing pre-spawn barrier and a closed process universe. No concrete
kernel hook, boot flag, seccomp, capability, module configuration or LSM mechanism
is selected as sufficient: their exact semantics, irreversibility, ABI coverage
and object correspondence remain unresolved. CONFIG_MODULES=n/built-in intentions
are retained source context, not a measured boot witness. No new collector,
sidecar, daemon, loader probe, shutdown procedure or enforcement installation is
introduced. No policy is proposed for the owner's Mac or any shared host.

Complete prevention of module insertion and a zero-additional-loader-exec claim
are separate obligations. If a process already running at admission could start
arbitrary loader code without a qualified pre-exec restriction, DMC-D04 fails;
renaming a binary allowlist cannot establish closure. If the immutable host cannot
satisfy this within the existing budget, the outcome is NO-GO, not a larger quota.
No cleanup or module unloading is authorized or treated as compensation.

Documentary fixtures DMC-F01–F17 in the existing accounting child distinguish
unknown ABI, late policy, preloaded state, active direct caller, loader spawn,
FD-backed loader, policy drift, unknown cost, in-flight request, admission race,
unbounded retry, a fully stipulated synthetic case, and kernel helper reachability, prior creation, queue epoch, retry costs and exec-FD uncertainty. Even the latter only
continues to existing gates; it never accepts a real host. These are invented
traces with explicit assumptions, not executable syscall/barrier tests.

Constitution Articles 5/6/7/12/13/14/19/20 and GOVERNANCE remain superior: effects,
point-of-use invariants, provenance, uncertainty and complete costs stay explicit.
No authority snapshot or assurance approval is refreshed. The previous Luna review
covered MPB only; the independent review below covers this extension. Architectural
decision and qualification remain pending. Runtime source pin, 7,704/13,342 prospective totals, escrow
[9,0,0,2,2], fixed [10,1,1,3,3] and all existing gates remain unchanged.

Independent read-only **gpt-6-luna** review completed on 2026-10-19. Finding
**DMC-1 (P2)** identified missing explicit coverage of kernel-originated module
auto-load/helper requests. DMC-D03/D04/D06 and DMC-F13–F17 now include helper
requests, queues/in-flight work, denial before helper creation, exec-FD paths,
retries and full costs. This is an obligation to qualify or exclude a possible
route, not an observed behavior of any particular kernel. A helper already
created remains a consumed violation even when insertion is denied later.

The correction was applied after the first review; the second review below
now covers that correction.
Luna found no quota contradiction or false acceptance in the reviewed proposal.
Seventeen documentary traces pass consistency checks; they are not barrier tests.
JSON parsing and diff whitespace checks passed. No runtime sources, source pin,
quota or gate changed. No builds, runtime models, real sources, native controls
or live census ran. All mechanism, object, cost and native-qualification gates
remain pending; the candidate remains NO-GO.

Second independent read-only **gpt-6-luna** review completed on 2026-10-19,
limited to DMC-1 and kernel-originated helpers. **DMC-1 is closed at documentary
design scope; no new findings.** DMC-D03/D04/D06 and DMC-F13–F17 explicitly
cover requests/queues/in-flight work, qualified denial before helper creation,
exec/FD routes, retries and complete costs within the original limits. A helper
already created remains a consumed violation; no fixture grants acceptance.

This closes the explicit coverage omission only. Mechanism selection, continuous
boot/host coverage, ABI and object correspondence, measured bounded costs,
architectural adoption and separately authorized native qualification remain
pending. The candidate remains NO-GO. JSON parsing, the 17 documentary fixtures'
non-acceptance flags, zero added quota and unchanged false design/implementation/
qualification/authorization gates were checked; diff whitespace checks passed.
No runtime source, source pin, quota or existing gate changed. No builds, runtime
models, real sources, native controls or live census ran during this review.

### DMC boot prohibition mechanism candidate — 2026-10-19

**Status: independently reviewed offline mechanism candidate; not implemented,
adopted or qualified.** This refines DMC-D01–D07 and preserves the
second Luna review's documentary closure of DMC-1. That review did not cover this
new mechanism selection; its separate review is recorded below. Existing
source-policy records are reused; no fresh
kernel source, build, running-host observation or native control was obtained.

Select for future qualification the existing pinned Linux 6.12.113 source identity
and configuration composition: CONFIG_MODULES=n, CONFIG_STATIC_USERMODEHELPER=y,
CONFIG_STATIC_USERMODEHELPER_PATH="", CONFIG_UEVENT_HELPER=n, with required
storage/crypto features built in. Selection means a proposed prerequisite, not a
claim that config text proves effective enforcement. No runtime sysctl, late
seccomp attachment or added broker/helper is selected as the primary prohibition.

| Mechanism obligation | Required future correspondence | Refusal boundary |
|---|---|---|
| DMB-M01 — compiled exclusion | Establish that the exact source/config/object and every supported ABI exclude dynamic module insertion through init_module/finit_module and equivalent entry paths. Document actual unavailable/denied behavior; no errno is assumed. | Missing ABI path, ambiguous config or object mismatch refuses candidate. |
| DMB-M02 — helper exclusion | Establish that the immutable empty static-helper path blocks every reachable kernel-originated helper request before helper task creation/exec, including queue and fallback paths; establish which paths bypass that common route and exclude them separately. | Reaching a queue, spawning then denying insertion, or an unclosed bypass cannot establish zero helper creation. |
| DMB-M03 — boot continuity | Bind the booted kernel, config, initial filesystem/early userspace, command line, policy objects and boot epoch to the qualified candidate before the first untrusted task. Establish no mutable alternate kernel/boot transition can replace that policy during the lifecycle. | A config file/hash alone, late lockdown, untrusted early userspace, unknown handoff or replacement capability refuses admission. |
| DMB-M04 — initial-state invariant | Trace all initial tasks/threads, built-in initialization, helper requests/queues and pending execs from the protected boot origin into admission and through final observation. Prove an uninterrupted invariant, not a census/sampling gap. | Preexisting unknown work or a helper already created is not repaired by later policy. Preserve any consumed/uncertain cost and stop. |
| DMB-M05 — userspace loader closure | Keep MPB-G1/G2/G3 and DMC-D04 independently mandatory. Close direct/renamed/FD-backed loader execs from active processes under an immutable qualified process/exec policy. This kernel composition does not by itself establish that userspace never starts a loader. | No concrete complete active-process exec mechanism is selected here; that unresolved gate alone keeps this candidate NO-GO. |
| DMB-M06 — accounting and enablement | Bound all denial paths, repeated requests, boot preparation, receipts and retained state under original applicable caps and original monotonic origin. Features needed by the image must be built in and compatible with prohibiting helpers. | No origin reset or uncharged preparation; if safe image operation needs the prohibited route, refuse the parent/candidate rather than enable it or enlarge quotas. |
| DMB-M07 — independent qualification | Future source/object inspection and separately authorized negative native checks must cover each row and every excluded alternate path. Independent observation must use the existing qualified accounting boundary. | No new observer daemon, test permission or build authority follows from this proposal; documentary consistency is not a qualification witness. |

The lifecycle state proposal is UNQUALIFIED → BOOT_IDENTITY_BOUND →
CONTINUITY_AND_COST_BOUND → EXISTING_ADMISSION_GATES. These are documentary
states, not new runtime tokens or approvals. Every transition requires retained
independent evidence; missing/drifting identity, nonempty/unknown helper policy,
unknown queue/cost or an alternate boot path yields REFUSE. If a helper has already
been created, use CONSUMED_OR_UNCERTAIN_STOP. Rebooting or unloading cannot erase
that history or refund budget. Even the last state grants no execution authority.
No automated remediation or new boot procedure is introduced.

Rejected primary alternatives are late module-disable switches, worker-local
capability drops/filters alone, removing a modprobe pathname, module signatures
alone, and a helper that runs merely to deny a request. These do not satisfy this
proposal's combined immutable-before-untrusted-userspace, pre-creation and
zero-additional-process obligations without separate evidence. This is a design
comparison, not a verified statement of any selected kernel object's behavior.

DMB-F01–F10 are documentary synthetic cases: config-only evidence, ABI unknown,
nonempty helper path, common-route bypass unknown, helper already spawned, early
userspace untrusted, alternate boot mutable, loader exec closure unknown, repeated
request cost unknown, and all prerequisites stipulated. The last only proceeds to
existing gates. No fixture represents a real boot or implemented enforcement test.

No runtime source or private 44-file pin changes. Prospective 7,704/13,342 totals,
escrow [9,0,0,2,2], fixed [10,1,1,3,3] and all existing gates are unchanged;
overhead remains unknown, not zero. Constitutional Articles 5/6/7/12/13/14/19/20,
GOVERNANCE and existing operational contracts remain superior. Architectural
adoption/ADR, complete host and process
closure, object correspondence, bounded costs and native qualification are pending.
No public interface, assurance snapshot, activation, build or experiment is added.

Structural Spec Kit preflight passed before edits. Ten documentary traces were
checked for non-acceptance and prior-effect consistency; a mislabeled successful
continuation after helper creation was rejected. Required config matches the
retained contract. JSON and diff whitespace checks passed. These checks provide
no implemented-barrier or native evidence; general profiles remain pending.

Independent read-only **gpt-6-luna** review of the DMB mechanism candidate
completed on 2026-10-19: **no new design findings**. Scope was DMB-M01–M07,
DMB-F01–F10 and this proposal. The review found no false host acceptance or
zero-cost claim; F05 preserves the consumed helper effect and F10 only continues
to existing gates. It did not independently audit actual kernel/config semantics
or establish source-to-object, ABI, boot or helper-bypass coverage.

Mechanism enforcement, complete host/active-loader closure, measured bounded
costs, architectural adoption and native qualification remain pending; the
candidate remains NO-GO. JSON parsing, ten fixture non-acceptance flags, zero
additional quota and preserved false gates were checked; diff whitespace passed.
No runtime source, source pin, checkout identity, quota or gate changed. No
builds, runtime models, real sources, native controls or live census ran.

### Active-process loader pre-exec mechanism candidate — 2026-10-19

**Status: independently reviewed offline mechanism proposal; unimplemented,
unadopted and unqualified.** This refines DMC-D04/DMB-M05. Previous Luna reviews do not
cover this extension; its separate review is recorded below. The scope is the
future dedicated immutable FC1 host, never
the owner's workstation/shared host. No new kernel sources or running-host facts
are asserted. Constitutional Articles 5/6/7/12/13/14/19/20, GOVERNANCE and existing
operational contracts remain superior; assurance stays draft/human-review pending.

Select for future source-level design a built-in mandatory kernel policy over a
closed task/exec universe, initialized in the trusted boot sequence before any
untrusted task. It must apply to all active tasks and descendants, not just FC1
workers or PID1 services. A userspace daemon, late filter, name classifier or
optional caller callback is not the selected enforcement mechanism. This choice
requires later kernel/source/object work; no exact existing hook or patch is
claimed sufficient. Failure to locate qualifying interception points is NO-GO.

The policy is deny-by-default for task creation and executable-image transition.
Its immutable table would bind the boot/policy epoch, original lifecycle and
causal owner, canonical executable objects and role transitions to the ORIGINAL
already-reserved accounting and original close-by. It cannot mint a new permit,
process role or escrow slice. Existing manager/executor gates remain mandatory;
a second check may consume/check the same bound attempt, never charge a duplicate
reservation or release/refund it on uncertainty. A generic runtime/plugin grant
or client-supplied label cannot populate the table. If an existing attempt cannot
be atomically bound to both enforcement layers, refuse the candidate.

| Obligation | Proposed mandatory action | Limit / refusal condition |
|---|---|---|
| ALP-A01 — origin and scope | Bind all existing tasks/threads, their initial objects, descendants and pending operations continuously from protected boot through final observation. Bind namespaces, credentials and retained FD provenance; reject unknown task origins. | Attaching policy at admission cannot retroactively clean an active process. Unknown initial task or in-flight creation refuses candidate. |
| ALP-A02 — creation fence | Before a new task becomes effective, validate an allowed creation transition against the original reservation and task/memory limits. Cover fork/clone/vfork variants, threads, supported ABIs and kernel helper creation or exclude the path. | Source work must identify a fence before the forbidden creation effect. Partial setup/allocations and denials still have costs. Existing helper bypass obligations DMB-M02 stay mandatory; unknown coverage refuses. |
| ALP-A03 — exec fence | Before any final executable-image transition, resolve and verify the complete immutable executable closure under retained object identity, then enforce the allowed transition and same original reservation. Cover direct, FD-based, interpreter and generic fallback dispatch, plus concurrent exec attempts. | Pathname, unit name, hash read before replacement or userspace precheck alone is insufficient. An executor already created is a prior effect, never zero-process denial. |
| ALP-A04 — executable closure | Bind executable file objects, interpreter/dynamic loader, libraries, executable mappings and behavior-relevant inputs/modes, including inherited FDs and environment. Reject missing or mutable closure; classify by admitted role and behavior, not a basename containing modprobe. | A trusted Python/shell/Git binary with arbitrary script, extension, subcommand or environment is not a proven safe loader exclusion. No complete admitted closure for these objects is asserted. |
| ALP-A05 — existing code | DMB direct-call protection remains mandatory for code already resident or invoked without exec, including in-process libraries. Preserve immutable executable-memory and privilege-domain obligations; reject unknown injection, dynamic-code or policy-widening paths. | A pre-exec fence does not detect every semantic loader and cannot mediate instructions already running. Unclosed code paths refuse admission, not speculative classification. |
| ALP-A06 — atomicity and authority | Serialize validation/reservation/use with retained kernel object references and bounded state, preserve original identity/nonce/epoch/counters, and reject racing revocation, reparenting, FD/object replacement or stale deadline. No policy relaxation via credentials, namespaces, boot replacement or fail-open errors. | Exact locking, source sites, object lifetime and ABI must be established later. Unknown transition outcome retains consumed/uncertain state and stops; no retry under a new origin. |
| ALP-A07 — bounded accounting | Bound lookup, object checks, synchronization, denial loops, retries, initial-state provenance and receipt/storage costs under the original lifecycle caps. No helper process or new logging service performs policy decisions. | No new quota, broker loan, refund, watchdog window or uncharged boot preparation. Unknown/unbounded overhead or incompatible legitimate workload means NO-GO. |
| ALP-A08 — qualification | Require independent design/source-to-object review and separately authorized native-negative checks for every creation/exec/ABI/input/race path and final observation. | Documentary traces and synthetic stipulated identities are not actual code-closure proof, boot evidence, installed policy or permission to implement. |

State transitions proposed as documentary semantics are: unbound → refuse;
bound original attempt + closed objects + qualified fences → existing gates;
identity/deadline drift → refuse and retain reservation; any prior creation/exec
or uncertain outcome → consumed-or-uncertain-stop. Denying an unknown exec does
not refund an already-created child. A direct exec in an existing process needs
no new child but still requires the exec fence and original exec accounting.
Denying module insertion later is not evidence of either fence's interception.

The current generic Git/Python/systemd workload is not assumed compatible with
this closed universe. Scripts, hooks, executable configuration, plugins, aliases,
FDs and library behavior require exact bounded closure or exclusion without
silently changing the originally selected workload. If meeting ALP requires
extra executor roles or helper allowance, refuse instead. This proposal selects
a mechanism family and obligations; it does not finish the kernel patch, table,
full behavior closure, overhead bound or integration with the existing ABI.

ALP-F01–F12 are documentary synthetic traces: unknown active task; renamed
loader; mutable FD object; trusted interpreter with unbound script; unknown
kernel helper creation path; child created before exec refusal; direct exec in
an existing task; policy/deadline drift; racing reservation use; denial storm
with unknown cost; in-process loading with DMB unqualified; and every required
condition stipulated. F06 preserves prior creation as a violation; F12 merely
continues to existing gates. These traces cannot establish that a loader has
been recognized or that the proposed kernel fences exist.

No runtime source, source pin, public interface, authority snapshot or adopted
ADR changes. Additional quota is zero; costs are unknown, not zero. All original
budgets, gates, checkout and NO-GO remain intact. No build, runtime model, real
source, native control, live census, host/provider operation or installation is
introduced. Architectural adoption and all technical/native qualification
remain pending; the documentary review is recorded below.

Spec Kit structural preflight passed before edits. Twelve documentary traces
passed prior-effect/non-acceptance consistency; a false continuation after child
creation was rejected. JSON parsing and diff whitespace checks passed. General
profiles remain pending; no implemented barrier or native evidence is claimed.

Independent read-only **gpt-6-luna** review completed on 2026-10-19 for
ALP-A01–A08, ALP-F01–F12 and the active-process mechanism proposal: **no new
design findings**. The review confirms distinct creation/exec obligations, the
same original reservation binding, retained prior effects and no new allowance
or refund. F06 preserves the created-child effect; F12 only continues to existing
gates, and none of the documentary fixtures grants native acceptance.

Exact interception points/ABI/table, atomic reservation integration, immutable
object/input closure, workload compatibility and complete costs remain unresolved.
Review is not implementation, adoption or qualification; the candidate remains
NO-GO. JSON parsing, twelve fixture non-acceptance flags, zero added quota and
preserved false gates were checked; diff whitespace passed. No runtime source,
source pin, checkout identity, quota or gate changed. No builds, runtime models,
real sources, native controls or live census ran in this review.

### Interception and original-reservation atomicity proposal — 2026-10-19

**Status: independently reviewed offline design; unimplemented, unadopted and
unqualified.** This refines ALP-A02/A03/A06 without turning earlier Luna reviews
into review of this delta. Only retained source text and documentary fixtures
were used. No additional upstream source, build, workload or native observation
was obtained. Runtime sources, ABI and the 44-file source pin are unchanged.

The retained manager implementation reserves one ledger ticket for site 0 and a
DISTINCT ticket for site 1. Site 0 precedes the executor spawn, site 1 precedes
the final target exec. delivered(sent=True) records continued-not-launch-proof,
not kernel consumption or successful exec. Its Python RLock protects the local
transaction, not atomic kernel validate/use. The 152/32-byte request/reply does
not establish an authenticated kernel reservation binding. No current code is
claimed to implement the protocol below.

Do not collapse the two sites into one allowance. Within a single original
attempt, creation and exec fences may check the same bound attempt without
charging an extra exec permit, but executor launch and final target exec retain
their two original distinct charges. Existing task/memory bounds also apply to
creation; an exec allowance does not grant extra tasks/threads. Git/broker
attempts must map to their own original partition records; the six manager roles
cannot lend them tickets. Missing mapping refuses the candidate.

| Interception ID | Proposed position and predicate | Required refusal/qualification boundary |
|---|---|---|
| IAR-I01 — dependency demand | Retain MPB-G1 refusal before module dependency registration and G2 mandatory manager refusal before environment preparation/first executor spawn. | A denial reply alone cannot prove global interception; unknown queued/cached jobs still refuse admission. |
| IAR-I02 — creation entry | At a mandatory kernel task-creation boundary for every supported fork/clone/vfork/thread/helper route, bind original attempt, parent task identity, exact creation transition and required task/memory bounds before the forbidden child becomes effective. | Exact source site and allocation/publication order are unresolved. Any unavoidable earlier setup cost must be bounded/charged; a hook after the child exists is insufficient for pre-creation denial. |
| IAR-I03 — creation handoff | Atomically bind the actual child task object and birth identity to the retained attempt before it can run, inherit or initiate another transition. Mark the creation edge consumed once; prevent another child using that edge. | PID alone or a userspace readback after scheduling is insufficient. Threads, credential changes, vfork ordering and helpers need explicit source coverage. |
| IAR-I04 — exec resolution | Cover every executable-image transition, including existing-task direct exec, FD execution, interpreter/dynamic loader and fallback, using retained immutable resolved objects and closed inputs. Reject unresolved closure before continuation. | Resolution/setup effects still cost resources; no basename-only or hash-then-reopen proof. Multi-stage interpreter resolution must share one exact transition without creating another grant. |
| IAR-I05 — final exec use | At the last qualified point before the image-transition effect, atomically revalidate task/object/epoch/deadline and consume that attempt's exec edge exactly once. Deny reuse or drift. | Exact source point/lifetime and all supported ABI paths remain pending. A failed/uncertain exec stays consumed; no fallback, retry or refund under the same edge. |
| IAR-I06 — lifecycle close | Serialize revocation/phase closure with every fence and preserve spent/uncertain records through final observation under the original close-by. | Sending a reply or closing a socket is not revocation of an already-linearized operation; unknown reconciliation makes the run fail, never reusable capacity. |

Candidate authority architecture: one authoritative kernel-resident attempt
state, with a bounded mirror in the existing owner ledger. A future qualified
bootstrap would bind the ORIGINAL pre-reserved attempt and its partition/counter
identity into that state through a private trusted control boundary. This is an
internal reference, not a transferable bearer permit or additional quota. A raw
reply ticket, client FD, PID, role label, environment or plugin grant cannot
create/import authority. Exact import ABI, credentials, trust boundary and
counter reconciliation are unresolved; the current wire ABI is insufficient to
claim them. No new helper/daemon is allowed to perform import or mediation.

The import protocol must first consume/reserve the original owner slot, then
establish the kernel record bound to that exact slot, and only then make it
eligible for fence use. There is no distributed atomicity inferred from a local
lock: failure between those steps leaves the slot spent/uncertain and the run
stopped. No kernel record without an original slot; no second import for a slot;
no inferred capacity from an absent or stale mirror. Kernel/owner disagreement
stops the lifecycle, without restoring either side's counters. If this cannot be
implemented within the existing trusted bootstrap and caps, the result is NO-GO.

Proposed attempt states (documentary, not implemented) are OWNER_RESERVED →
KERNEL_BOUND → CREATION_USED (where needed) → EXEC_USED → TERMINAL_RETAINED.
Direct exec in an existing task skips creation only under its bound transition.
An attempt specifying creation cannot skip it. Phase transition is not permission
to reuse any state. DENIED_RETAINED and UNCERTAIN_STOP are terminal; neither
returns capacity. The legacy delivery state remains a separate observation and
is never relabeled successful kernel use or overwritten retrospectively.

For creation and exec separately, one kernel serialization domain must cover the
final predicate check and irreversible edge-state update, excluding concurrent
use/revocation/phase close. This state update is the proposed linearization point
BEFORE the effect. If revocation wins, deny; if use wins, retain consumption even
when closure races or the downstream effect fails. At each subsequent fence,
check revocation, original phase/global deadline and immutable binding again.
Expiry between creation and exec prevents exec but cannot undo the child. Retain
object references and avoid sleeping socket/owner IPC under the kernel critical
section. Exact synchronization primitives, lock order, clock-domain mapping,
boot/task lifetime and race-free publication require later source/object review;
none is presumed solved by this description.

Unknown tasks or transitions deny without minting a record; denial itself still
uses bounded CPU/wall/memory/I/O/receipt capacity. Exhausted state capacity,
unknown clock conversion, rollback/replay, reboot/policy replacement, late import
or unbounded retry fails closed. No deadline reset, restart, spare role, loan or
new polling/observer process is introduced. Built-in helper prohibition DMB and
resident-code closure ALP remain separate mandatory gates.

IAR-F01–F14 are synthetic documentary traces for: missing binding; duplicate
import; cross-partition ticket; site 0 reused as site 1; sent reply without kernel
binding; revocation winning; consumption winning then failure; child exists then
deadline expires; duplicate exec; FD/object drift; mirror mismatch; direct exec
without a bound transition; unknown ABI/source point; and all conditions merely
stipulated. They exercise the proposed state contract, not a kernel/IPC model,
implemented transaction, successful syscall or native test.

Constitution Articles 5/6/7/12/13/14/19/20 and GOVERNANCE remain superior.
Architectural adoption, exact source sites and
ABI, qualified bootstrap import, complete cost/closure and native qualification
remain pending. All original quotas and gates are unchanged and the candidate
remains NO-GO. No implementation, public contract, authority snapshot, build,
runtime model, real source, control, host census or provider action is authorized.

Spec Kit structural preflight passed before edits. Fourteen documentary traces
passed non-acceptance/prior-effect consistency; a successful continuation mislabeled
after child creation was rejected. JSON parsing and diff whitespace checks passed.
General profiles remain pending; no native or implemented atomicity evidence exists.

Independent read-only **gpt-6-luna** review completed on 2026-10-19 for
IAR-I01–I06, IAR-F01–F14 and the original-reservation atomicity proposal:
**no new documentary design findings**. The review confirms distinct site 0/1
charges, original-slot binding before kernel eligibility, retained consumption
on disagreement/failure, and pre-effect use/revocation ordering. Local RLock,
reply delivery and socket closure are not presented as kernel atomicity or
successful launch. F14 only continues to existing gates.

Exact source hooks/ABI, trusted import, synchronization, clock mapping, task/object
lifetimes and complete costs remain unresolved. Review does not adopt, implement
or qualify the mechanism; the candidate remains NO-GO. JSON parsing, fourteen
fixture non-acceptance flags, zero added quota and preserved false gates were
checked; diff whitespace passed. No runtime source, source pin, checkout identity,
quota or gate changed. No builds, runtime models, real sources, native controls
or live census ran in this review.

### Trusted reservation import ABI and hook contracts — 2026-10-19

**Status: independently reviewed private offline ABI proposal; no implementation,
adoption or qualification.** This refines IAR-I02–I06. Existing wire v1 and runtime
sources are unchanged; previous Luna reviews do not cover this extension. Exact
Linux source call sites have not been verified. The hook names below are proposed
internal contracts, not claims that those kernel symbols or source patches exist.

Select a bounded kernel control descriptor created only by the qualified trusted
boot path and bound to the EXISTING qualified importer task object, executable
closure, owner partition, boot epoch and original lifecycle. Importer identity is
not selected by a caller-supplied PID, path, hash or role. Even a copied/inherited
FD cannot authorize another task: every control operation rechecks the immutable
bound task/object/credential context. No open-by-path, root-only shortcut,
namespace privilege or plugin grant may create a session. Descriptor provisioning,
exact importer/bootstrap correspondence and kernel privilege-domain closure are
unimplemented prerequisites; absence of them refuses the candidate. No new daemon,
helper, signing key, device installation or external transport is introduced.

The session is initialized from the ORIGINAL qualified preparation with frozen
disjoint partition/phase caps, role/site transitions, object/input closure table,
original monotonic origin and phase/global deadlines. No control operation can
modify those tables, extend a deadline or change phases unilaterally. A trusted
phase transition must be independently bound to the existing original lifecycle;
its control ABI is outside this proposal and remains a gate. An IMPORT is accepted
only for an already-consumed owner slot and a matching preauthorized table entry;
the kernel independently enforces one slot/import, original partition caps and
all predicates. The owner's receipt digest is a cross-reference, not proof of
consumption or authenticity. Trust in actual owner consumption requires the
qualified importer and its source/object/ledger binding; arbitrary userspace
state or a matching digest alone is insufficient. If that binding is unavailable,
IMPORT refuses, even when quota appears free.

Proposed private frame **reservation-import/0-draft**, canonical little-endian,
fixed 256 bytes, no pointers, variable strings, ancillary FDs or padding ambiguity:

| Offset | Bytes | Field |
|---:|---:|---|
| 0 | 8 | magic, exact ASCII FC1RSV00 |
| 8 | 2 | version = 0; draft only, no negotiation/downgrade |
| 10 | 2 | op: 1 IMPORT, 2 QUERY, 3 REVOKE, 4 CLOSE |
| 12 | 4 | frame bytes = 256 |
| 16 | 8 | session-local sequence, strictly increasing, no wrap |
| 24 | 16 | immutable session identity, bound to boot/preparation by retained kernel state |
| 40 | 4 | owner, phase, site, transition-kind: four exact table-defined u8 values |
| 44 | 4 | flags = 0 |
| 48 | 8 | original owner-slot index, zero-based; not a bearer capability |
| 56 | 8 | original boot/policy epoch |
| 64 | 32 | immutable executable/input closure table identity |
| 96 | 32 | parent/current task-binding table identity; resolves only to retained kernel task references |
| 128 | 32 | original transition table identity, including exact site and creation/exec edges |
| 160 | 32 | original owner-reservation receipt cross-reference |
| 192 | 8 | original monotonic origin ns |
| 200 | 8 | original phase deadline ns |
| 208 | 8 | original global close-by ns |
| 216 | 8 | expected session generation for compare-and-update |
| 224 | 32 | reserved, all zero |

Integers have checked ranges/overflow; every nonzero identity resolves to the
session's immutable table, never to a client-selected authority. IMPORT fields
must match original stored facts exactly. QUERY/REVOKE name the same exact tuple;
CLOSE has owner/phase/site/transition-kind/slot/closure/task/transition/receipt fields canonically zero
and retains exact session/epoch/times/generation. Unknown op, extra/short frame,
trailing data, unknown flags, reserved bytes, mismatched tuple or stale generation
rejects and fails the lifecycle; no partial enablement or automatic retry.

A fixed 64-byte response has magic/version/op and response size = 64 (16 bytes),
echoed sequence (8),
status i32 (4), retained state u32 (4), generation u64 (8), and zero reserved bytes
(24). Status 0 means only the named control transition was recorded. Negative
statuses are private draft categories for malformed, unauthorized, stale,
duplicate, exhausted and uncertain states; numeric assignments remain unfrozen.
No response contains a transferable permit or means successful spawn/exec.
QUERY is read-only accounting, never a retry/repair authorization. A lost/partial
response leaves the original slot consumed/uncertain and stops execution; QUERY
may describe retained state but cannot resume that failed lifecycle. REVOKE/CLOSE
never refund counters or erase state; already-linearized use remains consumed.

All control mutations and hook edge updates compare the same session generation
and serialize in one bounded authoritative kernel state domain. IMPORT atomically
checks the original tuple, remaining original cap, unused slot, immutable task
references and deadlines, then records KERNEL_BOUND and advances generation.
Only after that record can a hook continue. Owner reserve happens first; failure
between owner and kernel is terminal uncertainty, not a distributed transaction
rollback. Different site 0 and site 1 imports name DIFFERENT original slots and
charges. Rechecking an edge cannot debit another slot. CLOSE racing IMPORT wins
or loses at that serialization point; it cannot leave an eligible orphan record.
QUERY reads a stable generation without advancing authority generation; its
sequence processing still uses bounded serialized request metadata. In all cases, control requests do not run while a kernel hook waits on userspace.

| Proposed internal hook | Required retained inputs and linearization contract | Unqualified source boundary |
|---|---|---|
| HRI-H01 task_prepare | Current task object, bound original attempt, creation flags, namespace/credential context and task/memory bound. Check+mark creation edge used before forbidden creation becomes effective. | Exact supported creation/ABI/helper entry paths, pre-allocation costs and suitable source sites pending. |
| HRI-H02 task_publish | Retain and bind actual child object/birth identity before it can run or delegate. No second child can claim the used edge. | Must be ordered with H01 as one effect protocol, including failure between them, vfork/threads and publication races. No extra permit. |
| HRI-H03 exec_resolve | Retain complete resolved executable/interpreter/loader/library/mapping/input identities under existing-task/child transition. No hash-then-reopen or raw caller pointer binds authority. | Complete immutable closure, pre-commit preparation effects and interpreter recursion coverage pending. |
| HRI-H04 exec_commit | Recheck generation, original deadline, revocation, retained task/object identity and expected edge state; mark exec edge used before image transition. | Exact final non-bypassable source point and effect ordering pending. Downstream failure consumes edge, no fallback/retry. |
| HRI-H05 terminal_observe | Preserve record and counters for exit, failure, close or revocation; link actual outcome or uncertainty without making capacity reusable. | Existing final observer must independently qualify the retained facts; this adds no new observer process. |

A task that fails between prepare and publish leaves creation consumed/uncertain.
A prepared exec that expires before commit is denied but all setup and earlier
creation cost remains charged. Publication cannot occur after a winning close;
if creation already linearized, close cannot undo that prior effect and it stays
accounted even if publication/exit is uncertain. Exact synchronization needs a
source-level proof obligation: no sleeping control transport under hook locks,
bounded lock order/lifetime, atomic publication and original clock-domain mapping.
No lock primitive or stock security hook is claimed sufficient by name alone.

HRI-F01–F12 are documentary cases: unauthorized task with inherited descriptor;
receipt digest without qualified consumption binding; duplicate slot; site/slot
mismatch; stale generation; owner reserved/import lost; close before import;
creation then publication failure; exec preparation then deadline expiry; query
after uncertainty; noncanonical bytes; and all prerequisites stipulated. They are
not emitted packets, implementation tests or proofs of privileged import. No
frame grants extra quota; the fully stipulated case only reaches existing gates.

Constitution Articles 5/6/7/12/13/14/19/20 and GOVERNANCE remain superior.
Architectural decision, independent review, exact source hooks/control descriptor
ABI implementation, trusted importer/table provisioning, phase transition ABI,
full object/input closure, bounded synchronization/storage/denial costs and
native qualification remain pending. Runtime source pin, original quotas and all
gates remain unchanged; NO-GO persists. No builds, runtime models, real sources,
native controls, live census, installations or provider operations are introduced.

Spec Kit structural preflight passed before edits. Twelve documentary traces
passed cost/uncertainty and non-acceptance checks; a false resume after lost import
response was rejected. Request fields cover exactly 256 contiguous bytes; response
fields total 64 bytes. JSON parsing and diff whitespace checks passed. These are
documentary checks, not implemented ABI/transport tests; general profiles stay pending.

### Offline candidate preservation and publication closure — 2026-10-19

Independent read-only **gpt-6-luna** review of the pending trusted-import ABI and
HRI hook contracts completed without concrete design findings. This covers the
256/64-byte draft and its authority/failure boundaries, not actual kernel
semantics, implementation or native qualification. All remaining provisioning,
phase-transition, exact-source, synchronization, clock, lifetime and cost gates
remain pending. Previous reviews keep their exact delta boundaries.

The owner explicitly authorized coherent commits and a work-branch push without
merge. Preserve accumulated offline runtime/native sources, image contract and paired
tests, then the documentary/evidence record. This publication is a
save point for an incomplete candidate, not a release or whole-candidate approval.
No new test suite, quick/PR/sensitive/discovery profile, build, runtime model, real
workload or native control is executed. General validation remains pending, not
waived; historical slice results and the earlier validation-scope incident remain
unchanged. NO-GO, original budgets and all human/scientific/native/founder gates
remain intact. The source pin is checked without importing or running the runtime.

Publication static checks parsed Python AST without imports and all changed JSON,
confirmed the unchanged 44-source pin, and screened the bounded file set for
private-key/token-shaped material. This is not a comprehensive secrecy guarantee.
Staging exposed 30 whitespace diagnostics in the newly tracked unified patch:
all are required single-space empty context records. Patch bytes and pin are
preserved; whitespace checks on all other candidate paths pass. Earlier unstaged
whitespace results did not include this then-untracked patch. No runtime tests
were repeated and no full validation result is claimed.

Offline candidate source/contract/test commit: `98dfab46845349be2f48288e3bd2032c97f72422`. The accompanying
documentary commit preserves all accumulated evidence and pending gates. Target
is the work branch `feat/fc1-real-admission`; no PR, merge or CI dispatch is
authorized or performed as part of this closure.

## Integration with develop (2026-10-27)

Merging the branch into develop changed the hashed sources `git_runtime.py`,
`git_replay.py` and `runtime_scheduler.py` (optional `budget` parameter plumbing and a
shared `path_overlap` helper from develop). The code pin `_MODELED_SOURCE` was refreshed
mechanically to `b2251aa6d1be57eef361d25121eac726ed4be23364588158897691318a1a71d0` so
the source-drift guard keeps working. The pin recorded in the retained evidence and in
the image contract above is historical for the reviewed branch tip and is unchanged.
A fresh accounting review of those develop-side hunks is pending; this refresh is not
that review and accepts no coverage, budget or admission.
