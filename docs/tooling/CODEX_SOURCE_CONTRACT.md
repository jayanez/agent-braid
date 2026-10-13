# Codex source composition contract

Status: implementation authorized by the owner on 2026-10-12. Literal decision:
“Autorizo el contrato adicional y su implementación de la PR #504”. This is
approval of the separately versioned source contract and implementation scope;
it is not registration approval, capture authorization, native acceptance or
adoption of ADR 0021.

## Versions and migration

`agent-braid-codex-source-contract-v1` and
`agent-braid-codex-source-receipt-v1` are additional contracts implemented by
`agent_braid.tooling_codex_sources`. They do not replace or modify subscription
policy v1, native process policy v2, operational subscription policy v3, or
registration v1/v2/v5. Historical receipts remain unchanged.

The binding embedded in each record uses the existing structurally validated
operational binding shape to identify the account, namespace, registration,
slot, policy, build, executable, configuration, argv, candidate, model and
observer. Its use here does **not** assert compliance with v3 payment predicates.
Do not convert this composition to a v3 observation or fill `creditsEnabled`,
`extraUsageEnabled` or `subscriptionActive` with inferred values.

Existing launch/supervisor paths continue to enforce their registered contracts.
The new source composition is a preparation component, not an alternate launch
entry point. Live source verification, supervisor composition and any additional
registration route require their own reviewed integration before dispatch. No
runtime switch or fallback to this contract is enabled by this change.

## Frozen source contract

The contract has exactly `schema`, `binding`, `additionalSpendCapEur` (integer
zero), and `sources`. `sources` has exactly `quota`, `autoRecharge`, and
`process`. Each source pin has a nonempty `sourceRef` and `verifierRef`, and
lowercase SHA-256 `sourceSha256` and `verifierSha256` values. The caller supplies
the separately frozen canonical contract digest; contract mutation refuses.

Pins identify the acquisition and verification procedures; they are not hashes
of a changing response. The complete sanitized receipt receives its own digest
in the composition. Raw account identifiers, credentials, bodies and monetary
values must stay private. A trusted observer must authenticate and independently
verify each receipt against its pinned source before composing it. Matching
self-reported digests is a structural check, not source authentication.

## Required receipts

Each of the three receipts has exactly `schema`, `kind`, `contractSha256`,
`binding`, the four source/verifier pin fields, `phase`, `processId`,
`processBirthSha256`, `observedSequence`, `observedAt`, and `payload`.
All receipts must identify the same process phase, PID/birth and positive
observation sequence, and match the complete frozen binding. Prelaunch has null
PID/birth; running/completed require a positive integer PID and a birth digest.

Every timestamp must be timezone-aware, not future-dated, and within the
binding's freshness limit (at most 60 seconds). All sources are checked
individually; a new quota receipt cannot refresh an old recharge observation.
The result expires when the earliest receipt does. Missing, extra, conflicting,
non-boolean, stale or differently bound fields refuse composition.

| Source | Exact payload and required values |
| --- | --- |
| `quota` | `ordinaryUsageAllowed: true`, `spendControlReached: false`, `credits: {hasCredits: false, unlimited: false}` |
| `autoRecharge` | `autoRechargeEnabled: false` |
| `process` | `authMethod: chatgpt`, `route: included-subscription-quota`; `quotaBoundaryActive`, `noProviderOperationBeforeBind`, `observerConnected` all true; `apiCredentialAvailable`, `helperCredentialAvailable`, `providerOverrideAvailable`, `fallbackAvailable` all false |

Quota fields preserve their native meaning: ordinary included usage is allowed
and usable/unlimited credits are absent. They do not claim that a payment setting
is disabled, attest account-wide API billing, or establish actual cohort cash.
The API collectors' point-in-time metadata alone does not establish process
isolation, namespace correspondence, or live supervisory continuity. UI recharge
observations cannot be reused without fresh, independently verified native-account
and process correspondence. The implementation acquires no tokens, starts no
host, sends no prompts, and changes no provider settings.

## Validation and outstanding evidence

`tests.test_tooling_codex_sources` covers safe composition, strict boolean and
missing-field refusal, all-source freshness, source/verifier pin drift,
account/namespace/candidate/configuration/model binding drift, process conflicts,
frozen-contract mutation, and rejection by the existing v3 admission checker.
These are synthetic deterministic controls, not authentic provider evidence.

SPEC-041/T001–T010, SPEC-044/T001–T002 and OP001–OP006 remain pending their
original evidence. Next implementation boundary: the trusted native source
observer and its bounded supervisor integration, with independent verification
of source authenticity and browser/native namespace correspondence. Exact full
registration approval must precede native discovery/journey capture. Additional
spend remains EUR 0; cash, economic completion and human evaluation remain
separate gates.
