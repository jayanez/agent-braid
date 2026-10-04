# C2 execution contract

Implementation contract `isolated-preparation-serial-publication-v1` is subordinate
to ADR 0020. This draft records the implemented engineering boundary; whole-M4
acceptance and independent review remain pending.

The admitted language remains 2–4 immutable ordinary-text A/M patches. A fresh
consumer reconstructs the serial manifest and all portable replay evidence.
`parallel-owned-operator-grant-v1` is separate from C1's serial policy revision;
every grant binds that revision, full plan, manifest, destination and action.

The scheduler groups consecutive operations in the acknowledged order into
waves. Every dependency must belong to an earlier completed wave. Path equality
or ancestor/descendant overlap prevents sharing a wave. It never reorders the
operator's acknowledged checkpoints. The serial reference derives each wave's
immutable input commit and tree, exact patch digest, before modes/blobs, writes,
expected A/M effects and independently computed worker output tree. Shared Git
objects are read-only; no unknown footprint qualifies for a wave.

Each worker owns a separate bare Git repository, object store, index and sanitized
process environment. Workers only fetch the immutable prepared preview and apply
fixed patches to their own indexes. They cannot publish coordinator checkpoints
or mutate source storage. The shared worker-stage budget is 60 seconds, 256 Git
commands, 8 MiB captured output, 2 MiB per command and 64 MiB sampled scratch for
at most four workers. A worker failure or cancellation fans out to siblings. There
is no hard child memory cap; sampled scratch can overshoot between checks.

After successful preparation, the coordinator durably records the preparation
receipt in the owned operator store, then the accepted serial runtime alone
publishes its private checkpoints using compare-and-swap. Workers never become
publication authorities. A complete private result requires both deterministic
worker tree/effect replay and the accepted private Git result verifier. This does
not establish semantic source-code correctness or arbitrary interleaving safety.

The receipt is bound to the policy plan and survives serial interruption. An
already consumed grant only inspects existing state. A fresh purpose-bound resume
or abort grant reconciles the private result without rerunning workers. If the
process dies before a private run exists, the consumed grant cannot dispatch
again: inspect owned state and issue a fresh explicit grant for a new attempt.
Transient worker scratch is disposable and confers no recovery authority. A
missing or corrupt journal prevents a verified combined report; a digest alone
cannot establish the historical execution or timing of workers.

Recorded start/end intervals, Git command/output/scratch counts, integer CPU
nanoseconds and process-lifetime peak child RSS are observations. The verifier
checks their structural consistency; its independent replay proves only the
bounded tree/effect claim. Overlapping worker intervals do not prove simultaneous
CPU execution or positive speedup. All costs, including verification, rehearsal,
serial publication and cleanup, belong in C4's comparison.
