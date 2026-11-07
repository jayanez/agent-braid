# Contract: trace consent

Schema: `schemas/0.3.0-experimental/lightning-trace-consent.schema.json`
(identifier `braid-lightning-trace-consent/v0.1`; created by the lead).

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
previews and offers purge of existing content.

## Redaction placeholders

| Class | Placeholder |
|---|---|
| literal known secret | `[REDACTED:secret]` |
| API key or token pattern | `[REDACTED:token]` |
| bearer/OAuth header | `[REDACTED:bearer]` |
| private key block | `[REDACTED:private-key]` |
| email | `[REDACTED:email:<8-hex>]` (per-run salted hash, OD-2) |
| home path | `~` prefix replacement |

A record is stored only if the post-redaction scan is clean; otherwise it is
refused with `redaction-incomplete` and only a content-free stub is kept.

## Retention and purge

Sweep at every store open and on `agent-braid lightning sweep`; purge by
`agent-braid lightning purge [--run <id>] --apply --preview-digest <d>`. Purge
deletes content files and rewrites indexes without content; it never touches
host transcripts, Loom or System One files.

Refusal reasons: `content-consent-required`, `redaction-incomplete`,
`source-not-consented`, `retention-out-of-range`, `preview-stale`.
