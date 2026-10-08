# SPEC-038 validation procedures

## Development status — 2026-10-08

Exact source rights and protocol are approved. The bounded harness is merged and
validated; static admission and technical review cover two frozen operations and
20 treatment slots. See [implementation readiness](implementation-readiness.md)
for the evidence and scope. Earlier proposal descriptions retain their design-time
context. Owner stable-candidate/manifest review, capture and whole-M4 acceptance
remain pending.

These named procedures are evidence obligations; their execution status is recorded below. No source-project execution is authorized by this file.

## Derived evidence status — draft, 2026-10-08

T001 / SC-001 is supported for bounded implementation and evaluation preparation by `evidence/sc-001.json`, which references the exact nine-item decision receipt and frozen candidate hashes. T001 / SC-002 is supported by `evidence/sc-002.json`: the exact two-operation frame passed static replay/runtime admission, both AB and BA yield the same expected final-tree OID, all 20 planned slots and 40 future paths are retained, and all 18 candidate input hashes are recorded. This is static admission only.

The local quick and PR profiles completed on candidate `915e90fcf2f84ea7d9fa46da82aa28a5b3796cc6`, whose tree is identical to merged candidate `7d73c80f1b8c23a65b33bf584abac29a2e097417` (tree OID `8a48146a743cd867a8cc0cff0f112383ef838db6`). Each profile ran 762 tests (758 passed, 4 skipped); the profile receipts and binding limits are recorded in `evidence/candidate-validation-status.json`. The PR receipt documents operator launch and post-run HEAD/input-hash recheck but no immutable pre-run snapshot.

PR #390 merged at 7d73c80f. Hosted PR checks succeeded for selected validators; the special matrix was skipped and tracking run 37704302523 succeeded. Post-merge validation run 37705172263 also passed all selected jobs on real runners; its special integration matrix was explicitly skipped.

The new static preparation took 70.139261584 seconds wall time and 4.925153 seconds parent CPU time. The independent read-only manifest review found no actionable findings; it did not run Git, tests, preparation, grants, treatments or capture, and did not independently reproduce historic timing or source fingerprint. A separate full static C08 code/domain/security review also found no actionable findings but ran no tests or capture. Its final explicit bindings cover only the trial engine and fresh verifier; other current hashes are operator-observed inventory. No duplicate technical review is requested. Owner stable-candidate/manifest review remains pending.

Keep SC-003 through SC-006, SC-007, T004, T005, registered capture and whole-M4 acceptance pending. The source-rights candidate and protocol packet remain frozen; do not publish the private manifest, source content, patches, raw records, quotations or personal paths.

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
