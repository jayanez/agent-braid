# SPEC-074: Validation plan

Status (draft): every procedure has obtained evidence
(`scripts/spec074_capture_evidence.py`): procedure_001 (T002), procedure_002
(T003), procedure_003 (T004), procedure_004 (T005), procedure_005 (T006),
procedure_006 for T007 and T008 (rollout, Loom, host transcript and System One
sources), procedure_007 (T009) and procedure_008 (T010). Procedures run with
`.venv-speckit/bin/python -m unittest` on targeted modules with temporary homes
and committed fixtures; canaries are synthetic.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | `tests/test_spec074_consent_config.py`, `tests/test_lightning_config.py` | `lightning-config.schema.json` `traces` section and validator agree; consent changes only via `lightning init` matching preview digest | `raw` value accepted (must fail); stale digest; `plugin setup` changing consent (must fail) |
| procedure_002 | SC-002 | `tests/test_spec074_consent_gate.py`, `tests/test_lightning_store.py`, `tests/test_lightning_cli.py` | store refuses content fields with `store-consent`; adapter/CLI report `content-consent-required`; outputs content-free | invalid config treated as `redacted` (must fail) |
| procedure_003 | SC-003 | `tests/test_lightning_redact.py` | every class replaced by its placeholder; post-scan clean | disable one pattern → test fails |
| procedure_004 | SC-004 | `tests/test_spec074_canary_corpus.py` (corpus `tests/fixtures/spec074-canaries/corpus.json`, generator `scripts/spec074_canary_corpus.py`) | 100% canaries caught in all encodings; none in any output | drop base64 handling → failure reported |
| procedure_005 | SC-005 | `tests/test_spec074_retention_purge.py` (injected clock) | records past retention removed; purge leaves no content bytes | retention 91 refused; sweep skipped → test fails |
| procedure_006 | SC-006 | `tests/test_lightning_adapter.py` | deterministic redacted triplets/messages per source with losses; Loom strand and operation references (schema positions only) as salted, domain-separated `strand-<hmac16>` pseudonyms shared by triplets and messages, host-transcript attempt ids as `turn-<hmac16>`, rollout attempt ids as `attempt-<hmac16>`, System One episode ids as `episode-<hmac16>`, each kind in its own HMAC domain | unredacted text in output (must fail); raw id at any reference position, renamed non-reference field or colliding names, or a changed or shared HMAC domain (must fail) |
| procedure_007 | SC-007 | `tests/test_spec074_system_one_isolation.py` | shadow directory bytes and mtimes unchanged | adapter write into shadow dir detected |
| procedure_008 | SC-008 | `tests/test_spec074_boundaries.py`, `tests/test_lightning_cli.py` (`BoundaryTests`, `BL2BoundaryTests`) | no socket, subprocess, non-stdlib import or MCP tool; every CLI output `executionAuthorization: false`; no BL.4 telemetry event; run telemetry files content-free; no adapter output or error names a raw source id | patched socket call fails test; socket or process in the adapter gate fails the path; raw rollout attempt id, raw episode id, an interpolated refusal or a chained cause fails the leak test |
