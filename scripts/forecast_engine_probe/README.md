# Offline harness diagnostics

This directory contains development sources, not an admitted execution package.
The consumed v8 request and receipts remain unchanged. Its reviewed Git-bound
test bytes retain their historical identities even as current test files change.
Changing these sources does not renew approval or qualify the environment.

The 2026-10-15 offline repair covers three independently reproducible defects:

- Swift `Character` splitting misses CRLF-delimited event and completion records.
  `engineConsoleLines` splits UTF-8 bytes directly and waits for a complete LF-ended
  record, including when CR and LF arrive in separate reads. This also avoids
  the macOS/Linux Foundation substring difference found by CI. Native preflight and
  both host marker predicates share this implementation.
- A subsecond socat inactivity timeout can return exit zero after only the first
  response block. The synthetic Unix peer reproduces the 4096-byte cutoff with
  the previous options. The corrected command retains `STDIO,ignoreeof`, the
  one-second outer `timeout` and the 1 MiB response bound, without `-T0.8`.
- `parse_events` already decodes the event's base64 layer. The incomplete-log
  fallback now validates these bytes directly and encodes them only for the JSON
  output field. Test fixtures use the same single layer emitted by the guest.

Run the stdlib tests with an isolated Python 3.12+ environment:

```sh
python -m unittest tests.test_forecast_engine_probe tests.test_forecast_engine_console tests.test_forecast_engine_serial -v
```

`test_forecast_engine_console` compiles only the pure Foundation parser when
`swiftc` is available; it imports no Virtualization framework. Compiler absence
is an explicit skip. For additional offline checks, provide an isolated socat
binary and, optionally, the retained private console:

```sh
FC2_TEST_SOCAT=ISOLATED_SOCAT FC2_RETAINED_ENGINE_CONSOLE=PRIVATE_CONSOLE python -m unittest tests.test_forecast_engine_transport tests.test_forecast_engine_console -v
```

The socket peer is synthetic and owned by the test. Its stalled-response test
uses a host subprocess deadline; it does not dynamically exercise GNU timeout
inside Linux. The retained v8 input must remain refused: replay can recover its
bounded incomplete diagnostic and recognize its markers, but cannot repair the
truncated historical HTTP record or convert that failed attempt into qualification.
No test here starts a VM, daemon, container or model, installs an approval pin, or
prepares another execution request. Guest behavior after these changes remains
unexecuted. T007 and T008 remain subject to their existing separate gates.
