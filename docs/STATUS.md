# Project status and evidence record

This page collects the dated status, candidate-bound evidence and open gates that
used to live in the main README. The README describes what Agent Braid is and how
to use it; this record keeps the detailed, time-stamped account of what has been
validated, on which candidates and within which limits. Live tracking is in the
[GitHub Project](https://github.com/users/jayanez/projects/6), the
[milestones](https://github.com/jayanez/agent-braid/milestones) and the
[roadmap](../ROADMAP.md).

Relative links below were rebased from the repository root to `docs/`.

### Newest work

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

**In progress, nothing released — [M4.6 Claude Code dynamic workflows](../ROADMAP.md#m46--claude-code-dynamic-workflows):**
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

The runtime executes allowlisted Git plumbing. Repository code, source-ref
promotion and broader agent/provider adapters require additional contracts and
authority. The [runtime demo](../examples/runtime/README.md) gives you a complete
owned fixture; the [alpha quickstart](../specs/021-m4-alpha-runtime/quickstart.md)
covers grants, recovery and MCP configuration.

### Codex and Claude Code integrations

[M4.5](../docs/tooling/README.md) is an open integration program adjacent to M4. Its
original six specs retain the planned MCP, skills, lifecycle, presentation and evaluation
scope. [SPEC-047](../specs/047-local-technical-telemetry/spec.md) adds default-off local
aggregate telemetry; the combined portfolio has eight source specifications. [SPEC-046](../specs/046-native-ai-plugins/spec.md) extends M4.5 with
native packaging, a shared workspace registry and setup; it does not reopen
historical acceptance or replace existing evaluation gates. Current local evidence now covers bounded technical controls and fresh
macOS/Linux package checks, each bound to its own candidate; it does not establish
native host support, M4.5 acceptance or milestone closure. The complete current
status and candidate-specific limits are in the [tooling status](../docs/tooling/TECHNICAL_STATUS.md).

The [autonomous technical closure record](../docs/tooling/AUTONOMOUS_COMPLETION.md)
and [technical evidence status](../docs/tooling/TECHNICAL_STATUS.md) now link the
candidate-bound package, Linux, engineering, program, MCP and lifecycle evidence.
MCP, program controls and lifecycle procedures passed on their recorded local
candidates; installed macOS and emulated Linux AMD64 package checks passed for
`53f1704`. The 223-test engineering suite passed on `aaae2e7`, with a separate direct
223-test run on `24921e1`. These are distinct source identities and observation
domains, not a single end-to-end candidate claim.

The first targets are **Codex local CLI and Claude Code local CLI**. M4.5 formal product
support and full acceptance remain pending. Separate bounded SPEC-021 host
observations for Codex and Claude are linked below; they do not establish M4.5
product support or acceptance. Cursor, VS Code/GitHub Copilot, OpenCode and pi are
future routes. Start with the [integration guide](../docs/tooling/README.md) for the
spec, contract and task map.

### Optional local diagnostics

The [integration record](../specs/047-local-technical-telemetry/integration-review.md)
identifies the reviewed telemetry source, current base and pending acceptance gates.

The integration candidate adds local numeric telemetry to the portable MCP service and two analyzer CLI commands. It is **off by default**, has no automatic transmission, uses a private bounded SQLite store and retains 30 UTC dates on access. Installation previews/receipts expose the explicit server consent; skills never enable collection. Read [installation](../docs/tooling/INSTALL.md) and [telemetry privacy, commands and limits](../docs/tooling/TELEMETRY.md) before opting in.

```sh
agent-braid analyze /absolute/input.json --telemetry local
agent-braid telemetry status --format json
agent-braid telemetry report
agent-braid telemetry export /absolute/private/telemetry-batch.json
agent-braid telemetry merge /absolute/private/received-batch.json
agent-braid telemetry purge
```

Exports are incremental manual aggregates and have no persistent installation identity. Full evidence exports remain separate. Uninstall keeps metrics; explicit purge clears local data/deduplication and cannot revoke copies. The [M4.5 alignment](../docs/tooling/M45_ALIGNMENT.md) records current source inventory, prior SPEC-044/T004 bounded closure and pending candidate admission; historical checks below do not cover this changed candidate.

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


## 🧭 Evidence and project status

**Project status on 2026-10-11:** research alpha. The source inventory includes
44 specs and 19 registered GitHub milestones. M4.5 remains Open. Its 60 original
acceptance criteria are unchanged; 19 auxiliary tasks add evidence work. The six
source task files now show 52 checked and 27 unchecked boxes (79 total), plus six
open parents. These source counts do not assert remote issue state. “Closed” is
the remote milestone state; implementation, scientific acceptance and external
review remain distinct. The [spec and milestone index](../docs/development/SPEC_MILESTONE_INDEX.md)
lists every current assignment.

| Track | Milestone | State and evidence boundary |
| --- | --- | --- |
| Foundations | [M0 — Operational foundations](https://github.com/jayanez/agent-braid/milestone/1) | Closed; internally closed. Independent external validation remains pending. |
| Foundations | [M0.5 — Open strategy and preview preparation](https://github.com/jayanez/agent-braid/milestone/2) | Closed; internally closed. Two historical review items remain open in tracking. |
| Foundations | [M1 — Observable interaction analyzer](https://github.com/jayanez/agent-braid/milestone/3) | Closed internally against the reviewed candidate; independent external validation remains pending. |
| Research | [M2 — Confluence lab and scheduler](https://github.com/jayanez/agent-braid/milestone/4) | Closed internally. Bounded replay and finite observations do not establish general confluence. |
| Research | [M3 — Braid semantics](https://github.com/jayanez/agent-braid/milestone/5) | Closed internally for `anchored-sequence-v1`; no general braid or Yang–Baxter theorem is claimed. |
| Runtime | [M4 — Agent Braid runtime](https://github.com/jayanez/agent-braid/milestone/6) | Founder accepted bounded alpha engineering and evaluation as complete on 2026-10-09, with negative utility. Current GitHub tracking is shown in the [live M4 milestone](https://github.com/jayanez/agent-braid/milestone/6). Historical SPEC-021 G4 remains **NO-GO** on useful speedup under its frozen evidence. |
| Integration | [M4.5 — AI tooling integrations for Codex and Claude Code](https://github.com/jayanez/agent-braid/milestone/19) | **Open.** Candidate-bound local paired procedures, package checks and technical controls passed within their stated domains. The combined source inventory is 102/131 tasks checked, 29 open, with three historically closed parents, the closed SPEC-054 parent and six open spec parents (SPEC-060 adds the portable prompt names contract); SPEC-039/040/042 retain their recorded bounded acceptance. Native-host acceptance, human interpretation, remaining founder decisions and milestone closure remain open. |
| Publication | [PUB.1 — Public research preview](https://github.com/jayanez/agent-braid/milestone/7) | **Open.** The preview is public; historical publication authorization reconciliation remains separately tracked. |
| Governance | [GOV.1 — Governance and adoption](https://github.com/jayanez/agent-braid/milestone/8) | **Open.** Governance and adoption evidence work continues; issue state does not confer human or founder approval. |
| Research | [M3.5 — Native proposal predictor](https://github.com/jayanez/agent-braid/milestone/9) | **Open.** Synthetic-only T002/T004 software is complete; zero real pairs are admitted. T001/T007/T003/T005 and #180 remain open for source admission, protocol, real-feed adaptation, experiment and review. |
| Adoption | [ADP.1 — Recorded-trace adapters](https://github.com/jayanez/agent-braid/milestone/10) | **Open.** Generic synthetic metadata import and bounded lifecycle spikes provide engineering evidence; real-source admission and provider adoption remain pending. |
| Research | [LAB.1 — Effectful workload lab](https://github.com/jayanez/agent-braid/milestone/11) | **Open.** Contract and design work is in progress; no real external execution is authorized. |
| Research | [RES.1 — Formal interaction research](https://github.com/jayanez/agent-braid/milestone/12) | **Open.** Contextual and proof-obligation work remains bounded research; finite checking is not a proof of generality. |
| System 1 | [S1.0 — Decision contracts](https://github.com/jayanez/agent-braid/milestone/13) | **Open.** SPEC-028's standard-library synthetic reference core is implemented and technically reviewed; human review and feature acceptance remain pending. |
| System 1 | [S1.1 — Decision evaluation](https://github.com/jayanez/agent-braid/milestone/14) | **Open.** Prospective, permissioned corpus and evaluation gates are planned; no accepted utility claim. |
| System 1 | [S1.2 — Native decision model](https://github.com/jayanez/agent-braid/milestone/15) | **Open.** Model experiments remain gated by rights, feasibility and common evaluation; no learned model is accepted. |
| System 1 | [S1.3 — Advisory integration](https://github.com/jayanez/agent-braid/milestone/16) | **Open.** Integration remains advisory and gated by core evidence; no authority escalation. |
| System 1 | [S1.4 — Product capabilities and promotion](https://github.com/jayanez/agent-braid/milestone/17) | **Open.** Capability choices and promotion are separate decisions; no capability promotion is implied. |
| Forecasting | [FC.1 — Forecast-guided parallelism experiment](https://github.com/jayanez/agent-braid/milestone/18) | **Open.** Four forecast-program specs define permissioned telemetry, optional local forecasting and complete-cost experiments; no execution-domain expansion or utility acceptance. |

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

M3.5 synthetic software checks include deterministic synthetic fitting, calibration, inference and evaluation controls plus verifier-boundary tests. They establish those bounded software behaviors only. They do not establish real-source rights, prospective registration, real-feed adaptation, capture, real-workload fit, predictor benefit or scientific validation. The scope-bound synthetic software work for T002/#182 and T004/#184 is complete; the M3.5 experiment and milestone remain open. See the [M3.5 readiness note](../docs/development/m35-technical-readiness.md),
[Linux runbook](../docs/development/linux-experiments.md), [M4 cost diagnostics](../docs/development/M4_RUNTIME_COST_DIAGNOSTICS.md)
and [delivery record](../docs/development/autonomous-delivery.md).

Historical internal closure records and their limits are in [release records](../docs/releases/).
The founder reviewed those closures and has an explicit conflict of interest;
independent external validation remains pending. The [public cutover audit](../docs/releases/publication/CUTOVER_AUDIT_2026-09-25.md)
tracks historical authorization reconciliation separately from repository
availability. For the complete future work inventory, see the [foundational
implementation portfolio](../docs/development/FOUNDATION_IMPLEMENTATION_PORTFOLIO.md),
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
authorization remain pending. The [technical completion preparation](../docs/tooling/TECHNICAL_COMPLETION_20261011.md)
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
| **Inspect local System 1 decisions** | Opt-in `system-one` diagnostics with a standard-library reference backend, plus a verified typed-plan selection core with Core, stdio and opt-in MCP SDK consumers | Synthetic requests and owned fixtures in a finite two-to-four-operation grammar; no learned model, calibration, accepted utility or execution authority. |
| **Use Agent Braid from Codex or Claude Code** | Native user plugins (`0.1.0-alpha.4`) with bundled runtime, skills, workspace registry and guided setup | Alpha.2 passed both native interactive journeys; alpha.3 was observed on macOS Claude Code only; alpha.4 on macOS Claude Code and, through the CLI and loader, Codex; M4.5 product support and acceptance remain open. |
| **Forecast local workloads** | Opt-in `forecast` predict/advice/inspect/export, optional Chronos-2 adapter and a read-only stdio MCP transport | Synthetic and frozen paired controls with episode-cluster uncertainty; advice is heuristic and grants no parallelism or utility claim. |
| **Measure your own usage locally** | Default-off `telemetry` with a private bounded SQLite store and manual export/merge/purge | Numeric aggregates only, no automatic transmission; pilot remains **NO-GO**. |

## Native plugin release

The preferred installation route is the **native user plugin** for Codex or
Claude Code on macOS arm64 and Linux x86_64. It includes Python and dependencies,
registers its skills automatically and guides you through selecting repositories.
The experimental `0.1.0-alpha.4` marketplace is published on `plugin-dist`,
with the pinned tag [`agent-braid--v0.1.0-alpha.4`](https://github.com/jayanez/agent-braid/tree/agent-braid--v0.1.0-alpha.4).
It removes the plugin MCP prompts and the redundant skill prefixes (SPEC-054).
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
See [native installation and setup](../docs/tooling/NATIVE_PLUGINS.md) for marketplace
commands, repository selection and lifecycle operations. Neither installation nor
discovery registers a repository without the setup preview and explicit apply.

## Further records

| Topic | Records |
| --- | --- |
| Build and verify a local result | [Owned fixture tutorial](../examples/runtime/README.md) · [Alpha runtime / MCP](../specs/021-m4-alpha-runtime/quickstart.md) |
| Follow planned Codex and Claude Code support | [M4.5 integration guide](../docs/tooling/README.md) · [Capability matrix](../specs/039-ai-tooling-program/capability-matrix.md) |
| Prepare M3.5 sources | [Technical readiness](../docs/development/m35-technical-readiness.md) · [Prospective pilot](../specs/019-native-predictor/prospective-pilot.md) |
| Run Linux checks and inspect cost | [Linux execution](../docs/development/linux-experiments.md) · [Cost diagnostics](../docs/development/M4_RUNTIME_COST_DIAGNOSTICS.md) · [Delivery record](../docs/development/autonomous-delivery.md) |
| Follow project direction | [Roadmap](../ROADMAP.md) · [Implementation portfolio](../docs/development/FOUNDATION_IMPLEMENTATION_PORTFOLIO.md) · [Open-tooling strategy](../docs/strategy/OPEN_TOOLING_STRATEGY.md) · [Ecosystem](../docs/strategy/ECOSYSTEM.md) |
