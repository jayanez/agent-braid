# SPEC-074: Tasks

Stable task IDs. Completion requires obtained evidence; completion does not
imply owner acceptance. `quick` means
`.venv-speckit/bin/python -m scripts.validate_change --base develop --profile quick`.

## Phase P1 — consent

- [x] T001 (REQ-001 / SC-001): Owner review of spec, plan, contracts and
  privacy review; OD-1 to OD-3 decided 2026-11-13 (host transcripts opt-in;
  salted per-run email hash; no consent expiry). Dependencies: none. Verification:
  review record bound to a frozen commit.
- [ ] T002 (REQ-001 / SC-001): consent fields in the configuration validator,
  extension of the `traces` section of `lightning-config.schema.json` with
  corpus agreement, `lightning init` preview with digest. Dependencies: T001, SPEC-070 REQ-004. Verification:
  procedure_001.
- [ ] T003 (REQ-002 / SC-002): consent gate in store (`store-consent`) and
  adapter/CLI (`content-consent-required`); fail closed on invalid
  configuration. Dependencies: T002. Verification: procedure_002.

## Phase P2 — redaction

- [ ] T004 (REQ-003 / SC-003): `lightning_redact` with typed placeholders and
  post-scan; spec069 script imports the shared patterns. Dependencies: T001.
  Verification: procedure_003.
- [ ] T005 (REQ-004 / SC-004): committed canary corpus generator (plain,
  JSON-escaped, URL-encoded, split, base64) and test. Dependencies: T004.
  Verification: procedure_004.

## Phase P3 — retention

- [ ] T006 (REQ-005 / SC-005): sweep with injected clock, `lightning sweep`, and
  the BL.0 `lightning purge` extended to content with preview digest. Dependencies: T003.
  Verification: procedure_005.

## Phase P4 — adapter

- [ ] T007 (REQ-006 / SC-006): `lightning_adapter` triplets and messages from
  rollout records and Loom fixtures. Dependencies: T004. Verification:
  procedure_006.
- [ ] T008 (REQ-006 / SC-006): host transcript and System One readers through
  existing modules. Dependencies: T007. Verification: procedure_006.
- [ ] T009 (REQ-007 / SC-007): System One isolation test (read-only open, no
  writes under the shadow directory, no output path into System One).
  Dependencies: T008. Verification: procedure_007.

## Closing

- [ ] T010 (REQ-008 / SC-008): boundary tests (no socket, no subprocess,
  stdlib, no MCP tool, content-free telemetry). Dependencies: T007.
  Verification: procedure_008.
- [ ] T011 (REQ-001–REQ-008 / SC-001–SC-008): converge: `speckit-analyze`,
  privacy review updated with findings, tracking and docs synced, `quick`
  green, assurance obtained evidence filled. Dependencies: T001–T010.

## Verification procedure

Each task runs its procedure from [validation-plan.md](validation-plan.md),
then `quick`; evidence files go under `evidence/` with command, hashes and
outcome. Canary values are synthetic and never real credentials.
