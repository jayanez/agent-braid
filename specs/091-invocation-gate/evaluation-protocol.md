# SPEC-091 evaluation protocol (draft skeleton): pilots, 2×2 factorial and gate B

Status: draft, not approved and not frozen. Bracketed values are open owner decisions of spec.md. Each real
run below has its own freeze (labels, items, builds, seed, this protocol's section) on a `develop` commit
and its own owner yes line (REQ-045). No rollout precedes the simulation record (T007), whose hash each
protocol carries.

## Common to every run

- Host `claude-code`, model pinned, host CLI pinned with auto-update off, subscription route, EUR 0.
- Laboratory: the gate B profile with [OD-5] tools and pinned co-installed skills; `configDigest` recorded.
- Items: labelled `tool-necessary`, `tool-beneficial` or `tool-unnecessary` by [OD-2] before any rollout;
  near-miss items included; label record frozen by sha256 once Cohen's κ reaches [OD-21] on each label pair. Spent v4 prompts only as [OD-1] allows.
- Observation: whether `analyze-work` was called in the rollout (transcript tool names), aggregated to
  a per-item outcome by [OD-17]; the item, not the rollout, is the unit of every bound; for calls,
  `validFirstAttempt` from the unchanged SPEC-069 scorer as a secondary measure. Missing results are
  reported and counted as non-calls. A rollout with an instrument event (the skill or `analyze-work` missing
  from the session listing) is excluded from its item's outcome and re-run once in the same session; an
  item with fewer than 3 scored rollouts gives `held` (REQ-039). No LLM judge.
- Drift: SPEC-090 controls (versions per rollout, A/A anchors, seeded interleaved blocks, re-baseline).

## Development pilots (T008, T009, T018)

Each pilot runs only after its own pilot freeze and the owner's yes (REQ-035); pilot items never enter a
held-out set or its twin.

### Gate B noise pilot (T008)

Fresh development prompts that do not name the product, in the gate B laboratory, at the [OD-23] size;
the two [OD-27] arms (the shipped build and one named lever build) and an A/A pair of the shipped build.
Outputs: within-item correlation, paired per-item difference variance, discordance, A/A differences and
item-level recall, each with an interval, in the SPEC-090 input format, for gate B selection, the [OD-7]
sizes and the [OD-22] twin size and margin; gate A has its own pilot (SPEC-090 REQ-032). Descriptive.

### Development factorial (T009, H3)

2³ cells: product name (present, absent) × form (directive, question) × completeness sentence (present,
absent); [OD-6] prompts per cell, fresh except as [OD-1] allows. Per-cell invocation rates with exact
intervals; descriptive; not a gate. It estimates three of the seven v3/v4 differences on fresh prompts and
does not isolate the v3 to v4 change.

### Lever screening (T018, H1)

The `alwaysLoad` arm and the server-instruction arm, each against the shipped build, on the same labelled
development items at the [OD-24] size; item-level recall and false-positive rate; Holm over the two recall
superiority tests at [OD-19]; false positives enter as a noninferiority condition per lever at the [OD-9]
margin (REQ-037).

## 2×2 factorial (T011, T012; H1, H2)

Description (current, use-case-first) × hook (absent, present with the [OD-4] text). Within-item design:
every item runs in all four cells. [OD-7] recall-labelled plus [OD-8] `tool-unnecessary` items per cell at
3 repetitions (rollouts = items × 3 × 4); arms
interleaved in seeded randomized blocks. Contrasts: description main effect (use-case-first minus current,
averaged over hook levels), hook main effect (present minus absent, averaged over description levels),
interaction (the difference of differences). Candidate analyses, one picked by T007 before data: exact
paired McNemar per contrast on the [OD-17] item outcome; a logistic mixed model with an item random effect;
a sign-flip permutation test on item-level differences. The two recall main effects use Holm at [OD-19]; the interaction
is tested for equivalence within ±[OD-18] by TOST, otherwise reported descriptively. Report per cell:
recall on necessary and beneficial items and the false-positive rate on `tool-unnecessary` items
(including near-misses), each with the [OD-17] item-level bound. False positives are a noninferiority condition: the
exact one-sided upper bound on the paired false-positive difference, at the [OD-19] α, unadjusted, at or
below the [OD-9] margin. Criterion to
proceed to a held-out, paired on the same items in the decisive cell named in T011 (REQ-044), at
α = [OD-19]: [OD-9]. If the hook arm is unavailable, the preregistered
description-only paired comparison (hook absent) replaces the factorial for that criterion. Each rollout
records whether the hook context appeared, any host safety notice, and whether the skill and
`analyze-work` were listed; a missing listing is an instrument event. The hook arm is unavailable when its
context appears in none of the hook-arm rollouts of T012 (REQ-039).

## Gate B selection (T013, T019; only when [OD-20] requires it)

Incumbent: the decisive cell (REQ-044). Challengers are ranked by the paired item-level recall difference;
the incumbent is replaced only when a challenger's recall advantage exceeds δ_B of [OD-28], sized at the
target advantage Δ_B of [OD-28], with false-positive noninferiority at the [OD-9] margin and Holm at
[OD-19]. The winner and the incumbent are each scored once on the labelled gate B audit set of [OD-25] and
on the SPEC-090 gate A audit set; the paired difference is reported with an exact interval and does not
change the selection (REQ-041).

## Gate B held-out (T014, T015)

A fresh labelled pool at the [OD-25] sizes, partitioned by a recorded seed, stratified by label, into the
held-out set and a twin of recall-labelled items of [OD-22] size (SPEC-090 REQ-042); the builder refuses,
with zero rollouts, any item that names the product, and any pool that shares an item, fingerprint or
normalized 8-word window with a pilot, screening, 2×2, selection or audit item or with the SPEC-069, v2, v3
or v4 sets (REQ-014). Gate 0 tripwire: the twin's rollout-level call rate (1 repetition per item) is
compared with the rollout-level call rate of the [OD-20] arm on recall-labelled items in T012, minus the
[OD-22] margin, never with the gate A threshold (REQ-015). Frozen and scored once.
The arm is [OD-20]. Gate met when the recall lower bound is at least [OD-3] and the false-positive upper
bound is at most [OD-3], at α = SPEC-090 [OD-1]; the gate is conjunctive, so a false `met` stays at or below
α (intersection–union). Verdicts and precedence as SPEC-090 REQ-038 (REQ-034).

## Stopping rules

- Each set is scored once.
- Quota stops, host or model changes and resumes follow SPEC-090 REQ-037 unchanged (REQ-036): completed
  rollouts are kept, a resume fills only missing slots in frozen order on the same bytes, host and model,
  and a blocked resume of a held-out set invalidates it and spends it.
- A canary hit invalidates the run.
- Null, negative and invalidated results are valid outcomes and are recorded.
