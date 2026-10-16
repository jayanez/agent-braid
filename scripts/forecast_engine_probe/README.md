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

The subsequent cancellation review adds a shared pure `SerialInputGate` around
all bounded serial writes. Cancellation and each whole write have one lock order:
a write already begun completes before cancellation; cancellation winning first
prevents sender invocation. The absolute 20-second cleanup deadline is anchored
before waiting for that lock. No overall deadline or write budget is increased.
The pure queued-cancellation and in-flight controls run without Virtualization:

```sh
python -m unittest tests.test_forecast_engine_cancellation -v
```

These host-only Swift tests share a private temporary module cache within one
Python process. A verbose minimal Foundation/Dispatch compilation reports the
compiler version and prepares imported modules within 180 seconds.
Each current fixture is then compiled afresh within the original 60-second limit.
Preparation is attempted once, without retries; a failure remains an error.
The compiler runs in its own POSIX process group, which is killed on timeout.
Each wait/join during failure cleanup is bounded to 5 seconds. Diagnostics retain
only the last 8 KiB, with compiler command, phase and elapsed time. The native
fixture execution deadlines and VM/worker budgets are unchanged.

This separates toolchain preparation from fixture compilation. It does not
establish the exact cause of the historical Linux timeout after PR #527:
run `38874843633` exceeded 60 seconds without preserving compiler diagnostics or
version. The identical source passed in run `38871354533` (approximately 25 seconds
for the first compilation); the following parser compiled in approximately
4.3 and 1.5 seconds respectively. Cold module preparation is a hypothesis, not a
reproduced Linux finding. A fresh private-cache check on Apple Swift 6.4 took
2.142 seconds cold and 0.225 seconds warm; it is host-only evidence, not a Linux
reproduction. The bounded preparation window is a mitigation, not a measured
upper bound or proof that subsequent CI will pass.

The initial bounded Linux diagnosis in run `38880715567` used the same
`ubuntu-24.04` image version (`20261012.334.1`) as the original failing run. It
stopped at the separate `swiftc --version` query after 5.010 seconds, before any
fixture or Foundation compilation. This exposed an additional insufficient
startup budget introduced by the first helper revision. That redundant query has
been removed: the verbose bootstrap reports compiler details within the existing
preparation deadline. The image's versioned install script preinstalls Swift 6.4
and creates compiler symlinks; it does not establish a deferred installer as the
cause. The historical 60-second cause remains unresolved. No diagnostic rerun or
complete suite is implied by that diagnostic result alone.

A separately authorized single follow-up, run `38881821056`, reached compilation
with the corrected harness sources from PR #529 commit
`1f14726899d6ef352b7a45c97c8e48bb55863279`. The first fixture compilation took
19.325 seconds (0.661 seconds user CPU and 0.216 seconds system CPU). Its five-second
process snapshot showed `swift-driver` in state `D`, waiting on
`folio_wait_bit_common`, with 810 major faults and 1 user/3 system clock ticks.
The same fixture with a warm cache took 0.165 seconds; minimal Foundation with a
new private module cache took 0.766 seconds. This strongly supports cold file/page
I/O waits in the observed run rather than CPU-heavy fixture logic. A new module
cache does not reset host binary page caches, and a single snapshot does not
explain the entire delay or prove the historical timeout's exact cause.

The corrected helper then prepared modules in 0.665 seconds and compiled the gate
and parser in 0.214 and 1.015 seconds. Its focused checks passed 17 tests with one
private-console skip. Luna Latest reviewed the results: the observed mechanism is
supported, while the historical timeout remains unproven. On 2026-10-16 the owner
accepted this mechanism-level diagnosis as sufficient to resume ordinary PR
validation and authorized merging PR #529 only after all checks pass and Luna
finds no remaining problems. This acceptance does not prove the historical cause
or authorize further diagnostic, model or VM runs.
