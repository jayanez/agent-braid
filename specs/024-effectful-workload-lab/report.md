# SPEC-024 bounded report (T007 review packet)

Status: submitted for review on 2026-10-31. Scientific review: pending.
`executionAuthorization: false` for every artifact cited. This packet makes no
real refinement or independent validation claim; it packages what the lab did,
what it found and what it cannot say.

Packet: this report, [refinement-checklist.md](refinement-checklist.md),
[reproduction-record.md](reproduction-record.md),
[research/workload_lab/README.md](../../research/workload_lab/README.md) and the
SC-007 test `WorkloadReportTests` (`tests/test_effectful_workload_report.py`).

## Question and hypothesis

In a closed finite model of configuration, key-value and local-event
primitives, do captured reads, versions, aliases and event observations expose
order sensitivity that terminal values conceal (hypothesis of the spec)? A
secondary experiment (H2) asks whether a terminal-value additive rule can
recover, for a registered `add-constant` class, the candidates that
exact-resource-overlap classification rejects, at small incremental cost. A
negative or inconclusive answer would have completed the protocol equally.

## Population and protocol

Frozen manifest `examples/workload-lab/manifest.json` with
`registration.json`: 17 synthetic, in-repository fixtures (7 named controls,
10 H2 fixtures), protocol `effectful-workload-protocol-v2`
(manifest hash `ad8b00ca8c8fc4329699cd8ba5f07525b45f00cff604b76d69bacdb9fae6babc`,
protocol hash `7dfb10da9eb1a8a9e1e61b7d73e4641c23920d6283da322b2321e3a912faddb9`). Labels are executable invariants, not human
judgments; no fitting, split or inferential claim. Methods compared on
identical complete coverage: `conservative-all-orders`, `declared-effects`,
`additive-terminal`, `exhaustive-replay` (oracle). 3 warm-ups, 20 measured
repetitions per method and fixture, rotating order, full-stage cost accounting.

## Results

### Controls (T005, evidence `controls-20261022.json`)

All 17 fixtures: complete coverage, authored controls pass (`pass` 17). Each
named control demonstrates its failure or modeled prevention, and capped runs of all
17 fixtures are `inconclusive` and replay-verified (SC-007 test); a capped
control cannot pass (`WorkloadControlsTests`).

| Family | Fixtures | Finite findings (all complete) |
| --- | --- | --- |
| lost update | `lost-update` | divergent: state and results differ across orders |
| write skew | `write-skew` | inconclusive: a blocked path (false guard) stops comparison; state, versions, results, outcome differ |
| stale configuration read | `configuration-stale-read` | divergent: state and results |
| duplicate / idempotent events | `duplicate-events`, `idempotent-events` | terminal projection matches; events (and results) differ and stay explicit |
| alias / hidden effect | `alias-hidden-effects` | projection matches (`results` differ); operation `b` has a missing declaration, so independence is not supported |
| disjoint positive | `disjoint-positive` | projection matches, no mismatch dimension |

### Comparison (T006, evidence `comparison-20261024.json`)

SHA-256 `8635d525dfa3970a3adf0ae0e364f742c8e138a56b3a63d4e934389b53a091b2`;
one registered capture, CPython 3.13.11 arm64 darwin. 17/17 fixtures with
matched complete coverage and passing controls, 0 failed repetitions, no
removals. Per-method stage and total costs and retained-object counts are in
the file. Costs are machine-bound, taken on a loaded developer machine, and
descriptive only. Contextual equivalence and runtime safety: `unknown`.

### H2 (T008, `WorkloadH2Tests` and the same capture)

10 registered H2 fixtures: 4 terminal candidates, 6 exclusions
(outside-additive-class 3, non-success-path 1, unknown-effects 1,
version-precondition 1); exact-resource overlap alone rejects shared-target
additions, the rule recovers 3 (`h2-shared-additions`, `h2-dependent-additions`,
`h2-four-additions`), 0 false terminal candidates, every raw return/event
difference retained. Rule incremental cost: median 1,210.5 ppm, one-sided 95%
upper bound 1,510 ppm over 200 pooled samples, margin 50,000 ppm. Assessment:
`positive`, descriptive and local to the frozen synthetic corpus.

## Limits the reviewer must weigh (T008 required statements)

1. The cost test barely discriminates: the bound is about 33× below the margin,
   because the rule is a single pass over an already verified report.
2. The 200 paired samples pool 10 fixtures × 20 repetitions and are not
   independent; the order-statistic bound is descriptive.
3. The numerator excludes `footprintValidation` (`declared_effects`), which
   every method computes.
4. Disclosure: during the independent review of 2026-10-23 the registered
   experiment was run four times in a disposable copy (all positive; no
   evidence retained), so the outcome was observed before the official run;
   protocol v2 was not changed after those runs. A run under the system
   CPython 3.9.6 (below the 3.12 floor; positive, 3 recovered, 0 false
   candidates) was discarded, and the script was re-executed to shrink the
   evidence format (each time positive, same counts); only the final capture
   is retained.
5. One retained capture is one run. The clean-clone re-execution of
   2026-10-31 (reproduction record) reproduced every deterministic field and
   again assessed `positive` (median 1,259 ppm, upper bound 1,613 ppm); it is
   a reproduction, not a second registered run, and was not retained.
6. A usable positive result means only: on 17 hand-authored synthetic fixtures
   the lab recovered 3 candidates with no false candidate at small cost. It is
   not a utility, generality, safe-parallelism or commutation claim.

## Remaining T007 items

Not done by this packet: the `assurance.json` update, the `quick`/`pr` profile
runs on the final candidate (results are in the PR, not here), the "snapshot
then freeze clean candidate" step, and any independent reproduction or
recorded human scientific review.

## Claims withheld

No contextual equivalence, runtime safety, safe parallelism, real workload or
service correctness, real exactly-once delivery, probability or real-retry
statement, and no AIM certificate. `terminal-projection-match` is never
full-result, trace or effect equivalence. No real refinement or independent
validation has been performed; the checklist lists what such work would need.

## Task dependency loop and closure options (owner decision)

Spec dependencies and status text form a loop: T007 depends on T006 and T008
(`tasks.md`), while T006 and T008 each state that closure awaits the scientific
review in T007 (T008 also lists the T007 packet as including its results).
T007 cannot be closed before T006/T008, and neither can close before T007's
review. Scientific review is also, by SC-007, a pending human step that may
not be inferred. Options for the owner (none is applied by this packet):

- **A. Engineering closure first (T005 precedent, #689).** After an independent
  engineering review on a clean clone, the owner authorizes closing T006 and
  T008 as engineering closures; T007 is then closed once the packet is accepted
  as complete; scientific review stays pending and is recorded separately.
- **B. Joint closure.** One owner decision closes T006, T007 and T008 together
  when the packet is accepted; scientific review is pending without gating any
  task.
- **C. Re-word the edges.** Replace "closure awaits T007 review" in T006/T008
  with "scientific review recorded in T007 (pending)" and define T007 done as
  "packet submitted, reproduced and review requested".
- **D. Keep all open** until a human scientific review is recorded.

Recommendation, not a decision: A, because it is the accepted precedent, keeps
the engineering and scientific gates separate and needs no spec edit; the
independent engineering review for it has not been done by this packet (the
reproduction here was made by the authoring session).
