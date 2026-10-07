# Exploratory synthetic cost diagnosis

Protocol approval: public `3777e578`. Final diagnostic source checkpoint: `cc9dbb5d27cf2ff5d7f24c607aec8d12625c8065`. All four commands exited 0; eight full-boundary treatments completed with reconciled accounting, expected trees, unchanged source, unique grants/plans and independent verification. No registered measurement executed.

| Block | Serial whole wall (s) | Parallel whole wall (s) |
|---|---:|---:|
| independent-2-1024 | 14.235 | 27.595 |
| independent-2-65536 | 15.519 | 23.309 |
| independent-4-1024 | 67.617 | 81.392 |
| dependency-chain-4-1024 | 24.073 | 37.318 |

## Candidate choice

**No runtime optimization is selected.** One serial-first exploratory pair per block with uncontrolled caches/background load does not justify caching or skipping required replay, policy reconstruction, grants or consumers. Existing runtime contracts remain intact. The chain preserves `a, b, c, d` order in both modes; five fixed cap exclusions remain visible. These observations prepare admission for synthetic evaluation only.

## Capacity and remaining review

Four operational pair walls sum to 291.058 seconds. A linear 22-pair projection is 106.7 minutes, above the approved 45-minute dispatch budget. This is a rough planning projection, not a controlled forecast. Keep the budget, rows and repetitions unchanged; preserve incomplete and unexecuted treatments. No favorable complete-case outcome is allowed.

Exact final diagnostics and command/observer receipts are in `evidence/final-coordinator-diagnostics/`. Earlier captures remain in `evidence/diagnostics/` and `evidence/candidate-diagnostics/` and `evidence/final-diagnostics/` as dated development records whose source hashes do not match the final candidate. The original summary is preserved under `evidence/development-checkpoint-038399b/`. No capture is registered measurement. Fixture preparation and final observer/output are separately observed. Stable harness/manifest approval, actual-workload utility acceptance, G4 and M4 remain pending.
