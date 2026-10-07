# Exploratory synthetic cost diagnosis

Protocol approval: public `3777e578`. Diagnostic code checkpoint: `038399b72ace750556e010ad934e69d899bf1e57`. The checkpoint is dated local source provenance; selected input hashes bind its bytes. All four diagnostic commands exited 0, with eight completed, independently verified treatments. No registered measurement executed.

| Block | Serial whole wall (s) | Parallel whole wall (s) | Largest serial / parallel phases |
|---|---:|---:|---|
| independent-2-1024 | 10.086 | 15.562 | execution, grant / execution, preparation |
| independent-2-65536 | 10.471 | 16.002 | execution, grant / execution, preparation |
| independent-4-1024 | 46.405 | 55.566 | replay, execution / execution, replay |
| dependency-chain-4-1024 | 15.362 | 25.528 | execution, preparation / execution, grant |

## Candidate choice

**No runtime optimization is selected.** These are one-pair exploratory observations with serial-first order and uncontrolled caches/background load. Required replay, policy reconstruction, grant checks and final verification remain part of the measured cost. No mandatory consumer check is cached, skipped or sampled. The registered candidate uses the existing runtime plus opt-in diagnostic observation.

The chain completed operations `a, b, c, d` in both modes and remains an ordering control. Five fixed patch-cap exclusions remain in the nine-row inventory. Each of the four numerically eligible blocks completed both modes with the reviewed expected tree, reconciled accounting and unchanged source. These admission observations prepare the immutable trial manifest; they do not establish production safety or actual-workload benefit.

## Capacity and remaining review

The observed operational wall sum for four diagnostic pairs is 194.982 seconds. Multiplying by 22 pairs per block suggests approximately 71.5 minutes, above the approved 45-minute dispatch budget. This is a rough planning projection, not a controlled duration prediction. Keep the 45-minute stop: do not silently expand it, remove rows or reduce repetitions. Any remaining treatments will be retained as unexecuted and the registered protocol will be incomplete.

Observer finalization and shared artifact output are separately recorded outside operational ratios; fixture construction is separate preparation. Raw diagnostics, observer receipts, command exits and stdout/stderr are preserved in `evidence/diagnostics/`. Registered measurement still requires the separately reviewed stable harness and manifest. Synthetic utility acceptance, actual-workload evidence, G4 and M4 closure remain pending.
