# SPEC-075: Validation plan

Status: draft; no procedure has obtained evidence. Deterministic procedures run
locally and in CI as targeted test modules (`tests/test_lightning_export.py`,
planned).

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | owner review record | E1–E5 accepted or amended; OD-2 decided | review not bound to a frozen commit |
| procedure_002 | SC-002 | filter fixture tests | only consent `redacted` traces; exclusions counted (`consent-none`) | unconsented trace exported; drop not counted |
| procedure_003 | SC-003 | supervised writer tests | lines match contract; hashes match manifest; only `d4FirstAttempt` true or explicit `outcome` | unknown role accepted; failed record without `outcome` exported |
| procedure_004 | SC-004 | aggregation tests | 3 transition records, 1 trajectory record, limit declared | token-ID merge attempted without token IDs |
| procedure_005 | SC-005 | manifest schema test | valid manifest passes | missing `sha256` or `redactionVersion` passes |
| procedure_006 | SC-006 | double export, shuffled input, other working directory | byte-identical except `generatedAt` | timestamp or host path in dataset bytes |
| procedure_007 | SC-007 | balance tests | `rollout` kind: 2+2 kept, stable, dropped counts reported; `supervised` not balanced | unseeded choice differs across runs |
| procedure_008 | SC-008 | terms gate tests | refuse without record; proceed with permitting record, hash referenced | host export without record succeeds |
| procedure_009 | SC-009 | CLI tests | fixed refusal codes; no value echo; `export-disabled` unless `export.enabled` | symlinked or non-empty output accepted |
| procedure_010 | SC-010 | canary scan tests | abort, no output on hit; `clean` otherwise | partial file left after abort |
| procedure_011 | SC-011 | socket/subprocess patched tests; MCP tool list | offline success; no MCP tool exposes export | socket opened |
| procedure_013 | SC-013 | retention tests with injected clock; purge listing | record past retention refused `retention-expired`; manifest records retention; purge lists citing manifests | expired record exported; purge silent about citing manifest |
| procedure_012 | SC-012 | `speckit-converge`, link check | artifacts agree | unbacked claim in documentation |
