# Contract: native Claude manifest profile (proposal)

Status: proposal for review. Names and values marked *founder* depend on the
open items in [spec.md](../spec.md). Nothing here changes
`braid-harness-manifest/v0.1` for the offline profile.

## Profiles

| Profile | Host kind | Status |
|---|---|---|
| `offline-foundations` | `offline` | unchanged; byte-compatible (REQ-001) |
| `native-claude-laboratory` (proposed name) | `claude` | new closed profile |

The manifest `format` stays `braid-harness-manifest/v0.1`; `profile` selects the
closed schema. The existing order of checks is kept: top-level key set, then
`format`, then `profile`. Dispatch to the native validator happens at the
existing profile check, so an offline manifest with several faults keeps its
current first refusal reason; goldens include multi-fault manifests. The native
key set differs from the offline one, so the key-set check itself becomes
profile-aware without changing the offline result. An unknown profile is
refused as `unsupported-profile`, as today. Offline constants, accepted bytes,
digests, views and refusal reasons do not change; the native path is added
beside the offline one.

## Native fields that differ from offline

| Field | Native rule |
|---|---|
| `host.kind` | exactly `claude` |
| `host.executableSha256` | 64-hex SHA-256 of the resolved CLI executable (NC-4) |
| `host.build` | exact version string inside the supported window (NC-4), checked by a version validator in `harness_manifest.py` (importing `parse_version` from `harness_host_claude` would be circular) |
| `host.requested` | `{"model": <id or null>, "effort": <id or null>, "route": "subscription"}` |
| `host.observed` | all null in the manifest; observations live in run evidence, never in the manifest |
| `containment` (new key, native only) | `{"backend": <id>, "qualificationSha256": <hex>}`; the qualification itself is verified separately |
| `hostQualificationSha256` (new key, native only) | 64-hex hash of the Claude host record |
| `environment` | same keys as offline; `sha256` must equal both qualification records' `environmentSha256` |
| `executionAuthorization` | always `false` |

Adding `containment` and `hostQualificationSha256` only to the native key set
keeps the offline key set identical. Whether the two hashes live in the manifest
or are supplied only at call time is a T003 design question; either way they are
compared with externally trusted hashes, never trusted because the manifest
carries them.

## Native limits table

Same keys as `DEFAULT_LIMITS`. Values are *founder* (F3, NC-8, NC-10):

| Key | Native bound |
|---|---|
| `maxNativeSessions` | 1 per manifest (one session per unit) |
| `maxModelSessions` | 1 |
| `maxChildProcesses` | NC-8 |
| `maxNetworkConnections` | NC-1 (bounded, non-zero only for the allowed endpoints) |
| `maxAdditionalCashMicros` | 0 (F2) |
| `maxAutomaticRetries` | 0 |
| others (including `maxAdmissionSeconds`, which bounds admission freshness) | unchanged from offline |

Every value above its maximum is refused as `invalid-budget`. Session wall time
is not a manifest limit: it is the host run limit (`HostLimits.wall_seconds`),
today capped by `harness_lab.MAX_WALL_SECONDS = 60`. A native-only bound up to
the F3 30-minute unit cap is a separate reviewed change (T006).

## Environment hash inputs

The environment SHA-256 is the canonical digest of: OS product version and
build, architecture, isolation mechanism identity and binary hash (NC-2),
profile/policy bytes, Claude executable hash and version, credential method
identifier (never a secret), network allow-list and enforcing component hash,
limit values and probe catalog version. Any change produces a new hash, which
fails both `_check_backend` and `_check_transport` until re-qualified.
