# SPEC-074: Validation plan

Status (draft): procedure_001 (T002), procedure_002 (T003), procedure_003 (T004) and procedure_004 (T005) have obtained
evidence (`scripts/spec074_capture_evidence.py`); the others have none. Procedures run with
`.venv-speckit/bin/python -m unittest` on targeted modules with temporary homes
and committed fixtures; canaries are synthetic.

| Procedure | Scenario | Test target | Expected | Negative controls |
|---|---|---|---|---|
| procedure_001 | SC-001 | `tests/test_spec074_consent_config.py`, `tests/test_lightning_config.py` | `lightning-config.schema.json` `traces` section and validator agree; consent changes only via `lightning init` matching preview digest | `raw` value accepted (must fail); stale digest; `plugin setup` changing consent (must fail) |
| procedure_002 | SC-002 | `tests/test_spec074_consent_gate.py`, `tests/test_lightning_store.py`, `tests/test_lightning_cli.py` | store refuses content fields with `store-consent`; adapter/CLI report `content-consent-required`; outputs content-free | invalid config treated as `redacted` (must fail) |
| procedure_003 | SC-003 | `tests/test_lightning_redact.py` | every class replaced by its placeholder; post-scan clean | disable one pattern → test fails |
| procedure_004 | SC-004 | `tests/test_spec074_canary_corpus.py` (corpus `tests/fixtures/spec074-canaries/corpus.json`, generator `scripts/spec074_canary_corpus.py`) | 100% canaries caught in all encodings; none in any output | drop base64 handling → failure reported |
| procedure_005 | SC-005 | retention and purge tests (injected clock) | records past retention removed; purge leaves no content bytes | retention 91 refused; sweep skipped → test fails |
| procedure_006 | SC-006 | `tests/test_lightning_adapter.py` (planned) | deterministic redacted triplets/messages per source with losses | unredacted text in output (must fail) |
| procedure_007 | SC-007 | System One isolation test | shadow directory bytes and mtimes unchanged | adapter write into shadow dir detected |
| procedure_008 | SC-008 | boundary tests | no socket, subprocess, non-stdlib import or MCP tool; telemetry content-free | patched socket call fails test |
