# FC.1 real utility resumption — 2026-10-17

## Owner decision and current boundary

The owner explicitly resumed SPEC-034/T005 and approved implementing the FC.1
real-utility plan on 2026-10-17. This supersedes the instruction to keep preparing
SPEC-036 indefinitely deferred, for the software/admission work described here.
It does not erase the [cancelled partial attempt](t005-disposition.md), consume a
new native grant, or accept its original unchecked criterion. Historical decisions,
assurance and receipts retain their exact domains. SPEC-045/T007 remains not_planned.

The first implementation is the source-bound request envelope and concurrent
phase ledger in `agent_braid/forecast_admission.py`. It contains no native launcher,
runtime invocation, model, host inspection, source collection, CLI or MCP endpoint.
The original software paths, public contracts and mandatory verifiers are unchanged.

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
not a hard aggregate quota. The historical runners and supervisor are unchanged.

Until that concrete coverage, storage bound and input-specific request budget
are justified, stop before an executable candidate. Do not create another generic
watchdog, fixture, approval package or retry around unproved limits. The plugin
NO-GO applies to the plugin value scenario; it does not by itself prohibit these
separate fixed-runtime admission controls.

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
