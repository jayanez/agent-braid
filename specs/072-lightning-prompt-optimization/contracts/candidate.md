# Contract: `braid-lightning-candidate/v0.1`

One JSON line per candidate in
`<plugin home>/lightning/runs/<run-id>/candidates.jsonl`; the text is stored
beside it as `candidates/<sha256>.md`. Exact keys; unknown keys refused.

| Key | Type | Meaning |
|---|---|---|
| `schema` | const `braid-lightning-candidate/v0.1` | — |
| `sha256` | 64 hex | sha256 of the candidate body UTF-8 bytes |
| `parentSha256` | 64 hex or null | null only for the seed |
| `originPath` | repository-relative path | `integrations/agent-braid/skills/agent-braid-analyze/SKILL.md` |
| `frontMatterSha256` | 64 hex | fixed front matter (P3) |
| `algorithm` | enum `baseline`, `apo`, `gepa` | — |
| `round` | integer ≥ 0 | 0 for the seed |
| `optimizerCalls` | list of identifiers | runner call ids that produced it |
| `optimizerTemplateSha256` | 64 hex or null | template used (APO or GEPA reflection) |
| `contaminationCheck` | object `{inputSha256, passed}` per call | REQ-006 |
| `devScore` | object or null | minibatch and full development scores (P2) |
| `paretoMember` | boolean | GEPA only; false otherwise |
| `createdAt` | UTC RFC 3339 | — |
| `promotion` | const `none` | promotion is SPEC-073 and human only |
| `executionAuthorization` | const `false` | — |

Rules: records are append-only and immutable; a candidate whose text hash does
not match `sha256` is refused; the seed's `sha256` must equal the hash of the
body of `originPath` at the run's recorded commit.
