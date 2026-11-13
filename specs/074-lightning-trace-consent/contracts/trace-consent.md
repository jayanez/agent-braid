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
| `consentedAt` | date or null | null | set by apply when consent becomes `redacted` |
| `consentPreviewDigest` | hex or null | null | digest of the preview the owner applied |

## Setup preview

`agent-braid lightning init --trace-consent redacted` prints sources, retention,
redaction classes, storage location, purge command and a `previewDigest`; it
writes only with `--apply --preview-digest <d>`. Lowering consent to `none` also
previews and offers purge of existing content. `plugin setup` only sets
`lightning` `off` | `lab`; it never changes consent.

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
deletes content files and rewrites indexes without content; it never touches
host transcripts, Loom or System One files.

Refusal reasons: `store-consent` (SPEC-070 store refusal of a content field
while consent is `none`), `content-consent-required` (the same condition as
reported by the adapter and CLI), `redaction-incomplete`,
`source-not-consented`, `retention-out-of-range`, `preview-stale`.
