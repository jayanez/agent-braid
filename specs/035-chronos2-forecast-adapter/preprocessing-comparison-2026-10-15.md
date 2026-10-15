# Pinned Chronos preprocessing comparison

Domain: synthetic software acceptance of T003/T004. This is source inspection
and existing-control evidence, not a new model run or real-workload evaluation.
Luna Latest (`gpt-6-luna`, configured review model) completed the direct comparison
on 2026-10-15. No mismatch was identified within the documented numeric input path.

The upstream commit is `0aba28e9360b6355d5a919596c90b16c25939f02` (release 2.3.2).
The exact files were fetched from official immutable-commit URLs, hashed and read
as text. They were not imported or executed. T003's receipt binds all three hashes;
the pipeline hash also equals the earlier retained wheel/reference comparison.

| Local behavior | Pinned upstream source | Result |
|---|---|---|
| `translate_inputs` retains target matrix row order and named past/future maps | [pipeline.py](https://github.com/amazon-science/chronos-forecasting/blob/0aba28e9360b6355d5a919596c90b16c25939f02/src/chronos/chronos2/pipeline.py#L494), lines 494–506; [preprocess.py](https://github.com/amazon-science/chronos-forecasting/blob/0aba28e9360b6355d5a919596c90b16c25939f02/src/chronos/chronos2/preprocess.py#L271), lines 271–284 | Converter sorts covariate names and preserves target rows; named-key correspondence aligns with local inputs. |
| Known-future keys require matching historical identity and exact horizon | preprocess.py, lines 481–499 and 531–553; [dataset.py](https://github.com/amazon-science/chronos-forecasting/blob/0aba28e9360b6355d5a919596c90b16c25939f02/src/chronos/chronos2/dataset.py#L98), lines 98–106 | Local checks enforce subset/history and horizon rather than inventing context. |
| Worker converts numeric null target/covariate entries to float32 NaN | preprocess.py, lines 312–317 and 420–475 | Numeric tensor path preserves NaNs; future target rows are NaN. No future target is supplied locally. |
| `validate_window` enforces regular event grid, cutoff, masks and availability; `compile_window` makes late target arrivals missing | pipeline.py, lines 822–883 describes regular timestamp requirements for dataframe path | Local causal checks apply before raw tensor conversion. Existing tests reject off-grid/late/backfill input; this is stricter local eligibility, not upstream leakage assurance. |
| Worker sends one input with `cross_learning=False`, batch size 1; partitions reject reused episode groups and unpurged overlaps | pipeline.py, lines 639–650; dataset.py, lines 253–263 | Upstream merges groups across inputs only when cross-learning is enabled. Local partition checks remain independent. |
| Local point field is median; quantile axes/finite/order and uncalibrated labels are checked | pipeline.py, lines 817–820 | Second upstream return is the training quantile 0.5 despite the variable name `mean`; it is not labelled as a mean locally. |

Production input hashes are recorded in T003/T004. The 27 fresh synthetic controls
and retained installed v3/v5 parity retain their own scope; repeated tests are
not independent workload episodes. No upstream dynamic differential or new model
inference was executed for this source comparison. The explicit T003 requirement
to check against pinned preprocessing source is satisfied by this direct review,
including converter internals, rather than only a file-identity comparison.

Permissioned workload capture, artifact/loading authority, original worker/full
cost tasks, scientific utility and promotion remain separate. Runtime advice has
no authority to create grants or change deterministic eligibility.
