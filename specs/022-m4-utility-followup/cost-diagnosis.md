# Exploratory synthetic cost diagnosis

Protocol approval: public `3777e578`. Final diagnostic source checkpoint: `b3c41f338110bd3493f7a640e6a0e926d67e12f6`. All four commands exited 0; eight full-boundary treatments completed with reconciled accounting, expected trees, unchanged source, unique grants/plans and independent verification. No registered measurement executed.

| Block | Serial whole wall (s) | Parallel whole wall (s) |
|---|---:|---:|
| independent-2-1024 | 11.974 | 18.073 |
| independent-2-65536 | 11.430 | 19.455 |
| independent-4-1024 | 61.822 | 70.917 |
| dependency-chain-4-1024 | 18.958 | 30.947 |

## Candidate choice

**No runtime optimization is selected.** One serial-first exploratory pair per block with uncontrolled caches/background load does not justify caching or skipping required replay, policy reconstruction, grants or consumers. Existing runtime contracts remain intact. The chain preserves `a, b, c, d` order in both modes; five fixed cap exclusions remain visible. These observations prepare admission for synthetic evaluation only.

## Capacity and remaining review

Four operational pair walls sum to 243.577 seconds. A linear 22-pair projection is 89.3 minutes, above the approved 45-minute dispatch budget. This is a rough planning projection, not a controlled forecast. Keep the budget, rows and repetitions unchanged; preserve incomplete and unexecuted treatments. No favorable complete-case outcome is allowed.

Exact final diagnostics and command/observer receipts are in `evidence/final-diagnostics/`. Earlier captures remain in `evidence/diagnostics/` and `evidence/candidate-diagnostics/` as dated development records whose source hashes do not match the final candidate. The original summary is preserved under `evidence/development-checkpoint-038399b/`. No capture is registered measurement. Fixture preparation and final observer/output are separately observed. Stable harness/manifest approval, actual-workload utility acceptance, G4 and M4 remain pending.
