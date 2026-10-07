# Exploratory synthetic cost diagnosis

Protocol approval: public `3777e578`. Final diagnostic source checkpoint: `2edfa9901bd80f36f096cc3a91223b9e64b213c4`. All four commands exited 0; eight full-boundary treatments completed with reconciled accounting, expected trees, unchanged source and independent verification. No registered measurement executed.

| Block | Serial whole wall (s) | Parallel whole wall (s) |
|---|---:|---:|
| independent-2-1024 | 9.888 | 15.543 |
| independent-2-65536 | 9.967 | 15.494 |
| independent-4-1024 | 45.014 | 54.661 |
| dependency-chain-4-1024 | 15.297 | 25.467 |

## Candidate choice

**No runtime optimization is selected.** One serial-first exploratory pair per block with uncontrolled caches/background load does not justify caching or skipping required replay, policy reconstruction, grants or consumers. Current runtime contracts remain intact. The chain preserves `a, b, c, d` order in both modes; five fixed cap exclusions remain visible. These observations prepare admission for synthetic evaluation only.

## Capacity and remaining review

The four operational pair walls sum to 191.332 seconds. A linear 22-pair projection is 70.2 minutes, above the approved 45-minute dispatch budget. This is a rough planning projection, not a controlled forecast. Keep the budget, rows and repetitions unchanged; preserve incomplete and unexecuted treatments. No favorable complete-case outcome is allowed.

Exact final raw diagnostics and command/observer receipts are retained in `evidence/candidate-diagnostics/`. Earlier development diagnostics remain in `evidence/diagnostics/`; their dated summary is preserved in `evidence/development-checkpoint-038399b/`. Neither set is registered measurement. Closing observer/output and fixture preparation are separately observed. Stable harness/manifest approval, actual-workload utility acceptance, G4 and M4 remain pending.
