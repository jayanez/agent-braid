# SPEC-061 research

Sources were read on 2026-10-31. Host behavior described here is documentation
reading, not observation; REQ-014 tasks record observations separately.

## Repository facts reused

| Fact | Source | Use |
|---|---|---|
| Pairwise classification `ordered`, `conflicting`, `unknown`, `independent-candidate` with `sharedResources`, `reasons`, `constraints` and `evidence` (`method`, `assuranceClass`, `coverage`, `ruleSet`); report-level `summary`, `uncertainty` and `limits` | `agent_braid/analysis.py` (`analyze`, `_interaction`) | `crossing.classified`, `analysis.report` |
| Advisory plan `mode` (`candidate-preparation-waves`, `serial-fallback`, `manual-review`), `waves`, `fallbackOrder`, `conditions` | `agent_braid/git_replay.py` | `wave.planned` |
| Waves and workers with `startedNs`, `finishedNs`, `wave` | `agent_braid/runtime_scheduler.py` (`prepare_schedule`, `run_preparations`) | `wave.started`, `wave.finished`, strand spans |
| Operator grants with `issuedAt` and `expiresAt`, consumption and the refusal `operator grant expired or invalid` | `agent_braid/runtime_policy.py` (`prepare_policy_run`, `issue_operator_grant`) | `grant.issued` and `grant.consumed` from artifacts; `grant.expired` derived (`derived: true`) when a recorded grant's `expiresAt` has passed without consumption; `grant.refused` only from a recorded refusal envelope |
| Runtime phases in `state.json` | `agent_braid/git_runtime.py` (`prepare_run`) | `runtime.phase` |
| Pre-flight notices, receipts and hazard kinds | SPEC-057 outputs of `agent_braid/ownership.py` | `hazard.noticed`; read as JSON only |
| Workflow-gate phases and results (status enums copied verbatim) | SPEC-052 `braid-gate-result.schema.json`, `evidence/native-gate-runs.json` | `gate.phase`, `gate.result`, crossings |
| Host stream usage | `agent_braid/tooling_host_events.py` (`parse_host_events`), `tooling_incremental_usage.py` | `effort.sample`, `observation.gap` |
| Static presentation, escaping and export destination rules | `agent_braid/tooling_present.py` (`render_graph_ascii`, `_svg_graph`, `write_exports`) | frames, export |
| Field-level comparison row shape | `agent_braid/harness_records.py` (`compare`) | effort pack comparison |

Constraints found: `tests/test_plugin_package.py` rejects hooks, mods, monitors,
agents and channels inside `integrations/agent-braid/`;
`tests/test_orchestration_governance.py` rejects ownership imports and ownership
command names outside `cli.py` and `ownership_cli.py`; the validation classifier
fails closed for unknown paths; the core has no runtime dependency.

## Visual grammar

| Visual | Fact | Rule |
|---|---|---|
| Strand (tube along the time axis) | agent, operation or ownership unit | one per `strand.open` |
| Lane swap at a crossing | `independent-candidate` pair on one host | the only pair drawn as a swap; layout only |
| Directed link, no swap | `ordered` pair | arrow from the earlier to the later operation |
| No swap, recoil, red knot | `conflicting` pair | never drawn as a swap |
| Dashed pulsing link, no swap | `unknown` pair | never drawn as a swap or coloured as independent |
| Class badge on each crossing | `compatibilityClass` | categorical label and glyph per class (0 heuristic … 5 Yang–Baxter); never brightness or opacity; legend says "not a guarantee" |
| Bridge over intermediate lanes | a classified pair whose strands are not adjacent | intermediate strands are visibly not crossed; lanes are reordered to keep classified pairs adjacent where possible |
| Arc between host planes | cross-host pair | Claude, Braid and Codex planes |
| Translucent slab and grey serial ghost | `wave.planned` and the serial fallback | planned wave width against serial slots (advisory plan, not verified safe) |
| Ring gate | grant or workflow gate | colour by result |
| Cone | `hazard.noticed` | anchored at its unit strand |
| Tube radius and moving particles | effort samples | logarithmic radius, `host-estimate` |
| Broken strand with grey stub | `observation.gap` | absence is visible |

Article 11 boundary: crossings come only from computed classifications; lane order
is a layout choice; no braid relation or simplification is applied or implied, and
no crossing is drawn between strands that have no classified pair. Article 13
boundary: classes are shown categorically, never as a safety ordering.

## Spike lessons (throwaway, not evidence)

A scratchpad spike built 87 events from real computations (analysis of
`examples/analysis/file-edits.json` with an added conflicting and an unknown
operation, a Git runtime fixture with one wave of four workers and an operator
grant, the SPEC-052 gate runs, an ownership declaration with pre-flight and receipt
hazards, and host stream fixtures) and rendered them with Three.js 0.182.0.

1. The closed kind list was sufficient for every artifact family tried.
2. The adapters needed only public functions plus JSON reading of ownership outputs.
3. The swap/no-swap encoding made conflicts readable without text.
4. The serial ghost made "4 operations → 1 planned wave (serial 4)" legible.
5. Gaps found during the spike, to resolve in VIS.1: the time axis used `seq`
   instead of `relMs`; swaps between non-adjacent lanes crossed other strands
   (reorder lanes and draw bridges, never implicit crossings); opacity by class
   suggested a safety ordering (use categorical badges); wave height used final
   lane positions; Three.js came from a CDN; there was no live ingest.

## Host surfaces (documentation, 2026-10-31)

- **Claude Code**: OpenTelemetry export over OTLP HTTP/JSON with token, cost and
  agent identifiers (`claude_code.api_request` events); hooks may POST over HTTP
  (`SubagentStart`, `SubagentStop`, `PreToolUse`, `PostToolUse` and others, without
  tokens); mods (early access) can open a pane with SVG on desktop and kitty
  graphics images on terminals (VIS.2); the desktop browser pane shows loopback
  pages.
- **Codex**: OpenTelemetry `[otel]` export (`codex.turn.token_usage`), command
  hooks and `notify` (`agent-turn-complete`), rollout JSONL with cumulative token
  counts, the app-server JSON-RPC (`thread/tokenUsage/updated`); no side-panel
  API; MCP Apps (SEP-1865) render in Codex Desktop depending on the build (VIS.3).
- **Other hosts**: Cursor, OpenCode, Pi and VS Code converge on MCP, OpenTelemetry
  and their own hooks or JSONL; the loopback viewer and an MCP App cover most of
  them (VIS.4).
- **Three.js**: MIT; r182 recommends `WebGPURenderer` with a WebGL2 fallback.
  VIS.1 uses the WebGL2 renderer for broad support; WebGPU is a later option.
- **OpenTelemetry GenAI semantic conventions** are in Development; used as
  vocabulary only.

## Alternatives considered

| Alternative | Decision |
|---|---|
| Mod or hooks inside the plugin package | Rejected: ADR 0024/0029 and plugin package tests. |
| Hosted dashboard or remote collector | Rejected: privacy, upload and account requirements. |
| Replay-only first release | Rejected by the owner (D3): live ingest from VIS.1. |
| npm toolchain and bundler | Rejected: no Node in CI; vendored prebuilt ES modules with a hash manifest instead. |
| Persisting effort | Rejected (D4): ephemeral; explicit export only. |
| Registering the pack as a harness record kind | Deferred to HAR; VIS.1 reuses the comparison row shape. |

## Prior art

Session dashboards for Claude Code and Codex exist (for example claude-view,
agent-mission-control, a `mission-control` mod, agentviz, ccusage). They show
sessions, cost and tool calls. None of the tools reviewed on 2026-10-31 shows the
coordination layer: classified pairs, planned waves, grants, hazards and the
evidence behind them. That is the gap this viewer addresses.

## Sources

- https://code.claude.com/docs/en/monitoring-usage
- https://code.claude.com/docs/en/hooks
- https://learn.chatgpt.com/docs/app-server
- https://learn.chatgpt.com/docs/hooks
- https://github.com/openai/codex/issues/21019
- https://github.com/modelcontextprotocol/ext-apps/blob/main/specification/2026-01-26/apps.mdx
- https://threejs.org/manual/en/webgpurenderer
- https://github.com/davidbalivo/mission-control
