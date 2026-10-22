# Review repair after commit f0379606

An adversarial review of commit `f03796066d14d152dc1df3ba417546650b7405e4` found two
required software defects. This record covers only those repairs. The historical
[packet](evidence/rf01-rf02/packet.json) stays byte-exact and describes that commit,
not this tree.

## R1: a correction could prefer a later success

`FrozenRegistration` admitted several oracle attestations for one attempt, keyed by
artifact digest. A `correction` could then bind the attempt to a passing run after a
mature failed outcome, and the derived eligible and population outputs kept only the
success. That violates "never overwrite or remove a failed/immature outcome to prefer
a later success". The registration now admits at most one oracle attestation per
attempt (`conflicting-attestation`). A correction keeps the original oracle, so the
exit binding refuses a relabelled success (`verification-disposition`).

## R2: the late-maturity censoring invariant was not pinned by tests

The censoring guards were correct, but three mutants survived the suite. New tests:

- right-censored without a terminal, then a late-maturity amendment inside the
  horizon, refuses with `original-horizon-censored`;
- an unterminated outcome observed up to the horizon end must be right-censored;
- a terminal exactly at `originNs + horizonNs` is mature.

## Other changes

- Removed the per-outcome `record-time-regression` check; the global chain check
  already enforces it.
- `OperatorRegistry` refuses a bare string or bytes, or non-string members, for its
  receipt, root and revocation sets (`registry-type`) instead of splitting a string
  into characters.
- Removed unused imports.

## Checks

- Focused: 46 tests pass (42 before, plus four new contract tests and an extended
  registry test).
- Each targeted mutant fails its dedicated test: `terminalNs > end` changed to `>=`,
  the prior right-censored lock removed, the `observedUntilNs >= end` branch removed,
  and oracle uniqueness reverted to `(attempt, artifact)`.
- Other surviving review mutants (pre-origin, recommendation, contract pin,
  censor-time, task partition, record-date, state limit) remain open test gaps.

## File hashes (sha256)

| File | sha256 |
|---|---|
| `agent_braid/owned_work_authority.py` | `0fcaa2ef75ff7f3e5dbe0a59a3cf92f7963c34d124d338319abfd94cc84a2e64` |
| `agent_braid/owned_work_contracts.py` | `6df4dd3a64228aa88d081a5fbe2ee9cc7c32a41b347238cd79434200700d2f09` |
| `tests/test_owned_work_authority.py` | `af1760fd8e21bff91a6606ab40b48ad373273a35ce9befff4bd2d7dce19c9df5` |
| `tests/test_owned_work_contracts.py` | `7dc12c71f8c9fb551eddc1e6fe447f34bd98d24d46bed98c12d3ce73efbc9317` |
| `contracts/owned-work-evaluation-v1.md` | `bc39d331b77ec209b2cc924758be7e98eb21955a60befc35b8c9f8c077c5ef07` |

No independent review of these repairs is claimed. Capture, source admission,
training, human review and activation remain pending.
