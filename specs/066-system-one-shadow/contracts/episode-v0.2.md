# Contract: agent-braid-s1-episode/v0.2

Owner decision 2026-11-01 (SPEC-066 REQ-003 enrichment). v0.2 supersedes
[v0.1](episode-v0.1.md) as the schema the observer writes. v0.1 lines already in
a store stay valid and readable: the validator accepts both schemas, and
`system-one report` aggregates both (per-schema counts under `schemas`).

One episode is a single JSON object on one line (UTF-8, canonical: sorted keys,
no insignificant whitespace, no NaN or infinity, no duplicate members). The S1.5a
shadow observer writes it after a successful `analyze-work` call (AIM or Git).
`analyze` is reserved because its runtime result carries no interaction report.
An episode never reaches an MCP envelope.

## Inputs

The MCP adapter (`tooling_mcp._shadow`) hands three things to the off-request
worker. It passes them by reference and does no other work on the request path:

1. the final System 2 report (or the encoded evidence artifact that holds it)
2. the request object the adapter already validated
3. the configured `source_root` resolved path string, used only for the salt
   below

The worker reads the request and never changes it. It never re-runs Git or the
analyzer.

## Top level

Unchanged from v0.1 apart from `schemaVersion`. v0.2 adds no identifying
top-level field.

| Field | Type | Rule |
|---|---|---|
| `schemaVersion` | string | Exactly `agent-braid-s1-episode/v0.2` (`.../v0.1` accepted for legacy lines with v0.1 pairs) |
| `episodeId` | string | Random UUID4, lowercase. Not derived from any input |
| `day` | string | UTC date, `YYYY-MM-DD` |
| `surface` | string | `mcp` |
| `operation` | string | `analyze` or `analyze-work` |
| `analysisKind` | string | `aim` or `git` |
| `analyzer` | object | `{version, ruleSet}`, each matching `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$` |
| `operationCount` | integer | 1–64 |
| `pairCount` | integer | 0–2016 |
| `classificationCounts` | object | The four System 2 classes, summing to `pairCount` |
| `pairsRecorded` | integer | 0–64; pairs beyond 64 are dropped deterministically in report order |
| `pairs` | array | `pairsRecorded` v0.2 pair objects |
| `systemOne` | object | As in v0.1 (status, reason, backendId, manifestDigest, decisionPoint `DP-1`, answers, elapsedMicros) |
| `executionAuthorization` | boolean | Exactly `false` |

Caps, the 50 ms budget (now also covering feature derivation and salting),
worker semantics, retention and refusal reasons are unchanged from v0.1.

## Pair object

The v0.1 fields keep their v0.1 meaning, except that `effectKinds` is now filled.

| Field | Type | Rule |
|---|---|---|
| `system2` | string | `independent-candidate`, `ordered`, `conflicting` or `unknown` |
| `system2Determinate` | boolean | `false` only for `unknown` |
| `reasonCodes` | array | Closed set from v0.1 (exact sentence table) |
| `constraints` | array | Closed constraint vocabulary from v0.1 |
| `coverage` | array | Sorted subset of `complete`, `partial`, `unknown` |
| `sharedResourceCount` | integer | 0–4096 |
| `effectKinds` | null or object | `{left, right}`: sorted per-side sets over `read`, `write`, `call`, `transform`, `emit`, `delete`, `deploy`, `unknown`. Null when unavailable (see sources) |
| `dependency` | boolean | Whether an explicit dependency path orders the pair |
| `observedOutcome` | null | Always `null` (S1.5b joins outcomes separately) |
| `resourceClasses` | object | `{left, right}`: each an object with exactly the seven class keys, giving the count of that side's resources in each class, each 0–4096 |
| `sharedResourceClasses` | object | The seven class keys, counting the pair's shared resources; the sum equals `sharedResourceCount` (at least 4096 when capped) |
| `maxDepth` | integer | 0–16: the highest path segment count over the pair's path resources, capped at 16; 0 when no resource is a path |
| `sameParentDirCount` | integer | 0–4096: the number of (left resource, right resource) path pairs with the same immediate parent directory (the root counts as a parent), capped |
| `topDirOverlap` | boolean | True when some left and right path resource with at least two segments share the first segment |
| `resourceHashes` | null or object | `{left, right, shared}`: each a sorted, deduplicated list of at most 32 pseudonyms (the 32 lowest), each exactly 16 lowercase hex characters. Null when no salt is available |

### Sources of per-side values

- **Side resources.** The report's `operations[].resources` for the pair's
  `left` and `right` instance. **Shared resources.** The interaction's
  `sharedResources`. Both kinds of analysis provide these.
- **AIM `effectKinds`.** For each validated AIM record in the request, the union
  of `kind` over its `declared`, `inferred` and `observed` effects. These are
  the actual record kinds.
- **Git `effectKinds`.** The Git request carries no effects, and the adapter
  records only its effect map. The report's resources fix the kinds exactly:
  `git_adapter._record` writes `git://…` resources only with kind `write`, and
  `git-unsupported://…` resources (deleted, unsupported-status or uncertain
  paths) only with kind `unknown`. A resource with any other scheme makes that
  side unavailable, and the pair records `null`.
- `effectKinds` is `null` when no request was handed off (AIM), or when either
  side is unavailable.

## Path rules

These rules are deterministic and depend only on the resource string. They are
evaluated in memory, and the resource string itself is never stored.

**Path view.**
1. Remove a leading `scheme://authority/` prefix, where the scheme matches
   `^[A-Za-z][A-Za-z0-9+.-]*://` and the authority runs to the next `/`. So
   `git://<repo-id>/src/a.py` becomes `src/a.py`.
2. Cut the text at the first `?` or `#`.
3. If the remaining text contains neither `/` nor `.`, the resource is not a
   path. For example, `db:users`, `users` and `git://repo/` are not paths.
4. Otherwise, split on `/` and drop empty and `.` segments. The last segment is
   the basename and the others are directories. Comparisons are lowercase.

A non-path resource is class `other`. It contributes 0 to `maxDepth` and does
not count towards `sameParentDirCount` or `topDirOverlap`.

**Classification.** The first matching rule wins, in this order:

| Order | Class | Rule |
|---|---|---|
| 1 | `lockfile` | Basename exactly one of `package-lock.json`, `yarn.lock`, `pnpm-lock.yaml`, `poetry.lock`, `uv.lock`, `Pipfile.lock`, `Cargo.lock`, `go.sum`, `Gemfile.lock`, `composer.lock` (case-insensitive) |
| 2 | `generated` | A directory segment in `dist`, `build`, `out`, `target`, `node_modules`, `__pycache__`, `generated`; or the basename contains `.min.` or `generated` |
| 3 | `test` | A directory segment in `test`, `tests`, `__tests__`, `spec`; or the basename matches `test_*`, `*_test.*` (the stem ends in `_test`), `*.test.*` or `*.spec.*` |
| 4 | `docs` | Extension `.md`, `.rst`, `.txt`, `.adoc`; or a directory segment `docs` |
| 5 | `config` | Extension `.json`, `.yaml`, `.yml`, `.toml`, `.ini`, `.cfg`, `.conf`, `.env`; or a dotfile basename (starts with `.`) |
| 6 | `src` | Extension `.py`, `.js`, `.ts`, `.tsx`, `.jsx`, `.go`, `.rs`, `.java`, `.kt`, `.c`, `.h`, `.cpp`, `.cs`, `.rb`, `.php`, `.swift`, `.m`, `.scala`, `.sh` |
| 7 | `other` | Anything else, including every non-path resource |

Examples:
- `node_modules/yarn.lock` is `lockfile`
- `tests/build/helper.py` is `generated`
- `tests/fixtures/data.json` is `test`
- `docs/conf.py` is `docs`
- `.github/workflows/ci.yml` is `config`
- `assets/logo.png` is `other`

The extension is the suffix after the basename's last `.`, as returned by
`os.path.splitext`. A basename that is only a dotfile name (such as `.env`) has
no extension and matches rule 5 as a dotfile.

## Pseudonym construction

1. **Secret.** The store directory holds `salt.key`, a file of 32 random bytes
   (`os.urandom`) with mode `0600`. The observer creates it on first use, under
   the store lock, with `O_CREAT | O_EXCL | O_NOFOLLOW`. Every read applies the
   same checks as the other store files: no symlink, a regular file with a
   single link, owned by the user, no group or other permission bits, and
   exactly 32 bytes. The store's filename rule recognizes it as the store's own,
   alongside `store.lock`, so it is neither a day file nor an unrelated
   leftover. If it is unusable, busy, or the store refuses, no salt is
   available.
2. **Repo salt.** `repo_salt = HMAC-SHA256(secret, b"agent-braid-s1-repo\0" +
   fsencode(source_root))`. `source_root` is the resolved path string of the
   configured source root, handed off from `ToolingConfig`.
3. **Pseudonym.** The first 16 hex characters of `HMAC-SHA256(repo_salt,
   resource_string)`, where `resource_string` is the exact report resource string,
   UTF-8 encoded. System 2 resource identity is exact-string equality, so the
   pseudonym is per exact string. A Git `git-unsupported://` resource includes its
   operation's query, so it differs per operation.

When no salt is available, or no source root was handed off, `resourceHashes`
is `null`. All other features are still recorded.

## Never present

The following never appear:
- resource names and paths
- instance or attempt identifiers
- analysis identifiers and input digests
- repository names and the source-root path
- prompts and reason sentences
- host names and user names
- the secret and the repo salt

The secret and the source root never appear in episodes, reports, logs, status
output or error text.

The validator refuses any string outside the closed vocabularies, except
`episodeId`, `day`, `backendId`, `manifestDigest`, and the 16-hex pseudonyms in
`resourceHashes`. `system-one report` prints counts only and never prints
pseudonyms.

## Privacy statement

The pseudonyms are pseudonymous **within the local machine**:
- The same resource string in the same configured repository always maps to the
  same pseudonym.
- The same string under a different source root maps to a different pseudonym.
- Without `salt.key`, pseudonyms cannot be linked to a resource by guessing
  common paths.

The salt never leaves the machine and the store is never uploaded.
`system-one purge` deletes `salt.key` with the day files and lock. Pseudonyms in
any day file that was copied elsewhere then become unlinkable to new episodes.

This is not anonymity. Anyone holding both the store and `salt.key` can test
candidate paths. Whether the pseudonyms are retained beyond S1.5 is decided by
their ablation in S1.5d. If they carry no measured value, they are removed.
