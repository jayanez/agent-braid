# Claude source composition contract — proposal

Status: **proposal, 2026-10-13. Not approved, not implemented.** It needs the owner's
explicit approval of the contract and of its implementation, as the Codex contract
received in [PR #504](https://github.com/jayanez/agent-braid/pull/504), and it
depends on that pull request. It is not registration approval, capture
authorization, native acceptance or an observer. Additional spend stays EUR 0.

It builds on the results in the [Claude source diagnostic](CLAUDE_SOURCE_DIAGNOSTIC.md):
the isolated-store binding (gap B) and the interface account binding for
auto-recharge (gap A, owner-selected source).

## Purpose and boundary

Compose three source claims for a Claude Code launch — included quota with extra
usage, auto-recharge, and process route — into one checked, expiring result, in the
same way the Codex contract does. As there, the composition checks the **claims**;
it does not authenticate the sources, and its result cannot be passed as an
operational observation or used as a launch permit. Authentication of each receipt
against its pinned procedure remains the trusted observer's work.

## Versions and scope

Proposed names: `agent-braid-claude-source-contract-v1` and
`agent-braid-claude-source-receipt-v1`, in a new module
`agent_braid/tooling_claude_sources.py` with its own tests and documentation. They
are additive and leave unchanged subscription policy v1, native process policy v2,
operational policy v3, registration v1/v2/v5, the Codex contract and every
historical record. The existing operational binding shape is reused for identity
only (account, namespace, build, executable, configuration, argv, candidate, model,
observer, slot) with host `claude-code`; the existing structural check accepts that
host and authentication method `claude.ai`. Using it asserts no v3 payment
predicate. The module would duplicate the roughly 25 lines of canonical-JSON and
shape helpers instead of importing private helpers from the Codex module; a shared
helper is a later, coordinated change.

## Frozen contract

Exactly: `schema`, `binding`, `additionalSpendCapEur` (integer zero),
`isolatedStore`, `sourceMaxAgeSeconds` and `sources`.

- `isolatedStore.keychainSuffix`: the eight-hex suffix of the credential item that a
  process launched with the registered isolated configuration directory uses. It
  freezes the store without publishing a path.
- `sources`: `quota`, `autoRecharge`, `process`, each with the same four pin fields
  as the Codex contract (source and verifier reference and SHA-256). Pins identify
  procedures, not responses.
- `sourceMaxAgeSeconds`: one limit per source. `quota` and `process` must not exceed
  the binding limit (at most 60 s). `autoRecharge` may declare a longer limit, capped
  at a proposed 900 s, because an interface observation is slower to refresh. This
  needs the owner's decision (see below).

## Receipts

Each receipt has the Codex receipt fields (`schema`, `kind`, `contractSha256`,
`binding`, the four pins, `phase`, `processId`, `processBirthSha256`,
`observedSequence`, `observedAt`, `payload`) and the same rules: identical phase,
PID/birth and sequence across all three; timezone-aware, not future, within each
source's own limit; each source judged individually; the result expires with the
earliest receipt; missing, extra, conflicting, non-boolean, stale or differently
bound fields refuse composition.

| Source | Payload and required values |
| --- | --- |
| `quota` | `extraUsageEnabled: false`; `quotaWindows` with `fiveHour` and `sevenDay`, each a finite `usedPct` below 100 and a reset time in the future. |
| `autoRecharge` | `autoRechargeEnabled: false`; `basis: "interface-observation"`; `accountBound: true`; `organizationBinding` in {`bound`, `owner-declared-single-organization`}; `uiObservedAt`; `collectorReceiptSha256`; `recorderRecordSha256`. |
| `process` | the Codex process flags (`quotaBoundaryActive`, `noProviderOperationBeforeBind`, `observerConnected` true; `apiCredentialAvailable`, `helperCredentialAvailable`, `providerOverrideAvailable`, `fallbackAvailable` false); `authMethod: "claude.ai"`; `route: "included-subscription-quota"`; `storeBinding: "bound"`; `keychainSuffix` equal to the frozen one; `collectorReceiptSha256`; launch guarantees `settingSourcesEmpty`, `pinnedSettingsOnly`, `childEnvAllowlistOnly`, `canonicalConfigDir` true and `policySettingsCanInjectCredentials` false. |

Cross-source rules:
- The `process` and `autoRecharge` payloads must carry the same
  `collectorReceiptSha256`, so both refer to one profile read.
- `uiObservedAt` must not be later than the `autoRecharge` receipt time and must lie
  within 600 s of that profile read.
- `organizationBinding` of `owner-declared-single-organization` is accepted only when
  the frozen registration carries the owner's declaration (see below); `unbound` or
  absent refuses.
- A null or absent auto-reload field in the API never substitutes for the interface
  basis, and no field is inferred from absence, a zero balance or HTTP 200.

The claims keep their native meaning. Quota and extra usage come from the OAuth
usage and profile reads. Auto-recharge comes only from the interface observation
bound to the account. None of them attests account-wide API billing or actual cash.

## Decisions requested from the owner

1. **Organization scope.** The interface does not show which organization a setting
   belongs to, so the account binding cannot cover it. Options: (a) accept only
   `owner-declared-single-organization`, recorded in the registration, with the
   declaration's limits stated; (b) require a future organization-binding method
   before accepting any interface observation. Recommendation: (a). The API profile exposes a single
   organization, so multi-organization membership cannot be detected from it and
   remains the owner's declaration.
2. **Freshness of the interface source.** Reading claude.ai before every one of the
   108 attempts is costly. Options: (a) one limit for all sources (at most 60 s);
   (b) a longer `autoRecharge` limit (proposed at most 900 s) while quota, extra
   usage and process stay at 60 s and are re-read by the supervisor. Recommendation:
   (b), with the longer limit stated per registration.
3. **Isolated store registration.** The directory stays caller-selected; the contract
   freezes only its credential-item suffix. Registering and canonicalizing the path in
   the launch path is a separate proposal for the shared host module and is not
   part of this one.

## Controls the implementation would carry

Synthetic deterministic controls, not provider evidence: safe composition; strict
boolean and missing-field refusal; per-source freshness and the earliest-expiry rule;
source and verifier pin drift; binding drift (account, namespace, candidate,
configuration, model, host); process conflicts; frozen-contract mutation; unverifiable
or unknown source; `null` auto-reload without an interface basis; `accountBound` false
or absent; unbound or undeclared organization; mismatching or absent collector receipt
digest between sources; store suffix mismatch; each launch guarantee false;
`uiObservedAt` outside its window; rejection by the existing v3 admission checker.

## Not covered

No token is acquired, no host started, no prompt sent and no setting changed. The
module authenticates nothing and enables no launch path. Authentic acquisition and
independent verification of each source, the trusted observer's integration with the
supervisor, the shared host-module change for the isolated directory, refresh of the
interface observation at each admission, and any registration route stay in separate
reviewed batches. Pending SPEC-041, SPEC-044 T001/T002 and OP001–OP006 evidence is
unchanged.
