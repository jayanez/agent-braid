# Proposed cold readiness clarification

Status: adopted by the owner on 2026-10-14; implementation in progress. Historical v1/v2 behavior remains
30 seconds for model loading followed by one second for the first prediction.
This proposal changes the effective deadline of that first prediction. Retaining
the numeric ceilings does not make it an unchanged contract interpretation.

## Observed motivation

The approved v1 image failed its native Torch import; its receipt remains
inconclusive. The separately approved CPU v2 image passed native package/class
imports but its first registered cold warmup returned `deadline-exceeded` after
6.951616125 seconds through cleanup. The container was still running, without
OOM, before owned removal. No subsequent prediction was attempted. The v2
receipt does not directly capture individual load/first-forward timestamps;
its timeout and the reviewed code path support a resident-deadline failure,
not a measurement of steady-state latency or proof of general infeasibility.

## Proposed contract

- A single total **30-second cold budget** starts on entry to the first forecast
  call, before its validation/binding, checkpoint hashing, container setup,
  model loading and first forward pass. The caller's earlier deadline wins.
- The load command binds that exact already-registered first window/input
  digest and horizon. The first registered forecast is executed during startup,
  and its result is returned once. No extra warmup or unregistered prediction
  is added. The complete procedure stays at171 intended forecasts plus the two
  cancellation controls, at most173 attempts and300 seconds including teardown.
- The worker becomes resident-ready only after this first result is available
  and validated. Loading weights alone does not establish readiness.
- Every later request retains a **one-second** deadline. CPU1/library-thread1,
  2GiB container memory, zero swap, context128, horizons1/5/10, one active
  request, zero queue, network-none/read-only/nonroot controls remain unchanged.
- Cancellation and the tighter caller deadline apply throughout initialization
  and prediction. Any refusal/timeout remains visible, with confirmed cleanup
  or an explicit persistent cleanup-pending state. There is no implicit retry.
- First-result consumption, request identity and timing phases receive paired
  tests. A timeout cannot count as a successful warmup or resident-ready result.

## Review and decision boundaries

Independent Luna Latest design review found this technically plausible but
identified it as a contract clarification/change requiring explicit review.
Before adoption, it could not be implemented as the standing interpretation.
It cannot be used to reinterpret
the retained v2 result. An owner decision on this contract precedes dependent
implementation; subsequent code/protocol tests and technical review precede
presentation of the new exact image/host-wheel/manifest for model loading.
Existing v1/v2 artifact decisions do not authorize that changed package.

If this proposal is not adopted, keep the current profile and the actual model
conformance obligation open/inconclusive. Baseline/API/CLI/MCP engineering can
continue independently. No outcome approves a real source, experimental
launch, scientific utility, canonical ADR adoption or promotion.

## Retained owner decision

The owner selected “Adoptar la aclaración (recomendado)” in the interactive
decision associated with `call_fd991bc267934c429900dd70b4d2b4b6`. This adopts
only this timing clarification and authorizes implementation/review. It does
not approve loading a changed image or the canonical ADR.

## Diagnostic observation phases

In the unchanged v2 receipt, `running`, `exitCode` and `oomKilled` were read
from Docker State before forced removal. Because `running` was true, its
`exitCode: 0` is not an observed successful terminal exit. `cleanupConfirmed`
was set only after the owned removal succeeded. The raw receipt is preserved.

## Proposal byte history

The owner decision pins the original reviewed proposal SHA256
`473da6f1d0b50d7972ce39c972ba2b19de0390bc4a9395404de7e5a534eb0684`,
retained byte-for-byte in `cold-start-clarification-reviewed-proposal.md`.
This adopted companion appends decision/diagnostic notes and changes status
wording after that decision; it does not claim the owner reviewed these later
bytes. The cold-readiness terms are unchanged.
