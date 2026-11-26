# SPEC-086: OTel GenAI harness telemetry

**Milestone:** HAR.4 — Harness evaluation platform. Implements owner decision F4 of
the [harnessing benchmark](../../docs/strategy/HARNESSING_BENCHMARK.md) (2026-11-22).

**Status:** draft, documentation-only. Nothing is implemented, installed, exported or
published by this specification's first PR. Code waits for owner approval. The T001
owner review is recorded (2026-11-24, [record](evidence/t001-owner-review.md)); it
authorizes no code.

## Purpose and scope

Harness runs and evaluations leave hash-bound records (SPEC-048 journal and
observation, SPEC-049 evaluation and registry). The local telemetry store (SPEC-047)
keeps only closed daily aggregates and, by contract, no event rows, hashes or sub-day
times. No record maps to a standard trace format, and the harness candidate hash is
not a standard attribute. This specification derives OpenTelemetry GenAI spans from
those records, keeps them local, and makes export a separate opt-in. This is
engineering, not research. The conventions are status Development, so the mapping is
pinned and expected to change.

In scope: a mapping contract `agent-braid-otel-genai/v0.1` pinned to one convention
revision; `invoke_agent` and `execute_tool` spans with `gen_ai.agent.version` set to
the harness candidate hash; a private local span store; opt-in OTLP export; content
redacted by default; a mapping from the SPEC-047 vocabulary (including the #1405
harness CLI counters) that leaves that store unchanged; `telemetry-audit` coverage.

Exclusions (each is a MUST NOT, stated with its REQ ID below):

- Recording prompts, messages, system instructions, tool definitions, tool arguments
  or results, paths, user, host or repository names in any span (REQ-004).
- Writing span data, span ids or hashes into the SPEC-047 store, or changing its
  schema, batch format (v4), vocabulary or consent rules (REQ-007).
- Exporting at run time, enabling emission or export from `OTEL_*` environment
  variables (REQ-005, REQ-006), or uploading anything without an explicit operator
  command (REQ-006).
- Configuring host exporters (Claude Code, Codex) or ingesting host OTLP. SPEC-061
  owns viewer ingest (REQ-012).
- Turning a span, a backend dashboard or a score into a verdict, promotion or grant
  (REQ-008, REQ-015). Every span carries `agent_braid.execution_authorization = false`, and
  every command result keeps `executionAuthorization: false` (REQ-013).

## Requirements and acceptance scenarios

**REQ-001 Owner and independent review.** The spec, plan and mapping approach are
reviewed before any code.

- **SC-001:** Given this spec and plan, when the owner reviews them, then OD-1 to
  OD-8 are decided or deferred in a dated record and the spec is approved, amended
  or rejected.
- **SC-002:** Given the merged candidate, when the Codex review runs, then its raw
  output is recorded and each finding is triaged with a reason.

**REQ-002 Pinned conventions.** The mapping contract names one revision of the
semantic-conventions-genai repository (commit, date, schema URL, license). Every span
file carries the pin and the mapping version. A file with an unknown pin or version is
refused. A newer revision is adopted only by a reviewed change with a mapping diff.

- **SC-003:** Given span files with the pinned, an unknown and a missing pin, when
  they are read or exported, then only the pinned file is accepted and the others
  refuse with a fixed reason code.

**REQ-003 Span model.** One `invoke_agent` span per harness attempt or trial, with
`gen_ai.operation.name`, `gen_ai.agent.name` (closed value), `gen_ai.agent.id` (the
SPEC-049 profile id when registered) and `gen_ai.agent.version` = `sha256:<hex>` of
the candidate. One `execute_tool` child span per tool event that has recorded times,
with `gen_ai.tool.name` from an allowlist or `other`. An evaluation run is a parent
`invoke_workflow` span. Agent Braid fields use the `agent_braid.` namespace. Times
are never invented: untimed events are counted on the parent, and a required
attribute missing from the record is flagged as a conformance gap, never guessed.

- **SC-004:** Given committed SPEC-048/049 fixture records, when converted, then each
  attempt yields one `invoke_agent` span whose `gen_ai.agent.version` equals the
  record's candidate hash, each timed tool event one child span, untimed events a
  parent count, and conversion is byte-identical when repeated.

**REQ-004 Redaction by default.** The serializer is allowlist-based. Any attribute,
event or resource field not on the allowlist is dropped and counted. No opt-in content
attribute of the conventions is emitted in v0.1.

- **SC-005:** Given fixtures seeded with content, paths, user and host names and
  unknown attributes, when converted, then none appears in the output bytes, each
  drop is counted, and removing the allowlist check makes the test fail.

**REQ-005 Local first, with SPEC-047 consent.** Emission is off by default and needs
an explicit local mode chosen by the operator. Skills never enable it. Spans go to a
private store outside any repository (0700 directory, 0600 files, no links), bounded
in size, with 30 UTC-day retention and an explicit purge.

- **SC-006:** Given default settings, `OTEL_*` variables, a skill invocation and the
  explicit mode, when a harness command runs under each, then spans are written only
  in the explicit mode, only to the private store, with the stated permissions and
  bounds.

**REQ-006 Opt-in OTLP export.** Export is a separate command that reads local span
files and sends OTLP/HTTP JSON to an endpoint the operator names. It never runs during
a harness run. A failed export keeps the batch for retry; a re-export does not
duplicate spans.

- **SC-007:** Given a loopback test listener, when export runs with and without the
  explicit command, then spans arrive only with it, a refused or unreachable endpoint
  leaves the batch pending, and a retry delivers each span once.

**REQ-007 SPEC-047 compatibility.** The store, batch v4, vocabulary and consent stay
unchanged. The contract documents how SPEC-047 operations and outcomes (for example
`harness-compare`, `ok`/`refused`/`error`) map to span attributes, and how daily cells
map to OTel metric semantics. Spans and cells join only by UTC day and operation.

- **SC-008:** Given the SPEC-047 test suite and a v4 batch, when run with span
  emission on and off, then results and batch bytes are identical and the store
  contains no span id, hash or sub-day time.

**REQ-008 Outcomes and infrastructure errors.** A task failure is not a span error.
An infrastructure error (SPEC-082 classes) sets span status ERROR and a closed
`error.type`. A missing outcome is `unobserved`, never `ok`. Spans carry outcome
classes only, no score and no verdict.

- **SC-009:** Given records with correct, incorrect, ungraded, infrastructure-error
  and missing outcomes, when converted, then each maps to its fixed class and status,
  and no span has a score or verdict attribute.

**REQ-009 Noninterference.** A fault while writing spans never changes harness
records, output or exit codes. Overhead is measured and losses are counted.

- **SC-010:** Given injected write faults (full disk, unsafe store, oversize), when
  harness commands run, then their outputs and exit codes equal the emission-off run,
  and each loss is counted.

**REQ-010 Audit coverage.** `telemetry-audit` and `telemetry audit-logs` report the
span mode, span files per UTC day, dropped-attribute counts and export state, and list
what spans cannot show. They stay read-only.

- **SC-011:** Given a store with spans, drops and a pending export, when the audit
  runs, then it reports those counts, writes nothing and opens no socket.

**REQ-011 Conditional adoption.** The OpenTelemetry adoption track (AT-2026-004,
`watch`) moves only through a recorded owner decision with an ADR covering the output
contract and the export path. If the owner keeps `watch`, or the fixture check of H1
fails, the spec closes with a recorded "not adopted" outcome. That is a valid result.

- **SC-012:** Given the gate inputs, when the adoption decision is recorded, then it
  cites the ADR, the H1 fixture result and the owner decision, and a failed condition
  leaves export unreleased.

## Requirements: exclusions and export limits

**REQ-012 No host exporter or host ingest.** This specification MUST NOT configure
host exporters (Claude Code, Codex) or ingest host OTLP. SPEC-061 owns viewer ingest.

- **SC-013:** Given the harness trace commands and the converter, when a code search and the trace-command tests run, then no
  path writes a host exporter setting and no path ingests host OTLP.

**REQ-013 No execution authority.** Every span MUST carry
`agent_braid.execution_authorization = false`, and every command result MUST keep
`executionAuthorization: false`.

- **SC-014:** Given spans and command results from conversion, store, export and
  audit, when they are inspected, then the `agent_braid.execution_authorization`
  attribute of each span and the `executionAuthorization` field of each result is the
  boolean `false`.

**REQ-014 Loopback export only in v0.1.** Export MUST send only to a loopback
endpoint (127.0.0.1 or ::1), MUST NOT follow redirects and MUST bound the request
body (OD-5; plan, Approach).

- **SC-015:** Given a loopback listener, a non-loopback endpoint with no listener and
  a loopback listener that answers with a redirect, when export runs against each,
  then spans reach only the loopback listener without a redirect, the non-loopback
  endpoint is refused before any connection is opened, the redirect is not followed,
  and each refused batch stays pending.

**REQ-015 Spans do not promote or grant.** A command MUST NOT turn a span, a backend
dashboard or a score into a promotion or a grant.

- **SC-016:** Given span files with every outcome class and a pending export, when the
  trace, export and audit commands run, then none writes a promotion or grant record
  or changes one, and every result keeps `executionAuthorization: false`.

## Non-functional requirements

Operational and quality constraints, each with its source:

- Deterministic: repeat conversion is byte-identical (REQ-003).
- Ids derive from record hashes, so a re-export deduplicates (plan, Approach; T006).
- Offline derivation: no code on the harness hot path; the converter reads no file,
  network or clock (OD-2; plan, Approach; T006).
- Pinned: every span file carries the convention pin and the mapping version
  (REQ-002).
- Private and bounded store: 0700 directory, 0600 files, no links, bounded size, 30
  UTC-day retention and explicit purge (REQ-005).
- Retry without duplicates: a failed export keeps the batch and a re-export delivers
  each span once (REQ-006).
- Noninterference: a span-write fault never changes harness records, output or exit
  codes; overhead is measured and losses are counted (REQ-009). The overhead limit is
  an open question.
- Read-only audit: no write and no socket (REQ-010).

## Security and privacy

- No prompt, message, instruction, tool definition, argument, result, path, user,
  host or repository name in any span; allowlist serializer drops and counts the
  rest (REQ-004).
- Emission off by default; `OTEL_*` variables and skills never enable it; private
  store outside any repository with 0700 and 0600 permissions (REQ-005).
- Export only by explicit command, only to loopback in v0.1 (REQ-006, REQ-014).
- No span id, hash or sub-day time in the SPEC-047 store (REQ-007).
- No host exporter configuration and no host OTLP ingest (REQ-012).
- Spans grant nothing: `execution_authorization` is `false` (REQ-013, REQ-015).
- Future path (not normative, see [Non-goals](#non-goals)): content capture needs its
  own specification and consent.

## Terminology

- **Mapping contract:** `agent-braid-otel-genai/v0.1`, pinned to one convention
  revision (REQ-002).
- **Pin:** commit, date, schema URL and license of that revision; a span file with an
  unknown or missing pin is refused (REQ-002).
- **Span names:** `invoke_agent` (one per attempt or trial), `execute_tool` (one per
  timed tool event) and `invoke_workflow` (one per evaluation run) (REQ-003).
- **Agent identity:** `gen_ai.agent.name` is `agent-braid-harness`,
  `gen_ai.agent.id` is the SPEC-049 profile id and `gen_ai.agent.version` is
  `sha256:<hex>` of the candidate (REQ-003; OD-3).
- **Tool name:** a value from an allowlist, otherwise `other` (REQ-003).
- **Conformance gap:** a required attribute missing from the record; flagged, never
  guessed (REQ-003).
- **Outcome classes:** correct, incorrect, ungraded and infrastructure error, plus
  `unobserved` for a missing outcome; a task failure is not a span error and an
  infrastructure error sets status ERROR with a closed `error.type` (REQ-008). The
  closed values are fixed in the mapping contract (T005).
- **Span store:** the private local store of span files, separate from the SPEC-047
  store (REQ-005; OD-1).
- **Export state:** a batch is pending after a failed export until a retry delivers
  it (REQ-006).
- Shared terms follow the root [TERMINOLOGY.md](../../TERMINOLOGY.md).

## Owner decisions (open)

Open questions: see [Open questions](#open-questions). OD-1 to OD-7 were decided on
2026-11-24 in [the T001 record](evidence/t001-owner-review.md); the options below
are kept as the decision text.

- **OD-1 Span store.** (a) separate private store, like SPEC-047; (b) next to each
  run's evidence; (c) inside the SPEC-047 store (breaks its contract). Recommend (a).
- **OD-2 Emission path.** (a) derive spans offline from records with a command;
  (b) instrument the harness CLI live. Recommend (a): no hot-path code.
- **OD-3 Agent identity.** Recommend name `agent-braid-harness`, id = SPEC-049
  profile id, version = candidate hash. Alternative: host-qualified names.
- **OD-4 Content capture.** (a) never in v0.1; (b) a later opt-in under its own
  consent and spec. Recommend (a).
- **OD-5 Export transport.** (a) OTLP/HTTP JSON, standard library, loopback only;
  (b) any endpoint behind an explicit flag; (c) OTel SDK and gRPC. Recommend (a).
- **OD-6 Evaluation results.** (a) `agent_braid.*` outcome classes only; (b) also
  `gen_ai.evaluation.*` events. Recommend (a): a score reads as a verdict.
- **OD-7 ADR and adoption track.** Recommend a new ADR and moving AT-2026-004 to
  `adopted` with limits. Alternative: keep `watch` and ship local files only.
- **OD-8 Release.** Which alpha carries emission and which carries export.

## Non-goals

No collector, backend or dashboard; no new SPEC-047 metric; no backend compatibility claim.

Future paths, noted only and not designed here (owner, 2026-11-24): content capture
needs its own specification and consent and never includes `private-holdout` tasks
(SPEC-082); `gen_ai.evaluation.*` events need their own specification and would
carry a SPEC-083 verdict with its bounded claim text, never a bare score.

## Risks

Risks and assumptions: each entry below names the REQ or task it affects.

- Risk: The conventions change before v0.1 ships; the pin limits the blast radius
  (REQ-002, T004).
- Risk: Spans hold per-event times, model names and candidate hashes: more identifying
  than daily aggregates. Redaction and loopback export reduce this risk; they do not
  remove it (REQ-004, REQ-014).
- Risk: `OTEL_*` variables set for a host exporter could leak spans if honored
  (REQ-005).
- Risk: Backends may show span counts or durations as quality; spans are observation
  (REQ-008).
- Risk: Conformance gaps (no provider in offline fixture runs) may make backends drop
  spans (REQ-003, T012).
- Assumption: Harness records keep their current fields, including attempt start and
  end times and the candidate hash (REQ-003, T006).
- Assumption: The OTel GenAI conventions stay readable at the pinned revision
  (REQ-002, T004).
- Assumption: The SPEC-047 store, batch v4 and consent rules stay as merged (REQ-007).
- Assumption: Harbor trials (SPEC-084) reach spans only through ingested Agent Braid
  records (REQ-003).

## Hypothesis

H1: a metadata-only mapping keeps candidate identity, outcome class and
infrastructure-error separation for every fixture record with zero content fields.
This is a hypothesis; T012 may refute it. Clause zero: a negative or inconclusive
result is valid and closes the spec under REQ-011.

## Exit criteria

Verification is complete when the obtained evidence listed in
[the validation plan](validation-plan.md) exists for procedures 001 to 016, which map
to SC-001 to SC-016 and to the tasks in [tasks.md](tasks.md) that name them, and the
T015 adoption or "not adopted" record is written. Passing checks are not approval.

## Open questions

- OD-8 Release: which alpha carries emission and which carries export. Owner: the
  founder, who decided on 2026-11-24 to name them when the code and its tests are
  ready (T015).
- REQ-009 overhead: whether an overhead limit applies and its value; the requirement
  only says overhead is measured. Owner: the founder (T011).

## Dependencies

- SPEC-047 (consent, store, audit); SPEC-048 (journal, observation); SPEC-049
  (registry, evaluation, candidate hash); SPEC-023 (OTel screening); SPEC-061 (a
  possible consumer).
- [SPEC-082](../082-harness-task-qa-infra-controls/spec.md) infrastructure-error
  classes; [SPEC-083](../083-capability-regression-evals/spec.md) evaluation classes;
  [SPEC-084](../084-harbor-evaluation-substrate/spec.md) Harbor trials, which reach
  spans only through ingested records.
- Related: [ADR 0044](../../docs/adr/0044-harness-portability-tiers-skill-surface.md),
  [ADR 0045](../../docs/adr/0045-hybrid-harness-evaluation-substrate.md). No ADR yet
  for this spec; T003 drafts one (OD-7).

## References

- [CONSTITUTION.md](../../CONSTITUTION.md) clause zero, Articles 5, 13, 14, 15, 19,
  20, 23, 24; [GOVERNANCE.md](../../GOVERNANCE.md).
- [SPEC-047](../047-local-technical-telemetry/spec.md),
  [data contract](../047-local-technical-telemetry/data-contract.md),
  [TELEMETRY.md](../../docs/tooling/TELEMETRY.md).
- [Harnessing benchmark](../../docs/strategy/HARNESSING_BENCHMARK.md) §5 and F4;
  [radar 2026-11-22](../../research/radar/2026-11-22-harnessing.json) RAD-2026-048.
- [Adoption pathline](../../research/adoption/ADOPTION_PATHLINE.md);
  [AT-2026-004](../../research/adoption/2026-09-initial-triage.json).
- [OTel GenAI agent spans](https://github.com/open-telemetry/semantic-conventions-genai/blob/main/docs/gen-ai/gen-ai-agent-spans.md).
