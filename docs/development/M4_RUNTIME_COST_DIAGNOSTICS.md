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

## Current follow-up — 2026-10-07

This guide profiles the frozen SPEC-021 corpus; its six-pair observations and
historical G4 NO-GO retain their original boundary. The subsequent
[SPEC-022 quickstart](../../specs/022-m4-utility-followup/quickstart.md) documents
full-cost instrumentation and the registered comparison workflow. The
[180-minute successor](../../specs/022-m4-utility-followup/successor-protocol-180m.md)
is implemented for preparation after owner review; it preserves the original
45-minute plan version and does not authorize capture. Exact stable-harness and
manifest review, registered measurement and any new utility decision remain
separate pending gates. Engineering preparation diagnostics are not registered
measurement evidence. As of 2026-10-08, the [SPEC-038 real-workload study](../../specs/038-m4-real-workload-closure/implementation-readiness.md)
has owner-approved exact source-use rights and protocol. The bounded harness is
merged and validated; static admission and technical review cover the exact two
operations and 20 slots. Owner stable-candidate/manifest review and separate capture
authorization remain pending.
