# SPEC-067 contract: assurance profile, authorization and receipt (v0.1, proposed)

Contracts are proposals until reviewed (Article 24). Canonical JSON: UTF-8, sorted
keys, no insignificant whitespace; digests are SHA-256 over those bytes.

## Profile (`braid-harness-assurance-profile/v0.1`)

```json
{
  "schema": "braid-harness-assurance-profile/v0.1",
  "name": "string",
  "version": 1,
  "checkpoints": {
    "<checkpoint>": {"mode": "<hitl-mode>"},
    "pre-pr-review": {"mode": "<hitl-mode>", "depth": "R0|R1|R2|R3|R4"}
  },
  "riskRules": [{"id": "string", "match": {"paths": ["glob"], "minChangedLines": 0}, "raiseTo": "R3", "modeAtLeast": "approve-each"}],
  "standingAuthorizations": ["<authorization id>"]
}
```

- `checkpoints` keys are exactly the closed catalog of REQ-001; all are required.
- `depth` is allowed only on `pre-pr-review`. Mode order: `autonomous` <
  `notify` < `standing-authorization` < `approve-each` < `human-only`.
- Allowed modes per checkpoint are a fixed table. `release`, `clarification`,
  `grant`, `native-effect` and `auto-promotion` allow only `human-only`
  (REQ-003). `noAttribution` is an invariant, true for `pr-open`, `merge`,
  `release` and `post-merge`; a profile cannot set it false.
- `riskRules` may only name `raiseTo` at or above the configured depth and
  `modeAtLeast` at or above the configured mode; a rule that would lower is
  refused. Default path sets reuse `validate_change.classify()` (sensitive).
- Unknown keys anywhere are refused.

## Standing authorization (`braid-harness-standing-authorization/v0.1`)

Fields: `id`, `checkpoint`, `repository`, `branchPattern`, `conditions` (closed
set, for example `ciGreen`, `receiptsPresent`, `noOpenReviewThreads`),
`issuedAt`, `expiresAt`, `issuer`, `ownerStatement` (verbatim, nonempty),
`revokedAt` (nullable). Valid only if the checkpoint admits the mode (Q2), the
horizon is within Q3, and the issuer is permitted (Q4). Stored in an
operator-owned location; the agent can read it and cannot write it.

## Resolution

Effective depth and mode per checkpoint: scope precedence following SPEC-058
REQ-006 / `ownership.resolve_settings` (conversation over repository over user,
profile as lowest source, scope values from an operator-owned assurance settings
source); then raise-only risk escalation; then the REQ-003 floors last. Both
later steps only raise, so their order does not change the result. Output
records the source of each value and every refused lowering.

## Compiled artifact (`braid-harness-assurance-compiled/v0.1`)

Resolved view, input hashes, risk classification, `executionAuthorization: false`
(any other value refused), digest.

## Receipt (`braid-harness-gate-receipt/v0.1`)

Fields: `checkpoint`, `depth`, `depthSource`, `mode`, `modeSource`, `baseCommit`,
`headCommit`, `profileDigest`, `riskClass`, `reviews` (list of `kind`, `status`,
`findingsApplied`, `findingsRejected` each with reason), `commands` (`argv`,
`exitCode`, `outputSha256`), `approvals` (human approval reference or standing
authorization id), `fallbackReason` (nullable), `createdAt`, `digest`.
Verification checks canonical form and digest, commit binding, profile binding,
depth not below the effective depth, every required review present, every
command with an exit code, and that approvals match the mode. The digest detects
inconsistent edits only; receipts live in an operator-owned store written by the
orchestrator (REQ-007).

## Review ladder

| Depth | Required reviews (code) | Docs-only equivalent |
|---|---|---|
| R0 | none | none |
| R1 | code review | accuracy |
| R2 | R1, quality, simplification | R1, claim discipline, concision |
| R3 | R2, adversarial/security | as code |
| R4 | R3, independent multi-agent review (at least two reviewers distinct from the author and each other) | as code |

## Refusal reasons

Fixed strings, one per refusal in REQ-001 to REQ-008; the same input yields the
same reason and no partial view.
