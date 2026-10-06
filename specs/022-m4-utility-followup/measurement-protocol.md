# Prospective bounded utility measurement protocol

Status: candidate for human technical review. Not frozen or approved; no harness
instrumentation or registered measurement has executed for SPEC-022. Historical
SPEC-021 G4 NO-GO remains unchanged.

Population: owned synthetic ordinary-text A/M immutable fixed patches admitted
by existing SPEC-020/021 validation. Corpus blocks: independent 2-operation,
independent 4-operation, dependency-chain 4-operation; payload sizes 1 KiB, 64 KiB,
1 MiB per operation. Existing aggregate caps control admission. Keep any refused
block and its reason; never enlarge a runtime budget to include it.

Each admitted block has one base/commit/patch identity set, two unmeasured warm-up
pairs and 20 measured pairs. Alternate serial-first/parallel-first by repetition
parity. Fresh private run/grant destinations per treatment. Never replace trials,
remove outliers or claim controlled cold OS caches. Chain controls stay separate
from independent-block utility. Freeze exact generated manifest, harness/source,
observation and environment/cost boundary on a clean candidate after review and
before registered results.

Primary outcome: each independent block's median paired serial/parallel total wall
ratio; descriptive target >=1.10, zero unsafe admissions and equivalent independently
verified trees for every admitted run. Any invalid treatment remains in its pair
and makes the affected utility block inconclusive. No complete-case favorable
acceptance, pooling chains, causal claim or inferred general workload benefit.

Whole wall boundary starts before input loading and ends after cleanup. Retain
input/evidence loading, replay, preparation, grant issuance, execution, independent
verification, report serialization and cleanup; include instrumentation overhead.
Phase measurements reconcile to total with explicit residual, never overlapping
phase sums as a purported whole total. Capture wall/CPU/command/byte/worker-overlap
counters only when actually available; unavailable RSS/scratch/counters stay null
with reason. Record hardware, OS, Git/Python, background-load observations, first
and subsequent exposures, failures and exclusions.

Review checklist: fixed corpus identities and order, numeric caps, full cost
accounting, invalid-pair rule, diagnostic-vs-registered separation, forged/stale/
unknown/refusal/recovery controls, candidate freeze and independent-result checks.
An optimization may be chosen only after diagnostic runs, at most one, recorded
before registered freeze. No semantic/grant/consumer check can be removed. Human
technical review precedes instrumentation; founder utility decision follows results.
