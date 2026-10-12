# Claude Code source diagnostic — 2026-10-12

Status: owner-authorized read-only preparation batch for the Claude Code source
observer. **Outcome: the required sources are not yet verifiable, so no observer
component was implemented.** This record states which values were observed,
which remain unknown, and the exact field, method and condition still missing.

It depends on the Codex source composition contract proposed in
[PR #504](https://github.com/jayanez/agent-braid/pull/504) and does not modify it.
It is not registration approval, capture authorization, native acceptance or
evaluation evidence. No observer, launch, journey, registered reproduction or
any of the 108 intended attempts was started. No new provider request was made:
the diagnostic reused two existing private receipts produced by the unchanged,
previously reviewed collector, the private integrity-checked archive, local
configuration metadata and static inspection of the pinned isolated native
Claude Code 2.1.287 arm64 build. Additional spend: EUR 0.

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

The isolated configuration directory was identified from the owner-authorized
native login receipts of 2026-10-09. It is the directory that a registered
launch would pass as `CLAUDE_CONFIG_DIR`, and it still has to be registered
explicitly.

**Not yet done:**
- **The read.** The single live read must be started by the owner from a
  plain terminal. No new provider request has been made.
- **Credential refresh.** The stored credential from 2026-10-09 is likely
  expired. The collector never refreshes, so a refresh would need separate
  owner authorization.

The launch path must still guarantee:
- empty `--setting-sources` and the pinned `--settings` file;
- the child environment allowlist;
- no environment or key helper from policy settings;
- a canonical configuration path.

No observer, launch or evaluation attempt occurred. Additional spend remains
EUR 0.
