# C3 bounded stdio adapter

MCP 2025-11-25 stdio, implemented with the Python standard library and no new
runtime dependency. The server advertises only tools. Its six tools are analyze,
prepare, status, execute, recover and verify. No tool creates an operator grant.
The same verified policy and purpose-bound grant pipeline handles Python, CLI and
MCP dispatch. Annotations are hints, never execution authority.

Launch roots are operator configuration: one canonical source repository, one
canonical parent for direct-child private results and one owned grant store.
Requests outside those lexical scopes are refused before resolving arbitrary
caller-selected filesystem paths. Grant-store selection and grant bodies are not
tool arguments. The operation/attempt identities and full fixed plan survive the
transport. `status` and `verify` perform read-only combined consumer verification;
a missing private run reports no-private-run with dispatch history explicitly
unestablished. Read-only inspection neither issues nor consumes a grant.

Initialize negotiates the pinned revision and requires initialized notification.
Unknown methods/tools, malformed envelopes/parameters, duplicate JSON members,
nonfinite numbers, oversized frames and duplicate active IDs receive explicit
errors. Tool input validation and business/runtime failures use isError, following
the pinned tools contract. Notifications never receive responses. Discovery from
newer clients receives method-not-found so supported clients can fall back.

Frames and encoded responses are capped at 1 MiB. One tool operation is in flight.
A 360-second cancellation timer stops new phases and owned Git children. Existing
M2 verification may drain its bounded 120-second phase; there is no immediate
cancellation or shared hard deadline across independent phases. Cancellation,
disconnect and timeout cannot be reported as successful tool completion. A
completed private checkpoint can still exist after a lost response: inspect state
and use a fresh purpose-bound recovery grant. An overflow response also requires
inspection rather than implicit execution retry.

The tests use both an in-process protocol peer and actual stdio subprocesses with
owned Git fixtures. They cover lifecycle/version fallback, the exact tool list,
errors, bounds, cancellation/deadline, duplicate calls, root/store restrictions,
independent verification and disconnect after a controlled first checkpoint.
Those peers are not actual Codex/Claude evidence. Real-client records require a
clean frozen candidate and separate host captures.

Primary pinned error contract:
https://modelcontextprotocol.io/specification/2025-11-25/server/tools
