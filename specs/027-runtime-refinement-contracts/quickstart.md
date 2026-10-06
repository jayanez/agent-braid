# Planned scenario verification

No expanded operation is authorized. Future test/harness paths below are planned.

## SC-001 — Separate grant scope

`tests/test_runtime_refinement.py` must reject current private-runtime grants as promotion/code/external authority. Validate unknown capability and missing observation/premise records without executing operations.

## SC-002 — Promotion dry-run

Build owned disposable Git fixtures with an expected ref, detached/attached worktrees, dirty indexes and stale bases. Future `scripts/check_runtime_refinement.py --capability promotion --input <fixture.json> --output <assessment.json>` reports a proposal only. Assert zero caller source changes. Fault-injection controls classify intended CAS outcomes and recovery uncertainty; actual promotion is a later feature.

## SC-003 — Code isolation feasibility

Read-only installed-backend inventory first. Do not run project code or install a backend. Review harmless synthetic escape/network/write/exhaustion probes and authorization before running them. Missing enforcement yields NO-GO, with each unsupported control reported.

## SC-004 — External-effect failure model

Use immutable in-memory events from the workload laboratory: retries, duplicate delivery, ambiguous timeout and failure-after-emission. Retain per-attempt results and raw visible events; uncertainty never becomes successful rollback or permission to resend.

## SC-005 — Decision and gates

Run the prospective assessment suite `python3 -m unittest tests.test_runtime_refinement` after implementation. Verify each packet includes capability scope, prerequisites, evidence, restrictions, fallback and founder decision pending. Run repository quick/PR; neither approves an ADR or expanded execution.
