# M4 runtime cost diagnostics

This developer sidecar explains bounded M4 overhead using the owned two-edit
fixture. It leaves the [frozen measurement protocol](../../specs/021-m4-alpha-runtime/measurement-protocol.md),
`scripts/measure_m4_alpha.py` and historical evidence unchanged. The recorded
[G4 NO-GO](../../specs/021-m4-alpha-runtime/g4-decision.json) remains in effect;
a faster descriptive candidate does not accept or close M4.

## Internal preparation

Parallel policy preparation freshly validates the runtime request and materializes
its private serial rehearsal. It retains that scratch only within the invocation
to compute the serial worker reference, then disposes it before returning a plan.
The reference has its own unchanged wall/command/output/scratch/cancellation
budget; its scratch accounting includes the retained rehearsal and workers.
No caller-supplied digest or durable cache substitutes for input reconstruction.

Every policy consumer reconstructs a new invocation from immutable inputs. The
public schedule and preparation-receipt verifier independently rebuild their
reference. Grants, serialized private publication, effects and recovery retain
the [C2 execution contract](../../specs/021-m4-alpha-runtime/c2-execution-contract.md).

The scheduler creates a run-local executor when a wave has multiple workers,
reuses it across such waves and executes singleton waves directly. All workers
keep separate writable repositories/indexes; later waves wait for their
dependencies. Cancellation and failure stop subsequent work and dispose scratch.

## Capture a frozen candidate

Use the same interpreter and diagnostic script for each clean baseline/candidate
checkout. Output must be outside the measured checkout. No model or host calls,
source ref promotion, cache flushing or external workloads are involved.

```sh
python3 scripts/profile_m4_alpha.py \
  --checkout /absolute/path/to/baseline \
  --output /tmp/m4-baseline-cost.json
python3 scripts/profile_m4_alpha.py \
  --checkout /absolute/path/to/candidate \
  --output /tmp/m4-candidate-cost.json
python3 scripts/profile_m4_alpha.py \
  --compare /tmp/m4-baseline-cost.json /tmp/m4-candidate-cost.json \
  --output /tmp/m4-cost-comparison.json
```

Run each capture in a fresh interpreter. The script loads the frozen treatment and
runtime modules from the selected checkout; six pairs retain the original corpus,
admitted orders and serial-first/parallel-first alternation. Total wall begins
before replay/advisory production and ends after result verification and treatment
cleanup, including grant issuance and every preparation/reconstruction cost.

Each record binds the candidate SHA, frozen input hashes, environment and the
diagnostic script hash. Changes during capture invalidate the record. A comparison
requires matching interpreter/OS/architecture/Git, instrument, fixture and frozen
measurement/protocol hashes, pair identities and equivalent verified result trees.
Before computing medians, it rejects invalidated/drifted captures, negative or
non-integer metrics (including booleans), zero wall times, incomplete phases and
totals that disagree with the uniquely recorded bounded budgets. Zero CPU/RSS
observations remain valid. These consistency checks do not authenticate a record
or substitute for independent runtime verification.

## Read the sidecar

- `pairs[].samples` retains the original total cost and deterministic result fields.
- `diagnostic.phases` records nested inclusive wall time, Git commands and captured
  output for coordinator invocations; `phaseSummary` groups them by function.
- `diagnostic.budgets` lists each bounded budget exactly once with its origin phase,
  consumed counters, sampled scratch peak and unchanged limits. Its command/output
  totals must equal the frozen treatment totals.
- The comparison reports serial and parallel median full costs separately, saved
  Git commands and candidate/baseline wall ratios. A serial regression remains
  visible even if parallel overhead falls.

Do not sum different phase labels: parent phases include nested work. Concurrent
workers share one budget and are attributed to the coordinator phase; their
recorded intervals are observations, not proof of simultaneous CPU execution.
Instrumentation overhead is included. Process-lifetime peak child RSS is not a
per-treatment allocation peak, and phase scratch peaks are not simultaneous
storage. OS caches/background load are uncontrolled, so these small descriptive
samples establish neither causality nor general speedup. Safety reproduction,
independent review, human/founder gates and scientific validation stay separate.

## Current follow-up — 2026-10-09

This guide profiles the frozen SPEC-021 corpus; its six-pair observations and
historical G4 NO-GO retain their original boundary. The registered
[SPEC-022 synthetic study](../../specs/022-m4-utility-followup/successor-protocol-180m.md)
completed 88 valid pairs on b85f7e5. Its three admitted diagnostic blocks had
serial/parallel medians 0.6399138361, 0.6459474869 and 0.8480100361; dependency-chain
controls and exclusions remain separately reported. The
[SPEC-038 real-source study](../../specs/038-m4-real-workload-closure/evidence/registered-capture-summary-e66f9a1.json)
completed 20 valid treatments on e66f9a1, with ten verified matching-tree pairs,
four warm-up pairs and six measured pairs. Its measured median 0.6538998703 favored
serial execution in one finite, uncontrolled two-operation frame.

These populations and protocols are distinct and are not pooled. Costs include
recorded full phases/residuals and separately reported observer costs; missing
metrics are not zero and nested costs are not added twice. Cleaned run/grant paths
cannot be reverified after cleanup. None of these diagnostics shows useful speedup.
The founder approved the bounded utility disposition in item 21 and then accepted
whole bounded M4 alpha engineering and evaluation in item 22 with negative utility.
See the [utility decision](../../specs/022-m4-utility-followup/utility-decision-20261008.json)
and [whole-M4 decision](../../specs/038-m4-real-workload-closure/whole-m4-founder-decision-20261009.json).
Serial remains recommended for the measured families until representative paired
full-cost evidence demonstrates an advantage. The historical G4 NO-GO, capability
deferrals, scientific boundaries and separate governed tracking delivery are preserved.
