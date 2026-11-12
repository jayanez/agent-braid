# Offline product-boundary relay (partial T005)

`scripts/spec069_stdio_proxy.py` is an opt-in stdio relay, not a server or a host driver. It launches
the exact server command following `--` and passes its stdin/stdout bytes through. For each connection,
provide a **new** receipt path in a private directory; the file is created exclusively with mode 0600.
For example, an offline MCP client may launch `python scripts/spec069_stdio_proxy.py --receipt
/private/path/connection.json -- <plugin-launcher> plugin serve ...`. This is an interface for a future
driver integration, not a command to start a host or make a model call. No existing driver enables it.

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
`analyze-work` call is not required to complete a schema/listing receipt.
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
dependency is installed, the actual plugin server with a temporary registered workspace. Neither test
connects a host or model. T005 remains open: a future isolated native-driver integration must create a
separate receipt for every actual host connection, validate and compare them, observe object requests and
model-side eager/deferred loading, and preserve provenance. The independent human review of the ADR 0038
amendment remains separate.

**Spend gate:** neither the relay nor `spec069_native_runs.py` enforces a preventive EUR 25 limit.
Post-call usage, estimated prices, timeouts and turn limits cannot reliably bound a call already in flight,
unknown provider charges, exchange rates or concurrent usage. Do not start a paid probe unless a separately
verified, preventive per-pass control exists that covers all participating routes and worst-case in-flight
costs; otherwise this remains blocked. This offline slice changes no billing, permissions or quotas.
