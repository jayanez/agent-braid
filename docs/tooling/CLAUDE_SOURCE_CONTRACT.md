# Claude source composition contract

Status: implementation authorized by the owner on 2026-10-13. Literal decision:
“Autorizo el contrato y su implementación”. This is approval of the separately
versioned source contract and its implementation scope, which build on the Codex
contract integrated in [PR #504](https://github.com/jayanez/agent-braid/pull/504). It is
not registration approval, capture authorization, native acceptance, an observer or
adoption of ADR 0021. Additional spend stays EUR 0.

The three design decisions below were settled by the owner in chat on 2026-10-13. The
contract builds on the results in the [Claude source diagnostic](CLAUDE_SOURCE_DIAGNOSTIC.md):
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

`agent-braid-claude-source-contract-v1` and `agent-braid-claude-source-receipt-v1` are
implemented by `agent_braid.tooling_claude_sources`, with its own tests and this
documentation. They are additive and leave unchanged subscription policy v1, native process policy v2,
operational policy v3, registration v1/v2/v5, the Codex contract and every
historical record. The existing operational binding shape is reused for identity
only (account, namespace, build, executable, configuration, argv, candidate, model,
observer, slot) with host `claude-code`; the existing structural check accepts that
host and authentication method `claude.ai`. Using it asserts no v3 payment
predicate. The module duplicates the roughly 25 lines of canonical-JSON and shape helpers
instead of importing private helpers from the Codex module; a shared helper is a
later, coordinated change.

## Frozen contract

Exactly: `schema`, `binding`, `additionalSpendCapEur` (integer zero),
`isolatedStore`, `organizationScope`, `sourceMaxAgeSeconds` and `sources`.

- `isolatedStore.keychainSuffix`: the eight-hex suffix of the credential item that a
  process launched with the registered isolated configuration directory uses. It
  freezes the store without publishing a path.
- `organizationScope`: `binding` equal to `owner-declared-single-organization` and the
  SHA-256 of the owner's declaration text recorded in the registration. No other
  value is accepted in version 1.
- `sources`: `quota`, `autoRecharge`, `process`, each with the same four pin fields
  as the Codex contract (source and verifier reference and SHA-256). Pins identify
  procedures, not responses.
- `sourceMaxAgeSeconds`: one limit per source. `quota` and `process` must not exceed
  the binding limit (at most 60 s). `autoRecharge` may declare a longer limit, capped
  at 900 s, because an interface observation is slower to refresh. This is the owner's
  decision below and an explicit exception to the 60 s structural ceiling.

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
| `autoRecharge` | `autoRechargeEnabled: false`; `basis: "interface-observation"`; `accountBound: true`; `organizationBinding` equal to the frozen value; `uiObservedAt`; `profileObservedAt`; `collectorReceiptSha256`; `recorderRecordSha256` (both lowercase SHA-256). |
| `process` | the Codex process flags (`quotaBoundaryActive`, `noProviderOperationBeforeBind`, `observerConnected` true; `apiCredentialAvailable`, `helperCredentialAvailable`, `providerOverrideAvailable`, `fallbackAvailable` false); `authMethod: "claude.ai"`; `route: "included-subscription-quota"`; `storeBinding: "bound"`; `keychainSuffix` equal to the frozen one; `collectorReceiptSha256`; launch guarantees `settingSourcesEmpty`, `pinnedSettingsOnly`, `childEnvAllowlistOnly`, `canonicalConfigDir` true and `policySettingsCanInjectCredentials` false. |

Cross-source rules:
- The `process` and `autoRecharge` payloads must carry the same
  `collectorReceiptSha256`, so both refer to one profile read.
- `uiObservedAt` and `profileObservedAt` must not be later than the `autoRecharge`
  receipt time; they must lie within 600 s of each other; and `uiObservedAt` must not
  be older than the `autoRecharge` age limit at the check time.
- `organizationBinding` must equal the frozen `organizationScope.binding`; `unbound`,
  `bound` (reserved for a future method) or absent refuses.
- A null or absent auto-reload field in the API never substitutes for the interface
  basis, and no field is inferred from absence, a zero balance or HTTP 200.

Each receipt is valid until the earlier of its age limit and the instant its own claim
expires: the interface observation time plus the `autoRecharge` limit, or the earliest
quota window reset. The composition result expires with its earliest receipt. Expiry is inclusive: a result
whose age equals its limit is still accepted and expires at the check time. A quota
`usedPct` of zero is valid; negative, 100 or more is refused. The profile read may precede the
interface read by up to 600 s, so with a 900 s limit it can be up to 1500 s old; the
process receipt, at most its own limit (60 s or less) old, may share its collector digest. The freshness
of the process claims is bounded by the process receipt, not by that collector read; this
is accepted by design.

The claims keep their native meaning. Quota and extra usage come from the OAuth
usage and profile reads. Auto-recharge comes only from the interface observation
bound to the account. None of them attests account-wide API billing or actual cash.

## Owner design decisions (2026-10-13, in chat)

1. **Organization scope — owner-declared single organization.** The interface does not
   show which organization a setting belongs to, and the API profile exposes a single
   organization, so multi-organization membership cannot be detected from either. The
   contract accepts `organizationBinding: "owner-declared-single-organization"` only;
   `unbound` or absent refuses. The module checks only that the frozen
   `declarationSha256` is a well-formed SHA-256; the registration review or the observer
   must verify that it is the owner's declaration and that it states its limit. A future method that binds the organization would add
   the `bound` value without changing the rest.
2. **Freshness — a longer limit for the interface source only.** `autoRecharge` may
   declare its own `sourceMaxAgeSeconds`, at most 900 s per registration. `quota` and
   `process` stay within the binding's 60 s. The supervisor is expected to re-read them,
   extra usage live; that integration does not exist yet. This exceeds the existing structural ceiling for that one
   source, so the exception is written into the contract and each registration states it.
3. **Isolated store — separate proposal for the launch module.** The contract freezes
   only the credential-item suffix. Requiring a canonical `CLAUDE_CONFIG_DIR` in the
   shared host module, and comparing the expected suffix there, is a separate proposal
   for a later coordinated batch and is not part of this contract.

Next implementation boundary: the trusted Claude source observer that authenticates each
receipt against its pinned procedure and composes this result with the supervisor, the launch
module proposal for the isolated directory, and each registration's organization declaration
and interface freshness limit. Exact full registration approval must precede native capture.

## Validation and outstanding evidence

`tests.test_tooling_claude_sources` carries synthetic deterministic controls, not
provider evidence: safe composition and snapshot isolation; strict boolean and
missing-field refusal for every control; per-source freshness and the
earliest-expiry rule; source and verifier pin drift; binding drift; process lifecycle
and identity conflicts; frozen-contract mutation and every contract-field refusal
(host, suffix shape, organization scope, age limits and their ceilings); quota window
bounds and resets; `null`-style or unbound auto-recharge claims, wrong basis,
organization mismatch and interface-time windows (including exact boundaries);
store and suffix mismatch; mismatching collector receipt digests between sources; each
launch guarantee false; and rejection by the existing v3 admission checker. Mutation
testing ran in three rounds (the author's 19 and 35 deliberate module faults, then an
independent review's 90 single-point faults). Each round's surviving fail-open faults were
closed with targeted tests that also assert which rule refused. After the module was
restructured into one check per source, a 61-fault set left a single fault alive, a hash check
that the process claim's identical check makes redundant (the claims must carry the same digest).

## Not covered

No token is acquired, no host started, no prompt sent and no setting changed. The
module authenticates nothing and enables no launch path. Authentic acquisition and
independent verification of each source, the trusted observer's integration with the
supervisor, the shared host-module change for the isolated directory, refresh of the
interface observation at each admission, and any registration route stay in separate
reviewed batches. Pending SPEC-041, SPEC-044 T001/T002 and OP001–OP006 evidence is
unchanged.
