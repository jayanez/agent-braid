# Proposed M4 alpha exit matrix

All rows remain **open for final M4 acceptance**. Evidence is assembled below, with unexecuted checks and limitations called out. G0 accepted criteria and implementation scope, not final results. On 2026-10-05 the founder recorded a G4 NO-GO for accepting SPEC-021 as a useful speedup capability under the current evidence. This does not close M4; the milestone remains open.

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

Evidence artifacts are bound to the implementation candidate and inputs; later record packaging does not extend their domain. Actual Claude host evidence was added on `d46fc52`; Linux is obtained in the addendum. The historical PR profile binding is in c4-evidence/pr-validation.txt; current PR checks are recorded in the T013 reconciliation and decision packet. The G4 NO-GO is recorded in `g4-decision.json`; it does not change any M3/M3.5 scientific gate.

## Authorized Linux and CI addendum

Linux reproduction obtained at 9108a20 via run 37197461233: 61 tests, no skips; source/input/log bindings verified. PR CI run 37197290307 succeeded with 367 pass/five skips and an explicitly skipped integration matrix. Earlier pending-Linux statements describe the prior capture stage and are superseded by this addendum. At this 2026-10-04 snapshot, T010 was complete from the Claude evidence addendum below; final reconciliation and founder G4 were still open.

## Actual Claude host addendum (2026-10-05)

Claude Code 2.1.236 on Darwin arm64 completed the actual bounded MCP tool exercise on the same owned two-edit fixture family, using Claude.ai Max with usage credits disabled by operator confirmation. Preparation had no execution authority; an empty grant store refused execution; a separately issued local grant ran the fixture; an intentional disconnect preserved a verified prefix after `a`; a new resume grant completed `b`; the independent verifier matched the expected final tree; and retrying the consumed grant did not repeat execution. The transcript, redactions and exact candidate/input bindings are in `host-evidence/claude.json`. This closes T010 only; it does not constitute independent scientific validation, founder G4 acceptance, merge authority, or M3/M3.5 verification.

## T013 evidence reconciliation complete

The six deliverable rows map to assurance scenarios SC-001 through SC-016 (with some
scenarios supporting multiple rows) and their hash-bound artifacts in `assurance.json`. The consolidated candidate/platform map,
PR check results for reconciliation baseline head `f5d6b21` and explicit limits are in `t013-reconciliation.json`; post-T013 closure-candidate checks are recorded in `decision-packet.md`.
Fresh independent gpt-6-luna review of exact record commit `b1d602e1b96591fe693b0f9112b43bb4b98baaaa` found no actionable findings and verified all 56 artifact path/hash references across 13 unique files. Reconciliation SHA-256: `d1d670a91cee8e0e862c01554298e2528323954cbf9ef2d814d8b1323779ca24`; review record SHA-256: `b5e7b3bb9d0c4bc098b3b4770e26a4f3334b4e200c3c947f174dd121557d26f2`. T013 is complete. At that historical T013 snapshot, the founder G4 decision and T014 were still open.

## G4 founder decision (2026-10-05)

The founder recorded **NO-GO for accepting SPEC-021 as a useful speedup capability
under the current evidence**. Six pairs produced equivalent verified trees, while
the median serial/parallel total-wall ratio of `0.5581` favored serial execution
in this small, uncontrolled sample. This decision does not claim that parallelism
is generally unhelpful and does not accept or close whole M4. SPEC-021 and M4 remain
open. The conditional Spec Kit integration matrix was skipped in the current PR
workflows. See `g4-decision.json` for the decision source, exact candidate bindings,
evidence hashes and boundaries. M3/M3.5 scientific gates remain unchanged.

## Candidate-bound platform evidence on e66f9a1 (2026-10-08)

The current records add bounded platform observations for candidate
`e66f9a1b94fc5ebfbf784d9c48a76f53c1a656ee` / tree
`36821ee4685f583e97fede0e3c627dcf7d85bd07`. They do not replace the historical
snapshots above or close any exit row.

The [current Codex addendum](evidence/current-codex-host-e66f9a1.md) and
[summary JSON](evidence/current-codex-host-e66f9a1.json) document one Darwin arm64
Codex CLI 0.162.0-alpha.2 direct no-model bridge observation. It
exercised six MCP tools, missing-grant refusal, controlled disconnect and
recovery, independent prefix verification, verified completion, duplicate
suppression and abort, with zero model calls. The record matched 80 runtime input
hashes. Source, candidate, client binary and persistent host configuration were
unchanged. A distinct private 201-file pre-import guard was checked separately.
The temporary synthetic fixture was cleaned by the original harness at process exit; the
filesystem fixture is unavailable for later re-verification. The retained private
capture includes its 29-message transcript and outcome records. This is not a
model-mediated workload or a current Claude observation.

The distinct [Darwin core-suite addendum](evidence/current-darwin-core-e66f9a1.md)
and [summary JSON](evidence/current-darwin-core-e66f9a1.json) preserve three
executions on the same candidate. The original full run failed:
67 of 68 tests passed and one errored when a temporary repository lacked its
hooks directory. A focused 1-test diagnostic then passed, followed by a corrected
full run with 68 passes, zero skips and no timeout. The original run records its
80-input reproduction fingerprint and unchanged candidate/worktree state. The
separate 201-file candidate guard applies only to the focused diagnostic and
corrected full run. Each used a fresh Python process but the existing isolated
Python 3.13.11 environment, not a clean-room dependency setup. The added runs do
not erase the original failure or establish host-adapter behavior.

The [current Linux addendum](evidence/current-linux-core-protocol-e66f9a1.md) and
[summary JSON](evidence/current-linux-core-protocol-e66f9a1.json) document a
fresh-process reproduction of 68 core, policy, scheduler and
deterministic stdio-protocol tests, with zero skips, on Linux x86_64, Python
3.12.14 and Git 2.55.0. All 80 public-record input hashes matched candidate
objects. This covers only the Linux core/protocol sub-scope; it does not establish
Codex or Claude Linux host-adapter behavior. No cost result is claimed.

These records add evidence to the Codex host/protocol and Linux core/protocol
slices. The Claude current-host observation and the remaining six-row exit
criteria remain open. G4 NO-GO, SPEC-021's open state and M4's open milestone are
unchanged; the founder's whole-M4 decision remains separate.
