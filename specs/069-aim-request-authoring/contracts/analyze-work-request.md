# `analyze-work` request contract (SPEC-069, phases P1 and P3)

**Status:** the `aim` and `git` forms were accepted 2026-11-07 with
[ADR 0038](../../../docs/adr/0038-analyze-work-request-contract.md) by the owner. The
`units` section was added 2026-11-07 by SPEC-069 T006 after phase P3 started (the P2
baseline missed D4 and the founder decided P3 runs); it has not had owner review.
Normative for the request forms below; nothing here describes host behaviour (that is
measured in P2 and the final run).

## Call

`analyze-work` takes exactly `kind` and `request` (the plugin adds `workspaceId`).
`kind` is `aim`, `git` or `units`.

## Request forms

| kind | form | schema (draft 2020-12) |
|---|---|---|
| `aim` | envelope `{analysisInputVersion: "0.1.0-alpha", source: {kind, description}, operations: [AIM record, ...]}` | `schemas/0.1.0-alpha/analysis-input.schema.json` |
| `aim` | a single AIM record | `schemas/0.2.0-draft/agent-interaction-metadata.schema.json` |
| `aim` | a nonempty array of AIM records | `analysis-input.schema.json` (`$defs/records`) |
| `git` | `{gitAnalysisRequestVersion: "0.1.0-alpha", repository, baseRevision, operations: [>= 2 operations]}` | `schemas/0.1.0-alpha/git-analysis-request.schema.json` |
| `units` | `{unitsRequestVersion: "0.1.0-alpha", units: [{id, dependencies?, effects: [{kind, resource}], coverage?}, ...]}` (1 to 32 units) | `schemas/0.1.0-alpha/units-request.schema.json` (own version `0.1.0-alpha`) |

Report: `schemas/0.1.0-alpha/analysis-report.schema.json`.
`examples/analysis/file-edits.json` and `file-edits-conflict.json` are valid `aim`
envelopes; they are analyzed with the documented results in the test suite.

## What enforces what

| Layer | Checks |
|---|---|
| Published schema | field presence and exactness, types, enums, constants, non-blank strings (`\S`), digest pattern, array bounds, uniqueness of `dependencies` |
| `agent_braid/analysis.py` | everything above that the schema states, plus batch checks: unique `instanceId` and `attemptId`, known / non-self / acyclic dependencies |
| `tooling_mcp` adapter | at most 32 operations; `instanceId` and `attemptId` at most 256 UTF-8 bytes in arrays and `operations` lists (not in a single-record request); depth 32; input at most 1 MiB; git repository and worktree paths inside the configured roots |
| git adapter | revision resolution, ancestry, snapshot stability, output bounds |
| `agent_braid/units.py` | the `units` schema checks (including the lexical resource rules and both adapter bounds, with pointers), plus batch checks: unique unit `id`, known / non-self / acyclic dependencies, no two resources that differ only by letter case; then the construction below. The shared adapter bounds also run on the declaration and on the constructed records |

The complete inventory, with a reproducing input and both verdicts per difference,
is `evidence/divergence-inventory.json` (state at the start of P1) and
`evidence/divergence-inventory-after-decisions.json` (state after the decisions).
Documented differences between schema and runtime:

- Runtime-only (JSON Schema cannot express): batch checks, adapter bounds, roots,
  Git resolution.
- Runtime looser than the schema, kept until the next AIM version (D8): `evidence`
  items are not inspected beyond a nonempty array; git `uncertainPaths` uniqueness
  is not enforced; the identifier bound is not applied to a single-record request.
- Declared limits: see [compatibility.md](../compatibility.md).

## Kind `units` (REQ-006)

A `units` request records what the host model declares, nothing more. Agent Braid
validates it, normalizes resources lexically and builds one AIM 0.2.0-draft record per
unit, in input order. The response is
`{report, constructedRequest, provenance}`: `report` is `analysis.analyze` of
`constructedRequest`, so sending `constructedRequest` with `kind` `aim` returns a
byte-identical report.

### Request fields

| Field | Rule |
|---|---|
| `unitsRequestVersion` | required, the constant `0.1.0-alpha` |
| `units` | required, 1 to 32 unit objects (the adapter's operation bound, A7) |
| `units[].id` | required, non-blank, at most 256 UTF-8 bytes (the schema states 256 code points; the byte bound is runtime-only); unique in the request |
| `units[].dependencies` | optional (default `[]`), unique non-blank ids of other units in the request; no self or cyclic dependency |
| `units[].effects` | required, nonempty array of `{kind, resource}` with exactly those properties |
| `effects[].kind` | one of the Article 5 families: `read`, `write`, `call`, `transform`, `emit`, `delete`, `deploy` (`unknown` and anything else are refused) |
| `effects[].resource` | a workspace-relative path; normalized and refused as below |
| `units[].coverage` | optional, `complete`, `partial` or `unknown`; accepted so a model's claim does not fail the call, and never honoured |

### Lexical resource normalization (no filesystem access)

Refused, in this order, each with a fixed message at the resource's pointer: a
non-string or blank value; a control character (U+0000 to U+001F, U+007F); a
backslash; a scheme or drive letter (a first segment matching
`[A-Za-z][A-Za-z0-9+.-]*:`, so `repo://…`, `https://…`, `C:/…` and `notes:1.md` are
refused while `docs/a:b.md` is not); a leading `/`; any `..` segment; a path with no
segment left after normalization (`.`, `./`). Then: `.` and empty segments are dropped
(so `./README.md`, `docs//a` and a trailing `/` collapse) and the result is put in
Unicode NFC. After normalization, two resources in one request that are equal only
when case-folded are refused as ambiguous (`case-only-duplicate-resource`); exact
repeats are allowed (that is how a conflict is declared). The schema's `pattern`
states the refusals; NFC and the case check are runtime-only.

### Construction table

`<scope>` is the workspace scope (below), `<path>` a normalized resource, `C` the
construction identifier `agent-braid.units-declaration/0.1.0-alpha`.

| Constructed field | Value |
|---|---|
| envelope | `{analysisInputVersion: "0.1.0-alpha", source: {kind: "units", description: "Agent Braid C; effects declared by the host model, not observed"}, operations: [one record per unit, input order]}` |
| `aimVersion` | `0.2.0-draft` |
| `instanceId`, `attemptId` | the unit `id` (one attempt per declared unit; both stay within the 256-byte bound) |
| `definition.id` | `C`, reserved for this construction. `kind` `aim` does not refuse it (D8 forbids runtime tightening), so only the provenance of a `units` call shows that a record was constructed here |
| `definition.digest` | `sha256:` + SHA-256 of the UTF-8 bytes of `C`: identifies the construction rules version, not code |
| `inputDigest` | `sha256:` + SHA-256 of the canonical JSON (keys sorted, separators `,` `:`, ASCII escapes) of `{construction: C, workspace: <scope>, id, dependencies, effects: [{kind, resource: <path>}]}`, effects and dependencies in input order; different declarations or scopes give different digests |
| `dependencies` | the unit's dependencies, input order |
| `readVersions` | `{}` |
| `effects.declared` | `[{kind, resource: "repo://<scope>/<path>"}]`, input order; the resource is an opaque string, not percent-encoded |
| `effects.inferred`, `effects.observed` | `[]` |
| `effects.coverage` | `{status: "partial", domain: "workspace-relative paths declared by the host model", method: "units declaration (C)"}` whatever the request says, so no pair is ever `independent-candidate` (A2): pairs are `ordered`, `conflicting` or `unknown` |
| `evidence` | one item: `property: independence`, `method: declared`, `assuranceClass: 0`, the domain above, assumptions "Effects are declared by the host model and not observed by Agent Braid.", "The declaration may be incomplete, so coverage is partial." and "Resources are compared after lexical normalization only; symbolic links, case-insensitive file systems, generated files and semantic dependencies are not resolved.", `observationContract` "none: built from the request without filesystem or repository access", `executionContract` "no execution; analysis only" |
| `provenance` (response) | `{source: "units declaration", construction: C, constructionDigest, unitsRequestVersion, workspaceScope: <scope>, coverage: "partial", replay: "analyze-work kind aim with constructedRequest", executionAuthorization: false}` |

### Workspace scope (A4)

The plugin strips `workspaceId` from the arguments before the workspace service runs.
The scope is therefore derived inside the service from its configured source root
with the registry's own rule: the first 32 hex digits of the SHA-256 of the canonical
source root path. For a plugin workspace this equals its `workspaceId` (a test
compares them); for the portable `agent-braid-tooling` server it is the same digest of
its source root. The scope never contains the host path, but it is a pseudonym, not a
secret: anyone who can guess the path can recompute it (the same holds for
`workspaceId`).

Byte goldens of the constructed request (scope of a source root at `/workspace`) are
in `tests/fixtures/analysis-requests/units/golden/`; the corpus cases are in
`units/valid/` and `units/invalid/`.

## Refusals

A refused call returns `status: refused` and a summary
`analyze-work refused: <reason>[ at <pointer>; expected <form>][ [<code>]]`.

- **Structural** (shape, type, missing or unknown field, enum, bounds): the
  reason, ` at ` and a JSON Pointer into the request (`/` for the whole request,
  `/0/instanceId` for the first array element, `/operations/0/...` inside an
  envelope or git request), then `; expected ` and the accepted form. A missing or
  unknown property is reported at its parent object, with missing names listed and
  unknown keys replaced by `<key:xxxxxxxx>` (first eight hex digits of the SHA-256
  of the key). `readVersions` keys are request-defined and always tokenized.
- **Semantic** (batch checks): the alpha.7 reason and a code: `duplicate-instance-id`,
  `duplicate-attempt-id`, `unknown-dependency`, `self-dependency`,
  `cyclic-dependencies`. `units` adds `duplicate-unit-id` and
  `case-only-duplicate-resource`, and its semantic refusals also name the pointer of
  the offending element (indices only), for example
  `unknown dependency at /units/0/dependencies/0 [unknown-dependency]`.
- **Bounds** (`units`): `Request exceeds the 32-operation adapter limit at /units` and
  `Operation identifier exceeds 256 bytes at /units/<i>/id`, each with the expected form.
- **Boundary:** a repository or worktree path that does not exist and one outside
  the configured roots return the same refusal, which names neither path.
- **Masked:** git observation errors return `The bounded operation was refused`.
- Messages never contain a request value, are at most 1,024 characters, and the
  alpha.7 reason text always leads.

## Telemetry and shadow (REQ-014)

Local telemetry records a `units` call like any `analyze-work` call: outcome `ok` or
`refused` (with a refusal-reason bucket), duration, and the report's classification
counts; it does not distinguish `kind`. System One shadow records an accepted `units`
call as one episode with `analysisKind` `units`, derived from the constructed AIM
records and the report (no declaration text; effect kinds come from the constructed
records). A refused call records no episode. A shadow failure never changes the
envelope and is counted as `internal-error` in the in-process refusal counters; it is
no longer discarded silently. Before T014 a `units` episode was refused by the store's
validator (`unavailable`) and lost.

Platforms: normalization is lexical string logic with no filesystem or `os.path` use,
so it gives identical bytes on macOS, Linux and Windows path semantics (tested by
patching `os.path` to `ntpath`; CI runs on Linux, macOS is covered by the same tests
run locally and by Unicode NFD input as macOS file systems produce it). Windows is
tested only for this normalization, not for the plugin, the driver or the shadow
store (declared limit).

## Report label

When an interaction is `independent-candidate` and every evidence item of both
records has `method: declared`, the interaction carries
`completenessBasis: "declared-not-observed"`. It is absent otherwise (including
when either record has a non-declared evidence item). Classification, reasons,
constraints and evidence are unchanged. `analysisId` digests the whole report and
therefore includes the label.

## Delivery in the tool definition (phase P3, T005)

P3 runs (founder decision 2 of 2026-11-07), so REQ-005 delivery enters this contract.
This section was added by T005 after the owner's acceptance above; that acceptance does
not cover it, and it awaits review. The `analyze-work` `inputSchema` keeps a plain-object
top level: `type`, `additionalProperties`, `properties` (`kind` with the enum `aim`,
`git`, `units`; `request`; and the plugin-injected `workspaceId`), `required`, and one
`$defs` table (A1). `properties.request` is
`{"type": ["object", "array"], "oneOf": [...]}` with one branch per request form above,
each labelled by a `description` `kind=<kind>[ <form>]`. The AIM record and its effect
item are declared once under the top-level `$defs` and referenced as `#/$defs/<name>`.

- **Source.** `scripts/spec069_tool_schemas.py` derives the branches from the published
  schemas: annotations stripped, references inside one file inlined, a reference to
  another published file shared through `$defs`, `minLength: 1` dropped where
  `pattern: "\S"` already implies it. It writes `agent_braid/analyze_work_schema.py`
  (with the SHA-256 of each source schema); a test regenerates it and compares bytes.
- **One relaxation.** The `units` resource `pattern` states the lexical refusals with
  lookaheads, which not every model-provider schema dialect accepts; the declared
  branch replaces it with `\S` (non-blank). `agent_braid/units.py` still refuses every
  such resource with a pointer refusal, so the declared schema is looser than the
  published one only there: 19 of the 124 `units` corpus cases, each refused by the
  runtime. No declared pattern uses a lookaround (tested).
- **Equivalence.** On the committed corpus (310 `aim`, 119 `git`, 124 `units` cases),
  each kind's branches and the whole call schema give the published schemas' verdicts,
  with the relaxation above for `units` (`DeclaredSchemaDifferentialTests`). The
  link between `kind` and the request form cannot be stated inside `request` without a
  top-level combinator, so a request of another kind's form passes the declared schema
  and is refused by the runtime with a structural refusal.
- **Validating hosts.** A host that validates arguments against the declared schema
  refuses, before calling, the runtime-looser classes listed above (for example an
  `evidence` item that is not an evidence object); the runtime still accepts them.
- **Size cap (D12).** Name, description and `inputSchema` of each listed tool, as compact
  UTF-8 JSON, stay within 1,500 tokens approximated as ceil(bytes / 3.7) (`analyze-work`
  with the three kinds: 5,447 bytes, about 1,473 tokens). A one-time
  calibration measured 4.14–4.27 bytes per token with `o200k_base` and `cl100k_base`, so
  the approximation over-counts them by about 12–15 %; Anthropic's tokenizer is not
  measured. Above the cap the test fails and the description-only fallback applies.
- **Ablation switch (D9).** `python -m scripts.spec069_tool_schemas --delivery
  description-only` rewrites the generated module so a build serves the interim
  definition (`request` declared as object or array with the interim prose in both the
  tool description and `request`, byte identical to alpha.7 plus PR #1099 except that
  `kind` lists `units`). The per-kind arm's tool description replaces that prose with
  one sentence pointing at the labelled branches and the skill, because the shapes are
  in the schema and the definition must fit the cap; the ablation therefore compares
  "interim prose only" with "schema plus pointer".
  Only `per-kind` is committed. The arm is part of the built bytes, so it reaches every
  host the same way (no environment variable, which Codex does not forward to plugin MCP
  servers by default).
- **Host probe (2026-11-07, `evidence/host-probe-nested-schema.json`).** A recording stdio
  test double served the model-facing `analyze-work` definition (per-kind arm, 5,447
  bytes) to Claude Code and OpenCode in disposable profiles; Codex was not run (no
  OpenAI key in the environment, a declared limit). Both hosts listed the tool without
  refusing the nested form and received byte-identical definitions (same canonical
  SHA-256 on both connections, equal to the served definition). Claude Code sent the
  tool to the model API in its first request, with an `input_schema` equal to the served
  one (eager loading under `--strict-mcp-config`). **Not observed:** whether the models'
  calls conform and whether `request` arrives as an object, because the Anthropic API
  rejected every model call (credit balance too low); and OpenCode's model-API request.
  Those, the D9 ablation result and Codex's acceptance remain pending (REQ-005); adoption
  in a release waits for them. The ablation arm is `--arm final-no-schema` of
  `scripts/spec069_native_runs.py` versus `--arm final`.

## Compatibility and versions

Unchanged: `agent-braid-plugin/v0.2`, `agent-braid-tooling/v0.1`, AIM
`0.2.0-draft`, analysis input, git request and report `0.1.0-alpha`. New: the `units`
request `0.1.0-alpha` (additive; it changes no `aim` or `git` verdict or report). A
plugin without the `units` kind (alpha.7 and earlier) refuses a saved `units` request
with `Unsupported analysis kind`; rolling back loses only that kind, and a saved
`constructedRequest` still replays through `kind` `aim`. Every aim
request alpha.7 accepts is accepted with an identical report modulo the label and
the recomputed digest (`evidence/alpha7-replay.json`). Schema tightening and
rollback: [compatibility.md](../compatibility.md).

## Tests that enforce this contract

`tests/test_spec069_differential.py`, `test_spec069_units.py`, `test_spec069_refusals.py`,
`test_spec069_declared_label.py`, `test_spec069_alpha7_replay.py`,
`test_spec069_compatibility.py`, `test_spec069_divergence_inventory.py`,
`test_spec069_schema_delivery.py`.
