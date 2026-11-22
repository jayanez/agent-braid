# Implementation plan: SPEC-086 OTel GenAI harness telemetry

## Approach

- **Derive, do not instrument (OD-2).** A pure converter reads existing harness
  records and writes span files. Inputs: SPEC-048 journal records
  (`agent_braid/harness_journal.py`, `at` times, attempt start and end), observation
  records (`agent_braid/harness_observation.py`, tool events and loss counts),
  SPEC-049 evaluation and registry records (`agent_braid/harness_evaluation.py`,
  candidate hash, profile id). Harbor trials (SPEC-084) reach the converter only
  after ATIF ingestion into these records.
- **Output.** OTLP JSON (`resourceSpans`) with `schemaUrl` from the pin, resource
  `service.name = agent-braid` and `service.version`, and nothing else from the host.
  Trace and span ids are derived from record hashes, so a repeat conversion gives the
  same bytes and a re-export deduplicates.
- **Store (OD-1).** A private store beside the SPEC-047 store, not inside it: 0700
  directory, 0600 files, no links, no repository ancestor, size cap fixed in the
  contract, 30 UTC-day retention, explicit purge. Standard library only.
- **Export (OD-5).** A separate command drains local span files to an OTLP/HTTP JSON
  endpoint the operator names (loopback only in v0.1). No redirects, bounded body,
  pending batch kept on failure. `OTEL_*` variables are ignored.
- **SPEC-047 mapping.** A table in the mapping contract maps store operations and
  outcomes to span attributes and daily cells to metric semantics (`calls` to a
  counter, `duration` bins to explicit-bucket histogram bounds). The store and batch
  v4 do not change.
- **Audit.** `telemetry_audit.py` and the plugin `telemetry-audit` skill gain a
  read-only span section.

## Constitutional check

| Article | Obligation | How the plan meets it |
|---|---|---|
| 0 | No claim beyond evidence | H1 is a hypothesis; a negative fixture result closes the spec (REQ-011) |
| 5, 15 | Effects are explicit | Only the export command has a network effect; it is named, opt-in and loopback-only |
| 13, 14 | Evidence, not verdicts | Spans carry outcome classes and hashes for replay; no score or verdict (REQ-008) |
| 19 | Real, measurable problem | No standard trace of harness runs today; H1 measures retention and redaction |
| 20 | Analysis and execution separate | `executionAuthorization: false`; spans grant nothing |
| 23, 24 | Semantics before production | Mapping contract and ADR precede code (T003 to T005) |

No MUST conflict found. One deliberate difference from SPEC-047: spans hold per-event
times and hashes. They therefore live outside the SPEC-047 store and need their own
consent decision (OD-1, OD-7).

## Affected files for the later code phase (named, not edited)

- New: `agent_braid/harness_otel.py` (converter and allowlist serializer),
  `agent_braid/harness_otel_store.py` (private store, retention, purge),
  `agent_braid/harness_otel_export.py` (OTLP/HTTP JSON export).
- Changed: `agent_braid/harness_cli.py` (a `trace` subcommand group),
  `agent_braid/telemetry_audit.py`,
  `integrations/agent-braid/plugin/telemetry-audit/SKILL.md`.
- Unchanged by rule: `agent_braid/tooling_telemetry.py`,
  `agent_braid/tooling_telemetry_cli.py`,
  `specs/047-local-technical-telemetry/data-contract.md`, and the SPEC-065 frozen
  harness files.
- Tests: `tests/test_harness_otel.py`, `tests/test_harness_otel_store.py`,
  `tests/test_harness_otel_export.py`, `tests/test_telemetry_audit.py` (extended).
- Docs: `docs/tooling/TELEMETRY.md`, `docs/tooling/HARNESSING.md`, a new ADR (OD-7),
  and the AT-2026-004 entry in `research/adoption/2026-09-initial-triage.json`.
- Spec folder (later): `contracts/otel-genai-mapping.md`, `source-pins.json`.

## Phases

1. **P0 review.** T001 owner review, T002 Codex review, T003 ADR draft.
2. **P1 contract.** T004 pin, T005 mapping contract with the allowlist.
3. **P2 implementation.** T006 converter, T007 store and consent, T008 export,
   T009 audit, T010 tests with mutation controls, T011 noninterference.
4. **P3 measurement and decision.** T012 H1 fixture check, T013 loopback receipt,
   T014 docs, T015 adoption decision.

## Validation profile

- Drafting: `python3 -m scripts.validate_spec_kit`.
- Code phase: targeted tests, then `quick`
  (`python3 scripts/validate_change.py --base develop --profile quick`).
  Telemetry and plugin skill paths may escalate to the full suite.
- PR: the CI `validate` aggregate is the `pr`-profile evidence. A passing profile is
  not human review or approval.

## Rollback

- Documentation phase: revert the PR.
- Code phase: emission is off by default; removing the `trace` group and the store
  leaves SPEC-047 untouched. Purge deletes local span files. Exported spans in a
  backend are the operator's and cannot be recalled; the docs must say so.
- Convention change: keep the old pin readable, refuse new writes under it, and ship
  a new mapping version.
