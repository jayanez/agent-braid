# Contract: agent-braid-s1-label-rubric/v0.1

SPEC-066 REQ-103 (S1.5b), task T103. The rubric is frozen before any fit and before any
corpus is read. The machine-readable form is
[label-rubric-v0.1.json](label-rubric-v0.1.json); this text and that file must agree,
and a test checks the mapping below against the file.

Pinned digest (SHA-256 of the canonical JSON: sorted keys, no insignificant whitespace,
ASCII escapes): `6f3d9fede30aa1b9908e77b3a55e7028e0cee1bc382c92ee12cc120c570edccf`.
The digest is a test constant. Any edit to the JSON fails CI until the constant is
re-pinned in a reviewed change. `research/s15b_label_rubric.py` `rubric_digest()` is the
`oracleContractDigest` input for the later SPEC-051 descriptor; this contract mints no
descriptor and admits no fitting. `executionAuthorization` is `false`.

## Observed outcomes are primary

Every label comes from an observed outcome. Nothing is inferred from transcript text.

| Outcome kind | Label | Source and oracle |
|---|---|---|
| `runtime-conflict` | `conflict` | `real-run`, observed run result (T102) |
| `merge-conflict` | `conflict` | `real-run` (T102) or `git-history-replay` (T106, `git merge-tree`) |
| `merge-clean` | `textually-clean` | `git-history-replay` (T106, `git merge-tree`) |
| `verify-pass` | `no-conflict-observed` | `real-run`, after a combined execution (T102) |
| `verify-fail` | `integration-failure` | `real-run` (T102) |

- `textually-clean` and `no-conflict-observed` are two labels and are never pooled by
  default. A clean three-way merge is textual cleanliness, not semantic independence.
- `verify-fail` is its own label and is not folded into `conflict`: a failed verify does
  not show that the pair conflicted.
- T102 and T106 emit outcome kinds; this rubric alone maps kinds to labels.

## DP-1 scoring vocabulary

The DP-1 answers are `likely-independent`, `likely-conflicting` and `undetermined`.

- `likely-conflicting` is right on `conflict` and wrong on `textually-clean` and
  `no-conflict-observed`.
- `likely-independent` is right on `textually-clean` and `no-conflict-observed`, reported
  per label, and wrong on `conflict`.
- `integration-failure` is outside the truth sets: an answer on it is `unscored`.
- `undetermined` is counted and never scored as right or wrong.

## Missing-label policy (frozen)

- Unlabelled pairs are never imputed and never silently dropped.
- They are counted by class, source and reason, and excluded from fitting and
  evaluation.
- Every reported metric states the unlabelled share and a worst-case bound that counts
  all unlabelled pairs as each label in turn.

## Adjudication sample and label noise

- Per source, the sample size is `min(40, ceil(0.2 * labelled))`, allocated across labels
  in proportion to their counts (largest remainder, ties by label order). Rare labels
  can receive no slot.
- Within each source and label stratum, the join keys with the lowest SHA-256 rank of
  `manifest digest`, source, label and join key are taken. The manifest digest is the T104
  sealed corpus manifest, so the draw is fixed before labels are seen and cannot be
  tuned afterwards, provided T104 seals the manifest once and the manifest does not
  depend on the labels. The selector needs no PRNG state: this keyed ranking replaces
  the "seeded PRNG" wording of the S1.5b plan with the same guarantee (a draw fixed by
  the manifest digest) and is stable across Python versions.
- A stratum with no slot is counted, not hidden; a source with no labelled pair yields
  no sample.
- The noise estimand is the owner-versus-observed disagreement rate with a Wilson 95
  percent interval. With the expected small N the interval is wide and is reported as
  such; with no adjudicated pair the rate is absent, not zero.
- This is a limitation of the one-person owned population. Owner adjudication replaces
  SPEC-029's two blind reviewers (REQ-103); the sample measures label noise and
  establishes nothing else.

## Adjudication packet

Structural only: `joinKey`, `label`, `outcomeKind`, `source`, `structuralPair` (the v0.2
structural pair object). A structural-only packet may not be adjudicable by itself;
plan question Q3 decides whether a local pointer table is consented. Until then, T105
is limited to structural consistency audits.

## Privacy

The rubric, the selector and the estimator hold closed vocabularies, counts and opaque
join keys only: no path, commit, ref, author, prompt or transcript text.

## Carries forward

SPEC-029 T002 (#286). Consumed by T104 (corpus build and seal) and T105 (owner
adjudication).
