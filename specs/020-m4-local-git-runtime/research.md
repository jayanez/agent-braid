# Engineering decisions

Use deterministic fixed-patch serial execution to reuse M1 immutable provenance
and M2 isolated-index semantics. A private durable ref and reconstructible
write-ahead state distinguish the runtime increment from the temporary prototype.
Use expected intermediate trees as enforcement, not independent scientific proof.
Run Git only with bounded output/time/command/scratch budgets. macOS rejects RLIMIT_AS in this environment; this increment explicitly declares no hard child memory cap instead of presenting a fallback as enforced.
OS advisory locking avoids stale lock ownership after a process crash. A full
security sandbox, source promotion, arbitrary code and external adapters are
separate contracts. No external SDK is needed and no dependency is added.
