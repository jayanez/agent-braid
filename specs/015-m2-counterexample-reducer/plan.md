# Implementation plan

1. Add a private reducer that validates the input with the existing verifier,
   derives subset requests from immutable source commits and enumerates bounded
   dependency-closed subsets deterministically. Do not modify the current
   replay engine or schema.
2. Supervise input verification and subset replay in a private process group,
   with a single monotonic 120-second deadline and at most ten candidate subset
   attempts (all proper subsets for four operations). Kill the process group
   on timeout and wait for cleanup. Per-replay Git budgets remain in the
   existing engine; do not claim a shared Git-command, output or scratch quota.
   Return a scoped witness only after the smallest qualifying subset is
   independently verified; a timeout or incomplete search is inconclusive.
3. Add positive, irreducible, tampered-input and budget-failure tests. Run
   proportional and PR validation, freeze evidence and request scoped founder
   review. External validation remains pending.
