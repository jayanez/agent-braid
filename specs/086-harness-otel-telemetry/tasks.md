# SPEC-086: Tasks

Stable task IDs. Completion requires obtained evidence. `quick` means
`python3 scripts/validate_change.py --base develop --profile quick`. No task here
exports to a non-loopback endpoint, captures content or changes the SPEC-047 store.
Every result keeps `executionAuthorization: false`.

## Phase P0 — review

- [ ] T001 (REQ-001 / SC-001): Owner review of spec, plan (and ADR if any); decide or defer OD-1 to OD-8.
  Dependencies: none. Target files: none. Verification: procedure_001.
  Planned evidence: `evidence/t001-owner-review.md`; obtained: none.
- [ ] T002 (REQ-001 / SC-002): Run the Codex review of this spec on the merged candidate; record raw output and triage.
  Each finding is confirmed, fixed or rejected with a reason. Independent model
  review, not human review. Dependencies: this PR merged. Target files:
  `specs/086-harness-otel-telemetry/review/`. Verification: procedure_002.
  Planned evidence: `evidence/t002-codex-review.json`; obtained: none.
- [ ] T003 (REQ-011 / SC-012): Draft the ADR for the OTel output contract and the export path (Proposed).
  Covers the store location, the egress path and the AT-2026-004 move (OD-7).
  Dependencies: T001. Target files: `docs/adr/` (new ADR). Verification:
  procedure_012. Planned evidence: `evidence/t003-adr-draft.md`; obtained: none.

## Phase P1 — contract

- [ ] T004 (REQ-002 / SC-003): Pin one semantic-conventions-genai revision: commit, date, schema URL and license.
  Record the source pin and the refusal codes for unknown or missing pins.
  Dependencies: T001. Target files: `specs/086-harness-otel-telemetry/source-pins.json`.
  Verification: procedure_003. Planned evidence: `evidence/t004-pin.json`;
  obtained: none.
- [ ] T005 (REQ-003 / SC-004 REQ-004 / SC-005 REQ-007 / SC-008 REQ-008 / SC-009): Write the mapping contract `agent-braid-otel-genai/v0.1`.
  Span model, attribute allowlist, closed values (OD-3), outcome and `error.type`
  classes, conformance gaps, and the SPEC-047 mapping table. Dependencies: T004,
  SPEC-082 infrastructure-error classes. Target files:
  `specs/086-harness-otel-telemetry/contracts/otel-genai-mapping.md`. Verification:
  procedure_004. Planned evidence: `evidence/t005-contract-review.md`;
  obtained: none.

## Phase P2 — implementation (unreleased)

- [ ] T006 (REQ-003 / SC-004 REQ-004 / SC-005 REQ-008 / SC-009): Implement the pure converter and the allowlist serializer.
  No file, network or clock access inside the converter; ids derived from record
  hashes. Dependencies: T005. Target files: `agent_braid/harness_otel.py`.
  Verification: procedure_004. Planned evidence: `evidence/t006.json`;
  obtained: none.
- [ ] T007 (REQ-005 / SC-006): Implement the private span store, consent mode, retention and purge, and the `harness trace` commands.
  Off by default; `OTEL_*` ignored; skills cannot enable it. Dependencies: T006,
  OD-1. Target files: `agent_braid/harness_otel_store.py`,
  `agent_braid/harness_cli.py`. Verification: procedure_006. Planned evidence:
  `evidence/t007.json`; obtained: none.
- [ ] T008 (REQ-006 / SC-007): Implement the opt-in OTLP/HTTP JSON export with pending-batch retry and deduplication.
  Loopback only under OD-5; no redirects; bounded body. Dependencies: T007, OD-5.
  Target files: `agent_braid/harness_otel_export.py`. Verification: procedure_007.
  Planned evidence: `evidence/t008.json`; obtained: none.
- [ ] T009 (REQ-010 / SC-011): Extend `telemetry audit-logs` and the `telemetry-audit` skill with a read-only span section.
  Dependencies: T007. Target files: `agent_braid/telemetry_audit.py`,
  `integrations/agent-braid/plugin/telemetry-audit/SKILL.md`. Verification:
  procedure_011. Planned evidence: `evidence/t009.json`; obtained: none.
- [ ] T010 (REQ-002 / SC-003 REQ-003 / SC-004 REQ-004 / SC-005 REQ-005 / SC-006 REQ-006 / SC-007 REQ-007 / SC-008 REQ-008 / SC-009 REQ-010 / SC-011): Tests with one mutation control per guard.
  Guards: pin check, allowlist, no invented times, consent, `OTEL_*` refusal,
  loopback limit, store isolation. Dependencies: T006 to T009. Target files:
  `tests/test_harness_otel.py`, `tests/test_harness_otel_store.py`,
  `tests/test_harness_otel_export.py`, `tests/test_telemetry_audit.py`,
  `tests/test_harness_cli_telemetry.py`. Verification: procedure_003 to
  procedure_011, then `quick`. Planned evidence: `evidence/t010.json`;
  obtained: none.
- [ ] T011 (REQ-009 / SC-010): Inject write faults and measure overhead against the emission-off run.
  Dependencies: T007. Target files: `tests/test_harness_otel_store.py`.
  Verification: procedure_010. Planned evidence: `evidence/t011-noninterference.json`;
  obtained: none.

## Phase P3 — measurement and decision

- [ ] T012 (REQ-003 / SC-004 REQ-004 / SC-005 REQ-011 / SC-012): Run the H1 fixture check on committed SPEC-048/049 records.
  Report identity retention, outcome-class retention, redaction and conformance-gap
  rates. A miss is a negative result, not tuned away. Dependencies: T010. Target
  files: none. Verification: procedure_012. Planned evidence:
  `evidence/t012-h1-fixtures.json`; obtained: none.
- [ ] T013 (REQ-006 / SC-007): Record a loopback OTLP receipt with a standard-library listener (attribute names only, never values).
  Dependencies: T008. Target files: none. Verification: procedure_007. Planned
  evidence: `evidence/t013-loopback-receipt.json`; obtained: none.
- [ ] T014 (REQ-005 / SC-006 REQ-010 / SC-011): Document emission, store, purge, export and audit; state that exported spans cannot be recalled.
  Dependencies: T012. Target files: `docs/tooling/TELEMETRY.md`,
  `docs/tooling/HARNESSING.md`. Verification: procedure_006. Planned evidence:
  `evidence/t014-docs.md`; obtained: none.
- [ ] T015 (REQ-011 / SC-012): Record the adoption decision: ADR outcome, T012 result, owner decision and release (OD-8), or "not adopted".
  Update AT-2026-004 only after the decision. Dependencies: T003, T012. Target
  files: `research/adoption/2026-09-initial-triage.json`. Verification:
  procedure_012. Planned evidence: `evidence/t015-adoption.json`; obtained: none.
