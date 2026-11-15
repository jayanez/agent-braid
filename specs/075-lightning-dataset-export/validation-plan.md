# SPEC-075: Validation plan

Status: draft; procedure_001 has obtained evidence (T001 owner review record,
2026-11-14), procedure_005 (T002 schema, `tests/test_spec075_manifest_schema.py`,
and T006 builder, `tests/test_spec075_manifest.py`), procedure_002 (T003,
`tests/test_spec075_export_filter.py`; the dataset's redaction version is set by
T006), procedure_003 (T004, `tests/test_spec075_supervised.py`; its manifest-hash
half in `tests/test_spec075_manifest.py`), procedure_004 (T005,
`tests/test_spec075_rollout.py`), procedure_006 (T006,
`tests/test_spec075_manifest.py`) and procedure_007 (T007,
`tests/test_spec075_balance.py`) and procedure_008 (T008,
`tests/test_spec075_terms.py`, synthetic temporary records only); no other
procedure has. Evidence is
captured with `python -m scripts.spec075_capture_evidence`. Deterministic procedures run
locally and in CI as targeted test modules (`tests/test_spec075_*.py`, one
module per task).

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record ([reviews/owner-t001-20261114.md](reviews/owner-t001-20261114.md)) | E1–E5 accepted or amended; OD-2 decided. Obtained: E1–E5 accepted, OD-2 equal cap 1:1, OD-1 deferred | review not bound to a frozen commit (binding happens at the closing freeze on `develop`) |
| procedure_002 | SC-002 | filter fixture tests (`tests.test_spec075_export_filter`, T003) | only consent `redacted` traces; exclusions counted (`consent-none`) | unconsented trace exported; drop not counted |
| procedure_003 | SC-003 | supervised writer tests (`tests.test_spec075_supervised`, T004; the comparison with a written manifest lands with T006) | lines match contract; hashes match manifest; only `d4FirstAttempt` true or explicit `outcome` | unknown role accepted; failed record without `outcome` exported |
| procedure_004 | SC-004 | aggregation tests (`tests.test_spec075_rollout`, T005) | 3 transition records, 1 trajectory record, limit declared | token-ID merge attempted without token IDs |
| procedure_005 | SC-005 | manifest schema test (`tests.test_spec075_manifest_schema`, T002) and builder output against the schema and `check_manifest` (`tests.test_spec075_manifest`, T006) | valid manifest passes | missing `sha256` or `redactionVersion` passes |
| procedure_006 | SC-006 | double export, shuffled input, other working directory (`tests.test_spec075_manifest`, T006) | byte-identical except `generatedAt` | timestamp or host path in dataset bytes |
| procedure_007 | SC-007 | balance tests (`tests.test_spec075_balance`, T007) | `rollout` kind: 2+2 kept, stable, dropped counts reported; `supervised` not balanced | unseeded choice differs across runs |
| procedure_008 | SC-008 | terms gate tests (`tests.test_spec075_terms`, T008; synthetic temporary records only) | refuse without record; proceed with permitting record, hash referenced | host export without record succeeds |
| procedure_009 | SC-009 | CLI tests | fixed refusal codes; no value echo; `export-disabled` unless `export.enabled` | symlinked or non-empty output accepted |
| procedure_010 | SC-010 | canary scan tests | abort, no output on hit; `clean` otherwise | partial file left after abort |
| procedure_011 | SC-011 | socket/subprocess patched tests; MCP tool list | offline success; no MCP tool exposes export | socket opened |
| procedure_013 | SC-013 | retention tests with injected clock; purge listing | record past retention refused `retention-expired`; manifest records retention; purge lists citing manifests | expired record exported; purge silent about citing manifest |
| procedure_012 | SC-012 | `speckit-converge`, link check | artifacts agree | unbacked claim in documentation |
