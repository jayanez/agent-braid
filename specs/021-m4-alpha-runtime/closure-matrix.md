# Proposed M4 alpha exit matrix

All rows remain **open for final M4 acceptance**. Partial obtained evidence is recorded below. G0 accepted criteria and implementation scope, not final results.
M4 remains open until a separate exact-candidate closure decision.

| Roadmap deliverable | Required exit evidence | Requirements | Cut |
| --- | --- | --- | --- |
| MCP and host-runtime adapters | Pinned common protocol, conformance/refusal tests, real Codex and Claude Code tool invocations, independent result verification | REQ-001, 002, 006, 007 | C1/C3 |
| Transactional/isolation policies | Independently verified footprints, dependency-ready scheduling, distinct worker writable stores/indexes, exclusive coordinator CAS, zero unsafe admissions, serial agreement | REQ-002, 003 | C1/C2 |
| Live effect verification | Actual adapter path/mode/blob transitions and hashes checked before publication; drift/forgery controls rejected by independent consumer | REQ-004 | C2 |
| Replay and recovery | Fresh-process death/cancellation/disconnect/resume/abort cases and retry idempotence with verified prefixes; completed steps not duplicated | REQ-005 | C2/C3 |
| CI and policy gates | Executed quick/pr checks, deterministic protocol/policy tests, Linux reproduction artifacts, exact-candidate independent Luna review; blocked checks listed explicitly | REQ-006, 008 | C3/C4 |
| Portability across agent environments | Actual Codex and Claude Code observations on Darwin arm64; independent core/protocol reproduction on Linux x86_64, exact versions and limited coverage | REQ-007, 008 | C3/C4 |

Every row names candidate SHA, inputs, contracts, platform/version, actual command
or host action, output hashes and independent verifier outcome. Planned files and
synthetic peers cannot discharge a real-host row. All applicable negative controls
must pass; failing or unexecuted controls keep their row open.

G4 also requires measured conflicts refused, actual worker overlap, serial/parallel
result agreement, replayability, diagnostic usefulness and measured overhead.
A positive speedup is not presupposed. Negative/inconclusive utility is disclosed
and requires explicit founder go/no-go before claiming complete bounded M4 alpha.
No production, arbitrary-agent, external-write, scientific or formal guarantee.

## Historical implementation evidence snapshot at 67b8b521d0d18ebe679a905c3ed559d2f4a0119a

This earlier capture predates the full Claude host exercise below; its host-status
statement is retained as a historical observation, not the current state.

- C1/C2/C3 local sensitive checks: 372 tests, four skips (three SPEC-019 deferred implementation, one unavailable private-history test); no alpha-test skips.
- Fresh Darwin checkout/process reproduction: 61 tests, no skips; reused isolated interpreter.
- Historical Codex capture: all six tools, refusal, disconnect/resume/read-only retry/abort; zero model calls. That capture predates the separate full Claude exercise recorded below.
- Six paired cost trials: verified serial/parallel tree agreement in all pairs; median serial/parallel wall ratio 0.5581, negative-or-null-descriptive. Worker overlap remains observation rather than CPU proof.
- Two independent gpt-6-luna implementation reviews: no findings.

Evidence artifacts are bound to the implementation candidate and inputs; later record packaging does not extend their domain. Actual Claude host evidence was added on `d46fc52`; the separate founder G4 decision remains open. Linux is obtained in the addendum. The historical PR profile binding is in c4-evidence/pr-validation.txt; current PR checks are recorded in the T013 reconciliation. No M3/M3.5 scientific gate is changed.

## Authorized Linux and CI addendum

Linux reproduction obtained at 9108a20 via run 37197461233: 61 tests, no skips; source/input/log bindings verified. PR CI run 37197290307 succeeded with 367 pass/five skips and an explicitly skipped integration matrix. Earlier pending-Linux statements describe the prior capture stage and are superseded by this addendum. T010 is now complete from the Claude evidence addendum below; final reconciliation and founder G4 remain open.

## Actual Claude host addendum (2026-10-05)

Claude Code 2.1.236 on Darwin arm64 completed the actual bounded MCP tool exercise on the same owned two-edit fixture family, using Claude.ai Max with usage credits disabled by operator confirmation. Preparation had no execution authority; an empty grant store refused execution; a separately issued local grant ran the fixture; an intentional disconnect preserved a verified prefix after `a`; a new resume grant completed `b`; the independent verifier matched the expected final tree; and retrying the consumed grant did not repeat execution. The transcript, redactions and exact candidate/input bindings are in `host-evidence/claude.json`. This closes T010 only; it does not constitute independent scientific validation, founder G4 acceptance, merge authority, or M3/M3.5 verification.

## T013 evidence reconciliation complete

The six deliverable rows map to assurance scenarios SC-001 through SC-016 (with some
scenarios supporting multiple rows) and their hash-bound artifacts in `assurance.json`. The consolidated candidate/platform map,
current PR check results and explicit limits are in `t013-reconciliation.json`.
Fresh independent gpt-6-luna review of exact record commit `b1d602e1b96591fe693b0f9112b43bb4b98baaaa` found no actionable findings and verified all 56 artifact path/hash references across 13 unique files. Reconciliation SHA-256: `d1d670a91cee8e0e862c01554298e2528323954cbf9ef2d814d8b1323779ca24`; review record SHA-256: `b5e7b3bb9d0c4bc098b3b4770e26a4f3334b4e200c3c947f174dd121557d26f2`. T013 is complete. The founder G4 GO/NO-GO and T014 remain open.
