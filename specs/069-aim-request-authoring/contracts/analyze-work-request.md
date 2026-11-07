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
| `definition.id` | `C` (reserved; no producer code has this identifier) |
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
its source root. The scope never contains the host path.

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

## Report label

When an interaction is `independent-candidate` and every evidence item of both
records has `method: declared`, the interaction carries
`completenessBasis: "declared-not-observed"`. It is absent otherwise (including
when either record has a non-declared evidence item). Classification, reasons,
constraints and evidence are unchanged. `analysisId` digests the whole report and
therefore includes the label.

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
`test_spec069_compatibility.py`, `test_spec069_divergence_inventory.py`.
