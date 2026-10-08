# SPEC-021 Darwin core reproduction addendum (v2)

## Candidate and environment

The runs used frozen candidate `e66f9a1b94fc5ebfbf784d9c48a76f53c1a656ee` (tree `36821ee4685f583e97fede0e3c627dcf7d85bd07`) on Darwin arm64 with Python 3.13.11 and Git 2.54.0 (Apple Git-157). Keep two input inventories distinct: the reproduction script fingerprints 80 relevant inputs (50 Python, 23 JSON, and 7 Markdown files); the separate candidate guard checks 201 files using map SHA-256 `40e089bf3632edca48ef39c3f47f50bad6ffce2a938a34b00f556c8fa366d0b8`.

The initial failed full run used the reproduction's own 80-input before/after fingerprint and recorded both that inputs and the working tree stayed unchanged. The 201-file candidate guard was separately applied before and after the focused diagnostic and corrected full run. Do not attribute that guard to the original run.

The Python process was fresh, but it reused the pre-existing isolated environment; dependencies were not reinstalled in a clean room.

## Preserved first result

The initial full run executed 68 tests: 67 passed and one errored, with no skips or timeout. The error was `FileNotFoundError` in `test_execute_and_verify` while the existing test attempted to write `.git/hooks/post-commit`; its temporary Git repository had no hooks directory. The receipt SHA-256 is `607156a9b31e01a4f81645b0372a19b0f004909998cb83cd90de15d03d7ece0f`, and the log SHA-256 is `bbc7961d897d844667458d015eace6aa14fd26923b72d879bdef1da4cd307d19`. This original failure remains recorded as failed.

## Focused diagnostic and distinct full rerun

A focused 1-test diagnostic passed in 10.660 seconds (10.805 seconds outer time) with a separate private Git template containing only an empty `hooks/` directory. The 201-file candidate guard passed before and after. Its receipt SHA-256 is `da07633edb38ee7fbf514b071043811535d4b0df2afbe20c5c6a10da351a2f6b`.

A separate full fresh-process reproduction then passed all 68 tests with zero skips and no timeout: unittest time 653.984 seconds, outer operator time 654.361 seconds. It used the same e66 candidate and unchanged reproduction script. The 201-file candidate guard passed before and after; the reproduction script separately fingerprinted its 80 relevant inputs. The only additional environment change was the new private Git template containing only an empty `hooks/` directory. System Git configuration was disabled, the reviewed minimal global Git configuration was used, prompts were disabled, and the process set `core.hooksPath=/dev/null` and `core.fsmonitor=false`. The template inventory was exactly one empty `hooks/` directory before and after.

The corrected-environment receipt SHA-256 is `b14bc25d4fba94608a33ce990512b489bbab58ddc5b99383f91d7f9af9bc4800`; its log SHA-256 is `6eea5bd6157bc022cd77bbd4712c6d1f91cf0a4901a1d978065f88eea4640bd0`. Operator preflight and post-run record hashes are `211dbdba1261234bd48f410960361e895d202b9f1dece39ea429f2fd81acc819` and `fa6a8a93879466235c5f85e6c041abf0e0b0e0c79b927462ec9416dff28952f4`.

Independent read-only review by `gpt-6-luna` reported no findings; receipt SHA-256 `4bea438602ab1368ac51fc1f8012d212d3cf98fdb3f71b51a9b1adadbe1e8e07`.

## Scope limits

This is local Darwin arm64 evidence for the bounded Git runtime, policy, scheduler, and deterministic MCP stdio-peer suites. It includes no external model, current-client host, live MCP server, real-source workload, network, or CI. The result does not establish semantic correctness of arbitrary operations, speedup, Linux/current-client behavior, utility, or whole-M4 acceptance. The original failure remains visible alongside the distinct corrected-environment pass.
