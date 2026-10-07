# SPEC-022 exact pre-instrumentation technical review proposal

Status: draft for human technical decision. No instrumentation, grants, registered
measurements, utility acceptance or whole-feature approval. Historical SPEC-021
G4 NO-GO and M4-open status remain unchanged.

## Bound preparation and fixed corpus

Source/code input bytes bind public develop
`cfa6b7b264ebd8c472efc564946e9ce54979e242`; preparation used checkout
`985165f68b63ecafaa1a02b501aeba071deb50c9`, whose only deltas are the
metadata-only assurance snapshot correction and plan note. Selected contract and
fixture-generation input hashes are identical across those commits. Fixture manifest SHA-256:
`ec8f36b21dd745df8443acd6035ff75a4b01bd61fd004470ce0315a655908734`.
Preparation script SHA-256:
`3b2a1d9df9b569f0b3087bf1fc851f7563f388a865af8c63d190419f10155225`.
The manifest binds base/operation commits, patch/content hashes, source/final
expected trees, declared dependencies and operation order for every row below.
Generation completed with observed exit 0; expected trees are constructed from
owned blobs, not verified runtime results. Source commits use a common base.
The chain uses distinct files and dependencies a -> b -> c -> d; it tests order,
not cumulative Git ancestry or overlapping edits.

| Fixed order | Block ID | Aggregate patch bytes | Pre-registration disposition |
|---|---|---:|---|
| 1 | independent-2-1024 | 2284 | Numeric bounds only; admission pending |
| 2 | independent-2-65536 | 133328 | Numeric bounds only; admission pending |
| 3 | independent-2-1048576 | 2130130 | Excluded: runtime/replay patch caps |
| 4 | independent-4-1024 | 4568 | Numeric bounds only; admission pending |
| 5 | independent-4-65536 | 266656 | Excluded: runtime patch cap |
| 6 | independent-4-1048576 | 4260260 | Excluded: runtime/replay patch caps |
| 7 | dependency-chain-4-1024 | 4568 | Numeric bounds only; admission pending |
| 8 | dependency-chain-4-65536 | 266656 | Excluded: runtime patch cap |
| 9 | dependency-chain-4-1048576 | 4260260 | Excluded: runtime/replay patch caps |

The V2 manifest names these declared numerics `pinnedContractCaps`; Luna manually
reconciled them against the bound source constants. They are not runtime-read
counters or observed admission results. V1 remains preserved separately; V2
changes provenance labels/output destination/version and keeps all nine complete
block objects byte-equivalent.

Runtime aggregate patch cap is 262144 bytes; replay cap is 1048576. Existing
2-4 operation/16-path bounds, all stage time/command/output/scratch budgets and
point-of-use verification remain unchanged. No hard memory/global stage deadline
is inferred from those individual budgets. Final admission must be captured
before registration. Any further refusal remains a named exclusion; do not replace
it with a different workload. Do not infer admitted operations from patch size.

## Registration, denominator and stop rules

For each finally admitted block: 2 warm-up pairs then 20 measured pairs. Pair
index is zero-based within each block, including warm-ups; serial runs first on
even indices, parallel first on odd. Both treatments receive identical immutable
fixture inputs and fresh private run/grant destinations. Preserve all warm-up,
measured, failed and unexecuted records with explicit status. No replacement
trials, outlier deletion, favorable complete-case median or pooled chain utility.

There are 9 planned inventory blocks and 5 direct exclusions. At most 4 blocks
remain eligible for admission: at most 8 warm-up pairs and 80 measured pairs
(176 treatments total). Exclusions stay in the inventory denominator, but have
no measured-pair denominator or invented ratios. Report per-block intended,
attempted, valid, invalid and unexecuted counts. The ratio target >=1.10 applies
to each independently admitted block's median paired serial/parallel whole-wall
ratio. Chains are ordering/safety controls and cannot satisfy the independent
workload utility target. Local descriptive observations imply no population,
causal, production, scientific or general workload claim. This corpus is
repeated-character synthetic text and file-disjoint shapes; the chain is only a
declared-order control. It authorizes synthetic performance diagnostics only.
Even a ratio >=1.10 cannot by itself satisfy Constitution Article 19 actual-workload
evidence or close practical-utility/G4/M4 acceptance. Actual workload/source-rights
evidence and a separate founder decision remain necessary for that acceptance.

Proposed experiment dispatch budget: 45 minutes of elapsed registered capture,
with no new treatment dispatched after exhaustion. Existing per-stage completion
and cancellation behavior remains authoritative; 45 minutes is a dispatch stop,
not a hard-kill or hard process-termination guarantee. Budget exhaustion retains
all remaining pairs as unexecuted and prevents a positive complete-protocol
outcome. Unit/profile validation and fixture preparation are outside this
registered experiment budget and are separately reported. No paid/model/host
calls or background service changes.

## Non-overlapping wall phases and observer boundary

The outer treatment clock starts before loading/copying its immutable input and
ends after operational report serialization and owned treatment cleanup.
Exactly one coordinator phase owns each outer-clock interval. Nested runtime,
worker and verification spans are supplemental views, never added a second time.

| Phase | Start / end | Included work |
|---|---|---|
| input | first outer tick / immutable request ready | Input load, copy, normalization and validation |
| replay | replay call begin / returns or fails | Evidence/advisory production, all nested commands |
| preparation | policy preparation begin / returns or fails | Consumer checks, manifest/plan creation, parallel serial reference |
| grant | grant issuance begin / returns or fails | Acknowledgement, store writes and verification |
| execution | execute call begin / returns or fails | Point-of-use checks, worker preparation, references, commit/result/report writes |
| independent verification | final verifier begin / returns or fails | Explicit final tree/report verification |
| report serialization | report encoding begin / operational raw record encoded | Operational report and available observations; not future end timestamps |
| cleanup | owned cleanup begin / completes or fails | Owned treatment directories and resources |
| residual | outer interval minus disjoint phase union | Explicit coordinator/observer gaps; never called zero by assumption |

Per phase and outer interval: monotonic wall timestamps; parent process CPU delta;
completed-child user/system CPU deltas where actually observable. Parent process
CPU includes its threads. Child counters are process-wide cumulative observations,
not per-worker CPU allocation; don't claim live-child CPU that the counter has not
observed. Concurrent unrelated children invalidate counter attribution or leave
it null with reason. Never add inclusive CPU nested spans to their enclosing total.
All interval/counter deltas must be finite, ordered and nonnegative; missing
required wall phase accounting makes SC-001 incomplete, not a synthesized zero.
Optional unavailable CPU/RSS/scratch/overlap/byte observations are null with reason.

Git command and captured-byte observations include all actually observed stage
budgets. Count each command once; describe capture bytes as captured bytes, not
all filesystem/network I/O. Worker interval overlap is computed from the union
and maximum occupancy of observed worker spans, not summed worker duration or
CPU parallelism. Existing sampled scratch and process-lifetime RSS limitations
remain explicit. Refuse overlapping coordinator phases, gaps without residual,
unreconciled totals or double-counted nested work.

The final benchmark envelope must encode its closing timestamp after that tick:
this unavoidable observer sealing/output step is outside the operational outer
interval. Record it separately (elapsed wall and CPU if available, otherwise null
with reason); never describe it as included in the measured outer cost. Per-pair
ratio reports must name this boundary explicitly. Aggregate benchmark artifact
writing is shared observer work, separately timed/reported and never hidden as
free runtime work. No speedup claim may silently move work across the boundary.
If implementation cannot preserve this declared boundary, obtain a revised
protocol review before registered measurement.

## Failure and decision table

| Event | Required disposition |
|---|---|
| Expected cap refusal before registration | Named excluded block, no measured ratios; preserve all 9 inventory rows |
| Further admission refusal before registration | Additional named exclusion; preserve reason; no replacement workload |
| Registered timeout, error, cancellation, missing required accounting or missing treatment | Retain raw pair; block inconclusive; no favorable complete-case ratio/acceptance |
| Grant bypass, unsafe admission, wrong dependency order, source mutation, mismatched final trees or omitted mandatory verifier | Whole candidate NO-GO; stop new treatments; retain every attempted/unexecuted record |
| Manifest/hash/input identity drift | Invalidate registered candidate; stop new treatments; new freeze/review needed |
| Experiment dispatch budget exhausted | Incomplete protocol; remaining pairs unexecuted; no positive utility decision |
| Complete safe block, below threshold | Negative/null descriptive utility; legitimate protocol outcome |
| Complete safe block, at/above threshold | Positive synthetic diagnostic observation only; actual workload evidence and founder utility decision remain pending |

## Requested owner decision

Approve or request changes to this exact corpus inventory, cap exclusions,
registration/denominator rules, 45-minute dispatch budget, phase/observer boundary,
and failure table before T002 instrumentation. This decision authorizes only
implementation and evaluation preparation under existing contracts. At most one
contract-preserving improvement may be selected after diagnostic results and
before registered candidate freeze. Registered measurements require the separately
reviewed stable harness/manifest freeze. No utility acceptance, milestone closure,
external reproduction or expanded runtime authority is requested here.
