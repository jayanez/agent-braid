<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# System One shadow mode

**Status:** SPEC-066 S1.5a candidate. Shadow mode is **off by default** and starts
only after explicit consent. It measures how often the exact System 2 analyzer
cannot decide a pair of operations. It does not improve, change or gate any
result. See [SPEC-066](../../specs/066-system-one-shadow/spec.md) and
[ADR 0034](../adr/0034-system-one-shadow-advisory-boundary.md).

## What shadow mode is

With shadow mode on, each successful `analyze-work` call (AIM or Git) of the
plugin MCP server writes one structural decision episode to a private local store
beside the unchanged System 2 result. The episode describes the pairs System 2
analysed: its classification, reasons, coverage and a few structural counts. It
also records the answer of the installed System One backend for the pair
question (decision point DP-1, unknown-pair resolution).

- Every MCP envelope is byte-identical to the envelope with shadow mode off.
- The write happens after the envelope is built, on one background worker with a
  single-slot queue. The request never waits for it. When the worker is busy, the
  episode is dropped and counted in memory (`busy`).
- Shadow work never raises into the caller. Over its 50 ms work budget, the
  episode is recorded as `skipped`.
- `analyze` records an episode only when its result carries the interaction report
  (an AIM analysis); a Git replay `analyze` result carries none and records nothing.
  Artifact-backed reports above 1 MiB are not decoded and record nothing.
- Nothing is uploaded. There is no hosted service.

## What is recorded

One JSON line per episode, schema `agent-braid-s1-episode/v0.2` (the
[contract](../../specs/066-system-one-shadow/contracts/episode-v0.2.md) is
normative). Lines written as `v0.1` by earlier versions stay readable. Every
string comes from a closed vocabulary except the random episode identifier, the
UTC day, the backend identifier, the manifest digest and the salted pseudonyms.

| Group | Fields |
|---|---|
| Episode | random `episodeId` (UUID4, not derived from any input), UTC `day`, `surface`, `operation`, `analysisKind` (`aim` or `git`), analyzer version and rule set, `operationCount` |
| Pair counts | `pairCount`, `classificationCounts` for all pairs, `pairsRecorded` (at most 64 pairs per episode; the rest are counted but dropped in report order) |
| Per pair | System 2 class, whether it was determinate, reason codes, constraints, coverage, shared-resource count, dependency flag, per-side effect kinds (`read`, `write`, `call`, `transform`, `emit`, `delete`, `deploy`, `unknown`) |
| Structural features | per-side and shared counts over seven resource classes (`src`, `test`, `docs`, `config`, `lockfile`, `generated`, `other`), maximum path depth, same-parent-directory count, top-directory overlap |
| Pseudonyms | per-side and shared resource hashes: at most 32 each, 16 lowercase hex characters each |
| System One | `systemOne` status, reason, backend identifier, manifest digest, decision point `DP-1`, answers, elapsed microseconds |
| Boundary | `executionAuthorization: false` |

Resource classes come from deterministic rules on the resource string (for
example `package-lock.json` is `lockfile`, a `tests` directory is `test`). The
string itself is evaluated in memory and not stored.

The pseudonym of a resource is the first 16 hex characters of an HMAC-SHA256 of
the exact resource string, keyed with a secret that stays on this machine and
with the configured source root. The same resource in the same repository maps to
the same pseudonym; the same string under another repository maps to another one.
Without the salt file, pseudonyms cannot be linked back to a resource by guessing
common paths. This is pseudonymity within your machine, not anonymity: anyone who
holds both the store and `salt.key` can test candidate paths. If no salt is
available, `resourceHashes` is `null` and the other features are still recorded.

## What is never recorded

- resource names and paths, repository names and the source-root path
- operation instance or attempt identifiers
- analysis identifiers and digests of the input
- prompts, request or result content and reason sentences
- host names and user names
- the secret and the per-repository salt

The secret and the source root also never appear in reports, logs, status output
or error text. The report prints counts only and never prints pseudonyms.

## Where it lives

The store is fixed at `~/.local/share/agent-braid/system-one/`, independent of
repositories and host configuration. It reuses the telemetry path rules: canonical
paths, no symlinks, outside repositories and owned by you.

| Entry | Content | Permissions |
|---|---|---|
| directory | the store | owner only (`0700`) |
| `episodes-<UTC date>.jsonl` | one day file | `0600`, single hard link |
| `salt.key` | 32 random bytes | `0600`, single hard link |
| `store.lock` | lock file | `0600` |

A day file holds at most 4 MiB; an episode that would exceed it is refused and
counted in memory. Thirty UTC dates are retained, applied when the store is read
or written. No daemon removes older files in between. A busy, unsafe or full
store refuses the episode and never blocks or fails the caller.

## Enable

Consent is one global key in the plugin registry, like telemetry consent, and is
never implied by it. Preview first, then apply with the digest shown, then
reconnect the MCP server:

```sh
"/installed/plugin/launch" plugin setup --home "REGISTRY_HOME" --system-one shadow
# Inspect the preview, then repeat with:
# --apply --preview-digest THE_EXACT_PREVIEW_DIGEST
```

Read `plugin-status` after reconnecting. `systemOne.activeMode` is `shadow` once
the new connection runs with the consent; `systemOne.configuredMode` shows what
the registry holds and `reconnectRequired` tells you when they differ. `plugin-status`
also reports the store location, whether it exists (`store.present`) and
`episodeRetentionDays`, never episode contents. With the value `off` or absent,
the registry bytes and configuration digest stay as before.

The standalone portable server takes `python -m agent_braid.tooling_mcp
--system-one shadow` instead. See [native plugins](NATIVE_PLUGINS.md) and
[install](INSTALL.md) for the surrounding setup.

## Report

```sh
agent-braid system-one report
agent-braid system-one report --format json
```

The text report prints, for the retained dates, episode counts per day,
operation, System 2 class and System One status, and the share of System 2
`unknown` pairs (the DP-1 opportunity). The JSON form has schema
`agent-braid-s1-report/v0.1`: per-day and total counts, `pairsRecorded`,
`pairsAnalysed`, `unknownPairs`, `unknownShare` (over all analysed pairs),
`invalidLines`, this process's refusal counts, `limits` and
`executionAuthorization: false`. The report reads only the store, creates
nothing and never prints episode bodies. Episodes skipped before storage are
known only to the process that skipped them.

## Purge and turn off

```sh
agent-braid system-one purge          # asks for confirmation
agent-braid system-one purge --yes    # no prompt
```

Purge deletes the day files, `salt.key` and the lock, then the directory when
nothing else is in it, and prints a JSON summary. Removing the salt makes
pseudonyms in any copy you made elsewhere unlinkable to new episodes. Purge does
not remove copies, snapshots or backups you made; remove those yourself. If
another process holds the store, the command refuses and you retry shortly.

To stop recording, preview and apply `plugin setup --system-one off` the same way
and reconnect. Turning it off keeps the store; run `purge` to delete it.

Both `system-one` store commands accept `--telemetry local`; see
[TELEMETRY.md](TELEMETRY.md) for that contract.

## Non-claims

- Shadow mode makes no accuracy, calibration or promotion claim, and measures no
  utility. No outcome is joined to an episode in S1.5a.
- The reference backend (`stdlib-rule-fixture-v1`) always abstains with the reason
  `calibration-absent`. A different installed backend or manifest digest is
  recorded as `refused` with reason `identity-mismatch`.
- `executionAuthorization` is `false` in every episode and report. Shadow mode
  creates no grant and widens no filesystem trust.
- The registered hypothesis H-S1 (a calibrated local backend advising
  `likely-independent` on System 2 `unknown` pairs within a bounded false
  independence rate and a minimum coverage, see the spec) is untested. Nothing in
  S1.5a tests it.

## Limits

- Only DP-1 pairs are instrumented, and only for `analyze-work` and report-bearing `analyze` results.
- The 50 ms budget is a work budget checked between stages. It bounds the
  episode computation, not a filesystem write. A filesystem call stalled below
  Python has no separate hard deadline, so a stalled write can keep the
  background worker occupied. The request path is unaffected, and while the
  worker is occupied further episodes are dropped as `busy`.
- Refusals and internal errors before storage exist only as in-memory counts of
  the process that met them.
- Counts depend on use. A quiet week yields few episodes, and one machine is not
  a population.
- Pseudonyms are kept only while their value is under evaluation; they are
  removed if they carry no measured benefit.
