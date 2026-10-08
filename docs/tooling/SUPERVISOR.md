<!-- SPDX-License-Identifier: CC-BY-SA-4.0 -->
# Local process supervision boundary

`agent_braid.tooling_supervisor.run_supervised` is a bounded, one-shot POSIX
process adapter for a future SPEC-044 capture runner. It starts one pinned local
executable with `shell=False`, an explicit environment, an explicit private
working directory, and a new process group. It multiplexes stdin/stdout/stderr,
keeps stdout and stderr as separate mode-0600 partial artifacts, and writes
exclusive start and outcome receipts. A used output directory is never retried.

The caller provides a `ProcessRequest`, frozen `BudgetCaps`, and an observer
that returns `TelemetrySnapshot` values containing cumulative measured costs
and externally observed stop state. The supervisor refuses before launch when
the executable pin, path separation, initial measurement, freshness, stop
state, or registered caps fail. Source freshness may be configured up to 60
seconds; the separately named `observer_timeout_seconds` is capped at one
second. Polling is capped at 250 ms, and each SIGTERM/SIGKILL grace is capped
at one second; caller input cannot request unbounded cleanup waits. Observer callbacks
execute in a bounded daemon thread. A pre-dispatch timeout refuses before launch; a live timeout stops the
process group; a final timeout leaves the result unverified. Calls are never
retried or overlapped after timeout. Since Python cannot safely cancel a
callback thread, a timed-out callback may continue until it returns. The
callback must not itself perform provider/host actions, and the caller must
preserve the timeout as unknown. During execution the supervisor polls that
observer and checks the wall clock, output bound, and optional operator cancellation. On a
stop condition it sends SIGTERM to the process group, then SIGKILL after the
configured grace period, drains pipes within fixed bounds, and attempts to reap
the root process. The observer must authenticate its sources independently;
the supervisor does not authenticate cost/provider data or issue grants.

The caps accepted by `BudgetCaps` cannot exceed the approved ceilings of €25,
4,000,000 tokens, 57,600 seconds (16 hours), 4 GiB RSS, and 5 GiB logical disk.
These are maximum bounds, not permission to run. The request must bind lower
registered caps when applicable. Unknown, stale, non-finite, negative, or
regressing observations fail closed; missing measurements are never converted
to zero. A measurement failure after dispatch preserves the attempted outcome
as incomplete. Status `completed` requires process exit zero and a clean group
state; descendant cleanup, unknown telemetry, cancellation, cap exhaustion,
timeout, output overflow, or launch drift cannot be reported as success.

## Example composition

```python
from agent_braid.tooling_supervisor import run_supervised

# `request`, `caps`, and `observer` must be built from the separately
# authenticated registration/admission and operator-authorized private paths.
outcome = run_supervised(request, caps, observer, cancel_event=cancel_event)
if not outcome.completed:
    # Preserve the partial receipts and require inspection; never auto-retry.
    raise RuntimeError(f"capture process incomplete: {outcome.status}")
```

No raw environment values, argument strings, or stdin contents are copied into
receipts. The receipt records the executable and argument hashes, stdin byte
count, environment entry count, measurements and their source hashes, output
hashes, and bounded status metadata. A failed or timed-out final observation is
recorded by exception type in `observerFailure`, even when another stop reason
already determines the incomplete status; secret exception text is omitted.
Optional `FilePin` entries bind
configuration/skill pathnames to SHA-256 observations before and after the
pre-dispatch callback, immediately before `Popen`, and again after process
launch. Paths are hashed in the
receipt. These are pathname observations, not an atomic `fexec` guarantee: a
file may change between the final hash and the operating system opening it.
The external verifier must still establish source/configuration identity and
actual host provenance. The output files remain private and may
contain sensitive session output; callers must retain them only in the
registered private artifact boundary.

## Limits

Process-group signaling is best effort. A descendant can escape the group;
group state can be inaccessible or ambiguous; an OS may retain a killed child
as a zombie; and the supervisor cannot prove a provider stopped billing. It
does not control arbitrary host commands, grants, SDK interactions, or network
effects. Process RSS is only as complete as the injected observer and its
sampling boundary; samples are not a continuous peak. Disk accounting must be
provided by an authenticated measurement source. The supervisor cannot provide
a hard provider-dollar cap or guarantee continuous process-tree resource
limits. Any such uncertainty keeps the result incomplete and must be retained
for separate review.

This module does not itself authorize or execute an actual capture. Registered
source rights, provider consent, founder/owner decisions, two independent
human reviewers, exact candidate registration, and external receipt
verification remain separate gates. Tests launch only bounded local synthetic
subprocesses; they make no provider or host calls.
