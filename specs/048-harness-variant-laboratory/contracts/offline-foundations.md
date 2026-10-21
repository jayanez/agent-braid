# Offline foundations — internal wire/API v0.1

Authority: [ADR 0027](../../../docs/adr/0027-braid-harness-offline-foundations.md).
This finite internal contract implements T002–T004 only. It does not extend an
existing public schema, CLI, runtime grant, plugin or MCP interface. All advice
and reservation receipts have `executionAuthorization=false`; no record launches
a process. Native/model/child/network/retry/cash counts remain zero.

## Immutable manifest

`agent_braid.harness_manifest` exposes `parse_manifest(raw: bytes)` and
`verify_manifest(raw, *, expected_sha256, expected_bindings)`. Both return an
immutable `HarnessManifest` with `data`, `canonical_bytes`, `sha256`, `bindings`
and an independent mutable `to_dict()` copy. Direct DTO construction is not
consumer verification. Each consumer reparses raw bytes and checks a trusted
full manifest hash; named expected bindings may additionally constrain specific
observations. Producer hashes alone establish neither authenticity nor rights.

The wire format is `braid-harness-manifest/v0.1`, profile `offline-foundations`.
Every object has an exact key set; unknown/future fields or versions refuse.
The complete required top-level inventory is:

| Field | Meaning |
|---|---|
| `format`, `profile`, `executionAuthorization` | Exact version/profile and boolean false |
| `source` | Full 40-hex commit and selected input inventory including committed/uncommitted origin |
| `base`, `candidate` | Full SHA-256 of canonical file inventories; each file binds path, bytes SHA-256 and size |
| `task` | Task ID, input hash and separately bound fixture/oracle hash |
| `context` | Ordered eligible entries with identity, relative path, hash, size, explicit trust and selection |
| `host` | Offline kind; requested offline route and explicit null unavailable executable/model/provider/build observations |
| `tools` | Immutable tool-contract IDs and hashes; no executable loading |
| `policy`, `verifier`, `normalizer` | Explicit versions and full hashes |
| `environment` | OS/architecture observation, environment hash and trusted destination hash |
| `envelopeSha256` | Externally adopted operator-envelope identity; not issuance |
| `allowedComponentPaths` | Positive bounded editable component inventory |
| `effects` | Explicit read/write/delete resources with no globs |
| `limits` | Positive bounds may tighten ADR maxima; capability counts remain integer zero and currency EUR |

Inventory digests use existing Agent Braid canonical JSON (`system_one.canonical`)
and full SHA-256. Raw JSON is bounded UTF-8, depth 16, finite numbers and signed
64-bit integers; duplicate keys, invalid Unicode and booleans as integers refuse.
Paths are normalized relative NFC strings with no traversal, empty/dot components,
control/format characters, wildcard or separator aliases. Casefold collisions
refuse. Context order remains semantically observable; unordered file/tool/effect
inventories have a deterministic unique ordering.

Named bindings are `source`, `base`, `candidate`, `task`, `context`, `host`,
`tools`, `policy`, `verifier`, `normalizer`, `environment`, `fixture`, `envelope`.
The full manifest hash also covers effects, limits and allowed paths.

Read resources use four explicit namespaces: `source/<selected-input-path>`,
`base/<component-path>`, `candidate/<component-path>`, and `context/<entry-path>`.
Each must exist in its corresponding positive inventory. Write/delete resources
use `lab/<component-path>`, require membership in `allowedComponentPaths`, and
never authorize writes into a read root.

## Import and reservation trust boundaries

T003 receives separate trusted canonical source/base/candidate/context roots and
a new destination outside them. Destination identity is **SHA-256 of the raw
UTF-8 canonical absolute POSIX destination string**, not a JSON-string digest.
No-follow checks still apply; computing a digest does not authorize following
symlinks. The importer verifies declared metadata against actual bounded bytes,
types and modes before materialization. Guidance remains untrusted text.
Root separation compares the device/inode identities of directories observed
during no-follow traversal, including existing ancestors of an absent destination.
Lexical spelling alone cannot establish containment on a case-insensitive filesystem.
Physical nesting or aliases refuse before any import or reservation write.

Publication atomically claims a new private container; any preexisting path,
including an empty directory or symlink, refuses. Staging inside that container
can publish an accepted `candidate/` subtree only after complete validation.
Logical `lab/<component>` writes map to that subtree. Cleanup requires declared
delete resources and removes only the owned recorded staging inventory. Fixed
transaction bookkeeping is bounded and reported; an uncertain/failed cleanup
cannot be presented as accepted or silently retried. Receipts distinguish the
container, accepted tree, source hashes and cleanup state.

T004 receives a caller-supplied trusted operator scope, never one reconstructed
from candidate JSON. Operator admission is read from independently protected
owner-controlled files outside all read/import roots; a forged/rehashed raw
admission record cannot supply provenance. A separate private reservation directory
is permitted for bounded operator records and cannot be imported guidance.

The trusted scope binds issuer, adopted-profile identity, canonical roots,
fresh observation time, the twelve non-envelope identities, and count/byte caps.
Its digest deliberately excludes the full manifest hash and envelope binding to
avoid a self-referential digest. The completed manifest then binds that envelope;
the independently issued admission binds the final complete manifest hash.

Expiry is checked against a trusted caller clock, with a maximum 300-second
lifetime. Reservation serializes an exclusive durable single-use marker and
charges counts/bytes independently. Partial/consumed markers fail closed; recovery
does not issue or renew admission. T004 has no issuance, native dispatch, retry,
ordinary-use promotion or existing-grant conversion API. Library calls assume
the trusted Python operator/OS boundary in ADR 0027; hashes and filenames are not
signatures or protection from hostile same-UID arbitrary code.

The internal callable boundary is:

```python
import_candidate(raw, *, expected_sha256, expected_bindings,
                 source_root, base_root, candidate_root, context_root, destination)
reserve_admission(raw_manifest, *, expected_manifest_sha256,
                  scope: OperatorScope, admission_id, now)
```

Import requires all thirteen independently supplied bindings, and returns a
deeply immutable receipt; a refusal exposes its cleanup receipt on
`SurfaceError.receipt`. `OperatorScope` copies and freezes the twelve
non-envelope bindings and binds the issuer, adopted-profile hash, seven roots,
observation time and count/byte limits. Reservation returns immutable canonical
receipt bytes with `sha256` and `to_dict()`. Callers retain the receipts; T007
durable attempt recovery and T012 observation/export remain pending.

Operator and reservation directories must already exist with owner-only mode
0700. The lab destination may be absent, with an existing no-follow parent, so
reservation can precede import without creating the destination. Admission files
must be regular owner-controlled mode-0600 files with a single hard link. A
malformed existing reservation store refuses before creating the lock file;
checks repeat under a nonblocking exclusive lock before the single-use marker.
There is no transaction coordinator or dispatch API in this slice: the trusted
operator composes reservation before import, and failed import cannot replenish
the spent reservation.

## Compatibility and evidence

This version is internal and opt-in. Future formats refuse until explicitly
implemented/reviewed; there is no permissive migration or public re-export.
T011/T012 and T005+ retain context packaging, observation/privacy, runner and
recovery ownership. Component tests and current source hashes support only their
stated engineering controls; they do not establish native utility or promotion.
