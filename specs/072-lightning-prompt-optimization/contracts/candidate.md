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
| `contaminationCheck` | list of `{inputSha256, passed}`, one per optimizer call, `passed` true | REQ-006; a refused call yields no candidate |
| `devScore` | null or `{minibatch, full}`, each null or `{d4FirstAttempt, schemaValid, rollouts}` | development scores (P2); means in [0, 1] |
| `paretoMember` | boolean | GEPA only; false otherwise |
| `createdAt` | UTC RFC 3339 | — |
| `promotion` | const `none` | promotion is SPEC-073 and human only |
| `executionAuthorization` | const `false` | — |

Rules: records are append-only and immutable; a candidate whose text hash does
not match `sha256` is refused, and a record is refused until its text is stored;
the seed's `sha256` must equal the hash of the body of `originPath` at the run's
recorded commit. Lineage: only the round-0 `baseline` seed has a null parent and
no optimizer calls; every other candidate has a recorded parent, round ≥ 1,
optimizer calls and a template hash. A later record for the same `sha256` may
change only `devScore`, `paretoMember` and `createdAt` (the latest wins); any
other difference is refused (`candidate-immutable`).
