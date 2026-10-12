# Platform API verification reference — 2026-10-12

Status: owner-requested operational reference for SPEC-044. These are historical
preparation observations, obtained on 2026-10-11 UTC / 2026-10-12 Europe/Madrid.
They are not journey outcomes, present quota, a trusted runtime attestation or
approval of the complete registration.

## Recorded observations

| Provider read | Response time (UTC) | Observed metadata | Remaining uncertainty |
| --- | --- | --- | --- |
| Codex account/rate-limit read | 2026-10-11T22:16:24.775926Z | ChatGPT authentication, provider plan tag `prolite`; ordinary usage allowed; 10080-minute quota window 67% used; `credits.hasCredits=false`, `credits.unlimited=false`, `spendControlReached=false`. | Explicit `creditsEnabled`, `extraUsageEnabled` and `autoRechargeEnabled` fields were absent. Credit availability and account category do not establish payment settings. |
| Claude profile read | 2026-10-11T22:26:59.080995Z | HTTP 200; the reviewed `organization.has_extra_usage_enabled` field was false. | Point-in-time profile metadata does not prove future process identity or enforcement. |
| Claude usage read | 2026-10-11T22:26:59.471046Z | HTTP 200; the reviewed extra-usage boolean was false; five-hour quota 0% used; seven-day quota 93% used, resetting at 2026-10-12T20:00:00.350368Z. | Historical quota is not future available quota. |
| Claude prepaid-credit read | 2026-10-11T22:27:01.215593Z | HTTP 200; profile and prepaid organization identity hashes agreed. Monetary values were discarded. | No usable `auto_reload_settings.enabled` boolean was retained by the reviewed projection. Auto-reload remains unknown; successful HTTP status does not mean disabled. |

Remaining weekly percentages of 33% for Codex and 7% for Claude are arithmetic
derivations of the used percentages, not separately returned provider fields.
The Codex account/configuration/catalog reads also succeeded; the bounded catalog
contained seven entries, including the selected `gpt-6-luna` route. A catalog
entry is not an immutable backend build identity.

## How the observations were obtained

Codex used one bounded installed native app-server stdio session with existing
ChatGPT authentication. Its read-only RPC allowlist was `initialize`,
`initialized`, `account/read` with `refreshToken=false`,
`account/rateLimits/read` with `supportsLunaReserve=false` and
`excludeResetCreditDetails=true`, `config/read` with `includeLayers=false`,
and one `model/list` page with `limit=100`. Pagination remains explicit.
The collector checked the inspected executable digest before starting, stopped
on RPC errors and saved sanitized results in an exclusive private receipt.

Claude used a private personal direct HTTP diagnostic based on read operations
inspected in Claude Code 2.1.287 arm64. That source binding does not mean the
diagnostic launched or attested the native process. The reader obtained the
existing production-default macOS Keychain OAuth access token transiently in
memory, without refresh, storage, logging or a credential-file fallback.
It performed serial HTTPS GETs to `api.anthropic.com`:
`/api/oauth/profile`, `/api/oauth/usage`, then
`/api/oauth/organizations/{profileOrganizationUUID}/prepaid/credits` only after
a successful profile supplied a validated organization UUID. The prepaid read
used the same token with the profile-derived organization namespace and
source-bound version/platform headers. These are native-client internal routes,
not publicly documented subscription APIs.

Transport checks disabled proxies, redirects and TLS key logging, retained
default certificate/hostname verification, refused custom trust/storage/provider
contexts and an OS-account mismatch, and bounded response sizes. Receipts kept
response times, exact boolean controls, quota-window metadata and hashed
provenance. Missing, null, malformed and conflicting control values remain
unknown. Names/emails, raw identifiers and response bodies, credentials,
balances, spend and monthly credit counters were not persisted.

Codex collection finished before Claude collection began. The collectors sent
no model prompt or inference request, changed no account/payment setting and
purchased no credits. This claim is limited to the diagnostic collectors; it
does not describe inference used by the surrounding assistant/review chats.

## Evidence location and repeat procedure

The byte-exact receipts, collectors, route manifest, offline checks and Luna
Latest source/interpretation reviews are in the owner's private archive
`m45/2026-10-12-api-verification`. A separate private
`API_VERIFICATION_REFERENCE.private.md` records the exact local paths, receipt
and collector hashes, interpreter and repeat commands. The archive's 20 listed
files passed an offline SHA-256 integrity check. Private account/org hashes,
response fingerprints, receipt bodies and monetary inputs stay outside the
public repository. Keep the original archive unchanged and write each fresh
observation into a new private timestamped directory.

For subsequent verification, start with that reference and the reviewed
collectors. Reuse the read-only API method and existing native authentication;
do not reopen a generic source-selection or provider-support question. Support
contact is not the owner's selected verification route. Never substitute a
paid API/Admin key, purchase/enable credits, change settings, guess endpoints,
or send model prompts to obtain account/quota metadata.

Check the archived hashes and applicable build/authentication/transport context
before reuse. Stable reviewed methods do not need to be rediscovered. Source,
build or endpoint/authentication drift requires a focused update and review.
Absent/expired credentials or failed API reads require a precise blocker
record; the diagnostic does not refresh credentials or silently retry through
another route. Any genuinely necessary owner action should identify that
specific limitation.

Run fresh Codex reads first, wait for process exit, then run fresh Claude reads.
Preserve unknown payment controls, record actual response times and new receipt
hashes, compare source/account identities and controls, and apply the existing
freshness and drift requirements. New API reads were not performed to create
this reference.

## Conditions retained

This reference is subordinate to the
[operational subscription capture policy](operational-subscription-capture-policy.md)
and [evaluation protocol](evaluation-protocol.md). It does not waive EUR 0
additional-spend, the complete registration approval, slot/candidate/model/
host/account/configuration/argv binding, launch-process credential/fallback
isolation, a trusted bounded supervisor, cash reconciliation or human gates.
The personal metadata reader is separate from a future launched process's
no-helper-credential requirement.

The original snapshot is historical even when its collector is reusable.
Missing Codex payment settings and Claude auto-reload remain unresolved.
OP001–OP006 stay open until their paired acceptance evidence is inspected.
No registered reproduction or any of the 108 intended attempts was launched.
