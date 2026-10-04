# Proposed M4 alpha exit matrix

All rows are **open**. Acceptance of this proposal approves criteria, not results.
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
