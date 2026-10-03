# Pre-PR review corrections

The read-only review of candidate `02cae5c` found two P2 defects after the founder
accepted frozen candidate `4dd52c8`. That historical approval and its evidence
remain bound to the original bytes; they do not silently approve corrected code.

## R3: Recover abandoned private reference locks

A killed Git reference transaction can leave `refs/heads/result.lock`. Previously
fsck rejected that lock and both resume and abort were stranded. Recovery now
validates the sealed manifest/state, private configuration and admitted reference,
then removes only the known index/result-reference scratch locks while holding the
coordinator lock, before fsck. Surviving Git children retain the coordinator FD
and exclude recovery. Verification remains read-only. Invalid state retains locks.
The regression kills a real prepared Git transaction and tests both resume and
abort, read-only verification, and refusal to clean an invalid state.

## R4: Retain one invocation budget

Execution, recovery and verification now carry the same budget from preparation
through the consuming phase. Elapsed time, command count and output are cumulative.
Only the sampled scratch root moves after admission scratch is removed; peak
scratch accounting is retained. A fresh invocation gets a fresh budget. Regression
controls consume 31 seconds in each phase using budget timestamps, and exhaust
command/output counters after preparation; each must fail rather than complete.
The shared frozen M2 runner is unchanged. The reproduction harness timeout is
600 seconds to allow the expanded test suite; each runtime invocation remains
limited to 60 seconds.

## Corrected candidate acceptance

The corrected executable candidate and fresh reproduction are recorded separately
from the original accepted candidate. Updated assurance is human-review pending
until an explicit decision on the corrected frozen candidate is recorded.

## Obtained correction evidence

Executable candidate: `fb613da6db069b5d5fe101b82a7c089f9c4b5e7c`.
The [clean reproduction](../../examples/runtime/m4-corrected-reproduction.json)
passed all 19 tests in 126.510 seconds, with clean inputs unchanged during the run.
The quick profile escalated to sensitive validation and passed 330 tests, with
4 disclosed skips, plus all selected controls. See
[verification record](remediation-verification.json).
The earlier approval is preserved in [accepted-assurance-4dd52c8.json](accepted-assurance-4dd52c8.json)
and [founder-review.json](founder-review.json); current assurance is pending review
of the corrected frozen candidate.
