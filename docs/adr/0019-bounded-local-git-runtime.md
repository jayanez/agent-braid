# ADR 0019: Bounded authorized local Git runtime

- **Status:** Accepted by the founder on 2026-10-03 against frozen candidate `4dd52c8d1e54a8813e6113e09a772a371856f9a8`; [decision record](../../specs/020-m4-local-git-runtime/founder-review.json).
- **Date:** 2026-10-03
- **Constitutional articles:** 6, 7, 12–16, 19–25

## Context

M1/M2 analyze and rehearse immutable fixed patches. Their consultative records
cannot authorize execution. M4 needs a separately authorized, durable local
consumer with enforced effects and recovery. M3/M3.5 are independent tracks.

## Decision

Implement SPEC-020 as an opt-in standard-library local Git runtime. A reviewed
manifest and explicit matching digest acknowledgement admit one batch into one
new private run directory. Apply 2–4 ordinary text A/M patches in a declared
serial dependency order using private Git objects/index, verifying per-step
path/mode/blob effects and expected trees before advancing the private ref.
Use deterministic checkpoint commits, write-ahead state, fsynced atomic record
replacement, compare-and-swap refs and a POSIX advisory coordinator lock. Recover
process interruptions by reconciling the single pending transition, or abort to
the private base. A separate read-only verifier reconstructs expected results.

No source ref promotion, checkout, arbitrary code, hook, test, network service,
concurrent execution, external write adapter or new scientific guarantee is
admitted. The runtime output is an owned Git result, not proof of code correctness.
Existing AIM/M1/M2 records and `executionAuthorization: false` remain unchanged.

## Alternatives and consequences

Keeping only temporary replay loses durable results and recovery. Directly
promoting source refs requires a separate worktree-aware contract. Arbitrary
commands require enforceable OS isolation/effect observation and are deferred.
The owned POSIX filesystem/Git are trusted. Same-UID hostile interference and
power-loss guarantees are excluded; hashes are not signatures. Authorization
scope is private-run-only, never general permission from an analyzer verdict.

## Validation and review

SPEC-020 defines adversarial controls, real process-crash reproduction, bounded
resource failures and source immutability. Luna review and founder adoption are
separate. Founder adoption is recorded against the frozen candidate above. This ADR does
not close the full M4 milestone; CI does not grant human approval.

## References

- [Constitution](../../CONSTITUTION.md)
- [SPEC-020](../../specs/020-m4-local-git-runtime/spec.md)
- [ADR 0013](0013-isolated-git-replay-and-advisory-planning.md)
- [ADR 0014](0014-parallel-integration-contract.md)
