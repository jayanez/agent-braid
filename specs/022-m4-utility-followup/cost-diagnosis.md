# Exploratory synthetic cost diagnosis

**Historical v1 diagnostic, not the later registered capture.** These four one-pair-per-block synthetic diagnostics used the original 45-minute proposal. The final local diagnostic source checkpoint recorded at the time was `dd8ea6dc852c17e01803c8c4c63f644c9479cb33`; its source is not available in the current public clone, so this document does not claim public candidate review or independent reproduction. The historical inputs and artifact hashes are preserved in [the evidence binding](evidence/historical-development-evidence-binding-5cb144e.json). All four commands exited 0; eight full-boundary treatments completed with reconciled accounting, expected trees, unchanged source, unique grants/plans and independent verification. The distinct 180-minute v2 registered synthetic capture later completed on `b85f7e5`; see the [registered capture summary](evidence/registered-capture-summary-b85f7e5.json). The v2 result does not rewrite these v1 measurements or their 45-minute capacity projection.

| Block | Serial whole wall (s) | Parallel whole wall (s) |
|---|---:|---:|
| independent-2-1024 | 14.684 | 23.721 |
| independent-2-65536 | 15.940 | 23.281 |
| independent-4-1024 | 72.379 | 89.807 |
| dependency-chain-4-1024 | 24.129 | 39.252 |

## Candidate choice

**No runtime optimization is selected.** One serial-first exploratory pair per block with uncontrolled caches/background load does not justify caching or skipping required replay, policy reconstruction, grants or consumers. Existing runtime contracts remain intact. The chain preserves `a, b, c, d` order in both modes; five fixed cap exclusions remain visible. These observations prepare admission for synthetic evaluation only.

## Capacity and remaining review

Four operational pair walls sum to 303.194 seconds. A linear 22-pair projection is 111.2 minutes, above the v1 proposal's 45-minute dispatch budget. This is a rough planning projection, not a controlled forecast or a duration claim for the later v2 capture. Keep each protocol's budget, rows and repetitions unchanged; preserve incomplete and unexecuted treatments. No favorable complete-case outcome is allowed.

Exact final v1 diagnostics and command/observer receipts are in `evidence/final-guarded-diagnostics/`. Earlier captures remain in `evidence/diagnostics/`, `evidence/candidate-diagnostics/`, `evidence/final-diagnostics/` and `evidence/final-coordinator-diagnostics/` as dated development records whose source hashes do not match the final candidate. The original summary is preserved under `evidence/development-checkpoint-038399b/`. None of these exploratory captures is registered measurement; the later 180-minute v2 registered capture is separately recorded in the linked summary. Fixture preparation and final observer/output are separately observed. Stable harness/manifest review and capture authorization were completed for v2 candidate `b85f7e5`; actual-workload utility acceptance, G4 and M4 remain pending. These historical v1 records do not support a general utility claim.
