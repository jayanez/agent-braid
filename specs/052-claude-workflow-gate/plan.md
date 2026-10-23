# Implementation plan — SPEC-052

Status: draft planning. Nothing here authorizes implementation, a version bump, a release, publication, remote issue creation, concurrent agents or autonomous delivery. Obtained evidence: none; human review pending. Founder decisions of 2026-10-23 recorded in the [spec clarifications](spec.md#clarifications) are binding inputs.

## Technical context and scope

Language and runtime: one plain-JavaScript workflow script, `integrations/agent-braid/plugin/workflows/braid-gate.js`, executed by the Claude Code workflow runtime; no module loading, no direct filesystem or shell access from the script itself (agents run the commands). Host: Claude Code with dynamic workflows (introduced in v2.1.154, documented current v2.1.309; the [workflows page](https://code.claude.com/docs/en/workflows) and [plugin components page](https://code.claude.com/docs/en/plugins/components) are the primary sources). Product side: the unchanged plugin MCP (`workspaces`, `analyze-work`, `analyze`, `prepare`), the bundled launcher, and `git`. Storage: none; the gate writes nothing to the source repository.

Scope is the read-only gate of the spec: five strictly sequential phases (validate, analyze, baseline, finalize, report) and at most four agents. Out of scope: transcripts and read hazards (SPEC-053, gate G0, then a gate v2), pre-flight partitioning (possible SPEC-054, gate G2), any fan-out, edit, merge, ref, hook, mod, plugin agent, grant, execution or remote artifact.

Verified Agent Braid code limits that bound the design (read from the repository at the planning commit; they are cited, not changed):

| Limit | Value | Source |
| --- | --- | --- |
| MCP frame, depth, operations, active calls, call timeout | 1 MiB, 32, 32, 4, 360 s | `agent_braid/tooling_mcp.py` (`MAX_FRAME_BYTES`, `MAX_INPUT_DEPTH`, `MAX_OPERATIONS`, `MAX_ACTIVE_CALLS`, `CALL_TIMEOUT_SECONDS`) |
| Plugin admission | one non-blocking global lock; busy returns a refusal | `agent_braid/plugin_mcp.py` (`PluginRouter.admission`) |
| Worktree sources | accepted only when the path is in the operator-configured allowlist; commit sources need no allowlist | `agent_braid/tooling_mcp.py` (`_analyze_work`) |
| Repository scope | the request repository must equal the registered source root | `agent_braid/tooling_mcp.py` (`_analyze_work`) and `agent_braid/mcp_runtime.py` |
| `analyze-git` effects | only added or modified files become write effects; deletions, symlinks, submodule entries and NUL-containing files become `B` (unknown, partial coverage); `--no-renames`; read versions empty | `agent_braid/git_adapter.py` (`_snapshot`) |
| Replay and runtime operations | 2 to 4; 64 paths; 1 MiB patches; 120 s replay | `agent_braid/git_replay.py`, `agent_braid/git_runtime.py` |
| `ordered` classification | only from declared dependencies; the gate declares none | `agent_braid/analysis.py` (`_interaction`) |

Planning findings from reading the code (each is recorded in [research.md](research.md); the wording differences they exposed were applied to [spec.md](spec.md) on 2026-10-23 after adversarial review, so spec and plan now agree):

1. The MCP surface has no `plan-git` or `verify-git` tool. Replay evidence and the advisory plan come from the MCP `analyze` and `prepare` tools (`git_replay.produce` inside `mcp_runtime.RuntimeTools`); `verify-git` exists only as a CLI command. The spec now states REQ-004/REQ-005 in terms of MCP `analyze`/`prepare`, with the bundled CLI (`plan-git`/`verify-git`) only on the constrained-CLI fallback path.
2. The `analyze` and `prepare` MCP requests are runtime requests: they require `order`, `expectedFinalTree`, per-operation `declaredWrites` equal to the observed paths, empty `uncertainPaths`, full 40-hex identifiers and 2 to 4 operations. The script must derive these from schema-bound results; where `expectedFinalTree` cannot be derived deterministically the gate reports `not-prepared` with a stated reason.
3. `prepare` rehearses in a temporary directory and does not allocate the run directory (`git_runtime.prepare_run`); `runDirectory` must still be a direct child of the registered result root. The gate therefore needs the registered `resultRoot`, which comes from the bootstrap `workspaces` tool.
4. Path rules in `scripts/validate_change.py` are all-match, so the new `.js` path is already sensitive through the `ai-tooling` rule (`integrations/agent-braid/**`); the planned rule (T018) is for explicitness and boundary text, not for rescuing an unknown path.
5. With runtime enabled, the plugin MCP lists `execute`, `recover`, `verify` and `status` next to the gate's tools (`agent_braid/tooling_mcp.py` tool list; the tool definitions are the union over registered workspaces in `agent_braid/plugin_mcp.py`). Prompt discipline is therefore not a control (Article 12; ADR 0021): the gate refuses runtime-enabled registrations from the `workspaces` rows and requires a host permission allowlist (REQ-016).

## Constitution check before research

Authorities: Constitution clause zero and Articles 1–3, 5–7, 9, 12–15, 19–21, 23–25 (as in the spec and `assurance.json`); GOVERNANCE.md; operational semantics; claim discipline; ADR 0014 and `docs/architecture/PARALLEL_INTEGRATION.md`; ADRs 0019 and 0020; ADR 0021; ADR 0024 (native plugins).

| Article | Obligation applied | Plan response |
| --- | --- | --- |
| 12 | Prompts and planning never substitute for concurrency control | Every gating rule (refusal rules, status, replay and prepare eligibility, agreement classification) is computed by script code from schema-bound agent results (T008–T014); the tool surface is restricted by refusing runtime-enabled registrations and by a host permission allowlist (REQ-016, T009, T012, T028) |
| 13, 14 | Declared class, property, evidence method, domain, assumptions, observation and execution contracts; evidence, not only a verdict | The envelope carries a script-set `assurance` block (class `0-heuristic`, `notAGuarantee`), the observation boundary and `unobserved` list (REQ-007, T013) |
| 15 | Effect metadata without coupling the core to a vendor | The workflow is an optional Claude-only package component; no core module imports it; Codex ignores it |
| 19 | Success is conflicts surfaced; real multi-worktree observation before workload claims | No agent-count or speed claim; fixture agreement does not generalize (T021 limits); native observation tasks (T030) |
| 20 | Analysis and execution stay separate | The gate never calls grant, execute, recover, status, verify or runtime-mode tools; `prepare` is serial, non-allocating and non-authorizing |
| 21, 23–25 | Authority, evidence and review boundaries | `executionAuthorization` constant false; obtained evidence empty; human review pending; nothing frozen or approved |

ADR 0021: grant issuance is never model-callable and host approval is not runtime authority; the plan keeps grants outside the workflow. ADR 0024: its wording ("the unchanged five product skills", "no installation/session hooks") needs the amendment in [adr-proposal.md](adr-proposal.md). Decision rule: MUST contradictions block; none is identified. The one SHOULD-level tension is shipping an executable-looking file before the ADR is adopted; the clarification permits the unreleased PR2 increment to merge only if no version bump, plugin-dist publication or release occurs before adoption, and T022 carries that condition. The condition is also enforced by the builder: until adoption `assemble()` excludes `workflows/` by default and includes it only with an explicit opt-in that marks the artifact engineering-only, so no package built from `develop` after PR2 silently carries the workflow under the published alpha.3 version string (T015, T016; the default flips at T036). The Constitution and its replica are not edited.

## Research, assumptions and alternatives

[research.md](research.md) records the decisions with rationale and alternatives. Summary of the binding choices:

- Commit sources only; refs resolved and pinned to full identifiers; at least two distinct sources; re-resolution at the end reports staleness.
- Four agents maximum, strictly sequential, no isolation, no parallel or pipeline, no `agentType`, no `workflow()` call inside the gate, `schema` on every agent call.
- The validate agent is the only agent that reads the workspace registry through the read-only bootstrap tool `workspaces` (needed to compare the registered source root with the repository root, to learn the result root and to refuse runtime-enabled registrations); it takes no admission lock. Analyze and finalize are the only calls that take the admission lock, one at a time. HV-1 must confirm bootstrap tools are visible.
- Baseline by `git merge-tree --write-tree` with an explicit merge base and a temporary object directory using the repository store as an alternate; merge results (pairwise and chained) are ephemeral and never applied.
- Every Git command of every phase uses one fixed hardened template (see Hardened Git template below).
- Unconfirmed host behaviors (REQ-013) stay unverified until observed; the recipe says so.

Assumptions: Claude Code workflows are enabled and not disabled by the organization; the plugin is installed and a workspace registered; sources are committed work; EUR 0 additional spend. No data, labels or sampling are involved, so no source-yield or consent gate is needed for this spec; the fixture corpus (T005) is synthetic and its truth labels are written before any tool output is read.

## Design and compatibility

File-level design (all new files unless stated):

| Path | Role | PR / task |
| --- | --- | --- |
| `integrations/agent-braid/plugin/workflows/braid-gate.js` | The workflow: SPDX header, literal `meta`, argument validation, five phases, schema-validated envelope | PR2 T008–T014 |
| `tests/test_claude_workflow_gate.py` | Static (Node-free) checks, argument and degradation tests, schema tests, corpus tests | PR2 T004–T007 |
| `tests/claude_workflow_gate_helpers.py` | Deterministic fixture repository builder and known-answer corpus | PR2 T005 |
| `scripts/build_native_plugin.py` (edit) | `assemble()` copies `workflows/` after the setup skill copy behind an explicit pre-adoption opt-in (default excluded until adoption); version unchanged in PR2 | PR2 T016; default flip T036; R1 T038 |
| `tests/test_plugin_package.py` (edit) | Inventory, reproducibility, tamper, absence-of-hooks, excluded-default and included-opt-in checks | PR2 T015; T036 |
| `scripts/validate_change.py` and `tests/test_validation_profiles.py` (edit) | Explicit rule for the workflow artifact type | PR2 T017–T018 |
| `docs/tooling/CLAUDE_WORKFLOWS.md` | Recipe | PR2 T019; updated T032 |
| `docs/tooling/NATIVE_PLUGINS.md`, `PLUGIN_PACKAGE_README.md`, `PLUGIN_PRIVACY.md`, `plugin-submissions/README.md` (edit) | Distinguish skills from the workflow component | PR2 T020; T036 |
| `specs/052-claude-workflow-gate/contracts/*` | Argument and result schemas | PR1 T001 |
| `specs/052-claude-workflow-gate/evidence/*`, `release-acceptance.md`, `delivery/publication.json` | Receipts | HV, R1 |
| `docs/adr/<next free number>-*.md` | Canonical ADR | PR3 T034, only on founder adoption |

Workflow shape. Phases and agents (agent budget in parentheses):

1. `validate` (1 agent): the fixed hardened read-only Git template and the bootstrap `workspaces` tool; strict schema; the script applies the refusal rules, including `workspace-not-registered`, `workspace-root-mismatch`, `runtime-enabled-workspace` and `unsafe-tool-surface`.
2. `analyze` (1 agent): MCP `analyze-work` with `kind: git`, commit sources, pinned base; no worktree or path source.
3. `baseline` (1 agent): pairwise `git merge-tree --write-tree --merge-base=<base>` with a temporary `GIT_OBJECT_DIRECTORY` and the repository store as alternate.
4. `finalize` (1 agent, always when the run is still live): replay evidence through MCP `analyze` and `prepare` only when eligible (runtime request derived by the script), then re-resolution of base and sources; a moved or deleted reference is the defined stale-reference outcome (`inconclusive`, `staleRefs`). If nothing is eligible it only re-resolves.
5. `report` (script only): agreement classification, status, advisory order, limits, schema validation.

The gate uses at most four agents: none when the arguments are refused, fewer when an earlier phase refuses, is busy or fails, and exactly four on every run that completes validate, analyze, baseline and finalize (including an `inconclusive` stale-reference run). That keeps the "at most four" bound without branching on counts. Prompts embed only validated identifiers and fixed command templates; no commit message, diff or file content is ever placed in a prompt, and agents return only schema-bound fields.

Hardened Git template (REQ-006). One template is embedded as script constants and used for every Git command of every phase, because the user's repository configuration and the `.gitattributes` content of agent branches are untrusted inputs and `docs/architecture/PARALLEL_INTEGRATION.md` keeps credentials, network, hooks, submodules, filters and arbitrary project commands disabled unless a reviewed profile names them. The template sets an explicit environment (`GIT_CONFIG_NOSYSTEM=1`, `GIT_CONFIG_GLOBAL=/dev/null`, `GIT_TERMINAL_PROMPT=0`, no network helpers) and `-c` overrides that disable hooks (`core.hooksPath=/dev/null`), fsmonitor, external merge drivers and content filters; the baseline adds a temporary `GIT_OBJECT_DIRECTORY` with the repository store as alternate. Precedents: `GIT_CONFIG_NOSYSTEM` and `GIT_TERMINAL_PROMPT` in `agent_braid/git_replay.py`, `-c core.hooksPath=/dev/null` in `agent_braid/git_runtime.py`. Open fact (T011): which exact overrides disable every configured merge driver and filter on the pinned Git is verified with a sentinel fixture, not assumed; a command that cannot be hardened is a stated limit and its phase is unavailable or inconclusive. D-8 hardens the object store only; this template hardens the rest.

Tool surface and "constrained" (REQ-016). Because prompts are not a control, three layers apply. (1) The script refuses, from the `workspaces` rows, when any registered workspace has runtime enabled or a grant store (`runtime-enabled-workspace`) and when the validate agent reports `execute`, `recover`, `verify` or `status` among its visible plugin tools (`unsafe-tool-surface`, agent-reported). (2) A host permission allowlist, documented in the recipe and recorded by HV-1/HV-5, allows only the plugin tools `workspaces`, `analyze-work`, `analyze` and `prepare` and the fixed read-only Git command prefixes. (3) "Bash constrained to the plugin launcher", as the founder clarification phrases the CLI fallback, is defined here as a permission rule set in force for the session (subagents use the session's permission rules, so a per-agent allowlist is not assumed) that allows the fixed read-only Git prefixes needed by the primary path and, only on the fallback, the explicit launcher subcommands `analyze-git`, `plan-git`, `verify-git` and the argument-less read-only `plugin workspaces` (the registry read the fallback uses to compute the registry rules), and no rule matching the launcher binary as a whole, `grant-policy-run`, `execute-policy-run`, `recover-policy-run` or any other launcher subcommand. Git read commands and the launcher subcommands therefore coexist for all gate agents; the script's prompts are the only per-agent narrowing and are not a control. If the host cannot express this rule set, "cannot be constrained" is a recorded no-go for the CLI fallback and an input to SPEC-053 REQ-009 (whose converter inherits the same constraint plus exactly one more explicit subcommand, `analyze-claude-transcripts`, used alongside working MCP tools, as a planning amendment approved by the founder on 2026-10-24). On the fallback the registry rules (`workspace-not-registered`, `workspace-root-mismatch`, `runtime-enabled-workspace`) are computed from the rows printed by `plugin workspaces`, and the fallback refuses with `mcp-unavailable` when they cannot be obtained (REQ-016(e)). The limit that rule (1) is evaluated after the validate agent ran is stated in REQ-016.

Builder guard (REQ-011). Until the ADR 0024 amendment is adopted, `assemble()` excludes `workflows/` by default; an explicit opt-in includes it and marks the artifact engineering-only. PR2 package tests assert both the excluded default and the included opt-in, and the default flips with the adoption tasks (T036).

Compatibility: additive, Claude only. The portable manifest, `mcp.json`, `.mcp.json`, the five product skills and the setup skill stay byte-identical; the Claude manifest relies on the documented default `workflows/` scan, so no manifest field changes. Existing contracts, schemas and grants are unchanged. PR2 does not change `VERSION`; the alpha.4 bump is R1 (T038). The `workflows/` copy is behind the pre-adoption opt-in described above.

## Validation strategy

Requirement → scenario → test → evidence is carried by [validation-plan.md](validation-plan.md) (`procedure_req_NNN`, aligned with `assurance.json`) and the [task list](tasks.md). Layers:

1. Structural and offline: Node-free static checks (T004), schema checks (T007), fixture corpus (T005), harness with substituted agents (T006, T009–T014), packaging (T015). A missing JavaScript runtime is an unavailable observation, not a pass.
2. Negative controls: equal-to-base, duplicate, non-descendant, one source, 33 operations, revision-syntax identifier, parallel wrapper, isolation option, fifth agent, `model` or `effort` option, runtime-enabled registration with a planted grant, sentinel hook, fsmonitor, merge driver and filter, default build containing `workflows/`, tampered package file, altered result schema, moved reference between phases, busy lock, unregistered workspace, timeout.
3. Comparison (REQ-015): analyzer verdict versus merge-tree baseline per pair on a known-answer corpus, with a classification table and denominators; counterexamples are findings; H1 and H2 are not requirements and are claimed only within the corpus.
4. Host (REQ-013): HV-1 to HV-5 on a recorded Claude Code version, saved transcripts, pass/fail/unobserved with version; failures trigger the fallback or kill criterion in [program.md](program.md).
5. Release (REQ-014): clean commit, reproduction, native install, update, uninstall, fixture matrix, explicit gaps.

Validation profile. This feature touches sensitive paths: `specs/**`, `integrations/**`, `scripts/build_native_plugin.py`, `agent_braid/trace_adapter.py` (SPEC-053 dependency; not edited by SPEC-052) and `docs/adr/**` (PR3). Per `docs/development/VALIDATION_PROFILES.md` the planner escalates quick runs on these paths to the sensitive profile; run `python3 -m scripts.validate_change --base develop --profile quick` after each coherent increment and `--profile pr` once per stable candidate. Frozen-candidate evidence, clean-room reproduction, host verification, independent and human review and founder approval remain separate boundary gates and are never implied by a passing profile.

## PR and gate sequence for this spec

| Step | Content | Gate and blockers |
| --- | --- | --- |
| PR1 | Specs and planning packet (this packet: plan, research, quickstart, validation plan, tasks, contracts, tracking drafts) | T001–T003; founder disposition T002 |
| PR2 | Workflow source, builder change, tests, validation rule, recipe and documentation, corpus comparison | T004–T022; no version bump, release or publication; may merge before ADR adoption per the clarification, with the builder excluding `workflows/` by default |
| Host verification | HV-1 to HV-5, native fixture runs, auto-mode and disabled-workflow runs | T023–T032; founder provides the host (EUR 0); failure triggers fallback or no-go |
| PR3 | ADR adoption, re-snapshot of specs 047, 048, 051 and any other record whose authority inventory includes `docs/adr`, `authority-impact-review.json`, README and rule updates, builder default flip | T033–T036; founder decision first |
| R1 | Version 0.1.0-alpha.4 (expected), build, reproduction, release acceptance | T037–T041; requires PR3 and host outcomes; independent of G0 |
| Publication | One scoped, owner-authorized plugin-dist write with a `delivery/publication.json` receipt | T042; forbidden in the delivery that created this packet |
| Tracking | Remote milestone, issue and Project publication | T043; drafts only until the founder authorizes |
| Closure | Radar milestone review, technical review, founder closure of the SPEC-052 part | T044–T046; M4.6 closure also needs the SPEC-053 and G0 items |

SPEC-053 (adapter) and a later gate v2 are outside this plan; SPEC-052 does not wait for G0.

## Risks

| Risk | Effect | Mitigation | Residual |
| --- | --- | --- | --- |
| Plugin MCP tools not visible to workflow agents (HV-1) | No analysis path | Refuse with `mcp-unavailable`; CLI fallback only with the explicit launcher-subcommand allowlist defined above; else R1 no-go for the CLI path | Possible no-go; recorded as valid |
| Model-callable `execute`/`recover` reachable by a gate agent | Authority breach by prompt failure | Refuse runtime-enabled registrations; host allowlist; `unsafe-tool-surface` check; transcript inspection (REQ-016) | The validate agent runs before the registration is known; allowlist is the only control for that agent |
| Hostile repository configuration or attributes (hooks, fsmonitor, merge drivers, filters) | Code execution during Git commands | Fixed hardened Git template; sentinel tests; unhardenable command makes its phase unavailable | Depends on the pinned Git honoring the overrides (T011) |
| Nested call by plugin name unsupported (HV-3) | Only the direct slash path remains | Recipe documents the verified path only; kill criterion if nesting is the only path | Possible narrowing |
| Agent misreports a command result | Wrong envelope | Strict schemas; the analyzer independently re-resolves commits; baseline compared with direct runs in tests; native runs compared with direct commands | Not eliminated: agents execute the commands |
| `expectedFinalTree` cannot be derived for more than two sources | `not-prepared` for those runs | Report the reason; treat as a finding, not a failure; do not guess | Reduced convenience |
| Equal-to-base or other silent false negative | Blocking defect | Refusal rule tested first; kill criterion | None accepted |
| Analyzer says independent-candidate and merge-tree conflicts | Counterexample | Recorded, blocks conservativeness wording; kill criterion only if unbounded | Valid finding |
| Host workflow API drift | Script unvalidatable | Static checks on the literal `meta`; record version; refuse unknown shapes | Ongoing |
| Packaging the gate before ADR adoption | Authority wording conflict; identity collision with the published alpha.3 bytes | No version bump, release or publication before adoption (clarification; T022); builder excludes `workflows/` by default and includes it only with an engineering-only opt-in (T015, T016) | Founder decision; opt-in artifacts are never releasable |
| Over-claiming | Claim-discipline breach | Canonical limits in the schema; review checklist; no speed claim | Review-dependent |
| Admission lock held by another caller | Busy result | Report `busy`, no retry loop | Operator retries manually |
| Resume reruns agents (HV-4) | Duplicate analysis or prepare call | Record behavior; prepare is non-allocating; no retry logic in script | To be observed |

## Constitution check after design

The design keeps analysis and execution separate (Article 20), computes gating in script (Article 12), couples no core module to the vendor host (Article 15), makes no workload or speed claim (Article 19) and creates no authority (ADR 0021). No MUST contradiction is introduced. The ADR 0024 wording conflict is real and is handled by the adoption path, not waived. Structural checks, schemas and passing profiles are not proof of semantic safety.

## Human review and unresolved decisions

- Founder: disposition of this packet (T002); ADR adoption (T033); R1 go/no-go and number (T037); release acceptance (T041); publication (T042); tracking publication (T043); closure (T046).
- The spec change requests found while planning (replay mapping to MCP `analyze`/`prepare`, the runtime-request fields needed by `prepare`, the validate agent's read-only `workspaces` call, the all-match nature of the validation rules, the stale-reference outcome, the tool-surface control and the assurance block) were applied to spec.md on 2026-10-23; they remain planning edits pending human review, not approval.
- Open facts to be observed rather than assumed: HV-1 to HV-5; whether `git merge-tree` accepts a tree-ish as a branch argument on the pinned Git (needed for the chained expected-tree derivation); whether the hardening overrides disable every configured merge driver and filter; whether the host can express the REQ-016 allowlist; the Claude Code version(s) used.
- No dates, effort estimates or positive benefit claims are stated.
