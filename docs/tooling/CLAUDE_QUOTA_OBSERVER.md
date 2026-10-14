# Private Claude quota/profile observer

`agent_braid.tooling_claude_observer` reuses the unchanged private collector from
the reviewed UI/account/isolated-store candidate dated 2026-10-13. It does not
copy that collector into the repository or publish its private outputs. Native
integration and the first live use require review of this new adapter. No live
provider read was performed while implementing or testing this module.

## Frozen archive and build

`verify_private_archive(archive_root, review_root)` verifies the archived
`claude/collector.py`, `claude/routes.json`, historical run context, reviewed
candidate copies and every file named by the frozen review manifest. Opened
regular files must have private ownership/modes and match exact byte pins.
Canonical private root directories, final symlink refusal, bounded file reads
and pinned manifest sizes are enforced. Ancestors are part of the operator's
trusted installation. Historical context equality is not current authentication,
approval of a registration or a native reproduction.

The source constants bind collector SHA-256
`d2b98daaf1861e12b5d27d348081f3b0358f1b4c506fa5fb3655003a4590de13`,
route-manifest SHA-256
`3b50b92c21ef757caf7b22dabaae45b2afdb1ef20903416df8ff990cd753170b`
and Claude Code 2.1.287 binary SHA-256
`6eab8333fe2121553100d8f40bfada384a3e989b94f947e18ba6677a6fcb41ea`.
The private review/context pins are retained in the implementation. They identify
reviewed bytes and do not create review approval themselves.

`load_collector_for_offline_checks(...)` explicitly loads those verified bytes
under an inert module name. It calls no diagnostic, Keychain reader or endpoint.
Imports otherwise start no work. These offline operations remain distinct from
`ClaudeQuotaObserver.read`.

The installed PATH build observed by the coordinator on 2026-10-14 was 2.1.285,
with a different digest. The adapter refuses it. The caller must explicitly
select an independently verified reference artifact matching the registered 2.1.287 pin,
or separately review a new build/pin update. There is no PATH fallback, implicit
selection of an older executable or silently refreshed pin.
The coordinator subsequently retained an exact matching 2.1.287 artifact from
the official package with verified package integrity. That separate artifact
must be explicitly selected and bound to the registration; it does not change
the PATH build or authorize an authenticated metadata read. This artifact is
static eligibility/source-knowledge context; the quota observer never launches
Claude Code or selects it from PATH.

## Explicit producer-side acquisition

Construct `ClaudeQuotaObserver` with private archive/review roots, an explicit
`native_reference_artifact` and Python interpreter with its frozen digest, canonical
isolated configuration directory and expected credential-store suffix, frozen
profile account/organization/namespace identities, private identity-key path
and file digest, original 16-hex key fingerprint, and a trusted namespace
verifier. No default maps an organization digest to a process namespace.
`namespace_verifier(account_digest, organization_digest, expected_namespace)`
must independently establish that frozen correspondence and return `None` or
raise. Any other return value refuses.

`read(new_private_output, serialized_read_only=True, cancel_event=...)` requires
explicit external serialization, preferably inside
[SourceProducer](SOURCE_OBSERVER.md). Other host collectors must use the same
process-shared lock; the observer's instance lock alone cannot serialize other
instances or processes. This blocking function must never be the supervisor's
one-second consumer callback.

The adapter pins the inspected static reference artifact, interpreter, collector, routes,
private review context and identity-key file before acquisition. The suffix must
match SHA-256 of the exact canonical configuration path, as in the reviewed
collector. A plaintext credential-file alternative refuses before any process
starts. The unchanged collector additionally rejects configuration/environment
and key-helper ambiguity and validates its isolated store against the profile.

Acquisition runs the verified collector in an owned private Python subprocess
with isolated interpreter mode and site initialization disabled (`-I -S`). A
static loader reopens and checks collector
and manifest bytes inside the child before calling `run_personal_diagnostic`.
It also verifies the exact private key bytes opened in the child and supplies
those same validated bytes to the original collector's HMAC logic, rather than
reopening the key path after checking. The archived collector file remains
unchanged; the reviewed loader replaces only its key-file loader using the
original format/range/nonzero checks. OAuth acquisition, profile/usage transport
and canonicalization/HMAC algorithms retain their original procedures. Freeze
the new adapter/loader bytes as part of the source procedure; the diagnostic's
legacy `adapter_sha256` identifies the archived file alone.
The new output must be in the collector's original private directory and must
not exist already. No existing receipt is overwritten. Stdout/stderr are
discarded; exceptions never expose provider bodies or account values.

The child retains the original OS-account HOME and a fixed system PATH. It
receives the explicitly registered configuration directory as a collector
argument and CLI context in the environment. It does not export
`CLAUDE_CONFIG_DIR`: the archived collector refuses ambient store overrides and
derives its isolated store from the explicit argument. Acquisition runs
without inherited API credentials, provider overrides, proxies, Python loaders,
custom TLS configuration or key logging. The private key's path is passed as a
reference; key bytes, tokens and emails are never command arguments or logs.
The reviewed collector resolves the existing OAuth credential through Keychain
and performs direct TLS profile/usage GETs and its conditional metadata read.
It uses request metadata derived from the inspected CLI source, including its
User-Agent, without executing that CLI. It refreshes no token, logs in to no
account, changes no payment control and sends no inference prompt.

The interpreter, reference artifact, key file and canonical configuration
directory are checked initially, again immediately before `Popen`, and after
collector/group cleanup before sample publication. Archive/context pins are
also rechecked before publication. Observed drift refuses the whole sample.
These are bounded path observations, not an atomic guarantee that the OS
executed immutable code. The installation and its ancestor directories must
remain trusted and stable throughout acquisition; an adversarial same-UID
path-swap race can defeat separate path checks. This adapter uses no `fexecve`
claim or cross-platform executable-identity guarantee. The child key check is
stronger: its HMAC receives the exact bytes that passed the opened-file digest.

## Original observations and private projection

Both profile and usage must be successful explicit GET observations, bind the
exact private collector pins and declared inspected-build context, and have
original aware timestamps within at most 60
seconds. Collection/profile/usage completion ordering is checked. Profile and
usage must each report `extra_usage_enabled: false`; absence, `null`, a number
or disagreement refuses. Included five-hour/seven-day quota values must be
finite, below 100 and have future reset times.

The profile's account and organization must match independently frozen hashes.
The original keyed email witness and fingerprint must be present. Its isolated
store suffix and both account/organization configuration comparisons must be
explicitly bound; missing/unknown correspondence refuses. The usage receipt
normally lacks identity fields: its correspondence rests on the exact pinned
collector's same-token serial pass plus the trusted namespace verifier, rather
than inventing identity from that absence. Any identity field it does carry
must agree with the profile.

`ClaudeQuotaSample` is a private immutable metadata projection. `evidence_claims()`
states `nativeProcessObserved: false` and identifies direct collector TLS
acquisition separately from the static reference digest/version. The legacy
receipt's self-declared `candidate.binary_sha256` is checked only against that
inspected reference context; it cannot prove native process execution.
The sample retains the
original profile/usage times, matched store suffix, keyed account witness,
private quota values and opaque sample/profile receipt digests. Sensitive
identity/usage fields are excluded from representation. `as_quota_payload()`
returns a fresh private quota payload; it is not a public report. The sample
expires at the earliest profile/usage age limit or quota reset. Expensive
verification cannot retimestamp or extend it.

`as_native_profile_witness()` preserves the archived account HMAC method
`claude-account-email-v1`. Its canonicalization is NFC, trim and ASCII-only
lowercase; its email HMAC domain is `agent-braid-m45-account-email-v1` plus NUL.
The archived key fingerprint is the first 16 hex characters of
HMAC-SHA256 over `agent-braid-m45-key-fingerprint-v1`. The interface witness's
64-hex fingerprint field contains SHA-256 of that original 16-hex ASCII value.
This identifies the original short fingerprint; it is not a replacement
full-length key fingerprint or a re-projection of an irreversible email HMAC.
The frozen interface procedure must explicitly select this matching method.

## Cancellation, cleanup and remaining gates

The private collector has an explicit default 90-second deadline, capped at
100 seconds, within an outer producer budget of at most 120 seconds. Cancellation
is checked before spawn, during polling, at completion and before return. No
retry, credential refresh or fallback occurs. All exits terminate the owned
process group and reap its leader before releasing the instance lock. Interrupts
during cleanup propagate only after cleanup.

If a process/descendant cannot be confirmed stopped, cleanup deliberately
remains unresolved in the calling worker: the enclosing producer invalidates
its cache at its own deadline and retains serialization until the callback
actually exits. Do not detach this acquisition from that lifecycle or release
its shared lock while cleanup remains unknown.

The sample does not bind a launched Claude host, verify recharge UI, attest
continuous provider-operation gating or reconcile actual cash. It cannot be
converted to a v3 payment observation. Authenticated source-receipt composition,
native process attestation, account-bound UI observation, exact registration
approval and final acceptance remain separate requirements.

`tests.test_tooling_claude_observer` uses synthetic private archives, fake
receipt data and mocked subprocesses. It checks pins/modes/context, inert
loading, unknown control/identity refusal, freshness, quota exhaustion,
namespace correspondence, environment isolation, static-reference drift,
interpreter/key/configuration changes before spawn or during collection,
exact opened child-key validation, and cancellation/
group cleanup. The real retained archive also passed an offline byte/mode/context
check during implementation; that operation acquired no native credential and
made no provider request.
