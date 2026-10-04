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

## Obtained implementation evidence at 67b8b521d0d18ebe679a905c3ed559d2f4a0119a

- C1/C2/C3 local sensitive checks: 372 tests, four skips (three SPEC-019 deferred implementation, one unavailable private-history test); no alpha-test skips.
- Fresh Darwin checkout/process reproduction: 61 tests, no skips; reused isolated interpreter.
- Actual Codex bridge: all six tools, refusal, disconnect/resume/read-only retry/abort; zero model calls. Full Claude exercise remains pending.
- Six paired cost trials: verified serial/parallel tree agreement in all pairs; median serial/parallel wall ratio 0.5581, negative-or-null-descriptive. Worker overlap remains observation rather than CPU proof.
- Two independent gpt-6-luna implementation reviews: no findings.

Evidence artifacts are bound to the implementation candidate and inputs; later record packaging does not extend their domain. Full Claude and founder G4 remain open; Linux is obtained in the addendum. The PR profile has passed; see c4-evidence/pr-validation.json for its exact binding. No M3/M3.5 scientific gate is changed.

## Authorized Linux and CI addendum

Linux reproduction obtained at 9108a20 via run 37197461233: 61 tests, no skips; source/input/log bindings verified. PR CI run 37197290307 succeeded with 367 pass/five skips and an explicitly skipped integration matrix. Earlier pending-Linux statements describe the prior capture stage and are superseded by this addendum. All final-acceptance rows remain open pending full Claude evidence, final reconciliation and founder G4.
