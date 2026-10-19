<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Local reconciliation validation on e474320e

Base: `e474320eb763c33846665a0870677977b47d7a06`. Scope: reconstructed
telemetry and documentary lot, active draft refresh, no admission or publication.

The previous complete quick/sensitive run executed 1,888 tests with two errors
and 11 skips. Both errors reported the same missing frozen-export reference in
SPEC-046. A direct portable-validation call reproduced that exact error before
the draft refresh. The original assurance is archived intact; validators,
publication manifests and historical approval/evidence records are unchanged.

## Verification

- Targeted original errors: both passed (2 tests, 261.349 s). Command:
  `python -m unittest tests.test_history_equivalence.HistoryEquivalenceTests.test_m2_anchor_addenda_and_assurance_records_pass tests.test_spec_kit.SpecKitTests.test_current_tree_and_constitution_baseline -v`.
  [Raw output](evidence/reconciliation-e474320e-targeted.log).
- Stable PR validation profile: passed (exit 0). Command:
  `python scripts/validate_change.py --base develop --profile pr`. Python 3.13.11
  from the existing isolated environment, with its bin directory on PATH, no
  ambient PYTHONPATH, and isolated global/system Git configuration. The full
  suite ran 1,888 tests in 1,685.129 s, with 11 explicit skips and zero errors.
  Repository, contracts, release records, portable publication integrity, offline
  structural controls, finite scientific controls, Spec Kit structure/render,
  Constitution replica and whitespace passed.
  [Raw output](evidence/reconciliation-e474320e-pr.log).
- Preservation checks: all 128 pre-fix baseline entries preserved (the original
  assurance at its archive path); see [hash inventory](reconciliation-integrity.json).
  T004 and all task files are unchanged from the reconciled lot. The seven-spec
  inventory remains 65 checked / 26 open, including open T017/T018/T010.
- Git: exact parent base e474320e, both original C/D commit objects absent, no
  unresolved conflicts, push disabled. Final staged whitespace/link/integrity
  readback precedes the single local commit.

After the successful profile, only raw-log/report packaging and README/reconciliation
status prose were updated. Product code, tests, validators and the current
assurance were unchanged. Full validation was not repeated for that packaging.

Log SHA-256 values:

- Targeted: `309fb6a4405db35d216631cb3817d7db9f6a10a931ef7e9cb0428379c01f7226`.
- PR: `de46e1ce742b6936c812485e36e95fcb3208f7ac668e1e429a240b86ce778f13`.

 These local checks
supply no independent review, native observation, provider execution, pilot GO,
architectural adoption or final acceptance. T017/T018/T010 remain open; T004
retains only its prior bounded closure and was not rerun.
