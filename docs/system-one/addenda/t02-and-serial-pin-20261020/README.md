# DDP-T02 component and T04 serial pin — 2026-10-20

S1-DDP-T02-SERIAL-PIN-20261020. Canonical aliases: DDP-T02 = SPEC-029/T026; DDP-T04 = SPEC-028/T010. This additive receipt follows the [T04 pre-pin component receipt](../t04-component-20261020/README.md). Those earlier source hashes and availability statements retain their original observation time.

## Obtained component evidence

The [exact T02 worker receipt](worker-receipt.json), recorded 2026-10-20T06:26:04.039937Z, binds IR source, test and fixture. Its [focused log](focused-log.txt) reports 25 tests, zero failures/skips, exit0, 0.021s. Worker ownership was released. The documentary conversation checked all three hashes against the coordinator candidate and both logs against the receipt; it did not rerun tests or independently review algorithm correctness.

The [mutation log](mutation-log.txt) reports four directed semantic controls detected by assertion failure: EOF too strict, unconditional EOF relaxation, incorrectly relaxed BOF and source validation excluded from the work cap. These RED assertions are expected detections of intentionally mutated behavior, not failures of the unmutated component suite. The log states source bytes were not modified. Four directed controls do not establish exhaustive coverage, general reliability or scientific validation.

## Serial production-source pin

The [exact serial-pin receipt](serial-pin.json), recorded 2026-10-20T06:25:31.745084Z, records the coordinator's serial edit after both worker ownerships were released. Source timestamps are preserved even though the T02 worker receipt was written later.

| Binding | SHA-256 |
|---|---|
| Actual IR source pinned | a0378c34b805387b0518cf6ebc3da05599976cb7f037d5f140c2571c8f362ea3 |
| Registry before pin | 2cae6dabd1aa1f9a4818f9c5b7214c8647f078f3fcc5d1ffb26e5657dabaa8c2 |
| Registry after pin | 8d9cb2070683497ea789a9f03905e07f69d6c812c7d0ec9d6ab8a72116f88e6c |

The documentary conversation matched the actual current IR and registry-after bytes, and matched registry-before against the preserved earlier receipt. This satisfies the recorded serial pin dependency only. The earlier ten-test T04 pass was obtained on pre-pin registry bytes and does not validate the changed post-pin registry or the combined implementation. T04 whole-task closure, joined tests and profiles remain pending. Pinning does not expose or activate a public production interface.

## Source and next handoff

Code remains in `/Users/juanyanez/Documents/Codex/2026-10-20/agent-braid-verified-core`, branch `feat/verified-plan-core`, recorded baseline fe6d25b3d9fb989c230aa11779b6a51d494d7a4e. This documentary branch copies exact receipts/logs, not implementation code. [Bindings](bindings.json) preserve source and copied bytes. No source/contract/historical evidence was edited here.

The coordinator additionally reported T03 expanding to 12 passing tests in10.065s and a coordinator-owned `tests/test_system_one_verified_components.py` for acquisition→EN/ES IR→finite selection→actual registry and absence of research/ML imports. Their source hashes, release and final logs have not been received here: these are status reports, not verified component/integration evidence. No T05 wire selection or T06 consumer is inferred. Await T03's exact receipt, post-pin tests, joined validation and independent review. The old DDP-T01 full profile remains failed; none of these focused passes reclassifies it.

No task/issue/milestone was closed and no remote tracking was changed by this receipt. Training/calibration, representative/scientific acceptance, human review, admission/promotion and activation remain pending. The worker/serial receipts grant no downstream execution authority.
