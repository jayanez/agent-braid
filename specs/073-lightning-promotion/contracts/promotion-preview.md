# Contract: Lightning promotion preview

Schema identifier: `braid-lightning-promotion-preview/v0.1` (JSON on stdout).

| Field | Type | Meaning |
|---|---|---|
| `schema` | const | `braid-lightning-promotion-preview/v0.1` |
| `action` | enum `promote`, `rollback`, `revoke` | requested change |
| `scope` | id | registry scope from the closed scope map |
| `targetPath` | repo-relative path | mapped `SKILL.md` |
| `currentSha256` | hex or null | registry active digest |
| `candidateSha256` | hex | digest to become active |
| `fileSha256Before` | hex | target file bytes now |
| `registrySha256Before` | hex | registry bytes now (SHA-256 of empty bytes when no registry file exists) |
| `cohort` | const `native` | evaluated cohort |
| `evidence` | sorted list of hex | SPEC-049 registration and evaluation record digests cited |
| `heldOutSupport` | enum `supported`, `no-held-out-support` | H1 outcome of the SPEC-072 report for every host of the scope |
| `overrideReason` | string or null | required on apply when `heldOutSupport` is `no-held-out-support`; recorded in the decision |
| `diffSummary` | object `{added, removed}` line counts | no text body |
| `blockers` | sorted list of refusal reasons | refusals an apply would raise now (for example `regression-not-covered`, `no-held-out-support`, `transaction-in-progress`, `already-active`); empty when none |
| `requiredDecision` | const `approved` | the human decision still needed |
| `previewDigest` | hex | SHA-256 over canonical bytes of all fields above |
| `executionAuthorization` | const `false` | never true |

CLI: `agent-braid lightning promote --candidate <sha> --run-id <run> --registration <file>
--evaluation <file> --identity <file> [--scope <s>] [--root <checkout>] [--override-reason <text>]`
prints the preview on stdout and writes nothing; a refusal is the single stderr line
`lightning promote refused (<reason>)` with exit status 2.

Recovery: `lightning promote --abort --run-id <run> [--scope <s>] [--reason <id>]`
previews dropping a pending (interrupted) promotion: `action` `abort`, the
`pendingSha256` being dropped, the `candidateSha256` the file returns to (the active
candidate, or the baseline cited by the scope's first decision), the journal `reason`
and `requiredDecision` `human-apply`. `--apply --preview-digest <d>` restores that text,
then records `aborted`.

Apply rule: `--apply --preview-digest d` recomputes the preview and writes only
when the recomputed digest equals `d`. Right before writing, the registry and file bytes must still match
`registrySha256Before` and `fileSha256Before` (`preview-stale` otherwise). Order:
registry `record` (if new), human `decide`, `begin`, file write by atomic rename
(file mode kept, directory fsynced), `commit`; on any failure, `abort` and restore
the file bytes. If the restore or the abort record fails, the refusal is
`abort-failed` and `--abort` recovers. A scope's first apply keeps the replaced
baseline text, and an override reason's text, content-addressed in the run store,
and names the baseline in a `lightning-baseline:` limit id (scope map contract).

Refusal reasons: `unknown-scope`, `candidate-not-stored`, `digest-mismatch`,
`preview-stale`, `automatic-promotion-disabled`, `cohort-mismatch`,
`no-previous`, `text-too-large`, `no-held-out-support` (apply without an
owner override reason), `regression-not-covered` (OD-4: a SPEC-072 pair whose
C-vs-A strata are descriptive-only), `candidate-mismatch`, `registration-mismatch`,
`no-candidate`, `baseline-unknown` (the first decision names no single baseline).
