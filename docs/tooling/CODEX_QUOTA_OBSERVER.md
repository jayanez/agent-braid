# Codex native quota acquisition — 2026-10-12

Status: an additive preparation component implemented on top of the owner-approved
[source contract](CODEX_SOURCE_CONTRACT.md), dependent on PR #504. It acquires
account-level metadata through the native app-server. It does not complete the
operational observer, native discovery, a skill journey or registration approval.
Independent review of this adapter is required before its first live use.

## Source and acquisition boundary

`agent_braid/tooling_codex_observer.py` exposes `CodexQuotaObserver.read()` and an
immutable `CodexQuotaSample`. Importing the module performs no acquisition.
Construction requires the operator's independently frozen account namespace
SHA-256. A read additionally requires `serialized_read_only=True`; this records
the caller's explicit serialization assertion, not an independent scheduling
attestation. The instance lock refuses overlapping reads on that instance.
Cross-instance, cross-process and cross-host serialization remain the caller's
responsibility. Follow the existing Codex-then-Claude preparation order.

The adapter loads the private reviewed transport only after checking its exact
SHA-256, regular-file status, owner, private permissions and bounded size. The
transport is not redistributed or copied into the public tree. Its immutable
source pin is `6464c0bc4fd2c000b5337c62c27fbcfbbe90df5e254106b964d5d8581365db1f`.
The fixed native executable pin is
`0d5ac7aae20c4eda6242428d5e218c55ba96d8763fda2a271088ff37104b9d28`.
No parameter permits replacing those pins. The operator's private archive and
repeat reference supply the transport path. Missing or changed bytes refuse;
there is no download, discovery fallback, credential refresh or alternate binary.

Source files and the installed executable are trusted local inputs. Final-component
symlinks are refused; ancestor directories and the installation must remain trusted
and stable during acquisition. The prelaunch executable digest check does not
establish race-free OS code identity or independent process attestation. This
adapter does not provide a signing, installer or OS isolation guarantee.

The adapter owns a new native app-server process group, uses stdio RPC, suppresses
stderr, closes its transport and terminates/reaps the process on success or failure.
It inherits a small environment allowlist, refuses a custom HOME or CODEX_HOME and
does not manually read credentials. Existing default native authentication and
configuration still belong to the executable. Filtering the environment does not
prove that its stored configuration or launched evaluation route excludes helpers,
API credentials, provider overrides or fallback.

The only requests are:

1. `initialize` with the adapter's client identity and experimental capability;
2. `initialized` notification;
3. `account/read` with `refreshToken=false`;
4. `account/rateLimits/read` with `supportsLunaReserve=false` and
   `excludeResetCreditDetails=true`.

No model prompt, thread or turn request is issued. The reviewed transport bounds
each request to 20 seconds and buffers at most 2 MiB. There is no retry. Acquisition
may therefore take approximately 60 seconds plus process cleanup; it cannot serve
as the supervisor's bounded dispatch-time check. A future reviewed cached producer
and consumer would need freshness, invalidation and process-binding controls.

The official [account protocol source](https://github.com/openai/codex/blob/main/codex-rs/app-server-protocol/src/protocol/v2/account.rs)
was consulted through Context7 on 2026-10-12. Implementation compatibility remains
bound to the archived collector and installed binary pins, rather than an unpinned
latest protocol. Protocol or source changes require focused review and new pins.

## Projection and refusal

The account must explicitly be native `chatgpt` with `requiresOpenaiAuth=true`.
Routing/account namespace values must not conflict; account and quota namespaces
must agree exactly and hash to the operator's frozen namespace. Raw identifiers,
emails, balances, monetary counters, provider bodies and credentials are not
returned, printed or written by this adapter. Raw responses exist transiently in
memory as part of the reviewed transport. Exceptions crossing the acquisition API
use a generic redacted message.

The sample projects only `ordinaryUsageAllowed`, `spendControlReached`,
`credits.hasCredits` and `credits.unlimited` as exact booleans or `None`.
Absent, null or non-boolean values remain unknown. Observed unsafe flags remain
unsafe; they are not admission. Account plan tags are not used to infer active
entitlement. The observation timestamp conservatively precedes the account read;
completion must be earlier than its expiry, with a maximum age of 60 seconds.
Clock regression and expiry refuse. Consumers must recheck freshness at use time.

The returned account digest, namespace digest and source/build pins are provenance
metadata, not proof of independent source authentication. The app-server producer
is separate from the future registered evaluation process. No registered PID,
process birth, candidate, slot or launched-route identity is inferred from it.

## Validation, trace and remaining work

Eleven focused synthetic tests cover namespace drift/conflicts, unavailable auth,
unknown and unsafe controls, expiry/clock regression, file/pin refusal, environment
filtering, exact read-only calls, explicit serialization, exception redaction and
process-group cleanup including kill escalation. The real pinned private transport
also loaded successfully offline without starting a native process or RPC. The
20-file private archive integrity check passed. No fresh live API read was performed
for this increment, and no new receipt or current quota claim was obtained.
Candidate-wide quick/PR validation results are recorded against the final commit
in its companion PR and the linked GitHub task updates, including actual skips.

| Obligation | Contribution | Still required |
| --- | --- | --- |
| SPEC-044/T001, REQ-001/SC-001 | Reusable quota acquisition component and explicit provenance limits | Full frozen registration, sources, review and specific owner approval |
| SPEC-044/T002, REQ-002/SC-002 | Account-level source preparation | Reviewed live sources, registered-process binding and bounded supervisor admission before exact native discovery |
| SPEC-041/T001, REQ-001/SC-001 | Removes part of the source-acquisition implementation gap | Actual five-skill host discovery/load evidence and its required registration/admission |

Auto-recharge-to-native account correspondence, a fresh authoritative recharge
control, authentic registered-process/configuration/argv observation, credential
and fallback isolation, bounded supervisor integration, independent adapter/source
review and current live evidence remain open. Passing synthetic tests cannot close
these obligations or establish EUR 0 actual cash reconciliation.

This is a new preparation API, not a source-receipt schema revision. There is no
automatic conversion to `agent-braid-codex-source-receipt-v1`, no v3 payment-flag
synthesis and no new runtime admission path. Existing v1/v2/v3, registration
schemas, shared supervisor code and historical assurance/evidence remain unchanged.
Original native tasks and milestone #19 remain open. Human evaluation and founder
acceptance remain separate gates.
