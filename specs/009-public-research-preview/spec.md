# Public research-preview publication

## Purpose and scope

Publish Agent Braid as `v0.1.0-alpha.1` from a clean Git history while retaining
the current private repository as an internal archive. The public repository must
carry inspectable source provenance, fresh public-root reproduction evidence and
the existing scientific limits without exposing the private Git objects that
contain a historical proprietary-template derivative.

This feature covers publication tooling, portable provenance, historical-closure
validation, community scaffolding and the release protocol. It does not authorize
remote publication by itself, implement M2, publish a package, change runtime
semantics or upgrade any scientific claim.

## Authorities

Clause zero and Articles 13, 14, 17, 19, 21, 23 and 25 govern claim discipline,
inspectable evidence, public communication and evidence-building phases. The
licensing map, governance policy, ADR 0009, M0.5 closure and research-preview
proposal govern redistribution, approval and validation status. ADR 0010 will
record the subordinate clean-export architecture.

## Requirements and acceptance scenarios

### REQ-001 — Historical closures remain bounded and future-safe

Given the frozen M0, M0.5 and M1 candidates, when closure validation runs after
later feature work, then it must verify only the recorded candidate-to-closure
interval and accept unrelated later commits. Altering the recorded interval,
anchor or approved artifacts must fail. See SC-026.

### REQ-002 — Export only the reviewed distributable tree

Given an exact private source commit, when the export tool runs twice, then it
must produce byte-identical payloads and a canonical manifest containing the
source commit, source tree and SHA-256 inventory. It must exclude `.git`, ignored
local state and every untracked file. Unsafe destinations, dirty implicit input,
missing objects, symlinks and unsupported paths must fail. Machine-local absolute
paths must be deterministically redacted, dependent evidence digests rebound and
every transformation disclosed without changing the private source. See SC-027.

### REQ-003 — Portable provenance never impersonates private history

Given a clean public root containing the generated manifest, when public
validation runs, then current exported bytes and record integrity must be checked
while unavailable private ancestry is reported explicitly as unavailable. A late,
altered or incomplete manifest, undisclosed transformation or leaked local path
must not bypass strict historical validation. See SC-028.

### REQ-004 — Public evidence is fresh and non-authorizing

Given the clean public candidate, when the publication reproduction runs in a new
clone and Python 3.12 environment, then commands, versions, hashes, outputs and
repository state must be recorded against that public commit. Missing approval,
dirty state, mismatched commits or a claim of independent validation must block
release readiness. See SC-029.

### REQ-005 — Remote cutover cannot leak private objects

Given separate private-archive and public workspaces, when the founder authorizes
publication, then only the clean public object graph may be pushed. `main` and
`develop` must identify the approved release commit, `develop` must be the default,
and `v0.1.0-alpha.1` must be a prerelease with
`independent_validation: pending`. The private clone must never receive the public
remote. See SC-030.

## Scientific boundaries and compatibility

The publication reports internally reproduced evidence and founder review, not
independent validation. Manifest integrity does not prove the truth of historical
claims, the authenticity of the founder, production safety, complete dependency
discovery, general confluence or Yang–Baxter validity. AIM `0.1.0-draft` and
`0.2.0-draft`, certificates, assurance classes and analyzer report contracts are
unchanged.

## Evidence and unresolved questions

Implementation evidence will be captured locally before review. Publication,
repository rename, visibility changes, pushes, branch rules, tags and releases
remain unexecuted until a separate explicit founder authorization. GitHub Actions
blocked by billing will be recorded as not executed, never as approved.
