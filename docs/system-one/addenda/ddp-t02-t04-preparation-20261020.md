# DDP-T02/T03/T04 — preparation handoff, 2026-10-20

S1-DDP-T02-T04-PREPARATION-20261020. Subsequent to the [continuity receipt](verification-continuity-20261020/README.md); [exact coordinator handoff and bounded source observation](ddp-t02-t04-preparation-20261020.json). This is coordination evidence, not a component acceptance receipt.

The coordinator assigned three agents with separate module/test/JSON-fixture ownership: T02 verified_ir, T03 verified_acquisition, T04 verified_registry. At the handoff they were in read-only preparation pending GO. The managed worktree preflight failed on unreachable objects; recovery used a complete independent clone at `/Users/juanyanez/Documents/Codex/2026-10-20/agent-braid-verified-core`, branch `feat/verified-plan-core`, baseline fe6d25b3d9fb989c230aa11779b6a51d494d7a4e, without pruning the original store. Later in the read-back turn, the coordinator reports the recovered preflight passed and plans to import contracts/give GO. Its sealed preflight/component receipts have not been received here. No component delivery, focused-test result or integrated validation is claimed.

Implementation-direction clarifications reported by the coordinator, pending actual source and tests:

- T02 internal invalid/budget paths raise ValueError with a fixed reason; verify_program returns only five completed answered/defer fields. T05 maps failures into external refused responses; unexpected reason fields are excluded.
- interpret/render source-hunk validation also consumes a shared verification checkpoint with units1. Nested accounting must not reset the envelope at T05.
- T03 retains T024 safety flags and fixes diff context3, Myers, inter-hunk0, no color and prefixes as new hardening. Hash the actual acquired bytes; do not claim historical parity under non-default Git configuration.
- T04 reads bounded actual IR source without sibling imports. Production availability waits for the coordinator's actual serial source pin.

These directions do not amend the frozen T01 files or count as implemented behavior. Future component receipts must bind source/tests/fixtures, obtained passes and failures, limits and review findings. The existing shared-budget seam, T05/T06 dependencies, human/scientific/admission/promotion/activation gates remain separate. This documentary conversation starts no implementation and writes nothing into the coordinator candidate. No remote publication/merge authority is inferred.
