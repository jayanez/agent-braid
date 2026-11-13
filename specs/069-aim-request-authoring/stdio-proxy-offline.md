# Offline product-boundary relay (partial T005)

`scripts/spec069_stdio_proxy.py` is an opt-in stdio relay, not a server. It launches the exact server
command following `--` and passes its stdin/stdout bytes through. For each connection, provide a
**new** receipt path in a private directory; the file is created exclusively with mode 0600.
For example, an offline MCP client may launch `python scripts/spec069_stdio_proxy.py --receipt
/private/path/connection.json -- <plugin-launcher> plugin serve ...`.

The native driver can opt in with `scripts/spec069_native_runs.py --record-mcp`. It stages the candidate
inside its disposable profile, wraps only that copy's launcher, and records one private receipt per
connection. Result evidence contains validated, path-free receipt hashes and allowlisted metadata,
aggregated by protocol version and request shape. With no connection, it records zero rather than
claiming success. Fake-host runs refuse this option so pipeline-only evidence cannot be mistaken for a
product-boundary observation. The wrapper and receipts are removed by normal profile teardown.

The receipt records the negotiated protocol version, byte length and SHA-256 of each complete raw
`tools/list` response line (including its newline), canonical sorted compact JSON hashes of the result
and the unique `analyze-work` definition, tool count, and only the object/array/other type of each
`analyze-work` request. It does **not** save raw messages, arguments, prompts, tool descriptions or
credentials. Hashes can still disclose equality or permit guessing of low-entropy content: keep receipts
private and review them before sharing. Child stderr is inherited, not captured or redacted by the relay;
the caller must protect it. A receipt is not a transcript and cannot reconstruct or independently audit
the bytes. Compare canonical definition hashes only for comparable builds and protocol versions; compare
raw-line hashes only when JSON-RPC IDs and serialization are also the same. A matching hash is not host
acceptance, model exposure, loading mode or request correctness.

This relay expects newline-delimited JSON-RPC, at most 1 MiB per line, 4,096 outstanding requests per direction, and 4,096 recorded
events; invalid, missing or duplicate `analyze-work` definitions, outstanding requests, subprocess errors,
truncation and limit violations mark the receipt incomplete. It does not aggregate paginated listings or
establish that all tools were listed; each `tools/list` response must contain exactly one `analyze-work`.
`complete: true` additionally requires a valid `initialize` request offering a date-shaped protocol version,
its correlated successful response with a date-shaped protocol version, and at least one successful
`tools/list` response containing that target definition, as well as
a clean child exit and no recorded errors. Empty stdin, a clean child exit before handshake, initialization
without a target listing, or a listing without initialization cannot produce a complete receipt. An
`analyze-work` call is not required to complete a schema/listing receipt. The driver can compare
`analyze-work` definition hashes across observed connections and count object/array/other request shapes.
It explicitly leaves model-side eager/deferred loading `unobserved`: the stdio relay does not capture API
requests. A host transcript showing a call or tool-search step is not a substitute for that observation.
Requests with IDs in both directions are tracked separately until the corresponding opposite-side response;
duplicate outstanding IDs in one direction, unsolicited or duplicate responses, invalid IDs, non-JSON numeric
constants, numbers outside finite float range, scalar `params` and ambiguous messages invalidate the receipt.
The same ID may be outstanding in both directions. A successful
`tools/call` receipt requires a matching response but does not assert that its analysis succeeded.
The caller must supervise the process and use a timeout: ordinary stdio backpressure can block a peer.
After client EOF the relay allows five seconds for server shutdown, then terminates its process group.
An abrupt kill can leave an empty or partial receipt, which must be rejected, not treated as success.
The relay does not detect detached descendants or guarantee cleanup after the server leader has already
exited; the enclosing driver must independently enforce and verify process cleanup.

`tests/test_spec069_stdio_proxy.py` exercises local process doubles and, when the pinned optional MCP
dependency is installed, the actual plugin server with a temporary registered workspace.
`tests/test_spec069_native_runs.py` exercises the driver wrapper against a local MCP process. None of
these tests connects a host or model. T005 remains open: run the instrumented driver with Claude Code,
Codex and OpenCode under the separate spend gate; verify acceptance, object requests, byte/definition
identity and loading mode (through an appropriate model-side observation); record the host and model
versions and limits. The independent human review of the ADR 0038 amendment remains separate.

**Spend gate:** neither the relay nor `spec069_native_runs.py` enforces a preventive EUR 25 limit.
Post-call usage, estimated prices, timeouts and turn limits cannot reliably bound a call already in flight,
unknown provider charges, exchange rates or concurrent usage. Do not start a paid probe unless a separately
verified, preventive per-pass control exists that covers all participating routes and worst-case in-flight
costs; otherwise this remains blocked. This offline slice changes no billing, permissions or quotas.
