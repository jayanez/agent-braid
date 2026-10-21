# Owned-work compatibility disposition draft

Status: partial RF-T02 / proposed SPEC-045/T010 preparation. No ledger schema,
source admission, architectural adoption or completed migration is claimed.
The existing proposed task supplement remains the single backlog; this increment
does not register competing task IDs or mark RF-T01/RF-T02/RF-T10 completed.

`agent-braid-forecast-telemetry-v1` retains `authentic-on-synthetic`.
`forecast_data.validate_window` already supports permissioned windows through
an actual `source_verifier`; parsing or a lambda returning true is insufficient
evidence of source rights. The current forecasting API retains its synthetic
scope and no arbitrary repository/path input. SPEC-047 retains its closed
identity-free numeric aggregate contract, default-off consent and proposed ADR
0025. No implementation or historical assurance in those routes is changed.

The separate proposed `agent-braid-owned-work-evaluation/v1` ledger needs its
own reviewed contract, immutable prediction/outcome append rules, private bounded
store, retention/revocation, independent oracle and temporal/family split checks
before collection. Proposed lineage hashes are private identifiers, not anonymity.
Do not convert old synthetic receipts or aggregate SQLite into real-work records.
No projection is implemented; a future projection may use only existing allowed
numeric fields after route-specific consent/admission. Never export join IDs,
paths, content, source/model/policy digests or exact timestamps into SPEC-047.

The new `agent-braid-backlog-coverage/v1` research result is a metadata diagnostic,
not the proposed evaluation ledger or a System 1 decision. It grants no source
admission and returns no verified-supported cases. It therefore has no implicit
migration into forecasting, production telemetry, training data or runtime grants.
Original metadata provenance and every failed invocation must stay with the
authorized caller; the helper cannot enforce population completeness by itself.

The [coverage contract](../contracts/real-backlog-coverage.md) proposes distinct
draft identities for a future text-patch domain. Any adopted incompatible domain
or ledger revision needs new source/registry pins, explicit version dispatch and
cross-version refusal, separate tests and fresh evidence. Old receipts remain
bound to their old sources; no silent upgrade or historical gate closure follows.
