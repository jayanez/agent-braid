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
| `registrySha256Before` | hex | registry bytes now |
| `cohort` | const `native` | evaluated cohort |
| `evidence` | sorted list of hex | evaluation and cost report digests cited |
| `diffSummary` | object `{added, removed}` line counts | no text body |
| `requiredDecision` | const `approved` | the human decision still needed |
| `previewDigest` | hex | SHA-256 over canonical bytes of all fields above |
| `executionAuthorization` | const `false` | never true |

Apply rule: `--apply --preview-digest d` recomputes the preview and writes only
when the recomputed digest equals `d`. Order: registry `record` (if new), human
`decide`, `begin`, file write by atomic rename, `commit`; on any failure,
`abort` and restore the file bytes.

Refusal reasons: `unknown-scope`, `candidate-not-stored`, `digest-mismatch`,
`preview-stale`, `automatic-promotion-disabled`, `cohort-mismatch`,
`no-previous`, `text-too-large`.
