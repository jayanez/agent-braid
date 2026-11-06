# SPEC-069: Compatibility notes for phase P1 (REQ-009, D8)

Baseline: plugin `0.1.0-alpha.7`, runtime source commit `0eb75d84`
(`agent-braid--v0.1.0-alpha.7`). Evidence:
[`evidence/alpha7-replay.json`](evidence/alpha7-replay.json), checked by
`tests/test_spec069_alpha7_replay.py`.

## Accepted requests

Every aim request that alpha.7 accepted (103 of the 317 recorded: example files,
workloads, the T010 successful call and the accepted corpus cases) is still
accepted, and its report is identical to alpha.7's once the T015 label is removed
and `analysisId` is recomputed. Requests that alpha.7 did not accept are still not
accepted. No runtime acceptance changed (D8: no runtime tightening in this feature).

Differences a caller can observe:

| Change | Effect | Version |
|---|---|---|
| Refusal text of `analyze-work` | The alpha.7 reason leads; ` at <JSON Pointer>; expected <form>` or ` [code]` follows. Unknown request keys appear as `<key:digest8>`. | none; messages are not a versioned contract |
| Missing repository or worktree path | Same refusal as a path outside the roots (was `unknown` for a missing path) | none |
| Git `operations` that is not a list | Refused (was an internal error) | none |
| `completenessBasis: declared-not-observed` on declared-only `independent-candidate` pairs | Additive optional property; `analysisId` changes because it digests the whole report | analysis report stays `0.1.0-alpha`; the schema gains an optional property (T015) |

## Schema notes (tightening without a new version, D8)

The published schemas now state, with `pattern: "\S"`, what the runtime already
refused as blank. No request that the runtime accepts is refused by the schema, so
no AIM or request version changes. Tightened keywords:

AIM record, `schemas/0.2.0-draft/agent-interaction-metadata.schema.json`:

- `/properties/instanceId/pattern`
- `/properties/attemptId/pattern`
- `/properties/definition/properties/id/pattern`
- `/properties/readVersions/propertyNames`
- `/properties/effects/properties/declared/items/properties/resource/pattern`
- `/properties/effects/properties/inferred/items/properties/resource/pattern`
- `/properties/effects/properties/observed/items/properties/resource/pattern`
- `/properties/effects/properties/coverage/properties/domain/pattern`
- `/properties/effects/properties/coverage/properties/method/pattern`

Git request, `schemas/0.1.0-alpha/git-analysis-request.schema.json`:

- `/properties/repository/pattern`
- `/properties/baseRevision/pattern`
- `/properties/operations/items/properties/instanceId/pattern`
- `/properties/operations/items/properties/attemptId/pattern`
- `/properties/operations/items/properties/source/oneOf/0/properties/revision/pattern`

New schema: `schemas/0.1.0-alpha/analysis-input.schema.json` (envelope, single
record, nonempty array); it describes what the runtime already accepts.

## Runtime-only differences kept for the next AIM version (D8)

The runtime is looser than the schema here; tightening it would refuse requests
alpha.7 accepts, so it is not done:

- `evidence` items are not inspected beyond a nonempty array (the schema validates
  each item).
- The git adapter does not enforce `uniqueItems` on `uncertainPaths`.
- The 256-byte identifier bound does not apply to a single-record request.

Intentional non-structural checks that JSON Schema cannot express: unique
identifiers, known and acyclic dependencies, the 32-operation and 256-byte
adapter bounds, the 1 MiB input and depth 32 bounds, repository and worktree roots.

## Declared limits of the schema

- ECMAScript `\S` and Python `str.strip()` disagree on U+001C to U+001F, U+0085 and
  U+FEFF. Python validators match the runtime; ECMAScript validators may differ on
  those characters.
- Python `jsonschema` accepts a trailing newline after a digest (`$`); ECMAScript and
  the runtime refuse it.
- JSON `1.0` is an integer for the schema and a float for the runtime
  (`readVersions` values).

## Contract versions

`agent-braid-plugin/v0.2`, `agent-braid-tooling/v0.1`, AIM `0.2.0-draft`, analysis
input `0.1.0-alpha`, git request `0.1.0-alpha` and analysis report `0.1.0-alpha`
are unchanged. `tests/test_spec069_compatibility.py` fails if any changes without
this note.

## Rollback

Reinstall the previous plugin tag (`agent-braid--v0.1.0-alpha.7`). Phase P1 adds no
request kind, so no saved request becomes unusable; the `units` kind (P3, if it
runs) is not part of P1.
