# SPEC-083: Validation plan

Status: draft; no procedure has obtained evidence. Each procedure records the exact
candidate commit, input and fixture hashes, command, exit, outcome and limits.
Passing checks do not prove statistical validity or utility and are not approval.

| Procedure | Scenario | Method | Pass | Negative control / failure |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record (T001); Codex review record with triage (T002) | OD-1 to OD-6 decided or deferred; every Codex finding triaged | review treated as approval of an unimplemented candidate; a finding dropped without reason |
| procedure_002 | SC-002 | promotion check over a capability-only report; hash of the SPEC-049 protocol before and after | refusal "no regression verdict"; protocol hash unchanged | a capability report accepted as promotion evidence |
| procedure_003 | SC-003 | validate records with a missing field, a late seal and a post-seal edit | each refused with the field named | a record sealed after the first trial start accepted |
| procedure_004 | SC-004 | pair fixtures with 4 trials, a profile mismatch, a repeated run id and a non-held-out task | each `invalid` with its cause | an unpaired or mismatched comparison yields a verdict |
| procedure_005 | SC-005 | compare computed Δ and bound with hand values; trial-level-versus-clustered control | match within 10⁻⁶; control not `noninferior` | trial-level errors used for the bound |
| procedure_006 | SC-006 | one fixture per verdict region | each region gets its verdict; only `noninferior` is promotion-eligible | `inconclusive` or `blocked` marked eligible |
| procedure_007 | SC-007 | pass@k and pass^k on known counts; k > n | values match the formulas; k > n refused | pass^k extrapolated beyond n |
| procedure_008 | SC-008 | infrastructure errors below and above threshold | none counted as failure; over-threshold `invalid` | an infrastructure error counted as 0 |
| procedure_009 | SC-009 | missing candidate outcomes | primary uses worst case; three bounds reported | missing outcomes dropped silently |
| procedure_010 | SC-010 | 19 tasks; 20 tasks with one task at 4 trials | `descriptive-only`, no verdict | a verdict below the minimum |
| procedure_011 | SC-011 | verdict requested mid-run; run stopped by a quota cap | first refused; second `inconclusive` with cause | an interim verdict computed |
| procedure_012 | SC-012 | superiority claim drafted from a `noninferior` verdict below D3 | claim refused; bounded claim text shown | superiority text emitted |
