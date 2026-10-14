# FC.2 convergence supplement: costs and daemon boundary

This companion supersedes stale *pending actual-model* descriptions only within
the exact recorded source-e6/Chronos-v5 and owned-engine-v3 scope. Historical assurance snapshots and original task
criteria remain unchanged. No checkbox, GitHub issue, milestone or approval is
closed by this inventory. The new cost observer is an additive software candidate;
it has not been exercised with an actual model.

## Obtained baseline and model evidence

Candidate `7da458ce9125b30bb37e76f785ed3a6f2e60b8ac` passed the complete local PR
profile: 1464 tests, 12 skips. Exact-head GitHub validation and tracking also passed;
solo/dual integration was explicitly skipped. It remains draft PR #508, unmerged.
The source-e6 independently built/installed core produced 216 responses with
API/CLI/MCP parity and two independently granted synthetic Git episodes. Both
Git comparisons are inconclusive because the Chronos choice was unavailable.

One separately approved v5 procedure on source-e6 artifacts retained seven
actual CPU forecasts and two expected refusals in 33.208679542 seconds through
cleanup. It verified API H1/5/10 and CLI/MCP H1 numerical parity, owned attach-client
interruption and actual worker OOM. Luna checked bindings, all packet digests,
outcomes and cleanup without another model run. The consumed one-run pin was
removed. The broader v3 synthetic conformance remains bound to its earlier exact
artifact; it is not silently reassigned to e6 or the new cost wheel.

## Additive cost candidate validation

Software candidate `bdfa810b7c8bd22b9631a0579a4e19cb3a20ca09` passed the stable
local PR profile: 1486 tests, 12 skips, 1431.423 seconds. Exact-head validation
run 38571721649 and tracking run 38571721441 passed; solo/dual integration remained
explicitly skipped. The earlier development quick run was interrupted after its
inputs changed and is not counted as passing evidence.

Thirty-seven focused controls passed. Luna Latest independently reviewed the
ledger, origin, interruption and daemon-loss boundaries, including negative probes
and a coverage mutation. Two offline builds produced byte-identical wheels:
SHA256 `f7ecc403b51a921a0b5cb8c4bf66f5891501889ecf5e5881c454fab4be05ffe5`.
Installed Python in isolated mode outside the checkout retained baseline, cache
and absent-model responses plus two independently granted synthetic Git episodes.
Both comparisons remained inconclusive with no valid forecast-guided pair.

The observed interval was 55.065075791 seconds: union 54.987536793 seconds and
unattributed residual 0.077538998 seconds. Coordinator CPU was 5.540519 seconds;
waited-child CPU was 25.239438 seconds with a partial observation boundary.
Process-lifetime peak RSS was 29,179,904 bytes. These separate scopes are not summed.
Engine CPU, worker CPU, prior artifact setup and final receipt publication remain
uncovered. No model or Docker workload ran in this increment; full deployment
cost acceptance remains false. Raw private reproduction and independent review
remain preserved under their exact candidate and artifact identities.

## Separately admitted VM qualification

The one-run request SHA256
`cdb2a15ba62dfa288144d09e0cae3771c696fcee42e1eef0c60a32414115cb53`
was separately admitted by the owner and consumed once. The native VM started
and stopped with confirmed SDK cleanup in 10.975290875 seconds, including the
wrapper; helper wall time was 10.630016 seconds. Linux mounted the EROFS root
read-only and reached a shell. The owned helper is gone, the pin is absent, the
claim remains, and the cleanup lease is confirmed. The retained 20 GiB sparse
scratch file has zero allocated blocks. Luna Latest independently inspected the
bindings, console, receipts, lease, pin and process absence without another run.

This authentic local VM measurement used one configured guest vCPU and 4 GiB guest
RAM, with no hard host CPU/virtualization-overhead cap. Its best-effort 80-second
budget was met. It exposed no checkpoint, network device or shared directory,
and ran no forecast or Docker workload. Docker readiness remains unobserved;
VM stop is not worker/daemon conformance or full deployment-cost acceptance.
The frozen private procedure, approval, raw records and observation summary are
retained separately. The separately reviewed empty-engine request
`c2298e56c5ab45494131ceb81952f79680b1f4a58d6c2868967a292eef89c564`
was then admitted and consumed once. It failed before daemon startup: the guest
Python executable lacked its `encodings` standard-library module and PID1 exited.
The wrapper correctly returned incomplete (exit 2), retained the missing guest
receipt and kernel diagnostic, and confirmed SDK cleanup and pin removal within
68.737762333 seconds (helper 68.394346208 seconds). Its new 20 GiB scratch file
still has zero allocated blocks. No Docker readiness or crash was observed; no
retry is admitted.

The separately reviewed shell-based request SHA256
`1c0f29dfe83593fe9f282d9edf865d66218b813c2b43a82e358747f0969a27f1` was then
admitted and consumed once. The VM and guest shell started, but the script stopped
at its first mount because `/dev` was already mounted (`mount: /dev: devtmpfs
already mounted on /dev`). The collector reported incomplete (exit 2) and the
wrapper confirmed VM stop, cleanup and pin removal within 68.788 seconds (SDK
helper 68.393 seconds). The 20 GiB sparse scratch file has zero allocated blocks;
the claim and failed console remain preserved. The guest did not format its data
disk or start Docker, so no engine readiness or daemon crash was observed. The
long-lived Virtualization.framework service remained; no owned probe helper or
Docker daemon process remained. Luna Latest independently inspected the exact
receipt, console, lease, pin and process state. This failed attempt cannot close
the integrated worker fault or full-cost obligation. Any further correction needs
a new exact procedure and owner decision.

The shell-based request SHA256
`49e62e87a496e504a2504ae73fcc1ea2b3beeefebf1e78814b53007d0ac1dca8` was then
admitted and consumed once. The guest verified its existing `/dev` mount, formatted
and mounted only its private scratch disk, and invoked `/usr/bin/dockerd` with the
owned socket and data paths. The captured PID was 117 with `comm=bash`; the guest
never established the expected executable identity or Docker readiness. Two
readiness probes found no Unix socket, `kill -0` then found the process absent, and
the shell ended `incomplete` with no crash-admit token. No `/info`, image or
container observations were made and no daemon crash was induced. The VM stopped
with cleanup confirmed in 68.793450334 seconds; the helper reported 68.422456958
seconds. The owner pin was removed and claim retained. The private 20 GiB ext4
scratch image remains preserved (8,872 host blocks allocated) and reports that
journal recovery would be needed; it has not been mounted or repaired. The daemon
log was directed to guest `/run` tmpfs and was lost on VM stop. Luna Latest
independently confirmed the result and process boundary without another VM run.
This attempt establishes neither daemon readiness nor crash conformance. Any new
procedure must preserve bounded daemon diagnostics outside ephemeral guest tmpfs
and needs its own exact review and owner decision.

## Bounded daemon-log correction v5: executed, incomplete

The v4 collector was not presented to the owner or executed. Luna's review found
that its console export stopped at 32 KiB while the persistent ext4 log remained
unbounded. The v5 collector corrects the writer path: a private FIFO feeds an
exact 32,768-byte persistent prefix, and a separate reader continuously drains
the remaining output until EOF while retaining only its byte count. An
independent synthetic FIFO test kept the writer open for 3.2 seconds, then sent
another 1 MiB; the stored file stayed at 32 KiB and the writer completed. The
guest's post-stop join is bounded to one second and reports failure if the reader
is still active; a missing completion marker fails closed.

The exact v5 request is SHA256
`2d559fe1783b3ddd12297207ad6049cde3776a0f3a13b21bf4a61cd1b9e79286`.
Luna Latest independently checked all 21 unique asset bindings, embedded shell,
code signature and its sole Virtualization entitlement. Its refreshed
configuration-only receipt is 144 bytes and reports `vmCreated=false` and
`vmStarted=false`. Fifteen Python synthetic tests, eleven native preflight cases,
the bounded-input control and plan-only validation passed. The live-FIFO test
does not exercise the join timeout or VM supervisor stop timeout dynamically;
those paths were source-reviewed and remain separate from executed evidence.
The v5 request was then approved and consumed once. Its VM and private scratch
were cleaned up and the owner pin was removed. Linux reached the guest shell and
started the pinned `/usr/bin/dockerd`, but Docker exited before readiness with
`invalid userland-proxy-path: userland-proxy is enabled, but userland-proxy-path
is not set`. Two readiness probes observed no socket; no `/info`, image or
container observations were made, no crash admission was issued and no signal
was sent. The receipt also exposed a count parser defect: the collector saved
the decimal `wc` output, but the summary treated the count's text length as the
number of drained bytes. The attempt result SHA256 is
`d1cd4f6687a59d0c5b0505fb171ca4d8917fce1e35ced6711683874385b009ba`.

## Corrected empty-engine packet v6: executed, incomplete

The v6 packet SHA256 is
`70be094fbce64dc5ebe06a1757da7106a2764a7331f42be4b1c24a925d925e4f`.
It explicitly disables Docker's userland proxy in the owned daemon config,
checks that config with one `dockerd --validate` invocation before daemon start,
and parses the numeric drained-tail count before computing total bytes and the
truncation flag. The updated host protocol pins the exact new config bytes, and
the request records the consumed v5 failure and cleanup result.

The packet's 16 Python synthetic tests (including the counter/truncation cases
and live FIFO cap), 11 native preflight cases, Bash syntax check and bounded
input control passed. The signed helper verifies with its sole Virtualization
entitlement, its embedded guest script matches the source, and the refreshed
configuration-only receipt says `vmCreated=false` and `vmStarted=false`. Luna
independently reviewed this exact v6 packet and found it ready for presentation;
the owner approved the exact request SHA and its single run was consumed. The VM
stopped and cleanup was confirmed in 68.777864458 seconds; the pin was removed.
The private daemon config passed `dockerd --validate`, and the captured process
was verified as the pinned `/usr/bin/dockerd`. Docker then exited before API
readiness with `error initializing buildkit: error creating buildkit instance:
failed to find runc binary`. The bounded diagnostic was retained (90 bytes),
showed two failed readiness probes, and no image/container observations occurred.
No crash-admit token was sent and no daemon signal was issued. The result
SHA256 is `67cf3d5752fc939c74cac74ba2685f71d49c2d6611b16320908be55980fe11e4`.
This is not worker conformance or full deployment-cost evidence.

Read-only metadata inspection of the installed EROFS image confirms `/usr/bin/runc`
is a regular executable matching the pinned digest, and its containerd config
declares `io.containerd.runc.v2`; the same image contains the executable
`/usr/bin/containerd-shim-runc-v2` (SHA256
`709fa03b8b731c50ce3241247a4945b49c14e3ef0d8584c0159daf291fcb151f`). The
upstream [containerd Runtime V2 documentation](https://github.com/containerd/containerd/blob/main/docs/runtime-v2.md)
says the runtime shim is resolved through the normal `PATH`. The v6 receipt did
not record that environment, so this supported collecting and checking `PATH`
and both runtime names but did not prove the cause of BuildKit's exact error.

## Corrected empty-engine packet v7: executed, incomplete

The v7 request SHA256 is
`2f6d04aa315fbc8d342c3a91185a9337a327b7f6f4e634a64d7c51b8068d04e1`; the
consumed result SHA256 is
`f47ae30bac9384a207969be1f1482edbb28a60e1476617385e9a188edeb032b2`. Luna
Latest independently verified the exact request/result binding, all 23 asset
bindings, the admitted decision, cleanup lease, pin removal, and absence of a
remaining owned probe process. The VM stopped and cleanup was confirmed after
68.718455750 seconds.

The guest resolved both pinned runtime tools at `/usr/bin/runc` and
`/usr/bin/containerd-shim-runc-v2`, validated the private daemon configuration,
and launched the pinned `/usr/bin/dockerd`. This confirms those PATH lookups in
this run, but not daemon readiness. Host preflight saw `/info` return HTTP 200
with JSON `null`, `/images/json?all=1` return HTTP 499, and
`/containers/json?all=1` return `[]`. Because the image population could not be
established, the host rejected preflight and did not send the crash-admission
token. No image/container creation request or daemon signal was issued; the
approved crash control was not exercised.

The supervisor stopped the VM immediately after preflight rejection. Thus the
guest completion marker, exit-trap summary, drained-log count, and signal/wait
receipt are absent; the apparent completion-marker text in console output is
the echoed script source, not an emitted guest event. Luna confirms
`guestResult=null`, `enginePreflightValidated=false`, and
`guestCompletionSeen=false`. This is a failure-path observability gap in the
control protocol. It neither establishes a daemon crash nor explains the null
and 499 API responses. The exact v7 run is consumed; no follow-up VM run is
authorized by it.

## SPEC-045 task matrix

| Task | Obtained evidence and procedure | Remaining acceptance boundary |
|---|---|---|
| T001 | Engineering ownership/contracts, owner implementation scope, independent Luna technical review; `engineering.json`, `technical-review.md` | Additive cost contract technically reviewed; canonical ADR adoption remains separate |
| T002 | Seeded signal families, causal negatives, independent synthetic Git fixtures; `independent-core-summary.json` and installed raw receipts | Cost observer fixture tests and stable candidate validation obtained; no real source admission |
| T003 | Default-off session API/CLI, causal/cache/deadline/refusal tests; source-e6 validation and installed core/model receipts | New installed core wheel validated; actual model evidence retains original artifact binding |
| T004 | Separate bounded read-only stdio MCP; installed core parity and actual v5 MCP H1 | New installed core validated; active System 1 bridge stays deferred |
| T005 | Owned immutable receipt store/schema inspection/export tests | New cost ledger publication/inspection is a companion, not a change to historical store schemas |
| T006 | Installed core reproduction and independently reviewed v5 interface/fault receipts | Synthetic daemon-down lease test and additive wheel/profile/review obtained; actual whole-daemon fault is not covered |
| T007 | Actual v3 conformance; independent e6/v5 API/CLI/MCP, attach interruption, OOM and cleanup | Full deployment cost counters/allocation and owned whole-daemon control; new artifacts/procedures need exact admission |
| T008 | Public evidence index, frozen procedures/owner decisions, draft PR and proposed managed FC.2 records | Governed merge, reviewed publication, scoped tracking and private Project readback |

## Original FC.1 obligations affected by this increment

| Task | New technical evidence | Residual obligation |
|---|---|---|
| 034/T002–T004 | Cost phase offsets, overlap union and residual; causal fixtures unchanged | Permissioned capture/operator chain stays separate |
| 035/T005 | Synthetic daemon-loss refusal, retained identity, persistent cleanup marker and next-lease denial | VM stop/cleanup observed; owned daemon crash/destruction and operator marker recovery remain pending |
| 035/T007–T008 | Existing independent installed/model evidence remains usable; new core-cost wheel bound separately | New candidate installed validation obtained; exact actual-model/cost/engine packet remains gated |
| 036/T002, T005–T006 | Optional observer captures per-arm preparation, replay, grants, execution, verification and cleanup, retaining failed arms | Engine/model/setup allocation, supervision/publication and real registered roster |
| 037/T005–T007 | Explicit overhead/cost gaps prevent treating fixture economics as complete measured utility | Real shadow/source chain, exact scope decision and promotion gates |

Other original FC.1 tasks retain their previous status and literal criteria.
No current model pin, synthetic fixture, test result, receipt hash or GitHub green
check admits real sources, launches an experiment, adopts an ADR, accepts utility
or promotes forecasting. M4 historical utility NO-GO is unchanged.

## Remaining bounded work

1. Integrate actual engine/model counters and setup allocation under a separately
   admitted exact procedure. Keep every uncovered deployment counter visible.
2. Complete daemon-environment readiness and exact integrated cost/fault admission.
   Native VM boot/stop and a read-only Linux shell are separately qualified; six
   admitted empty-engine attempts remain incomplete: the first lacked guest
   `encodings`, the second found `/dev` already mounted, the third did not establish
   the daemon executable identity, and v5 reached the pinned daemon but rejected
   its configuration before readiness; v6 passed configuration validation but
   BuildKit could not locate `runc`; v7 resolved both pinned runtime paths and
   launched the daemon, but `/info` returned JSON `null` and the images endpoint
   returned HTTP 499. The host therefore withheld crash admission and stopped
   the VM before the guest could emit its bounded failure receipt. PATH lookup
   is now observed, while daemon readiness, the cause of the API responses,
   failure-path receipt delivery, integrated worker/daemon failure and model
   cost collection remain pending. Diagnose and test the receipt protocol
   offline with synthetic null/499 fixtures before proposing any new exact
   execution packet; consumed approvals do not carry over.
3. The exact software candidate is frozen and validated. Merge requires the owner's
   actual integration decision. Post-merge tracking must use canonical clean
   develop, reviewed guarded operations and FC.1/FC.2-only readback; do not apply
   unrelated M4.5 or historical tracking changes.
