# Proposed external-effect boundary

Status: abstract synthetic assessment, no provider adapter.
Each attempt names its own ID, operation ID and idempotency key. Preserve duplicate
delivery as distinct attempts; duplicate attempt IDs are malformed. An idempotency
key alone does not guarantee provider deduplication. Retain visible effects even
on failure-after-effect, and keep ambiguous timeout unresolved regardless of
whether a visible effect was recorded. Do not resend automatically. Compensation
requires a different operation and recovery contract; it is not an exact inverse.

The bounded simulator accepts only opaque synthetic IDs, four closed outcome
values and explicit boolean effect observations. It does not interpret credentials,
URLs, arguments, code, arbitrary events or private payloads. Inconsistent outcome
and effect fields reject before producing a success result. No provider, network,
model, command or grant dispatch exists on this path.
