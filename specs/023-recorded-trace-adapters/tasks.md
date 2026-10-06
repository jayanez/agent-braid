# Tasks

All tasks are unchecked implementation work. Dependencies are task prerequisites,
not authorization to run agents. Targets below are planned files unless they
already exist. Each acceptance contract maps to `quickstart.md`; add concrete
feature tests during implementation and capture actual evidence before checking
any task. External permissions and scientific/adoption decisions remain explicit.

- [ ] T001 (REQ-001/SC-001): Define the bounded generic import and provenance contracts
  - Dependencies: none; inspect the current AIM/report baseline and SPEC-011.
  - Targets: `agent_braid/trace_adapter.py`, new versioned import/provenance schema paths selected in the implementation PR, `docs/development/` migration note, applicable ADR proposal if required, and `tests/test_trace_adapter.py` fixtures.
  - Deliverable: fixed metadata allowlist and size/event/depth bounds, source/mapper version and digest rules, identity/dependency/version mapping table, one-attempt limit, explicit real-source admission and migration/versioning impact. Existing AIM/report schema bytes remain unchanged.
  - Verification/evidence: SC-001 contract; schema/fixture positive and malformed/missing/collision/cycle/stale-version cases, exact interface version and reviewed contract packet. Pin expected mapping independently of implementation.
- [ ] T002 (REQ-002/SC-002): Implement conservative metadata mapping with explicit loss
  - Dependencies: T001.
  - Targets: `agent_braid/trace_adapter.py`, `tests/test_trace_adapter.py`, synthetic trace fixtures and mapping-loss evidence under this feature.
  - Deliverable: pure mapping to AIM, source identity/digests preserved, explicit optional unknown/partial coverage, no timestamp-derived dependency, required gaps and multi-attempt instances rejected, unsupported non-sensitive metadata retained only under the allowlist.
  - Verification/evidence: SC-002 contract and future feature unittest suite; fixed direct-AIM controls show unknown cannot become independence. Save projection/loss tables, rejected multi-attempt controls, command/environment and raw outputs.
- [ ] T003 (REQ-003/SC-003): Add the read-only library and proposed analyze-trace CLI path
  - Dependencies: T002.
  - Targets: `agent_braid/cli.py`, `agent_braid/trace_adapter.py`, `tests/test_trace_adapter.py`, CLI help/documentation.
  - Deliverable: additive local-file command with fixed mapper and explicit provenance destination, no SDK/plugin/provider/runtime/grant dispatch, library returns artifacts and CLI alone writes the explicit local result.
  - Verification/evidence: SC-003 contract; forbidden executable/network/model/grant controls and spies record zero process/network/model calls. Preserve existing CLI behavior and non-authorizing report fields.
- [ ] T004 (REQ-004/SC-004): Enforce privacy, parser and destination admission controls
  - Dependencies: T003.
  - Targets: `agent_braid/trace_adapter.py`, CLI output handling, `tests/test_trace_adapter.py`, metadata-only security/readiness notes.
  - Deliverable: default synthetic-only admission, no raw prompt/argument/credential/person payload, duplicate-member and resource-bound rejection, symlink/output-collision refusal and sanitized diagnostics. Real-source rights/transformation admission remains separate.
  - Verification/evidence: SC-004 contract; synthetic sensitive sentinels never appear in diagnostics or saved outputs, rejected input leaves no partial success, parser/path/limit negative cases recorded. No claim of arbitrary secret detection.
- [ ] T005 (REQ-005/SC-005): Verify deterministic report parity and provenance binding
  - Dependencies: T004.
  - Targets: `tests/test_trace_adapter.py`, fixed generic/direct-AIM fixtures, this feature's validation evidence and mapping compatibility note.
  - Deliverable: same-input direct-AIM/importer comparison, source/projection/report digest chain and deterministic serialized outputs without changing analyzer rules or assurance classes.
  - Verification/evidence: SC-005 contract; `python3 -m unittest discover -s tests -p 'test_trace_adapter.py'` after implementation. Save twice-run byte comparisons, schema validation, report constraints and zero false-safe classifications for registered controls with denominator.
- [ ] T006 (REQ-006/SC-006): Run separate OpenAI approval and MCP async-state lifecycle spikes
  - Dependencies: T005; discover/pin primary provider/protocol source versions before coding each spike.
  - Targets: offline spike scripts/fixtures under this feature, source-pin and result packets, current follow-up records linking `AT-2026-001-openai-approval-evidence` and `AT-2026-002-mcp-async-state`.
  - Deliverable: synthetic approval/rejection/pause/resume and deferred-task/status/state-handle cases, fixed mapping/unknown/false-safe metrics and positive/negative/inconclusive outcomes. Preserve timelines and reject unsupported flattening; do not reimplement existing MCP stdio serving.
  - Verification/evidence: SC-006 contract; no SDK install or provider/model/network calls. Save source versions, corpus and expected outcomes fixed before mapping, all retained/lost fields and unsupported cases. Negative/inconclusive outcomes complete the spike but cannot promote adoption.
- [ ] T007 (REQ-007/SC-007): Screen A2A, NeMo Agent Toolkit and OpenTelemetry compatibility
  - Dependencies: T001; may be prepared independently of T002–T006 once sources are selected.
  - Targets: this feature's ecosystem screening records and current follow-up source/adoption references.
  - Deliverable: each candidate's discovered source/version, conformance availability, license/dependency/privacy assessment, AIM loss and baseline with `watch`/`spike`/`rejected`/`research-only` next decision; missing facts stay pending/inconclusive.
  - Verification/evidence: SC-007 contract and record review; no dependency installation, collector, remote trace or compatibility claim. Preserve frozen SPEC-011/radar bytes and record retrieval provenance.
- [ ] T008 (REQ-008/SC-008): Capture full evidence and separate readiness/adoption decisions
  - Dependencies: T005, T006, T007.
  - Targets: this feature's evidence/decision packet, `assurance.json`, `readiness.md` and current follow-up adoption records.
  - Deliverable: requirements-to-test/evidence matrix, generic software readiness and distinct provider/real-source/publication statuses, contract/security review and unresolved scientific limits.
  - Verification/evidence: SC-008 contract; `python3 scripts/validate_spec_kit.py`, `python3 scripts/validate_change.py --base develop --profile quick`, then `--profile pr` once on the stable candidate. Bind actual commit/environment/commands/results; freeze a clean candidate for review. Human acceptance, provider adoption, external reproduction and publication remain separate gates.
