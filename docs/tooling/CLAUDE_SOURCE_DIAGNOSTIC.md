# Claude Code source diagnostic — 2026-10-12

Status: owner-authorized read-only preparation batch for the Claude Code source
observer. **Outcome: the required sources are not yet verifiable, so no observer
component was implemented.** This record states which values were observed,
which remain unknown, and the exact field, method and condition still missing.

It depends on the Codex source composition contract proposed in
[PR #504](https://github.com/jayanez/agent-braid/pull/504) and does not modify it.
It is not registration approval, capture authorization, native acceptance or
evaluation evidence. No observer, launch, journey, registered reproduction or
any of the 108 intended attempts was started. The original diagnostic made no
new provider request: it reused two existing private receipts produced by the
unchanged, previously reviewed collector, the private integrity-checked archive, local
configuration metadata and static inspection of the pinned isolated native
Claude Code 2.1.287 arm64 build. Additional spend: EUR 0. A later owner-run,
metadata-only read is recorded at the end of this document.

## Source matrix

"Process binding" means a value that can be verified to apply to the process a
future registered launch would start. Identity comparisons used private SHA-256
digests; identifiers and digests stay in the owner's private evidence.

| Field | Observed | Unknown | Process binding |
| --- | --- | --- | --- |
| Account and organization | Profile reads at 2026-10-11T22:26:59Z and 2026-10-12T10:54:31Z returned the same account and organization; the prepaid read's organization namespace matched the profile in both runs. | — | Only for the default credential store: its cached `oauthAccount` account/organization and the current assistant session's organization/account environment variables match the profile. Not established for the isolated launch store (gap B). |
| Included quota | Usage read at 2026-10-12T10:54:32Z: five-hour window 0% used, seven-day window 94% used, resetting at 2026-10-12T20:00Z. | Present value; that observation has expired. | None; point-in-time metadata. |
| Extra usage | `false` in profile and usage reads in both runs; the default store's cached flag is also `false`. | — | Default store only. |
| Auto-recharge | A main-session UI observation displayed automatic reload as off. | **Unknown.** Both prepaid reads returned HTTP 200 without a usable `auto_reload_settings.enabled` boolean. | None; the UI account was not bound to the native namespace. |
| Build | Isolated native 2.1.287 arm64 executable matches its pinned digest; required CLI flags are present. | Provider backend build. | Executable digest only. |
| Configuration | Default settings contain no API-key helper; the default API base host is first-party. | Effective configuration of the isolated launched process. | Pending host-adapter pins; not executed. |
| Credentials and fallback | The default store has no stored API key or key helper. | Existence and account of the isolated store's OAuth credential. | Not observed. |

HTTP 200, absence, `null` or a zero balance were not interpreted as `false`.

## Gap A — authoritative auto-recharge source

- **Field:** `auto_reload_settings.enabled` (boolean) from
  `GET /api/oauth/organizations/{org}/prepaid/credits`, together with the JSON
  type of `amount`.
- **Method:** the reviewed OAuth metadata collector (serial profile, usage and
  prepaid GETs with existing authentication, no refresh).
- **Missing condition:** two HTTP 200 reads produced no retained boolean. The
  reviewed projection collapses an absent key, `null`, a non-boolean value and a
  native "not supported" response into `unknown_or_missing`, so repeating the
  unchanged collector cannot resolve the value.
- **Static source facts (2.1.287):** the native client treats a prepaid response
  whose `amount` is not a number as "not supported". Its usage view displays
  automatic reload as on only when `auto_reload_settings.enabled === true`, so
  the native UI renders an absent value as off; that display is not admissible
  evidence of `false`. The only other auto-reload route in the build is a write
  (`PUT …/contracts/auto_reload_settings`) and is forbidden.
- **Minimal action:** a shape-only collector revision that records the JSON type
  of `amount` and the presence/type of `auto_reload_settings` and its `enabled`
  field (never values), a specific review of that revision, and one serial read
  into a new private directory. If `amount` is not numeric, the OAuth routes
  provide no authoritative auto-recharge source and the owner must decide which
  source, if any, is admissible.

## Gap B — account, organization and process correspondence

- **Field:** account and organization of the credential store the launched
  process will actually use.
- **Static source facts (2.1.287):** the native client resolves the organization
  from `CLAUDE_CODE_ORGANIZATION_UUID`, then from `oauthAccount.organizationUuid`
  in the configuration directory's `.claude.json`, then from a profile fetch.
  `agent_braid.tooling_hosts` requires an explicit isolated `CLAUDE_CONFIG_DIR`
  and excludes the organization variable from the child environment. A
  non-default configuration directory selects a different, suffixed Keychain
  item and a different `.claude.json`.
- **Missing condition:** the reviewed collector deliberately refuses
  `CLAUDE_CONFIG_DIR` and reads only the default store. Its account/organization
  therefore binds to the default store, not to the isolated launch store, whose
  authentication state is unknown. The UI account is also unbound.
- **Minimal action:** a reviewed observer mode for the exact isolated
  configuration directory that compares its `oauthAccount` digests with a
  profile read through that same store, or an owner decision on how that store
  is authenticated without a new ad-hoc login or credential copying. No shared
  module change is required for this step.

## Proposed coordinated batch

1. Shape-only Claude collector revision for gap A, with its specific review.
2. Isolated-store observer mode for gap B, with its specific review.
3. Only after both sources verify: the first authentic Claude source observer,
   with negative controls for an unverifiable source, unknown state, expiry and
   account/process mismatch, composed with the separately versioned source
   contract after PR #504 is integrated.

Observer receipts, OP001–OP006, SPEC-044 T001/T002 and SPEC-041 remain pending
their original evidence. Required reviews, the complete registration approval,
cash reconciliation and human gates are unchanged.

## Follow-up — 2026-10-13

Steps 1 and 2 above were prepared as private collector revisions. Their
sources, receipts and digests stay in the owner's private evidence and are not
published.

- **Gap A revision.** For a successful prepaid response, the receipt records
  only JSON type labels for the body, `amount`, `auto_reload_settings` and its
  `enabled` field, plus whether the native client would treat the route as
  supported. It records no values. Admission semantics are unchanged: only an
  exact boolean counts as an observed control.
- **Gap B revision.** An explicit mode reads the credential store that a
  process launched with a given isolated `CLAUDE_CONFIG_DIR` would use: the
  directory-specific Keychain item, without refresh, and that directory's
  global configuration. It then binds the stored account and organization to a
  profile read (`bound`, `mismatch`, `unknown` or `credential_unavailable`
  with a fixed reason). It refuses before any credential access when the
  directory is not canonical, when a plaintext credential file is present, or
  when the configuration supplies environment overrides or an API-key helper.
  Prepaid is read only when bound.

At the owner's request, the required independent reviews ran in Claude Code
instead of the earlier Codex reviewer, using the most capable available model
at high reasoning effort.
- Gap A was approved in one round.
- Gap B was approved after two rounds of requested changes. One finding was a
  credential-source gap: the native client applies the global configuration's
  `env` block to the process environment.
- During the final review, the reviewer ran a mocked negative probe that
  invoked the Security CLI eleven times against synthetic, nonexistent
  Keychain items. This broke the review's rules. The reviewer reported that no
  real item was read. The offline tests now block any real Security CLI or
  network call.
- These reviews are model reviews, not provider or runtime attestation.

The isolated configuration directory first identified from the 2026-10-09
login receipts no longer held its credential. The owner therefore created a
stable owner-private directory outside the repository and logged in there
natively. Registering that directory as the launch `CLAUDE_CONFIG_DIR` is a
coordination item for a later batch.

## Result of the isolated-store read — 2026-10-13

One owner-run read used the approved collector, with no retry, refresh or
inference request.

| Gap | Result |
| --- | --- |
| B — account/organization ↔ process store | **Resolved, point in time.** The stored account and organization of the isolated store match a profile read made with the same credential (`bound`). Extra usage was `false` in the profile and usage reads. |
| A — auto-recharge | **Still unknown.** The prepaid route is supported (numeric `amount`) but reports `auto_reload_settings` as `null` with no `enabled` field. A null settings object is not a boolean and is not treated as `false`. |

The B binding does not attest the launched process environment, policy
settings or freshness at dispatch; the launch-path guarantees below remain.

**Owner decision (2026-10-13, in chat):** the admissible auto-recharge source
for Claude is a fresh, explicit observation of the setting in the claude.ai
usage interface, bound to the same account. This records the choice of source;
it does not yet change a versioned contract. Open design points:
- The collectors discard email addresses, so the binding method between the
  interface account and the API profile account needs its own reviewed
  definition (for example a private identity comparison at observation time).
- Each admission needs a fresh observation; an earlier interface observation
  is not reusable evidence.
- The observer cannot be implemented until that method and the contract change
  are specified and reviewed.

The launch path must still guarantee:
- empty `--setting-sources` and the pinned `--settings` file;
- the child environment allowlist;
- no environment or key helper from policy settings;
- a canonical configuration path.

No observer, launch or evaluation attempt occurred. Additional spend remains
EUR 0.

## Interface account binding — 2026-10-13

The OAuth prepaid route cannot supply auto-recharge, so the owner-selected source
is a claude.ai interface observation. A method links that observation to the
account of a specific collector receipt without retaining any email.

**Method (private, not published).**
- An owner-private random key file produces a keyed HMAC of the canonical account
  email. The collector can add it, with a short key fingerprint, to the profile
  receipt. The email and other profile values are never retained. Without the key
  file the collector behaves as before.
- A separate recorder is not an observer and reads neither the interface, the
  Keychain nor the network. The caller supplies the state it saw, the time it saw
  it, and the displayed account email on standard input. The recorder compares the
  email's HMAC with the profile of one named receipt and writes `autoRechargeEnabled`
  only when the account matches. The receipt must be the expected schema, have
  exactly one successful profile read, and record its isolated store as bound.
  The observation time must be consistent with the profile read within a bounded
  window. Otherwise the value is null. The output carries the receipt digest and
  contains no email or HMAC.

**Review.** The independent reviews again ran in Claude Code (most capable model,
high effort) at the owner's request. Round one found two blocking issues: the
record was not tied to a specific receipt, and it presented the recorder's clock as
the interface observation time. Both were fixed with the non-blocking items, and
round two approved. Several non-blocking hardening items were deliberately left
unapplied to keep the approved bytes, and the model reviews are not provider or
runtime attestation.

**Interface findings.** In the signed-in interface the auto-recharge line is on the
usage settings page, which shows no email. The account email appears only in the
sidebar account menu. An observation therefore needs both surfaces read within the
window.

**Result.** One owner-run collector read, followed within seconds by the interface
reading, bound the displayed account to the isolated store's profile. The interface
showed automatic reload as disabled, and the recorder returned `autoRechargeEnabled =
false` with `accountBoundObservation = true`. The isolated store was again `bound`
and extra usage was `false`.

**Limits.**
- The state, its time and the displayed email are caller-asserted.
- The organization shown in the interface is not bound; a multi-organization
  account could display another organization's setting.
- The result holds at its observation time and does not attest the launched process.
- The collector receipt is not authenticated beyond its recorded digest, so any
  consumer must check that digest and the adapter digest against reviewed values.
- Every admission needs a fresh pair of reads.

**Still pending before an observer can exist:** a versioned contract that accepts
this observation as the auto-recharge source, registration of the isolated
configuration directory in the launch path with its expected Keychain item suffix,
and a decision on how each admission refreshes the interface observation. No observer,
launch or evaluation attempt occurred. Additional spend remains EUR 0.
