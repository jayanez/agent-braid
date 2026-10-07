# SPEC-038 validation procedures

## Development status — 2026-10-08

Exact source rights and protocol are approved for bounded implementation and
preparation. See [implementation readiness](implementation-readiness.md) for the
scoped decision and current gates. Earlier proposal descriptions below retain
their design-time context; stable review, capture and whole-M4 acceptance remain pending.

These named procedures are planned evidence obligations, not executed tests.
No source-project execution is authorized by this file.

- `procedure_sc001`: verify named rightsholder, exact rights scope/term,
  provenance and retention against exact frozen inputs; missing or ambiguous
  authority must remain blocked.
- `procedure_sc002`: check the entire frozen candidate frame against unchanged
  SPEC-020 caps, A/M text/mode/path rules, dependencies and common base; retain
  every exclusion and fail infeasible without substitutions.
- `procedure_sc003`: exercise only reviewed harness refusal and verifier
  controls after separate harness approval; verify stale/unsafe/forged inputs
  cannot execute or promote source refs.
- `procedure_sc004`: reconcile the 4 unscored warm-up pairs and 6 measured pairs
  (3 per AB/BA operation order), including exact deterministic pair and
  treatment order. Reconcile intended, attempted, valid, invalid, failed,
  refused, recovered and unexecuted identities; retain all slots and prohibit
  replacement/complete-case analysis.
- `procedure_sc005`: independently recompute serial/parallel SPEC-021 coordinator
  treatment total-wall from evidence/input production through replay, preparation,
  grant, execution, consumer verification, report serialization and cleanup.
  Reconcile disjoint phases and residual, verify no double-counting, confirm the
  45-minute dispatch/360-second observation budgets, and inspect the separate
  fresh-process verification receipt. Disclose source, rights, operator, setup,
  and observer costs separately.
- `procedure_sc006`: verify outcome packet includes negative/inconclusive/
  infeasible findings, unsupported scope, all controls and independent tree
  verification; separate protocol adherence from outcome.
- `procedure_sc007`: check that both exact review records predate the action
  each governs and that absent gate leaves capture blocked.
- `procedure_sc008`: audit final packet against all six SPEC-021 closure rows,
  preserve historical G4 NO-GO, and require a separate whole-M4 founder record.

## C08 engineering controls

`tests/test_m4_real_workload_preparation.py` covers exact manifest bytes and
schedule, immutable source inspection, hostile ambient Git configuration and
private destination containment. `tests/test_m4_real_workload_trials.py` covers
authority before dispatch, accounting, deadlines, denominator reconciliation,
retained outcomes, fresh-process inspection and conditional final cleanup.
These controls use owned synthetic repositories. Their execution receipts belong
to the implementation candidate; passing them does not supply registered
actual-workload evidence or satisfy the separate capture approval.

Source-project code and test commands remain prohibited by this protocol.
