# Project status and evidence record

This page is the single source for current project state. [ROADMAP.md](../ROADMAP.md)
holds the plan, the [README](../README.md) describes the product and links here,
and the [documentation map](README.md) says which file is the authority for each
kind of fact. Live issue state is in the
[GitHub Project](https://github.com/users/jayanez/projects/6) and the
[milestones](https://github.com/jayanez/agent-braid/milestones). A closed milestone
or a passing check is not a feature acceptance, a scientific result or a human
review; the evidence-boundary table below says what each record covers.

## Current state — 2026-11-26

Method: counts computed on 2026-11-26 at `develop` `02b19545` from `specs/`,
[github-tracking.json](development/github-tracking.json) and the read-only query
`gh api 'repos/jayanez/agent-braid/milestones?state=all'`.

| Item | Value | Source |
| --- | --- | --- |
| Specs | 81 (`specs/*/spec.md`), all assigned to a milestone | `specs/`, `github-tracking.json` (`specs`) |
| Published milestones | 38: 28 closed, 10 open (M4.5 reopened on 2026-11-27 for #425) | GitHub milestones API |
| Unpublished milestone | 1 (M4.6 — Claude Code dynamic workflows; no remote record) | `github-tracking.json` (`unpublished_milestones`) |
| Latest plugin release | `0.1.0-alpha.9`, tag `agent-braid--v0.1.0-alpha.9`, published 2026-11-16; rollback target `0.1.0-alpha.8` | [release notes](tooling/RELEASE_NOTES_ALPHA9.md), `git ls-remote --tags` |
| Python package version | `0.1.0a2` | `pyproject.toml` |

Spec-to-milestone assignments are in the [spec and milestone index](development/SPEC_MILESTONE_INDEX.md).

### Milestones on GitHub (2026-11-26)

Issues are open / closed. Closure PRs of 2026-10-31 (#798, #799, #800, #803, #806)
closed M4.5, LAB.1, RES.1, GOV.1, M3.5, FC.1 and PUB.1 and mapped remaining open
specs to Deferred #24.

The Deferred (#24) and M4.5 (#19) rows and the milestone totals above include the
F5 stage-2 GitHub writes applied on 2026-11-27: the 14 closures as not planned,
#425 moved to M4.5 (reopened for it) and the new issue #1700. The tracking audit
reports `operations: []`. Before them Deferred read 72 / 20 and M4.5 read 0 / 111,
closed. The decisions of 2026-11-26 are in the
[Deferred triage](development/deferred-triage-20261126.md).

| # | Milestone | State | Closed | Issues |
| --- | --- | --- | --- | --- |
| [1](https://github.com/jayanez/agent-braid/milestone/1) | M0 — Operational foundations | closed | 2026-09-23 | 0 / 14 |
| [2](https://github.com/jayanez/agent-braid/milestone/2) | M0.5 — Open strategy and preview preparation | closed | 2026-09-23 | 0 / 16 |
| [3](https://github.com/jayanez/agent-braid/milestone/3) | M1 — Observable interaction analyzer | closed | 2026-09-23 | 0 / 33 |
| [4](https://github.com/jayanez/agent-braid/milestone/4) | M2 — Confluence lab and scheduler | closed | 2026-09-27 | 0 / 42 |
| [5](https://github.com/jayanez/agent-braid/milestone/5) | M3 — Braid semantics | closed | 2026-09-27 | 0 / 7 |
| [6](https://github.com/jayanez/agent-braid/milestone/6) | M4 — Agent Braid runtime | closed | 2026-10-09 | 0 / 46 |
| [7](https://github.com/jayanez/agent-braid/milestone/7) | PUB.1 — Public research preview | closed | 2026-10-31 | 0 / 10 |
| [8](https://github.com/jayanez/agent-braid/milestone/8) | GOV.1 — Governance and adoption | closed | 2026-10-31 | 0 / 35 |
| [9](https://github.com/jayanez/agent-braid/milestone/9) | M3.5 — Native proposal predictor | closed | 2026-10-31 | 0 / 11 |
| [10](https://github.com/jayanez/agent-braid/milestone/10) | ADP.1 — Recorded-trace adapters | closed | 2026-10-31 | 0 / 9 |
| [11](https://github.com/jayanez/agent-braid/milestone/11) | LAB.1 — Effectful workload lab | closed | 2026-10-31 | 0 / 9 |
| [12](https://github.com/jayanez/agent-braid/milestone/12) | RES.1 — Formal interaction research | closed | 2026-10-31 | 0 / 8 |
| [13](https://github.com/jayanez/agent-braid/milestone/13) | S1.0 — Decision contracts | closed | 2026-10-31 | 0 / 11 |
| [14](https://github.com/jayanez/agent-braid/milestone/14) | S1.1 — Decision evaluation | closed | 2026-10-31 | 0 / 18 |
| [15](https://github.com/jayanez/agent-braid/milestone/15) | S1.2 — Native decision model | closed | 2026-10-31 | 0 / 0 |
| [16](https://github.com/jayanez/agent-braid/milestone/16) | S1.3 — Advisory integration | closed | 2026-10-31 | 0 / 10 |
| [17](https://github.com/jayanez/agent-braid/milestone/17) | S1.4 — Product capabilities and promotion | closed | 2026-10-31 | 0 / 6 |
| [18](https://github.com/jayanez/agent-braid/milestone/18) | FC.1 — Forecast-guided parallelism experiment | closed | 2026-10-31 | 0 / 41 |
| [19](https://github.com/jayanez/agent-braid/milestone/19) | M4.5 — AI tooling integrations for Codex and Claude Code | open | – | 1 / 111 |
| [20](https://github.com/jayanez/agent-braid/milestone/20) | FC.2 — Local forecasting capabilities | closed | 2026-10-31 | 0 / 17 |
| [21](https://github.com/jayanez/agent-braid/milestone/21) | HAR.1 — Braid Harness laboratory | open | – | 2 / 30 |
| [22](https://github.com/jayanez/agent-braid/milestone/22) | HAR.2 — Braid Harness evaluation and learning | closed | 2026-11-24 | 0 / 15 |
| [23](https://github.com/jayanez/agent-braid/milestone/23) | HAR.3 — Braid Harness adaptation and integration | open | – | 13 / 30 |
| [24](https://github.com/jayanez/agent-braid/milestone/24) | Deferred | open | – | 58 / 34 |
| [25](https://github.com/jayanez/agent-braid/milestone/25) | VIS.1 — Activity viewer | open | – | 29 / 90 |
| [26](https://github.com/jayanez/agent-braid/milestone/26) | S1.5 — System One shadow activation | open | – | 31 / 27 |
| [27](https://github.com/jayanez/agent-braid/milestone/27) | M4.7 — AI tooling integration for OpenCode | closed | 2026-11-05 | 0 / 12 |
| [28](https://github.com/jayanez/agent-braid/milestone/28) | M4.8 — AIM request authoring | closed | 2026-11-13 | 0 / 34 |
| [29](https://github.com/jayanez/agent-braid/milestone/29) | BL.0 — Braid Lightning foundations | closed | 2026-11-08 | 0 / 11 |
| [30](https://github.com/jayanez/agent-braid/milestone/30) | BL.1 — Lightning rollouts and verifiable reward | closed | 2026-11-11 | 0 / 14 |
| [31](https://github.com/jayanez/agent-braid/milestone/31) | BL.2 — Lightning prompt optimization | closed | 2026-11-14 | 0 / 14 |
| [32](https://github.com/jayanez/agent-braid/milestone/32) | BL.3 — Lightning promotion | open | – | 3 / 9 |
| [33](https://github.com/jayanez/agent-braid/milestone/33) | BL.4 — Lightning trace consent | closed | 2026-11-14 | 0 / 18 |
| [34](https://github.com/jayanez/agent-braid/milestone/34) | BL.5 — Lightning dataset export | closed | 2026-11-17 | 0 / 14 |
| [35](https://github.com/jayanez/agent-braid/milestone/35) | BL.2b — Lightning held-out re-evaluation | closed | 2026-11-22 | 0 / 17 |
| [36](https://github.com/jayanez/agent-braid/milestone/36) | BL.2c — Lightning tool-level kind-choice fix | open | – | 4 / 9 |
| [37](https://github.com/jayanez/agent-braid/milestone/37) | HAR.4 — Harness evaluation platform | open | – | 67 / 6 |
| [38](https://github.com/jayanez/agent-braid/milestone/38) | M4.9 — AI tooling integration for Pi and ThinkRail | open | – | 13 / 0 |


### Parked work and reopen triggers

What stays in Deferred #24 after the 2026-11-26 triage (57 kept issues plus the
new measurement issue [#1700](https://github.com/jayanez/agent-braid/issues/1700),
which implements the reopen trigger of [triage Q3](development/deferred-triage-20261126.md#q3-1343-analyze-work-d4--cerrar-superado-por-079-recomendado);
none is accepted, cancelled or authorized by being parked). The full wording is
only in the [triage record](development/deferred-triage-20261126.md); this table is
a pointer. A review date raises a warning in the weekly tracking audit until it is
removed (see [GitHub tracking](development/GITHUB_TRACKING.md#parked-work-review-dates)).

| Group | Issues | Reopen when | Review by | Decision |
| --- | --- | --- | --- | --- |
| System One (SPEC-028–033 parents, SPEC-030, SPEC-032) | #275, #284, #303, #312, #321, #294–#302, #581–#588, #314, #317, #318 | SPEC-029 T001 third-party source permissions granted and admitted real groups > 0, or SPEC-066 T104 owned corpus plus an S1.5d Wilson GO | – | [Q10](development/deferred-triage-20261126.md#q10-system-one--parked-con-trigger-corregido-recomendado) ([Q8](development/deferred-triage-20261126.md#q8-parents-417-spec-041-439-spec-043-321-spec-033) for #321) |
| SPEC-076 local GRPO | #1252–#1267 | founder go/no-go accepting ADR 0042, a local CUDA GPU, SPEC-075 delivered | – | [Q11](development/deferred-triage-20261126.md#q11-spec-076--parked-con-trigger-recomendado) |
| SPEC-060 alias removal | #760, #771 | REQ-007 criteria hold and the owner decides removal | 2027-04-25 | [Q12](development/deferred-triage-20261126.md#q12-spec-060--parked-con-trigger-y-fecha-recomendado) |
| SPEC-046 submission | #537, #551, #552 | owner decides to submit and the external requirement is met (spec stays read-only) | – | [Q9](development/deferred-triage-20261126.md#q9-spec-046--sí-solo-lectura--parked-recomendado) |
| SPEC-041 tasks | #418, #423 | T001: all five skills loaded at recorded versions; T006: C1–C3 receipts for `evidence` | – | [Q5](development/deferred-triage-20261126.md#q5-spec-041-418-423-425--t001t006-parked-t008-rescate-recomendado) |
| SPEC-041/043 closure | #426, #427, #448, #449 | T001–T008 of the same spec closed or closed by owner decision | – | [Q6](development/deferred-triage-20261126.md#q6-closure-bookkeeping--mantener-parked-con-trigger-recomendado) |
| SPEC-043 tasks | #440, #442, #447 | the observation criteria of the 2026-10-31 M4.5 record | – | [Q7](development/deferred-triage-20261126.md#q7-spec-043-440-442-447--parked-con-criterio-del-record-recomendado) |
| Parents SPEC-041, SPEC-043 | #417, #439 | follow their child tasks | – | [Q8](development/deferred-triage-20261126.md#q8-parents-417-spec-041-439-spec-043-321-spec-033) |
| Codex/OpenCode `analyze-work` validity | [#1700](https://github.com/jayanez/agent-braid/issues/1700) | SPEC-079 T010 (#1513) converges and the owner authorizes the measurement | – | [Q3](development/deferred-triage-20261126.md#q3-1343-analyze-work-d4--cerrar-superado-por-079-recomendado) |

## Work merged by 2026-10-24

As of 2026-10-24, all lines below are merged into `develop`. Each keeps
`executionAuthorization: false` (where applicable) and leaves its human, scientific
and acceptance gates open.

| Work | Pull request | What it adds |
| --- | --- | --- |
| **Braid Harness offline foundations** (SPEC-048 T001–T004, ADR 0027) | [#657](https://github.com/jayanez/agent-braid/pull/657) | Immutable offline experiment manifests, protected candidate import and single-use operator admission for comparing agent-guidance variants; no native host, model or paid route. |
| **Owned-work evaluation contracts** (SPEC-051) | [#659](https://github.com/jayanez/agent-braid/pull/659) | Pure operator-authority resolution and frozen-registration append validation for evaluating real owned work; no real sources, storage or training. |
| **Effectful workload laboratory** (SPEC-024 T001–T004, ADR 0028) | [#660](https://github.com/jayanez/agent-braid/pull/660) | A closed, standard-library simulator that explores effectful request/transition state spaces with byte-bounded exploration and binds observations to replayable evidence. |
| **Contextual proof obligations** (SPEC-025) | [#658](https://github.com/jayanez/agent-braid/pull/658) | A reconciled finite evidence packet for contextual safety checks; no theorem is accepted. |
| **Plugin MCP local telemetry consent** (SPEC-046/SPEC-047) | [#669](https://github.com/jayanez/agent-braid/pull/669), [#670](https://github.com/jayanez/agent-braid/pull/670) | Persisted default-off local telemetry consent in the plugin registry (v0.2), set only through `plugin setup --telemetry`, and plugin `0.1.0-alpha.3` (published on `plugin-dist`); `0.1.0-alpha.4` is published on `plugin-dist` (tag `agent-braid--v0.1.0-alpha.4`); `plugin discover` reads a v0.1 registry before migration. SPEC-047 T010/T017/T018 and the pilot stay open/NO-GO. |
| **Braid Harness runner, journal, refinement, context, observation, CLI and integration controls** (SPEC-048 T005, T006, T007, T009, T011, T012, T015) | [#674](https://github.com/jayanez/agent-braid/pull/674), [#673](https://github.com/jayanez/agent-braid/pull/673), [#681](https://github.com/jayanez/agent-braid/pull/681), [#712](https://github.com/jayanez/agent-braid/pull/712), [#713](https://github.com/jayanez/agent-braid/pull/713), [#720](https://github.com/jayanez/agent-braid/pull/720), [#721](https://github.com/jayanez/agent-braid/pull/721) | Pure bounded context assembly, pure loss- and privacy-accounted observation records, and a deterministic fixture runner that launches a bounded child process whose built-in containment is labelled `simulated` and confines no filesystem, network or credentials; any native backend refuses without a verified qualification. A hash-chained, atomically published attempt journal reconciles an interrupted attempt as `interrupted` with unknown outcome and never renews a reservation, and a one-round propose-probe-compose refinement keeps the unchanged base unless a candidate clears a frozen margin. An experimental `harness` command group (inspect, validate, prepare, status, recover-inspect, compare) with strict byte-for-byte record codecs has one effect (`prepare` creates a new private directory), and deterministic adversarial integration controls drive the whole pipeline with the `simulated` backend; deterministic success is not native qualification. No host, model or paid route. T008, T013 and T014 (native adapters) stay open behind their admission gates. |
| **Effectful workload comparison evidence** (SPEC-024 T005–T008) | [#675](https://github.com/jayanez/agent-braid/pull/675), [#689](https://github.com/jayanez/agent-braid/pull/689), [#680](https://github.com/jayanez/agent-braid/pull/680) | Negative controls, an independently reviewed engineering closure of T005 (scientific review of the corpus pending) and one registered, machine-bound comparison run. T006–T008 stay open pending scientific review; the single positive run is not a utility claim. |
| **Owned-work evaluation closure** (SPEC-051 T004) | [#676](https://github.com/jayanez/agent-braid/pull/676) | Compatibility and profile evidence for the pure contracts; remote closure, real sources and review remain pending. |
| **Plugin reconnect-required refusal** (SPEC-046 T016–T019) | [#679](https://github.com/jayanez/agent-braid/pull/679), [#682](https://github.com/jayanez/agent-braid/pull/682), [#696](https://github.com/jayanez/agent-braid/pull/696), [#691](https://github.com/jayanez/agent-braid/pull/691) | A typed `reconnect-required` refusal, effective-configuration reconnect detection with path-free digests in `plugin-status`, documentation of multi-session registry changes, and the owner decision that router-level refusals stay uncounted in local telemetry (no contract change). T016–T019 are closed as engineering and documentary closures; the installed-procedure reruns remain pending. #691 stops two telemetry concurrency tests failing on a loaded runner. |

**Unpublished milestone, nothing released — [M4.6 Claude Code dynamic workflows](../ROADMAP.md#m46--claude-code-dynamic-workflows):**
[SPEC-052](../specs/052-claude-workflow-gate/spec.md) specifies a read-only
integration gate for Claude Code dynamic workflows; the engineering candidate has
host verification HV-1 to HV-5 and native runs T030 and T031 recorded on Claude Code
2.1.292 (evidence under `specs/052-claude-workflow-gate/evidence/`, disposition in
`hv-disposition.md`), and the founder accepted the wildcard allowlist trade-off for
the MCP path on 2026-10-25; ADR 0029 is a Proposed draft awaiting adoption, and the
release (R1) is a separate founder decision.
[SPEC-053](../specs/053-claude-transcript-trace-adapter/spec.md) is a transcript trace
adapter blocked by a preregistered G0 experiment (revision 3, not frozen). SPEC-057 to SPEC-059 extend the
milestone to orchestrator-style parallel agents (advisory ownership, pre-flight,
checkpoint and recovery evidence; an opt-in guard gated by a staged G1; a
sketched ledger and optional push gated by G2). Nothing is released; ADR changes remain
proposals until the founder adopts them.

**Published — [M4.7 OpenCode integration](../ROADMAP.md#m47--ai-tooling-integration-for-opencode)
([SPEC-068](../specs/068-opencode-native-integration/spec.md)):** plugin `0.1.0-alpha.7`
(published 2026-11-04) adds the OpenCode native plugin, `plugin doctor --host opencode`
(skill and server collisions), `install.sh --host opencode` and `--host all`, and a
legacy `tooling install --host opencode` profile. T001 to T011 are done: engineering
checks, a disposable-profile host matrix, a T010 native observation on macOS arm64 with
OpenCode 2.1.4 (20 of 23 rows observed, 19 before publication; the one contradiction, row 14, was fixed in the
release, not re-observed) and a post-publication install smoke from `plugin-dist`. Not observed: Linux,
the session `_meta` identifier (row 23) and native host installs of alpha.7 in Claude
Code and Codex; the `analyze-work` schema does not describe the AIM request shape
(issue #1080). See the
[release record](../specs/068-opencode-native-integration/release-acceptance-alpha7.md).

The runtime executes allowlisted Git plumbing. Repository code, source-ref
promotion and broader agent/provider adapters require additional contracts and
authority. The [runtime demo](../examples/runtime/README.md) gives you a complete
owned fixture; the [alpha quickstart](../specs/021-m4-alpha-runtime/quickstart.md)
covers grants, recovery and MCP configuration.

### Codex and Claude Code integrations

[M4.5](tooling/README.md) is an integration program adjacent to M4 (milestone closed 2026-10-31, #799 and #800; see the table above). Its
original six specs retain the planned MCP, skills, lifecycle, presentation and evaluation
scope. [SPEC-047](../specs/047-local-technical-telemetry/spec.md) adds default-off local
aggregate telemetry; the combined portfolio has eight source specifications. [SPEC-046](../specs/046-native-ai-plugins/spec.md) extends M4.5 with
native packaging, a shared workspace registry and setup; it does not reopen
historical acceptance or replace existing evaluation gates. Current local evidence now covers bounded technical controls and fresh
macOS/Linux package checks, each bound to its own candidate; it does not establish
native host support, M4.5 acceptance or milestone closure. The complete current
status and candidate-specific limits are in the [tooling status](tooling/TECHNICAL_STATUS.md).

The [autonomous technical closure record](tooling/AUTONOMOUS_COMPLETION.md)
and [technical evidence status](tooling/TECHNICAL_STATUS.md) now link the
candidate-bound package, Linux, engineering, program, MCP and lifecycle evidence.
MCP, program controls and lifecycle procedures passed on their recorded local
candidates; installed macOS and emulated Linux AMD64 package checks passed for
`53f1704`. The 223-test engineering suite passed on `aaae2e7`, with a separate direct
223-test run on `24921e1`. These are distinct source identities and observation
domains, not a single end-to-end candidate claim.

The first targets are **Codex local CLI and Claude Code local CLI**. M4.5 formal product
support and full acceptance remain pending. Separate bounded SPEC-021 host
observations for Codex and Claude are linked below; they do not establish M4.5
product support or acceptance. Cursor, VS Code/GitHub Copilot and pi are future routes;
OpenCode is a native plugin host from plugin `0.1.0-alpha.7` (SPEC-068), observed in
OpenCode on macOS arm64 only. Start with the [integration guide](tooling/README.md) for the
spec, contract and task map.

### Optional local diagnostics

The [integration record](../specs/047-local-technical-telemetry/integration-review.md)
identifies the reviewed telemetry source, current base and pending acceptance gates.

The integration candidate adds local numeric telemetry to the portable MCP service and two analyzer CLI commands. It is **off by default**, has no automatic transmission, uses a private bounded SQLite store and retains 30 UTC dates on access. Installation previews/receipts expose the explicit server consent; skills never enable collection. Read [installation](tooling/INSTALL.md) and [telemetry privacy, commands and limits](tooling/TELEMETRY.md) before opting in.

```sh
agent-braid analyze /absolute/input.json --telemetry local
agent-braid telemetry status --format json
agent-braid telemetry report
agent-braid telemetry export /absolute/private/telemetry-batch.json
agent-braid telemetry merge /absolute/private/received-batch.json
agent-braid telemetry purge
```

Exports are incremental manual aggregates and have no persistent installation identity. Full evidence exports remain separate. Uninstall keeps metrics; explicit purge clears local data/deduplication and cannot revoke copies. The [M4.5 alignment](tooling/M45_ALIGNMENT.md) records current source inventory, prior SPEC-044/T004 bounded closure and pending candidate admission; historical checks below do not cover this changed candidate.

The [local follow-up review](../specs/046-local-technical-telemetry/review-20261016.md) records export-retry durability and input-file validation corrections, their regression controls and the candidate's remaining review/admission limits.

The [canonical owner decisions D17/D18/D10](../specs/046-local-technical-telemetry/owner-decisions-20261016.md) record the additive observation contract, reviewed coverage with pilot **NO-GO**, and bounded engineering acknowledgment with final acceptance deferred. T017, T018 and T010 remain open; installation and telemetry consent are unchanged.

The [canonical E9 owner decisions](../specs/046-local-technical-telemetry/owner-decisions-e9-20261017.md)
record the approved documentary dispositions for frozen candidate `e9d4153cc880`:
observation-contract applicability, coverage with pilot **NO-GO**, and bounded
engineering acknowledgment with final acceptance deferred. T017/T018/T010 remain
open; these decisions authorize no native/provider execution or installation/
consent change. The historical C/D decisions retain their original scope.



## Final repository validation — 2026-10-11

Both repository profiles passed on the same clean frozen source `72a396d294205201f7f56d00fa2349dccb540a5c`.
The receipts validate source work and do not extend the host, registered-cohort,
human-evaluation or founder-acceptance boundaries.

- Quick profile: `72a396d294205201f7f56d00fa2349dccb540a5c`; 1293 tests, 12 skipped; terminal profile receipt and raw output are hash-bound privately.
- Stable PR profile: `72a396d294205201f7f56d00fa2349dccb540a5c`; 1293 tests, 12 skipped; terminal profile receipt and raw output are hash-bound privately.

<a id="quick-start"></a>


## Evidence boundaries by milestone

Research alpha. The table states, per milestone, what the evidence does and does
not cover. Its figures were written between 2026-10-11 and 2026-11-24 and each row
dates its own claims; the current milestone state is in the
[table above](#milestones-on-github-2026-11-26) and takes precedence where they
differ. “Closed” is the remote milestone state; implementation, scientific
acceptance and external review remain distinct.

| Track | Milestone | State and evidence boundary |
| --- | --- | --- |
| Foundations | [M0 — Operational foundations](https://github.com/jayanez/agent-braid/milestone/1) | Closed; internally closed. Independent external validation remains pending. |
| Foundations | [M0.5 — Open strategy and preview preparation](https://github.com/jayanez/agent-braid/milestone/2) | Closed; internally closed. Two historical review items remain open in tracking. |
| Foundations | [M1 — Observable interaction analyzer](https://github.com/jayanez/agent-braid/milestone/3) | Closed internally against the reviewed candidate; independent external validation remains pending. |
| Research | [M2 — Confluence lab and scheduler](https://github.com/jayanez/agent-braid/milestone/4) | Closed internally. Bounded replay and finite observations do not establish general confluence. |
| Research | [M3 — Braid semantics](https://github.com/jayanez/agent-braid/milestone/5) | Closed internally for `anchored-sequence-v1`; no general braid or Yang–Baxter theorem is claimed. |
| Runtime | [M4 — Agent Braid runtime](https://github.com/jayanez/agent-braid/milestone/6) | Founder accepted bounded alpha engineering and evaluation as complete on 2026-10-09, with negative utility. Current GitHub tracking is shown in the [live M4 milestone](https://github.com/jayanez/agent-braid/milestone/6). Historical SPEC-021 G4 remains **NO-GO** on useful speedup under its frozen evidence. |
| Integration | [M4.5 — AI tooling integrations for Codex and Claude Code](https://github.com/jayanez/agent-braid/milestone/19) | Candidate-bound local paired procedures, package checks and technical controls passed within their stated domains. The combined source inventory is 122/135 tasks closed (including 10 cancelled SPEC-044 tasks), 13 open, with six closed spec parents (SPEC-039, SPEC-040, SPEC-042, SPEC-044, SPEC-047, SPEC-054) and four open (SPEC-041, SPEC-043, SPEC-046, SPEC-060); SPEC-039/040/042 retain their recorded bounded acceptance. Native-host acceptance, human interpretation and remaining founder decisions are not recorded; the milestone was closed on 2026-10-31 (#799, #800) with remaining specs mapped to Deferred #24. M4.5 was reopened on 2026-11-27 for #425 (SPEC-041 T008, rescued from Deferred, decided 2026-11-26; [triage Q5](development/deferred-triage-20261126.md#q5-spec-041-418-423-425--t001t006-parked-t008-rescate-recomendado)). |
| Integration | [M4.7 — AI tooling integration for OpenCode](https://github.com/jayanez/agent-braid/milestone/27) | **Closed 2026-11-05** (plugin `0.1.0-alpha.7` published 2026-11-04). SPEC-068 T001 to T011 are done and plugin `0.1.0-alpha.7` is published ([record](../specs/068-opencode-native-integration/release-acceptance-alpha7.md)); Linux, native host installs of alpha.7 in Claude Code and Codex, and T010 row 23 are not observed, and the `analyze-work` AIM schema limit is tracked in issue #1080. M4.5 is not reopened. |
| Integration | [M4.8 — AIM request authoring](https://github.com/jayanez/agent-braid/milestone/28) | **Closed 2026-11-13.** [SPEC-069](../specs/069-aim-request-authoring/spec.md) T001–T015 done; [ADR 0038](adr/0038-analyze-work-request-contract.md) (accepted 2026-11-07) defines the published, tested `analyze-work` request contract for host models (origin issue #1080). Released in `0.1.0-alpha.8` (2026-11-13, record PR #1345) and carried in `0.1.0-alpha.9`. T008/T010 closed with an accepted D4 deviation (#1322); the D4 gap was follow-up #1343, decided 2026-11-26 ([triage Q3](development/deferred-triage-20261126.md#q3-1343-analyze-work-d4--cerrar-superado-por-079-recomendado)) and closed as not planned on 2026-11-27. SPEC-069 is still a draft: its freeze and owner review are pending. |
| Publication | [PUB.1 — Public research preview](https://github.com/jayanez/agent-braid/milestone/7) | The preview is public; historical publication authorization reconciliation is tracked separately (closure PR #806, 2026-10-31). |
| Governance | [GOV.1 — Governance and adoption](https://github.com/jayanez/agent-braid/milestone/8) | Issue state does not confer human or founder approval (closure PR #803, 2026-10-31). |
| Research | [M3.5 — Native proposal predictor](https://github.com/jayanez/agent-braid/milestone/9) | Synthetic-only T002/T004 software is complete; zero real pairs are admitted. Tasks T001, T007, T003 and T005 are open for source admission, protocol, real-feed adaptation, experiment and review; they sit in Deferred #24 since the milestone closed on 2026-10-31 (#803). |
| Adoption | [ADP.1 — Recorded-trace adapters](https://github.com/jayanez/agent-braid/milestone/10) | **Closed (2026-10-31), human review pending.** Generic synthetic metadata import and bounded lifecycle spikes provide engineering evidence; real-source admission and provider adoption remain pending. |
| Research | [LAB.1 — Effectful workload lab](https://github.com/jayanez/agent-braid/milestone/11) | Contract and design work; no real external execution is authorized (closure PR #798, 2026-10-31). |
| Research | [RES.1 — Formal interaction research](https://github.com/jayanez/agent-braid/milestone/12) | Contextual and proof-obligation work is bounded research (closure PR #798, 2026-10-31); finite checking is not a proof of generality. |
| System 1 | [S1.0 — Decision contracts](https://github.com/jayanez/agent-braid/milestone/13) | **Closed as deferred (2026-10-31).** SPEC-028's standard-library synthetic reference core is implemented and technically reviewed; human review and feature acceptance remain pending. The bounded verified-decision delivery lot (registry and selection, DDP-T04/T05, SPEC-028/T010–T011) is checked as bounded engineering only; human, scientific, promotion and activation gates remain pending. **True state (2026-11-01 [completeness audit](system-one/addenda/completeness-audit-20261101/README.md)):** the code is on `develop` (about 4,360 lines in `agent_braid/system_one*.py` and `mcp_advice.py`) but has no product callers; the only entry point is the opt-in `agent-braid system-one` command over synthetic fixtures; no learned model exists and no use has been observed. |
| System 1 | [S1.1 — Decision evaluation](https://github.com/jayanez/agent-braid/milestone/14) | **Closed as deferred (2026-10-31).** Prospective, permissioned corpus and evaluation gates are planned; no accepted utility claim. The bounded IR and compatibility lot (DDP-T02/T07, SPEC-029/T026–T027) is checked as bounded engineering only; human, scientific, promotion and activation gates remain pending. **True state (2026-11-01 [completeness audit](system-one/addenda/completeness-audit-20261101/README.md)):** no permissioned corpus was admitted and the registered SPEC-029 T009 comparison never ran; the open tasks sit in milestone Deferred #24. |
| System 1 | [S1.2 — Native decision model](https://github.com/jayanez/agent-braid/milestone/15) | **Closed as deferred (2026-10-31).** Model experiments remain gated by rights, feasibility and common evaluation; no learned model is accepted. **True state (2026-11-01 [completeness audit](system-one/addenda/completeness-audit-20261101/README.md)):** the milestone delivered no closed work; no learned model exists (`stdlib-rule-fixture-v1`, calibration absent). |
| System 1 | [S1.3 — Advisory integration](https://github.com/jayanez/agent-braid/milestone/16) | **Closed as deferred (2026-10-31).** Integration remains advisory and gated by core evidence; no authority escalation. The bounded acquisition and controlled-consumer lot (DDP-T03/T06, SPEC-031/T010–T011) is checked as bounded engineering only; human, scientific, promotion and activation gates remain pending. **True state (2026-11-01 [completeness audit](system-one/addenda/completeness-audit-20261101/README.md)):** the advice wrappers have no source callers and telemetry cannot observe them; real-use sources show zero System One invocations. |
| System 1 | [S1.4 — Product capabilities and promotion](https://github.com/jayanez/agent-braid/milestone/17) | **Closed as deferred (2026-10-31).** Capability choices and promotion are separate decisions; no capability promotion is implied. SPEC-033/T009 (DDP-T08) is checked as documentary gate packaging only; human, scientific, promotion and activation gates remain pending. **True state (2026-11-01 [completeness audit](system-one/addenda/completeness-audit-20261101/README.md)):** no capability is wired into a product path; promotion has no recorded evidence to decide on. |
| System 1 | [S1.5 — Shadow activation](https://github.com/jayanez/agent-braid/milestone/26) | **Opt-in shadow mode supported (S1.5a merged #860, #940; plugin `0.1.0-alpha.5` and later); S1.5a closed 2026-11-10; reviewable rule-based DP-1 advise merged and published in plugin `0.1.0-alpha.9` ([record](../specs/066-system-one-shadow/release-acceptance-alpha9.md)), not live (no owner go); `specs/066-system-one-shadow/spec.md` Status is draft on 2026-11-26.** [SPEC-066](../specs/066-system-one-shadow/spec.md) and [ADR 0034](adr/0034-system-one-shadow-advisory-boundary.md) specify an opt-in, local shadow recorder next to the unchanged System 2 result. The owner's shadow week (2026-11-02 to 2026-11-09) gave 25 episodes, 142 pairs, all `abstained` (counts only, no utility claim); the owner closed S1.5a on 2026-11-10 and started S1.5b. The 2026-11-14 sibling-pair feasibility check (B0) is INFEASIBLE (3015 labelled pairs, 4 System-2-`unknown`), so S1.5d (T301–T303, learned model) is Deferred under the Wilson GO rule (D3). Owner decisions of 2026-11-14: D6 a reviewable rule-based DP-1 advise under a risk-accepted GO (REQ-402, ADR 0034 addendum #1379), D7 automatic rollback to `shadow` at the first real conflict on an advised-independent pair, D8 GO packet 2026-11-28, `advise` live 2026-11-30, mandatory review 2026-12-31 (the go expires at review). Merged: promotion registry and `advise` plumbing (T401 early, #1374), DP-1 structural rule, `systemOneAdvice` in effective `advise` and the owner `system-one promote` command (T404, #1375), merge-outcome join, false-independence and Wilson report and the D7 rollback (T405, #1389). Open: T406 (owner decision packet, owner only). State on 2026-11-16: 29 shadow episodes, 0 joined outcomes, the `runtime-state` source refused `path-outside-admitted`; a weekly read-only count task runs Mondays. No utility claim, no learned model; `advise` is not live. |
| Forecasting | [FC.1 — Forecast-guided parallelism experiment](https://github.com/jayanez/agent-braid/milestone/18) | Four forecast-program specs define permissioned telemetry, optional local forecasting and complete-cost experiments; no execution-domain expansion or utility acceptance. |
| Harness | [HAR.1 — Braid Harness laboratory](https://github.com/jayanez/agent-braid/milestone/21) | **Open on 2026-11-26 with 2 open parent issues (SPEC-048, SPEC-065); all their tasks are done.** SPEC-048: 15 of 15 tasks done; T008 closed on 2026-11-20 with the Claude profile qualified with limits (founder T008-11: Haiku and subscription route only, EUR 0, no cross-unit independence or effort claim); Codex stays refused and moves to a later milestone as concrete tasks (owner decision E3, 2026-11-16). SPEC-065 (native Claude containment): 15 of 15 tasks done; qualified on 2026-11-17 until 2026-12-17T22:19:29Z (one machine, Claude only); approved by the owner on 2026-11-21 with documented limits (review record bound to `a768e6d3`; T012-01 to T012-03 required in the next re-qualification). Experimental `agent-braid harness` CLI ([Harnessing](tooling/HARNESSING.md)), now countable in local telemetry with `--telemetry local` (batch schema v4, #1405); no paid route, promotion or MCP surface. |
| Harness | [HAR.2 — Braid Harness evaluation and learning](https://github.com/jayanez/agent-braid/milestone/22) | **Closed 2026-11-24 (owner) with its actual scope.** Offline evaluation complete; native cohort inconclusive; no-go on both axes; harness experimental under D7; unmeasured items carried to HAR.4. SPEC-049: 14 of 14 tasks done, with the T010 dispositions of 2026-11-23 (`evidence/t010.json`): utility inconclusive on both axes, the native route feasible on one machine until the SPEC-065 expiry, Luna D5 requested and not obtained, rollout experimental with nothing promoted; the six endpoints, effort, costs and arm D carried to HAR.4 (SPEC-082/083/084). The native cohort T014 ran on 2026-11-20/21 (15 of 15 slots, 13 correct; descriptive only) and was closed as inconclusive; T007 records no-go for native ordinary use on both axes, and SPEC-050 D7 keeps the harness experimental with nothing promoted (owner, 2026-11-22, `evidence/t007.json`). SPEC-067 (assurance profiles, tracked in the HAR.3 milestone): 11 of 13 tasks done; approved by the owner on 2026-11-22 with documented limits (review record bound to `2b48a5d6`, after two Codex reviews and fixes #1477/#1488). Open: T012 and T013 (Codex findings C67-005/006). |
| Harness | [HAR.3 — Braid Harness adaptation and integration](https://github.com/jayanez/agent-braid/milestone/23) | **In progress.** SPEC-050: 11 of 12 tasks done, all offline (components, skills, hooks, orchestration, search, curation, disabled auto-policy, lifecycle, advisory). T004 closed offline-only on 2026-11-23 (E3 adapter against deterministic doubles only, section 13 drafted, not adopted; `evidence/t004.json`) and its native remainder carried to SPEC-084/T015. Open: T012 portfolio review, which waits for the D6 usability observation after alpha.10 (with the SPEC-080 skill) and the requested Luna review D5. SPEC-077: not published (T008, 2026-11-22) because T014 was inconclusive and D7 closed the harness as experimental; ADR 0043 rejected; T001, T003 to T007 and T009 moved to Deferred. SPEC-080 (read-only `harness` skill in every host; ADR 0044 Accepted 2026-11-23; T001 owner review done, all seven decisions with the recommended option): draft, documentation only. |
| Harness | [HAR.4 — Harness evaluation platform](https://github.com/jayanez/agent-braid/milestone/37) | **Open on 2026-11-26 (67 open, 6 closed issues; the 6 closed are owner and Codex review tasks: SPEC-082 T001/T002, SPEC-083 T001/T002, SPEC-085 T001, SPEC-086 T001).** SPEC-082 (task QA and infrastructure controls), SPEC-083 (capability versus regression evaluations), SPEC-084 (Harbor containers plus a macOS shadow; ADR 0045 Proposed; T001 part 1 recorded in #1655), SPEC-085 (promotion pointers) and SPEC-086 (OTel GenAI telemetry) were refined on 2026-11-26 (#1666, #1667, #1674, #1679); no implementation task is closed. Basis: [harnessing benchmark](strategy/HARNESSING_BENCHMARK.md). |
| Tooling | [M4.9 — AI tooling integration for Pi and ThinkRail](https://github.com/jayanez/agent-braid/milestone/38) | **Planned (documentation only).** SPEC-081 draft: Pi package with skills and MCP entry, installer profile, build target and diagnosis, after an observation of real Pi and ThinkRail installs; nothing implemented. |
| Visualization | VIS.1 — Activity viewer (#25) | **In progress; VIS.1a closed and frozen 2026-11-03; T047 review follow-ups done 2026-11-03 (#1025, #1026, CI now runs the wheel and sdist tests); VIS.1b go/no-go T035 by 2027-01-31 is pending real use. VIS.1d dashboard relaunch (2026-11-05): dashboard shell, live loom and plan map (#1086), `view open` (#1094), Explore 3D, audit and docs (T068–T073 except the VoiceOver pass); T074 closure pending owner review.** Event contract `agent-braid-loom/v0.1`, adapters, ring store, viewer model, loopback server, `agent-braid view` CLI, the first-party web table view and the Three.js braid scene are merged, and the built wheel ships the web bundle (usable from a source checkout or an installed package). Earlier draft note: [SPEC-061](../specs/061-activity-viewer/spec.md) specifies a read-only, loopback-only activity viewer in two deliveries (VIS.1a coordination slice, then VIS.1b effort, recording and export) with a go/no-go checkpoint between them; ADR 0032 and ADR 0033 were accepted on 2026-11-01 (Three.js pinned at r186). Owner review T001 accepted the specification on 2026-11-01; the go/no-go checkpoint T035 is due by 2027-01-31. VIS.1a implementation history: contract, validation rule, artifact adapters, event store, vendored Three.js r186, view model, ownership/gate adapters, loopback server, event stream, replay and watch, Claude hooks ingest merged (2026-11-02); web table view, bundle security tests, `view` CLI and Three.js braid scene merged (2026-11-03); VIS.1a amendment A1–A4 (2026-11-03): plugin keeps 30-day private copies of `analyze-work` reports, `serve` discovers them from registered result roots, source checkboxes merged; wheel packaging (T043, 2026-11-03) and per-root checkboxes with a start banner that maps `root N` to its path (T044) merged. VIS.1a closure (2026-11-03): boundary tests, viewer guide (`docs/tooling/VIEWER.md`) and closure review (#1011), closure fixes (#1013), evidence (#1017); the owner approved the closure and the assurance record is frozen; the T035 go/no-go for VIS.1b is pending. Probes 2026-11-01: T030 (two field-level mismatches) and T032 verified; T031 unobserved until the Codex usage limit resets; census T038 met (11 non-synthetic sessions, mostly Agent Braid's own development; 5 of 6 kinds; no grants); T033 pending. VIS.2–VIS.4 are planned derived tracks. |
| Optimization | BL.0 — Braid Lightning foundations (milestone created after merge) | **Closed 2026-11-08** ([#1164](https://github.com/jayanez/agent-braid/pull/1164); owner review of candidate `c0b6956e`). SPEC-070: ADRs 0039–0041 accepted, 0042 deferred; opt-in consent, `lightning init` wizard, validated profile and private run store. No run, host launch or model call. |
| Optimization | [BL.1 — Lightning rollouts and verifiable reward](https://github.com/jayanez/agent-braid/milestone/30) | **Closed 2026-11-11** (owner review of candidate `39a427ae`). SPEC-071: `lightning_hosts` extracted from the SPEC-069 driver, subscription-only `lightning_runner`, verifiable `lightning_reward`, hooks, `lightning run/status/report`, fake-host pipeline with negative controls; real Claude Code baseline 16/30 inside the T010 interval with zero paid-route observations (route-changed comparison). OpenCode is a declared limit (OD-2). |
| Optimization | [BL.2 — Lightning prompt optimization](https://github.com/jayanez/agent-braid/milestone/31) | **Complete with a negative result (2026-11-13).** SPEC-072 T001–T013 done and converged (T012): APO and GEPA from the paper, contamination controls, budgets, replay, protocol frozen by hash before the held-out run. Held-out in Claude Code (`claude-sonnet-5-5`, 90 rollouts, subscription route): A0 25/30, A1 APO 23/30, A2 GEPA 24/30, all miss D4; H1 not supported. No candidate for promotion. OpenCode is a declared limit; exploratory arms E1/E2 not run. |
| Optimization | BL.3–BL.5 — Braid Lightning promotion, trace consent, dataset export | **BL.3 open on 2026-11-26 (3 open issues: SPEC-073 parent, T010, T011); T007 rollback, T008 revocation and T009 reflections merged 2026-11-24 (#1638, #1639, #1640) and the T010 owner rollback drill script on 2026-11-24 (#1648); no BL.2 candidate has been promoted. BL.4 closed 2026-11-14 and BL.5 closed 2026-11-17 (SPEC-074 and SPEC-075 approved by the owner on 2026-11-17, review records bound to `a5a7235c` and `21926de6`; export off by default, terms gate closed).** SPEC-073 to SPEC-075; SPEC-076 (local GPU GRPO) under Deferred. [BL.2c — Lightning tool-level kind-choice fix](https://github.com/jayanez/agent-braid/milestone/36) (SPEC-079) is open on 2026-11-26 (4 open issues: parent, T008, T009, T010); T007 froze the v4 protocol on 2026-11-24 (#1643) and registered `v4-test` in the runner (#1650). [Program](../specs/070-braid-lightning-foundations/program.md). |
| Optimization | [BL.2b — Lightning held-out re-evaluation](https://github.com/jayanez/agent-braid/milestone/35) | **Opened 2026-11-20, closed 2026-11-22** (milestone API, 17 issues closed). SPEC-078: HELD-04 guidance fix merged (#1445); held-out v2 with Gate 0 and baseline A0 first; optimization only if A0 misses. |

### Runtime and evidence boundaries

SPEC-021's historical study found equal verified trees in six paired trials,
with a median serial/parallel total-wall ratio of **0.5581**. In that small,
uncontrolled sample, serial execution took about 55.81% of parallel total wall
time. This is descriptive evidence, not a population estimate or a general
claim about parallelism. The [G4 decision](../specs/021-m4-alpha-runtime/g4-decision.json)
remains authoritative.

SPEC-022 completed its registered synthetic capture on candidate `b85f7e5`:
88/88 valid pairs (8 warm-up, 80 measured; 176 treatments), with five blocks
excluded by pinned caps. Required in-treatment verification completed; fresh
inspection verified capture structure and bounded replay, and four fresh control
suites passed (76 tests). All three admitted independent diagnostic blocks were
negative; the dependency-chain block was an order control. These fixture results do not establish general speedup or utility. On 2026-10-08,
the owner approved a bounded T006 interpretation: no useful-speedup claim or
parallel performance default for the measured families. This is not a general
claim about parallelism; SPEC-021 G4 NO-GO remains. See the
[decision packet](../specs/022-m4-utility-followup/decision-packet.md) and [derived
capture summary](../specs/022-m4-utility-followup/evidence/registered-capture-summary-b85f7e5.json)
for ratios, full costs and inspection limits.

SPEC-027 has implemented read-only
refinement assessments and synthetic/disposable controls. The founder recorded
NO-GO/defer dispositions for source promotion, arbitrary code execution and real
external effects by the bounded M4 alpha runtime; no capability was adopted and no
expanded execution authority was granted. SPEC-038 completed a bounded registered capture on
candidate `e66f9a1`: all 20 treatment slots were valid (eight warm-up and 12
measured treatments across ten pairs, of which six were measured), and the mandatory fresh-process
verifier reported `verified` for all 20 before conditional cleanup. The six
measured serial/parallel total-wall ratios were below one (median
`0.6538998702917553`; AB median `0.6530442113`, BA median `0.6547555293`), a
finite negative result for parallel utility on this exact two-operation source
frame. On 2026-10-09 the founder accepted bounded M4 alpha engineering and
evaluation as complete with negative utility. The decision preserves historical
G4 NO-GO and does not establish general utility, production safety, semantic
correctness or a scientific result. Current GitHub tracking is shown in the [live M4 milestone](https://github.com/jayanez/agent-braid/milestone/6). The checks establish tracked Git-tree
equality for the admitted orders, not semantic equivalence or native-code validity. No real-source
interruption/recovery controls were run. See the [derived capture
summary](../specs/038-m4-real-workload-closure/evidence/registered-capture-summary-e66f9a1.json)
for bounded evidence and limits. SPEC-021 G4 remains NO-GO. The [whole-M4
decision](../specs/038-m4-real-workload-closure/whole-m4-founder-decision-20261009.json)
and [closure packet](../specs/038-m4-real-workload-closure/whole-m4-closure-packet.md)
record the bounded acceptance and its limits. Current GitHub tracking is shown in the [live M4 milestone](https://github.com/jayanez/agent-braid/milestone/6).

On candidate `e66f9a1`, Codex CLI 0.162.0-alpha.2 completed a bounded Darwin
arm64 direct-tool-bridge observation with zero model calls. It exercised all six
MCP tools, refusal, disconnect recovery, independent-prefix verification,
completion, duplicate suppression and abort. The Codex run matched 80 runtime input
hashes; a separate 201-file pre-import guard has a different scope. Linux
reproduced 68 core, policy, scheduler and protocol tests with no skips on the same
candidate. Source, candidate, client binary and persistent host configuration were
unchanged. A separate model-mediated Claude Code 2.1.285 capture recorded missing-grant
refusal, a verified checkpoint interruption and recovery, completion, and consumed-grant
retry suppression; its 201-file pre-import guard is a distinct check. Independent Luna review found no findings within the stated capture scope; the capture did not test abort. These observations
remain bounded to their stated host and fixture scopes and do not change the G4 NO-GO.
See the [Codex host record](../specs/021-m4-alpha-runtime/evidence/current-codex-host-e66f9a1.md),
[current Claude host record](../specs/021-m4-alpha-runtime/evidence/current-claude-host-e66f9a1.md),
[Linux reproduction record](../specs/021-m4-alpha-runtime/evidence/current-linux-core-protocol-e66f9a1.md)
and [six-row exit matrix](../specs/021-m4-alpha-runtime/closure-matrix.md).

A separate Darwin core-suite reproduction on `e66f9a1` first passed 67 of 68
tests and retained one hooks-directory error. A focused 1-test diagnostic passed;
a corrected full run then passed all 68 tests without skips. Both later runs used a
minimal private Git template and a separate 201-file guard; the original run binds
only its 80-input fingerprint. All three runs used fresh Python processes, but
reused the existing isolated Python 3.13.11 environment. This is not a clean-room
reproduction or a host-adapter observation. See the [Darwin test record](../specs/021-m4-alpha-runtime/evidence/current-darwin-core-e66f9a1.md).

M3.5 synthetic software checks include deterministic synthetic fitting, calibration, inference and evaluation controls plus verifier-boundary tests. They establish those bounded software behaviors only. They do not establish real-source rights, prospective registration, real-feed adaptation, capture, real-workload fit, predictor benefit or scientific validation. The scope-bound synthetic software work for T002/#182 and T004/#184 is complete; the M3.5 experiment and milestone remain open. See the [M3.5 readiness note](development/m35-technical-readiness.md),
[Linux runbook](development/linux-experiments.md), [M4 cost diagnostics](development/M4_RUNTIME_COST_DIAGNOSTICS.md)
and [delivery record](development/autonomous-delivery.md).

Historical internal closure records and their limits are in [release records](releases/).
The founder reviewed those closures and has an explicit conflict of interest;
independent external validation remains pending. The [public cutover audit](releases/publication/CUTOVER_AUDIT_2026-09-25.md)
tracks historical authorization reconciliation separately from repository
availability. For the complete future work inventory, see the [foundational
implementation portfolio](development/FOUNDATION_IMPLEMENTATION_PORTFOLIO.md),
[System 1 program](../specs/028-system-one-core/program.md), [forecast program](../specs/034-workload-forecast-data/spec.md)
and [roadmap](../ROADMAP.md).

<a id="scientific-contract"></a>


## Accounting and identity notes

The experimental registration-v4 accounting route supports the owner-selected
estimated subscription convention, with actual allocation unknown. The owner
also approved the additive [operational subscription capture policy
v3](../specs/044-ai-tooling-evaluation/operational-subscription-capture-policy.md)
for registration-v5. It binds the native process route and fresh quota state,
uses a bounded supervisor, and keeps actual cash unknown until independent
verification gates acceptance and positive utility. Additional spend remains
EUR 0; no purchase, overage or paid fallback is permitted. Strict registration
v1/v2 behavior, the 108-slot roster and deferred human review remain unchanged.
The additive implementation and synthetic controls are available. Authentic
process-bound native evidence, complete registration approval and capture
authorization remain pending. The [technical completion preparation](tooling/TECHNICAL_COMPLETION_20261011.md)
records package preparation, native-interface limits and the selected free
Linux x86_64 route; no registered slot has launched.

The [local telemetry identity reconciliation](../specs/047-local-technical-telemetry/identity-reconciliation-b13737ed4584.md) assigns SPEC-047/ADR-0025 to telemetry while preserving native plugin SPEC-046/ADR-0024 and all frozen evidence. Installation and default-off consent are unchanged; pilot **NO-GO** and tasks remain open.

## Capability coverage

| Capability | Working surface | What the evidence covers |
| --- | --- | --- |
| **Inspect agent interactions** | AIM analyzer, effect graph and JSON/text reports | Exact-resource conflicts, dependency order and conservative `unknown` results. |
| **Replay changes before execution** | Read-only Git adapter, replay verifier and advisory preparation waves | Every admissible order of **2–4 immutable commits**, under the declared tracked-tree observation. |
| **Check structured exchanges** | `anchored-sequence-v1` producer and consumer | Context-dependent insert residuals, retained intermediate paths and bounded braid-relation controls. |
| **Run an owned Git pipeline** | Verified policy plans, local grants, isolated preparation and serial publication | Fixed text patches, checked paths/modes/blobs, private results and process-interruption resume/abort. |
| **Connect through stdio MCP** | Six bounded tools: `analyze`, `prepare`, `status`, `execute`, `recover`, `verify` | Configured source/result roots and the same local policy; grant issuance stays with the operator. |
| **Prepare and inspect M3.5 proposals** | Synthetic trainer/inference, evaluator controls, hidden-proposal journals, session/pair accounting, filtered labs and aggregate seals | Software scope completed for T002/T004 on caller-declared synthetic inputs; **zero admitted real pairs**. Real-feed adaptation, source rights, protocol approval, capture, real fit and held-out evaluation remain gated. |
| **Inspect local System 1 decisions** | Opt-in `system-one` diagnostics with a standard-library reference backend, plus a verified typed-plan selection core with Core, stdio and opt-in MCP SDK consumers | Synthetic requests and owned fixtures in a finite two-to-four-operation grammar. Since plugin `0.1.0-alpha.5` an opt-in System One shadow mode (SPEC-066 S1.5a) records one structural episode per successful `analyze-work` call on the machine, with `system-one report|purge` and a `system-one` telemetry operation; outputs are unchanged and the reference backend abstains. No learned model, calibration, accepted utility or execution authority; the first owner shadow week (2026-11-02 to 2026-11-09) recorded 25 episodes, all abstained. A reviewable rule-based DP-1 advise is merged but not live (owner go packet 2026-11-28). |
| **Use Agent Braid from Codex, Claude Code or OpenCode** | Native user plugins (`0.1.0-alpha.9`, a pre-release published 2026-11-16; rollback target `0.1.0-alpha.8`) with bundled runtime, skills, workspace registry and guided setup; plugin versions are a separate line from the Python package (`0.1.0a2`) | Alpha.2 passed both native interactive journeys; alpha.3 was observed on macOS Claude Code only; alpha.4 on macOS Claude Code and, through the CLI and loader, Codex; alpha.5 (System One shadow mode) is published with engineering checks only; alpha.6 (published 2026-11-03) adds registry quarantine (deleted worktrees no longer disable the plugin; `plugin setup --prune-stale`), the `telemetry-audit` skill and a `pluginVersion` field in `plugin-status`, with engineering checks only; alpha.7 (published 2026-11-04) adds the OpenCode native plugin (SPEC-068; `plugin doctor --host opencode`, `install.sh --host opencode`/`all`, a legacy `tooling install --host opencode` profile), with engineering checks, a disposable-profile OpenCode observation on macOS arm64 and a post-publication install smoke, and the native host observations of alpha.6 and alpha.7 in Claude Code and Codex pending; M4.5 product support and acceptance remain open. |
| **Forecast local workloads** | Opt-in `forecast` predict/advice/inspect/export, optional Chronos-2 adapter and a read-only stdio MCP transport | Synthetic and frozen paired controls with episode-cluster uncertainty; advice is heuristic and grants no parallelism or utility claim. |
| **Measure your own usage locally** | Default-off `telemetry` with a private bounded SQLite store and manual export/merge/purge | Numeric aggregates only, no automatic transmission; pilot remains **NO-GO**. Since plugin `0.1.0-alpha.6` it also counts closed refusal reasons and plugin server starts (batch schema v2) and offers a read-only `telemetry audit-logs` comparison of host MCP logs with the store; no field-use evidence yet. |

## Native plugin release

The preferred installation route is the **native user plugin** for Codex or
Claude Code on macOS arm64 and Linux x86_64. It includes Python and dependencies,
registers its skills automatically and guides you through selecting repositories.
As of 2026-11-26 the latest release is `0.1.0-alpha.9` (published 2026-11-16, tag
[`agent-braid--v0.1.0-alpha.9`](https://github.com/jayanez/agent-braid/tree/agent-braid--v0.1.0-alpha.9),
[release notes](tooling/RELEASE_NOTES_ALPHA9.md)) and the rollback target is
`0.1.0-alpha.8`. Observed installs (dated records): update, removal and reinstall
in Claude Code and Codex, and install, interactive skill and command use, update and
removal in OpenCode, all on macOS arm64
([alpha.4 record](../specs/046-native-ai-plugins/release-acceptance-alpha4.md),
[OpenCode observation](../specs/068-opencode-native-integration/evidence/native-observation.json));
Linux execution has not been observed. The history below starts at
`0.1.0-alpha.7`, whose marketplace is on `plugin-dist`,
with the pinned tag [`agent-braid--v0.1.0-alpha.7`](https://github.com/jayanez/agent-braid/tree/agent-braid--v0.1.0-alpha.7)
([readiness and notes](../specs/068-opencode-native-integration/release-readiness-alpha7.md)). It adds the
OpenCode native plugin (SPEC-068; [record](../specs/068-opencode-native-integration/release-acceptance-alpha7.md)); its Claude Code and Codex installs have not been observed, and OpenCode was observed on macOS arm64 only. The previous `0.1.0-alpha.6` (tag
[`agent-braid--v0.1.0-alpha.6`](https://github.com/jayanez/agent-braid/tree/agent-braid--v0.1.0-alpha.6),
[record](../specs/046-native-ai-plugins/release-acceptance-alpha6.md)) is the rollback target and added registry
quarantine, the `telemetry-audit` skill and `pluginVersion` in `plugin-status`; `0.1.0-alpha.5` (tag
[`agent-braid--v0.1.0-alpha.5`](https://github.com/jayanez/agent-braid/tree/agent-braid--v0.1.0-alpha.5),
[record](../specs/046-native-ai-plugins/release-acceptance-alpha5.md)) added opt-in
System One shadow mode (SPEC-066); alpha.4 removed the plugin MCP prompts and the
redundant skill prefixes (SPEC-054).
The portable MCP server in `develop` implements unprefixed prompt names with bounded
deprecated aliases (`agent-braid-tooling/v0.2`, package `0.1.0a2`):
[SPEC-060](../specs/060-portable-prompt-names/spec.md) is implemented and was accepted on
2026-10-27 under accepted [ADR 0031](adr/0031-portable-prompt-names.md). Package `0.1.0a2`
was published on 2026-10-27 as GitHub pre-release `v0.1.0-alpha.2` (wheel, sdist and
SHA256SUMS; no PyPI; see the [release record](../specs/060-portable-prompt-names/evidence/release-0.1.0a2.md)). An owner-provided capture of the Claude Code slash menu is recorded in the
[interactive menu result](../specs/060-portable-prompt-names/evidence/interactive-slash-result.md):
with the portable server under the key `agent-braid` beside the plugin, skill and prompt share
the same slash text but appear as distinct entries (the prompt carries an `(MCP)` suffix); under
a distinct key they differ. The alias deprecation marking is visible in both cases; the portable
server alone was not observed.
Native macOS observations (Claude Code update from alpha.3 and a public Git-tag
install; Codex CLI install, remove and reinstall) are in the
[alpha.4 acceptance record](../specs/046-native-ai-plugins/release-acceptance-alpha4.md);
interactive skill use and Linux were not observed. The
[alpha.3 record](../specs/046-native-ai-plugins/release-acceptance-alpha3.md) documents the
previous release. The
[alpha.2 record](../specs/046-native-ai-plugins/release-acceptance.md) holds the
earlier two-host journeys.
See [native installation and setup](tooling/NATIVE_PLUGINS.md) for marketplace
commands, repository selection and lifecycle operations. Neither installation nor
discovery registers a repository without the setup preview and explicit apply.

## Further records

| Topic | Records |
| --- | --- |
| Build and verify a local result | [Owned fixture tutorial](../examples/runtime/README.md) · [Alpha runtime / MCP](../specs/021-m4-alpha-runtime/quickstart.md) |
| Follow planned Codex and Claude Code support | [M4.5 integration guide](tooling/README.md) · [Capability matrix](../specs/039-ai-tooling-program/capability-matrix.md) |
| Prepare M3.5 sources | [Technical readiness](development/m35-technical-readiness.md) · [Prospective pilot](../specs/019-native-predictor/prospective-pilot.md) |
| Run Linux checks and inspect cost | [Linux execution](development/linux-experiments.md) · [Cost diagnostics](development/M4_RUNTIME_COST_DIAGNOSTICS.md) · [Delivery record](development/autonomous-delivery.md) |
| Follow project direction | [Roadmap](../ROADMAP.md) · [Implementation portfolio](development/FOUNDATION_IMPLEMENTATION_PORTFOLIO.md) · [Open-tooling strategy](strategy/OPEN_TOOLING_STRATEGY.md) · [Ecosystem](strategy/ECOSYSTEM.md) |
