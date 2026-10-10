# AI tooling evidence presentation

`agent_braid.tooling_present` formats an already available result envelope. It
does not read repository files, fetch evidence URIs, start a host, invoke a
provider, or dispatch runtime operations. Callers resolve owned evidence and
pass the complete typed value to these helpers.

```python
from agent_braid.tooling_present import (
    build_exports,
    build_graph,
    canonical_result_json,
    render_graph_ascii,
    render_summary,
    write_exports,
)

summary = render_summary(tooling_result)
graph = build_graph(tooling_result)
terminal_graph = render_graph_ascii(graph)
result_for_cli_parity = canonical_result_json(tooling_result)
```

The summary reports adapter status separately from domain status. An adapter
`ok` means a valid core result was returned; it does not mean an analysis found
independence, an execution finished, or a verifier established code correctness.
Unknown, conflicting, conditional, refused, cancelled, failed, and verified
states retain their distinct labels. An advisory order is explicitly described
as advice. The text does not promote structural analogy into a theorem or
execution authority.

The graph is derived only from explicit operation dependencies and interaction
classifications. It will not infer an independence edge. The plain terminal
renderer is ASCII-only, percent-encodes graph identifiers to prevent them from
impersonating edge syntax, and emits no ANSI color controls. SVG and HTML use fixed
offline templates, escaped labels, and text labels/styles that remain meaningful
without color. Malformed references, unknown classifications, excessive graph
size, artifact-reference-only results, and oversized JSON refuse with
`PresentationError`.

## Evidence exports

`build_exports` returns deterministic bytes for `summary.md`, `graph.svg`,
`index.html`, `evidence.json`, and `receipt.json`; it performs no writes. The
caller must explicitly select zero or more evidence reference IDs. Those IDs
must already be present in the envelope. The export views contain only a compact
summary and graph, not arbitrary result payloads. Their receipt says that the
complete envelope value is in `evidence.json` and binds it and each view with
SHA-256 digests. JSON is stable canonical serialization of the complete parsed
envelope; it preserves the value, not the original transport frame bytes.

`write_exports` performs the same explicit selection and writes to the exact
absolute destination supplied by the operator. The destination must be new;
its parent must already be a user-owned private directory. The export directory
is created with mode `0700` and files with mode `0600`. Existing destinations,
shared parent directories, malformed evidence, and collisions refuse without
overwriting. The absolute path is returned to the caller but is not written into
the exported views or receipt.

The raw evidence file may contain private paths or other sensitive fields. Keep
it in the protected export directory and share only the sanitized views when
appropriate. The helper never reads additional source content to complete an
export. A selected reference is a pointer only; callers must resolve it through
their already authorized owned-artifact interface before passing any additional
evidence into a future formatter.
