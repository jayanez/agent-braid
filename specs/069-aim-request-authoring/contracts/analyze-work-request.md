# `analyze-work` request contract (SPEC-069, phase P1)

**Status:** accepted 2026-11-07 with [ADR 0038](../../../docs/adr/0038-analyze-work-request-contract.md)
by the owner. Normative for the request forms below; nothing here describes host
behaviour (that is measured in P2).

## Call

`analyze-work` takes exactly `kind` and `request` (the plugin adds `workspaceId`).
`kind` is `aim` or `git`. The kind `units` is **not part of this contract**: it is
designed in the specification and defined here only if phase P3 runs (D6).

## Request forms

| kind | form | schema (draft 2020-12) |
|---|---|---|
| `aim` | envelope `{analysisInputVersion: "0.1.0-alpha", source: {kind, description}, operations: [AIM record, ...]}` | `schemas/0.1.0-alpha/analysis-input.schema.json` |
| `aim` | a single AIM record | `schemas/0.2.0-draft/agent-interaction-metadata.schema.json` |
| `aim` | a nonempty array of AIM records | `analysis-input.schema.json` (`$defs/records`) |
| `git` | `{gitAnalysisRequestVersion: "0.1.0-alpha", repository, baseRevision, operations: [>= 2 operations]}` | `schemas/0.1.0-alpha/git-analysis-request.schema.json` |

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
  `cyclic-dependencies`.
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

## Delivery in the tool definition (phase P3, T005)

P3 runs (founder decision 2 of 2026-11-07), so REQ-005 delivery enters this contract.
This section was added by T005 after the owner's acceptance above; that acceptance does
not cover it, and it awaits review. The `analyze-work` `inputSchema` keeps a plain-object top level: `type`,
`additionalProperties`, `properties` (`kind`, `request`, and the plugin-injected
`workspaceId`), `required`, and one `$defs` table (A1). `properties.request` is
`{"type": ["object", "array"], "oneOf": [...]}` with one branch per request form above,
each labelled by a `description` `kind=<kind>[ <form>]`. The AIM record and its effect
item are declared once under the top-level `$defs` and referenced as `#/$defs/<name>`.

- **Source.** `scripts/spec069_tool_schemas.py` derives the branches from the published
  schemas: annotations stripped, references inside one file inlined, a reference to
  another published file shared through `$defs`, `minLength: 1` dropped where
  `pattern: "\S"` already implies it. It writes `agent_braid/analyze_work_schema.py`
  (with the SHA-256 of each source schema); a test regenerates it and compares bytes.
- **Equivalence.** On the committed corpus, each kind's branches and the whole call
  schema give the published schemas' verdicts (`DeclaredSchemaDifferentialTests`). The
  link between `kind` and the request form cannot be stated inside `request` without a
  top-level combinator, so a request of another kind's form passes the declared schema
  and is refused by the runtime with a structural refusal.
- **Validating hosts.** A host that validates arguments against the declared schema
  refuses, before calling, the runtime-looser classes listed above (for example an
  `evidence` item that is not an evidence object); the runtime still accepts them.
- **Size cap (D12).** Name, description and `inputSchema` of each listed tool, as compact
  UTF-8 JSON, stay within 1,500 tokens approximated as ceil(bytes / 3.7). A one-time
  calibration measured 4.09–4.23 bytes per token with `o200k_base` and `cl100k_base`, so
  the approximation over-counts them by about 10–14 %; Anthropic's tokenizer is not
  measured. Above the cap the test fails and the description-only fallback applies.
- **Ablation switch (D9).** `python -m scripts.spec069_tool_schemas --delivery
  description-only` rewrites the generated module so a build serves the interim
  definition (`request` declared as object or array with the prose description, byte
  identical to alpha.7 plus PR #1099); the tool description is the same in both arms.
  Only `per-kind` is committed. The arm is part of the built bytes, so it reaches every
  host the same way (no environment variable, which Codex does not forward to plugin MCP
  servers by default).
- **Not yet observed.** Whether each host accepts the nested form, the recording-proxy
  byte identity across host connections, eager or deferred schema loading, and the D9
  ablation result are pending on the native driver; adoption in a release waits for
  them (REQ-005). Hand-off: `reviews/t005-handoff-20261107.md`.

## Compatibility and versions

Unchanged: `agent-braid-plugin/v0.2`, `agent-braid-tooling/v0.1`, AIM
`0.2.0-draft`, analysis input, git request and report `0.1.0-alpha`. Every aim
request alpha.7 accepts is accepted with an identical report modulo the label and
the recomputed digest (`evidence/alpha7-replay.json`). Schema tightening and
rollback: [compatibility.md](../compatibility.md).

## Tests that enforce this contract

`tests/test_spec069_differential.py`, `test_spec069_refusals.py`,
`test_spec069_declared_label.py`, `test_spec069_alpha7_replay.py`,
`test_spec069_compatibility.py`, `test_spec069_divergence_inventory.py`,
`test_spec069_schema_delivery.py`.
