# SPEC-070: Validation plan

Status (2026-11-08, draft): procedures 002–008 have local test runs on the
candidate; procedures 001 and 009 need the owner and the post-merge tracking
reconciliation. Deterministic procedures run in CI `validate`. The last column
names the scenario `test_name` used in `assurance.json`; SC-001 maps once, to
procedure_001, whose record also carries the procedure_009 tracking check.

| Procedure | Scenario | Test target | Expected | Negative controls | Assurance `test_name` |
|---|---|---|---|---|---|
| procedure_001 | SC-001 | owner review of ADRs 0039–0042, program and contract | decisions recorded; ADR status updated by the owner | any ADR accepted without a review record | `procedure_001` |
| procedure_002 | SC-002 | `tests/test_lightning_cli.py` `BoundaryTests.test_module_carries_upstream_notice`; inventory hashes against the pinned upstream commits | notices present; hashes match | a module without notice; a changed upstream file | `BoundaryTests.test_module_carries_upstream_notice` (`tests/test_lightning_cli.py`) |
| procedure_003 | SC-003 | `tests/test_lightning_schema.py` | round trip; exact keys; state machine | unknown key, missing key, invalid transition, NaN, duplicate key | `RecordTests.test_state_machine_follows_upstream_transitions` (`tests/test_lightning_schema.py`) |
| procedure_004 | SC-004 | `tests/test_lightning_config.py` | defaults valid; constants fixed; schema agrees with validator | `eurCap` 1, API route, automatic promotion, traversal path | `ConfigTests.test_published_schema_agrees_with_the_validator` (`tests/test_lightning_config.py`) |
| procedure_005 | SC-005 | `tests/test_lightning_cli.py` `WizardTests` | preview writes nothing; exact digest applies; stale preview refused | wrong digest; `--apply` without `--non-interactive` | `WizardTests.test_non_interactive_preview_then_apply_with_exact_digest` (`tests/test_lightning_cli.py`) |
| procedure_006 | SC-006 | `tests/test_lightning_store.py` | private modes; append/read; sweep; purge | content kind, symlink, tampered line, duplicate run | `StoreTests.test_unknown_kinds_mismatches_and_content_are_refused` (`tests/test_lightning_store.py`) |
| procedure_007 | SC-007 | `tests/test_lightning_cli.py` `SetupTests` | key absent or lab; digest unchanged when off; effects lines | unknown mode | `SetupTests.test_lightning_consent_is_optional_and_digest_compatible` (`tests/test_lightning_cli.py`) |
| procedure_008 | SC-008 | `tests/test_lightning_cli.py` `BoundaryTests` | stdlib-only imports; no socket/subprocess; no MCP mention | a forbidden import | `BoundaryTests.test_modules_import_only_stdlib_and_open_no_sockets_or_processes` (`tests/test_lightning_cli.py`) |
| procedure_009 | — (supplementary; its tracking result is recorded in the procedure_001 record for SC-001) | `scripts/sync_github_tracking.py source`, then post-merge `audit` | source check passes; audit lists BL milestones and issues | missing spec mapping | — |
