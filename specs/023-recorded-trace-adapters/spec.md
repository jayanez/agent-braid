# Recorded-trace adapters

## Purpose and scope

SPEC-023 makes the read-only analyzer usable on bounded, recorded operation
metadata from other agent environments. The first implementable increment is a
provider-neutral, metadata-only JSON importer into existing AIM
`0.2.0-draft` and analysis-report `0.1.0-alpha`, with a separate import-provenance
artifact. It is an engineering feature followed by two bounded lifecycle spikes.
This document prepares implementation; it contains no implemented importer or
provider adoption decision.

The existing Git adapter (SPEC-005) and operator-configured stdio MCP runtime
(SPEC-021, `agent_braid/mcp_runtime.py`) remain distinct. Serving local runtime
tools over MCP does not implement recorded MCP asynchronous task/state import.
No SDK, collector, provider client, remote retrieval, model invocation, execution,
credential handling or live trace capture is in this increment. A2A, NeMo Agent
Toolkit and OpenTelemetry receive compatibility screening only.

## Authorities

Clause zero and Articles 1, 5, 7, 13–16, 19–21, 23 and 25 apply. See
`GOVERNANCE.md`, ADRs 0005, 0007, 0008, 0020,
`docs/architecture/AGENT_INTERACTION_METADATA.md`,
`docs/architecture/ASSURANCE_LEVELS.md`, the versioned AIM/report schemas,
`docs/theory/OPERATIONAL_SEMANTICS.md`, `SECURITY.md`, and SPEC-011's adoption
pathline. A lifecycle annotation is evidence about a source's recorded status;
it is neither an AIM execution grant nor a scientific assurance upgrade.

## Clarifications and bounded decisions

- Baseline: manually prepared AIM plus the existing deterministic analyzer.
  Compare generic mapping and each lifecycle spike against that baseline on the
  same finite synthetic cases; do not compare different workloads.
- Generic MVP input: one local UTF-8 JSON file, at most 1 MiB, 64 operations,
  512 events, nesting depth 16, and metadata strings of at most 256 characters.
  The implementation must reject limit breaches before pairwise analysis.
- Default admission: explicitly synthetic, allowlisted metadata only. Real or
  sanitized real traces require a separately reviewed admission record naming
  rights, allowed fields, transformations, retention and privacy boundaries;
  until that record exists they are rejected.
- A local source document and its selected schema/protocol version are pinned
  before a provider spike. No current SDK version is asserted by this spec.
- The analyzer accepts one attempt per operation instance. The generic MVP
  requires that shape. Multiple attempts, pause/resume and deferred states are
  retained in spike provenance; any projection requiring their collapse is
  explicitly unsupported rather than silently flattening them.
- `analyze-trace` is a proposed additive CLI command for later implementation,
  taking a local input, an explicit mapper identifier and explicit provenance
  output. It exposes no execution switch and does not change `analyze`.

## Requirements and acceptance scenarios

### REQ-001 — Versioned import admission and preservation

**SC-001:** Given a synthetic generic trace within the bounds, with explicit
source/mapper versions and source hashes, when it is imported, then every
operation definition, instance, attempt, dependency, read version and effect
channel has an auditable AIM mapping and the source hash and mapping decisions
are bound in provenance. Missing identities, definition/input digests, duplicate
IDs, dangling/cyclic dependencies, unsupported mapper versions or malformed
version values are rejected with a bounded diagnostic. Local artifact digests
must be labelled as local transformations and never represented as missing
source-content digests.

### REQ-002 — Incomplete knowledge cannot become independence

**SC-002:** Given absent version/footprint coverage, a lifecycle event with no
known effect, or unsupported semantics, when mapping is attempted, then the
output records explicit information loss and `unknown`/partial coverage.
Timestamps alone cannot establish dependency edges; approvals cannot establish
completed effects. Required identity gaps reject the input. Optional unknown
metadata remains in a bounded allowlisted provenance representation, and
unknown fields never become empty footprints or asserted complete coverage.
Multiple attempts per instance must be rejected by the generic MVP.

### REQ-003 — Offline import has no execution surface

**SC-003:** Given a file containing a network address, shell command, executable
plugin hook, model request, grant or execution instruction, when it reaches the
import boundary, then no network/client/process dispatch occurs. Executable
fields and remote input locations are rejected; permissible opaque metadata
cannot be interpreted as instructions. Analysis and provenance always retain
`executionAuthorization: false` where that field is defined.

### REQ-004 — Privacy and parser admission fail closed

**SC-004:** Given a non-admitted real trace, raw prompts, argument bodies,
credentials, personal content, duplicate JSON members, oversized/deep input or
unsafe output destination, when import is requested, then it is rejected before
content is echoed or persisted. The test corpus uses synthetic sentinels, checks
that diagnostics do not reveal them, and verifies symlink/path and output
collision refusal. The importer does not claim to detect arbitrary secrets;
allowlisted metadata and reviewed source admission establish the boundary.

### REQ-005 — Reuse the existing analyzer and report

**SC-005:** Given admitted generic records, when the importer and direct AIM
baseline analyze the same mapped operations, then the report classifications,
constraints and evidence boundaries agree, outputs are deterministic, and
existing AIM/report versions remain unchanged. The separate provenance artifact
contains source/mapper versions, source/projection/report hashes, mapping losses,
coverage and limits. Neither a provider status nor protocol conformance raises
an assurance class.

### REQ-006 — Two lifecycle spikes have falsifiable outcomes

**SC-006:** Given selected primary source versions and synthetic OpenAI Agents
approval/reject/pause/resume cases and MCP deferred-task/status/state-handle
cases, when separate offline spikes run, then each reports retained/lost identity,
attempt ownership, explicit dependencies/versions, lifecycle-state coverage,
unknown classifications, incompatible shapes and every false-safe result against
predeclared cases. Success means required field retention with no false-safe
result in that corpus; negative or inconclusive results complete the spike and
can stop provider implementation. A spike is not provider adoption, live
conformance, execution authorization or validation of provider claims.

### REQ-007 — Other ecosystems have an explicit screening decision

**SC-007:** Given A2A, NeMo Agent Toolkit and OpenTelemetry candidates, when
screened, then each records primary source/version discovery, available
conformance evidence, license/dependency impact, privacy risks, AIM losses,
baseline and the next decision (`watch`, `spike`, `rejected`, or `research-only`).
Unavailable sources or version/conformance ambiguity are recorded as pending or
inconclusive. Screening cannot install a dependency or claim live compatibility.

### REQ-008 — Implementation and adoption remain distinct decisions

**SC-008:** Given generic implementation evidence, the lifecycle spike results
and screening records, when readiness is assessed, then a decision packet links
requirements, fixture/test evidence, mapping limits and SPEC-011 tracks. Generic
software readiness, provider adoption, real-source admission and publication
have separate recorded outcomes; no historical track is overwritten or promoted
merely because this spec exists. New contracts or architectural boundaries carry
migration/versioning notes and an applicable ADR before implementation acceptance.

Each SC identifier names a future acceptance contract in `quickstart.md` and
`assurance.json`; no future test is represented as already executed.

## Scientific boundaries and compatibility

The hypothesis is that structured recorded metadata can retain useful ordering
and uncertainty evidence without a provider dependency. Synthetic retention and
classification comparisons are engineering evidence about their exact fixtures.
They establish no real workload coverage, comprehensive effect discovery,
protocol compliance, production safety, general confluence or Yang–Baxter result.
A comparison's false-safe count refers only to predeclared finite cases and is
reported with corpus size, cases excluded and unsupported mappings.

This spec changes no current schema bytes or runtime authorization. Later
implementation adds a versioned import interface and provenance contract after
review, reusing AIM/report semantics. Any incompatible requirement starts a
separate contract/ADR decision rather than weakening `unknown` or existing checks.

## Evidence and unresolved questions

Obtained evidence is empty and human review is pending. Implementation tasks are
ready for the generic synthetic increment. Provider version selection, source
rights, external reproduction, real trace admission, provider adoption and
publication remain explicit later decisions. Those questions do not block
building and testing the generic offline importer.
