# SPEC-070: Validation plan

Status (2026-11-08, draft): procedures 002–008 have local test runs on the
candidate; procedures 001 and 009 need the owner and the post-merge tracking
reconciliation. Deterministic procedures run in CI `validate`.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review of ADRs 0039–0042, program and contract | decisions recorded; ADR status updated by the owner | any ADR accepted without a review record |
| procedure_002 | SC-002 | `tests/test_lightning_cli.py` `BoundaryTests.test_module_carries_upstream_notice`; inventory hashes against the pinned upstream commits | notices present; hashes match | a module without notice; a changed upstream file |
| procedure_003 | SC-003 | `tests/test_lightning_schema.py` | round trip; exact keys; state machine | unknown key, missing key, invalid transition, NaN, duplicate key |
| procedure_004 | SC-004 | `tests/test_lightning_config.py` | defaults valid; constants fixed; schema agrees with validator | `eurCap` 1, API route, automatic promotion, traversal path |
| procedure_005 | SC-005 | `tests/test_lightning_cli.py` `WizardTests` | preview writes nothing; exact digest applies; stale preview refused | wrong digest; `--apply` without `--non-interactive` |
| procedure_006 | SC-006 | `tests/test_lightning_store.py` | private modes; append/read; sweep; purge | content kind, symlink, tampered line, duplicate run |
| procedure_007 | SC-007 | `tests/test_lightning_cli.py` `SetupTests` | key absent or lab; digest unchanged when off; effects lines | unknown mode |
| procedure_008 | SC-008 | `tests/test_lightning_cli.py` `BoundaryTests` | stdlib-only imports; no socket/subprocess; no MCP mention | a forbidden import |
| procedure_009 | SC-001 | `scripts/sync_github_tracking.py source`, then post-merge `audit` | source check passes; audit lists BL milestones and issues | missing spec mapping |
