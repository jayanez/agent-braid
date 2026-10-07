# M4-C07 protocol and source-rights review packet — draft

**Status:** concrete candidate for review; not reviewed or authorized. No source
execution or collection has occurred. The SPEC-013 candidate is statically
within current operation/path/byte shape based on public commit metadata and
diff inventory; runtime preparation admission, verified result, and rights
remain pending, so a reviewer may still return infeasible.

## Decision requested at this boundary

Review whether (a) the exact candidate source has documented rights for this
specific local M4 use, (b) an eligible 2–4-operation workload can be identified
without changing source identity or existing runtime contracts, and (c) the
protocol below is acceptable for narrow harness implementation and evaluation
preparation under the user's M4 authorization. Acceptance does not authorize
registered capture, runtime grants, or a milestone decision. Record reviewer
identity/role, conflicts, date, exact packet and source hashes, decision,
rationale, scope, exclusions, and any conditions in a separate decision record.
Do not fill this draft as if approval had occurred.

## Exact source candidate and rights evidence needed

Repository `jayanez/agent-braid`; base
`f3c734a1f42d6d5962cfedc57d7f6c1efe40e0a6`; candidate PR #137 commit
`58351f812614058e53a8ee6aef1dd458f1bb70fc` and PR #138 commit
`083f1a390988a9527a5aaeb19133401243b1d714`. Both commits and their M2
footprints are documented in SPEC-013. PR #137 changes three paths/64 lines
(7,872 diff bytes); PR #138 changes five paths/999 lines (55,208 diff bytes).
The paths are disjoint, total 8 paths, and are ordinary 100644 A/M files from
one base with no declared dependencies. This is a real repository task family
whose static shape fits existing path/byte ceilings. Commit authorship is
attributed to Juan Antonio Yáñez García and live PR metadata shows submitter
`jayanez`; this does not itself grant new M4 rights. It is not runtime
admission: no preparation, result tree, rights approval, or execution was
obtained. No patch is admitted by this packet.

Required before a go decision: named source owner/rightsholder; evidence of
authorship/authority for each operation; exact written permission for M4 local
preparation/execution, tree observation, required retention and reporting;
term/revocation; redistribution and redaction limits; and any contribution or
review conflicts. The permissions must match the exact commits, base, methods,
cost logging, and evidence retention. Historical M2 approvals are insufficient.

## Proposed bounded protocol

- **Treatments:** the actual SPEC-021 policy coordinator twice on the same
  immutable source input: `--mode serial` and `--mode parallel`. Each arm
  includes the full coordinator path from evidence/advisory production through
  preparation, explicit grant issuance/acknowledgment, execution, independent
  consumer verification, report serialization, and owned cleanup. This is not
  ordinary replay compared with SPEC-020 alone. Both arms use the same candidate
  and existing `tracked-tree-v1` verifier. No tests or arbitrary repository
  commands, hooks, network/provider calls, host changes, or ref promotion.
- **Workload and order blocks:** exact eligible operations from the candidate
  source frame; run the two legal declared serial orders, `AB` and `BA`, only if
  preflight confirms both. Each arm starts from the same immutable base and
  receives identical operation commits, replay inputs, policy, and budgets.
  Freeze all source/patch/expected-tree hashes and every exclusion before
  results. No source substitution.
- **Warm-up:** two unscored paired warm-ups per operation order (four pairs,
  eight treatments total). For each order, warm-up 1 is serial-first and
  warm-up 2 parallel-first. They use fresh result and grant destinations and
  are retained with costs/status, but excluded from measured ratios. They are
  not called cold-cache trials and no OS caches are flushed.
  Dispatch these warm-up pairs first, in this exact global order:

  | Global pair dispatch | Pair ID | Operation order | First coordinator mode |
  |---:|---|---|---|
  | 1 | W-AB-1 | AB | serial |
  | 2 | W-AB-2 | AB | parallel |
  | 3 | W-BA-1 | BA | serial |
  | 4 | W-BA-2 | BA | parallel |

  Within each pair, the second treatment uses the other coordinator mode.
  The six measured pairs follow these four warm-up pairs without interleaving.
- **Measured sample:** three paired repetitions in each operation order: six
  measured pairs, twelve treatments. Fixed IDs are `M-AB-1..3` then `M-BA-1..3`.
  Seed string is `SPEC-038-v1|seed=380038|base=f3c734a1f42d6d5962cfedc57d7f6c1efe40e0a6|a=58351f812614058e53a8ee6aef1dd458f1bb70fc|b=083f1a390988a9527a5aaeb19133401243b1d714`; its SHA-256 is
  `9a99f698a3b13f59329a5dee14fcc8af0e610cd8f1b2f3a6ad8d6dffaffbef8c`. For
  measured pair order, sort IDs by ascending SHA-256 of `seed-string + "|" +
  pair-id`, breaking ties lexically. The frozen schedule is:

  | Global pair dispatch | Pair | Operation order | First coordinator mode |
  |---:|---|---|---|
  | 5 | M-AB-2 | AB | serial |
  | 6 | M-BA-2 | BA | parallel |
  | 7 | M-BA-3 | BA | serial |
  | 8 | M-AB-1 | AB | parallel |
  | 9 | M-AB-3 | AB | serial |
  | 10 | M-BA-1 | BA | parallel |

  The seed digest first byte is even, so modes alternate serial-first,
  parallel-first. Freeze this exact schedule in the reviewed manifest before any
  result. Every treatment gets a fresh private
  result and grant destination. No replacement pairs or favorable complete-case
  denominator.
- **Outcomes and denominator:** retain all four warm-up and six measured pair
  slots, treatment order, intended/attempted/valid/invalid/failed/refused/
  interrupted/recovered/unexecuted status, source immutability, final trees,
  verifier results, conflicts/dependencies/refusals, observed overlap, and
  diagnostic usefulness. The six measured pairs are descriptive repetitions of
  one finite task frame, not six independent workloads. Primary descriptive
  statistic is the median of six per-pair ratios `serial total wall / parallel
  total wall`, with all six raw ratios and per-order summaries. Report first and
  later exposures separately. No threshold, hypothesis test, causal or
  population inference; a direction either way is descriptive only.
- **Full total-wall boundary:** each treatment timer starts before its evidence
  production/input load and ends after the coordinator's independent consumer
  verification, operational report serialization, and treatment cleanup. Record
  non-overlapping `input`, `replay`, `preparation`, `grant`, `execution`,
  `independent_verification`, `report_serialization`, `cleanup`, and explicit
  `residual` wall phases, plus the outer total. Nested intervals are supplemental
  and never added twice. Include all setup, replay, coordinator work, grants,
  execution, validation, reports, and cleanup in the treatment ratio. Report
  source/right acquisition, review time, environment setup, operator effort,
  final observer sealing/output, and shared artifact writes separately outside
  the per-treatment ratio; state their actual measured costs or null with reason.
  Capture available parent/child CPU, Git commands, captured bytes, sampled
  scratch, process-lifetime RSS, worker intervals, and their limits. Never call
  unavailable costs zero or infer CPU parallelism from overlap.
- **Fresh-process control:** after all treatments and before sealing the packet,
  start one new Python process with no inherited measurement-process state. Use
  only existing read-only SPEC-021 verify/inspect paths to inspect all 20
  treatment slots (four warm-up pairs plus six measured pairs), independently
  verify each completed result, and compare final tree identities within each
  pair. An unexecuted slot is checked as an explicit unexecuted disposition.
  This control executes no workload code and issues no grants. Time and report
  it separately; it is not included in treatment ratios. Final evidence-directory cleanup and packet
  sealing are timed separately. Missing/mismatched verification makes the
  affected pair invalid and the packet inconclusive.
- **Budgets and timeout:** total registered dispatch budget is 45 minutes from
  first warm-up start; no new treatment starts after expiry. Retain all remaining
  slots as unexecuted. Existing per-stage SPEC-021 caps remain unchanged,
  including its 60-second shared worker-stage budget, 256 Git commands,
  2-MiB command output, 64-MiB sampled scratch, and 8-MiB result output; the
  protocol does not raise them. Each treatment has a 360-second observation
  deadline matching the pinned SPEC-021 tool timeout. A timeout is incomplete,
  never success; do not hard-kill outside current cancellation/recovery
  semantics. If state is uncertain, stop dispatch and use only existing inspect,
  verify, or recovery procedure. The active treatment may finish its existing
  bounded safe path after the 45-minute no-new-start point; retain all such
  time and outcomes. Report end-to-end experiment wall from first warm-up start
  through fresh-process verification, final private cleanup, and packet seal,
  with the shared observer work and every treatment interval separately
  itemized.
- **Stops and interpretation:** stale inputs, unsafe paths/modes/effects,
  invalid grant, source mutation, wrong tree, verifier disagreement, or
  mismatched manifest stop new dispatch and preserve all records. A verified
  tree is an observation under declared contracts, not semantic equivalence.
  Negative, null, inconclusive, and infeasible outcomes are valid. This finite
  description makes no generalized speedup, safety, confluence, or M4 claim.

## Review boundaries

1. **Protocol/source rights:** exact source, provenance/rights, eligibility,
   complete frame, serial/parallel coordinator method, pair count, order, full
   total-wall accounting, budget, fresh-process control, and stop rules.
   This is the present requested boundary.
2. **Stable harness/manifest:** after narrow implementation, independent review
   of exact candidate, harness behavior, generated manifest, verification,
   refusal/recovery and accounting before any capture-specific approval.
3. **Capture authorization:** separate exact human authorization required after
   boundaries 1 and 2. No authorization is requested or recorded here.
4. **Whole-M4 decision:** after evidence and independent review, a new founder
   decision must consider the entire SPEC-021 closure matrix. Historical G4
   NO-GO and M4-open status remain visible; no protocol result alone closes M4.

## Current open gates

Source rights are unknown; patch eligibility is unevaluated; the proposed
complete frame may yield no admissible batch; protocol/source review is
pending; stable harness/manifest review and capture authorization do not yet
exist; no actual-workload evidence exists. No claims about approval or result
are made.
