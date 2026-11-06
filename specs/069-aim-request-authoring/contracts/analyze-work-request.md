# `analyze-work` request contract (SPEC-069, phase P1)

**Status:** proposed with [ADR 0038](../../../docs/adr/0038-analyze-work-request-contract.md);
not accepted until the owner reviews both. Normative for the request forms
below; nothing here describes host behaviour (that is measured in P2).

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

## Compatibility and versions

Unchanged: `agent-braid-plugin/v0.2`, `agent-braid-tooling/v0.1`, AIM
`0.2.0-draft`, analysis input, git request and report `0.1.0-alpha`. Every aim
request alpha.7 accepts is accepted with an identical report modulo the label and
the recomputed digest (`evidence/alpha7-replay.json`). Schema tightening and
rollback: [compatibility.md](../compatibility.md).

## Tests that enforce this contract

`tests/test_spec069_differential.py`, `test_spec069_refusals.py`,
`test_spec069_declared_label.py`, `test_spec069_alpha7_replay.py`,
`test_spec069_compatibility.py`, `test_spec069_divergence_inventory.py`.
