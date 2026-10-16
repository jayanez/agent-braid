# Source producer and supervisor cache

`agent_braid.tooling_source_observer` adds a producer/consumer boundary around
the approved [Codex](CODEX_SOURCE_CONTRACT.md) and
[Claude](CLAUDE_SOURCE_CONTRACT.md) source contracts. It starts no worker at
import, reads no credentials, performs no provider request, and changes no
payment setting. Native collectors, account-bound interface observations and
process attestations remain required external acquisition procedures.

## Authentication and publication

Create `SourceObserverCache(contract, expected_contract_sha256=...,
receipt_verifier=...)` with the exact frozen per-slot contract and an explicitly
installed `SourceReceiptVerifier`. There is no permissive default verifier.
Its `verify_receipt(kind, receipt, pin)` must authenticate the complete receipt
against the independently trusted acquisition/verification procedures, accept
by returning `None`, or refuse by raising. Matching receipt labels or hashes
alone is insufficient. Each input to the verifier is deeply immutable.

`publish(receipts, now=...)` first owns a bounded finite JSON snapshot, checks
composition and authenticates all three exact receipts. It then publishes
atomically. This is a producer operation and must not run inside the supervisor
callback. Authentication failure invalidates the previous snapshot; raw external
exceptions are redacted. Contract mutation, identity drift, sequence regression,
source-clock regression and lifecycle regression also refuse. High-water marks
survive invalidation, preventing a failed refresh from resetting those checks.

`FrozenPrivateReceiptVerifier` supplies a concrete file/pin boundary for private
captured provenance. It requires all three `ProcedureFiles(source, verifier)`,
a private provenance bundle and its independently frozen SHA-256, plus a trusted
`provenance_verifier(kind, receipt, pin, source_bytes, verifier_bytes, bundle)`.
That callable must return exactly `True` after authenticating the witness and
the exact receipt, including reference identity, account correspondence and
process binding. The module verifies opened procedure bytes against the source
contract, refuses writable-by-others files and requires an owner-only regular
bundle. Final symlinks and digest drift refuse. Ancestor directories are part of
the operator's trusted installation. No receipt can select executable code:
this component passes pinned bytes to the externally installed verifier and
never executes them itself.

The bundle digest establishes byte identity, not authenticity. An independently
trusted bundle and verifier are both necessary. This component cannot turn a
synthetic fixture or self-authored matching hash into native account evidence.

## Fast reads and transport

`read(now=..., expected_binding=..., phase=..., process_id=...,
process_birth_sha256=...)` performs bounded local composition of the original
receipts. It never reads files, invokes a verifier, performs RPC or accesses UI.
Records are capped at 128 KiB. The supervisor retains its separate one-second
callback deadline; scheduling and hardware latency are not guaranteed by an
in-memory implementation. Clock regression, stale data or a different phase,
PID, birth or account/configuration binding invalidates availability.

The result is `AuthenticatedSourceObservation`, with a frozen `.composition`
and deeply immutable `.receipts`. Its `.as_dict()` returns a fresh JSON copy.
No timestamp is rewritten on read. Codex sources retain their contract limit
of at most 60 seconds; Claude's exception of at most 900 seconds applies only
to `autoRecharge`. The earliest receipt expiry, interface observation expiry or
quota reset controls the whole observation. Refreshing quota cannot rejuvenate
an old interface observation.

`source_observation_from_dict(value, contract, expected_contract_sha256=...,
now=...)` returns a base `SourceObservation` containing checked claims. It does
not recreate the authenticated subtype. `check_source_observation(...)` checks
the original receipt set and claimed composition against an exact expected
binding and phase/PID/birth without external calls. DTO types and serialization
are not signatures or admission capabilities: a receiving supervisor still
requires its own trusted source-route verifier. Neither helper converts the
sources into v3 payment booleans or establishes actual cash.

## Explicit acquisition and cleanup

`SourceProducer(cache, acquire, lock_path=..., timeout_seconds=..., utc_now=...)`
is one-shot. `acquire(cancel_event)` must acquire the complete receipt set using
the registered procedures and clean up its own subprocesses or UI resources.
`acquire_once()` runs acquisition and authentication in a background worker,
with an explicit deadline of at most 120 seconds. It rechecks freshness at
publication and never retries automatically. Create a new producer only as an
explicit, separately admitted refresh.

Both host producers must share one canonical absolute lock path in a private
owner-only directory. A nonblocking `flock` serializes acquisitions across
processes on macOS/Linux. Lock symlinks, hard links, permissive files and unsafe
directories refuse. Unsupported locking platforms fail closed. Collectors
invoked outside this lifecycle still require external serialization.

Timeout, `stop()` or an interrupted acquisition invalidates the cache and
signals cancellation. `KeyboardInterrupt` and `SystemExit` propagate after
cleanup; interrupted synchronous publication also invalidates before propagation. Late
results cannot publish. A generic Python worker cannot forcibly terminate its
callback; the cross-process lock remains held until the callback actually
exits. `drain(timeout_seconds=...)` returns `False` while cleanup remains
unknown. No new overlapping acquisition is permitted then. The native
collector adapter must honor cancellation and perform bounded process cleanup
before its callback returns.

## Obtained evidence and outstanding boundaries

`tests.test_tooling_source_observer` supplies only synthetic deterministic
controls: immutable snapshots, explicit authentication, private pin drift,
per-source freshness, lifecycle and clock regressions, expired-cache refusal,
serialization without trust promotion, cancellation, bounded verification,
late-result rejection and lock exclusion in another process. These tests do
not establish authentic provider access, live continuous gate enforcement,
cash reconciliation, native skill discovery or experimental acceptance.

The existing read-only Codex quota observer can supply account-level metadata
within an explicit serialized acquisition. It cannot by itself supply the
bound recharge UI witness or the launched process route. Claude's collector,
interface/account witness and canonical isolated-store process attestation
also remain separate real-source requirements. Native capture still requires
the exact frozen registration and its required approvals.

## Concrete supervisor consumer

`agent_braid.tooling_source_runtime.CachedSourceRuntime` connects one exact
`SourceObserverCache` to the source-route supervisor. Supply the per-slot
`SourceRouteBinding`, the explicit pinned `ProcedureFiles`, an externally
verified local telemetry callable and a UTC clock. Installation verifies the
procedure bytes and exact cache contract. This establishes byte identity;
trust in the installed receipt verifier and acquisition procedures remains
external and must be recorded with the registration.

Pass `runtime.observe` as the consumer and `runtime` as
`source_route_verifier`. Both read only the authenticated in-memory cache;
neither invokes acquisition, UI, provider RPC or a receipt verifier. The runtime
rejects absent/invalidated/superseded observations, legacy-route mixing and
missing kernel birth. Its verifier compares the exact original receipt set
against the current cache for the requested phase and process. The supervisor
independently rechecks the source composition and deadlines. Local telemetry
still needs its own cost/stop authenticator. Publish new snapshots from the
separate serialized producer before each required lifecycle transition; an
unavailable running snapshot stops before releasing stdin.
