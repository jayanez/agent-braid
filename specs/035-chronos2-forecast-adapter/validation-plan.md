# SPEC-035: Prospective validation procedures

These are named future procedures, not executed tests. A draft assurance record may reference this existing plan. Implementation must supply actual executable tests or a candidate-bound research report before validating any scenario. Source/model/launch/promotion decisions require their actual human record.

## procedure_001: REQ-001 / SC-001

Given an installation without optional ML packages. Exercise the default CLI or forecast discovery runs. Expect core behavior is unchanged, no model import or download occurs and an explicit unsupported request refuses precisely.
Include the refusal and adversarial branches named in the requirement, record every attempted case, and bind raw input/output/candidate/environment hashes. Synthetic conformance remains separate from permissioned workload utility.
Planned evidence: `evidence/sc-001.json`; obtained evidence: none.

## procedure_002: REQ-002 / SC-002

Given an unapproved manifest, mutable model reference or changed checkpoint file. Exercise provisioning or loading is requested. Expect it refuses before network/download/load; only approved hashes in an isolated local installation are accepted.
Include the refusal and adversarial branches named in the requirement, record every attempted case, and bind raw input/output/candidate/environment hashes. Synthetic conformance remains separate from permissioned workload utility.
Planned evidence: `evidence/sc-002.json`; obtained evidence: none.

## procedure_003: REQ-003 / SC-003

Given multiple targets, a past-only channel and an unknown future value. Exercise inputs are translated for Chronos2Pipeline. Expect target order and masks are preserved, future outcomes never enter covariates and unsupported representations refuse without silent filling.
Include the refusal and adversarial branches named in the requirement, record every attempted case, and bind raw input/output/candidate/environment hashes. Synthetic conformance remains separate from permissioned workload utility.
Planned evidence: `evidence/sc-003.json`; obtained evidence: none.

## procedure_004: REQ-004 / SC-004

Given reordered channels, crossed/nonfinite quantiles or the upstream mean-named median return. Exercise a forecast envelope is emitted. Expect valid p50 is labeled median with units/horizon; malformed output refuses and nominal interval levels are not reported as calibrated coverage.
Include the refusal and adversarial branches named in the requirement, record every attempted case, and bind raw input/output/candidate/environment hashes. Synthetic conformance remains separate from permissioned workload utility.
Planned evidence: `evidence/sc-004.json`; obtained evidence: none.

## procedure_005: REQ-005 / SC-005

Given a worker that hangs, crashes, exceeds budget or lacks memory enforcement. Exercise the request deadline or shutdown occurs. Expect the owned process is stopped under its reviewed contract, resources are accounted for and advice refuses without executing a workload.
Include the refusal and adversarial branches named in the requirement, record every attempted case, and bind raw input/output/candidate/environment hashes. Synthetic conformance remains separate from permissioned workload utility.
Planned evidence: `evidence/sc-005.json`; obtained evidence: none.

## procedure_006: REQ-006 / SC-006

Given two similar requests with different masks or a new resource receipt. Exercise a forecast cache or lifecycle reuse is attempted. Expect the cache misses or refuses appropriately and cached/uncached outputs meet declared numerical tolerance without hidden future inputs.
Include the refusal and adversarial branches named in the requirement, record every attempted case, and bind raw input/output/candidate/environment hashes. Synthetic conformance remains separate from permissioned workload utility.
Planned evidence: `evidence/sc-006.json`; obtained evidence: none.

## procedure_007: REQ-007 / SC-007

Given a stub-passing adapter and an approved real CPU checkpoint run. Exercise the conformance packet is produced. Expect stub and real results are distinguished, unsupported devices are unclaimed and loading/inference/fallback costs remain in later policy accounting.
Include the refusal and adversarial branches named in the requirement, record every attempted case, and bind raw input/output/candidate/environment hashes. Synthetic conformance remains separate from permissioned workload utility.
Planned evidence: `evidence/sc-007.json`; obtained evidence: none.
