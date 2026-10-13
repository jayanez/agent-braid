# Read-only auto-recharge interface observer

`agent_braid.tooling_interface_observer` adapts an actual browser read to the
approved [source contracts](SOURCE_OBSERVER.md). It requires an explicitly
installed reader and trusted provenance verifier. It starts no work at import
and contains no browser automation, login, cookie access, provider request,
setting toggle or credential-file access.

The adapter is implemented; a real pinned reader/verifier installation and its
native capture remain separate requirements. The checked boolean, session
digest and procedure hashes cannot authenticate themselves.

## Reader and verification boundary

The caller freezes an `OperationalProcessRouteBinding` used for identity only,
an `InterfaceSourcePin` identifying acquisition and verification procedures,
the review-record digest and an independently authenticated
`NativeProfileWitness`. That witness contains account/namespace digests, the
keyed email binding, key fingerprint, original profile time and private profile
receipt digest. Its constructor does not authenticate the profile.

`browser_reader(cancel_event)` returns `BrowserInterfaceRead` with the explicit
observed recharge control, original observation time, authoritative current
account email, session-binding digest, private trace bytes and origin. The
reader must observe account and control in the same authenticated session,
using only permitted read-only screenshots/accessibility/browser-state reads.
The origins accepted here are `https://chatgpt.com` for Codex and
`https://claude.ai` for Claude. Missing identity or trace, another origin,
non-boolean/unknown controls and enabled recharge refuse.

The required verifier method is:

```python
verify_browser_read(observed, native_profile, binding, pin,
                    review_sha256, organization_declaration_sha256)
```

It must authenticate the exact owned browser snapshot and native-profile
witness against the pinned procedures, verify current-session correspondence,
and verify the frozen review/organization declaration. It accepts by returning
`None`, otherwise raises. Returning a boolean, including `False`, refuses.
The installed verifier must verify its own reviewed procedure bytes and reader
provenance; copying the pin fields into a response is insufficient. This module
never loads code selected by an untrusted response. A synthetic test verifier
is unsuitable for native acquisition.

## Private account correspondence

`private_email_binding(email, private_key)` and `key_fingerprint(private_key)`
must be used identically by the independently trusted profile recorder and the
interface adapter. The private key must have at least 32 bytes and must come
from a private random-key installation. The adapter receives it in memory and
never writes it. The fingerprint binds the two witnesses to that exact key.

Email canonicalization normalizes Unicode to NFC, strips surrounding whitespace
and lowercases only ASCII A–Z. It requires an exact built-in string, one `@`, nonempty local/domain parts and no internal
whitespace or control characters, with a 320-byte ceiling. The domain-separated
HMAC-SHA256 covers the canonical email; fingerprint SHA256 uses a separate
domain. Matching uses constant-time comparisons. This is the registered
provider-account matching convention, not a general equivalence rule for all
email servers.

`NativeProfileWitness.email_binding_method` freezes the explicit method. The
default `interface-email-v1` uses email domain `agent-braid-interface-email-v1`
followed by a NUL byte; its key fingerprint uses SHA256 over the separate
`agent-braid-interface-key-v1` domain, NUL byte and private key. The Claude-only
`claude-account-email-v1` compatibility method preserves the reviewed private
collector's `agent-braid-m45-account-email-v1` domain plus NUL. Its original
key fingerprint is the first 16 hex characters of HMAC-SHA256 over
`agent-braid-m45-key-fingerprint-v1`. The public witness field stores SHA256
of those original 16 ASCII characters; this identifies the original short
fingerprint and does not upgrade its collision strength. No method can recover
or re-domain an email HMAC without the original email and key. Recorders must
preserve the method and authenticate its collector provenance; silently treating
the two domains as interchangeable refuses account correspondence. Full Unicode
case folding is excluded because it can merge distinct addresses such as
`strasse` and `straße`.

The actual email remains ephemeral and is excluded from DTO representation and
all exported records. The adapter retains no raw browser trace; it returns its
digest. The installed reader/verifier must preserve any required authentic
trace in its independently controlled private evidence store and must avoid
logging the email, key, cookies, session secrets or trace contents. The digest
is a reference to that witness, not an authenticity proof.

## Acquisition, freshness and cancellation

Construct `InterfaceObserver` with the binding, profile, pin, private HMAC key,
review digest, reader and verifier. Claude also requires the frozen SHA-256 of
the owner's single-organization declaration; that scope retains the limitations
in the Claude contract. Codex accepts no Claude organization declaration.

`capture(cancel_event=...)` is explicit and one-shot. A background worker covers
both reading and verification with a deadline of at most 60 seconds. It owns
immutable input values, checks before and after verification and rejects a
clock regression. The adapter does not automatically retry or substitute
another source. Its generic worker cannot forcibly terminate an external
reader; `stop()` signals cancellation and `drain(timeout_seconds=...)` reports
whether the reader/verifier actually exited. Timeout, cancellation or main
thread interruption discards results. External cancellation is rechecked after
the completed wait and immediately before returning an observation;
`KeyboardInterrupt` and `SystemExit`
propagate after cancellation. A late worker result cannot be returned by a
new capture on the same observer.

Use this adapter inside `SourceProducer`'s shared host-serialization lifecycle.
The enclosing producer must retain its process-shared lock until this observer
has drained. Returning immediately from a timed-out nested capture while its
reader still runs would release serialization too early. A native adapter must
honor cancellation and complete its bounded cleanup before returning control
to the enclosing acquisition callback.

Original interface timestamps are retained. Codex's maximum age is 60 seconds;
Claude may explicitly choose up to 900 seconds only for this interface source.
Profile/interface skew is at most 60 seconds for Codex and 600 seconds for
Claude; a future profile time refuses. These rules do not extend quota or
process freshness. A delayed verification cannot refresh an old observation.

## Sanitized output and evidence limits

`InterfaceObservation.as_dict()` exports identity bindings, original UI/profile
times, expiry, review/source/verifier pins, private HMAC/key fingerprints and
trace/profile-receipt digests. It includes no raw identity or trace.
`as_auto_recharge_payload()` produces the host contract's exact payload. For
Claude it preserves the original UI/profile times and references the private
collector receipt and sanitized recorder record.

When creating the enclosing source receipt, preserve
`InterfaceObservation.observed_at` as `observedAt`; never assign a cache read or
publication time. Keep its pins and complete account/namespace/review binding,
then authenticate the exact enclosing receipt through the source verifier.
The output is no launch permit, registration approval, account-wide billing
attestation or cash reconciliation.

`tests.test_tooling_interface_observer` uses explicitly fake readers and
verifiers. It covers private account mismatch, missing/unsafe controls,
origin/session refusal, original timestamps and host-specific ceilings,
post-verification expiry, immutable snapshot ownership, cancellation,
interruptions and bounded reads. No actual browser source, native provider
session or human acceptance was obtained by these tests.
