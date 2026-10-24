# SPEC-059 contracts (draft, not adopted)

Planning files only. Nothing here is implemented, frozen, signed or approved.

| File | Role |
|---|---|
| [coordination-contract.md](coordination-contract.md) | The drafted G2 contract (identity, concurrency, idempotency, recovery, delivery, privacy) for founder review. Adopts nothing. |
| [push-settings.schema.json](push-settings.schema.json) | The `extensions.SPEC-059` entry of the SPEC-057 `orchestration-settings` schema (push transports, kill switch) and the resolved delivery result. Extends SPEC-057 by reference; redefines no scope, mode or strategy. |
| [push-settings.example.json](push-settings.example.json), [push-settings-extension.example.json](push-settings-extension.example.json) | A whole settings record and a bare extension entry. An example is not evidence. |
| [push-resolution.example.json](push-resolution.example.json) | A valid resolved delivery: push requested, unavailable, effective delivery is the Mailbox. |
| [push-resolution-active-while-pull.invalid.json](push-resolution-active-while-pull.invalid.json) | Negative fixture: `pushStatus` `active` with effective mode `pull`. Must fail validation. |
| [transport-matrix.json](transport-matrix.json) | Documentation-level candidate transports by strategy, with gates and evidence status. None is selected; none is host-observed. |
| [interop-adapters.md](interop-adapters.md) | Interoperation, documentation only; adapters deferred until demand or G1 evidence. |

Notices are the SPEC-057 hazard notice and refusals are the SPEC-057 command-error shape; neither is copied here. The earlier ledger event, notice, error, recovery-view and attributed-write export schemas were removed in the sketch and are drafted only if G2 opens.

Composition check (planning aid, offline): the whole settings record validates against the SPEC-057 `orchestration-settings` schema, which stores the extension without interpreting it; the extension entry validates against `push-settings.schema.json`; the resolved delivery validates against `#/$defs/resolvedDelivery` and the invalid fixture does not. Text patterns end with `(?![\s\S])` so that a trailing line feed is rejected.
