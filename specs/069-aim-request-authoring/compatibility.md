# SPEC-069: Compatibility notes for phases P1 and P3 (REQ-009, D8)

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
| New `kind` `units` (P3, T006) | Additive: a request kind alpha.7 refused (`Unsupported analysis kind`) is now accepted; no `aim` or `git` verdict or report changes | new contract `units` request `0.1.0-alpha` (`schemas/0.1.0-alpha/units-request.schema.json`); the other versions below are unchanged |

## The `units` kind (phase P3)

`units` is part of the P3 request contract
([contract](contracts/analyze-work-request.md), section "Kind `units`"; REQ-006). It
has its own versioned schema and runtime (`agent_braid/units.py`) and returns the
constructed AIM request with the report, so a result can be replayed through `kind`
`aim` on any plugin that has the `aim` kind, including alpha.7. Adding it changes
nothing that alpha.7 accepted: the alpha.7 replay and the aim/git corpus are
unchanged (`evidence/procedure_006.json`). Its schema states only what its runtime
refuses, except the runtime-only checks listed in the contract (unique unit ids, known
and acyclic dependencies, case-only duplicate resources, the 256-byte identifier
bound).

## Release-note text: replacing the interim guidance of PR #1099

Proposed text for the plugin release that ships `units` (owner reviews; nothing is published here):

> `analyze-work` now accepts `kind` `units`. List units with an `id`, optional
> `dependencies` and `effects` of `{kind, resource}` where `resource` is a
> workspace-relative path; Agent Braid builds the AIM records, always records coverage as
> `partial`, and returns the report with the constructed AIM request, which can be sent
> again with `kind` `aim`. This supersedes the interim guidance of PR #1099, which described
> the AIM envelope in the tool description and gave a complete AIM example in the
> analyze skill because hosts had to guess the request shape; that guidance stays valid
> for `kind` `aim`, and `units` is the simpler path for simple requests. The `aim` and `git` kinds, their reports and `analysisId` are unchanged. A plugin before
> this release refuses a saved `units` request with `Unsupported analysis kind`; the
> constructed request still replays through `kind` `aim`. System One shadow episodes now
> use `analysisKind` `units` for these calls. Windows path semantics are tested for
> normalization only.

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
this note. New in P3: the `units` request `0.1.0-alpha`.

## Rollback

Reinstall the previous plugin tag (`agent-braid--v0.1.0-alpha.7`). The previous plugin
refuses a saved `units` request (`unitsRequestVersion` `0.1.0-alpha`) with a fixed
message naming the kind it does not support: `analyze-work refused: Unsupported
analysis kind` (observed on the alpha.7 runtime, source `0eb75d84`, 2026-11-07). A
saved `constructedRequest` from a `units` result is an ordinary `aim` envelope and
still replays through `kind` `aim` there. Saved `aim` and `git` requests are
unaffected.
