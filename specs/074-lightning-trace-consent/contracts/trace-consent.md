# Contract: trace consent

Schema: the `traces` section of
`schemas/0.3.0-experimental/lightning-config.schema.json`
(`braid-lightning-config/v0.1`), extended by this specification. There is no
separate consent schema.

## Consent record (inside `lightning.json` `traces`)

| Field | Type | Default | Rule |
|---|---|---|---|
| `contentConsent` | enum `none`, `redacted` | `none` | no other value; invalid configuration reads as `none` |
| `sources` | unique subset of `rollout`, `host-transcript`, `loom`, `system-one` | `["rollout"]` | content read only from listed sources |
| `retentionDays` | integer 1–90 | 30 | sweep bound |
| `consentedAt` | `YYYY-MM-DD` or null | null | set by apply when consent becomes `redacted`; never answered |
| `consentPreviewDigest` | hex or null | null | `previewDigest` of the preview the owner applied; never answered |

`consentedAt` and `consentPreviewDigest` are optional in a stored profile (BL.0
profiles lack them) and read as null. With `none` both are null; with `redacted`
both are set. A re-apply that keeps `redacted` and the same sources keeps the
record; new sources renew it; lowering to `none` clears it. Consent does not
expire (OD-3). A record that breaks these rules, or an answer that tries to set
it, is refused with `config-consent` (added to the SPEC-070 configuration
refusal vocabulary).

## Setup preview

`agent-braid lightning init --trace-consent redacted [--trace-sources
rollout,host-transcript]` (`--trace-content` is the BL.0 spelling) prints a
`consent` summary (level, `consentedAt`, sources, retention, `expires: null`),
effects naming sources, retention, redaction classes, storage location, the
residual risk and the purge command, and a `previewDigest`; it
writes only with `--apply --preview-digest <d>`. Lowering consent to `none` also
previews and offers purge of existing content. Consent has no expiry (OD-3);
`agent-braid lightning status` reports `traceConsent` with the same summary
(`none` when no profile exists). `plugin setup` only sets `lightning` `off` |
`lab`; it never changes consent.

## Consent gate

The store reads `traces.contentConsent` from the profile when a content-bearing
record arrives; a missing, unreadable or invalid profile reads as `none`. A
caller may pass `none` explicitly, which overrides the profile; any other
explicit value is refused. Without `redacted` the record is refused with
`store-consent` and nothing is written. With `redacted` the record must first
pass redaction (C2); until the store wires `lightning_redact` with the run's
email salt and content retention (T006) it is refused with
`redaction-incomplete`. The adapter gate (`agent_braid/lightning_adapter.py`)
reports `content-consent-required` without consent and `source-not-consented`
for a source not in `traces.sources`; `agent-braid lightning status` reports it
as `traceContent` (`contentConsent`, `source`, `content`, `refusal`).

## Redaction placeholders

| Class | Placeholder |
|---|---|
| literal known secret | `[REDACTED:secret]` |
| API key or token pattern | `[REDACTED:token]` |
| bearer/OAuth header | `[REDACTED:bearer]` |
| private key block | `[REDACTED:private-key]` |
| email | `[REDACTED:email:<8-hex>]` (per-run salted hash, OD-2 decided) |
| home path | `~` prefix replacement |

A record is stored only if the post-redaction scan is clean; otherwise it is
refused with `redaction-incomplete` and only a content-free stub is kept.

## Retention and purge

Sweep at every store open and on `agent-braid lightning sweep`; purge by the
BL.0 `agent-braid lightning purge [--run <id>] --apply --preview-digest <d>`,
extended here to content records. Purge
deletes content files and the run's email salt (OD-2) and rewrites indexes
without content; it never touches
host transcripts, Loom or System One files.

Refusal reasons: `store-consent` (SPEC-070 store refusal of a content field
while consent is `none`), `content-consent-required` (the same condition as
reported by the adapter and CLI), `redaction-incomplete`,
`source-not-consented`, `retention-out-of-range`, `preview-stale`.
