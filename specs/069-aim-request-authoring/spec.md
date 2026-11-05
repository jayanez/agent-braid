# SPEC-069: AIM request authoring for host models

**Milestone:** M4.8 — AIM request authoring (GitHub milestone 28; origin issue #1080).

**Status:** draft. Owner decisions D1 to D4 of 2026-11-05 are recorded under
Clarifications. Interim mitigation PR #1099 (tool description and skill example)
is not this feature's delivery and does not satisfy any requirement here.

## Purpose and scope

Host models in Claude Code, Codex and OpenCode must be able to author a valid
`analyze-work` request without prior knowledge of AIM, and every accepted or
refused request must follow one published, tested contract. This is engineering,
not a research protocol.

Origin: SPEC-068 T010 row 16, finding F1
(`specs/068-opencode-native-integration/evidence/native-observation.json`).
OpenCode's model sent `{units: [{id, writes}]}` because the tool declared
`request` only as "object or array"; the call was refused. With
`examples/analysis/file-edits-conflict.json` the same call returned `conflicting`
with the constraint `serialize-or-isolate`.

Pre-specification finding (2026-11-05, reproduced with the repository's
`jsonschema` dev dependency): the published AIM record schema
`schemas/0.2.0-draft/agent-interaction-metadata.schema.json` and the runtime
validator `agent_braid/analysis.py` disagree in both directions. `evidence: [{}]`
is accepted by the validator and refused by the schema; a blank `instanceId` or a
blank effect `resource` is accepted by the schema and refused by the validator;
a `readVersions` value of `1.0` is accepted by the schema and refused by the
validator. A second observation: the analyzer compares resources exactly, so
`repo://w/README.md` and `repo://w/./README.md` declared with `complete`
coverage are classified `independent-candidate` (review A2).
No schema exists for the analysis-input envelope (`analysisInputVersion`,
`source`, `operations`). This is an observation of two inputs each, not an
exhaustive inventory; REQ-002 produces the inventory.

In scope:

- one published contract per `analyze-work` request kind (`aim`, `git`, and the
  new `units`), enforced identical to the runtime validators;
- delivery of that contract to host models through the MCP tool definition;
- a simple, deterministic `units` authoring path that builds AIM records;
- refusals that name the failing field and expected form;
- guidance (skill, tool description, examples, documentation) that cannot drift
  from the contract;
- native evidence in the three hosts and a release gate.

Exclusions:

- Changes to analysis semantics, rule sets, classifications or assurance classes
  of the `aim` and `git` kinds.
- `analyze`, `prepare`, `execute`, `recover` and grant semantics.
- Inferring effects from repository content: `units` records only what the model
  declares.
- Any claim that a model will always author a valid request. Model behaviour is
  measured (REQ-010), not guaranteed.
- Publication, tags, plugin-dist pushes or releases without the owner's explicit
  yes (REQ-012).

## Authorities

Constitution clause zero and Articles 0, 5, 13, 14, 15, 16, 19, 20, 23 and 24;
[GOVERNANCE.md](../../GOVERNANCE.md);
[claim discipline](../../docs/theory/CLAIM_DISCIPLINE.md);
ADR 0024 (native AI plugins), ADR 0030 (native plugin surface naming),
ADR 0037 (OpenCode native plugin); precedents
[SPEC-046](../046-native-ai-plugins/spec.md),
[SPEC-054](../054-plugin-surface-naming/spec.md) and
[SPEC-068](../068-opencode-native-integration/spec.md). Contracts:
`schemas/0.2.0-draft/agent-interaction-metadata.schema.json`,
`schemas/0.1.0-alpha/git-analysis-request.schema.json`,
`schemas/0.1.0-alpha/analysis-report.schema.json`. A new ADR 0038 records the
`analyze-work` request contract (REQ-001).

Article 16 requires AIM to be versioned conservatively: any change to what the
AIM 0.2.0-draft schema accepts is a versioned decision (REQ-002, REQ-009).
Article 15 forbids blindly trusting declared metadata: `units` declarations are
recorded as declarations with partial coverage (REQ-006). Article 13 forbids
presenting a producer's claim as verified evidence: constructed records carry a
declared method and an assurance class no higher than the declaration supports.
Article 14 requires inspectable evidence: the constructed AIM is returned with
the report.

## Clarifications

Owner decisions of 2026-11-05 (asked interactively with explanation, risks,
undo and recommendation; the owner chose the recommended option each time):

- **D1 — Source of truth.** The JSON Schemas are the public contract. The runtime
  validators stay hand-written and dependency-free (`pyproject.toml` declares no
  runtime dependencies). A differential test over a shared corpus fails CI on any
  verdict difference. Existing divergences are resolved first (REQ-002, REQ-004).
- **D2 — Delivery.** A compact schema per `kind` is declared inside the
  `analyze-work` `inputSchema`. Its token cost per session is measured and
  capped (REQ-005). Adversarial review A1 (verified): the top level of
  `inputSchema` must stay a plain object, because the Claude and OpenAI tool
  APIs refuse top-level `oneOf` and `plugin_mcp.list_tools` writes
  `properties.workspaceId` into every tool schema. The per-kind choice
  therefore lives inside `request`, subject to a host probe.
- **D3 — Simple path.** A new `kind` `units` lets the model send units with
  exact resources and read/write effects; Agent Braid builds AIM records
  deterministically. It is a new public contract with its own version (REQ-006).
- **D4 — Host threshold.** Per host, over a fixed set of N = 10 prompts in a
  disposable profile: 10/10 valid requests with at most one refusal-guided retry,
  and at least 8/10 valid at the first attempt (REQ-010). Scoring rules,
  repetitions and a held-out prompt set (review A9) are decided in D9.
- **D5 — Automation (owner instruction, 2026-11-05).** Everything that can be
  automated transparently runs automatically: sandboxes, disposable host
  profiles, native runs, evidence capture and checks. Owner effort is limited to
  decisions, the release yes and steps that cannot be automated, each listed with
  its reason (REQ-013). Past labs (SPEC-068 T010) required pasting prompts and
  answers by hand; that pattern is not acceptable here.

Owner decisions of 2026-11-05 after the counterfactual analysis
(`reviews/counterfactual-20261105.md`):

- **D6 — Phases.** P1: contract alignment, envelope schema, differential test,
  refusals and compatibility (REQ-002, REQ-003, REQ-004, REQ-007, REQ-009,
  REQ-015). P2: the automated driver and a baseline run of the interim guidance
  (alpha.7 plus PR #1099) in the hosts (REQ-013, REQ-010 baseline arm). P3:
  `units` and schema delivery (REQ-005, REQ-006, REQ-008, REQ-014) only if the
  P2 baseline misses the D4 threshold in a required host; otherwise P3 is
  recorded as not needed, with the baseline evidence. Release and closure
  (REQ-010 final run, REQ-011, REQ-012) close the feature.
- **D7 — Declared-complete label.** When a pair is `independent-candidate` and
  the evidence of both records is only `method: declared`, the report labels it
  as declared, not observed (REQ-015). Classification is unchanged.
- **D8 — Alignment policy (resolves OD-5).** Where the published schema is
  looser than the runtime, tighten the schema with a note and no new AIM
  version (no working request breaks). Where the runtime is looser than the
  schema, keep the runtime behaviour as a documented runtime-only difference and
  fold the tightening into the next AIM version.
- **D9 — Measurement (resolves OD-6).** Three repetitions per prompt, a held-out
  prompt set frozen before the guidance is rewritten, pinned model identifiers,
  confidence intervals, an ablation arm (interim guidance only vs schema in
  `inputSchema`; the schema is kept only if it improves first-attempt validity
  in at least one host), and an automatic re-run of the driver at every plugin
  release and whenever the host version or pinned model changes.

- **D10 — Milestone (resolves OD-1).** Milestone M4.8 created and #1080 moved
  to it on 2026-11-05. Task issues are created later, only with the owner's yes.
- **D11 — Required hosts (resolves OD-3).** Claude Code, Codex and OpenCode must
  all meet REQ-010 before release. Codex must be installed for the driver
  (it is not on this machine's `PATH` on 2026-11-05).

Open questions for the owner (OD-*) are listed under Evidence and unresolved
questions.

## Requirements and acceptance scenarios

### REQ-001 — Specification and architecture

Record the `analyze-work` request contract (kinds, schemas, delivery, `units`
construction, refusal format, versioning) in ADR 0038 and a contract file under
`contracts/`.

**SC-001:** Given this specification, ADR 0038 and the request contract, when
they are analyzed against ADR 0024, ADR 0030, ADR 0037 and Articles 13–16, then
requirements, tasks and procedures agree, unchanged contracts are listed, and the
native-evidence and owner gates are explicit.

Verification: [procedure_001](validation-plan.md); T001.

### REQ-002 — Divergence inventory and resolution

Produce a complete inventory of differences between each published schema and
its runtime validator (AIM record, analysis-input envelope, git request): every
constraint the schema states, every check the validator performs, and every
case where they disagree. Resolve each divergence by a recorded decision: tighten
the schema, tighten the validator, or document an intentional non-structural
check (for example cycles, duplicate identifiers, unknown dependencies, which
JSON Schema cannot express). The inventory names the layer of each check:
published schema, `analysis.py`, the `tooling_mcp` adapter bounds (32
operations, 256-byte identifiers) or the git adapter, and records string
semantics that differ between Python and ECMAScript validators (for example
which characters count as whitespace for "blank"). A change to what AIM
0.2.0-draft accepts follows Article 16 and D8 (REQ-009). If the inventory finds
more than 15 divergences, D1 is reopened for the owner (counterfactual C1).

**SC-002:** Given the schemas and validators at the candidate commit, when the
inventory procedure enumerates schema keywords and validator checks, then every
divergence has a row with a reproducing input, both verdicts and a decision; the
three divergences observed on 2026-11-05 are present; adapter-only bounds and
whitespace semantics have rows; no row is resolved by deleting a test case.

Verification: [procedure_002](validation-plan.md); T002.

### REQ-003 — Analysis-input envelope schema

Publish a JSON Schema for the analysis-input envelope (`analysisInputVersion`
`0.1.0-alpha`, `source {kind, description}`, `operations`) that references the
AIM record schema, and state the accepted alternatives the runtime already
supports (single AIM record, nonempty AIM array).

**SC-003:** Given the new envelope schema, when every example under
`examples/analysis/` with `sourceKind` `aim` and every corpus case is validated,
then schema verdicts equal runtime verdicts, and the schema is listed in the
schema inventory with its version.

Verification: [procedure_003](validation-plan.md); T003.

### REQ-004 — Differential equivalence of schema and validator

Maintain a versioned corpus of valid and invalid requests for each kind: one
minimal valid case, one mutation per field (missing, extra, wrong type, empty,
blank, boundary), and batch-level cases (duplicates, cycles, unknown or self
dependencies). A test compares, for every case, the schema verdict with the
runtime verdict of the complete `analyze-work` service path (adapter bounds
plus validator), so no layer is left out; batch-level and adapter-only cases
record the expected runtime-only refusal. Corpus strings avoid characters whose
"blank" status differs between Python and ECMAScript, or record that difference
as a declared limit.

**SC-004:** Given the corpus and the schemas, when the differential test runs in
CI, then every structural case has equal verdicts and every batch-level case has
the recorded runtime refusal; a deliberately introduced divergence (negative
control: relax one schema keyword, and separately one validator check) fails the
test.

Verification: [procedure_004](validation-plan.md); T004.

### REQ-005 — Schema delivery in the tool definition

Declare in the `analyze-work` `inputSchema` a compact schema per `kind`,
derived from the published schemas, so a host can validate or guide the call.
The top level stays a plain object with `properties` and `required` (A1); the
per-kind schemas sit inside `request`. Before adoption, a host probe confirms
that each host accepts the nested form; a host that refuses it uses the
documented fallback (description plus skill) as a declared limit. The tool
definitions are recorded at the server boundary (the plugin's `list_tools`
output, captured by a recording stdio proxy), where byte identity across hosts
is checked. Size is measured with named tokenizers as an approximation and kept
under the cap OD-2. Whether a host loads tool schemas eagerly or on use (Claude
Code defers MCP tool schemas until use) is recorded. The per-kind schema is
kept only if the D9 ablation arm shows it improves first-attempt validity in at
least one host; otherwise the fallback is used everywhere.

**SC-005:** Given the built plugin, when the plugin's `list_tools` runs (unit
test) and each host connects through the recording proxy, then every tool is
listed (no exception from the `workspaceId` injection), `analyze-work` declares
the per-kind schemas inside `request`, the recorded definition bytes are
identical for every host connection, the approximate size is under the cap, the
declared schema accepts and refuses the corpus as the published schemas do, and
each host's acceptance of the nested form is recorded.

Verification: [procedure_005](validation-plan.md); T005.

### REQ-006 — `units` authoring kind

Add `kind` `units` with its own versioned request schema. A request lists units,
each with a unique identifier, optional dependencies on other units, and exact
resources with effect kinds from Article 5. Agent Braid builds one AIM
0.2.0-draft record per unit deterministically from a field-by-field construction
table in the contract (REQ-001), with byte-level golden fixtures:

- `definition.id` is the reserved `agent-braid.units-declaration/<version>`;
  `definition.digest` identifies the construction rules version;
  `inputDigest` is the digest of the canonical, normalized unit declaration
  (identifier, dependencies, normalized resources, kinds and workspace scope),
  so different declarations have different digests and a record cannot pass
  as a producer's code digest;
- coverage is always `partial`, whatever the request says, so a `units`
  request can never be classified `independent-candidate` (A2): pairs are
  `ordered`, `conflicting` or `unknown`;
- the evidence item is fixed: `method` `declared`, assurance class 0, and
  assumptions stating that effects are declared by the host model and not
  observed;
- resources are normalized lexically, without filesystem access: Unicode NFC,
  `.` segments collapsed, `..` refused, trailing `/` removed, absolute paths
  and schemes refused; two resources that differ only by letter case in one
  request are refused as ambiguous.

The workspace scope is the registered workspace of the call; where the plugin
layer strips `workspaceId` before the service (A4), the plan places
construction where the identifier is known. `units` requests count toward the
same adapter bounds as `operations` (32 units, 256-byte identifiers) (A7). The
response contains the analysis report and the constructed AIM request, so the
result can be replayed through `kind` `aim`.

**SC-006:** Given a `units` request equivalent to T010's attempt (two units that
write `README.md`), when `analyze-work` runs, then the constructed AIM validates
against the AIM schema and equals its golden fixture byte for byte, replaying it
through `kind` `aim` returns an identical report, the pair is `conflicting` with
`serialize-or-isolate`, coverage is `partial`, and the provenance names the
`units` construction. Negative controls: `README.md` and `./README.md` in two
units are recognized as the same resource; a request claiming `complete`
coverage still yields `partial`; two units with disjoint resources yield
`unknown`, never `independent-candidate`; a `..` path, an absolute path, a
case-only duplicate, 33 units, a 257-byte identifier, a duplicate unit
identifier, an unknown dependency and an unsupported effect kind are refused
with REQ-007 messages; two runs on the same input give identical bytes.

Verification: [procedure_006](validation-plan.md); T006.

### REQ-007 — Field-specific refusals

Structural refusals of an `analyze-work` request (shape, type, missing or extra
field, enum, bounds) name the failing location as a JSON Pointer and the
expected form, for `aim`, `git` and `units`. Pointer segments that come from
request keys not defined by the schema are replaced by a fixed token with a
short digest, so an unknown key is never echoed (A8). Semantic refusals (batch
checks, git adapter errors, workspace boundary) use fixed codes and fixed
messages; git messages stay masked because they can carry paths or Git output.
A missing path and a path outside the configured roots produce the same refusal,
so refusals do not reveal whether a host path exists. Messages are at most 1024
characters and never contain request values.

**SC-007:** Given each invalid corpus case, when it is sent through the MCP
`analyze-work` tool, then a structural refusal names the case's pointer and
expected form and a semantic refusal returns its fixed code; every message is at
most 1024 characters. Negative controls: an unknown key shaped like a secret is
not echoed; a git error carrying a path is masked; a nonexistent path and an
existing path outside the root return the same refusal.

Verification: [procedure_007](validation-plan.md); T007.

### REQ-008 — Drift-proof guidance

The analyze skill example, the tool description, every request example under
`examples/analysis/` and the request examples in `docs/tooling/` are validated
against the published schemas by a test, or generated from them. The interim text
of PR #1099 is replaced by guidance that covers all three kinds, prefers `units`
for simple requests, and keeps the honesty rules (coverage, declaration digests,
verbatim refusals).

**SC-008:** Given the guidance files, when the drift test runs, then every
embedded request validates and analyzes with its documented result, including
the documented classification and constraints (A14); changing a required field
name in the schema, or the documented result, without updating the other fails
the test.

Verification: [procedure_008](validation-plan.md); T008.

### REQ-009 — Compatibility and versioning

Requests accepted by `analyze-work` in plugin `0.1.0-alpha.7` remain accepted
with identical reports, unless REQ-002 records a decision to refuse a specific
class; each such class is listed with its reason, its version change and its
migration message. Per D8, schema tightening that matches existing runtime
refusals needs no new version but a note; runtime tightening that would refuse
requests alpha.7 accepts is not done in this feature and is recorded for the
next AIM version (counterfactual C8: the compatibility risk is in the
validator, not the schema). The `agent-braid-plugin` and
`agent-braid-tooling` contract versions follow the same rule. A rollback path
to the previous plugin is documented, including what happens to saved `units`
requests (the previous plugin refuses them with a version message).

**SC-009:** Given a recorded set of requests accepted by alpha.7 (examples,
goldens and T010 inputs), when they are replayed on the candidate, then each is
accepted with a byte-identical report (no runtime tightening is allowed by D8);
schema notes list every tightened keyword; contract version fields match the
plan.

Verification: [procedure_009](validation-plan.md); T009.

### REQ-010 — Native host evidence

In each of Claude Code, Codex and OpenCode, in a disposable profile that never
touches the user's configuration, the automated driver of REQ-013 runs a fixed
prompt set of N = 10 analysis
requests written in natural language without AIM vocabulary (covering
`units`-shaped, AIM-only and git cases). Each prompt has a scoring rule fixed
in advance: the expected resources, effect kinds and classification. A run is
valid only if the model calls `analyze-work`, the call is accepted, and the
encoded resources and result match the rule; not calling the tool, or a call
that declares nothing, is a failure. "First attempt" is the first
`analyze-work` call; a retry is a later call after an Agent Braid refusal;
calls to `plugin-status` or `workspaces` do not count as attempts. Decided (D9): three repetitions per prompt, a held-out prompt set frozen before the
guidance is rewritten (T008) and not shown to its authors, pinned model
identifiers, and confidence intervals reported with the result. The D9 rules
apply: three repetitions, held-out set, pinned models, intervals and the
ablation arm. Two runs are defined: the P2 baseline on the interim guidance and
the final run on the release candidate. Record raw transcripts, tool calls,
refusals and retries. Apply the D4 threshold per host. A missed threshold, an
unobserved host or an inconclusive run is reported as such and blocks REQ-012 for
that host; it is not reinterpreted.

**SC-010:** Given the candidate plugin installed in each host's disposable
profile, when the ten prompts run, then each host records at least 8/10 valid
requests at the first attempt and 10/10 within one refusal-guided retry, with
versions, model identifiers, transcripts and hashes recorded; any shortfall is
recorded as a negative result with its cases.

Verification: [procedure_010](validation-plan.md); T010.

### REQ-011 — Documentation

Document the three request kinds, when to use `units`, the honesty rules, the
refusal format and the compatibility notes in `docs/tooling/NATIVE_PLUGINS.md`
and the plugin release notes, without claiming unobserved host behaviour.

**SC-011:** Given the documentation, when it is reviewed against the contract and
REQ-010 evidence, then every behavioural statement is backed by a test or an
observation, links resolve, and limits are stated.

Verification: [procedure_011](validation-plan.md); T011.

### REQ-012 — Release gate and issue closure

Ship through a plugin release (`0.1.0-alpha.8` or later) only with the owner's
explicit yes, after REQ-010 meets the threshold in Claude Code, Codex and OpenCode (D11;
the gate can never be met with zero hosts, A13).
Close issue #1080 only after that evidence exists on the published release.
Every later plugin release re-runs the driver automatically (D9), and the
release notes report the field metric: first-attempt acceptance rate per kind
from local telemetry (REQ-014), marked as real-use evidence.

**SC-012:** Given the release candidate, when the owner reviews REQ-001 to
REQ-011 evidence, then publication happens only after a recorded explicit yes,
the published package matches the candidate, and #1080 is closed with a link to
the native evidence.

Verification: [procedure_012](validation-plan.md); T012.

### REQ-013 — Fully automated validation and native runs

Provide one driver command that, without manual intervention, creates the
disposable profiles and a sandbox workspace with fixed content, builds and
installs the candidate plugin in each available host, runs the REQ-010 prompt
set through each host's non-interactive mode (for example `claude -p`,
`codex exec`, `opencode run`), captures transcripts, tool calls and versions,
scores them, writes the evidence JSON with hashes, and tears everything down.

Safety of unattended runs (A10):

- the host's tool permissions allow only the Agent Braid MCP tools; shell, file
  edit, web and other tools are denied, so content in the sandbox cannot steer
  the model into side effects;
- the run happens inside an operating-system sandbox or container that denies
  access to the user's real host configuration, keychain and home directory;
  the driver never opens those paths, and the check is a denied-access probe
  plus a canary fake configuration, not a hash of the user's files;
- credentials are read by the driver outside the sandbox (environment or
  keychain) and injected into the sandboxed host as environment variables at
  run time; they are never written to files or prompts, and transcripts are
  redacted and scanned for secrets before evidence is written. Authentication
  fallback, in order (counterfactual C5): a long-lived host token through the
  environment; a one-time sign-in stored in a dedicated reusable sandbox
  profile (never the user's real profile), recorded as `auth:
  interactive-once`; otherwise the host is a declared limit. API-key runs have
  a billing cost that the runbook states per pass;
- `--fake-hosts` evidence proves the pipeline, not the host, and is labelled so;
- a `--fake-hosts` mode runs the same pipeline with fake host executables in CI.

The runbook lists every remaining manual step with the reason it cannot be
automated; the expected list is owner decisions, the release yes, and a
one-time host sign-in inside the disposable profile if the host offers no
non-interactive authentication. A host that cannot run headless is reported as
a limit, not replaced by manual copy-paste.

**SC-013:** Given a machine with the hosts installed, when the operator runs the
driver once, then it completes all available hosts unattended, the evidence file
and transcripts exist with hashes, the denied-access probe and the canary show
no access to real configuration (negative control: a run configured with a
leaked real path is stopped), a planted fake secret does not appear in the
evidence (negative control), denied tools are refused when the model asks for
them, teardown leaves no profile or process behind, and the manual-step list in
the runbook matches what the run actually required.

Verification: [procedure_013](validation-plan.md); T013.

### REQ-014 — Telemetry and platforms

Shadow and local telemetry handle `kind` `units` explicitly: episodes are
recorded with defined outcome keys, never dropped silently (review A12:
`ToolingService._shadow` forwards the request `kind` to the shadow worker inside
a broad `except Exception: pass`, so an unsupported kind would vanish without a
record; T014 verifies the current behaviour). Path normalization and the driver are specified for macOS and
Linux; Windows behaviour is tested or declared a limit. The release notes state
how the interim guidance of PR #1099 is replaced.

**SC-014:** Given `units` requests through the plugin, when telemetry is
inspected, then each request has a shadow or telemetry record with the defined
outcome key and no swallowed exception; normalization tests pass on macOS and
Linux CI, and Windows is tested or listed as a limit.

Verification: [procedure_014](validation-plan.md); T014.

### REQ-015 — Declared-complete label in reports

When an `analyze-work` report classifies a pair `independent-candidate` and the
evidence of both records has only `method: declared`, the interaction carries an
additive label stating that completeness is declared, not observed (D7). The
classification, constraints and existing report fields are unchanged; the
analysis report schema gains the optional label under its versioning rules.

**SC-015:** Given two disjoint `aim` records with `complete` coverage and only
declared evidence, when they are analyzed, then the pair stays
`independent-candidate` and carries the declared-not-observed label; with a
`replay` evidence method on both records the label is absent; every other field
is byte-identical to the alpha.7 report except the added label.

Verification: [procedure_015](validation-plan.md); T015.

## Scientific boundaries and compatibility

Engineering only; no hypothesis and no scientific claim. The differential test
proves agreement on the corpus, not on all inputs; the corpus design (REQ-004)
bounds that gap. Native evidence (REQ-010) describes the observed host versions,
models and prompt set only; it is not a guarantee of future model behaviour.
`units` records are declarations: their analysis is exactly as reliable as the
declared resources, and their coverage and assurance class say so. Additive by
default: `aim` and `git` semantics, the analysis report schema and existing
contracts are unchanged except where REQ-002 records a versioned decision.

## Evidence and unresolved questions

Planned and obtained evidence are separate fields in `assurance.json`. At draft
stage no obtained evidence exists; the 2026-11-05 divergence observation is a
pre-specification note, to be reproduced and recorded by T002.

Open questions for the owner:

- **OD-2:** Token cap for the `analyze-work` definition (REQ-005), proposed in
  the plan from measurements.
- **OD-4:** Host authentication in disposable profiles (REQ-013): which
  non-interactive method each host supports, observed in the plan's research;
  if none, the owner accepts a one-time sign-in step or declares the host a
  limit.

OD-1, OD-3, OD-5 and OD-6 were resolved by D10, D11, D8 and D9.

Native evidence, human review and owner approval are separate gates; no green
check implies them.
