# HAR.2 T005 case roster and arm identities

Status: **Draft for founder freeze — not frozen.** Drafted 2026-10-30 at
`develop` `0a002d0f8cef32cdf6ff5863ffec9e5bb2848bc6`. Trace: SPEC-049/T005.
Machine-readable draft with input hashes and commands:
[evidence/registration/t005-roster-draft.json](evidence/registration/t005-roster-draft.json).

This draft answers the two founder inputs that
[evaluation-report.md](evaluation-report.md) and
[evidence/t005.json](evidence/t005.json) list as blocking the deterministic
cohort: a case roster and the A/B/C arm identities. It is a proposal only. It
freezes nothing, runs no cohort and reports no outcome. The cohort stays
descriptive only (protocol D3) and `executionAuthorization` stays false. A freeze
needs a founder decision record, as T002 had
([t002-founder-freeze-20261028.json](evidence/registration/t002-founder-freeze-20261028.json)).

## 1. Case roster

Every case comes from an anchor registered in [corpus.md](corpus.md) and
[source-registration.md](source-registration.md). No other case is proposed.
All are `synthetic`. Anchor bytes were re-hashed at the draft head and equal the
pinned values, and the named test methods sit at the registered lines.

"Anchor runs" means the existing repository test passes today. All 7 anchor
tests passed (`Ran 7 tests ... OK`, command in the JSON draft). That is a
regression check of the source fixture, not an HAR outcome. "HAR case
executable" means a registrable `harness_verification.Unit` exists: a task
input, frozen rubric and deterministic oracle bound into a unit hash. **None
exists for any case.** Building them is construction work that must finish
before the freeze (R11).

| Case | Lineage | Family | Stratum (R4) | Source anchor | Anchor runs | HAR case executable | Partition (fallback, today) | Partition (if L4 qualifies) |
|---|---|---|---|---|---|---|---|---|
| L1-C03-a | L1 | C03 | coordination | S01 `RuntimeSchedulerTests.test_real_overlap_isolated_resources_and_serial_effect_agreement` (line 63) | yes | no | holdout | discovery |
| L1-C03-b | L1 | C03 | coordination | S01 `RuntimeSchedulerTests.test_dependencies_serialize_waves_and_reversed_order_is_safe` (73) | yes | no | holdout | discovery |
| L1-C02-a | L1 | C02 | coordination | S01 `RuntimeSchedulerTests.test_changed_footprints_limits_and_stale_inputs_never_start_workers` (191) | yes | no | holdout | discovery |
| L1-C03-c | L1 | C03 | coordination | S01 `RuntimeSchedulerTests.test_new_recovery_grant_preserves_worker_journal_without_rerun` (270) | yes | no | holdout | discovery |
| L1-C01-a | L1 | C01 | continuity | S01 `RuntimeSchedulerTests.test_fresh_process_kill_preserves_prefix_and_resume_does_not_rerun_workers` (303) | yes | no | holdout | discovery |
| L2-C01-a | L2 | C01 | continuity | S02 `ToolingSessionTests.test_candidate_drift_after_dispatch_is_retained_as_interrupted` (573) | yes | no | discovery | discovery |
| L3-C02-a | L3 | C02 | coordination | S03 `GitAdapterTests.test_overlap_dependency_delete_binary_and_uncertainty_are_conservative` (79) | yes | no | unassigned | unassigned |
| L4-C04-a | L4 | C04 | continuity | S04 DDP-T08 and S05 coordinator handoff (documents) | n/a (documents) | no; the derived packaging task is not constructed | not in roster | holdout |

All L1 cases share the S06 `GitRuntimeTests.setUp` base, so they count as one
independent unit for inference.

### Partition per D1

- **L4 holdout (D1's first choice).** It applies only if a derived C04 task
  qualifies. Proposed test for qualifying (R2): before any outcome, the task has
  a constructed input, a frozen rubric and a deterministic oracle that checks
  artifact/source identity and that pending gates stay visible. That task does
  not exist today, so L4 does not qualify.
- **Whole-lineage holdout (D1's fallback, the only assignment possible today).**
  L1 is held out whole, which covers both axes and three families. L2 is
  discovery. Holding out L2 instead would leave a one-case, continuity-only
  holdout with no coordination axis.
- L1 is never split under either assignment. L3 stays unassigned under both until
  its relation to L1 is resolved (R3). It is not counted in either partition.

### What the fallback still lacks

- **A thin discovery set.** Discovery is one C01 case. An arm-C refinement round
  run on it sees only continuity material.
- **Uneven strata.** Continuity has 1 holdout case and coordination has 4.

## 2. Arm identities

`harness_evaluation.register` needs three candidate hashes and a matched profile
hash. B must differ from A. A must equal the base of the arm-C refinement round,
and C must be that round's chosen candidate, or the base when the round keeps it.

No guidance surface is committed in the repository today: no manifest base
inventory or guidance file exists outside test fixtures. So A and B below are
**proposed bytes** whose hashes are computed with the repository's own code
(`system_one.digest` and the `harness_refinement._candidate_hash` overlay). Each
hash freezes only if the founder accepts the bytes.

| Arm | Role | Proposed content | Candidate SHA-256 | Status |
|---|---|---|---|---|
| A | static base | Empty guidance inventory (`[]`): the unchanged base harness with no added guidance | `4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945` | computed; proposal (R5) |
| B | checkpoint/context guidance | A plus one file, `guidance/checkpoint.md` (493 bytes, file SHA-256 `dc3324a6529df71d66945e9999f4ba0f3df754b9b4a84338b9a87d2cce3ebf80`; text below) | `4bc36ca01e403f9312a74c7658fb77cea88465fc993875a540eff8974fa36516` | computed; proposal (R6); differs from A |
| C | contrastive refinement | Candidate selected by a recorded `harness_refinement.run_round` on discovery, or A on an explicit keep-base | **not computable** | **founder input** (R8) |

Proposed `guidance/checkpoint.md` (exact bytes, UTF-8, trailing newline):

```text
# Checkpoint and context guidance

- Before each step that changes files, record a checkpoint naming the step, its inputs and the source revision.
- After an interruption, read the latest checkpoint and resume at the first step it does not mark complete. Do not repeat completed steps.
- If the source revision or a declared input changed since the checkpoint, stop and report the drift instead of continuing.
- Keep a short handoff note listing done steps, pending steps and open conditions.
```

**Matched profile (R7).** Proposed profile SHA-256:
`2f42b12d6c9777826922632fedccb5e51761646cca81a40aa79c3c978aa92ba4`. It is the
`system_one.digest` of this record: cohort `synthetic`; host `offline` with
model, effort and route `null`/`null`/`offline`; simulated containment; no
tools; the SHA-256 of the six source inputs S01–S06; and the digest of
`harness_manifest.DEFAULT_LIMITS` (`a3975840…1dbb3c`). It binds anchor bytes
rather than a commit, so unrelated commits do not change it. `register` treats
this hash as caller-declared, and nothing ties it to a run manifest
(module docstring).

**Arm C cannot be produced today.** It needs all of the following, none of which
exists:

1. A real proposer. Only injected test doubles exist.
2. A harness manifest whose base inventory is A and whose `allowedComponentPaths`
   include `guidance/checkpoint.md`.
3. A frozen selection policy (`marginMicros`, `maxProbes` ≤ 4) bound to that
   manifest.
4. A prober that scores candidates with an independent verifier on discovery
   cases.

## 3. Arm order

**A–C Latin square (D1).** `register` computes it from the unit ids, rotating
A/B/C within each task family in sorted id order. The preview below comes from
`harness_evaluation._order` on the draft case ids. The final order is whatever
`register` records at the freeze.

| Holdout case (fallback) | Family | Order |
|---|---|---|
| L1-C01-a | C01 | A, B, C |
| L1-C02-a | C02 | A, B, C |
| L1-C03-a | C03 | A, B, C |
| L1-C03-b | C03 | B, C, A |
| L1-C03-c | C03 | C, A, B |

If L4 qualifies, L4-C04-a gets A, B, C. A family with one case never rotates, so
only C03 is counterbalanced (R9).

**Arm D fixed temporal order (D1).** D1 orders arm D by lineage construction
order. No case is constructed yet, so the draft takes registration order (L1, L2,
L4) as construction order, with each lineage's cases in source line order:
L1-C03-a, L1-C03-b, L1-C02-a, L1-C03-c, L1-C01-a, L2-C01-a, and then L4-C04-a if
it is constructed. L3 is excluded while unassigned. Libraries start empty and
separate for each comparator and cohort. A case sees only entries from strictly
earlier eligible cases; what counts as eligible is R10a. Arm D stays infeasible
until arm C exists (R10).

## 4. Decisions for the founder

Accept, change or defer each item separately. Recommendations are in brackets.

- **R1 Case set.** The 7 anchor-derived cases above, plus L4-C04-a as a
  placeholder that counts only if constructed. No other case. [accept]
- **R2 Partition.** L4 holdout if L4-C04-a meets the qualifying test above before
  any outcome. Otherwise use the fallback: L1 holdout, L2 discovery. [accept; the
  fallback applies today]
- **R3 L3.** L3-C02-a stays unassigned. The merge-or-stand-alone question is
  deferred until someone compares the S03 and S06 fixture provenance. [defer]
- **R4 Strata.** Strata follow the axis: continuity (C01, C04) and coordination
  (C02, C03, with C03 classed by its parallelism endpoint). There is one
  synthetic-offline cohort, and native data is kept separate. [accept]
- **R5 Arm A.** Empty guidance inventory, candidate
  `4f53cda1…1202b945`. [accept]
- **R6 Arm B.** `guidance/checkpoint.md` with the exact bytes above, candidate
  `4bc36ca0…fa36516`. [accept or edit the text; any edit changes the hash]
- **R7 Matched profile.** The offline profile record, hash
  `2f42b12d…aa92ba4`. [accept for the synthetic cohort; a native cohort needs
  its own profile]
- **R8 Arm C.** This is a founder input. (a) Defer until a real proposer exists,
  through the native branch T004/T008. (b) Accept a deterministic proposer that
  abstains in both scopes. The round then records `keep-base`/`all-abstained`, so
  C = A by construction: it satisfies `register` but carries no information. Either way,
  the manifest, policy margin and probe budget for the round must be supplied.
  [(a) defer]
- **R9 A–C order.** The Latin-square rotation as `register` computes it. Accept
  that singleton families get A, B, C unrotated, and record this as a descriptive
  limit. [accept]
- **R10 Arm D order.** The fixed sequence above, with registration order taken as
  construction order. D stays conditional on arm C and T006. [accept]
- **R10a Arm D eligibility.** (a) Every strictly earlier assigned case is
  eligible, discovery or holdout, as online experience from earlier-task
  prefixes. Under the fallback, later L1 holdout cases would then draw on entries
  from earlier L1 cases that share the S06 base, so such within-lineage
  retrievals must be reported separately. (b) Only discovery entries are
  eligible. Under the fallback, L2 comes after every L1 case, so the L1 holdout
  would see an empty library. Margins and policies are never tuned on holdout
  outcomes under either option. [decide; the draft leans to (a) with separate
  reporting]
- **R11 Unit construction.** Authorize construction, not execution, of a
  `Unit` for each assigned case: task input, frozen rubric, deterministic oracle
  bytes and unit hash. These are then added to the freeze record before any
  outcome. [accept]
- **R12 Scope reaffirmed.** The cohort stays descriptive only (D3).
  `executionAuthorization`, native admission and promotion stay false. Numeric
  caps (D2) and improvement thresholds (D4) stay deferred. [accept]
- **R13 Guidance-observable double.** Record the follow-up below as a task
  description only. Implementing it needs its own decision. [accept as a
  follow-up]

## 5. Feasibility verdict

**Even with this roster frozen, the deterministic cohort would give A = B = C by
construction.** Three independent reasons:

1. **Nothing reads the guidance.** The anchor fixtures and the `harness_lab`
   simulated-containment runner run fixed scripts that never read guidance.
   A and B therefore produce byte-identical observations, and the guidance bytes
   cannot change any outcome. Writing arm-specific behavior into the fixtures
   would invent the effect being measured.
2. **Arm C does not exist** without a real proposer (R8). The only deterministic
   way to obtain C makes C = A.
3. **The fallback holdout is a single lineage (L1).** `harness_evaluation`
   therefore reports every comparison as `descriptive-only` before any outcome
   is seen: coordination (4 cases, 1 lineage) with reasons
   `repeated-within-lineage` and `below-D3-minimum`, continuity (1 case) with
   `below-D3-minimum` only.

The registration itself becomes feasible once R1–R11 are settled, arm C exists
and the units are constructed. A comparison of guidance variants does not: it still needs a
solver that reads guidance, which is the native branch (T004/T008).

### Proposed follow-up (description only, not implemented)

**SPEC-049 follow-up: deterministic guidance-reading solver double (engineering
positive control).** This is the smallest double that makes guidance observable.

- **What it is.** A fixed, offline solver double for the two C01 interrupted-work
  cases (L1-C01-a, L2-C01-a). It reads only the candidate guidance surface
  through the manifest's allowed component paths. It maps a closed directive
  grammar to one behavior switch: resume from the latest checkpoint instead of
  restarting.
- **Frozen in advance.** The grammar, the mapping and the "directive absent"
  default behavior are frozen and hashed before any run.
- **Negative controls.** Unknown or reworded directives cause no behavior change.
  An empty perturbation of A gives identical output.
- **How outcomes are labeled.** Outcomes go only under a separate
  `synthetic-control` label and are excluded from every D4 verdict and method
  claim. They show that guidance reaches the solver, that arms are
  distinguishable, and that the independent oracle, denominators and costs
  propagate end to end. They do not show that any guidance is better.
- **Acceptance.** A versus B differ exactly in the cells the frozen mapping
  predicts. Both negative controls give identical outcomes. No other file or
  fixture changes.
- **Where it belongs.** It should live in its own task with its own tests. It
  does not unblock arm C.

## Limits

No HAR unit, host, model, native session, paid route or human annotation was
used, and no cost or endpoint was produced. `register` and `evaluate` were not
called with this roster. The pre-PR reviews were run by Claude subagents and are
not independent Luna review.
