# Refinement decisions

The existing runtime has a trusted owned POSIX/Git boundary and private result; it excludes source promotion, arbitrary code, hostile same-UID interference and external write adapters. This feature assesses those gaps rather than retroactively treating accepted evidence as a stronger contract.

Prefer manual export while promotion ownership/ref/worktree premises remain unresolved. Prefer NO-GO for arbitrary code where OS enforcement is unavailable. Prefer simulated external outcomes while rights, idempotency and uncertain-failure semantics remain unspecified. Each assessment can conclude rejected/watch without making the useful analyzer dependent on a broader runtime.

No backend/library/provider version is selected here. Inspect current installed capabilities and fetch primary documentation (Context7 for APIs when available) in the dedicated assessment task. Installation and paid usage require specific authority and are never a prerequisite to reporting feasibility.
