# T05 request context and digest seams — implementation direction

S1-DDP-T05-SEAMS-20261020; canonical task SPEC-028/T011. Source: coordinator S1.x System One, thread01a14a9e-bea2-7c71-b818-c6d244a809cd, turn01a15822-7322-7982-bb6e-1f3471ea7031, verified by readback. This follows the [actual T05 assignment](first-batch-final-package-20261020/t05-assignment.json). Status: coordinator-confirmed implementation directions, pending T05 source-bound receipt/tests; not accepted or tested capabilities. Frozen T01 and T02/T03/T04 records are unchanged.

## Request lifetime and snapshots

Internal proposed API: `VerifiedRequestContext(raw, owned_root, *, cancellation, clock)`, with convenient `evaluate(raw, ...)`, without public registration. The live trusted context holds frozen request/evidence bodies, the same git_budget, checkpoint/remaining_ns, decide/reacquire/revalidate and a phase boundary for future T06. No global or serializable request context is proposed.

`decide` returns an immutable producer snapshot with cleanup unknown. Closing and publishing before token release creates a new final snapshot with actual usage; it must not mutate the earlier snapshot. Repeated publication returns the same sealed result. A later implementation receipt must establish this behavior and ordering; this direction alone does not.

## Hash identity and future consumer rule

| Field/reference | Exact intended hashed object |
|---|---|
| evidenceRefs.snapshot | Full AcquiredSnapshot envelope |
| VerifiedDecision.snapshotDigest | Inner retained snapshot |
| interpretation evidence reference | Full interpretation payload |
| verifier evidence reference | Full VerifierResult |

These are intentionally different hash domains. The coordinator requires future T06 to retain the exact decision body/digest used in its proposal, report final usage through ConsumerResult and never silently replace a decision body under the old digest. T06 is future work; this handoff neither implements nor authorizes its consumer execution. Hash-algorithm/canonicalization and actual output conformance remain subject to the frozen contract and eventual tests.

Raw admission reuses pure acquisition._admit/_BOUNDS before I/O. Existing CancellationToken claim/wakers/publish/release, an internally latched irreversible Git cancellation event, memoized deadlines and aggregated counters must preserve the same request envelope. The source directive is recorded here; no new snapshot/hash scheme, wire default or execution authority is adopted by this document.

## Verification and operations boundary

No T05 test result, complete implementation receipt, independent review or acceptance is claimed. The next receipt should explicitly test immutable producer/final snapshots, repeated publication, exact envelope-vs-inner digests, accessible evidence bodies, cancellation/publication ordering and same-budget reacquisition. Any deviation must be reported with source hashes and corrective evidence rather than silently changing this chronology.

The source turn also records successful archival of the empty managed worktree used for the failed shared-store preflight. The isolated implementation clone and research sources are retained. This conversation performs no worktree archival or implementation writes. No task/issue/milestone closure, human/scientific review, training/calibration, admission/promotion or activation is implied.
